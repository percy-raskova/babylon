//! The scene's frame time, timed as the client's own `frame_perf` line is: 300 intervals
//! after two seconds of settling, taken while the primary window has focus.

use super::frame::ParticleMode;
use super::scene::SceneRunner;
use bevy::prelude::*;
use bevy::window::PrimaryWindow;
use hypergraph_rs_bevy::{FrameWindows, WindowStats};
use serde::Serialize;
use std::time::Duration;

/// Intervals in one window, as the client's `SAMPLE_COUNT`.
pub const SAMPLE_WINDOW: usize = 300;
/// Seconds of settling before the first window, as the client's `SETTLE_SECONDS`.
pub const SETTLE: Duration = Duration::from_secs(2);

/// The figures of one full window, in milliseconds.
#[derive(Serialize, Clone, Copy, Debug, PartialEq)]
pub struct FrameTime {
    pub median_ms: f64,
    pub p95_ms: f64,
    pub window: usize,
}

/// The intervals so far and the last window's figures.
#[derive(Resource)]
pub struct SceneFrameTimes {
    windows: FrameWindows,
    pub last: Option<FrameTime>,
}

impl Default for SceneFrameTimes {
    fn default() -> Self {
        Self {
            windows: FrameWindows::new(SAMPLE_WINDOW, SETTLE),
            last: None,
        }
    }
}

/// A window's figures in milliseconds.
#[must_use]
pub fn frame_time(stats: &WindowStats) -> FrameTime {
    FrameTime {
        median_ms: stats.median.as_secs_f64() * 1_000.0,
        p95_ms: stats.p95.as_secs_f64() * 1_000.0,
        window: SAMPLE_WINDOW,
    }
}

/// The word the log line gives for how particles are drawn.
const fn mode_word(mode: ParticleMode) -> &'static str {
    match mode {
        ParticleMode::Groups => "groups",
        ParticleMode::People => "people",
    }
}

/// Push each frame's real interval while the primary window has focus; a full window is logged
/// to the client's file and kept.
pub fn time_frames(
    time: Res<Time<Real>>,
    windows: Query<&Window, With<PrimaryWindow>>,
    scene: Res<SceneRunner>,
    mut times: ResMut<SceneFrameTimes>,
) {
    if !windows.single().is_ok_and(|window| window.focused) {
        return;
    }
    let Some(stats) = times.windows.push(time.delta()) else {
        return;
    };
    let figures = frame_time(&stats);
    log::info!(
        "frame_perf view=small_world mode={} period={} median_ms={:.3} p95_ms={:.3}",
        mode_word(scene.mode),
        scene.shown.unwrap_or(0),
        figures.median_ms,
        figures.p95_ms,
    );
    times.last = Some(figures);
}
