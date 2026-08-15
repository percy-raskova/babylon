//! Consciousness class-surface ternary port (issue #588, ADR204 W10).
//! FIRST consumer of the `probability` deffield lane in committed content
//! (digest B.2) — pinned by name here. UNPOSITIONED idiom: ternary fields
//! are never defaulted into existence; readers optional-bind with `0.0p`
//! defaults and gate on `(> (+ r (+ l f)) 0)` — a sum of zero IS "no
//! reading" (L-ABS), never a fabricated share.
//!
//! Task 1+2 scope: the declaration surface (`consciousness-ternary-
//! conformance.bscn`), the pack's first rule (`consciousness/p0-position`),
//! and the measured readout (`consciousness/p8-dominant-worldview`, Task 2) —
//! dominant pole = argmax, ties resolved in the ruled order LIBERAL >
//! REVOLUTIONARY > FASCIST at a STRICT 1e-6 (frozen
//! models/entities/consciousness.py:177-192, transcribed verbatim) — THE one
//! home for the hegemonic tie-break. The routing update law (p1..p7) lands in
//! Task 3 on top of these exact qnames. The four spelling-spike verdicts
//! Task 1 was chartered to settle are recorded in the scenario file's own
//! header; the store-side facts they rest on:
//!
//! - Absence errors on read (III.11): an unwritten field is a loud
//!   `GraphError`, never a default `0.0` (`scenario.rs`'s "No defaults"
//!   contract, `substrate.rs:177-184`).
//! - One-home law + the Task-1 -> Task-2 handoff (controller ruling 1):
//!   `social-class/dominant-worldview`'s ONLY writer is
//!   `consciousness/p8-dominant-worldview`; p0 does NOT record dominance at
//!   positioning. Task 1 pinned the field ABSENT on the freshly-positioned
//!   class as the one-home guard (no writer existed yet); with p8 landed,
//!   that same class now reads the measured readout of its (0, 1, 0) rest
//!   state — LIBERAL — and loud absence survives only for the genuinely
//!   unread (class-unpositioned, employer).

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
// Task 2's eight tv-* read-path fixtures (ids 6-13; org-solid is 5).
const TV_LIBERAL_CLEAR: NodeId = NodeId(6);
const TV_REVOLUTIONARY_CLEAR: NodeId = NodeId(7);
const TV_FASCIST_CLEAR: NodeId = NodeId(8);
const TV_TIE_LR: NodeId = NodeId(9);
const TV_TIE_RF: NodeId = NodeId(10);
const TV_TIE_LF: NodeId = NodeId(11);
const TV_STRICT_GAP: NodeId = NodeId(12);
const TV_TIE_ALL_TRUE: NodeId = NodeId(13);

/// Task 1's posture test: one tick of the p0-position rule over the
/// five-class-plus-org world (Task 2's eight tv-* fixtures ride along, inert
/// to p0 — no anchors), asserting the four seed roles' exact post-tick
/// ternary states — including that absence stays LOUD (the UNPOSITIONED
/// witness) and that positioning records the ruled rest state. Task-2
/// handoff: `dominant-worldview` is now written by
/// `consciousness/p8-dominant-worldview`, so the class-emergent assertion
/// below flipped from Task 1's absence pin (the one-home guard) to the
/// positive LIBERAL readout.
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
    assert_eq!(
        report.fired, 12,
        "p0 fires once (class-emergent) + p8 fires for the eleven \
         positioned-or-seeded classes (exploited, bribed, emergent, 8 tv-*)"
    );

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
    // ONE-HOME HANDOFF (controller ruling 1, Task 1 -> Task 2): p0 does NOT
    // record dominance — `social-class/dominant-worldview`'s only writer is
    // `consciousness/p8-dominant-worldview`. Task 1 pinned this read ABSENT
    // as the one-home guard (no writer existed); with p8 landed, the
    // freshly-positioned class now reads the measured readout of the ruled
    // (0, 1, 0) rest state: dl = 0 < 1e-6, so LIBERAL takes the tie order's
    // first slot — A-001's liberal hegemonic default, now MEASURED by the
    // readout rather than written at positioning. Stored ordinal 1
    // (declaration order IS the storage ordinal, ADR195; parity pinned by
    // tick_goldens.rs's
    // consciousness_ternary_worldview_member_order_is_the_ruled_ordinal).
    assert_eq!(
        graph
            .node_attribute(CLASS_EMERGENT, "social-class/dominant-worldview")
            .expect("p8 writes the readout for the same-tick-positioned class (D116)"),
        1.0,
        "dominant of (0, 1, 0) is LIBERAL — the one-home readout, not a p0 write"
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

/// Task 2's read-path vectors: `consciousness/p8-dominant-worldview` over the
/// eight tv-* fixture classes — the measured readout (argmax, then the ruled
/// tie order LIBERAL > REVOLUTIONARY > FASCIST within a STRICT 1e-6 of the
/// max; frozen `models/entities/consciousness.py:177-192`, transcribed
/// verbatim) proven on every arm: three clear maxima, the three pairwise
/// ties, the strictness boundary (an exactly-1e-6 gap is NOT a tie — decimal
/// and f64-verbatim agree, and the frozen ground truth's `dominant_tendency`
/// returns fascist for that seed; controller ruling 2026-08-15), and the true
/// all-equal tie. The tv classes seed ONLY population / active=1 / the
/// ternary / agitation 0 — no anchors, no edges — so Task 3's update rules
/// will never touch them.
#[test]
fn dominant_worldview_readout_vectors() {
    let mut graph = HypergraphStore::new();
    let mut sink = babylon_bsl::structural_verbs::CollectingSink::default();
    let report = run_once_into(SCENARIO, CONSCIOUSNESS_RULES, &mut graph, &mut sink)
        .expect("the consciousness ternary scenario plus the p0+p8 pack must load and run");

    // p8 fires exactly eleven times: class-exploited, class-bribed, and
    // class-emergent (positioned by p0 THIS tick — D116 same-tick
    // visibility) plus the eight tv-* fixtures; never class-unpositioned or
    // employer (ternary sum 0 — the UNPOSITIONED guard), never org-solid
    // (not a SOCIAL_CLASS subject).
    let p8_fired = report
        .per_rule_fired
        .iter()
        .find(|(id, _)| id == "consciousness/p8-dominant-worldview")
        .map(|(_, n)| *n);
    assert_eq!(
        p8_fired,
        Some(11),
        "p8 reads every positioned class and nothing else"
    );

    // Stored ordinals: REVOLUTIONARY = 0, LIBERAL = 1, FASCIST = 2 —
    // declaration order IS the storage ordinal (ADR195), pinned explicitly by
    // tick_goldens.rs's
    // consciousness_ternary_worldview_member_order_is_the_ruled_ordinal; this
    // table asserts through that parity (the OrgKind read-back pattern —
    // scenario.rs's an_enum_field_seeds_by_member_ref_and_stores_the_declared_ordinal).
    const REVOLUTIONARY: f64 = 0.0;
    const LIBERAL: f64 = 1.0;
    const FASCIST: f64 = 2.0;
    let cases = [
        (TV_LIBERAL_CLEAR, LIBERAL, "(0.2, 0.5, 0.3): clear l max"),
        (
            TV_REVOLUTIONARY_CLEAR,
            REVOLUTIONARY,
            "(0.6, 0.4, 0.0): clear r max",
        ),
        (TV_FASCIST_CLEAR, FASCIST, "(0.2, 0.3, 0.5): clear f max"),
        (
            TV_TIE_LR,
            LIBERAL,
            "(0.5, 0.5, 0.0): l == r at the max, ruled L > R",
        ),
        (
            TV_TIE_RF,
            REVOLUTIONARY,
            "(0.5, 0.0, 0.5): r == f at the max, ruled R > F",
        ),
        (
            TV_TIE_LF,
            LIBERAL,
            "(0.0, 0.5, 0.5): l == f at the max, ruled L > F",
        ),
        (
            TV_STRICT_GAP,
            FASCIST,
            "(0.333333, 0.333333, 0.333334): an exactly-1e-6 gap is NOT a tie \
             (strict `<`) — the unique f max wins",
        ),
        (
            TV_TIE_ALL_TRUE,
            LIBERAL,
            "(0.333333, 0.333333, 0.333333): the true all-equal tie — dl = 0 < 1e-6, \
             LIBERAL takes the ruled order's first slot",
        ),
    ];
    for (id, ordinal, why) in cases {
        assert_eq!(
            graph
                .node_attribute(id, "social-class/dominant-worldview")
                .expect("tv classes are positioned seeds — p8 writes the readout"),
            ordinal,
            "{why}"
        );
    }
}
