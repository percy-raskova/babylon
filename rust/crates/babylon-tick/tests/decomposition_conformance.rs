//! Registration + scenario-ceremony conformance for the joint Decomposition
//! (@11.0) + ControlRatio (@12.0) port train — Task 1 of
//! `docs/superpowers/plans/2026-08-17-decomposition-controlratio-port.md`
//! (frozen source: `src/babylon/engine/systems/decomposition.py`, 370
//! lines, + `src/babylon/engine/systems/control_ratio.py`, 248 lines).
//!
//! # Task 1 scope
//!
//! This task ships NO `decomposition/*`/`control-ratio/*` rule pack content
//! (that is Task 2 onward) — it registers both systems in `lib.rs`, builds
//! the shared conformance world (`content/scenarios/
//! decomposition-conformance.bscn`), carries the frozen-mirror provenance
//! below, and records THE SPIKE verdict (plan §2's RISK box) that later
//! tasks depend on.
//!
//! # Step 1 red-phase note
//!
//! `scenario_and_empty_pack_load` (below) was written and run BEFORE
//! `"decomposition"`/`"control-ratio"` were added to `lib.rs`'s
//! registered-system `HashSet`; it failed with:
//!
//! ```text
//! rule decomposition/probe rejected: E-LOAD-002: rule decomposition/probe
//! carries no anchor and its first id segment names no registered system —
//! a rule cannot land nowhere (§2.3)
//! ```
//!
//! — confirming the probe reaches the real anchor check
//! (`mod_anchors::check_anchor` against `ctx.systems`, `rule_pipeline.rs:313`)
//! rather than failing for an unrelated reason (the scenario's own
//! declarations loaded clean). Registering both systems turned it green.
//! Same deviation from the plan's literal "empty rule source" text that
//! `production_conformance.rs:75-94` already recorded: `run_once_into`'s own
//! `split_content` refuses a content set with zero `(rule …)` top-forms
//! outright, so a truly empty source cannot reach the anchor check at all;
//! this test uses two minimal, never-firing probe rules instead, one per
//! newly-registered system.
//!
//! # THE SPIKE (Step 5) — verdict
//!
//! Two throwaway spike rules were run through the real `run_once_into`
//! driver against this exact scenario, then deleted (their bodies never
//! landed in this file):
//!
//! - **(a)** a carrier-anchored rule (`:field institution/…` binding) folding
//!   `(fold sum (nodes NodeType/SOCIAL_CLASS) (field-of it
//!   social-class/population))` into `institution/la-population` — LOADED,
//!   EVALUATED, and produced the correct sum: `1000 + 20 + 77 + 200 + 10 =
//!   1307`, asserted directly against the post-tick graph before deletion.
//! - **(b)** a class-anchored rule reading `(field-of (select-max (nodes
//!   NodeType/INSTITUTION) 1) institution/decomposition-complete)` — LOADED
//!   AND EVALUATED CLEAN.
//!
//! **Neither shape refused.** The incidence-edge fallback design (seeding a
//! carrier→class edge and reading via `neighbors`) is NOT needed; Task 2
//! onward relies on both shapes directly, exactly as plan §2 specifies. This
//! is also the FIRST landed content to use `NodeType/INSTITUTION` as a
//! singleton carrier reached via `(select-max (nodes NodeType/INSTITUTION)
//! 1)`, and the FIRST to fold over `(nodes NodeType/SOCIAL_CLASS)` rather
//! than a `neighbors` query — every prior `fold`/`select-max` in the landed
//! estate reads `neighbors` (`territory.bsl:157-160`, `production.bsl:172-
//! 175`), which is capability precedent, not content precedent; this
//! scenario is the content precedent.
//!
//! # Frozen-mirror provenance
//!
//! Every state value below was printed by the frozen `DecompositionSystem`
//! (@11.0) then `ControlRatioSystem` (@12.0), one `step()` each, sharing ONE
//! `TickContext.persistent_data` dict (matching the frozen engine's own
//! single `context` threaded through every system in a tick), over a
//! fixture that mirrors `decomposition-conformance.bscn` node for node. The
//! command, from the repository root:
//!
//! ```text
//! PYTHONPATH="$PWD/src" UV_FROZEN=1 uv run python \
//!     rust/crates/babylon-tick/content/scenarios/decomposition_conformance.py
//! ```
//!
//! Its output on 2026-08-17, verbatim:
//!
//! ```text
//! defines (src/babylon/data/defines.yaml, carceral: section):
//!   carceral.control_capacity = 4
//!   carceral.enforcer_fraction = 0.15
//!   carceral.proletariat_fraction = 0.85
//!   carceral.revolution_threshold = 0.5
//!   carceral.decomposition_delay = 52
//!   carceral.control_ratio_delay = 52
//!   carceral.terminal_decision_delay = 1
//!   carceral.<approaching-consumption-multiple> = 2  (bare literal, decomposition.py:155, NO defines backing)
//!
//! post-tick persistent_data (the frozen state machine §2 reformulates onto the carrier):
//!   _class_decomposition_tick = 1
//!   _decomposition_complete = True
//!   _superwage_crisis_tick = 1
//!
//! post-tick social classes:
//!   la-dying       active=False population=1000 (seed 1000) wealth=400.0 (seed 400.0)
//!   enforcer-seed  active=True population=170 (seed 20) wealth=160.0 (seed 100.0)
//!   ip-seed        active=True population=850 (seed 77) wealth=340.0 (seed 33.0)
//!   lumpen         active=True population=200 (seed 200) wealth=10.0 (seed 10.0)
//!   bourgeois      active=True population=10 (seed 10) wealth=9000.0 (seed 9000.0)
//!
//! events:
//!   superwage_crisis {'payer_id': 'C003', 'receiver_id': 'la-dying', 'desired_wages': 0.0, 'available_pool': 0.0, 'narrative_hint': 'SUPERWAGE CRISIS: Labor aristocracy wealth collapsing. Super-wages cannot sustain the privileged stratum.'}
//!   class_decomposition {'source_class': 'la-dying', 'source_population': 1000, 'source_wealth': 400.0, 'enforcer_fraction': 0.15, 'proletariat_fraction': 0.85, 'population_transferred': {'to_enforcer': 150, 'to_proletariat': 850}, 'wealth_transferred': {'to_enforcer': 60.0, 'to_proletariat': 340.0}, 'trigger_event': 'superwage_crisis', 'narrative_hint': 'CLASS DECOMPOSITION: Labor aristocracy collapses. 150 become guards/cops. 850 fall into the precariat.'}
//! ```
//!
//! **Both the early-warning `SUPERWAGE_CRISIS` and the fallback-triggered
//! `CLASS_DECOMPOSITION` fire in the SAME tick** — a real, observed frozen
//! behavior, not a design assumption: `la-dying`'s wealth (400) is both
//! `< subsistence_threshold + 2*consumption` (500 + 2*10 = 520, the
//! "approaching" early-warning gate) AND `< subsistence_threshold` (500, the
//! `la_about_to_die` fallback gate), and `DecompositionSystem.step()`
//! evaluates both gates sequentially within one call
//! (`decomposition.py:179-223`) with no tick-order separation between them.
//! `ip-seed`'s OVERWRITE (`population: 77 -> 850`, NOT `77 + 850`) versus
//! `enforcer-seed`'s ADDITIVE gain (`population: 20 -> 170 = 20 + 150`) is
//! exactly the two mutation shapes the scenario's own header names as
//! provable by this fixture's non-zero pre-seeds.
//!
//! # Why exact equality and no tolerance
//!
//! `Int * Real` and `int()` truncation are the only operations either engine
//! performs to reach the numbers above — both correctly-rounded binary64
//! (`bsl-language.rst` §4.3) — so later tasks' Rust-side pins may assert
//! exact equality against BSL-measured values, not against these printed
//! floats (ADR183: this mirror is a structure/ordering oracle, not a byte
//! oracle; no `decomposition/*`/`control-ratio/*` rule exists yet in Task 1
//! to measure BSL-side numbers from).
//!
//! # Task 2 — Pack A's p01 (LA census) + p02 (early warning)
//!
//! The four tests below are the first `decomposition/*` rules to run
//! against this world; every asserted value is measured from the BSL engine
//! itself (`content/rules/decomposition.bsl`), cross-checked by hand against
//! the frozen mirror's dump above: `la-dying`'s census carries its own
//! population (1000) and wealth (400.0) exactly, both flags fire (wealth
//! 400 < subsistence 500 < subsistence + 2*consumption 520), and every
//! other class's four census fields stay at their seeded 0 (the D127
//! hash-neutral idiom — p01 has no `when` clause). `SUPERWAGE_CRISIS` fires
//! exactly once with the flattened 3-key payload (D-records 4/5 in
//! `decomposition.bsl`'s header: `payer_id`/`narrative_hint` dropped, no
//! string payloads on `emit`), and the carrier latches
//! `superwage-crisis-known`/`-tick` (1 / tick 1) the SAME tick — matching
//! the frozen mirror's `_superwage_crisis_tick = 1`.
//!
//! **Fuel — measured, not guessed, per the E-LOAD-040 refusal readback,
//! THEN the documented `bound ≥ :fuel` / runtime `bound + 1` off-by-one
//! (`bsl-language.rst` §4.5, "authors should budget `:fuel ≥ bound + 1`"):**
//! p01's rule declared with `:fuel 1` refused at load with `E-LOAD-040:
//! rule decomposition/p01-la-census static bound 72 exceeds its declared
//! :fuel 1`; p02 (once p01's fuel was raised) refused the same way at
//! `static bound 32`. Setting `:fuel` to those EXACT computed bounds (72,
//! 32) loads clean but then `E-EVAL-040`s at runtime ("fuel meter reached
//! zero") — the documented §3.7/§4.5 boundary: the load check accepts
//! `bound == :fuel`, but the runtime meter must stay strictly positive, so
//! the true minimum is `bound + 1`. `:fuel 73` / `:fuel 33` (measured
//! bound + 1, not a round margin) is what the rules below declare.

use babylon_bsl::evaluator::Value;
use babylon_bsl::scenario::load_scenario;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::substrate::{GraphSubstrate, NodeId};
use babylon_tick::run_once_into;

const SCENARIO: &str = include_str!("../content/scenarios/decomposition-conformance.bscn");
const RULE: &str = include_str!("../content/rules/decomposition.bsl");

// Node ids, fixed by the scenario's own declaration order (the scenario's
// own header names the same map; territory-conformance.bscn/territory_
// conformance.rs precedent).
const LA_DYING: NodeId = NodeId(0);
const ENFORCER_SEED: NodeId = NodeId(1);
const IP_SEED: NodeId = NodeId(2);
const LUMPEN: NodeId = NodeId(3);
const BOURGEOIS: NodeId = NodeId(4);
const CARCERAL_REGISTER: NodeId = NodeId(5);

/// Task 2 scope: Pack A's p01 (LA census) + p02 (early warning) only.
fn run() -> (HypergraphStore, CollectingSink) {
    let mut graph = HypergraphStore::new();
    let mut sink = CollectingSink::default();
    run_once_into(SCENARIO, RULE, &mut graph, &mut sink).expect("the Pack A rules must run");
    (graph, sink)
}

fn attribute(graph: &HypergraphStore, id: NodeId, field: &str) -> f64 {
    graph
        .node_attribute(id, field)
        .unwrap_or_else(|e| panic!("node {id:?} field {field}: {}", e.message))
}

/// p01 publishes the LA census ONLY for the active LA — every other class
/// (a different role, or an inactive one) writes zero to all four census
/// fields, the D127 hash-neutral idiom (no `when` skip).
#[test]
fn p01_publishes_the_la_census_only_for_the_active_la() {
    let (graph, _) = run();
    assert_eq!(
        attribute(&graph, LA_DYING, "social-class/la-census-population"),
        1000.0,
        "la-dying: la-census-population"
    );
    assert_eq!(
        attribute(&graph, LA_DYING, "social-class/la-census-wealth"),
        400.0,
        "la-dying: la-census-wealth"
    );
    for (id, name) in [
        (ENFORCER_SEED, "enforcer-seed"),
        (IP_SEED, "ip-seed"),
        (LUMPEN, "lumpen"),
        (BOURGEOIS, "bourgeois"),
    ] {
        for field in [
            "social-class/la-census-population",
            "social-class/la-census-wealth",
            "social-class/la-approaching-flag",
            "social-class/la-dying-flag",
        ] {
            assert_eq!(
                attribute(&graph, id, field),
                0.0,
                "{name}: {field} must be 0"
            );
        }
    }
}

/// p01's two flags: `la-dying`'s wealth (400) is below both subsistence
/// (500, the dying gate) and subsistence + 2*consumption (520, the
/// approaching gate) — `wealth < subsistence` implies
/// `wealth < subsistence + 2*consumption` since consumption >= 0.
#[test]
fn p01_flags_the_dying_la() {
    let (graph, _) = run();
    assert_eq!(
        attribute(&graph, LA_DYING, "social-class/la-dying-flag"),
        1.0,
        "la-dying: la-dying-flag"
    );
    assert_eq!(
        attribute(&graph, LA_DYING, "social-class/la-approaching-flag"),
        1.0,
        "la-dying: la-approaching-flag"
    );
}

/// p02 emits exactly one SUPERWAGE_CRISIS, with the flattened payload
/// (`payer_id`/`narrative_hint` dropped, D-record 4/5) — `receiver` is a
/// NodeRef to the LA subject itself.
#[test]
fn p02_emits_superwage_crisis_once_with_the_receiver_ref() {
    let (_, sink) = run();
    let crises: Vec<_> = sink
        .events
        .iter()
        .filter(|(ty, _)| ty == "SUPERWAGE_CRISIS")
        .collect();
    assert_eq!(crises.len(), 1, "exactly one SUPERWAGE_CRISIS this tick");
    let (_, payload) = crises[0];
    assert_eq!(
        payload[0],
        ("receiver".to_owned(), Value::NodeRef(LA_DYING))
    );
    assert_eq!(payload[1], ("desired-wages".to_owned(), Value::Real(0.0)));
    assert_eq!(payload[2], ("available-pool".to_owned(), Value::Real(0.0)));
}

/// p02 latches the carrier's `superwage-crisis-known`/`-tick` the SAME tick
/// it emits — decomposition.py:196-197's `persistent["_superwage_crisis_
/// tick"] = tick`.
#[test]
fn p02_latches_the_crisis_tick_on_the_carrier() {
    let (graph, _) = run();
    assert_eq!(
        attribute(
            &graph,
            CARCERAL_REGISTER,
            "institution/superwage-crisis-known"
        ),
        1.0,
        "carrier: superwage-crisis-known"
    );
    assert_eq!(
        attribute(
            &graph,
            CARCERAL_REGISTER,
            "institution/superwage-crisis-tick"
        ),
        1.0,
        "carrier: superwage-crisis-tick == tick 1 (run_once_into always runs tick 1)"
    );
}

/// The load-smoke test, through the REAL `run_once_into` seam — proves the
/// scenario loads clean against BOTH newly-registered systems.
#[test]
fn scenario_and_empty_pack_load() {
    const PROBE_RULE: &str = r#"
(rule decomposition/probe
  :material-basis "load-only smoke: prove the scenario loads against a registered decomposition system"
  :fuel 8
  (bindings (binding wealth :field social-class/wealth))
  (when (< wealth 0))
  (effects
    (update-node self social-class/wealth (set wealth))))

(rule control-ratio/probe
  :material-basis "load-only smoke: prove the scenario loads against a registered control-ratio system"
  :fuel 8
  (bindings (binding pop :field social-class/population))
  (when (< pop 0))
  (effects
    (update-node self social-class/population (set pop))))
"#;
    let mut graph = HypergraphStore::new();
    let mut sink = babylon_bsl::structural_verbs::CollectingSink::default();
    run_once_into(SCENARIO, PROBE_RULE, &mut graph, &mut sink)
        .expect("the scenario must load and run against BOTH registered-system probe rules");
}

/// The scenario's own node census, independent of any rule pack — five
/// `SOCIAL_CLASS` fixtures plus the one `INSTITUTION` carrier, no edges
/// (the census is type-scoped via `nodes`, plan §2's own "why no edges are
/// needed" note).
#[test]
fn the_scenario_loads_clean_with_the_declared_census() {
    let mut graph = HypergraphStore::new();
    let loaded = load_scenario(SCENARIO, &mut graph).expect("the scenario must load clean");
    assert_eq!(loaded.node_count, 6, "5 social classes + 1 carrier");
    assert_eq!(
        loaded.edge_count, 0,
        "the census is type-scoped, no edges needed"
    );
    assert_eq!(
        loaded.node_types.get("SOCIAL_CLASS").copied(),
        Some(5),
        "five social-class nodes"
    );
    assert_eq!(
        loaded.node_types.get("INSTITUTION").copied(),
        Some(1),
        "exactly one carrier — this is what gives NodeType/INSTITUTION ceiling 1"
    );
}

/// The `defenum` ordinal-parity test (class-surface plan amendment 7),
/// mirroring `tick_goldens.rs::worldview_member_order_is_the_ruled_ordinal`
/// — THIS scenario's own `SocialRole` re-declaration (not shared across
/// scenarios) must store the SAME eight members in the SAME order as
/// `src/babylon/models/enums/social.py:34-41` (ADR195: declaration order IS
/// the storage ordinal).
#[test]
fn social_role_order_is_the_ruled_ordinal() {
    let mut graph = HypergraphStore::new();
    let loaded = load_scenario(SCENARIO, &mut graph).expect("the scenario must load clean");
    let ty = loaded
        .enums
        .resolve("SocialRole")
        .expect("the SocialRole defenum is declared");
    let members = [
        "CORE_BOURGEOISIE",
        "PERIPHERY_PROLETARIAT",
        "LABOR_ARISTOCRACY",
        "PETTY_BOURGEOISIE",
        "LUMPENPROLETARIAT",
        "COMPRADOR_BOURGEOISIE",
        "INTERNAL_PROLETARIAT",
        "CARCERAL_ENFORCER",
    ];
    for (ordinal, member) in members.iter().enumerate() {
        assert_eq!(
            loaded.enums.ordinal(ty, member),
            Some(ordinal as u32),
            "SocialRole::{member} must sit at ordinal {ordinal} (ADR195)"
        );
    }
}
