//! Canonical evidence for one actually paid agency attendance shift.
use babylon_kernel::currency::Currency;
use babylon_material_circuit::AccountId;
use babylon_material_circuit::AgencyAttendanceOutcome;
use babylon_material_circuit::AgencyObservationFundingReceipt;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_material_circuit::HouseholdTimeReceipt;
use babylon_material_circuit::IncomeReceipt;
use babylon_material_circuit::MoneyLocation;
use babylon_material_circuit::MoneyTransferPurpose;
use babylon_material_circuit::MoneyTransferReceipt;
use babylon_material_circuit::OrganizationAccountId;
use babylon_material_circuit::ShiftId;
use babylon_material_circuit::UnitId;
use babylon_material_circuit::WageAccrualReceipt;
use babylon_material_circuit::MAX_AGENCY_ATTENDANCE_PER_PERIOD;

use super::MaterialWorldError;
use super::ReceiptCursor;

pub(super) const ROW_BYTES: usize = 192;

/// A paid agency shift joined to its actual household time, accrual and payment.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AgencyPaidReceipt {
    pub intent_id: [u8; 32],
    pub shift_id: ShiftId,
    pub agency: OrganizationAccountId,
    pub principal_id: FinalDemandPrincipalId,
    pub labor_unit_id: UnitId,
    pub period: u64,
    pub hours: u64,
    pub wage: Currency,
}

pub(super) fn from_funding(
    rows: &[AgencyObservationFundingReceipt],
) -> Result<Vec<AgencyPaidReceipt>, MaterialWorldError> {
    if rows.len() > MAX_AGENCY_ATTENDANCE_PER_PERIOD {
        return Err(MaterialWorldError::Wire);
    }
    let mut paid = Vec::new();
    for row in rows {
        let input = &row.input;
        if row.outcome != AgencyAttendanceOutcome::Paid {
            if row.paid.micro_units() != 0 || row.attended_hours != 0 || row.attendance.is_some() {
                return Err(MaterialWorldError::Wire);
            }
            continue;
        }
        let attendance = row.attendance.as_ref().ok_or(MaterialWorldError::Wire)?;
        if attendance.intent_id != input.intent_id
            || attendance.shift_id != input.shift_id
            || attendance.principal_id != input.principal_id
            || attendance.labor_unit_id != input.labor_unit_id
            || attendance.period != input.due_period
            || attendance.hours != input.hours
            || row.attended_hours != input.hours
            || row.shortfall_hours != 0
            || row.requested != row.paid
            || row.reserved != row.paid
            || row.cancelled.micro_units() != 0
            || row.shortfall.micro_units() != 0
            || input
                .hourly_rate
                .micro_units()
                .checked_mul(i128::from(input.hours))
                != Some(row.paid.micro_units())
        {
            return Err(MaterialWorldError::Wire);
        }
        paid.push(AgencyPaidReceipt {
            intent_id: input.intent_id,
            shift_id: input.shift_id,
            agency: input.agency,
            principal_id: input.principal_id,
            labor_unit_id: input.labor_unit_id,
            period: input.due_period,
            hours: input.hours,
            wage: row.paid,
        });
    }
    Ok(paid)
}

pub(super) fn validate_nonpaid(
    rows: &[AgencyObservationFundingReceipt],
    wages: &[WageAccrualReceipt],
    transfers: &[MoneyTransferReceipt],
    time: &[HouseholdTimeReceipt],
    period: u64,
) -> Result<(), MaterialWorldError> {
    for row in rows
        .iter()
        .filter(|row| row.outcome != AgencyAttendanceOutcome::Paid)
    {
        let input = &row.input;
        let requested = input
            .hourly_rate
            .micro_units()
            .checked_mul(i128::from(input.hours))
            .ok_or(MaterialWorldError::Arithmetic)?;
        if input.intent_id == [0; 32]
            || input.due_period != period
            || input.hours == 0
            || input.hourly_rate.micro_units() <= 0
            || requested != row.requested.micro_units()
            || input.shift_id != babylon_material_circuit::agency_shift_id(period, input.intent_id)
            || row.paid.micro_units() != 0
            || row.attended_hours != 0
            || row.shortfall_hours != input.hours
            || row.attendance.is_some()
            || wages.iter().any(|w| w.shift == input.shift_id)
            || transfers
                .iter()
                .any(|t| t.purpose == MoneyTransferPurpose::WagePayment(input.shift_id))
        {
            return Err(MaterialWorldError::Wire);
        }
        let reservations: Vec<_> = transfers
            .iter()
            .filter(|t| t.purpose == MoneyTransferPurpose::ShiftReservation(input.shift_id))
            .collect();
        let cancellations: Vec<_> = transfers
            .iter()
            .filter(|t| t.purpose == MoneyTransferPurpose::ShiftCancellation(input.shift_id))
            .collect();
        match row.outcome {
            AgencyAttendanceOutcome::NoFunds => {
                if row.reserved.micro_units() != 0
                    || row.cancelled.micro_units() != 0
                    || row.shortfall.micro_units() <= 0
                    || row.shortfall.micro_units() > requested
                    || !reservations.is_empty()
                    || !cancellations.is_empty()
                {
                    return Err(MaterialWorldError::Wire);
                }
            }
            AgencyAttendanceOutcome::InsufficientTime => {
                let household = time
                    .iter()
                    .find(|t| {
                        t.principal_id == input.principal_id
                            && t.labor_unit_id == input.labor_unit_id
                    })
                    .ok_or(MaterialWorldError::Wire)?;
                if row.reserved != row.requested
                    || row.cancelled != row.requested
                    || row.shortfall.micro_units() != 0
                    || reservations.len() != 1
                    || cancellations.len() != 1
                    || !matches!(
                        (
                            transfers.iter().position(|t| t.purpose == MoneyTransferPurpose::ShiftReservation(input.shift_id)),
                            transfers.iter().position(|t| t.purpose == MoneyTransferPurpose::ShiftCancellation(input.shift_id)),
                        ),
                        (Some(reservation), Some(cancellation)) if reservation < cancellation
                    )
                    || (household.protected_unresolved_hours == 0
                        && household.unpaid_unresolved_hours == 0
                        && household.contribution_available_hours >= input.hours)
                    || reservations[0].debit.location
                        != MoneyLocation::Cash(AccountId::Organization(input.agency))
                    || reservations[0].credit.location
                        != MoneyLocation::PayrollReserve(input.shift_id)
                    || cancellations[0].debit.location
                        != MoneyLocation::PayrollReserve(input.shift_id)
                    || cancellations[0].credit.location
                        != MoneyLocation::Cash(AccountId::Organization(input.agency))
                    || reservations[0].credit.delta != row.requested
                    || cancellations[0].credit.delta != row.requested
                    || reservations[0].debit.delta.micro_units().checked_neg() != Some(requested)
                    || cancellations[0].debit.delta.micro_units().checked_neg() != Some(requested)
                {
                    return Err(MaterialWorldError::Wire);
                }
            }
            AgencyAttendanceOutcome::Paid => unreachable!("paid rows are filtered"),
        }
    }
    Ok(())
}

// A cancelled organization shift has no paid-agency row, but its two actual
// postings still retain the reservation identity and chronological order.
pub(super) fn validate_cancellations(
    transfers: &[MoneyTransferReceipt],
) -> Result<(), MaterialWorldError> {
    use std::collections::{BTreeMap, BTreeSet};
    let mut cancelled = BTreeSet::new();
    for transfer in transfers {
        if let (
            MoneyTransferPurpose::ShiftCancellation(id),
            MoneyLocation::Cash(AccountId::Organization(_)),
        ) = (transfer.purpose, transfer.credit.location)
        {
            if !cancelled.insert(id) {
                return Err(MaterialWorldError::Wire);
            }
        }
    }
    if cancelled.is_empty() {
        return Ok(());
    }
    let mut reservations = BTreeMap::new();
    for (index, transfer) in transfers.iter().enumerate() {
        if let MoneyTransferPurpose::ShiftReservation(id) = transfer.purpose {
            if cancelled.contains(&id) && reservations.insert(id, (index, transfer)).is_some() {
                return Err(MaterialWorldError::Wire);
            }
        }
    }
    for (index, transfer) in transfers.iter().enumerate() {
        if let MoneyTransferPurpose::ShiftCancellation(id) = transfer.purpose {
            if !cancelled.contains(&id) {
                continue;
            }
            let (earlier, reserve) = reservations.get(&id).ok_or(MaterialWorldError::Wire)?;
            if *earlier >= index
                || reserve.debit.location != transfer.credit.location
                || reserve.credit.location != transfer.debit.location
                || reserve.credit.delta != transfer.credit.delta
                || reserve.debit.delta.micro_units().checked_neg()
                    != Some(transfer.credit.delta.micro_units())
                || transfer.debit.delta.micro_units().checked_neg()
                    != Some(transfer.credit.delta.micro_units())
            {
                return Err(MaterialWorldError::Wire);
            }
        }
    }
    Ok(())
}

pub(super) fn validate(
    rows: &[AgencyPaidReceipt],
    wages: &[WageAccrualReceipt],
    transfers: &[MoneyTransferReceipt],
    income: &[IncomeReceipt],
    period: u64,
) -> Result<(), MaterialWorldError> {
    if rows.len() > MAX_AGENCY_ATTENDANCE_PER_PERIOD {
        return Err(MaterialWorldError::Wire);
    }
    for row in rows {
        if row.intent_id == [0; 32]
            || row.period != period
            || row.period == 0
            || row.hours == 0
            || row.wage.micro_units() <= 0
            || row.shift_id != babylon_material_circuit::agency_shift_id(period, row.intent_id)
        {
            return Err(MaterialWorldError::Wire);
        }
        let employer = AccountId::Organization(row.agency);
        let payee = AccountId::Household(row.principal_id);
        let matching: Vec<_> = wages.iter().filter(|w| w.shift == row.shift_id).collect();
        if matching.len() != 1
            || (
                matching[0].employer,
                matching[0].payee,
                matching[0].period,
                matching[0].obligated_hours,
                matching[0].amount,
            ) != (employer, payee, period, row.hours, row.wage)
        {
            return Err(MaterialWorldError::Wire);
        }
        let reserve: Vec<_> = transfers
            .iter()
            .filter(|t| t.purpose == MoneyTransferPurpose::ShiftReservation(row.shift_id))
            .collect();
        let payment: Vec<_> = transfers
            .iter()
            .filter(|t| t.purpose == MoneyTransferPurpose::WagePayment(row.shift_id))
            .collect();
        if reserve.len() != 1
            || payment.len() != 1
            || !matches!(
                (
                    transfers.iter().position(|t| t.purpose == MoneyTransferPurpose::ShiftReservation(row.shift_id)),
                    transfers.iter().position(|t| t.purpose == MoneyTransferPurpose::WagePayment(row.shift_id)),
                ),
                (Some(reservation), Some(payment)) if reservation < payment
            )
            || transfers
                .iter()
                .any(|t| t.purpose == MoneyTransferPurpose::ShiftCancellation(row.shift_id))
            || reserve[0].debit.location != MoneyLocation::Cash(employer)
            || reserve[0].credit.location != MoneyLocation::PayrollReserve(row.shift_id)
            || payment[0].debit.location != MoneyLocation::PayrollReserve(row.shift_id)
            || payment[0].credit.location != MoneyLocation::Cash(payee)
            || reserve[0].credit.delta != row.wage
            || payment[0].credit.delta != row.wage
            || reserve[0].debit.delta.micro_units().checked_neg() != Some(row.wage.micro_units())
            || payment[0].debit.delta.micro_units().checked_neg() != Some(row.wage.micro_units())
        {
            return Err(MaterialWorldError::Wire);
        }
        let household = income
            .iter()
            .find(|i| i.account == payee)
            .ok_or(MaterialWorldError::Wire)?;
        let total = wages
            .iter()
            .filter(|w| w.payee == payee)
            .try_fold(0_i128, |sum, w| {
                sum.checked_add(w.amount.micro_units())
                    .ok_or(MaterialWorldError::Arithmetic)
            })?;
        if household.statement.wage_income.micro_units() != total {
            return Err(MaterialWorldError::Wire);
        }
    }
    for row in income {
        let expected = rows
            .iter()
            .find(|r| row.account == AccountId::Organization(r.agency))
            .map_or(0, |r| r.wage.micro_units());
        if row.statement.agency_observation_labor_expense.micro_units() != expected {
            return Err(MaterialWorldError::Wire);
        }
    }
    if rows.iter().any(|r| {
        !income
            .iter()
            .any(|i| i.account == AccountId::Organization(r.agency))
    }) {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}

pub(super) fn encode(rows: &[AgencyPaidReceipt], bytes: &mut Vec<u8>) {
    for row in rows {
        bytes.extend_from_slice(&row.intent_id);
        bytes.extend_from_slice(&row.shift_id.as_bytes());
        bytes.extend_from_slice(&row.agency.as_bytes());
        bytes.extend_from_slice(&row.principal_id.as_bytes());
        bytes.extend_from_slice(&row.labor_unit_id.as_bytes());
        bytes.extend_from_slice(&row.period.to_be_bytes());
        bytes.extend_from_slice(&row.hours.to_be_bytes());
        bytes.extend_from_slice(&row.wage.micro_units().to_be_bytes());
    }
}

pub(super) fn decode(
    cursor: &mut ReceiptCursor<'_>,
) -> Result<AgencyPaidReceipt, MaterialWorldError> {
    Ok(AgencyPaidReceipt {
        intent_id: cursor.take()?,
        shift_id: ShiftId::from_bytes(cursor.take()?),
        agency: OrganizationAccountId::from_bytes(cursor.take()?),
        principal_id: FinalDemandPrincipalId::from_bytes(cursor.take()?),
        labor_unit_id: UnitId::from_bytes(cursor.take()?),
        period: cursor.u64()?,
        hours: cursor.u64()?,
        wage: Currency::from_micro_units(i128::from_be_bytes(cursor.take()?)),
    })
}
