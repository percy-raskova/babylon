//! Behavior tests for `babylon_tui::views::palette::PaletteView`.
//!
//! The filtering case table below is read straight off the vendored
//! Textual runtime — not invented — via:
//!
//!     .venv/bin/python3 -c "
//!     import asyncio
//!     from babylon.tui.palette import EntityNavigatorProvider
//!     from textual.app import App, ComposeResult
//!     from textual.widgets import Label
//!
//!     KNOWN = frozenset({'county/26163', 'county/48999', 'org/tenants-un', 'org/uaw-9999'})
//!
//!     class Host(App):
//!         def __init__(self):
//!             super().__init__()
//!             self.known_entities = KNOWN
//!         def compose(self):
//!             yield Label('host')
//!
//!     async def main():
//!         app = Host()
//!         async with app.run_test():
//!             provider = EntityNavigatorProvider(app.screen)
//!             for q in ['county', 'tenants', 'org', 'un', '999', 'c26163',
//!                       'county/26163', 'uaw', 'zzz']:
//!                 hits = [hit async for hit in provider.search(q)]
//!                 ranked = sorted(hits, key=lambda h: -h.score)
//!                 print(repr(q), [h.text for h in ranked])
//!
//!     asyncio.run(main())
//!
//! (`''` is omitted from this table: `Provider.search("")` crashes inside
//! Textual's own `FuzzySearch.score` — `palette.rs`'s module docs cover why
//! `PaletteView` deliberately does not reproduce that call shape.)

use babylon_tui::views::msg::AppEvent;
use babylon_tui::views::palette::PaletteView;
use ratatui::backend::TestBackend;
use ratatui::crossterm::event::KeyCode;
use ratatui::Terminal;

const KNOWN_JSON: &str = r#"["county/26163", "county/48999", "org/tenants-un", "org/uaw-9999"]"#;

/// Types `query` character-by-character, as the real key-event stream would.
fn type_query(view: &mut PaletteView, query: &str) {
    for c in query.chars() {
        assert!(view.handle_key(KeyCode::Char(c)).is_none());
    }
}

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
fn opens_with_every_known_subject_sorted_and_no_query() {
    let view = PaletteView::open(KNOWN_JSON);
    assert_eq!(view.query, "");
    assert_eq!(
        view.matches,
        vec![
            "county/26163",
            "county/48999",
            "org/tenants-un",
            "org/uaw-9999"
        ]
    );
    assert_eq!(view.selected, 0);
}

#[test]
fn filters_a_tied_prefix_query_in_alphabetical_order() {
    // Python: fs.match('county', ..) == 21.0 for both counties (an exact tie).
    let mut view = PaletteView::open(KNOWN_JSON);
    type_query(&mut view, "county");
    assert_eq!(view.matches, vec!["county/26163", "county/48999"]);
}

#[test]
fn filters_to_a_single_mid_word_substring_match() {
    let mut view = PaletteView::open(KNOWN_JSON);
    type_query(&mut view, "tenants");
    assert_eq!(view.matches, vec!["org/tenants-un"]);
}

#[test]
fn filters_a_tied_org_query_in_alphabetical_order() {
    let mut view = PaletteView::open(KNOWN_JSON);
    type_query(&mut view, "org");
    assert_eq!(view.matches, vec!["org/tenants-un", "org/uaw-9999"]);
}

#[test]
fn ranks_a_tighter_contiguous_match_above_a_looser_scattered_one() {
    // Python: fs.match('999', 'org/uaw-9999') == 12.0 (contiguous digit run,
    // a word start) > fs.match('999', 'county/48999') == 9.0 (scattered).
    let mut view = PaletteView::open(KNOWN_JSON);
    type_query(&mut view, "999");
    assert_eq!(view.matches, vec!["org/uaw-9999", "county/48999"]);
}

#[test]
fn filters_an_exact_full_id_query_to_only_that_id() {
    let mut view = PaletteView::open(KNOWN_JSON);
    type_query(&mut view, "county/26163");
    assert_eq!(view.matches, vec!["county/26163"]);
}

#[test]
fn filters_a_single_word_query() {
    let mut view = PaletteView::open(KNOWN_JSON);
    type_query(&mut view, "uaw");
    assert_eq!(view.matches, vec!["org/uaw-9999"]);
}

#[test]
fn a_query_matching_nothing_yields_an_empty_honest_list() {
    let mut view = PaletteView::open(KNOWN_JSON);
    type_query(&mut view, "zzz");
    assert_eq!(view.matches, Vec::<String>::new());
}

#[test]
fn backspace_removes_the_last_query_character_and_refilters() {
    let mut view = PaletteView::open(KNOWN_JSON);
    type_query(&mut view, "tenantz");
    assert_eq!(view.matches, Vec::<String>::new());
    assert!(view.handle_key(KeyCode::Backspace).is_none());
    assert_eq!(view.query, "tenant");
    assert_eq!(view.matches, vec!["org/tenants-un"]);
}

#[test]
fn down_then_enter_opens_the_second_ranked_match() {
    let mut view = PaletteView::open(KNOWN_JSON);
    type_query(&mut view, "county");
    assert_eq!(view.selected, 0);
    assert!(view.handle_key(KeyCode::Down).is_none());
    assert_eq!(view.selected, 1);
    let event = view.handle_key(KeyCode::Enter);
    assert_eq!(
        event,
        Some(AppEvent::OpenSubject("county/48999".to_string()))
    );
}

#[test]
fn up_at_the_top_row_stays_clamped_at_zero() {
    let mut view = PaletteView::open(KNOWN_JSON);
    type_query(&mut view, "county");
    assert!(view.handle_key(KeyCode::Up).is_none());
    assert_eq!(view.selected, 0);
}

#[test]
fn down_at_the_last_row_stays_clamped() {
    let mut view = PaletteView::open(KNOWN_JSON);
    type_query(&mut view, "county");
    assert!(view.handle_key(KeyCode::Down).is_none());
    assert!(view.handle_key(KeyCode::Down).is_none());
    assert_eq!(view.selected, 1); // only 2 matches: index can't exceed 1
}

#[test]
fn enter_on_an_empty_match_list_emits_nothing() {
    let mut view = PaletteView::open(KNOWN_JSON);
    type_query(&mut view, "zzz");
    assert_eq!(view.handle_key(KeyCode::Enter), None);
}

#[test]
fn esc_emits_back() {
    let mut view = PaletteView::open(KNOWN_JSON);
    assert_eq!(view.handle_key(KeyCode::Esc), Some(AppEvent::Back));
}

#[test]
fn a_malformed_catalog_opens_honestly_empty() {
    let view = PaletteView::open("not json");
    assert_eq!(view.matches, Vec::<String>::new());
}

#[test]
fn render_shows_the_query_line_and_ranked_matches() {
    let mut view = PaletteView::open(KNOWN_JSON);
    type_query(&mut view, "county");
    let backend = TestBackend::new(40, 12);
    let mut terminal = Terminal::new(backend).unwrap();
    terminal
        .draw(|frame| view.render(frame, frame.area()))
        .unwrap();
    let text = buffer_text(&terminal);
    assert!(text.contains("> county"), "{text}");
    assert!(text.contains("county/26163"), "{text}");
    assert!(text.contains("county/48999"), "{text}");
}

#[test]
fn render_shows_the_honest_absence_line_when_nothing_matches() {
    let mut view = PaletteView::open(KNOWN_JSON);
    type_query(&mut view, "zzz");
    let backend = TestBackend::new(40, 12);
    let mut terminal = Terminal::new(backend).unwrap();
    terminal
        .draw(|frame| view.render(frame, frame.area()))
        .unwrap();
    let text = buffer_text(&terminal);
    assert!(text.contains("no matching subjects"), "{text}");
}
