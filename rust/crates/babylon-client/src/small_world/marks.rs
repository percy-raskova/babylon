//! The rules' receipts as rows of the panel: every row is a sum of the fields of one period's receipts, and a
//! period the rule does not hold in adds none.

use super::frame::FrameError;
use super::inspect::{self, Pick};
use super::reading::Party;
use super::rules::SceneRule;
use crate::human_numbers;
use babylon_circuit_worlds::{Household, PeriodResult, Workplace};
use babylon_material_circuit::{
    AdjustmentReceipt, HiringBoundReceipt, HiringLimit, PlaceMoveReceipt, StaffingPoolId, StopHold,
    StopReceipt,
};
use std::collections::BTreeMap;

type Rows = Vec<(String, String)>;

fn missing(what: &str) -> FrameError {
    FrameError::Edge(what.to_owned())
}

fn grouped(n: u64) -> String {
    human_numbers::grouped(u128::from(n))
}

fn add(a: u64, b: u64) -> Result<u64, FrameError> {
    a.checked_add(b).ok_or(FrameError::Arithmetic)
}

/// The rows the rules add to the panel of a pick, for the period at `index` of `history`.
///
/// # Errors
/// `FrameError::Edge` for a receipt of no workplace, pool or household of the world;
/// `FrameError::Arithmetic` for a sum that overflows.
pub fn rule_rows(history: &[PeriodResult], index: usize, pick: &Pick) -> Result<Rows, FrameError> {
    let result = history
        .get(index)
        .ok_or_else(|| missing("no such period in the history"))?;
    let mut rows = Vec::new();
    if holds(result, SceneRule::SeekingInPlace) {
        match pick {
            Pick::Body(Party::Workplace(w)) => seeker_rows_of_workplace(result, *w, &mut rows)?,
            Pick::Body(Party::Household(h)) => seeker_rows_of_household(result, *h, &mut rows)?,
            Pick::Particle(id) => {
                if let Some((h, _)) = inspect::household_of(id) {
                    seeker_rows_of_household(result, h, &mut rows)?;
                }
            }
            Pick::Body(Party::Treasury | Party::Fund) | Pick::Set(_) => {}
        }
    }
    if holds(result, SceneRule::HiringWithinMeans) {
        if let Pick::Body(Party::Workplace(w)) = pick {
            bound_rows(result, *w, &mut rows)?;
        }
    }
    if holds(result, SceneRule::StopWithoutPay) {
        if let Pick::Body(Party::Workplace(w)) = pick {
            stop_rows(history, index, *w, &mut rows)?;
        }
    }
    Ok(rows)
}

/// Whether the period's catalog asked for a rule of this kind.
#[must_use]
pub fn holds(result: &PeriodResult, rule: SceneRule) -> bool {
    result
        .rules
        .iter()
        .any(|asked| SceneRule::of(*asked) == rule)
}

/// The period's moves of people, in receipt order.
pub fn moves(result: &PeriodResult) -> impl Iterator<Item = &PlaceMoveReceipt> {
    result
        .receipts
        .adjustments
        .iter()
        .filter_map(|receipt| match receipt {
            AdjustmentReceipt::PlaceMove(moved) => Some(moved),
            AdjustmentReceipt::HiringBound(_) | AdjustmentReceipt::Stop(_) => None,
        })
}

/// The period's stop receipt of a workplace's site.
fn stop_of(result: &PeriodResult, w: Workplace) -> Option<&StopReceipt> {
    result
        .receipts
        .adjustments
        .iter()
        .find_map(|receipt| match receipt {
            AdjustmentReceipt::Stop(stop) if stop.site_id == w.site_id() => Some(stop),
            AdjustmentReceipt::Stop(_)
            | AdjustmentReceipt::HiringBound(_)
            | AdjustmentReceipt::PlaceMove(_) => None,
        })
}

/// Whether the period's receipts hold the workplace's site `Held`.
fn is_held_in(result: &PeriodResult, w: Workplace) -> bool {
    stop_of(result, w).is_some_and(|stop| stop.hold == StopHold::Held)
}

/// The first period of the unbroken run of closes, ending at `index`, whose receipts hold the site `Held`.
#[must_use]
pub fn held_since(history: &[PeriodResult], index: usize, w: Workplace) -> Option<u64> {
    let mut since = None;
    for result in history.get(..=index)?.iter().rev() {
        if !is_held_in(result, w) {
            break;
        }
        since = Some(result.period);
    }
    since
}

/// The stop rule's rows of a workplace from the period's `StopReceipt` of its site.
fn stop_rows(
    history: &[PeriodResult],
    index: usize,
    w: Workplace,
    rows: &mut Rows,
) -> Result<(), FrameError> {
    let result = history
        .get(index)
        .ok_or_else(|| missing("no such period in the history"))?;
    let Some(stop) = stop_of(result, w) else {
        return Ok(());
    };
    if stop.hold == StopHold::Held {
        let since = held_since(history, index, w).ok_or_else(|| missing("a held run"))?;
        rows.push((
            "No money, no work".to_owned(),
            format!("held since period {since}"),
        ));
        if let Some(limit) = stop.limit {
            rows.push(("Most it may employ".to_owned(), grouped(limit)));
        }
    }
    if stop.could_not_pay {
        let unpaid = result
            .receipts
            .member_labor_use
            .iter()
            .filter(|row| row.site_id == w.site_id())
            .try_fold(0_u64, |sum, row| add(sum, row.unattended_hours))?;
        rows.push(("Hours it could not pay".to_owned(), grouped(unpaid)));
    }
    Ok(())
}

/// The period's bound receipts of a workplace's site, in receipt order.
fn bounds_of(result: &PeriodResult, w: Workplace) -> impl Iterator<Item = &HiringBoundReceipt> {
    result
        .receipts
        .adjustments
        .iter()
        .filter_map(move |receipt| match receipt {
            AdjustmentReceipt::HiringBound(bound) if bound.site_id == w.site_id() => Some(bound),
            AdjustmentReceipt::HiringBound(_)
            | AdjustmentReceipt::PlaceMove(_)
            | AdjustmentReceipt::Stop(_) => None,
        })
}

/// "nothing", "its capacity", "its inputs", "its money", "another limit".
#[must_use]
pub const fn limit_words(limit: HiringLimit) -> &'static str {
    match limit {
        HiringLimit::None => "nothing",
        HiringLimit::Capacity => "its capacity",
        HiringLimit::Inputs => "its inputs",
        HiringLimit::Money => "its money",
        HiringLimit::Other => "another limit",
    }
}

/// 0 to 4 in the order of `HiringLimit`, as the bench writes `bound_by_` (Task 4, decision 4).
const fn limit_code(limit: HiringLimit) -> u8 {
    match limit {
        HiringLimit::None => 0,
        HiringLimit::Capacity => 1,
        HiringLimit::Inputs => 2,
        HiringLimit::Money => 3,
        HiringLimit::Other => 4,
    }
}

/// The bound's rows of a workplace from the period's `HiringBound` receipts of its site. They are for the next
/// period: the bound of a close cuts the attendance of the period that opens after it.
fn bound_rows(result: &PeriodResult, w: Workplace, rows: &mut Rows) -> Result<(), FrameError> {
    let mut asked = 0_u64;
    let mut allowed = 0_u64;
    let mut limit: Option<HiringLimit> = None;
    for bound in bounds_of(result, w) {
        asked = add(asked, bound.asked_hours)?;
        allowed = add(allowed, bound.bound_hours)?;
        if limit.is_none_or(|held| limit_code(bound.limit) > limit_code(held)) {
            limit = Some(bound.limit);
        }
    }
    let Some(limit) = limit else {
        return Ok(());
    };
    rows.push(("Hours asked for the next period".to_owned(), grouped(asked)));
    rows.push((
        "Hours its money and inputs allow".to_owned(),
        grouped(allowed),
    ));
    rows.push(("Bound by".to_owned(), limit_words(limit).to_owned()));
    Ok(())
}

fn workplace_of_pool(pool: StaffingPoolId) -> Result<Workplace, FrameError> {
    Workplace::ALL
        .into_iter()
        .find(|w| w.pool_id() == pool)
        .ok_or_else(|| missing("a move of a pool of no workplace"))
}

/// The persons of the period's members of `h` at `w`'s site: `opening_employed`, summed.
fn employed_of(result: &PeriodResult, h: Household, w: Workplace) -> Result<u64, FrameError> {
    result
        .members
        .iter()
        .filter(|m| m.site_id == w.site_id() && m.member.household_id() == h.principal())
        .try_fold(0_u64, |sum, m| add(sum, m.opening_employed))
}

fn seeker_rows_of_workplace(
    result: &PeriodResult,
    w: Workplace,
    rows: &mut Rows,
) -> Result<(), FrameError> {
    let looked = result
        .members
        .iter()
        .filter(|m| m.site_id == w.site_id())
        .try_fold(0_u64, |sum, m| add(sum, m.closing_reserve))?;
    rows.push((
        format!("Looked for work in {}", w.place.label()),
        grouped(looked),
    ));
    let mut found: BTreeMap<Workplace, u64> = BTreeMap::new();
    let mut taken: BTreeMap<Household, u64> = BTreeMap::new();
    for moved in moves(result) {
        if moved.from_pool == w.pool_id() {
            let host = workplace_of_pool(moved.host_pool)?;
            let slot = found.entry(host).or_insert(0);
            *slot = add(*slot, moved.persons)?;
        }
        if moved.host_pool == w.pool_id() {
            let home = Household::from_principal(moved.household_id)
                .ok_or_else(|| missing("a move of a household of no world"))?;
            let slot = taken.entry(home).or_insert(0);
            *slot = add(*slot, moved.persons)?;
        }
    }
    for host in Workplace::ALL {
        if let Some(persons) = found.get(&host) {
            rows.push((format!("Found work at {}", host.label()), grouped(*persons)));
        }
    }
    for home in Household::ALL {
        if let Some(persons) = taken.get(&home) {
            rows.push((format!("Taken on from {}", home.label()), grouped(*persons)));
        }
    }
    for home in Household::ALL {
        if home == w.workers() {
            continue;
        }
        let employed = employed_of(result, home, w)?;
        if employed > 0 {
            rows.push((
                format!("Working here from {}", home.label()),
                grouped(employed),
            ));
        }
    }
    Ok(())
}

fn seeker_rows_of_household(
    result: &PeriodResult,
    h: Household,
    rows: &mut Rows,
) -> Result<(), FrameError> {
    for w in Workplace::ALL {
        let employed = employed_of(result, h, w)?;
        if employed > 0 {
            rows.push((format!("Worked at {}", w.label()), grouped(employed)));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::human_numbers;
    use crate::small_world::frame::{self, ParticleMode};
    use crate::small_world::inspect::Pick;
    use crate::small_world::reading::Party;
    use babylon_circuit_worlds::doubled::HOURS_PER_PERSON;
    use babylon_circuit_worlds::{
        Household, Kind, Lasts, Place, Places, Runner, Scale, Shock, Workplace, World,
    };
    use babylon_material_circuit::{AdjustmentRule, StopHold, StopReceipt};
    use std::error::Error;

    type TestResult = Result<(), Box<dyn Error>>;

    /// The first period of `fund-P2` of the seekers' set (`pc-seek-400`) in which a move is received.
    const FIRST_MOVE: u64 = 16;

    /// The bench's `fund-P2`: the fund world, the seekers on, the harvest failing in both places until lifted.
    fn fund_p2() -> Result<Runner, Box<dyn Error>> {
        let rules = vec![World::switches_at(Scale::Small)[1]];
        let mut runner = Runner::open_world(&World {
            rules,
            ..World::scene()
        })?;
        runner.strike(Shock::HarvestFails, Places::Both, Lasts::UntilLifted)?;
        Ok(runner)
    }

    fn row_of(rows: &[(String, String)], label: &str) -> Option<String> {
        rows.iter()
            .find(|(name, _)| name == label)
            .map(|(_, value)| value.clone())
    }

    /// The hours of the move are the household's `WorkFlow` to the host, in the groups and in the people.
    fn the_host_s_workforce_holds_the_movers(
        after: &PeriodResult,
        home: Household,
        host: Workplace,
        working: u64,
    ) -> TestResult {
        let given: u64 = frame::build_picture(after, ParticleMode::Groups)?
            .reading
            .work
            .iter()
            .filter(|f| f.household == home && f.workplace == host)
            .map(|f| f.given)
            .sum();
        assert!(given > 0);
        let groups = frame::build_picture(after, ParticleMode::Groups)?;
        let edge = frame::workforce_edge(host);
        let members = groups
            .sets
            .workforces
            .members_with_data(&edge)
            .ok_or("set")?;
        let held = members
            .iter()
            .find(|(m, _)| *m == frame::household_id(home))
            .map(|(_, hours)| **hours);
        assert_eq!(held, Some(given));
        let people = frame::build_picture(after, ParticleMode::People)?;
        let members = people
            .sets
            .workforces
            .members_with_data(&edge)
            .ok_or("set")?;
        let prefix = format!(
            "person:{}:",
            frame::household_id(home).trim_start_matches("household:")
        );
        let mine: Vec<u64> = members
            .iter()
            .filter(|(m, _)| m.starts_with(&prefix))
            .map(|(_, hours)| **hours)
            .collect();
        assert_eq!(u64::try_from(mine.len())?, working);
        assert!(mine.iter().all(|hours| *hours <= HOURS_PER_PERSON));
        assert_eq!(mine.iter().sum::<u64>(), given);
        Ok(())
    }

    #[test]
    fn a_move_is_read_from_its_receipts() -> TestResult {
        let mut runner = fund_p2()?;
        while runner
            .history()
            .last()
            .is_none_or(|r| r.period < FIRST_MOVE + 1)
        {
            runner.step()?;
        }
        let history = runner.history();
        let at = usize::try_from(FIRST_MOVE)? - 1;
        let result = &history[at];
        assert_eq!(result.period, FIRST_MOVE);
        assert!(history[..at].iter().all(|r| moves(r).next().is_none()));
        let first = moves(result).next().ok_or("no move in the pinned period")?;
        let host = Workplace::ALL
            .into_iter()
            .find(|w| w.pool_id() == first.host_pool)
            .ok_or("host")?;
        let from = Workplace::ALL
            .into_iter()
            .find(|w| w.pool_id() == first.from_pool)
            .ok_or("from")?;
        let home = Household::from_principal(first.household_id).ok_or("home")?;
        let taken: u64 = moves(result)
            .filter(|m| m.host_pool == first.host_pool && m.household_id == first.household_id)
            .map(|m| m.persons)
            .sum();
        let found: u64 = moves(result)
            .filter(|m| m.from_pool == first.from_pool && m.host_pool == first.host_pool)
            .map(|m| m.persons)
            .sum();
        assert!(taken > 0 && found > 0);
        let host_rows = rule_rows(history, at, &Pick::Body(Party::Workplace(host)))?;
        assert_eq!(
            row_of(&host_rows, &format!("Taken on from {}", home.label())),
            Some(human_numbers::grouped(u128::from(taken)))
        );
        let from_rows = rule_rows(history, at, &Pick::Body(Party::Workplace(from)))?;
        assert_eq!(
            row_of(&from_rows, &format!("Found work at {}", host.label())),
            Some(human_numbers::grouped(u128::from(found)))
        );
        // A move is for the next period: the host's "Taken on" is its "Working here" of the next one.
        let next = at + 1;
        let after = &history[next];
        let working: u64 = after
            .members
            .iter()
            .filter(|m| m.site_id == host.site_id() && m.member.household_id() == home.principal())
            .map(|m| m.opening_employed)
            .sum();
        assert!(working >= taken);
        let host_rows = rule_rows(history, next, &Pick::Body(Party::Workplace(host)))?;
        assert_eq!(
            row_of(&host_rows, &format!("Working here from {}", home.label())),
            Some(human_numbers::grouped(u128::from(working)))
        );
        let home_rows = rule_rows(history, next, &Pick::Body(Party::Household(home)))?;
        assert_eq!(
            row_of(&home_rows, &format!("Worked at {}", host.label())),
            Some(human_numbers::grouped(u128::from(working)))
        );
        let by_particle = rule_rows(history, next, &Pick::Particle(frame::household_id(home)))?;
        assert_eq!(by_particle, home_rows);
        the_host_s_workforce_holds_the_movers(after, home, host, working)?;
        Ok(())
    }

    /// The first period of `fund-P2` of the bound's set (`pc-bound-400`) whose close cuts some workplace by a
    /// limit other than none: farm A, by its inputs (`Inputs`, code 2). The bench's `bound_by_farm_a` of that run
    /// (`pc-bound-400/fund-P2.tsv`) is 2 from period 1 on, checked by hand once.
    const FIRST_CUT: u64 = 1;

    /// The bench's `fund-P2` of the bound's form: the bound and the seekers on, the harvest failing in both
    /// places until lifted.
    fn bound_fund_p2() -> Result<Runner, Box<dyn Error>> {
        let switches = World::switches_at(Scale::Small);
        let mut runner = Runner::open_world(&World {
            rules: vec![switches[0], switches[1]],
            ..World::scene()
        })?;
        runner.strike(Shock::HarvestFails, Places::Both, Lasts::UntilLifted)?;
        Ok(runner)
    }

    fn bound_of(result: &PeriodResult, w: Workplace) -> (u64, u64, Option<HiringLimit>) {
        let mut asked = 0_u64;
        let mut allowed = 0_u64;
        let mut limit: Option<HiringLimit> = None;
        for bound in bounds_of(result, w) {
            asked += bound.asked_hours;
            allowed += bound.bound_hours;
            if limit.is_none_or(|held| limit_code(bound.limit) > limit_code(held)) {
                limit = Some(bound.limit);
            }
        }
        (asked, allowed, limit)
    }

    #[test]
    fn the_bound_s_rows_are_its_receipt_s() -> TestResult {
        let farm = Workplace {
            place: Place::A,
            kind: Kind::Farm,
        };
        let mut result = Runner::open()?.step()?.clone();
        let pick = Pick::Body(Party::Workplace(farm));
        assert_eq!(rule_rows(&[result.clone()], 0, &pick)?, Rows::new());
        result.rules = vec![AdjustmentRule::HiringWithinMeans];
        // No receipt of the site, no row.
        assert_eq!(rule_rows(&[result.clone()], 0, &pick)?, Rows::new());
        let unit_id = result.members.first().ok_or("a member")?.unit_id;
        let words = [
            (HiringLimit::None, "nothing"),
            (HiringLimit::Capacity, "its capacity"),
            (HiringLimit::Inputs, "its inputs"),
            (HiringLimit::Money, "its money"),
            (HiringLimit::Other, "another limit"),
        ];
        for (limit, said) in words {
            assert_eq!(limit_words(limit), said);
        }
        let mut codes: Vec<u8> = words.iter().map(|(limit, _)| limit_code(*limit)).collect();
        codes.sort_unstable();
        assert_eq!(codes, vec![0, 1, 2, 3, 4]);
        for (limit, said) in words {
            let mut held = result.clone();
            held.receipts
                .adjustments
                .push(AdjustmentReceipt::HiringBound(HiringBoundReceipt {
                    period: held.period + 1,
                    site_id: farm.site_id(),
                    unit_id,
                    asked_hours: 40,
                    bound_hours: 30,
                    limit,
                }));
            let rows = rule_rows(&[held], 0, &pick)?;
            assert_eq!(
                rows,
                vec![
                    (
                        "Hours asked for the next period".to_owned(),
                        "40".to_owned()
                    ),
                    (
                        "Hours its money and inputs allow".to_owned(),
                        "30".to_owned()
                    ),
                    ("Bound by".to_owned(), said.to_owned()),
                ]
            );
        }
        Ok(())
    }

    #[test]
    fn the_bound_reads_as_the_bench_counts_it() -> TestResult {
        let mut runner = bound_fund_p2()?;
        while runner
            .history()
            .last()
            .is_none_or(|r| r.period < FIRST_CUT + 1)
        {
            runner.step()?;
        }
        let history = runner.history();
        let cut_at = usize::try_from(FIRST_CUT)? - 1;
        let first_cut = |result: &PeriodResult| {
            Workplace::ALL
                .into_iter()
                .find(|w| bounds_of(result, *w).any(|bound| bound.limit != HiringLimit::None))
        };
        assert!(history[..cut_at].iter().all(|r| first_cut(r).is_none()));
        let site = first_cut(&history[cut_at]).ok_or("no cut in the pinned period")?;
        let rows = rule_rows(history, cut_at, &Pick::Body(Party::Workplace(site)))?;
        assert_ne!(row_of(&rows, "Bound by"), Some("nothing".to_owned()));
        assert!(row_of(&rows, "Bound by").is_some());
        for (index, result) in history[..=cut_at].iter().enumerate() {
            for w in Workplace::ALL {
                let rows = rule_rows(history, index, &Pick::Body(Party::Workplace(w)))?;
                let (asked, allowed, limit) = bound_of(result, w);
                match limit {
                    None => assert!(row_of(&rows, "Bound by").is_none()),
                    Some(limit) => {
                        assert_eq!(
                            row_of(&rows, "Hours asked for the next period"),
                            Some(human_numbers::grouped(u128::from(asked)))
                        );
                        assert_eq!(
                            row_of(&rows, "Hours its money and inputs allow"),
                            Some(human_numbers::grouped(u128::from(allowed)))
                        );
                        assert_eq!(
                            row_of(&rows, "Bound by"),
                            Some(limit_words(limit).to_owned())
                        );
                    }
                }
            }
        }
        Ok(())
    }

    fn clinic_a() -> Workplace {
        Workplace {
            place: Place::A,
            kind: Kind::Clinic,
        }
    }

    /// Seven copies of a quiet period, periods 1 to 7, the stop rule asked; clinic A is `Free` at 4 and `Held`
    /// at 5, 6 and 7 (limit 0, could not pay). In the seventh each of its members left 3 hours unattended.
    fn stop_history() -> Result<(Vec<PeriodResult>, u64), Box<dyn Error>> {
        let base = Runner::open()?.step()?.clone();
        let site = clinic_a().site_id();
        let mut history = Vec::new();
        for period in 1..=7_u64 {
            let mut result = base.clone();
            result.period = period;
            result.rules = vec![AdjustmentRule::StopWithoutPay];
            let held = period >= 5;
            result
                .receipts
                .adjustments
                .push(AdjustmentReceipt::Stop(StopReceipt {
                    period,
                    site_id: site,
                    could_not_pay: held,
                    hold: if held { StopHold::Held } else { StopHold::Free },
                    limit: held.then_some(0),
                }));
            history.push(result);
        }
        let mut unattended = 0_u64;
        for row in &mut history[6].receipts.member_labor_use {
            if row.site_id == site {
                row.unattended_hours = 3;
                unattended += 3;
            }
        }
        assert!(unattended > 0, "the clinic has members to leave unpaid");
        Ok((history, unattended))
    }

    #[test]
    fn held_since_counts_the_unbroken_run() -> TestResult {
        let (history, _) = stop_history()?;
        let clinic = clinic_a();
        assert_eq!(held_since(&history, 6, clinic), Some(5));
        assert_eq!(held_since(&history, 4, clinic), Some(5));
        assert_eq!(held_since(&history, 3, clinic), None);
        assert_eq!(
            held_since(
                &history,
                6,
                Workplace {
                    place: Place::A,
                    kind: Kind::Farm
                }
            ),
            None
        );
        Ok(())
    }

    #[test]
    fn the_stop_s_rows_are_its_receipt_s() -> TestResult {
        let (history, unattended) = stop_history()?;
        let pick = Pick::Body(Party::Workplace(clinic_a()));
        let rows = rule_rows(&history, 6, &pick)?;
        assert_eq!(
            rows,
            vec![
                (
                    "No money, no work".to_owned(),
                    "held since period 5".to_owned()
                ),
                ("Most it may employ".to_owned(), "0".to_owned()),
                (
                    "Hours it could not pay".to_owned(),
                    human_numbers::grouped(u128::from(unattended))
                ),
            ]
        );
        // A free workplace that paid gets no row; a period the rule is not asked in adds none.
        assert_eq!(rule_rows(&history, 3, &pick)?, Rows::new());
        let mut unasked = history.clone();
        unasked[6].rules = Vec::new();
        assert_eq!(rule_rows(&unasked, 6, &pick)?, Rows::new());
        Ok(())
    }

    #[test]
    fn every_close_with_the_rule_tests_every_site() -> TestResult {
        let switches = World::switches_at(Scale::Small);
        let mut runner = Runner::open()?;
        runner.turn_on(switches[1])?;
        runner.turn_on(switches[2])?;
        for _ in 0..34 {
            runner.step()?;
        }
        let history = runner.history();
        assert_eq!(history.len(), 34);
        for (index, result) in history.iter().enumerate() {
            let stops: Vec<&StopReceipt> = result
                .receipts
                .adjustments
                .iter()
                .filter_map(|receipt| match receipt {
                    AdjustmentReceipt::Stop(stop) => Some(stop),
                    AdjustmentReceipt::HiringBound(_) | AdjustmentReceipt::PlaceMove(_) => None,
                })
                .collect();
            assert_eq!(stops.len(), 8, "period {}", result.period);
            for w in Workplace::ALL {
                let stop = stops
                    .iter()
                    .find(|stop| stop.site_id == w.site_id())
                    .ok_or("a receipt for each site")?;
                let rows = rule_rows(history, index, &Pick::Body(Party::Workplace(w)))?;
                let stop_rows: Vec<&(String, String)> = rows
                    .iter()
                    .filter(|(label, _)| {
                        matches!(
                            label.as_str(),
                            "No money, no work" | "Most it may employ" | "Hours it could not pay"
                        )
                    })
                    .collect();
                let unpaid: u64 = result
                    .receipts
                    .member_labor_use
                    .iter()
                    .filter(|row| row.site_id == w.site_id())
                    .map(|row| row.unattended_hours)
                    .sum();
                let expected = usize::from(stop.hold == StopHold::Held)
                    + usize::from(stop.hold == StopHold::Held && stop.limit.is_some())
                    + usize::from(stop.could_not_pay);
                assert_eq!(
                    stop_rows.len(),
                    expected,
                    "{w:?} in period {}",
                    result.period
                );
                if stop.could_not_pay {
                    assert_eq!(
                        row_of(&rows, "Hours it could not pay"),
                        Some(human_numbers::grouped(u128::from(unpaid)))
                    );
                }
            }
        }
        Ok(())
    }
}
