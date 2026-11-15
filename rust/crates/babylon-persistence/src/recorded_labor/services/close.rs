//! Performed service grants carry their producer's basis for this period only.
use super::super::book::{Frame, Result};
use super::super::model::{LaborNode, ReceiptRef, RecordedLaborError};
use super::super::production;
use crate::recorded_labor::LaborDisposition;
use crate::recorded_labor::LaborReceiptFamily;
use babylon_material_circuit::{
    AccountId, MaterialCatalog, ServicePerformanceReceipt, ServiceStage,
};
use babylon_tick::material_world::MaterialTickReceipts;
use std::collections::BTreeMap;

fn buyer(row: &ServicePerformanceReceipt) -> Result<LaborNode> {
    match row.buyer {
        AccountId::Site(site) => Ok(LaborNode::site(site, row.good_id, row.unit_id)),
        AccountId::Household(household) => {
            Ok(LaborNode::household(household, row.good_id, row.unit_id))
        }
        _ => Err(RecordedLaborError::ReceiptMismatch("service buyer")),
    }
}

pub(in super::super) fn handoff(
    frame: &mut Frame,
    catalog: &MaterialCatalog,
    phase: ServiceStage,
    r: &MaterialTickReceipts,
) -> Result<()> {
    let mismatch = RecordedLaborError::ReceiptMismatch("service output");
    let mut expected = BTreeMap::new();
    for (ordinal, row) in r.service_outputs.iter().enumerate() {
        if production::stage(catalog, row.good_id, row.unit_id)? != Some(phase) {
            continue;
        }
        let node = LaborNode::site(row.site_id, row.good_id, row.unit_id);
        if row.period != r.resolve_tick
            || row.expired_quantity.checked_add(row.allocated_quantity)
                != Some(row.produced_quantity)
            || frame.quantity(node) != row.produced_quantity
            || expected.insert(node, (ordinal, row)).is_some()
        {
            return Err(mismatch);
        }
    }
    // Providers may also be buyers. Withdraw all seller grants and expire unassigned
    // production before returning any incoming service basis to that stage's stock.
    let mut grants = Vec::new();
    for (ordinal, row) in r.service_performance.iter().enumerate() {
        if production::stage(catalog, row.good_id, row.unit_id)? != Some(phase) {
            continue;
        }
        row.validate()
            .map_err(|_| RecordedLaborError::ReceiptMismatch("service performance"))?;
        if row.period != r.resolve_tick {
            return Err(RecordedLaborError::ReceiptMismatch("service performance"));
        }
        if row.performed_quantity == 0 {
            continue;
        }
        let source = LaborNode::site(row.provider_site_id, row.good_id, row.unit_id);
        if !expected.contains_key(&source) {
            return Err(mismatch);
        }
        let target = buyer(row)?;
        let basis = frame.take(source, row.performed_quantity)?;
        frame.edge(
            source,
            target,
            row.performed_quantity,
            basis,
            ReceiptRef::new(LaborReceiptFamily::ServicePerformance, ordinal),
        );
        grants.push((target, row.performed_quantity, basis));
    }
    for (source, (ordinal, row)) in expected {
        if frame.quantity(source) != row.expired_quantity {
            return Err(mismatch);
        }
        frame.release(
            source,
            LaborNode::sink(LaborDisposition::UnallocatedServiceExpiry),
            row.expired_quantity,
            ReceiptRef::new(LaborReceiptFamily::ServiceOutputs, ordinal),
        )?;
    }
    for (node, quantity, basis) in grants {
        frame.credit(node, quantity, basis)?;
    }
    Ok(())
}

#[derive(Default)]
struct GrantTotals {
    performed: u64,
    used: u64,
    unused: u64,
}

/// Storable production has already withdrawn its performed intermediate inputs.
/// Household needs consume their pooled service grants, then unused grants expire.
pub(in super::super) fn finish(frame: &mut Frame, r: &MaterialTickReceipts) -> Result<()> {
    let mismatch = RecordedLaborError::ReceiptMismatch("service use");
    let mut totals = BTreeMap::<LaborNode, GrantTotals>::new();
    for row in &r.service_performance {
        let total = totals.entry(buyer(row)?).or_default();
        total.performed = total
            .performed
            .checked_add(row.performed_quantity)
            .ok_or(RecordedLaborError::Arithmetic)?;
        total.used = total
            .used
            .checked_add(row.used_quantity)
            .ok_or(RecordedLaborError::Arithmetic)?;
        total.unused = total
            .unused
            .checked_add(row.unused_quantity)
            .ok_or(RecordedLaborError::Arithmetic)?;
    }
    let mut controlled = BTreeMap::new();
    for (ordinal, row) in r.household_services.iter().enumerate() {
        let node = LaborNode::household(row.principal_id, row.good_id, row.unit_id);
        let total = totals.entry(node).or_default();
        if row.period != r.resolve_tick
            || row.satisfied_quantity != total.used
            || row.unused_quantity != total.unused
            || row.performed_quantity != total.performed
            || controlled.insert(node, ordinal).is_some()
        {
            return Err(mismatch);
        }
    }
    for (&node, total) in &totals {
        let remaining = match node {
            LaborNode::HouseholdStock { .. } => total.performed,
            LaborNode::SiteStock { .. } => total.unused,
            _ => return Err(mismatch),
        };
        if frame.quantity(node) != remaining {
            return Err(mismatch);
        }
    }
    for (&node, &ordinal) in &controlled {
        frame.release(
            node,
            LaborNode::sink(LaborDisposition::HouseholdServiceUse),
            r.household_services[ordinal].satisfied_quantity,
            ReceiptRef::new(LaborReceiptFamily::HouseholdServices, ordinal),
        )?;
    }
    for (ordinal, row) in r.service_performance.iter().enumerate() {
        let node = buyer(row)?;
        let reference = ReceiptRef::new(LaborReceiptFamily::ServicePerformance, ordinal);
        if matches!(row.buyer, AccountId::Household(_)) && !controlled.contains_key(&node) {
            if row.unused_quantity != 0 {
                return Err(mismatch);
            }
            frame.release(
                node,
                LaborNode::sink(LaborDisposition::HouseholdServiceUse),
                row.used_quantity,
                reference,
            )?;
        }
        frame.release(
            node,
            LaborNode::sink(LaborDisposition::UnusedServiceExpiry),
            row.unused_quantity,
            reference,
        )?;
    }
    Ok(())
}
