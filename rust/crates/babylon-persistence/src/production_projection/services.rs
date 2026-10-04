//! Reconcile ephemeral service production, acquisition, use and expiry.
//! Services never enter a completed durable-stock account.
use super::{lifecycle, ProductionProjectionError};
use babylon_material_circuit::{
    AccountId, CommodityKind, GoodId, MaterialCircuitState, ProcessId, SiteId, UnitId,
};
use babylon_tick::material_world::MaterialTickReceipts;
use std::collections::{BTreeMap, BTreeSet};
type Result<T> = std::result::Result<T, ProductionProjectionError>;
type GrantKey = (AccountId, GoodId, UnitId);
type OutputKey = (SiteId, GoodId, UnitId);

pub(super) fn service_kinds(state: &MaterialCircuitState) -> BTreeSet<(GoodId, UnitId)> {
    state
        .commodities
        .iter()
        .filter(|r| matches!(r.kind, CommodityKind::PeriodService { .. }))
        .map(|r| (r.good_id, r.unit_id))
        .collect()
}
fn add<K: Ord>(map: &mut BTreeMap<K, u64>, key: K, n: u64) -> Result<()> {
    let value = map.entry(key).or_default();
    *value = value
        .checked_add(n)
        .ok_or(ProductionProjectionError::Arithmetic)?;
    Ok(())
}
fn nonzero<K: Ord>(map: BTreeMap<K, u64>) -> BTreeMap<K, u64> {
    map.into_iter().filter(|r| r.1 != 0).collect()
}

pub(super) fn validate(
    prior: &MaterialCircuitState,
    current: &MaterialCircuitState,
    receipt: &MaterialTickReceipts,
) -> Result<()> {
    if prior.commodities != current.commodities
        || prior.service_connections != current.service_connections
    {
        return Err(ProductionProjectionError::State);
    }
    let kinds = service_kinds(prior);
    if prior
        .inventory
        .iter()
        .chain(&current.inventory)
        .any(|r| kinds.contains(&(r.good_id, r.unit_id)))
    {
        return Err(ProductionProjectionError::State);
    }
    let production: BTreeMap<_, _> = receipt
        .production
        .iter()
        .map(|r| (r.process_id, r))
        .collect();
    if production.len() != receipt.production.len() {
        return Err(ProductionProjectionError::State);
    }
    let mut performed = BTreeMap::<OutputKey, u64>::new();
    let mut grants = BTreeMap::<GrantKey, u64>::new();
    let mut used = BTreeMap::<GrantKey, u64>::new();
    let mut seen = BTreeSet::new();
    for row in &receipt.service_performance {
        row.validate()
            .map_err(|_| ProductionProjectionError::State)?;
        if row.period != prior.period
            || !kinds.contains(&(row.good_id, row.unit_id))
            || !seen.insert(row.order_id)
        {
            return Err(ProductionProjectionError::State);
        }
        add(
            &mut performed,
            (row.provider_site_id, row.good_id, row.unit_id),
            row.performed_quantity,
        )?;
        add(
            &mut grants,
            (row.buyer, row.good_id, row.unit_id),
            row.performed_quantity,
        )?;
        add(
            &mut used,
            (row.buyer, row.good_id, row.unit_id),
            row.used_quantity,
        )?;
    }
    validate_outputs(prior, receipt, &production, &kinds, performed)?;
    let mut expected_use = recipe_use(prior, &production, &kinds)?;
    household_use(prior, receipt, &kinds, &grants, &mut expected_use)?;
    if nonzero(used) != nonzero(expected_use) {
        return Err(ProductionProjectionError::State);
    }
    Ok(())
}
fn validate_outputs(
    prior: &MaterialCircuitState,
    receipt: &MaterialTickReceipts,
    production: &BTreeMap<ProcessId, &babylon_material_circuit::ProductionReceipt>,
    kinds: &BTreeSet<(GoodId, UnitId)>,
    performed: BTreeMap<OutputKey, u64>,
) -> Result<()> {
    let mut expected: BTreeMap<_, _> = prior
        .process_outputs
        .iter()
        .filter(|r| kinds.contains(&(r.good_id, r.unit_id)))
        .map(|r| (r.process_id, r))
        .collect();
    let mut allocated = BTreeMap::new();
    for row in &receipt.service_outputs {
        row.validate()
            .map_err(|_| ProductionProjectionError::State)?;
        let output = expected
            .remove(&row.process_id)
            .ok_or(ProductionProjectionError::State)?;
        let batches = production
            .get(&row.process_id)
            .map_or(0, |r| r.produced_batches);
        if row.period != prior.period
            || (row.site_id, row.good_id, row.unit_id)
                != (output.site_id, output.good_id, output.unit_id)
            || batches.checked_mul(output.quantity_per_batch) != Some(row.produced_quantity)
        {
            return Err(ProductionProjectionError::State);
        }
        add(
            &mut allocated,
            (row.site_id, row.good_id, row.unit_id),
            row.allocated_quantity,
        )?;
    }
    if !expected.is_empty() || nonzero(allocated) != nonzero(performed) {
        return Err(ProductionProjectionError::State);
    }
    Ok(())
}
fn recipe_use(
    prior: &MaterialCircuitState,
    production: &BTreeMap<ProcessId, &babylon_material_circuit::ProductionReceipt>,
    kinds: &BTreeSet<(GoodId, UnitId)>,
) -> Result<BTreeMap<GrantKey, u64>> {
    let sites: BTreeMap<_, _> = prior
        .process_outputs
        .iter()
        .map(|r| (r.process_id, r.site_id))
        .collect();
    let mut result = BTreeMap::new();
    for input in &prior.input_coefficients {
        if !kinds.contains(&(input.good_id, input.unit_id)) {
            continue;
        }
        let site = *sites
            .get(&input.process_id)
            .ok_or(ProductionProjectionError::State)?;
        let used = production
            .get(&input.process_id)
            .map_or(0, |r| r.produced_batches)
            .checked_mul(input.quantity_per_batch)
            .ok_or(ProductionProjectionError::Arithmetic)?;
        add(
            &mut result,
            (AccountId::Site(site), input.good_id, input.unit_id),
            used,
        )?;
    }
    Ok(result)
}
fn household_use(
    prior: &MaterialCircuitState,
    receipt: &MaterialTickReceipts,
    kinds: &BTreeSet<(GoodId, UnitId)>,
    grants: &BTreeMap<GrantKey, u64>,
    used: &mut BTreeMap<GrantKey, u64>,
) -> Result<()> {
    let mut expected = BTreeMap::new();
    if let Some(r) = lifecycle::recurring(prior) {
        let households: BTreeMap<_, _> = r.households.iter().map(|r| (r.principal_id, r)).collect();
        for need in &r.household_needs {
            if !kinds.contains(&(need.good_id, need.unit_id)) {
                continue;
            }
            let cohort = households
                .get(&need.principal_id)
                .ok_or(ProductionProjectionError::State)?;
            let required = need
                .required_quantity(cohort)
                .map_err(|_| ProductionProjectionError::State)?;
            if expected
                .insert(
                    (
                        AccountId::Household(need.principal_id),
                        need.good_id,
                        need.unit_id,
                    ),
                    required,
                )
                .is_some()
            {
                return Err(ProductionProjectionError::State);
            }
        }
    }
    let mut controlled = BTreeSet::new();
    for row in &receipt.household_services {
        row.validate()
            .map_err(|_| ProductionProjectionError::State)?;
        let key = (
            AccountId::Household(row.principal_id),
            row.good_id,
            row.unit_id,
        );
        if expected.remove(&key) != Some(row.required_quantity)
            || row.period != prior.period
            || grants.get(&key).copied().unwrap_or(0) != row.performed_quantity
            || !controlled.insert(key)
        {
            return Err(ProductionProjectionError::State);
        }
        add(used, key, row.satisfied_quantity)?;
    }
    if !expected.is_empty() {
        return Err(ProductionProjectionError::State);
    }
    for (&key, &quantity) in grants {
        if matches!(key.0, AccountId::Household(_)) && !controlled.contains(&key) {
            add(used, key, quantity)?;
        }
    }
    Ok(())
}
