//! Finite procurement and subsequent plans derived from the same market close.

use std::collections::{BTreeMap, BTreeSet};

use babylon_kernel::currency::Currency;

use super::AttendancePlan;
use crate::clearing::{MarketBid, MarketMoment, MarketTable, Offer};
use crate::transition::MaterialContext;
use crate::valuation::CostClose;
use crate::LocalRetailFulfillmentReceipt;
use crate::MaintenanceReceipt;
use crate::MaterialCatalog;
use crate::ServiceMarketReceipt;
use crate::{
    AccountId, CircuitAccounting, GoodId, HouseholdDemandReceipt, LocalTransferReceipt,
    MaterialCircuitError, MaterialCircuitState, MonetaryCircuit, MoneyTransferReceipt,
    OrderAccessMode, OrderId, OrderRow, OutboundOrderId, ProcessId, PurchaseEscrow,
    RecurringEconomy, ReplenishmentPolicy, RoutedDispatchReceipt, SiteId, UnitId,
};
use babylon_kernel::content_digest;

pub(crate) type StockKey = (SiteId, GoodId, UnitId);
type StockLedger = BTreeMap<StockKey, u64>;

fn active(state: &MaterialCircuitState) -> bool {
    matches!(&state.accounting, CircuitAccounting::Monetary(economy) if economy.recurring.is_some())
}

/// Inspection of an inventory-position decision before any supplier allocation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProcurementReceipt {
    pub period: u64,
    pub order_id: OrderId,
    pub buyer_site_id: SiteId,
    pub supplier_site_id: SiteId,
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub on_hand: u64,
    pub outstanding_inbound: u64,
    pub target_stock: u64,
    pub desired_quantity: u64,
    pub admitted_quantity: u64,
    pub unit_price: Currency,
}

/// A demand cap is a plan, not a promise that inputs, labor or money will exist.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProductionPlanReceipt {
    pub period: u64,
    pub next_period: u64,
    pub process_id: ProcessId,
    pub site_id: SiteId,
    pub dispatched_quantity: u64,
    pub unshipped_quantity: u64,
    pub closing_output_stock: u64,
    pub output_buffer: u64,
    pub planned_batches: u64,
}

fn add(
    rows: &mut BTreeMap<StockKey, u64>,
    key: StockKey,
    quantity: u64,
) -> Result<(), MaterialCircuitError> {
    let value = rows.entry(key).or_default();
    *value = value
        .checked_add(quantity)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    Ok(())
}

fn stock_position(
    state: &MaterialCircuitState,
    deferred_local: &[LocalTransferReceipt],
) -> Result<(StockLedger, StockLedger), MaterialCircuitError> {
    let mut on_hand: BTreeMap<_, _> = state
        .inventory
        .iter()
        .map(|row| ((row.site_id, row.good_id, row.unit_id), row.quantity))
        .collect();
    for row in deferred_local {
        add(
            &mut on_hand,
            (row.buyer_site_id, row.good_id, row.unit_id),
            row.quantity,
        )?;
    }
    let mut pending = BTreeMap::new();
    for row in &state.orders {
        let outstanding = row
            .ordered
            .checked_sub(row.delivered)
            .and_then(|value| value.checked_sub(row.lost))
            .ok_or(MaterialCircuitError::PurchaseInvariant)?;
        // Undelivered order quantity already contains its freight. Adding the
        // freight table here would count each in-transit good twice.
        add(
            &mut pending,
            (row.buyer_site_id, row.good_id, row.unit_id),
            outstanding,
        )?;
    }
    Ok((on_hand, pending))
}

/// Stable supplier-order identity independent of subsequent fulfillment or quote changes.
#[must_use]
pub fn recurring_procurement_order_id(
    period: u64,
    buyer: SiteId,
    supplier: SiteId,
    good: GoodId,
    unit: UnitId,
) -> OrderId {
    let mut bytes = b"babylon.recurring-procurement.v1\0".to_vec();
    bytes.extend_from_slice(&period.to_be_bytes());
    bytes.extend_from_slice(&buyer.as_bytes());
    bytes.extend_from_slice(&supplier.as_bytes());
    bytes.extend_from_slice(&good.as_bytes());
    bytes.extend_from_slice(&unit.as_bytes());
    OrderId::from_bytes(content_digest::sha256_of(&bytes))
}

/// The stock a buyer holds, what is on its way, and what its policy asks it to buy now.
struct Position {
    stock: u64,
    inbound: u64,
    desired: u64,
}

fn position(
    policy: &ReplenishmentPolicy,
    on_hand: &StockLedger,
    pending: &StockLedger,
) -> Result<Position, MaterialCircuitError> {
    let key = (policy.buyer_site_id, policy.good_id, policy.unit_id);
    let stock = on_hand.get(&key).copied().unwrap_or(0);
    let inbound = pending.get(&key).copied().unwrap_or(0);
    let held = stock
        .checked_add(inbound)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let desired = policy
        .target_stock
        .saturating_sub(held)
        .min(policy.maximum_purchase);
    Ok(Position {
        stock,
        inbound,
        desired,
    })
}

fn economy_of(
    state: &MaterialCircuitState,
) -> Result<(&MonetaryCircuit, &RecurringEconomy), MaterialCircuitError> {
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        return Err(MaterialCircuitError::MonetaryInvariant);
    };
    let recurring = economy
        .recurring
        .as_deref()
        .ok_or(MaterialCircuitError::MonetaryInvariant)?;
    Ok((economy, recurring))
}

fn posted_price(
    state: &MaterialCircuitState,
    policy: &ReplenishmentPolicy,
) -> Result<Currency, MaterialCircuitError> {
    let (_, recurring) = economy_of(state)?;
    let offer_key = (policy.supplier_site_id, policy.good_id, policy.unit_id);
    let index = recurring
        .offers
        .binary_search_by_key(&offer_key, |row| (row.site_id, row.good_id, row.unit_id))
        .map_err(|_| MaterialCircuitError::PurchaseInvariant)?;
    Ok(recurring.offers[index].unit_price)
}

/// The buyer's cash above the policy's floor.
fn spendable(
    state: &MaterialCircuitState,
    policy: &ReplenishmentPolicy,
) -> Result<i128, MaterialCircuitError> {
    let (economy, _) = economy_of(state)?;
    let cash = economy
        .book
        .cash(AccountId::Site(policy.buyer_site_id))?
        .micro_units();
    Ok(cash.saturating_sub(policy.cash_floor.micro_units()).max(0))
}

/// What one restocking pass has accepted so far.
struct Accepted<'a> {
    ids: BTreeSet<OrderId>,
    receipts: Vec<(usize, ProcurementReceipt)>,
    pending: StockLedger,
    transfers: &'a mut Vec<MoneyTransferReceipt>,
}

/// Fund and record one accepted order of a policy.
fn accept(
    state: &mut MaterialCircuitState,
    accepted: &mut Accepted<'_>,
    policy: &ReplenishmentPolicy,
    id: OrderId,
    sale: (u64, Currency),
) -> Result<(), MaterialCircuitError> {
    let (quantity, price) = sale;
    crate::transition::check_order_principal_limits(
        state
            .orders
            .len()
            .checked_add(1)
            .ok_or(MaterialCircuitError::Arithmetic)?,
        state.final_demand_orders.len(),
        state.service_orders.len(),
    )?;
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Err(MaterialCircuitError::MonetaryInvariant);
    };
    accepted
        .transfers
        .push(economy.book.reserve_purchase(PurchaseEscrow::new(
            OutboundOrderId::Delivery(id),
            AccountId::Site(policy.buyer_site_id),
            AccountId::Site(policy.supplier_site_id),
            quantity,
            price,
        )?)?);
    state.orders.push(OrderRow {
        order_id: id,
        access_mode: OrderAccessMode::CommoditySale,
        buyer_site_id: policy.buyer_site_id,
        supplier_site_id: policy.supplier_site_id,
        good_id: policy.good_id,
        unit_id: policy.unit_id,
        ordered: quantity,
        shipped: 0,
        lost: 0,
        delivered: 0,
        realized: 0,
    });
    accepted.ids.insert(id);
    add(
        &mut accepted.pending,
        (policy.buyer_site_id, policy.good_id, policy.unit_id),
        quantity,
    )
}

fn procurement_receipt(
    period: u64,
    policy: &ReplenishmentPolicy,
    held: &Position,
    sale: (u64, Currency),
) -> ProcurementReceipt {
    ProcurementReceipt {
        period,
        order_id: recurring_procurement_order_id(
            period,
            policy.buyer_site_id,
            policy.supplier_site_id,
            policy.good_id,
            policy.unit_id,
        ),
        buyer_site_id: policy.buyer_site_id,
        supplier_site_id: policy.supplier_site_id,
        good_id: policy.good_id,
        unit_id: policy.unit_id,
        on_hand: held.stock,
        outstanding_inbound: held.inbound,
        target_stock: policy.target_stock,
        desired_quantity: held.desired,
        admitted_quantity: sale.0,
        unit_price: sale.1,
    }
}

/// Order one policy by today's rule: what its cash affords at the posted price.
fn restock_at_posted_price(
    state: &mut MaterialCircuitState,
    on_hand: &StockLedger,
    accepted: &mut Accepted<'_>,
    index: usize,
    policy: &ReplenishmentPolicy,
) -> Result<(), MaterialCircuitError> {
    let held = position(policy, on_hand, &accepted.pending)?;
    let price = posted_price(state, policy)?;
    let affordable = spendable(state, policy)? / price.micro_units();
    let quantity = u64::try_from(affordable.min(i128::from(held.desired)))
        .map_err(|_| MaterialCircuitError::Arithmetic)?;
    let receipt = procurement_receipt(state.period, policy, &held, (quantity, price));
    let id = receipt.order_id;
    accepted.receipts.push((index, receipt));
    if quantity == 0 {
        return Ok(());
    }
    accept(state, accepted, policy, id, (quantity, price))
}

/// What a restocking pass reads besides the state it changes.
struct Market<'a> {
    catalog: &'a MaterialCatalog,
    costs: &'a CostClose,
    offer: Offer<'a>,
    table: &'a mut MarketTable,
}

/// Clear one market of restocking: every business that buys this seller's product bids for it, the
/// price rises while the seller is short, and each buyer's order is made at that price.
fn restock_at_market_price(
    state: &mut MaterialCircuitState,
    on_hand: &StockLedger,
    accepted: &mut Accepted<'_>,
    market: &mut Market<'_>,
    members: &[(usize, &ReplenishmentPolicy)],
) -> Result<(), MaterialCircuitError> {
    let first = members
        .first()
        .ok_or(MaterialCircuitError::MarketClearingInvariant)?
        .1;
    let seller = (first.supplier_site_id, first.good_id, first.unit_id);
    let quote = posted_price(state, first)?;
    let supply = market.offer.supply(seller.0, seller.1, seller.2)?;
    let mut bids = vec![];
    let mut bidders = vec![];
    let mut held = vec![];
    for (slot, &(_, policy)) in members.iter().enumerate() {
        let position = position(policy, on_hand, &accepted.pending)?;
        let purse = spendable(state, policy)?;
        if position.desired > 0 && purse > 0 {
            bids.push(MarketBid {
                wanted: position.desired,
                purse: Currency::from_micro_units(purse),
                limit: Some(crate::clearing::limit_price(
                    market.catalog,
                    state,
                    market.costs,
                    policy.buyer_site_id,
                    policy.good_id,
                    policy.unit_id,
                    quote,
                )?),
            });
            bidders.push(slot);
        }
        held.push(position);
    }
    let outcome = crate::clearing::clear_market(supply, quote, &bids)?;
    market.table.record(
        state.period,
        MarketMoment::Restocking,
        seller,
        quote,
        supply,
        bids.len(),
        &outcome,
        crate::clearing::one_rung(&bids),
    )?;
    let mut sold = vec![0_u64; members.len()];
    for (&slot, &quantity) in bidders.iter().zip(&outcome.quantities) {
        sold[slot] = quantity;
    }
    let total = sold
        .iter()
        .try_fold(0_u64, |sum, &quantity| sum.checked_add(quantity))
        .ok_or(MaterialCircuitError::Arithmetic)?;
    market.offer.take(seller.0, seller.1, seller.2, total)?;
    for (slot, &(index, policy)) in members.iter().enumerate() {
        let price = if sold[slot] > 0 { outcome.price } else { quote };
        let receipt = procurement_receipt(state.period, policy, &held[slot], (sold[slot], price));
        let id = receipt.order_id;
        accepted.receipts.push((index, receipt));
        if sold[slot] > 0 {
            accept(state, accepted, policy, id, (sold[slot], price))?;
        }
    }
    Ok(())
}

/// Restock every business from its policies.
///
/// Without a market policy each policy orders what its cash affords at the posted price. With one,
/// the products in the order of paying clear market by market, sorted by place and seller, and
/// the others are ordered as before.
pub(crate) fn replenish(
    catalog: &MaterialCatalog,
    state: &mut MaterialCircuitState,
    deferred_local: &[LocalTransferReceipt],
    transfers: &mut Vec<MoneyTransferReceipt>,
    costs: &CostClose,
    markets: &mut MarketTable,
) -> Result<(BTreeSet<OrderId>, Vec<ProcurementReceipt>), MaterialCircuitError> {
    if !active(state) {
        return Ok((BTreeSet::new(), Vec::new()));
    }
    let (on_hand, pending) = stock_position(state, deferred_local)?;
    let policies: Vec<ReplenishmentPolicy> = economy_of(state)?.1.replenishment.clone();
    let mut accepted = Accepted {
        ids: BTreeSet::new(),
        receipts: Vec::new(),
        pending,
        transfers,
    };
    let mut at_posted_price = vec![];
    let mut by_market: BTreeMap<_, Vec<usize>> = BTreeMap::new();
    for (index, policy) in policies.iter().enumerate() {
        let place = catalog
            .market_clearing
            .as_ref()
            .and_then(|rule| rule.place(policy.good_id, policy.unit_id));
        match place {
            Some(place) => by_market
                .entry((
                    place,
                    policy.supplier_site_id,
                    policy.good_id,
                    policy.unit_id,
                ))
                .or_default()
                .push(index),
            None => at_posted_price.push(index),
        }
    }
    if !by_market.is_empty() {
        let mut market = Market {
            catalog,
            costs,
            offer: Offer::new(catalog, state)?,
            table: markets,
        };
        for indices in by_market.into_values() {
            let mut members: Vec<_> = indices.iter().map(|&i| (i, &policies[i])).collect();
            members.sort_by_key(|&(_, p)| {
                recurring_procurement_order_id(
                    state.period,
                    p.buyer_site_id,
                    p.supplier_site_id,
                    p.good_id,
                    p.unit_id,
                )
            });
            restock_at_market_price(state, &on_hand, &mut accepted, &mut market, &members)?;
        }
    }
    for index in at_posted_price {
        restock_at_posted_price(state, &on_hand, &mut accepted, index, &policies[index])?;
    }
    state.orders.sort_by_key(|row| row.order_id);
    let mut receipts = accepted.receipts;
    receipts.sort_by_key(|&(index, _)| index);
    Ok((
        accepted.ids,
        receipts.into_iter().map(|(_, receipt)| receipt).collect(),
    ))
}

/// What the pass after a sale did not send is cancelled: its money returns to the buyer and the
/// order shrinks to what moved, so that a buyer counts only goods in transit as arriving. An order
/// of which nothing moved leaves no row.
pub(crate) fn cancel_unsent(
    state: &mut MaterialCircuitState,
    accepted: &BTreeSet<OrderId>,
    transfers: &mut Vec<MoneyTransferReceipt>,
) -> Result<(), MaterialCircuitError> {
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Ok(());
    };
    for order in &mut state.orders {
        if !accepted.contains(&order.order_id) {
            continue;
        }
        let unsent = order
            .ordered
            .checked_sub(order.shipped)
            .ok_or(MaterialCircuitError::OrderInvariant)?;
        if unsent == 0 {
            continue;
        }
        let movement = economy
            .book
            .cancel_purchase_units(OutboundOrderId::Delivery(order.order_id), unsent)?;
        transfers.push(movement.transfer);
        order.ordered = order.shipped;
    }
    state.orders.retain(|order| order.ordered > 0);
    Ok(())
}

/// What a period's close tells the seller about what was wanted: what households asked for, and
/// what buyers could pay for at the posted price and did not get at the market's.
#[derive(Clone, Copy)]
pub(crate) struct Wanted<'a> {
    pub(crate) demand: &'a [HouseholdDemandReceipt],
    pub(crate) markets: &'a MarketTable,
    /// The period's service markets: what each provider was asked and planned (rule A6).
    pub(crate) services: &'a [ServiceMarketReceipt],
    /// The period's restocking decisions (rule A6).
    pub(crate) procurement: &'a [ProcurementReceipt],
}

/// What each seller was asked for and has not sent: orders still open, households' expired demand,
/// and what buyers were priced out of.
fn unshipped_quantities(
    state: &MaterialCircuitState,
    wanted: Wanted<'_>,
    gains: &StockLedger,
) -> Result<StockLedger, MaterialCircuitError> {
    let Wanted {
        demand, markets, ..
    } = wanted;
    let mut unshipped = BTreeMap::new();
    for order in &state.orders {
        add(
            &mut unshipped,
            (order.supplier_site_id, order.good_id, order.unit_id),
            order.ordered - order.shipped,
        )?;
    }
    for row in demand {
        add(
            &mut unshipped,
            (row.retailer_site_id, row.good_id, row.unit_id),
            row.expired_quantity,
        )?;
    }
    for row in &state.final_demand_orders {
        add(
            &mut unshipped,
            (row.retailer_site_id, row.good_id, row.unit_id),
            row.ordered - row.fulfilled,
        )?;
    }
    // Under a market policy a buyer that could pay at the posted price and was priced out wanted
    // the goods as much as one that held an order, and the seller plans from it.
    for (key, quantity) in markets.priced_out_goods() {
        add(&mut unshipped, key, quantity)?;
    }
    // A seller whose price stepped down plans for what its buyers could pay for at the new price (A1).
    for (&key, &quantity) in gains {
        add(&mut unshipped, key, quantity)?;
    }
    Ok(unshipped)
}

pub(crate) fn plan_production(
    catalog: &MaterialCatalog,
    state: &mut MaterialCircuitState,
    dispatches: &[RoutedDispatchReceipt],
    sold: (&[LocalTransferReceipt], &[LocalRetailFulfillmentReceipt]),
    wanted: Wanted<'_>,
    gains: &StockLedger,
    next_period: u64,
) -> Result<Vec<ProductionPlanReceipt>, MaterialCircuitError> {
    if !active(state) {
        return Ok(Vec::new());
    }
    let (local, retail) = sold;
    let mut outbound = BTreeMap::new();
    let order_index: BTreeMap<_, _> = state.orders.iter().map(|row| (row.order_id, row)).collect();
    for row in dispatches {
        let order = order_index
            .get(&row.order_id)
            .ok_or(MaterialCircuitError::OrderInvariant)?;
        add(
            &mut outbound,
            (order.supplier_site_id, order.good_id, order.unit_id),
            row.quantity,
        )?;
    }
    for row in local {
        add(
            &mut outbound,
            (row.supplier_site_id, row.good_id, row.unit_id),
            row.quantity,
        )?;
    }
    for row in retail {
        add(
            &mut outbound,
            (row.retailer_site_id, row.good_id, row.unit_id),
            row.quantity,
        )?;
    }
    let unshipped = unshipped_quantities(state, wanted, gains)?;
    let inventory: BTreeMap<_, _> = state
        .inventory
        .iter()
        .map(|row| ((row.site_id, row.good_id, row.unit_id), row.quantity))
        .collect();
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Ok(Vec::new());
    };
    let Some(recurring) = &mut economy.recurring else {
        return Ok(Vec::new());
    };
    let mut receipts = Vec::new();
    for policy in &mut recurring.production {
        let output = catalog
            .process_outputs
            .binary_search_by_key(&policy.process_id, |row| row.process_id)
            .ok()
            .map(|index| &catalog.process_outputs[index])
            .ok_or(MaterialCircuitError::ProcessInvariant)?;
        let key = (policy.site_id, output.good_id, output.unit_id);
        if catalog.commodities.iter().any(|r| {
            (r.good_id, r.unit_id) == (output.good_id, output.unit_id)
                && matches!(r.kind, crate::CommodityKind::PeriodService { .. })
        }) {
            continue;
        }
        let sent = outbound.get(&key).copied().unwrap_or(0);
        let waiting = unshipped.get(&key).copied().unwrap_or(0);
        let stock = inventory.get(&key).copied().unwrap_or(0);
        let target = sent
            .checked_add(waiting)
            .and_then(|value| value.checked_add(policy.output_buffer))
            .ok_or(MaterialCircuitError::Arithmetic)?;
        let wanted = target.saturating_sub(stock);
        // Checked ceil division: a partial batch is not a production operation.
        policy.planned_batches =
            wanted / output.quantity_per_batch + u64::from(wanted % output.quantity_per_batch != 0);
        receipts.push(ProductionPlanReceipt {
            period: state.period,
            next_period,
            process_id: policy.process_id,
            site_id: policy.site_id,
            dispatched_quantity: sent,
            unshipped_quantity: waiting,
            closing_output_stock: stock,
            output_buffer: policy.output_buffer,
            planned_batches: policy.planned_batches,
        });
    }
    Ok(receipts)
}

fn handling_quantities(
    state: &MaterialCircuitState,
    wanted: Wanted<'_>,
    dispatches: &[RoutedDispatchReceipt],
    sold: (&[LocalTransferReceipt], &[LocalRetailFulfillmentReceipt]),
    gains: &StockLedger,
) -> Result<StockLedger, MaterialCircuitError> {
    let (local, retail) = sold;
    let Wanted {
        demand, markets, ..
    } = wanted;
    let mut merchandise = BTreeMap::new();
    for row in demand {
        add(
            &mut merchandise,
            (row.retailer_site_id, row.good_id, row.unit_id),
            row.admitted_quantity,
        )?;
    }
    let orders: BTreeMap<_, _> = state.orders.iter().map(|row| (row.order_id, row)).collect();
    for row in dispatches {
        let order = orders
            .get(&row.order_id)
            .ok_or(MaterialCircuitError::OrderInvariant)?;
        add(
            &mut merchandise,
            (order.supplier_site_id, order.good_id, order.unit_id),
            row.quantity,
        )?;
    }
    for row in local {
        add(
            &mut merchandise,
            (row.supplier_site_id, row.good_id, row.unit_id),
            row.quantity,
        )?;
    }
    for order in &state.orders {
        add(
            &mut merchandise,
            (order.supplier_site_id, order.good_id, order.unit_id),
            order.ordered - order.shipped,
        )?;
    }
    let generated: BTreeSet<_> = demand.iter().map(|row| row.order_id).collect();
    for row in retail
        .iter()
        .filter(|row| !generated.contains(&row.order_id))
    {
        add(
            &mut merchandise,
            (row.retailer_site_id, row.good_id, row.unit_id),
            row.quantity,
        )?;
    }
    for order in &state.final_demand_orders {
        add(
            &mut merchandise,
            (order.retailer_site_id, order.good_id, order.unit_id),
            order.ordered - order.fulfilled,
        )?;
    }
    for (key, quantity) in markets.priced_out_goods() {
        add(&mut merchandise, key, quantity)?;
    }
    for (&key, &quantity) in gains {
        add(&mut merchandise, key, quantity)?;
    }
    Ok(merchandise)
}

pub(crate) fn plan_attendance(
    context: MaterialContext<'_>,
    wanted: Wanted<'_>,
    dispatches: &[RoutedDispatchReceipt],
    sold: (&[LocalTransferReceipt], &[LocalRetailFulfillmentReceipt]),
    maintenance: Option<&MaintenanceReceipt>,
    gains: &StockLedger,
    next_period: u64,
) -> Result<(), MaterialCircuitError> {
    let MaterialContext { catalog, state } = context;
    if !active(state) {
        return Ok(());
    }
    let mut hours = planned_hours(
        catalog,
        state,
        wanted,
        dispatches,
        sold,
        maintenance,
        gains,
        next_period,
    )?;
    if catalog
        .market_clearing
        .as_ref()
        .is_some_and(|policy| policy.plans_from_spare_money)
    {
        let extension = super::spare_money::extend(catalog, state, &hours, wanted, next_period)?;
        if extension.raised_batches {
            hours = planned_hours(
                catalog,
                state,
                wanted,
                dispatches,
                sold,
                maintenance,
                gains,
                next_period,
            )?;
        }
        for ((site, unit), extra) in extension.handling {
            add_hours(&mut hours, site, unit, extra)?;
        }
    }
    install_attendance_plans(state, &hours, next_period)
}

/// Today's hours: production through `derive_shared_labor_requests`, equipment work, merchant
/// handling and maintenance.
#[allow(
    clippy::too_many_arguments,
    reason = "the closed period's moves and the step down's gains are read beside the plans"
)]
fn planned_hours(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    wanted: Wanted<'_>,
    dispatches: &[RoutedDispatchReceipt],
    sold: (&[LocalTransferReceipt], &[LocalRetailFulfillmentReceipt]),
    maintenance: Option<&MaintenanceReceipt>,
    gains: &StockLedger,
    next_period: u64,
) -> Result<BTreeMap<(SiteId, UnitId), u64>, MaterialCircuitError> {
    let production = crate::production::derive_shared_labor_requests(catalog, state, next_period)?;
    let mut hours = BTreeMap::<(SiteId, UnitId), u64>::new();
    for request in production {
        add_hours(&mut hours, request.site_id, request.unit_id, request.hours)?;
    }
    for (_, site, unit, requested) in crate::equipment::work_requests(catalog, state)? {
        add_hours(&mut hours, site, unit, requested)?;
    }
    let merchants: BTreeMap<_, _> = catalog
        .merchants
        .iter()
        .map(|row| (row.site_id, row))
        .collect();
    let coefficients: BTreeMap<_, _> = catalog
        .handling_coefficients
        .iter()
        .map(|row| {
            (
                (row.site_id, row.good_id, row.unit_id),
                (row.hours_per_unit, row.units),
            )
        })
        .collect();
    let merchandise = handling_quantities(state, wanted, dispatches, sold, gains)?;
    for (key, quantity) in merchandise {
        let Some(merchant) = merchants.get(&key.0) else {
            continue;
        };
        let coefficient = coefficients
            .get(&key)
            .ok_or(MaterialCircuitError::MerchantInvariant)?;
        let requested = crate::transition::merchant_admission::block_hours(
            coefficient.0,
            coefficient.1,
            quantity,
        )?;
        add_hours(
            &mut hours,
            merchant.site_id,
            merchant.labor_unit_id,
            requested,
        )?;
    }
    if let Some(receipt) = maintenance {
        let requested = receipt
            .requested_jobs
            .checked_mul(receipt.binding.labor_units_per_job)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        add_hours(
            &mut hours,
            receipt.binding.provider_site_id,
            receipt.binding.labor_unit_id,
            requested,
        )?;
    }
    Ok(hours)
}

fn install_attendance_plans(
    state: &mut MaterialCircuitState,
    hours: &BTreeMap<(SiteId, UnitId), u64>,
    next_period: u64,
) -> Result<(), MaterialCircuitError> {
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Err(MaterialCircuitError::MonetaryInvariant);
    };
    let recurring = economy
        .recurring
        .as_mut()
        .ok_or(MaterialCircuitError::MonetaryInvariant)?;
    let employment: BTreeSet<_> = economy
        .employment
        .iter()
        .map(|terms| (terms.site_id, terms.unit_id))
        .collect();
    let principals: BTreeSet<_> = employment
        .iter()
        .copied()
        .chain(
            state
                .labor
                .iter()
                .filter(|row| row.period == state.period)
                .map(|row| (row.site_id, row.unit_id)),
        )
        .collect();
    recurring.attendance = principals
        .into_iter()
        .map(|(site_id, unit_id)| AttendancePlan {
            site_id,
            unit_id,
            period: next_period,
            planned_hours: if employment.contains(&(site_id, unit_id)) {
                hours.get(&(site_id, unit_id)).copied().unwrap_or(0)
            } else {
                0
            },
        })
        .collect();
    Ok(())
}

fn add_hours(
    hours: &mut BTreeMap<(SiteId, UnitId), u64>,
    site: SiteId,
    unit: UnitId,
    quantity: u64,
) -> Result<(), MaterialCircuitError> {
    let current = hours.entry((site, unit)).or_default();
    *current = current
        .checked_add(quantity)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    Ok(())
}

pub(crate) fn retire_resolved_purchases(
    state: &mut MaterialCircuitState,
) -> Result<(), MaterialCircuitError> {
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Ok(());
    };
    if economy.recurring.is_none() {
        return Ok(());
    }
    let in_transit: BTreeSet<_> = state.freight.iter().map(|row| row.order_id).collect();
    let mut retained = Vec::new();
    for order in std::mem::take(&mut state.orders) {
        if order.delivered.checked_add(order.lost) == Some(order.ordered)
            && !in_transit.contains(&order.order_id)
        {
            economy
                .book
                .retire_purchase(OutboundOrderId::Delivery(order.order_id))?;
        } else {
            retained.push(order);
        }
    }
    state.orders = retained;
    let mut retained = Vec::new();
    for order in std::mem::take(&mut state.final_demand_orders) {
        if order.fulfilled == order.ordered {
            economy
                .book
                .retire_purchase(OutboundOrderId::LocalFinalDemand(order.order_id))?;
        } else {
            retained.push(order);
        }
    }
    state.final_demand_orders = retained;
    Ok(())
}
