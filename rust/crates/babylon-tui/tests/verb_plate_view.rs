//! Behavior tests for `babylon_tui::views::verbs::VerbPlateView`.
//!
//! Fixtures are built to contract §3's own shape
//! (`docs/superpowers/specs/2026-07-27-m2-seam-contracts.md`):
//! `VerbPlateView.model_dump_json()` — every `VerbRow` key present
//! (including explicit `null`s), canonical verb order `educate, reproduce,
//! attack, mobilize, campaign, aid, investigate, move, negotiate`.

use babylon_tui::layout_registry::LayoutRegistry;
use babylon_tui::views::verbs::VerbPlateView;
use ratatui::backend::TestBackend;
use ratatui::Terminal;
use serde_json::{json, Value};

/// One well-formed `VerbRow` object, every key present per the contract's
/// `extra='forbid'` pydantic model (a real payload never omits a key, even
/// when its value is `null`).
#[allow(clippy::too_many_arguments)]
fn row(
    verb: &str,
    eligible: bool,
    reason: Option<&str>,
    remedy: Option<&str>,
    can_afford: bool,
    afford_note: Option<&str>,
    candidate_target_ids: Vec<&str>,
) -> Value {
    json!({
        "verb": verb,
        "eligible": eligible,
        "reason": reason,
        "remedy": remedy,
        "can_afford": can_afford,
        "afford_note": afford_note,
        "preview": {
            "estimated_consciousness_delta": 0.01,
            "estimated_heat_delta": 0.01,
            "action_point_cost": 1.0,
            "success_probability": 0.7,
            "affected_territory_ids": [],
            "warnings": []
        },
        "candidate_target_ids": candidate_target_ids
    })
}

/// All nine rows, in canonical order, wrapping into a full `VerbPlateView`
/// payload. `attack` is ineligible (reason+remedy); `mobilize` is eligible
/// but unaffordable (afford_note); `investigate` carries two candidate
/// target ids for the [`VerbPlateView::row`] accessor test.
fn full_fixture_rows() -> Vec<Value> {
    vec![
        row("educate", true, None, None, true, None, vec![]),
        row("reproduce", true, None, None, true, None, vec![]),
        row(
            "attack",
            false,
            Some("target destroyed"),
            Some("scout a new target"),
            true,
            None,
            vec![],
        ),
        row(
            "mobilize",
            true,
            None,
            None,
            false,
            Some("short 2 AP"),
            vec!["territory/26163"],
        ),
        row(
            "campaign",
            true,
            None,
            None,
            true,
            None,
            vec!["social_class/proletariat"],
        ),
        row(
            "aid",
            true,
            None,
            None,
            true,
            None,
            vec!["social_class/proletariat"],
        ),
        row(
            "investigate",
            true,
            None,
            None,
            true,
            None,
            vec!["territory/26163", "organization/org-x"],
        ),
        row(
            "move",
            true,
            None,
            None,
            true,
            None,
            vec!["territory/26163"],
        ),
        row(
            "negotiate",
            true,
            None,
            None,
            true,
            None,
            vec!["organization/org-x"],
        ),
    ]
}

fn plate_json(verbs: Vec<Value>) -> String {
    json!({
        "kind": "verb_plate",
        "org_id": "organization/vanguard",
        "tick": 42,
        "verbs": verbs
    })
    .to_string()
}

fn full_fixture() -> String {
    plate_json(full_fixture_rows())
}

/// A caller-truncated payload: `negotiate` (the ninth canonical verb)
/// dropped entirely, leaving eight rows.
fn truncated_fixture() -> String {
    let mut rows = full_fixture_rows();
    rows.pop(); // drops "negotiate"
    plate_json(rows)
}

/// Dumps a `TestBackend` buffer's visible text, one line per row, for
/// substring assertions (matches the crate's existing test convention).
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

/// Renders `view` into a backend tall enough (13 inner rows after the
/// 2-row border) that all 11 plate lines fit in a single column.
fn render_single_column(view: &VerbPlateView) -> String {
    let backend = TestBackend::new(80, 15);
    let mut terminal = Terminal::new(backend).unwrap();
    let mut registry = LayoutRegistry::new();
    terminal
        .draw(|frame| view.render(frame, frame.area(), &mut registry))
        .unwrap();
    buffer_text(&terminal)
}

#[test]
fn all_nine_verbs_render_with_positional_f_key_labels() {
    let view = VerbPlateView::open(&full_fixture());
    let text = render_single_column(&view);
    assert!(text.contains("F1 Educate"), "{text}");
    assert!(text.contains("F2 Reproduce"), "{text}");
    assert!(text.contains("F3 Attack"), "{text}");
    assert!(text.contains("F4 Mobilize"), "{text}");
    assert!(text.contains("F5 Campaign"), "{text}");
    assert!(text.contains("F6 Aid"), "{text}");
    assert!(text.contains("F8 Move"), "{text}");
    assert!(text.contains("F9 Negotiate"), "{text}");
}

#[test]
fn investigate_expands_to_three_sub_verb_lines_sharing_f7() {
    let view = VerbPlateView::open(&full_fixture());
    let text = render_single_column(&view);
    assert!(text.contains("F7 Investigate(Territory)"), "{text}");
    assert!(text.contains("F7 Investigate(Org)"), "{text}");
    assert!(text.contains("F7 Investigate(Edge)"), "{text}");
}

#[test]
fn an_ineligible_row_shows_its_reason_and_remedy_never_hidden() {
    let view = VerbPlateView::open(&full_fixture());
    let text = render_single_column(&view);
    assert!(text.contains("F3 Attack"), "{text}");
    assert!(text.contains("target destroyed"), "{text}");
    assert!(text.contains("scout a new target"), "{text}");
}

#[test]
fn an_unaffordable_row_stays_plain_and_shows_its_afford_note() {
    let view = VerbPlateView::open(&full_fixture());
    let text = render_single_column(&view);
    assert!(text.contains("F4 Mobilize"), "{text}");
    assert!(text.contains("short 2 AP"), "{text}");
    // Unaffordable never means the same thing as ineligible: no
    // reason/remedy parenthetical rides along an affordability note.
    assert!(!text.contains("F4 Mobilize  ("), "{text}");
}

#[test]
fn a_truncated_eight_row_payload_shows_a_loud_missing_marker() {
    let view = VerbPlateView::open(&truncated_fixture());
    let text = render_single_column(&view);
    assert!(
        text.contains("negotiate — missing from plate view"),
        "{text}"
    );
    // Every other verb still renders normally.
    assert!(text.contains("F1 Educate"), "{text}");
    assert!(text.contains("F8 Move"), "{text}");
}

#[test]
fn a_truncated_payloads_missing_verb_has_no_row_at_its_canonical_slot() {
    let view = VerbPlateView::open(&truncated_fixture());
    // "negotiate" is CANONICAL_VERBS[8] -> F9 -> row(8).
    assert!(view.row(8).is_none());
    // Every other slot is still populated.
    assert!(view.row(0).is_some());
}

#[test]
fn null_payload_renders_the_honest_absence_line() {
    let view = VerbPlateView::open("null");
    assert!(view.is_absent());
    assert!(!view.is_unreadable());
    let text = render_single_column(&view);
    assert!(text.contains("no verb plate — no campaign bound"), "{text}");
}

#[test]
fn garbage_payload_renders_the_loud_unreadable_state_not_absence() {
    let view = VerbPlateView::open("not json at all");
    assert!(view.is_unreadable());
    assert!(!view.is_absent());
    let text = render_single_column(&view);
    assert!(text.contains("UNREADABLE"), "{text}");
    assert!(!text.contains("no campaign bound"), "{text}");
}

#[test]
fn well_formed_json_with_the_wrong_shape_is_also_unreadable() {
    // Valid JSON, but not a VerbPlateView object (missing every required
    // key) — still a loud parse failure, never a fabricated empty plate.
    let view = VerbPlateView::open(r#"{"foo": "bar"}"#);
    assert!(view.is_unreadable());
}

#[test]
fn row_accessor_returns_parsed_candidate_target_ids() {
    let view = VerbPlateView::open(&full_fixture());
    // "investigate" is CANONICAL_VERBS[6] -> F7 -> row(6).
    let investigate_row = view.row(6).expect("investigate row present");
    assert_eq!(investigate_row.verb, "investigate");
    assert_eq!(
        investigate_row.candidate_target_ids,
        vec![
            "territory/26163".to_string(),
            "organization/org-x".to_string()
        ]
    );
    assert!(investigate_row.eligible);
}

#[test]
fn reproduce_row_has_empty_candidate_target_ids_self_targeting() {
    let view = VerbPlateView::open(&full_fixture());
    // "reproduce" is CANONICAL_VERBS[1] -> F2 -> row(1).
    let reproduce_row = view.row(1).expect("reproduce row present");
    assert_eq!(reproduce_row.verb, "reproduce");
    assert!(reproduce_row.candidate_target_ids.is_empty());
}

#[test]
fn two_column_layout_still_shows_every_line_when_area_is_too_short() {
    // Inner height after the 2-row border is 6 — fewer than the 11 plate
    // lines (one column can't fit them all), but enough for the two-column
    // fallback's taller side (ceil(11/2) == 6) to show everything.
    let backend = TestBackend::new(100, 8);
    let mut terminal = Terminal::new(backend).unwrap();
    let view = VerbPlateView::open(&full_fixture());
    let mut registry = LayoutRegistry::new();
    terminal
        .draw(|frame| view.render(frame, frame.area(), &mut registry))
        .unwrap();
    let text = buffer_text(&terminal);
    assert!(text.contains("F1 Educate"), "{text}");
    assert!(text.contains("F6 Aid"), "{text}");
    assert!(text.contains("F9 Negotiate"), "{text}");
    assert!(text.contains("F7 Investigate(Edge)"), "{text}");
}
