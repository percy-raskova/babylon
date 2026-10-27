//! Bounded, explicit equipment and installation relationships.
use super::EquipmentPosition;
use super::MaterialCircuitError;
use super::MaterialCircuitState;
use super::ProductiveEquipment;
use super::Result;
use crate::GoodId;
use crate::MaterialCatalog;
use crate::UnitId;
use crate::{CircuitAccounting, CommodityKind, MAX_MATERIAL_CIRCUIT_ROWS};
use std::collections::BTreeSet;

pub(crate) fn row_limits(
    content: &ProductiveEquipment,
    position: &EquipmentPosition,
) -> Result<()> {
    row_limits_content(content)?;
    if [position.cohorts.len(), position.pending.len()]
        .into_iter()
        .any(|n| n > MAX_MATERIAL_CIRCUIT_ROWS)
    {
        return Err(MaterialCircuitError::RowLimit);
    }
    Ok(())
}

pub(crate) fn row_limits_content(e: &ProductiveEquipment) -> Result<()> {
    if [
        e.definitions.len(),
        e.bindings.len(),
        e.installation_inputs.len(),
        e.installation_policies.len(),
        e.investment_policies.len(),
    ]
    .into_iter()
    .any(|n| n > MAX_MATERIAL_CIRCUIT_ROWS)
    {
        return Err(MaterialCircuitError::RowLimit);
    }
    Ok(())
}

pub(crate) fn canonicalize_position(position: &mut crate::EquipmentPosition) {
    position.cohorts.sort_by_key(|r| (r.process_id, r.id));
    position.pending.sort_by_key(|r| (r.process_id, r.id));
}

pub(crate) fn canonicalize(e: &mut ProductiveEquipment) {
    e.definitions.sort_by_key(|r| r.id);
    e.bindings.sort_by_key(|r| r.process_id);
    e.installation_inputs
        .sort_by_key(|r| (r.definition_id, r.good_id, r.unit_id));
    e.installation_policies.sort_by_key(|r| r.process_id);
    e.investment_policies.sort_by_key(|r| r.process_id);
}

fn unique<T, K: Ord>(rows: &[T], key: impl Fn(&T) -> K) -> Result<()> {
    if rows.windows(2).any(|p| key(&p[0]) >= key(&p[1])) {
        return Err(MaterialCircuitError::DuplicateRow);
    }
    Ok(())
}

/// Validate the authored definitions once, without any installed position.
///
/// # Errors
/// Refuses a row bound, duplicate identity or zero coefficient.
pub(crate) fn validate_content(e: &ProductiveEquipment) -> Result<()> {
    row_limits_content(e)?;
    unique(&e.definitions, |r| r.id)?;
    unique(&e.bindings, |r| r.process_id)?;
    unique(&e.installation_inputs, |r| {
        (r.definition_id, r.good_id, r.unit_id)
    })?;
    unique(&e.installation_policies, |r| r.process_id)?;
    unique(&e.investment_policies, |r| r.process_id)?;
    for d in &e.definitions {
        if d.batches_per_unit_per_period == 0
            || d.service_batches_per_unit == 0
            || d.installation_hours_per_unit == 0
        {
            return Err(MaterialCircuitError::EquipmentInvariant);
        }
        e.definitions
            .binary_search_by_key(&d.id, |r| r.id)
            .map_err(|_| MaterialCircuitError::EquipmentInvariant)?;
    }
    for b in &e.bindings {
        e.definition(b.process_id)?;
    }
    for i in &e.installation_inputs {
        e.definitions
            .binary_search_by_key(&i.definition_id, |r| r.id)
            .map_err(|_| MaterialCircuitError::EquipmentInvariant)?;
        if i.quantity_per_equipment_unit == 0 {
            return Err(MaterialCircuitError::EquipmentInvariant);
        }
    }
    for p in &e.installation_policies {
        if p.maximum_started_units_per_period == 0 || p.maximum_hours_per_period == 0 {
            return Err(MaterialCircuitError::EquipmentInvariant);
        }
    }
    for p in &e.investment_policies {
        if p.maximum_installed_units == 0
            || p.maximum_purchase_per_period == 0
            || p.replacement_target_units > p.maximum_installed_units
            || p.expansion_earnings_fraction_bps > 10000
            || p.cash_floor.micro_units() < 0
            || e.installation_policies
                .binary_search_by_key(&p.process_id, |r| r.process_id)
                .is_err()
        {
            return Err(MaterialCircuitError::EquipmentInvariant);
        }
    }
    Ok(())
}

/// Validate one installed position against its authored content and the period.
///
/// # Errors
/// Refuses a row bound, duplicate identity, foreign definition or stale asset.
pub(crate) fn validate(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    content: &ProductiveEquipment,
) -> Result<()> {
    let position = &state.capacity_reservations.equipment;
    row_limits(content, position)?;
    if !matches!(state.accounting, CircuitAccounting::Monetary(_)) {
        return Err(MaterialCircuitError::EquipmentInvariant);
    }
    validate_content(content)?;
    unique(&position.cohorts, |r| (r.process_id, r.id))?;
    unique(&position.pending, |r| (r.process_id, r.id))?;
    if position
        .cohorts
        .iter()
        .map(|r| r.id)
        .collect::<BTreeSet<_>>()
        .len()
        != position.cohorts.len()
        || position
            .pending
            .iter()
            .map(|r| r.id)
            .collect::<BTreeSet<_>>()
            .len()
            != position.pending.len()
    {
        return Err(MaterialCircuitError::DuplicateRow);
    }
    validate_definitions(catalog, state, content)?;
    validate_assets(state, content, position)?;
    validate_policies(catalog, state, content)
}

fn validate_definitions(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    e: &ProductiveEquipment,
) -> Result<()> {
    let processes: BTreeSet<_> = catalog
        .process_outputs
        .iter()
        .map(|r| (r.process_id, r.site_id))
        .collect();
    let labor: BTreeSet<_> = state.labor.iter().map(|r| (r.site_id, r.unit_id)).collect();
    for d in &e.definitions {
        if d.batches_per_unit_per_period == 0
            || d.service_batches_per_unit == 0
            || d.installation_hours_per_unit == 0
            || !storable(catalog, d.equipment_good_id, d.equipment_unit_id)
        {
            return Err(MaterialCircuitError::EquipmentInvariant);
        }
    }
    for b in &e.bindings {
        let (_, d) = e.definition(b.process_id)?;
        if !processes.contains(&(b.process_id, b.site_id))
            || !labor.contains(&(b.site_id, d.installation_labor_unit_id))
        {
            return Err(MaterialCircuitError::EquipmentInvariant);
        }
    }
    for i in &e.installation_inputs {
        let d = e
            .definitions
            .binary_search_by_key(&i.definition_id, |r| r.id)
            .map_err(|_| MaterialCircuitError::EquipmentInvariant)?;
        if i.quantity_per_equipment_unit == 0
            || !storable(catalog, i.good_id, i.unit_id)
            || (i.good_id, i.unit_id)
                == (
                    e.definitions[d].equipment_good_id,
                    e.definitions[d].equipment_unit_id,
                )
        {
            return Err(MaterialCircuitError::EquipmentInvariant);
        }
    }
    Ok(())
}

fn validate_assets(
    state: &MaterialCircuitState,
    e: &ProductiveEquipment,
    position: &EquipmentPosition,
) -> Result<()> {
    for c in &position.cohorts {
        let (_, d) = e.definition(c.process_id)?;
        let life = c
            .units
            .checked_mul(d.service_batches_per_unit)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        c.units
            .checked_mul(d.batches_per_unit_per_period)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        if c.units == 0
            || c.remaining_service_batches == 0
            || c.remaining_service_batches > life
            || c.usable_from_period == 0
            || c.usable_from_period > state.period
        {
            return Err(MaterialCircuitError::EquipmentInvariant);
        }
    }
    for p in &position.pending {
        let (_, d) = e.definition(p.process_id)?;
        let hours = p
            .units
            .checked_mul(d.installation_hours_per_unit)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        if e.installation_policies
            .binary_search_by_key(&p.process_id, |r| r.process_id)
            .is_err()
            || p.units == 0
            || p.remaining_hours == 0
            || p.remaining_hours > hours
            || p.started_period == 0
            || p.started_period >= state.period
        {
            return Err(MaterialCircuitError::EquipmentInvariant);
        }
    }
    Ok(())
}

fn validate_policies(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    e: &ProductiveEquipment,
) -> Result<()> {
    let routes: BTreeSet<_> = catalog
        .supplier_routes
        .iter()
        .map(|r| (r.buyer_site_id, r.supplier_site_id, r.good_id, r.unit_id))
        .collect();
    let CircuitAccounting::Monetary(m) = &state.accounting else {
        return Err(MaterialCircuitError::EquipmentInvariant);
    };
    let offers: BTreeSet<_> = m
        .recurring
        .iter()
        .flat_map(|r| r.offers.iter())
        .map(|r| (r.site_id, r.good_id, r.unit_id))
        .collect();
    for p in &e.installation_policies {
        e.definition(p.process_id)?;
        if p.maximum_started_units_per_period == 0
            || p.maximum_hours_per_period == 0
            || (matches!(p.target, super::InstallationTarget::ProductionPlan { .. })
                && super::choice::planned_batches(state, p.process_id).is_none())
        {
            return Err(MaterialCircuitError::EquipmentInvariant);
        }
    }
    for p in &e.investment_policies {
        let (b, d) = e.definition(p.process_id)?;
        if p.maximum_installed_units == 0
            || p.maximum_purchase_per_period == 0
            || p.replacement_target_units > p.maximum_installed_units
            || p.expansion_earnings_fraction_bps > 10000
            || p.cash_floor.micro_units() < 0
            || e.installation_policies
                .binary_search_by_key(&p.process_id, |r| r.process_id)
                .is_err()
            || !routes.contains(&(
                b.site_id,
                p.supplier_site_id,
                d.equipment_good_id,
                d.equipment_unit_id,
            ))
        {
            return Err(MaterialCircuitError::EquipmentInvariant);
        }
        if !offers.contains(&(p.supplier_site_id, d.equipment_good_id, d.equipment_unit_id)) {
            return Err(MaterialCircuitError::EquipmentInvariant);
        }
    }
    Ok(())
}

fn storable(catalog: &MaterialCatalog, good: GoodId, unit: UnitId) -> bool {
    catalog
        .commodities
        .binary_search_by_key(&(good, unit), |r| (r.good_id, r.unit_id))
        .is_ok_and(|i| matches!(catalog.commodities[i].kind, CommodityKind::Storable { .. }))
}
