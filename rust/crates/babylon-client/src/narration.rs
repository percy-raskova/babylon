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

use babylon_bsl::evaluator::Value;

/// One declared row: the template + optional causal `because:` line for
/// one landed `EventType`, plus its own provenance (§2.2's `NarrationSpec`
/// shape). Every field is `&'static str`/`Option<&'static str>` — the
/// whole table is compile-time data, not a runtime construction.
#[derive(Debug, Clone, Copy)]
pub struct NarrationSpec {
    pub event_type: &'static str,
    /// The declared wire key naming the one `NodeRef` this beat is about
    /// (Minor 2 — never first-match-wins); `None` for a pure-aggregate
    /// payload, rendered at world scope (Minor 3).
    pub subject_key: Option<&'static str>,
    pub template: &'static str,
    pub because: Option<&'static str>,
    /// The frozen file, its line range, and the freeze tag — survives the
    /// Python engine deletion ceremony as the sole remaining provenance
    /// record (I7).
    pub source: &'static str,
}

/// The transcribed narration table (§2.2/§2.3) — one row per landed
/// `EventType` this wave's two shipped stories actually emit. One row per
/// line (the parity guard's own regex contract).
pub const NARRATION_TABLE: &[NarrationSpec] = &[
    NarrationSpec {
        event_type: "SUPERWAGE_CRISIS",
        subject_key: Some("receiver"),
        template: "SUPERWAGE CRISIS: Labor aristocracy wealth collapsing. Super-wages cannot sustain the privileged stratum.",
        because: Some("the labor aristocracy's wealth clears the approaching, not dying, gate \u{2014} super-wages can no longer sustain the privileged stratum"),
        source: "src/babylon/engine/systems/decomposition.py:189-192 @ p27-python-freeze",
    },
    NarrationSpec {
        event_type: "CLASS_DECOMPOSITION",
        subject_key: Some("source-class"),
        template: "CLASS DECOMPOSITION: Labor aristocracy collapses. {population-transferred-to-enforcer} become guards/cops. {population-transferred-to-proletariat} fall into the precariat.",
        because: Some("triggered by superwage_crisis, 52 ticks earlier (carceral/decomposition-delay, carceral-arc-conformance.bscn:17,137)"),
        source: "src/babylon/engine/systems/decomposition.py:361-365 @ p27-python-freeze",
    },
    NarrationSpec {
        event_type: "CONTROL_RATIO_CRISIS",
        subject_key: None,
        template: "CONTROL RATIO CRISIS: {prisoner-population} prisoners exceed {max-controllable} control capacity (1:{control-capacity} ratio). The carceral state cannot contain the surplus.",
        because: Some("triggered by class_decomposition, 52 ticks earlier (carceral/control-ratio-delay, carceral-arc-conformance.bscn:18,138) \u{2014} the prisoners exceed what the enforcers can hold"),
        source: "src/babylon/engine/systems/control_ratio.py:201-205 @ p27-python-freeze",
    },
    NarrationSpec {
        event_type: "TERMINAL_DECISION",
        subject_key: None,
        template: TERMINAL_DECISION_GENOCIDE,
        because: Some("the atomized surplus population cannot resist \u{2014} average organization {avg-organization} falls short of the revolution threshold {revolution-threshold}"),
        source: "src/babylon/engine/systems/control_ratio.py:228-232 @ p27-python-freeze",
    },
    NarrationSpec {
        event_type: "LIFECYCLE_TRANSITION",
        subject_key: Some("territory-id"),
        template: "{subject} lifecycle: D={pop-d} P={pop-p} D'={pop-d-prime} (dependency ratio {dependency-ratio})",
        because: None,
        source: "src/babylon/game/chronicle_adapter.py:409-413 @ p27-python-freeze",
    },
    NarrationSpec {
        event_type: "LEGITIMATION_CRISIS",
        subject_key: Some("territory-id"),
        template: "{subject} legitimation crisis (index {legitimation-index})",
        because: None,
        source: "src/babylon/game/chronicle_adapter.py:414-417 @ p27-python-freeze",
    },
    NarrationSpec {
        event_type: "LEGITIMATION_RECOVERY",
        subject_key: Some("territory-id"),
        template: "{subject} legitimation recovers (index {legitimation-index})",
        because: None,
        source: "src/babylon/game/chronicle_adapter.py:418-421 @ p27-python-freeze",
    },
    NarrationSpec {
        event_type: "ENTITY_DEATH",
        subject_key: Some("entity-id"),
        template: "{subject} dies: wealth {wealth} < needs {consumption-needs}",
        because: None,
        source: "src/babylon/game/chronicle_adapter.py:447-450 @ p27-python-freeze",
    },
];

/// `TERMINAL_DECISION`'s two whole-sentence variants — see the module doc.
/// Neither contains a `{slot}`.
const TERMINAL_DECISION_GENOCIDE: &str = "GENOCIDE: Atomized surplus population cannot resist. \
     The system eliminates what it cannot exploit or control.";
const TERMINAL_DECISION_REVOLUTION: &str = "REVOLUTION: Organized prisoners and radicalized \
     guards unite. The carceral apparatus turns against capital.";

/// Looks up `event_type`'s declared row, if any.
#[must_use]
pub fn spec_for(event_type: &str) -> Option<&'static NarrationSpec> {
    NARRATION_TABLE
        .iter()
        .find(|spec| spec.event_type == event_type)
}

/// One payload-only key §2.6/I2 declares a structural non-computation —
/// the SAME two `SUPERWAGE_CRISIS` rows `projection.rs::MATERIAL_NOT_COMPUTED`
/// declares (a bare structural zero, `decomposition.bsl:264-265`), mirrored
/// here because narration slots resolve against the EVENT PAYLOAD, not a
/// graph field, so they need their own declared table even though the
/// underlying fact is the same. `ENTITY_DEATH.cause` is declared too for
/// the same parity, though no shipped template names it (§2.6: "the
/// narration templates for those slots carry no `{slot}` at all").
struct NotComputedPayloadKey {
    event_type: &'static str,
    key: &'static str,
    reason: &'static str,
}

const NOT_COMPUTED_PAYLOAD_KEYS: &[NotComputedPayloadKey] = &[
    NotComputedPayloadKey {
        event_type: "SUPERWAGE_CRISIS",
        key: "desired-wages",
        reason:
            "a bare structural zero \u{2014} this port's real dollar figures do not compute here",
    },
    NotComputedPayloadKey {
        event_type: "SUPERWAGE_CRISIS",
        key: "available-pool",
        reason:
            "a bare structural zero \u{2014} this port's real dollar figures do not compute here",
    },
    NotComputedPayloadKey {
        event_type: "ENTITY_DEATH",
        key: "cause",
        reason: "not on the wire at all \u{2014} the discriminant is re-derivable, not carried",
    },
];

fn not_computed_reason(event_type: &str, key: &str) -> Option<&'static str> {
    NOT_COMPUTED_PAYLOAD_KEYS
        .iter()
        .find(|row| row.event_type == event_type && row.key == key)
        .map(|row| row.reason)
}

/// Renders one `Value` for embedding in a slot — `Int`/`Real` are the only
/// variants any shipped template's payload slots ever carry; the remaining
/// arms are handled exhaustively (Rust's own type-safety requirement) with
/// an honest debug fallback, never a fabricated numeral.
fn format_value(value: &Value) -> String {
    match value {
        Value::Int(i) => i.to_string(),
        Value::Real(r) => format!("{r:.2}"),
        Value::Bool(b) => b.to_string(),
        Value::Enum { member, .. } => member.clone(),
        Value::NodeRef(id) => format!("node #{}", id.0),
        Value::Currency(_) | Value::Ratio { .. } | Value::HyperedgeRef(_) | Value::EdgeRef(_) => {
            format!("{value:?}")
        }
    }
}

/// Resolves one `{key}` slot's substitution text (§2.2/§2.6/Minor 2):
/// `{subject}` is the reserved non-wire name for the caller-resolved
/// subject display; a declared `NotComputed` key renders its reason
/// (never the literal numeral the payload happens to hold); a key the
/// payload does not carry renders the literal text `{absent}`; otherwise
/// the payload's own value, formatted.
fn render_slot(
    event_type: &str,
    key: &str,
    payload: &[(String, Value)],
    subject_display: &str,
) -> String {
    if key == "subject" {
        return subject_display.to_owned();
    }
    if let Some(reason) = not_computed_reason(event_type, key) {
        return format!("not computed by this port \u{2014} {reason}");
    }
    match payload.iter().find(|(k, _)| k == key) {
        Some((_, value)) => format_value(value),
        None => "{absent}".to_owned(),
    }
}

/// Substitutes every `{key}` in `template` via [`render_slot`]. UTF-8 safe
/// (operates on `str` slices via `split_once`, never raw byte casts —
/// several templates carry a non-ASCII em dash). Loop bound: `template`'s
/// own byte length — each iteration consumes at least one `{...}` pair, so
/// the loop cannot outlive that many passes (Power-of-10 rule 2).
fn substitute(
    event_type: &str,
    template: &str,
    payload: &[(String, Value)],
    subject_display: &str,
) -> String {
    let mut result = String::with_capacity(template.len());
    let mut rest = template;
    for _ in 0..template.len() {
        let Some((literal, after_open)) = rest.split_once('{') else {
            result.push_str(rest);
            return result;
        };
        result.push_str(literal);
        let Some((key, tail)) = after_open.split_once('}') else {
            // An unmatched `{` — render it literally rather than dropping it.
            result.push('{');
            result.push_str(after_open);
            return result;
        };
        result.push_str(&render_slot(event_type, key, payload, subject_display));
        rest = tail;
    }
    result
}

/// The two rendered lines a beat card ever carries — `because` is `None`
/// for every row that declares no causal line (never `Some(String::new())`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RenderedBeat {
    pub headline: String,
    pub because: Option<String>,
}

/// `TERMINAL_DECISION`'s payload-conditional template choice (see the
/// module doc) — `None` when `outcome` is missing or neither `0` nor `1`,
/// the same "no verified copy" discipline an unrecognized `EventType`
/// falls through under.
fn terminal_decision_template(payload: &[(String, Value)]) -> Option<&'static str> {
    match payload.iter().find(|(k, _)| k == "outcome").map(|(_, v)| v) {
        Some(Value::Int(1)) => Some(TERMINAL_DECISION_REVOLUTION),
        Some(Value::Int(0)) => Some(TERMINAL_DECISION_GENOCIDE),
        _ => None,
    }
}

/// Renders one beat: `event_type` + its raw payload + the caller-resolved
/// `subject_display` (the declared `subject_key`'s `NodeRef` resolved to a
/// FIPS/entity display string, or `"world"` for a subject-less row — the
/// caller's job, since only it holds the roster this crate's narration
/// layer stays pure without). An unverified `EventType` (or, for
/// `TERMINAL_DECISION`, an unverified `outcome`) falls through to the
/// generic `<EVENT_TYPE> @ <subject>` line — never dropped, never guessed.
#[must_use]
pub fn render(
    event_type: &str,
    payload: &[(String, Value)],
    subject_display: &str,
) -> RenderedBeat {
    let template = if event_type == "TERMINAL_DECISION" {
        terminal_decision_template(payload)
    } else {
        spec_for(event_type).map(|spec| spec.template)
    };
    let Some(template) = template else {
        return RenderedBeat {
            headline: format!("{event_type} @ {subject_display}"),
            because: None,
        };
    };
    let spec = spec_for(event_type);
    RenderedBeat {
        headline: substitute(event_type, template, payload, subject_display),
        because: spec
            .and_then(|s| s.because)
            .map(|because| substitute(event_type, because, payload, subject_display)),
    }
}

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
    /// renderer's own `NotComputed` discipline must hold for it directly.
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
