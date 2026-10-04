//! Authenticate the captured target and actual position without allocating new work.
use super::{
    add, Definitions, MaterialCircuitState, MaterialTickReceipts, ProductionProjectionError,
    ProductiveEquipment, Result,
};
use babylon_material_circuit::{
    EquipmentCohortId, InstallationTarget, InstalledEquipmentCohort, ProcessId,
};
use std::collections::BTreeMap;

type Units = BTreeMap<ProcessId, u64>;

pub(super) fn validate(
    prior: &MaterialCircuitState,
    equipment: &ProductiveEquipment,
    receipt: &MaterialTickReceipts,
    definitions: &Definitions<'_>,
    post_wear: &BTreeMap<EquipmentCohortId, InstalledEquipmentCohort>,
) -> Result<()> {
    let plans: BTreeMap<_, _> = super::super::lifecycle::recurring(prior)
        .into_iter()
        .flat_map(|r| &r.production)
        .map(|r| (r.process_id, r.planned_batches))
        .collect();
    let mut policies: BTreeMap<_, _> = equipment
        .installation_policies
        .iter()
        .map(|r| (r.process_id, r))
        .collect();
    let installed = units(post_wear.values().map(|r| (r.process_id, r.units)))?;
    let pending = units(equipment.pending.iter().map(|r| (r.process_id, r.units)))?;
    let mut started = Units::new();
    let mut continuing = Units::new();
    for r in &receipt.installation {
        add(
            if r.started {
                &mut started
            } else {
                &mut continuing
            },
            r.process_id,
            r.units,
        )?;
    }
    for r in &receipt.installation_decisions {
        r.validate().map_err(|_| ProductionProjectionError::State)?;
        let policy = policies
            .remove(&r.process_id)
            .ok_or(ProductionProjectionError::State)?;
        let (binding, definition) = definitions.get(r.process_id)?;
        let planned = plans.get(&r.process_id).copied();
        let target = match policy.target {
            InstallationTarget::FixedUnits(n) => n,
            InstallationTarget::ProductionPlan { replacement_units } => {
                let batches = planned.ok_or(ProductionProjectionError::State)?;
                if definition.batches_per_unit_per_period == 0 {
                    return Err(ProductionProjectionError::State);
                }
                batches
                    .div_ceil(definition.batches_per_unit_per_period)
                    .max(replacement_units)
            }
        };
        let live = installed.get(&r.process_id).copied().unwrap_or(0);
        let work_in_progress = pending.get(&r.process_id).copied().unwrap_or(0);
        let position = live
            .checked_add(work_in_progress)
            .ok_or(ProductionProjectionError::Arithmetic)?;
        if r.period != prior.period
            || r.site_id != binding.site_id
            || r.captured_plan_batches != planned.unwrap_or(0)
            || r.target_units != target
            || r.installed_units != live
            || r.pending_units != work_in_progress
            || r.requested_units != target.saturating_sub(position)
            || r.started_units != started.remove(&r.process_id).unwrap_or(0)
            || r.started_units > policy.maximum_started_units_per_period
            || r.pending_units != continuing.remove(&r.process_id).unwrap_or(0)
        {
            return Err(ProductionProjectionError::State);
        }
    }
    if !policies.is_empty() || !started.is_empty() || !continuing.is_empty() {
        return Err(ProductionProjectionError::State);
    }
    Ok(())
}
fn units(rows: impl Iterator<Item = (ProcessId, u64)>) -> Result<Units> {
    let mut result = Units::new();
    for (key, quantity) in rows {
        add(&mut result, key, quantity)?;
    }
    Ok(result)
}
