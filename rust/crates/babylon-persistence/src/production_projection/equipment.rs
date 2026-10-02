//! Asset receipts reconcile physical instruments and work in progress with adjacent books.
//! This validates actual movements without choosing installation or investment policy.
mod installation;
mod wear;
use super::ProductionProjectionError;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    CapacitySupply, CircuitAccounting, EquipmentAssetId, EquipmentBinding, EquipmentDefinition,
    EquipmentDefinitionId, GoodId, MaterialCircuitState, ProcessId, ProductiveEquipment,
    RollingProcessSupply, SiteId, UnitId,
};
use babylon_tick::material_world::MaterialTickReceipts;
use std::collections::BTreeMap;
type Result<T> = std::result::Result<T, ProductionProjectionError>;
type AssetBook = BTreeMap<EquipmentAssetId, (SiteId, Currency)>;
type MaterialKey = (SiteId, GoodId, UnitId);
type LaborKey = (SiteId, UnitId);
#[derive(Default)]
pub(super) struct EquipmentFacts {
    pub materials: BTreeMap<MaterialKey, u64>,
    /// Hours awaiting work, then actual hours used; never a fresh labor allocation.
    pub labor: BTreeMap<LaborKey, (u64, u64)>,
}
pub(super) fn get(state: &MaterialCircuitState) -> Option<&ProductiveEquipment> {
    match &state.capacity_supply {
        CapacitySupply::Rolling(s) => match &s.processes {
            RollingProcessSupply::Equipment(e) => Some(e),
            RollingProcessSupply::CapturedNameplate(_) => None,
        },
        CapacitySupply::FiniteSchedule => None,
    }
}
pub(super) struct Definitions<'a> {
    processes: BTreeMap<ProcessId, (&'a EquipmentBinding, &'a EquipmentDefinition)>,
    materials: BTreeMap<EquipmentDefinitionId, Vec<(GoodId, UnitId, u64)>>,
}
impl<'a> Definitions<'a> {
    pub(super) fn new(e: &'a ProductiveEquipment) -> Result<Self> {
        let definitions: BTreeMap<_, _> = e.definitions.iter().map(|r| (r.id, r)).collect();
        let mut processes = BTreeMap::new();
        let mut materials = BTreeMap::new();
        for d in &e.definitions {
            materials.insert(d.id, vec![(d.equipment_good_id, d.equipment_unit_id, 1)]);
        }
        for r in &e.installation_inputs {
            materials
                .get_mut(&r.definition_id)
                .ok_or(ProductionProjectionError::State)?
                .push((r.good_id, r.unit_id, r.quantity_per_equipment_unit));
        }
        for b in &e.bindings {
            let d = *definitions
                .get(&b.definition_id)
                .ok_or(ProductionProjectionError::State)?;
            if processes.insert(b.process_id, (b, d)).is_some() {
                return Err(ProductionProjectionError::State);
            }
        }
        if definitions.len() != e.definitions.len() {
            return Err(ProductionProjectionError::State);
        }
        Ok(Self {
            processes,
            materials,
        })
    }
    pub(super) fn get(
        &self,
        process: ProcessId,
    ) -> Result<(&EquipmentBinding, &EquipmentDefinition)> {
        self.processes
            .get(&process)
            .copied()
            .ok_or(ProductionProjectionError::State)
    }
}
pub(super) fn validate(
    prior: &MaterialCircuitState,
    current: &MaterialCircuitState,
    receipt: &MaterialTickReceipts,
) -> Result<EquipmentFacts> {
    let (before, after) = match (get(prior), get(current)) {
        (None, None)
            if receipt.installation.is_empty()
                && receipt.equipment_wear.is_empty()
                && receipt.investment.is_empty() =>
        {
            return Ok(EquipmentFacts::default())
        }
        (Some(a), Some(b)) => (a, b),
        _ => return Err(ProductionProjectionError::State),
    };
    if prior.period.checked_add(1) != Some(current.period)
        || receipt.resolve_tick != prior.period
        || before.definitions != after.definitions
        || before.bindings != after.bindings
        || before.installation_inputs != after.installation_inputs
        || before.installation_policies != after.installation_policies
        || before.investment_policies != after.investment_policies
    {
        return Err(ProductionProjectionError::State);
    }
    let definitions = Definitions::new(before)?;
    let mut assets = asset_book(prior)?;
    let mut cohorts = wear::reconcile(prior, before, receipt, &definitions, &mut assets)?;
    let (pending, facts) = installation::reconcile(
        prior,
        before,
        receipt,
        &definitions,
        &mut assets,
        &mut cohorts,
    )?;
    let closing_cohorts: BTreeMap<_, _> = after.cohorts.iter().map(|r| (r.id, r.clone())).collect();
    let closing_pending: BTreeMap<_, _> = after.pending.iter().map(|r| (r.id, r.clone())).collect();
    if closing_cohorts.len() != after.cohorts.len()
        || closing_pending.len() != after.pending.len()
        || cohorts != closing_cohorts
        || pending != closing_pending
        || assets != asset_book(current)?
    {
        return Err(ProductionProjectionError::State);
    }
    validate_capacity(current)?;
    Ok(facts)
}
fn asset_book(state: &MaterialCircuitState) -> Result<AssetBook> {
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        return Err(ProductionProjectionError::State);
    };
    let mut values = BTreeMap::new();
    for r in e.costs.snapshot().equipment {
        if r.amount.micro_units() < 0 || values.insert(r.asset, (r.owner, r.amount)).is_some() {
            return Err(ProductionProjectionError::State);
        }
    }
    Ok(values)
}
fn add<K: Ord>(values: &mut BTreeMap<K, u64>, key: K, quantity: u64) -> Result<()> {
    let total = values.entry(key).or_default();
    *total = total
        .checked_add(quantity)
        .ok_or(ProductionProjectionError::Arithmetic)?;
    Ok(())
}
fn add_cost<K: Ord>(values: &mut BTreeMap<K, Currency>, key: K, amount: Currency) -> Result<()> {
    let total = values.entry(key).or_insert(Currency::from_micro_units(0));
    *total = total
        .checked_add(amount)
        .map_err(|_| ProductionProjectionError::Arithmetic)?;
    Ok(())
}

fn validate_capacity(state: &MaterialCircuitState) -> Result<()> {
    let CapacitySupply::Rolling(supply) = &state.capacity_supply else {
        return Err(ProductionProjectionError::State);
    };
    let expected: BTreeMap<_, _> = supply
        .processes
        .capacities(state.period)
        .map_err(|_| ProductionProjectionError::State)?
        .into_iter()
        .map(|r| ((r.site_id, r.process_id), r.batches_per_period))
        .collect();
    let actual: BTreeMap<_, _> = state
        .capacities
        .iter()
        .map(|r| ((r.site_id, r.process_id), r.available_batches))
        .collect();
    if actual.len() != state.capacities.len()
        || expected != actual
        || state.capacities.iter().any(|r| r.period != state.period)
    {
        return Err(ProductionProjectionError::State);
    }
    Ok(())
}
