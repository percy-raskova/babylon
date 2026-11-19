//! The county's places, its list and its session.
use std::collections::BTreeMap;

use babylon_practice_contract as practice_contract;
use babylon_practice_contract::{
    Band, ContactOutcome, CountyPeriodFacts, CountyReviewConfig, CountyReviewError, HourCharge,
    PositionKey, Roster, RosterRow, SessionOutcome, SessionRecord, SessionRow, SupportLine,
};

use super::support;
use super::support::{Rng, A, B, B50, C, D, N9};

fn hold(
    c: &CountyReviewConfig,
    r: &Roster,
    f: &CountyPeriodFacts,
    contact: Option<PositionKey>,
) -> SessionOutcome {
    practice_contract::hold_session(c, r, f, contact).expect("the session is held")
}

#[test]
fn a_place_is_an_exact_rate_reduced_and_compared_in_wide_arithmetic() {
    let full = practice_contract::place(1, 11_520_000_000, 3, 2_016_000_000, 13_440_000_000)
        .expect("places");
    let same = practice_contract::place(2, 576_000_000, 1, 1, 2).expect("places");
    let half = practice_contract::place(1, 1_920_000_000, 1, 2_016_000_000, 13_440_000_000)
        .expect("places");
    assert_eq!(full, same, "two ways to the same rate are one place");
    assert!(full > half);
    let zero = practice_contract::place(0, 11_520_000_000, 3, 1, 2).expect("places");
    assert!(zero.is_zero() && zero == practice_contract::Place::ZERO);
    for (wages, people, collected, taxed) in
        [(0, 3, 1, 2), (5, 0, 1, 2), (5, 3, 0, 2), (5, 3, 1, 0)]
    {
        let none = practice_contract::place(1, wages, people, collected, taxed).expect("places");
        assert!(
            none.is_zero(),
            "a missing factor puts a position at nothing"
        );
    }
    // Numerators and denominators whose cross products overflow 128 bits still compare exactly.
    let high = practice_contract::place(1, i128::MAX, 1, 1, 3).expect("places");
    let lower = practice_contract::place(1, i128::MAX - 1, 1, 1, 3).expect("places");
    assert!(high > lower);
    assert!(lower < high);
    assert_ne!(high, lower);
    assert_eq!(
        practice_contract::place(u16::MAX, i128::MAX, 1, i128::MAX, 1),
        Err(CountyReviewError::Arithmetic),
        "a product that cannot be held is refused"
    );
    assert_eq!(
        practice_contract::place(1, -1, 1, 1, 1),
        Err(CountyReviewError::Arithmetic),
        "a negative amount is refused"
    );
}

#[test]
fn the_worked_example_of_the_design() {
    let (c, mut r, f) = support::world();
    support::reach(&mut r, D, 1);
    let out = hold(&c, &r, &f, None);
    let rec = &out.record;
    assert_eq!(rec.household_units_payable, 5);
    assert_eq!(support::row(rec, A).units_paid, 2);
    assert_eq!(
        (support::row(rec, D).asked, support::row(rec, D).asked_paid),
        (1, 1)
    );
    assert_eq!(support::row(rec, B).units_paid, 1);
    assert_eq!(
        (
            support::row(rec, C).units_paid,
            support::row(rec, C).units_unpaid,
            support::row(rec, C).losers,
            support::row(rec, C).losers_reached
        ),
        (1, 1, 1, 0)
    );
    assert_eq!(
        (
            support::row(rec, A).rank,
            support::row(rec, D).rank,
            support::row(rec, B).rank,
            support::row(rec, C).rank
        ),
        (1, 1, 2, 3)
    );
    assert_eq!(
        rec.lines,
        vec![
            SupportLine {
                group: 0,
                units: 4,
                amount_micros: 1_120_000_000
            },
            SupportLine {
                group: 1,
                units: 1,
                amount_micros: 280_000_000
            }
        ]
    );
    assert_eq!(out.hour_charges, vec![HourCharge { group: 0, hours: 2 }]);
    assert_eq!(
        (
            rec.aid_roll_households,
            rec.claimants_roll_households,
            rec.kept_back_units
        ),
        (1, 0, 0)
    );
    assert_eq!(rec.contact, None);
    support::balanced(rec);
}

#[test]
fn ties_keep_the_holder() {
    // Severs: "an asking household goes on the list below every unit at the same place". Without
    // it D would take a unit from A.
    let (c, mut r, f) = support::world_with(&[support::tuple(A, 2, 0), support::tuple(D, 1, 1)]);
    support::reach(&mut r, D, 1);
    let out = hold(&c, &r, &f, None);
    let rec = &out.record;
    assert_eq!(rec.household_units_payable, 2);
    assert_eq!(support::row(rec, A).units_paid, 2);
    assert_eq!(
        (
            support::row(rec, D).asked,
            support::row(rec, D).asked_no_place
        ),
        (1, 1)
    );
    assert_eq!(support::row(rec, D).asked_paid, 0);
    assert!(
        out.hour_charges.is_empty(),
        "a household with no place spends no hour"
    );
    support::balanced(rec);
}

#[test]
fn a_household_with_no_wage_takes_nothing() {
    // Severs: a household with no place is ranked as if it had one. It asks, stands at the last
    // rank and finds the units already spoken for.
    let nowage = PositionKey {
        group: 1,
        band: B50,
        crew: None,
        at_work: 0,
        seeking: 0,
        units: 0,
    };
    let (c, mut r, f) = support::world_with(&[
        support::tuple(A, 2, 0),
        support::tuple(B, 1, 0),
        support::tuple(C, 2, 0),
        support::tuple(nowage, 3, 1),
    ]);
    support::reach(&mut r, nowage, 1);
    let out = hold(&c, &r, &f, None);
    let rec = &out.record;
    assert_eq!(support::row(rec, nowage).asked, 1);
    assert_eq!(support::row(rec, nowage).asked_no_place, 1);
    assert_eq!(support::row(rec, nowage).rank, support::row(rec, C).rank);
    assert_eq!(support::row(rec, nowage).rank, 3);
    assert_eq!(support::row(rec, C).units_paid, 2);
    assert_eq!(out.hour_charges, Vec::new());
    support::balanced(rec);
}

#[test]
fn a_short_county_pays_from_the_top() {
    // Severs: "the county pays the household list from the top". Paying lines in identifier order
    // would pay C before B.
    let (c, r, mut f) = support::world();
    support::short(&mut f, 3);
    let rec = hold(&c, &r, &f, None).record;
    assert_eq!(rec.household_units_payable, 3);
    assert_eq!(rec.relief_micros, 840_000_000);
    assert_eq!(support::row(&rec, A).units_paid, 2);
    assert_eq!(support::row(&rec, B).units_paid, 1);
    assert_eq!(support::row(&rec, C).units_paid, 0);
    assert_eq!(
        rec.lines,
        vec![SupportLine {
            group: 0,
            units: 3,
            amount_micros: 840_000_000
        }],
        "group 1 holds no unit and has no line"
    );
    support::balanced(&rec);
}

#[test]
fn no_money_for_relief_removes_every_line() {
    // Severs: the county's cash bounds relief. With no cash a line of zero would reach the engine.
    let (c, mut r, mut f) = support::world();
    support::reach(&mut r, A, 1);
    f.cash_micros = 0;
    let out = hold(&c, &r, &f, None);
    let rec = &out.record;
    assert_eq!(rec.relief_micros, 0);
    assert_eq!(rec.lines, Vec::new());
    assert_eq!(rec.collective_lines, Vec::new());
    assert_eq!(rec.household_units_payable, 0);
    assert!(rec.rows.iter().all(|x| x.units_paid == 0));
    assert_eq!(
        rec.rows.iter().map(|x| x.units_unpaid).sum::<u64>(),
        rec.household_units_listed,
        "every unit is unpaid"
    );
    assert_eq!(
        support::row(rec, A).came_from_roll,
        1,
        "a reached household on the roll comes"
    );
    support::balanced(rec);
}

#[test]
fn the_cash_the_limit_and_the_first_class_each_bound_relief() {
    // Severs: relief is the cash, or the limit if lower, less the first class, and never below zero.
    let (c, r, mut f) = support::world();
    f.first_class_micros = f.cash_micros;
    assert_eq!(hold(&c, &r, &f, None).record.relief_micros, 0);
    f.first_class_micros = 0;
    f.spending_limit_micros = 0;
    assert_eq!(hold(&c, &r, &f, None).record.relief_micros, 0);
    f.spending_limit_micros = 10_000_000_000;
    f.cash_micros = 5;
    f.cash_floor_micros = 10;
    assert_eq!(
        hold(&c, &r, &f, None).record.relief_micros,
        0,
        "cash below the floor leaves nothing, and no amount is below zero"
    );
    f.cash_micros = 10_000_000_000;
    f.cash_floor_micros = 0;
    f.first_class_micros = 9_000_000_000;
    let rec = hold(&c, &r, &f, None).record;
    assert_eq!(
        rec.relief_micros, 1_000_000_000,
        "the first class comes off the top"
    );
    assert_eq!(rec.household_units_payable, 3, "whole units only");
    support::balanced(&rec);
}

#[test]
fn an_exact_tie_between_positions_is_paid_to_nobody() {
    // Severs: "if two remainders are exactly equal the county may not prefer one position".
    // Two crews are paid alike, so the two positions stand at one place; one unit can be paid.
    let first = A;
    let second = PositionKey { crew: Some(1), ..A };
    let (c, r, mut f) =
        support::world_with(&[support::tuple(first, 1, 0), support::tuple(second, 1, 0)]);
    f.crews[0].accrued_wages_micros = 1_920_000_000;
    support::short(&mut f, 1);
    let rec = hold(&c, &r, &f, None).record;
    assert_eq!(rec.household_units_payable, 1);
    assert_eq!(
        (
            support::row(&rec, first).units_paid,
            support::row(&rec, second).units_paid
        ),
        (0, 0)
    );
    assert_eq!(rec.kept_back_units, 1);
    assert_eq!(
        support::row(&rec, first).rank,
        support::row(&rec, second).rank
    );
    assert_eq!(rec.lines, Vec::new());
    support::balanced(&rec);
}

#[test]
fn a_reached_household_whose_unit_is_unpaid_comes_and_brings_one() {
    // Severs: "a household on the roll comes if a unit of its own is not paid".
    let (c, mut r, mut f) = support::world();
    support::reach(&mut r, C, 1);
    support::short(&mut f, 3);
    let out = hold(&c, &r, &f, None);
    let rec = &out.record;
    assert_eq!(support::row(rec, C).units_unpaid, 2);
    assert_eq!(support::row(rec, C).losers_reached, 1);
    assert_eq!(support::row(rec, C).came_from_roll, 1);
    assert_eq!(support::row(rec, C).brought, 1);
    assert_eq!(
        out.hour_charges,
        vec![HourCharge {
            group: 1,
            hours: 2 + 2
        }]
    );
    assert_eq!(rec.claimants_roll_households, 1);
    let brought = out
        .roster
        .rows
        .iter()
        .find(|x| x.key == C)
        .expect("C is in the roster");
    assert_eq!(
        (brought.households, brought.reached),
        (2, 2),
        "C is fully reached"
    );
    support::balanced(rec);
}

#[test]
fn one_reached_household_among_many_is_not_the_loser() {
    // Severs: the declared split. A tie falls on the unreached household.
    let (c, mut r, mut f) = support::world();
    support::reach(&mut r, C, 1);
    support::short(&mut f, 4);
    let rec = hold(&c, &r, &f, None).record;
    assert_eq!(support::row(&rec, C).units_unpaid, 1);
    assert_eq!(support::row(&rec, C).losers, 1);
    assert_eq!(support::row(&rec, C).losers_reached, 0);
    assert_eq!(support::row(&rec, C).nothing_at_stake, 1);
    assert_eq!(support::row(&rec, C).came_from_roll, 0);
    support::balanced(&rec);
}

#[test]
fn no_free_hours_records_no_time() {
    // Severs: "a household with no hours does not ask".
    let (c, mut r, mut f) = support::world();
    support::reach(&mut r, D, 1);
    f.groups[0].free_hours = 0;
    let out = hold(&c, &r, &f, None);
    let rec = &out.record;
    assert_eq!(
        (
            support::row(rec, D).asked,
            support::row(rec, D).asked_no_time
        ),
        (0, 1)
    );
    assert_eq!(
        support::row(rec, C).units_paid,
        2,
        "the list is as if nobody asked"
    );
    assert_eq!(rec.aid_roll_households, 0);
    assert_eq!(out.hour_charges, Vec::new());
    support::balanced(rec);
}

#[test]
fn a_unit_below_the_floor_keeps_everyone_home() {
    // Severs: the floor, two hours at the going wage ($48), against the stake.
    let (mut c, mut r, mut f) = support::world();
    c.unit_price_micros = 40_000_000;
    support::reach(&mut r, D, 1);
    support::reach(&mut r, C, 1);
    f.cash_micros = 3 * 40_000_000;
    let out = hold(&c, &r, &f, None);
    let rec = &out.record;
    assert_eq!(support::row(rec, D).not_worth_time, 1);
    assert_eq!(support::row(rec, D).asked, 0);
    assert_eq!(support::row(rec, C).losers_reached, 1);
    assert_eq!(support::row(rec, C).not_worth_time, 1);
    assert_eq!(support::row(rec, C).came_from_roll, 0);
    assert_eq!(out.hour_charges, Vec::new());
    support::balanced(rec);
}

#[test]
fn a_crew_with_nobody_at_work_or_a_group_with_no_taxed_wages_stands_at_nothing() {
    // Severs: a place divides by the crew's people and by the group's taxed wages.
    let (c, r, mut f) = support::world();
    f.crews[2].accrued_wages_micros = 5_000_000_000;
    let rec = hold(&c, &r, &f, None).record;
    assert_eq!(
        support::row(&rec, C).rank,
        3,
        "nobody at work: the last rank"
    );
    support::balanced(&rec);
    f.groups[0].taxed_wages_micros = 0;
    f.groups[0].wage_tax_collected_micros = 0;
    let rec = hold(&c, &r, &f, None).record;
    assert!(
        rec.rows.iter().all(|x| x.rank == 1),
        "if no household paid wage tax all stand at one place"
    );
    support::balanced(&rec);
}

#[test]
fn the_contact_lands_before_the_list() {
    // Severs: step 1 of the session, the contact counts before the list is made.
    let (c, r, f) = support::world();
    let out = hold(&c, &r, &f, Some(D));
    assert_eq!(out.record.contact, Some((D, ContactOutcome::Reached)));
    assert_eq!(support::row(&out.record, D).asked_paid, 1);
    support::balanced(&out.record);
    let nowhere = PositionKey { band: N9, ..D };
    let out = hold(&c, &r, &f, Some(nowhere));
    assert_eq!(
        out.record.contact,
        Some((nowhere, ContactOutcome::NoSuchPosition))
    );
    assert_eq!(out.roster, r, "a position with no row changes nothing");
    support::balanced(&out.record);
    let mut done = r.clone();
    support::reach(&mut done, D, 1);
    let out = hold(&c, &done, &f, Some(D));
    assert_eq!(out.record.contact, Some((D, ContactOutcome::NobodyLeft)));
    support::balanced(&out.record);
}

fn counts(row: &SessionRow) -> [u64; 16] {
    [
        row.units_paid,
        row.units_unpaid,
        row.asked,
        row.asked_paid,
        row.asked_no_place,
        row.asked_no_time,
        row.losers,
        row.losers_reached,
        row.came_from_roll,
        row.roll_no_time,
        row.nothing_at_stake,
        row.not_worth_time,
        row.brought,
        row.hours_in_room,
        row.hours_bringing,
        row.rank.into(),
    ]
}

#[test]
fn swapping_the_pay_of_two_crews_reverses_who_loses() {
    // Severs: a position's place comes from its own crew's wages. Group totals are unchanged.
    let (c, r, mut f) = support::world();
    support::short(&mut f, 2);
    let first = hold(&c, &r, &f, None).record;
    assert_eq!(
        (
            support::row(&first, B).units_unpaid,
            support::row(&first, A).units_unpaid
        ),
        (1, 0)
    );
    let wages = (
        f.crews[0].accrued_wages_micros,
        f.crews[1].accrued_wages_micros,
    );
    f.crews[0].accrued_wages_micros = wages.1;
    f.crews[1].accrued_wages_micros = wages.0;
    let second = hold(&c, &r, &f, None).record;
    assert_eq!(
        (
            support::row(&second, B).units_unpaid,
            support::row(&second, A).units_unpaid
        ),
        (0, 1),
        "the unpaid unit is now in A"
    );
    support::balanced(&first);
    support::balanced(&second);
}

#[test]
fn a_group_average_would_give_another_answer() {
    // The mutation Amendment AM asks for: give every row of group 0 the group's average, here
    // 3_360_000_000 for each person at work, and the list changes. The real rule reads each
    // position's own figures.
    let (c, r, mut f) = support::world();
    support::short(&mut f, 2);
    let real = hold(&c, &r, &f, None).record;
    f.crews[0].accrued_wages_micros = 3 * 3_360_000_000;
    f.crews[1].accrued_wages_micros = 3_360_000_000;
    let averaged = hold(&c, &r, &f, None).record;
    assert_ne!(real.rows, averaged.rows);
    assert_eq!(support::row(&real, A).units_paid, 2);
    assert_eq!(
        (
            support::row(&averaged, A).units_paid,
            support::row(&averaged, B).units_paid
        ),
        (1, 1),
        "at one shared place the units are split, not given to the highest"
    );
    support::balanced(&real);
    support::balanced(&averaged);
}

fn by_key(
    rec: &SessionRecord,
    back: impl Fn(PositionKey) -> PositionKey,
) -> BTreeMap<PositionKey, [u64; 16]> {
    rec.rows.iter().map(|r| (back(r.key), counts(r))).collect()
}

fn swap_crews_01(key: PositionKey) -> PositionKey {
    let crew = key.crew.map(|c| match c {
        0 => 1,
        1 => 0,
        other => other,
    });
    PositionKey { crew, ..key }
}

#[test]
fn renaming_crews_changes_no_count() {
    // Severs: no rule reads a crew's index. Crews 0 and 1 are exchanged everywhere.
    let (c, mut r, mut f) = support::world();
    support::reach(&mut r, D, 1);
    support::reach(&mut r, C, 1);
    support::short(&mut f, 3);
    let plain = hold(&c, &r, &f, None).record;
    let mut swapped = r.clone();
    for row in &mut swapped.rows {
        row.key = swap_crews_01(row.key);
    }
    swapped.rows.sort_by_key(|row| row.key);
    let mut g = f.clone();
    g.crews.swap(0, 1);
    g.crews[0].crew = 0;
    g.crews[1].crew = 1;
    let other = hold(&c, &swapped, &g, None).record;
    assert_eq!(by_key(&plain, |k| k), by_key(&other, swap_crews_01));
    assert_eq!(plain.lines, other.lines);
    assert_eq!(plain.kept_back_units, other.kept_back_units);
    assert_eq!(plain.household_units_payable, other.household_units_payable);
    support::balanced(&plain);
    support::balanced(&other);
}

#[test]
fn splitting_a_crew_that_pays_alike_moves_at_most_one_unit() {
    // Severs: a place depends on the crew's wage per person, not on the crew's size. Crew 0 is
    // split in two; each person is paid alike, so every place is unchanged.
    let (c, r, mut f) = support::world();
    support::short(&mut f, 1);
    let whole = hold(&c, &r, &f, None).record;
    let mut split_config = support::config(&[(4, 3, false), (2, 2, false)], &[0, 0, 1, 0]);
    split_config.unit_price_micros = c.unit_price_micros;
    let a_new = PositionKey { crew: Some(3), ..A };
    let split = support::hand_roster(
        &split_config,
        &[
            support::tuple(A, 1, 0),
            support::tuple(a_new, 1, 0),
            support::tuple(D, 1, 0),
            support::tuple(B, 1, 0),
            support::tuple(C, 2, 0),
        ],
    );
    let mut g = support::facts(&split_config, &split, &[], &[4, 2]);
    for (crew, wages) in [
        (0, 7_680_000_000),
        (1, 1_920_000_000),
        (2, 0),
        (3, 3_840_000_000),
    ] {
        g.crews[crew].accrued_wages_micros = wages;
    }
    g.groups[0].taxed_wages_micros = f.groups[0].taxed_wages_micros;
    g.groups[0].wage_tax_collected_micros = f.groups[0].wage_tax_collected_micros;
    for group in &mut g.groups {
        group.free_hours = 100;
    }
    g.cash_micros = f.cash_micros;
    g.spending_limit_micros = f.spending_limit_micros;
    let halves = hold(&split_config, &split, &g, None).record;
    let total = |rec: &SessionRecord, shape: fn(PositionKey) -> PositionKey| {
        let mut sums: BTreeMap<PositionKey, [u64; 16]> = BTreeMap::new();
        for r in &rec.rows {
            let slot = sums.entry(shape(r.key)).or_insert([0; 16]);
            for (sum, count) in slot.iter_mut().zip(counts(r)) {
                *sum += count;
            }
        }
        sums
    };
    let forget_crew = |k: PositionKey| PositionKey {
        crew: k.crew.map(|_| 0),
        ..k
    };
    let (before, after) = (total(&whole, forget_crew), total(&halves, forget_crew));
    assert_eq!(
        before.keys().collect::<Vec<_>>(),
        after.keys().collect::<Vec<_>>()
    );
    for (key, sums) in &before {
        for (index, count) in sums.iter().enumerate() {
            if index == 15 {
                continue; // ranks are not counts of households
            }
            assert!(
                count.abs_diff(after[key][index]) <= 1,
                "position {key:?} figure {index}: {count} against {}",
                after[key][index]
            );
        }
    }
    assert_eq!(whole.kept_back_units, 0);
    assert_eq!(
        halves.kept_back_units, 1,
        "the two halves tie for the one unit"
    );
    support::balanced(&whole);
    support::balanced(&halves);
}

#[test]
fn two_units_are_lost_a_household_at_a_time() {
    // Severs: "a household that holds two loses both before the next loses one".
    let two = PositionKey {
        group: 1,
        band: B50,
        crew: Some(2),
        at_work: 0,
        seeking: 2,
        units: 2,
    };
    let (c, r, mut f) = support::world_with(&[support::tuple(two, 2, 0)]);
    f.cash_micros = 280_000_000;
    let rec = hold(&c, &r, &f, None).record;
    assert_eq!(rec.household_units_payable, 1);
    assert_eq!(support::row(&rec, two).units_unpaid, 3);
    assert_eq!(support::row(&rec, two).losers, 2);
    support::balanced(&rec);
    // With every household reached the one that loses a single unit is a reached household.
    let (c, mut r, mut f) = support::world_with(&[support::tuple(two, 2, 0)]);
    support::reach(&mut r, two, 2);
    f.cash_micros = 280_000_000;
    let rec = hold(&c, &r, &f, None).record;
    assert_eq!(support::row(&rec, two).losers_reached, 2);
    assert_eq!(support::row(&rec, two).came_from_roll, 2);
    support::balanced(&rec);
}

#[test]
fn the_band_changes_no_outcome() {
    // Severs: no rule of the session reads a band.
    let (c, mut r, mut f) = support::world();
    support::reach(&mut r, D, 1);
    support::reach(&mut r, C, 1);
    support::short(&mut f, 4);
    let plain = hold(&c, &r, &f, None).record;
    let rekeyed = |band_of: fn(PositionKey) -> Band| {
        let mut moved = r.clone();
        for row in &mut moved.rows {
            row.key.band = band_of(row.key);
        }
        moved.rows.sort_by_key(|row: &RosterRow| row.key);
        moved
    };
    let only_d = rekeyed(|k| if k == D { B50 } else { k.band });
    let all = rekeyed(|_| N9);
    let first = hold(&c, &only_d, &f, None).record;
    let second = hold(&c, &all, &f, None).record;
    let want = by_key(&plain, |k| PositionKey { band: B50, ..k });
    assert_eq!(by_key(&first, |k| PositionKey { band: B50, ..k }), want);
    assert_eq!(by_key(&second, |k| PositionKey { band: B50, ..k }), want);
    assert_eq!(plain.lines, first.lines);
    assert_eq!(plain.lines, second.lines);
    support::balanced(&first);
    support::balanced(&second);
}

#[test]
fn every_session_balances() {
    let mut rng = Rng(0x2545_f491_4f6c_dd1d);
    let (mut held, mut attempts) = (0, 0);
    // How many sessions reached each branch: the property is empty if one stays at zero.
    let mut seen = [0_u32; 6];
    while held < 300 {
        attempts += 1;
        assert!(
            attempts < 200_000,
            "the law accepted too few random openings"
        );
        let Some((c, _, roster)) = support::random_opening(&mut rng) else {
            continue;
        };
        held += 1;
        let households: Vec<u64> = roster.groups.iter().map(|g| g.households).collect();
        let mut f = support::facts(&c, &roster, &[], &households);
        for crew in &mut f.crews {
            crew.accrued_wages_micros = i128::from(rng.up_to(50)) * 480_000_000;
        }
        for group in &mut f.groups {
            let taxed = rng.up_to(40);
            group.taxed_wages_micros = i128::from(taxed) * 1_000_000_000;
            group.wage_tax_collected_micros = i128::from(rng.up_to(taxed)) * 1_000_000_000;
            group.free_hours = rng.up_to(12);
        }
        f.cash_micros = i128::from(rng.up_to(80)) * 100_000_000;
        f.spending_limit_micros = i128::from(rng.up_to(80)) * 100_000_000;
        f.first_class_micros = i128::from(rng.up_to(2)) * 1_000_000_000;
        let contact = (rng.up_to(2) == 0).then(|| {
            let last = u64::try_from(roster.rows.len() - 1).expect("small");
            roster.rows[usize::try_from(rng.up_to(last)).expect("small")].key
        });
        let out = practice_contract::hold_session(&c, &roster, &f, contact)
            .expect("a session on a lawful world is held");
        let rec = &out.record;
        support::balanced(rec);
        let lines: i128 = rec
            .lines
            .iter()
            .chain(&rec.collective_lines)
            .map(|l| l.amount_micros)
            .sum();
        assert!(lines <= rec.relief_micros, "lines never exceed relief");
        for charge in &out.hour_charges {
            let free = f.groups[usize::try_from(charge.group).expect("small")].free_hours;
            assert!(
                charge.hours <= free,
                "no charge exceeds the group's free hours"
            );
        }
        for line in &rec.lines {
            let units: u64 = rec
                .rows
                .iter()
                .filter(|r| r.key.group == line.group)
                .map(|r| r.units_paid + r.asked_paid)
                .sum();
            assert_eq!(
                line.units, units,
                "a group's line is the units its positions hold"
            );
        }
        for (slot, branch) in seen.iter_mut().zip([
            rec.rows.iter().any(|r| r.asked_paid > 0),
            rec.rows.iter().any(|r| r.asked_no_place > 0),
            rec.rows.iter().any(|r| r.asked_no_time > 0),
            rec.rows.iter().any(|r| r.came_from_roll > 0),
            rec.rows.iter().any(|r| r.brought > 0),
            rec.kept_back_units > 0,
        ]) {
            *slot += u32::from(branch);
        }
        practice_contract::validate_roster(&c, &out.roster).expect("the new roster is lawful");
        let before: u64 = roster.rows.iter().map(|r| r.reached).sum();
        let after: u64 = out.roster.rows.iter().map(|r| r.reached).sum();
        let landed = u64::from(matches!(rec.contact, Some((_, ContactOutcome::Reached))));
        let brought: u64 = rec.rows.iter().map(|r| r.brought).sum();
        assert_eq!(
            after,
            before + landed + brought,
            "reach rises by the contact and those brought"
        );
    }
    assert!(
        seen.iter().all(|n| *n > 0),
        "every branch of the session was reached: {seen:?}"
    );
}
