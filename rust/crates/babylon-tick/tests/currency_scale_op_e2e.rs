//! The composed-path proof for the declared-domain Currency scale operation
//! (`bsl-language.rst` §3.2 addendum, Director ruling 2026-08-11,
//! #492/ADR194): a scenario declaring a `defconst`-with-`:cap` Ratio and a
//! rule computing `Currency × Ratio` clear content, load and evaluation
//! through the SAME `run_once`/`run_once_into` the CLI driver and
//! `babylon-client`'s engine link both call — the composed-path lesson
//! `floor_intrinsic_e2e.rs` records (round 1 of ADR188 Row 2's review
//! shipped a helper only a test called; this crate's E2E tests exist so a
//! seam is proved through the REAL entry point, not a lookalike).
//!
//! **Why the money value is an inline literal, not a `:field`.** Slice 1's
//! `GraphSubstrate` attributes are plain `f64` (`scenario.rs`'s own module
//! doc: "No `Currency` attributes" — typed i128 attribute storage is a
//! declared Phase-2 trait revision) and `defconst` refuses a `Currency`
//! literal for the identical reason (`scenario.rs::load_defconst`,
//! unchanged by this addendum). A `Currency` value can currently enter a
//! rule's evaluation ONLY as a literal written directly in the rule body —
//! true before this change and after it; this test's rule reads that
//! literal exactly the way an eviction-pipeline rule will once Territory's
//! own port train lands (out of scope here — this proves the MACHINERY).
//!
//! **Why the result is `emit`ted, not `update-node`d.** The identical gap:
//! `update-node` refuses a `Currency` write (`structural_verbs.rs`'s
//! `currency_writes_are_a_loud_declared_gap_never_a_lossy_cast`), while
//! `emit`'s payload is an evaluated [`babylon_bsl::evaluator::Value`] with
//! no type restriction (`emit_collects_the_evaluated_payload`). Observing
//! the product through the event sink sidesteps the graph-storage gap
//! entirely rather than working around it.
//!
//! Territory's real `rent_spike_multiplier` is `1500.5$ × 2.0` — the exact
//! shape this test proves, with the exact numbers the port train's fixture
//! cites (§492's issue body: "tested moddable to 2.0").

use babylon_bsl::evaluator::Value;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::memory::MemoryGraph;
use babylon_tick::run_once_into;

const SCENARIO: &str = r#"
(scenario scale-op-e2e/one-territory
  (deffield territory/population int extensive)
  (defconst territory/rent-spike-multiplier 2.0r :cap 10r)

  (node core NodeType/TERRITORY
    (territory/population 1)))
"#;

const RULE: &str = r#"
(rule vitality/scale-op-e2e-rent-spike
  :material-basis "prove Currency x declared-domain Ratio clears content, load and evaluation (#492/ADR194)"
  :fuel 64
  (bindings
    (binding population :field territory/population)
    (binding multiplier :const territory/rent-spike-multiplier)
    (binding spiked-rent :expr (* 1500.5$ multiplier)))
  (when (> population 0))
  (effects
    (emit EventType/RUPTURE (spiked-rent spiked-rent))))
"#;

#[test]
fn a_rule_scaling_currency_by_a_declared_domain_ratio_runs_through_run_once() {
    let mut graph = MemoryGraph::new();
    let mut sink = CollectingSink::default();
    let report = run_once_into(SCENARIO, RULE, &mut graph, &mut sink)
        .expect("Currency x declared-domain Ratio must clear the whole seam");

    assert_eq!(report.fired, 1);

    assert_eq!(sink.events.len(), 1);
    let (event_type, payload) = &sink.events[0];
    assert_eq!(event_type, "RUPTURE");
    let (name, value) = &payload[0];
    assert_eq!(name, "spiked-rent");

    // 1500.5$ x 2.0 = 3001.0$ exactly — a fixed-point x grid-quantized
    // multiply, no binary64 rounding ambiguity at these values.
    assert_eq!(
        *value,
        Value::Currency(babylon_kernel::Currency::from_micro_units(3_001_000_000)),
        "1500.5$ * 2.0r must equal exactly 3001.0$"
    );
}

#[test]
fn the_declared_call_is_deterministic_across_two_full_runs() {
    let mut graph_a = MemoryGraph::new();
    let mut sink_a = CollectingSink::default();
    let a = run_once_into(SCENARIO, RULE, &mut graph_a, &mut sink_a).expect("first run");

    let mut graph_b = MemoryGraph::new();
    let mut sink_b = CollectingSink::default();
    let b = run_once_into(SCENARIO, RULE, &mut graph_b, &mut sink_b).expect("second run");

    assert_eq!(a.after, b.after);
    assert_eq!(sink_a.events, sink_b.events);
}

/// The declared `:cap` fails the WHOLE tick, loudly, when the scenario
/// itself is inconsistent (`E-LOAD-052`) — proved through the full
/// `run_once` seam, not just `scenario::tests`' narrower call into
/// `load_scenario` alone (this is the same "prove it through the real
/// entry point" argument the module doc makes for the whole file).
///
/// **This does NOT reach `E-EVAL-041`, and that absence is itself
/// recorded rather than papered over.** `load_scenario` runs before
/// `load_rule_form`/`run_tick` in `run_once_into`, so an inconsistent
/// `(value, cap)` pair is refused before a rule ever evaluates it — through
/// `defconst`, the ONLY producer of a capped `Value::Ratio` today, the two
/// checks can never observe different verdicts. `E-EVAL-041`'s own defense-
/// in-depth case (a `Value::Ratio` whose `cap` and `value` disagree despite
/// having passed load — e.g. a future non-`defconst` source) is unit-tested
/// directly in `evaluator.rs`, where it CAN be constructed.
#[test]
fn a_ratio_over_its_declared_cap_fails_the_whole_tick_loudly() {
    const OVER_CAP_SCENARIO: &str = r#"
(scenario scale-op-e2e/over-cap
  (deffield territory/population int extensive)
  (defconst territory/rent-spike-multiplier 12r :cap 10r)

  (node core NodeType/TERRITORY
    (territory/population 1)))
"#;
    let mut graph = MemoryGraph::new();
    let mut sink = CollectingSink::default();
    let err = run_once_into(OVER_CAP_SCENARIO, RULE, &mut graph, &mut sink).unwrap_err();
    assert!(
        err.contains("exceeds its own :cap"),
        "unexpected message: {err}"
    );
}

/// The mirror success case: a bare (uncapped) declared-domain Ratio — the
/// exact shape `rent_spike_multiplier`'s real `(0, ∞)` domain has — still
/// clears the whole seam and multiplies cleanly for a value an ordinary
/// `Coefficient` could never have carried (well above `1.0`).
#[test]
fn an_uncapped_declared_domain_ratio_also_clears_the_whole_seam() {
    const UNCAPPED_SCENARIO: &str = r#"
(scenario scale-op-e2e/uncapped
  (deffield territory/population int extensive)
  (defconst territory/rent-spike-multiplier 5r)

  (node core NodeType/TERRITORY
    (territory/population 1)))
"#;
    let mut graph = MemoryGraph::new();
    let mut sink = CollectingSink::default();
    let report = run_once_into(UNCAPPED_SCENARIO, RULE, &mut graph, &mut sink)
        .expect("an uncapped declared-domain Ratio must still clear the seam");
    assert_eq!(report.fired, 1);
    let (_, payload) = &sink.events[0];
    let (_, value) = &payload[0];
    assert_eq!(
        *value,
        Value::Currency(babylon_kernel::Currency::from_micro_units(7_502_500_000)),
        "1500.5$ * 5.0r must equal exactly 7502.5$"
    );
}
