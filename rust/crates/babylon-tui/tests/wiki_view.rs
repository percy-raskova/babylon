//! `WikiView` contract tests (plan Task 15).
//!
//! Explicit expected-content asserts over a `TestBackend` buffer — no insta
//! snapshots (blessing needs a `cargo run` the parent session owns).

use std::collections::BTreeSet;

use babylon_tui::host::Host;
use babylon_tui::layout_registry::LayoutRegistry;
use babylon_tui::router::BabylonTarget;
use babylon_tui::views::msg::AppEvent;
use babylon_tui::views::wiki::WikiView;
use ratatui::backend::TestBackend;
use ratatui::buffer::Buffer;
use ratatui::crossterm::event::{KeyCode, KeyModifiers};
use ratatui::Terminal;

/// A fake host serving three fixture pages (`alpha`, `beta`, `gamma`);
/// every other subject is an honest absence (JSON `null`).
struct FakeHost;

impl Host for FakeHost {
    fn lobby_catalog_json(&self) -> String {
        "[]".to_string()
    }

    fn read_page_json(&self, subject: &str) -> String {
        let page = match subject {
            "alpha" => "# Alpha\n\nThe first fixture page.",
            "beta" => "# Beta\n\nThe second fixture page.",
            "gamma" => "# Gamma\n\nThe third fixture page.",
            _ => return "null".to_string(),
        };
        serde_json::to_string(page).expect("fixture page encodes")
    }
}

/// Join the buffer's rows into one string for substring assertions
/// (mirrors `tests/lobby_view.rs`'s helper).
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

/// Render `view` into a fresh `TestBackend` buffer.
fn render(view: &WikiView) -> Buffer {
    let backend = TestBackend::new(60, 15);
    let mut terminal = Terminal::new(backend).unwrap();
    let known: BTreeSet<String> = BTreeSet::new();
    let mut registry = LayoutRegistry::new();
    terminal
        .draw(|frame| {
            let area = frame.area();
            view.render(frame, area, &mut registry, &known);
        })
        .unwrap();
    terminal.backend().buffer().clone()
}

#[test]
fn open_entity_with_page_renders_its_heading() {
    let mut view = WikiView::new();
    view.open(&BabylonTarget::Entity("alpha".to_string()), &FakeHost);
    assert_eq!(view.current.as_deref(), Some("alpha"));

    let text = buffer_text(&render(&view));
    assert!(text.contains("Alpha"), "expected heading in:\n{text}");
    assert!(
        text.contains("first fixture page"),
        "expected body in:\n{text}"
    );
}

#[test]
fn open_subject_with_no_page_renders_the_honest_absence_page() {
    let mut view = WikiView::new();
    view.open(
        &BabylonTarget::Redlink("missing_thing".to_string()),
        &FakeHost,
    );
    assert_eq!(view.current.as_deref(), Some("missing_thing"));

    let text = buffer_text(&render(&view));
    assert!(
        text.contains("missing_thing"),
        "expected subject name in:\n{text}"
    );
    assert!(
        text.contains("No page recorded for this subject."),
        "expected honest-absence body in:\n{text}"
    );
}

#[test]
fn kind_target_resolves_subject_as_kind_slash_id() {
    // A `Kind` target's subject is "<kind>/<id>" — this fixture host has no
    // page under that composite subject, so it renders honest absence
    // naming the composite id (proving the resolution, not just the
    // absence path).
    let mut view = WikiView::new();
    view.open(
        &BabylonTarget::Kind {
            kind: "county".to_string(),
            id: "wayne".to_string(),
        },
        &FakeHost,
    );
    assert_eq!(view.current.as_deref(), Some("county/wayne"));
}

#[test]
fn jumplist_back_back_forward_and_branch_truncation() {
    let mut view = WikiView::new();
    view.open(&BabylonTarget::Entity("alpha".to_string()), &FakeHost);
    view.open(&BabylonTarget::Entity("beta".to_string()), &FakeHost);
    view.open(&BabylonTarget::Entity("gamma".to_string()), &FakeHost);
    assert_eq!(view.jumplist, vec!["alpha", "beta", "gamma"]);
    assert_eq!(view.jumplist_idx, 2);

    assert_eq!(view.back(), Some("beta".to_string()));
    assert_eq!(view.jumplist_idx, 1);
    assert_eq!(view.back(), Some("alpha".to_string()));
    assert_eq!(view.jumplist_idx, 0);
    assert_eq!(view.back(), None, "idempotent at the oldest entry");
    assert_eq!(view.jumplist_idx, 0);

    assert_eq!(view.forward(), Some("beta".to_string()));
    assert_eq!(view.jumplist_idx, 1);

    // Opening a new page from mid-jumplist (currently positioned at "beta")
    // truncates the discarded forward entry ("gamma"), browser-style.
    view.open(&BabylonTarget::Entity("delta".to_string()), &FakeHost);
    assert_eq!(view.jumplist, vec!["alpha", "beta", "delta"]);
    assert_eq!(view.jumplist_idx, 2);
    assert_eq!(view.forward(), None, "delta is now the newest entry");
}

#[test]
fn reopening_the_current_subject_does_not_grow_the_jumplist() {
    let mut view = WikiView::new();
    view.open(&BabylonTarget::Entity("alpha".to_string()), &FakeHost);
    view.open(&BabylonTarget::Entity("alpha".to_string()), &FakeHost);
    assert_eq!(view.jumplist, vec!["alpha"]);
    assert_eq!(view.jumplist_idx, 0);
}

#[test]
fn back_and_forward_are_none_on_a_view_with_no_history() {
    let mut view = WikiView::new();
    assert_eq!(view.back(), None);
    assert_eq!(view.forward(), None);
}

#[test]
fn handle_key_bracket_and_ctrl_bindings_emit_open_subject() {
    let mut view = WikiView::new();
    view.open(&BabylonTarget::Entity("alpha".to_string()), &FakeHost);
    view.open(&BabylonTarget::Entity("beta".to_string()), &FakeHost);

    assert_eq!(
        view.handle_key(KeyCode::Char('['), KeyModifiers::NONE),
        Some(AppEvent::OpenSubject("alpha".to_string())),
        "[ walks back"
    );
    assert_eq!(
        view.handle_key(KeyCode::Char(']'), KeyModifiers::NONE),
        Some(AppEvent::OpenSubject("beta".to_string())),
        "] walks forward"
    );
    assert_eq!(
        view.handle_key(KeyCode::Char('o'), KeyModifiers::CONTROL),
        Some(AppEvent::OpenSubject("alpha".to_string())),
        "Ctrl-O walks back"
    );
    assert_eq!(
        view.handle_key(KeyCode::Char('i'), KeyModifiers::CONTROL),
        Some(AppEvent::OpenSubject("beta".to_string())),
        "Ctrl-I walks forward"
    );

    // A bare 'o'/'i' (no Ctrl) is not a jumplist binding.
    assert_eq!(
        view.handle_key(KeyCode::Char('o'), KeyModifiers::NONE),
        None
    );
    assert_eq!(
        view.handle_key(KeyCode::Char('i'), KeyModifiers::NONE),
        None
    );
}

#[test]
fn q_and_esc_emit_back() {
    let mut view = WikiView::new();
    assert_eq!(
        view.handle_key(KeyCode::Char('q'), KeyModifiers::NONE),
        Some(AppEvent::Back)
    );
    assert_eq!(
        view.handle_key(KeyCode::Esc, KeyModifiers::NONE),
        Some(AppEvent::Back)
    );
}

#[test]
fn scroll_keys_adjust_scroll_and_saturate() {
    let mut view = WikiView::new();
    view.open(&BabylonTarget::Entity("alpha".to_string()), &FakeHost);

    // Up at the top saturates at 0 (no underflow panic).
    assert_eq!(view.handle_key(KeyCode::Up, KeyModifiers::NONE), None);
    assert_eq!(view.handle_key(KeyCode::PageUp, KeyModifiers::NONE), None);

    assert_eq!(view.handle_key(KeyCode::Down, KeyModifiers::NONE), None);
    assert_eq!(view.handle_key(KeyCode::PageDown, KeyModifiers::NONE), None);
    // Rendering after scrolling should not panic even with no visible link.
    let _ = render(&view);
}

#[test]
fn unmapped_key_emits_nothing() {
    let mut view = WikiView::new();
    assert_eq!(
        view.handle_key(KeyCode::Char('z'), KeyModifiers::NONE),
        None
    );
}
