//! Task 14's own headless proof: pressing Space advances the tick and
//! updates the hash text — real `MapPlugin` + `TickLoopPlugin` together, no
//! hand-installed resources.
use bevy::asset::AssetPlugin;
use bevy::input::keyboard::{Key, KeyboardInput, NativeKey};
use bevy::input::ButtonState;
use bevy::prelude::*;

/// Presses `key` through the REAL `KeyboardInput` message pipeline.
/// Necessary, not stylistic: `MapPlugin` conditionally self-adds
/// `InputPlugin`, whose `PreUpdate` `keyboard_input_system`
/// unconditionally clears `just_pressed` every frame — a direct
/// `ButtonInput::press()` call made from test code (outside any schedule,
/// before `app.update()`) gets wiped by that same clear before an
/// `Update`-scheduled system like `advance_ticks` ever observes it
/// (`crates/babylon-client/src/map/mod.rs`'s own module doc has the full
/// citation and the first place this was found). `window:
/// Entity::PLACEHOLDER` is safe — `keyboard_input_system` never reads it.
fn press_key_via_real_event(app: &mut App, key: bevy::input::keyboard::KeyCode) {
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

/// FB3 fix (adversarial-panel finding): this test's own NAME already
/// claimed "updates the hash text", but the body only ever checked
/// `TickCounter` — hardcoding `refresh_readouts`' hash text to
/// `"hash: deadbeefdeadbeef"` left this test fully green (mutation-proven).
/// Now the test reads the ACTUAL rendered `HashReadout` text and checks it
/// against the session's own real post-tick `state_hash`, so the name is
/// no longer an overclaim.
#[test]
fn pressing_space_advances_the_tick_and_updates_the_hash_text() {
    // Needed below to call `.state_hash()`; hoisted to the top of the
    // function (clippy::items_after_statements) rather than left inline
    // where it was first used.
    use babylon_graph::state_hash::CanonicalState;

    let mut app = App::new();
    app.add_plugins((MinimalPlugins, AssetPlugin::default()));
    app.add_plugins(babylon_client::map::MapPlugin);
    app.add_plugins(babylon_client::loop_ui::TickLoopPlugin);
    app.update(); // Startup: EngineSession inserted, tick 0

    let counter = app
        .world()
        .resource::<babylon_client::loop_ui::TickCounter>();
    assert_eq!(counter.0, 0);

    press_key_via_real_event(&mut app, KeyCode::Space);
    app.update();

    let counter = app
        .world()
        .resource::<babylon_client::loop_ui::TickCounter>();
    assert_eq!(counter.0, 1);

    // The ACTUAL rendered hash text must match the session's own real
    // post-tick state_hash — not a placeholder, not a stale value.
    let session = app
        .world()
        .resource::<babylon_client::engine_link::EngineSession>();
    let expected_hash = session
        .inner
        .graph()
        .state_hash()
        .expect("post-tick state hashes");
    let expected_text = format!("hash: {}", babylon_tick::hex(&expected_hash));

    let world = app.world_mut();
    let mut query = world.query_filtered::<&Text, With<babylon_client::loop_ui::HashReadout>>();
    let hash_text = query
        .single(world)
        .expect("exactly one hash readout entity")
        .0
        .clone();
    assert_eq!(
        hash_text, expected_text,
        "the rendered hash readout must equal the session's own real post-tick state_hash"
    );
}
