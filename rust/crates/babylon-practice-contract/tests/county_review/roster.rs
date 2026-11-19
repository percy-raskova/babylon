use babylon_practice_contract as practice_contract;
use babylon_practice_contract::{
    Band, CountyReviewConfig, CountyReviewError, GroupKind, Placement, Roster,
};

use super::support;
use super::support::{Changes, Rng, RowTuple, B50, N40, N9, T1};

#[test]
fn fewer_people_than_households_gives_each_person_a_household() {
    let c = support::config(&[(10, 2, false)], &[0]);
    let p = practice_contract::opening_placement(&c, &[support::open(0, 3, 2)]).expect("places");
    assert_eq!(
        support::placed(&p),
        vec![
            ((0, None, 0, 0, 0), 5),
            ((0, Some(0), 0, 1, 1), 2),
            ((0, Some(0), 1, 0, 0), 3)
        ]
    );
}

#[test]
fn more_people_than_households_spreads_work_evenly_and_seekers_to_the_fewest_at_work() {
    let c = support::config(&[(4, 3, false)], &[0]);
    let p = practice_contract::opening_placement(&c, &[support::open(0, 6, 3)]).expect("places");
    assert_eq!(
        support::placed(&p),
        vec![
            ((0, Some(0), 1, 1, 1), 2),
            ((0, Some(0), 2, 0, 0), 1),
            ((0, Some(0), 2, 1, 1), 1)
        ]
    );
}

#[test]
fn two_crews_with_equal_claims_leave_the_tied_household_with_no_crew() {
    let c = support::config(&[(5, 2, false)], &[0, 0]);
    let p =
        practice_contract::opening_placement(&c, &[support::open(0, 4, 0), support::open(1, 2, 2)])
            .expect("places");
    assert_eq!(
        support::placed(&p),
        vec![
            ((0, None, 0, 0, 0), 1),
            ((0, Some(0), 2, 0, 0), 2),
            ((0, Some(1), 1, 1, 1), 2)
        ]
    );
}

#[test]
fn more_seekers_than_households_gives_a_household_two_or_three_units() {
    let c = support::config(&[(2, 5, false)], &[0]);
    let p = practice_contract::opening_placement(&c, &[support::open(0, 1, 5)]).expect("places");
    assert_eq!(
        support::placed(&p),
        vec![((0, Some(0), 0, 3, 3), 1), ((0, Some(0), 1, 2, 2), 1)]
    );
}

#[test]
fn more_crews_than_households_is_refused() {
    let c = support::config(&[(1, 0, false)], &[0, 0]);
    assert_eq!(
        practice_contract::opening_placement(&c, &[support::open(0, 1, 0), support::open(1, 1, 0)]),
        Err(CountyReviewError::MoreCrewsThanHouseholds)
    );
}

#[test]
fn units_placed_must_equal_the_roll() {
    let c = support::config(&[(10, 3, false)], &[0]);
    assert_eq!(
        practice_contract::opening_placement(&c, &[support::open(0, 3, 2)]),
        Err(CountyReviewError::RollMismatch)
    );
}

#[test]
fn a_crew_named_twice_or_not_at_all_is_refused() {
    let c = support::config(&[(10, 0, false)], &[0]);
    assert_eq!(
        practice_contract::opening_placement(&c, &[support::open(0, 1, 0), support::open(0, 1, 0)]),
        Err(CountyReviewError::DuplicateCrew)
    );
    assert_eq!(
        practice_contract::opening_placement(&c, &[support::open(7, 1, 0)]),
        Err(CountyReviewError::UnknownCrew)
    );
}

#[test]
fn a_collective_residence_has_no_rows() {
    let mut c = support::config(&[(10, 2, false), (0, 772, false)], &[0]);
    c.groups[1].kind = GroupKind::CollectiveResidence;
    let r = practice_contract::opening_roster(&c, &[support::open(0, 3, 2)], &[]).expect("opens");
    assert!(
        r.rows.iter().all(|row| row.key.group == 0),
        "no row belongs to the collective residence"
    );
    assert_eq!(r.groups[1].households, 0);
    assert_eq!(r.groups[0].households, 10);
}

#[test]
fn a_configuration_that_cannot_be_read_is_refused_by_name() {
    let mut c = support::config(&[(10, 0, false)], &[0]);
    c.unit_price_micros = 0;
    assert_eq!(
        practice_contract::validate_county_review_config(&c),
        Err(CountyReviewError::InvalidTerms)
    );
    let mut c = support::config(&[(10, 0, false), (4, 0, false)], &[0]);
    c.groups.swap(0, 1);
    assert_eq!(
        practice_contract::validate_county_review_config(&c),
        Err(CountyReviewError::GroupsNotCanonical)
    );
    let mut c = support::config(&[(10, 0, false)], &[0]);
    c.crews[0].group = 5;
    assert_eq!(
        practice_contract::validate_county_review_config(&c),
        Err(CountyReviewError::UnknownGroup)
    );
    let mut c = support::config(&[(10, 0, false)], &[0]);
    c.schema_version = 2;
    assert_eq!(
        practice_contract::validate_county_review_config(&c),
        Err(CountyReviewError::UnsupportedSchema)
    );
}

#[test]
fn the_next_forty_are_taken_by_the_number_at_work_and_bring_their_seekers() {
    let c = support::config(&[(9, 2, false)], &[0]); // the next 40% needs 4 of the 9
    let r = practice_contract::opening_roster(&c, &[support::open(0, 10, 2)], &[]).expect("opens");
    // the household with 2 at work first; then 3 of the 8 with 1 at work, in proportion 6 : 2,
    // so one of them has a job-seeker and a unit
    assert_eq!(
        support::rows(&r),
        vec![
            ((0, B50, Some(0), 1, 0, 0), 4, 0),
            ((0, B50, Some(0), 1, 1, 1), 1, 0),
            ((0, N40, Some(0), 1, 0, 0), 2, 0),
            ((0, N40, Some(0), 1, 1, 1), 1, 0),
            ((0, N40, Some(0), 2, 0, 0), 1, 0)
        ]
    );
}

#[test]
fn a_unit_does_not_keep_a_household_out_of_the_next_forty() {
    let c = support::config(&[(4, 3, false)], &[0]); // the next 40% needs 2 of the 4: the two households with 2 at work
    let r = practice_contract::opening_roster(&c, &[support::open(0, 6, 3)], &[]).expect("opens");
    assert_eq!(
        support::rows(&r),
        vec![
            ((0, B50, Some(0), 1, 1, 1), 2, 0),
            ((0, N40, Some(0), 2, 0, 0), 1, 0),
            ((0, N40, Some(0), 2, 1, 1), 1, 0)
        ]
    );
}

#[test]
fn households_only_looking_for_work_come_last_and_those_outside_the_labor_force_never() {
    let c = support::config(&[(9, 3, false)], &[0]); // the next 40% needs 4: 2 at work, then 2 of the 3 only looking
    let r = practice_contract::opening_roster(&c, &[support::open(0, 2, 3)], &[]).expect("opens");
    assert_eq!(
        support::rows(&r),
        vec![
            ((0, B50, None, 0, 0, 0), 4, 0),
            ((0, B50, Some(0), 0, 1, 1), 1, 0),
            ((0, N40, Some(0), 0, 1, 1), 2, 0),
            ((0, N40, Some(0), 1, 0, 0), 2, 0)
        ]
    );
}

#[test]
fn the_top_hundredth_has_nobody_in_the_labor_force() {
    let c = support::config(&[(20, 2, true)], &[0]); // owners: the top 1% needs 2 of the 20
    let r = practice_contract::opening_roster(&c, &[support::open(0, 5, 2)], &[]).expect("opens");
    assert_eq!(
        support::rows(&r),
        vec![
            ((0, N9, None, 0, 0, 0), 11, 0),
            ((0, N9, Some(0), 0, 1, 1), 2, 0),
            ((0, N9, Some(0), 1, 0, 0), 5, 0),
            ((0, T1, None, 0, 0, 0), 2, 0)
        ]
    );
}

#[test]
fn an_exact_tie_at_a_bands_line_stays_in_the_lower_band() {
    let c = support::config(&[(16, 0, false)], &[0, 0]); // the next 40% needs 7; two equal crews tie for the seventh
    let r = practice_contract::opening_roster(
        &c,
        &[support::open(0, 8, 0), support::open(1, 8, 0)],
        &[],
    )
    .expect("opens");
    assert_eq!(
        support::rows(&r),
        vec![
            ((0, B50, Some(0), 1, 0, 0), 5, 0),
            ((0, B50, Some(1), 1, 0, 0), 5, 0),
            ((0, N40, Some(0), 1, 0, 0), 3, 0),
            ((0, N40, Some(1), 1, 0, 0), 3, 0)
        ]
    );
}

#[test]
fn an_opening_that_cannot_obey_the_law_is_refused_by_name() {
    let owners = support::config(&[(10, 0, true)], &[0]); // every owner household has someone at work
    assert_eq!(
        practice_contract::opening_roster(&owners, &[support::open(0, 10, 0)], &[]),
        Err(CountyReviewError::TopBandInLaborForce)
    );
    let others = support::config(&[(9, 0, false)], &[0]); // the next 40% needs 4 households in the labor force; there are 2
    assert_eq!(
        practice_contract::opening_roster(&others, &[support::open(0, 2, 0)], &[]),
        Err(CountyReviewError::WageBandOutsideLaborForce)
    );
}

#[test]
fn opening_reach_is_placed_on_the_groups_rows_in_proportion() {
    let c = support::config(&[(4, 3, false)], &[0]);
    // rows (B50, 1, 1, 1) x2, (N40, 2, 0, 0) x1 and (N40, 2, 1, 1) x1: three reached of four
    // are 1.5, 0.75 and 0.75 by weight, and the two larger remainders take the odd ones
    let r =
        practice_contract::opening_roster(&c, &[support::open(0, 6, 3)], &[(0, 3)]).expect("opens");
    assert_eq!(
        support::rows(&r),
        vec![
            ((0, B50, Some(0), 1, 1, 1), 2, 1),
            ((0, N40, Some(0), 2, 0, 0), 1, 1),
            ((0, N40, Some(0), 2, 1, 1), 1, 1)
        ]
    );
}

#[test]
fn opening_reach_that_cannot_be_placed_is_refused() {
    let c = support::config(&[(4, 3, false)], &[0]);
    assert_eq!(
        practice_contract::opening_roster(&c, &[support::open(0, 6, 3)], &[(0, 5)]),
        Err(CountyReviewError::OpeningReachNotPlaceable)
    );
    assert_eq!(
        practice_contract::opening_roster(&c, &[support::open(0, 6, 3)], &[(0, 2)]),
        Err(CountyReviewError::OpeningReachNotPlaceable),
        "two of four leave an exact tie at the cut, and a tie is withheld"
    );
    assert_eq!(
        practice_contract::opening_roster(&c, &[support::open(0, 6, 3)], &[(3, 1)]),
        Err(CountyReviewError::UnknownGroup)
    );
}

/// The banded roster of the second band test: 4 households, `E = 6`, `S = 3`.
fn base() -> (CountyReviewConfig, Roster) {
    let c = support::config(&[(4, 3, false)], &[0]);
    let r = practice_contract::opening_roster(&c, &[support::open(0, 6, 3)], &[]).expect("opens");
    (c, r)
}

fn after_with(changes: Changes, placement: Placement) -> Vec<RowTuple> {
    let (c, r) = base();
    let f = support::facts(&c, &r, &[(0, changes)], &[4]);
    support::rows(&practice_contract::roll_forward_with(&c, &r, &f, placement).expect("rolls"))
}

fn after(changes: Changes) -> Vec<RowTuple> {
    after_with(changes, Placement::Declared)
}

fn hires(n: u64) -> Changes {
    Changes {
        hires: n,
        ..Changes::default()
    }
}

fn separations(n: u64) -> Changes {
    Changes {
        separations: n,
        ..Changes::default()
    }
}

fn left_seeking(n: u64) -> Changes {
    Changes {
        left_seeking: n,
        ..Changes::default()
    }
}

#[test]
fn a_hire_takes_a_seeker_from_the_households_with_the_fewest_at_work() {
    assert_eq!(
        after(hires(1)),
        vec![
            ((0, B50, Some(0), 1, 1, 1), 1, 0),
            ((0, B50, Some(0), 2, 0, 1), 1, 0),
            ((0, N40, Some(0), 2, 0, 0), 1, 0),
            ((0, N40, Some(0), 2, 1, 1), 1, 0)
        ]
    );
}

#[test]
fn a_layoff_takes_from_the_most_at_work_and_a_tie_goes_to_fewer_units() {
    // separations = 1: (2, 0, 0) and (2, 1, 1) tie; the one with no unit goes
    assert_eq!(
        after(separations(1)),
        vec![
            ((0, B50, Some(0), 1, 1, 1), 2, 0),
            ((0, N40, Some(0), 1, 1, 0), 1, 0),
            ((0, N40, Some(0), 2, 1, 1), 1, 0)
        ]
    );
    // separations = 2: both go
    assert_eq!(
        after(separations(2)),
        vec![
            ((0, B50, Some(0), 1, 1, 1), 2, 0),
            ((0, N40, Some(0), 1, 1, 0), 1, 0),
            ((0, N40, Some(0), 1, 2, 1), 1, 0)
        ]
    );
}

#[test]
fn a_seeker_who_leaves_the_labor_force_keeps_the_households_unit() {
    // left_seeking = 1: weights 2 and 1; the larger remainder is the (B50, 1, 1, 1) row
    assert_eq!(
        after(left_seeking(1)),
        vec![
            ((0, B50, Some(0), 1, 0, 1), 1, 0),
            ((0, B50, Some(0), 1, 1, 1), 1, 0),
            ((0, N40, Some(0), 2, 0, 0), 1, 0),
            ((0, N40, Some(0), 2, 1, 1), 1, 0)
        ]
    );
}

#[test]
fn a_person_at_work_who_leaves_is_taken_from_the_households_with_the_most_at_work() {
    let changes = Changes {
        left_at_work: 3,
        ..Changes::default()
    };
    // the two with 2 at work lose one each, then the third comes from the level now at 1, which holds
    // the four households in proportion: 2 : 1 : 1 by (units, seeking, at_work, band), the tie falling on
    // the earliest
    let result = after(changes);
    let at_work: u64 = result
        .iter()
        .map(|((_, _, _, at_work, _, _), households, _)| u64::from(*at_work) * households)
        .sum();
    assert_eq!(at_work, 3, "six people at work less three who left");
    assert!(
        result
            .iter()
            .all(|((_, _, _, at_work, _, _), _, _)| *at_work <= 1),
        "the households with the most at work lose first: {result:?}"
    );
}

#[test]
fn a_household_keeps_its_band_and_an_exact_tie_between_bands_falls_on_the_lower() {
    let c = support::config(&[(6, 0, false)], &[0]);
    let r = support::hand_roster(
        &c,
        &[
            ((0, B50, Some(0), 1, 0, 0), 3, 0),
            ((0, N40, Some(0), 1, 0, 0), 3, 0),
        ],
    );
    let f = support::facts(&c, &r, &[(0, separations(1))], &[6]);
    let rolled = practice_contract::roll_forward(&c, &r, &f).expect("rolls");
    // the two rows tie for it, and the lower band gives it
    assert_eq!(
        support::rows(&rolled),
        vec![
            ((0, B50, Some(0), 0, 1, 0), 1, 0),
            ((0, B50, Some(0), 1, 0, 0), 2, 0),
            ((0, N40, Some(0), 1, 0, 0), 3, 0)
        ]
    );
    assert_eq!(rolled.period, 1, "the roster stands for the next period");
}

/// 9 households, 2 units, `E = 4`, `S = 2` opens as `(B50, None, 0, 0, 0) x 3`,
/// `(B50, Some(0), 0, 1, 1) x 2` and `(N40, Some(0), 1, 0, 0) x 4`.
fn nine() -> (CountyReviewConfig, Roster) {
    let c = support::config(&[(9, 2, false)], &[0]);
    let r = practice_contract::opening_roster(&c, &[support::open(0, 4, 2)], &[]).expect("opens");
    assert_eq!(
        support::rows(&r),
        vec![
            ((0, B50, None, 0, 0, 0), 3, 0),
            ((0, B50, Some(0), 0, 1, 1), 2, 0),
            ((0, N40, Some(0), 1, 0, 0), 4, 0)
        ],
        "the opening this test starts from"
    );
    (c, r)
}

#[test]
fn a_household_left_with_nobody_in_the_labor_force_has_no_crew_and_can_leave_with_its_unit() {
    let (c, r) = nine();
    // left_seeking = 1 makes one (0, 1, 1) household (B50, None, 0, 0, 1); closing_households = 8:
    // one household leaves, in proportion 3 : 1, so it is one with no unit
    let f = support::facts(&c, &r, &[(0, left_seeking(1))], &[8]);
    let rolled = practice_contract::roll_forward(&c, &r, &f).expect("rolls");
    assert_eq!(
        support::rows(&rolled),
        vec![
            ((0, B50, None, 0, 0, 0), 2, 0),
            ((0, B50, None, 0, 0, 1), 1, 0),
            ((0, B50, Some(0), 0, 1, 1), 1, 0),
            ((0, N40, Some(0), 1, 0, 0), 4, 0)
        ]
    );
    assert_eq!(rolled.groups[0].departed_units, 0);
    assert_eq!(rolled.groups[0].households, 8);

    // closing_households = 5: all four leave, and departed_units becomes 1
    let f = support::facts(&c, &r, &[(0, left_seeking(1))], &[5]);
    let rolled = practice_contract::roll_forward(&c, &r, &f).expect("rolls");
    assert_eq!(
        support::rows(&rolled),
        vec![
            ((0, B50, Some(0), 0, 1, 1), 1, 0),
            ((0, N40, Some(0), 1, 0, 0), 4, 0)
        ]
    );
    assert_eq!(rolled.groups[0].departed_units, 1);
    assert_eq!(
        rolled.group_units(0) + rolled.groups[0].departed_units,
        2,
        "a unit that leaves with a household stays in the roll"
    );

    // closing_households = 4: only four have nobody in the labor force
    let f = support::facts(&c, &r, &[(0, left_seeking(1))], &[4]);
    assert_eq!(
        practice_contract::roll_forward(&c, &r, &f),
        Err(CountyReviewError::HouseholdsBelowLaborHouseholds)
    );

    // more households than the roster holds
    let f = support::facts(&c, &r, &[(0, left_seeking(1))], &[10]);
    assert_eq!(
        practice_contract::roll_forward(&c, &r, &f),
        Err(CountyReviewError::RosterEngineMismatch)
    );
}

#[test]
fn a_moved_household_stays_reached_or_unreached() {
    let c = support::config(&[(2, 2, false)], &[0]);
    let r = support::hand_roster(&c, &[((0, B50, Some(0), 1, 1, 1), 2, 1)]);
    let f = support::facts(&c, &r, &[(0, hires(1))], &[2]);
    let rolled = practice_contract::roll_forward(&c, &r, &f).expect("rolls");
    // the unreached household moves
    assert_eq!(
        support::rows(&rolled),
        vec![
            ((0, B50, Some(0), 1, 1, 1), 1, 1),
            ((0, B50, Some(0), 2, 0, 1), 1, 0)
        ]
    );
}

#[test]
fn sums_that_do_not_match_the_engine_are_refused() {
    let (c, r) = base();
    let mut bad = support::facts(&c, &r, &[], &[4]);
    bad.crews[0].opening_at_work = 7; // against a roster that holds 6
    assert_eq!(
        practice_contract::roll_forward(&c, &r, &bad),
        Err(CountyReviewError::RosterEngineMismatch)
    );
    let mut bad = support::facts(&c, &r, &[], &[4]);
    bad.crews[0].closing_seeking += 1; // the changes do not give the engine's closing sum
    assert_eq!(
        practice_contract::roll_forward(&c, &r, &bad),
        Err(CountyReviewError::RosterEngineMismatch)
    );
    let mut bad = support::facts(&c, &r, &[], &[4]);
    bad.crews.clear();
    assert_eq!(
        practice_contract::roll_forward(&c, &r, &bad),
        Err(CountyReviewError::FactsShape)
    );
    let too_many = support::facts(&c, &r, &[(0, hires(4))], &[4]);
    assert_eq!(
        practice_contract::roll_forward(&c, &r, &too_many),
        Err(CountyReviewError::RosterEngineMismatch),
        "three seekers cannot supply four hires"
    );
}

#[test]
fn the_other_bounds_take_the_households_that_hold_units_first_or_last() {
    let c = support::config(&[(4, 1, false)], &[0]);
    let r = support::hand_roster(
        &c,
        &[
            ((0, B50, Some(0), 1, 0, 0), 3, 0),
            ((0, B50, Some(0), 1, 1, 1), 1, 0),
        ],
    );
    let f = support::facts(&c, &r, &[(0, separations(1))], &[4]);
    let run = |placement| {
        support::rows(&practice_contract::roll_forward_with(&c, &r, &f, placement).expect("rolls"))
    };
    assert_eq!(
        run(Placement::Declared),
        vec![
            ((0, B50, Some(0), 0, 1, 0), 1, 0),
            ((0, B50, Some(0), 1, 0, 0), 2, 0),
            ((0, B50, Some(0), 1, 1, 1), 1, 0)
        ],
        "in proportion 3 : 1 the larger remainder is the household with no unit"
    );
    assert_eq!(
        run(Placement::HoldersFirst),
        vec![
            ((0, B50, Some(0), 0, 2, 1), 1, 0),
            ((0, B50, Some(0), 1, 0, 0), 3, 0)
        ]
    );
    assert_eq!(
        run(Placement::HoldersLast),
        vec![
            ((0, B50, Some(0), 0, 1, 0), 1, 0),
            ((0, B50, Some(0), 1, 0, 0), 2, 0),
            ((0, B50, Some(0), 1, 1, 1), 1, 0)
        ]
    );
}

#[test]
fn a_roster_that_breaks_a_rule_is_refused_by_name() {
    let c = support::config(&[(4, 0, false)], &[0]);
    let good = support::hand_roster(&c, &[((0, B50, Some(0), 1, 0, 0), 4, 0)]);
    assert_eq!(practice_contract::validate_roster(&c, &good), Ok(()));

    let mut bad = good.clone();
    bad.rows[0].reached = 5;
    assert_eq!(
        practice_contract::validate_roster(&c, &bad),
        Err(CountyReviewError::ReachedExceedsHouseholds)
    );
    let mut bad = good.clone();
    bad.rows[0].households = 0;
    assert_eq!(
        practice_contract::validate_roster(&c, &bad),
        Err(CountyReviewError::EmptyRosterRow)
    );
    let mut bad = good.clone();
    bad.groups[0].households = 5;
    assert_eq!(
        practice_contract::validate_roster(&c, &bad),
        Err(CountyReviewError::GroupHouseholdsMismatch)
    );
    let mut bad = good.clone();
    bad.rows[0].key.crew = None;
    assert_eq!(
        practice_contract::validate_roster(&c, &bad),
        Err(CountyReviewError::CrewlessRowInLaborForce)
    );
    let mut bad = good.clone();
    bad.rows[0].key.band = T1;
    assert_eq!(
        practice_contract::validate_roster(&c, &bad),
        Err(CountyReviewError::TopBandWithCrew)
    );
    let mut bad = good.clone();
    bad.rows[0].key.crew = Some(3);
    assert_eq!(
        practice_contract::validate_roster(&c, &bad),
        Err(CountyReviewError::UnknownCrew)
    );
    let mut bad = good.clone();
    bad.groups.clear();
    assert_eq!(
        practice_contract::validate_roster(&c, &bad),
        Err(CountyReviewError::RosterShape)
    );

    let two = support::config(&[(2, 0, false), (2, 0, false)], &[0, 1]);
    let mixed = support::hand_roster(
        &two,
        &[
            ((1, B50, Some(0), 1, 0, 0), 2, 0),
            ((0, B50, None, 0, 0, 0), 2, 0),
        ],
    );
    assert_eq!(
        practice_contract::validate_roster(&two, &mixed),
        Err(CountyReviewError::CrewGroupMismatch)
    );
    let unsorted = {
        let mut r = support::hand_roster(
            &c,
            &[
                ((0, B50, Some(0), 1, 0, 0), 2, 0),
                ((0, N40, Some(0), 1, 0, 0), 2, 0),
            ],
        );
        r.rows.reverse();
        r
    };
    assert_eq!(
        practice_contract::validate_roster(&c, &unsorted),
        Err(CountyReviewError::RosterNotCanonical)
    );
}

#[test]
fn band_counts_show_who_works_in_each_band_top_first() {
    let c = support::config(&[(20, 2, true)], &[0]);
    let r = practice_contract::opening_roster(&c, &[support::open(0, 5, 2)], &[]).expect("opens");
    let counts = r.band_counts();
    assert_eq!(
        counts.iter().map(|b| b.band).collect::<Vec<Band>>(),
        vec![T1, N9, N40, B50]
    );
    let top = &counts[0];
    assert_eq!(
        (top.households, top.outside_labor_force, top.with_work),
        (2, 2, 0)
    );
    let next9 = &counts[1];
    assert_eq!(
        (
            next9.households,
            next9.with_work,
            next9.seeking_only,
            next9.outside_labor_force
        ),
        (18, 5, 2, 11)
    );
    assert_eq!(
        (next9.people_at_work, next9.people_seeking, next9.units),
        (5, 2, 2)
    );
    assert_eq!(r.crew_at_work(0), 5);
    assert_eq!(r.crew_seeking(0), 2);
    assert_eq!(r.group_units(0), 2);
}

/// One random period that the sums allow.
fn random_changes(
    rng: &mut Rng,
    c: &CountyReviewConfig,
    r: &Roster,
) -> (Vec<(u32, Changes)>, Vec<u64>) {
    let mut changes = Vec::new();
    for i in 0..c.crews.len() {
        let crew = u32::try_from(i).expect("small");
        let (e, s) = (r.crew_at_work(crew), r.crew_seeking(crew));
        let left_at_work = rng.up_to(e.min(3));
        let left_seeking = rng.up_to(s.min(3));
        let (e, s) = (e - left_at_work, s - left_seeking);
        let (hires, separations) = if rng.up_to(1) == 0 {
            (rng.up_to(s.min(4)), 0)
        } else {
            (0, rng.up_to(e.min(4)))
        };
        changes.push((
            crew,
            Changes {
                left_at_work,
                left_seeking,
                hires,
                separations,
            },
        ));
    }
    let closing = r
        .groups
        .iter()
        .enumerate()
        .map(|(g, group)| {
            let crewless: u64 = r
                .rows
                .iter()
                .filter(|row| {
                    usize::try_from(row.key.group).expect("small") == g && row.key.crew.is_none()
                })
                .map(|row| row.households)
                .sum();
            group.households - rng.up_to(crewless.min(3))
        })
        .collect();
    (changes, closing)
}

fn band_households(r: &Roster) -> Vec<u64> {
    r.band_counts().iter().map(|b| b.households).collect()
}

fn reached(r: &Roster) -> u64 {
    r.rows.iter().map(|row| row.reached).sum()
}

#[test]
fn rolling_forward_keeps_every_total() {
    let mut rng = Rng(0x9e37_79b9_7f4a_7c15);
    let mut accepted = 0;
    let mut attempts = 0;
    while accepted < 200 {
        attempts += 1;
        assert!(
            attempts < 200_000,
            "the law accepted too few random openings"
        );
        let Some((c, _, mut roster)) = support::random_opening(&mut rng) else {
            continue;
        };
        accepted += 1;
        let roll: Vec<u64> = (0..c.groups.len())
            .map(|g| roster.group_units(u32::try_from(g).expect("small")))
            .collect();
        for _ in 0..6 {
            let (changes, closing) = random_changes(&mut rng, &c, &roster);
            let f = support::facts(&c, &roster, &changes, &closing);
            let next = practice_contract::roll_forward(&c, &roster, &f)
                .expect("a period the sums allow rolls");
            let left: u64 = roster
                .groups
                .iter()
                .zip(&closing)
                .map(|(before, after)| before.households - after)
                .sum();
            for (g, group) in next.groups.iter().enumerate() {
                assert_eq!(
                    group.households, closing[g],
                    "group {g} households follow the engine"
                );
                assert_eq!(
                    next.group_units(u32::try_from(g).expect("small")) + group.departed_units,
                    roll[g],
                    "group {g}: units held plus units departed stay the roll"
                );
            }
            for i in 0..changes.len() {
                let crew = u32::try_from(i).expect("small");
                let f_crew = &f.crews[i];
                assert_eq!(
                    next.crew_at_work(crew),
                    f_crew.closing_at_work,
                    "crew {i} at work"
                );
                assert_eq!(
                    next.crew_seeking(crew),
                    f_crew.closing_seeking,
                    "crew {i} seeking"
                );
            }
            let (before, now) = (band_households(&roster), band_households(&next));
            assert!(
                before.iter().zip(&now).all(|(b, n)| n <= b),
                "no band gains a household: {before:?} then {now:?}"
            );
            assert_eq!(
                before.iter().sum::<u64>() - now.iter().sum::<u64>(),
                left,
                "bands lose exactly the households that left"
            );
            if left == 0 {
                assert_eq!(
                    before, now,
                    "with no departure each band keeps its households"
                );
                assert_eq!(reached(&next), reached(&roster), "nobody becomes unreached");
            } else {
                assert!(
                    reached(&next) <= reached(&roster),
                    "reach only falls with a departure"
                );
            }
            assert!(
                next.rows
                    .iter()
                    .all(|row| row.key.band != T1 || row.key.crew.is_none()),
                "no top 1% household is in the labor force"
            );
            assert_eq!(next.period, roster.period + 1);
            roster = next;
        }
    }
}

#[test]
fn bands_are_a_fixed_ordering_lowest_first() {
    assert!(
        Band::Bottom50 < Band::Next40 && Band::Next40 < Band::Next9 && Band::Next9 < Band::Top1
    );
}
