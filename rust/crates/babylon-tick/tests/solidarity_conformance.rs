//! Conformance vectors for `solidarity/p0-transmit` (the Solidarity @8.0
//! port train, frozen `src/babylon/engine/systems/solidarity.py`, issue
//! #557 umbrella) — `docs/superpowers/plans/2026-08-17-solidarity-port.md`.
//!
//! # Task 1 scope
//!
//! This file lands the loadable namespace and the conformance world every
//! later task's witness asserts on (Tasks 2-5). Task 1 itself asserts only
//! that the world loads, through the real `run_once_into` seam, and that
//! its node/edge census matches declaration. No transmission rule exists
//! yet — `content/rules/solidarity.bsl` lands in Task 2 — so this file uses
//! an inline, never-firing PROBE rule to exercise the seam, the same idiom
//! `production_conformance.rs`'s own Task 1
//! (`scenario_loads_with_a_probe_pack`) used for the identical reason: an
//! empty rule source cannot exercise `run_once_into` at all
//! (`split_content` refuses a content set with zero `(rule …)` forms
//! outright, independent of system registration), so a probe rule is the
//! only way to reach the load path this test exists to prove.
//!
//! # §4.2 spike verdict (Task 1 step 2)
//!
//! **PASS, no fallback needed.** A throwaway `solidarity/`-namespaced rule
//! and a throwaway `solidarity/`-namespaced defconst were loaded together
//! via `run_once` (in a scratch test, deleted once the verdict was
//! recorded) after adding `"solidarity"` to `lib.rs`'s `systems` HashSet,
//! and the load succeeded with no `E-LOAD-*` error — confirming
//! `load_defconst`'s `consts` map and the rule-id anchor /
//! `:field`/`:const` binding resolution paths do not collide on a shared
//! `solidarity/` prefix, exactly as
//! `docs/superpowers/plans/2026-08-17-solidarity-port.md` §4.2 predicted
//! from reading `scenario.rs:517-545`. See
//! `content/scenarios/solidarity-conformance.bscn`'s own header for the
//! same verdict recorded a second, permanent place.
//!
//! # Provenance
//!
//! The world is `content/scenarios/solidarity-conformance.bscn`, built
//! fresh per the plan §8 (neither `edge-write-lane-e2e.bscn` nor
//! `consciousness-ternary-conformance.bscn` is reusable as-is). Its own
//! header documents every witness group's shape and exact arithmetic; see
//! that file for the per-node rationale. Task 2 replaces `PROBE_RULE`
//! below with `content/rules/solidarity.bsl`'s real `solidarity/p0-transmit`
//! and extends this file with per-witness value assertions.

use babylon_bsl::scenario::load_scenario;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::memory::MemoryGraph;
use babylon_tick::{run_once, run_once_into};

const SCENARIO: &str = include_str!("../content/scenarios/solidarity-conformance.bscn");

/// A minimal, NEVER-FIRING probe: reads a field every node in the world
/// declares (`social-class/revolutionary`, a `probability` field whose
/// domain is `[0,1]`) and gates on a condition no seed can satisfy
/// (`< r 0`). Exists solely to reach the anchor check
/// (`mod_anchors::check_anchor` against `ctx.systems`) — the same idiom
/// `production_conformance.rs::scenario_loads_with_a_probe_pack` uses.
/// Task 2 deletes this constant along with the whole `run()`/probe
/// apparatus once `content/rules/solidarity.bsl` exists.
const PROBE_RULE: &str = r#"
(rule solidarity/probe
  :material-basis "load-only smoke: prove the scenario loads against a registered solidarity system (Task 1); Task 2 replaces this probe with solidarity/p0-transmit"
  :fuel 8
  (bindings (binding r :field social-class/revolutionary :optional :default 0.0p))
  (when (< r 0))
  (effects
    (update-node self social-class/revolutionary (set r))))
"#;

fn run() -> (MemoryGraph, CollectingSink) {
    let mut graph = MemoryGraph::new();
    let mut sink = CollectingSink::default();
    run_once_into(SCENARIO, PROBE_RULE, &mut graph, &mut sink)
        .expect("the Solidarity conformance world must load and run against a registered system");
    (graph, sink)
}

/// The world loads through the real `run_once_into` seam, and its
/// node/edge census matches what the `.bscn` declares: 22 `SOCIAL_CLASS`
/// nodes and 12 `SOLIDARITY` edges (plan §8's four witness groups — plain
/// transmission (1 pair), MASS_AWAKENING crossing (1 shared source + 3
/// targets), the three skip gates (3 pairs), multi-inbound divergence (2
/// sources -> 1 target) — plus the inactive-source pair, the
/// inactive-target pair, and the clamp pair; see the `.bscn`'s own node
/// census for the exact id-to-witness map).
///
/// The probe never fires (`r` is always `>= 0` on a `probability` field,
/// so `< r 0` is never true) — this test does not depend on that, but a
/// nonzero `fired` count here would mean the probe rule itself is
/// malformed, not that the pack "works", so it is asserted too as a
/// sanity check on the probe's own never-firing claim.
#[test]
fn the_conformance_world_loads_with_the_declared_census() {
    let (_graph, _sink) = run();

    let mut probe_graph = MemoryGraph::new();
    let loaded = load_scenario(SCENARIO, &mut probe_graph).expect("the scenario must load clean");
    assert_eq!(loaded.node_count, 22, "22 SOCIAL_CLASS witness nodes");
    assert_eq!(loaded.edge_count, 12, "12 SOLIDARITY witness edges");
    assert_eq!(
        loaded.node_types.get("SOCIAL_CLASS").copied(),
        Some(22),
        "every declared node is a SOCIAL_CLASS (the plan's single-subject-type ruling, §2.1)"
    );
    assert_eq!(
        loaded.edge_types.get("SOLIDARITY").copied(),
        Some(12),
        "every declared edge is SOLIDARITY"
    );

    let report = run_once(SCENARIO, PROBE_RULE).expect("run_once must agree with run_once_into");
    assert_eq!(
        report.fired, 0,
        "the probe's guard (< r 0) is unsatisfiable on a [0,1] field — nothing fires yet"
    );
}
