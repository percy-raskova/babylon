//! The tutorial overlay: a top strip presenting the host's own
//! Patches-guided `WAYNE_OPENING_ARC` progress (plan Task 27, contract
//! `docs/superpowers/specs/2026-07-27-m3-tutorial-contracts.md` §1).
//!
//! [`TutorialOverlayView`] is a pure renderer over
//! [`crate::host::Host::tutorial_state_json`]'s payload — the HOST is the
//! sole arming authority (`{"active": false}` renders nothing; there is no
//! client-side heuristic for "should the tutorial be showing"). The
//! integrator (`app.rs`) owns the poll cadence (pre-fetched outside
//! `terminal.draw()`, the `peek_json` idiom), the `tutorial_enabled` /
//! `chrome.is_some()` seam-crossing savers, and the `Esc`-dismiss session
//! flag — this module only parses one payload and paints one strip.
//!
//! **Two never-conflated failure/absence states** (Constitution III.11):
//! `{"active": false}` is the honest absence — [`TutorialOverlayView`]
//! renders NOTHING for it, distinct from a malformed payload, which sets
//! [`TutorialOverlayView::parse_failed`] and renders the loud CRIMSON
//! `▌ tutorial UNREADABLE — malformed host data` strip instead.
//!
//! **Rendering never reassembles prose** (the U1/M3 no-duplication
//! contract, contract §0): `heading`/`body`/`patches` cross the wire fully
//! assembled by the host; this module paints them verbatim, in three fixed
//! roles — heading GOLD bold, `Patches: {line}` in `AMBER` (present only
//! on a non-finished step; the finished payload's `patches` is `null`),
//! body lines BONE. The finished state's two strings render through the
//! same path (contract §1: "Finished state renders its two strings the
//! same way") — it just happens to carry no `patches` line.
//!
//! **Layout**: a TOP STRIP over the play area (the Textual overlay is
//! `dock: top`, `max-height: 40%` — `tutorial_overlay.py:157-167` — NOT a
//! centered popup; **RECORDED DEVIATION**: the plan's `tui-popup` sketch is
//! superseded — `tui-popup` is absent from `Cargo.lock`, so an offline
//! build cannot fetch it, and the Textual original is a top dock anyway).
//! `min(content, 40% of area)` a bordered `Block` titled `"Tutorial"`, full
//! width — hand-rolled per the two existing overlay precedents
//! (`palette.rs`'s centered box, `app.rs`'s peek overlay), neither of which
//! is itself a top-docked strip.
//!
//! **R1 fix (verify-panel blocker): reserve, never overlay.** The strip
//! used to `Clear` + paint itself OVER whatever the integrator had already
//! drawn — swallowing chrome underneath and letting clicks reach entities
//! the strip visually covered (the wiki laid out its link-hit rects against
//! the FULL area, unaware the strip would sit on top of the first several
//! rows). [`TutorialOverlayView::height_for`] now lets the integrator
//! (`app.rs`) size a dedicated band FIRST — Textual dock semantics (reserve,
//! push down) — and split the frame area into `(strip band, remainder)`
//! BEFORE laying out anything else; [`TutorialOverlayView::render`] then
//! draws into exactly the rect it is given, no `Clear`, no internal height
//! computation — the band is exclusively its own.
//!
//! **Z-order** (contract §1): the strip is a reserved band, not an overlay,
//! so only the palette and peek remain layered on top of the base view —
//! the integrator's concern, not this module's; [`TutorialOverlayView`]
//! only knows how to paint itself into whatever `area` it's handed.

use ratatui::layout::Rect;
use ratatui::style::{Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Paragraph, Wrap};
use ratatui::Frame;
use serde::Deserialize;
use serde_json::Value;
use unicode_width::UnicodeWidthStr;

use crate::theme::{BONE, CRIMSON, GOLD};
// Reserved for Patches' dialogue line (the golden-fur register of the ksbc
// palette; `tui/theme.py:71-74`'s `AMBER`, "Reserved for the autopause
// indicator... NOT a §9b role token"). Declared in `chronicle.rs`, not
// `theme.rs` — the cross-language parity guard
// (`tests/unit/render/test_rust_theme_parity.py`) parses every
// `Color::Rgb` literal in `theme.rs` against the Python §9b palette and
// would fail on a constant with no §9b counterpart — this module reuses
// `chronicle`'s `pub(crate)` constant (same value, same citation) rather
// than adding a second copy.
use crate::views::chronicle::AMBER;

/// The strip's bordered title (contract §1).
const TITLE: &str = "Tutorial";

/// The strip's height ceiling as a percentage of the play area (contract
/// §1, porting the Textual overlay's own `max-height: 40%`,
/// `tutorial_overlay.py:157-167`).
const MAX_HEIGHT_PERCENT: u32 = 40;

/// The loud parse-failure line — NEVER conflated with the inactive state
/// (Constitution III.11).
const UNREADABLE_TEXT: &str = "▌ tutorial UNREADABLE — malformed host data";

/// The wire shape of an ACTIVE `tutorial_state_json` payload (contract §1),
/// deserialized only once `"active"` has already been read `true` off the
/// raw JSON — see [`TutorialOverlayView::update_from_json`]. `step_id` and
/// `patches` are the two fields the finished payload nulls out; every
/// other field is present on both the active-step and finished shapes.
#[derive(Debug, Deserialize)]
struct ActiveTutorialPayload {
    finished: bool,
    step_index: u64,
    total: u64,
    step_id: Option<String>,
    heading: String,
    /// `null` on the finished step (contract §1); `Some` on every real
    /// step (Patches never skips a beat).
    patches: Option<String>,
    body: String,
}

/// The tutorial overlay's parsed state. Fields mirror
/// [`crate::host::Host::tutorial_state_json`]'s active-payload shape
/// verbatim; [`Self::parse_failed`] is never on the wire — it is set only
/// by a failed [`Self::update_from_json`] call, mirroring `app.rs`'s
/// `PacingSnapshot::unreadable` pattern (a parse failure is a loud
/// first-class state, never a fabricated `active: false`).
#[derive(Debug, Default)]
pub struct TutorialOverlayView {
    /// Whether a tutorial is armed for this session (host-decided; the
    /// client has no arming heuristic of its own).
    pub active: bool,
    /// Whether the arc has completed (the two-string finished state).
    pub finished: bool,
    /// The current step's 0-based index (meaningless while `!active`).
    pub step_index: u64,
    /// The arc's total step count (meaningless while `!active`).
    pub total: u64,
    /// The current step's id, or `None` in the finished state.
    pub step_id: Option<String>,
    /// The rendered heading line (`"Step {n}/{total}: ..."`, or the
    /// finished headline) — host-assembled, never reconstructed here.
    pub heading: String,
    /// Patches' dialogue line for this step, or `None` on the finished
    /// step.
    pub patches: Option<String>,
    /// The rendered GIVEN/WHEN/THEN body (or the finished dismiss prompt).
    pub body: String,
    /// `true` when the last [`Self::update_from_json`] payload failed to
    /// parse — rendered loudly, never conflated with `active: false`.
    pub parse_failed: bool,
}

impl TutorialOverlayView {
    /// A fresh, inactive view (renders nothing) — before any host payload
    /// has arrived.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Absorb a fresh `tutorial_state_json` payload, replacing state
    /// wholesale.
    ///
    /// `{"active": false}` resets to the honest-absence default. A
    /// well-formed active payload (every field present; `step_id`/
    /// `patches` nullable) replaces every field. Anything else — bad JSON,
    /// a missing `"active"` key, or an active payload missing a required
    /// field — opens the loud [`Self::parse_failed`] state rather than
    /// keeping stale content next to nothing, or silently defaulting to
    /// inactive (Constitution III.11).
    pub fn update_from_json(&mut self, payload: &str) {
        let parsed: Value = match serde_json::from_str(payload) {
            Ok(value) => value,
            Err(_) => return self.mark_unreadable(),
        };
        let Some(active) = parsed.get("active").and_then(Value::as_bool) else {
            return self.mark_unreadable();
        };
        if !active {
            *self = Self::default();
            return;
        }
        match serde_json::from_value::<ActiveTutorialPayload>(parsed) {
            Ok(step) => {
                self.active = true;
                self.finished = step.finished;
                self.step_index = step.step_index;
                self.total = step.total;
                self.step_id = step.step_id;
                self.heading = step.heading;
                self.patches = step.patches;
                self.body = step.body;
                self.parse_failed = false;
            }
            Err(_) => self.mark_unreadable(),
        }
    }

    /// Open the loud parse-failure state — resets every other field to its
    /// default so a stale step never renders alongside the UNREADABLE
    /// banner.
    fn mark_unreadable(&mut self) {
        *self = Self::default();
        self.parse_failed = true;
    }

    /// The strip's content lines, tagged with the role that decides their
    /// style — the single source [`Self::content_lines`] (the styled
    /// render) and [`Self::height_for`] (the plain-text wrap count) both
    /// build from, so the two can never drift apart from each other.
    ///
    /// The loud UNREADABLE line stands alone when [`Self::parse_failed`];
    /// otherwise: the heading, `Patches: {line}` only when
    /// [`Self::patches`] is `Some` (absent on the finished step), then
    /// every body line. Shared by the active and finished states, which
    /// differ only in whether `patches` is present (contract §1).
    fn strip_lines(&self) -> Vec<(StripLineRole, String)> {
        if self.parse_failed {
            return vec![(StripLineRole::Unreadable, UNREADABLE_TEXT.to_string())];
        }
        let mut lines = vec![(StripLineRole::Heading, self.heading.clone())];
        if let Some(patches) = &self.patches {
            lines.push((StripLineRole::Patches, format!("Patches: {patches}")));
        }
        for body_line in self.body.split('\n') {
            lines.push((StripLineRole::Body, body_line.to_string()));
        }
        lines
    }

    /// [`Self::strip_lines`] styled per role: heading GOLD bold, Patches
    /// AMBER, body BONE, the loud UNREADABLE line bold CRIMSON.
    fn content_lines(&self) -> Vec<Line<'static>> {
        self.strip_lines()
            .into_iter()
            .map(|(role, text)| {
                let style = match role {
                    StripLineRole::Heading => Style::new().fg(GOLD).add_modifier(Modifier::BOLD),
                    StripLineRole::Patches => Style::new().fg(AMBER),
                    StripLineRole::Body => Style::new().fg(BONE),
                    StripLineRole::Unreadable => {
                        Style::new().fg(CRIMSON).add_modifier(Modifier::BOLD)
                    }
                };
                Line::from(Span::styled(text, style))
            })
            .collect()
    }

    /// The strip's height for a `width`-wide band inside a `total_height`
    /// play area (R1: the integrator sizes the band BEFORE laying out
    /// anything else, never after): the wrapped content row count — word
    /// wrap on the SAME `width` [`Self::render`]'s `Wrap { trim: false }`
    /// uses, less the 2 border columns, computed via
    /// `wrapped_row_count` (ratatui 0.30 gates its own
    /// `Paragraph::line_count` `pub(crate)` behind the
    /// `unstable-rendered-line-info` feature this crate does not enable,
    /// so this crate computes the wrapped count locally instead) — plus
    /// the 2 border rows, clamped to 40% of `total_height` (contract §1's
    /// `max-height: 40%` port) and never exceeding `total_height` itself.
    /// Returns `0` while the strip would render nothing (`!active &&
    /// !parse_failed`) — the integrator's cue to reserve no band at all.
    #[must_use]
    pub fn height_for(&self, width: u16, total_height: u16) -> u16 {
        if !self.active && !self.parse_failed {
            return 0;
        }
        let inner_width = width.saturating_sub(2).max(1);
        let content_rows: usize = self
            .strip_lines()
            .iter()
            .map(|(_, text)| wrapped_row_count(text, inner_width))
            .sum();
        let content_height = (content_rows as u16).saturating_add(2);
        let max_height = ((u32::from(total_height) * MAX_HEIGHT_PERCENT) / 100) as u16;
        content_height
            .min(max_height.max(1))
            .min(total_height.max(1))
            .max(1)
    }

    /// Render the strip into EXACTLY `area` of `frame`: NOTHING while
    /// `!active && !parse_failed` (the honest-absence state — the host is
    /// the sole arming authority, and the integrator is expected to skip
    /// calling this at all once dismissed, but a stray call is still
    /// harmless here); the loud UNREADABLE strip on a parse failure;
    /// otherwise the heading/Patches/body lines, active or finished alike,
    /// word-wrapped to `area`'s width (`Wrap { trim: false }` — R3 fix: an
    /// un-wrapped `Paragraph` silently clips whatever falls past the pane
    /// edge, which had been quietly dropping the tail of every heading and
    /// Patches line wider than the play area).
    ///
    /// R1 fix: no internal height computation, no `Clear` — the caller
    /// (`app.rs`) sizes `area` via [`Self::height_for`] first and this strip
    /// is the band's exclusive occupant, never an overlay atop something
    /// else.
    pub fn render(&self, frame: &mut Frame<'_>, area: Rect) {
        if !self.active && !self.parse_failed {
            return;
        }
        let lines = self.content_lines();
        let block = Block::bordered().title(TITLE);
        let inner = block.inner(area);
        frame.render_widget(block, area);
        frame.render_widget(Paragraph::new(lines).wrap(Wrap { trim: false }), inner);
    }
}

/// The style role of one [`TutorialOverlayView::strip_lines`] entry.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum StripLineRole {
    /// GOLD bold.
    Heading,
    /// AMBER.
    Patches,
    /// BONE.
    Body,
    /// Bold CRIMSON — the loud parse-failure line.
    Unreadable,
}

/// The number of terminal rows `text` occupies once greedily word-wrapped
/// to `width` columns (each word measured via [`UnicodeWidthStr`]) —
/// mirrors ratatui's own `WordWrapper` (`Wrap { trim: false }`) closely
/// enough for this crate's prose: plain English sentences, single spaces
/// between words, no exotic multi-space runs or wide/combining glyphs. A
/// single word wider than `width` alone (no natural break point) is placed
/// on its own row rather than hard-split at the column edge — a known,
/// documented simplification that never arises in this crate's actual
/// heading/Patches/body text.
fn wrapped_row_count(text: &str, width: u16) -> usize {
    let width = usize::from(width.max(1));
    let mut rows = 0usize;
    // Bounded by `text`'s own line count — a fixed, finite input.
    for line in text.split('\n') {
        if line.is_empty() {
            rows += 1;
            continue;
        }
        let mut current_width: Option<usize> = None;
        // Bounded by the line's own word count — each iteration consumes
        // exactly one word.
        for word in line.split(' ') {
            let word_width = word.width();
            current_width = Some(match current_width {
                None => word_width,
                Some(w) if w + 1 + word_width <= width => w + 1 + word_width,
                Some(_) => {
                    rows += 1;
                    word_width
                }
            });
        }
        rows += 1; // the last (or only) row on this logical line
    }
    rows.max(1)
}

#[cfg(test)]
mod tests {
    use super::*;

    const ACTIVE_STEP: &str = r#"{"active": true, "finished": false, "step_index": 3,
        "total": 22, "step_id": "run_until_autopause",
        "heading": "Step 4/22: Given the campaign is bound, when the player presses 'r', then the driver runs until autopause.",
        "patches": "Now let the weeks roll — the engine stops us the instant something critical fires.",
        "body": "GIVEN: the campaign is bound\nWHEN: the player presses 'r'\nTHEN: the driver runs until autopause"}"#;

    const FINISHED: &str = r#"{"active": true, "finished": true, "step_index": 22,
        "total": 22, "step_id": null, "heading": "Opening arc complete.",
        "patches": null, "body": "Press Escape to dismiss this tutorial."}"#;

    #[test]
    fn a_fresh_view_is_inactive() {
        let view = TutorialOverlayView::new();
        assert!(!view.active);
        assert!(!view.parse_failed);
    }

    #[test]
    fn an_active_step_parses_every_field() {
        let mut view = TutorialOverlayView::new();
        view.update_from_json(ACTIVE_STEP);
        assert!(view.active);
        assert!(!view.finished);
        assert_eq!(view.step_index, 3);
        assert_eq!(view.total, 22);
        assert_eq!(view.step_id.as_deref(), Some("run_until_autopause"));
        assert_eq!(
            view.patches.as_deref(),
            Some("Now let the weeks roll — the engine stops us the instant something critical fires.")
        );
        assert!(!view.parse_failed);
    }

    #[test]
    fn inactive_payload_resets_to_the_default() {
        let mut view = TutorialOverlayView::new();
        view.update_from_json(ACTIVE_STEP);
        assert!(view.active);
        view.update_from_json(r#"{"active": false}"#);
        assert!(!view.active);
        assert!(!view.parse_failed);
        assert_eq!(view.heading, "");
    }

    #[test]
    fn the_finished_state_carries_a_null_step_id_and_patches() {
        let mut view = TutorialOverlayView::new();
        view.update_from_json(FINISHED);
        assert!(view.active);
        assert!(view.finished);
        assert!(view.step_id.is_none());
        assert!(view.patches.is_none());
        assert_eq!(view.heading, "Opening arc complete.");
        assert_eq!(view.body, "Press Escape to dismiss this tutorial.");
    }

    #[test]
    fn malformed_json_opens_parse_failed_never_inactive() {
        let mut view = TutorialOverlayView::new();
        view.update_from_json(ACTIVE_STEP);
        view.update_from_json("not json");
        assert!(view.parse_failed);
        assert!(!view.active);
    }

    #[test]
    fn an_active_payload_missing_a_required_field_is_parse_failed() {
        let mut view = TutorialOverlayView::new();
        view.update_from_json(r#"{"active": true, "finished": false}"#);
        assert!(view.parse_failed);
        assert!(!view.active);
    }

    #[test]
    fn a_payload_missing_the_active_key_is_parse_failed() {
        let mut view = TutorialOverlayView::new();
        view.update_from_json(r#"{"finished": false}"#);
        assert!(view.parse_failed);
    }
}
