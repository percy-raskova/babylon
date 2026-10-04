//! Exact captured time policy, last-close partitions and idempotent debit ledger.

use super::accounting::ordered_rows;
use super::{append_rows, decode_rows, Cursor};
use crate::{
    FinalDemandPrincipalId, GoodId, HouseholdContributionReceipt, HouseholdContributionUse,
    HouseholdNeedBasis, HouseholdTimeAccounting, HouseholdTimeBook, HouseholdTimeCommitment,
    HouseholdTimePolicy, HouseholdTimeReceipt, HouseholdUnmetTimeBurden, MaterialCircuitError,
    UnitId, MAX_MATERIAL_CIRCUIT_ROWS,
};

type Result<T> = std::result::Result<T, MaterialCircuitError>;

fn append_commitment(out: &mut Vec<u8>, row: &HouseholdTimeCommitment) {
    out.push(row.basis as u8);
    out.extend_from_slice(&row.hours_per_basis.to_be_bytes());
}

fn decode_commitment(cursor: &mut Cursor<'_>) -> Result<HouseholdTimeCommitment> {
    let basis = match cursor.u8()? {
        1 => HouseholdNeedBasis::Persons,
        2 => HouseholdNeedBasis::Households,
        _ => return Err(MaterialCircuitError::WireEnum),
    };
    Ok(HouseholdTimeCommitment {
        basis,
        hours_per_basis: cursor.u64()?,
    })
}

pub(super) fn append(out: &mut Vec<u8>, accounting: &HouseholdTimeAccounting) -> Result<()> {
    let HouseholdTimeAccounting::Modeled(book) = accounting else {
        out.push(0);
        return Ok(());
    };
    out.push(1);
    crate::household_time::validate_structure(book)?;
    if book.policies.len() > MAX_MATERIAL_CIRCUIT_ROWS {
        return Err(MaterialCircuitError::WireLimit);
    }
    out.extend_from_slice(
        &u32::try_from(book.policies.len())
            .map_err(|_| MaterialCircuitError::WireLimit)?
            .to_be_bytes(),
    );
    for row in &book.policies {
        out.extend_from_slice(&row.principal_id.as_bytes());
        out.extend_from_slice(&row.labor_unit_id.as_bytes());
        out.extend_from_slice(&row.eligible_persons.to_be_bytes());
        out.extend_from_slice(&row.hours_per_eligible_person.to_be_bytes());
        append_commitment(out, &row.protected);
        append_commitment(out, &row.routine_provisioning);
        append_rows(out, &row.unmet_burdens, |bytes, r| {
            bytes.extend_from_slice(&r.good_id.as_bytes());
            bytes.extend_from_slice(&r.unit_id.as_bytes());
            bytes.extend_from_slice(&r.hours_per_unmet_unit.to_be_bytes());
        })?;
    }
    append_rows(out, &book.receipts, append_receipt)?;
    append_rows(out, &book.contributions, |bytes, row| {
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
    let policies = decode_rows(cursor, |c| {
        let principal_id = FinalDemandPrincipalId::from_bytes(c.array()?);
        let labor_unit_id = UnitId::from_bytes(c.array()?);
        let eligible_persons = c.u64()?;
        let hours_per_eligible_person = c.u64()?;
        let protected = decode_commitment(c)?;
        let routine_provisioning = decode_commitment(c)?;
        let unmet_burdens = decode_rows(c, |b| {
            Ok(HouseholdUnmetTimeBurden {
                good_id: GoodId::from_bytes(b.array()?),
                unit_id: UnitId::from_bytes(b.array()?),
                hours_per_unmet_unit: b.u64()?,
            })
        })?;
        ordered_rows(&unmet_burdens, |r| (r.good_id, r.unit_id))?;
        Ok(HouseholdTimePolicy {
            principal_id,
            labor_unit_id,
            eligible_persons,
            hours_per_eligible_person,
            protected,
            routine_provisioning,
            unmet_burdens,
        })
    })?;
    let receipts = decode_rows(cursor, decode_receipt)?;
    let contributions = decode_rows(cursor, |c| {
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
    ordered_rows(&policies, |r| r.principal_id)?;
    ordered_rows(&receipts, |r| r.principal_id)?;
    ordered_rows(&contributions, |r| r.contribution.use_id)?;
    let book = HouseholdTimeBook {
        policies,
        receipts,
        contributions,
    };
    crate::household_time::validate_structure(&book)?;
    Ok(HouseholdTimeAccounting::Modeled(book))
}
