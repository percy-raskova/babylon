//! Presentation color constants for the county map that live outside the
//! §9b role palette (`crate::palette`).
//!
//! **F4 fix (adversarial verification of PR #490).** The first cut
//! declared `PANEL` as a private `const` inline in `map/mesh.rs`. That
//! bypassed `tests/unit/render/test_rust_theme_parity.py`'s §9b parity
//! guard, which reads only `palette.rs` — not a false pass on `PANEL`
//! itself (`PANEL` is deliberately not a §9b token, so the guard was never
//! supposed to claim it), but a genuine gap: nothing watched for a STRAY
//! `Color::srgb_u8`/`Color::srgb` literal added to any OTHER file in this
//! crate. Two things close that gap: (1) `PANEL` now lives here, in the
//! file the B1 plan's Task 9 (Phase C, out of scope for this PR) is
//! specced to create and extend with the four-band diverging tension
//! channel (`pub fn band_color`, `pub const PANEL`) — so Task 9 finds one
//! existing declaration to extend, not a second one to reconcile; (2) the
//! parity guard itself grew a crate-wide sweep
//! (`test_no_stray_color_literals_outside_palette_or_a_declared_exemption`)
//! that fails on any `Color::srgb[_u8]` call outside `palette.rs` unless
//! its file is named in the guard's own `_SWEEP_EXEMPTIONS` registry with
//! a reason — `map/bands.rs` (this file) is that registry's first entry.

use bevy::color::Color;

/// `PANEL` is not a §9b token — the deleted Ratatui client declared
/// `PANEL = Rgb(32, 4, 4)` (`#200404`) locally, with a comment recording
/// that it deliberately misses `MUTED_DARK`. It is the map's "no honest
/// data this tick" absence fill: B1 Task 6 starts every fill vertex here
/// (the map opens honestly empty, no lens data has arrived yet), and
/// Phase C's four-band lens (Task 9) resolves an absent `w` to this same
/// color.
pub const PANEL: Color = Color::srgb_u8(32, 4, 4);
