//! Admission spends existing cash; physical handoff and period consumption differ.

use super::{HouseholdConsumptionReceipt, HouseholdDemandReceipt, RecurringEconomy, Result};
use crate::{
    AccountId, CircuitAccounting, FinalDemandOrder, FinalDemandPrincipalId, GoodId,
    LocalRetailFulfillmentReceipt, MAX_MATERIAL_CIRCUIT_ROWS, MaterialCircuitError,
    MaterialCircuitState, MonetaryBook, MoneyTransferReceipt, OrderId, OutboundOrderId,
    PurchaseEscrow, UnitId,
};
use babylon_kernel::content_digest::sha256_of;
use std::collections::{BTreeMap, BTreeSet};

type HouseholdKey = (FinalDemandPrincipalId, GoodId, UnitId);

fn order_id(period: u64, key: HouseholdKey) -> OrderId {
    let mut bytes = b"babylon.recurring-household-order.v1\0".to_vec();
    bytes.extend_from_slice(&period.to_be_bytes());
    bytes.extend_from_slice(&key.0.as_bytes());
    bytes.extend_from_slice(&key.1.as_bytes());
    bytes.extend_from_slice(&key.2.as_bytes());
    OrderId::from_bytes(sha256_of(&bytes))
}

fn requirements(rows: &RecurringEconomy) -> Result<BTreeMap<HouseholdKey, u64>> {
    let people: BTreeMap<_, _> = rows
        .households
        .iter()
        .map(|r| (r.principal_id, r.persons))
        .collect();
    rows.household_needs
        .iter()
        .map(|need| {
            let persons = people
                .get(&need.principal_id)
                .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
            let quantity = persons
                .checked_mul(need.units_per_person)
                .ok_or(MaterialCircuitError::Arithmetic)?;
            Ok(((need.principal_id, need.good_id, need.unit_id), quantity))
        })
        .collect()
}

fn household_phase(rows: &RecurringEconomy, period: u64) -> Result<()> {
    let previous = period
        .checked_sub(1)
        .ok_or(MaterialCircuitError::PeriodInvariant)?;
    if rows.last_household_admission_period != period
        || rows.last_household_consumption_period != previous
    {
        return Err(MaterialCircuitError::PeriodInvariant);
    }
    Ok(())
}

/// Admit once after payroll, sharing real cash in household/good/unit order.
/// Only completed staging is installed, including its admission cursor.
pub(crate) fn admit_household_orders(
    state: &mut MaterialCircuitState,
    transfers: &mut Vec<MoneyTransferReceipt>,
) -> Result<Vec<HouseholdDemandReceipt>> {
    super::validate(state)?;
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Ok(vec![]);
    };
    let Some(rows) = &mut economy.recurring else {
        return Ok(vec![]);
    };
    let required = requirements(rows)?;
    let stock: BTreeMap<_, _> = rows
        .household_stocks
        .iter()
        .map(|r| ((r.principal_id, r.good_id, r.unit_id), r.quantity))
        .collect();
    let offers: BTreeMap<_, _> = rows
        .offers
        .iter()
        .map(|r| ((r.site_id, r.good_id, r.unit_id), r.unit_price))
        .collect();
    let existing: BTreeSet<_> = state
        .final_demand_orders
        .iter()
        .map(|r| r.order_id)
        .collect();
    let mut policies: Vec<_> = rows.household_purchases.iter().collect();
    policies.sort_by_key(|r| (r.principal_id, r.good_id, r.unit_id));
    let mut book = economy.book.clone();
    let mut orders = vec![];
    let mut movements = vec![];
    let mut receipts = vec![];
    for policy in policies {
        let key = (policy.principal_id, policy.good_id, policy.unit_id);
        let id = order_id(state.period, key);
        if existing.contains(&id) {
            return Err(MaterialCircuitError::DuplicateRow);
        }
        let opening_stock = *stock
            .get(&key)
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        let required_quantity = *required
            .get(&key)
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        let target = required_quantity
            .checked_add(policy.target_closing_stock)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        let desired_quantity = target.saturating_sub(opening_stock);
        let requested_quantity = if policy.enabled {
            desired_quantity.min(policy.maximum_purchase)
        } else {
            0
        };
        let unit_price = *offers
            .get(&(policy.retailer_site_id, policy.good_id, policy.unit_id))
            .ok_or(MaterialCircuitError::PurchaseInvariant)?;
        let buyer = AccountId::Household(policy.principal_id);
        let affordable = book.cash(buyer)?.micro_units() / unit_price.micro_units();
        let admitted_quantity = u64::try_from(affordable.min(i128::from(requested_quantity)))
            .map_err(|_| MaterialCircuitError::Arithmetic)?;
        let demand = HouseholdDemandReceipt {
            period: state.period,
            principal_id: policy.principal_id,
            retailer_site_id: policy.retailer_site_id,
            good_id: policy.good_id,
            unit_id: policy.unit_id,
            order_id: id,
            opening_stock,
            required_quantity,
            desired_quantity,
            requested_quantity,
            admitted_quantity,
            fulfilled_quantity: 0,
            expired_quantity: 0,
            unit_price,
        };
        if admitted_quantity > 0 {
            let count = state
                .orders
                .len()
                .checked_add(state.final_demand_orders.len())
                .and_then(|n| n.checked_add(orders.len()))
                .ok_or(MaterialCircuitError::Arithmetic)?;
            if count >= MAX_MATERIAL_CIRCUIT_ROWS {
                return Err(MaterialCircuitError::RowLimit);
            }
            let (order, movement) = fund_order(&mut book, &demand)?;
            orders.push(order);
            movements.push(movement);
        }
        receipts.push(demand);
    }
    economy.book = book;
    rows.last_household_admission_period = state.period;
    state.final_demand_orders.extend(orders);
    state.final_demand_orders.sort_by_key(|r| r.order_id);
    transfers.extend(movements);
    Ok(receipts)
}

fn fund_order(
    book: &mut MonetaryBook,
    demand: &HouseholdDemandReceipt,
) -> Result<(FinalDemandOrder, MoneyTransferReceipt)> {
    let movement = book.reserve_purchase(PurchaseEscrow::new(
        OutboundOrderId::LocalFinalDemand(demand.order_id),
        AccountId::Household(demand.principal_id),
        AccountId::Site(demand.retailer_site_id),
        demand.admitted_quantity,
        demand.unit_price,
    )?)?;
    Ok((
        FinalDemandOrder {
            order_id: demand.order_id,
            retailer_site_id: demand.retailer_site_id,
            demand_principal_id: demand.principal_id,
            good_id: demand.good_id,
            unit_id: demand.unit_id,
            ordered: demand.admitted_quantity,
            fulfilled: 0,
        },
        movement,
    ))
}

fn validate_demand_receipts(
    rows: &RecurringEconomy,
    period: u64,
    demands: &[HouseholdDemandReceipt],
) -> Result<()> {
    if demands.len() != rows.household_purchases.len() {
        return Err(MaterialCircuitError::FinalDemandInvariant);
    }
    let policies: BTreeMap<_, _> = rows
        .household_purchases
        .iter()
        .map(|r| ((r.principal_id, r.good_id, r.unit_id), r))
        .collect();
    let required = requirements(rows)?;
    let stocks: BTreeMap<_, _> = rows
        .household_stocks
        .iter()
        .map(|r| ((r.principal_id, r.good_id, r.unit_id), r.quantity))
        .collect();
    let offers: BTreeMap<_, _> = rows
        .offers
        .iter()
        .map(|r| ((r.site_id, r.good_id, r.unit_id), r.unit_price))
        .collect();
    let mut seen = BTreeSet::new();
    for demand in demands {
        let key = (demand.principal_id, demand.good_id, demand.unit_id);
        let policy = policies
            .get(&key)
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        let required_quantity = *required
            .get(&key)
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        let opening_stock = *stocks
            .get(&key)
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        let desired_quantity = required_quantity
            .checked_add(policy.target_closing_stock)
            .ok_or(MaterialCircuitError::Arithmetic)?
            .saturating_sub(opening_stock);
        let requested_quantity = if policy.enabled {
            desired_quantity.min(policy.maximum_purchase)
        } else {
            0
        };
        let unit_price = offers
            .get(&(policy.retailer_site_id, policy.good_id, policy.unit_id))
            .ok_or(MaterialCircuitError::PurchaseInvariant)?;
        if (
            demand.required_quantity,
            demand.opening_stock,
            demand.desired_quantity,
            demand.requested_quantity,
            demand.unit_price,
        ) != (
            required_quantity,
            opening_stock,
            desired_quantity,
            requested_quantity,
            *unit_price,
        ) {
            return Err(MaterialCircuitError::FinalDemandInvariant);
        }
        if !seen.insert(key)
            || demand.period != period
            || demand.order_id != order_id(period, key)
            || demand.retailer_site_id != policy.retailer_site_id
            || demand.unit_price.micro_units() <= 0
            || demand.admitted_quantity > demand.requested_quantity
            || demand.requested_quantity > demand.desired_quantity
            || demand.fulfilled_quantity != 0
            || demand.expired_quantity != 0
        {
            return Err(MaterialCircuitError::FinalDemandInvariant);
        }
    }
    Ok(())
}

fn validate_handoff(
    order: &FinalDemandOrder,
    receipt: &LocalRetailFulfillmentReceipt,
) -> Result<()> {
    if receipt.quantity == 0
        || receipt.retailer_site_id != order.retailer_site_id
        || receipt.demand_principal_id != order.demand_principal_id
        || receipt.good_id != order.good_id
        || receipt.unit_id != order.unit_id
        || order.fulfilled > order.ordered
    {
        return Err(MaterialCircuitError::FinalDemandInvariant);
    }
    Ok(())
}

/// Credit and settle new handoffs once, then expire only generated principals.
/// A prior finite household order remains open for its undelivered remainder.
pub(crate) fn complete_household_orders(
    state: &mut MaterialCircuitState,
    demands: &mut [HouseholdDemandReceipt],
    handoffs: &[LocalRetailFulfillmentReceipt],
    transfers: &mut Vec<MoneyTransferReceipt>,
) -> Result<()> {
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Ok(());
    };
    let Some(rows) = &mut economy.recurring else {
        return Ok(());
    };
    household_phase(rows, state.period)?;
    validate_demand_receipts(rows, state.period, demands)?;
    if handoffs.len() > MAX_MATERIAL_CIRCUIT_ROWS {
        return Err(MaterialCircuitError::RowLimit);
    }
    let household_ids: BTreeSet<_> = rows.households.iter().map(|r| r.principal_id).collect();
    let physical: BTreeMap<_, _> = state
        .final_demand_orders
        .iter()
        .map(|r| (r.order_id, r))
        .collect();
    let mut stock: BTreeMap<_, _> = rows
        .household_stocks
        .iter()
        .map(|r| ((r.principal_id, r.good_id, r.unit_id), r.quantity))
        .collect();
    let mut book = economy.book.clone();
    let mut movements = vec![];
    let mut seen = BTreeSet::new();
    let mut ordered: Vec<_> = handoffs.iter().collect();
    ordered.sort_by_key(|receipt| receipt.order_id);
    for receipt in ordered {
        if !seen.insert(receipt.order_id) {
            return Err(MaterialCircuitError::DuplicateRow);
        }
        let order = physical
            .get(&receipt.order_id)
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        validate_handoff(order, receipt)?;
        if !household_ids.contains(&receipt.demand_principal_id) {
            continue;
        }
        let id = OutboundOrderId::LocalFinalDemand(receipt.order_id);
        let purchase = book.purchase(id)?;
        if purchase.buyer != AccountId::Household(receipt.demand_principal_id)
            || purchase.seller != AccountId::Site(receipt.retailer_site_id)
            || purchase.quantity != order.ordered
            || purchase.refunded != 0
            || purchase.delivered.checked_add(receipt.quantity) != Some(order.fulfilled)
        {
            return Err(MaterialCircuitError::PurchaseInvariant);
        }
        let quantity = stock
            .get_mut(&(
                receipt.demand_principal_id,
                receipt.good_id,
                receipt.unit_id,
            ))
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        *quantity = quantity
            .checked_add(receipt.quantity)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        movements.push(book.settle_purchase(id, order.fulfilled)?.transfer);
    }
    let mut resolved = demands.to_vec();
    let mut retired = BTreeSet::new();
    for demand in &mut resolved {
        if let Some(id) =
            resolve_generated_order(&mut book, &physical, demand, &seen, &mut movements)?
        {
            retired.insert(id);
        }
    }
    let mut next_stocks = rows.household_stocks.clone();
    for row in &mut next_stocks {
        row.quantity = *stock
            .get(&(row.principal_id, row.good_id, row.unit_id))
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
    }
    rows.household_stocks = next_stocks;
    economy.book = book;
    state
        .final_demand_orders
        .retain(|row| !retired.contains(&row.order_id));
    demands.clone_from_slice(&resolved);
    transfers.extend(movements);
    Ok(())
}

fn resolve_generated_order(
    book: &mut MonetaryBook,
    physical: &BTreeMap<OrderId, &FinalDemandOrder>,
    demand: &mut HouseholdDemandReceipt,
    seen: &BTreeSet<OrderId>,
    movements: &mut Vec<MoneyTransferReceipt>,
) -> Result<Option<OrderId>> {
    let id = OutboundOrderId::LocalFinalDemand(demand.order_id);
    if demand.admitted_quantity == 0 {
        if physical.contains_key(&demand.order_id) || book.purchase(id).is_ok() {
            return Err(MaterialCircuitError::PurchaseInvariant);
        }
        return Ok(None);
    }
    let order = physical
        .get(&demand.order_id)
        .ok_or(MaterialCircuitError::PurchaseInvariant)?;
    let purchase = book.purchase(id)?;
    if order.ordered != demand.admitted_quantity
        || order.demand_principal_id != demand.principal_id
        || order.retailer_site_id != demand.retailer_site_id
        || order.good_id != demand.good_id
        || order.unit_id != demand.unit_id
        || purchase.quantity != demand.admitted_quantity
        || purchase.unit_price != demand.unit_price
        || purchase.buyer != AccountId::Household(demand.principal_id)
        || purchase.seller != AccountId::Site(demand.retailer_site_id)
        || purchase.delivered != order.fulfilled
        || purchase.refunded != 0
        || (order.fulfilled > 0 && !seen.contains(&demand.order_id))
    {
        return Err(MaterialCircuitError::PurchaseInvariant);
    }
    demand.fulfilled_quantity = order.fulfilled;
    demand.expired_quantity = demand
        .admitted_quantity
        .checked_sub(order.fulfilled)
        .ok_or(MaterialCircuitError::PurchaseInvariant)?;
    if demand.expired_quantity > 0 {
        movements.push(book.refund_purchase(id, demand.expired_quantity)?.transfer);
    }
    book.retire_purchase(id)?;
    Ok(Some(demand.order_id))
}

/// Consume this period's need from actual stock; unmet units are evidence, not debt.
pub(crate) fn consume_household_needs(
    state: &mut MaterialCircuitState,
) -> Result<Vec<HouseholdConsumptionReceipt>> {
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Ok(vec![]);
    };
    let Some(rows) = &mut economy.recurring else {
        return Ok(vec![]);
    };
    household_phase(rows, state.period)?;
    let existing: BTreeSet<_> = state
        .final_demand_orders
        .iter()
        .map(|r| r.order_id)
        .collect();
    for policy in &rows.household_purchases {
        let id = order_id(
            state.period,
            (policy.principal_id, policy.good_id, policy.unit_id),
        );
        if existing.contains(&id)
            || economy
                .book
                .purchase(OutboundOrderId::LocalFinalDemand(id))
                .is_ok()
        {
            return Err(MaterialCircuitError::PurchaseInvariant);
        }
    }
    let needed = requirements(rows)?;
    let stocks: BTreeMap<_, _> = rows
        .household_stocks
        .iter()
        .map(|r| ((r.principal_id, r.good_id, r.unit_id), r.quantity))
        .collect();
    let mut receipts = vec![];
    for (key, required_quantity) in needed {
        let available_quantity = *stocks
            .get(&key)
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        let consumed_quantity = available_quantity.min(required_quantity);
        receipts.push(HouseholdConsumptionReceipt {
            period: state.period,
            principal_id: key.0,
            good_id: key.1,
            unit_id: key.2,
            required_quantity,
            available_quantity,
            consumed_quantity,
            unmet_quantity: required_quantity - consumed_quantity,
            closing_quantity: available_quantity - consumed_quantity,
        });
    }
    let closing: BTreeMap<_, _> = receipts
        .iter()
        .map(|r| ((r.principal_id, r.good_id, r.unit_id), r.closing_quantity))
        .collect();
    let mut next_stocks = rows.household_stocks.clone();
    for row in &mut next_stocks {
        row.quantity = *closing
            .get(&(row.principal_id, row.good_id, row.unit_id))
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
    }
    rows.household_stocks = next_stocks;
    rows.last_household_consumption_period = state.period;
    Ok(receipts)
}
