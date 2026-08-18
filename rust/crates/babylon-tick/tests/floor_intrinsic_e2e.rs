//! The end-to-end proof the adversarial review demanded: a rule that
//! DECLARES `(intrinsic floor …)` and CALLS `(floor …)` clears content,
//! load, and evaluation through the exact same `run_once`/`run_once_into`
//! the CLI driver (`main.rs`'s two-path invocation) and `babylon-client`'s
//! engine link (`engine_link.rs`) both call — the SAME entry point
//! production uses, not a third parameter only this test exercises (round
//! 1 of this review shipped exactly that gap: `run_once_with_intrinsics`
//! had no production caller at all).
//!
//! The intrinsic declaration lives INSIDE `RULE`, alongside the `(rule …)`
//! form — §2.2: "file boundaries and file names carry no semantics", so an
//! `(intrinsic …)` top-form is ordinary content wherever it appears in the
//! source `run_once` reads, not a side channel.
//!
//! `population = 11`, `rate = 0.5c` (exact in binary64 — no rounding
//! ambiguity), `deaths = floor(population * rate) = floor(5.5) = 5`.

use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::memory::MemoryGraph;
use babylon_graph::substrate::{GraphSubstrate, NodeId};
use babylon_tick::{run_once, run_once_into};

const SCENARIO: &str = r#"
(scenario floor-e2e/one-class
  (deffield social-class/population int extensive)
  (deffield social-class/deaths int extensive)
  (defconst economy/rate 0.5c)

  (node core NodeType/SOCIAL_CLASS
    (social-class/population 11)))
"#;

const RULE: &str = r#"
(intrinsic floor :params (real) :returns int :cost 5)
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

/// The mirror source with the two top-forms in the OTHER order — proves
/// `split_content` really does treat placement as non-semantic rather than
/// happening to work only because the intrinsic decl comes first.
const RULE_INTRINSIC_LAST: &str = r#"
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
(intrinsic floor :params (real) :returns int :cost 5)
"#;

#[test]
fn a_rule_that_declares_and_calls_floor_runs_through_run_once() {
    let mut graph = MemoryGraph::new();
    let mut sink = CollectingSink::default();
    let report = run_once_into(SCENARIO, RULE, &mut graph, &mut sink)
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

/// §2.2's "file boundaries and file names carry no semantics", proven for
/// FORM ORDER specifically: the intrinsic declaration AFTER the rule form
/// must produce byte-identical hashes to the declaration BEFORE it.
#[test]
fn declaration_order_relative_to_the_rule_does_not_matter() {
    let first = run_once(SCENARIO, RULE).expect("intrinsic-first source");
    let last = run_once(SCENARIO, RULE_INTRINSIC_LAST).expect("intrinsic-last source");
    assert_eq!(first.after, last.after);
    assert_eq!(first.fired, last.fired);
}

#[test]
fn the_declared_call_is_deterministic_across_two_full_runs() {
    let a = run_once(SCENARIO, RULE).expect("first run");
    let b = run_once(SCENARIO, RULE).expect("second run");
    assert_eq!(a.after, b.after);
}

/// The other half of leg 2: a name outside `DECLARABLE_INTRINSICS` refuses
/// the WHOLE load, loudly — never a partial admission of the rest.
#[test]
fn declaring_an_uncapped_intrinsic_refuses_the_whole_load() {
    const TANH_RULE: &str = r#"
(intrinsic tanh :params (real) :returns real :cost 40)
(rule vitality/floor-e2e-count-deaths
  :material-basis "x" :fuel 8 (when #t))
"#;
    let err = run_once(SCENARIO, TANH_RULE).unwrap_err();
    assert!(
        err.contains("declarable intrinsic set"),
        "unexpected message: {err}"
    );
}

/// A declared signature that disagrees with the kernel's registration
/// (`E-LOAD-020`) refuses the whole load too — floor's kernel signature is
/// `(real) -> int`, not `(int) -> int`.
#[test]
fn a_mismatched_declared_signature_refuses_the_whole_load() {
    const WRONG_SIGNATURE_RULE: &str = r#"
(intrinsic floor :params (int) :returns int :cost 5)
(rule vitality/floor-e2e-count-deaths
  :material-basis "x" :fuel 8 (when #t))
"#;
    let err = run_once(SCENARIO, WRONG_SIGNATURE_RULE).unwrap_err();
    assert!(err.contains("E-LOAD-020"), "unexpected message: {err}");
}

/// A duplicate intrinsic name across the content set (`E-LOAD-001`) refuses
/// the whole load rather than the last declaration silently winning.
#[test]
fn a_duplicate_intrinsic_declaration_refuses_the_whole_load() {
    const DUPLICATE_RULE: &str = r#"
(intrinsic floor :params (real) :returns int :cost 5)
(intrinsic floor :params (real) :returns int :cost 9)
(rule vitality/floor-e2e-count-deaths
  :material-basis "x" :fuel 8 (when #t))
"#;
    let err = run_once(SCENARIO, DUPLICATE_RULE).unwrap_err();
    assert!(err.contains("E-LOAD-001"), "unexpected message: {err}");
}

/// Leg 1's own claim, retargeted after Task 2 (#576) closed its original
/// gap: `exp`/`log` dispatch now (`KernelIntrinsicHost::call` has an arm
/// for every member of `DECLARABLE_INTRINSICS` — `{exp, log, floor}`, all
/// three in lockstep with `declarations::kernel_signature`), so there is no
/// longer any name that clears the declaration-time cap check while
/// staying undispatched at EVALUATION — that specific gap closes by
/// construction as long as the cap and the dispatch table stay matched,
/// which is exactly what this train's own Task 2 did for the last two
/// members.
///
/// `round-half-even` is the closest surviving analog, and the ONLY one
/// available: ADR188 Row 3 RATIFIED it in principle, but its mechanical
/// landing — admission to `DECLARABLE_INTRINSICS` itself (D70,
/// `declarations.rs:103-109`) — is separate, not-yet-done work, so it
/// still refuses the WHOLE LOAD through the exact same
/// `run_once`/`run_once_into` seam the CLI driver and `babylon-client`'s
/// engine link both call. This is one checkpoint earlier than the original
/// test exercised (declaration/cap, not evaluation) — the only checkpoint
/// left where an "approved but not yet wired" name is still catchable —
/// but it proves the same underlying property the original test's own doc
/// comment named: the load pipeline and `KernelIntrinsicHost` never
/// silently admit or silently no-op a name the kernel does not fully
/// support.
#[test]
fn round_half_even_is_ratified_but_still_refuses_the_whole_load() {
    const ROUND_HALF_EVEN_RULE: &str = r#"
(intrinsic round-half-even :params (real) :returns real :cost 6)
(rule vitality/floor-e2e-undispatchable
  :material-basis "round-half-even is ADR188 Row 3 ratified but not yet admitted to DECLARABLE_INTRINSICS"
  :fuel 64
  (bindings
    (binding population :field social-class/population)
    (binding rate :const economy/rate)
    (binding scaled :expr (round-half-even rate)))
  (when (> population 0))
  (effects
    (update-node self social-class/deaths (set population))))
"#;
    let err = run_once(SCENARIO, ROUND_HALF_EVEN_RULE).unwrap_err();
    assert!(
        err.contains("round-half-even") && err.contains("RATIFIED"),
        "unexpected message: {err}"
    );
}
