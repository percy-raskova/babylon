//! The chronicle rail: a right-hand strip rendering the host's pre-salienced
//! event history (design §7; contract `docs/superpowers/specs/
//! 2026-07-27-m2-seam-contracts.md` §2, plan Task 22).
//!
//! **Salience ships as data the host pre-computes; Rust renders, never
//! ranks.** The dedupe/volume-floor/autopause-scan rules all span ticks and
//! live entirely behind [`crate::host::Host::chronicle_rail_json`] (mirrors
//! `tui/app.py:1655-1694`'s pipeline) — this module only paints the
//! render-ready rows the host hands it, in the order they arrive, plus a
//! selectable cursor over the navigable ones.
//!
//! **Two distinct never-conflated states** (Constitution III.11): a
//! genuinely empty rail (no rows, no autopause banner) renders the honest
//! absence line the contract itself uses for a quiet tick, "the wire is
//! quiet", in bold CRIMSON; a payload that fails to parse — including an
//! unrecognized `"kind"`/`"severity"` value, since both are closed serde
//! enums rather than open strings, so an unknown variant is a parse error
//! rather than a silently dropped row — renders a DIFFERENT loud
//! "UNREADABLE" line. The two must never look alike.

use ratatui::crossterm::event::KeyCode;
use ratatui::layout::Rect;
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Paragraph};
use ratatui::Frame;
use serde::Deserialize;

use crate::theme::{BONE, CRIMSON, GOLD};
use crate::views::msg::AppEvent;

/// Reserved for the autopause indicator (`tui/theme.py:71-74`: `AMBER: Final
/// = "#ff8c00"`, "Reserved for the autopause indicator... NOT a §9b role
/// token"). Deliberately declared HERE rather than in `theme.rs` — the
/// cross-language parity guard (`tests/unit/render/test_rust_theme_parity.py`)
/// parses every `Color::Rgb` literal in `theme.rs` against the Python §9b
/// palette and would fail on a constant with no §9b counterpart, so this
/// module keeps its own copy instead of adding a fifth `theme.rs` constant.
pub(crate) const AMBER: Color = Color::Rgb(255, 140, 0);

/// The rail's title, per the contract's play-screen chrome (design §7).
const TITLE: &str = "CHRONICLE";

/// The honest-absence line for a totally empty rail (no rows, no banner) —
/// mirrors the Textual renderer's own quiet-wire wording as the client-side
/// absence sentinel. (There is no `"quiet"` ROW kind: `chronicle_stream`
/// never emits an empty bulletin, so a per-tick quiet row would be a dead
/// variant behind a hand-built test shape — the M1 panel's exact class.)
const ABSENCE_TEXT: &str = "the wire is quiet";

/// The loud parse-failure line, matching the M1 `watchlist.rs`/`lobby.rs`
/// "UNREADABLE" wording pattern.
const UNREADABLE_TEXT: &str = "▌ chronicle UNREADABLE — malformed host data";

/// One row's `"kind"` — a CLOSED vocabulary (mirrors the contract §2 table);
/// an unrecognized value is a serde deserialization error, not a silently
/// skipped row, so it surfaces through [`ChronicleRail::update_from_json`]
/// as the loud `parse_failed` state.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RowKind {
    /// A non-navigable tick-header line (e.g. `"T0847"`).
    Header,
    /// A salient event line; carries [`ChronicleRow::severity`].
    Event,
}

/// One event row's `"severity"` — a CLOSED vocabulary (mirrors the contract
/// §2 table); same unknown-value-is-a-parse-error treatment as
/// [`RowKind`].
#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Severity {
    /// Renders bold CRIMSON.
    Critical,
    /// Renders (non-bold) module `AMBER`.
    Warning,
    /// Renders (non-bold) [`BONE`].
    Informational,
}

/// One row of [`crate::host::Host::chronicle_rail_json`]'s `"rows"` array,
/// field-for-field per contract §2.
#[derive(Debug, Deserialize)]
pub struct ChronicleRow {
    /// The subject id this row navigates to on `Enter`, or `None` for a
    /// non-navigable row (every `"header"` row, by contract).
    pub subject: Option<String>,
    /// The row's display kind.
    pub kind: RowKind,
    /// The tick the row was generated at.
    pub tick: u64,
    /// Present only on `"event"` rows.
    pub severity: Option<Severity>,
    /// The bold-GOLD actor prefix (only ~6 `EventType`s ever carry one);
    /// [`Self::text`] excludes it.
    pub actor: Option<String>,
    /// The row's body text.
    pub text: String,
}

/// The wire shape of [`crate::host::Host::chronicle_rail_json`] (contract
/// §2), used only as a `serde_json::from_str` target inside
/// [`ChronicleRail::update_from_json`].
#[derive(Debug, Deserialize)]
struct ChronicleRailPayload {
    autopause_line: Option<String>,
    rows: Vec<ChronicleRow>,
}

/// The chronicle rail view: the host's render-ready row list, a selection
/// cursor over the navigable (non-null-`subject`) rows, and the scroll
/// offset that keeps the cursor on screen.
#[derive(Debug, Default)]
pub struct ChronicleRail {
    /// The autopause banner line, or `None` when inactive (absence, never a
    /// dimmed row — contract §2).
    pub autopause_line: Option<String>,
    /// The rail's rows, in host order (newest-first).
    pub rows: Vec<ChronicleRow>,
    /// Index into [`Self::rows`] of the highlighted navigable row, or `None`
    /// when no row has a non-null `subject`.
    pub cursor: Option<usize>,
    /// `true` when the last [`Self::update_from_json`] payload failed to
    /// parse — rendered loudly, never conflated with an honestly empty rail.
    pub parse_failed: bool,
    /// The index of the first visible row (scrolls to keep the cursor on
    /// screen); irrelevant while [`Self::rows`] fits inside the last drawn
    /// area.
    scroll: usize,
}

/// The first row index with a non-null `subject`, or `None` if every row is
/// non-navigable (mirrors the up/down skip rule).
fn first_navigable(rows: &[ChronicleRow]) -> Option<usize> {
    rows.iter().position(|row| row.subject.is_some())
}

impl ChronicleRail {
    /// Parse a fresh `chronicle_rail_json()` payload, replacing the rail's
    /// state wholesale.
    ///
    /// A well-formed payload (including a closed `"kind"`/`"severity"`
    /// vocabulary on every row) replaces [`Self::rows`]/[`Self::autopause_line`]
    /// and resets the cursor to the first navigable row. A malformed payload
    /// — bad JSON, a missing field, or an unrecognized `"kind"`/`"severity"`
    /// value — clears the rail and sets [`Self::parse_failed`] rather than
    /// keeping stale rows next to a loud banner (Constitution III.11: an
    /// unreadable payload is an ERROR, never a half-shown world).
    pub fn update_from_json(&mut self, payload: &str) {
        match serde_json::from_str::<ChronicleRailPayload>(payload) {
            Ok(parsed) => {
                // Highlight preservation (the Textual idiom,
                // `app.py:1690-1694`): keep the selected row across a
                // refresh by re-resolving its subject against the new list,
                // falling back to the first navigable row only when it is
                // gone; clamp the scroll rather than snapping to the top.
                let kept_subject = self
                    .cursor
                    .and_then(|index| self.rows.get(index))
                    .and_then(|row| row.subject.clone());
                self.cursor = kept_subject
                    .and_then(|subject| {
                        parsed
                            .rows
                            .iter()
                            .position(|row| row.subject.as_deref() == Some(subject.as_str()))
                    })
                    .or_else(|| first_navigable(&parsed.rows));
                self.scroll = self.scroll.min(parsed.rows.len().saturating_sub(1));
                self.autopause_line = parsed.autopause_line;
                self.rows = parsed.rows;
                self.parse_failed = false;
            }
            Err(_) => {
                self.autopause_line = None;
                self.rows = Vec::new();
                self.cursor = None;
                self.parse_failed = true;
                self.scroll = 0;
            }
        }
    }

    /// Move the cursor to the next navigable row in `direction` (`-1` up,
    /// `1` down), skipping non-navigable rows and clamping (never wrapping)
    /// at either end. A no-op when nothing is navigable.
    fn move_cursor(&mut self, direction: i64) {
        let Some(current) = self.cursor else {
            return;
        };
        let mut index = current as i64;
        // Bounded by `rows.len()`: each step moves `index` strictly toward
        // one end of the vector, so it exits (via the bounds check below)
        // in at most `rows.len()` iterations.
        for _ in 0..self.rows.len() {
            index += direction;
            let Ok(candidate) = usize::try_from(index) else {
                return;
            };
            match self.rows.get(candidate).map(|row| row.subject.is_some()) {
                Some(true) => {
                    self.cursor = Some(candidate);
                    return;
                }
                Some(false) => continue,
                None => return,
            }
        }
    }

    /// Route one key press: Up/Down move [`Self::cursor`] over navigable
    /// rows; Enter opens the highlighted row's subject (the same
    /// [`AppEvent::OpenSubject`] the watchlist rail uses). Esc never reaches
    /// this handler — the app shell defocuses the rail itself.
    pub fn handle_key(&mut self, code: KeyCode) -> Option<AppEvent> {
        match code {
            KeyCode::Up => {
                self.move_cursor(-1);
                None
            }
            KeyCode::Down => {
                self.move_cursor(1);
                None
            }
            KeyCode::Enter => self
                .cursor
                .and_then(|index| self.rows.get(index))
                .and_then(|row| row.subject.clone())
                .map(AppEvent::OpenSubject),
            _ => None,
        }
    }

    /// Render the rail into `area` of `frame`: a bordered panel titled
    /// `"CHRONICLE"`, the autopause banner (if any) pinned as the first
    /// line, then the row window `Self::scroll` selects, or one of the two
    /// distinct absence/failure states in place of rows.
    ///
    /// Takes `&mut self` because drawing is also where `self.scroll`
    /// catches up to wherever [`Self::cursor`] last moved — the scroll
    /// offset is otherwise meaningless without a drawn area to scroll
    /// within.
    pub fn render(
        &mut self,
        frame: &mut Frame,
        area: Rect,
        focused: bool,
        registry: &mut crate::layout_registry::LayoutRegistry,
    ) {
        // Wave 1 §5: region + visible navigable rows are hit-testable.
        registry.register(
            crate::layout_registry::WidgetId(3001),
            area,
            Some("region:chronicle".to_string()),
        );
        let title = if focused {
            format!("{TITLE} ●")
        } else {
            TITLE.to_string()
        };
        let mut block = Block::bordered().title(title);
        if focused {
            // Wave 1 §4: the focused region's border is CRIMSON (the peek
            // overlay precedent) — the ● suffix stays as a second channel.
            block = block.border_style(Style::new().fg(CRIMSON));
        }
        let inner = block.inner(area);
        frame.render_widget(block, area);

        if self.parse_failed {
            let loud = Paragraph::new(UNREADABLE_TEXT).style(Style::new().fg(CRIMSON));
            frame.render_widget(loud, inner);
            return;
        }

        if self.rows.is_empty() && self.autopause_line.is_none() {
            let absence = Paragraph::new(Span::styled(
                ABSENCE_TEXT,
                Style::new().fg(CRIMSON).add_modifier(Modifier::BOLD),
            ));
            frame.render_widget(absence, inner);
            return;
        }

        let banner_height: u16 = if self.autopause_line.is_some() { 1 } else { 0 };
        let visible_rows = usize::from(inner.height.saturating_sub(banner_height));

        if let Some(cursor) = self.cursor {
            if cursor < self.scroll {
                self.scroll = cursor;
            } else if visible_rows > 0 && cursor >= self.scroll + visible_rows {
                self.scroll = cursor + 1 - visible_rows;
            }
        }

        let mut lines: Vec<Line> = Vec::new();
        if let Some(banner) = &self.autopause_line {
            lines.push(Line::from(Span::styled(
                banner.clone(),
                Style::new().fg(AMBER).add_modifier(Modifier::BOLD),
            )));
        }
        for (index, row) in self
            .rows
            .iter()
            .enumerate()
            .skip(self.scroll)
            .take(visible_rows)
        {
            // Wave 1 §5: navigable rows are hit-testable at their VISIBLE
            // position (banner + scroll offsets applied).
            if row.subject.is_some() {
                let visible_index = (index - self.scroll) as u16 + banner_height;
                registry.register(
                    crate::layout_registry::WidgetId(3200 + index as u32),
                    Rect {
                        x: inner.x,
                        y: inner.y + visible_index,
                        width: inner.width,
                        height: 1,
                    },
                    Some(format!("chronicle:{index}")),
                );
            }
            let line = row_line(row);
            // The REVERSED cursor renders only on the FOCUSED rail — two
            // panes must never both look focused (verify-panel finding).
            lines.push(if focused && Some(index) == self.cursor {
                highlighted(line)
            } else {
                line
            });
        }
        frame.render_widget(Paragraph::new(lines), inner);
    }
}

/// Build one row's display line per its `kind` (contract §2's color table).
fn row_line(row: &ChronicleRow) -> Line<'static> {
    match row.kind {
        RowKind::Header => Line::from(Span::styled(
            row.text.clone(),
            Style::new().fg(GOLD).add_modifier(Modifier::BOLD),
        )),
        RowKind::Event => event_line(row),
    }
}

/// Build an `"event"` row's line: severity picks the text color (critical
/// bold CRIMSON, warning module [`AMBER`], informational — or an absent
/// severity — BONE), with an optional bold-GOLD actor prefix ahead of the
/// text (`"{actor}: "`, the Textual `_event_line` separator; the host's
/// `text` field itself never includes the actor).
fn event_line(row: &ChronicleRow) -> Line<'static> {
    let (color, bold) = match row.severity {
        Some(Severity::Critical) => (CRIMSON, true),
        Some(Severity::Warning) => (AMBER, false),
        Some(Severity::Informational) | None => (BONE, false),
    };
    let mut style = Style::new().fg(color);
    if bold {
        style = style.add_modifier(Modifier::BOLD);
    }
    match &row.actor {
        Some(actor) => Line::from(vec![
            Span::styled(
                format!("{actor}: "),
                Style::new().fg(GOLD).add_modifier(Modifier::BOLD),
            ),
            Span::styled(row.text.clone(), style),
        ]),
        None => Line::from(Span::styled(row.text.clone(), style)),
    }
}

/// Re-style every span of `line` with [`Modifier::REVERSED`] added, keeping
/// each span's own foreground color (reversed video swaps at the terminal,
/// not in the stored `fg`/`bg`, so this never disturbs the color a test —
/// or a future reader — expects a given span to carry).
fn highlighted(line: Line<'static>) -> Line<'static> {
    Line::from(
        line.spans
            .into_iter()
            .map(|span| Span::styled(span.content, span.style.add_modifier(Modifier::REVERSED)))
            .collect::<Vec<_>>(),
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_malformed_kind_fails_the_whole_payload() {
        let mut rail = ChronicleRail::default();
        rail.update_from_json(
            r#"{"autopause_line": null, "rows": [
                {"subject": null, "kind": "bogus", "tick": 1, "severity": null,
                 "actor": null, "text": "x"}
            ]}"#,
        );
        assert!(rail.parse_failed);
        assert!(rail.rows.is_empty());
    }

    #[test]
    fn cursor_starts_on_the_first_navigable_row() {
        let mut rail = ChronicleRail::default();
        rail.update_from_json(
            r#"{"autopause_line": null, "rows": [
                {"subject": null, "kind": "header", "tick": 1, "severity": null,
                 "actor": null, "text": "T0001"},
                {"subject": "organization/org-a", "kind": "event", "tick": 1,
                 "severity": "informational", "actor": null, "text": "reports in"}
            ]}"#,
        );
        assert_eq!(rail.cursor, Some(1));
    }
}
