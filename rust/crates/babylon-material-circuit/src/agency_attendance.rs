//! A funded agency shift draws on an existing household's actual time and cash.
use crate::{
    AccountId, CircuitAccounting, FinalDemandPrincipalId, FundedShift, MaterialCatalog,
    MaterialCircuitError, MaterialCircuitState, MoneyLocation, MoneyTransferReceipt,
    OrganizationAccountId, ShiftId, UnitId, WageAccrualReceipt,
};
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_location::EconomicLocation;
use std::result::Result as StdResult;

/// One selected agency shift is admitted in each material period.
pub const MAX_AGENCY_ATTENDANCE_PER_PERIOD: usize = 1;

/// Stable period-bound shift identity; retired shifts cannot be reused in another period.
#[must_use]
pub fn agency_shift_id(period: u64, intent_id: [u8; 32]) -> ShiftId {
    let mut bytes = b"babylon.agency-funded-attendance.v1\0".to_vec();
    bytes.extend_from_slice(&period.to_be_bytes());
    bytes.extend_from_slice(&intent_id);
    ShiftId::from_bytes(babylon_kernel::content_digest::sha256_of(&bytes))
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AgencyAttendanceInput {
    pub intent_id: [u8; 32],
    pub shift_id: ShiftId,
    pub agency: OrganizationAccountId,
    pub principal_id: FinalDemandPrincipalId,
    pub residence: EconomicLocation,
    pub labor_unit_id: UnitId,
    pub due_period: u64,
    pub hours: u64,
    pub hourly_rate: Currency,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CityPdAttendance {
    pub intent_id: [u8; 32],
    pub shift_id: ShiftId,
    pub principal_id: FinalDemandPrincipalId,
    pub labor_unit_id: UnitId,
    pub period: u64,
    pub hours: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AgencyAttendanceOutcome {
    NoFunds,
    InsufficientTime,
    Paid,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AgencyObservationFundingReceipt {
    pub input: AgencyAttendanceInput,
    pub outcome: AgencyAttendanceOutcome,
    pub requested: Currency,
    pub reserved: Currency,
    pub paid: Currency,
    pub cancelled: Currency,
    pub shortfall: Currency,
    pub attended_hours: u64,
    pub shortfall_hours: u64,
    pub attendance: Option<CityPdAttendance>,
}

pub(crate) struct PendingAgency {
    pub input: AgencyAttendanceInput,
    pub amount: Currency,
    pub reserved: bool,
    pub shortfall: Currency,
}

type Result<T> = StdResult<T, MaterialCircuitError>;
fn zero() -> Currency {
    Currency::from_micro_units(0)
}

pub(crate) fn validate_input(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    inputs: &[AgencyAttendanceInput],
) -> Result<()> {
    if inputs.len() > MAX_AGENCY_ATTENDANCE_PER_PERIOD {
        return Err(MaterialCircuitError::DuplicateRow);
    }
    for input in inputs {
        if input.due_period != state.period || input.due_period == 0 {
            return Err(MaterialCircuitError::PeriodInvariant);
        }
        if input.hours == 0 {
            return Err(MaterialCircuitError::ZeroQuantity);
        }
        if input.intent_id == [0; 32]
            || input.shift_id != agency_shift_id(input.due_period, input.intent_id)
            || input.hourly_rate.micro_units() <= 0
        {
            return Err(MaterialCircuitError::PayrollInvariant);
        }
        input
            .hourly_rate
            .micro_units()
            .checked_mul(i128::from(input.hours))
            .ok_or(MaterialCircuitError::Arithmetic)?;
        let principal = state
            .final_demand_principals
            .iter()
            .filter(|p| p.id == input.principal_id)
            .collect::<Vec<_>>();
        let policy = catalog
            .household_time_policy
            .iter()
            .filter(|p| p.principal_id == input.principal_id)
            .collect::<Vec<_>>();
        let CircuitAccounting::Monetary(economy) = &state.accounting else {
            return Err(MaterialCircuitError::PayrollInvariant);
        };
        let recurring = economy
            .recurring
            .as_ref()
            .ok_or(MaterialCircuitError::PayrollInvariant)?;
        if principal.len() != 1
            || principal[0].location != input.residence
            || policy.len() != 1
            || policy[0].labor_unit_id != input.labor_unit_id
            || policy[0].eligible_persons == 0
            || recurring
                .households
                .iter()
                .filter(|r| r.principal_id == input.principal_id)
                .count()
                != 1
            || economy.book.shift(input.shift_id).is_ok()
        {
            return Err(MaterialCircuitError::PayrollInvariant);
        }
        economy.book.cash(AccountId::Organization(input.agency))?;
        economy
            .book
            .cash(AccountId::Household(input.principal_id))?;
    }
    Ok(())
}

pub(crate) fn reserve(
    opening: &MaterialCircuitState,
    state: &mut MaterialCircuitState,
    inputs: &[AgencyAttendanceInput],
    transfers: &mut Vec<MoneyTransferReceipt>,
) -> Result<Option<PendingAgency>> {
    let Some(input) = inputs.first() else {
        return Ok(None);
    };
    let amount = Currency::from_micro_units(
        input
            .hourly_rate
            .micro_units()
            .checked_mul(i128::from(input.hours))
            .ok_or(MaterialCircuitError::Arithmetic)?,
    );
    let employer = AccountId::Organization(input.agency);
    let CircuitAccounting::Monetary(initial) = &opening.accounting else {
        return Err(MaterialCircuitError::PayrollInvariant);
    };
    let initial_cash = initial.book.cash(employer)?.micro_units();
    let debited = transfers
        .iter()
        .filter(|row| row.debit.location == MoneyLocation::Cash(employer))
        .try_fold(0_i128, |sum, row| {
            let amount = row
                .debit
                .delta
                .micro_units()
                .checked_neg()
                .ok_or(MaterialCircuitError::Arithmetic)?;
            if amount <= 0 {
                return Err(MaterialCircuitError::PayrollInvariant);
            }
            sum.checked_add(amount)
                .ok_or(MaterialCircuitError::Arithmetic)
        })?;
    let available_opening = initial_cash
        .checked_sub(debited)
        .ok_or(MaterialCircuitError::Arithmetic)?
        .max(0);
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Err(MaterialCircuitError::PayrollInvariant);
    };
    let cash = Currency::from_micro_units(
        economy
            .book
            .cash(employer)?
            .micro_units()
            .min(available_opening),
    );
    let reserved = cash >= amount;
    let shortfall = if reserved {
        zero()
    } else {
        Currency::from_micro_units(amount.micro_units() - cash.micro_units())
    };
    if reserved {
        transfers.push(economy.book.reserve_shift(FundedShift::new(
            input.shift_id,
            AccountId::Organization(input.agency),
            AccountId::Household(input.principal_id),
            input.due_period,
            input.hours,
            input.hourly_rate,
        )?)?);
    }
    Ok(Some(PendingAgency {
        input: input.clone(),
        amount,
        reserved,
        shortfall,
    }))
}

pub(crate) fn settle(
    pending: &PendingAgency,
    eligible: bool,
    state: &mut MaterialCircuitState,
    transfers: &mut Vec<MoneyTransferReceipt>,
    accruals: &mut Vec<WageAccrualReceipt>,
) -> Result<AgencyObservationFundingReceipt> {
    let mut result = AgencyObservationFundingReceipt {
        input: pending.input.clone(),
        outcome: AgencyAttendanceOutcome::NoFunds,
        requested: pending.amount,
        reserved: zero(),
        paid: zero(),
        cancelled: zero(),
        shortfall: pending.shortfall,
        attended_hours: 0,
        shortfall_hours: pending.input.hours,
        attendance: None,
    };
    if !pending.reserved {
        return Ok(result);
    }
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Err(MaterialCircuitError::PayrollInvariant);
    };
    result.reserved = pending.amount;
    if eligible {
        accruals.push(economy.book.accrue_shift(pending.input.shift_id)?);
        transfers.push(economy.book.pay_shift(pending.input.shift_id)?);
        result.paid = pending.amount;
        result.attended_hours = pending.input.hours;
        result.shortfall_hours = 0;
        result.outcome = AgencyAttendanceOutcome::Paid;
        result.attendance = Some(CityPdAttendance {
            intent_id: pending.input.intent_id,
            shift_id: pending.input.shift_id,
            principal_id: pending.input.principal_id,
            labor_unit_id: pending.input.labor_unit_id,
            period: pending.input.due_period,
            hours: pending.input.hours,
        });
    } else {
        transfers.push(economy.book.cancel_unearned_shift(pending.input.shift_id)?);
        result.cancelled = pending.amount;
        result.outcome = AgencyAttendanceOutcome::InsufficientTime;
    }
    economy.book.retire_shift(pending.input.shift_id)?;
    Ok(result)
}
