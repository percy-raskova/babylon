//! The scriptable half of the B2 eyes-on gate (Task 18). Never a
//! replacement for the human pass (nothing here can see a color on
//! screen), but it proves every INPUT-DRIVEN, hash-provable claim that
//! pass makes, so a future change that silently breaks the loop reds THIS
//! gate in CI before a human ever has to notice by eye.
//!
//! **Mechanical fixes, recorded rather than silently applied.**
//!
//! 1. Event-type strings at the sink boundary are BARE enum members —
//!    `"LIFECYCLE_TRANSITION"`, `"ENTITY_DEATH"` — never
//!    `"EventType/LIFECYCLE_TRANSITION"`/`"EventType/ENTITY_DEATH"`, the
//!    literal spelling the plan's own code block used. Verified against
//!    every live event-name assertion in `babylon-tick`'s own conformance
//!    tests (`lifecycle_conformance.rs`, `vitality_conformance.rs`) and
//!    against `structural_verbs::EffectExecutor::enum_member`, which
//!    returns the bare `Atom::EnumRef { member, .. }` — the same gotcha
//!    Task 7's `us_counties_demo.rs` and this plan's handoff notes already
//!    name (bit the plan twice before this).
//! 2. Directly mutating `ButtonInput` (`.press()`/`.release()`) from test
//!    code, then calling `app.update()`, does not reliably drive
//!    `just_pressed` here: `MapPlugin` conditionally self-adds
//!    `InputPlugin`, whose `PreUpdate` `keyboard_input_system`
//!    unconditionally clears `just_pressed` every frame to make room for
//!    real events, wiping a manually-set flag before an `Update`-scheduled
//!    system (`advance_on_space`/`cycle_lens_on_tab`) ever observes it —
//!    the same gotcha `map/mod.rs`'s own module doc and Tasks 11/12/14
//!    already found and fixed. Pressing through a REAL `KeyboardInput`
//!    message (`Entity::PLACEHOLDER` for the unread `window` field) lets
//!    `keyboard_input_system`'s own event-driven logic set `just_pressed`
//!    correctly; releasing directly between presses is safe (`clear()`
//!    never touches the `pressed` set, only `just_pressed`/`just_released`).
use babylon_graph::state_hash::CanonicalState; // trait import — .state_hash() below needs it in scope
use bevy::asset::AssetPlugin;
use bevy::input::keyboard::{Key, KeyboardInput, NativeKey};
use bevy::input::ButtonState;
use bevy::prelude::*;
use std::collections::HashSet;

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

#[test]
fn five_space_presses_advance_five_distinct_ticks_and_fire_both_packs_events() {
    let mut app = App::new();
    app.add_plugins((MinimalPlugins, AssetPlugin::default()));
    app.add_plugins(babylon_client::map::MapPlugin);
    app.add_plugins(babylon_client::loop_ui::TickLoopPlugin);
    app.update(); // Startup

    let mut hashes = HashSet::new();
    for _ in 0..5 {
        press_key_via_real_event(&mut app, KeyCode::Space);
        app.update();
        release_key(&mut app, KeyCode::Space);

        let session = app
            .world()
            .resource::<babylon_client::engine_link::EngineSession>();
        hashes.insert(session.inner.graph().state_hash().expect("hash"));
    }
    assert_eq!(hashes.len(), 5, "five presses, five distinct hashes");

    let session = app
        .world()
        .resource::<babylon_client::engine_link::EngineSession>();
    assert!(
        session
            .sink
            .events
            .iter()
            .any(|(name, _)| name == "LIFECYCLE_TRANSITION"),
        "the event feed must carry lifecycle's own emitted events"
    );
    assert!(
        session
            .sink
            .events
            .iter()
            .any(|(name, _)| name == "ENTITY_DEATH"),
        "the event feed must carry vitality's own emitted events too — \
         proving both packs actually ran, not just lifecycle"
    );
}

#[test]
fn defaults_to_population_trend_and_tab_cycles_through_all_three() {
    let mut app = App::new();
    app.add_plugins((MinimalPlugins, AssetPlugin::default()));
    app.add_plugins(babylon_client::map::MapPlugin);
    app.update();

    // Task 8's finding: Tension has zero data on this demo content, so the
    // app must not default to it.
    assert_eq!(
        *app.world().resource::<babylon_client::map::ActiveLens>(),
        babylon_client::map::ActiveLens::PopulationTrend
    );

    let mut seen = vec![*app.world().resource::<babylon_client::map::ActiveLens>()];
    for _ in 0..3 {
        press_key_via_real_event(&mut app, KeyCode::Tab);
        app.update();
        release_key(&mut app, KeyCode::Tab);
        seen.push(*app.world().resource::<babylon_client::map::ActiveLens>());
    }
    use babylon_client::map::ActiveLens::{Legitimation, PopulationTrend, Tension};
    assert_eq!(
        seen,
        vec![PopulationTrend, Tension, Legitimation, PopulationTrend],
        "three presses from the default must visit every lens once and return to start"
    );
}

#[test]
fn a_known_demo_county_actually_recolors_after_a_space_press() {
    // THE test the MEDIUM-HIGH finding asked for: real `TickLoopPlugin` +
    // `MapPlugin` together, no hand-installed `CurrentLensData` (contrast
    // Task 10 Step 4's own test, which deliberately hand-builds a fixture
    // to test `recolor_on_lens_changed`'s LOGIC in isolation — this test
    // proves the real app's WIRING reaches the mesh at all, which a
    // hand-installed resource cannot prove by construction). Before this
    // test existed, every automated check in this plan passed even in a
    // build where `CurrentLensData`/lens-recolor wiring never resolved and
    // the map never recolored — this closes that gap.
    let mut app = App::new();
    app.add_plugins((MinimalPlugins, AssetPlugin::default()));
    app.add_plugins(babylon_client::map::MapPlugin);
    app.add_plugins(babylon_client::loop_ui::TickLoopPlugin);
    app.update(); // Startup — real EngineSession, real CurrentLensData, real MapSurface.

    fn county_zero_colors(app: &App) -> Vec<[f32; 4]> {
        let surface = app.world().resource::<babylon_client::map::MapSurface>();
        let meshes = app.world().resource::<Assets<Mesh>>();
        let mesh = meshes
            .get(&surface.fill_mesh)
            .expect("fill mesh is registered");
        let (start, end) = surface.tessellation.county_vertex_range[0]; // atlas index 0 = DEMO_FIPS[0]
        match mesh
            .attribute(Mesh::ATTRIBUTE_COLOR)
            .expect("fill mesh carries per-vertex color")
        {
            bevy::mesh::VertexAttributeValues::Float32x4(colors) => {
                colors[start as usize..end as usize].to_vec()
            }
            other => panic!("unexpected color attribute shape: {other:?}"),
        }
    }

    // Tick 0: PopulationTrend is the default lens, and every county reads
    // `Some(0.0)` (now == baseline, nothing has ticked yet) — DIM.
    let before = county_zero_colors(&app);

    press_key_via_real_event(&mut app, KeyCode::Space);
    app.update();

    // Atlas index 0 is a `core` (x0.95) family county — Task 9b's own
    // table has this family net-DECLINING, so after tick 1 it must read
    // CRIMSON, genuinely different from tick 0's DIM.
    let after = county_zero_colors(&app);

    assert_ne!(
        before, after,
        "the demo county at atlas index 0 must actually recolor after one Space press — \
         if this fails, CurrentLensData is not reaching the mesh even though the tick itself \
         advanced (check that advance_on_space's ResMut<CurrentLensData> param and its three \
         lens.rs calls are wired, and that recolor_on_lens_changed's Res<MapSurface> resolves)"
    );
}
