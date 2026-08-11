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
/// `Update`-scheduled system like `advance_on_space` ever observes it
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

#[test]
fn pressing_space_advances_the_tick_and_updates_the_hash_text() {
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
}
