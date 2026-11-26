//! Complete merchant and local final-demand admission before any allocation.

use super::BTreeSet;
use crate::{
    GoodId, MaterialCatalog, MaterialCircuitError, MaterialCircuitState, MerchantHandling,
    MerchantRole, SiteId, UnitId,
};

pub(crate) fn merchant(catalog: &MaterialCatalog, site: SiteId) -> Option<&MerchantHandling> {
    catalog
        .merchants
        .binary_search_by_key(&site, |row| row.site_id)
        .ok()
        .map(|index| &catalog.merchants[index])
}

/// A merchant's handling row for a good: `(hours_per_unit, units)`, the hours that handle a block of units.
pub(crate) fn handling_row(
    catalog: &MaterialCatalog,
    site: SiteId,
    good: GoodId,
    unit: UnitId,
) -> Result<(u64, u64), MaterialCircuitError> {
    catalog
        .handling_coefficients
        .binary_search_by_key(&(site, good, unit), |row| {
            (row.site_id, row.good_id, row.unit_id)
        })
        .ok()
        .map(|index| {
            let row = &catalog.handling_coefficients[index];
            (row.hours_per_unit, row.units)
        })
        .filter(|(hours, units)| *hours > 0 && *units > 0)
        .ok_or(MaterialCircuitError::MerchantInvariant)
}

pub(crate) fn hours_per_unit(
    catalog: &MaterialCatalog,
    site: SiteId,
    good: GoodId,
    unit: UnitId,
) -> Result<u64, MaterialCircuitError> {
    handling_row(catalog, site, good, unit).map(|(hours, _)| hours)
}

/// Hours to handle `quantity` units of a block row: `ceil(quantity x hours_per_unit / units)`.
pub(crate) fn block_hours(
    hours_per_unit: u64,
    units: u64,
    quantity: u64,
) -> Result<u64, MaterialCircuitError> {
    let total = u128::from(quantity)
        .checked_mul(u128::from(hours_per_unit))
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let units = u128::from(units);
    if units == 0 {
        return Err(MaterialCircuitError::MerchantInvariant);
    }
    u64::try_from(total.div_ceil(units)).map_err(|_| MaterialCircuitError::Arithmetic)
}

/// Units that `hours` hours handle of a block row: `floor(hours x units / hours_per_unit)`.
pub(crate) fn block_units(
    hours_per_unit: u64,
    units: u64,
    hours: u64,
) -> Result<u64, MaterialCircuitError> {
    let total = u128::from(hours)
        .checked_mul(u128::from(units))
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let per = u128::from(hours_per_unit);
    if per == 0 {
        return Err(MaterialCircuitError::MerchantInvariant);
    }
    u64::try_from(total / per).map_err(|_| MaterialCircuitError::Arithmetic)
}

/// Hours to handle `quantity` units at this site: `ceil(quantity x hours_per_unit / units)`.
///
/// # Errors
/// `MerchantInvariant` for a site and good without a row; `Arithmetic` on overflow.
pub(crate) fn handling_hours(
    catalog: &MaterialCatalog,
    site: SiteId,
    good: GoodId,
    unit: UnitId,
    quantity: u64,
) -> Result<u64, MaterialCircuitError> {
    let (hours, units) = handling_row(catalog, site, good, unit)?;
    block_hours(hours, units, quantity)
}

/// Units that `hours` hours can handle: `floor(hours x units / hours_per_unit)`.
///
/// # Errors
/// `MerchantInvariant` for a site and good without a row; `Arithmetic` on overflow.
pub(crate) fn handled_units(
    catalog: &MaterialCatalog,
    site: SiteId,
    good: GoodId,
    unit: UnitId,
    hours: u64,
) -> Result<u64, MaterialCircuitError> {
    let (per, units) = handling_row(catalog, site, good, unit)?;
    block_units(per, units, hours)
}

/// The handling cost of one unit at `wage` micros an hour: `ceil(hours_per_unit x wage / units)` micros.
///
/// # Errors
/// `Arithmetic` on overflow or a negative wage; `MerchantInvariant` for a block of no units.
pub(crate) fn handling_cost_per_unit(
    hours_per_unit: u64,
    units: u64,
    wage: i128,
) -> Result<i128, MaterialCircuitError> {
    if wage < 0 {
        return Err(MaterialCircuitError::Arithmetic);
    }
    if units == 0 {
        return Err(MaterialCircuitError::MerchantInvariant);
    }
    let total = i128::from(hours_per_unit)
        .checked_mul(wage)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let units = i128::from(units);
    // total >= 0 and units > 0, so the quotient rounds up with no overflow past `total`.
    Ok(total / units + i128::from(total % units != 0))
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
        if merchant(catalog, row.site_id).is_none() || row.hours_per_unit == 0 || row.units == 0 {
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
