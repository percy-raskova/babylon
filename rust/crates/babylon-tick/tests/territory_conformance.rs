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
