//! `babylon-client` — the Program 28 B0 Bevy scaffold. Amendment AF names
//! this crate the v1.0 client: a standalone Bevy executable, engine crates
//! linked in-process, no PyO3 in the play path. B0 proves the window opens
//! with the KSBC palette (`palette`) and the engine link fires one
//! deterministic tick at startup (`engine_link`) — both live in this
//! package's library target (`lib.rs`) so the integration tests can reach
//! them without duplicating the code into the binary.
//!
//! No true "Iosevka Term" family is installed on this build machine (only
//! Nerd Font variants, without a bundled OFL license file alongside them);
//! per the B0 scope this title uses Bevy's built-in default font rather
//! than shipping an unlicensed asset. Iosevka lands when the Director's
//! font files are available (see the PR body).

use babylon_client::{engine_link, palette};
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
        .add_systems(Startup, (spawn_camera, spawn_title, log_engine_link))
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

/// B0's proof that the client links the engine in-process: run one
/// deterministic tick at startup and log the byte-pinned state hash. A
/// client that opens with a dead engine link is the loud-failure case, not
/// a warning — a silent failure here would mean the "the engine runs
/// in-process" claim is untested every time the game actually launches.
fn log_engine_link() {
    let report = engine_link::engine_link_probe()
        .unwrap_or_else(|e| panic!("engine link probe failed at startup: {e}"));
    info!(
        "engine link: post-tick state hash {}",
        babylon_tick::hex(&report.after)
    );
}
