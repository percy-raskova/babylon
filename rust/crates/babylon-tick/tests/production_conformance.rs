//! Conformance vectors for the `production/*` rule pack (P27, issue #565 —
//! the Production port train, `docs/superpowers/plans/2026-08-12-production-
//! port-plan.md`), taken from the frozen Python engine's live behaviour.
//!
//! # Provenance
//!
//! Every STRUCTURAL claim below (which fields moved, in which direction, the
//! accumulation set, the extraction-intensity aggregate) was checked against
//! the frozen `ProductionSystem` running one `step()` over a fixture that
//! mirrors `content/scenarios/production-conformance.bscn` node for node.
//! The command, from the repository root:
//!
//! ```text
//! PYTHONPATH="$PWD/src" uv run python \
//!     rust/crates/babylon-tick/content/scenarios/production_conformance.py
//! ```
//!
//! The frozen system is the contract source for STRUCTURE and ORDERING, not
//! a correctness oracle (ADR183) — the port train's own D-records
//! (`production.bsl`'s header) name every place this pack's arithmetic
//! diverges from the frozen engine's field shape. Every NUMERIC value pinned
//! below is measured from the BSL engine's own output, never copied from the
//! frozen mirror's printed floats.
//!
//! # Scenario census (Task 1)
//!
//! Eight social classes, four territories, eleven edges (eight TENANCY,
//! three WAGES) — see `production-conformance.bscn`'s own header for the
//! full per-node conformance-case map.

use babylon_bsl::scenario::load_scenario;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::substrate::{GraphSubstrate, NodeId};
use babylon_tick::run_once_into;

const SCENARIO: &str = include_str!("../content/scenarios/production-conformance.bscn");

// Node ids, fixed by the scenario's own declaration order
// (`production-conformance.bscn`'s own header names the same map). Several
// are unused until later tasks (p2/p3's LA-worker vectors, p4's territory
// fold) accrete their own tests — named now, for documentation symmetry
// with the scenario's own header, per `territory_conformance.rs`'s
// precedent.
const WORKER_PP: NodeId = NodeId(0);
#[allow(dead_code)]
const WORKER_PP_TWO_LANDS: NodeId = NodeId(1);
#[allow(dead_code)]
const WORKER_LA_ONE: NodeId = NodeId(2);
#[allow(dead_code)]
const WORKER_LA_TWO: NodeId = NodeId(3);
#[allow(dead_code)]
const WORKER_LA_ORPHAN: NodeId = NodeId(4);
#[allow(dead_code)]
const WORKER_LA_IDLE: NodeId = NodeId(5);
const COMPRADOR: NodeId = NodeId(6);
const EMPLOYER: NodeId = NodeId(7);
#[allow(dead_code)]
const T_ALPHA: NodeId = NodeId(8);
#[allow(dead_code)]
const T_BETA: NodeId = NodeId(9);
#[allow(dead_code)]
const T_DEAD: NodeId = NodeId(10);
#[allow(dead_code)]
const T_EMPTY: NodeId = NodeId(11);

/// Task 1, Step 1: the load-smoke test, through the REAL `run_once_into`
/// seam — proves BOTH halves the plan names (`Expected: FAIL (unregistered
/// system / missing scenario)`).
///
/// **Deviation from the plan's literal text (plan line 41):** the plan
/// describes "an empty rule source"; `run_once_into`'s own `split_content`
/// refuses a content set with zero `(rule …)` top-forms outright
/// ("a content set needs at least one (rule …) top-form, found 0") —
/// confirmed by running exactly that against `lib.rs` before this rule
/// existed. A truly empty rule source therefore cannot exercise the
/// system-registration gate at all; it fails for an unrelated, earlier
/// reason. This test uses a minimal, never-firing probe rule anchored at
/// `production/probe` instead — the same idiom
/// `territory_conformance.rs::a_no_op_rule_is_deterministic_across_two_
/// independent_loads` uses for the identical purpose — which DOES reach the
/// anchor check (`mod_anchors::check_anchor` against `ctx.systems`,
/// `rule_pipeline.rs:313`) `"production"` was NOT yet in `lib.rs`'s
/// registered-system `HashSet` (`lib.rs:174-205`) at the time this test was
/// first written, and the probe genuinely failed with an unregistered-
/// system anchor error — confirmed by running it before Task 1 Step 2's
/// registration edit landed.
#[test]
fn scenario_loads_with_a_probe_pack() {
    const PROBE_RULE: &str = r#"
(rule production/probe
  :material-basis "load-only smoke: prove the scenario loads against a registered production system"
  :fuel 8
  (bindings (binding wealth :field social-class/wealth))
  (when (< wealth 0))
  (effects
    (update-node self social-class/wealth (set wealth))))
"#;
    let mut graph = HypergraphStore::new();
    let mut sink = babylon_bsl::structural_verbs::CollectingSink::default();
    run_once_into(SCENARIO, PROBE_RULE, &mut graph, &mut sink)
        .expect("the scenario must load and run against a registered-system probe rule");
}

/// The scenario's own node/edge census, independent of any rule pack.
#[test]
fn the_scenario_loads_clean_with_the_declared_census() {
    let mut graph = HypergraphStore::new();
    let loaded = load_scenario(SCENARIO, &mut graph).expect("the scenario must load clean");
    assert_eq!(loaded.node_count, 12, "8 social classes + 4 territories");
    assert_eq!(loaded.edge_count, 11, "8 TENANCY + 3 WAGES");
    assert_eq!(
        loaded.node_types.get("SOCIAL_CLASS").copied(),
        Some(8),
        "eight social-class nodes"
    );
    assert_eq!(
        loaded.node_types.get("TERRITORY").copied(),
        Some(4),
        "four territory nodes"
    );
    assert_eq!(loaded.edge_types.get("TENANCY").copied(), Some(8));
    assert_eq!(loaded.edge_types.get("WAGES").copied(), Some(3));
}

/// Every field the pack's four rules read must be present on every node of
/// its own subject type (No-defaults contract) — a smoke read of all five
/// declared social-class fields and all three declared territory fields,
/// before any rule exists to touch them.
#[test]
fn every_node_seeds_all_its_declared_fields() {
    let mut graph = HypergraphStore::new();
    load_scenario(SCENARIO, &mut graph).expect("the scenario must load clean");
    for id in 0..8u64 {
        let node = NodeId(id);
        for field in [
            "social-class/role",
            "social-class/active",
            "social-class/population",
            "social-class/wealth",
            "social-class/production-value",
        ] {
            graph
                .node_attribute(node, field)
                .unwrap_or_else(|e| panic!("node {id} field {field}: {}", e.message));
        }
    }
    for id in 8..12u64 {
        let node = NodeId(id);
        for field in [
            "territory/biocapacity",
            "territory/max-biocapacity",
            "territory/extraction-intensity",
        ] {
            graph
                .node_attribute(node, field)
                .unwrap_or_else(|e| panic!("node {id} field {field}: {}", e.message));
        }
    }
}

// ============================================================ Task 2: p1

const PRODUCTION_RULE: &str = include_str!("../content/rules/production.bsl");

fn run_production() -> (HypergraphStore, babylon_tick::TickReport) {
    let mut graph = HypergraphStore::new();
    let mut sink = babylon_bsl::structural_verbs::CollectingSink::default();
    let report = run_once_into(SCENARIO, PRODUCTION_RULE, &mut graph, &mut sink)
        .expect("the production pack must load and run");
    (graph, report)
}

fn wealth(graph: &HypergraphStore, id: NodeId) -> f64 {
    graph
        .node_attribute(id, "social-class/wealth")
        .unwrap_or_else(|e| panic!("node {id:?} social-class/wealth: {}", e.message))
}

fn production_value(graph: &HypergraphStore, id: NodeId) -> f64 {
    graph
        .node_attribute(id, "social-class/production-value")
        .unwrap_or_else(|e| panic!("node {id:?} social-class/production-value: {}", e.message))
}

/// `production/p1-direct-production`: `worker-pp` (PERIPHERY_PROLETARIAT,
/// TENANCY to `t-alpha`, biocapacity 80/100) accumulates its own wealth by
/// exactly `(base_labor_power / weeks_per_year) * population * bio_ratio` =
/// `(1.0/52) * 100 * 0.8` — measured, matching the frozen mirror's own
/// printed `worker-pp wealth=11.538461538461538` bit for bit (this rule's
/// binding chain is a direct, unreordered transcription of production.py's
/// own `(effective_labor_power * population) * bio_ratio`, so bit-identical
/// agreement is the expected, not merely hoped-for, result — ADR183 still
/// requires it be measured, not assumed).
#[test]
fn p1_direct_producer_accumulates_own_wealth() {
    let (graph, _report) = run_production();
    assert_eq!(
        wealth(&graph, WORKER_PP).to_bits(),
        11.538461538461538_f64.to_bits(),
        "10 + (1/52)*100*0.8, measured — matches the frozen mirror's own printed float bit for bit"
    );
    assert_eq!(
        production_value(&graph, WORKER_PP).to_bits(),
        1.5384615384615385_f64.to_bits(),
        "the produced value itself, written to the new per-node ledger field"
    );
}

/// p1's `when` guard is role-scoped to `PERIPHERY_PROLETARIAT` alone —
/// `comprador` (COMPRADOR_BOURGEOISIE, holds a TENANCY edge to `t-alpha`)
/// and `employer` (CORE_BOURGEOISIE, no TENANCY at all) are both untouched:
/// their seed wealth (10.0) stays exactly as seeded.
#[test]
fn p1_leaves_non_producer_roles_wealth_unmoved() {
    let (graph, _report) = run_production();
    assert_eq!(
        wealth(&graph, COMPRADOR),
        10.0,
        "comprador: not a producer role"
    );
    assert_eq!(
        wealth(&graph, EMPLOYER),
        10.0,
        "employer: not a producer role, no TENANCY"
    );
}
