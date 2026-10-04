//! Finite time evidence joins actual unique member attendance, including idle.

use std::collections::{BTreeMap, BTreeSet};

use babylon_material_circuit::{
    FinalDemandPrincipalId, HouseholdTimeReceipt, MemberLaborUseReceipt, UnitId,
};

use super::{MaterialWorldError, ReceiptCursor};

pub(super) const ROW_BYTES: usize = 136;

pub(super) fn validate_state(
    state: &babylon_material_circuit::MaterialCircuitState,
    rows: &[HouseholdTimeReceipt],
) -> Result<(), MaterialWorldError> {
    use babylon_material_circuit::{CircuitAccounting, HouseholdTimeAccounting};
    let captured = match &state.accounting {
        CircuitAccounting::Monetary(economy) => match &economy.household_time {
            HouseholdTimeAccounting::NotModeled => &[][..],
            HouseholdTimeAccounting::Modeled(book) => &book.receipts,
        },
        CircuitAccounting::PhysicalControl => &[][..],
    };
    if captured != rows {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}

pub(super) fn validate(
    rows: &[HouseholdTimeReceipt],
    attendance: &[MemberLaborUseReceipt],
    period: u64,
) -> Result<(), MaterialWorldError> {
    if !rows
        .windows(2)
        .all(|pair| pair[0].principal_id < pair[1].principal_id)
    {
        return Err(MaterialWorldError::Wire);
    }
    // Explicit fixed-time controls omit this family while retaining attendance.
    if rows.is_empty() {
        return Ok(());
    }
    let mut members = BTreeSet::new();
    let mut hours = BTreeMap::<_, u64>::new();
    for row in attendance {
        row.validate().map_err(|_| MaterialWorldError::Wire)?;
        if row.period != period || !members.insert(row.member_id) {
            return Err(MaterialWorldError::Wire);
        }
        let used = hours.entry((row.payee, row.unit_id)).or_default();
        *used = used
            .checked_add(row.attended_hours)
            .ok_or(MaterialWorldError::Arithmetic)?;
    }
    for row in rows {
        row.validate().map_err(|_| MaterialWorldError::Wire)?;
        if row.period != period
            || hours
                .remove(&(row.principal_id, row.labor_unit_id))
                .unwrap_or(0)
                != row.attended_hours
        {
            return Err(MaterialWorldError::Wire);
        }
    }
    if !hours.is_empty() {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}

pub(super) fn encode(
    rows: &[HouseholdTimeReceipt],
    period: u64,
    bytes: &mut Vec<u8>,
) -> Result<(), MaterialWorldError> {
    for row in rows {
        row.validate().map_err(|_| MaterialWorldError::Wire)?;
        if row.period != period {
            return Err(MaterialWorldError::Wire);
        }
        bytes.extend_from_slice(&row.principal_id.as_bytes());
        bytes.extend_from_slice(&row.period.to_be_bytes());
        bytes.extend_from_slice(&row.labor_unit_id.as_bytes());
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
            bytes.extend_from_slice(&value.to_be_bytes());
        }
    }
    Ok(())
}

pub(super) fn decode(
    cursor: &mut ReceiptCursor<'_>,
    period: u64,
) -> Result<HouseholdTimeReceipt, MaterialWorldError> {
    let row = HouseholdTimeReceipt {
        principal_id: FinalDemandPrincipalId::from_bytes(cursor.take()?),
        period: cursor.u64()?,
        labor_unit_id: UnitId::from_bytes(cursor.take()?),
        endowment_hours: cursor.u64()?,
        attended_hours: cursor.u64()?,
        protected_hours: cursor.u64()?,
        protected_unresolved_hours: cursor.u64()?,
        unpaid_requested_hours: cursor.u64()?,
        unpaid_allocated_hours: cursor.u64()?,
        unpaid_unresolved_hours: cursor.u64()?,
        contribution_available_hours: cursor.u64()?,
    };
    row.validate().map_err(|_| MaterialWorldError::Wire)?;
    if row.period != period {
        return Err(MaterialWorldError::Wire);
    }
    Ok(row)
}
