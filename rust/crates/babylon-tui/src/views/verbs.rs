//! The verb plate: the nine Article V verbs, one bottom-of-screen plate
//! (plan Task 23).
//!
//! Ports the *display* shape of `babylon.tui.verb_plate::render_verb_plate`
//! over the wire shape `Host::verb_plate_view_json` serves (contract §3,
//! `docs/superpowers/specs/2026-07-27-m2-seam-contracts.md`):
//! `VerbPlateView.model_dump_json()` from
//! `babylon.projection.verbs.view_models`, or the literal string `"null"`
//! when no session/player org is bound.
//!
//! **Eligibility gates the row; affordability never hides one** (mirrors
//! `verb_plate.py`'s own contract): an ineligible verb still renders, with
//! its player-facing `reason`/`remedy` inline — never omitted; an
//! eligible-but-unaffordable verb still renders as legal, with the
//! `afford_note` riding along honestly rather than disabling the row.
//!
//! **Investigate's three sub-verbs surface faithfully, not collapsed**
//! (Constitution Article V): the plate renders `Investigate(Territory)`,
//! `Investigate(Org)`, `Investigate(Edge)` as three named lines, all three
//! sharing the ONE `investigate` row's eligibility/cost/preview signal and
//! F-key (mirrors `verb_plate.py:64-67,162-196` — the view-model does not
//! yet carry independent per-sub-verb signals).
//!
//! **F-keys are POSITIONAL over the fixed nine-verb canonical order**
//! (`CANONICAL_VERBS`, mirroring `preview.py::VERB_TO_ACTION_TYPE`'s own
//! dict order), not over the raw payload array index: a well-formed payload
//! ships all nine rows in that same order, so the two coincide, but a
//! caller-truncated payload (fewer than nine rows) is matched back onto the
//! canonical order **by verb name**, so a dropped verb always renders its
//! loud missing-marker line at ITS canonical F-key slot regardless of where
//! (or whether) the truncation happened to leave a gap in the array
//! (mirrors `verb_plate.py:134-144,177-196`'s own by-name `by_verb` lookup).
//!
//! **Malformed JSON is a distinct loud state, never conflated with
//! absence** (Constitution III.11): `"null"` opens the honest
//! "no verb plate — no campaign bound" absence state; anything else that
//! fails to parse as a `VerbPlateView` object opens the CRIMSON
//! `UNREADABLE` state instead. Dispatch (`F1`-`F9` -> `issue_verb`) is
//! integration wiring, not this module's concern — [`VerbPlateView::row`]
//! exists so the app shell's key handler can read a row's `eligible`/
//! `candidate_target_ids` for honest-target dispatch without touching JSON
//! itself.

use ratatui::layout::{Constraint, Direction, Layout, Rect};
use ratatui::style::{Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Paragraph};
use ratatui::Frame;
use serde::Deserialize;
use serde_json::Value;

use crate::theme::{BONE, CRIMSON, DIM};

/// The nine canonical Article V verbs, in plate/F-key order (mirrors
/// `preview.py::VERB_TO_ACTION_TYPE`'s own dict order). F-key `N` (1-indexed)
/// binds to this order's `N - 1`th verb.
const CANONICAL_VERBS: [&str; 9] = [
    "educate",
    "reproduce",
    "attack",
    "mobilize",
    "campaign",
    "aid",
    "investigate",
    "move",
    "negotiate",
];

/// Investigate's three named sub-verbs, in Constitution Article V's own
/// order (mirrors `verb_plate.py::INVESTIGATE_SUB_VERBS`).
const INVESTIGATE_SUB_VERBS: [&str; 3] = ["Territory", "Org", "Edge"];

/// The honest-absence line for `"null"` (no session / no player org bound).
const ABSENCE_TEXT: &str = "▌ no verb plate — no campaign bound";

/// The loud, distinct parse-failure line for a malformed payload — never
/// conflated with [`ABSENCE_TEXT`] (Constitution III.11).
const UNREADABLE_TEXT: &str = "▌ verb plate UNREADABLE — malformed host data";

/// Deterministic consequence-preview estimates for one proposed verb.
///
/// Field shape pins to `babylon.projection.verbs.view_models.VerbPreview`.
#[derive(Debug, Clone, PartialEq, Deserialize)]
pub struct VerbPreview {
    /// Estimated collective-identity delta, rounded to 4 places.
    pub estimated_consciousness_delta: f64,
    /// Estimated heat delta, rounded to 4 places.
    pub estimated_heat_delta: f64,
    /// Action-point cost of the verb.
    pub action_point_cost: f64,
    /// Rounded success estimate.
    pub success_probability: f64,
    /// The acting org's territories plus the explicit target, in that order.
    pub affected_territory_ids: Vec<String>,
    /// Player-facing caveats — honest, never suppressed.
    pub warnings: Vec<String>,
}

/// One verb's parsed row, as served inside `VerbPlateView.verbs`.
///
/// Field shape pins to `babylon.projection.verbs.view_models.VerbRow`.
#[derive(Debug, Clone, PartialEq, Deserialize)]
pub struct VerbRowParsed {
    /// The canonical verb name (e.g. `"educate"`).
    pub verb: String,
    /// Target-existence predicate result — the row is gated on this alone,
    /// never on [`Self::can_afford`].
    pub eligible: bool,
    /// Player-facing reason when ineligible, else `None`.
    pub reason: Option<String>,
    /// Player-facing remedy when ineligible, else `None`.
    pub remedy: Option<String>,
    /// Affordability via the same check that gates submission.
    pub can_afford: bool,
    /// The affordability failure note, else `None`.
    pub afford_note: Option<String>,
    /// The target-less consequence preview, or `None` (an honest absence).
    pub preview: Option<VerbPreview>,
    /// The verb's own honest candidate target ids — a picker (or an F-key
    /// handler deriving an honest target) reads this without touching the
    /// graph itself. Empty for a self-targeting verb (`reproduce`).
    pub candidate_target_ids: Vec<String>,
}

/// The raw `VerbPlateView` object shape, before it is re-keyed onto
/// `CANONICAL_VERBS`' fixed slots.
#[derive(Debug, Clone, Deserialize)]
struct VerbPlateViewRaw {
    /// The acting organization.
    org_id: String,
    /// The tick the plate was computed against.
    tick: u64,
    /// One row per canonical verb — not necessarily all nine, if a caller
    /// truncated the view (see the module docs).
    verbs: Vec<VerbRowParsed>,
}

/// The verb plate view: nine Article-V verbs (Investigate expanded to
/// three), honest-absence and loud-unreadable states, and a row accessor
/// for the app shell's F-key dispatch.
pub struct VerbPlateView {
    /// The acting organization; `None` in the absent/unreadable states.
    org_id: Option<String>,
    /// The tick the plate was computed against; `None` in the
    /// absent/unreadable states.
    tick: Option<u64>,
    /// One slot per `CANONICAL_VERBS` entry (empty in the
    /// absent/unreadable states); `None` marks a verb missing from a
    /// caller-truncated payload.
    slots: Vec<Option<VerbRowParsed>>,
    /// `true` for the `"null"` honest-absence payload.
    absent: bool,
    /// `true` for a payload that failed to parse as a `VerbPlateView`.
    unreadable: bool,
}

impl VerbPlateView {
    /// Build a verb plate view from `Host::verb_plate_view_json`'s raw JSON.
    ///
    /// `"null"` opens the honest-absence state; anything that fails to
    /// parse as JSON, or parses but does not match the `VerbPlateView`
    /// object shape, opens the loud `unreadable` state instead — the two
    /// are never conflated (Constitution III.11).
    #[must_use]
    pub fn open(raw: &str) -> Self {
        let parsed: Value = match serde_json::from_str(raw) {
            Ok(value) => value,
            Err(_) => return Self::unreadable_state(),
        };
        if parsed.is_null() {
            return Self::absent_state();
        }
        match serde_json::from_value::<VerbPlateViewRaw>(parsed) {
            Ok(view) => Self::ready_state(view),
            Err(_) => Self::unreadable_state(),
        }
    }

    /// The honest-absence state: no rows, no org/tick.
    fn absent_state() -> Self {
        Self {
            org_id: None,
            tick: None,
            slots: Vec::new(),
            absent: true,
            unreadable: false,
        }
    }

    /// The loud parse-failure state: no rows, no org/tick.
    fn unreadable_state() -> Self {
        Self {
            org_id: None,
            tick: None,
            slots: Vec::new(),
            absent: false,
            unreadable: true,
        }
    }

    /// Re-keys a well-formed payload's rows onto `CANONICAL_VERBS`' fixed
    /// nine slots by verb NAME (never by array position), so a
    /// caller-truncated payload still slots every present row at its own
    /// canonical F-key regardless of where the gap fell.
    fn ready_state(view: VerbPlateViewRaw) -> Self {
        let slots = CANONICAL_VERBS
            .iter()
            .map(|verb| view.verbs.iter().find(|row| row.verb == *verb).cloned())
            .collect();
        Self {
            org_id: Some(view.org_id),
            tick: Some(view.tick),
            slots,
            absent: false,
            unreadable: false,
        }
    }

    /// `true` when this view is the `"null"` honest-absence payload.
    #[must_use]
    pub fn is_absent(&self) -> bool {
        self.absent
    }

    /// `true` when this view's payload failed to parse.
    #[must_use]
    pub fn is_unreadable(&self) -> bool {
        self.unreadable
    }

    /// The row bound to F-key `idx + 1` (`idx` in `0..=8`, matching
    /// `CANONICAL_VERBS`' order), or `None` when the view carries no rows
    /// (absent/unreadable) or the payload was truncated and that verb is
    /// missing. The app shell's F-key handler reads `eligible` and
    /// `candidate_target_ids` off this for honest-target dispatch.
    #[must_use]
    pub fn row(&self, idx: usize) -> Option<&VerbRowParsed> {
        self.slots.get(idx).and_then(Option::as_ref)
    }

    /// Builds the plate's eleven display lines (eight single-verb lines
    /// plus Investigate's three sub-verb lines), in `CANONICAL_VERBS`
    /// order. Always eleven lines regardless of truncation — a missing verb
    /// contributes its loud marker line(s) in place of its normal line(s),
    /// never fewer.
    fn build_lines(&self) -> Vec<Line<'static>> {
        let mut lines = Vec::with_capacity(11);
        for (index, verb) in CANONICAL_VERBS.iter().enumerate() {
            let fkey = index + 1;
            let slot = self.slots.get(index).and_then(Option::as_ref);
            if *verb == "investigate" {
                for sub in INVESTIGATE_SUB_VERBS {
                    let label = format!("Investigate({sub})");
                    lines.push(match slot {
                        Some(row) => verb_line(fkey, &label, row),
                        None => missing_verb_line(verb),
                    });
                }
            } else {
                let label = capitalize(verb);
                lines.push(match slot {
                    Some(row) => verb_line(fkey, &label, row),
                    None => missing_verb_line(verb),
                });
            }
        }
        lines
    }

    /// Renders the verb plate into `area`: the honest-absence line, the
    /// loud unreadable line, or the eleven verb/sub-verb lines — laid out
    /// in two side-by-side columns when `area` is too short to fit every
    /// line in one.
    pub fn render(&self, frame: &mut Frame, area: Rect) {
        let title = match (&self.org_id, self.tick) {
            (Some(org_id), Some(tick)) => format!("{org_id} — verb plate @ T{tick:04}"),
            _ => "Verb Plate".to_string(),
        };
        let block = Block::bordered().title(title);
        let inner = block.inner(area);
        frame.render_widget(block, area);

        if self.unreadable {
            let loud = Paragraph::new(UNREADABLE_TEXT).style(Style::new().fg(CRIMSON));
            frame.render_widget(loud, inner);
            return;
        }
        if self.absent {
            let absence = Paragraph::new(ABSENCE_TEXT);
            frame.render_widget(absence, inner);
            return;
        }

        let lines = self.build_lines();
        if usize::from(inner.height) >= lines.len() {
            frame.render_widget(Paragraph::new(lines), inner);
            return;
        }

        // Not enough rows to fit every line in one column: split into two
        // side-by-side columns (11 lines max, so this never needs a third).
        let mid = lines.len().div_ceil(2);
        let (left, right) = lines.split_at(mid);
        let columns = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([Constraint::Percentage(50), Constraint::Percentage(50)])
            .split(inner);
        frame.render_widget(Paragraph::new(left.to_vec()), columns[0]);
        frame.render_widget(Paragraph::new(right.to_vec()), columns[1]);
    }
}

/// One verb (or Investigate sub-verb) line: `"F{fkey} {label}"`, styled and
/// annotated per the row's eligibility/affordability.
///
/// Status semantics (a documented simplification of `verb_plate.py`'s own
/// `✓`/`✗` + gold/crimson symbols, pinned by plan Task 23): eligible AND
/// affordable renders plain [`BONE`]; eligible but NOT affordable renders
/// [`BONE`] with the `afford_note` appended in [`DIM`] (never disabling the
/// row); ineligible renders entirely in [`DIM`] with `(reason — remedy)`
/// appended — visible, never hidden (Constitution III.11 / spec-116 FR-4.8).
fn verb_line(fkey: usize, label: &str, row: &VerbRowParsed) -> Line<'static> {
    let prefix = format!("F{fkey} {label}");
    if !row.eligible {
        let reason = row.reason.as_deref().unwrap_or("(no reason given)");
        let remedy = row.remedy.as_deref().unwrap_or("(no remedy given)");
        return Line::from(Span::styled(
            format!("{prefix}  ({reason} — {remedy})"),
            Style::new().fg(DIM),
        ));
    }
    if !row.can_afford {
        let note = row.afford_note.as_deref().unwrap_or("(unaffordable)");
        return Line::from(vec![
            Span::styled(prefix, Style::new().fg(BONE)),
            Span::styled(format!("  {note}"), Style::new().fg(DIM)),
        ]);
    }
    Line::from(Span::styled(prefix, Style::new().fg(BONE)))
}

/// The loud refusal for a canonical verb absent from a caller-truncated
/// plate view (mirrors `verb_plate.py::_missing_verb_line`, `verb_plate.py:
/// 134-144`): Article V's nine verbs are "always available", so a missing
/// row is a caller bug, never silently dropped.
fn missing_verb_line(verb: &str) -> Line<'static> {
    Line::from(Span::styled(
        format!("▌ {verb} — missing from plate view"),
        Style::new().fg(CRIMSON).add_modifier(Modifier::BOLD),
    ))
}

/// Capitalizes a canonical verb's first character for display (`"educate"`
/// -> `"Educate"`). Every `CANONICAL_VERBS` entry is ASCII lowercase, so
/// this never needs to handle multi-byte casing.
fn capitalize(verb: &str) -> String {
    let mut chars = verb.chars();
    match chars.next() {
        Some(first) => first.to_uppercase().collect::<String>() + chars.as_str(),
        None => String::new(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_malformed_payload_opens_unreadable_not_absent() {
        let view = VerbPlateView::open("not json");
        assert!(view.is_unreadable());
        assert!(!view.is_absent());
    }

    #[test]
    fn null_opens_absent_not_unreadable() {
        let view = VerbPlateView::open("null");
        assert!(view.is_absent());
        assert!(!view.is_unreadable());
    }

    #[test]
    fn row_returns_none_in_the_absent_state() {
        let view = VerbPlateView::open("null");
        assert!(view.row(0).is_none());
    }
}
