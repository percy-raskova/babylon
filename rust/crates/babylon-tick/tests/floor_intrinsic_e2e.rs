//! The end-to-end proof the adversarial review demanded: a rule that
//! DECLARES `(intrinsic floor …)` and CALLS `(floor …)` clears content,
//! load, and evaluation through the exact same `run_once` family the CLI
//! driver and `babylon-client`'s engine link use — not `KernelIntrinsicHost`
//! exercised in isolation (that was the #480-shaped gap: a component proven
//! in a unit test that no production path actually reaches).
//!
//! `population = 11`, `rate = 0.5c` (exact in binary64 — no rounding
//! ambiguity), `deaths = floor(population * rate) = floor(5.5) = 5`.

use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::memory::MemoryGraph;
use babylon_graph::substrate::{GraphSubstrate, NodeId};
use babylon_tick::{run_once_into_with_intrinsics, run_once_with_intrinsics};

const SCENARIO: &str = r#"
(scenario floor-e2e/one-class
  (deffield social-class/population int extensive)
  (deffield social-class/deaths int extensive)
  (defconst economy/rate 0.5c)

  (node core NodeType/SOCIAL_CLASS
    (social-class/population 11)))
"#;

const INTRINSICS: &str = "(intrinsic floor :params (real) :returns int :cost 5)";

const RULE: &str = r#"
(rule vitality/floor-e2e-count-deaths
  :material-basis "prove the floor intrinsic clears content, load and evaluation"
  :fuel 64
  (bindings
    (binding population :field social-class/population)
    (binding rate :const economy/rate)
    (binding deaths :expr (floor (* population rate))))
  (when (> population 0))
  (effects
    (update-node self social-class/deaths (set deaths))))
"#;

#[test]
fn a_rule_that_declares_and_calls_floor_runs_through_run_once() {
    let mut graph = MemoryGraph::new();
    let mut sink = CollectingSink::default();
    let report = run_once_into_with_intrinsics(SCENARIO, INTRINSICS, RULE, &mut graph, &mut sink)
        .expect("a declared, called floor intrinsic must clear the whole seam");

    assert_eq!(report.fired, 1);
    assert_ne!(report.before, report.after, "the rule must move state");

    let deaths = graph
        .node_attribute(NodeId(0), "social-class/deaths")
        .expect("social-class/deaths must have been written");
    assert_eq!(
        deaths, 5.0,
        "floor(11 * 0.5) = floor(5.5) = 5 — a ceiling or round-half-even \
         implementation would write 6"
    );
}

#[test]
fn the_declared_call_is_deterministic_across_two_full_runs() {
    let a = run_once_with_intrinsics(SCENARIO, INTRINSICS, RULE).expect("first run");
    let b = run_once_with_intrinsics(SCENARIO, INTRINSICS, RULE).expect("second run");
    assert_eq!(a.after, b.after);
}

/// The other half of leg 2: a name outside `DECLARABLE_INTRINSICS` refuses
/// the WHOLE load, loudly — never a partial admission of the rest.
#[test]
fn declaring_an_uncapped_intrinsic_refuses_the_whole_load() {
    let err = run_once_with_intrinsics(
        SCENARIO,
        "(intrinsic tanh :params (real) :returns real :cost 40)",
        RULE,
    )
    .unwrap_err();
    assert!(
        err.contains("declarable intrinsic set"),
        "unexpected message: {err}"
    );
}

/// Leg 1's own claim, proven where it matters: calling an intrinsic that is
/// declarable in principle (`exp` is in `DECLARABLE_INTRINSICS`) but has no
/// real `KernelIntrinsicHost` dispatch arm still fails loud through the
/// FULL seam — `KernelIntrinsicHost` subsumes `EmptyIntrinsicHost`'s
/// behavior rather than silently succeeding.
#[test]
fn a_declared_but_undispatchable_intrinsic_still_fails_loud_at_evaluation() {
    const EXP_RULE: &str = r#"
(rule vitality/floor-e2e-undispatchable
  :material-basis "exp is declarable but not yet dispatchable"
  :fuel 64
  (bindings
    (binding population :field social-class/population)
    (binding rate :const economy/rate)
    (binding scaled :expr (exp rate)))
  (when (> population 0))
  (effects
    (update-node self social-class/deaths (set population))))
"#;
    let err = run_once_with_intrinsics(
        SCENARIO,
        "(intrinsic exp :params (real) :returns real :cost 40)",
        EXP_RULE,
    )
    .unwrap_err();
    assert!(err.contains("tick failed"), "unexpected message: {err}");
}
