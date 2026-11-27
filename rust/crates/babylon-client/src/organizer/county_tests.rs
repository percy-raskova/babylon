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
        household_units_listed: None,
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
        household_units_listed: Some(positions().iter().map(|p| p.units_listed).sum()),
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
    assert!(text.contains(county::STANDING_LINE), "{text}");
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
    close(&mut app);
    for label in ["County ledger", "County session", "Food run"] {
        tests::press_named(&mut app, label);
        let body = tests::painted_text(&mut app, true);
        assert!(
            body.starts_with(
                "These figures are period 3, the live period. Past sessions are in the Archive."
            ),
            "{label}: {body}"
        );
        close(&mut app);
    }
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
    assert!(text.contains("rank 2"));
    assert!(
        text.contains("rank 3 · Bottom 50%")
            && text.contains("Reasons are earned by contact: reach a household in a position"),
        "an uncontacted listed position states the remedy once, under the list: {text}"
    );
    // The client holds only the live projection: a period from the first session on, before the
    // live one, had its session, and that record is in the Archive.
    let archived = county::session(&view, 2);
    assert_eq!(archived, "The session of period 2 is in the Archive.");
    let before_first = county::session(&view, 1);
    assert_eq!(
        before_first,
        "No county session has been held as of period 1. The first is in period 2."
    );
    assert!(!archived.contains("rank 2") && !before_first.contains("rank 2"));
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

/// A county that has held a session in `period`: four household units on the roll, `payable` of
/// them payable, and a contact only when `contact` says so. Its first session is period 4.
fn session_held(period: u64, payable: u64, contact: bool) -> CountyReviewProjection {
    let mut listed = position(key(Band::Bottom50, Some(0), 2, 4), Some(1), None);
    listed.units_listed = 4;
    CountyReviewProjection {
        first_session_period: 4,
        session_period: Some(period),
        household_units_listed: Some(4),
        household_units_payable: Some(payable),
        contact: contact.then(|| (key(Band::Bottom50, Some(0), 2, 4), ContactOutcome::Reached)),
        positions: vec![listed],
        ..fixture()
    }
}

#[test]
fn the_first_session_record_pauses_with_the_plain_notice_and_only_once() {
    let before = fixture();
    let first = session_held(4, 4, false);
    assert_eq!(
        client::county_update(Some(&before), Some(&first)),
        Some("The county's session record arrived.".to_owned())
    );
    assert_eq!(client::county_update(Some(&first), Some(&first)), None);
    assert_eq!(client::county_update(Some(&before), Some(&before)), None);
    assert_eq!(client::county_update(None, Some(&first)), None);
    assert_eq!(client::county_update(Some(&first), None), None);
}

#[test]
fn a_session_that_carries_the_players_contact_says_it_was_heard() {
    let before = session_held(4, 4, false);
    let after = session_held(5, 4, true);
    assert_eq!(
        client::county_update(Some(&before), Some(&after)),
        Some("The county's session record arrived: your contact was heard.".to_owned())
    );
}

#[test]
fn a_session_that_changes_whether_the_county_can_pay_every_unit_says_so() {
    let every = session_held(4, 4, false);
    let some = session_held(5, 2, false);
    let none = session_held(6, 0, false);
    let again = session_held(7, 4, false);
    let notice = |before: &CountyReviewProjection, after: &CountyReviewProjection| {
        client::county_update(Some(before), Some(after))
    };
    assert_eq!(
        notice(&every, &some),
        Some(
            "The county's session record arrived: the county could not pay every unit.".to_owned()
        )
    );
    assert_eq!(
        notice(&some, &none),
        Some("The county's session record arrived: the county paid no household unit.".to_owned())
    );
    // From every unit paid straight to none: the one notice says that nothing was paid, not that
    // the county fell a little short.
    assert_eq!(
        notice(&every, &none),
        Some("The county's session record arrived: the county paid no household unit.".to_owned())
    );
    // From some units paid to some, or none to none or to some, is not news.
    assert_eq!(notice(&some, &session_held(8, 1, false)), None);
    assert_eq!(notice(&none, &session_held(8, 0, false)), None);
    assert_eq!(notice(&none, &session_held(8, 2, false)), None);
    assert_eq!(
        notice(&none, &again),
        Some(
            "The county's session record arrived: the county can pay every unit again.".to_owned()
        )
    );
    assert_eq!(
        notice(&some, &session_held(7, 4, false)),
        Some(
            "The county's session record arrived: the county can pay every unit again.".to_owned()
        )
    );
}

#[test]
fn a_listed_row_that_left_the_roster_does_not_hide_a_shortfall() {
    // The session listed rows of 4 and 2 units (6 in all) and could pay 4. Every household of the
    // second row has since been hired, so the roll-forward left only the first row: its 4 listed
    // units alone would make 4 payable look like every unit.
    let mut before = session_held(4, 6, false);
    before.household_units_listed = Some(6);
    let mut after = session_held(5, 4, false);
    after.household_units_listed = Some(6);
    assert_eq!(
        after
            .positions
            .iter()
            .map(|position| position.units_listed)
            .sum::<u64>(),
        4,
        "the projection's positions hold fewer listed units than the session listed"
    );
    assert_eq!(
        client::county_update(Some(&before), Some(&after)),
        Some(
            "The county's session record arrived: the county could not pay every unit.".to_owned()
        )
    );
    // The other way: a session that is still short is not "every unit again" because a row left.
    let mut short = session_held(4, 2, false);
    short.household_units_listed = Some(6);
    assert_eq!(client::county_update(Some(&short), Some(&after)), None);
}

#[test]
fn a_contact_and_a_change_of_standing_share_one_notice() {
    let before = session_held(4, 4, false);
    let after = session_held(5, 2, true);
    assert_eq!(
        client::county_update(Some(&before), Some(&after)),
        Some(
            "The county's session record arrived: your contact was heard, and the county could not pay every unit."
                .to_owned()
        )
    );
}

#[test]
fn a_session_with_nothing_for_the_player_installs_silently() {
    let every = session_held(4, 4, false);
    let later = session_held(5, 4, false);
    assert_eq!(client::county_update(Some(&every), Some(&later)), None);
    let some = session_held(5, 2, false);
    let still_some = session_held(6, 1, false);
    assert_eq!(client::county_update(Some(&some), Some(&still_some)), None);
    let none = session_held(5, 0, false);
    let still_none = session_held(6, 0, false);
    assert_eq!(client::county_update(Some(&none), Some(&still_none)), None);
}

fn status_after(
    previous: CountyReviewProjection,
    next: CountyReviewProjection,
) -> (OrganizerClient, bool) {
    let (mut client, mut session, request, mut snapshot) =
        crate::organizer::tests::status_fixture();
    let RuntimeSessionRequest::OrganizerStatus { request_id, .. } = request else {
        panic!("status");
    };
    snapshot.city_pd_encounters.clear();
    client.county_review = Some(previous);
    snapshot.county_review = Some(next);
    session.playing = true;
    client
        .status(request_id, snapshot, &mut session)
        .expect("the status is admitted");
    (client, session.playing)
}

#[test]
fn a_status_with_a_first_session_record_installs_the_notice_and_pauses_play() {
    let (client, playing) = status_after(fixture(), session_held(4, 4, false));
    assert_eq!(client.message, "The county's session record arrived.");
    assert!(!playing, "the first session record pauses play");
    assert_eq!(
        client
            .county_review
            .as_ref()
            .and_then(|view| view.session_period),
        Some(4)
    );
}

#[test]
fn a_status_with_a_session_the_player_has_no_reason_to_read_leaves_play_running() {
    let (client, playing) = status_after(session_held(4, 4, false), session_held(5, 4, false));
    assert!(client.message.is_empty(), "{}", client.message);
    assert!(playing, "a quiet session does not pause play");
    assert_eq!(
        client
            .county_review
            .as_ref()
            .and_then(|view| view.session_period),
        Some(5),
        "the record is installed all the same"
    );
}

/// A session held in period 3 in which a contact moved one unit: the contacted position gained a
/// household that asked and was paid, the position below it lost a unit, and two others held
/// nothing and saw nothing.
fn moved() -> CountyReviewProjection {
    let mut gained = position(key(Band::Next40, Some(0), 1, 0), Some(2), None);
    gained.asked_paid = 1;
    gained.contacted = true;
    let mut lost = position(key(Band::Bottom50, Some(0), 2, 1), Some(3), None);
    lost.units_unpaid = 1;
    CountyReviewProjection {
        positions: vec![
            position(key(Band::Top1, None, 0, 0), Some(1), None),
            gained,
            lost,
            position(key(Band::Next9, Some(0), 3, 0), Some(4), None),
            position(key(Band::Next9, Some(0), 4, 0), Some(5), None),
        ],
        ..held()
    }
}

#[test]
fn the_session_names_what_it_changed_before_the_list() {
    let text = county::session(&moved(), 3);
    let changed = text
        .find("What this session changed")
        .expect("the record has a block of changes");
    let list = text
        .find("The list, in rank order")
        .expect("the record has the list");
    assert!(changed < list, "the block comes first: {text}");
    let block = &text[changed..list];
    assert!(
        block.contains("rank 2 · Next 40%") && block.contains("1 household asked and was paid"),
        "the gaining position is named: {block}"
    );
    assert!(
        block.contains("rank 3 · Bottom 50%") && block.contains("1 unit left unpaid"),
        "the losing position is named: {block}"
    );
    assert!(
        !block.contains("rank 1 ·"),
        "a quiet position is not: {block}"
    );
    assert!(!block.contains("Every listed unit was paid"), "{block}");
}

#[test]
fn a_session_in_which_nothing_happened_says_so() {
    let mut quiet = moved();
    for position in &mut quiet.positions {
        position.units_unpaid = 0;
        position.asked_paid = 0;
    }
    let text = county::session(&quiet, 3);
    assert!(
        text.contains("Every listed unit was paid and nobody new asked."),
        "{text}"
    );
}

#[test]
fn a_position_with_nothing_listed_and_nothing_happening_is_counted_not_listed() {
    let text = county::session(&moved(), 3);
    let list = &text[text
        .find("The list, in rank order")
        .expect("the record has the list")..];
    assert!(list.contains("rank 2 · Next 40%"), "{list}");
    assert!(list.contains("rank 3 · Bottom 50%"), "{list}");
    assert!(!list.contains("rank 1 ·"), "{list}");
    assert!(
        !list.contains("rank 4 ·") && !list.contains("rank 5 ·"),
        "{list}"
    );
    assert!(
        list.contains("3 other positions hold no unit; nobody there asked."),
        "{list}"
    );
    let mut one_left = moved();
    one_left.positions.truncate(4);
    assert!(county::session(&one_left, 3)
        .contains("2 other positions hold no unit; nobody there asked."),);
    one_left.positions.truncate(3);
    assert!(
        county::session(&one_left, 3)
            .contains("1 other position holds no unit; nobody there asked."),
        "one reads in the singular"
    );
}

#[test]
fn the_session_states_the_remedy_once_under_the_list() {
    let text = county::session(&moved(), 3);
    let remedy = "Reasons are earned by contact: reach a household in a position to see why its households asked or stayed home.";
    assert_eq!(text.matches(remedy).count(), 1, "{text}");
    assert!(
        text.find(remedy) > text.find("The list, in rank order"),
        "it stands under the list's heading: {text}"
    );
    assert!(
        !text.contains("Reach a household here."),
        "no per-row remedy: {text}"
    );
}

#[test]
fn a_session_reads_a_count_of_one_in_the_singular_and_hides_reasons_without_earning() {
    let mut view = moved();
    view.claimants_roll_households = Some(1);
    view.aid_roll_households = Some(1);
    let text = county::session(&view, 3);
    assert!(
        text.contains("Claimants' Assembly roll: 1 household came from the roll"),
        "{text}"
    );
    assert!(
        text.contains("Aid partners roll: 1 household asked and was paid"),
        "{text}"
    );
    assert!(text.contains("1 unit listed"), "{text}");
    assert!(
        !text.contains("1 households") && !text.contains("1 units"),
        "{text}"
    );
    assert!(
        !text.contains("wanted to ask and had no hours"),
        "no earned reasons without contact: {text}"
    );
    let one = county::who_works(&CountyReviewProjection {
        bands: vec![BandCount {
            households: 1,
            units: 1,
            people_at_work: 1,
            people_seeking: 1,
            ..band(Band::Top1, 1)
        }],
        ..fixture()
    });
    assert!(
        one.contains("1 household ·")
            && one.contains("1 person at work")
            && one.contains("1 person looking for work")
            && one.contains("1 unit"),
        "{one}"
    );
    assert!(
        !one.contains("1 households") && !one.contains("1 units"),
        "{one}"
    );
}

#[test]
fn an_earned_position_shows_its_reasons_in_the_block_and_an_unearned_one_does_not() {
    let text = county::session(&held(), 3);
    let list = text.find("The list, in rank order").expect("the list");
    let block = &text[text.find("What this session changed").expect("the block")..list];
    assert!(
        block.contains("rank 2 · Next 40%")
            && block.contains("2 households wanted to ask and had no hours"),
        "an earned position's reasons are in the block: {block}"
    );
    let unearned = block
        .lines()
        .find(|line| line.contains("rank 3 · Bottom 50%"))
        .expect("the unpaid unit is named");
    assert!(
        unearned.ends_with(": 1 unit left unpaid."),
        "an unearned position shows no reasons: {unearned}"
    );
}

/// A county with one reached position, rank 1, whose households asked as the arguments say:
/// `asked` in all, `paid` of them paid, `no_place` finding no place open, and `brought` brought.
fn asked_at(asked: u64, paid: u64, no_place: u64, brought: u64) -> CountyReviewProjection {
    let mut reached = position(
        key(Band::Bottom50, Some(0), 2, 0),
        Some(1),
        Some(PositionEarned {
            asked,
            asked_no_place: no_place,
            asked_no_time: 0,
            nothing_at_stake: 0,
            brought,
            ..earned()
        }),
    );
    reached.asked_paid = paid;
    CountyReviewProjection {
        positions: vec![reached],
        ..held()
    }
}

/// The text of the block of changes, from its heading to the list.
fn changes_block(view: &CountyReviewProjection) -> String {
    let text = county::session(view, 3);
    let from = text.find("What this session changed").expect("the block");
    let to = text.find("The list, in rank order").expect("the list");
    text[from..to].to_owned()
}

#[test]
fn a_household_that_asked_is_told_once_by_what_became_of_it() {
    // Every household that asked found no place open: one clause, with no bare count before it.
    let block = changes_block(&asked_at(2, 0, 2, 0));
    assert!(
        block.contains(": 2 households asked and found no place open."),
        "{block}"
    );
    assert_eq!(block.matches("asked").count(), 1, "{block}");
    // One asked and was paid, and one was brought.
    let block = changes_block(&asked_at(1, 1, 0, 1));
    assert!(
        block.contains(
            ": 1 household asked and was paid, 1 household was brought, to be reached from the \
             next session."
        ),
        "{block}"
    );
    assert_eq!(block.matches("asked").count(), 1, "{block}");
    // The list's reason line reads the same as the block.
    let text = county::session(&asked_at(2, 0, 2, 0), 3);
    let list = &text[text.find("The list, in rank order").expect("the list")..];
    assert!(
        list.contains("\n     2 households asked and found no place open"),
        "{list}"
    );
    assert!(!text.contains("no place was open"), "{text}");
    // One household that found no place open reads in the singular.
    assert!(changes_block(&asked_at(1, 0, 1, 0))
        .contains(": 1 household asked and found no place open."),);
}

#[test]
fn the_bare_count_of_households_that_asked_stays_when_the_clauses_do_not_add_up() {
    // Five asked: one was paid and two found no place open. The other two are not told, so the
    // count of all five stays, after the paid household and before the reasons.
    let block = changes_block(&asked_at(5, 1, 2, 0));
    assert!(
        block.contains(
            ": 1 household asked and was paid, 5 households asked in all, 2 households asked and \
             found no place open."
        ),
        "{block}"
    );
    // Three asked and nothing is told of them: the bare count is all there is.
    let block = changes_block(&asked_at(3, 0, 0, 0));
    assert!(block.contains(": 3 households asked in all."), "{block}");
    // One asked and nothing is told of it: the count reads in the singular, with no "in all".
    let block = changes_block(&asked_at(1, 0, 0, 0));
    assert!(block.contains(": 1 household asked."), "{block}");
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
