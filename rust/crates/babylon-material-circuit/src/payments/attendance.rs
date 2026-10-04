//! Finite member attendance, resident payroll, and exact actual-work attribution.
use std::collections::BTreeMap;
use std::ops::Range;

use crate::{
    AccountId, CircuitAccounting, FinalDemandPrincipalId, FundedShift, MaterialCircuitError,
    MaterialCircuitState, MoneyTransferReceipt, ShiftId, SiteId, StaffingMemberId, UnitId,
    WageAccrualReceipt,
};
use babylon_kernel::{content_digest::sha256_of, currency::Currency};

type Result<T> = std::result::Result<T, MaterialCircuitError>;

/// Compensation does not assign political class or establish ownership shares.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum LaborCompensation {
    Wage(Currency),
    WorkingOwner,
    UnpaidFamily,
}
impl LaborCompensation {
    #[must_use]
    pub fn wage_rate(self) -> Currency {
        match self {
            Self::Wage(rate) => rate,
            Self::WorkingOwner | Self::UnpaidFamily => Currency::from_micro_units(0),
        }
    }
}

/// Captured terms for one resident member at one workplace.
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub struct EmploymentTerms {
    pub member_id: StaffingMemberId,
    pub site_id: SiteId,
    pub unit_id: UnitId,
    pub payee: FinalDemandPrincipalId,
    pub compensation: LaborCompensation,
}

/// Aggregate physical hours; a mixed workplace has no single household payee.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct LaborUseReceipt {
    pub site_id: SiteId,
    pub unit_id: UnitId,
    pub period: u64,
    pub available_hours: u64,
    pub planned_hours: u64,
    pub unplanned_hours: u64,
    pub funded_hours: u64,
    pub unfunded_hours: u64,
    pub non_wage_hours: u64,
    pub used_hours: u64,
    pub paid_idle_hours: u64,
    pub unpaid_idle_hours: u64,
}

/// Every attended hour and every earned micro-unit has one actual use.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MemberLaborUseReceipt {
    pub member_id: StaffingMemberId,
    pub site_id: SiteId,
    pub unit_id: UnitId,
    pub payee: FinalDemandPrincipalId,
    pub compensation: LaborCompensation,
    pub period: u64,
    pub available_hours: u64,
    pub planned_hours: u64,
    pub unplanned_hours: u64,
    pub attended_hours: u64,
    pub unattended_hours: u64,
    pub production_hours: u64,
    pub handling_hours: u64,
    pub maintenance_hours: u64,
    pub installation_hours: u64,
    pub idle_hours: u64,
    pub accrued_wages: Currency,
    pub production_wages: Currency,
    pub handling_wages: Currency,
    pub maintenance_wages: Currency,
    pub installation_wages: Currency,
    pub idle_wages: Currency,
}
impl MemberLaborUseReceipt {
    /// Standalone exact conservation, independent of graph/source admission.
    /// # Errors
    /// Refuses inconsistent hours, unsupported compensation, or wage attribution.
    pub fn validate(&self) -> Result<()> {
        let used = self
            .production_hours
            .checked_add(self.handling_hours)
            .and_then(|n| n.checked_add(self.maintenance_hours))
            .and_then(|n| n.checked_add(self.installation_hours));
        if self.period == 0
            || self.planned_hours.checked_add(self.unplanned_hours) != Some(self.available_hours)
            || self.attended_hours.checked_add(self.unattended_hours) != Some(self.planned_hours)
            || used.and_then(|n| n.checked_add(self.idle_hours)) != Some(self.attended_hours)
            || matches!(self.compensation, LaborCompensation::Wage(rate) if rate.micro_units() <= 0)
            || (!matches!(self.compensation, LaborCompensation::Wage(_))
                && self.unattended_hours != 0)
        {
            return Err(MaterialCircuitError::PayrollInvariant);
        }
        for (hours, wages) in [
            (self.attended_hours, self.accrued_wages),
            (self.production_hours, self.production_wages),
            (self.handling_hours, self.handling_wages),
            (self.maintenance_hours, self.maintenance_wages),
            (self.installation_hours, self.installation_wages),
            (self.idle_hours, self.idle_wages),
        ] {
            if wages != wage_amount(hours, self.compensation)? {
                return Err(MaterialCircuitError::PayrollInvariant);
            }
        }
        Ok(())
    }
}

#[derive(Clone, Copy)]
pub(crate) enum LaborUse {
    Production,
    Handling,
    Maintenance,
    Installation,
}

#[derive(Default)]
pub(crate) struct AttendanceLedger {
    members: Vec<MemberLaborUseReceipt>,
    groups: BTreeMap<(SiteId, UnitId), Range<usize>>,
}
impl AttendanceLedger {
    pub(crate) fn members(&self) -> &[MemberLaborUseReceipt] {
        &self.members
    }
    pub(crate) fn consume(
        &mut self,
        site: SiteId,
        unit: UnitId,
        hours: u64,
        purpose: LaborUse,
    ) -> Result<Currency> {
        if hours == 0 {
            return Ok(Currency::from_micro_units(0));
        }
        let range = self
            .groups
            .get(&(site, unit))
            .ok_or(MaterialCircuitError::PayrollInvariant)?
            .clone();
        let rows = &mut self.members[range];
        let shares = crate::staffing::proportional_shares(
            hours,
            &rows.iter().map(|r| r.idle_hours).collect::<Vec<_>>(),
        )
        .map_err(|_| MaterialCircuitError::PayrollInvariant)?;
        let mut total = Currency::from_micro_units(0);
        for (row, share) in rows.iter_mut().zip(shares) {
            let wages = wage_amount(share, row.compensation)?;
            row.idle_hours -= share;
            row.idle_wages = row
                .idle_wages
                .checked_sub(wages)
                .map_err(|_| MaterialCircuitError::Arithmetic)?;
            let (used, cost) = match purpose {
                LaborUse::Production => (&mut row.production_hours, &mut row.production_wages),
                LaborUse::Handling => (&mut row.handling_hours, &mut row.handling_wages),
                LaborUse::Maintenance => (&mut row.maintenance_hours, &mut row.maintenance_wages),
                LaborUse::Installation => {
                    (&mut row.installation_hours, &mut row.installation_wages)
                }
            };
            *used = used
                .checked_add(share)
                .ok_or(MaterialCircuitError::Arithmetic)?;
            *cost = cost
                .checked_add(wages)
                .map_err(|_| MaterialCircuitError::Arithmetic)?;
            total = total
                .checked_add(wages)
                .map_err(|_| MaterialCircuitError::Arithmetic)?;
        }
        Ok(total)
    }

    pub(crate) fn finish(
        self,
        state: &MaterialCircuitState,
    ) -> Result<(Vec<LaborUseReceipt>, Vec<MemberLaborUseReceipt>)> {
        let mut aggregates = Vec::with_capacity(self.groups.len());
        for ((site, unit), range) in &self.groups {
            let mut result = LaborUseReceipt {
                site_id: *site,
                unit_id: *unit,
                period: state.period,
                available_hours: 0,
                planned_hours: 0,
                unplanned_hours: 0,
                funded_hours: 0,
                unfunded_hours: 0,
                non_wage_hours: 0,
                used_hours: 0,
                paid_idle_hours: 0,
                unpaid_idle_hours: 0,
            };
            for row in &self.members[range.clone()] {
                row.validate()?;
                add_hours(&mut result.available_hours, row.available_hours)?;
                add_hours(&mut result.planned_hours, row.planned_hours)?;
                add_hours(&mut result.unplanned_hours, row.unplanned_hours)?;
                add_hours(&mut result.used_hours, row.attended_hours - row.idle_hours)?;
                match row.compensation {
                    LaborCompensation::Wage(_) => {
                        add_hours(&mut result.funded_hours, row.attended_hours)?;
                        add_hours(&mut result.unfunded_hours, row.unattended_hours)?;
                        add_hours(&mut result.paid_idle_hours, row.idle_hours)?;
                    }
                    LaborCompensation::WorkingOwner | LaborCompensation::UnpaidFamily => {
                        add_hours(&mut result.non_wage_hours, row.attended_hours)?;
                        add_hours(&mut result.unpaid_idle_hours, row.idle_hours)?;
                    }
                }
            }
            let index = state
                .labor
                .binary_search_by_key(&(state.period, *site, *unit), |r| {
                    (r.period, r.site_id, r.unit_id)
                })
                .map_err(|_| MaterialCircuitError::PayrollInvariant)?;
            if result.paid_idle_hours.checked_add(result.unpaid_idle_hours)
                != Some(state.labor[index].available)
            {
                return Err(MaterialCircuitError::PayrollInvariant);
            }
            aggregates.push(result);
        }
        Ok((aggregates, self.members))
    }
}

fn add_hours(total: &mut u64, amount: u64) -> Result<()> {
    *total = total
        .checked_add(amount)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    Ok(())
}
fn wage_amount(hours: u64, mode: LaborCompensation) -> Result<Currency> {
    mode.wage_rate()
        .micro_units()
        .checked_mul(i128::from(hours))
        .map(Currency::from_micro_units)
        .ok_or(MaterialCircuitError::Arithmetic)
}

/// Stable identity for one member's funded attendance commitment.
#[must_use]
pub fn member_shift_id(period: u64, terms: &EmploymentTerms) -> ShiftId {
    let mut bytes = b"babylon.member-funded-attendance.v1\0".to_vec();
    bytes.extend_from_slice(&period.to_be_bytes());
    bytes.extend_from_slice(&terms.member_id.as_bytes());
    bytes.extend_from_slice(&terms.site_id.as_bytes());
    bytes.extend_from_slice(&terms.unit_id.as_bytes());
    bytes.extend_from_slice(&terms.payee.as_bytes());
    ShiftId::from_bytes(sha256_of(&bytes))
}

pub(crate) fn fund_attendance(
    state: &mut MaterialCircuitState,
    transfers: &mut Vec<MoneyTransferReceipt>,
    accruals: &mut Vec<WageAccrualReceipt>,
) -> Result<AttendanceLedger> {
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Ok(AttendanceLedger::default());
    };
    for shift in economy.book.snapshot().shifts {
        transfers.push(economy.book.pay_shift(shift.id)?);
        economy.book.retire_shift(shift.id)?;
    }
    let terms = economy.employment.iter().enumerate().fold(
        BTreeMap::<_, Vec<_>>::new(),
        |mut groups, (index, row)| {
            groups
                .entry((row.site_id, row.unit_id))
                .or_default()
                .push(index);
            groups
        },
    );
    let capacities: BTreeMap<_, _> = economy
        .member_labor
        .iter()
        .filter(|r| r.period == state.period)
        .map(|r| (r.member_id, r.available_hours))
        .collect();
    let mut ledger = AttendanceLedger::default();
    for labor in state.labor.iter_mut().filter(|r| r.period == state.period) {
        let Some(indices) = terms.get(&(labor.site_id, labor.unit_id)) else {
            if labor.available != 0 {
                return Err(MaterialCircuitError::PayrollInvariant);
            }
            continue;
        };
        let available = indices
            .iter()
            .map(|i| {
                capacities
                    .get(&economy.employment[*i].member_id)
                    .copied()
                    .ok_or(MaterialCircuitError::PayrollInvariant)
            })
            .collect::<Result<Vec<_>>>()?;
        let planned = if let Some(recurring) = &economy.recurring {
            let index = recurring
                .attendance
                .binary_search_by_key(&(labor.site_id, labor.unit_id), |r| (r.site_id, r.unit_id))
                .map_err(|_| MaterialCircuitError::PayrollInvariant)?;
            let plan = &recurring.attendance[index];
            if plan.period != state.period {
                return Err(MaterialCircuitError::PeriodInvariant);
            }
            plan.planned_hours.min(labor.available)
        } else {
            labor.available
        };
        let shares = crate::staffing::proportional_shares(planned, &available)
            .map_err(|_| MaterialCircuitError::PayrollInvariant)?;
        let start = ledger.members.len();
        let mut attended_total = 0;
        // Captured canonical member order resolves scarce payroll cash. Work use
        // is separately proportional across everyone who actually attends.
        for ((index, available), planned) in indices.iter().zip(available).zip(shares) {
            let row = fund_member_attendance(
                &mut economy.book,
                &economy.employment[*index],
                state.period,
                available,
                planned,
                transfers,
                accruals,
            )?;
            add_hours(&mut attended_total, row.attended_hours)?;
            ledger.members.push(row);
        }
        labor.available = attended_total;
        ledger
            .groups
            .insert((labor.site_id, labor.unit_id), start..ledger.members.len());
    }
    Ok(ledger)
}

fn fund_member_attendance(
    book: &mut crate::MonetaryBook,
    terms: &EmploymentTerms,
    period: u64,
    available: u64,
    planned: u64,
    transfers: &mut Vec<MoneyTransferReceipt>,
    accruals: &mut Vec<WageAccrualReceipt>,
) -> Result<MemberLaborUseReceipt> {
    let attended = match terms.compensation {
        LaborCompensation::Wage(rate) => {
            let cash = book.cash(AccountId::Site(terms.site_id))?.micro_units();
            u64::try_from((cash / rate.micro_units()).min(i128::from(planned)))
                .map_err(|_| MaterialCircuitError::Arithmetic)?
        }
        LaborCompensation::WorkingOwner | LaborCompensation::UnpaidFamily => planned,
    };
    let wages = wage_amount(attended, terms.compensation)?;
    if let LaborCompensation::Wage(rate) = terms.compensation {
        if attended != 0 {
            let id = member_shift_id(period, terms);
            transfers.push(book.reserve_shift(FundedShift::new(
                id,
                AccountId::Site(terms.site_id),
                AccountId::Household(terms.payee),
                period,
                attended,
                rate,
            )?)?);
            accruals.push(book.accrue_shift(id)?);
            transfers.push(book.pay_shift(id)?);
            book.retire_shift(id)?;
        }
    }
    let zero = Currency::from_micro_units(0);
    Ok(MemberLaborUseReceipt {
        member_id: terms.member_id,
        site_id: terms.site_id,
        unit_id: terms.unit_id,
        payee: terms.payee,
        compensation: terms.compensation,
        period,
        available_hours: available,
        planned_hours: planned,
        unplanned_hours: available - planned,
        attended_hours: attended,
        unattended_hours: planned - attended,
        installation_hours: 0,
        installation_wages: zero,
        production_hours: 0,
        handling_hours: 0,
        maintenance_hours: 0,
        idle_hours: attended,
        accrued_wages: wages,
        production_wages: zero,
        handling_wages: zero,
        maintenance_wages: zero,
        idle_wages: wages,
    })
}
