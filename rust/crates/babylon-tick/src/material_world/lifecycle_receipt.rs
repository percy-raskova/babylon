//! Conserved household population flows for a single authenticated period.
use super::{MaterialWorldError, ReceiptCursor};
use babylon_material_circuit::{
    CircuitAccounting, FinalDemandPrincipalId, HouseholdLifecycleReceipt, HouseholdTimeReceipt,
    MaterialCircuitState, ResidentAges, ResidentWorkforceAttrition, StaffingMemberBinding,
    StaffingMemberId, StaffingMemberReceipt, StaffingMemberState, StaffingPoolId,
};

use std::collections::BTreeMap;

pub(super) const WIDTH: usize = 176;

pub(super) fn validate_close(
    state: &MaterialCircuitState,
    rows: &[HouseholdLifecycleReceipt],
) -> Result<bool, MaterialWorldError> {
    let Some(book) = state.household_lifecycle() else {
        return if rows.is_empty() {
            Ok(false)
        } else {
            Err(MaterialWorldError::Wire)
        };
    };
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        return Err(MaterialWorldError::Wire);
    };
    let cohorts = &economy
        .recurring
        .as_ref()
        .ok_or(MaterialWorldError::Wire)?
        .households;
    if rows.is_empty() || rows.len() != book.positions.len() {
        return Err(MaterialWorldError::Wire);
    }
    for (row, position) in rows.iter().zip(&book.positions) {
        let index = cohorts
            .binary_search_by_key(&row.principal_id, |c| c.principal_id)
            .map_err(|_| MaterialWorldError::Wire)?;
        let cohort = &cohorts[index];
        if (row.opening, row.opening_households) != position.previous_opening()
            || row.principal_id != position.principal_id
            || row.closing != position.ages
            || row.closing_households != cohort.households
            || row
                .closing
                .persons()
                .map_err(|_| MaterialWorldError::Wire)?
                != cohort.persons
        {
            return Err(MaterialWorldError::Wire);
        }
    }
    Ok(true)
}

pub(super) fn validate_time_scope(
    rows: &[HouseholdLifecycleReceipt],
    time: &[HouseholdTimeReceipt],
) -> Result<(), MaterialWorldError> {
    if rows
        .windows(2)
        .any(|p| p[0].principal_id >= p[1].principal_id)
        || rows.iter().any(|r| {
            time.binary_search_by_key(&r.principal_id, |t| t.principal_id)
                .is_err()
        })
    {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}

fn append_ages(bytes: &mut Vec<u8>, ages: &ResidentAges) {
    for n in [
        ages.under_16,
        ages.age_16_17,
        ages.age_18_64,
        ages.age_65_plus,
    ] {
        bytes.extend_from_slice(&n.to_be_bytes());
    }
}

fn ages(cursor: &mut ReceiptCursor<'_>) -> Result<ResidentAges, MaterialWorldError> {
    Ok(ResidentAges {
        under_16: cursor.u64()?,
        age_16_17: cursor.u64()?,
        age_18_64: cursor.u64()?,
        age_65_plus: cursor.u64()?,
    })
}

pub(super) fn encode(
    rows: &[HouseholdLifecycleReceipt],
    period: u64,
    bytes: &mut Vec<u8>,
) -> Result<(), MaterialWorldError> {
    for row in rows {
        if row.period != period {
            return Err(MaterialWorldError::Wire);
        }
        row.validate().map_err(|_| MaterialWorldError::Wire)?;
        bytes.extend_from_slice(&row.principal_id.as_bytes());
        append_ages(bytes, &row.opening);
        append_ages(bytes, &row.closing);
        bytes.extend_from_slice(&row.births.to_be_bytes());
        append_ages(bytes, &row.deaths);
        for n in [
            row.reached_16,
            row.reached_18,
            row.reached_65,
            row.opening_households,
            row.closing_households,
        ] {
            bytes.extend_from_slice(&n.to_be_bytes());
        }
    }
    Ok(())
}

pub(super) fn decode(
    cursor: &mut ReceiptCursor<'_>,
    period: u64,
) -> Result<HouseholdLifecycleReceipt, MaterialWorldError> {
    let row = HouseholdLifecycleReceipt {
        period,
        principal_id: FinalDemandPrincipalId::from_bytes(cursor.take()?),
        opening: ages(cursor)?,
        closing: ages(cursor)?,
        births: cursor.u64()?,
        deaths: ages(cursor)?,
        reached_16: cursor.u64()?,
        reached_18: cursor.u64()?,
        reached_65: cursor.u64()?,
        opening_households: cursor.u64()?,
        closing_households: cursor.u64()?,
    };
    row.validate().map_err(|_| MaterialWorldError::Wire)?;
    Ok(row)
}

pub(super) const ATTRITION_WIDTH: usize = 128;

pub(super) fn encode_attrition(rows: &[ResidentWorkforceAttrition], bytes: &mut Vec<u8>) {
    for row in rows {
        bytes.extend_from_slice(&row.principal_id.as_bytes());
        bytes.extend_from_slice(&row.pool_id.as_bytes());
        bytes.extend_from_slice(&row.member_id.as_bytes());
        for n in [
            row.opening_employed,
            row.opening_reserve,
            row.employed_removed,
            row.reserve_removed,
        ] {
            bytes.extend_from_slice(&n.to_be_bytes());
        }
    }
}

pub(super) fn decode_attrition(
    cursor: &mut ReceiptCursor<'_>,
) -> Result<ResidentWorkforceAttrition, MaterialWorldError> {
    Ok(ResidentWorkforceAttrition {
        principal_id: FinalDemandPrincipalId::from_bytes(cursor.take()?),
        pool_id: StaffingPoolId::from_bytes(cursor.take()?),
        member_id: StaffingMemberId::from_bytes(cursor.take()?),
        opening_employed: cursor.u64()?,
        opening_reserve: cursor.u64()?,
        employed_removed: cursor.u64()?,
        reserve_removed: cursor.u64()?,
    })
}

pub(super) fn validate_workforce(
    households: &[HouseholdLifecycleReceipt],
    staffing: &[StaffingMemberReceipt],
    attrition: &[ResidentWorkforceAttrition],
) -> Result<(), MaterialWorldError> {
    if households.is_empty() {
        return if attrition.is_empty() {
            Ok(())
        } else {
            Err(MaterialWorldError::Wire)
        };
    }
    let changes: BTreeMap<_, _> = attrition.iter().map(|r| (r.member_id, r)).collect();
    let mut members = Vec::with_capacity(staffing.len());
    for member in staffing {
        let mut employed = member.opening_employed;
        let mut reserve = member.opening_reserve;
        if let Some(change) = changes.get(&member.member.member_id()) {
            employed = employed
                .checked_add(change.employed_removed)
                .ok_or(MaterialWorldError::Arithmetic)?;
            reserve = reserve
                .checked_add(change.reserve_removed)
                .ok_or(MaterialWorldError::Arithmetic)?;
        }
        let force = employed
            .checked_add(reserve)
            .ok_or(MaterialWorldError::Arithmetic)?;
        let initial = StaffingMemberBinding::from_living_force(
            member.member.member_id(),
            member.member.household_id(),
            member.member.residence(),
            force,
        );
        let state = StaffingMemberState::try_new(initial, employed, reserve)
            .map_err(|_| MaterialWorldError::Wire)?;
        members.push((member.pool_id, state));
    }
    let expected = babylon_material_circuit::reconcile_resident_workforce(households, &members)
        .map_err(|_| MaterialWorldError::Wire)?;
    if expected != attrition {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}
