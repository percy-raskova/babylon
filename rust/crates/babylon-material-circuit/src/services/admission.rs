use super::{
    is_service, GoodId, MaterialCircuitError, MaterialCircuitState, Result, ServiceOrder,
    ServicePerformanceReceipt, UnitId, MAX_SERVICE_RECEIPTS_PER_PERIOD,
};
use crate::{
    AccountId, CircuitAccounting, MoneyTransferReceipt, OutboundOrderId, PurchaseEscrow, SiteId,
    MAX_MATERIAL_CIRCUIT_ROWS,
};
use babylon_kernel::{content_digest::sha256_of, currency::Currency};

/// Exact identity of a generated current-period service request.
#[must_use]
pub fn recurring_service_order_id(
    period: u64,
    buyer: AccountId,
    provider: SiteId,
    good: GoodId,
    unit: UnitId,
) -> crate::OrderId {
    let (tag, id) = match buyer {
        AccountId::Site(id) => (1, id.as_bytes()),
        AccountId::Household(id) => (2, id.as_bytes()),
        AccountId::Organization(id) => (3, id.as_bytes()),
        AccountId::Public(id) => (4, id.as_bytes()),
    };
    let mut bytes = b"babylon.recurring-service-order.v1\0".to_vec();
    bytes.extend_from_slice(&period.to_be_bytes());
    bytes.push(tag);
    bytes.extend_from_slice(&id);
    bytes.extend_from_slice(&provider.as_bytes());
    bytes.extend_from_slice(&good.as_bytes());
    bytes.extend_from_slice(&unit.as_bytes());
    crate::OrderId::from_bytes(sha256_of(&bytes))
}
/// Exact identity of a top-up against captured, accepted service commitments.
/// `due` is the strictly order-ID-sorted `(order, quantity, accepted price)` slice.
#[must_use]
pub fn recurring_service_topup_order_id(
    base: crate::OrderId,
    due: &[(crate::OrderId, u64, Currency)],
) -> crate::OrderId {
    let mut bytes = b"babylon.recurring-service-topup.v1\0".to_vec();
    bytes.extend_from_slice(&base.as_bytes());
    for (order, quantity, price) in due {
        bytes.extend_from_slice(&order.as_bytes());
        bytes.extend_from_slice(&quantity.to_be_bytes());
        bytes.extend_from_slice(&price.micro_units().to_be_bytes());
    }
    crate::OrderId::from_bytes(sha256_of(&bytes))
}
struct Request {
    order_id: crate::OrderId,
    buyer: AccountId,
    provider: SiteId,
    good: GoodId,
    unit: UnitId,
    requested: u64,
    floor: Currency,
}
fn requests(state: &MaterialCircuitState) -> Result<Vec<Request>> {
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        return Ok(vec![]);
    };
    let Some(r) = &e.recurring else {
        return Ok(vec![]);
    };
    let requirements = super::input_requirements(state, false)?;
    let mut result = Vec::new();
    for p in &r.service_inputs {
        result.push(Request {
            order_id: recurring_service_order_id(
                state.period,
                AccountId::Site(p.buyer_site_id),
                p.provider_site_id,
                p.good_id,
                p.unit_id,
            ),
            buyer: AccountId::Site(p.buyer_site_id),
            provider: p.provider_site_id,
            good: p.good_id,
            unit: p.unit_id,
            requested: super::required_input(&requirements, p),
            floor: p.cash_floor,
        });
    }
    for p in &r.household_purchases {
        if !is_service(state, p.good_id, p.unit_id) {
            continue;
        }
        let cohort = r
            .households
            .iter()
            .find(|r| r.principal_id == p.principal_id)
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        let need = r
            .household_needs
            .iter()
            .find(|r| {
                (r.principal_id, r.good_id, r.unit_id) == (p.principal_id, p.good_id, p.unit_id)
            })
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        let required = need.required_quantity(cohort)?;
        result.push(Request {
            order_id: recurring_service_order_id(
                state.period,
                AccountId::Household(p.principal_id),
                p.retailer_site_id,
                p.good_id,
                p.unit_id,
            ),
            buyer: AccountId::Household(p.principal_id),
            provider: p.retailer_site_id,
            good: p.good_id,
            unit: p.unit_id,
            requested: if p.enabled {
                required.min(p.maximum_purchase)
            } else {
                0
            },
            floor: Currency::from_micro_units(0),
        });
    }
    deduct_due_commitments(state, &mut result)?;
    result.sort_by_key(|r| (r.buyer, r.good, r.unit, r.provider));
    Ok(result)
}
type DueKey = (AccountId, SiteId, GoodId, UnitId);
fn deduct_due_commitments(state: &MaterialCircuitState, requests: &mut [Request]) -> Result<()> {
    let mut due = std::collections::BTreeMap::<DueKey, (u64, Vec<&ServiceOrder>)>::new();
    for order in state
        .service_orders
        .iter()
        .filter(|o| o.performance_period == state.period)
    {
        let entry = due
            .entry((
                order.buyer,
                order.provider_site_id,
                order.good_id,
                order.unit_id,
            ))
            .or_default();
        entry.0 = entry
            .0
            .checked_add(order.quantity)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        entry.1.push(order);
    }
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        return Ok(());
    };
    for request in requests {
        if let Some((quantity, orders)) =
            due.get(&(request.buyer, request.provider, request.good, request.unit))
        {
            request.requested = request.requested.saturating_sub(*quantity);
            // Preserve accepted reserves; a remaining requirement is a separate current-price purchase.
            let accepted = orders
                .iter()
                .map(|order| {
                    let reserve = e.book.purchase(OutboundOrderId::Service(order.order_id))?;
                    Ok((order.order_id, order.quantity, reserve.unit_price))
                })
                .collect::<Result<Vec<_>>>()?;
            request.order_id = recurring_service_topup_order_id(request.order_id, &accepted);
        }
    }
    Ok(())
}
pub(super) fn admit(
    state: &mut MaterialCircuitState,
    movements: &mut Vec<MoneyTransferReceipt>,
) -> Result<Vec<ServicePerformanceReceipt>> {
    let requests = requests(state)?;
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        return Ok(vec![]);
    };
    let mut result = Vec::new();
    for order in &state.service_orders {
        if order.performance_period == state.period {
            let price = e
                .book
                .purchase(OutboundOrderId::Service(order.order_id))?
                .unit_price;
            result.push(receipt(order, order.quantity, price));
        }
    }
    for request in requests {
        let recurring = e
            .recurring
            .as_ref()
            .ok_or(MaterialCircuitError::ServiceInvariant)?;
        let price = recurring
            .offers
            .iter()
            .find(|o| {
                (o.site_id, o.good_id, o.unit_id) == (request.provider, request.good, request.unit)
            })
            .ok_or(MaterialCircuitError::PurchaseInvariant)?
            .unit_price;
        let cash = e
            .book
            .cash(request.buyer)?
            .micro_units()
            .saturating_sub(request.floor.micro_units())
            .max(0);
        let quantity =
            u64::try_from((cash / price.micro_units()).min(i128::from(request.requested)))
                .map_err(|_| MaterialCircuitError::Arithmetic)?;
        let order = ServiceOrder {
            order_id: request.order_id,
            performance_period: state.period,
            provider_site_id: request.provider,
            buyer: request.buyer,
            good_id: request.good,
            unit_id: request.unit,
            quantity,
        };
        if state
            .service_orders
            .iter()
            .any(|r| r.order_id == order.order_id)
        {
            return Err(MaterialCircuitError::DuplicateRow);
        }
        if quantity > 0 {
            if state.service_orders.len() + state.orders.len() + state.final_demand_orders.len()
                >= MAX_MATERIAL_CIRCUIT_ROWS
            {
                return Err(MaterialCircuitError::RowLimit);
            }
            movements.push(e.book.reserve_purchase(PurchaseEscrow::new(
                OutboundOrderId::Service(order.order_id),
                order.buyer,
                AccountId::Site(order.provider_site_id),
                quantity,
                price,
            )?)?);
            state.service_orders.push(order.clone());
        }
        result.push(receipt(&order, request.requested, price));
    }
    result.sort_by_key(|r| r.order_id);
    state.service_orders.sort_by_key(|r| r.order_id);
    if result.len() > MAX_SERVICE_RECEIPTS_PER_PERIOD {
        return Err(MaterialCircuitError::RowLimit);
    }
    if result.windows(2).any(|r| r[0].order_id == r[1].order_id) {
        return Err(MaterialCircuitError::DuplicateRow);
    }
    Ok(result)
}
fn receipt(order: &ServiceOrder, requested: u64, price: Currency) -> ServicePerformanceReceipt {
    ServicePerformanceReceipt {
        period: order.performance_period,
        order_id: order.order_id,
        provider_site_id: order.provider_site_id,
        buyer: order.buyer,
        good_id: order.good_id,
        unit_id: order.unit_id,
        requested_quantity: requested,
        admitted_quantity: order.quantity,
        performed_quantity: 0,
        used_quantity: 0,
        unused_quantity: 0,
        expired_quantity: 0,
        unit_price: price,
    }
}
