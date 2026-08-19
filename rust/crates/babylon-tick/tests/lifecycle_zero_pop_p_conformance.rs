//! Task W5 (BSL Hygiene Knock-out, 2026-08-18) — the lifecycle division
//! guard's conformance vector.
//!
//! `lifecycle/dpd-circuit`'s `dependency-ratio` binding divides by
//! `new-pop-p`, the post-transition productive population
//! (`content/rules/lifecycle.bsl:308-319`). The binding was unguarded: a
//! subject whose D and P cohorts both hit zero in the same tick (the
//! productive class fully liquidated, with no D-phase inflow to replace
//! it) drives `new-pop-p` to exactly `0.0`, and the division threw
//! `E-EVAL-012` (division by zero in the binary64 lane), aborting the
//! tick. No landed conformance fixture reaches this case — every
//! pre-existing vector keeps post-tick `pop-p` strictly positive
//! (`lifecycle.bsl`'s own pre-guard comment) — which is exactly why the
//! gap was latent rather than caught on contact.
//!
//! Director ruling (popup 2026-08-18): guard it, not a loud invariant —
//! zero productive population is a reachable material state (a county's
//! productive class fully liquidated by the D-P-D' circuit itself), not a
//! programming error.
//!
//! This is a **scratch** scenario — a minimal literal built specifically
//! to drive `new-pop-p` to exactly zero through the real evaluator,
//! deliberately kept off the pinned-fixture estate the Pin Law protects
//! (`content/scenarios/lifecycle-conformance.bscn` and its siblings are
//! untouched by this task).
//!
//! # Why `new-pop-p` lands on exactly `0.0`
//!
//! `new-pop-p = pop-p + (rate-d-to-p * pop-d) - (rate-p-to-d-prime *
//! pop-p)` (`lifecycle.bsl:274,278`). Seeding `pop-d = 0` AND `pop-p = 0`
//! makes every term on the right a product against zero, so the result is
//! exact `0.0` by construction — no subtractive floating-point
//! cancellation is in play, and no vector-authoring luck is needed to hit
//! the exact bit pattern. `pop-d-prime` is seeded nonzero (`1000`), so the
//! dependency-ratio numerator (`new-pop-d + new-pop-d-prime`) is
//! genuinely positive: this is the reachable, meaningful case the guard
//! exists for, not a degenerate `0/0`.

use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::memory::MemoryGraph;
use babylon_graph::substrate::{GraphSubstrate, NodeId};
use babylon_tick::run_once_into;

const RULE: &str = include_str!("../content/rules/lifecycle.bsl");

/// A single depopulated-productive-class subject: `pop-d` and `pop-p` both
/// zero, `pop-d-prime` nonzero — the case that drives `new-pop-p` to
/// exactly `0.0` while the dependency-ratio numerator stays positive. The
/// `:const` environment is lifted verbatim from
/// `content/scenarios/lifecycle-conformance.bscn` (same values, same
/// provenance) since this vector exercises Block 1's guard only, not the
/// legitimation or ideology blocks.
const SCENARIO: &str = r#"
(scenario lifecycle/zero-pop-p-guard
  (deffield territory/pop-d real extensive)
  (deffield territory/pop-p real extensive)
  (deffield territory/pop-d-prime real extensive)
  (deffield territory/wealth-d-prime real extensive)
  (deffield territory/dependency-ratio real intensive)
  (deffield territory/legitimation-index real intensive)
  (deffield territory/legitimation-crisis int intensive)
  (deffield territory/transmitted-ideology real intensive)

  (defconst lifecycle/birth-rate 0.0107c)
  (defconst lifecycle/rate-d-to-p 0.0556c)
  (defconst lifecycle/rate-p-to-d-prime 0.0213c)
  (defconst lifecycle/rate-d-prime-to-death 0.039c)
  (defconst lifecycle/pension-coverage-rate 0.73c)
  (defconst lifecycle/home-ownership-rate 0.656c)
  (defconst lifecycle/ss-replacement-rate 0.426c)
  (defconst lifecycle/healthcare-security 0.6c)
  (defconst lifecycle/retirement-confidence 0.5c)
  (defconst lifecycle/legit-w-home-ownership 0.35c)
  (defconst lifecycle/legit-w-healthcare-security 0.3c)
  (defconst lifecycle/legit-w-retirement-confidence 0.2c)
  (defconst lifecycle/legit-w-pension-coverage 0.1c)
  (defconst lifecycle/legit-w-ss-replacement 0.05c)
  (defconst lifecycle/legitimation-crisis-threshold 0.3c)
  (defconst lifecycle/legitimation-unstable-threshold 0.5c)
  (defconst lifecycle/ideology-caregiver-weight 0.7c)
  (defconst lifecycle/ideology-institutional-weight 0.3c)
  (defconst lifecycle/ideology-regression-coefficient 0.4c)
  (defconst lifecycle/caregiver-ideology-default 0.5c)
  (defconst lifecycle/institutional-hegemony-default 0.5c)

  ; pop-d and pop-p both zero: no productive class, no D-phase cohort to
  ; replace it this tick. pop-d-prime nonzero: a real, positive dependency
  ; numerator over a zero denominator.
  (node depopulated-county NodeType/TERRITORY
    (territory/pop-d 0)
    (territory/pop-p 0)
    (territory/pop-d-prime 1000)
    (territory/wealth-d-prime 1000000)
    (territory/dependency-ratio 0)
    (territory/legitimation-index 0)
    (territory/legitimation-crisis 0)
    (territory/transmitted-ideology 0)))
"#;

fn run() -> Result<(MemoryGraph, CollectingSink), String> {
    let mut graph = MemoryGraph::new();
    let mut sink = CollectingSink::default();
    run_once_into(SCENARIO, RULE, &mut graph, &mut sink)?;
    Ok((graph, sink))
}

fn attribute(graph: &MemoryGraph, id: u64, field: &str) -> f64 {
    graph
        .node_attribute(NodeId(id), field)
        .unwrap_or_else(|e| panic!("node {id} field {field}: {}", e.message))
}

/// The guard's whole point: a fully-liquidated productive class (`pop-d`
/// AND `pop-p` both zero) must not abort the tick. Before the guard
/// landed, this failed with `E-EVAL-012` (division by zero in the
/// binary64 lane) — see the module doc's provenance.
#[test]
fn a_fully_depopulated_productive_class_does_not_abort_the_tick() {
    let (graph, _) = run().expect(
        "the tick must survive a zero new-pop-p — Director ruling 2026-08-18: \
         guard it, not a loud invariant, never E-EVAL-012",
    );
    assert_eq!(
        attribute(&graph, 0, "territory/pop-p"),
        0.0,
        "pop-d and pop-p both seeded zero stay zero this tick (no D-phase inflow)"
    );
    assert_eq!(
        attribute(&graph, 0, "territory/dependency-ratio"),
        0.0,
        "new-pop-p == 0 must yield the honest inert value (Real zero), never a crash"
    );
}
