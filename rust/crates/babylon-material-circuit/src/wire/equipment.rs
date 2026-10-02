//! Complete current equipment supply; old state formats are refused.
use super::accounting::decode_currency;
use super::{append_rows, decode_rows, Cursor};
use crate::{
    EquipmentBinding, EquipmentCohortId, EquipmentDefinition, EquipmentDefinitionId, GoodId,
    InstallationId, InstallationInput, InstallationPolicy, InstallationTarget,
    InstalledEquipmentCohort, InvestmentPolicy, MaterialCircuitError, PendingInstallation,
    ProcessId, ProductiveEquipment, SiteId, UnitId,
};
pub(super) fn append(
    out: &mut Vec<u8>,
    e: &ProductiveEquipment,
) -> Result<(), MaterialCircuitError> {
    append_rows(out, &e.definitions, |b, r| {
        b.extend_from_slice(&r.id.as_bytes());
        b.extend_from_slice(&r.equipment_good_id.as_bytes());
        b.extend_from_slice(&r.equipment_unit_id.as_bytes());
        b.extend_from_slice(&r.batches_per_unit_per_period.to_be_bytes());
        b.extend_from_slice(&r.service_batches_per_unit.to_be_bytes());
        b.extend_from_slice(&r.installation_labor_unit_id.as_bytes());
        b.extend_from_slice(&r.installation_hours_per_unit.to_be_bytes());
    })?;
    append_rows(out, &e.bindings, |b, r| {
        b.extend_from_slice(&r.process_id.as_bytes());
        b.extend_from_slice(&r.site_id.as_bytes());
        b.extend_from_slice(&r.definition_id.as_bytes());
    })?;
    append_rows(out, &e.installation_inputs, |b, r| {
        b.extend_from_slice(&r.definition_id.as_bytes());
        b.extend_from_slice(&r.good_id.as_bytes());
        b.extend_from_slice(&r.unit_id.as_bytes());
        b.extend_from_slice(&r.quantity_per_equipment_unit.to_be_bytes());
    })?;
    append_rows(out, &e.cohorts, |b, r| {
        b.extend_from_slice(&r.id.as_bytes());
        b.extend_from_slice(&r.process_id.as_bytes());
        b.extend_from_slice(&r.units.to_be_bytes());
        b.extend_from_slice(&r.remaining_service_batches.to_be_bytes());
        b.extend_from_slice(&r.usable_from_period.to_be_bytes());
    })?;
    append_rows(out, &e.pending, |b, r| {
        b.extend_from_slice(&r.id.as_bytes());
        b.extend_from_slice(&r.process_id.as_bytes());
        b.extend_from_slice(&r.units.to_be_bytes());
        b.extend_from_slice(&r.started_period.to_be_bytes());
        b.extend_from_slice(&r.remaining_hours.to_be_bytes());
    })?;
    append_rows(out, &e.installation_policies, |b, r| {
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
    append_rows(out, &e.investment_policies, |b, r| {
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
pub(super) fn decode(c: &mut Cursor<'_>) -> Result<ProductiveEquipment, MaterialCircuitError> {
    Ok(ProductiveEquipment {
        definitions: decode_rows(c, |b| {
            Ok(EquipmentDefinition {
                id: EquipmentDefinitionId::from_bytes(b.array()?),
                equipment_good_id: GoodId::from_bytes(b.array()?),
                equipment_unit_id: UnitId::from_bytes(b.array()?),
                batches_per_unit_per_period: b.u64()?,
                service_batches_per_unit: b.u64()?,
                installation_labor_unit_id: UnitId::from_bytes(b.array()?),
                installation_hours_per_unit: b.u64()?,
            })
        })?,
        bindings: decode_rows(c, |b| {
            Ok(EquipmentBinding {
                process_id: ProcessId::from_bytes(b.array()?),
                site_id: SiteId::from_bytes(b.array()?),
                definition_id: EquipmentDefinitionId::from_bytes(b.array()?),
            })
        })?,
        installation_inputs: decode_rows(c, |b| {
            Ok(InstallationInput {
                definition_id: EquipmentDefinitionId::from_bytes(b.array()?),
                good_id: GoodId::from_bytes(b.array()?),
                unit_id: UnitId::from_bytes(b.array()?),
                quantity_per_equipment_unit: b.u64()?,
            })
        })?,
        cohorts: decode_rows(c, |b| {
            Ok(InstalledEquipmentCohort {
                id: EquipmentCohortId::from_bytes(b.array()?),
                process_id: ProcessId::from_bytes(b.array()?),
                units: b.u64()?,
                remaining_service_batches: b.u64()?,
                usable_from_period: b.u64()?,
            })
        })?,
        pending: decode_rows(c, |b| {
            Ok(PendingInstallation {
                id: InstallationId::from_bytes(b.array()?),
                process_id: ProcessId::from_bytes(b.array()?),
                units: b.u64()?,
                started_period: b.u64()?,
                remaining_hours: b.u64()?,
            })
        })?,
        installation_policies: decode_rows(c, |b| {
            Ok(InstallationPolicy {
                process_id: ProcessId::from_bytes(b.array()?),
                target: match b.u8()? {
                    1 => InstallationTarget::FixedUnits(b.u64()?),
                    2 => InstallationTarget::ProductionPlan {
                        replacement_units: b.u64()?,
                    },
                    _ => return Err(MaterialCircuitError::WireEnum),
                },
                maximum_started_units_per_period: b.u64()?,
                maximum_hours_per_period: b.u64()?,
            })
        })?,
        investment_policies: decode_rows(c, |b| {
            Ok(InvestmentPolicy {
                process_id: ProcessId::from_bytes(b.array()?),
                supplier_site_id: SiteId::from_bytes(b.array()?),
                replacement_target_units: b.u64()?,
                maximum_installed_units: b.u64()?,
                maximum_purchase_per_period: b.u64()?,
                expansion_earnings_fraction_bps: b.u16()?,
                cash_floor: decode_currency(b)?,
            })
        })?,
    })
}
