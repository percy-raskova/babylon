//! `LobbyView` contract tests (plan Task 16).
//!
//! Explicit expected-content asserts over a `TestBackend` buffer — no insta
//! snapshots (blessing needs a `cargo run` the parent session owns).

use babylon_tui::views::lobby::LobbyView;
use babylon_tui::views::msg::AppEvent;
use ratatui::backend::TestBackend;
use ratatui::buffer::Buffer;
use ratatui::crossterm::event::KeyCode;
use ratatui::Terminal;

/// Two rows, mirroring `Host::lobby_catalog_json`'s emitted shape
/// (`src/babylon/tui/host.py`).
const TWO_ROWS: &str = r#"[
    {"campaign_id":"11111111-1111-1111-1111-111111111111","name":"Wayne County","tick":3,"status":"ACTIVE","defines_hash":"abc123","engine_version":"0.9.0"},
    {"campaign_id":"22222222-2222-2222-2222-222222222222","name":"Cuyahoga Front","tick":0,"status":"ABANDONED","defines_hash":"def456","engine_version":"0.9.0"}
]"#;

/// Render `view` into a fresh `TestBackend` buffer of `width`x`height`.
fn render(view: &LobbyView, width: u16, height: u16) -> Buffer {
    let backend = TestBackend::new(width, height);
    let mut terminal = Terminal::new(backend).unwrap();
    terminal
        .draw(|frame| view.render(frame, frame.area()))
        .unwrap();
    terminal.backend().buffer().clone()
}

/// Join the buffer's rows into one string for substring assertions
/// (whitespace-preserving, so `contains` on a joined phrase still works
/// within one row).
fn buffer_lines(buf: &Buffer) -> Vec<String> {
    let area = buf.area;
    (0..area.height)
        .map(|y| {
            (0..area.width)
                .map(|x| {
                    buf.cell((area.x + x, area.y + y))
                        .map(|c| c.symbol())
                        .unwrap_or(" ")
                })
                .collect::<String>()
        })
        .collect()
}

fn buffer_text(buf: &Buffer) -> String {
    buffer_lines(buf).join("\n")
}

#[test]
fn populated_catalog_renders_all_rows_and_fields() {
    let view = LobbyView::from_catalog_json(TWO_ROWS);
    assert_eq!(view.rows.len(), 2);
    let buf = render(&view, 80, 10);
    let text = buffer_text(&buf);

    assert!(text.contains("THE ARCHIVE"));
    assert!(text.contains("CAMPAIGNS"));

    assert!(text.contains("Wayne County"));
    assert!(text.contains("Tick 3"));
    assert!(text.contains("ACTIVE"));
    assert!(text.contains("engine 0.9.0"));
    assert!(text.contains("defines abc123"));

    assert!(text.contains("Cuyahoga Front"));
    assert!(text.contains("Tick 0"));
    assert!(text.contains("ABANDONED"));
    assert!(text.contains("defines def456"));
}

#[test]
fn empty_catalog_renders_honest_absence() {
    let view = LobbyView::from_catalog_json("[]");
    assert!(view.rows.is_empty());
    let buf = render(&view, 80, 10);
    let text = buffer_text(&buf);
    assert!(text.contains("No campaigns in the catalog."));
    assert!(!text.contains("Wayne County"));
}

#[test]
fn malformed_json_never_panics_and_yields_empty_catalog() {
    let view = LobbyView::from_catalog_json("not json at all");
    assert!(view.rows.is_empty());
    assert_eq!(view.selected, 0);

    let view_null = LobbyView::from_catalog_json("null");
    assert!(view_null.rows.is_empty());

    let view_blank = LobbyView::from_catalog_json("");
    assert!(view_blank.rows.is_empty());
}

#[test]
fn down_then_up_moves_selection_and_highlight_follows() {
    let mut view = LobbyView::from_catalog_json(TWO_ROWS);
    assert_eq!(view.selected, 0);

    let event = view.handle_key(KeyCode::Down);
    assert_eq!(event, None);
    assert_eq!(view.selected, 1);
    let buf = render(&view, 80, 10);
    let lines = buffer_lines(&buf);
    let cuyahoga_line = lines
        .iter()
        .find(|l| l.contains("Cuyahoga Front"))
        .expect("Cuyahoga Front row present");
    assert!(
        cuyahoga_line.contains('>'),
        "selected row should carry the highlight symbol"
    );
    let wayne_line = lines
        .iter()
        .find(|l| l.contains("Wayne County"))
        .expect("Wayne County row present");
    assert!(
        !wayne_line.trim_start().starts_with('>'),
        "unselected row should not be highlighted"
    );

    let event = view.handle_key(KeyCode::Up);
    assert_eq!(event, None);
    assert_eq!(view.selected, 0);
}

#[test]
fn vim_keys_move_selection_same_as_arrows() {
    let mut view = LobbyView::from_catalog_json(TWO_ROWS);
    assert_eq!(view.handle_key(KeyCode::Char('j')), None);
    assert_eq!(view.selected, 1);
    assert_eq!(view.handle_key(KeyCode::Char('k')), None);
    assert_eq!(view.selected, 0);
}

#[test]
fn selection_saturates_at_both_ends() {
    let mut view = LobbyView::from_catalog_json(TWO_ROWS);

    // Up at index 0 stays at 0.
    assert_eq!(view.handle_key(KeyCode::Up), None);
    assert_eq!(view.selected, 0);

    // Down past the last row stays at the last row.
    assert_eq!(view.handle_key(KeyCode::Down), None);
    assert_eq!(view.selected, 1);
    assert_eq!(view.handle_key(KeyCode::Down), None);
    assert_eq!(view.selected, 1);
    assert_eq!(view.handle_key(KeyCode::Down), None);
    assert_eq!(view.selected, 1);
}

#[test]
fn enter_emits_load_campaign_for_the_selected_row() {
    let mut view = LobbyView::from_catalog_json(TWO_ROWS);
    view.selected = 1;
    let event = view.handle_key(KeyCode::Enter);
    assert_eq!(
        event,
        Some(AppEvent::LoadCampaign(
            "22222222-2222-2222-2222-222222222222".to_string()
        ))
    );
}

#[test]
fn enter_on_first_row_emits_its_own_campaign_id() {
    let mut view = LobbyView::from_catalog_json(TWO_ROWS);
    let event = view.handle_key(KeyCode::Enter);
    assert_eq!(
        event,
        Some(AppEvent::LoadCampaign(
            "11111111-1111-1111-1111-111111111111".to_string()
        ))
    );
}

#[test]
fn enter_on_empty_catalog_emits_nothing() {
    let mut view = LobbyView::from_catalog_json("[]");
    assert_eq!(view.handle_key(KeyCode::Enter), None);
}

#[test]
fn n_emits_new_campaign() {
    let mut view = LobbyView::from_catalog_json(TWO_ROWS);
    assert_eq!(
        view.handle_key(KeyCode::Char('n')),
        Some(AppEvent::NewCampaign)
    );
}

#[test]
fn q_and_esc_emit_quit() {
    let mut view = LobbyView::from_catalog_json(TWO_ROWS);
    assert_eq!(view.handle_key(KeyCode::Char('q')), Some(AppEvent::Quit));
    assert_eq!(view.handle_key(KeyCode::Esc), Some(AppEvent::Quit));
}

#[test]
fn unmapped_key_emits_nothing() {
    let mut view = LobbyView::from_catalog_json(TWO_ROWS);
    assert_eq!(view.handle_key(KeyCode::Char('z')), None);
}
