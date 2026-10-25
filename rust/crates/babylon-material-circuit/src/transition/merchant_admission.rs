//! Complete merchant and local final-demand admission before any allocation.

use super::BTreeSet;
use crate::{
    GoodId, MaterialCatalog, MaterialCircuitError, MaterialCircuitState, MerchantHandling,
    MerchantRole, SiteId, UnitId,
};

pub(super) fn merchant(catalog: &MaterialCatalog, site: SiteId) -> Option<&MerchantHandling> {
    catalog
        .merchants
        .binary_search_by_key(&site, |row| row.site_id)
        .ok()
        .map(|index| &catalog.merchants[index])
}

pub(super) fn hours_per_unit(
    catalog: &MaterialCatalog,
    site: SiteId,
    good: GoodId,
    unit: UnitId,
) -> Result<u64, MaterialCircuitError> {
    catalog
        .handling_coefficients
        .binary_search_by_key(&(site, good, unit), |row| {
            (row.site_id, row.good_id, row.unit_id)
        })
        .ok()
        .map(|index| catalog.handling_coefficients[index].hours_per_unit)
        .filter(|hours| *hours > 0)
        .ok_or(MaterialCircuitError::MerchantInvariant)
}

pub(super) fn validate_merchants(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
) -> Result<(), MaterialCircuitError> {
    if super::has_duplicate(&catalog.merchants, |row| row.site_id)
        || super::has_duplicate(&catalog.handling_coefficients, |row| {
            (row.site_id, row.good_id, row.unit_id)
        })
        || super::has_duplicate(&state.final_demand_principals, |row| row.id)
        || super::has_duplicate(&state.final_demand_orders, |row| row.order_id)
    {
        return Err(MaterialCircuitError::DuplicateRow);
    }
    let road_principals: BTreeSet<_> = state
        .route_stage_capacities
        .iter()
        .map(|row| row.corridor_id)
        .collect();
    let mut handling_principals = BTreeSet::new();
    for row in &catalog.merchants {
        if super::site_node(catalog, row.site_id).is_none()
            || road_principals.contains(&row.capacity_id)
        {
            return Err(MaterialCircuitError::MerchantInvariant);
        }
        if !handling_principals.insert(row.capacity_id) {
            return Err(MaterialCircuitError::DuplicateRow);
        }
    }
    for row in &catalog.handling_coefficients {
        if merchant(catalog, row.site_id).is_none() || row.hours_per_unit == 0 {
            return Err(MaterialCircuitError::MerchantInvariant);
        }
        catalog.grams_per_unit(row.good_id, row.unit_id)?;
    }
    for row in &state.orders {
        if merchant(catalog, row.supplier_site_id).is_some() {
            hours_per_unit(catalog, row.supplier_site_id, row.good_id, row.unit_id)?;
        }
    }
    for row in &state.final_demand_orders {
        let retailer = merchant(catalog, row.retailer_site_id)
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        let principal = state
            .final_demand_principals
            .binary_search_by_key(&row.demand_principal_id, |row| row.id)
            .ok()
            .map(|index| &state.final_demand_principals[index])
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        if retailer.role != MerchantRole::Retail
            || retailer.location != principal.location
            || row.ordered == 0
            || row.fulfilled > row.ordered
        {
            return Err(MaterialCircuitError::FinalDemandInvariant);
        }
        hours_per_unit(catalog, row.retailer_site_id, row.good_id, row.unit_id)?;
        catalog.grams_per_unit(row.good_id, row.unit_id)?;
    }
    Ok(())
}
