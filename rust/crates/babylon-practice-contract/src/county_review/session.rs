//! The county's session: the contact lands, the list is made and paid down, households ask, come
//! and bring one more.
//!
//! One function for each numbered step of design 7.4 and of the plan's `hold_session`. Every step
//! runs on whole households, whole units and exact fractions. The list is worked out once, from
//! the top; no step is repeated. No rule reads an identifier or a band: ties are settled by the
//! order of the answers and by `apportion`.
use serde::{Deserialize, Serialize};

use super::place;
use super::place::Place;
use super::roster;
use super::split;
use super::split::Ties;
use super::types::{
    CountyPeriodFacts, CountyReviewConfig, CountyReviewError, GroupKind, PositionKey, Roster,
};

/// What came of the organizer's contact.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ContactOutcome {
    /// A household of the position is reached.
    Reached,
    /// Every household of the position was already reached.
    NobodyLeft,
    /// The roster has no such position.
    NoSuchPosition,
}

/// What the session did for one position. Households of a position cannot be told apart, so
/// every figure is a count.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SessionRow {
    /// The position.
    pub key: PositionKey,
    /// 1 for the highest place; equal places share a rank; places of zero share the last rank.
    pub rank: u32,
    /// Households in the position.
    pub households: u64,
    /// Households reached, after the contact lands.
    pub reached: u64,
    /// Units the position holds on the roll.
    pub units_listed: u64,
    /// Of those, the units the county pays.
    pub units_paid: u64,
    /// Of those, the units the county does not pay.
    pub units_unpaid: u64,
    /// Households that asked for a unit.
    pub asked: u64,
    /// Of those, households the county paid.
    pub asked_paid: u64,
    /// Of those, households the county could not reach with its money.
    pub asked_no_place: u64,
    /// Reached households that wanted to ask and had no hours.
    pub asked_no_time: u64,
    /// Households that lose at least one unit.
    pub losers: u64,
    /// Of those, the reached households.
    pub losers_reached: u64,
    /// Reached households that came because the county did not pay a unit they hold.
    pub came_from_roll: u64,
    /// Reached households that would have come from the roll and had no hours.
    pub roll_no_time: u64,
    /// Reached households that hold a unit and lose none.
    pub nothing_at_stake: u64,
    /// Reached households whose stake is below the floor.
    pub not_worth_time: u64,
    /// Households brought, reached from the next session.
    pub brought: u64,
    /// Hours spent in the room.
    pub hours_in_room: u64,
    /// Hours spent bringing.
    pub hours_bringing: u64,
}

/// A line the county sets for the next close: a group's units and amount.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SupportLine {
    /// Index of the group.
    pub group: u32,
    /// Units the line is for.
    pub units: u64,
    /// The amount, in millionths of a dollar.
    #[serde(with = "super::decimal")]
    pub amount_micros: i128,
}

/// Hours a group's households spend in the session.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct HourCharge {
    /// Index of the group.
    pub group: u32,
    /// Hours charged.
    pub hours: u64,
}

/// What the county publishes about one session.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SessionRecord {
    /// The period just closed.
    pub period: u64,
    /// The county's cash.
    #[serde(with = "super::decimal")]
    pub cash_micros: i128,
    /// The spending limit.
    #[serde(with = "super::decimal")]
    pub spending_limit_micros: i128,
    /// The first class.
    #[serde(with = "super::decimal")]
    pub first_class_micros: i128,
    /// The roll's total, collective residence included.
    #[serde(with = "super::decimal")]
    pub roll_total_micros: i128,
    /// The money for relief.
    #[serde(with = "super::decimal")]
    pub relief_micros: i128,
    /// The collective-residence lines, cut in proportion when the county is short.
    pub collective_lines: Vec<SupportLine>,
    /// Units the households hold on the roll.
    pub household_units_listed: u64,
    /// Units the county can pay to households.
    pub household_units_payable: u64,
    /// Units an exact tie left unpaid.
    pub kept_back_units: u64,
    /// The contact and what came of it.
    pub contact: Option<(PositionKey, ContactOutcome)>,
    /// One row for every position of the roster, in the roster's order.
    pub rows: Vec<SessionRow>,
    /// The household lines for the next close, in group order.
    pub lines: Vec<SupportLine>,
    /// Households that came from the roll: the Claimants' Assembly's.
    pub claimants_roll_households: u64,
    /// Households that asked and were paid: the aid partners'.
    pub aid_roll_households: u64,
}

/// A session's record, the roster with the new reach, and the hours it cost.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SessionOutcome {
    /// The published record.
    pub record: SessionRecord,
    /// The roster with the contact and the households brought. It is not rolled forward.
    pub roster: Roster,
    /// Hours to charge each group, omitted when zero.
    pub hour_charges: Vec<HourCharge>,
}

/// A row being worked, and its place.
struct Work {
    row: SessionRow,
    place: Place,
}

fn add(a: u64, b: u64) -> Result<u64, CountyReviewError> {
    a.checked_add(b).ok_or(CountyReviewError::Arithmetic)
}

fn sub(a: u64, b: u64) -> Result<u64, CountyReviewError> {
    a.checked_sub(b).ok_or(CountyReviewError::Arithmetic)
}

fn mul(a: u64, b: u64) -> Result<u64, CountyReviewError> {
    a.checked_mul(b).ok_or(CountyReviewError::Arithmetic)
}

fn micros(units: u64, price: i128) -> Result<i128, CountyReviewError> {
    i128::from(units)
        .checked_mul(price)
        .ok_or(CountyReviewError::Arithmetic)
}

fn to_index(value: u32) -> Result<usize, CountyReviewError> {
    usize::try_from(value).map_err(|_| CountyReviewError::Arithmetic)
}

fn to_group(index: usize) -> Result<u32, CountyReviewError> {
    u32::try_from(index).map_err(|_| CountyReviewError::Arithmetic)
}

fn sum<I: Iterator<Item = Result<u64, CountyReviewError>>>(
    mut values: I,
) -> Result<u64, CountyReviewError> {
    values.try_fold(0_u64, |total, value| add(total, value?))
}

/// Step 1: the roster follows the engine's sums for every crew.
fn check_inputs(
    config: &CountyReviewConfig,
    roster: &Roster,
    facts: &CountyPeriodFacts,
) -> Result<(), CountyReviewError> {
    roster::validate_county_review_config(config)?;
    roster::validate_roster(config, roster)?;
    roster::check_facts_shape(config, facts)?;
    for crew in &facts.crews {
        if roster.crew_at_work(crew.crew) != crew.opening_at_work
            || roster.crew_seeking(crew.crew) != crew.opening_seeking
        {
            return Err(CountyReviewError::RosterEngineMismatch);
        }
    }
    Ok(())
}

/// Step 2: the contact lands in its position, if the position exists and has a household left.
fn land_contact(
    roster: &mut Roster,
    contact: Option<PositionKey>,
) -> Result<Option<(PositionKey, ContactOutcome)>, CountyReviewError> {
    let Some(key) = contact else {
        return Ok(None);
    };
    let outcome = match roster.rows.binary_search_by_key(&key, |row| row.key) {
        Err(_) => ContactOutcome::NoSuchPosition,
        Ok(index) => {
            let row = roster
                .rows
                .get_mut(index)
                .ok_or(CountyReviewError::RosterShape)?;
            if row.reached >= row.households {
                ContactOutcome::NobodyLeft
            } else {
                row.reached = add(row.reached, 1)?;
                ContactOutcome::Reached
            }
        }
    };
    Ok(Some((key, outcome)))
}

/// The money for relief and the units it pays.
struct Money {
    listed: u64,
    roll_total_micros: i128,
    relief_micros: i128,
    collective_lines: Vec<SupportLine>,
    payable: u64,
}

/// Step 3: the county announces its money for relief and the household units it pays.
fn announce_money(
    config: &CountyReviewConfig,
    facts: &CountyPeriodFacts,
    roster: &Roster,
) -> Result<Money, CountyReviewError> {
    let price = config.unit_price_micros;
    let listed = sum(roster
        .rows
        .iter()
        .map(|row| mul(u64::from(row.key.units), row.households)))?;
    let mut collective: Vec<(u32, u64)> = Vec::new();
    for (index, group) in config.groups.iter().enumerate() {
        if group.kind == GroupKind::CollectiveResidence {
            collective.push((to_group(index)?, group.roll_units));
        }
    }
    let collective_units = sum(collective.iter().map(|(_, units)| Ok(*units)))?;
    let roll_total = micros(add(listed, collective_units)?, price)?;
    let budget = facts
        .cash_micros
        .checked_sub(facts.cash_floor_micros)
        .ok_or(CountyReviewError::Arithmetic)?
        .min(facts.spending_limit_micros)
        .max(0);
    let relief = budget
        .checked_sub(facts.first_class_micros)
        .ok_or(CountyReviewError::Arithmetic)?
        .max(0)
        .min(roll_total);
    let whole = relief == roll_total;
    let mut collective_lines = Vec::new();
    let mut collective_paid = 0_i128;
    for (group, units) in collective {
        let full = micros(units, price)?;
        let amount = if whole {
            full
        } else {
            relief
                .checked_mul(full)
                .ok_or(CountyReviewError::Arithmetic)?
                / roll_total
        };
        collective_paid = collective_paid
            .checked_add(amount)
            .ok_or(CountyReviewError::Arithmetic)?;
        if amount > 0 {
            collective_lines.push(SupportLine {
                group,
                units,
                amount_micros: amount,
            });
        }
    }
    let payable = if whole {
        listed
    } else {
        let left = relief
            .checked_sub(collective_paid)
            .ok_or(CountyReviewError::Arithmetic)?;
        u64::try_from(left / price)
            .map_err(|_| CountyReviewError::Arithmetic)?
            .min(listed)
    };
    Ok(Money {
        listed,
        roll_total_micros: roll_total,
        relief_micros: relief,
        collective_lines,
        payable,
    })
}

/// Step 4: the place of every position, from the period's wages, people and tax receipts.
fn rank_positions(
    facts: &CountyPeriodFacts,
    roster: &Roster,
) -> Result<Vec<Work>, CountyReviewError> {
    let mut work = Vec::with_capacity(roster.rows.len());
    for row in &roster.rows {
        let position = match row.key.crew {
            None => Place::ZERO,
            Some(crew) => {
                let crew_facts = facts
                    .crews
                    .get(to_index(crew)?)
                    .ok_or(CountyReviewError::UnknownCrew)?;
                let group_facts = facts
                    .groups
                    .get(to_index(row.key.group)?)
                    .ok_or(CountyReviewError::UnknownGroup)?;
                place::place(
                    row.key.at_work,
                    crew_facts.accrued_wages_micros,
                    roster.crew_at_work(crew),
                    group_facts.wage_tax_collected_micros,
                    group_facts.taxed_wages_micros,
                )?
            }
        };
        let units_listed = mul(u64::from(row.key.units), row.households)?;
        work.push(Work {
            place: position,
            row: SessionRow {
                key: row.key,
                rank: 0,
                households: row.households,
                reached: row.reached,
                units_listed,
                units_paid: 0,
                units_unpaid: units_listed,
                asked: 0,
                asked_paid: 0,
                asked_no_place: 0,
                asked_no_time: 0,
                losers: 0,
                losers_reached: 0,
                came_from_roll: 0,
                roll_no_time: 0,
                nothing_at_stake: 0,
                not_worth_time: 0,
                brought: 0,
                hours_in_room: 0,
                hours_bringing: 0,
            },
        });
    }
    give_ranks(&mut work)?;
    Ok(work)
}

/// Positions in the order of the list: highest place first, the roster's order inside a place.
fn by_place(work: &[Work], indices: impl Iterator<Item = usize>) -> Vec<(Place, usize)> {
    let mut ordered: Vec<(Place, usize)> = indices
        .map(|index| (work.get(index).map_or(Place::ZERO, |w| w.place), index))
        .collect();
    ordered.sort_by(|a, b| b.0.cmp(&a.0).then(a.1.cmp(&b.1)));
    ordered
}

/// Rank 1 is the highest place. Equal places share a rank and ranks follow one another, so places
/// of zero share the last rank.
fn give_ranks(work: &mut [Work]) -> Result<(), CountyReviewError> {
    let ordered = by_place(work, 0..work.len());
    let mut rank = 0_u32;
    for class in ordered.chunk_by(|a, b| a.0 == b.0) {
        rank = rank.checked_add(1).ok_or(CountyReviewError::Arithmetic)?;
        for (_, index) in class {
            work.get_mut(*index)
                .ok_or(CountyReviewError::RosterShape)?
                .row
                .rank = rank;
        }
    }
    Ok(())
}

/// Rows of each group, in the roster's order.
fn rows_by_group(
    config: &CountyReviewConfig,
    work: &[Work],
) -> Result<Vec<Vec<usize>>, CountyReviewError> {
    let mut groups = vec![Vec::new(); config.groups.len()];
    for (index, w) in work.iter().enumerate() {
        groups
            .get_mut(to_index(w.row.key.group)?)
            .ok_or(CountyReviewError::UnknownGroup)?
            .push(index);
    }
    Ok(groups)
}

/// Gives households hours, a group's pool at one place at a time, highest place first.
///
/// `wants` is a row and the households that want `per_household` hours each. The households a
/// pool of equal places may take are `min(pool, hours / per_household)`, shared by `apportion`
/// with `Withhold`, so two positions at one place never differ by an identifier. Returns every
/// row's grant, zero included, and takes the hours from `hours`.
fn allot(
    work: &[Work],
    wants: &[(usize, u64)],
    hours: &mut u64,
    per_household: u64,
) -> Result<Vec<(usize, u64)>, CountyReviewError> {
    let mut ordered: Vec<(Place, usize, u64)> = wants
        .iter()
        .map(|(index, want)| {
            (
                work.get(*index).map_or(Place::ZERO, |w| w.place),
                *index,
                *want,
            )
        })
        .collect();
    ordered.sort_by(|a, b| b.0.cmp(&a.0).then(a.1.cmp(&b.1)));
    let mut granted = Vec::with_capacity(ordered.len());
    for pool in ordered.chunk_by(|a, b| a.0 == b.0) {
        let weights: Vec<u64> = pool.iter().map(|(_, _, want)| *want).collect();
        let wanted = sum(weights.iter().map(|w| Ok(*w)))?;
        // Hours that cost nothing set no limit.
        let room = hours.checked_div(per_household).unwrap_or(u64::MAX);
        let shares = split::apportion(wanted.min(room), &weights, Ties::Withhold)?.shares;
        let used = sum(shares.iter().map(|s| Ok(*s)))?;
        *hours = sub(*hours, mul(used, per_household)?)?;
        granted.extend(
            pool.iter()
                .zip(shares)
                .map(|((_, index, _), share)| (*index, share)),
        );
    }
    Ok(granted)
}

/// The least a stake must be worth for a household to give a session its hours.
fn floor_micros(config: &CountyReviewConfig) -> Result<i128, CountyReviewError> {
    micros(config.session_hours, config.going_wage_micros)
}

/// Step 5: reached households that hold no unit ask for one, if their group has hours.
fn who_asks(
    config: &CountyReviewConfig,
    work: &mut [Work],
    by_group: &[Vec<usize>],
    hours: &mut [u64],
) -> Result<(), CountyReviewError> {
    let worth_it = config.unit_price_micros >= floor_micros(config)?;
    for (members, group_hours) in by_group.iter().zip(hours.iter_mut()) {
        let wants: Vec<(usize, u64)> = members
            .iter()
            .filter_map(|&index| {
                let row = &work.get(index)?.row;
                (row.key.units == 0 && row.reached > 0).then_some((index, row.reached))
            })
            .collect();
        if !worth_it {
            for (index, want) in wants {
                set(work, index, |row| row.not_worth_time = want)?;
            }
            continue;
        }
        for (index, granted) in allot(work, &wants, group_hours, config.session_hours)? {
            let reached = row_of(work, index)?.reached;
            let no_time = sub(reached, granted)?;
            set(work, index, |row| {
                row.asked = granted;
                row.asked_no_time = no_time;
            })?;
        }
    }
    Ok(())
}

fn row_of(work: &[Work], index: usize) -> Result<&SessionRow, CountyReviewError> {
    work.get(index)
        .map(|w| &w.row)
        .ok_or(CountyReviewError::RosterShape)
}

fn set(
    work: &mut [Work],
    index: usize,
    change: impl FnOnce(&mut SessionRow),
) -> Result<(), CountyReviewError> {
    let w = work.get_mut(index).ok_or(CountyReviewError::RosterShape)?;
    change(&mut w.row);
    Ok(())
}

/// Pays what `left` covers to the rows of one class, in proportion to what each wants, and returns
/// what is left, and the units an exact tie kept back.
fn settle(
    work: &mut [Work],
    wants: &[(usize, u64)],
    left: u64,
    write: impl Fn(&mut SessionRow, u64),
) -> Result<(u64, u64), CountyReviewError> {
    let total = sum(wants.iter().map(|(_, want)| Ok(*want)))?;
    if left >= total {
        for (index, want) in wants {
            set(work, *index, |row| write(row, *want))?;
        }
        return Ok((sub(left, total)?, 0));
    }
    let weights: Vec<u64> = wants.iter().map(|(_, want)| *want).collect();
    let split = split::apportion(left, &weights, Ties::Withhold)?;
    for ((index, _), share) in wants.iter().zip(split.shares) {
        set(work, *index, |row| write(row, share))?;
    }
    Ok((0, split.withheld))
}

/// Step 6: the county pays down the list from the top. In each class of equal places the rows
/// that hold units come first, then the rows that asked. Returns the units an exact tie kept back.
fn pay_down_list(work: &mut [Work], payable: u64) -> Result<u64, CountyReviewError> {
    let mut left = payable;
    let mut kept_back = 0_u64;
    let ordered = by_place(work, 0..work.len());
    for class in ordered.chunk_by(|a, b| a.0 == b.0) {
        let members: Vec<usize> = class.iter().map(|(_, index)| *index).collect();
        let holders: Vec<(usize, u64)> = members
            .iter()
            .filter_map(|&i| row_of(work, i).ok().map(|row| (i, row.units_listed)))
            .filter(|(_, listed)| *listed > 0)
            .collect();
        let (after_holders, withheld) = settle(work, &holders, left, |row, paid| {
            row.units_paid = paid;
        })?;
        kept_back = add(kept_back, withheld)?;
        let askers: Vec<(usize, u64)> = members
            .iter()
            .filter_map(|&i| row_of(work, i).ok().map(|row| (i, row.asked)))
            .filter(|(_, asked)| *asked > 0)
            .collect();
        let (after_askers, withheld) = settle(work, &askers, after_holders, |row, paid| {
            row.asked_paid = paid;
        })?;
        kept_back = add(kept_back, withheld)?;
        left = after_askers;
    }
    for w in work.iter_mut() {
        w.row.units_unpaid = sub(w.row.units_listed, w.row.units_paid)?;
    }
    Ok(kept_back)
}

/// Step 7: askers the county's money did not reach stay home and give their hours back.
fn askers_come_or_stay(
    config: &CountyReviewConfig,
    work: &mut [Work],
    by_group: &[Vec<usize>],
    hours: &mut [u64],
) -> Result<(), CountyReviewError> {
    for (members, group_hours) in by_group.iter().zip(hours.iter_mut()) {
        for &index in members {
            let (asked, paid) = {
                let row = row_of(work, index)?;
                (row.asked, row.asked_paid)
            };
            let stayed = sub(asked, paid)?;
            set(work, index, |row| row.asked_no_place = stayed)?;
            *group_hours = add(*group_hours, mul(stayed, config.session_hours)?)?;
        }
    }
    Ok(())
}

/// How a row's unpaid units fall on its households, a household at a time.
struct Losses {
    /// Reached households that lose all their units.
    reached_in_full: u64,
    /// Reached households that lose only part of their units: zero or one.
    reached_in_part: u64,
    /// The units that household loses.
    part_units: u64,
}

/// A row's losers, and which of the reached ones lose everything.
///
/// The unpaid units are taken a household at a time, so `ceil(unpaid / units)` households lose.
/// They are reached and unreached households in proportion to their numbers, an exact tie falling
/// on the unreached. If one household loses fewer than all its units, it is an unreached one when
/// the row has an unreached loser.
fn split_losses(row: &mut SessionRow) -> Result<Losses, CountyReviewError> {
    let units = u64::from(row.key.units);
    if units == 0 {
        return Ok(Losses {
            reached_in_full: 0,
            reached_in_part: 0,
            part_units: 0,
        });
    }
    row.losers = row.units_unpaid.div_ceil(units);
    let unreached = sub(row.households, row.reached)?;
    let shares = split::apportion(row.losers, &[unreached, row.reached], Ties::InOrder)?.shares;
    row.losers_reached = shares
        .get(1)
        .copied()
        .ok_or(CountyReviewError::Arithmetic)?;
    let part_units = row.units_unpaid % units;
    let unreached_losers = sub(row.losers, row.losers_reached)?;
    if part_units == 0 || unreached_losers > 0 {
        return Ok(Losses {
            reached_in_full: row.losers_reached,
            reached_in_part: 0,
            part_units,
        });
    }
    Ok(Losses {
        reached_in_full: sub(row.losers_reached, 1)?,
        reached_in_part: 1,
        part_units,
    })
}

/// Reached losers whose stake covers their time, per row. Records the losers, those at nothing's
/// stake and those below the floor.
fn count_losers(
    config: &CountyReviewConfig,
    work: &mut [Work],
) -> Result<Vec<u64>, CountyReviewError> {
    let floor = floor_micros(config)?;
    let price = config.unit_price_micros;
    let mut willing = Vec::with_capacity(work.len());
    for w in work.iter_mut() {
        let row = &mut w.row;
        let losses = split_losses(row)?;
        let units = u64::from(row.key.units);
        let mut worth_it = 0_u64;
        if micros(units, price)? >= floor {
            worth_it = add(worth_it, losses.reached_in_full)?;
        }
        if micros(losses.part_units, price)? >= floor {
            worth_it = add(worth_it, losses.reached_in_part)?;
        }
        if units > 0 {
            row.nothing_at_stake = sub(row.reached, row.losers_reached)?;
            row.not_worth_time = sub(row.losers_reached, worth_it)?;
        }
        willing.push(worth_it);
    }
    Ok(willing)
}

/// Step 8: reached households that lose a unit come, if their stake covers their time and their
/// group has the hours, highest place first.
fn losers_come(
    config: &CountyReviewConfig,
    work: &mut [Work],
    by_group: &[Vec<usize>],
    hours: &mut [u64],
) -> Result<(), CountyReviewError> {
    let willing = count_losers(config, work)?;
    for (members, group_hours) in by_group.iter().zip(hours.iter_mut()) {
        let wants: Vec<(usize, u64)> = members
            .iter()
            .filter_map(|&index| {
                willing
                    .get(index)
                    .filter(|count| **count > 0)
                    .map(|count| (index, *count))
            })
            .collect();
        for (index, share) in allot(work, &wants, group_hours, config.session_hours)? {
            let want = willing
                .get(index)
                .copied()
                .ok_or(CountyReviewError::RosterShape)?;
            let no_time = sub(want, share)?;
            set(work, index, |row| {
                row.came_from_roll = share;
                row.roll_no_time = no_time;
            })?;
        }
    }
    Ok(())
}

/// Step 9: each household that came brings one more of its own position, if the position has one
/// left and the group has the hours. Raises `reached` in the returned roster.
fn spread(
    config: &CountyReviewConfig,
    work: &mut [Work],
    by_group: &[Vec<usize>],
    hours: &mut [u64],
) -> Result<(), CountyReviewError> {
    for (members, group_hours) in by_group.iter().zip(hours.iter_mut()) {
        let mut wants = Vec::new();
        for &index in members {
            let row = row_of(work, index)?;
            let came = add(row.asked_paid, row.came_from_roll)?;
            let left = sub(row.households, row.reached)?;
            if came.min(left) > 0 {
                wants.push((index, came.min(left)));
            }
        }
        for (index, brought) in allot(work, &wants, group_hours, config.bring_hours)? {
            set(work, index, |row| row.brought = brought)?;
        }
    }
    Ok(())
}

/// Step 10: a group's line is the units its positions hold on the list, added up, at the unit
/// price. A group with no unit has no line.
fn support_lines(
    config: &CountyReviewConfig,
    work: &[Work],
) -> Result<Vec<SupportLine>, CountyReviewError> {
    let mut units = vec![0_u64; config.groups.len()];
    for w in work {
        let slot = units
            .get_mut(to_index(w.row.key.group)?)
            .ok_or(CountyReviewError::UnknownGroup)?;
        *slot = add(*slot, add(w.row.units_paid, w.row.asked_paid)?)?;
    }
    let mut lines = Vec::new();
    for (index, held) in units.into_iter().enumerate() {
        if held > 0 {
            lines.push(SupportLine {
                group: to_group(index)?,
                units: held,
                amount_micros: micros(held, config.unit_price_micros)?,
            });
        }
    }
    Ok(lines)
}

/// Step 11: each group is charged the room's hours for each household that came and the bringing
/// hours for each household brought. A group that spent none is omitted.
fn hour_charges(
    config: &CountyReviewConfig,
    work: &mut [Work],
) -> Result<Vec<HourCharge>, CountyReviewError> {
    let mut hours = vec![0_u64; config.groups.len()];
    for w in work.iter_mut() {
        let row = &mut w.row;
        row.hours_in_room = mul(
            add(row.asked_paid, row.came_from_roll)?,
            config.session_hours,
        )?;
        row.hours_bringing = mul(row.brought, config.bring_hours)?;
        let slot = hours
            .get_mut(to_index(row.key.group)?)
            .ok_or(CountyReviewError::UnknownGroup)?;
        *slot = add(*slot, add(row.hours_in_room, row.hours_bringing)?)?;
    }
    let mut charges = Vec::new();
    for (index, spent) in hours.into_iter().enumerate() {
        if spent > 0 {
            charges.push(HourCharge {
                group: to_group(index)?,
                hours: spent,
            });
        }
    }
    Ok(charges)
}

/// Holds one session of the county.
///
/// The roster is the households as they stood during the period just closed, `facts` are the
/// engine's labor and tax facts of that close, and `contact` is the position the organizer
/// reached. The outcome carries the record, the roster with the new reach (not rolled forward) and
/// the hours each group spent.
///
/// # Errors
///
/// `RosterEngineMismatch` when a crew's sums in the roster differ from the engine's, `FactsShape`
/// for facts that do not hold every crew and group, the refusals of the configuration and the
/// roster, and `Arithmetic` for a sum or product that leaves its range. A contact with no position
/// or no household left is not an error: the record says so.
pub fn hold_session(
    config: &CountyReviewConfig,
    roster: &Roster,
    facts: &CountyPeriodFacts,
    contact: Option<PositionKey>,
) -> Result<SessionOutcome, CountyReviewError> {
    check_inputs(config, roster, facts)?;
    let mut after = roster.clone();
    let contact = land_contact(&mut after, contact)?;
    let money = announce_money(config, facts, &after)?;
    let mut work = rank_positions(facts, &after)?;
    let by_group = rows_by_group(config, &work)?;
    let mut hours: Vec<u64> = facts.groups.iter().map(|g| g.free_hours).collect();
    who_asks(config, &mut work, &by_group, &mut hours)?;
    let kept_back_units = pay_down_list(&mut work, money.payable)?;
    askers_come_or_stay(config, &mut work, &by_group, &mut hours)?;
    losers_come(config, &mut work, &by_group, &mut hours)?;
    spread(config, &mut work, &by_group, &mut hours)?;
    let lines = support_lines(config, &work)?;
    let hour_charges = hour_charges(config, &mut work)?;
    for (row, w) in after.rows.iter_mut().zip(&work) {
        row.reached = add(row.reached, w.row.brought)?;
    }
    let claimants_roll_households = sum(work.iter().map(|w| Ok(w.row.came_from_roll)))?;
    let aid_roll_households = sum(work.iter().map(|w| Ok(w.row.asked_paid)))?;
    let record = SessionRecord {
        period: facts.period,
        cash_micros: facts.cash_micros,
        spending_limit_micros: facts.spending_limit_micros,
        first_class_micros: facts.first_class_micros,
        roll_total_micros: money.roll_total_micros,
        relief_micros: money.relief_micros,
        collective_lines: money.collective_lines,
        household_units_listed: money.listed,
        household_units_payable: money.payable,
        kept_back_units,
        contact,
        rows: work.into_iter().map(|w| w.row).collect(),
        lines,
        claimants_roll_households,
        aid_roll_households,
    };
    Ok(SessionOutcome {
        record,
        roster: after,
        hour_charges,
    })
}
