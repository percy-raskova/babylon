//! Exact maintenance identities and completed accounts from authenticated registers.
use super::ProductionProjectionError;
use crate::{
    michigan_economy::digest_hex,
    michigan_material::MichiganMaterialCatalog,
    production_observation::{CompletedProductionMaintenance, ProductionMaintenanceAccount},
};
use babylon_material_circuit::{MaintenanceBinding, MaintenanceReceipt, MaterialCircuitState};
use babylon_tick::material_world::MaterialTickReceipts;
type Result<T> = std::result::Result<T, ProductionProjectionError>;

pub(super) fn project_maintenance(
    catalog: &MichiganMaterialCatalog,
    state: &MaterialCircuitState,
    opening: Option<&MaterialCircuitState>,
    receipt: Option<&MaterialTickReceipts>,
) -> Result<Option<ProductionMaintenanceAccount>> {
    let done = completed(state, opening, receipt)?;
    let Some(binding) = &state.maintenance_binding else {
        if catalog.maintenance().is_some() {
            return Err(ProductionProjectionError::Content);
        }
        return Ok(None);
    };
    let designed = catalog
        .maintenance()
        .ok_or(ProductionProjectionError::Content)?;
    let provider = catalog
        .sites()
        .iter()
        .find(|site| site.key == designed.provider_site_key)
        .ok_or(ProductionProjectionError::Content)?;
    let process = catalog
        .processes()
        .iter()
        .find(|process| process.key == designed.consumer_process_key)
        .ok_or(ProductionProjectionError::Content)?;
    let consumer = catalog
        .sites()
        .iter()
        .find(|site| site.key == process.site_key)
        .ok_or(ProductionProjectionError::Content)?;
    let spare = catalog
        .goods()
        .iter()
        .find(|good| good.key == designed.spare_good_key)
        .ok_or(ProductionProjectionError::Content)?;
    let output = state
        .process_outputs
        .iter()
        .find(|row| row.process_id == process.id())
        .ok_or(ProductionProjectionError::State)?;
    let good = catalog
        .goods()
        .iter()
        .find(|good| good.id() == output.good_id && good.unit_id() == output.unit_id)
        .ok_or(ProductionProjectionError::State)?;
    if binding.provider_site_id != provider.id()
        || binding.consumer_process_id != process.id()
        || output.site_id != consumer.id()
        || binding.spare_good_id != spare.id()
        || binding.spare_unit_id != spare.unit_id()
        || binding.spare_units_per_job != designed.spare_units_per_job
        || binding.labor_units_per_job != designed.labor_units_per_job
        || binding.enabled_batches_per_job != designed.enabled_batches_per_job
        || binding.maximum_jobs_per_period != designed.maximum_jobs_per_period
    {
        return Err(ProductionProjectionError::Content);
    }
    let service = state
        .maintenance_service
        .ok_or(ProductionProjectionError::State)?;
    service
        .available_batches
        .checked_mul(output.quantity_per_batch)
        .ok_or(ProductionProjectionError::Arithmetic)?;
    Ok(Some(ProductionMaintenanceAccount {
        provider_site_id: digest_hex(&provider.id().as_bytes()),
        consumer_site_id: digest_hex(&consumer.id().as_bytes()),
        consumer_process_id: digest_hex(&process.id().as_bytes()),
        spare_good_id: digest_hex(&spare.id().as_bytes()),
        spare_unit_id: digest_hex(&spare.unit_id().as_bytes()),
        spare_good: spare.label.clone(),
        spare_unit: spare.unit_key.clone(),
        labor_unit_id: digest_hex(&binding.labor_unit_id.as_bytes()),
        labor_unit: "labor-hours".into(),
        output_good_id: digest_hex(&good.id().as_bytes()),
        output_unit_id: digest_hex(&good.unit_id().as_bytes()),
        output_good: good.label.clone(),
        output_unit: good.unit_key.clone(),
        output_per_batch: output.quantity_per_batch,
        spare_units_per_job: binding.spare_units_per_job,
        labor_units_per_job: binding.labor_units_per_job,
        enabled_batches_per_job: binding.enabled_batches_per_job,
        maximum_jobs_per_period: binding.maximum_jobs_per_period,
        next_service_period: service.period,
        next_service_batches: service.available_batches,
        completed: done.map(completed_account),
    }))
}

/// Refuse omitted completed accounts and mismatched binding/period/quantity identities.
/// This checks receipt algebra; the circuit remains the only transition authority.
pub(super) fn completed<'a>(
    state: &MaterialCircuitState,
    opening: Option<&MaterialCircuitState>,
    receipt: Option<&'a MaterialTickReceipts>,
) -> Result<Option<&'a MaintenanceReceipt>> {
    let Some(binding) = &state.maintenance_binding else {
        if state.maintenance_service.is_some()
            || opening.is_some_and(|prior| prior.maintenance_binding.is_some())
            || receipt.is_some_and(|receipt| receipt.maintenance.is_some())
        {
            return Err(ProductionProjectionError::State);
        }
        return Ok(None);
    };
    let service = state
        .maintenance_service
        .ok_or(ProductionProjectionError::State)?;
    if service.period != state.period {
        return Err(ProductionProjectionError::State);
    }
    let (prior, receipt) = match (opening, receipt) {
        (None, None) if state.period == 1 => return Ok(None),
        (Some(prior), Some(receipt))
            if prior.period.checked_add(1) == Some(state.period)
                && receipt.resolve_tick == prior.period =>
        {
            (prior, receipt)
        }
        _ => return Err(ProductionProjectionError::History),
    };
    let done = receipt
        .maintenance
        .as_ref()
        .ok_or(ProductionProjectionError::History)?;
    let opening_service = prior
        .maintenance_service
        .ok_or(ProductionProjectionError::State)?;
    if prior.maintenance_binding.as_ref() != Some(binding)
        || &done.binding != binding
        || done.period != prior.period
        || opening_service.period != prior.period
        || done.opening_service_batches != opening_service.available_batches
        || done.next_service != service
    {
        return Err(ProductionProjectionError::State);
    }
    check_inputs(prior, receipt, binding, done)?;
    check_quantities(binding, done)?;
    Ok(Some(done))
}

fn check_inputs(
    prior: &MaterialCircuitState,
    receipt: &MaterialTickReceipts,
    binding: &MaintenanceBinding,
    done: &MaintenanceReceipt,
) -> Result<()> {
    let stocks = prior
        .inventory
        .iter()
        .filter(|row| {
            row.site_id == binding.provider_site_id
                && row.good_id == binding.spare_good_id
                && row.unit_id == binding.spare_unit_id
        })
        .collect::<Vec<_>>();
    let labor = prior
        .labor
        .iter()
        .filter(|row| {
            row.site_id == binding.provider_site_id
                && row.unit_id == binding.labor_unit_id
                && row.period == prior.period
        })
        .collect::<Vec<_>>();
    if stocks.len() > 1 || labor.len() > 1 {
        return Err(ProductionProjectionError::State);
    }
    let mut arrived = 0_u64;
    for row in &receipt.arrivals {
        let order = prior
            .orders
            .iter()
            .find(|order| order.order_id == row.order_id)
            .ok_or(ProductionProjectionError::State)?;
        if order.buyer_site_id == binding.provider_site_id
            && order.good_id == binding.spare_good_id
            && order.unit_id == binding.spare_unit_id
        {
            arrived = arrived
                .checked_add(row.quantity)
                .ok_or(ProductionProjectionError::Arithmetic)?;
        }
    }
    let production = receipt
        .production
        .iter()
        .filter(|row| row.process_id == binding.consumer_process_id)
        .collect::<Vec<_>>();
    if production.len() > 1
        || done.opening_spare_parts != stocks.first().map_or(0, |row| row.quantity)
        || done.arrived_spare_parts != arrived
        || done.available_labor_hours
            != maintenance_hours(
                prior,
                receipt,
                binding,
                labor.first().map_or(0, |row| row.available),
            )?
        || done.consumed_service_batches != production.first().map_or(0, |row| row.produced_batches)
    {
        return Err(ProductionProjectionError::State);
    }
    Ok(())
}

fn maintenance_hours(
    prior: &MaterialCircuitState,
    receipt: &MaterialTickReceipts,
    binding: &MaintenanceBinding,
    available: u64,
) -> Result<u64> {
    if matches!(
        prior.accounting,
        babylon_material_circuit::CircuitAccounting::PhysicalControl
    ) {
        return Ok(available);
    }
    let mut rows = receipt.labor_use.iter().filter(|row| {
        row.site_id == binding.provider_site_id && row.unit_id == binding.labor_unit_id
    });
    let row = rows.next().ok_or(ProductionProjectionError::State)?;
    if rows.next().is_some() || row.available_hours != available || row.funded_hours > available {
        return Err(ProductionProjectionError::State);
    }
    let mut productive = 0_u64;
    for work in receipt
        .production
        .iter()
        .filter(|work| work.site_id == binding.provider_site_id)
    {
        let coefficient = prior
            .labor_coefficients
            .iter()
            .find(|row| row.process_id == work.process_id)
            .ok_or(ProductionProjectionError::State)?;
        if coefficient.unit_id == binding.labor_unit_id {
            productive = work
                .produced_batches
                .checked_mul(coefficient.quantity_per_batch)
                .and_then(|hours| productive.checked_add(hours))
                .ok_or(ProductionProjectionError::Arithmetic)?;
        }
    }
    row.funded_hours
        .checked_sub(productive)
        .ok_or(ProductionProjectionError::State)
}

fn check_quantities(binding: &MaintenanceBinding, done: &MaintenanceReceipt) -> Result<()> {
    if binding.spare_units_per_job == 0
        || binding.labor_units_per_job == 0
        || binding.enabled_batches_per_job == 0
    {
        return Err(ProductionProjectionError::State);
    }
    let jobs = done.prospective_batches / binding.enabled_batches_per_job
        + u64::from(
            !done
                .prospective_batches
                .is_multiple_of(binding.enabled_batches_per_job),
        );
    let feasible = jobs
        .min(binding.maximum_jobs_per_period)
        .min(done.available_spare_parts / binding.spare_units_per_job)
        .min(done.available_labor_hours / binding.labor_units_per_job);
    if done.requested_jobs != jobs
        || done.completed_jobs != feasible
        || done
            .opening_spare_parts
            .checked_add(done.arrived_spare_parts)
            != Some(done.available_spare_parts)
        || done
            .consumed_service_batches
            .checked_add(done.expired_service_batches)
            != Some(done.opening_service_batches)
        || done.completed_jobs.checked_mul(binding.spare_units_per_job)
            != Some(done.consumed_spare_parts)
        || done.completed_jobs.checked_mul(binding.labor_units_per_job)
            != Some(done.consumed_labor_hours)
        || done
            .completed_jobs
            .checked_mul(binding.enabled_batches_per_job)
            != Some(done.next_service.available_batches)
    {
        return Err(ProductionProjectionError::State);
    }
    Ok(())
}

fn completed_account(done: &MaintenanceReceipt) -> CompletedProductionMaintenance {
    CompletedProductionMaintenance {
        period: done.period,
        opening_service_batches: done.opening_service_batches,
        consumed_service_batches: done.consumed_service_batches,
        expired_service_batches: done.expired_service_batches,
        prospective_batches: done.prospective_batches,
        requested_jobs: done.requested_jobs,
        opening_spare_parts: done.opening_spare_parts,
        arrived_spare_parts: done.arrived_spare_parts,
        available_spare_parts: done.available_spare_parts,
        available_labor_hours: done.available_labor_hours,
        completed_jobs: done.completed_jobs,
        consumed_spare_parts: done.consumed_spare_parts,
        consumed_labor_hours: done.consumed_labor_hours,
    }
}
