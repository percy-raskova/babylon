//! PER-23 Slice 4 harness (ADR249 R5/R6/R9): the county dossier card's real
//! headless proofs. Every test builds the production plugin set
//! (`MapPlugin` + `TickLoopPlugin` + `DossierCardPlugin`) on
//! `MinimalPlugins` and drives REAL resources, REAL messages, and REAL
//! pointer events — the same composition discipline `tests/projection.rs`
//! established (direct `ButtonInput::press` is wiped by `InputPlugin`'s
//! `PreUpdate`, so key presses ride real `KeyboardInput` messages).
//!
//! The parity thesis under test: the card's repaint derives ONLY from
//! `ActiveCountyDossier`, `DossierFetchState`, and `DossierPageView`, so a
//! seeded projection renders byte-identical zone text headless that the
//! windowed viewer renders from a real fetch — one resource family, one
//! paint path (the rationale `ui::dossier_card`'s module doc commits to).

use babylon_client::decision_surface::{DeclaredSurface, SurfaceId};
use babylon_client::dossier::ChangelogRow;
use babylon_client::map::SelectedCounty;
use babylon_client::palette;
use babylon_client::story;
use babylon_client::ui::dossier_card::{
    ActiveCountyDossier, CountyDossierCardProjection, DossierCardPlugin, DossierCardRoot,
    DossierFetchError, DossierFetchState, DossierPageView, DossierZone,
};
use babylon_client::ui::dossier_compose::{
    PlaceChip, DOSSIER_DECISION_QUESTION, INVESTIGATE_SEALED_CHIP, STUB_SEALED_LINE,
    VAGUE_SEALED_LINE,
};
use babylon_persistence::{
    fog_chip_v1, ArchiveAtomSubjectKindV1, ArchiveAtomSubjectV1, ArchiveAtomV1, ArchiveAtomValueV1,
    ArchiveCitationV1, ArchiveEvidenceClassV1, CampaignId,
};
use bevy::asset::AssetPlugin;
use bevy::input::keyboard::{Key, KeyboardInput, NativeKey};
use bevy::input::ButtonState;
use bevy::picking::backend::HitData;
use bevy::picking::events::{Click, Pointer};
use bevy::picking::pointer::{Location, PointerButton, PointerId};
use bevy::prelude::*;
use bevy::time::TimeUpdateStrategy;
use serde_json::json;
use std::ffi::OsString;
use std::sync::{Mutex, MutexGuard};
use std::time::Duration;
use uuid::Uuid;

// ---- app composition (the production wiring, headless) ----

/// Serializes this binary's `BABYLON_READER_DSN` mutations. Rust test
/// threads share one process, so removing the variable without a lock lets
/// a parallel test's fetch task observe the wrong environment.
static READER_DSN_LOCK: Mutex<()> = Mutex::new(());

/// Holds [`READER_DSN_LOCK`] and restores the ambient `BABYLON_READER_DSN`
/// on drop. The fixture returns this guard before the App so callers bind it
/// first: the App and its fetch tasks drop before the guard restores the env.
/// Keeping the guard outside Bevy also releases it when an assertion unwinds.
struct ReaderDsnGuard {
    _lock: MutexGuard<'static, ()>,
    prior: Option<OsString>,
}

impl ReaderDsnGuard {
    fn lock_and_remove() -> Self {
        let lock = READER_DSN_LOCK
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let prior = std::env::var_os("BABYLON_READER_DSN");
        std::env::remove_var("BABYLON_READER_DSN");
        Self { _lock: lock, prior }
    }
}

impl Drop for ReaderDsnGuard {
    fn drop(&mut self) {
        match self.prior.take() {
            Some(value) => std::env::set_var("BABYLON_READER_DSN", value),
            None => std::env::remove_var("BABYLON_READER_DSN"),
        }
    }
}

/// Builds the real app: the same plugin trio `main.rs`'s windowed mode
/// wires, minus the window. `SelectedStory(counties())` mirrors
/// `tests/projection.rs::new_app`.
fn new_app() -> (ReaderDsnGuard, App) {
    // Determinism contract: this harness never has an Archive reader. A
    // developer's shell may export `BABYLON_READER_DSN` for the live foci;
    // left set, the fetch tasks this file spawns would race a real Postgres.
    // The guard serializes the removal against parallel tests and restores
    // the ambient value only when the App (and its fetch tasks) drops.
    let dsn_guard = ReaderDsnGuard::lock_and_remove();
    let mut app = App::new();
    app.add_plugins((MinimalPlugins, AssetPlugin::default()));
    app.add_plugins(babylon_client::map::MapPlugin);
    app.add_plugins(babylon_client::loop_ui::TickLoopPlugin);
    app.add_plugins(DossierCardPlugin);
    app.insert_resource(story::SelectedStory(story::counties()));
    // I4 (tests/projection.rs): pin zero injected sim time before the first
    // update so `RunState.running`'s wall-clock batch can never advance the
    // engine mid-assertion.
    app.insert_resource(TimeUpdateStrategy::ManualDuration(Duration::ZERO));
    app.update(); // Startup
    (dsn_guard, app)
}

/// Presses `key` through the REAL `KeyboardInput` message pipeline — the
/// house pattern (`tests/projection.rs::press_key_via_real_event`): with
/// `MapPlugin`'s `InputPlugin` present, a direct `ButtonInput::press()` is
/// cleared before any `Update` system observes it.
fn press_key_via_real_event(app: &mut App, key: KeyCode) {
    app.world_mut()
        .resource_mut::<Messages<KeyboardInput>>()
        .write(KeyboardInput {
            key_code: key,
            logical_key: Key::Unidentified(NativeKey::Unidentified),
            state: ButtonState::Pressed,
            text: None,
            repeat: false,
            window: Entity::PLACEHOLDER,
        });
}

fn release_key(app: &mut App, key: KeyCode) {
    app.world_mut()
        .resource_mut::<ButtonInput<KeyCode>>()
        .release(key);
}

// ---- fixtures ----

/// One Archive atom on county 01001 (atlas index 0), the dossier.rs test
/// fixture shape.
fn atom(signal_key: &str, value: &str, valid_tick: u64) -> ArchiveAtomV1 {
    ArchiveAtomV1::try_new(
        CampaignId::from_uuid(Uuid::nil()),
        ArchiveAtomSubjectV1::try_new(ArchiveAtomSubjectKindV1::County, "01001".to_owned())
            .expect("subject admits"),
        signal_key.to_owned(),
        "employment".to_owned(),
        ArchiveEvidenceClassV1::Observed,
        &ArchiveAtomValueV1::Text(value.to_owned()),
        ArchiveCitationV1::try_new("src".to_owned(), "loc".to_owned()).expect("citation admits"),
        valid_tick,
    )
    .expect("atom admits")
}

/// The deterministic card projection: durable 12 / verified 11 (Archive
/// lagging → CRIMSON materializing line), one signal atom, three place
/// chips covering granted / pending / fog, one supersession row.
fn fixture_projection() -> CountyDossierCardProjection {
    CountyDossierCardProjection {
        geoid: "01001".to_owned(),
        title: "Autauga County".to_owned(),
        durable_tick: Some(12),
        content_tick: Some(11),
        verified_tick: Some(11),
        atoms: vec![
            atom("subject", "Autauga County", 1),
            atom("employment", "728576 jobs", 12),
        ],
        places: vec![
            PlaceChip::known("0101076", "Prattville", false),
            PlaceChip::known("0101128", "Millbrook", true),
            PlaceChip::unknown("0199999"),
        ],
        changelog: vec![ChangelogRow {
            signal_key: "employment".to_owned(),
            from_tick: Some(11),
            to_tick: 12,
            from_atom_id: None,
            to_atom_id: [7u8; 32],
            from_value: Some(json!(31.4)),
            to_value: json!(31.87),
        }],
    }
}

// ---- tree readers ----

fn card_root(app: &mut App) -> Entity {
    let world = app.world_mut();
    let mut query = world.query_filtered::<Entity, With<DossierCardRoot>>();
    query.single(world).expect("exactly one dossier card root")
}

fn zone_entity(app: &mut App, zone: DossierZone) -> Entity {
    let world = app.world_mut();
    let mut query = world.query::<(Entity, &DossierZone)>();
    query
        .iter(world)
        .find_map(|(entity, found)| (*found == zone).then_some(entity))
        .unwrap_or_else(|| panic!("zone {zone:?} must exist"))
}

/// Concatenated `Text`/`TextSpan` content of one subtree, one component per
/// line — every `contains` assertion below is against text a player would
/// actually read.
fn subtree_text(app: &mut App, entity: Entity) -> String {
    fn collect(world: &World, entity: Entity, out: &mut String) {
        let piece = world
            .get::<Text>(entity)
            .map(|text| text.0.as_str())
            .or_else(|| world.get::<TextSpan>(entity).map(|span| span.0.as_str()));
        if let Some(piece) = piece {
            if !out.is_empty() {
                out.push('\n');
            }
            out.push_str(piece);
        }
        if let Some(children) = world.get::<Children>(entity) {
            for child in children.iter() {
                collect(world, child, out);
            }
        }
    }
    let world = app.world_mut();
    let mut out = String::new();
    collect(world, entity, &mut out);
    out
}

fn zone_text(app: &mut App, zone: DossierZone) -> String {
    let entity = zone_entity(app, zone);
    subtree_text(app, entity)
}

fn subtree_text_colors(app: &mut App, entity: Entity) -> Vec<Color> {
    fn collect(world: &World, entity: Entity, out: &mut Vec<Color>) {
        if let Some(color) = world.get::<TextColor>(entity) {
            out.push(color.0);
        }
        if let Some(children) = world.get::<Children>(entity) {
            for child in children.iter() {
                collect(world, child, out);
            }
        }
    }
    let world = app.world_mut();
    let mut out = Vec::new();
    collect(world, entity, &mut out);
    out
}

/// Finds the chip NODE whose child `Text` equals `wanted` under `root` —
/// chips are identified by their rendered label (exactly what a player
/// reads), but the node is what carries `PlaceChipNode`, the observers, and
/// the state border (the text child has its own default-required
/// `BorderColor(NONE)`, so tests must address the node, not the text).
fn chip_node_with_text(app: &mut App, root: Entity, wanted: &str) -> Entity {
    let text_entity = find_entity_with_text(app, root, wanted)
        .unwrap_or_else(|| panic!("a chip rendered {wanted:?}"));
    app.world()
        .get::<ChildOf>(text_entity)
        .unwrap_or_else(|| panic!("a chip text lives under a chip node"))
        .parent()
}
/// Finds the first entity whose own `Text`/`TextSpan` equals `wanted` under
/// `root`.
fn find_entity_with_text(app: &mut App, root: Entity, wanted: &str) -> Option<Entity> {
    fn walk(world: &World, entity: Entity, wanted: &str) -> Option<Entity> {
        let matches = world
            .get::<Text>(entity)
            .is_some_and(|text| text.0 == wanted)
            || world
                .get::<TextSpan>(entity)
                .is_some_and(|span| span.0 == wanted);
        if matches {
            return Some(entity);
        }
        world
            .get::<Children>(entity)?
            .iter()
            .find_map(|child| walk(world, child, wanted))
    }
    let world = app.world_mut();
    walk(world, root, wanted)
}

// ---- card driving ----

/// Drives a REAL county selection (spawning the fetch task through
/// `drive_dossier_fetch`), then seizes the card with the deterministic
/// fixture: `Idle` makes `collect_dossier_fetch` early-return forever after
/// (its destructuring match needs `InFlight`), so the orphaned task can
/// never overwrite the seeded projection, and one update repaints every
/// zone from it.
fn seize_card(app: &mut App, projection: CountyDossierCardProjection) {
    app.world_mut().resource_mut::<SelectedCounty>().0 = Some(0); // atlas 0 = fips 01001
    app.update();
    assert!(
        matches!(
            app.world().resource::<DossierFetchState>(),
            DossierFetchState::InFlight { .. } | DossierFetchState::Failed(_)
        ),
        "a real selection change must start a fetch"
    );
    *app.world_mut().resource_mut::<DossierFetchState>() = DossierFetchState::Idle;
    app.world_mut().resource_mut::<ActiveCountyDossier>().0 = Some(projection);
    *app.world_mut().resource_mut::<DossierPageView>() = DossierPageView::Card;
    app.update(); // repaint renders the fixture
}

/// Clicks one place chip by its rendered label through a REAL
/// `Pointer<Click>` trigger on the chip NODE — the observer path a player's
/// click takes, not a direct message write.
fn click_chip(app: &mut App, label: &str) {
    let places = zone_entity(app, DossierZone::Places);
    let chip = chip_node_with_text(app, places, label);
    app.world_mut().trigger(Pointer::new(
        PointerId::Mouse,
        Location {
            target: bevy::camera::NormalizedRenderTarget::None {
                width: 0,
                height: 0,
            },
            position: Vec2::ZERO,
        },
        Click {
            button: PointerButton::Primary,
            hit: HitData {
                camera: Entity::PLACEHOLDER,
                depth: 0.0,
                position: None,
                normal: None,
            },
            duration: Duration::ZERO,
        },
        chip,
    ));
    app.update(); // observer writes the request; repaint swaps the page
}

// ---- the proofs ----

/// Structural golden: the card spawns at Startup hidden, declares the
/// `CountyDossier` surface on the root and every zone, carries all seven
/// zones exactly once, and seals its actions footer with the pinned R9
/// chip text.
#[test]
fn card_spawns_hidden_with_every_zone_and_the_surface_declaration() {
    let (_dsn_guard, mut app) = new_app();
    let root = card_root(&mut app);

    assert_eq!(
        app.world().get::<Visibility>(root),
        Some(&Visibility::Hidden),
        "no county selected — the card must start hidden"
    );
    assert_eq!(
        app.world().get::<DeclaredSurface>(root),
        Some(&DeclaredSurface::new(SurfaceId::CountyDossier)),
        "the root declares the gameplay-role manifest row (ADR249 R9)"
    );

    for zone in [
        DossierZone::Title,
        DossierZone::Question,
        DossierZone::DualTick,
        DossierZone::Signals,
        DossierZone::Places,
        DossierZone::Chronicle,
        DossierZone::Actions,
    ] {
        let world = app.world_mut();
        let mut query = world.query::<&DossierZone>();
        let count = query.iter(world).filter(|found| **found == zone).count();
        assert_eq!(count, 1, "zone {zone:?} must exist exactly once");
    }

    let actions = zone_entity(&mut app, DossierZone::Actions);
    let footer = subtree_text(&mut app, actions);
    assert_eq!(footer, INVESTIGATE_SEALED_CHIP);
    assert!(
        subtree_text_colors(&mut app, actions).contains(&palette::DIM),
        "the sealed chip renders DIM — visibly unavailable, never hidden"
    );
}

/// A selection change reveals the card and starts exactly one fetch. The
/// first frame paints whichever honest line the task has reached: the
/// in-flight "Reading cited observations..." while the task runs, or the
/// reader-absent line if the pool already failed it — never stale data,
/// never a panic, and the projection stays cleared.
#[test]
fn selection_reveals_the_card_and_paints_an_honest_fetch_line() {
    let (_dsn_guard, mut app) = new_app();
    let root = card_root(&mut app);
    assert_eq!(
        app.world().get::<Visibility>(root),
        Some(&Visibility::Hidden)
    );

    app.world_mut().resource_mut::<SelectedCounty>().0 = Some(0);
    app.update();

    assert_eq!(
        app.world().get::<Visibility>(root),
        Some(&Visibility::Visible),
        "a selection must reveal the card"
    );
    assert!(
        app.world().resource::<ActiveCountyDossier>().0.is_none(),
        "an in-flight card never shows stale data"
    );
    let state = app.world().resource::<DossierFetchState>();
    let expected = match state {
        DossierFetchState::InFlight { .. } => "Reading cited observations...",
        DossierFetchState::Failed(DossierFetchError::ReaderAbsent(_)) => {
            "Archive reader not configured"
        }
        other => panic!("first frame must be in-flight or reader-absent, got {other:?}"),
    };
    let dual_tick = zone_text(&mut app, DossierZone::DualTick);
    assert!(
        dual_tick.contains(expected),
        "the dual-tick zone must paint {expected:?}, got {dual_tick:?}"
    );
}

/// The full task path against an absent reader: the fetch FAILS to the
/// honest `ReaderAbsent` state (the CI headless reality) and the card
/// renders the reader-absent line — never a panic, projection stays empty.
#[test]
fn reader_absent_is_the_terminal_honest_line_never_a_panic() {
    let (_dsn_guard, mut app) = new_app();
    app.world_mut().resource_mut::<SelectedCounty>().0 = Some(0);
    for _ in 0..100 {
        app.update();
        if !matches!(
            app.world().resource::<DossierFetchState>(),
            DossierFetchState::InFlight { .. }
        ) {
            break;
        }
    }
    assert!(
        matches!(
            app.world().resource::<DossierFetchState>(),
            DossierFetchState::Failed(DossierFetchError::ReaderAbsent(_))
        ),
        "with no DSN the fetch must terminate ReaderAbsent"
    );
    assert!(app.world().resource::<ActiveCountyDossier>().0.is_none());
    let dual_tick = zone_text(&mut app, DossierZone::DualTick);
    assert!(
        dual_tick.contains("Archive reader not configured"),
        "got {dual_tick:?}"
    );
}

/// The parity proof: with the fixture projection installed, ONE update
/// repaints the whole card from resources alone — title, decision
/// question, the CRIMSON Archive-lag dual tick, signal rows (subject atom
/// suppressed, citation line attached), the chronicle row with the `%.6f`
/// values, and the sealed actions footer.
#[test]
fn seeded_projection_renders_the_whole_card_after_one_update() {
    let (_dsn_guard, mut app) = new_app();
    seize_card(&mut app, fixture_projection());

    assert_eq!(zone_text(&mut app, DossierZone::Title), "Autauga County");
    assert_eq!(
        zone_text(&mut app, DossierZone::Question),
        DOSSIER_DECISION_QUESTION
    );

    // durable 12 / verified 11: the Archive lags, so the verified tick and
    // the materializing line render CRIMSON (R9's honest lag state).
    let dual_tick = zone_text(&mut app, DossierZone::DualTick);
    assert!(dual_tick.contains("durable 12"), "got {dual_tick:?}");
    assert!(dual_tick.contains("verified 11"), "got {dual_tick:?}");
    assert!(
        dual_tick.contains("Archive materializing — verified 11 of 12"),
        "got {dual_tick:?}"
    );
    let dual_tick_zone = zone_entity(&mut app, DossierZone::DualTick);
    assert!(
        subtree_text_colors(&mut app, dual_tick_zone).contains(&palette::CRIMSON),
        "a lagging verified tick must render CRIMSON"
    );

    let signals = zone_text(&mut app, DossierZone::Signals);
    // One segment per line (the tree reader joins components with '\n'):
    // the key, the typed value, and the pinned citation line must all
    // render from the same atom.
    assert!(signals.contains("employment: "), "got {signals:?}");
    assert!(signals.contains("728576 jobs"), "got {signals:?}");
    assert!(
        signals.contains(" — src; loc"),
        "the citation line rides the row, got {signals:?}"
    );
    assert!(
        !signals.contains("subject"),
        "the subject-identity atom is the title, never a signal row"
    );

    let chronicle = zone_text(&mut app, DossierZone::Chronicle);
    // One segment per line: the tick, the key, both values at %.6f, the
    // GOLD arrow, and the verification span each render as their own span.
    assert!(chronicle.contains("t12 "), "got {chronicle:?}");
    assert!(chronicle.contains("employment "), "got {chronicle:?}");
    assert!(
        chronicle.contains("31.400000"),
        "the supersession row renders the from-value at %.6f, got {chronicle:?}"
    );
    assert!(
        chronicle.contains(" → "),
        "the supersession arrow renders, got {chronicle:?}"
    );
    assert!(
        chronicle.contains("31.870000"),
        "the supersession row renders the to-value at %.6f, got {chronicle:?}"
    );
    assert!(
        chronicle.contains("verified 11→12"),
        "the row carries its verification span, got {chronicle:?}"
    );

    let actions = zone_text(&mut app, DossierZone::Actions);
    assert_eq!(actions, INVESTIGATE_SEALED_CHIP);
}

/// The three chip states render from the same projection: granted (BONE,
/// no border), pending (DIM with the pinned "· pending" suffix, DIM
/// border), and fog (the pinned `fog_chip_v1` text, zero label bytes,
/// DIM border).
#[test]
fn place_chips_render_granted_pending_and_fog_states() {
    let (_dsn_guard, mut app) = new_app();
    seize_card(&mut app, fixture_projection());
    let places = zone_entity(&mut app, DossierZone::Places);

    for (label, expected_color, expected_border) in [
        ("Prattville", palette::BONE, Color::NONE),
        (
            "Millbrook · pending",
            palette::DIM,
            palette::DIM.with_alpha(0.6),
        ),
        (
            fog_chip_v1("place", "0199999").as_str(),
            palette::DIM,
            palette::DIM.with_alpha(0.6),
        ),
    ] {
        let chip = chip_node_with_text(&mut app, places, label);
        let colors = subtree_text_colors(&mut app, chip);
        assert!(
            colors.contains(&expected_color),
            "chip {label:?} must render {expected_color:?}, got {colors:?}"
        );
        let border = app
            .world()
            .get::<BorderColor>(chip)
            .expect("a chip carries its base border");
        assert_eq!(
            border.top, expected_border,
            "chip {label:?}'s border color is part of its state language"
        );
    }

    // Exactly three chips — one per link atom in the fixture.
    let world = app.world_mut();
    let mut query = world.query::<(&Children, &DossierZone)>();
    let count = query
        .iter(world)
        .find_map(|(children, zone)| (*zone == DossierZone::Places).then_some(children.len()))
        .expect("the places zone exists");
    assert_eq!(count, 3, "one chip per place link");
}

/// R6(a): clicking a GRANTED chip swaps the card for the client-composed
/// stub — containment from public record, cursory line BONE, the pinned
/// `STUB_SEALED_LINE` CRIMSON, and the data zones honestly emptied.
#[test]
fn granted_chip_click_replaces_the_card_with_the_r6a_stub() {
    let (_dsn_guard, mut app) = new_app();
    seize_card(&mut app, fixture_projection());

    click_chip(&mut app, "Prattville");

    let view = app.world().resource::<DossierPageView>();
    let DossierPageView::Placeholder(request) = view else {
        panic!("a chip click must swap the page view, got {view:?}");
    };
    assert_eq!(request.id, "0101076");
    assert_eq!(request.label.as_deref(), Some("Prattville"));

    assert_eq!(zone_text(&mut app, DossierZone::Title), "Prattville");
    assert_eq!(
        zone_text(&mut app, DossierZone::Question),
        "What is known about place 0101076?"
    );
    let signals = zone_text(&mut app, DossierZone::Signals);
    assert!(
        signals.contains("Prattville — place in Autauga County."),
        "R6(a) containment comes from the county title, got {signals:?}"
    );
    assert!(
        signals.contains(STUB_SEALED_LINE),
        "the stub seals with the pinned R6(a) sentence, got {signals:?}"
    );
    let signals_zone = zone_entity(&mut app, DossierZone::Signals);
    assert!(
        subtree_text_colors(&mut app, signals_zone).contains(&palette::CRIMSON),
        "the sealed line renders CRIMSON"
    );
    assert_eq!(zone_text(&mut app, DossierZone::Places), "");
    assert_eq!(zone_text(&mut app, DossierZone::Chronicle), "");
    assert_eq!(zone_text(&mut app, DossierZone::DualTick), "");
}

/// R6(b): clicking a FOG chip (zero label bytes) swaps the card for the
/// vague placeholder — kind and public id only, no invented name.
#[test]
fn fog_chip_click_replaces_the_card_with_the_r6b_vague_placeholder() {
    let (_dsn_guard, mut app) = new_app();
    seize_card(&mut app, fixture_projection());

    let fog_label = fog_chip_v1("place", "0199999");
    click_chip(&mut app, &fog_label);

    let view = app.world().resource::<DossierPageView>();
    let DossierPageView::Placeholder(request) = view else {
        panic!("a chip click must swap the page view, got {view:?}");
    };
    assert_eq!(request.id, "0199999");
    assert!(
        request.label.is_none(),
        "a fog chip carries zero label bytes below the fog"
    );

    assert_eq!(
        zone_text(&mut app, DossierZone::Title),
        fog_chip_v1("place", "0199999"),
        "an ungranted page renders its pinned fog identity, never an invented name"
    );
    let signals = zone_text(&mut app, DossierZone::Signals);
    assert!(
        signals.contains("You don't have enough detail on place 0199999."),
        "R6(b) names no one below the fog, got {signals:?}"
    );
    assert!(
        signals.contains(VAGUE_SEALED_LINE),
        "the vague placeholder seals with the pinned R6(b) sentence, got {signals:?}"
    );
}

/// The N-key restart clears the card THROUGH the selection signal:
/// `restart_on_n_key`'s `SelectedCounty = None` write is what
/// `drive_dossier_fetch` reacts to — the projection, the page view, and
/// the root visibility all return to the resting state in the same frame.
#[test]
fn n_key_restart_clears_the_card_through_the_selection_signal() {
    let (_dsn_guard, mut app) = new_app();
    seize_card(&mut app, fixture_projection());
    assert_eq!(zone_text(&mut app, DossierZone::Title), "Autauga County");

    press_key_via_real_event(&mut app, KeyCode::KeyN);
    app.update();
    release_key(&mut app, KeyCode::KeyN);

    assert_eq!(app.world().resource::<SelectedCounty>().0, None);
    assert!(
        app.world().resource::<ActiveCountyDossier>().0.is_none(),
        "the restart must drop the projection"
    );
    assert_eq!(
        app.world().resource::<DossierPageView>(),
        &DossierPageView::Card,
        "the page view returns to the card (nothing selected)"
    );
    let root = card_root(&mut app);
    assert_eq!(
        app.world().get::<Visibility>(root),
        Some(&Visibility::Hidden),
        "with no selection the card renders nothing"
    );
}

/// The actions footer is static chrome through every page: the sealed
/// Investigate chip renders unchanged on the stub page too — R9's typed
/// `Unavailable` has a visible counterpart on every render of the card.
#[test]
fn sealed_actions_footer_survives_every_page_view() {
    let (_dsn_guard, mut app) = new_app();
    seize_card(&mut app, fixture_projection());
    click_chip(&mut app, "Prattville");
    let actions = zone_text(&mut app, DossierZone::Actions);
    assert_eq!(actions, INVESTIGATE_SEALED_CHIP);
}

#[test]
fn held_selection_refresh_clears_previous_card_and_starts_a_new_read() {
    let (_dsn_guard, mut app) = new_app();
    seize_card(&mut app, fixture_projection());
    let selected = app.world().resource::<SelectedCounty>().0;
    app.world_mut()
        .resource_mut::<babylon_client::ui::dossier_card::DossierRefresh>()
        .bump();
    app.update();
    assert_eq!(app.world().resource::<SelectedCounty>().0, selected);
    assert!(app.world().resource::<ActiveCountyDossier>().0.is_none());
    assert!(matches!(
        app.world().resource::<DossierFetchState>(),
        DossierFetchState::InFlight { .. } | DossierFetchState::Failed(_)
    ));
}

#[test]
fn obsolete_campaign_generation_and_county_results_cannot_install_or_report_errors() {
    use babylon_client::ui::dossier_card::{DossierCampaignId, DossierRefresh};
    use bevy::tasks::AsyncComputeTaskPool;

    let (_dsn_guard, mut app) = new_app();
    seize_card(&mut app, fixture_projection());
    let campaign = app.world().resource::<DossierCampaignId>().0;
    let generation = app.world().resource::<DossierRefresh>().0;
    for (requested_campaign, requested_generation, fips, error) in [
        (
            CampaignId::from_uuid(Uuid::nil()),
            generation,
            "01001",
            false,
        ),
        (campaign, generation + 1, "01001", false),
        (campaign, generation, "26163", false),
        (campaign, generation + 1, "01001", true),
    ] {
        let result = if error {
            Err(DossierFetchError::ReadFailed("obsolete failure".to_owned()))
        } else {
            Ok(fixture_projection())
        };
        let task = AsyncComputeTaskPool::get().spawn(async move { result });
        *app.world_mut().resource_mut::<DossierFetchState>() = DossierFetchState::InFlight {
            fips: fips.to_owned(),
            campaign: requested_campaign,
            generation: requested_generation,
            task,
        };
        app.update();
        assert!(matches!(
            app.world().resource::<DossierFetchState>(),
            DossierFetchState::Idle
        ));
        assert!(app.world().resource::<ActiveCountyDossier>().0.is_none());
        assert!(!zone_text(&mut app, DossierZone::DualTick).contains("obsolete failure"));
    }
}

#[test]
fn unchanged_card_and_unfinished_task_preserve_the_rendered_subtree() {
    use babylon_client::ui::dossier_card::{DossierCampaignId, DossierRefresh};
    use bevy::tasks::AsyncComputeTaskPool;

    let (_dsn_guard, mut app) = new_app();
    seize_card(&mut app, fixture_projection());
    let title = zone_entity(&mut app, DossierZone::Title);
    let initial = app
        .world()
        .get::<Children>(title)
        .expect("painted title")
        .iter()
        .collect::<Vec<_>>();
    app.update();
    assert_eq!(
        app.world()
            .get::<Children>(title)
            .expect("title remains")
            .iter()
            .collect::<Vec<_>>(),
        initial
    );

    let campaign = app.world().resource::<DossierCampaignId>().0;
    let generation = app.world().resource::<DossierRefresh>().0;
    let task = AsyncComputeTaskPool::get().spawn(std::future::pending());
    *app.world_mut().resource_mut::<DossierFetchState>() = DossierFetchState::InFlight {
        fips: "01001".to_owned(),
        campaign,
        generation,
        task,
    };
    app.update();
    let pending = app
        .world()
        .get::<Children>(title)
        .expect("pending title")
        .iter()
        .collect::<Vec<_>>();
    for _ in 0..3 {
        app.update();
    }
    assert_eq!(
        app.world()
            .get::<Children>(title)
            .expect("pending title remains")
            .iter()
            .collect::<Vec<_>>(),
        pending
    );
}

#[test]
fn observer_archive_layout_and_historical_limitation_are_explicit() {
    use babylon_client::observer::ObserverSession;
    use babylon_client::observer_ui::ObserverUiState;
    use babylon_client::ui::dossier_card::DossierCampaignId;

    let (_dsn_guard, mut app) = new_app();
    seize_card(&mut app, fixture_projection());
    let campaign = app.world().resource::<DossierCampaignId>().0;
    let mut observer = ObserverSession::new(campaign);
    observer.ready(12, None);
    app.insert_resource(observer);
    app.insert_resource(ObserverUiState {
        menu_open: false,
        splash_visible: false,
        ..default()
    });
    app.update();
    let root = card_root(&mut app);
    assert_eq!(
        *app.world().get::<Visibility>(root).expect("visibility"),
        Visibility::Hidden
    );
    let node = app.world().get::<Node>(root).expect("layout");
    assert_eq!(
        (node.top, node.bottom, node.right),
        (px(112), px(96), px(16))
    );
    assert_eq!(
        (node.width, node.min_width, node.max_width),
        (percent(27), px(320), px(440))
    );
    app.world_mut()
        .resource_mut::<ObserverUiState>()
        .archive_open = true;
    app.update();
    assert_eq!(
        *app.world().get::<Visibility>(root).expect("visibility"),
        Visibility::Visible
    );
    assert!(zone_text(&mut app, DossierZone::DualTick).contains("Content last changed at tick 11"));
    app.world_mut()
        .resource_mut::<ObserverSession>()
        .inspect_tick(10);
    app.update();
    assert!(app.world().resource::<ActiveCountyDossier>().0.is_none());
    assert!(matches!(
        app.world().resource::<DossierFetchState>(),
        DossierFetchState::HistoricalUnavailable
    ));
    let text = zone_text(&mut app, DossierZone::DualTick);
    assert!(
        text.contains("Historical Archive pages are unavailable"),
        "{text}"
    );
    assert!(!zone_text(&mut app, DossierZone::Signals).contains("728576 jobs"));
    assert_eq!(
        zone_text(&mut app, DossierZone::Title),
        "Autauga County, AL"
    );
    assert_eq!(
        zone_text(&mut app, DossierZone::Actions),
        "READ-ONLY ARCHIVE"
    );
    assert_eq!(
        zone_text(&mut app, DossierZone::Question),
        "Which cited observations are available for this county?"
    );
    for modal in [0, 1, 2] {
        let mut ui = app.world_mut().resource_mut::<ObserverUiState>();
        ui.menu_open = modal == 0;
        ui.splash_visible = modal == 1;
        ui.comparison_open = modal == 2;
        app.update();
        assert_eq!(
            *app.world().get::<Visibility>(root).expect("visibility"),
            Visibility::Hidden
        );
    }
}
