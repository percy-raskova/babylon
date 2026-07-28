//! Behavior tests for `babylon_tui::views::watchlist::WatchlistView`.
//!
//! The row shape here is deliberately generic (`serde_json::Value` objects,
//! per the pinned `WatchlistView` contract) rather than a literal port of
//! `babylon.tui.watchlist`'s `ProjectionRecord`-typed rows — see
//! `watchlist.rs`'s module docs for why: the exact non-`"subject"` field
//! set is Task 17's Python-owned schema, not yet on disk. What IS ported
//! verbatim from `babylon.tui.watchlist`: the `"▌ watchlist — nothing
//! pinned yet"` absence wording (`_absence_text`) and the read-only
//! Up/Down/Enter/Esc row-navigation shape `watchlist_rows` exists to feed
//! an `OptionList` with.

use babylon_tui::views::msg::AppEvent;
use babylon_tui::views::watchlist::WatchlistView;
use ratatui::backend::TestBackend;
use ratatui::crossterm::event::KeyCode;
use ratatui::Terminal;

const TWO_PINS_JSON: &str = r#"[
    {"subject": "county/26163", "population": 1749343},
    {"subject": "county/26125", "population": 1270432}
]"#;

/// Dumps a `TestBackend` buffer's visible text, one line per row, for
/// substring assertions.
fn buffer_text(terminal: &Terminal<TestBackend>) -> String {
    let buffer = terminal.backend().buffer();
    let area = buffer.area;
    let mut out = String::new();
    for y in area.top()..area.bottom() {
        for x in area.left()..area.right() {
            out.push_str(buffer[(x, y)].symbol());
        }
        out.push('\n');
    }
    out
}

#[test]
fn opens_with_every_row_from_the_json_payload() {
    let view = WatchlistView::open(TWO_PINS_JSON);
    assert_eq!(view.rows.len(), 2);
    assert_eq!(view.selected, 0);
}

#[test]
fn a_malformed_payload_opens_honestly_empty() {
    let view = WatchlistView::open("not json");
    assert_eq!(view.rows.len(), 0);
}

#[test]
fn an_absent_payload_opens_honestly_empty() {
    let view = WatchlistView::open("[]");
    assert_eq!(view.rows.len(), 0);
}

#[test]
fn down_then_enter_opens_the_second_rows_subject() {
    let mut view = WatchlistView::open(TWO_PINS_JSON);
    assert!(view.handle_key(KeyCode::Down).is_none());
    assert_eq!(view.selected, 1);
    let event = view.handle_key(KeyCode::Enter);
    assert_eq!(
        event,
        Some(AppEvent::OpenSubject("county/26125".to_string()))
    );
}

#[test]
fn enter_on_the_first_row_opens_its_subject() {
    let mut view = WatchlistView::open(TWO_PINS_JSON);
    let event = view.handle_key(KeyCode::Enter);
    assert_eq!(
        event,
        Some(AppEvent::OpenSubject("county/26163".to_string()))
    );
}

#[test]
fn up_at_the_top_row_stays_clamped_at_zero() {
    let mut view = WatchlistView::open(TWO_PINS_JSON);
    assert!(view.handle_key(KeyCode::Up).is_none());
    assert_eq!(view.selected, 0);
}

#[test]
fn down_at_the_last_row_stays_clamped() {
    let mut view = WatchlistView::open(TWO_PINS_JSON);
    view.handle_key(KeyCode::Down);
    view.handle_key(KeyCode::Down);
    assert_eq!(view.selected, 1);
}

#[test]
fn enter_on_an_empty_watchlist_emits_nothing() {
    let mut view = WatchlistView::open("[]");
    assert_eq!(view.handle_key(KeyCode::Enter), None);
}

#[test]
fn enter_on_a_row_with_no_subject_field_emits_nothing() {
    let mut view = WatchlistView::open(r#"[{"population": 42}]"#);
    assert_eq!(view.handle_key(KeyCode::Enter), None);
}

#[test]
fn render_shows_the_pin_count_title_and_row_fields() {
    let view = WatchlistView::open(TWO_PINS_JSON);
    let backend = TestBackend::new(50, 12);
    let mut terminal = Terminal::new(backend).unwrap();
    terminal
        .draw(|frame| {
            view.render(
                frame,
                frame.area(),
                true,
                &mut babylon_tui::layout_registry::LayoutRegistry::new(),
            )
        })
        .unwrap();
    let text = buffer_text(&terminal);
    assert!(text.contains("Watchlist (2 pinned)"), "{text}");
    assert!(text.contains("county/26163"), "{text}");
    assert!(text.contains("population: 1749343"), "{text}");
    assert!(text.contains("county/26125"), "{text}");
}

#[test]
fn render_shows_the_honest_absence_line_and_zero_pin_count() {
    let view = WatchlistView::open("[]");
    let backend = TestBackend::new(50, 12);
    let mut terminal = Terminal::new(backend).unwrap();
    terminal
        .draw(|frame| {
            view.render(
                frame,
                frame.area(),
                true,
                &mut babylon_tui::layout_registry::LayoutRegistry::new(),
            )
        })
        .unwrap();
    let text = buffer_text(&terminal);
    assert!(text.contains("Watchlist (0 pinned)"), "{text}");
    assert!(text.contains("watchlist — nothing pinned yet"), "{text}");
}
