//! The county's session rule crosses the real BSL/tick boundary.
//!
//! The world is a hand-built staffed county (`support/county_review_fixture.rs`): the engine pays and
//! taxes wages, closes household time, and pays the county's support lines. Each period runs the
//! organizer's practice and then the county's session through the real rules.

// Shared fixture modules contain helpers used by other integration targets.
#[allow(
    dead_code,
    reason = "the fixture's knobs are used by some of the tests only"
)]
#[path = "support/county_review_fixture.rs"]
mod county_fixture;
#[allow(
    dead_code,
    reason = "the shared fixture module serves other integration targets"
)]
#[path = "../../babylon-persistence/src/michigan_dynamic_hex_foundation.rs"]
mod michigan_dynamic_hex_foundation;
#[allow(
    dead_code,
    reason = "the shared fixture module serves other integration targets"
)]
#[path = "support/organizer_aid_fixture.rs"]
mod organizer_aid_fixture;

use babylon_bsl::causal_contract::EffectSignature;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_kernel::content_digest;
use babylon_material_circuit::{
    AccountId, CircuitAccounting, FinalDemandPrincipalId, HouseholdTimeAccounting, MonetaryCircuit,
    PublicTransferTreatment,
};
use babylon_practice_contract::{
    ContactOutcome, OrganizerChoice, OrganizerOutcome, PositionKey, SessionRecord,
};
use babylon_tick::material_world::{self, MaterialWorldRegister};

use crate::county_fixture::{Options, COUNTY_ACTOR, GRANT_MICROS, UNIT_MICROS};
use crate::organizer_aid_fixture::{Candidate, Session, MATERIAL, PRACTICE, PRODUCTS};

const COUNTY_REVIEW: &str =
    include_str!("../../../../content/scenarios/national/county-review-cycle.bsl");

fn rules() -> String {
    format!("{MATERIAL}\n{PRODUCTS}\n{PRACTICE}\n{COUNTY_REVIEW}")
}

fn session(options: Options) -> Session {
    let foundation = michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
        .expect("the Michigan hex foundation builds");
    county_fixture::try_session(foundation, &rules(), options, true)
        .expect("the county fixture opens a session")
}

fn prepare(session: &Session, choice: Option<OrganizerChoice>) -> Candidate {
    let accepted = choice.map(|choice| organizer_aid_fixture::commitment(session, choice));
    organizer_aid_fixture::prepare(session, accepted.as_ref())
}

fn commit(session: &mut Session, candidate: Candidate) {
    let mut sink = CollectingSink::default();
    organizer_aid_fixture::commit(session, &mut sink, candidate);
}

/// One whole period: prepare it, and commit it.
fn period(session: &mut Session, choice: Option<OrganizerChoice>) {
    let candidate = prepare(session, choice);
    commit(session, candidate);
}

fn monetary(register: &MaterialWorldRegister) -> &MonetaryCircuit {
    let CircuitAccounting::Monetary(economy) = &register.state().accounting else {
        panic!("the county world is monetary");
    };
    economy
}

/// The household support lines of the county's account: `(recipient principal, amount)`.
fn support_lines(register: &MaterialWorldRegister) -> Vec<([u8; 32], i128)> {
    monetary(register)
        .financial
        .public_allocations
        .iter()
        .filter(|row| row.treatment == PublicTransferTreatment::HouseholdIncomeSupport)
        .map(|row| {
            let AccountId::Household(principal) = row.recipient else {
                panic!("support goes to households");
            };
            (principal.as_bytes(), row.amount_per_period.micro_units())
        })
        .collect()
}

fn session_record(register: &MaterialWorldRegister) -> &SessionRecord {
    register
        .county_review()
        .expect("the register carries the county")
        .state()
        .last_session
        .as_ref()
        .expect("the county held a session")
}

/// The county's own uses of household hours: `(principal, hours, period, use identifier)`.
fn county_uses(register: &MaterialWorldRegister) -> Vec<([u8; 32], u64, u64, [u8; 32])> {
    let HouseholdTimeAccounting::Modeled(time) = &monetary(register).household_time else {
        panic!("the county world models household time");
    };
    time.contributions
        .iter()
        .filter(|row| row.contribution.actor_id == COUNTY_ACTOR)
        .map(|row| {
            (
                row.contribution.principal_id.as_bytes(),
                row.contribution.hours,
                row.period,
                row.contribution.use_id,
            )
        })
        .collect()
}

/// The position of the wage group's two households at the second workplace.
fn second_workplace(register: &MaterialWorldRegister) -> PositionKey {
    register
        .county_review()
        .expect("the register carries the county")
        .state()
        .roster
        .rows
        .iter()
        .find(|row| row.key.crew == Some(1))
        .expect("two households work at the second workplace")
        .key
}

fn wage_group() -> [u8; 32] {
    county_fixture::wage_group().as_bytes()
}

fn seeking_group() -> [u8; 32] {
    county_fixture::seeking_group().as_bytes()
}

#[test]
fn a_campaign_with_the_rule_and_no_county_section_is_refused_by_name() {
    let foundation = michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
        .expect("the Michigan hex foundation builds");
    let error = organizer_aid_fixture::try_session(
        foundation,
        &rules(),
        organizer_aid_fixture::opening(),
        organizer_aid_fixture::config(),
    )
    .err()
    .expect("the county's rule without a county section refuses before gameplay");
    assert!(
        error
            .to_string()
            .contains("County review needs a captured county administration"),
        "{error}"
    );
}

#[test]
fn the_same_campaign_without_the_rule_opens() {
    let foundation = michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
        .expect("the Michigan hex foundation builds");
    organizer_aid_fixture::try_session(
        foundation,
        &format!("{MATERIAL}\n{PRODUCTS}\n{PRACTICE}"),
        organizer_aid_fixture::opening(),
        organizer_aid_fixture::config(),
    )
    .expect("the fixture opens a session");
}

#[test]
fn a_county_section_without_the_rule_is_refused_by_name() {
    let foundation = michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
        .expect("the Michigan hex foundation builds");
    let error = county_fixture::try_session(
        foundation,
        &format!("{MATERIAL}\n{PRODUCTS}\n{PRACTICE}"),
        Options::default(),
        true,
    )
    .err()
    .expect("a county section needs its session rule");
    assert!(
        error
            .to_string()
            .contains("County review must run once after organizer practice"),
        "{error}"
    );
}

#[test]
fn before_the_first_session_only_the_roster_moves() {
    let mut session = session(Options {
        first_session_period: 4,
        ..Options::default()
    });
    let opening = session.material().clone();
    let lines = support_lines(&opening);
    assert_eq!(lines, vec![(seeking_group(), 3 * UNIT_MICROS)]);
    let candidate = prepare(&session, None);
    let register = candidate.material().register();
    let county = register.county_review().expect("the county is kept");
    assert_eq!(county.state().roster.period, 1);
    assert!(county.state().last_facts.is_some(), "the facts are kept");
    assert!(county.state().last_session.is_none(), "no session is held");
    assert_eq!(support_lines(register), lines, "no line is written");
    assert_eq!(
        monetary(register).financial,
        monetary(&opening).financial,
        "the county wrote no row of its account"
    );
    assert!(county_uses(register).is_empty(), "no hour is charged");
    commit(&mut session, candidate);
    assert_eq!(session.completed_tick(), 1);
}

#[test]
fn without_a_contact_the_lines_are_the_rolls_own() {
    let mut session = session(Options::default());
    let opening = support_lines(session.material());
    for _ in 0..2 {
        period(&mut session, None);
        let register = session.material();
        assert_eq!(support_lines(register), opening);
        assert!(county_uses(register).is_empty(), "no hour is charged");
        let record = session_record(register);
        assert_eq!(record.contact, None);
        assert_eq!(record.household_units_listed, 3);
        assert_eq!(record.household_units_payable, 3);
    }
    assert_eq!(
        session
            .material()
            .county_review()
            .expect("the county is kept")
            .state()
            .roster
            .period,
        2
    );
}

#[test]
fn a_contact_moves_a_unit_and_the_next_close_pays_the_line_in_full() {
    let mut session = session(Options::default());
    let key = second_workplace(session.material());
    assert_eq!((key.at_work, key.seeking, key.units), (1, 0, 0));
    period(&mut session, Some(OrganizerChoice::ReviewContact(key)));
    let register = session.material();
    let record = session_record(register);
    assert_eq!(record.contact, Some((key, ContactOutcome::Reached)));
    assert_eq!(
        record
            .rows
            .iter()
            .find(|row| row.key == key)
            .map(|row| (row.asked, row.asked_paid)),
        Some((1, 1)),
        "the reached household asks for a unit and is paid"
    );
    // The household with a wage gains the unit and the group that held three loses one.
    let gaining = (wage_group(), UNIT_MICROS);
    let losing = (seeking_group(), 2 * UNIT_MICROS);
    assert_eq!(support_lines(register), vec![gaining, losing]);
    let lines: Vec<_> = record
        .lines
        .iter()
        .map(|line| (line.group, line.units, line.amount_micros))
        .collect();
    assert_eq!(
        lines,
        vec![(0, 1, UNIT_MICROS), (1, 2, 2 * UNIT_MICROS)],
        "the lines the county announced"
    );
    // The next close pays those lines in full.
    let candidate = prepare(&session, None);
    let receipts = material_world::decode_material_receipts(candidate.material().receipt_bytes())
        .expect("the committed receipts decode");
    let paid = |principal: FinalDemandPrincipalId| {
        let rows: Vec<_> = receipts
            .public_budgets
            .iter()
            .filter(|row| {
                row.treatment == PublicTransferTreatment::HouseholdIncomeSupport
                    && row.recipient == AccountId::Household(principal)
            })
            .collect();
        assert_eq!(rows.len(), 1, "one support line for the group");
        (
            rows[0].requested.micro_units(),
            rows[0].paid.micro_units(),
            rows[0].unfunded.micro_units(),
        )
    };
    assert_eq!(
        paid(county_fixture::wage_group()),
        (UNIT_MICROS, UNIT_MICROS, 0),
        "the gaining group's new line is paid in full"
    );
    assert_eq!(
        paid(county_fixture::seeking_group()),
        (2 * UNIT_MICROS, 2 * UNIT_MICROS, 0),
        "the losing group's line is one unit lower, and paid in full"
    );
    commit(&mut session, candidate);
}

#[test]
fn a_contact_on_a_position_that_is_gone_spends_the_hours_and_commits() {
    let mut session = session(Options::default());
    let mut key = second_workplace(session.material());
    key.at_work = 5;
    let before = support_lines(session.material());
    period(&mut session, Some(OrganizerChoice::ReviewContact(key)));
    let register = session.material();
    assert_eq!(session.completed_tick(), 1, "the turn commits");
    assert_eq!(
        session_record(register).contact,
        Some((key, ContactOutcome::NoSuchPosition))
    );
    let receipt = register
        .organizer_journal()
        .and_then(|journal| journal.latest())
        .and_then(|entries| {
            entries
                .receipts
                .iter()
                .find(|receipt| receipt.outcome == OrganizerOutcome::ReviewContactMade)
        })
        .expect("the organizer's contact receipt is kept");
    assert_eq!(receipt.choice, OrganizerChoice::ReviewContact(key));
    assert_eq!(receipt.hours_spent, 8, "the organizer's hours are spent");
    assert_eq!(support_lines(register), before, "no unit moved");
    assert!(county_uses(register).is_empty(), "nobody came to the room");
}

#[test]
fn a_county_with_no_cash_for_relief_has_no_household_line() {
    let mut session = session(Options {
        public_cash: 0,
        ..Options::default()
    });
    // A job-seeking household is reached. It loses its unit and comes.
    let key = session
        .material()
        .county_review()
        .expect("the register carries the county")
        .state()
        .roster
        .rows
        .iter()
        .find(|row| row.key.crew == Some(2))
        .expect("the job-seekers have a position")
        .key;
    period(&mut session, Some(OrganizerChoice::ReviewContact(key)));
    let register = session.material();
    let record = session_record(register);
    assert!(record.cash_micros < record.first_class_micros);
    assert_eq!(record.relief_micros, 0);
    assert_eq!(record.household_units_payable, 0);
    assert!(record.lines.is_empty(), "nobody is paid");
    assert!(
        support_lines(register).is_empty(),
        "no zero-amount line reaches the engine"
    );
    let row = record
        .rows
        .iter()
        .find(|row| row.key == key)
        .expect("the session lists the position");
    assert_eq!(row.units_paid, 0);
    assert_eq!(
        row.came_from_roll, 1,
        "the reached household on the roll comes"
    );
    // The state still validates: its bytes decode.
    let decoded = MaterialWorldRegister::decode_external(
        session.catalog(),
        register.canonical_bytes().to_vec(),
    )
    .expect("a register with no support line decodes");
    assert_eq!(decoded.digest(), register.digest());
    period(&mut session, None);
    assert!(
        support_lines(session.material()).is_empty(),
        "the county still has no money for a line"
    );
}

#[test]
fn the_first_class_and_the_limit_are_never_written() {
    let mut session = session(Options::default());
    let first_class = |register: &MaterialWorldRegister| {
        let economy = monetary(register);
        (
            economy
                .financial
                .public_allocations
                .iter()
                .filter(|row| row.treatment != PublicTransferTreatment::HouseholdIncomeSupport)
                .cloned()
                .collect::<Vec<_>>(),
            economy.financial.public_budgets.clone(),
            economy.financial.taxes.clone(),
        )
    };
    let opening = first_class(session.material());
    assert_eq!(opening.0.len(), 1);
    assert_eq!(opening.0[0].amount_per_period.micro_units(), GRANT_MICROS);
    let key = second_workplace(session.material());
    period(&mut session, Some(OrganizerChoice::ReviewContact(key)));
    assert_eq!(first_class(session.material()), opening);
    period(&mut session, None);
    assert_eq!(first_class(session.material()), opening);
    period(&mut session, None);
    assert_eq!(first_class(session.material()), opening);
}

#[test]
fn hours_are_charged_to_the_households_group() {
    let mut session = session(Options::default());
    let key = second_workplace(session.material());
    period(&mut session, Some(OrganizerChoice::ReviewContact(key)));
    let register = session.material();
    let record = session_record(register);
    let row = record
        .rows
        .iter()
        .find(|row| row.key == key)
        .expect("the session lists the position");
    // One household asked and came (2 hours) and brought one more (2 hours).
    assert_eq!((row.hours_in_room, row.hours_bringing), (2, 2));
    let uses = county_uses(register);
    assert_eq!(uses.len(), 1, "one use for each charged group");
    let (principal, hours, period_charged, use_id) = uses[0];
    assert_eq!(principal, wage_group());
    assert_eq!(hours, 4);
    assert_eq!(period_charged, 1);
    let mut identity = b"babylon.county-review-hours.v1\0".to_vec();
    identity.extend_from_slice(&[1; 16]);
    identity.extend_from_slice(&1_u64.to_be_bytes());
    identity.extend_from_slice(&wage_group());
    assert_eq!(use_id, content_digest::sha256_of(&identity));
    let HouseholdTimeAccounting::Modeled(time) = &monetary(register).household_time else {
        panic!("the county world models household time");
    };
    let organizer_hours: u64 = time
        .contributions
        .iter()
        .filter(|row| row.contribution.actor_id != COUNTY_ACTOR)
        .map(|row| row.contribution.hours)
        .sum();
    assert!(
        organizer_hours >= 8,
        "the organizer's own contact hours stay charged"
    );
    let reach = register
        .county_review()
        .expect("the register carries the county")
        .state()
        .roster
        .rows
        .iter()
        .find(|row| row.key.crew == Some(1))
        .map(|row| row.reached);
    assert_eq!(reach, Some(2), "the contact and the household it brought");
}

#[test]
fn the_rule_runs_once_after_the_organizers_practice() {
    let session = session(Options::default());
    let candidate = prepare(&session, None);
    let effects: Vec<_> = candidate
        .graph_report()
        .report()
        .audit_receipts
        .iter()
        .map(|receipt| receipt.effect.clone())
        .collect();
    let at = |wanted: &EffectSignature| {
        effects
            .iter()
            .enumerate()
            .filter(|(_, effect)| *effect == wanted)
            .map(|(index, _)| index)
            .collect::<Vec<_>>()
    };
    let county = at(&EffectSignature::CountyReview);
    let practice = at(&EffectSignature::OrganizerPractice);
    assert_eq!(county.len(), 1, "one county receipt");
    assert_eq!(practice.len(), 1, "one practice receipt");
    assert_eq!(
        county[0],
        practice[0] + 1,
        "the county follows the practice"
    );
    assert!(at(&EffectSignature::MaterialCycle)[0] < practice[0]);
}

#[test]
fn replay_gives_the_same_bytes() {
    let run = || {
        let mut session = session(Options::default());
        let key = second_workplace(session.material());
        let mut digests = Vec::new();
        for choice in [Some(OrganizerChoice::ReviewContact(key)), None, None] {
            period(&mut session, choice);
            digests.push(session.material().digest());
        }
        (digests, session.material().canonical_bytes().to_vec())
    };
    let (first, bytes) = run();
    let (second, again) = run();
    assert_eq!(
        first, second,
        "the registers' digests agree period by period"
    );
    assert_eq!(bytes, again);
    assert_eq!(first.len(), 3);
    assert_ne!(first[0], first[1]);
}

#[test]
fn without_a_wage_tax_no_household_ranks_and_no_unit_moves() {
    // The same contact, with the tax receipt cut to nothing: the household at work has no place,
    // the units on the roll keep their holders, and the asker is not paid.
    let mut session = session(Options {
        tax_bps: 0,
        ..Options::default()
    });
    let key = second_workplace(session.material());
    let opening = support_lines(session.material());
    period(&mut session, Some(OrganizerChoice::ReviewContact(key)));
    let register = session.material();
    let record = session_record(register);
    assert_eq!(record.contact, Some((key, ContactOutcome::Reached)));
    let row = record
        .rows
        .iter()
        .find(|row| row.key == key)
        .expect("the session lists the position");
    assert_eq!((row.asked, row.asked_paid, row.asked_no_place), (1, 0, 1));
    assert_eq!(support_lines(register), opening, "no unit moved");
}

#[test]
fn the_county_section_binds_in_either_order() {
    let (catalog, organizer_first, county_first) =
        county_fixture::registers_in_both_orders(Options::default());
    assert!(organizer_first.county_review().is_some());
    assert!(organizer_first.organizer_config().is_some());
    assert_eq!(organizer_first.digest(), county_first.digest());
    assert_eq!(
        organizer_first.canonical_bytes(),
        county_first.canonical_bytes()
    );
    let decoded = MaterialWorldRegister::decode_external(
        &catalog,
        organizer_first.canonical_bytes().to_vec(),
    )
    .expect("a county register with an organizer decodes");
    assert_eq!(decoded.county_review(), organizer_first.county_review());
    assert_eq!(decoded.organizer_state(), organizer_first.organizer_state());
}
