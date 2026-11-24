//! Member attendance and household time are physical records independent of their cash treatment.
use super::model::{RecordedAttendance, RecordedHouseholdTime};
use super::{LaborId, LaborReceiptFamily, ReceiptRef, RecordedLaborError, Result};
use crate::production_projection;
use babylon_material_circuit::{LaborCompensation, MaterialCatalog, MaterialCircuitState};
use babylon_tick::material_world::MaterialTickReceipts;

use super::RecordedCompensation;

pub(super) fn report(
    catalog: &MaterialCatalog,
    before: &MaterialCircuitState,
    after: &MaterialCircuitState,
    r: &MaterialTickReceipts,
) -> Result<Vec<RecordedAttendance>> {
    production_projection::validate_completed_labor(catalog, before, after, r)
        .map_err(|_| RecordedLaborError::InvalidAttendance)?;
    Ok(r.member_labor_use
        .iter()
        .enumerate()
        .map(|(ordinal, row)| RecordedAttendance {
            member: LaborId(row.member_id.as_bytes()),
            site: LaborId(row.site_id.as_bytes()),
            unit: LaborId(row.unit_id.as_bytes()),
            compensation: match row.compensation {
                LaborCompensation::Wage(_) => RecordedCompensation::Wage,
                LaborCompensation::WorkingOwner => RecordedCompensation::WorkingOwner,
                LaborCompensation::UnpaidFamily => RecordedCompensation::UnpaidFamily,
            },
            attended_hours: row.attended_hours,
            production_hours: row.production_hours,
            maintenance_hours: row.maintenance_hours,
            handling_hours: row.handling_hours,
            installation_hours: row.installation_hours,
            idle_hours: row.idle_hours,
            receipt: ReceiptRef::new(LaborReceiptFamily::MemberLaborUse, ordinal),
        })
        .collect())
}

pub(super) fn household_time(r: &MaterialTickReceipts) -> Result<Vec<RecordedHouseholdTime>> {
    r.household_time
        .iter()
        .enumerate()
        .map(|(ordinal, row)| {
            row.validate()
                .map_err(|_| RecordedLaborError::ReceiptMismatch("household_time"))?;
            if row.period != r.resolve_tick {
                return Err(RecordedLaborError::ReceiptMismatch("household_time"));
            }
            Ok(RecordedHouseholdTime {
                household: LaborId(row.principal_id.as_bytes()),
                unit: LaborId(row.labor_unit_id.as_bytes()),
                endowment_hours: row.endowment_hours,
                attended_hours: row.attended_hours,
                protected_hours: row.protected_hours,
                protected_unresolved_hours: row.protected_unresolved_hours,
                unpaid_requested_hours: row.unpaid_requested_hours,
                unpaid_allocated_hours: row.unpaid_allocated_hours,
                unpaid_unresolved_hours: row.unpaid_unresolved_hours,
                contribution_available_hours: row.contribution_available_hours,
                receipt: ReceiptRef::new(LaborReceiptFamily::HouseholdTime, ordinal),
            })
        })
        .collect()
}
