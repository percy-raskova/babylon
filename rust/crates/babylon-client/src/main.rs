//! `babylon-client` — the Program 28 B0 Bevy scaffold. Amendment AF names
//! this crate the v1.0 client: a standalone Bevy executable, engine crates
//! linked in-process, no PyO3 in the play path. B0 proves the window opens
//! with the KSBC palette (this module) and the engine link fires one
//! deterministic tick at startup (`engine_link`, Task 12).
//!
//! No true "Iosevka Term" family is installed on this build machine (only
//! Nerd Font variants, without a bundled OFL license file alongside them);
//! per the B0 scope this title uses Bevy's built-in default font rather
//! than shipping an unlicensed asset. Iosevka lands when the Director's
//! font files are available (see the PR body).

mod palette;

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
        .insert_resource(ClearColor(palette::FIELD))
        .add_systems(Startup, (spawn_camera, spawn_title))
        .run();
}

fn spawn_camera(mut commands: Commands) {
    commands.spawn(Camera2d);
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
