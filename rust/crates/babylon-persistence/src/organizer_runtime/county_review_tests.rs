//! The county review's snapshot, preview and archive text, on the captured national campaign.

use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_practice_contract::{
    Band, ContactOutcome, CountyReviewConfig, CountyReviewCrew, CountyReviewGroup, GroupKind,
    OrganizerAllocation, OrganizerChoice, OrganizerCommand, OrganizerOutcome,
    OrganizerPartnerResponse, OrganizerPeriodJournal, OrganizerPeriodJournalEntries,
    OrganizerReceipt, PayMode, PositionKey, SessionRecord, SessionRow,
};
use babylon_tick::material_replay::MaterialReplaySession;
use babylon_tick::replay_session::ReplayCommitDisposition;
use uuid::Uuid;

use super::county_review;
use crate::economic_catalog::{self, CapturedEconomicCatalog, NationalOpponent};
use crate::identity::CampaignId;

type Session = MaterialReplaySession<HypergraphStore>;

fn campaign() -> CampaignId {
    CampaignId::from_uuid(Uuid::from_u128(0x0026_1631_7037))
}

pub(crate) fn session(name: &str, opponent: NationalOpponent) -> Session {
    CapturedEconomicCatalog::capture_national_campaign_with_opponent(
        economic_catalog::national_catalog_input(),
        campaign(),
        opponent,
    )
    .expect("the national campaign captures")
    .create_foundation(
        ReplaySessionId::try_from(name).expect("session identity"),
        ReplaySeed::new(319),
    )
    .expect("ordinary national foundation")
    .into_session()
    .expect("national session")
}

fn command(session: &Session, choice: OrganizerChoice) -> OrganizerCommand {
    let config = session.material().organizer_config().expect("organizer");
    OrganizerCommand {
        allocation: OrganizerAllocation::None,
        campaign_id: config.campaign_id,
        actor_id: config.controlled_actor_id,
        authority_id: config.input_authority_id,
        expected_period: session.completed_tick(),
        content_digest: config.content_digest,
        resource_digest: babylon_practice_contract::organizer_resource_digest()
            .expect("the resource digest"),
        nonce: [5; 16],
        choice,
    }
}

fn close_one_period(session: &mut Session) {
    let actions = babylon_practice_contract::organizer_action_batch(
        session.material().organizer_config().expect("organizer"),
        session.material().organizer_state().expect("state"),
        None,
        session.graph_session().session_identity().clone(),
    )
    .expect("the organizer's actions");
    let candidate = session
        .prepare_advance(&actions)
        .expect("the period closes");
    session
        .commit_prepared_and_publish(&mut CollectingSink::default(), candidate, |_, _| {
            Ok::<_, ()>(ReplayCommitDisposition::Committed)
        })
        .expect("the period commits");
}

#[test]
fn review_preview_answers_only_a_review_contact() {
    let mut with_county = session("county-preview", NationalOpponent::CityPd);
    close_one_period(&mut with_county);
    let register = with_county.material();
    let key = register
        .county_review()
        .expect("the county section")
        .state()
        .roster
        .rows[0]
        .key;
    let contact = command(&with_county, OrganizerChoice::ReviewContact(key));
    let preview = county_review::review_preview(register, &contact)
        .expect("a contact on a register with a county section previews")
        .expect("and a close has been seen");
    assert_eq!(preview.key, key);
    assert_eq!(preview.basis_period, 1);
    assert_eq!(preview.outcome, ContactOutcome::Reached);
    for choice in [OrganizerChoice::Hold, OrganizerChoice::Reinforce] {
        assert_eq!(
            county_review::review_preview(register, &command(&with_county, choice)),
            Ok(None),
            "{choice:?} has no county preview"
        );
    }
    // A position the roster does not hold is answered, not hidden.
    let nowhere = PositionKey {
        units: u16::MAX,
        ..key
    };
    let missing = county_review::review_preview(
        register,
        &command(&with_county, OrganizerChoice::ReviewContact(nowhere)),
    )
    .expect("a missing position still previews")
    .expect("with a close seen");
    assert_eq!(missing.outcome, ContactOutcome::NoSuchPosition);

    let control = session("county-preview-control", NationalOpponent::None);
    assert!(control.material().county_review().is_none());
    assert_eq!(
        county_review::review_preview(
            control.material(),
            &command(&control, OrganizerChoice::ReviewContact(key))
        ),
        Ok(None),
        "a register with no county section has nothing to preview"
    );
}

#[test]
fn review_preview_before_any_close_has_nothing_to_say() {
    let opening = session("county-preview-opening", NationalOpponent::CityPd);
    let key = opening
        .material()
        .county_review()
        .expect("the county section")
        .state()
        .roster
        .rows[0]
        .key;
    assert_eq!(
        county_review::review_preview(
            opening.material(),
            &command(&opening, OrganizerChoice::ReviewContact(key))
        ),
        Ok(None)
    );
}

fn receipt(
    period: u64,
    choice: OrganizerChoice,
    outcome: OrganizerOutcome,
    id: u8,
) -> OrganizerReceipt {
    OrganizerReceipt {
        receipt_id: [id; 32],
        commitment_id: None,
        actor_id: 1,
        period,
        choice,
        standing_work: false,
        outcome,
        hours_spent: 0,
        partner_actor_id: None,
        partner_response: OrganizerPartnerResponse::NotRequested,
        observation_ids: vec![],
        contact_product_id: None,
        time_use: vec![],
    }
}

#[test]
fn contacted_positions_come_from_made_contacts_of_every_period_once_each() {
    let first = PositionKey {
        group: 1,
        band: Band::Bottom50,
        crew: None,
        at_work: 0,
        seeking: 0,
        units: 1,
    };
    let second = PositionKey { group: 0, ..first };
    let mut journal = OrganizerPeriodJournal::empty();
    for (period, entries) in [
        (
            4,
            vec![receipt(
                4,
                OrganizerChoice::ReviewContact(first),
                OrganizerOutcome::ReviewContactMade,
                1,
            )],
        ),
        (
            5,
            vec![
                receipt(
                    5,
                    OrganizerChoice::ReviewContact(second),
                    OrganizerOutcome::ReviewContactMade,
                    2,
                ),
                receipt(
                    5,
                    OrganizerChoice::Hold,
                    OrganizerOutcome::NoAuthorizedPractice,
                    3,
                ),
            ],
        ),
        (
            6,
            vec![receipt(
                6,
                OrganizerChoice::ReviewContact(first),
                OrganizerOutcome::ReviewContactMade,
                4,
            )],
        ),
    ] {
        let mut period_entries = OrganizerPeriodJournalEntries::new(period);
        period_entries.receipts = entries;
        journal.periods.push(period_entries);
    }
    assert_eq!(county_review::contacted(&journal), vec![second, first]);
}

fn row(rank: u32, at: u16, listed: u64, paid: u64) -> SessionRow {
    SessionRow {
        key: PositionKey {
            group: 0,
            band: Band::Bottom50,
            crew: None,
            at_work: at,
            seeking: 0,
            units: 1,
        },
        rank,
        households: 1,
        reached: 0,
        units_listed: listed,
        units_paid: paid,
        units_unpaid: listed - paid,
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
    }
}

fn record(rows: Vec<SessionRow>) -> SessionRecord {
    SessionRecord {
        period: 4,
        cash_micros: 5_000_000_000_000,
        spending_limit_micros: 4_000_000_000_000,
        first_class_micros: 1_500_000_000_000,
        roll_total_micros: 20_094_200_000_000,
        relief_micros: 2_500_000_000_000,
        collective_lines: vec![],
        household_units_listed: 71_765,
        household_units_payable: 8_928,
        kept_back_units: 3,
        contact: None,
        rows,
        lines: vec![],
        claimants_roll_households: 0,
        aid_roll_households: 0,
    }
}

/// A county of two groups and one crew, with names a reader can tell apart.
pub(crate) fn sample_config() -> CountyReviewConfig {
    CountyReviewConfig {
        schema_version: babylon_practice_contract::COUNTY_REVIEW_SCHEMA_VERSION,
        campaign_id: [1; 16],
        actor_id: 9,
        authority_id: [2; 16],
        county: *b"26163",
        administration_label: "Administration".to_owned(),
        claimants_body_label: "Claimants".to_owned(),
        aid_body_label: "Aid".to_owned(),
        public_account_id: [3; 32],
        unit_price_micros: 280_000_000,
        going_wage_micros: 24_000_000,
        session_hours: 2,
        bring_hours: 2,
        first_session_period: 1,
        groups: vec![
            CountyReviewGroup {
                group_id: [1; 32],
                label: "Wayne households".to_owned(),
                kind: GroupKind::Ordinary,
                opening_households: 10,
                roll_units: 10,
                has_ownership_income: false,
                receives_mutual_aid: false,
            },
            CountyReviewGroup {
                group_id: [2; 32],
                label: "Hospital families".to_owned(),
                kind: GroupKind::Ordinary,
                opening_households: 5,
                roll_units: 5,
                has_ownership_income: false,
                receives_mutual_aid: false,
            },
        ],
        crews: vec![CountyReviewCrew {
            crew_id: [1; 32],
            group: 0,
            site_id: [4; 32],
            unit_id: [5; 32],
            workplace_label: "Wayne General".to_owned(),
            pay_mode: PayMode::Wage,
        }],
        content_digest: [6; 32],
        policy_source_digest: [7; 32],
    }
}

fn at_crew(mut row: SessionRow, crew: u32) -> SessionRow {
    row.key.crew = Some(crew);
    row
}

#[test]
fn the_session_text_names_each_position_that_holds_a_unit() {
    let config = sample_config();
    let held = county_review::session_signal_text(
        &config,
        &record(vec![
            at_crew(row(2, 1, 4, 4), 0),
            row(1, 0, 3, 1),
            row(3, 2, 0, 0),
        ]),
    )
    .expect("the text");
    assert_eq!(
        held,
        "The county had $2,500,000.00 for relief after $1,500,000.00 of lines paid first, \
         against a roll of $20,094,200.00. It could pay 8928 of 71765 household units and kept \
         back 3 to an exact tie. Positions paid in full: 1. Paid in part: 1. Not paid: 0. \
         Positions that hold units, highest on the list first: \
         Bottom 50% \u{b7} Wayne households \u{b7} no wage \u{b7} no one in the labor force, rank 1: \
         3 listed, 1 paid, 2 unpaid; \
         Bottom 50% \u{b7} Wayne households \u{b7} Wayne General (wage), rank 2: 4 listed, 4 paid, \
         0 unpaid. Positions holding no unit, left out: 1."
    );

    // A session that kept nothing back says nothing of a tie.
    let mut none_kept = record(vec![row(1, 0, 3, 3)]);
    none_kept.kept_back_units = 0;
    let text = county_review::session_signal_text(&config, &none_kept).expect("the text");
    assert!(!text.contains("kept back"), "{text}");
    assert!(
        text.contains("household units. Positions paid in full: 1."),
        "{text}"
    );
    assert!(
        text.ends_with("0 unpaid. Positions holding no unit, left out: 0."),
        "{text}"
    );
}

#[test]
fn a_position_the_county_does_not_hold_has_no_text() {
    let mut stranger = row(1, 0, 3, 3);
    stranger.key.group = 9;
    assert_eq!(
        county_review::session_signal_text(&sample_config(), &record(vec![stranger])),
        Err(crate::archive::SemanticArchiveError::InvalidIdentity)
    );
}

#[test]
fn the_session_text_fits_the_archive_at_any_size_and_says_what_it_left_out() {
    // A roster far larger than Wayne's positions is cut at the limit and says how many it left.
    let many: Vec<_> = (0..5_000_u32)
        .map(|n| {
            row(
                n + 1,
                u16::try_from(n % 60_000).expect("a small number"),
                12,
                5,
            )
        })
        .collect();
    let long = county_review::session_signal_text(&sample_config(), &record(many)).expect("text");
    assert!(long.len() <= 4_096, "{} bytes", long.len());
    assert!(
        long.contains("Positions with units that did not fit: "),
        "{long}"
    );
    assert!(
        long.ends_with("Positions holding no unit, left out: 0."),
        "{long}"
    );
    assert!(long.contains("rank 1: 12 listed"), "{long}");
}

#[test]
fn the_largest_session_text_fits_the_archive() {
    let mut session = session("county-archive-text", NationalOpponent::CityPd);
    for _ in 0..4 {
        close_one_period(&mut session);
    }
    let county = session
        .material()
        .county_review()
        .expect("the county section");
    let held = county
        .state()
        .last_session
        .as_ref()
        .expect("the first session was held at period 4");
    let text = county_review::session_signal_text(county.config(), held).expect("the text");
    assert!(text.len() <= 4_096, "{} bytes", text.len());
    assert!(
        text.starts_with("The county had $"),
        "the signal opens with the money for relief: {text}"
    );
    assert!(
        !text.contains(" 0 listed"),
        "no position without a unit is listed: {text}"
    );
    assert!(!text.contains("kept back 0"), "{text}");
    let group = &county.config().groups[0].label;
    assert!(
        text.contains(&format!(" \u{b7} {group} \u{b7} ")),
        "a position is named by its public structure: {text}"
    );
}

#[test]
fn a_snapshot_whose_county_projection_was_altered_no_longer_matches_the_register() {
    let session = session("county-snapshot-match", NationalOpponent::CityPd);
    let (catalog, register) = (session.catalog(), session.material());
    let snapshot = super::captured_organizer_snapshot(catalog, register, None, session.duration())
        .expect("the opening snapshot");
    assert!(snapshot.county_review.is_some());
    assert_eq!(
        super::aid_snapshot_matches(catalog, register, &snapshot),
        Ok(true)
    );
    let mut richer = snapshot.clone();
    richer
        .county_review
        .as_mut()
        .expect("the projection")
        .cash_micros += 1;
    assert_eq!(
        super::aid_snapshot_matches(catalog, register, &richer),
        Ok(false)
    );
    let mut hidden = snapshot;
    hidden.county_review = None;
    assert_eq!(
        super::aid_snapshot_matches(catalog, register, &hidden),
        Ok(false)
    );
}
