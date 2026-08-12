//! Conformance vectors for the `territory/*` rule pack (P27 Phase 2, the
//! Territory port train — `docs/superpowers/plans/2026-08-12-territory-
//! port-plan.md`, PR B), taken from the frozen Python engine's live
//! behaviour.
//!
//! # Provenance
//!
//! Every STRUCTURAL claim below (which fields moved, in which direction,
//! the latch set, the sink chosen, the suppression set) was checked against
//! the frozen `TerritorySystem` running one `step()` over a fixture that
//! mirrors `content/scenarios/territory-conformance.bscn` node for node.
//! The command, from the repository root:
//!
//! ```text
//! PYTHONPATH="$PWD/src" uv run python \
//!     rust/crates/babylon-tick/content/scenarios/territory_conformance.py
//! ```
//!
//! The frozen system is the contract source for STRUCTURE and ORDERING,
//! not a correctness oracle (ADR183) — the port train's own D-records
//! (`territory.bsl`'s header) name every place this pack's arithmetic
//! diverges from the frozen engine's operation SEQUENCE for the same
//! real-valued function (the scaled-Int rent lane, the pull-side spillover
//! fold, the directed-vs-any sink/spillover walks). Every NUMERIC value
//! pinned below is measured from the BSL engine's own output, never copied
//! from the frozen mirror's printed floats.
//!
//! # Scenario census (Task 3)
//!
//! Twelve territories, three social classes, seven edges (five ADJACENCY,
//! two TENANCY) — see `territory-conformance.bscn`'s own header for the
//! full per-node conformance-case map.

use babylon_bsl::scenario::load_scenario;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::substrate::{GraphSubstrate, NodeId};
use babylon_tick::run_once_into;

const SCENARIO: &str = include_str!("../content/scenarios/territory-conformance.bscn");

// Node ids, fixed by the scenario's own declaration order
// (`territory-conformance.bscn`'s own header names the same map). Several
// are unused until later tasks (p2's sink/latch nodes, p3's chain, p4's
// camp) accrete their own tests — named now, for documentation symmetry
// with the scenario's own header, per `query_lane_e2e.rs`'s precedent.
const SUB_THRESHOLD_HIGH: NodeId = NodeId(0);
const SUB_THRESHOLD_LOW: NodeId = NodeId(1);
#[allow(dead_code)]
const LATCH_TICK_SOURCE: NodeId = NodeId(2);
#[allow(dead_code)]
const SINK_PENAL: NodeId = NodeId(3);
#[allow(dead_code)]
const SINK_RESERVATION: NodeId = NodeId(4);
#[allow(dead_code)]
const LATCH_NO_SINK: NodeId = NodeId(5);
#[allow(dead_code)]
const ALREADY_LATCHED_TO_CAMP: NodeId = NodeId(6);
#[allow(dead_code)]
const CONCENTRATION_CAMP: NodeId = NodeId(7);
const CHAIN_1: NodeId = NodeId(8);
#[allow(dead_code)]
const CHAIN_2: NodeId = NodeId(9);
#[allow(dead_code)]
const CHAIN_3: NodeId = NodeId(10);
#[allow(dead_code)]
const ISOLATED_FALLBACK: NodeId = NodeId(11);
#[allow(dead_code)] // named for documentation symmetry with the id map above
const TENANT_1: NodeId = NodeId(12);
#[allow(dead_code)]
const TENANT_2: NodeId = NodeId(13);
#[allow(dead_code)]
const NON_TENANT: NodeId = NodeId(14);

/// Task 3, Step 2: the scenario loads clean and the node/edge census
/// matches the header's own count — no rule pack yet, load-only.
#[test]
fn the_scenario_loads_clean_with_the_declared_census() {
    let mut graph = HypergraphStore::new();
    let loaded = load_scenario(SCENARIO, &mut graph).expect("the scenario must load clean");
    assert_eq!(loaded.node_count, 15, "12 territories + 3 social classes");
    assert_eq!(loaded.edge_count, 7, "5 ADJACENCY + 2 TENANCY");
    assert_eq!(
        loaded.node_types.get("TERRITORY").copied(),
        Some(12),
        "twelve territory nodes"
    );
    assert_eq!(
        loaded.node_types.get("SOCIAL_CLASS").copied(),
        Some(3),
        "three social-class nodes"
    );
    assert_eq!(loaded.edge_types.get("ADJACENCY").copied(), Some(5));
    assert_eq!(loaded.edge_types.get("TENANCY").copied(), Some(2));
}

/// Every field the pack's four phases read must be present on every
/// territory (No-defaults contract) — a smoke read of all six declared
/// territory fields on every one of the twelve nodes, before any rule
/// exists to touch them.
#[test]
fn every_territory_seeds_all_six_declared_fields() {
    let mut graph = HypergraphStore::new();
    load_scenario(SCENARIO, &mut graph).expect("the scenario must load clean");
    for id in 0..12u64 {
        let node = NodeId(id);
        for field in [
            "territory/profile",
            "territory/territory-type",
            "territory/heat",
            "territory/rent-level-x1e6",
            "territory/under-eviction",
            "territory/population",
        ] {
            graph
                .node_attribute(node, field)
                .unwrap_or_else(|e| panic!("node {id} field {field}: {}", e.message));
        }
    }
}

/// A no-op tick (a rule that never fires) still hashes deterministically —
/// the load-only byte-determinism check this pack's later goldens build on.
#[test]
fn a_no_op_rule_is_deterministic_across_two_independent_loads() {
    const NO_OP_RULE: &str = r#"
(rule territory/noop-probe
  :material-basis "load-only smoke: prove the scenario alone hashes deterministically"
  :fuel 8
  (bindings (binding heat :field territory/heat))
  (when (< heat 0))
  (effects
    (update-node self territory/heat (set heat))))
"#;
    let a = run_once_into(
        SCENARIO,
        NO_OP_RULE,
        &mut HypergraphStore::new(),
        &mut babylon_bsl::structural_verbs::CollectingSink::default(),
    )
    .expect("the scenario plus a never-firing rule must still run");
    let b = run_once_into(
        SCENARIO,
        NO_OP_RULE,
        &mut HypergraphStore::new(),
        &mut babylon_bsl::structural_verbs::CollectingSink::default(),
    )
    .expect("second run");
    assert_eq!(a.before, b.before, "pre-tick hash reproducible");
    assert_eq!(a.after, b.after, "post-tick hash reproducible");
    assert_eq!(a.fired, 0, "no territory has heat < 0");
}

// ============================================================ Task 4: p1

const TERRITORY_RULES: &str = include_str!("../content/rules/territory.bsl");

fn run_territory() -> (HypergraphStore, babylon_tick::TickReport) {
    let mut graph = HypergraphStore::new();
    let mut sink = babylon_bsl::structural_verbs::CollectingSink::default();
    let report = run_once_into(SCENARIO, TERRITORY_RULES, &mut graph, &mut sink)
        .expect("the territory pack must load and run");
    (graph, report)
}

fn heat(graph: &HypergraphStore, id: NodeId) -> f64 {
    graph
        .node_attribute(id, "territory/heat")
        .unwrap_or_else(|e| panic!("node {id:?} territory/heat: {}", e.message))
}

/// `territory/p1-heat-dynamics`: HIGH_PROFILE gains exactly the defined
/// `high_profile_heat_gain` (0.15) — `sub-threshold-high`'s seed 0.3 -> 0.45.
#[test]
fn p1_high_profile_gains_exactly_the_defined_gain() {
    let (graph, _report) = run_territory();
    // Measured (ADR183), not derived: IEEE-754 `0.3 + 0.15` does NOT land
    // on the correctly-rounded literal `0.45` — it is one ULP below
    // (`0.44999999999999996`). The frozen Python mirror's own printed
    // output (`territory_conformance.py`) agrees bit-for-bit
    // (`heat=0.44999999999999996`): both engines perform the identical
    // `heat + gain` binary64 add.
    assert_eq!(
        heat(&graph, SUB_THRESHOLD_HIGH).to_bits(),
        0.44999999999999996_f64.to_bits(),
        "0.3 + 0.15, measured — matches the frozen mirror's own printed float bit for bit"
    );
}

/// LOW_PROFILE decays by `(1 - heat_decay_rate)` = x0.9 —
/// `sub-threshold-low`'s seed 0.4 -> ~0.36.
#[test]
fn p1_low_profile_decays_by_the_defined_rate() {
    let (graph, _report) = run_territory();
    // Measured (ADR183): `0.4 * 0.9` is one ULP above the correctly-rounded
    // `0.36` literal (`0.36000000000000004`) — matches the frozen mirror's
    // own printed output bit for bit.
    assert_eq!(
        heat(&graph, SUB_THRESHOLD_LOW).to_bits(),
        0.36000000000000004_f64.to_bits(),
        "0.4 * 0.9, measured — matches the frozen mirror's own printed float bit for bit"
    );
}

/// `chain-1`'s seed 0.9 + 0.15 = 1.05, over the [0,1] ceiling — the
/// `system_base.py::_write_clamped` double-clamp idiom (nested-if, floor
/// then ceiling) must land it at EXACTLY 1.0, not 1.05.
#[test]
fn p1_clamps_the_ceiling_at_exactly_one() {
    let (graph, _report) = run_territory();
    assert_eq!(
        heat(&graph, CHAIN_1),
        1.0,
        "0.9 + 0.15 = 1.05 must clamp to exactly 1.0"
    );
}

/// `:fuel`/guard shape: `(when #t)` fires unconditionally — every one of
/// the twelve territories, and nothing else (the three social classes
/// carry no `territory/*` fields, so they are not this rule's subject
/// type at all).
#[test]
fn p1_fires_on_every_seeded_territory() {
    let (_graph, report) = run_territory();
    let p1_fired = report
        .per_rule_fired
        .iter()
        .find(|(id, _)| id == "territory/p1-heat-dynamics")
        .map(|(_, n)| *n);
    assert_eq!(p1_fired, Some(12), "all twelve territories, unconditional");
}
