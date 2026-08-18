//! Task 7.5's own headless real-`App` proof (plan
//! `docs/superpowers/plans/2026-08-17-b3-null-hypothesis-viewer.md` §2.11,
//! task-7-brief.md): `\u{2191}`/`\u{2193}` select through carceral's own
//! derived roster and the real `StatePanelText` entity renders the
//! selected node's own published fields, live off the graph — §2.8's own
//! "read the actual rendered `Text` component" discipline, never a
//! hand-built fixture. Also proves counties (a `MapBinding::Fips` story)
//! is unaffected: the arrow keys are a no-op there, and the panel keeps
//! rendering its own `SelectedCounty` path.

use babylon_client::story;
use bevy::asset::AssetPlugin;
use bevy::input::keyboard::{Key, KeyboardInput, NativeKey};
use bevy::input::ButtonState;
use bevy::prelude::*;

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

fn new_app(selected_story: &'static story::Story) -> App {
    let mut app = App::new();
    app.add_plugins((MinimalPlugins, AssetPlugin::default()));
    app.add_plugins(babylon_client::map::MapPlugin);
    app.add_plugins(babylon_client::loop_ui::TickLoopPlugin);
    app.insert_resource(story::SelectedStory(selected_story));
    app.update(); // Startup.
    app
}

fn state_panel_text(app: &mut App) -> String {
    let world = app.world_mut();
    let mut query = world.query_filtered::<&Text, With<babylon_client::loop_ui::StatePanelText>>();
    query.single(world).map(|t| t.0.clone()).unwrap_or_default()
}

#[test]
fn arrow_down_selects_the_first_carceral_roster_node_and_renders_its_live_fields() {
    let mut app = new_app(story::carceral());

    assert_eq!(
        state_panel_text(&mut app),
        "",
        "nothing selected yet must render the honest empty panel"
    );

    press_key_via_real_event(&mut app, KeyCode::ArrowDown);
    app.update();
    release_key(&mut app, KeyCode::ArrowDown);

    let label = {
        let session = app
            .world()
            .resource::<babylon_client::engine_link::EngineSession>();
        session.full_roster[0].0.clone()
    };

    let text = state_panel_text(&mut app);
    assert!(text.starts_with(&format!("{label} (1/6)")), "got {text:?}");
    // la-approaching (index 0 by NodeId — the scenario's own declaration
    // order) is a SOCIAL_CLASS node: population 600, wealth 515, per
    // carceral-arc-conformance.bscn's own seeded values.
    assert!(
        text.contains("social-class/population: 600.00"),
        "got {text:?}"
    );
    assert!(text.contains("social-class/wealth: 515.00"), "got {text:?}");
}

#[test]
fn arrow_down_seven_times_from_the_start_wraps_back_to_the_first_node() {
    let mut app = new_app(story::carceral());
    // Six presses visit all six distinct roster entries (index 0..=5); the
    // SEVENTH is the first one that wraps back to index 0.
    for _ in 0..7 {
        press_key_via_real_event(&mut app, KeyCode::ArrowDown);
        app.update();
        release_key(&mut app, KeyCode::ArrowDown);
    }
    let text = state_panel_text(&mut app);
    assert!(
        text.contains("(1/6)"),
        "seven presses over a six-entry roster must wrap back to the first, got {text:?}"
    );
}

#[test]
fn arrow_up_from_the_start_also_lands_on_the_first_node_never_a_negative_index() {
    let mut app = new_app(story::carceral());
    press_key_via_real_event(&mut app, KeyCode::ArrowUp);
    app.update();
    release_key(&mut app, KeyCode::ArrowUp);
    let text = state_panel_text(&mut app);
    assert!(text.contains("(1/6)"), "got {text:?}");
}

#[test]
fn the_institution_carrier_is_selectable_and_renders_its_own_published_fields() {
    let mut app = new_app(story::carceral());
    // carceral-register (the INSTITUTION carrier) sorts LAST by NodeId
    // among the 6-entry roster (5 SOCIAL_CLASS nodes declared first in the
    // scenario, the carrier declared last, per
    // carceral_arc_conformance.rs's own CARCERAL_REGISTER = NodeId(5)) —
    // 6 presses from unselected (index 0..=5, ONE press per entry) lands
    // on it.
    for _ in 0..6 {
        press_key_via_real_event(&mut app, KeyCode::ArrowDown);
        app.update();
        release_key(&mut app, KeyCode::ArrowDown);
    }
    let text = state_panel_text(&mut app);
    assert!(text.starts_with("carceral-register (6/6)"), "got {text:?}");
    assert!(
        text.contains("institution/enforcer-population: 0.00"),
        "every latch/census field is seeded 0 at tick 0, got {text:?}"
    );
}

#[test]
fn counties_the_map_bound_story_ignores_the_arrow_keys() {
    let mut app = new_app(story::counties());
    press_key_via_real_event(&mut app, KeyCode::ArrowDown);
    app.update();
    release_key(&mut app, KeyCode::ArrowDown);
    assert_eq!(
        app.world()
            .resource::<babylon_client::ui::roster_panel::SelectedRosterIndex>()
            .0,
        None,
        "a MapBinding::Fips story must never move SelectedRosterIndex"
    );
    assert_eq!(
        state_panel_text(&mut app),
        "",
        "counties' own state panel must stay the SelectedCounty-driven (empty until a click) \
         path, not the roster panel"
    );
}
