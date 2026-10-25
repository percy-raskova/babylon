//! Canonical immutable-catalog bytes; the digest travels with every state.

use crate::CapacitySupply;
use crate::MaintenanceBinding;
use crate::{
    AidMandate, AidTransport, HouseholdNeed, HouseholdTimeCommitment, HouseholdTimePolicy,
    MaterialCatalog, MaterialCircuitError, ServiceInputPolicy,
};

/// Canonical domain for one immutable material catalog.
pub const MATERIAL_CATALOG_DOMAIN_BYTES: &[u8] = b"babylon.material-catalog.v1";

pub(super) const CATALOG_SCHEMA_VERSION: u16 = 1;

fn append_commitment(out: &mut Vec<u8>, row: &HouseholdTimeCommitment) {
    out.push(row.basis as u8);
    out.extend_from_slice(&row.hours_per_basis.to_be_bytes());
}

pub(super) fn append_mandates(
    out: &mut Vec<u8>,
    rows: &[AidMandate],
) -> Result<(), MaterialCircuitError> {
    super::state::append_rows(out, rows, |b, r| {
        b.extend_from_slice(&r.id);
        b.extend_from_slice(&r.source_hash);
        for actor in [r.donor_actor, r.donor_contributor_id, r.recipient_actor] {
            b.extend_from_slice(&actor.to_be_bytes());
        }
        super::accounting::append_account(b, r.payer);
        b.extend_from_slice(&r.donor.as_bytes());
        b.extend_from_slice(&r.recipient.as_bytes());
        b.extend_from_slice(&r.good_id.as_bytes());
        b.extend_from_slice(&r.unit_id.as_bytes());
        b.extend_from_slice(&r.labor_unit_id.as_bytes());
        b.extend_from_slice(&r.hours_per_unit.to_be_bytes());
        b.extend_from_slice(&r.maximum_quantity.to_be_bytes());
        b.extend_from_slice(&r.cash_per_unit.micro_units().to_be_bytes());
        match r.transport {
            AidTransport::Local => b.push(1),
            AidTransport::Routed {
                route_id,
                from_node_id,
                to_node_id,
            } => {
                b.push(2);
                b.extend_from_slice(&route_id.as_bytes());
                b.extend_from_slice(&from_node_id.as_bytes());
                b.extend_from_slice(&to_node_id.as_bytes());
            }
        }
    })
}

pub(super) fn append_time_policies(
    out: &mut Vec<u8>,
    rows: &[HouseholdTimePolicy],
) -> Result<(), MaterialCircuitError> {
    if rows.len() > crate::MAX_MATERIAL_CIRCUIT_ROWS {
        return Err(MaterialCircuitError::WireLimit);
    }
    let count = u32::try_from(rows.len()).map_err(|_| MaterialCircuitError::WireLimit)?;
    out.extend_from_slice(&count.to_be_bytes());
    for row in rows {
        out.extend_from_slice(&row.principal_id.as_bytes());
        out.extend_from_slice(&row.labor_unit_id.as_bytes());
        out.extend_from_slice(&row.eligible_persons.to_be_bytes());
        out.extend_from_slice(&row.hours_per_eligible_person.to_be_bytes());
        append_commitment(out, &row.protected);
        append_commitment(out, &row.routine_provisioning);
        super::state::append_rows(out, &row.unmet_burdens, |bytes, r| {
            bytes.extend_from_slice(&r.good_id.as_bytes());
            bytes.extend_from_slice(&r.unit_id.as_bytes());
            bytes.extend_from_slice(&r.hours_per_unmet_unit.to_be_bytes());
        })?;
    }
    Ok(())
}

pub(super) fn append_service_inputs(
    out: &mut Vec<u8>,
    rows: &[ServiceInputPolicy],
) -> Result<(), MaterialCircuitError> {
    super::state::append_rows(out, rows, |b, r| {
        b.extend_from_slice(&r.buyer_site_id.as_bytes());
        b.extend_from_slice(&r.provider_site_id.as_bytes());
        b.extend_from_slice(&r.good_id.as_bytes());
        b.extend_from_slice(&r.unit_id.as_bytes());
        b.extend_from_slice(&r.quantity_per_period.to_be_bytes());
        b.extend_from_slice(&r.maximum_purchase.to_be_bytes());
        b.extend_from_slice(&r.cash_floor.micro_units().to_be_bytes());
    })
}

pub(super) fn append_needs(
    out: &mut Vec<u8>,
    rows: &[HouseholdNeed],
) -> Result<(), MaterialCircuitError> {
    super::state::append_bounded_rows(out, rows, crate::MAX_HOUSEHOLD_NEEDS, |b, row| {
        b.extend_from_slice(&row.principal_id.as_bytes());
        b.extend_from_slice(&row.good_id.as_bytes());
        b.extend_from_slice(&row.unit_id.as_bytes());
        b.push(row.basis as u8);
        b.extend_from_slice(&row.units_per_basis.to_be_bytes());
    })
}

fn append_maintenance(out: &mut Vec<u8>, binding: Option<&MaintenanceBinding>) {
    out.push(u8::from(binding.is_some()));
    if let Some(binding) = binding {
        out.extend_from_slice(&binding.provider_site_id.as_bytes());
        out.extend_from_slice(&binding.consumer_process_id.as_bytes());
        out.extend_from_slice(&binding.spare_good_id.as_bytes());
        out.extend_from_slice(&binding.spare_unit_id.as_bytes());
        out.extend_from_slice(&binding.labor_unit_id.as_bytes());
        out.extend_from_slice(&binding.spare_units_per_job.to_be_bytes());
        out.extend_from_slice(&binding.labor_units_per_job.to_be_bytes());
        out.extend_from_slice(&binding.enabled_batches_per_job.to_be_bytes());
        out.extend_from_slice(&binding.maximum_jobs_per_period.to_be_bytes());
    }
}

fn append_policy(out: &mut Vec<u8>, policy: &CapacitySupply) -> Result<(), MaterialCircuitError> {
    match policy {
        CapacitySupply::FiniteSchedule => out.push(0),
        CapacitySupply::Rolling(rows) => {
            out.push(1);
            match &rows.processes {
                crate::RollingProcessSupply::CapturedNameplate(installed) => {
                    out.push(0);
                    super::state::append_rows(out, installed, |b, r| {
                        b.extend_from_slice(&r.process_id.as_bytes());
                        b.extend_from_slice(&r.site_id.as_bytes());
                        b.extend_from_slice(&r.batches_per_period.to_be_bytes());
                    })?;
                }
                crate::RollingProcessSupply::Equipment(content) => {
                    out.push(1);
                    super::equipment::append_content(out, content)?;
                }
            }
            super::state::append_rows(out, &rows.shared, |b, row| {
                b.extend_from_slice(&row.corridor_id.as_bytes());
                b.extend_from_slice(&row.grams_per_period.to_be_bytes());
            })?;
        }
    }
    Ok(())
}

/// Canonical bytes for one validated catalog.
///
/// # Errors
/// Returns the first row-bound refusal.
pub(crate) fn bytes(catalog: &MaterialCatalog) -> Result<Vec<u8>, MaterialCircuitError> {
    let mut out = Vec::new();
    out.extend_from_slice(MATERIAL_CATALOG_DOMAIN_BYTES);
    out.push(0);
    out.extend_from_slice(&CATALOG_SCHEMA_VERSION.to_be_bytes());
    append_policy(&mut out, &catalog.capacity_policy)?;
    super::state::append_site_nodes(&mut out, &catalog.site_logistics_nodes)?;
    super::state::append_process_outputs(&mut out, &catalog.process_outputs)?;
    super::state::append_input_coefficients(&mut out, &catalog.input_coefficients)?;
    super::state::append_labor_coefficients(&mut out, &catalog.labor_coefficients)?;
    super::services::append_commodities(&mut out, &catalog.commodities)?;
    super::state::append_supplier_routes(&mut out, &catalog.supplier_routes)?;
    super::state::append_route_stages(&mut out, &catalog.route_stages)?;
    super::state::append_merchants(&mut out, &catalog.merchants)?;
    super::state::append_handling_coefficients(&mut out, &catalog.handling_coefficients)?;
    append_maintenance(&mut out, catalog.maintenance_binding.as_ref());
    append_mandates(&mut out, &catalog.aid_mandates)?;
    append_time_policies(&mut out, &catalog.household_time_policy)?;
    append_service_inputs(&mut out, &catalog.service_inputs)?;
    append_needs(&mut out, &catalog.household_needs)?;
    Ok(out)
}
