//! Canonical immutable-catalog bytes; the digest travels with every state.

use crate::AdjustmentRule;
use crate::MaintenanceBinding;
use crate::{
    AidMandate, AidTransport, HouseholdNeed, HouseholdTimeCommitment, HouseholdTimePolicy,
    HouseholdWant, MaterialCatalogDefinition, MaterialCircuitError, ServiceInputPolicy,
};
use crate::{CapacitySupply, CompanyConditionOrder};

/// Canonical domain for one immutable material catalog.
pub const MATERIAL_CATALOG_DOMAIN_BYTES: &[u8] = b"babylon.material-catalog.v2";

pub(super) const CATALOG_SCHEMA_VERSION: u16 = 2;

/// A catalog with a market policy writes this version, then the version it would write without one.
const MARKET_CATALOG_SCHEMA_VERSION: u16 = 6;

/// A market policy with household wants writes this version where 6 is written.
const MARKET_TIERS_CATALOG_SCHEMA_VERSION: u16 = 7;

/// A market policy that plans from spare money writes this version first, then every byte the same
/// catalog writes without it.
const SPARE_MONEY_CATALOG_SCHEMA_VERSION: u16 = 8;

/// A market policy that asks for adjustments writes this version first, then its rules, then every byte the
/// same catalog writes without them.
const ADJUSTMENT_CATALOG_SCHEMA_VERSION: u16 = 9;

/// A catalog with a handling row of more than one unit writes this version right after the domain bytes, then
/// every byte the same catalog writes without it, then a tail with each handling row's units.
const HANDLING_BLOCK_CATALOG_SCHEMA_VERSION: u16 = 10;

/// A catalog with a want at a scale other than 10,000 writes this version right after the domain bytes (after
/// version 10 where both are written), then every byte the same catalog writes without it, then a tail with each
/// want row's scale (after the handling blocks' tail where both are written).
const WANT_SCALE_CATALOG_SCHEMA_VERSION: u16 = 11;

fn has_scaled_wants(catalog: &MaterialCatalogDefinition) -> bool {
    catalog.market_clearing.as_ref().is_some_and(|policy| {
        policy
            .household_wants
            .iter()
            .any(|row| row.scale_bps != crate::WANT_SCALE_ONE_BPS)
    })
}

fn append_want_scales(
    out: &mut Vec<u8>,
    catalog: &MaterialCatalogDefinition,
) -> Result<(), MaterialCircuitError> {
    let rows = catalog
        .market_clearing
        .as_ref()
        .map_or(&[][..], |policy| policy.household_wants.as_slice());
    let count = u32::try_from(rows.len()).map_err(|_| MaterialCircuitError::WireLimit)?;
    out.extend_from_slice(&count.to_be_bytes());
    for row in rows {
        out.extend_from_slice(&row.scale_bps.to_be_bytes());
    }
    Ok(())
}

fn append_adjustments(
    out: &mut Vec<u8>,
    rules: &[AdjustmentRule],
) -> Result<(), MaterialCircuitError> {
    if rules.is_empty() {
        return Ok(());
    }
    out.extend_from_slice(&ADJUSTMENT_CATALOG_SCHEMA_VERSION.to_be_bytes());
    let count = u16::try_from(rules.len()).map_err(|_| MaterialCircuitError::WireLimit)?;
    out.extend_from_slice(&count.to_be_bytes());
    for rule in rules {
        out.push(rule.tag());
        if let AdjustmentRule::OwnerRestart { outlay_periods } = rule {
            out.extend_from_slice(&outlay_periods.to_be_bytes());
        }
    }
    Ok(())
}

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
        b.extend_from_slice(&r.maximum_cash.micro_units().to_be_bytes());
        b.extend_from_slice(&r.initial_quantity.to_be_bytes());
        b.extend_from_slice(&r.initial_cash.micro_units().to_be_bytes());
        b.extend_from_slice(&[r.food_receiving as u8, r.cash_receiving as u8]);
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

fn append_wants(out: &mut Vec<u8>, rows: &[HouseholdWant]) -> Result<(), MaterialCircuitError> {
    super::state::append_bounded_rows(out, rows, crate::MAX_HOUSEHOLD_WANTS, |b, row| {
        b.extend_from_slice(&row.principal_id.as_bytes());
        b.push(row.tier as u8);
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
/// The versions of the tails written right after the domain bytes: handling blocks (10), then want scales (11).
/// Each says whether its tail follows the body.
fn append_tail_versions(out: &mut Vec<u8>, catalog: &MaterialCatalogDefinition) -> (bool, bool) {
    let blocks = catalog
        .handling_coefficients
        .iter()
        .any(|row| row.units != 1);
    if blocks {
        out.extend_from_slice(&HANDLING_BLOCK_CATALOG_SCHEMA_VERSION.to_be_bytes());
    }
    let scales = has_scaled_wants(catalog);
    if scales {
        out.extend_from_slice(&WANT_SCALE_CATALOG_SCHEMA_VERSION.to_be_bytes());
    }
    (blocks, scales)
}

pub(crate) fn bytes(catalog: &MaterialCatalogDefinition) -> Result<Vec<u8>, MaterialCircuitError> {
    let mut out = Vec::new();
    out.extend_from_slice(MATERIAL_CATALOG_DOMAIN_BYTES);
    out.push(0);
    let (blocks, scales) = append_tail_versions(&mut out, catalog);
    if let Some(policy) = &catalog.market_clearing {
        append_adjustments(&mut out, &policy.adjustments)?;
    }
    if catalog
        .market_clearing
        .as_ref()
        .is_some_and(|policy| policy.plans_from_spare_money)
    {
        out.extend_from_slice(&SPARE_MONEY_CATALOG_SCHEMA_VERSION.to_be_bytes());
    }
    let version = match catalog
        .company_portfolios
        .map(|policy| policy.condition_order)
    {
        Some(CompanyConditionOrder::FirstApplicable) => 5,
        Some(CompanyConditionOrder::HighDemandBeforeSpare) => 4,
        None if catalog.company_payouts.is_empty() => CATALOG_SCHEMA_VERSION,
        None => 3,
    };
    if let Some(policy) = &catalog.market_clearing {
        let market = if policy.household_wants.is_empty() {
            MARKET_CATALOG_SCHEMA_VERSION
        } else {
            MARKET_TIERS_CATALOG_SCHEMA_VERSION
        };
        out.extend_from_slice(&market.to_be_bytes());
    }
    out.extend_from_slice(&version.to_be_bytes());
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
    if !catalog.company_payouts.is_empty() {
        let count = u32::try_from(catalog.company_payouts.len())
            .map_err(|_| MaterialCircuitError::WireLimit)?;
        out.extend_from_slice(&count.to_be_bytes());
        for company in &catalog.company_payouts {
            out.extend_from_slice(&company.company.as_bytes());
            out.extend_from_slice(&company.earnings_bps.to_be_bytes());
            let count =
                u32::try_from(company.claims.len()).map_err(|_| MaterialCircuitError::WireLimit)?;
            out.extend_from_slice(&count.to_be_bytes());
            for &(owner, weight) in &company.claims {
                super::accounting::append_account(&mut out, owner);
                out.extend_from_slice(&weight.to_be_bytes());
            }
        }
    }
    if let Some(policy) = &catalog.company_portfolios {
        for row in policy.rows {
            for weight in row {
                out.extend_from_slice(&weight.to_be_bytes());
            }
        }
        out.extend_from_slice(&policy.high_utilization_bps.to_be_bytes());
        out.push(policy.history_periods);
        out.extend_from_slice(&policy.modest_expansion_bps.to_be_bytes());
    }
    if let Some(policy) = &catalog.market_clearing {
        let count = u32::try_from(policy.paying_order.len())
            .map_err(|_| MaterialCircuitError::WireLimit)?;
        out.extend_from_slice(&count.to_be_bytes());
        for (good, unit) in &policy.paying_order {
            out.extend_from_slice(&good.as_bytes());
            out.extend_from_slice(&unit.as_bytes());
        }
        if !policy.household_wants.is_empty() {
            append_wants(&mut out, &policy.household_wants)?;
        }
    }
    if blocks {
        let count = u32::try_from(catalog.handling_coefficients.len())
            .map_err(|_| MaterialCircuitError::WireLimit)?;
        out.extend_from_slice(&count.to_be_bytes());
        for row in &catalog.handling_coefficients {
            out.extend_from_slice(&row.units.to_be_bytes());
        }
    }
    if scales {
        append_want_scales(&mut out, catalog)?;
    }
    Ok(out)
}
