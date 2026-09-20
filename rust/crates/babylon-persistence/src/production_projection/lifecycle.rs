//! Period-local order witnesses, including admissions absent from both snapshots.
//! These joins authenticate receipts; they do not allocate, plan, or replay work.
use super::ProductionProjectionError;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    recurring_household_order_id, recurring_procurement_order_id, AccountId, CircuitAccounting,
    FinalDemandOrder, MaterialCircuitState, MonetaryCircuit, MoneyLocation, MoneyTransferPurpose,
    OrderAccessMode, OrderId, OrderRow, OutboundOrderId, PurchaseEscrow, RecurringEconomy,
};
use babylon_tick::material_world::MaterialTickReceipts;
use std::collections::{BTreeMap, BTreeSet};

type Result<T> = std::result::Result<T, ProductionProjectionError>;

pub(super) struct PeriodOrders {
    pub deliveries: BTreeMap<OrderId, (OrderRow, OrderRow)>,
    pub final_orders: BTreeMap<OrderId, (FinalDemandOrder, FinalDemandOrder)>,
    pub early_retired: BTreeSet<OutboundOrderId>,
    pub expired: BTreeMap<OrderId, u64>,
}

pub(super) fn recurring(state: &MaterialCircuitState) -> Option<&RecurringEconomy> {
    match &state.accounting {
        CircuitAccounting::Monetary(book) => book.recurring.as_deref(),
        CircuitAccounting::PhysicalControl => None,
    }
}

fn monetary(state: &MaterialCircuitState) -> Option<&MonetaryCircuit> {
    match &state.accounting {
        CircuitAccounting::Monetary(book) => Some(book),
        CircuitAccounting::PhysicalControl => None,
    }
}

pub(super) fn join(
    prior: &MaterialCircuitState,
    current: &MaterialCircuitState,
    receipts: &MaterialTickReceipts,
) -> Result<PeriodOrders> {
    if prior.period.checked_add(1) != Some(current.period) || receipts.resolve_tick != prior.period
    {
        return Err(ProductionProjectionError::History);
    }
    if monetary(prior).is_some() != monetary(current).is_some()
        || recurring(prior).is_some() != recurring(current).is_some()
    {
        return Err(ProductionProjectionError::State);
    }
    if monetary(prior).is_none()
        && (!receipts.money_transfers.is_empty()
            || !receipts.wage_accruals.is_empty()
            || !receipts.labor_use.is_empty())
    {
        return Err(ProductionProjectionError::State);
    }
    let mut orders = PeriodOrders {
        deliveries: BTreeMap::new(),
        final_orders: BTreeMap::new(),
        early_retired: BTreeSet::new(),
        expired: BTreeMap::new(),
    };
    for row in &prior.orders {
        if orders
            .deliveries
            .insert(row.order_id, (row.clone(), row.clone()))
            .is_some()
        {
            return Err(ProductionProjectionError::State);
        }
    }
    for row in &prior.final_demand_orders {
        if orders
            .final_orders
            .insert(row.order_id, (row.clone(), row.clone()))
            .is_some()
        {
            return Err(ProductionProjectionError::State);
        }
    }
    let mut admissions = BTreeMap::new();
    admit_households(prior, receipts, &mut orders, &mut admissions)?;
    admit_firms(prior, receipts, &mut orders, &mut admissions)?;
    add_movements(receipts, &mut orders)?;
    reconcile(prior, current, &mut orders)?;
    check_purchases(prior, current, receipts, &orders, &admissions)?;
    Ok(orders)
}

fn admit_households(
    prior: &MaterialCircuitState,
    receipts: &MaterialTickReceipts,
    orders: &mut PeriodOrders,
    admissions: &mut BTreeMap<OutboundOrderId, PurchaseEscrow>,
) -> Result<()> {
    let offers = offer_index(prior)?;
    let policies = recurring(prior)
        .map(|rows| rows.household_purchases.as_slice())
        .unwrap_or_default();
    let mut expected: BTreeMap<_, _> = policies
        .iter()
        .map(|row| ((row.principal_id, row.good_id, row.unit_id), row))
        .collect();
    if expected.len() != policies.len() {
        return Err(ProductionProjectionError::State);
    }
    for row in &receipts.household_demand {
        let key = (row.principal_id, row.good_id, row.unit_id);
        let policy = expected
            .remove(&key)
            .ok_or(ProductionProjectionError::State)?;
        let price = *offers
            .get(&(policy.retailer_site_id, row.good_id, row.unit_id))
            .ok_or(ProductionProjectionError::State)?;
        if row.period != prior.period
            || row.order_id != recurring_household_order_id(prior.period, key)
            || row.retailer_site_id != policy.retailer_site_id
            || row.unit_price != price
            || row.admitted_quantity > row.requested_quantity
            || row.requested_quantity > row.desired_quantity
            || row.requested_quantity > policy.maximum_purchase
            || (!policy.enabled && row.requested_quantity != 0)
            || row.fulfilled_quantity.checked_add(row.expired_quantity)
                != Some(row.admitted_quantity)
            || orders.final_orders.contains_key(&row.order_id)
        {
            return Err(ProductionProjectionError::State);
        }
        if row.admitted_quantity == 0 {
            continue;
        }
        let order = FinalDemandOrder {
            order_id: row.order_id,
            demand_principal_id: row.principal_id,
            retailer_site_id: row.retailer_site_id,
            good_id: row.good_id,
            unit_id: row.unit_id,
            ordered: row.admitted_quantity,
            fulfilled: 0,
        };
        orders
            .final_orders
            .insert(row.order_id, (order.clone(), order));
        orders.expired.insert(row.order_id, row.expired_quantity);
        let id = OutboundOrderId::LocalFinalDemand(row.order_id);
        let purchase = PurchaseEscrow::new(
            id,
            AccountId::Household(row.principal_id),
            AccountId::Site(row.retailer_site_id),
            row.admitted_quantity,
            row.unit_price,
        )
        .map_err(|_| ProductionProjectionError::State)?;
        if admissions.insert(id, purchase).is_some() {
            return Err(ProductionProjectionError::State);
        }
    }
    if !expected.is_empty() {
        return Err(ProductionProjectionError::State);
    }
    Ok(())
}

type OfferKey = (
    babylon_material_circuit::SiteId,
    babylon_material_circuit::GoodId,
    babylon_material_circuit::UnitId,
);
fn offer_index(prior: &MaterialCircuitState) -> Result<BTreeMap<OfferKey, Currency>> {
    let mut result = BTreeMap::new();
    for row in recurring(prior)
        .map(|rows| rows.offers.as_slice())
        .unwrap_or_default()
    {
        if row.unit_price.micro_units() <= 0
            || result
                .insert((row.site_id, row.good_id, row.unit_id), row.unit_price)
                .is_some()
        {
            return Err(ProductionProjectionError::State);
        }
    }
    Ok(result)
}

fn admit_firms(
    prior: &MaterialCircuitState,
    receipts: &MaterialTickReceipts,
    orders: &mut PeriodOrders,
    admissions: &mut BTreeMap<OutboundOrderId, PurchaseEscrow>,
) -> Result<()> {
    let offers = offer_index(prior)?;
    let policies = recurring(prior)
        .map(|rows| rows.replenishment.as_slice())
        .unwrap_or_default();
    let mut expected: BTreeMap<_, _> = policies
        .iter()
        .map(|row| {
            (
                (
                    row.buyer_site_id,
                    row.supplier_site_id,
                    row.good_id,
                    row.unit_id,
                ),
                row,
            )
        })
        .collect();
    if expected.len() != policies.len() {
        return Err(ProductionProjectionError::State);
    }
    for row in &receipts.procurement {
        let key = (
            row.buyer_site_id,
            row.supplier_site_id,
            row.good_id,
            row.unit_id,
        );
        let policy = expected
            .remove(&key)
            .ok_or(ProductionProjectionError::State)?;
        if row.period != prior.period
            || row.order_id
                != recurring_procurement_order_id(prior.period, key.0, key.1, key.2, key.3)
            || Some(&row.unit_price) != offers.get(&(key.1, key.2, key.3))
            || row.target_stock != policy.target_stock
            || row.desired_quantity > policy.maximum_purchase
            || row.admitted_quantity > row.desired_quantity
            || orders.deliveries.contains_key(&row.order_id)
        {
            return Err(ProductionProjectionError::State);
        }
        if row.admitted_quantity == 0 {
            continue;
        }
        let order = OrderRow {
            order_id: row.order_id,
            access_mode: OrderAccessMode::CommoditySale,
            buyer_site_id: key.0,
            supplier_site_id: key.1,
            good_id: key.2,
            unit_id: key.3,
            ordered: row.admitted_quantity,
            shipped: 0,
            delivered: 0,
            realized: 0,
            lost: 0,
        };
        orders
            .deliveries
            .insert(row.order_id, (order.clone(), order));
        let id = OutboundOrderId::Delivery(row.order_id);
        let purchase = PurchaseEscrow::new(
            id,
            AccountId::Site(key.0),
            AccountId::Site(key.1),
            row.admitted_quantity,
            row.unit_price,
        )
        .map_err(|_| ProductionProjectionError::State)?;
        if admissions.insert(id, purchase).is_some() {
            return Err(ProductionProjectionError::State);
        }
    }
    if !expected.is_empty() {
        return Err(ProductionProjectionError::State);
    }
    Ok(())
}

fn add(total: &mut u64, value: u64) -> Result<()> {
    if value == 0 {
        return Err(ProductionProjectionError::State);
    }
    *total = total
        .checked_add(value)
        .ok_or(ProductionProjectionError::Arithmetic)?;
    Ok(())
}

fn quantities(rows: impl Iterator<Item = (OrderId, u64)>) -> Result<BTreeMap<OrderId, u64>> {
    let mut result = BTreeMap::new();
    for (id, quantity) in rows {
        add(result.entry(id).or_default(), quantity)?;
    }
    Ok(result)
}

fn add_movements(receipts: &MaterialTickReceipts, orders: &mut PeriodOrders) -> Result<()> {
    add_transport_movements(receipts, orders)?;
    let mut outbound = BTreeSet::new();
    for row in &receipts.dispatches {
        if !outbound.insert(OutboundOrderId::Delivery(row.order_id)) {
            return Err(ProductionProjectionError::State);
        }
        add(
            &mut orders
                .deliveries
                .get_mut(&row.order_id)
                .ok_or(ProductionProjectionError::State)?
                .1
                .shipped,
            row.quantity,
        )?;
    }
    for row in &receipts.local_transfers {
        if !outbound.insert(OutboundOrderId::Delivery(row.order_id)) {
            return Err(ProductionProjectionError::State);
        }
        let value = &mut orders
            .deliveries
            .get_mut(&row.order_id)
            .ok_or(ProductionProjectionError::State)?
            .1;
        if (
            value.supplier_site_id,
            value.buyer_site_id,
            value.good_id,
            value.unit_id,
        ) != (
            row.supplier_site_id,
            row.buyer_site_id,
            row.good_id,
            row.unit_id,
        ) {
            return Err(ProductionProjectionError::State);
        }
        add(&mut value.shipped, row.quantity)?;
        add(&mut value.delivered, row.quantity)?;
        add(&mut value.realized, row.quantity)?;
    }
    for row in &receipts.local_fulfillments {
        if !outbound.insert(OutboundOrderId::LocalFinalDemand(row.order_id)) {
            return Err(ProductionProjectionError::State);
        }
        let value = &mut orders
            .final_orders
            .get_mut(&row.order_id)
            .ok_or(ProductionProjectionError::State)?
            .1;
        if (
            value.demand_principal_id,
            value.retailer_site_id,
            value.good_id,
            value.unit_id,
        ) != (
            row.demand_principal_id,
            row.retailer_site_id,
            row.good_id,
            row.unit_id,
        ) {
            return Err(ProductionProjectionError::State);
        }
        add(&mut value.fulfilled, row.quantity)?;
    }
    for row in &receipts.household_demand {
        let quantity = orders
            .final_orders
            .get(&row.order_id)
            .map_or(0, |(_, close)| close.fulfilled);
        if quantity != row.fulfilled_quantity {
            return Err(ProductionProjectionError::State);
        }
    }
    Ok(())
}

fn add_transport_movements(
    receipts: &MaterialTickReceipts,
    orders: &mut PeriodOrders,
) -> Result<()> {
    let arrivals = quantities(
        receipts
            .arrivals
            .iter()
            .map(|row| (row.order_id, row.quantity)),
    )?;
    if arrivals
        != quantities(
            receipts
                .deliveries
                .iter()
                .map(|row| (row.order_id, row.quantity)),
        )?
        || arrivals
            != quantities(
                receipts
                    .realizations
                    .iter()
                    .map(|row| (row.order_id, row.quantity)),
            )?
    {
        return Err(ProductionProjectionError::State);
    }
    for row in &receipts.losses {
        add(
            &mut orders
                .deliveries
                .get_mut(&row.order_id)
                .ok_or(ProductionProjectionError::State)?
                .1
                .lost,
            row.quantity,
        )?;
    }
    for row in &receipts.arrivals {
        add(
            &mut orders
                .deliveries
                .get_mut(&row.order_id)
                .ok_or(ProductionProjectionError::State)?
                .1
                .delivered,
            row.quantity,
        )?;
    }
    for row in &receipts.realizations {
        add(
            &mut orders
                .deliveries
                .get_mut(&row.order_id)
                .ok_or(ProductionProjectionError::State)?
                .1
                .realized,
            row.quantity,
        )?;
    }
    Ok(())
}

fn reconcile(
    prior: &MaterialCircuitState,
    current: &MaterialCircuitState,
    orders: &mut PeriodOrders,
) -> Result<()> {
    let in_transit: BTreeSet<_> = current.freight.iter().map(|lot| lot.order_id).collect();
    let mut actual: BTreeMap<_, _> = current
        .orders
        .iter()
        .map(|row| (row.order_id, row))
        .collect();
    if actual.len() != current.orders.len() {
        return Err(ProductionProjectionError::State);
    }
    for (id, (before, after)) in &orders.deliveries {
        if after.shipped > after.ordered
            || after
                .delivered
                .checked_add(after.lost)
                .is_none_or(|closed| closed > after.shipped)
            || after.realized > after.delivered
            || (monetary(prior).is_some() && after.realized != after.delivered)
        {
            return Err(ProductionProjectionError::State);
        }
        match actual.remove(id) {
            Some(row) if row == after => {}
            None if recurring(prior).is_some()
                && after.delivered.checked_add(after.lost) == Some(after.ordered)
                && !in_transit.contains(id) =>
            {
                if before.shipped == before.ordered {
                    orders.early_retired.insert(OutboundOrderId::Delivery(*id));
                }
            }
            _ => return Err(ProductionProjectionError::State),
        }
    }
    if !actual.is_empty() {
        return Err(ProductionProjectionError::State);
    }
    let mut actual: BTreeMap<_, _> = current
        .final_demand_orders
        .iter()
        .map(|row| (row.order_id, row))
        .collect();
    if actual.len() != current.final_demand_orders.len() {
        return Err(ProductionProjectionError::State);
    }
    for (id, (before, after)) in &orders.final_orders {
        if after.fulfilled > after.ordered {
            return Err(ProductionProjectionError::State);
        }
        match actual.remove(id) {
            Some(row) if row == after && !orders.expired.contains_key(id) => {}
            None if recurring(prior).is_some()
                && after
                    .fulfilled
                    .checked_add(orders.expired.get(id).copied().unwrap_or(0))
                    == Some(after.ordered) =>
            {
                if before.fulfilled == before.ordered {
                    orders
                        .early_retired
                        .insert(OutboundOrderId::LocalFinalDemand(*id));
                }
            }
            _ => return Err(ProductionProjectionError::State),
        }
    }
    if !actual.is_empty() {
        return Err(ProductionProjectionError::State);
    }
    Ok(())
}

fn check_cash(
    before: &MonetaryCircuit,
    after: &MonetaryCircuit,
    receipts: &MaterialTickReceipts,
) -> Result<()> {
    let mut cash: BTreeMap<_, _> = before
        .book
        .snapshot()
        .accounts
        .into_iter()
        .map(|row| (row.id, row.cash.micro_units()))
        .collect();
    for transfer in &receipts.money_transfers {
        if transfer.debit.delta.micro_units() >= 0
            || transfer.credit.delta.micro_units() <= 0
            || transfer
                .debit
                .delta
                .micro_units()
                .checked_add(transfer.credit.delta.micro_units())
                != Some(0)
        {
            return Err(ProductionProjectionError::State);
        }
        for posting in [&transfer.debit, &transfer.credit] {
            if let MoneyLocation::Cash(id) = posting.location {
                let value = cash.get_mut(&id).ok_or(ProductionProjectionError::State)?;
                *value = value
                    .checked_add(posting.delta.micro_units())
                    .ok_or(ProductionProjectionError::Arithmetic)?;
                if *value < 0 {
                    return Err(ProductionProjectionError::State);
                }
            }
        }
    }
    let closing: BTreeMap<_, _> = after
        .book
        .snapshot()
        .accounts
        .into_iter()
        .map(|row| (row.id, row.cash.micro_units()))
        .collect();
    if cash != closing {
        return Err(ProductionProjectionError::State);
    }
    Ok(())
}

fn check_purchases(
    prior: &MaterialCircuitState,
    current: &MaterialCircuitState,
    receipts: &MaterialTickReceipts,
    orders: &PeriodOrders,
    admissions: &BTreeMap<OutboundOrderId, PurchaseEscrow>,
) -> Result<()> {
    let (Some(before), Some(after)) = (monetary(prior), monetary(current)) else {
        return Ok(());
    };
    check_cash(before, after, receipts)?;
    let mut closing: BTreeMap<_, _> = after
        .book
        .snapshot()
        .purchases
        .into_iter()
        .map(|row| (row.order, row))
        .collect();
    let mut principals: BTreeMap<_, _> = before
        .book
        .snapshot()
        .purchases
        .into_iter()
        .map(|row| (row.order, row))
        .collect();
    for (id, row) in admissions {
        if principals.insert(*id, row.clone()).is_some() {
            return Err(ProductionProjectionError::State);
        }
    }
    if principals.len() != orders.deliveries.len() + orders.final_orders.len() {
        return Err(ProductionProjectionError::State);
    }
    let active: BTreeSet<_> = current
        .orders
        .iter()
        .map(|row| OutboundOrderId::Delivery(row.order_id))
        .chain(
            current
                .final_demand_orders
                .iter()
                .map(|row| OutboundOrderId::LocalFinalDemand(row.order_id)),
        )
        .collect();
    if active.iter().ne(closing.keys()) {
        return Err(ProductionProjectionError::State);
    }
    let mut amounts = purchase_amounts(receipts, &principals)?;
    for (id, mut principal) in principals {
        principal = advance_purchase(
            principal,
            orders,
            admissions.contains_key(&id),
            amounts.remove(&id).unwrap_or_default(),
        )?;
        match closing.remove(&id) {
            Some(value) if value == principal => {}
            None if recurring(prior).is_some()
                && principal.delivered.checked_add(principal.refunded)
                    == Some(principal.quantity) => {}
            _ => return Err(ProductionProjectionError::State),
        }
    }
    if !closing.is_empty() || !amounts.is_empty() {
        return Err(ProductionProjectionError::State);
    }
    Ok(())
}

fn purchase_amounts(
    receipts: &MaterialTickReceipts,
    principals: &BTreeMap<OutboundOrderId, PurchaseEscrow>,
) -> Result<BTreeMap<OutboundOrderId, [i128; 3]>> {
    let mut amounts = BTreeMap::<_, [i128; 3]>::new();
    for row in &receipts.money_transfers {
        let (id, offset) = match row.purpose {
            MoneyTransferPurpose::PurchaseReservation(id) => (id, 0),
            MoneyTransferPurpose::DeliverySettlement(id) => (id, 1),
            MoneyTransferPurpose::PurchaseRefund(id) => (id, 2),
            _ => continue,
        };
        let principal = principals
            .get(&id)
            .ok_or(ProductionProjectionError::State)?;
        let (debit, credit) = match offset {
            0 => (
                MoneyLocation::Cash(principal.buyer),
                MoneyLocation::PurchaseReserve(id),
            ),
            1 => (
                MoneyLocation::PurchaseReserve(id),
                MoneyLocation::Cash(principal.seller),
            ),
            _ => (
                MoneyLocation::PurchaseReserve(id),
                MoneyLocation::Cash(principal.buyer),
            ),
        };
        let value = row.credit.delta.micro_units();
        if value <= 0
            || row.debit.delta.micro_units().checked_add(value) != Some(0)
            || (row.debit.location, row.credit.location) != (debit, credit)
        {
            return Err(ProductionProjectionError::State);
        }
        let total = &mut amounts.entry(id).or_default()[offset];
        *total = total
            .checked_add(value)
            .ok_or(ProductionProjectionError::Arithmetic)?;
    }
    Ok(amounts)
}

fn advance_purchase(
    mut principal: PurchaseEscrow,
    orders: &PeriodOrders,
    admitted: bool,
    amounts: [i128; 3],
) -> Result<PurchaseEscrow> {
    let id = principal.order;
    let (delivered, refunded, buyer, seller, quantity) = match id {
        OutboundOrderId::Delivery(id) => {
            let (_, row) = orders
                .deliveries
                .get(&id)
                .ok_or(ProductionProjectionError::State)?;
            (
                row.delivered,
                row.lost,
                AccountId::Site(row.buyer_site_id),
                AccountId::Site(row.supplier_site_id),
                row.ordered,
            )
        }
        OutboundOrderId::LocalFinalDemand(id) => {
            let (_, row) = orders
                .final_orders
                .get(&id)
                .ok_or(ProductionProjectionError::State)?;
            (
                row.fulfilled,
                orders.expired.get(&id).copied().unwrap_or(0),
                AccountId::Household(row.demand_principal_id),
                AccountId::Site(row.retailer_site_id),
                row.ordered,
            )
        }
    };
    if (principal.buyer, principal.seller, principal.quantity) != (buyer, seller, quantity) {
        return Err(ProductionProjectionError::State);
    }
    let amount = |quantity: u64| {
        principal
            .unit_price
            .micro_units()
            .checked_mul(i128::from(quantity))
            .ok_or(ProductionProjectionError::Arithmetic)
    };
    let expected = [
        if admitted { amount(quantity)? } else { 0 },
        amount(
            delivered
                .checked_sub(principal.delivered)
                .ok_or(ProductionProjectionError::State)?,
        )?,
        amount(
            refunded
                .checked_sub(principal.refunded)
                .ok_or(ProductionProjectionError::State)?,
        )?,
    ];
    if amounts != expected {
        return Err(ProductionProjectionError::State);
    }
    principal.delivered = delivered;
    principal.refunded = refunded;
    Ok(principal)
}

/// Authenticate active and ephemeral principals before a committed period enters history.
pub(crate) fn validate_period(
    prior: &MaterialCircuitState,
    current: &MaterialCircuitState,
    receipt: &MaterialTickReceipts,
) -> Result<()> {
    join(prior, current, receipt)?;
    if recurring(prior).is_some() {
        super::households::completed_balances(prior, current, receipt)?;
    }
    Ok(())
}
