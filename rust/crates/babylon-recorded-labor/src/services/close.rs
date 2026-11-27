//! Performed service grants carry their producer's basis for this period only.
use crate::book::{Frame, Handed, Result};
use crate::model::{
    LaborDisposition, LaborNode, LaborReceiptFamily, ReceiptRef, RecordedLaborError,
};
use crate::production;
use crate::view::PeriodView;
use babylon_material_circuit::{
    AccountId, HouseholdWantReceipt, MaterialCatalog, OrderId, ServicePerformanceReceipt,
    ServiceStage,
};
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

/// Performed services of one stage pass to their buyers.
///
/// # Errors
/// A receipt that does not match the stock, or an arithmetic overflow: `RecordedLaborError`.
pub fn handoff(
    frame: &mut Frame,
    catalog: &MaterialCatalog,
    phase: ServiceStage,
    view: &PeriodView<'_>,
) -> Result<()> {
    let mismatch = RecordedLaborError::ReceiptMismatch("service output");
    let mut expected = BTreeMap::new();
    for (ordinal, row) in view.receipts.service_outputs.iter().enumerate() {
        if production::stage(catalog, row.good_id, row.unit_id)? != Some(phase) {
            continue;
        }
        let node = LaborNode::site(row.site_id, row.good_id, row.unit_id);
        if row.period != view.period
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
    for (ordinal, row) in view.receipts.service_performance.iter().enumerate() {
        if production::stage(catalog, row.good_id, row.unit_id)? != Some(phase) {
            continue;
        }
        row.validate()
            .map_err(|_| RecordedLaborError::ReceiptMismatch("service performance"))?;
        if row.period != view.period {
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
        frame.handed.push(Handed {
            receipt: ReceiptRef::new(LaborReceiptFamily::ServicePerformance, ordinal),
            from: source,
            to: target,
            quantity: row.performed_quantity,
            basis,
        });
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
    /// Performed beyond the need: the rows of wants, which the need's receipt does not count.
    wanted: u64,
}

/// The want a performance row is the purchase of: its order, household, good and unit.
fn wants_row<'a>(
    row: &ServicePerformanceReceipt,
    wants: &BTreeMap<OrderId, &'a HouseholdWantReceipt>,
) -> Option<&'a HouseholdWantReceipt> {
    wants.get(&row.order_id).copied().filter(|want| {
        row.buyer == AccountId::Household(want.principal_id)
            && (row.good_id, row.unit_id) == (want.good_id, want.unit_id)
    })
}

/// Storable production has already withdrawn its performed intermediate inputs.
/// Household needs consume their pooled service grants, then unused grants expire. A household's
/// want (what it bought beyond its need, by tier) is used before the need reads its own: its row is
/// left out of the need's totals, must be wholly used and must be what was bought, and its hours
/// leave the household with the need's.
///
/// # Errors
/// A receipt that does not match the stock, or an arithmetic overflow: `RecordedLaborError`.
pub fn finish(frame: &mut Frame, view: &PeriodView<'_>) -> Result<()> {
    let mismatch = RecordedLaborError::ReceiptMismatch("service use");
    let wants = view.bought_wants()?;
    let mut totals = BTreeMap::<LaborNode, GrantTotals>::new();
    for row in view.receipts.service_performance {
        let total = totals.entry(buyer(row)?).or_default();
        if let Some(want) = wants_row(row, &wants) {
            if row.used_quantity != row.performed_quantity
                || row.unused_quantity != 0
                || row.performed_quantity != want.bought_quantity
            {
                return Err(mismatch);
            }
            total.wanted = total
                .wanted
                .checked_add(row.performed_quantity)
                .ok_or(RecordedLaborError::Arithmetic)?;
            continue;
        }
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
    for (ordinal, row) in view.receipts.household_services.iter().enumerate() {
        let node = LaborNode::household(row.principal_id, row.good_id, row.unit_id);
        let total = totals.entry(node).or_default();
        if row.period != view.period
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
            LaborNode::HouseholdStock { .. } => total
                .performed
                .checked_add(total.wanted)
                .ok_or(RecordedLaborError::Arithmetic)?,
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
            view.receipts.household_services[ordinal].satisfied_quantity,
            ReceiptRef::new(LaborReceiptFamily::HouseholdServices, ordinal),
        )?;
    }
    for (ordinal, row) in view.receipts.service_performance.iter().enumerate() {
        let node = buyer(row)?;
        let reference = ReceiptRef::new(LaborReceiptFamily::ServicePerformance, ordinal);
        if matches!(row.buyer, AccountId::Household(_))
            && (!controlled.contains_key(&node) || wants_row(row, &wants).is_some())
        {
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
