//! Arrived materials enter bounded WIP and share the existing attendance residual.
use super::EquipmentCohortId;
use super::EquipmentDefinition;
use super::InstallationId;
use super::InstallationReceipt;
use super::InstalledEquipmentCohort;
use super::MaterialCircuitError;
use super::MaterialCircuitState;
use super::PendingInstallation;
use super::ProcessId;
use super::ProductiveEquipment;
use super::Result;
use crate::inventory::InventoryLedger;
use crate::valuation::CostClose;
use crate::{AccountId, EquipmentPosition, MaterialCatalog, SiteId, StaffingWorkSource, UnitId};
use babylon_kernel::currency::Currency;

use super::InstallationDecisionReceipt;
use crate::inventory;
use crate::GoodId;
use babylon_kernel::content_digest;
use std::collections::BTreeMap;
/// Stable installation principal for one process and start period.
#[must_use]
pub fn equipment_installation_id(period: u64, process: ProcessId) -> InstallationId {
    let mut b = b"babylon.equipment-installation.v1\0".to_vec();
    b.extend_from_slice(&period.to_be_bytes());
    b.extend_from_slice(&process.as_bytes());
    InstallationId::from_bytes(content_digest::sha256_of(&b))
}
fn material_requirements(
    e: &ProductiveEquipment,
    d: &EquipmentDefinition,
) -> Vec<(GoodId, UnitId, u64)> {
    let mut rows = vec![(d.equipment_good_id, d.equipment_unit_id, 1)];
    let lo = e
        .installation_inputs
        .partition_point(|r| r.definition_id < d.id);
    let hi = e
        .installation_inputs
        .partition_point(|r| r.definition_id <= d.id);
    rows.extend(
        e.installation_inputs[lo..hi]
            .iter()
            .map(|r| (r.good_id, r.unit_id, r.quantity_per_equipment_unit)),
    );
    rows
}
fn start_projects(
    state: &MaterialCircuitState,
    content: &ProductiveEquipment,
    position: &mut EquipmentPosition,
    inventory: &mut InventoryLedger,
    eligible: &mut InventoryLedger,
    costs: &mut CostClose,
) -> Result<InstallationStarts> {
    let period = state.period;
    let mut starts = BTreeMap::new();
    let mut decisions = content
        .installation_policies
        .iter()
        .map(|p| super::choice::decision(state, content, position, p))
        .collect::<Result<Vec<_>>>()?;
    for (policy, decision) in content.installation_policies.iter().zip(&mut decisions) {
        let (binding, d) = content.definition(policy.process_id)?;
        let materials = material_requirements(content, d);
        let units = materials.iter().fold(
            policy
                .maximum_started_units_per_period
                .min(decision.requested_units),
            |n, (good, unit, qty)| {
                n.min(
                    eligible
                        .get(&(binding.site_id, *good, *unit))
                        .copied()
                        .unwrap_or(0)
                        / qty,
                )
            },
        );
        decision.started_units = units;
        decision.validate()?;
        if units == 0 {
            continue;
        }
        if position.pending.len() >= crate::MAX_MATERIAL_CIRCUIT_ROWS {
            return Err(MaterialCircuitError::RowLimit);
        }
        let hours = units
            .checked_mul(d.installation_hours_per_unit)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        let id = equipment_installation_id(period, policy.process_id);
        let mut value = Currency::from_micro_units(0);
        for (good, unit, coefficient) in materials {
            let quantity = units
                .checked_mul(coefficient)
                .ok_or(MaterialCircuitError::Arithmetic)?;
            let key = (binding.site_id, good, unit);
            let available = inventory.get(&key).copied().unwrap_or(0);
            let cost = costs.input(
                (AccountId::Site(binding.site_id), good, unit),
                available,
                quantity,
            )?;
            inventory::debit_inventory(
                eligible,
                key,
                quantity,
                MaterialCircuitError::EquipmentInvariant,
            )?;
            inventory::debit_inventory(
                inventory,
                key,
                quantity,
                MaterialCircuitError::EquipmentInvariant,
            )?;
            value = value
                .checked_add(cost)
                .map_err(|_| MaterialCircuitError::Arithmetic)?;
        }
        costs.installation_start(id, binding.site_id, value)?;
        starts.insert(id, value);
        position.pending.push(PendingInstallation {
            id,
            process_id: policy.process_id,
            units,
            started_period: period,
            remaining_hours: hours,
        });
    }
    Ok(InstallationStarts {
        costs: starts,
        decisions,
    })
}
struct InstallationStarts {
    costs: BTreeMap<InstallationId, Currency>,
    decisions: Vec<InstallationDecisionReceipt>,
}
pub(crate) struct InstallationClose {
    pub work: Vec<InstallationReceipt>,
    pub decisions: Vec<InstallationDecisionReceipt>,
}
pub(crate) fn install(
    catalog: &MaterialCatalog,
    state: &mut MaterialCircuitState,
    costs: &mut CostClose,
) -> Result<InstallationClose> {
    let Some(content) = catalog.equipment_content() else {
        return Ok(InstallationClose {
            work: vec![],
            decisions: vec![],
        });
    };
    let mut position = std::mem::take(super::position_mut(state));
    position.cohorts.retain(|c| c.remaining_service_batches > 0);
    let period = state.period;
    let next = period
        .checked_add(1)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let mut eligible = super::choice::eligible_inventory(state)?;
    let mut inventory = inventory::take_inventory(state);
    let admission = start_projects(
        state,
        content,
        &mut position,
        &mut inventory,
        &mut eligible,
        costs,
    )?;
    let starts = admission.costs;
    position.pending.sort_by_key(|r| (r.process_id, r.id));
    let mut budgets: BTreeMap<_, _> = content
        .installation_policies
        .iter()
        .map(|p| (p.process_id, p.maximum_hours_per_period))
        .collect();
    let pending = std::mem::take(&mut position.pending);
    let mut receipts = Vec::with_capacity(pending.len());
    for mut p in pending {
        let (b, d) = content.definition(p.process_id)?;
        let site = b.site_id;
        let unit = d.installation_labor_unit_id;
        let labor = state
            .labor
            .binary_search_by_key(&(period, site, unit), |r| (r.period, r.site_id, r.unit_id))
            .map_err(|_| MaterialCircuitError::EquipmentInvariant)?;
        let budget = budgets
            .get_mut(&p.process_id)
            .ok_or(MaterialCircuitError::EquipmentInvariant)?;
        let used = p
            .remaining_hours
            .min(*budget)
            .min(state.labor[labor].available);
        let opening = costs.installation_carrying(p.id)?;
        let opening_hours = p.remaining_hours;
        let (wages, closing) = costs.installation_work(p.id, site, unit, used)?;
        p.remaining_hours -= used;
        *budget -= used;
        state.labor[labor].available -= used;
        let row = InstallationReceipt {
            period,
            id: p.id,
            process_id: p.process_id,
            site_id: site,
            units: p.units,
            started: starts.contains_key(&p.id),
            opening_hours,
            used_hours: used,
            remaining_hours: p.remaining_hours,
            usable_from_period: if p.remaining_hours == 0 { next } else { 0 },
            opening_carrying: if starts.contains_key(&p.id) {
                Currency::from_micro_units(0)
            } else {
                opening
            },
            materials_capitalized: starts
                .get(&p.id)
                .copied()
                .unwrap_or(Currency::from_micro_units(0)),
            wages_capitalized: wages,
            closing_carrying: closing,
        };
        row.validate()?;
        receipts.push(row);
        if p.remaining_hours == 0 {
            finish_project(&mut position, &p, d, next, costs)?;
        } else {
            position.pending.push(p);
        }
    }
    super::canonicalize_position(&mut position);
    *super::position_mut(state) = position;
    inventory::publish_inventory(state, inventory);
    receipts.sort_by_key(|r| (r.process_id, r.id));
    Ok(InstallationClose {
        work: receipts,
        decisions: admission.decisions,
    })
}
fn finish_project(
    position: &mut EquipmentPosition,
    project: &PendingInstallation,
    definition: &EquipmentDefinition,
    next: u64,
    costs: &mut CostClose,
) -> Result<()> {
    if position.cohorts.len() >= crate::MAX_MATERIAL_CIRCUIT_ROWS {
        return Err(MaterialCircuitError::RowLimit);
    }
    let life = project
        .units
        .checked_mul(definition.service_batches_per_unit)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let id = EquipmentCohortId::from_bytes(project.id.as_bytes());
    costs.installation_complete(project.id, id)?;
    position.cohorts.push(InstalledEquipmentCohort {
        id,
        process_id: project.process_id,
        units: project.units,
        remaining_service_batches: life,
        usable_from_period: next,
    });
    Ok(())
}

/// Installation requests survive zero productive capacity and do not consume it.
pub(crate) fn work_requests(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
) -> Result<Vec<(StaffingWorkSource, SiteId, UnitId, u64)>> {
    let Some(content) = catalog.equipment_content() else {
        return Ok(vec![]);
    };
    let position = super::position(state);
    let mut inventory = super::choice::eligible_inventory(state)?;
    let mut result = Vec::with_capacity(content.installation_policies.len());
    for p in &content.installation_policies {
        let (b, d) = content.definition(p.process_id)?;
        let lo = position
            .pending
            .partition_point(|r| r.process_id < p.process_id);
        let hi = position
            .pending
            .partition_point(|r| r.process_id <= p.process_id);
        let mut hours = position.pending[lo..hi].iter().try_fold(0_u64, |n, r| {
            n.checked_add(r.remaining_hours)
                .ok_or(MaterialCircuitError::Arithmetic)
        })?;
        let materials = material_requirements(content, d);
        let decision = super::choice::decision(state, content, position, p)?;
        let possible = materials.iter().fold(
            p.maximum_started_units_per_period
                .min(decision.requested_units),
            |n, (g, u, q)| n.min(inventory.get(&(b.site_id, *g, *u)).copied().unwrap_or(0) / q),
        );
        for (good, unit, coefficient) in materials {
            let quantity = possible
                .checked_mul(coefficient)
                .ok_or(MaterialCircuitError::Arithmetic)?;
            inventory::debit_inventory(
                &mut inventory,
                (b.site_id, good, unit),
                quantity,
                MaterialCircuitError::EquipmentInvariant,
            )?;
        }
        hours = hours
            .checked_add(
                possible
                    .checked_mul(d.installation_hours_per_unit)
                    .ok_or(MaterialCircuitError::Arithmetic)?,
            )
            .ok_or(MaterialCircuitError::Arithmetic)?;
        result.push((
            StaffingWorkSource::Installation(p.process_id),
            b.site_id,
            d.installation_labor_unit_id,
            hours.min(p.maximum_hours_per_period),
        ));
    }
    Ok(result)
}
