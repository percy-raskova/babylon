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
use ratatui::layout::Rect;
use ratatui::Terminal;

/// Render `view` into a fresh `width`x`height` `TestBackend` buffer: sizes
/// the strip band via [`TutorialOverlayView::height_for`] exactly like the
/// integrator (`app.rs`) now does (R1), then renders into that exact rect
/// — `render()` no longer self-clamps; the band is the caller's to size.
fn draw(view: &TutorialOverlayView, width: u16, height: u16) -> Buffer {
    let backend = TestBackend::new(width, height);
    let mut terminal = Terminal::new(backend).expect("backend");
    terminal
        .draw(|frame| {
            let area = frame.area();
            let strip_height = view.height_for(width, height);
            let strip = Rect {
                x: area.x,
                y: area.y,
                width: area.width,
                height: strip_height,
            };
            view.render(frame, strip);
        })
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

/// Dumps just `rect`'s interior as ONE space-joined string, row by row —
/// unlike [`buffer_text`], which dumps the WHOLE buffer width per row
/// (including the strip's own left/right border characters), so joining
/// its rows with a plain space would splice a stray `│ │` between two
/// physical rows of the SAME wrapped logical line. Used only to check that
/// a phrase surviving `Wrap { trim: false }` across a row boundary reads
/// back as one contiguous run of words (word-wrap replaces exactly the
/// separating space with the row break, so rejoining with a space
/// reconstructs the original spacing).
fn inner_text_flat(buffer: &Buffer, rect: Rect) -> String {
    (rect.y..rect.y + rect.height)
        .map(|row| {
            (rect.x..rect.x + rect.width)
                .map(|col| buffer[(col, row)].symbol())
                .collect::<String>()
                .trim_end()
                .to_string()
        })
        .collect::<Vec<_>>()
        .join(" ")
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
    // 20 rows: with `Wrap { trim: false }` the 106-char heading now wraps
    // to 2 physical rows at this canvas's 98-column inner width (Patches
    // and every body line still fit on one row each) — 2 heading + 1
    // Patches + 3 body = 6 content rows, +2 border rows = 8; 40% of 20 is
    // 8, so THIS golden shows the whole strip uncropped. The 40%-clamp
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
    // R3 fix, full Patches sentence: at this canvas's 98-column inner
    // width the 91-char Patches line fits on ONE physical row (unlike the
    // heading below), so the plain buffer dump already reads it back
    // contiguously — no un-wrapped `Paragraph` silently dropped its tail.
    assert!(
        text.contains(
            "Now let the weeks roll — the engine stops us the instant something critical fires."
        ),
        "the full Patches sentence did not survive wrapping:\n{text}"
    );
    // R3/R4 fix, heading tail: the 106-char heading DOES exceed the
    // 98-column inner width, so `Wrap { trim: false }` breaks it across two
    // physical rows — reassemble just the strip's INTERIOR (never the
    // whole-buffer dump, whose per-row border characters would splice a
    // stray `│ │` into the join) with a single space per row boundary
    // (exactly what word-wrap replaced with the row break) before asserting
    // the tail survived INTACT, rather than merely being truncated the way
    // an un-wrapped `Paragraph` used to silently drop it.
    let strip_height = view.height_for(100, 20);
    let inner = Rect {
        x: 1,
        y: 1,
        width: 100 - 2,
        height: strip_height.saturating_sub(2),
    };
    let flat_inner = inner_text_flat(&buffer, inner);
    assert!(
        flat_inner.contains("then the driver runs until autopause."),
        "the heading's full tail did not survive wrapping:\n{text}"
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
