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
//! explicitly (the crate DOES enable `preserve_order` for the peek plates,
//! so sorted display never leans on map iteration order) as `key: value`.
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

/// The watchlist rail: pinned-subject rows. Pin/unpin writes are LIVE as of
/// M2 (`P` pins the current dossier; `p` toggles the highlighted row while
/// the rail holds focus) — the writes cross through
/// `crate::host::Host::pin_watchlist`; this view stays a pure renderer over
/// `watchlist_json` pulls.
pub struct WatchlistView {
    /// One JSON object per pinned subject, as served by
    /// [`crate::host::Host::watchlist_json`]. Each row is expected to carry
    /// at least a `"subject"` string key; rows failing that are still shown
    /// (their fields render generically) but never open on `Enter`.
    pub rows: Vec<Value>,
    /// Index into [`WatchlistView::rows`] of the highlighted row.
    pub selected: usize,
    /// `true` when the watchlist payload failed to parse — rendered
    /// loudly, never conflated with "nothing pinned".
    pub parse_failed: bool,
}

impl WatchlistView {
    /// Opens the watchlist over a `watchlist_json` payload. A malformed or
    /// absent payload opens with an honestly empty row list rather than a
    /// fabricated one (Constitution III.11).
    pub fn open(watchlist_json: &str) -> Self {
        match serde_json::from_str::<Vec<Value>>(watchlist_json) {
            Ok(rows) => Self {
                rows,
                selected: 0,
                parse_failed: false,
            },
            Err(_) => Self {
                rows: Vec::new(),
                selected: 0,
                parse_failed: true,
            },
        }
    }

    /// Routes one key press: Up/Down move the selection (clamped, never
    /// wrapping); Enter opens the highlighted row's `"subject"` (`None` if
    /// the row list is empty, or the highlighted row has no string
    /// `"subject"` field). Esc never reaches this handler — the app shell
    /// defocuses the rail itself.
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
            _ => None,
        }
    }

    /// Renders the watchlist rail: a bordered panel titled with the pin
    /// count, one line per pinned row, or the honest-absence line when
    /// nothing is pinned. The selection highlight renders only while the
    /// rail holds focus (`focused`) — two panes must never both look
    /// focused.
    pub fn render(
        &self,
        frame: &mut Frame,
        area: Rect,
        focused: bool,
        registry: &mut crate::layout_registry::LayoutRegistry,
    ) {
        // Wave 1 §5: the rail region + each visible row are hit-testable
        // (click-to-focus, click-to-select, wheel routing by region).
        registry.register(
            crate::layout_registry::WidgetId(3000),
            area,
            Some("region:watchlist".to_string()),
        );
        let marker = if focused { " ●" } else { "" };
        let title = format!("Watchlist ({} pinned){marker}", self.rows.len());
        let mut block = Block::default().borders(Borders::ALL).title(title);
        if focused {
            // Wave 1 §4: the focused region's border is CRIMSON (the peek
            // overlay precedent) — the ● suffix stays as a second channel.
            block = block.border_style(Style::new().fg(crate::theme::CRIMSON));
        }
        let inner = block.inner(area);
        frame.render_widget(block, area);
        for index in 0..self.rows.len().min(usize::from(inner.height)) {
            registry.register(
                crate::layout_registry::WidgetId(3100 + index as u32),
                Rect {
                    x: inner.x,
                    y: inner.y + index as u16,
                    width: inner.width,
                    height: 1,
                },
                Some(format!("watchlist:{index}")),
            );
        }

        if self.parse_failed {
            // An unreadable payload is an ERROR, never "nothing pinned".
            let loud = Paragraph::new("▌ watchlist UNREADABLE — malformed host data")
                .style(Style::new().fg(crate::theme::CRIMSON));
            frame.render_widget(loud, inner);
            return;
        }
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
                let style = if focused && index == self.selected {
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
/// every other key (sorted EXPLICITLY — the crate enables `serde_json`'s
/// `preserve_order` feature for the peek plates, so map iteration is
/// insertion order and this view's sorted display must not lean on it)
/// as `key: value`. A row with no `"subject"` string still renders
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
    let mut keys: Vec<&String> = object.keys().filter(|k| *k != "subject").collect();
    keys.sort();
    for key in keys {
        if let Some(value) = object.get(key) {
            parts.push(format!("{key}: {}", format_value(value)));
        }
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
