use super::CommodityKind;
use super::GoodId;
use super::MaterialCircuitError;
use super::MaterialCircuitState;
use super::Result;
use super::ServiceConnection;
use super::UnitId;
use crate::MaterialCatalog;
use crate::SiteId;
use crate::{AccountId, CircuitAccounting, PricePolicy, MAX_MATERIAL_CIRCUIT_ROWS};
use std::collections::BTreeSet;

pub(crate) fn canonicalize(state: &mut MaterialCircuitState) {
    state.service_connections.sort();
    state.service_orders.sort_by_key(|r| r.order_id);
}
fn account_exists(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    account: AccountId,
) -> bool {
    match account {
        AccountId::Site(id) => catalog
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
    provider: SiteId,
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
pub(crate) fn validate(catalog: &MaterialCatalog, state: &MaterialCircuitState) -> Result<()> {
    if state.service_connections.len() > crate::MAX_SERVICE_CONNECTIONS {
        return Err(MaterialCircuitError::RowLimit);
    }
    if catalog.commodities.len() > MAX_MATERIAL_CIRCUIT_ROWS
        || state.service_orders.len() > crate::MAX_SERVICE_ORDERS
    {
        return Err(MaterialCircuitError::RowLimit);
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
    for output in &catalog.process_outputs {
        if let Some(output_stage) = super::stage(catalog, output)? {
            if !providers.insert((output.site_id, output.good_id, output.unit_id)) {
                return Err(MaterialCircuitError::ServiceInvariant);
            }
            let start = catalog
                .input_coefficients
                .partition_point(|r| r.process_id < output.process_id);
            let end = catalog
                .input_coefficients
                .partition_point(|r| r.process_id <= output.process_id);
            for input in &catalog.input_coefficients[start..end] {
                if matches!(super::kind(catalog,input.good_id,input.unit_id)?,CommodityKind::PeriodService{stage} if stage>=output_stage)
                {
                    return Err(MaterialCircuitError::ServiceInvariant);
                }
            }
        }
    }
    for input in &catalog.input_coefficients {
        super::kind(catalog, input.good_id, input.unit_id)?;
    }
    for row in &state.inventory {
        if !matches!(
            super::kind(catalog, row.good_id, row.unit_id)?,
            CommodityKind::Storable { .. }
        ) {
            return Err(MaterialCircuitError::ServiceInvariant);
        }
    }
    for row in &state.service_connections {
        if !providers.contains(&(row.provider_site_id, row.good_id, row.unit_id))
            || !account_exists(catalog, state, row.buyer)
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
    validate_policies(catalog, state, &providers)
}
fn validate_policies(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    providers: &BTreeSet<(SiteId, GoodId, UnitId)>,
) -> Result<()> {
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        return if state.service_orders.is_empty() {
            Ok(())
        } else {
            Err(MaterialCircuitError::MonetaryInvariant)
        };
    };
    let Some(r) = &e.recurring else { return Ok(()) };
    if catalog.service_inputs.len() > MAX_MATERIAL_CIRCUIT_ROWS {
        return Err(MaterialCircuitError::RowLimit);
    }
    let mut keys = BTreeSet::new();
    for policy in &catalog.service_inputs {
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
        let service = super::is_service(catalog, offer.good_id, offer.unit_id);
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
        let first = catalog
            .process_outputs
            .partition_point(|o| o.process_id < policy.process_id);
        let output = catalog
            .process_outputs
            .get(first)
            .filter(|o| o.process_id == policy.process_id)
            .ok_or(MaterialCircuitError::ProcessInvariant)?;
        if super::is_service(catalog, output.good_id, output.unit_id) && policy.output_buffer != 0 {
            return Err(MaterialCircuitError::ServiceInvariant);
        }
    }
    for row in &r.household_stocks {
        if !matches!(
            super::kind(catalog, row.good_id, row.unit_id)?,
            CommodityKind::Storable { .. }
        ) {
            return Err(MaterialCircuitError::ServiceInvariant);
        }
    }
    Ok(())
}
