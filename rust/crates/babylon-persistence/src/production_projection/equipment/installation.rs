use super::{
    add, add_cost, AssetBook, Definitions, EquipmentFacts, MaterialCircuitState,
    MaterialTickReceipts, ProductionProjectionError, ProductiveEquipment, Result,
};
use babylon_material_circuit::{
    equipment_installation_id, AccountId, EquipmentAssetId, EquipmentCohortId, InstallationId,
    InstallationReceipt, InstalledEquipmentCohort, PendingInstallation,
};
use std::collections::{BTreeMap, BTreeSet};
type Pending = BTreeMap<InstallationId, PendingInstallation>;
type Cohorts = BTreeMap<EquipmentCohortId, InstalledEquipmentCohort>;
pub(super) fn reconcile(
    prior: &MaterialCircuitState,
    equipment: &ProductiveEquipment,
    receipt: &MaterialTickReceipts,
    definitions: &Definitions<'_>,
    assets: &mut AssetBook,
    cohorts: &mut Cohorts,
) -> Result<(Pending, EquipmentFacts)> {
    let mut old: Pending = equipment
        .pending
        .iter()
        .map(|r| (r.id, r.clone()))
        .collect();
    let mut pending = Pending::new();
    let mut facts = EquipmentFacts::default();
    let policies: BTreeMap<_, _> = equipment
        .installation_policies
        .iter()
        .map(|r| (r.process_id, r))
        .collect();
    let mut seen = BTreeSet::new();
    let mut used = BTreeMap::new();
    for r in &receipt.installation {
        r.validate().map_err(|_| ProductionProjectionError::State)?;
        let policy = policies
            .get(&r.process_id)
            .ok_or(ProductionProjectionError::State)?;
        let previous = old.remove(&r.id);
        if r.period != prior.period
            || !seen.insert(r.id)
            || (r.started && r.units > policy.maximum_started_units_per_period)
        {
            return Err(ProductionProjectionError::State);
        }
        let start = validate_start(prior.period, r, previous.as_ref(), definitions, &mut facts)?;
        transition(r, start, assets, cohorts, &mut pending, definitions)?;
        add(&mut used, r.process_id, r.used_hours)?;
    }
    if !old.is_empty()
        || used
            .iter()
            .any(|(id, n)| *n > policies[id].maximum_hours_per_period)
    {
        return Err(ProductionProjectionError::State);
    }
    wages(receipt, definitions)?;
    Ok((pending, facts))
}
fn validate_start(
    period: u64,
    r: &InstallationReceipt,
    previous: Option<&PendingInstallation>,
    definitions: &Definitions<'_>,
    facts: &mut EquipmentFacts,
) -> Result<u64> {
    let (binding, definition) = definitions.get(r.process_id)?;
    if r.site_id != binding.site_id {
        return Err(ProductionProjectionError::State);
    }
    let start = if r.started {
        if previous.is_some()
            || r.id != equipment_installation_id(period, r.process_id)
            || r.units.checked_mul(definition.installation_hours_per_unit) != Some(r.opening_hours)
        {
            return Err(ProductionProjectionError::State);
        }
        for &(good, unit, coefficient) in &definitions.materials[&definition.id] {
            add(
                &mut facts.materials,
                (r.site_id, good, unit),
                r.units
                    .checked_mul(coefficient)
                    .ok_or(ProductionProjectionError::Arithmetic)?,
            )?;
        }
        period
    } else {
        let old = previous.ok_or(ProductionProjectionError::State)?;
        if (old.process_id, old.units, old.remaining_hours)
            != (r.process_id, r.units, r.opening_hours)
        {
            return Err(ProductionProjectionError::State);
        }
        old.started_period
    };
    let hours = facts
        .labor
        .entry((r.site_id, definition.installation_labor_unit_id))
        .or_default();
    hours.0 = hours
        .0
        .checked_add(r.opening_hours)
        .ok_or(ProductionProjectionError::Arithmetic)?;
    hours.1 = hours
        .1
        .checked_add(r.used_hours)
        .ok_or(ProductionProjectionError::Arithmetic)?;
    Ok(start)
}
fn transition(
    r: &InstallationReceipt,
    started_period: u64,
    assets: &mut AssetBook,
    cohorts: &mut Cohorts,
    pending: &mut Pending,
    definitions: &Definitions<'_>,
) -> Result<()> {
    let key = EquipmentAssetId::Installation(r.id);
    let previous = assets.remove(&key);
    if (r.started && previous.is_some())
        || (!r.started && previous != Some((r.site_id, r.opening_carrying)))
    {
        return Err(ProductionProjectionError::State);
    }
    let asset = if r.remaining_hours == 0 {
        let (_, d) = definitions.get(r.process_id)?;
        let id = EquipmentCohortId::from_bytes(r.id.as_bytes());
        if cohorts
            .insert(
                id,
                InstalledEquipmentCohort {
                    id,
                    process_id: r.process_id,
                    units: r.units,
                    remaining_service_batches: r
                        .units
                        .checked_mul(d.service_batches_per_unit)
                        .ok_or(ProductionProjectionError::Arithmetic)?,
                    usable_from_period: r.usable_from_period,
                },
            )
            .is_some()
        {
            return Err(ProductionProjectionError::State);
        }
        EquipmentAssetId::Installed(id)
    } else {
        pending.insert(
            r.id,
            PendingInstallation {
                id: r.id,
                process_id: r.process_id,
                units: r.units,
                started_period,
                remaining_hours: r.remaining_hours,
            },
        );
        key
    };
    if assets
        .insert(asset, (r.site_id, r.closing_carrying))
        .is_some()
    {
        return Err(ProductionProjectionError::State);
    }
    Ok(())
}
fn wages(receipt: &MaterialTickReceipts, definitions: &Definitions<'_>) -> Result<()> {
    let mut actual = BTreeMap::new();
    let mut expected = BTreeMap::new();
    let mut accounts = BTreeMap::new();
    for r in &receipt.installation {
        let (_, d) = definitions.get(r.process_id)?;
        add_cost(
            &mut actual,
            (r.site_id, d.installation_labor_unit_id),
            r.wages_capitalized,
        )?;
        add_cost(
            &mut accounts,
            AccountId::Site(r.site_id),
            r.wages_capitalized,
        )?;
    }
    for r in &receipt.member_labor_use {
        add_cost(&mut expected, (r.site_id, r.unit_id), r.installation_wages)?;
    }
    actual.retain(|_, v| v.micro_units() > 0);
    expected.retain(|_, v| v.micro_units() > 0);
    accounts.retain(|_, v| v.micro_units() > 0);
    let statements: BTreeMap<_, _> = receipt
        .income
        .iter()
        .filter(|r| r.statement.installation_labor_capitalized.micro_units() > 0)
        .map(|r| (r.account, r.statement.installation_labor_capitalized))
        .collect();
    if actual != expected || accounts != statements {
        return Err(ProductionProjectionError::State);
    }
    Ok(())
}
