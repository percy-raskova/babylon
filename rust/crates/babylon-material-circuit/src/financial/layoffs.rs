//! The record of layoffs: advancing it from a staffing decision, and what it is owed.
use super::{LayoffRecord, PublicProgramTerms, Result, MAX_LAYOFF_PERIODS};
use crate::{
    FinalDemandPrincipalId, LaborCompensation, MaterialCircuitError, MonetaryCircuit,
    StaffingMemberId, StaffingMemberReceipt,
};
use babylon_kernel::currency::Currency;
use std::cmp::Ordering;
use std::collections::{BTreeMap, BTreeSet};

/// Whether the account holds a program that pays after a layoff.
pub(crate) fn holds_after_layoff_program(economy: &MonetaryCircuit) -> bool {
    economy
        .financial
        .programs
        .iter()
        .any(|p| matches!(p.terms, PublicProgramTerms::AfterLayoff { .. }))
}

/// The recipients of the after-layoff programs, and the periods a record keeps (the longest term's half
/// periods, rounded up, at most `MAX_LAYOFF_PERIODS`; 0 without such a program).
pub(crate) fn program_window(
    economy: &MonetaryCircuit,
) -> (BTreeSet<FinalDemandPrincipalId>, usize) {
    let mut recipients = BTreeSet::new();
    let mut window = 0_usize;
    for program in &economy.financial.programs {
        if let PublicProgramTerms::AfterLayoff { half_periods, .. } = program.terms {
            recipients.extend(program.recipients.iter().copied());
            window = window.max(usize::from(half_periods.div_ceil(2)));
        }
    }
    (recipients, window.min(MAX_LAYOFF_PERIODS))
}

/// The members that can hold a record of layoffs: those whose employment term is a wage paid to a recipient
/// of an after-layoff program. A member with no wage has no pay for the benefit to be half of.
pub(crate) fn record_holders(economy: &MonetaryCircuit) -> BTreeSet<StaffingMemberId> {
    let (recipients, _) = program_window(economy);
    economy
        .employment
        .iter()
        .filter(|term| can_have_record(term.compensation, term.payee, &recipients))
        .map(|term| term.member_id)
        .collect()
}

/// Advance every record of layoffs from the member receipts of the closing period.
///
/// Records whose member is no longer paid a wage to a recipient of an after-layoff program are
/// dropped. Each member that can have a record and works at a site and unit that has any receipt
/// must have its own receipt, as must each member that holds one. Receipts of members that cannot
/// have a record are ignored: the caller passes every pool's receipts.
///
/// # Errors
/// `PublicProgramInvariant` for a receipt of another period, a repeated receipt, a receipt whose
/// household or workplace is not its member's, or a missing receipt.
pub(crate) fn advance_records(
    economy: &mut MonetaryCircuit,
    closing_period: u64,
    receipts: &[StaffingMemberReceipt],
) -> Result<()> {
    let invalid = MaterialCircuitError::PublicProgramInvariant;
    let (recipients, window) = program_window(economy);
    let old = std::mem::take(&mut economy.financial.layoffs);
    if recipients.is_empty() {
        return Ok(());
    }
    let mut by_member = BTreeMap::new();
    for receipt in receipts {
        if receipt.period != closing_period
            || by_member
                .insert(receipt.member.member_id(), receipt)
                .is_some()
        {
            return Err(invalid);
        }
    }
    let staffed: BTreeSet<_> = receipts.iter().map(|r| (r.site_id, r.unit_id)).collect();
    let old: BTreeMap<StaffingMemberId, LayoffRecord> =
        old.into_iter().map(|r| (r.member_id, r)).collect();
    let mut records = Vec::new();
    for term in &economy.employment {
        let receipt = by_member.get(&term.member_id).copied();
        if let Some(r) = receipt {
            if r.member.household_id() != term.payee
                || (r.site_id, r.unit_id) != (term.site_id, term.unit_id)
            {
                return Err(invalid);
            }
        }
        if !can_have_record(term.compensation, term.payee, &recipients) {
            continue;
        }
        let held = old.get(&term.member_id);
        let Some(receipt) = receipt else {
            if held.is_some() || staffed.contains(&(term.site_id, term.unit_id)) {
                return Err(invalid);
            }
            continue;
        };
        let cohorts = advance_layoffs(
            held.map_or(&[][..], |r| r.cohorts.as_slice()),
            window,
            receipt,
        )?;
        if !cohorts.is_empty() {
            records.push(LayoffRecord {
                member_id: term.member_id,
                hours_per_person: held.map_or(receipt.hours_per_person, |r| r.hours_per_person),
                cohorts,
            });
        }
    }
    records.sort_by_key(|r| r.member_id);
    economy.financial.layoffs = records;
    Ok(())
}
fn can_have_record(
    compensation: LaborCompensation,
    payee: FinalDemandPrincipalId,
    recipients: &BTreeSet<FinalDemandPrincipalId>,
) -> bool {
    matches!(compensation, LaborCompensation::Wage(_)) && recipients.contains(&payee)
}

/// The cohorts after one staffing decision. `window` is the periods the record keeps.
///
/// In order: (a) people who left the reserve unhired (the receipt's opening reserve already counts
/// them) leave from the oldest end; (b) every cohort ages one period and the one at `window`
/// leaves; (c) separations start a new cohort at the front; (d) hires take from the newest cohort
/// first, and once the covered are all back, from the uncovered; (e) trailing zeros are dropped.
///
/// # Errors
/// `PublicProgramInvariant` for a window of 0 or more than `MAX_LAYOFF_PERIODS`, or a record that
/// would exceed the closing reserve; `Arithmetic` on overflow.
pub(crate) fn advance_layoffs(
    cohorts: &[u64],
    window: usize,
    receipt: &StaffingMemberReceipt,
) -> Result<Vec<u64>> {
    let invalid = MaterialCircuitError::PublicProgramInvariant;
    if window == 0 || window > MAX_LAYOFF_PERIODS {
        return Err(invalid);
    }
    let mut next = cohorts.to_vec();
    // (a) The people who left the reserve unhired leave from the oldest end.
    let mut surplus = sum(&next)?.saturating_sub(receipt.opening_reserve);
    for cohort in next.iter_mut().rev() {
        let taken = surplus.min(*cohort);
        *cohort -= taken;
        surplus -= taken;
    }
    // (b) Every cohort ages one period; the one at the window leaves.
    next.insert(0, 0);
    next.truncate(window);
    // (c) Separations start a new cohort at the front.
    next[0] = receipt.separations;
    // (d) Hires take the newest covered first, then the uncovered, who have no cohort.
    let mut hires = receipt.hires;
    for cohort in &mut next {
        let taken = hires.min(*cohort);
        *cohort -= taken;
        hires -= taken;
    }
    // (e) Trailing zeros are dropped, and nobody is covered who is not looking.
    while next.last() == Some(&0) {
        next.pop();
    }
    if sum(&next)? > receipt.closing_reserve {
        return Err(invalid);
    }
    Ok(next)
}
fn sum(cohorts: &[u64]) -> Result<u64> {
    cohorts.iter().try_fold(0_u64, |n, &c| {
        n.checked_add(c).ok_or(MaterialCircuitError::Arithmetic)
    })
}

/// Persons covered and the amount owed this period for one member's record.
///
/// With `H = half_periods`, a cohort at `k < H / 2` counts two half periods, one at `k == H / 2`
/// when `H` is odd counts one, older ones nothing. The due is
/// `floor(wage x hours_per_person x wage_share_bps x units / 20_000)`, one floor for the member.
///
/// # Errors
/// `Arithmetic` on overflow.
pub(crate) fn layoff_due(
    wage: Currency,
    hours_per_person: u64,
    wage_share_bps: u16,
    half_periods: u16,
    cohorts: &[u64],
) -> Result<(u64, Currency)> {
    let arithmetic = MaterialCircuitError::Arithmetic;
    let full = usize::from(half_periods / 2);
    let mut covered = 0_u64;
    let mut units = 0_u128;
    for (k, &persons) in cohorts.iter().enumerate() {
        let halves: u128 = match k.cmp(&full) {
            Ordering::Less => 2,
            Ordering::Equal if half_periods % 2 == 1 => 1,
            _ => 0,
        };
        if halves > 0 && persons > 0 {
            covered = covered.checked_add(persons).ok_or(arithmetic)?;
            units = u128::from(persons)
                .checked_mul(halves)
                .and_then(|u| units.checked_add(u))
                .ok_or(arithmetic)?;
        }
    }
    let rate = u128::try_from(wage.micro_units()).map_err(|_| arithmetic)?;
    let owed = rate
        .checked_mul(u128::from(hours_per_person))
        .and_then(|n| n.checked_mul(u128::from(wage_share_bps)))
        .and_then(|n| n.checked_mul(units))
        .ok_or(arithmetic)?
        / 20_000;
    let owed = i128::try_from(owed).map_err(|_| arithmetic)?;
    Ok((covered, Currency::from_micro_units(owed)))
}

#[cfg(test)]
mod tests {
    use super::{advance_layoffs, layoff_due};
    use crate::{
        FinalDemandPrincipalId, SiteId, StaffingMemberBinding, StaffingMemberId,
        StaffingMemberReceipt, StaffingPoolId, UnitId,
    };
    use babylon_kernel::currency::Currency;

    /// A receipt of the given opening reserve, hires and separations (one of the two is 0).
    fn receipt(opening_reserve: u64, hires: u64, separations: u64) -> StaffingMemberReceipt {
        let labor_force = opening_reserve + 5;
        let closing_reserve = opening_reserve + separations - hires;
        let closing_employed = 5 + hires - separations;
        StaffingMemberReceipt {
            period: 1,
            pool_id: StaffingPoolId::from_bytes([1; 32]),
            site_id: SiteId::from_bytes([2; 32]),
            unit_id: UnitId::from_bytes([3; 32]),
            member: StaffingMemberBinding::from_living_force(
                StaffingMemberId::from_bytes([4; 32]),
                FinalDemandPrincipalId::from_bytes([5; 32]),
                "county:26163".parse().expect("a county"),
                labor_force,
            ),
            hours_per_person: 10,
            opening_employed: 5,
            opening_reserve,
            hires,
            separations,
            closing_employed,
            closing_reserve,
            next_opening_hours: closing_employed * 10,
        }
    }

    fn advance(cohorts: &[u64], window: usize, r: (u64, u64, u64)) -> Vec<u64> {
        advance_layoffs(cohorts, window, &receipt(r.0, r.1, r.2)).expect("the record advances")
    }

    #[test]
    fn a_layoff_starts_a_cohort() {
        assert_eq!(advance(&[], 7, (0, 0, 2)), [2]);
    }

    #[test]
    fn cohorts_age_and_the_oldest_leaves_after_its_half() {
        assert_eq!(advance(&[1, 0, 0, 0, 0, 0, 3], 7, (4, 0, 0)), [0, 1]);
    }

    #[test]
    fn hires_take_the_newest_first() {
        assert_eq!(advance(&[3, 2], 7, (5, 4, 0)), [0, 0, 1]);
    }

    #[test]
    fn hires_beyond_the_covered_come_from_the_uncovered() {
        assert_eq!(advance(&[2], 7, (10, 5, 0)), Vec::<u64>::new());
    }

    #[test]
    fn departures_leave_from_the_oldest_end() {
        assert_eq!(advance(&[2, 3], 7, (4, 0, 0)), [0, 2, 2]);
    }

    #[test]
    fn a_shorter_window_drops_older_cohorts() {
        assert_eq!(advance(&[1, 1, 1, 1, 1, 1, 1], 3, (7, 0, 0)), [0, 1, 1]);
    }

    #[test]
    fn a_window_outside_the_record_is_refused() {
        assert!(advance_layoffs(&[1], 0, &receipt(2, 0, 0)).is_err());
        assert!(advance_layoffs(&[1], 14, &receipt(2, 0, 0)).is_err());
    }

    fn due(wage: i128, hours: u64, bps: u16, half: u16, cohorts: &[u64]) -> (u64, i128) {
        let (covered, owed) =
            layoff_due(Currency::from_micro_units(wage), hours, bps, half, cohorts)
                .expect("the due computes");
        (covered, owed.micro_units())
    }

    #[test]
    fn a_record_is_owed_two_half_periods_then_one() {
        assert_eq!(
            due(10_000_000, 10, 5_000, 13, &[2, 0, 0, 0, 0, 0, 1]),
            (3, 125_000_000)
        );
    }

    #[test]
    fn a_cohort_past_the_term_is_owed_nothing() {
        assert_eq!(
            due(10_000_000, 10, 5_000, 12, &[0, 0, 0, 0, 0, 0, 4]),
            (0, 0)
        );
    }

    #[test]
    fn one_floor_for_the_member() {
        assert_eq!(due(10_000_001, 7, 3_333, 13, &[1]), (1, 23_331_002));
    }
}
