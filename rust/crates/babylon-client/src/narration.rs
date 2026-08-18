//! The narration templates (B3 wave-1 Task 4, plan
//! `docs/superpowers/plans/2026-08-17-b3-null-hypothesis-viewer.md` §2.2/
//! §2.3): [`NARRATION_TABLE`] transcribes one sentence per landed
//! `EventType` — the four carceral beats from the frozen systems' own
//! `narrative_hint` copy (`decomposition.py`/`control_ratio.py`, §2.2 point
//! 4), the four counties-story events from
//! `src/babylon/game/chronicle_adapter.py::_SUMMARY_BUILDERS`'s own
//! wording — plus, for the four critical rows, the transcribed `because:`
//! causal line (§2.3). Every `{slot}` binds to a named wire payload key
//! (never a pydantic field name); a key the payload does not carry renders
//! the literal text `{absent}`; a key `§2.6`'s I2 table declares a
//! structural non-computation renders its reason, never the literal
//! numeral the payload happens to hold. `{subject}` is the one reserved
//! non-wire slot name — it renders the resolved display of the row's own
//! declared `subject_key` (Minor 2), never guessed.
//!
//! **`TERMINAL_DECISION` is payload-conditional, not slot-conditional
//! (§2.2 point 4).** `control_ratio.py:221-232`'s two `narrative_hint`
//! branches (GENOCIDE / REVOLUTION) are two ENTIRELY DIFFERENT sentences,
//! neither containing a `{slot}` — a single `NarrationSpec.template`
//! cannot express a payload-conditional CHOICE of whole sentence, so that
//! one dispatch lives beside the table (`terminal_decision_template`)
//! rather than inside it. An `outcome` value that is neither `0` nor `1`
//! falls through to the generic line, same discipline as an unverified
//! `EventType`.
//!
//! **The drift guard.** `tests/unit/render/test_rust_narration_parity.py`
//! (Task 4.6) parses [`NARRATION_TABLE`] and asserts every template's
//! wire-key slots are keys `babylon.engine.event_builders.EVENT_BUILDERS`
//! (or, for the handful of slots BSL's payload-flattening/EVENT_BUILDERS'
//! own incompleteness makes unverifiable that way, the frozen system's own
//! raw `payload={...}` dict literal — a documented, cited, narrow
//! exemption, never a silent gap) actually reads for that `EventType`.
//!
//! RED (this commit): none of `NarrationSpec`, `NARRATION_TABLE`,
//! `spec_for`, `render` exist yet — the test module below fails to
//! compile, mirroring the `d4f353d9` "module absent" RED-commit precedent.

#[cfg(test)]
mod tests {
    use super::{render, spec_for};
    use babylon_bsl::evaluator::Value;

    /// The frozen mirror's own tick-53 payload
    /// (`carceral_arc_conformance.rs:60`), flattened to the wire keys
    /// `decomposition.bsl:377-386` actually emits.
    fn class_decomposition_payload() -> Vec<(String, Value)> {
        vec![
            (
                "source-class".to_owned(),
                Value::NodeRef(babylon_graph::substrate::NodeId(0)),
            ),
            ("source-population".to_owned(), Value::Int(600)),
            ("source-wealth".to_owned(), Value::Real(515.0)),
            ("enforcer-fraction".to_owned(), Value::Real(0.15)),
            ("proletariat-fraction".to_owned(), Value::Real(0.85)),
            (
                "population-transferred-to-enforcer".to_owned(),
                Value::Int(90),
            ),
            (
                "population-transferred-to-proletariat".to_owned(),
                Value::Int(510),
            ),
            (
                "wealth-transferred-to-enforcer".to_owned(),
                Value::Real(77.25),
            ),
            (
                "wealth-transferred-to-proletariat".to_owned(),
                Value::Real(437.75),
            ),
        ]
    }

    #[test]
    fn class_decomposition_renders_the_frozen_mirrors_exact_copy() {
        let rendered = render(
            "CLASS_DECOMPOSITION",
            &class_decomposition_payload(),
            "world",
        );
        assert_eq!(
            rendered.headline,
            "CLASS DECOMPOSITION: Labor aristocracy collapses. 90 become guards/cops. \
             510 fall into the precariat."
        );
    }

    fn terminal_decision_payload(outcome: i64) -> Vec<(String, Value)> {
        vec![
            ("outcome".to_owned(), Value::Int(outcome)),
            (
                "avg-organization".to_owned(),
                Value::Real(0.056_338_028_169_014_086),
            ),
            ("revolution-threshold".to_owned(), Value::Real(0.5)),
            ("prisoner-population".to_owned(), Value::Int(710)),
            ("enforcer-population".to_owned(), Value::Int(110)),
        ]
    }

    #[test]
    fn terminal_decision_outcome_zero_renders_the_genocide_copy() {
        let rendered = render("TERMINAL_DECISION", &terminal_decision_payload(0), "world");
        assert!(
            rendered.headline.contains("GENOCIDE"),
            "outcome 0 must render the GENOCIDE copy, got {:?}",
            rendered.headline
        );
        assert!(!rendered.headline.contains("REVOLUTION"));
    }

    #[test]
    fn terminal_decision_outcome_one_renders_the_revolution_copy() {
        let rendered = render("TERMINAL_DECISION", &terminal_decision_payload(1), "world");
        assert!(
            rendered.headline.contains("REVOLUTION"),
            "outcome 1 must render the REVOLUTION copy, got {:?}",
            rendered.headline
        );
        assert!(!rendered.headline.contains("GENOCIDE"));
    }

    #[test]
    fn a_payload_missing_a_slot_key_renders_the_literal_absent_marker_for_that_slot_only() {
        let mut payload = class_decomposition_payload();
        payload.retain(|(k, _)| k != "population-transferred-to-enforcer");
        let rendered = render("CLASS_DECOMPOSITION", &payload, "world");
        assert_eq!(
            rendered.headline,
            "CLASS DECOMPOSITION: Labor aristocracy collapses. {absent} become guards/cops. \
             510 fall into the precariat.",
            "only the missing slot renders {{absent}} — the rest of the sentence is unchanged"
        );
    }

    /// §2.6/I2's declared `SUPERWAGE_CRISIS.desired-wages` row — even
    /// though no SHIPPED template references this slot (the frozen
    /// `narrative_hint` never mentions the dollar figures either), the
    /// renderer's own NotComputed discipline must hold for it directly.
    #[test]
    fn a_declared_not_computed_key_renders_its_reason_and_no_numeral() {
        let payload = vec![
            (
                "receiver".to_owned(),
                Value::NodeRef(babylon_graph::substrate::NodeId(0)),
            ),
            ("desired-wages".to_owned(), Value::Real(0.0)),
            ("available-pool".to_owned(), Value::Real(0.0)),
        ];
        let rendered = super::substitute(
            "SUPERWAGE_CRISIS",
            "wages: {desired-wages}",
            &payload,
            "world",
        );
        assert!(
            !rendered.chars().any(|c| c.is_ascii_digit()),
            "a NotComputed slot must render its reason, never the literal 0.0 the \
             payload happens to hold — got {rendered:?}"
        );
        assert!(rendered.contains("not computed by this port"));
    }

    #[test]
    fn an_unknown_event_type_falls_through_to_the_generic_line() {
        let rendered = render("SOME_UNVERIFIED_EVENT_TYPE", &[], "world");
        assert_eq!(rendered.headline, "SOME_UNVERIFIED_EVENT_TYPE @ world");
        assert!(rendered.because.is_none());
    }

    // ---- §2.3's because: line, the four critical rows ----

    #[test]
    fn each_critical_row_renders_its_transcribed_because_line() {
        for event_type in [
            "SUPERWAGE_CRISIS",
            "CLASS_DECOMPOSITION",
            "CONTROL_RATIO_CRISIS",
            "TERMINAL_DECISION",
        ] {
            let spec = spec_for(event_type)
                .unwrap_or_else(|| panic!("{event_type} must have a declared NarrationSpec"));
            assert!(
                spec.because.is_some(),
                "{event_type} is one of the four critical rows — it must declare a because: line"
            );
        }
    }

    #[test]
    fn terminal_decisions_because_line_binds_its_threshold_slots() {
        let rendered = render("TERMINAL_DECISION", &terminal_decision_payload(0), "world");
        let because = rendered
            .because
            .expect("TERMINAL_DECISION must render a because: line");
        assert!(
            because.contains("0.5"),
            "the because: line must bind {{revolution-threshold}} to the real payload \
             value, got {because:?}"
        );
        assert!(
            !because.contains('{') && !because.contains('}'),
            "every slot in the because: line must have been bound — no leftover \
             {{brace}} placeholders, got {because:?}"
        );
    }

    /// A beat whose row declares no `because:` (every non-critical row)
    /// renders no second line at all — never an empty one.
    #[test]
    fn a_beat_with_no_because_row_renders_no_second_line_at_all() {
        let payload = vec![
            (
                "territory-id".to_owned(),
                Value::NodeRef(babylon_graph::substrate::NodeId(0)),
            ),
            ("legitimation-index".to_owned(), Value::Real(0.62)),
        ];
        let rendered = render("LEGITIMATION_RECOVERY", &payload, "01013");
        assert!(
            rendered.because.is_none(),
            "LEGITIMATION_RECOVERY declares no because: row — rendering must be None, \
             never Some(String::new())"
        );
    }
}
