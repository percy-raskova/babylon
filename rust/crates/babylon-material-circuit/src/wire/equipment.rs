//! Authored equipment definitions and the separately encoded installed position.

use super::Cursor;
use crate::{
    EquipmentCohortId, EquipmentPosition, InstallationId, InstallationTarget,
    InstalledEquipmentCohort, MaterialCircuitError, PendingInstallation, ProcessId,
    ProductiveEquipment,
};

pub(super) fn append_content(
    out: &mut Vec<u8>,
    e: &ProductiveEquipment,
) -> Result<(), MaterialCircuitError> {
    super::append_rows(out, &e.definitions, |b, r| {
        b.extend_from_slice(&r.id.as_bytes());
        b.extend_from_slice(&r.equipment_good_id.as_bytes());
        b.extend_from_slice(&r.equipment_unit_id.as_bytes());
        b.extend_from_slice(&r.batches_per_unit_per_period.to_be_bytes());
        b.extend_from_slice(&r.service_batches_per_unit.to_be_bytes());
        b.extend_from_slice(&r.installation_labor_unit_id.as_bytes());
        b.extend_from_slice(&r.installation_hours_per_unit.to_be_bytes());
    })?;
    super::append_rows(out, &e.bindings, |b, r| {
        b.extend_from_slice(&r.process_id.as_bytes());
        b.extend_from_slice(&r.site_id.as_bytes());
        b.extend_from_slice(&r.definition_id.as_bytes());
    })?;
    super::append_rows(out, &e.installation_inputs, |b, r| {
        b.extend_from_slice(&r.definition_id.as_bytes());
        b.extend_from_slice(&r.good_id.as_bytes());
        b.extend_from_slice(&r.unit_id.as_bytes());
        b.extend_from_slice(&r.quantity_per_equipment_unit.to_be_bytes());
    })?;
    super::append_rows(out, &e.installation_policies, |b, r| {
        b.extend_from_slice(&r.process_id.as_bytes());
        match r.target {
            InstallationTarget::FixedUnits(units) => {
                b.push(1);
                b.extend_from_slice(&units.to_be_bytes());
            }
            InstallationTarget::ProductionPlan { replacement_units } => {
                b.push(2);
                b.extend_from_slice(&replacement_units.to_be_bytes());
            }
        }
        b.extend_from_slice(&r.maximum_started_units_per_period.to_be_bytes());
        b.extend_from_slice(&r.maximum_hours_per_period.to_be_bytes());
    })?;
    super::append_rows(out, &e.investment_policies, |b, r| {
        b.extend_from_slice(&r.process_id.as_bytes());
        b.extend_from_slice(&r.supplier_site_id.as_bytes());
        b.extend_from_slice(&r.replacement_target_units.to_be_bytes());
        b.extend_from_slice(&r.maximum_installed_units.to_be_bytes());
        b.extend_from_slice(&r.maximum_purchase_per_period.to_be_bytes());
        b.extend_from_slice(&r.expansion_earnings_fraction_bps.to_be_bytes());
        b.extend_from_slice(&r.cash_floor.micro_units().to_be_bytes());
    })?;
    Ok(())
}

pub(super) fn append_position(
    out: &mut Vec<u8>,
    position: &EquipmentPosition,
) -> Result<(), MaterialCircuitError> {
    super::append_rows(out, &position.cohorts, |b, r| {
        b.extend_from_slice(&r.id.as_bytes());
        b.extend_from_slice(&r.process_id.as_bytes());
        b.extend_from_slice(&r.units.to_be_bytes());
        b.extend_from_slice(&r.remaining_service_batches.to_be_bytes());
        b.extend_from_slice(&r.usable_from_period.to_be_bytes());
    })?;
    super::append_rows(out, &position.pending, |b, r| {
        b.extend_from_slice(&r.id.as_bytes());
        b.extend_from_slice(&r.process_id.as_bytes());
        b.extend_from_slice(&r.units.to_be_bytes());
        b.extend_from_slice(&r.started_period.to_be_bytes());
        b.extend_from_slice(&r.remaining_hours.to_be_bytes());
    })
}

pub(super) fn decode_position(
    c: &mut Cursor<'_>,
) -> Result<EquipmentPosition, MaterialCircuitError> {
    Ok(EquipmentPosition {
        cohorts: super::decode_rows(c, |b| {
            Ok(InstalledEquipmentCohort {
                id: EquipmentCohortId::from_bytes(b.array()?),
                process_id: ProcessId::from_bytes(b.array()?),
                units: b.u64()?,
                remaining_service_batches: b.u64()?,
                usable_from_period: b.u64()?,
            })
        })?,
        pending: super::decode_rows(c, |b| {
            Ok(PendingInstallation {
                id: InstallationId::from_bytes(b.array()?),
                process_id: ProcessId::from_bytes(b.array()?),
                units: b.u64()?,
                started_period: b.u64()?,
                remaining_hours: b.u64()?,
            })
        })?,
    })
}
