//! Exact optional maintenance evidence in the current material receipt codec.

use super::{MaterialWorldError, ReceiptCursor};
use babylon_material_circuit::{
    GoodId, MaintenanceBinding, MaintenanceReceipt, MaintenanceService, ProcessId, SiteId, UnitId,
};

pub(super) const ROW_BYTES: usize = 5 * 32 + 19 * 8;

fn validate(row: &MaintenanceReceipt, period: u64) -> Result<(), MaterialWorldError> {
    let b = &row.binding;
    if b.spare_units_per_job == 0
        || b.labor_units_per_job == 0
        || b.enabled_batches_per_job == 0
        || b.maximum_jobs_per_period == 0
        || b.spare_unit_id == b.labor_unit_id
        || row.period != period
        || period.checked_add(1) != Some(row.next_service.period)
    {
        return Err(MaterialWorldError::Wire);
    }
    let maximum_service = b
        .maximum_jobs_per_period
        .checked_mul(b.enabled_batches_per_job)
        .ok_or(MaterialWorldError::Wire)?;
    let requested = (row.prospective_batches / b.enabled_batches_per_job)
        .checked_add(u64::from(
            !row.prospective_batches
                .is_multiple_of(b.enabled_batches_per_job),
        ))
        .ok_or(MaterialWorldError::Wire)?;
    let completed = requested
        .min(b.maximum_jobs_per_period)
        .min(row.available_spare_parts / b.spare_units_per_job)
        .min(row.available_labor_hours / b.labor_units_per_job);
    if row.opening_service_batches > maximum_service
        || row
            .consumed_service_batches
            .checked_add(row.expired_service_batches)
            != Some(row.opening_service_batches)
        || row.opening_spare_parts.checked_add(row.arrived_spare_parts)
            != Some(row.available_spare_parts)
        || row.requested_jobs != requested
        || requested.checked_mul(b.labor_units_per_job).is_none()
        || row.completed_jobs != completed
        || completed.checked_mul(b.spare_units_per_job) != Some(row.consumed_spare_parts)
        || completed.checked_mul(b.labor_units_per_job) != Some(row.consumed_labor_hours)
        || completed.checked_mul(b.enabled_batches_per_job)
            != Some(row.next_service.available_batches)
    {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}

pub(super) fn encode(
    row: &MaintenanceReceipt,
    period: u64,
    bytes: &mut Vec<u8>,
) -> Result<(), MaterialWorldError> {
    validate(row, period)?;
    let b = &row.binding;
    for id in [
        b.provider_site_id.as_bytes(),
        b.consumer_process_id.as_bytes(),
        b.spare_good_id.as_bytes(),
        b.spare_unit_id.as_bytes(),
        b.labor_unit_id.as_bytes(),
    ] {
        bytes.extend_from_slice(&id);
    }
    for value in [
        b.spare_units_per_job,
        b.labor_units_per_job,
        b.enabled_batches_per_job,
        b.maximum_jobs_per_period,
        row.period,
        row.opening_service_batches,
        row.consumed_service_batches,
        row.expired_service_batches,
        row.prospective_batches,
        row.requested_jobs,
        row.opening_spare_parts,
        row.arrived_spare_parts,
        row.available_spare_parts,
        row.available_labor_hours,
        row.completed_jobs,
        row.consumed_spare_parts,
        row.consumed_labor_hours,
        row.next_service.period,
        row.next_service.available_batches,
    ] {
        bytes.extend_from_slice(&value.to_be_bytes());
    }
    Ok(())
}

pub(super) fn decode(
    cursor: &mut ReceiptCursor<'_>,
    period: u64,
) -> Result<MaintenanceReceipt, MaterialWorldError> {
    let row = MaintenanceReceipt {
        binding: MaintenanceBinding {
            provider_site_id: SiteId::from_bytes(cursor.take()?),
            consumer_process_id: ProcessId::from_bytes(cursor.take()?),
            spare_good_id: GoodId::from_bytes(cursor.take()?),
            spare_unit_id: UnitId::from_bytes(cursor.take()?),
            labor_unit_id: UnitId::from_bytes(cursor.take()?),
            spare_units_per_job: cursor.u64()?,
            labor_units_per_job: cursor.u64()?,
            enabled_batches_per_job: cursor.u64()?,
            maximum_jobs_per_period: cursor.u64()?,
        },
        period: cursor.u64()?,
        opening_service_batches: cursor.u64()?,
        consumed_service_batches: cursor.u64()?,
        expired_service_batches: cursor.u64()?,
        prospective_batches: cursor.u64()?,
        requested_jobs: cursor.u64()?,
        opening_spare_parts: cursor.u64()?,
        arrived_spare_parts: cursor.u64()?,
        available_spare_parts: cursor.u64()?,
        available_labor_hours: cursor.u64()?,
        completed_jobs: cursor.u64()?,
        consumed_spare_parts: cursor.u64()?,
        consumed_labor_hours: cursor.u64()?,
        next_service: MaintenanceService {
            period: cursor.u64()?,
            available_batches: cursor.u64()?,
        },
    };
    validate(&row, period)?;
    Ok(row)
}
