//! Authenticate transient service principals against captured reach and policies.
use super::{monetary, offer_index, recurring, PeriodOrders, ProductionProjectionError, Result};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    recurring_service_order_id, recurring_service_topup_order_id, AccountId, CommodityKind, GoodId,
    MaterialCircuitState, OrderId, OutboundOrderId, PurchaseEscrow, ServiceOrder,
    ServicePerformanceReceipt, SiteId, UnitId,
};
use babylon_tick::material_world::MaterialTickReceipts;
use std::collections::{BTreeMap, BTreeSet};
type Key = (AccountId, SiteId, GoodId, UnitId);

pub(super) struct ServiceWitness {
    pub order: ServiceOrder,
    pub performed: u64,
    pub expired: u64,
}
struct Request {
    key: Key,
    maximum: u64,
    price: Currency,
}

pub(super) fn admit(
    prior: &MaterialCircuitState,
    current: &MaterialCircuitState,
    receipts: &MaterialTickReceipts,
    orders: &mut PeriodOrders,
    admissions: &mut BTreeMap<OutboundOrderId, PurchaseEscrow>,
) -> Result<()> {
    let purchases: BTreeMap<_, _> = monetary(prior)
        .map(|m| m.book.snapshot().purchases)
        .unwrap_or_default()
        .into_iter()
        .map(|p| (p.order, p))
        .collect();
    let mut due = BTreeMap::new();
    let mut future = BTreeMap::new();
    for order in &prior.service_orders {
        if order.performance_period < prior.period
            || orders
                .services
                .insert(
                    order.order_id,
                    ServiceWitness {
                        order: order.clone(),
                        performed: 0,
                        expired: 0,
                    },
                )
                .is_some()
        {
            return Err(ProductionProjectionError::State);
        }
        if order.performance_period == prior.period {
            due.insert(order.order_id, order);
        } else {
            future.insert(order.order_id, order);
        }
    }
    let actual: BTreeMap<_, _> = current
        .service_orders
        .iter()
        .map(|r| (r.order_id, r))
        .collect();
    if actual.len() != current.service_orders.len() || actual != future {
        return Err(ProductionProjectionError::State);
    }
    let mut expected = requests(prior, &purchases)?;
    let connections: BTreeSet<_> = prior
        .service_connections
        .iter()
        .map(|r| (r.buyer, r.provider_site_id, r.good_id, r.unit_id))
        .collect();
    let mut seen = BTreeSet::new();
    for row in &receipts.service_performance {
        row.validate()
            .map_err(|_| ProductionProjectionError::State)?;
        let key = (row.buyer, row.provider_site_id, row.good_id, row.unit_id);
        if row.period != prior.period || !seen.insert(row.order_id) || !connections.contains(&key) {
            return Err(ProductionProjectionError::State);
        }
        if let Some(order) = due.remove(&row.order_id) {
            let purchase = purchases
                .get(&OutboundOrderId::Service(row.order_id))
                .ok_or(ProductionProjectionError::State)?;
            if key
                != (
                    order.buyer,
                    order.provider_site_id,
                    order.good_id,
                    order.unit_id,
                )
                || row.admitted_quantity != order.quantity
                || row.requested_quantity != order.quantity
                || row.unit_price != purchase.unit_price
            {
                return Err(ProductionProjectionError::State);
            }
        } else {
            let request = expected
                .remove(&row.order_id)
                .ok_or(ProductionProjectionError::State)?;
            if request.key != key
                || row.unit_price != request.price
                || row.requested_quantity > request.maximum
                || orders.services.contains_key(&row.order_id)
            {
                return Err(ProductionProjectionError::State);
            }
            if row.admitted_quantity == 0 {
                continue;
            }
            admit_generated(row, orders, admissions)?;
        }
        let witness = orders
            .services
            .get_mut(&row.order_id)
            .ok_or(ProductionProjectionError::State)?;
        witness.performed = row.performed_quantity;
        witness.expired = row.expired_quantity;
    }
    if !due.is_empty() || !expected.is_empty() {
        return Err(ProductionProjectionError::State);
    }
    Ok(())
}
fn admit_generated(
    row: &ServicePerformanceReceipt,
    orders: &mut PeriodOrders,
    admissions: &mut BTreeMap<OutboundOrderId, PurchaseEscrow>,
) -> Result<()> {
    let order = ServiceOrder {
        order_id: row.order_id,
        performance_period: row.period,
        provider_site_id: row.provider_site_id,
        buyer: row.buyer,
        good_id: row.good_id,
        unit_id: row.unit_id,
        quantity: row.admitted_quantity,
    };
    let id = OutboundOrderId::Service(row.order_id);
    let principal = PurchaseEscrow::new(
        id,
        row.buyer,
        AccountId::Site(row.provider_site_id),
        row.admitted_quantity,
        row.unit_price,
    )
    .map_err(|_| ProductionProjectionError::State)?;
    if admissions.insert(id, principal).is_some()
        || orders
            .services
            .insert(
                row.order_id,
                ServiceWitness {
                    order,
                    performed: 0,
                    expired: 0,
                },
            )
            .is_some()
    {
        return Err(ProductionProjectionError::State);
    }
    Ok(())
}
fn requests(
    prior: &MaterialCircuitState,
    purchases: &BTreeMap<OutboundOrderId, PurchaseEscrow>,
) -> Result<BTreeMap<OrderId, Request>> {
    let Some(recurring) = recurring(prior) else {
        return Ok(BTreeMap::new());
    };
    let offers = offer_index(prior)?;
    let services: BTreeSet<_> = prior
        .commodities
        .iter()
        .filter(|r| matches!(r.kind, CommodityKind::PeriodService { .. }))
        .map(|r| (r.good_id, r.unit_id))
        .collect();
    let mut limits = BTreeMap::<Key, u64>::new();
    for p in &recurring.service_inputs {
        if limits
            .insert(
                (
                    AccountId::Site(p.buyer_site_id),
                    p.provider_site_id,
                    p.good_id,
                    p.unit_id,
                ),
                p.quantity_per_period.min(p.maximum_purchase),
            )
            .is_some()
        {
            return Err(ProductionProjectionError::State);
        }
    }
    for p in &recurring.household_purchases {
        if services.contains(&(p.good_id, p.unit_id))
            && limits
                .insert(
                    (
                        AccountId::Household(p.principal_id),
                        p.retailer_site_id,
                        p.good_id,
                        p.unit_id,
                    ),
                    if p.enabled { p.maximum_purchase } else { 0 },
                )
                .is_some()
        {
            return Err(ProductionProjectionError::State);
        }
    }
    let mut due = BTreeMap::<Key, Vec<(OrderId, u64, Currency)>>::new();
    for o in prior
        .service_orders
        .iter()
        .filter(|o| o.performance_period == prior.period)
    {
        let quote = purchases
            .get(&OutboundOrderId::Service(o.order_id))
            .ok_or(ProductionProjectionError::State)?
            .unit_price;
        due.entry((o.buyer, o.provider_site_id, o.good_id, o.unit_id))
            .or_default()
            .push((o.order_id, o.quantity, quote));
    }
    let mut result = BTreeMap::new();
    for (key, maximum) in limits {
        let mut id = recurring_service_order_id(prior.period, key.0, key.1, key.2, key.3);
        if let Some(rows) = due.get_mut(&key) {
            rows.sort_unstable_by_key(|r| r.0);
            id = recurring_service_topup_order_id(id, rows);
        }
        let price = *offers
            .get(&(key.1, key.2, key.3))
            .ok_or(ProductionProjectionError::State)?;
        if result
            .insert(
                id,
                Request {
                    key,
                    maximum,
                    price,
                },
            )
            .is_some()
        {
            return Err(ProductionProjectionError::State);
        }
    }
    Ok(result)
}
