//! Behavior tests for `babylon_tui::views::chronicle::ChronicleRail`
//! (contract `docs/superpowers/specs/2026-07-27-m2-seam-contracts.md` §2,
//! plan Task 22).
//!
//! Fixture text deliberately avoids the contract's literal emoji/em-dash
//! banner wording — the banner is an opaque host-supplied string as far as
//! this view is concerned, and plain ASCII keeps the `style_at` cell-mapping
//! below exact (some emoji render double-width, which would misalign a
//! byte-offset-to-cell lookup). The one exception is the absence line,
//! the contract's own honest-absence wording, which IS load-bearing and
//! reproduced verbatim.

use babylon_tui::theme::{BONE, CRIMSON, GOLD};
use babylon_tui::views::chronicle::ChronicleRail;
use babylon_tui::views::msg::AppEvent;
use ratatui::backend::TestBackend;
use ratatui::crossterm::event::KeyCode;
use ratatui::style::{Color, Modifier};
use ratatui::Terminal;

/// Mirrors `chronicle::AMBER` (declared `pub(crate)` there on purpose — see
/// that module's doc comment — so it isn't reachable from this external
/// integration-test crate; this is the one place its literal value is
/// duplicated).
const AMBER: Color = Color::Rgb(255, 140, 0);

const MIXED_FIXTURE: &str = r#"{
    "autopause_line": "AUTOPAUSE - THIS CANNOT PASS UNREAD",
    "rows": [
        {"subject": null, "kind": "header", "tick": 847, "severity": null,
         "actor": null, "text": "T0847"},
        {"subject": "organization/org-x", "kind": "event", "tick": 847,
         "severity": "critical", "actor": "The Vanguard",
         "text": "storms the compound"},
        {"subject": "organization/org-y", "kind": "event", "tick": 847,
         "severity": "informational", "actor": null,
         "text": "logs a routine report"}
    ]
}"#;

const BANNER_ONLY_FIXTURE: &str = r#"{
    "autopause_line": "AUTOPAUSE NOW",
    "rows": [
        {"subject": "organization/org-z", "kind": "event", "tick": 5,
         "severity": "informational", "actor": null,
         "text": "first event happens"}
    ]
}"#;

const EMPTY_FIXTURE: &str = r#"{"autopause_line": null, "rows": []}"#;

const SKIP_FIXTURE: &str = r#"{
    "autopause_line": null,
    "rows": [
        {"subject": null, "kind": "header", "tick": 10, "severity": null,
         "actor": null, "text": "T0010"},
        {"subject": "organization/org-a", "kind": "event", "tick": 10,
         "severity": "informational", "actor": null, "text": "first"},
        {"subject": null, "kind": "header", "tick": 9, "severity": null,
         "actor": null, "text": "T0009"},
        {"subject": "organization/org-b", "kind": "event", "tick": 9,
         "severity": "informational", "actor": null, "text": "second"}
    ]
}"#;

const NO_BANNER_FIXTURE: &str = r#"{
    "autopause_line": null,
    "rows": [
        {"subject": null, "kind": "header", "tick": 3, "severity": null,
         "actor": null, "text": "T0003"},
        {"subject": "organization/org-c", "kind": "event", "tick": 3,
         "severity": "critical", "actor": null, "text": "no warnings here"}
    ]
}"#;

/// Draws `rail` into a fresh `TestBackend` of the given size.
fn draw(rail: &mut ChronicleRail, width: u16, height: u16) -> Terminal<TestBackend> {
    let backend = TestBackend::new(width, height);
    let mut terminal = Terminal::new(backend).unwrap();
    terminal
        .draw(|frame| rail.render(frame, frame.area(), true))
        .unwrap();
    terminal
}

/// Dumps a `TestBackend` buffer's visible text, one `String` per row.
fn buffer_lines(terminal: &Terminal<TestBackend>) -> Vec<String> {
    let buffer = terminal.backend().buffer();
    let area = buffer.area;
    (area.top()..area.bottom())
        .map(|y| {
            (area.left()..area.right())
                .map(|x| buffer[(x, y)].symbol())
                .collect::<String>()
        })
        .collect()
}

/// The `(fg, modifier)` style of `needle`'s first character, scanning the
/// rendered buffer row by row. Panics if `needle` never appears.
fn style_at(terminal: &Terminal<TestBackend>, needle: &str) -> (Color, Modifier) {
    let buffer = terminal.backend().buffer();
    let area = buffer.area;
    for y in area.top()..area.bottom() {
        let cells: Vec<&str> = (area.left()..area.right())
            .map(|x| buffer[(x, y)].symbol())
            .collect();
        let row = cells.concat();
        if let Some(byte_pos) = row.find(needle) {
            let char_index = row[..byte_pos].chars().count();
            let x = area.left() + char_index as u16;
            let cell = &buffer[(x, y)];
            return (cell.fg, cell.modifier);
        }
    }
    panic!(
        "substring {needle:?} not found in rendered buffer:\n{}",
        buffer_lines(terminal).join("\n")
    );
}

#[test]
fn mixed_fixture_renders_exact_colors_including_module_amber_banner() {
    let mut rail = ChronicleRail::default();
    rail.update_from_json(MIXED_FIXTURE);
    let terminal = draw(&mut rail, 60, 8);

    let (banner_fg, banner_mod) = style_at(&terminal, "AUTOPAUSE");
    assert_eq!(banner_fg, AMBER, "banner should carry module AMBER");
    assert!(banner_mod.contains(Modifier::BOLD), "banner should be bold");

    let (header_fg, header_mod) = style_at(&terminal, "T0847");
    assert_eq!(header_fg, GOLD);
    assert!(header_mod.contains(Modifier::BOLD));

    let (actor_fg, actor_mod) = style_at(&terminal, "The Vanguard");
    assert_eq!(actor_fg, GOLD, "actor prefix is bold GOLD");
    assert!(actor_mod.contains(Modifier::BOLD));

    let (critical_fg, critical_mod) = style_at(&terminal, "storms the compound");
    assert_eq!(critical_fg, CRIMSON, "critical severity is bold CRIMSON");
    assert!(critical_mod.contains(Modifier::BOLD));

    let (info_fg, info_mod) = style_at(&terminal, "logs a routine report");
    assert_eq!(info_fg, BONE, "informational severity is BONE");
    assert!(!info_mod.contains(Modifier::BOLD));
}

#[test]
fn autopause_banner_renders_as_the_first_content_line() {
    let mut rail = ChronicleRail::default();
    rail.update_from_json(BANNER_ONLY_FIXTURE);
    let terminal = draw(&mut rail, 50, 6);
    let lines = buffer_lines(&terminal);

    // lines[0] is the top border; lines[1] is the first content row.
    assert!(lines[1].contains("AUTOPAUSE NOW"), "{lines:?}");
    assert!(
        !lines[1].contains("first event happens"),
        "the banner must precede every row, not share its line: {lines:?}"
    );
}

#[test]
fn empty_rail_with_no_banner_renders_the_honest_absence_line() {
    let mut rail = ChronicleRail::default();
    rail.update_from_json(EMPTY_FIXTURE);
    let terminal = draw(&mut rail, 50, 6);

    let (fg, modifier) = style_at(&terminal, "the wire is quiet");
    assert_eq!(fg, CRIMSON);
    assert!(modifier.contains(Modifier::BOLD));
}

#[test]
fn a_malformed_payload_renders_the_loud_unreadable_state() {
    let mut rail = ChronicleRail::default();
    rail.update_from_json("not json");
    assert!(rail.parse_failed);

    let terminal = draw(&mut rail, 50, 6);
    let (fg, _) = style_at(&terminal, "UNREADABLE");
    assert_eq!(fg, CRIMSON);
}

#[test]
fn cursor_skips_null_subject_rows_and_enter_opens_the_highlighted_subject() {
    let mut rail = ChronicleRail::default();
    rail.update_from_json(SKIP_FIXTURE);
    // Index 0 is the header (non-navigable); the cursor opens on index 1.
    assert_eq!(rail.cursor, Some(1));

    assert!(rail.handle_key(KeyCode::Down).is_none());
    // Index 2 is a tick header (non-navigable) — Down must skip straight to 3.
    assert_eq!(rail.cursor, Some(3));

    let event = rail.handle_key(KeyCode::Enter);
    assert_eq!(
        event,
        Some(AppEvent::OpenSubject("organization/org-b".to_string()))
    );

    assert!(rail.handle_key(KeyCode::Up).is_none());
    assert_eq!(
        rail.cursor,
        Some(1),
        "Up skips back over the same header row"
    );

    // Clamped, never wrapping, at the top navigable row.
    assert!(rail.handle_key(KeyCode::Up).is_none());
    assert_eq!(rail.cursor, Some(1));
}

#[test]
fn no_banner_means_no_amber_cell_anywhere_in_the_rail() {
    let mut rail = ChronicleRail::default();
    rail.update_from_json(NO_BANNER_FIXTURE);
    let terminal = draw(&mut rail, 50, 6);
    let buffer = terminal.backend().buffer();
    let area = buffer.area;
    for y in area.top()..area.bottom() {
        for x in area.left()..area.right() {
            assert_ne!(
                buffer[(x, y)].fg,
                AMBER,
                "no autopause banner is active, so AMBER must not appear at ({x}, {y})"
            );
        }
    }
}
