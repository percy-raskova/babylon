//! One bounded repair dependency; whole jobs enable only the following period.

use crate::inventory::{debit_inventory, publish_inventory, take_inventory};
use crate::{
    MaintenanceBinding, MaintenanceReceipt, MaintenanceService, MaterialCircuitError,
    MaterialCircuitState, ProcessId, ProductionReceipt,
};

pub(crate) fn validate(state: &MaterialCircuitState) -> Result<(), MaterialCircuitError> {
    let (binding, service) = match (&state.maintenance_binding, state.maintenance_service) {
        (None, None) => return Ok(()),
        (Some(binding), Some(service)) => (binding, service),
        _ => return Err(MaterialCircuitError::MaintenanceInvariant),
    };
    if binding.spare_units_per_job == 0
        || binding.labor_units_per_job == 0
        || binding.enabled_batches_per_job == 0
        || binding.maximum_jobs_per_period == 0
        || binding.spare_unit_id == binding.labor_unit_id
        || service.period != state.period
    {
        return Err(MaterialCircuitError::MaintenanceInvariant);
    }
    let maximum = binding
        .maximum_jobs_per_period
        .checked_mul(binding.enabled_batches_per_job)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    if service.available_batches > maximum {
        return Err(MaterialCircuitError::MaintenanceInvariant);
    }
    let consumer = state
        .process_outputs
        .iter()
        .find(|row| row.process_id == binding.consumer_process_id)
        .ok_or(MaterialCircuitError::MaintenanceInvariant)?;
    let inputs: Vec<_> = state
        .input_coefficients
        .iter()
        .filter(|row| row.process_id == binding.consumer_process_id)
        .collect();
    // The bounded relation has disjoint resource principals, not implicit priority
    // over another process, merchant, or an outbound order for production inputs.
    if consumer.site_id == binding.provider_site_id
        || inputs.is_empty()
        || consumer.good_id != binding.spare_good_id
        || consumer.unit_id != binding.spare_unit_id
        || !state
            .site_logistics_nodes
            .iter()
            .any(|row| row.site_id == binding.provider_site_id)
        || state.process_outputs.iter().any(|row| {
            row.site_id == binding.provider_site_id
                || (row.site_id == consumer.site_id && row.process_id != consumer.process_id)
        })
        || state
            .merchants
            .iter()
            .any(|row| row.site_id == binding.provider_site_id)
        || inputs
            .iter()
            .any(|row| row.good_id == consumer.good_id && row.unit_id == consumer.unit_id)
        || state.orders.iter().any(|row| {
            row.supplier_site_id == binding.provider_site_id
                || (row.supplier_site_id == consumer.site_id
                    && inputs
                        .iter()
                        .any(|input| input.good_id == row.good_id && input.unit_id == row.unit_id))
        })
        || state.labor.iter().any(|row| {
            row.site_id == binding.provider_site_id && row.unit_id != binding.labor_unit_id
        })
    {
        return Err(MaterialCircuitError::MaintenanceInvariant);
    }
    Ok(())
}

pub(crate) fn limit_batches(
    state: &MaterialCircuitState,
    process: ProcessId,
    period: u64,
    batches: u64,
) -> Result<u64, MaterialCircuitError> {
    let Some(binding) = &state.maintenance_binding else {
        return Ok(batches);
    };
    if binding.consumer_process_id != process {
        return Ok(batches);
    }
    let service = state
        .maintenance_service
        .ok_or(MaterialCircuitError::MaintenanceInvariant)?;
    if service.period != period {
        return Err(MaterialCircuitError::MaintenanceInvariant);
    }
    Ok(batches.min(service.available_batches))
}

fn spare_parts(state: &MaterialCircuitState, binding: &MaintenanceBinding) -> u64 {
    state
        .inventory
        .iter()
        .find(|row| {
            row.site_id == binding.provider_site_id
                && row.good_id == binding.spare_good_id
                && row.unit_id == binding.spare_unit_id
        })
        .map_or(0, |row| row.quantity)
}

pub(crate) fn execute(
    opening: &MaterialCircuitState,
    state: &mut MaterialCircuitState,
    production: &[ProductionReceipt],
) -> Result<Option<MaintenanceReceipt>, MaterialCircuitError> {
    let Some(binding) = state.maintenance_binding.clone() else {
        return Ok(None);
    };
    let service = state
        .maintenance_service
        .ok_or(MaterialCircuitError::MaintenanceInvariant)?;
    let next_period = state
        .period
        .checked_add(1)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let consumed_service_batches = production
        .iter()
        .find(|row| row.process_id == binding.consumer_process_id)
        .map_or(0, |row| row.produced_batches);
    let expired_service_batches = service
        .available_batches
        .checked_sub(consumed_service_batches)
        .ok_or(MaterialCircuitError::MaintenanceInvariant)?;
    let prospective_batches =
        crate::production::prospective_batches(state, binding.consumer_process_id, next_period)?;
    let requested_jobs = prospective_batches.div_ceil(binding.enabled_batches_per_job);
    // Reject unrepresentable staffing demand even when current resources are zero.
    requested_jobs
        .checked_mul(binding.labor_units_per_job)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let opening_spare_parts = spare_parts(opening, &binding);
    let available_spare_parts = spare_parts(state, &binding);
    let arrived_spare_parts = available_spare_parts
        .checked_sub(opening_spare_parts)
        .ok_or(MaterialCircuitError::MaintenanceInvariant)?;
    let labor_index = state.labor.iter().position(|row| {
        row.site_id == binding.provider_site_id
            && row.unit_id == binding.labor_unit_id
            && row.period == state.period
    });
    let available_labor_hours = labor_index.map_or(0, |index| state.labor[index].available);
    let completed_jobs = requested_jobs
        .min(binding.maximum_jobs_per_period)
        .min(available_spare_parts / binding.spare_units_per_job)
        .min(available_labor_hours / binding.labor_units_per_job);
    let consumed_spare_parts = completed_jobs
        .checked_mul(binding.spare_units_per_job)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let consumed_labor_hours = completed_jobs
        .checked_mul(binding.labor_units_per_job)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let next_service = MaintenanceService {
        period: next_period,
        available_batches: completed_jobs
            .checked_mul(binding.enabled_batches_per_job)
            .ok_or(MaterialCircuitError::Arithmetic)?,
    };
    let mut inventory = take_inventory(state);
    debit_inventory(
        &mut inventory,
        (
            binding.provider_site_id,
            binding.spare_good_id,
            binding.spare_unit_id,
        ),
        consumed_spare_parts,
        MaterialCircuitError::MaintenanceInvariant,
    )?;
    publish_inventory(state, inventory);
    if let Some(index) = labor_index {
        state.labor[index].available = available_labor_hours
            .checked_sub(consumed_labor_hours)
            .ok_or(MaterialCircuitError::Arithmetic)?;
    }
    state.maintenance_service = Some(next_service);
    Ok(Some(MaintenanceReceipt {
        binding,
        period: state.period,
        opening_service_batches: service.available_batches,
        consumed_service_batches,
        expired_service_batches,
        prospective_batches,
        requested_jobs,
        opening_spare_parts,
        arrived_spare_parts,
        available_spare_parts,
        available_labor_hours,
        completed_jobs,
        consumed_spare_parts,
        consumed_labor_hours,
        next_service,
    }))
}
