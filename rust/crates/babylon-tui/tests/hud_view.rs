//! Behavior tests for `babylon_tui::views::hud::HudStrip` (plan Task 24,
//! contract `docs/superpowers/specs/2026-07-27-m2-seam-contracts.md` §4,
//! §1).
//!
//! Layout note: line 2's five gauges render in the fixed `AXIS_KEYS` order
//! (REV, ECO, FAS, OGV, FRG), each as a 17-cell block — `"{ABBREV} ["` (5
//! cells) + a 10-cell bar + `"] "` (2 cells) — so REV's bar sits at
//! columns 5..15, ECO's at 22..32, FAS's at 39..49, OGV's at 56..66, and
//! FRG's at 73..83 on row 1 of the strip. Several tests below index those
//! columns directly rather than searching for them, since they are
//! pinned by `hud.rs`'s own module docs, not incidental.

use babylon_tui::theme::{BONE, CRIMSON, DIM, GOLD};
use babylon_tui::views::hud::HudStrip;
use ratatui::backend::TestBackend;
use ratatui::style::Modifier;
use ratatui::Terminal;

/// Contract §4's own tick-0 example: a bound campaign with every axis at
/// honest `0.0` progress — real data, NOT the pre-bind absence.
const ALL_ZERO_AXES: &str = r#"{"pattern": null, "outcome": "in_progress", "game_over": false,
 "horizon_tick": 27040, "since_tick": null, "locked": false,
 "axes": {"revolutionary_victory": 0.0, "ecological_collapse": 0.0,
          "fascist_consolidation": 0.0, "red_ogv": 0.0,
          "fragmented_collapse": 0.0}}"#;

/// An `endgame_status_json` payload with exactly one axis key present —
/// every other axis is entirely ABSENT from the object (not merely
/// zeroed), exercising the honest-missing-key fallback alongside whatever
/// `axis_value`/`progress` the test wants to isolate.
fn payload_with_one_axis(axis_key: &str, axis_value: f64) -> String {
    format!(
        r#"{{"pattern": null, "outcome": "in_progress", "game_over": false,
 "horizon_tick": 27040, "since_tick": null, "locked": false,
 "axes": {{"{axis_key}": {axis_value}}}}}"#
    )
}

/// A payload where `pattern` is currently recognized and held.
fn payload_with_pattern(pattern: &str, since_tick: u64, axis_key: &str, axis_value: f64) -> String {
    format!(
        r#"{{"pattern": "{pattern}", "outcome": "{pattern}", "game_over": false,
 "horizon_tick": 27040, "since_tick": {since_tick}, "locked": true,
 "axes": {{"{axis_key}": {axis_value}}}}}"#
    )
}

/// Dumps a `TestBackend` buffer's visible text, one line per row.
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

/// Renders `strip` into a backend wide enough for all five gauges (85
/// cells, see the module docs) plus headroom, and tall enough for the
/// 3-line strip.
fn draw(strip: &mut HudStrip) -> Terminal<TestBackend> {
    let backend = TestBackend::new(100, 4);
    let mut terminal = Terminal::new(backend).unwrap();
    terminal
        .draw(|frame| strip.render(frame, frame.area()))
        .unwrap();
    terminal
}

#[test]
fn tick_zero_all_zero_axes_renders_five_empty_bars_not_absence() {
    let mut strip = HudStrip::new();
    strip.set_tick(0);
    strip.update_endgame(ALL_ZERO_AXES);
    let text = buffer_text(&draw(&mut strip));
    assert!(text.contains("T+0/27040"), "{text}");
    assert!(!text.contains("no campaign bound"), "{text}");
    for abbrev in ["REV", "ECO", "FAS", "OGV", "FRG"] {
        let marker = format!("{abbrev} [----------]");
        assert!(text.contains(&marker), "missing {marker} in:\n{text}");
    }
}

#[test]
fn null_payload_renders_the_honest_absence_line() {
    let mut strip = HudStrip::new();
    strip.update_endgame("null");
    let text = buffer_text(&draw(&mut strip));
    assert!(text.contains("hud: no campaign bound"), "{text}");
}

#[test]
fn absence_is_the_strips_default_before_any_update() {
    let mut strip = HudStrip::new();
    let text = buffer_text(&draw(&mut strip));
    assert!(text.contains("hud: no campaign bound"), "{text}");
}

#[test]
fn a_partial_progress_axis_renders_proportionally_filled_gold_cells() {
    let mut strip = HudStrip::new();
    strip.update_endgame(&payload_with_one_axis("revolutionary_victory", 0.42));
    let terminal = draw(&mut strip);
    let buffer = terminal.backend().buffer();
    // REV's bar occupies columns 5..15; round(0.42 * 10) == 4 filled cells.
    for x in 5..9 {
        assert_eq!(buffer[(x, 1)].symbol(), "█", "x={x}");
        assert_eq!(buffer[(x, 1)].fg, GOLD, "x={x}");
    }
    for x in 9..15 {
        assert_eq!(buffer[(x, 1)].symbol(), "-", "x={x}");
        assert_eq!(buffer[(x, 1)].fg, DIM, "x={x}");
    }
}

#[test]
fn a_triggered_axis_renders_bold_crimson_and_the_pattern_suffix_appears_on_line_one() {
    let mut strip = HudStrip::new();
    strip.set_tick(600);
    strip.update_endgame(&payload_with_pattern(
        "revolutionary_victory",
        500,
        "revolutionary_victory",
        1.0,
    ));
    let terminal = draw(&mut strip);
    let buffer = terminal.backend().buffer();
    let text = buffer_text(&terminal);
    assert!(text.contains("T+600/27040"), "{text}");
    assert!(text.contains("REVOLUTIONARY VICTORY since T500"), "{text}");
    // REV's bar (columns 5..15) is fully filled and triggered: bold CRIMSON
    // end to end, no GOLD/DIM split.
    for x in 5..15 {
        assert_eq!(buffer[(x, 1)].symbol(), "█", "x={x}");
        assert_eq!(buffer[(x, 1)].fg, CRIMSON, "x={x}");
        assert!(
            buffer[(x, 1)].modifier.contains(Modifier::BOLD),
            "x={x} should be bold"
        );
    }
}

#[test]
fn a_missing_axis_key_renders_an_honest_empty_bar() {
    let mut strip = HudStrip::new();
    // "red_ogv" (the OGV gauge) is entirely absent from this fixture.
    strip.update_endgame(&payload_with_one_axis("revolutionary_victory", 0.0));
    let terminal = draw(&mut strip);
    let buffer = terminal.backend().buffer();
    // OGV's bar occupies columns 56..66.
    for x in 56..66 {
        assert_eq!(
            buffer[(x, 1)].symbol(),
            "-",
            "missing-key axis should read honest 0.0 (empty), x={x}"
        );
        assert_eq!(buffer[(x, 1)].fg, DIM, "x={x}");
    }
}

#[test]
fn pacing_unattached_renders_its_exact_line() {
    let mut strip = HudStrip::new();
    strip.update_endgame(ALL_ZERO_AXES);
    strip.update_pacing(
        r#"{"attached": false, "locked": false, "lock_reason": null,
        "awaiting_ack": false, "pause_summary": null, "busy": false}"#,
    );
    let text = buffer_text(&draw(&mut strip));
    assert!(text.contains("PACING: no paced driver attached"), "{text}");
}

#[test]
fn pacing_locked_renders_its_exact_line_bold_crimson() {
    let mut strip = HudStrip::new();
    strip.update_endgame(ALL_ZERO_AXES);
    strip.update_pacing(
        r#"{"attached": true, "locked": true, "lock_reason": "pattern held",
        "awaiting_ack": false, "pause_summary": null, "busy": false}"#,
    );
    let terminal = draw(&mut strip);
    let text = buffer_text(&terminal);
    assert!(text.contains("PACING: LOCKED — pattern held"), "{text}");
    let buffer = terminal.backend().buffer();
    let x = text.lines().nth(2).unwrap().find('P').unwrap() as u16;
    assert_eq!(buffer[(x, 2)].fg, CRIMSON);
    assert!(buffer[(x, 2)].modifier.contains(Modifier::BOLD));
}

#[test]
fn pacing_awaiting_ack_renders_its_exact_line_in_amber() {
    let mut strip = HudStrip::new();
    strip.update_endgame(ALL_ZERO_AXES);
    strip.update_pacing(
        r#"{"attached": true, "locked": false, "lock_reason": null,
        "awaiting_ack": true, "pause_summary": "3 events", "busy": false}"#,
    );
    let terminal = draw(&mut strip);
    let text = buffer_text(&terminal);
    assert!(
        text.contains("PACING: autopause pending (3 events) — press 'a' to acknowledge"),
        "{text}"
    );
    let buffer = terminal.backend().buffer();
    let x = text.lines().nth(2).unwrap().find('P').unwrap() as u16;
    assert_eq!(buffer[(x, 2)].fg, ratatui::style::Color::Rgb(255, 140, 0));
}

#[test]
fn pacing_busy_renders_its_exact_line() {
    let mut strip = HudStrip::new();
    strip.update_endgame(ALL_ZERO_AXES);
    strip.update_pacing(
        r#"{"attached": true, "locked": false, "lock_reason": null,
        "awaiting_ack": false, "pause_summary": null, "busy": true}"#,
    );
    let text = buffer_text(&draw(&mut strip));
    assert!(
        text.contains("PACING: a run is already in progress"),
        "{text}"
    );
}

#[test]
fn pacing_ready_renders_its_exact_line_in_bone() {
    let mut strip = HudStrip::new();
    strip.update_endgame(ALL_ZERO_AXES);
    strip.update_pacing(
        r#"{"attached": true, "locked": false, "lock_reason": null,
        "awaiting_ack": false, "pause_summary": null, "busy": false}"#,
    );
    let terminal = draw(&mut strip);
    let text = buffer_text(&terminal);
    assert!(text.contains("PACING: ready"), "{text}");
    let buffer = terminal.backend().buffer();
    let x = text.lines().nth(2).unwrap().find('P').unwrap() as u16;
    assert_eq!(buffer[(x, 2)].fg, BONE);
}

#[test]
fn a_malformed_endgame_payload_renders_the_loud_unreadable_line() {
    let mut strip = HudStrip::new();
    strip.update_endgame("not json");
    let terminal = draw(&mut strip);
    let text = buffer_text(&terminal);
    assert!(text.contains("hud UNREADABLE"), "{text}");
    let buffer = terminal.backend().buffer();
    let x = text.lines().next().unwrap().find('▌').unwrap() as u16;
    assert_eq!(buffer[(x, 0)].fg, CRIMSON);
}

#[test]
fn a_malformed_pacing_payload_renders_the_loud_unreadable_pacing_line_only() {
    let mut strip = HudStrip::new();
    strip.update_endgame(ALL_ZERO_AXES);
    strip.update_pacing("not json");
    let terminal = draw(&mut strip);
    let text = buffer_text(&terminal);
    // Lines 1-2 still render normally — a broken pacing feed says nothing
    // about whether the endgame feed is readable.
    assert!(text.contains("T+0/27040"), "{text}");
    assert!(text.contains("REV [----------]"), "{text}");
    assert!(text.contains("PACING: UNREADABLE"), "{text}");
    let buffer = terminal.backend().buffer();
    let x = text.lines().nth(2).unwrap().find('P').unwrap() as u16;
    assert_eq!(buffer[(x, 2)].fg, CRIMSON);
}
