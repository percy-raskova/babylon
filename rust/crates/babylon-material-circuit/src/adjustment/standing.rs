//! No money, no work (A17 of ADR314, as measured in round eight): a workplace that could not pay the hours its
//! plan asked keeps only the people it paid, takes nobody on until it has paid everyone it employs, and then
//! hires only as far as its money pays one period of wages.
//!
//! What the rule remembers of each workplace from one close to the next is `WorkplaceStanding`. The caller keeps
//! it, as it keeps the staffing state; it is not part of the stored state.

use std::collections::BTreeMap;

use super::receipts::StopReceipt;
use crate::{
    AccountId, MaterialCircuitError, MemberLaborUseReceipt, MonetaryCircuit, PlaceStaffingError,
    SiteId, StaffingError, StaffingState,
};

/// Whether the stop rule holds a workplace back.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum StopHold {
    /// Not held back: it paid everyone it employed, or it has not yet failed to.
    #[default]
    Free,
    /// Held back: it could not pay, and has not yet paid everyone it employs.
    Held,
}

/// What the rule remembers of one workplace.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct WorkplaceStandingRow {
    /// The workplace.
    pub site_id: SiteId,
    /// Whether it is held back.
    pub hold: StopHold,
}

/// What the rules remember of each workplace from one close to the next. The caller keeps it, as it keeps the
/// staffing state.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct WorkplaceStanding {
    rows: Vec<WorkplaceStandingRow>,
}

impl WorkplaceStanding {
    /// Nothing remembered: the opening. Every workplace is `Free`.
    #[must_use]
    pub const fn opening() -> Self {
        Self { rows: Vec::new() }
    }

    /// One row for each workplace the rules have seen, in site order.
    #[must_use]
    pub fn rows(&self) -> &[WorkplaceStandingRow] {
        &self.rows
    }

    /// The hold of a workplace: `Free` for one the rules have not seen.
    #[must_use]
    pub fn hold_of(&self, site: SiteId) -> StopHold {
        self.rows
            .binary_search_by_key(&site, |row| row.site_id)
            .map_or(StopHold::Free, |index| self.rows[index].hold)
    }
}

/// What the test reads of one workplace at a close.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct SiteTest {
    /// The hours its people made available this period.
    pub(crate) available: u64,
    /// The hours of them it paid.
    pub(crate) attended: u64,
    /// The hours of them it could not pay.
    pub(crate) unattended: u64,
    /// What the hours made available cost, in millionths of a dollar.
    pub(crate) bill: i128,
    /// Its cash in the closed period's state, in millionths of a dollar.
    pub(crate) cash: i128,
    /// The persons it employed when the period opened.
    pub(crate) employed: u64,
    /// The hours of a person.
    pub(crate) hours_per_person: u64,
    /// Its largest wage rate for an hour, in millionths of a dollar.
    pub(crate) rate: i128,
}

/// What the test decides about one workplace.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct Verdict {
    pub(crate) could_not_pay: bool,
    pub(crate) hold: StopHold,
    /// The most persons it may employ after this close; `None` when not limited.
    pub(crate) limit: Option<u64>,
}

/// The rule's test of one workplace: `previous` is its hold before this close.
///
/// - It could not pay (`unattended > 0`): it keeps `min(employed, ceil(attended / hours a person))` people and
///   is held.
/// - Else, held and its people were all paid for hours made available: it is free.
/// - Else, still held: it may employ `employed` and as many more as the cash left after its own people's bill
///   pays one period of.
///
/// # Errors
/// `Arithmetic` for hours a person of 0 or a sum that does not fit.
pub(crate) fn judge(previous: StopHold, test: &SiteTest) -> Result<Verdict, MaterialCircuitError> {
    let arithmetic = MaterialCircuitError::Arithmetic;
    if test.hours_per_person == 0 {
        return Err(arithmetic);
    }
    if test.unattended > 0 {
        let paid = test.attended.div_ceil(test.hours_per_person);
        return Ok(Verdict {
            could_not_pay: true,
            hold: StopHold::Held,
            limit: Some(test.employed.min(paid)),
        });
    }
    let held = previous == StopHold::Held && test.available == 0;
    if !held {
        return Ok(Verdict {
            could_not_pay: false,
            hold: StopHold::Free,
            limit: None,
        });
    }
    let spare = test.cash.checked_sub(test.bill).ok_or(arithmetic)?.max(0);
    let person = test
        .rate
        .checked_mul(i128::from(test.hours_per_person))
        .ok_or(arithmetic)?;
    let limit = if person <= 0 {
        None
    } else {
        let hires = u64::try_from(spare / person).map_err(|_| arithmetic)?;
        Some(test.employed.checked_add(hires).ok_or(arithmetic)?)
    };
    Ok(Verdict {
        could_not_pay: false,
        hold: StopHold::Held,
        limit,
    })
}

/// What the stop rule decided at one close.
pub(crate) struct StopRound {
    /// What is remembered after it.
    pub(crate) standing: WorkplaceStanding,
    /// The most persons each limited workplace may employ after the close.
    pub(crate) limits: BTreeMap<SiteId, u64>,
    /// One receipt for each workplace, in site order.
    pub(crate) receipts: Vec<StopReceipt>,
}

/// The sums the test reads of one workplace's member labor receipts, and the bill.
#[derive(Default)]
struct Hours {
    available: u64,
    attended: u64,
    unattended: u64,
    bill: i128,
}

fn hours_by_site(
    uses: &[MemberLaborUseReceipt],
    period: u64,
) -> Result<BTreeMap<SiteId, Hours>, MaterialCircuitError> {
    let arithmetic = MaterialCircuitError::Arithmetic;
    let mut sites: BTreeMap<SiteId, Hours> = BTreeMap::new();
    for row in uses.iter().filter(|row| row.period == period) {
        let hours = sites.entry(row.site_id).or_default();
        hours.available = hours
            .available
            .checked_add(row.available_hours)
            .ok_or(arithmetic)?;
        hours.attended = hours
            .attended
            .checked_add(row.attended_hours)
            .ok_or(arithmetic)?;
        hours.unattended = hours
            .unattended
            .checked_add(row.unattended_hours)
            .ok_or(arithmetic)?;
        let cost = i128::from(row.available_hours)
            .checked_mul(row.compensation.wage_rate().micro_units())
            .ok_or(arithmetic)?;
        hours.bill = hours.bill.checked_add(cost).ok_or(arithmetic)?;
    }
    Ok(sites)
}

/// Each workplace's persons at the opening and its hours a person, from the staffing state's pools. A workplace
/// whose pools do not share a schedule is refused.
fn persons_by_site(
    opening: &StaffingState,
) -> Result<BTreeMap<SiteId, (u64, u64)>, PlaceStaffingError> {
    let mut sites: BTreeMap<SiteId, (u64, u64)> = BTreeMap::new();
    for pool in opening.pools() {
        let hours = pool.binding().policy().hours_per_person();
        let row = sites.entry(pool.binding().site_id()).or_insert((0, hours));
        if row.1 != hours {
            return Err(PlaceStaffingError::Staffing(
                StaffingError::PopulationInvariant,
            ));
        }
        row.0 = row
            .0
            .checked_add(pool.employed())
            .ok_or(MaterialCircuitError::Arithmetic)?;
    }
    Ok(sites)
}

/// Test every workplace of the staffing state at the close of `period`, from the period's member labor
/// receipts and the closed state's cash.
///
/// # Errors
/// A circuit refusal for arithmetic or a workplace without an account; a staffing refusal for pools of one
/// workplace with different schedules.
pub(crate) fn test_workplaces(
    economy: &MonetaryCircuit,
    uses: &[MemberLaborUseReceipt],
    period: u64,
    opening: &StaffingState,
    wages: &BTreeMap<SiteId, i128>,
    previous: &WorkplaceStanding,
) -> Result<StopRound, PlaceStaffingError> {
    let hours = hours_by_site(uses, period)?;
    let persons = persons_by_site(opening)?;
    let mut rows = Vec::with_capacity(persons.len());
    let mut limits = BTreeMap::new();
    let mut receipts = Vec::with_capacity(persons.len());
    for (site, (employed, hours_per_person)) in persons {
        let read = hours.get(&site);
        let cash = economy
            .book
            .cash(AccountId::Site(site))
            .map_err(MaterialCircuitError::from)?
            .micro_units();
        let test = SiteTest {
            available: read.map_or(0, |h| h.available),
            attended: read.map_or(0, |h| h.attended),
            unattended: read.map_or(0, |h| h.unattended),
            bill: read.map_or(0, |h| h.bill),
            cash,
            employed,
            hours_per_person,
            rate: wages.get(&site).copied().unwrap_or(0),
        };
        let verdict = judge(previous.hold_of(site), &test)?;
        if let Some(limit) = verdict.limit {
            limits.insert(site, limit);
        }
        rows.push(WorkplaceStandingRow {
            site_id: site,
            hold: verdict.hold,
        });
        receipts.push(StopReceipt {
            period,
            site_id: site,
            could_not_pay: verdict.could_not_pay,
            hold: verdict.hold,
            limit: verdict.limit,
        });
    }
    Ok(StopRound {
        standing: WorkplaceStanding { rows },
        limits,
        receipts,
    })
}
