//! Exact captured time policy, last-close partitions and idempotent debit ledger.

use super::accounting;
use super::Cursor;
use crate::{
    FinalDemandPrincipalId, HouseholdContributionReceipt, HouseholdContributionUse,
    HouseholdTimeAccounting, HouseholdTimeBook, HouseholdTimeReceipt, MaterialCircuitError, UnitId,
};
use std::result::Result as StdResult;

type Result<T> = StdResult<T, MaterialCircuitError>;

pub(super) fn append(out: &mut Vec<u8>, accounting: &HouseholdTimeAccounting) -> Result<()> {
    let HouseholdTimeAccounting::Modeled(book) = accounting else {
        out.push(0);
        return Ok(());
    };
    out.push(1);
    crate::household_time::validate_structure(book)?;
    super::append_rows(out, &book.receipts, append_receipt)?;
    super::append_rows(out, &book.contributions, |bytes, row| {
        bytes.extend_from_slice(&row.period.to_be_bytes());
        bytes.extend_from_slice(&row.contribution.use_id);
        bytes.extend_from_slice(&row.contribution.principal_id.as_bytes());
        bytes.extend_from_slice(&row.contribution.actor_id.to_be_bytes());
        bytes.extend_from_slice(&row.contribution.contributor_id.to_be_bytes());
        bytes.extend_from_slice(&row.contribution.hours.to_be_bytes());
    })?;
    Ok(())
}

fn append_receipt(out: &mut Vec<u8>, row: &HouseholdTimeReceipt) {
    out.extend_from_slice(&row.principal_id.as_bytes());
    out.extend_from_slice(&row.period.to_be_bytes());
    out.extend_from_slice(&row.labor_unit_id.as_bytes());
    for value in [
        row.endowment_hours,
        row.attended_hours,
        row.protected_hours,
        row.protected_unresolved_hours,
        row.unpaid_requested_hours,
        row.unpaid_allocated_hours,
        row.unpaid_unresolved_hours,
        row.contribution_available_hours,
    ] {
        out.extend_from_slice(&value.to_be_bytes());
    }
}

fn decode_receipt(cursor: &mut Cursor<'_>) -> Result<HouseholdTimeReceipt> {
    Ok(HouseholdTimeReceipt {
        principal_id: FinalDemandPrincipalId::from_bytes(cursor.array()?),
        period: cursor.u64()?,
        labor_unit_id: UnitId::from_bytes(cursor.array()?),
        endowment_hours: cursor.u64()?,
        attended_hours: cursor.u64()?,
        protected_hours: cursor.u64()?,
        protected_unresolved_hours: cursor.u64()?,
        unpaid_requested_hours: cursor.u64()?,
        unpaid_allocated_hours: cursor.u64()?,
        unpaid_unresolved_hours: cursor.u64()?,
        contribution_available_hours: cursor.u64()?,
    })
}

pub(super) fn decode(cursor: &mut Cursor<'_>) -> Result<HouseholdTimeAccounting> {
    match cursor.u8()? {
        0 => return Ok(HouseholdTimeAccounting::NotModeled),
        1 => {}
        _ => return Err(MaterialCircuitError::WireEnum),
    }
    let receipts = super::decode_rows(cursor, decode_receipt)?;
    let contributions = super::decode_rows(cursor, |c| {
        Ok(HouseholdContributionReceipt {
            period: c.u64()?,
            contribution: HouseholdContributionUse {
                use_id: c.array()?,
                principal_id: FinalDemandPrincipalId::from_bytes(c.array()?),
                actor_id: c.u64()?,
                contributor_id: c.u64()?,
                hours: c.u64()?,
            },
        })
    })?;
    accounting::ordered_rows(&receipts, |r| r.principal_id)?;
    accounting::ordered_rows(&contributions, |r| r.contribution.use_id)?;
    let book = HouseholdTimeBook {
        receipts,
        contributions,
    };
    crate::household_time::validate_structure(&book)?;
    Ok(HouseholdTimeAccounting::Modeled(book))
}
