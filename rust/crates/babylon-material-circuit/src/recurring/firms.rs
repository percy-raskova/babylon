//! Finite procurement and subsequent plans derived from the same market close.

use std::collections::{BTreeMap, BTreeSet};

use babylon_kernel::{content_digest::sha256_of, currency::Currency};

use super::{AttendancePlan, PricePolicy};
use crate::{
    AccountId, CircuitAccounting, GoodId, HouseholdDemandReceipt, LocalTransferReceipt,
    MaterialCircuitError, MaterialCircuitState, MoneyTransferReceipt, OrderAccessMode, OrderId,
    OrderRow, OutboundOrderId, ProcessId, PurchaseEscrow, RoutedDispatchReceipt, SiteId, UnitId,
    MAX_MATERIAL_CIRCUIT_ROWS,
};

type StockKey = (SiteId, GoodId, UnitId);
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

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PriceDecision {
    Fixed,
    Hold,
    UnservedDemand,
    ExcessStock,
}

/// Offers for the next period; existing purchase reserves keep their own prices.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PriceReceipt {
    pub period: u64,
    pub site_id: SiteId,
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub old_price: Currency,
    pub next_price: Currency,
    pub unserved_quantity: u64,
    pub closing_stock: u64,
    pub reason: PriceDecision,
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
    OrderId::from_bytes(sha256_of(&bytes))
}

pub(crate) fn replenish(
    state: &mut MaterialCircuitState,
    deferred_local: &[LocalTransferReceipt],
    transfers: &mut Vec<MoneyTransferReceipt>,
) -> Result<(BTreeSet<OrderId>, Vec<ProcurementReceipt>), MaterialCircuitError> {
    if !active(state) {
        return Ok((BTreeSet::new(), Vec::new()));
    }
    let (on_hand, mut pending) = stock_position(state, deferred_local)?;
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Ok((BTreeSet::new(), Vec::new()));
    };
    let Some(recurring) = &economy.recurring else {
        return Ok((BTreeSet::new(), Vec::new()));
    };
    let mut ids = BTreeSet::new();
    let mut receipts = Vec::new();
    for policy in &recurring.replenishment {
        let key = (policy.buyer_site_id, policy.good_id, policy.unit_id);
        let stock = on_hand.get(&key).copied().unwrap_or(0);
        let inbound = pending.get(&key).copied().unwrap_or(0);
        let position = stock
            .checked_add(inbound)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        let desired = policy
            .target_stock
            .saturating_sub(position)
            .min(policy.maximum_purchase);
        let offer_key = (policy.supplier_site_id, policy.good_id, policy.unit_id);
        let offer_index = recurring
            .offers
            .binary_search_by_key(&offer_key, |row| (row.site_id, row.good_id, row.unit_id))
            .map_err(|_| MaterialCircuitError::PurchaseInvariant)?;
        let price = recurring.offers[offer_index].unit_price;
        let cash = economy
            .book
            .cash(AccountId::Site(policy.buyer_site_id))?
            .micro_units();
        let spendable = cash.saturating_sub(policy.cash_floor.micro_units()).max(0);
        let affordable = spendable / price.micro_units();
        let quantity = u64::try_from(affordable.min(i128::from(desired)))
            .map_err(|_| MaterialCircuitError::Arithmetic)?;
        let id = recurring_procurement_order_id(
            state.period,
            policy.buyer_site_id,
            policy.supplier_site_id,
            policy.good_id,
            policy.unit_id,
        );
        receipts.push(ProcurementReceipt {
            period: state.period,
            order_id: id,
            buyer_site_id: policy.buyer_site_id,
            supplier_site_id: policy.supplier_site_id,
            good_id: policy.good_id,
            unit_id: policy.unit_id,
            on_hand: stock,
            outstanding_inbound: inbound,
            target_stock: policy.target_stock,
            desired_quantity: desired,
            admitted_quantity: quantity,
            unit_price: price,
        });
        if quantity == 0 {
            continue;
        }
        if state.orders.len() + state.final_demand_orders.len() >= MAX_MATERIAL_CIRCUIT_ROWS {
            return Err(MaterialCircuitError::RowLimit);
        }
        transfers.push(economy.book.reserve_purchase(PurchaseEscrow::new(
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
        ids.insert(id);
        add(&mut pending, key, quantity)?;
    }
    state.orders.sort_by_key(|row| row.order_id);
    Ok((ids, receipts))
}

pub(crate) fn plan_production(
    state: &mut MaterialCircuitState,
    dispatches: &[RoutedDispatchReceipt],
    local: &[LocalTransferReceipt],
    retail: &[crate::LocalRetailFulfillmentReceipt],
    demand: &[HouseholdDemandReceipt],
    next_period: u64,
) -> Result<Vec<ProductionPlanReceipt>, MaterialCircuitError> {
    if !active(state) {
        return Ok(Vec::new());
    }
    let mut outbound = BTreeMap::new();
    let mut unshipped = BTreeMap::new();
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
        let output = state
            .process_outputs
            .binary_search_by_key(&policy.process_id, |row| row.process_id)
            .ok()
            .map(|index| &state.process_outputs[index])
            .ok_or(MaterialCircuitError::ProcessInvariant)?;
        let key = (policy.site_id, output.good_id, output.unit_id);
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
    demand: &[HouseholdDemandReceipt],
    dispatches: &[RoutedDispatchReceipt],
    local: &[LocalTransferReceipt],
    retail: &[crate::LocalRetailFulfillmentReceipt],
) -> Result<StockLedger, MaterialCircuitError> {
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
    Ok(merchandise)
}

pub(crate) fn plan_attendance(
    state: &mut MaterialCircuitState,
    demand: &[HouseholdDemandReceipt],
    dispatches: &[RoutedDispatchReceipt],
    local: &[LocalTransferReceipt],
    retail: &[crate::LocalRetailFulfillmentReceipt],
    maintenance: Option<&crate::MaintenanceReceipt>,
    next_period: u64,
) -> Result<(), MaterialCircuitError> {
    if !matches!(&state.accounting, CircuitAccounting::Monetary(economy) if economy.recurring.is_some())
    {
        return Ok(());
    }
    let production = crate::production::derive_shared_labor_requests(state, next_period)?;
    let mut hours = BTreeMap::<(SiteId, UnitId), u64>::new();
    for request in production {
        add_hours(&mut hours, request.site_id, request.unit_id, request.hours)?;
    }
    let merchants: BTreeMap<_, _> = state
        .merchants
        .iter()
        .map(|row| (row.site_id, row))
        .collect();
    let coefficients: BTreeMap<_, _> = state
        .handling_coefficients
        .iter()
        .map(|row| ((row.site_id, row.good_id, row.unit_id), row.hours_per_unit))
        .collect();
    let merchandise = handling_quantities(state, demand, dispatches, local, retail)?;
    for (key, quantity) in merchandise {
        let Some(merchant) = merchants.get(&key.0) else {
            continue;
        };
        let coefficient = coefficients
            .get(&key)
            .ok_or(MaterialCircuitError::MerchantInvariant)?;
        let requested = quantity
            .checked_mul(*coefficient)
            .ok_or(MaterialCircuitError::Arithmetic)?;
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
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        unreachable!()
    };
    let recurring = economy
        .recurring
        .as_mut()
        .ok_or(MaterialCircuitError::MonetaryInvariant)?;
    recurring.attendance = economy
        .employment
        .iter()
        .map(|terms| AttendancePlan {
            site_id: terms.site_id,
            unit_id: terms.unit_id,
            period: next_period,
            planned_hours: hours
                .get(&(terms.site_id, terms.unit_id))
                .copied()
                .unwrap_or(0),
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

pub(crate) fn update_prices(
    state: &mut MaterialCircuitState,
    demand: &[HouseholdDemandReceipt],
) -> Result<Vec<PriceReceipt>, MaterialCircuitError> {
    if !active(state) {
        return Ok(Vec::new());
    }
    let mut unserved = BTreeMap::new();
    for row in demand {
        add(
            &mut unserved,
            (row.retailer_site_id, row.good_id, row.unit_id),
            row.expired_quantity,
        )?;
    }
    for order in &state.orders {
        add(
            &mut unserved,
            (order.supplier_site_id, order.good_id, order.unit_id),
            order.ordered - order.shipped,
        )?;
    }
    for row in &state.final_demand_orders {
        add(
            &mut unserved,
            (row.retailer_site_id, row.good_id, row.unit_id),
            row.ordered - row.fulfilled,
        )?;
    }
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
    for offer in &mut recurring.offers {
        let key = (offer.site_id, offer.good_id, offer.unit_id);
        let waiting = unserved.get(&key).copied().unwrap_or(0);
        let stock = inventory.get(&key).copied().unwrap_or(0);
        let old = offer.unit_price;
        let reason = match offer.pricing {
            PricePolicy::Fixed => PriceDecision::Fixed,
            PricePolicy::Responsive {
                minimum,
                maximum,
                step,
                target_stock,
            } => {
                if waiting > 0 && stock <= target_stock {
                    // Saturation is explicit at the declared quote ceiling.
                    offer.unit_price = Currency::from_micro_units(
                        old.micro_units()
                            .saturating_add(step.micro_units())
                            .min(maximum.micro_units()),
                    );
                    PriceDecision::UnservedDemand
                } else if waiting == 0 && stock > target_stock {
                    offer.unit_price = Currency::from_micro_units(
                        old.micro_units()
                            .saturating_sub(step.micro_units())
                            .max(minimum.micro_units()),
                    );
                    PriceDecision::ExcessStock
                } else {
                    PriceDecision::Hold
                }
            }
        };
        receipts.push(PriceReceipt {
            period: state.period,
            site_id: offer.site_id,
            good_id: offer.good_id,
            unit_id: offer.unit_id,
            old_price: old,
            next_price: offer.unit_price,
            unserved_quantity: waiting,
            closing_stock: stock,
            reason,
        });
    }
    Ok(receipts)
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
