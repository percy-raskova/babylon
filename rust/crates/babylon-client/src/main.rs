//! `babylon-client` — the Program 28 client. Amendment AF names this crate
//! the v1.0 client: a standalone Bevy executable, engine crates linked
//! in-process, no PyO3 in the play path.
//!
//! No true "Iosevka Term" family is installed on this build machine (only
//! Nerd Font variants, without a bundled OFL license file alongside them);
//! per the B0 scope this title uses Bevy's built-in default font rather
//! than shipping an unlicensed asset. Iosevka lands when the Director's
//! font files are available (see the PR body).
//!
//! B1 Task 6 wires in `map::MapPlugin`, which spawns the county fill and
//! border meshes at Startup. B1 Task 7 folds the camera into `MapPlugin`
//! too (`map::camera::spawn_camera`, a bounded pan/zoom `PanCamera` sized
//! from the atlas) — B0's bare `spawn_camera` is dropped here so exactly
//! one camera exists.
//!
//! B2 Task 14 wires in `loop_ui::TickLoopPlugin` — Space advances the tick,
//! a HUD readout shows the counter and the deterministic hash. B0's
//! `log_engine_link` Startup system is retired here: `EngineSession::start`
//! (`TickLoopPlugin`'s own Startup system) now IS the engine link, and it
//! panics loudly on failure exactly as `log_engine_link` did —
//! `engine_link::engine_link_probe` itself is untouched (B0's own pinned
//! test, `tests/engine_link.rs`, still exercises it directly).

use babylon_client::{loop_ui, map, palette};
use bevy::prelude::*;

fn main() {
    App::new()
        .add_plugins(DefaultPlugins.set(WindowPlugin {
            primary_window: Some(Window {
                title: "Babylon — The Fall of America".into(),
                ..default()
            }),
            ..default()
        }))
        .add_plugins(map::MapPlugin)
        .add_plugins(loop_ui::TickLoopPlugin)
        .insert_resource(ClearColor(palette::FIELD))
        .add_systems(Startup, spawn_title)
        .run();
}

fn spawn_title(mut commands: Commands) {
    commands.spawn((
        Text::new("BABYLON"),
        TextFont {
            font_size: 64.0,
            ..default()
        },
        TextColor(palette::GOLD),
        Node {
            position_type: PositionType::Absolute,
            top: px(24),
            left: px(24),
            ..default()
        },
    ));
}
