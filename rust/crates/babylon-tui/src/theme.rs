//! KSBC role colors for the Rust client (DESIGN_BIBLE §9b).
//!
//! The single source of truth is Python's
//! `babylon/render/tiers.py::TRUECOLOR_PALETTE`; these constants mirror it
//! for the FFI side, and the cross-language parity guard
//! `tests/unit/render/test_rust_theme_parity.py` parses THIS file's
//! `Color::Rgb(r, g, b)` literals against the Python palette — keep each
//! constant on one line so the guard's regex stays trivial.

use ratatui::style::Color;

/// Accent crimson (`#dc143c`): absence markers, redlinks, plate borders.
pub const CRIMSON: Color = Color::Rgb(220, 20, 60);
/// Accent gold (`#ffd700`): titles, known wikilinks.
pub const GOLD: Color = Color::Rgb(255, 215, 0);
/// Body text (`#e8e8e8`).
pub const BONE: Color = Color::Rgb(232, 232, 232);
/// Secondary/dim labels (`#404040`).
pub const DIM: Color = Color::Rgb(64, 64, 64);
/// Recessed panel fill (`#202020`): code-band backgrounds.
pub const MUTED_DARK: Color = Color::Rgb(32, 32, 32);
/// Structural blue (`#4169e1`): horizontal rules, note alerts.
pub const ROYAL: Color = Color::Rgb(65, 105, 225);
/// Grounded green (`#228b22`): tip alerts.
pub const GREEN_DARK: Color = Color::Rgb(34, 139, 34);
