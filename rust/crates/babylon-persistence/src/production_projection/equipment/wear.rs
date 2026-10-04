use super::{
    add, add_cost, AssetBook, Definitions, MaterialCircuitState, MaterialTickReceipts,
    ProductionProjectionError, ProductiveEquipment, Result,
};
use babylon_material_circuit::{
    AccountId, EquipmentAssetId, EquipmentCohortId, InstalledEquipmentCohort,
};
use std::collections::{BTreeMap, BTreeSet};
pub(super) fn reconcile(
    prior: &MaterialCircuitState,
    equipment: &ProductiveEquipment,
    receipt: &MaterialTickReceipts,
    definitions: &Definitions<'_>,
    assets: &mut AssetBook,
) -> Result<BTreeMap<EquipmentCohortId, InstalledEquipmentCohort>> {
    let mut cohorts: BTreeMap<_, _> = equipment
        .cohorts
        .iter()
        .map(|r| (r.id, r.clone()))
        .collect();
    let mut seen = BTreeSet::new();
    let mut used = BTreeMap::new();
    let mut costs = BTreeMap::new();
    for r in &receipt.equipment_wear {
        r.validate().map_err(|_| ProductionProjectionError::State)?;
        let cohort = cohorts
            .get_mut(&r.cohort_id)
            .ok_or(ProductionProjectionError::State)?;
        let (binding, definition) = definitions.get(cohort.process_id)?;
        let key = EquipmentAssetId::Installed(r.cohort_id);
        if r.period != prior.period
            || !seen.insert(r.cohort_id)
            || (r.process_id, r.site_id) != (cohort.process_id, binding.site_id)
            || cohort.usable_from_period > prior.period
            || r.opening_service_batches != cohort.remaining_service_batches
            || cohort
                .units
                .checked_mul(definition.batches_per_unit_per_period)
                .is_none_or(|n| r.used_batches > n)
            || assets.get(&key) != Some(&(r.site_id, r.opening_carrying))
        {
            return Err(ProductionProjectionError::State);
        }
        cohort.remaining_service_batches = r.remaining_service_batches;
        if r.remaining_service_batches == 0 {
            assets.remove(&key);
        } else {
            assets.insert(key, (r.site_id, r.closing_carrying));
        }
        add(&mut used, r.process_id, r.used_batches)?;
        add_cost(&mut costs, AccountId::Site(r.site_id), r.carried_to_output)?;
    }
    cohorts.retain(|_, r| r.remaining_service_batches > 0);
    let expected: BTreeMap<_, _> = receipt
        .production
        .iter()
        .filter(|r| r.produced_batches > 0)
        .map(|r| (r.process_id, r.produced_batches))
        .collect();
    if used != expected {
        return Err(ProductionProjectionError::State);
    }
    let actual: BTreeMap<_, _> = receipt
        .income
        .iter()
        .filter(|r| r.statement.equipment_wear_capitalized.micro_units() > 0)
        .map(|r| (r.account, r.statement.equipment_wear_capitalized))
        .collect();
    costs.retain(|_, v| v.micro_units() > 0);
    if costs != actual {
        return Err(ProductionProjectionError::State);
    }
    Ok(cohorts)
}
