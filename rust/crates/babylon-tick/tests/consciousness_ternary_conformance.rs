//! Consciousness class-surface ternary port (issue #588, ADR204 W10).
//! FIRST consumer of the `probability` deffield lane in committed content
//! (digest B.2) — pinned by name here. UNPOSITIONED idiom: ternary fields
//! are never defaulted into existence; readers optional-bind with `0.0p`
//! defaults and gate on `(> (+ r (+ l f)) 0)` — a sum of zero IS "no
//! reading" (L-ABS), never a fabricated share.
//!
//! Task 1 scope: the declaration surface (`consciousness-ternary-
//! conformance.bscn`) plus the pack's first rule (`consciousness/p0-position`
//! in `consciousness.bsl`). The read path and the routing update law land in
//! later tasks on top of these exact qnames. The four spelling-spike
//! verdicts this task was chartered to settle are recorded in the scenario
//! file's own header; the store-side facts they rest on:
//!
//! - Absence errors on read (III.11): an unwritten field is a loud
//!   `GraphError`, never a default `0.0` (`scenario.rs`'s "No defaults"
//!   contract, `substrate.rs:177-184`).
//! - One-home law (controller ruling 1, fix round):
//!   `social-class/dominant-worldview`'s ONLY writer is Task 2's
//!   `consciousness/p8-dominant-worldview`; p0 does NOT record dominance
//!   at positioning, so the field reads ABSENT even for the
//!   freshly-positioned class — pinned below as the one-home guard.

use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::substrate::{GraphSubstrate, NodeId};
use babylon_tick::run_once_into;

const SCENARIO: &str = include_str!("../content/scenarios/consciousness-ternary-conformance.bscn");
const CONSCIOUSNESS_RULES: &str = include_str!("../content/rules/consciousness.bsl");

// Node ids, fixed by the scenario's own declaration order (the scenario
// file's header names the same map).
const CLASS_EXPLOITED: NodeId = NodeId(0);
const CLASS_UNPOSITIONED: NodeId = NodeId(2);
const CLASS_EMERGENT: NodeId = NodeId(3);
const EMPLOYER: NodeId = NodeId(4);

/// Task 1's posture test: one tick of the p0-position rule over the
/// five-class-plus-org world, asserting the four seed roles' exact
/// post-tick ternary states — including that absence stays LOUD (the
/// UNPOSITIONED witness) and that positioning records the ruled rest state
/// while `dominant-worldview` stays absent (the one-home guard).
#[test]
fn unpositioned_class_gets_no_reading() {
    let mut graph = HypergraphStore::new();
    let mut sink = babylon_bsl::structural_verbs::CollectingSink::default();
    let report = run_once_into(SCENARIO, CONSCIOUSNESS_RULES, &mut graph, &mut sink)
        .expect("the consciousness ternary scenario plus the p0 pack must load and run");

    // p0 fired exactly once: class-emergent is the ONLY subject that is
    // active, anchored (wages-paid + value-produced present), and
    // ternary-absent (r + l + f sums to exactly zero under the declared
    // `0.0p` defaults).
    let p0_fired = report
        .per_rule_fired
        .iter()
        .find(|(id, _)| id == "consciousness/p0-position")
        .map(|(_, n)| *n);
    assert_eq!(
        p0_fired,
        Some(1),
        "p0-position fires for class-emergent and nothing else"
    );
    assert_eq!(report.fired, 1, "the pack ships one rule this task");

    // class-unpositioned (no anchors, no ternary seed): p0's guard rejects
    // it (the -1 anchor sentinels), so EVERY ternary field stays unwritten
    // and reads loud-absent — never a fabricated share (L-ABS; the row-19
    // disease's death certificate).
    assert!(
        graph
            .node_attribute(CLASS_UNPOSITIONED, "social-class/revolutionary")
            .is_err(),
        "unpositioned: social-class/revolutionary must error absent (III.11), never default"
    );
    assert!(
        graph
            .node_attribute(CLASS_UNPOSITIONED, "social-class/dominant-worldview")
            .is_err(),
        "unpositioned: social-class/dominant-worldview must error absent (III.11)"
    );

    // class-emergent (anchors, no ternary seed): p0 positioned it at the
    // ruled unorganized rest state (0, 1, 0) EXACTLY — `0.0p`/`1.0p`
    // literals convert as `unscaled / 10^scale` of exact operands, so plain
    // equality is bit-exact here.
    assert_eq!(
        graph
            .node_attribute(CLASS_EMERGENT, "social-class/revolutionary")
            .expect("positioned: revolutionary written"),
        0.0
    );
    assert_eq!(
        graph
            .node_attribute(CLASS_EMERGENT, "social-class/liberal")
            .expect("positioned: liberal written"),
        1.0
    );
    assert_eq!(
        graph
            .node_attribute(CLASS_EMERGENT, "social-class/fascist")
            .expect("positioned: fascist written"),
        0.0
    );
    assert_eq!(
        graph
            .node_attribute(CLASS_EMERGENT, "social-class/agitation")
            .expect("positioned: agitation initialized"),
        0.0,
        "p0 initializes the agitation accumulator to zero at positioning"
    );
    // ONE-HOME GUARD (controller ruling 1): p0 does NOT record dominance —
    // `social-class/dominant-worldview`'s only writer is Task 2's
    // `consciousness/p8-dominant-worldview`, which does not exist yet, so a
    // freshly-positioned class reads the field ABSENT after this tick. The
    // brief's original skeleton asserted a LIBERAL readback here — a plan
    // defect (it asserted a Task-2 artifact); the absence IS the guard.
    assert!(
        graph
            .node_attribute(CLASS_EMERGENT, "social-class/dominant-worldview")
            .is_err(),
        "one-home law: no writer exists in Task 1 — dominant-worldview errors absent \
         even for the freshly-positioned class"
    );

    // class-exploited (seeded (0.5, 0.4, 0.1)): p0 did NOT touch it — the
    // seeded shares survive the tick bit-for-bit. The seed conversions are
    // one correctly-rounded IEEE-754 division each (`5/10`, `4/10`, `1/10`),
    // landing exactly on the language literals.
    assert_eq!(
        graph
            .node_attribute(CLASS_EXPLOITED, "social-class/revolutionary")
            .expect("seeded: revolutionary present"),
        0.5,
        "the positioned seed is not p0's subject — untouched"
    );
    assert_eq!(
        graph
            .node_attribute(CLASS_EXPLOITED, "social-class/liberal")
            .expect("seeded: liberal present"),
        0.4
    );
    assert_eq!(
        graph
            .node_attribute(CLASS_EXPLOITED, "social-class/fascist")
            .expect("seeded: fascist present"),
        0.1
    );

    // employer (active, population, NO anchors): p0 did NOT position it —
    // the -1 anchor sentinels reject it even though it IS active. An
    // anchorless class is never a consciousness subject until it carries
    // its own wage relation.
    assert!(
        graph
            .node_attribute(EMPLOYER, "social-class/revolutionary")
            .is_err(),
        "employer: never positioned — social-class/revolutionary errors absent"
    );
    assert!(
        graph
            .node_attribute(EMPLOYER, "social-class/dominant-worldview")
            .is_err(),
        "employer: social-class/dominant-worldview errors absent"
    );
}
