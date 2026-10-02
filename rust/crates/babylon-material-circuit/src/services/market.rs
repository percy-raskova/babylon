use super::{
    stage, GoodId, MaterialCircuitError, MaterialCircuitState, Result, ServiceMarketReceipt,
    ServicePerformanceReceipt, ServicePriceDecision, UnitId,
};
use crate::{CircuitAccounting, PricePolicy, ServiceOrder};
use babylon_kernel::currency::Currency;
use std::collections::BTreeMap;

type MarketKey = (crate::SiteId, GoodId, UnitId);

pub(super) fn capture(state: &MaterialCircuitState) -> Result<Vec<ServiceMarketReceipt>> {
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        return Ok(vec![]);
    };
    let Some(r) = &e.recurring else {
        return Ok(vec![]);
    };
    let mut markets = Vec::new();
    for output in &state.process_outputs {
        if stage(state, output)?.is_none() {
            continue;
        }
        let offer = r
            .offers
            .binary_search_by_key(&(output.site_id, output.good_id, output.unit_id), |r| {
                (r.site_id, r.good_id, r.unit_id)
            })
            .ok()
            .map(|i| &r.offers[i])
            .ok_or(MaterialCircuitError::PurchaseInvariant)?;
        markets.push(ServiceMarketReceipt {
            period: state.period,
            next_period: 0,
            process_id: output.process_id,
            site_id: output.site_id,
            good_id: output.good_id,
            unit_id: output.unit_id,
            requested_quantity: 0,
            admitted_quantity: 0,
            performed_quantity: 0,
            available_capacity: crate::capacity::process_available(
                state,
                output.process_id,
                output.site_id,
                state.period,
            )?
            .checked_mul(output.quantity_per_batch)
            .ok_or(MaterialCircuitError::Arithmetic)?,
            direct_cost: Currency::from_micro_units(0),
            old_price: offer.unit_price,
            next_price: offer.unit_price,
            reason: ServicePriceDecision::Fixed,
            planned_quantity: 0,
        });
    }
    markets.sort_by_key(|r| (r.site_id, r.good_id, r.unit_id));
    Ok(markets)
}
fn sum(
    rows: &[&ServicePerformanceReceipt],
    quantity: impl Fn(&ServicePerformanceReceipt) -> u64,
) -> Result<u64> {
    rows.iter().try_fold(0_u64, |n, r| {
        n.checked_add(quantity(r))
            .ok_or(MaterialCircuitError::Arithmetic)
    })
}
pub(super) fn update(
    state: &mut MaterialCircuitState,
    performance: &[ServicePerformanceReceipt],
    markets: &mut [ServiceMarketReceipt],
    next_period: u64,
) -> Result<()> {
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        return Ok(());
    };
    let Some(r) = &mut e.recurring else {
        return Ok(());
    };
    // Group borrowed rows, but sum lazily in market order to preserve first refusal.
    let mut performance_groups = BTreeMap::<MarketKey, Vec<&ServicePerformanceReceipt>>::new();
    for row in performance {
        performance_groups
            .entry((row.provider_site_id, row.good_id, row.unit_id))
            .or_default()
            .push(row);
    }
    let mut future_groups = BTreeMap::<MarketKey, Vec<&ServiceOrder>>::new();
    for order in &state.service_orders {
        if order.performance_period == next_period {
            future_groups
                .entry((order.provider_site_id, order.good_id, order.unit_id))
                .or_default()
                .push(order);
        }
    }
    for market in markets {
        let key = (market.site_id, market.good_id, market.unit_id);
        market.next_period = next_period;
        let rows = performance_groups.get(&key).map_or(&[][..], Vec::as_slice);
        market.requested_quantity = sum(rows, |r| r.requested_quantity)?;
        market.admitted_quantity = sum(rows, |r| r.admitted_quantity)?;
        market.performed_quantity = sum(rows, |r| r.performed_quantity)?;
        let offer = r
            .offers
            .binary_search_by_key(&key, |r| (r.site_id, r.good_id, r.unit_id))
            .ok()
            .map(|i| &mut r.offers[i])
            .ok_or(MaterialCircuitError::PurchaseInvariant)?;
        let future = future_groups
            .get(&key)
            .map_or(&[][..], Vec::as_slice)
            .iter()
            .try_fold(0_u64, |n, o| {
                n.checked_add(o.quantity)
                    .ok_or(MaterialCircuitError::Arithmetic)
            })?;
        market.planned_quantity = market.requested_quantity.max(future);
        r.production
            .binary_search_by_key(&market.process_id, |p| p.process_id)
            .ok()
            .map(|i| &mut r.production[i])
            .ok_or(MaterialCircuitError::ProcessInvariant)?
            .planned_batches = market.planned_quantity.div_ceil(
            state
                .process_outputs
                .binary_search_by_key(&market.process_id, |o| o.process_id)
                .ok()
                .map(|i| &state.process_outputs[i])
                .ok_or(MaterialCircuitError::ProcessInvariant)?
                .quantity_per_batch,
        );
        let (price, reason) = quote(market, &offer.pricing)?;
        offer.unit_price = price;
        market.next_price = price;
        market.reason = reason;
    }
    Ok(())
}
fn quote(
    row: &ServiceMarketReceipt,
    policy: &PricePolicy,
) -> Result<(Currency, ServicePriceDecision)> {
    let PricePolicy::ServiceResponsive {
        minimum,
        maximum,
        step,
    } = *policy
    else {
        return if matches!(policy, PricePolicy::Fixed) {
            Ok((row.old_price, ServicePriceDecision::Fixed))
        } else {
            Err(MaterialCircuitError::ServiceInvariant)
        };
    };
    let receipts_value = row
        .old_price
        .micro_units()
        .checked_mul(i128::from(row.performed_quantity))
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let reason = if row.admitted_quantity > row.performed_quantity {
        ServicePriceDecision::FundedUnmet
    } else if row.performed_quantity > 0 && row.direct_cost.micro_units() > receipts_value {
        ServicePriceDecision::CostPressure
    } else if row.performed_quantity < row.available_capacity
        && (row.performed_quantity == 0 || row.direct_cost.micro_units() < receipts_value)
    {
        ServicePriceDecision::SpareCapacity
    } else {
        ServicePriceDecision::Hold
    };
    let price = match reason {
        ServicePriceDecision::FundedUnmet | ServicePriceDecision::CostPressure => {
            Currency::from_micro_units(
                row.old_price
                    .micro_units()
                    .saturating_add(step.micro_units())
                    .min(maximum.micro_units()),
            )
        }
        ServicePriceDecision::SpareCapacity => Currency::from_micro_units(
            row.old_price
                .micro_units()
                .saturating_sub(step.micro_units())
                .max(minimum.micro_units()),
        ),
        _ => row.old_price,
    };
    Ok((price, reason))
}
