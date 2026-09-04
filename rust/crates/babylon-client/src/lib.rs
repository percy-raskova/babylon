//! `babylon-client`'s library surface — the atlas, tessellate, map,
//! palette, engine-link, CLI, and headless-dossier modules that both the
//! binary (`main.rs`, a pure dispatch shim) and the integration tests
//! consume. The Bevy `App` construction lives in `app.rs`; this crate is
//! otherwise a thin scaffold, not a reusable client-engine API.

// Every Bevy system parameter (`Res<T>`, `ResMut<T>`, `Query<T>`,
// `Commands`, …) is, by Bevy's own `SystemParam` design, taken BY VALUE —
// `&Res<T>` does not implement `SystemParam` and would not compile as a
// system signature. `clippy::needless_pass_by_value` cannot see that
// constraint and flags every one of them (24 sites across
// `map/pick.rs`, `map/bands.rs`, `map/hud.rs`, `loop_ui.rs`, `map/mod.rs`
// as of Task 1's pedantic-debt fix pass) with a "take a reference instead"
// suggestion that would break the build if followed. This is the
// documented Bevy/clippy interaction, not a crate-specific judgment call —
// a crate-level allow is the correct fix precisely because the false
// positive is systemic to the ECS API shape, not confined to one file.
#![allow(clippy::needless_pass_by_value)]

pub mod app;
pub mod atlas;
pub mod cli;
pub mod coverage;
pub mod decision_surface;
pub mod dossier;
pub mod engine_link;
pub mod lens;
pub mod logging;
pub mod loop_ui;
pub mod map;
pub mod narration;
pub mod palette;
pub mod projection;
pub mod session_log;
pub mod severity;
pub mod story;
pub mod tessellate;
#[cfg(test)]
mod test_support;
pub mod ui;
pub mod visual_assets;
