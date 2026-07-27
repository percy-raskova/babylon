//! The endgame HUD strip: a persistent top-of-screen status band (plan
//! Task 24, contract `docs/superpowers/specs/2026-07-27-m2-seam-contracts.md`
//! §4, §1).
//!
//! Ports the *display* semantics of `dashboard_view.py::render_hud_text`
//! (Program 24 P4) over the M2 wire shapes the contract pins:
//!
//! - **Line 1** — `T+{tick}/{horizon_tick}` (mirrors `render_hud_text`'s
//!   `counter`), appended with the recognized pattern's full label and
//!   since-tick in bold CRIMSON when one is held. `tick` itself never
//!   crosses on [`crate::host::Host::endgame_status_json`] — that payload
//!   carries only the fixed `horizon_tick` — so the integrator threads it
//!   in separately via [`HudStrip::set_tick`] on every post-tick refresh
//!   (contract §6).
//! - **Line 2** — the five endgame axis gauges, keyed by the FIXED
//!   `AXIS_KEYS` order (mirrors `dashboard_view.py:36-42`'s
//!   `_AXIS_ORDER`, itself citing `endgame_detector.py:71-77`'s own
//!   `axis_progress()` key order) — NEVER the `axes` JSON object's own
//!   iteration order (contract §4).
//! - **Line 3** — the PACING state (contract §1; mirrors
//!   `dashboard_view.py:154-163`'s branch order and wording verbatim).
//!
//! Two host feeds cross the wire independently
//! ([`HudStrip::update_endgame`] from `endgame_status_json`,
//! [`HudStrip::update_pacing`] from `pacing_state_json`) and each owns its
//! own honest-absence / loud-failure reading (Constitution III.11), never
//! conflated:
//!
//! - `endgame_status_json`'s `"null"` is the ONLY pre-bind absence (no
//!   campaign chosen yet) and collapses the whole strip to one honest
//!   line — a bound tick-0 all-zero-axes payload is a REAL status and
//!   renders five empty bars, never the absence line (contract §4).
//! - A payload that fails to parse opens the loud, distinct `UNREADABLE`
//!   reading. For `endgame_status_json` this collapses the whole strip
//!   (mirrors `WatchlistView`/`LobbyView`'s own parse-failure
//!   short-circuit — with no readable horizon there is nothing sensible to
//!   draw a counter or bars from); for `pacing_state_json` it is isolated
//!   to line 3 only, since a malformed pacing payload says nothing about
//!   whether the endgame feed is fine.
//!
//! [`HudStrip`] keeps its parsed state private (unlike the M1 views this
//! mirrors, which expose their rows/selection as `pub` fields for direct
//! inspection): M1 views are one-shot value bags reopened fresh from a
//! single JSON pull, while this strip accumulates two independently
//! updated feeds across the campaign's lifetime, so its internal
//! bookkeeping (which of the three readings above is current) is not
//! itself useful public API — only the rendered output is.

use std::collections::HashMap;

use ratatui::layout::Rect;
use ratatui::style::{Modifier, Style};
use ratatui::text::{Line, Span, Text};
use ratatui::widgets::Paragraph;
use ratatui::Frame;
use serde::Deserialize;
use serde_json::Value;

use crate::theme::{BONE, CRIMSON, DIM, GOLD};

use crate::views::chronicle::AMBER;

/// One gauge's width in glyphs — 8, not the contract's illustrative 10:
/// five `"{ABBR} [########] "` units must fit an 80-column terminal
/// (5 × 15 = 75 ≤ 80; at width 10 the fifth gauge clipped mid-bar, making
/// a full bar indistinguishable from 7/10 — the verify panel's finding).
const BAR_WIDTH: usize = 8;

/// The five recognized endgame patterns, contract-fixed order (mirrors
/// `endgame_detector.py:71-77`'s own `axis_progress()` key order, re-cited
/// by `dashboard_view.py:36-42`'s `_AXIS_ORDER`): `(id, full label,
/// abbreviated label)`. `id` is both the `axes` JSON key and the
/// `pattern` string value; the full label feeds line 1's pattern suffix
/// ([`pattern_label`]); the 3-glyph abbreviation keeps line 2's five
/// gauges inside an 80-column strip.
///
/// Indexed by THIS array, never by iterating the `axes` JSON object — a
/// missing key reads honest `0.0` ([`axis_value`]), never a KeyError,
/// never a different display order (contract §4).
const AXIS_KEYS: [(&str, &str, &str); 5] = [
    ("revolutionary_victory", "REVOLUTIONARY VICTORY", "REV"),
    ("ecological_collapse", "ECOLOGICAL COLLAPSE", "ECO"),
    ("fascist_consolidation", "FASCIST CONSOLIDATION", "FAS"),
    ("red_ogv", "RED OGV", "OGV"),
    ("fragmented_collapse", "FRAGMENTED COLLAPSE", "FRG"),
];

/// The honest pre-bind absence line — the ONLY reading for
/// `endgame_status_json`'s `"null"` (contract §4; never used for a bound
/// tick-0 all-zero payload, which is real data and renders five empty
/// bars instead).
const HUD_ABSENT_TEXT: &str = "hud: no campaign bound";

/// The loud, distinct parse-failure line for `endgame_status_json`
/// (mirrors `WatchlistView`/`LobbyView`'s own `"... UNREADABLE —
/// malformed host data"` wording).
const HUD_UNREADABLE_TEXT: &str = "▌ hud UNREADABLE — malformed host data";

/// The loud, distinct parse-failure line for `pacing_state_json` —
/// isolated to line 3 (see the module docs) rather than blanking the
/// whole strip.
const PACING_UNREADABLE_TEXT: &str = "PACING: UNREADABLE — malformed host data";

/// `EndgameStatus.model_dump_json()`'s pinned shape (contract §4;
/// `projection/endgame.py:34-57`), narrowed to the fields this strip
/// actually renders. `outcome`/`game_over`/`locked` are real fields on the
/// wire that no M2 HUD line reads yet; serde's default (no
/// `deny_unknown_fields`) ignores them harmlessly rather than this struct
/// carrying a dead placeholder for each.
#[derive(Deserialize)]
struct EndgameStatus {
    /// The currently recognized pattern's id (one of [`AXIS_KEYS`]'s
    /// five), or `None` — looked up through [`pattern_label`] for line 1's
    /// suffix, never rendered as the raw id.
    pattern: Option<String>,
    /// The fixed campaign horizon tick — line 1's counter denominator.
    horizon_tick: u64,
    /// The tick `pattern` was first recognized; `None` when no pattern is
    /// held. Only meaningful alongside a non-`None` `pattern` (contract
    /// §4: a matched-but-not-held axis has no tracked since-tick of its
    /// own).
    since_tick: Option<u64>,
    /// The detector's per-axis progress payload, verbatim — read ONLY
    /// through [`axis_value`], keyed by [`AXIS_KEYS`], never iterated
    /// directly (contract §4).
    axes: HashMap<String, Value>,
}

/// `pacing_state_json`'s pinned shape (contract §1; mirrors
/// `PacedDriverHandle`, `tui/app.py:525-582`).
#[derive(Deserialize)]
struct PacingState {
    /// `false` when no campaign/driver is bound — all other fields are
    /// false/`None` in that case (the host trait's own documented default,
    /// `host.rs::Host::pacing_state_json`).
    attached: bool,
    /// Whether the paced driver is locked (a held endgame pattern past its
    /// lock window).
    locked: bool,
    /// The human-readable reason for `locked`, when `locked` is true.
    lock_reason: Option<String>,
    /// Whether a completed run is awaiting player acknowledgement.
    awaiting_ack: bool,
    /// A short summary of the pending autopause, when `awaiting_ack` is
    /// true.
    pause_summary: Option<String>,
    /// Whether a `run_until_paused` batch is already in flight.
    busy: bool,
}

impl PacingState {
    /// The state before any real `pacing_state_json` payload has arrived —
    /// identical to the host trait's own default encoding (`attached:
    /// false`, everything else false/`None`), so a fresh [`HudStrip`]
    /// renders the same "no paced driver attached" line the host itself
    /// would serve for an unbound session.
    fn unattached() -> Self {
        Self {
            attached: false,
            locked: false,
            lock_reason: None,
            awaiting_ack: false,
            pause_summary: None,
            busy: false,
        }
    }
}

/// The HUD's endgame reading: pre-bind absence, a loud parse failure, or a
/// bound (possibly all-zero) status. See the module docs for why absence
/// and failure are never conflated.
enum EndgameSlot {
    /// No campaign bound (`endgame_status_json` served JSON `null`).
    Absent,
    /// A malformed payload — loud, distinct from absence (III.11).
    Unreadable,
    /// A bound campaign's real status, possibly all-zero at tick 0.
    Bound(EndgameStatus),
}

/// The HUD's pacing reading: a loud parse failure, or a bound state. There
/// is no separate "absent" variant here — the host's own default payload
/// (`attached: false`) already encodes "no driver wired" as ordinary data
/// (see [`PacingState::unattached`]).
enum PacingSlot {
    /// A malformed payload — loud, distinct from the `attached: false`
    /// reading (III.11).
    Unreadable,
    /// A bound (possibly unattached) pacing state.
    Bound(PacingState),
}

/// The endgame HUD strip: a persistent 3-line top-of-screen band (plan
/// Task 24). See the module docs for the per-line contract and the
/// absence/failure reading each feed owns independently.
pub struct HudStrip {
    tick: u64,
    endgame: EndgameSlot,
    pacing: PacingSlot,
}

impl HudStrip {
    /// A fresh strip before any host payload has arrived: tick `0`, no
    /// campaign bound (the internal `EndgameSlot::Absent` reading), and
    /// the pacing feed's own honest unattached default
    /// (`PacingState::unattached`).
    #[must_use]
    pub fn new() -> Self {
        Self {
            tick: 0,
            endgame: EndgameSlot::Absent,
            pacing: PacingSlot::Bound(PacingState::unattached()),
        }
    }

    /// Set the campaign's current committed tick (line 1's counter
    /// numerator). The integrator calls this alongside
    /// [`Self::update_endgame`] on every post-tick refresh (contract §6) —
    /// `EndgameStatus` carries only the fixed `horizon_tick`, never the
    /// live tick itself.
    pub fn set_tick(&mut self, tick: u64) {
        self.tick = tick;
    }

    /// Absorb a fresh `endgame_status_json` payload (contract §4).
    ///
    /// `"null"` is the honest pre-bind absence — never conflated with a
    /// bound tick-0 all-zero-axes payload, which parses as a real
    /// (internal) `EndgameStatus` and renders five empty bars. Anything
    /// that fails to parse as either reading opens the loud, distinct
    /// `Unreadable` state (Constitution III.11) rather than silently
    /// defaulting to either honest one.
    pub fn update_endgame(&mut self, payload: &str) {
        self.endgame = match serde_json::from_str::<Option<EndgameStatus>>(payload) {
            Ok(None) => EndgameSlot::Absent,
            Ok(Some(status)) => EndgameSlot::Bound(status),
            Err(_) => EndgameSlot::Unreadable,
        };
    }

    /// Absorb a fresh `pacing_state_json` payload (contract §1). A payload
    /// that fails to parse the pinned shape opens the loud `Unreadable`
    /// pacing state, isolated to line 3 (see the module docs) — it says
    /// nothing about whether the endgame feed is readable.
    pub fn update_pacing(&mut self, payload: &str) {
        self.pacing = match serde_json::from_str::<PacingState>(payload) {
            Ok(state) => PacingSlot::Bound(state),
            Err(_) => PacingSlot::Unreadable,
        };
    }

    /// Render the strip into `area` of `frame`.
    ///
    /// Pre-bind absence or a parse failure on the endgame feed collapses
    /// the whole strip to one line (see the module docs); otherwise all
    /// three lines render, with line 3 reading its own independent
    /// (internal) pacing reading.
    pub fn render(&mut self, frame: &mut Frame, area: Rect) {
        match &self.endgame {
            EndgameSlot::Absent => {
                frame.render_widget(Paragraph::new(HUD_ABSENT_TEXT), area);
            }
            EndgameSlot::Unreadable => {
                let loud = Paragraph::new(HUD_UNREADABLE_TEXT)
                    .style(Style::new().fg(CRIMSON).add_modifier(Modifier::BOLD));
                frame.render_widget(loud, area);
            }
            EndgameSlot::Bound(status) => {
                let lines = vec![
                    tick_line(self.tick, status),
                    axis_line(&status.axes),
                    pacing_line(&self.pacing),
                ];
                frame.render_widget(Paragraph::new(Text::from(lines)), area);
            }
        }
    }
}

impl Default for HudStrip {
    fn default() -> Self {
        Self::new()
    }
}

/// Look up a recognized pattern id's full display label off [`AXIS_KEYS`],
/// or `None` when `pattern` is `None` or (defensively) doesn't match any
/// of the five recognized ids.
fn pattern_label(pattern: Option<&str>) -> Option<&'static str> {
    let id = pattern?;
    AXIS_KEYS
        .into_iter()
        .find(|entry| entry.0 == id)
        .map(|entry| entry.1)
}

/// Line 1: the `T+{tick}/{horizon_tick}` counter, plus the held pattern's
/// full label and since-tick in bold CRIMSON when one is recognized.
fn tick_line(tick: u64, status: &EndgameStatus) -> Line<'static> {
    let counter = format!("T+{tick}/{}", status.horizon_tick);
    match pattern_label(status.pattern.as_deref()) {
        None => Line::from(counter),
        Some(label) => {
            let since = status
                .since_tick
                .map_or_else(|| "?".to_string(), |t| t.to_string());
            Line::from(vec![
                Span::raw(counter),
                Span::styled(
                    format!(" — {label} since T{since}"),
                    Style::new().fg(CRIMSON).add_modifier(Modifier::BOLD),
                ),
            ])
        }
    }
}

/// Read one axis's progress off `EndgameStatus.axes`, honestly `0.0` when
/// the key is absent or its value isn't numeric (mirrors
/// `dashboard_view.py::_axis_value`, `dashboard_view.py:67-79`).
fn axis_value(axes: &HashMap<String, Value>, key: &str) -> f64 {
    axes.get(key).and_then(Value::as_f64).unwrap_or(0.0)
}

/// The filled/empty glyph counts for one [`BAR_WIDTH`]-cell bar, clamping
/// `progress` defensively to `[0.0, 1.0]` before rounding — this renderer
/// never trusts an upstream invariant it cannot itself verify (the same
/// discipline `dashboard_view.py::_bar` documents for its own clamp).
fn bar_glyphs(progress: f64) -> (usize, usize) {
    let clamped = progress.clamp(0.0, 1.0);
    let filled = (clamped * BAR_WIDTH as f64).round() as usize;
    (filled, BAR_WIDTH - filled)
}

/// Line 2: the five endgame axis gauges, keyed by the fixed [`AXIS_KEYS`]
/// order. An axis at progress `>= 1.0` is DERIVED-triggered (the
/// detector's own documented invariant, contract §4) and renders bold
/// CRIMSON end-to-end; otherwise GOLD fill on DIM empty.
fn axis_line(axes: &HashMap<String, Value>) -> Line<'static> {
    let mut spans: Vec<Span<'static>> = Vec::new();
    for (key, _full_label, abbrev) in AXIS_KEYS {
        let progress = axis_value(axes, key);
        let (filled, empty) = bar_glyphs(progress);
        spans.push(Span::raw(format!("{abbrev} [")));
        if progress >= 1.0 {
            let triggered = Style::new().fg(CRIMSON).add_modifier(Modifier::BOLD);
            spans.push(Span::styled("█".repeat(filled), triggered));
            spans.push(Span::styled("-".repeat(empty), triggered));
        } else {
            spans.push(Span::styled("█".repeat(filled), Style::new().fg(GOLD)));
            spans.push(Span::styled("-".repeat(empty), Style::new().fg(DIM)));
        }
        spans.push(Span::raw("] "));
    }
    Line::from(spans)
}

/// Line 3: the PACING state (contract §1, mirroring
/// `dashboard_view.py:154-163`'s branch order and wording verbatim).
fn pacing_line(slot: &PacingSlot) -> Line<'static> {
    match slot {
        PacingSlot::Unreadable => Line::from(Span::styled(
            PACING_UNREADABLE_TEXT,
            Style::new().fg(CRIMSON).add_modifier(Modifier::BOLD),
        )),
        PacingSlot::Bound(state) => {
            if !state.attached {
                Line::from("PACING: no paced driver attached")
            } else if state.locked {
                let reason = state.lock_reason.as_deref().unwrap_or("(no reason given)");
                Line::from(Span::styled(
                    format!("PACING: LOCKED — {reason}"),
                    Style::new().fg(CRIMSON).add_modifier(Modifier::BOLD),
                ))
            } else if state.awaiting_ack {
                let summary = state.pause_summary.as_deref().unwrap_or("(no summary)");
                Line::from(Span::styled(
                    format!("PACING: autopause pending ({summary}) — press 'a' to acknowledge"),
                    Style::new().fg(AMBER),
                ))
            } else if state.busy {
                Line::from("PACING: a run is already in progress")
            } else {
                Line::from(Span::styled("PACING: ready", Style::new().fg(BONE)))
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn axis_value_reads_a_present_key() {
        let mut axes = HashMap::new();
        axes.insert("revolutionary_victory".to_string(), Value::from(0.5));
        assert_eq!(axis_value(&axes, "revolutionary_victory"), 0.5);
    }

    #[test]
    fn axis_value_defaults_a_missing_key_to_zero() {
        let axes: HashMap<String, Value> = HashMap::new();
        assert_eq!(axis_value(&axes, "fragmented_collapse"), 0.0);
    }

    #[test]
    fn axis_value_defaults_a_non_numeric_value_to_zero() {
        let mut axes = HashMap::new();
        axes.insert("red_ogv".to_string(), Value::from("not a number"));
        assert_eq!(axis_value(&axes, "red_ogv"), 0.0);
    }

    #[test]
    fn bar_glyphs_rounds_to_the_nearest_cell() {
        assert_eq!(bar_glyphs(0.42), (3, 5));
        assert_eq!(bar_glyphs(0.0), (0, 8));
        assert_eq!(bar_glyphs(1.0), (8, 0));
    }

    #[test]
    fn bar_glyphs_clamps_an_out_of_range_progress() {
        assert_eq!(bar_glyphs(-0.5), (0, 8));
        assert_eq!(bar_glyphs(1.5), (8, 0));
    }

    #[test]
    fn pattern_label_looks_up_a_recognized_id() {
        assert_eq!(pattern_label(Some("red_ogv")), Some("RED OGV"));
    }

    #[test]
    fn pattern_label_is_none_for_no_pattern() {
        assert_eq!(pattern_label(None), None);
    }
}
