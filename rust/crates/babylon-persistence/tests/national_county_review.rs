//! The Wayne county review: what the captured national campaign opens with and what the organizer's
//! snapshot shows of it.
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_persistence::economic_catalog::{CapturedEconomicCatalog, NationalOpponent};
use babylon_persistence::identity::CampaignId;
use babylon_persistence::qualification_audit::aid;
use babylon_persistence::runtime_session::{
    Band, GroupKind, LedgerLineKind, OrganizerAllocation, OrganizerChoice, OrganizerCommand,
    OrganizerCommitment, OrganizerPreview, OrganizerSnapshot, RuntimeSessionResponse,
    RuntimeSessionScope, RUNTIME_SESSION_MAX_LINE_BYTES,
};
use babylon_practice_contract as practice_contract;
use babylon_tick::material_replay::MaterialReplaySession;
use babylon_tick::material_world::CountyReviewRegister;
use babylon_tick::replay_session::ReplayCommitDisposition;
use serde_json::Value;
use std::path::Path;
use uuid::Uuid;

type Session = MaterialReplaySession<HypergraphStore>;

#[path = "fixtures/national_capture.rs"]
mod national_capture;

fn campaign() -> CampaignId {
    CampaignId::from_uuid(Uuid::from_u128(0x0026_1631_7036))
}

fn national_opening() -> CapturedEconomicCatalog {
    CapturedEconomicCatalog::capture_national_campaign(national_capture::input(), campaign())
        .expect("the national campaign captures the county review")
}

fn county_review_of(catalog: CapturedEconomicCatalog) -> CountyReviewRegister {
    let foundation = catalog
        .create_foundation(
            ReplaySessionId::try_from("national-county-review").expect("session identity"),
            ReplaySeed::new(319),
        )
        .expect("the county review opens inside the material register");
    foundation
        .initial_register()
        .county_review()
        .expect("the opening register carries the county section")
        .clone()
}

fn snapshot(catalog: CapturedEconomicCatalog) -> OrganizerSnapshot {
    let session = catalog
        .create_foundation(
            ReplaySessionId::try_from("national-county-snapshot").expect("session identity"),
            ReplaySeed::new(319),
        )
        .expect("ordinary national foundation")
        .into_session()
        .expect("national session");
    aid::material_disclosure(session.catalog(), session.material(), session.duration())
        .expect("the opening disclosure")
}

#[test]
fn wayne_is_captured_with_a_roster_that_adds_back() {
    let opening = county_review_of(national_opening());
    let (config, state) = (opening.config(), opening.state());
    assert_eq!(
        (
            config.county,
            config.unit_price_micros,
            config.first_session_period
        ),
        (*b"26163", 280_000_000, 4)
    );
    assert_eq!(config.going_wage_micros, 24_000_000);
    assert!(config
        .crews
        .iter()
        .all(|crew| config.groups[crew.group as usize].kind == GroupKind::Ordinary));
    practice_contract::validate_county_review_config(config)
        .expect("the configuration is canonical");
    practice_contract::validate_roster(config, &state.roster)
        .expect("the roster adds back to the groups");
    for (index, group) in config.groups.iter().enumerate() {
        if group.kind == GroupKind::Ordinary {
            assert_eq!(
                state.roster.groups[index].households,
                group.opening_households
            );
            assert_eq!(
                state
                    .roster
                    .group_units(u32::try_from(index).expect("few groups")),
                group.roll_units
            );
        }
    }
    let reached: u64 = state.roster.rows.iter().map(|row| row.reached).sum();
    assert_eq!(
        reached, 5,
        "2 claimant households and 3 of the aid partners' 4"
    );
}

#[test]
fn wayne_opens_with_the_directors_bands() {
    let opening = county_review_of(national_opening());
    let (config, roster) = (opening.config(), &opening.state().roster);
    let ordinary = |owner: bool| -> u64 {
        config
            .groups
            .iter()
            .filter(|g| g.kind == GroupKind::Ordinary && g.has_ownership_income == owner)
            .map(|g| g.opening_households)
            .sum()
    };
    let (owners, others) = (ordinary(true), ordinary(false));
    let b = roster.band_counts();
    assert_eq!(b[0].households + b[1].households, owners);
    assert_eq!(b[2].households + b[3].households, others);
    assert!(b[0].households <= owners / 10 + 1 && b[0].households + 8 >= owners / 10);
    assert!(b[2].households <= others * 4 / 9 + 1 && b[2].households + 64 >= others * 4 / 9);
    assert_eq!(
        b[0].with_work + b[0].seeking_only,
        0,
        "the top 1% do not work"
    );
    assert_eq!(
        b[2].outside_labor_force, 0,
        "the next 40% are all in the labor force"
    );
    assert!(b[2].people_seeking > 0, "and they have unemployment too");
    assert!(
        b[3].units > b[2].units && b[3].units > b[1].units,
        "most relief sits with the bottom 50%"
    );
    assert!(
        b[3].people_seeking * (b[2].people_at_work + b[2].people_seeking)
            > b[2].people_seeking * (b[3].people_at_work + b[3].people_seeking),
        "a larger share of the bottom 50%'s labor force looks for work than of the next 40%'s"
    );
    assert!(roster
        .rows
        .iter()
        .filter(|row| row.reached > 0)
        .all(|row| row.key.band == Band::Bottom50));
}

#[test]
fn the_organizer_holds_the_review_the_county_configuration_is_bound_to() {
    let catalog = national_opening();
    let config = catalog.county_review_config().expect("the county review");
    let review = catalog
        .organizer_config()
        .expect("the organizer")
        .review
        .as_ref()
        .expect("the playable campaign reaches the review");
    assert_eq!(review.county_geoid, "26163");
    assert_eq!(review.first_session_period, 4);
    assert_eq!(
        review.county_config_digest,
        practice_contract::county_review_config_digest(config).expect("the digest")
    );
}

#[test]
fn a_county_footer_that_differs_from_the_opening_is_refused_on_decode() {
    let catalog = national_opening();
    let mut bytes = catalog.canonical_bytes().to_vec();
    let label = b"Wayne County administration";
    let at = bytes
        .windows(label.len())
        .rposition(|window| window == label)
        .expect("the county footer holds the administration's name");
    bytes[at + label.len() - 1] = b'N';
    let digest = babylon_kernel::content_digest::sha256_of(&bytes);
    assert_eq!(
        CapturedEconomicCatalog::decode(&bytes, digest).err(),
        Some(babylon_persistence::economic_catalog::EconomicCatalogError::Identity),
        "a configuration the opening does not derive is not the campaign's"
    );
    // The untouched bytes decode to the same catalog.
    let same = CapturedEconomicCatalog::decode(catalog.canonical_bytes(), catalog.digest())
        .expect("the canonical bytes decode");
    assert_eq!(same.county_review_config(), catalog.county_review_config());
}

#[test]
fn the_snapshot_at_the_opening_shows_the_ledger_and_hides_every_amount() {
    let view = snapshot(national_opening())
        .county_review
        .expect("a campaign with a county review projects it");
    assert!(view.positions.iter().all(|p| p.earned.is_none()));
    assert!(view
        .ledger
        .iter()
        .any(|l| l.kind == LedgerLineKind::CityPdPayroll && l.amount_micros == 13_551_360_000_000));
    assert_eq!(view.session_period, None);
}

#[test]
fn the_wayne_status_line_fits_the_protocol() {
    let snapshot = snapshot(national_opening());
    let line = serde_json::to_vec(&RuntimeSessionResponse::OrganizerStatus {
        request_id: 1,
        scope: RuntimeSessionScope {
            epoch: 1,
            campaign_id: Some(campaign().as_uuid().to_string()),
        },
        snapshot: Box::new(snapshot),
    })
    .expect("the status line serializes");
    assert!(
        line.len() < RUNTIME_SESSION_MAX_LINE_BYTES / 2,
        "the opening status line is {} bytes",
        line.len()
    );
}

#[test]
fn a_snapshot_of_a_register_with_no_county_section_has_no_county_field() {
    let control = CapturedEconomicCatalog::capture_national_campaign_with_opponent(
        national_capture::input(),
        campaign(),
        NationalOpponent::None,
    )
    .expect("the control keeps the organizer's public route and has no county");
    assert!(control.county_review_config().is_none());
    let view = snapshot(control);
    assert!(view.county_review.is_none());
    let json = serde_json::to_value(&view).expect("the snapshot serializes");
    assert!(
        json.get("county_review").is_none(),
        "a snapshot with no county section keeps the bytes it had"
    );
    let back: OrganizerSnapshot = serde_json::from_value(json).expect("the snapshot reads back");
    assert_eq!(back, view);
}

#[test]
fn every_committed_snapshot_and_preview_fixture_still_deserializes_with_its_bytes() {
    let roundtrip = |value: Value| {
        let snapshot: OrganizerSnapshot =
            serde_json::from_value(value.clone()).expect("the fixture is a snapshot");
        assert!(snapshot.county_review.is_none());
        assert_eq!(
            serde_json::to_value(&snapshot).expect("the snapshot serializes"),
            value,
            "a snapshot with no county section keeps its bytes"
        );
    };
    for fixture in [
        include_str!("fixtures/national_organizer_opening_v20.json"),
        include_str!("fixtures/national_organizer_pending_v20.json"),
    ] {
        roundtrip(serde_json::from_str(fixture).expect("the fixture is JSON"));
    }
    for fixture in [
        include_str!("fixtures/cash_only_no_food_v20.json"),
        include_str!("fixtures/food_only_no_payer_v20.json"),
    ] {
        let value: Value = serde_json::from_str(fixture).expect("the fixture is JSON");
        roundtrip(value["snapshot"].clone());
        let preview: OrganizerPreview =
            serde_json::from_value(value["preview"].clone()).expect("the fixture holds a preview");
        assert!(preview.review.is_none());
        assert_eq!(
            serde_json::to_value(&preview).expect("the preview serializes"),
            value["preview"],
            "a preview with no county contact keeps its bytes"
        );
    }
}

fn advance(session: &mut Session, commitment: Option<&OrganizerCommitment>) {
    let actions = babylon_practice_contract::organizer_action_batch(
        session.material().organizer_config().expect("organizer"),
        session.material().organizer_state().expect("state"),
        commitment,
        session.graph_session().session_identity().clone(),
    )
    .expect("the organizer's actions");
    let candidate = session
        .prepare_advance_with_organizer(&actions, commitment)
        .expect("the period closes");
    session
        .commit_prepared_and_publish(&mut CollectingSink::default(), candidate, |_, _| {
            Ok::<_, ()>(ReplayCommitDisposition::Committed)
        })
        .expect("the period commits");
}

#[test]
fn the_first_session_is_held_and_the_snapshot_shows_only_the_position_the_organizer_reached() {
    let mut session = national_opening()
        .create_foundation(
            ReplaySessionId::try_from("national-county-session").expect("session identity"),
            ReplaySeed::new(319),
        )
        .expect("ordinary national foundation")
        .into_session()
        .expect("national session");
    for _ in 0..3 {
        advance(&mut session, None);
    }
    let before =
        aid::material_disclosure(session.catalog(), session.material(), session.duration())
            .expect("the disclosure before the first session");
    let view = before.county_review.expect("the county's projection");
    assert_eq!((view.roster_period, view.session_period), (3, None));
    let target = view
        .positions
        .iter()
        .find(|p| p.key.band == Band::Bottom50 && p.key.units > 0)
        .expect("a bottom 50% household that holds a unit")
        .key;
    let config = session.material().organizer_config().expect("organizer");
    let command = OrganizerCommand {
        allocation: OrganizerAllocation::None,
        campaign_id: config.campaign_id,
        actor_id: config.controlled_actor_id,
        authority_id: config.input_authority_id,
        expected_period: 3,
        content_digest: config.content_digest,
        resource_digest: babylon_practice_contract::organizer_resource_digest()
            .expect("the resource digest"),
        nonce: [4; 16],
        choice: OrganizerChoice::ReviewContact(target),
    };
    let commitment = babylon_practice_contract::admit_organizer(
        config,
        session.material().organizer_state().expect("state"),
        &command,
    )
    .expect("the contact is admitted");
    advance(&mut session, Some(&commitment));
    let after = aid::material_disclosure(session.catalog(), session.material(), session.duration())
        .expect("the disclosure after the first session");
    let view = after.county_review.expect("the county's projection");
    assert_eq!((view.roster_period, view.session_period), (4, Some(4)));
    let (key, _) = view.contact.expect("the session records the contact");
    assert_eq!(key, target);
    for position in &view.positions {
        assert_eq!(
            position.earned.is_some(),
            position.key == target,
            "only the position the organizer reached shows its amounts"
        );
    }
    let register = session.material().county_review().expect("county section");
    let session_record = register
        .state()
        .last_session
        .as_ref()
        .expect("the session was held");
    assert_eq!(session_record.period, 4);
}

/// Prints what the design could not give (spec section 3): the counts of the Wayne opening.
/// Run once with `--ignored`; the file it writes is kept in `reports/`.
#[test]
#[ignore = "writes reports/county-review-2026-11-19/wayne-opening-roster.json"]
fn print_wayne_opening_roster() {
    let catalog = national_opening();
    let session = catalog
        .create_foundation(
            ReplaySessionId::try_from("national-county-print").expect("session identity"),
            ReplaySeed::new(319),
        )
        .expect("ordinary national foundation")
        .into_session()
        .expect("national session");
    let register = session
        .material()
        .county_review()
        .expect("the county section");
    let (config, roster) = (register.config(), &register.state().roster);
    let snapshot =
        aid::material_disclosure(session.catalog(), session.material(), session.duration())
            .expect("the opening disclosure");
    let line = serde_json::to_vec(&RuntimeSessionResponse::OrganizerStatus {
        request_id: 1,
        scope: RuntimeSessionScope {
            epoch: 1,
            campaign_id: Some(campaign().as_uuid().to_string()),
        },
        snapshot: Box::new(snapshot),
    })
    .expect("the status line serializes");
    let groups: Vec<_> = config
        .groups
        .iter()
        .enumerate()
        .map(|(index, group)| {
            let at = u32::try_from(index).expect("few groups");
            let rows = roster.rows.iter().filter(|row| row.key.group == at);
            serde_json::json!({
                "label": group.label,
                "kind": group.kind,
                "households": group.opening_households,
                "roll_units": group.roll_units,
                "has_ownership_income": group.has_ownership_income,
                "receives_mutual_aid": group.receives_mutual_aid,
                "crews": config.crews.iter().filter(|crew| crew.group == at).count(),
                "rows": rows.clone().count(),
                "reached": rows.map(|row| row.reached).sum::<u64>(),
            })
        })
        .collect();
    let bands: Vec<_> = roster
        .band_counts()
        .into_iter()
        .map(|count| serde_json::to_value(count).expect("a band count serializes"))
        .collect();
    let report = serde_json::json!({
        "campaign": campaign().as_uuid().to_string(),
        "unit_price_micros": config.unit_price_micros.to_string(),
        "groups": groups,
        "crews": config.crews.len(),
        "positions": roster.rows.len(),
        "who_works_by_band": bands,
        "organizer_status_line_bytes": line.len(),
        "organizer_status_line_bound": RUNTIME_SESSION_MAX_LINE_BYTES,
    });
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../../reports/county-review-2026-11-19/wayne-opening-roster.json");
    std::fs::create_dir_all(path.parent().expect("the report has a directory"))
        .expect("the report directory is created");
    std::fs::write(
        &path,
        serde_json::to_string_pretty(&report).expect("the report serializes") + "\n",
    )
    .expect("the report is written");
}
