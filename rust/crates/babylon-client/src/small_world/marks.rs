//! The rules' receipts as rows of the panel: every row is a sum of the fields of one period's receipts, and a
//! period the rule does not hold in adds none.

use super::frame::FrameError;
use super::inspect::{self, Pick};
use super::reading::Party;
use super::rules::SceneRule;
use crate::human_numbers;
use babylon_circuit_worlds::{Household, PeriodResult, Workplace};
use babylon_material_circuit::{AdjustmentReceipt, PlaceMoveReceipt, StaffingPoolId};
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
    if !holds(result, SceneRule::SeekingInPlace) {
        return Ok(rows);
    }
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
            AdjustmentReceipt::HiringBound(_) => None,
        })
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
        Household, Lasts, Places, Runner, Scale, Shock, Workplace, World,
    };
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
}
