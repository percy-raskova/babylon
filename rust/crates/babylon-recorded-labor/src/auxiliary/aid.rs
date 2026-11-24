//! Physical household gifts and actual voluntary handling time.
use crate::book::{Frame, Result};
use crate::model::{
    LaborDisposition, LaborNode, LaborReceiptFamily, ReceiptRef, RecordedLaborError,
};
use crate::view::PeriodView;
use babylon_material_circuit::{
    AidFreightLot, AidOutcome, AidReceipt, AidTransport, CircuitAccounting, MaterialCatalog,
    MaterialCircuitState, OrderId,
};
use std::collections::BTreeMap;

fn lots(state: &MaterialCircuitState) -> BTreeMap<OrderId, &AidFreightLot> {
    match &state.accounting {
        CircuitAccounting::PhysicalControl => BTreeMap::new(),
        CircuitAccounting::Monetary(economy) => economy
            .aid
            .freight
            .iter()
            .map(|lot| (lot.commitment_id, lot))
            .collect(),
    }
}

fn lot_for<'a>(
    lots: &BTreeMap<OrderId, &'a AidFreightLot>,
    row: &AidReceipt,
) -> Result<&'a AidFreightLot> {
    let mismatch = RecordedLaborError::ReceiptMismatch("aid freight");
    let AidTransport::Routed { route_id, .. } = row.transport else {
        return Err(mismatch);
    };
    let lot = lots.get(&row.commitment_id).copied().ok_or(mismatch)?;
    if row.mandate_id != lot.mandate_id
        || row.dispatch_period != lot.dispatch_period
        || row.donor != lot.donor
        || row.recipient != lot.recipient
        || row.good_id != lot.good_id
        || row.unit_id != lot.unit_id
        || route_id != lot.route_id
    {
        return Err(mismatch);
    }
    Ok(lot)
}

/// Gifts in transit arrive or are lost.
///
/// # Errors
/// A receipt that does not match the stock, or an arithmetic overflow: `RecordedLaborError`.
pub fn aid_arrivals(frame: &mut Frame, view: &PeriodView<'_>) -> Result<()> {
    if view.receipts.aid.is_empty() {
        return Ok(());
    }
    let opening = lots(view.before);
    // The engine removes a stage loss before handing off the surviving portion.
    // Its receipt tape subsequently sorts by outcome and places Granted before Lost.
    for phase in [AidOutcome::Lost, AidOutcome::Granted] {
        for (ordinal, row) in view.receipts.aid.iter().enumerate().filter(|(_, r)| {
            r.outcome == phase && matches!(r.transport, AidTransport::Routed { .. })
        }) {
            let lot = lot_for(&opening, row)?;
            if row.dispatch_period >= view.period
                || row.period != view.period
                || lot.stage_arrival_period != view.period
                || row.quantity == 0
                || row.contribution_hours != 0
            {
                return Err(RecordedLaborError::ReceiptMismatch("aid arrival"));
            }
            let reference = ReceiptRef::new(LaborReceiptFamily::Aid, ordinal);
            let source = LaborNode::freight(lot.lot_id);
            if phase == AidOutcome::Lost {
                frame.release(
                    source,
                    LaborNode::sink(LaborDisposition::AidFreightLoss),
                    row.quantity,
                    reference,
                )?;
            } else {
                let destination = LaborNode::household(row.recipient, row.good_id, row.unit_id);
                frame.move_units(source, destination, row.quantity, reference)?;
            }
        }
    }
    Ok(())
}

/// Gifts leave the donors, with the donors' own hours posted to them.
///
/// # Errors
/// A receipt that does not match the stock, or an arithmetic overflow: `RecordedLaborError`.
pub fn aid_dispatch(
    frame: &mut Frame,
    catalog: &MaterialCatalog,
    view: &PeriodView<'_>,
) -> Result<()> {
    if view.receipts.aid.is_empty() {
        return Ok(());
    }
    let closing = lots(view.after);
    let mut sent: Vec<_> = view
        .receipts
        .aid
        .iter()
        .enumerate()
        .filter(|(_, row)| {
            matches!(
                (row.outcome, row.transport),
                (AidOutcome::Granted, AidTransport::Local)
                    | (AidOutcome::Dispatched, AidTransport::Routed { .. })
            )
        })
        .collect();
    // The native dispatch allocator applies all household debits/grants by mandate.
    // Restoring that order matters when multiple gifts draw from the same stock.
    sent.sort_unstable_by_key(|(_, row)| row.mandate_id);
    for (ordinal, row) in sent {
        let mismatch = RecordedLaborError::ReceiptMismatch("aid dispatch");
        let idx = catalog
            .aid_mandates
            .binary_search_by_key(&row.mandate_id, |m| m.id)
            .map_err(|_| mismatch)?;
        let mandate = &catalog.aid_mandates[idx];
        row.validate_against(mandate).map_err(|_| mismatch)?;
        if row.dispatch_period != view.period || row.period != view.period {
            return Err(mismatch);
        }
        let target = match row.transport {
            AidTransport::Local => LaborNode::household(row.recipient, row.good_id, row.unit_id),
            AidTransport::Routed { .. } => {
                let lot = lot_for(&closing, row)?;
                if lot.quantity != row.quantity || lot.stage_arrival_period <= view.period {
                    return Err(mismatch);
                }
                LaborNode::freight(lot.lot_id)
            }
        };
        let reference = ReceiptRef::new(LaborReceiptFamily::Aid, ordinal);
        let source = LaborNode::household(row.donor, row.good_id, row.unit_id);
        let goods = frame.take(source, row.quantity)?;
        frame.edge(source, target, row.quantity, goods, reference);
        let fulfillment = frame.direct(
            LaborNode::household_work(row.donor, mandate.labor_unit_id),
            target,
            row.contribution_hours,
            reference,
        )?;
        frame.credit(target, row.quantity, goods.add(fulfillment)?)?;
    }
    Ok(())
}
