//! The watchlist rail: a read-only, row-addressable view over pinned subjects.
//!
//! Ports the *display* shape of `babylon.tui.watchlist` — specifically
//! `watchlist_rows`'s contract (one selectable row per pinned id, keyed by
//! its subject id, plus a single named absence row when nothing is pinned)
//! — over the wire shape [`crate::host::Host::watchlist_json`] actually
//! serves: a JSON array of row objects, each carrying at least a `"subject"`
//! string key (the id [`WatchlistView::handle_key`]'s `Enter` opens).
//!
//! **Schema note (Python-owned, not yet pinned):** the exact set of display
//! fields a watchlist row carries beyond `"subject"` is Program 24 P3
//! WO-46/Task 17 territory (`babylon.tui.watchlist._row_text` computes a
//! `peek(view, depth=0)` line, which is Python-side `ProjectionRecord`
//! rendering logic with no Rust port target in this milestone). Rather than
//! guess at field names that may not match what Task 17 ships, each row
//! stays a `serde_json::Value` object and [`WatchlistView::render`] renders
//! it generically: the `"subject"` value first, then every other key sorted
//! (`serde_json::Map`'s default backing is a `BTreeMap` — deterministic
//! iteration with no `preserve_order` feature enabled here) as `key: value`.
//! This is forward-compatible with whatever concrete fields Task 17 lands
//! without a follow-up Rust change, at the cost of not reproducing
//! `_row_text`'s exact prose today.
//!
//! Absence follows the [`crate::host::Host`] trait's own documented
//! contract (`"or \`null\`/\`[]\`, never a fabricated value"`) rather than
//! `watchlist_rows`'s Python-internal convention of a single
//! `(None, absence_text)` placeholder row for `OptionList` — an empty JSON
//! array here means "nothing pinned", and [`WatchlistView`] renders its own
//! honest-absence line for it, reusing `_absence_text`'s exact wording.

use ratatui::crossterm::event::KeyCode;
use ratatui::layout::Rect;
use ratatui::style::{Modifier, Style};
use ratatui::text::{Line, Span, Text};
use ratatui::widgets::{Block, Borders, Paragraph};
use ratatui::Frame;
use serde_json::Value;

use crate::views::msg::AppEvent;

/// The exact wording of `babylon.tui.watchlist._absence_text` (ported
/// verbatim so the honest-absence line reads identically to the Textual
/// client).
const ABSENCE_TEXT: &str = "▌ watchlist — nothing pinned yet";

/// The watchlist rail: pinned-subject rows, read-only in M1 (pin/unpin
/// writes land in M2 — see `babylon.tui.watchlist`'s own module docs on the
/// `WatchlistPersistence` seam).
pub struct WatchlistView {
    /// One JSON object per pinned subject, as served by
    /// [`crate::host::Host::watchlist_json`]. Each row is expected to carry
    /// at least a `"subject"` string key; rows failing that are still shown
    /// (their fields render generically) but never open on `Enter`.
    pub rows: Vec<Value>,
    /// Index into [`WatchlistView::rows`] of the highlighted row.
    pub selected: usize,
}

impl WatchlistView {
    /// Opens the watchlist over a `watchlist_json` payload. A malformed or
    /// absent payload opens with an honestly empty row list rather than a
    /// fabricated one (Constitution III.11).
    pub fn open(watchlist_json: &str) -> Self {
        let rows: Vec<Value> = serde_json::from_str(watchlist_json).unwrap_or_default();
        Self { rows, selected: 0 }
    }

    /// Routes one key press: Up/Down move the selection (clamped, never
    /// wrapping); Enter opens the highlighted row's `"subject"` (`None` if
    /// the row list is empty, or the highlighted row has no string
    /// `"subject"` field); Esc backs out of the rail.
    pub fn handle_key(&mut self, code: KeyCode) -> Option<AppEvent> {
        match code {
            KeyCode::Up => {
                self.selected = self.selected.saturating_sub(1);
                None
            }
            KeyCode::Down => {
                if self.selected + 1 < self.rows.len() {
                    self.selected += 1;
                }
                None
            }
            KeyCode::Enter => self
                .rows
                .get(self.selected)
                .and_then(|row| row.get("subject"))
                .and_then(Value::as_str)
                .map(|subject| AppEvent::OpenSubject(subject.to_string())),
            KeyCode::Esc => Some(AppEvent::Back),
            _ => None,
        }
    }

    /// Renders the watchlist rail: a bordered panel titled with the pin
    /// count, one line per pinned row, or the honest-absence line when
    /// nothing is pinned.
    pub fn render(&self, frame: &mut Frame, area: Rect) {
        let title = format!("Watchlist ({} pinned)", self.rows.len());
        let block = Block::default().borders(Borders::ALL).title(title);
        let inner = block.inner(area);
        frame.render_widget(block, area);

        if self.rows.is_empty() {
            let absence = Paragraph::new(ABSENCE_TEXT);
            frame.render_widget(absence, inner);
            return;
        }

        let lines: Vec<Line> = self
            .rows
            .iter()
            .enumerate()
            .map(|(index, row)| {
                let style = if index == self.selected {
                    Style::default().add_modifier(Modifier::REVERSED)
                } else {
                    Style::default()
                };
                Line::from(Span::styled(row_text(row), style))
            })
            .collect();
        let list = Paragraph::new(Text::from(lines));
        frame.render_widget(list, inner);
    }
}

/// Renders one row object generically: `"subject"`'s value first, then
/// every other key (sorted, `serde_json::Map`'s deterministic default
/// order) as `key: value`. A row with no `"subject"` string still renders
/// its other fields — never silently dropped (Constitution III.11) — just
/// unopenable (see [`WatchlistView::handle_key`]).
fn row_text(row: &Value) -> String {
    let Some(object) = row.as_object() else {
        return format_value(row);
    };
    let subject = object
        .get("subject")
        .and_then(Value::as_str)
        .unwrap_or("(no subject)");
    let mut parts = vec![subject.to_string()];
    for (key, value) in object {
        if key == "subject" {
            continue;
        }
        parts.push(format!("{key}: {}", format_value(value)));
    }
    parts.join("  ")
}

/// Formats a JSON scalar for display: strings unquoted, null as an explicit
/// em-dash placeholder, everything else via its compact JSON form.
fn format_value(value: &Value) -> String {
    match value {
        Value::String(s) => s.clone(),
        Value::Null => "—".to_string(),
        other => other.to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn row_text_puts_subject_first_then_sorted_fields() {
        let row: Value = serde_json::from_str(
            r#"{"subject":"county/26163","population":1749343,"note":"Wayne"}"#,
        )
        .unwrap();
        assert_eq!(
            row_text(&row),
            "county/26163  note: Wayne  population: 1749343"
        );
    }

    #[test]
    fn row_text_handles_a_missing_subject_without_panicking() {
        let row: Value = serde_json::from_str(r#"{"population":1749343}"#).unwrap();
        assert_eq!(row_text(&row), "(no subject)  population: 1749343");
    }
}
