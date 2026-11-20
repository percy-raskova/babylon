//! The county review's four views, the contact and the preview it shows.
use super::super::county::{self, CountyUnavailable};
use super::super::{client, OrganizerClient, OrganizerInspector};
use super::{tests, ActionButton, OrganizerAction};
use crate::observer::ObserverSession;
use babylon_persistence::runtime_session::{
    Band, BandCount, ContactOutcome, ContactPreview, CountyReviewProjection, LedgerLine,
    LedgerLineKind, OrganizerAllocation, OrganizerChoice, PayMode, PositionEarned, PositionKey,
    PositionView, RuntimeSessionRequest,
};
use bevy::a11y::AccessibilityNode;
use bevy::prelude::{App, Mut, Text};
use std::collections::{BTreeMap, BTreeSet};

const CLASS_WORDS: [&str; 3] = ["workers", "proletariat", "the base"];

fn key(band: Band, crew: Option<u32>, at_work: u16, units: u16) -> PositionKey {
    PositionKey {
        group: 0,
        band,
        crew,
        at_work,
        seeking: 0,
        units,
    }
}

fn earned() -> PositionEarned {
    PositionEarned {
        households: 12,
        reached: 2,
        wage_micros_per_household: 48_000_000_000,
        wage_tax_micros_per_household: 4_800_000_000,
        stake_micros: 280_000_000,
        group_ownership_income_micros: 9_000_000,
        group_support_income_micros: 3_000_000,
        group_aid_income_micros: 1_000_000,
        asked: 3,
        asked_no_place: 1,
        asked_no_time: 2,
        roll_no_time: 0,
        nothing_at_stake: 1,
        not_worth_time: 0,
        brought: 0,
    }
}

fn position(key: PositionKey, rank: Option<u32>, earned: Option<PositionEarned>) -> PositionView {
    PositionView {
        key,
        group_label: "Wayne households".into(),
        workplace_label: key.crew.map(|_| "Wayne plant".into()),
        pay_mode: key.crew.map(|_| PayMode::Wage),
        rank,
        has_wages: key.crew.is_some() && key.at_work > 0,
        has_ownership_income: key.band == Band::Top1,
        has_support: key.units > 0,
        has_mutual_aid: false,
        units_listed: u64::from(key.units),
        units_paid: 0,
        units_unpaid: u64::from(key.units),
        asked_paid: 0,
        came_from_roll: 0,
        contacted: earned.is_some(),
        earned,
    }
}

fn band(band: Band, households: u64) -> BandCount {
    BandCount {
        band,
        households,
        with_work: households / 2,
        seeking_only: households / 4,
        outside_labor_force: households - households / 2 - households / 4,
        people_at_work: households / 2,
        people_seeking: households / 4,
        units: 0,
    }
}

fn positions() -> Vec<PositionView> {
    vec![
        position(key(Band::Top1, None, 0, 0), Some(1), None),
        position(key(Band::Next40, Some(0), 1, 0), Some(2), Some(earned())),
        position(key(Band::Bottom50, Some(0), 2, 1), Some(3), None),
        position(key(Band::Next9, Some(0), 1, 0), None, None),
    ]
}

/// A county before its first session: the roster has no ranks.
pub(in crate::organizer) fn fixture() -> CountyReviewProjection {
    CountyReviewProjection {
        county: *b"26163",
        administration_label: "Wayne County administration".into(),
        claimants_body_label: "Claimants' Assembly".into(),
        aid_body_label: "Aid partners".into(),
        roster_period: 3,
        first_session_period: 4,
        session_period: None,
        unit_price_micros: 280_000_000,
        cash_micros: 5_000_000_000,
        spending_limit_micros: 4_000_000_000,
        ledger: vec![
            LedgerLine {
                kind: LedgerLineKind::CityPdPayroll,
                label: "City PD payroll".into(),
                amount_micros: 1_000_000_000,
                first_class: true,
            },
            LedgerLine {
                kind: LedgerLineKind::HouseholdSupport,
                label: "Wayne households".into(),
                amount_micros: 560_000_000,
                first_class: false,
            },
        ],
        first_class_micros: 1_000_000_000,
        relief_micros: None,
        household_units_payable: None,
        kept_back_units: None,
        roll: vec![("Wayne households".into(), 2)],
        bands: vec![
            band(Band::Top1, 4),
            band(Band::Next9, 36),
            band(Band::Next40, 160),
            band(Band::Bottom50, 200),
        ],
        claimants_roll_households: None,
        aid_roll_households: None,
        contact: None,
        positions: positions(),
    }
}

/// A county whose roster has `count` positions, for paging.
pub(in crate::organizer) fn paged(count: u16) -> CountyReviewProjection {
    CountyReviewProjection {
        positions: (0..count)
            .map(|at_work| {
                position(
                    key(Band::Bottom50, Some(0), at_work, 0),
                    Some(u32::from(at_work) + 1),
                    None,
                )
            })
            .collect(),
        ..fixture()
    }
}

/// The same county after a session held in period 3.
fn held() -> CountyReviewProjection {
    CountyReviewProjection {
        first_session_period: 2,
        session_period: Some(3),
        relief_micros: Some(560_000_000),
        household_units_payable: Some(1),
        kept_back_units: Some(0),
        claimants_roll_households: Some(4),
        aid_roll_households: Some(1),
        contact: Some((key(Band::Next40, Some(0), 1, 0), ContactOutcome::Reached)),
        ..fixture()
    }
}

/// A preview of a contact in the contacted position that asks for nothing and moves nobody.
fn contact_preview(outcome: ContactOutcome) -> ContactPreview {
    ContactPreview {
        key: key(Band::Next40, Some(0), 1, 0),
        basis_period: 3,
        outcome,
        asks: false,
        place_open: false,
        taken_from: Vec::new(),
        then_at_stake: Vec::new(),
    }
}

/// A reached household that asks and finds a place, taking the unit of `taken_from`.
fn place_open_preview(taken_from: PositionKey) -> ContactPreview {
    ContactPreview {
        asks: true,
        place_open: true,
        taken_from: vec![taken_from],
        ..contact_preview(ContactOutcome::Reached)
    }
}

fn app_with_roster() -> (App, PositionKey) {
    let (mut app, _) = tests::admitted_scene_fixture();
    app.world_mut()
        .resource_mut::<OrganizerClient>()
        .county_review = Some(fixture());
    app.update();
    (app, fixture().positions[0].key)
}

fn close(app: &mut App) {
    app.world_mut()
        .write_message(OrganizerAction::CloseInspector);
    app.update();
}

fn assert_preview_request(app: &mut App, choice: OrganizerChoice) {
    let client = app.world().resource::<OrganizerClient>();
    assert!(
        matches!(
            &client.outbox,
            Some(RuntimeSessionRequest::PreviewOrganizer { command, .. })
                if command.choice == choice
                    && command.expected_period == 3
                    && command.allocation == OrganizerAllocation::None
        ),
        "the review queued a preview of {choice:?}"
    );
}

/// Answers the queued preview with the county's own preview of the contact.
fn feed_preview(app: &mut App, review: ContactPreview) {
    app.world_mut()
        .resource_scope(|world, mut client: Mut<OrganizerClient>| {
            let mut session = world.resource_mut::<ObserverSession>();
            let Some(RuntimeSessionRequest::PreviewOrganizer {
                request_id,
                command,
                ..
            }) = client.outbox.take()
            else {
                panic!("the choice queued a review request")
            };
            let mut preview = tests::preview_for(&command);
            preview.review = Some(review);
            client
                .previewed(request_id, preview, &mut session)
                .expect("the preview answers the queued request");
        });
    app.update();
}

fn assert_submit_request(app: &mut App, choice: OrganizerChoice) {
    let client = app.world().resource::<OrganizerClient>();
    assert!(
        matches!(
            &client.outbox,
            Some(RuntimeSessionRequest::SubmitOrganizer { command, .. })
                if command.choice == choice
        ),
        "confirming queued a submission of {choice:?}"
    );
}

#[test]
fn an_uncontacted_position_shows_structure_and_hides_amounts() {
    let lines = county::roster_page(&fixture(), 0);
    let line = lines
        .iter()
        .find(|l| l.contains("no wage"))
        .expect("the fixture has a position with no wage");
    assert!(line.contains("Amounts are earned by contact"));
    assert!(!line.contains('$'));
    let contacted = lines
        .iter()
        .find(|l| l.contains("Next 40%"))
        .expect("the fixture has a contacted position");
    assert!(contacted.contains("$48,000.00 a household"));
    assert!(!contacted.contains("Amounts are earned by contact"));
    assert!(contacted.contains("Designed: MIM reads wage and salary income"));
    assert!(contacted.contains("Nation: pending."));
}

#[test]
fn the_roster_says_once_that_no_session_has_been_held_and_marks_positions_moved_since() {
    let (mut app, _) = app_with_roster();
    tests::press_named(&mut app, "Household roster");
    assert!(tests::painted_text(&mut app, true).contains("The county has not held a session yet."));
    let before = county::roster_page(&fixture(), 0).join("\n");
    assert!(!before.contains("Not on the last list"));
    let after = county::roster_page(&held(), 0);
    let moved = after
        .iter()
        .find(|line| line.starts_with("Next 9%"))
        .expect("the fixture holds an unranked position");
    assert!(
        moved.contains("Not on the last list: its households moved here since the last session.")
    );
    assert!(after[0].contains("rank 1"));
}

#[test]
fn choosing_a_slot_reviews_and_confirms_a_review_contact() {
    let (mut app, key) = app_with_roster();
    tests::press_named(&mut app, "Household roster");
    tests::press_named(&mut app, "Reach a household here (1)");
    assert_eq!(
        app.world().resource::<OrganizerClient>().inspector,
        OrganizerInspector::Closed,
        "choosing a slot closes the roster so the board shows the contact"
    );
    let world = app.world_mut();
    assert!(
        world
            .query::<&Text>()
            .iter(world)
            .any(|text| text.0.contains("Reach a household at Top 1%")),
        "the board's comparison card names the position"
    );
    tests::press_named(&mut app, "Review choice");
    assert_preview_request(&mut app, OrganizerChoice::ReviewContact(key));
    let review = ContactPreview {
        key,
        ..place_open_preview(fixture().positions[2].key)
    };
    feed_preview(&mut app, review);
    let text = tests::painted_text(&mut app, false);
    assert!(text.contains("A place is open."), "{text}");
    assert!(
        text.contains("The unit would come from: Bottom 50%"),
        "{text}"
    );
    assert!(text.contains("Cost: 8 of 16 organizer-hours"), "{text}");
    assert!(text.contains("lands in period 4"), "{text}");
    assert!(text.contains("worked from period 3"), "{text}");
    tests::press_named(&mut app, "Confirm ruling");
    assert_submit_request(&mut app, OrganizerChoice::ReviewContact(key));
}

#[test]
fn the_roster_counts_who_works_in_each_band_and_names_each_positions_band() {
    let text = county::who_works(&fixture());
    assert!(text.contains("Who works") && text.contains("Next 40%") && text.contains("Bottom 50%"));
    assert!(text.contains("Top 1%") && text.contains("Next 9%"));
    assert!(text.contains("Designed: Does not work. Lives entirely off investments."));
    assert!(text.contains(
        "Designed: Works, but is more likely to receive welfare and to need aid. Does not own a home."
    ));
    assert!(text.contains("Homes and wealth are not in this slice."));
    assert!(text.contains("160 households · 80 with someone at work · 40 only looking for work"));
    assert!(county::roster_page(&fixture(), 0).iter().all(|line| {
        ["Top 1%", "Next 9%", "Next 40%", "Bottom 50%"]
            .iter()
            .any(|band| line.starts_with(band))
    }));
}

#[test]
fn a_past_period_disables_the_slots_with_a_reason() {
    let (mut app, _) = app_with_roster();
    tests::press_named(&mut app, "Household roster");
    {
        let mut session = app.world_mut().resource_mut::<ObserverSession>();
        session.inspect_tick(2);
        let context = session.context();
        assert!(session.installed(&context));
    }
    app.update();
    let body = tests::painted_text(&mut app, true);
    assert!(
        body.starts_with(
            "These figures are period 3, the live period. Past sessions are in the Archive."
        ),
        "{body}"
    );
    assert!(body.contains(
        "Past period: reading only. Return Live before changing the organization's commitments."
    ));
    let client = app.world().resource::<OrganizerClient>();
    let session = app.world().resource::<ObserverSession>();
    assert!(!super::enabled(
        OrganizerAction::ChooseRosterSlot(0),
        client,
        session
    ));
    assert_eq!(
        county::why_unavailable(client, session.viewed_tick),
        Some(CountyUnavailable::PastPeriod)
    );
}

#[test]
fn each_reason_a_slot_is_disabled_has_its_stated_text() {
    assert_eq!(
        county::unavailable(CountyUnavailable::BeforeFirstSession {
            first_session_period: 6
        }),
        "The county holds its first session in period 6. A contact can be made from period 5."
    );
    assert_eq!(
        county::unavailable(CountyUnavailable::AlreadyChosen),
        "A ruling is already accepted for this period."
    );
    assert_eq!(
        county::unavailable(CountyUnavailable::NoReview),
        "This campaign has no county review."
    );
    let (mut app, _) = app_with_roster();
    app.world_mut()
        .resource_mut::<OrganizerClient>()
        .county_review
        .as_mut()
        .expect("the fixture county")
        .first_session_period = 6;
    tests::press_named(&mut app, "Household roster");
    let body = tests::painted_text(&mut app, true);
    assert!(
        body.contains("The county holds its first session in period 6."),
        "{body}"
    );
    let client = app.world().resource::<OrganizerClient>();
    let session = app.world().resource::<ObserverSession>();
    assert!(!super::enabled(
        OrganizerAction::ChooseRosterSlot(0),
        client,
        session
    ));
    assert!(!client.choice_available(OrganizerChoice::ReviewContact(fixture().positions[0].key)));
}

#[test]
fn a_campaign_with_no_county_review_says_so_in_all_four_views() {
    let (mut app, _) = tests::admitted_scene_fixture();
    for label in [
        "County ledger",
        "Household roster",
        "County session",
        "Food run",
    ] {
        tests::press_named(&mut app, label);
        let body = tests::painted_text(&mut app, true);
        assert!(
            body.contains("This campaign has no county review."),
            "{label}: {body}"
        );
        close(&mut app);
    }
}

#[test]
fn every_county_view_ends_with_the_standing_line() {
    let (mut app, _) = app_with_roster();
    for label in ["County ledger", "County session", "Food run"] {
        tests::press_named(&mut app, label);
        let body = tests::painted_text(&mut app, true);
        assert!(body.ends_with(county::STANDING_LINE), "{label}: {body}");
        close(&mut app);
    }
    let world = app.world_mut();
    let standing = world
        .query::<&Text>()
        .iter(world)
        .filter(|text| text.0 == county::STANDING_LINE)
        .count();
    assert_eq!(standing, 1, "the roster ends with the line below its slots");
}

#[test]
fn no_county_text_names_a_class() {
    let (app, _) = app_with_roster();
    let client = app.world().resource::<OrganizerClient>();
    let mut texts = vec![
        county::ledger(&fixture()),
        county::ledger(&held()),
        county::who_works(&fixture()),
        county::session(&held(), 3),
        county::food_run(client),
    ];
    texts.extend(county::roster_page(&fixture(), 0));
    texts.extend(county::roster_page(&held(), 0));
    texts.extend(
        [
            CountyUnavailable::NoReview,
            CountyUnavailable::PastPeriod,
            CountyUnavailable::AlreadyChosen,
            CountyUnavailable::BeforeFirstSession {
                first_session_period: 4,
            },
        ]
        .map(county::unavailable),
    );
    for outcome in [
        place_open_preview(fixture().positions[2].key),
        contact_preview(ContactOutcome::NobodyLeft),
    ] {
        texts.push(county::preview(Some(&outcome), &fixture()));
    }
    for text in texts {
        let lower = text.to_lowercase();
        for word in CLASS_WORDS {
            assert!(!lower.contains(word), "{word:?} in {text}");
        }
    }
}

#[test]
fn every_contact_preview_has_its_own_text() {
    let view = fixture();
    let reached_with_place = place_open_preview(view.positions[2].key);
    let reached_without_place = ContactPreview {
        asks: true,
        ..contact_preview(ContactOutcome::Reached)
    };
    let nobody = contact_preview(ContactOutcome::NobodyLeft);
    let missing = contact_preview(ContactOutcome::NoSuchPosition);
    let would_not_ask = contact_preview(ContactOutcome::Reached);
    let cases = [
        (Some(&reached_with_place), "A place is open. The unit would come from: Bottom 50%"),
        (
            Some(&reached_without_place),
            "No place is open: every unit below this household is held by a household that pays the same or more.",
        ),
        (Some(&nobody), "Nobody is left to reach here."),
        (Some(&missing), "This position is no longer on the roster."),
        (
            Some(&would_not_ask),
            "A reached household here would not ask: it already holds its units or a unit is worth less than its time.",
        ),
        (
            None,
            "No session has closed yet, so there is nothing to preview.",
        ),
    ];
    let mut seen = BTreeSet::new();
    for (preview, phrase) in cases {
        let text = county::preview(preview, &view);
        assert!(text.contains(phrase), "{phrase}: {text}");
        if preview.is_some() {
            assert!(text.contains("worked from period 3"), "{text}");
        }
        assert!(seen.insert(text), "each case reads differently");
    }
}

#[test]
fn the_session_shows_only_a_session_held_by_the_viewed_period() {
    let view = held();
    let text = county::session(&view, 3);
    assert!(text.contains("COUNTY SESSION · period 3"));
    assert!(text.contains("Money for relief: $560.00 · units payable: 1"));
    assert!(text.contains("Claimants' Assembly roll: 4 households came from the roll"));
    assert!(text.contains("Your contact at the session: Next 40%"));
    assert!(text.contains("2 households wanted to ask and had no hours"));
    assert!(text.contains("rank 1"));
    let earlier = county::session(&view, 2);
    assert!(earlier.starts_with("No county session has been held as of period 2."));
    assert!(!earlier.contains("rank 1"));
    let none = county::session(&fixture(), 3);
    assert!(none.starts_with("No county session has been held"));
}

#[test]
fn the_roster_pages_by_eight_and_resets_when_the_roster_period_changes() {
    let view = paged(10);
    assert_eq!(county::page_count(&view), 2);
    assert_eq!(
        county::roster_page(&view, 0).len(),
        county::ROSTER_PAGE_ROWS
    );
    assert_eq!(county::roster_page(&view, 1).len(), 2);
    assert_eq!(
        county::slot_key(&view, 1, 1),
        Some(key(Band::Bottom50, Some(0), 9, 0))
    );
    assert_eq!(county::slot_key(&view, 1, 2), None);

    let (mut app, _) = app_with_roster();
    app.world_mut()
        .resource_mut::<OrganizerClient>()
        .county_review = Some(view.clone());
    tests::press_named(&mut app, "Household roster");
    assert!(!super::enabled(
        OrganizerAction::RosterPage(-1),
        app.world().resource::<OrganizerClient>(),
        app.world().resource::<ObserverSession>(),
    ));
    tests::press_named(&mut app, "Next");
    assert_eq!(app.world().resource::<OrganizerClient>().roster_page, 1);
    assert!(tests::painted_text(&mut app, true).contains("page 2 of 2"));
    tests::press_named(&mut app, "Reach a household here (2)");
    assert_eq!(
        app.world().resource::<OrganizerClient>().choice(),
        OrganizerChoice::ReviewContact(key(Band::Bottom50, Some(0), 9, 0)),
        "the second slot of the second page is the tenth position"
    );
    let mut client = OrganizerClient {
        county_review: Some(view.clone()),
        roster_page: 1,
        ..OrganizerClient::default()
    };
    county::keep_page(&mut client, Some(&view));
    assert_eq!(client.roster_page, 1, "the same period keeps its page");
    let mut later = view;
    later.roster_period = 4;
    county::keep_page(&mut client, Some(&later));
    assert_eq!(
        client.roster_page, 0,
        "a new roster period starts at the first page"
    );
}

#[test]
fn a_slot_button_is_named_for_its_position_for_assistive_technology() {
    let (mut app, _) = app_with_roster();
    tests::press_named(&mut app, "Household roster");
    app.update();
    let world = app.world_mut();
    let labels = world
        .query::<(&ActionButton, &AccessibilityNode)>()
        .iter(world)
        .filter_map(|(button, node)| match button.0 {
            OrganizerAction::ChooseRosterSlot(slot) => {
                Some((slot, node.label().map(str::to_owned)))
            }
            _ => None,
        })
        .collect::<BTreeMap<_, _>>();
    assert_eq!(labels.len(), county::ROSTER_PAGE_ROWS);
    assert!(labels[&0]
        .as_deref()
        .is_some_and(|label| label.starts_with("Reach a household here (1): Top 1%")));
    assert!(labels[&7]
        .as_deref()
        .is_some_and(|label| label.contains("no position on this page")));
}

#[test]
fn a_new_session_record_pauses_with_a_notice_and_only_once() {
    let before = fixture();
    let after = held();
    assert_eq!(
        client::county_update(Some(&before), Some(&after)),
        Some("The county's session record arrived.")
    );
    assert_eq!(client::county_update(Some(&after), Some(&after)), None);
    assert_eq!(client::county_update(Some(&before), Some(&before)), None);
    assert_eq!(client::county_update(None, Some(&after)), None);
    assert_eq!(client::county_update(Some(&after), None), None);
}

#[test]
fn the_food_run_reads_what_the_client_holds_and_says_when_nothing_has_run() {
    let (app, _) = app_with_roster();
    let text = county::food_run(app.world().resource::<OrganizerClient>());
    assert!(
        text.contains("No local food terms are open this period."),
        "{text}"
    );
    assert!(
        text.contains("No local aid run has resolved yet."),
        "{text}"
    );
}
