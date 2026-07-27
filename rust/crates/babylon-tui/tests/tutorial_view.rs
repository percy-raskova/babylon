//! Snapshot tests for the tutorial overlay strip (plan Task 27, contract
//! `docs/superpowers/specs/2026-07-27-m3-tutorial-contracts.md` §1): an
//! active step with the Patches line, the finished state, the loud
//! UNREADABLE strip, and the 40%-height clamp over a tall body. Follows the
//! crate's existing insta-snapshot convention (`hello_frame.rs`,
//! `raster_skeleton.rs`): `insta::assert_snapshot!(format!("{:?}", buffer))`
//! over a `TestBackend` buffer.

use babylon_tui::views::tutorial::TutorialOverlayView;
use ratatui::backend::TestBackend;
use ratatui::buffer::Buffer;
use ratatui::Terminal;

/// Render `view` into a fresh `width`x`height` `TestBackend` buffer.
fn draw(view: &TutorialOverlayView, width: u16, height: u16) -> Buffer {
    let backend = TestBackend::new(width, height);
    let mut terminal = Terminal::new(backend).expect("backend");
    terminal
        .draw(|frame| view.render(frame, frame.area()))
        .expect("frame renders");
    terminal.backend().buffer().clone()
}

/// Dumps a `TestBackend` buffer's visible text, one line per row.
fn buffer_text(buffer: &Buffer) -> String {
    let area = buffer.area;
    (0..area.height)
        .map(|row| {
            (0..area.width)
                .map(|col| buffer[(col, row)].symbol())
                .collect::<String>()
                .trim_end()
                .to_string()
        })
        .collect::<Vec<_>>()
        .join("\n")
}

#[test]
fn inactive_renders_nothing() {
    let view = TutorialOverlayView::new();
    let buffer = draw(&view, 80, 10);
    let text = buffer_text(&buffer);
    assert!(
        text.chars().all(char::is_whitespace),
        "the honest-absence state drew something:\n{text}"
    );
}

#[test]
fn active_step_with_patches_line() {
    let mut view = TutorialOverlayView::new();
    view.update_from_json(
        r#"{"active": true, "finished": false, "step_index": 3, "total": 22,
            "step_id": "run_until_autopause",
            "heading": "Step 4/22: Given the campaign is bound, when the player presses 'r', then the driver runs until autopause.",
            "patches": "Now let the weeks roll — the engine stops us the instant something critical fires.",
            "body": "GIVEN: the campaign is bound\nWHEN: the player presses 'r'\nTHEN: the driver runs until autopause"}"#,
    );
    // 20 rows: 40% = 8 ≥ the 7-row content, so THIS golden shows the whole
    // strip (heading + Patches + all three body lines); the 40%-clamp
    // clipping behavior has its own dedicated test below.
    let buffer = draw(&view, 100, 20);
    let text = buffer_text(&buffer);
    assert!(
        text.contains("Patches: Now let the weeks roll"),
        "Patches line missing:\n{text}"
    );
    assert!(text.contains("Step 4/22"), "heading missing:\n{text}");
    assert!(
        text.contains("GIVEN: the campaign is bound"),
        "body lines missing:\n{text}"
    );
    insta::assert_snapshot!(format!("{buffer:?}"));
}

#[test]
fn finished_state_renders_its_two_strings() {
    let mut view = TutorialOverlayView::new();
    view.update_from_json(
        r#"{"active": true, "finished": true, "step_index": 22, "total": 22,
            "step_id": null, "heading": "Opening arc complete.",
            "patches": null, "body": "Press Escape to dismiss this tutorial."}"#,
    );
    let buffer = draw(&view, 100, 12);
    let text = buffer_text(&buffer);
    assert!(
        text.contains("Opening arc complete."),
        "finished heading missing:\n{text}"
    );
    assert!(
        text.contains("Press Escape to dismiss this tutorial."),
        "finished body missing:\n{text}"
    );
    assert!(
        !text.contains("Patches:"),
        "the finished state must carry no Patches line:\n{text}"
    );
    insta::assert_snapshot!(format!("{buffer:?}"));
}

#[test]
fn malformed_payload_renders_the_unreadable_strip() {
    let mut view = TutorialOverlayView::new();
    view.update_from_json("not json");
    let buffer = draw(&view, 80, 8);
    let text = buffer_text(&buffer);
    assert!(
        text.contains("tutorial UNREADABLE — malformed host data"),
        "UNREADABLE strip missing:\n{text}"
    );
    insta::assert_snapshot!(format!("{buffer:?}"));
}

#[test]
fn a_tall_body_clamps_to_forty_percent_of_the_area() {
    let mut view = TutorialOverlayView::new();
    // 20 body lines + heading + Patches = 22 content lines; +2 border rows
    // = 24 — exactly the whole area, so an unclamped strip would swallow
    // the entire 24-row frame. 40% of 24 is 9 (integer division): the
    // strip must stop there instead.
    let body_lines: Vec<String> = (1..=20).map(|n| format!("line {n}")).collect();
    let body = body_lines.join("\n");
    let payload = serde_json::json!({
        "active": true, "finished": false, "step_index": 0, "total": 1,
        "step_id": "s", "heading": "Step 1/1: h", "patches": "p", "body": body,
    })
    .to_string();
    view.update_from_json(&payload);
    let buffer = draw(&view, 80, 24);
    let text = buffer_text(&buffer);
    let drawn_rows = text.lines().filter(|line| !line.trim().is_empty()).count();
    assert_eq!(
        drawn_rows, 9,
        "the strip did not clamp to 40% of the 24-row area:\n{text}"
    );
    insta::assert_snapshot!(format!("{buffer:?}"));
}
