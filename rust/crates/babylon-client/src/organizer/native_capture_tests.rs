//! Opt-in fixture-based native rendering through the real window and UI handlers.
//!
//! Register beside `ui::tests` with `#[path = "native_capture_tests.rs"]`.
//! Run only this ignored test with
//! `--test-threads=1`, a task-owned `DISPLAY`, and `BABYLON_NATIVE_CAPTURE_DIR` pointing
//! to a new evidence directory. No runtime process or database is involved.

use std::collections::VecDeque;
use std::ffi::OsString;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

use babylon_persistence::identity::CampaignId;
use babylon_persistence::observer_reader::ObserverCountyEconomy;
use babylon_persistence::runtime_session::{
    OrganizerBodySource, OrganizerObservation, OrganizerReport, OrganizerSnapshot,
};
use bevy::input::keyboard::{Key, KeyboardInput, NativeKey};
use bevy::input::ButtonState;
use bevy::input_focus::{FocusCause, InputFocus};
use bevy::prelude::*;
use bevy::render::renderer::RenderAdapterInfo;
use bevy::render::view::screenshot::{Screenshot, ScreenshotCaptured};
use bevy::window::{PrimaryWindow, WindowPlugin, WindowResolution};
use bevy::winit::WinitPlugin;
use uuid::Uuid;

use crate::atlas::CountyAtlas;
use crate::campaign_browser::CampaignBrowserPlugin;
use crate::map::MapPlugin;
use crate::map_economy_lens::MapLens;
use crate::navigation::NavigationPlugin;
use crate::observer::ObserverSession;
use crate::observer_focus::{
    FocusTree, ObserverFocusPlugin, ObserverFocusPolicy, ObserverFocusTarget,
};
use crate::observer_history::ObserverHistoryPlugin;
use crate::observer_io::ObserverSet;
use crate::observer_map3d::ObserverMap3dPlugin;
use crate::observer_opening::{MenuPage, OpeningPresentation, OpeningStage};
use crate::observer_progress::OperationProgress;
use crate::observer_ui::{ObserverFrame, ObserverShellPlugin, ObserverUiState};
use crate::organizer::{OrganizerClient, OrganizerInspector, RequestKind};
use crate::production::{PrimaryView, ProductionPlugin};
use crate::test_support::EnvVarGuard;
use crate::ui::dossier_card::{
    DossierCampaignId, DossierCardPlugin, DossierFetchError, DossierFetchState,
};
use crate::ui::Interaction;
use crate::visual_assets::{ObserverFonts, VisualAssets, VisualAssetsPlugin};

use super::{ActionButton, OrganizerAction};

/// All extra environment changes occur under the existing test environment lock.
struct IsolatedEnvironment {
    saved: Vec<(&'static str, Option<OsString>)>,
    _data: EnvVarGuard,
}

impl IsolatedEnvironment {
    fn new(root: &Path) -> Self {
        let data = EnvVarGuard::lock("XDG_DATA_HOME");
        data.set(root.join("data").to_str().expect("temporary path is UTF-8"));
        let mut saved = Vec::new();
        for (key, suffix) in [
            ("XDG_STATE_HOME", "state"),
            ("XDG_CONFIG_HOME", "config"),
            ("XDG_CACHE_HOME", "cache"),
        ] {
            saved.push((key, std::env::var_os(key)));
            std::env::set_var(key, root.join(suffix));
        }
        // A fixture diagnostic must not inherit an ordinary campaign's readers.
        for key in ["BABYLON_READER_DSN", "BABYLON_CAMPAIGN_ID"] {
            saved.push((key, std::env::var_os(key)));
            std::env::remove_var(key);
        }
        Self { saved, _data: data }
    }
}

impl Drop for IsolatedEnvironment {
    fn drop(&mut self) {
        for (key, previous) in self.saved.drain(..).rev() {
            match previous {
                Some(value) => std::env::set_var(key, value),
                None => std::env::remove_var(key),
            }
        }
    }
}

#[derive(Clone, Copy)]
enum Activation {
    Keyboard,
    Pointer,
}

enum Step {
    Size(UVec2, bool),
    Named(&'static str, Activation),
    Organizer(OrganizerAction, Activation),
    Capture(String),
    FocusDraft,
    OpenSettings,
    Inspector(OrganizerInspector),
    Primary(PrimaryView),
    Tour(bool),
    Archive(bool),
    ArchiveUnavailable,
    DisclosureClosed,
    Pending(bool),
    ReducedMotion(bool),
    Error,
    Unchanged,
}

#[derive(Resource)]
struct NativeCapture {
    steps: VecDeque<Step>,
    settle: u32,
    capture_pending: bool,
    capture_result: Option<Result<(), String>>,
    output: PathBuf,
    deadline: Instant,
    draft: String,
    period: u64,
    world_hash: Option<String>,
    completed: usize,
    expected_captures: usize,
    viewport: UVec2,
    release_enter: Option<Entity>,
}

fn admitted() -> (OrganizerClient, ObserverSession) {
    use babylon_persistence::runtime_session::RuntimeSessionRequest;
    let (_, _, _, mut snapshot) = crate::organizer::tests::status_fixture();
    let identity = Uuid::new_v4();
    let mut session = ObserverSession::new(CampaignId::from_uuid(identity));
    session.connected_fixture();
    session.ready(3, None);
    assert!(
        session.installed(&session.context()),
        "fixture context installs"
    );
    session.organizer_enabled = true;
    session.playing = true;
    session.content_hash = Some(crate::dossier::hex_bytes([4; 32]));
    session.world_hash = Some(crate::dossier::hex_bytes([5; 32]));
    snapshot.body_scope.source = Some(OrganizerBodySource::Committed {
        tick_content_hash: [4; 32],
        world_hash: [5; 32],
    });
    session.foundation_digest = Some("foundation".into());
    snapshot.body_scope.campaign_id = *identity.as_bytes();
    for encounter in &mut snapshot.city_pd_encounters {
        encounter.campaign_id = *identity.as_bytes();
    }
    let national: OrganizerSnapshot = serde_json::from_str(include_str!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../babylon-persistence/tests/fixtures/national_organizer_opening_v19.json"
    )))
    .expect("captured national opening fixture");
    snapshot.view.organization_label = "Wayne Organizing Collective · native fixture".into();
    snapshot.view.workplace_label = "Wayne County repair and maintenance workplace committee serving the eastern industrial district".into();
    snapshot.view.workplace_partner_label = "Workplace Committee".into();
    snapshot.view.neighborhood_partner_label = "Neighborhood Contact Group".into();
    snapshot.collection = national.collection.map(|mut collection| {
        collection.period = snapshot.view.period;
        collection.actor_id = snapshot.view.actor_id;
        collection
    });
    for period in [2, 3] {
        snapshot.view.observations.push(OrganizerObservation {
            observation_id: [u8::try_from(period).expect("fixture period fits"); 32],
            actor_id: 90,
            subject_id: 91,
            source_actor_id: 92,
            observed_period: period - 1,
            acquired_period: period,
            receipt_id: Some([7; 32]),
            report: OrganizerReport::Work {
                performed_labor_hours: 2,
                output_kg: 777,
                previous_labor_hours: None,
                previous_output_kg: None,
            },
        });
    }
    let mut client = OrganizerClient {
        campaign: Some(identity),
        ..default()
    };
    client.queue(&mut session, RequestKind::Status, None);
    let RuntimeSessionRequest::OrganizerStatus { request_id, .. } =
        client.outbox.take().expect("fixture status request")
    else {
        panic!("status request expected");
    };
    client
        .status(request_id, snapshot, &mut session)
        .expect("fixture passes current admission");
    (client, session)
}

fn replay_steps(steps: &mut VecDeque<Step>) {
    steps.push_back(Step::Named("World", Activation::Keyboard));
    steps.push_back(Step::Primary(PrimaryView::Map));
    steps.push_back(Step::Named("Menu [Esc]", Activation::Keyboard));
    steps.push_back(Step::OpenSettings);
    steps.push_back(Step::Named("Replay interface tour", Activation::Keyboard));
    steps.push_back(Step::Primary(PrimaryView::Organizer));
}

fn tour_steps(steps: &mut VecDeque<Step>, label: &str, larger: bool) {
    if steps.len() == 1 {
        steps.push_back(Step::Tour(true));
        steps.push_back(Step::Named("Skip [Esc]", Activation::Keyboard));
        steps.push_back(Step::Tour(false));
        steps.push_back(Step::Unchanged);
    }
    replay_steps(steps);
    steps.push_back(Step::ReducedMotion(larger));
    steps.push_back(Step::Tour(true));
    for index in 0..7 {
        steps.push_back(Step::Capture(format!("{label}-tour-{}", index + 1)));
        if index == 1 {
            steps.push_back(Step::Named("Previous", Activation::Keyboard));
            steps.push_back(Step::Named("Next", Activation::Keyboard));
        }
        steps.push_back(Step::Named("Next", Activation::Keyboard));
    }
    steps.push_back(Step::Tour(false));
    steps.push_back(Step::ReducedMotion(false));
    steps.push_back(Step::Unchanged);
}

fn inspector_steps(steps: &mut VecDeque<Step>, label: &str) {
    for (inspector, suffix, activation) in [
        (
            OrganizerInspector::Practices,
            "practices",
            Activation::Pointer,
        ),
        (
            OrganizerInspector::Receipts,
            "receipts",
            Activation::Keyboard,
        ),
        (
            OrganizerInspector::Relationships,
            "relationships",
            Activation::Keyboard,
        ),
        (
            OrganizerInspector::Evidence,
            "reports",
            Activation::Keyboard,
        ),
    ] {
        steps.push_back(Step::Organizer(
            OrganizerAction::Inspect(inspector),
            activation,
        ));
        steps.push_back(Step::Inspector(inspector));
        steps.push_back(Step::Capture(format!("{label}-{suffix}")));
        steps.push_back(Step::Named("Back", Activation::Keyboard));
    }
}

fn plan() -> VecDeque<Step> {
    let mut steps = VecDeque::new();
    for (size, larger) in [
        (UVec2::new(1366, 768), true),
        (UVec2::new(1366, 768), false),
        (UVec2::new(1920, 1080), false),
        (UVec2::new(1920, 1080), true),
    ] {
        let label = format!(
            "{}x{}-{}",
            size.x,
            size.y,
            if larger { "larger" } else { "standard" }
        );
        steps.push_back(Step::Size(size, larger));
        tour_steps(&mut steps, &label, larger);
        steps.push_back(Step::Capture(format!("{label}-organizer")));
        inspector_steps(&mut steps, &label);
        steps.push_back(Step::Named("Evidence", Activation::Keyboard));
        steps.push_back(Step::Inspector(OrganizerInspector::Evidence));
        steps.push_back(Step::Capture(format!("{label}-evidence-shell")));
        steps.push_back(Step::Named("Back", Activation::Keyboard));
        steps.push_back(Step::Inspector(OrganizerInspector::Closed));
        steps.push_back(Step::Named("Archive", Activation::Keyboard));
        steps.push_back(Step::Archive(true));
        steps.push_back(Step::ArchiveUnavailable);
        steps.push_back(Step::Capture(format!("{label}-archive-unavailable")));
        steps.push_back(Step::Named("Back", Activation::Keyboard));
        steps.push_back(Step::Archive(false));
        steps.push_back(Step::Primary(PrimaryView::Organizer));
        steps.push_back(Step::Named("Archive", Activation::Keyboard));
        steps.push_back(Step::Archive(true));
        steps.push_back(Step::ArchiveUnavailable);
        steps.push_back(Step::Named("Organizing Home", Activation::Keyboard));
        steps.push_back(Step::Archive(false));
        steps.push_back(Step::Primary(PrimaryView::Organizer));
        steps.push_back(Step::Named("Details", Activation::Keyboard));
        steps.push_back(Step::FocusDraft);
        steps.push_back(Step::Capture(format!("{label}-expanded-details")));
        steps.push_back(Step::Named("Back", Activation::Keyboard));
        steps.push_back(Step::Inspector(OrganizerInspector::Closed));
        steps.push_back(Step::Named("World", Activation::Keyboard));
        steps.push_back(Step::Primary(PrimaryView::Map));
        steps.push_back(Step::Capture(format!("{label}-world-neutral")));
        steps.push_back(Step::Named("Map lens +", Activation::Keyboard));
        steps.push_back(Step::Named("Jobs [1]", Activation::Keyboard));
        steps.push_back(Step::DisclosureClosed);
        steps.push_back(Step::Capture(format!("{label}-world-economic")));
        steps.push_back(Step::Named("Map lens +", Activation::Keyboard));
        steps.push_back(Step::Named("Inventory [6]", Activation::Keyboard));
        steps.push_back(Step::DisclosureClosed);
        steps.push_back(Step::Capture(format!("{label}-world-commodity-labels")));
        steps.push_back(Step::Named("Organizing Home", Activation::Keyboard));
        steps.push_back(Step::Primary(PrimaryView::Organizer));
        steps.push_back(Step::Named("Back", Activation::Keyboard));
        steps.push_back(Step::Primary(PrimaryView::Map));
        steps.push_back(Step::Named("Organizing Home", Activation::Keyboard));
        steps.push_back(Step::Pending(true));
        steps.push_back(Step::Named("World", Activation::Keyboard));
        steps.push_back(Step::Primary(PrimaryView::Map));
        steps.push_back(Step::Named("Organizing Home", Activation::Keyboard));
        steps.push_back(Step::Primary(PrimaryView::Organizer));
        steps.push_back(Step::Capture(format!("{label}-refresh-pending")));
        steps.push_back(Step::ReducedMotion(true));
        steps.push_back(Step::Capture(format!("{label}-refresh-reduced-motion")));
        steps.push_back(Step::Pending(false));
        steps.push_back(Step::ReducedMotion(false));
        steps.push_back(Step::Error);
        steps.push_back(Step::Capture(format!("{label}-visible-error")));
        steps.push_back(Step::Unchanged);
    }
    steps
}

fn eligible_targets(world: &mut World) -> Vec<Entity> {
    use bevy::ecs::system::RunSystemOnce as _;
    world
        .run_system_once(
            |tree: FocusTree,
             policy: Res<ObserverFocusPolicy>,
             targets: Query<Entity, With<ObserverFocusTarget>>| {
                targets
                    .iter()
                    .filter(|entity| tree.tabbable(*entity, &policy))
                    .collect::<Vec<Entity>>()
            },
        )
        .expect("native targets resolve through the real focus policy")
}

fn activate(world: &mut World, entity: Entity, activation: Activation) {
    assert!(
        eligible_targets(world).contains(&entity),
        "native control must pass the real visibility, modal and focus policy"
    );
    match activation {
        Activation::Keyboard => {
            world
                .resource_mut::<InputFocus>()
                .set(entity, FocusCause::Navigated);
            let window = world
                .query_filtered::<Entity, With<PrimaryWindow>>()
                .single(world)
                .expect("native primary window");
            enter(world, window, ButtonState::Pressed);
            world.resource_mut::<NativeCapture>().release_enter = Some(window);
        }
        Activation::Pointer => {
            *world
                .get_mut::<Interaction>(entity)
                .expect("real pointer control") = Interaction::Pressed;
        }
    }
}

fn enter(world: &mut World, window: Entity, state: ButtonState) {
    world.write_message(KeyboardInput {
        key_code: KeyCode::Enter,
        logical_key: Key::Unidentified(NativeKey::Unidentified),
        state,
        text: None,
        repeat: false,
        window,
    });
}

fn capture(world: &mut World, label: &str) {
    log_frame(world, label);
    let path = world
        .resource::<NativeCapture>()
        .output
        .join(format!("{label}.png"));
    assert!(
        !path.exists(),
        "native evidence must not overwrite prior captures"
    );
    let expected = world
        .query_filtered::<&Window, With<PrimaryWindow>>()
        .single(world)
        .expect("one primary window")
        .physical_size();
    assert_eq!(
        expected,
        world.resource::<NativeCapture>().viewport,
        "actual native window reaches the requested matrix dimensions"
    );
    world.resource_mut::<NativeCapture>().capture_pending = true;
    world.spawn(Screenshot::primary_window()).observe(
        move |captured: On<ScreenshotCaptured>, mut capture: ResMut<NativeCapture>| {
            capture.capture_result = Some((|| {
                let image = captured
                    .image
                    .clone()
                    .try_into_dynamic()
                    .map_err(|error| format!("native image: {error}"))?
                    .to_rgb8();
                if image.width() != expected.x || image.height() != expected.y {
                    return Err(format!(
                        "wrong capture size: {:?}, expected {expected:?}",
                        image.dimensions()
                    ));
                }
                image
                    .save(&path)
                    .map_err(|error| format!("{}: {error}", path.display()))?;
                eprintln!("fixture-based native rendering: {}", path.display());
                Ok(())
            })());
        },
    );
}

fn log_frame(world: &mut World, label: &str) {
    if label.ends_with("-tour-1") {
        if let Some(adapter) = world.get_resource::<RenderAdapterInfo>() {
            eprintln!(
                "native adapter: name={} backend={:?} device={:?}",
                adapter.name, adapter.backend, adapter.device_type
            );
        }
    }
    if label.ends_with("-organizer") {
        let scale = world.resource::<UiScale>().0;
        eprintln!("native configuration: {label}, UiScale={scale}");
        for (button, border, background, target) in world
            .query::<(
                &ActionButton,
                &BorderColor,
                &BackgroundColor,
                &ObserverFocusTarget,
            )>()
            .iter(world)
        {
            if button.0 == OrganizerAction::Advance {
                eprintln!(
                    "native Advance: available={} border={border:?} background={background:?}",
                    target.available
                );
            }
        }
    }
}

fn focus_draft(world: &mut World) {
    let choice = world.resource::<OrganizerClient>().choice();
    let admitted = eligible_targets(world);
    let entity = world
        .query::<(Entity, &ActionButton)>()
        .iter(world)
        .find_map(|(entity, button)| {
            (button.0 == OrganizerAction::Choose(choice) && admitted.contains(&entity))
                .then_some(entity)
        })
        .expect("selected practice is a real admitted focus control");
    world
        .resource_mut::<InputFocus>()
        .set(entity, FocusCause::Navigated);
}

fn assets_ready(world: &World) -> bool {
    let fonts = world.resource::<ObserverFonts>();
    let font_assets = world.resource::<Assets<Font>>();
    let visuals = world.resource::<VisualAssets>();
    let images = world.resource::<Assets<Image>>();
    font_assets.get(&fonts.body).is_some()
        && font_assets.get(&fonts.display).is_some()
        && images.get(&visuals.group_wayne_collective).is_some()
        && images.get(&visuals.group_workplace_committee).is_some()
        && images.get(&visuals.group_neighborhood_contact).is_some()
}

fn drive(world: &mut World) {
    if let Some(window) = world.resource_mut::<NativeCapture>().release_enter.take() {
        enter(world, window, ButtonState::Released);
    }
    assert!(
        Instant::now() < world.resource::<NativeCapture>().deadline,
        "fixture-based native rendering exceeded its 45-minute deadline"
    );
    if !assets_ready(world) {
        return;
    }
    let result = world.resource_mut::<NativeCapture>().capture_result.take();
    if let Some(result) = result {
        result.expect("native Screenshot capture must save successfully");
        let mut capture = world.resource_mut::<NativeCapture>();
        capture.capture_pending = false;
        capture.completed += 1;
        capture.settle = 0;
    }
    if world.resource::<NativeCapture>().capture_pending {
        return;
    }
    if world.resource::<NativeCapture>().settle > 0 {
        world.resource_mut::<NativeCapture>().settle -= 1;
        return;
    }
    let Some(step) = world.resource_mut::<NativeCapture>().steps.pop_front() else {
        let capture = world.resource::<NativeCapture>();
        assert_eq!(
            capture.completed, capture.expected_captures,
            "every planned native capture completes with a saved acknowledgement"
        );
        eprintln!(
            "native matrix complete: {} acknowledged PNGs",
            capture.completed
        );
        world.write_message(AppExit::Success);
        return;
    };
    // Input/release, modal eligibility, Last-stage restoration and its next layout
    // all run before the following capture. Saved-image acknowledgement needs no idle frames.
    world.resource_mut::<NativeCapture>().settle = 4;
    execute_step(world, step);
}

fn activate_named(world: &mut World, label: &str, activation: Activation) {
    let admitted = eligible_targets(world);
    let entity = world
        .query::<(Entity, &ObserverFocusTarget, &Children)>()
        .iter(world)
        .find_map(|(entity, target, children)| {
            (target.available
                && admitted.contains(&entity)
                && children
                    .iter()
                    .any(|child| world.get::<Text>(child).is_some_and(|text| text.0 == label)))
            .then_some(entity)
        })
        .unwrap_or_else(|| panic!("visible admitted native control: {label}"));
    activate(world, entity, activation);
}

fn activate_organizer(world: &mut World, action: OrganizerAction, activation: Activation) {
    let admitted = eligible_targets(world);
    let entity = world
        .query::<(Entity, &ActionButton, &ObserverFocusTarget)>()
        .iter(world)
        .find_map(|(entity, button, target)| {
            (button.0 == action && target.available && admitted.contains(&entity)).then_some(entity)
        })
        .unwrap_or_else(|| panic!("visible organizer control: {action:?}"));
    activate(world, entity, activation);
}

fn open_settings(world: &mut World) {
    assert!(
        world.resource::<ObserverUiState>().menu_open,
        "native Settings route begins in the actual open menu"
    );
    let opening = world.resource::<OpeningPresentation>();
    assert_eq!(
        opening.stage,
        OpeningStage::Game,
        "the admitted fixture uses the real in-game lifecycle"
    );
    match opening.menu_page {
        MenuPage::InGame => activate_named(world, "Settings", Activation::Keyboard),
        MenuPage::Settings => {}
        page @ (MenuPage::Home | MenuPage::SavedGames | MenuPage::Campaigns) => {
            panic!("unexpected in-game menu page before replay: {page:?}");
        }
    }
}

fn execute_step(world: &mut World, step: Step) {
    match step {
        Step::Size(size, larger) => {
            world.resource_mut::<NativeCapture>().viewport = size;
            let mut windows = world.query_filtered::<&mut Window, With<PrimaryWindow>>();
            windows
                .single_mut(world)
                .expect("one real primary window")
                .resolution
                .set_physical_resolution(size.x, size.y);
            world.resource_mut::<ObserverUiState>().larger_interface = larger;
            world.resource_mut::<ObserverUiState>().lens = MapLens::Relationships;
            world.resource_mut::<OrganizerClient>().message.clear();
        }
        Step::Named(label, activation) => {
            activate_named(world, label, activation);
        }
        Step::Organizer(action, activation) => {
            activate_organizer(world, action, activation);
        }
        Step::OpenSettings => {
            open_settings(world);
        }
        Step::FocusDraft => {
            focus_draft(world);
        }
        Step::Capture(label) => {
            capture(world, &label);
        }
        Step::Inspector(expected) => {
            assert_eq!(
                world.resource::<OrganizerClient>().inspector,
                expected,
                "real organizer handler opens the requested inspector"
            );
        }
        Step::Primary(expected) => {
            assert_eq!(
                *world.resource::<PrimaryView>(),
                expected,
                "real navigation handler restores the requested primary view"
            );
        }
        Step::Tour(expected) => {
            assert_eq!(
                world.resource::<ObserverUiState>().interface_tour_open,
                expected,
                "tour opening/completion follows its real controls"
            );
        }
        Step::Archive(expected) => {
            assert_eq!(
                world.resource::<ObserverUiState>().archive_open,
                expected,
                "real Archive/Home handlers toggle the archive overlay"
            );
        }
        Step::DisclosureClosed => {
            assert!(
                world.resource::<ObserverUiState>().disclosure.is_none(),
                "selecting a lens closes its ordinary disclosure drawer"
            );
        }
        Step::ArchiveUnavailable => {
            wait_for_archive(world);
        }
        Step::Pending(pending) => {
            world
                .resource_mut::<ObserverSession>()
                .set_organizer_control_pending(pending);
        }
        Step::ReducedMotion(reduced) => {
            world.resource_mut::<ObserverUiState>().reduced_motion = reduced;
        }
        Step::Error => {
            world.resource_mut::<OrganizerClient>().message =
                "Fixture diagnostic: organizer refresh failed. Your committed period remains available; retry the refresh.".into();
        }
        Step::Unchanged => {
            assert_unchanged(world);
        }
    }
}

fn wait_for_archive(world: &mut World) {
    match world.resource::<DossierFetchState>() {
        DossierFetchState::InFlight { .. } => {
            world
                .resource_mut::<NativeCapture>()
                .steps
                .push_front(Step::ArchiveUnavailable);
        }
        DossierFetchState::Failed(DossierFetchError::ReaderAbsent(_)) => {}
        state => panic!("isolated Archive must report its unavailable reader honestly: {state:?}"),
    }
}

fn assert_unchanged(world: &World) {
    let capture = world.resource::<NativeCapture>();
    let client = world.resource::<OrganizerClient>();
    let session = world.resource::<ObserverSession>();
    assert_eq!(
        format!("{:?}", client.draft),
        capture.draft,
        "tour and reading never edit the draft"
    );
    assert_eq!(
        session.durable_tick, capture.period,
        "reading never advances the period"
    );
    assert_eq!(
        session.world_hash, capture.world_hash,
        "reading never changes world identity"
    );
    assert!(
        client.outbox.is_none() && client.pending.is_none(),
        "native reading never submits authority requests"
    );
    assert!(!session.playing, "closing the tour leaves autoplay paused");
}

fn observation(session: &ObserverSession, states: &[&str]) -> ObserverFrame {
    let mut frame = crate::observer_io::tests::snapshot_with_event(session, "production", 3);
    frame.production = Some(crate::production::tests::snapshot());
    let atlas = CountyAtlas::parse(include_bytes!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../assets/map/county_atlas.bin"
    )))
    .expect("captured atlas");
    for index in 0..atlas.len() {
        let county = atlas.county(index).expect("atlas county exists");
        if states.iter().any(|state| county.fips.starts_with(*state)) {
            frame.counties.push(ObserverCountyEconomy {
                county_geoid: county.fips.into(),
                annual_avg_estabs_count: Some(200),
                annual_avg_emplvl: Some(1_000 + u64::try_from(index).expect("atlas index fits")),
                total_annual_wages: Some(12_000_000),
                annual_avg_wkly_wage: Some(700),
            });
        }
    }
    frame
        .counties
        .sort_by(|left, right| left.county_geoid.cmp(&right.county_geoid));
    ObserverFrame(Some(frame), None)
}

fn install_native_app(
    app: &mut App,
    client: OrganizerClient,
    session: ObserverSession,
    capture: NativeCapture,
    frame: ObserverFrame,
) {
    let dossier_campaign = DossierCampaignId(session.campaign);
    app.add_plugins(
        DefaultPlugins
            .set(WindowPlugin {
                primary_window: Some(Window {
                    title: "Babylon · fixture-based native rendering".into(),
                    resolution: WindowResolution::new(1366, 768).with_scale_factor_override(1.0),
                    ..default()
                }),
                ..default()
            })
            .set(WinitPlugin {
                run_on_any_thread: true,
            }),
    )
    .add_plugins(VisualAssetsPlugin)
    .add_plugins(MapPlugin)
    .add_plugins(ObserverFocusPlugin)
    .add_plugins(ObserverShellPlugin)
    .add_plugins(ObserverMap3dPlugin)
    .add_plugins(ProductionPlugin)
    .add_plugins(CampaignBrowserPlugin)
    .add_plugins(ObserverHistoryPlugin)
    .add_plugins(DossierCardPlugin)
    .insert_resource(client)
    .insert_resource(dossier_campaign)
    .insert_resource(session)
    .insert_resource(capture)
    .insert_resource(frame)
    .insert_resource(PrimaryView::Organizer)
    .insert_resource(OpeningPresentation {
        stage: OpeningStage::Game,
        menu_page: MenuPage::InGame,
        ..default()
    })
    .insert_resource(ObserverUiState {
        menu_open: false,
        splash_visible: false,
        ..default()
    })
    .init_resource::<OperationProgress>()
    .insert_resource(ClearColor(crate::observer_theme::INK))
    .configure_sets(
        Update,
        (
            ObserverSet::Input,
            ObserverSet::Receive,
            ObserverSet::Install,
            ObserverSet::Paint,
        )
            .chain(),
    )
    .add_systems(
        Update,
        crate::observer_progress::track.before(ObserverSet::Paint),
    )
    .add_systems(Last, drive);
    // command_app currently installs no navigation plugin. Keep composition safe
    // if that shared test constructor acquires one during later integration.
    if !app.is_plugin_added::<NavigationPlugin>() {
        app.add_plugins(NavigationPlugin);
    }
    super::install(app);
    crate::organizer::interface_tour::install(app);
}

#[test]
#[ignore = "requires task-owned native X11 renderer and explicit evidence directory"]
fn fixture_based_native_rendering_matrix() {
    run_capture(plan(), &["26"]);
}

#[test]
#[ignore = "requires task-owned native X11 renderer and explicit evidence directory"]
fn fixture_based_native_regional_palette() {
    let steps = VecDeque::from([
        Step::Size(UVec2::new(1920, 1080), false),
        Step::Tour(true),
        Step::Named("Skip [Esc]", Activation::Keyboard),
        Step::Tour(false),
        Step::Named("World", Activation::Keyboard),
        Step::Primary(PrimaryView::Map),
        Step::Capture("1920x1080-standard-regional-neutral".into()),
        Step::Unchanged,
    ]);
    run_capture(steps, &["18", "26", "39"]);
}

fn run_capture(steps: VecDeque<Step>, states: &[&str]) {
    let output = PathBuf::from(
        std::env::var_os("BABYLON_NATIVE_CAPTURE_DIR")
            .expect("opt-in native rendering requires BABYLON_NATIVE_CAPTURE_DIR"),
    );
    assert!(
        output.is_absolute(),
        "native evidence directory must be absolute"
    );
    fs::create_dir_all(&output).expect("create new native evidence directory");
    let isolation_root = std::env::temp_dir().join(format!("wayne-native-{}", Uuid::new_v4()));
    fs::create_dir_all(&isolation_root).expect("create disposable presentation state");
    let _environment = IsolatedEnvironment::new(&isolation_root);
    let (client, session) = admitted();
    let frame = observation(&session, states);
    eprintln!(
        "native regional fixture: states={states:?} counties={}",
        frame
            .0
            .as_ref()
            .expect("fixture observation")
            .counties
            .len()
    );
    eprintln!(
        "native fixture campaign={} personal_state={} output={}",
        session.campaign.as_uuid(),
        isolation_root.display(),
        output.display()
    );
    let capture = NativeCapture {
        expected_captures: steps
            .iter()
            .filter(|step| matches!(step, Step::Capture(_)))
            .count(),
        steps,
        settle: 90,
        capture_pending: false,
        capture_result: None,
        output,
        deadline: Instant::now() + Duration::from_mins(45),
        draft: format!("{:?}", client.draft),
        period: session.durable_tick,
        world_hash: session.world_hash.clone(),
        completed: 0,
        viewport: UVec2::new(1366, 768),
        release_enter: None,
    };
    let (mut app, _requests) = crate::observer_io::tests::command_app();
    install_native_app(&mut app, client, session, capture, frame);
    assert_eq!(
        app.run(),
        AppExit::Success,
        "native capture app exits successfully"
    );
}
