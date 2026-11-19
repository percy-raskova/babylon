//! The preview and the fogged projection.
use babylon_practice_contract as practice_contract;
use babylon_practice_contract::{
    Band, ContactOutcome, CountyReviewConfig, CountyReviewError, CountyReviewProjection,
    CountyReviewState, LedgerInput, LedgerLine, LedgerLineKind, PayMode, PositionKey, PositionView,
};

use super::support;
use super::support::{A, B, C, D};

fn line(kind: LedgerLineKind, label: &str, amount_micros: i128, first_class: bool) -> LedgerLine {
    LedgerLine {
        kind,
        label: label.to_owned(),
        amount_micros,
        first_class,
    }
}

fn workplace(label: &str, amount_micros: i128) -> LedgerLine {
    line(LedgerLineKind::PublicWorkplace, label, amount_micros, true)
}

fn agency(amount_micros: i128) -> LedgerLine {
    line(
        LedgerLineKind::CityPdVisits,
        "City PD visits",
        amount_micros,
        true,
    )
}

fn ledger() -> LedgerInput {
    LedgerInput {
        cash_micros: 1_400_000_000,
        spending_limit_micros: 10_000_000_000,
        lines: Vec::new(),
        city_pd_payroll: None,
    }
}

fn project(
    c: &CountyReviewConfig,
    state: &CountyReviewState,
    input: &LedgerInput,
    contacted: &[PositionKey],
) -> CountyReviewProjection {
    practice_contract::project(c, state, input, contacted).expect("the projection is made")
}

fn view(p: &CountyReviewProjection, key: PositionKey) -> &PositionView {
    p.positions
        .iter()
        .find(|v| v.key == key)
        .expect("the position is in the projection")
}

fn amounts(lines: &[LedgerLine]) -> Vec<(LedgerLineKind, i128)> {
    lines.iter().map(|l| (l.kind, l.amount_micros)).collect()
}

#[test]
fn amounts_are_shown_only_for_a_contacted_position() {
    let (c, state) = support::state_after_contact();
    let p = project(&c, &state, &ledger(), &[D]);
    assert!(view(&p, D).earned.is_some() && view(&p, D).contacted);
    for key in [A, B, C] {
        assert!(view(&p, key).earned.is_none() && !view(&p, key).contacted);
    }
    // The list is public.
    assert_eq!((view(&p, C).units_listed, view(&p, C).units_unpaid), (2, 1));
    let earned = view(&p, D).earned.as_ref().expect("D is contacted");
    assert_eq!(earned.wage_tax_micros_per_household, 576_000_000);
    assert_eq!(earned.wage_micros_per_household, 3_840_000_000);
    assert_eq!((earned.households, earned.reached), (1, 1));
    assert_eq!(earned.stake_micros, 280_000_000);
    assert_eq!(earned.asked, 1);
}

#[test]
fn nothing_earned_appears_for_a_position_the_player_has_not_contacted() {
    let (c, mut state) = support::state_after_contact();
    let facts = state.last_facts.as_mut().expect("the facts are held");
    facts.groups[0].ownership_income_micros = 123_456_789;
    facts.groups[0].support_income_micros = 223_456_789;
    facts.groups[0].aid_income_micros = 323_456_789;
    let unknown = project(&c, &state, &ledger(), &[]);
    let known = project(&c, &state, &ledger(), &[D]);
    // From the fog's side: no earned figure is in the projection of a county nobody has reached.
    let text = serde_json::to_string(&unknown).expect("the projection serializes");
    for earned in [
        "576000000",
        "3840000000",
        "123456789",
        "223456789",
        "323456789",
    ] {
        assert!(!text.contains(&format!("\"{earned}\"")), "{earned} leaked");
    }
    assert!(unknown.positions.iter().all(|v| v.earned.is_none()));
    // From the contact's side: the figures appear for D and only for D.
    let text = serde_json::to_string(&known).expect("the projection serializes");
    for earned in ["576000000", "3840000000", "123456789"] {
        assert!(text.contains(&format!("\"{earned}\"")), "{earned} is shown");
    }
    for v in &known.positions {
        if v.key == D {
            continue;
        }
        assert_eq!(v, view(&unknown, v.key), "{:?} is unchanged", v.key);
    }
    let (with, without) = (view(&known, D), view(&unknown, D));
    assert_eq!(
        PositionView {
            contacted: false,
            earned: None,
            ..with.clone()
        },
        *without
    );
    // Everything but the positions is the same for both.
    assert_eq!(
        CountyReviewProjection {
            positions: Vec::new(),
            ..known
        },
        CountyReviewProjection {
            positions: Vec::new(),
            ..unknown
        }
    );
}

#[test]
fn the_list_is_public_and_ordered_by_rank_then_key() {
    let (c, state) = support::state_after_contact();
    let p = project(&c, &state, &ledger(), &[]);
    let order: Vec<PositionKey> = p.positions.iter().map(|v| v.key).collect();
    assert_eq!(order, vec![A, D, B, C], "A and D share rank 1; then B, C");
    let ranks: Vec<Option<u32>> = p.positions.iter().map(|v| v.rank).collect();
    assert_eq!(ranks, vec![Some(1), Some(1), Some(2), Some(3)]);
    assert_eq!(p.session_period, Some(0));
    assert_eq!(
        p.contact,
        Some((D, ContactOutcome::Reached)),
        "the contact is public"
    );
    assert_eq!(p.household_units_payable, Some(5));
    assert_eq!(p.kept_back_units, Some(0));
    assert_eq!(view(&p, D).asked_paid, 1);
    let (before_config, before) = support::state_before_contact();
    let p = project(&before_config, &before, &ledger(), &[]);
    assert_eq!(p.session_period, None);
    assert!(p.positions.iter().all(|v| v.rank.is_none()));
    let order: Vec<PositionKey> = p.positions.iter().map(|v| v.key).collect();
    let mut sorted = order.clone();
    sorted.sort();
    assert_eq!(order, sorted, "with no session the order is the key's");
    assert_eq!((p.relief_micros, p.household_units_payable), (None, None));
    let text = serde_json::to_string(&p).expect("the projection serializes");
    assert!(
        text.contains("\"relief_micros\":null"),
        "no session, no relief"
    );
}

#[test]
fn relief_is_a_decimal_string_and_round_trips() {
    let (c, state) = support::state_after_contact();
    let p = project(&c, &state, &ledger(), &[]);
    let text = serde_json::to_string(&p).expect("the projection serializes");
    assert!(
        text.contains("\"relief_micros\":\"1400000000\""),
        "relief is a decimal string: {text}"
    );
    let back: CountyReviewProjection =
        serde_json::from_str(&text).expect("the projection deserializes");
    assert_eq!(back, p);
    let bare = text.replace(
        "\"relief_micros\":\"1400000000\"",
        "\"relief_micros\":1400000000",
    );
    assert!(serde_json::from_str::<CountyReviewProjection>(&bare).is_err());
    let padded = text.replace(
        "\"relief_micros\":\"1400000000\"",
        "\"relief_micros\":\"01400000000\"",
    );
    assert!(serde_json::from_str::<CountyReviewProjection>(&padded).is_err());
}

#[test]
fn a_position_shows_its_structure_whether_or_not_it_is_contacted() {
    let (c, state) = support::state_before_contact();
    let p = project(&c, &state, &ledger(), &[]);
    let a = view(&p, A);
    assert_eq!(a.group_label, "Group 0");
    assert_eq!(a.workplace_label.as_deref(), Some("Workplace 0"));
    assert_eq!(a.pay_mode, Some(PayMode::Wage));
    assert!(a.has_wages && a.has_support && !a.has_ownership_income && !a.has_mutual_aid);
    let d = view(&p, D);
    assert!(d.has_wages && !d.has_support, "D holds no unit");
    let c_view = view(&p, C);
    assert_eq!(c_view.workplace_label.as_deref(), Some("Workplace 2"));
    assert!(!c_view.has_wages, "nobody of C is at work");
    assert_eq!(c_view.group_label, "Group 1");
}

#[test]
fn the_ledger_names_the_city_pd_payroll_inside_the_workplace_grant() {
    let (c, state) = support::state_before_contact();
    let input = LedgerInput {
        lines: vec![
            workplace("County public workplace", 20_000_000_000_000),
            agency(24_000_000),
            line(
                LedgerLineKind::HouseholdSupport,
                "Group 0 support",
                840_000_000,
                false,
            ),
        ],
        city_pd_payroll: Some((
            "County public workplace".to_owned(),
            3_529,
            13_551_360_000_000,
        )),
        ..ledger()
    };
    let p = project(&c, &state, &input, &[]);
    assert_eq!(
        amounts(&p.ledger),
        vec![
            (LedgerLineKind::PublicWorkplace, 6_448_640_000_000),
            (LedgerLineKind::CityPdPayroll, 13_551_360_000_000),
            (LedgerLineKind::CityPdVisits, 24_000_000),
            (LedgerLineKind::HouseholdSupport, 840_000_000),
        ]
    );
    assert_eq!(p.first_class_micros, 20_000_024_000_000);
    assert_eq!(
        (p.cash_micros, p.unit_price_micros),
        (1_400_000_000, 280_000_000)
    );
    let without = project(
        &c,
        &state,
        &LedgerInput {
            city_pd_payroll: None,
            ..input
        },
        &[],
    );
    assert_eq!(without.ledger.len(), 3, "no payroll, no payroll line");
    assert_eq!(without.first_class_micros, 20_000_024_000_000);
}

#[test]
fn a_payroll_larger_than_its_workplace_or_without_one_is_refused() {
    let (c, state) = support::state_before_contact();
    let mut input = LedgerInput {
        lines: vec![workplace("County public workplace", 1_000)],
        city_pd_payroll: Some(("County public workplace".to_owned(), 1, 1_001)),
        ..ledger()
    };
    assert_eq!(
        practice_contract::project(&c, &state, &input, &[]),
        Err(CountyReviewError::LedgerPayrollNotInWorkplace)
    );
    input.city_pd_payroll = Some(("Elsewhere".to_owned(), 1, 1));
    assert_eq!(
        practice_contract::project(&c, &state, &input, &[]),
        Err(CountyReviewError::LedgerPayrollNotInWorkplace)
    );
}

#[test]
fn the_roll_is_listed_by_group() {
    let (c, state) = support::state_before_contact();
    let p = project(&c, &state, &ledger(), &[]);
    assert_eq!(
        p.roll,
        vec![("Group 0".to_owned(), 3), ("Group 1".to_owned(), 2)]
    );
    assert_eq!(p.roster_period, 0);
    assert_eq!(p.first_session_period, 1);
    assert_eq!(p.county, *b"26163");
}

#[test]
fn who_works_in_each_band_is_a_public_county_total() {
    let (c, state) = support::state_before_contact();
    let p = project(&c, &state, &ledger(), &[]);
    let got: Vec<_> = p
        .bands
        .iter()
        .map(|b| {
            (
                b.band,
                b.households,
                b.with_work,
                b.seeking_only,
                b.outside_labor_force,
                b.people_at_work,
                b.people_seeking,
                b.units,
            )
        })
        .collect();
    assert_eq!(
        got,
        vec![
            (Band::Top1, 0, 0, 0, 0, 0, 0, 0),
            (Band::Next9, 0, 0, 0, 0, 0, 0, 0),
            (Band::Next40, 1, 1, 0, 0, 1, 0, 0),
            (Band::Bottom50, 5, 3, 2, 0, 3, 5, 5),
        ]
    );
    // Public: contacting someone does not change them.
    let known = project(&c, &state, &ledger(), &[A, B, C, D]);
    assert_eq!(known.bands, p.bands);
}

#[test]
fn the_preview_reads_only_the_public_record() {
    let (c, state) = support::state_before_contact();
    let pv = practice_contract::preview_contact(&c, &state, D)
        .expect("the preview is made")
        .expect("a close has been seen");
    assert_eq!(
        (pv.outcome, pv.asks, pv.place_open),
        (ContactOutcome::Reached, true, true)
    );
    assert_eq!(pv.taken_from, vec![C]);
    assert_eq!(pv.then_at_stake, vec![C]);
    assert_eq!(pv.basis_period, 0);
    assert_eq!(pv.key, D);
    let none = CountyReviewState {
        last_facts: None,
        ..state
    };
    assert_eq!(practice_contract::preview_contact(&c, &none, D), Ok(None));
}

#[test]
fn a_preview_of_a_household_that_holds_a_unit_asks_for_nothing() {
    let (c, state) = support::state_before_contact();
    let pv = practice_contract::preview_contact(&c, &state, C)
        .expect("the preview is made")
        .expect("a close has been seen");
    assert!(!pv.asks && !pv.place_open);
    assert_eq!(pv.outcome, ContactOutcome::Reached);
}

#[test]
fn a_household_with_no_hours_to_give_does_not_ask_and_the_preview_does_not_say_no_place() {
    let (c, mut state) = support::state_before_contact();
    let facts = state.last_facts.as_mut().expect("the facts are held");
    for group in &mut facts.groups {
        group.free_hours = 0;
    }
    let pv = practice_contract::preview_contact(&c, &state, D)
        .expect("the preview is made")
        .expect("a close has been seen");
    assert_eq!(pv.outcome, ContactOutcome::Reached);
    assert!(!pv.asks, "the household has no time to ask");
    assert!(!pv.place_open);
}

#[test]
fn a_preview_of_a_position_that_does_not_exist_or_has_nobody_left_changes_nothing() {
    let (c, mut state) = support::state_before_contact();
    let missing = PositionKey { units: 9, ..D };
    let pv = practice_contract::preview_contact(&c, &state, missing)
        .expect("the preview is made")
        .expect("a close has been seen");
    assert_eq!(pv.outcome, ContactOutcome::NoSuchPosition);
    assert!(!pv.asks && !pv.place_open && pv.taken_from.is_empty() && pv.then_at_stake.is_empty());
    support::reach(&mut state.roster, D, 1);
    let pv = practice_contract::preview_contact(&c, &state, D)
        .expect("the preview is made")
        .expect("a close has been seen");
    assert_eq!(pv.outcome, ContactOutcome::NobodyLeft);
    assert!(!pv.asks && !pv.place_open && pv.taken_from.is_empty());
}

#[test]
fn the_preview_after_a_roll_forward_with_hires_still_answers() {
    let (c, mut r, mut f) = support::world();
    support::short(&mut f, 5);
    let outcome =
        practice_contract::hold_session(&c, &r, &f, Some(D)).expect("the session is held");
    // Crew 0 hires one of its two job-seekers in the period.
    f.crews[0].hires = 1;
    f.crews[0].closing_at_work = 4;
    f.crews[0].closing_seeking = 1;
    let rolled =
        practice_contract::roll_forward(&c, &outcome.roster, &f).expect("the roster rolls forward");
    assert_ne!(
        rolled.crew_at_work(0),
        f.crews[0].opening_at_work,
        "the stored roster no longer matches the last close's opening"
    );
    r = rolled;
    let key = r
        .rows
        .iter()
        .find(|row| row.reached < row.households)
        .map(|row| row.key)
        .expect("a household is still unreached");
    let state = CountyReviewState {
        schema_version: 1,
        roster: r,
        last_facts: Some(f),
        last_session: Some(outcome.record),
    };
    let pv = practice_contract::preview_contact(&c, &state, key)
        .expect("the preview is not refused")
        .expect("a close has been seen");
    assert_eq!(pv.basis_period, 0, "the preview is of the last close");
    let p = project(&c, &state, &ledger(), &[]);
    assert!(p.positions.iter().any(|v| v.key == key));
}

#[test]
fn a_projection_of_a_state_the_roster_refuses_is_refused() {
    let (c, mut state) = support::state_before_contact();
    state.roster.rows.swap(0, 1);
    assert_eq!(
        practice_contract::project(&c, &state, &ledger(), &[]),
        Err(CountyReviewError::RosterNotCanonical)
    );
    assert_eq!(
        practice_contract::preview_contact(&c, &state, D),
        Err(CountyReviewError::RosterNotCanonical)
    );
}

#[test]
fn a_crew_with_nobody_at_work_and_a_group_with_no_taxed_wages_stand_at_zero() {
    // C has nobody at work; group 1 pays no wage tax. Nothing divides by zero.
    let (c, r, mut f) = support::world_with(&[support::tuple(C, 2, 1)]);
    f.groups[0].taxed_wages_micros = 0;
    let state = CountyReviewState {
        schema_version: 1,
        roster: r,
        last_facts: Some(f),
        last_session: None,
    };
    let p = project(&c, &state, &ledger(), &[C]);
    let earned = view(&p, C).earned.as_ref().expect("C is contacted");
    assert_eq!(
        (
            earned.wage_micros_per_household,
            earned.wage_tax_micros_per_household
        ),
        (0, 0)
    );
}
