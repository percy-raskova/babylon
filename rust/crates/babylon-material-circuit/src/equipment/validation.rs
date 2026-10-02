//! Bounded, explicit equipment and installation relationships.
use super::{MaterialCircuitError, MaterialCircuitState, ProductiveEquipment, Result};
use crate::{CircuitAccounting, CommodityKind, MAX_MATERIAL_CIRCUIT_ROWS};
use std::collections::BTreeSet;
pub(crate) fn row_limits(e: &ProductiveEquipment) -> Result<()> {
    if [
        e.definitions.len(),
        e.bindings.len(),
        e.installation_inputs.len(),
        e.cohorts.len(),
        e.pending.len(),
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
pub(crate) fn canonicalize(e: &mut ProductiveEquipment) {
    e.definitions.sort_by_key(|r| r.id);
    e.bindings.sort_by_key(|r| r.process_id);
    e.installation_inputs
        .sort_by_key(|r| (r.definition_id, r.good_id, r.unit_id));
    e.cohorts.sort_by_key(|r| (r.process_id, r.id));
    e.pending.sort_by_key(|r| (r.process_id, r.id));
    e.installation_policies.sort_by_key(|r| r.process_id);
    e.investment_policies.sort_by_key(|r| r.process_id);
}
fn unique<T, K: Ord>(rows: &[T], key: impl Fn(&T) -> K) -> Result<()> {
    if rows.windows(2).any(|p| key(&p[0]) >= key(&p[1])) {
        return Err(MaterialCircuitError::DuplicateRow);
    }
    Ok(())
}
pub(crate) fn validate(state: &MaterialCircuitState, e: &ProductiveEquipment) -> Result<()> {
    row_limits(e)?;
    if !matches!(state.accounting, CircuitAccounting::Monetary(_)) {
        return Err(MaterialCircuitError::EquipmentInvariant);
    }
    unique(&e.definitions, |r| r.id)?;
    unique(&e.bindings, |r| r.process_id)?;
    unique(&e.installation_inputs, |r| {
        (r.definition_id, r.good_id, r.unit_id)
    })?;
    unique(&e.cohorts, |r| (r.process_id, r.id))?;
    unique(&e.pending, |r| (r.process_id, r.id))?;
    unique(&e.installation_policies, |r| r.process_id)?;
    unique(&e.investment_policies, |r| r.process_id)?;
    if e.cohorts
        .iter()
        .map(|r| r.id)
        .collect::<BTreeSet<_>>()
        .len()
        != e.cohorts.len()
        || e.pending
            .iter()
            .map(|r| r.id)
            .collect::<BTreeSet<_>>()
            .len()
            != e.pending.len()
    {
        return Err(MaterialCircuitError::DuplicateRow);
    }
    validate_definitions(state, e)?;
    validate_assets(state, e)?;
    validate_policies(state, e)
}
fn validate_definitions(state: &MaterialCircuitState, e: &ProductiveEquipment) -> Result<()> {
    let processes: BTreeSet<_> = state
        .process_outputs
        .iter()
        .map(|r| (r.process_id, r.site_id))
        .collect();
    let labor: BTreeSet<_> = state.labor.iter().map(|r| (r.site_id, r.unit_id)).collect();
    for d in &e.definitions {
        if d.batches_per_unit_per_period == 0
            || d.service_batches_per_unit == 0
            || d.installation_hours_per_unit == 0
            || !storable(state, d.equipment_good_id, d.equipment_unit_id)
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
            || !storable(state, i.good_id, i.unit_id)
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
fn validate_assets(state: &MaterialCircuitState, e: &ProductiveEquipment) -> Result<()> {
    for c in &e.cohorts {
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
    for p in &e.pending {
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
fn validate_policies(state: &MaterialCircuitState, e: &ProductiveEquipment) -> Result<()> {
    let routes: BTreeSet<_> = state
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

fn storable(state: &MaterialCircuitState, good: crate::GoodId, unit: crate::UnitId) -> bool {
    state
        .commodities
        .binary_search_by_key(&(good, unit), |r| (r.good_id, r.unit_id))
        .ok()
        .is_some_and(|i| matches!(state.commodities[i].kind, CommodityKind::Storable { .. }))
}
