//! Accounting from validated adjacent registers and the completed receipt family.

use std::collections::{BTreeMap, BTreeSet};

use babylon_material_circuit::{MaterialCircuitState, ProcessId, SiteId, UnitId};
use babylon_tick::material_world::MaterialTickReceipts;

use super::ProductionProjectionError;
use crate::{
    michigan_economy::digest_hex, production_observation::CompletedProductionLabor,
    production_observation::ProductionLaborAccount,
};

mod attendance;

type Principal = (SiteId, UnitId);
type Budgets = BTreeMap<Principal, u64>;
type Totals = BTreeMap<Principal, LaborTotals>;

#[derive(Clone, Copy, Default)]
struct LaborTotals {
    planned: u64,
    used: u64,
    handling_needed: u64,
    handling_used: u64,
    maintenance_needed: u64,
    maintenance_used: u64,
}

pub(super) fn project_labor_accounts(
    state: &MaterialCircuitState,
    opening: Option<&MaterialCircuitState>,
    receipt: Option<&MaterialTickReceipts>,
) -> Result<Vec<ProductionLaborAccount>, ProductionProjectionError> {
    let maintenance = super::maintenance::completed(state, opening, receipt)?;
    let next = budgets(state)?;
    let (prior, totals) = match (opening, receipt) {
        (None, None) if state.period == 1 => (None, Totals::new()),
        (Some(prior), Some(receipt))
            if prior.period.checked_add(1) == Some(state.period)
                && receipt.resolve_tick == prior.period =>
        {
            if !super::outbound::same_rows(&prior.labor_coefficients, &state.labor_coefficients)
                || !super::outbound::same_rows(&prior.process_outputs, &state.process_outputs)
                || !super::outbound::same_rows(&prior.merchants, &state.merchants)
                || !super::outbound::same_rows(
                    &prior.handling_coefficients,
                    &state.handling_coefficients,
                )
            {
                return Err(ProductionProjectionError::State);
            }
            let available = budgets(prior)?;
            let totals = completed_totals(prior, receipt, maintenance, &available)?;
            (Some(available), totals)
        }
        _ => return Err(ProductionProjectionError::History),
    };
    let mut keys: BTreeSet<_> = next.keys().copied().collect();
    if let Some(prior) = &prior {
        keys.extend(prior.keys().copied());
    }
    keys.extend(totals.keys().copied());
    keys.into_iter()
        .map(|key| {
            let completed = prior
                .as_ref()
                .map(|prior| {
                    let available = prior.get(&key).copied().unwrap_or(0);
                    let account = totals.get(&key).copied().unwrap_or_default();
                    let used = account.used;
                    let unused = available
                        .checked_sub(used)
                        .ok_or(ProductionProjectionError::State)?;
                    Ok::<_, ProductionProjectionError>(CompletedProductionLabor {
                        period: state.period - 1,
                        opening: available,
                        planned: account.planned,
                        used,
                        unused,
                        handling_needed: account.handling_needed,
                        handling_used: account.handling_used,
                        maintenance_needed: account.maintenance_needed,
                        maintenance_used: account.maintenance_used,
                    })
                })
                .transpose()?;
            Ok(ProductionLaborAccount {
                site_id: digest_hex(&key.0.as_bytes()),
                unit_id: digest_hex(&key.1.as_bytes()),
                unit: "labor-hours".to_owned(),
                next_opening_period: state.period,
                next_opening_available: next.get(&key).copied().unwrap_or(0),
                completed,
            })
        })
        .collect()
}

/// Missing sparse capacity is zero; a duplicated principal is never summed.
fn budgets(state: &MaterialCircuitState) -> Result<Budgets, ProductionProjectionError> {
    let mut result = Budgets::new();
    for row in state.labor.iter().filter(|row| row.period == state.period) {
        if result
            .insert((row.site_id, row.unit_id), row.available)
            .is_some()
        {
            return Err(ProductionProjectionError::State);
        }
    }
    for (key, _) in process_labor(state)?.into_values() {
        result.entry(key).or_insert(0);
    }
    for merchant in &state.merchants {
        result
            .entry((merchant.site_id, merchant.labor_unit_id))
            .or_insert(0);
    }
    if let Some(binding) = &state.maintenance_binding {
        result
            .entry((binding.provider_site_id, binding.labor_unit_id))
            .or_insert(0);
    }
    Ok(result)
}

fn completed_totals(
    opening: &MaterialCircuitState,
    receipt: &MaterialTickReceipts,
    maintenance: Option<&babylon_material_circuit::MaintenanceReceipt>,
    available: &Budgets,
) -> Result<Totals, ProductionProjectionError> {
    let sources = process_labor(opening)?;
    let mut processes = BTreeMap::<ProcessId, (Principal, u64, u64)>::new();
    for plan in &opening.production_commitments {
        let (key, coefficient) = sources
            .get(&plan.process_id)
            .copied()
            .ok_or(ProductionProjectionError::State)?;
        if plan.period != opening.period
            || plan.site_id != key.0
            || processes
                .insert(plan.process_id, (key, coefficient, plan.planned_batches))
                .is_some()
        {
            return Err(ProductionProjectionError::State);
        }
    }
    let mut totals = Totals::new();
    for row in &receipt.production {
        let (key, coefficient, planned) = processes
            .remove(&row.process_id)
            .ok_or(ProductionProjectionError::State)?;
        if row.site_id != key.0 || row.planned_batches != planned || row.produced_batches > planned
        {
            return Err(ProductionProjectionError::State);
        }
        let account = totals.entry(key).or_default();
        account.planned = add_time(account.planned, planned, coefficient)?;
        account.used = add_time(account.used, row.produced_batches, coefficient)?;
    }
    if !processes.is_empty() {
        return Err(ProductionProjectionError::State);
    }
    add_handling_time(opening, receipt, &mut totals)?;
    if let Some(done) = maintenance {
        let account = totals
            .entry((done.binding.provider_site_id, done.binding.labor_unit_id))
            .or_default();
        account.maintenance_needed =
            add_time(0, done.requested_jobs, done.binding.labor_units_per_job)?;
        account.maintenance_used = done.consumed_labor_hours;
        account.used = add_time(account.used, done.consumed_labor_hours, 1)?;
    }
    attendance::reconcile(opening, receipt, &totals, available)?;
    Ok(totals)
}

fn add_handling_time(
    opening: &MaterialCircuitState,
    receipt: &MaterialTickReceipts,
    totals: &mut Totals,
) -> Result<(), ProductionProjectionError> {
    let merchants: BTreeMap<_, _> = opening
        .merchants
        .iter()
        .map(|row| (row.site_id, row.labor_unit_id))
        .collect();
    if merchants.len() != opening.merchants.len() {
        return Err(ProductionProjectionError::State);
    }
    let mut seen = BTreeSet::new();
    for row in &receipt.handling {
        let unit = merchants
            .get(&row.site_id)
            .ok_or(ProductionProjectionError::State)?;
        if !seen.insert(row.order)
            || row.handled_quantity > row.feasible_quantity
            || row.used_hours > row.needed_hours
        {
            return Err(ProductionProjectionError::State);
        }
        let account = totals.entry((row.site_id, *unit)).or_default();
        account.handling_needed = add_time(account.handling_needed, row.needed_hours, 1)?;
        account.handling_used = add_time(account.handling_used, row.used_hours, 1)?;
        account.used = add_time(account.used, row.used_hours, 1)?;
    }
    Ok(())
}

/// One checked immutable lookup replaces a coefficient scan for every process.
fn process_labor(
    state: &MaterialCircuitState,
) -> Result<BTreeMap<ProcessId, (Principal, u64)>, ProductionProjectionError> {
    let mut coefficients: BTreeMap<_, _> = state
        .labor_coefficients
        .iter()
        .map(|row| (row.process_id, (row.unit_id, row.quantity_per_batch)))
        .collect();
    if coefficients.len() != state.labor_coefficients.len() {
        return Err(ProductionProjectionError::State);
    }
    let mut result = BTreeMap::new();
    for row in &state.process_outputs {
        let (unit, quantity) = coefficients
            .remove(&row.process_id)
            .ok_or(ProductionProjectionError::State)?;
        if result
            .insert(row.process_id, ((row.site_id, unit), quantity))
            .is_some()
        {
            return Err(ProductionProjectionError::State);
        }
    }
    if !coefficients.is_empty() {
        return Err(ProductionProjectionError::State);
    }
    Ok(result)
}

fn add_time(total: u64, batches: u64, coefficient: u64) -> Result<u64, ProductionProjectionError> {
    coefficient
        .checked_mul(batches)
        .and_then(|time| total.checked_add(time))
        .ok_or(ProductionProjectionError::Arithmetic)
}

#[cfg(test)]
mod tests;
