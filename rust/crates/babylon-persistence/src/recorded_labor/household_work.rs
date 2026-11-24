//! Household hours that leave the book without a good: observations of an agency and the organizer's
//! cash collection. Both read the view of one period.
use super::book::{Frame, Result};
use super::model::{LaborNode, ReceiptRef, RecordedLaborError};
use super::view::PeriodView;
use crate::recorded_labor::LaborDisposition;
use crate::recorded_labor::LaborReceiptFamily;
use babylon_material_circuit::{CircuitAccounting, HouseholdTimeAccounting};

pub(super) fn agency_observations(frame: &mut Frame, view: &PeriodView<'_>) -> Result<()> {
    for (ordinal, row) in view.receipts.agency.iter().enumerate() {
        let basis = frame.direct(
            LaborNode::household_work(row.principal_id, row.labor_unit_id),
            LaborNode::sink(LaborDisposition::AgencyObservation),
            row.hours,
            ReceiptRef::new(LaborReceiptFamily::AgencyPaid, ordinal),
        )?;
        frame.release_basis(basis)?;
    }
    Ok(())
}

/// The cash gift consumes an identified household contribution without creating a carried good.
pub(super) fn collections(frame: &mut Frame, view: &PeriodView<'_>) -> Result<()> {
    let mismatch = RecordedLaborError::ReceiptMismatch("collections");
    let row = match view.receipts.collections {
        [] => return Ok(()),
        [row] => row,
        _ => return Err(mismatch),
    };
    row.validate().map_err(|_| mismatch)?;
    if row.period != view.period {
        return Err(mismatch);
    }
    let CircuitAccounting::Monetary(e) = &view.after.accounting else {
        return Err(mismatch);
    };
    let HouseholdTimeAccounting::Modeled(book) = &e.household_time else {
        return Err(mismatch);
    };
    let Some(usage) = row.contribution_use() else {
        return Ok(());
    };
    let index = book
        .contributions
        .binary_search_by_key(&usage.use_id, |actual| actual.contribution.use_id)
        .map_err(|_| mismatch)?;
    let actual = &book.contributions[index];
    if actual.period != row.period || actual.contribution != usage {
        return Err(mismatch);
    }
    let basis = frame.direct(
        LaborNode::household_work(row.donor, row.labor_unit_id),
        LaborNode::sink(LaborDisposition::OrganizerCashCollection),
        usage.hours,
        ReceiptRef::new(LaborReceiptFamily::Collections, 0),
    )?;
    frame.release_basis(basis)
}
