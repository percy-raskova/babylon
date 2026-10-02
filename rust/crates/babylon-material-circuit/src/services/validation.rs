use super::{
    is_service, kind, stage, CommodityKind, GoodId, MaterialCircuitError, MaterialCircuitState,
    Result, ServiceConnection, UnitId,
};
use crate::{AccountId, CircuitAccounting, PricePolicy, MAX_MATERIAL_CIRCUIT_ROWS};
use std::collections::BTreeSet;

pub(crate) fn canonicalize(state: &mut MaterialCircuitState) {
    state.commodities.sort_by_key(|r| (r.good_id, r.unit_id));
    state.service_connections.sort();
    state.service_orders.sort_by_key(|r| r.order_id);
    if let CircuitAccounting::Monetary(e) = &mut state.accounting {
        if let Some(r) = &mut e.recurring {
            r.service_inputs
                .sort_by_key(|r| (r.buyer_site_id, r.good_id, r.unit_id));
        }
    }
}
fn account_exists(state: &MaterialCircuitState, account: AccountId) -> bool {
    match account {
        AccountId::Site(id) => state
            .site_logistics_nodes
            .binary_search_by_key(&id, |r| r.site_id)
            .is_ok(),
        AccountId::Household(id) => state
            .final_demand_principals
            .binary_search_by_key(&id, |r| r.id)
            .is_ok(),
        _ => false,
    }
}
fn connection(
    state: &MaterialCircuitState,
    provider: crate::SiteId,
    buyer: AccountId,
    good: GoodId,
    unit: UnitId,
) -> bool {
    state
        .service_connections
        .binary_search(&ServiceConnection {
            provider_site_id: provider,
            buyer,
            good_id: good,
            unit_id: unit,
        })
        .is_ok()
}
pub(crate) fn validate(state: &MaterialCircuitState) -> Result<()> {
    if state.service_connections.len() > crate::MAX_SERVICE_CONNECTIONS {
        return Err(MaterialCircuitError::RowLimit);
    }
    for n in [state.commodities.len(), state.service_orders.len()] {
        if n > MAX_MATERIAL_CIRCUIT_ROWS {
            return Err(MaterialCircuitError::RowLimit);
        }
    }
    if state.service_connections.windows(2).any(|p| p[0] == p[1])
        || state
            .service_orders
            .windows(2)
            .any(|p| p[0].order_id == p[1].order_id)
    {
        return Err(MaterialCircuitError::DuplicateRow);
    }
    let mut providers = BTreeSet::new();
    for output in &state.process_outputs {
        if let Some(output_stage) = stage(state, output)? {
            if !providers.insert((output.site_id, output.good_id, output.unit_id)) {
                return Err(MaterialCircuitError::ServiceInvariant);
            }
            let start = state
                .input_coefficients
                .partition_point(|r| r.process_id < output.process_id);
            let end = state
                .input_coefficients
                .partition_point(|r| r.process_id <= output.process_id);
            for input in &state.input_coefficients[start..end] {
                if matches!(kind(state,input.good_id,input.unit_id)?,CommodityKind::PeriodService{stage} if stage>=output_stage)
                {
                    return Err(MaterialCircuitError::ServiceInvariant);
                }
            }
        }
    }
    for input in &state.input_coefficients {
        kind(state, input.good_id, input.unit_id)?;
    }
    for row in &state.inventory {
        if !matches!(
            kind(state, row.good_id, row.unit_id)?,
            CommodityKind::Storable { .. }
        ) {
            return Err(MaterialCircuitError::ServiceInvariant);
        }
    }
    for row in &state.service_connections {
        if !providers.contains(&(row.provider_site_id, row.good_id, row.unit_id))
            || !account_exists(state, row.buyer)
            || row.buyer == AccountId::Site(row.provider_site_id)
        {
            return Err(MaterialCircuitError::ServiceInvariant);
        }
    }
    for row in &state.service_orders {
        if row.quantity == 0
            || row.performance_period < state.period
            || !connection(
                state,
                row.provider_site_id,
                row.buyer,
                row.good_id,
                row.unit_id,
            )
        {
            return Err(MaterialCircuitError::ServiceInvariant);
        }
    }
    validate_policies(state, &providers)
}
fn validate_policies(
    state: &MaterialCircuitState,
    providers: &BTreeSet<(crate::SiteId, GoodId, UnitId)>,
) -> Result<()> {
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        return if state.service_orders.is_empty() {
            Ok(())
        } else {
            Err(MaterialCircuitError::MonetaryInvariant)
        };
    };
    let Some(r) = &e.recurring else { return Ok(()) };
    if r.service_inputs.len() > MAX_MATERIAL_CIRCUIT_ROWS {
        return Err(MaterialCircuitError::RowLimit);
    }
    let mut keys = BTreeSet::new();
    for policy in &r.service_inputs {
        if !keys.insert((policy.buyer_site_id, policy.good_id, policy.unit_id)) {
            return Err(MaterialCircuitError::DuplicateRow);
        }
        if policy.cash_floor.micro_units() < 0
            || policy.quantity_per_period == 0
            || !connection(
                state,
                policy.provider_site_id,
                AccountId::Site(policy.buyer_site_id),
                policy.good_id,
                policy.unit_id,
            )
            || r.offers
                .binary_search_by_key(
                    &(policy.provider_site_id, policy.good_id, policy.unit_id),
                    |o| (o.site_id, o.good_id, o.unit_id),
                )
                .is_err()
        {
            return Err(MaterialCircuitError::ServiceInvariant);
        }
    }
    for offer in &r.offers {
        let service = is_service(state, offer.good_id, offer.unit_id);
        match offer.pricing {
            PricePolicy::ServiceResponsive {
                minimum,
                maximum,
                step,
            } if service
                && providers.contains(&(offer.site_id, offer.good_id, offer.unit_id))
                && minimum.micro_units() > 0
                && minimum <= maximum
                && step.micro_units() > 0
                && offer.unit_price >= minimum
                && offer.unit_price <= maximum => {}
            PricePolicy::ServiceResponsive { .. } => {
                return Err(MaterialCircuitError::ServiceInvariant)
            }
            PricePolicy::Responsive { .. } if service => {
                return Err(MaterialCircuitError::ServiceInvariant)
            }
            _ => {}
        }
        if service && !providers.contains(&(offer.site_id, offer.good_id, offer.unit_id)) {
            return Err(MaterialCircuitError::ServiceInvariant);
        }
    }
    for policy in &r.production {
        // Preserve the first canonical match before later duplicate-process validation.
        let first = state
            .process_outputs
            .partition_point(|o| o.process_id < policy.process_id);
        let output = state
            .process_outputs
            .get(first)
            .filter(|o| o.process_id == policy.process_id)
            .ok_or(MaterialCircuitError::ProcessInvariant)?;
        if is_service(state, output.good_id, output.unit_id) && policy.output_buffer != 0 {
            return Err(MaterialCircuitError::ServiceInvariant);
        }
    }
    for row in &r.household_stocks {
        if !matches!(
            kind(state, row.good_id, row.unit_id)?,
            CommodityKind::Storable { .. }
        ) {
            return Err(MaterialCircuitError::ServiceInvariant);
        }
    }
    Ok(())
}
