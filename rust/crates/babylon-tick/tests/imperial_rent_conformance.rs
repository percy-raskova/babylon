//! Registration + scenario-ceremony conformance for the ImperialRent BSL
//! port train (Material Base @9.0, Checkpoint A campaign) — Task 1 of
//! `docs/superpowers/plans/2026-08-18-imperialrent-port.md` (frozen source:
//! `src/babylon/engine/systems/economic.py::ImperialRentSystem`, `step()` at
//! `:46-86`, 837 lines total).
//!
//! # Task 1 scope
//!
//! This task ships NO `imperial-rent/*` rule pack content (that is Task 2
//! onward) — it registers the system in `lib.rs`, builds the shared world-1
//! conformance scenario (`content/scenarios/imperial-rent-conformance.bscn`),
//! carries the frozen-mirror provenance below, and records THE SPIKE
//! verdict (plan §8's Task 1 Step 5) that later tasks depend on.
//!
//! Where this train's own dossier
//! (`reports/imperial-rent-bsl-surface-facts-2026-08-18.md`) and the task
//! brief disagree, the dossier governs — notably: B7 is STRUCK (no
//! `social-class/class-consciousness` field; the frozen accessor already
//! re-points to `social-class/revolutionary`, matching `solidarity.bsl`'s
//! own identical re-point), and this train's ADR number is
//! NEXT-FREE-AT-LANDING (ADR215 as of the dossier's 2026-08-18 measurement,
//! re-checked whenever an ADR actually files).
//!
//! # Step 1 red-phase note
//!
//! `scenario_and_empty_pack_load` (below) was written and run BEFORE
//! `"imperial-rent"` was added to `lib.rs`'s registered-system `HashSet`
//! (verified by temporarily reverting the registration and re-running this
//! one test); it failed with:
//!
//! ```text
//! rule imperial-rent/probe rejected: E-LOAD-002: rule imperial-rent/probe
//! carries no anchor and its first id segment names no registered system —
//! a rule cannot land nowhere (§2.3)
//! ```
//!
//! — confirming the probe reaches the real anchor check
//! (`mod_anchors::check_anchor` against `ctx.systems`, `rule_pipeline.rs:313`)
//! rather than failing for an unrelated reason (the scenario's own
//! declarations loaded clean). Registering the system turned it green. Same
//! deviation from the plan's literal "empty rule source" text that
//! `production_conformance.rs:75-94` and `decomposition_conformance.rs`'s
//! own Step 1 note already record: `run_once_into`'s own `split_content`
//! refuses a content set with zero `(rule …)` top-forms outright, so a truly
//! empty source cannot reach the anchor check at all; this test uses one
//! minimal, never-firing probe rule instead (only ONE new system this train
//! registers, unlike the Decomposition+ControlRatio train's two).
//!
//! # THE SPIKE (Step 5) — verdict
//!
//! Two throwaway spike rules were run through the real `run_once_into`
//! driver, then deleted (their bodies never landed in this file or in
//! `content/rules/`):
//!
//! - **Spike 1** (against `SCENARIO`, this file's own primary world) proved
//!   shapes (a)-(e) and (g) in one rule anchored on `social-class/active`
//!   (subject type `SOCIAL_CLASS`, inferred from the first `:field`
//!   binding's namespace, `tick.rs::subject_type_of`):
//!   - **(a)** `(for-each (neighbors self EdgeType/EXPLOITATION :out
//!     NodeType/SOCIAL_CLASS) …)` fired for `periphery-worker` (the sole
//!     EXPLOITATION source) and iterated zero times for the other four
//!     classes (D127 hash-neutral) — LOADED AND EVALUATED CLEAN.
//!   - **(b)** `(update-edge (edge-between EdgeType/EXPLOITATION self it)
//!     exploitation/value-flow (set 1))` wrote the `.bscn`-seeded
//!     `exploitation/value-flow` edge attribute — post-tick read back `1.0`.
//!   - **(c)** the same body issued BOTH `(update-node self
//!     social-class/production-value (add 1))` and `(update-node it
//!     social-class/production-value (add 1))` — both writes observed
//!     applying (confirmed by the final aggregate values below, which
//!     include their contribution).
//!   - **(d)** a nested `(guard (= (field-of it social-class/role)
//!     SocialRole/CORE_BOURGEOISIE) (emit …) (update-node it … (add 10))
//!     (update-node it … (add 10)))` — THREE effects — loaded and ran, all
//!     three firing together (the guard's predicate held for
//!     `core-bourgeoisie`, the sole EXPLOITATION target; exactly one
//!     `SURPLUS_EXTRACTION` event observed).
//!   - **(e)** the `(field-of it social-class/role)` enum-ref equality
//!     inside that guard typechecked and evaluated correctly.
//!   - **(g)** a second `for-each` over `(nodes NodeType/SOCIAL_CLASS)` (5
//!     elements) issued a repeated, `it`-independent `(update-node self
//!     social-class/production-value (set 42))` alongside a repeated
//!     `(update-node self social-class/wealth (add 1))`. Measured post-tick
//!     values (`run_once_into`, this exact rule + `SCENARIO`, 2026-08-18):
//!     `periphery-worker`/`comprador`/`labor-aristocracy`/`petty-b` all read
//!     `production-value=42.0` (the repeated `set` accepted, never refused,
//!     last write wins — all five were identical so "last" is
//!     unobservable by value alone, but no collision error occurred) and
//!     `wealth=seed+5.0` (`805.0`/`305.0`/`255.0` — the `add` DID
//!     accumulate across all 5 iterations, unlike `set`).
//!     `core-bourgeoisie` (subject-order FIRST, `tick.rs`'s "subject order
//!     outer, source order inner") reads `production-value=53.0` — its OWN
//!     `for-each (nodes …)` batch (5x `set 42`) applied FIRST (it is the
//!     lowest-id subject), THEN `periphery-worker`'s LATER `it`-targeted
//!     `(add 1)` and the guard's `(add 10)` applied ON TOP of the
//!     already-42 value (`42 + 1 + 10 = 53`) — the cross-subject
//!     accumulation-onto-a-prior-set the dossier's `structural_verbs.rs`
//!     reading predicted, now observed for real. `core-bourgeoisie`'s
//!     `wealth=10015.0` (`10000 + 10` [guard] `+ 5` [own for-each's 5x
//!     `add 1`]) confirms the same batch, no contribution lost. Exactly
//!     Task 0 Step 4(e)'s static reading, now proven against the real
//!     driver, with no surprise.
//! - **Spike 2** (against a small inline two-INSTITUTION-node fixture, NOT
//!   `SCENARIO` — this scenario mints exactly one INSTITUTION node by
//!   design) proved **(f)**: `(select-max (nodes NodeType/INSTITUTION)
//!   (field-of it institution/rent-carrier))` resolved the real carrier
//!   (`rent-carrier 1`) over a LOWER-id decoy (`rent-carrier 0`) — proving
//!   the discriminator, not ascending-id tiebreak, decides the winner. This
//!   shape is kept as the PERMANENT
//!   `carrier_discriminator_resolves_over_a_lower_id_decoy` test below
//!   (Step 6), not deleted with the rest of the spike.
//!
//! **No shape refused.** Task 2 onward may rely on all seven directly,
//! exactly as the plan's §3.1/§8 disposition specifies.
//!
//! # THE THREE FIRSTS (Step 6) — fix round 1, reviewer Important 2
//!
//! Pinned here, by name, per the brief's own Step 6 instruction (the
//! per-test doc on `carrier_discriminator_resolves_over_a_lower_id_decoy`
//! below states the THIRD of these in its own words; this is the one place
//! all three are named together):
//!
//! 1. **This is the first BSL content — of any kind, throwaway spike or
//!    landed pack — to use `update-edge`.** Spike 1 (item (b) above) is the
//!    first-ever content-adjacent `update-edge` invocation in this repo's
//!    history; the landed `content/rules/*.bsl` estate uses only
//!    `update-node` before this train. (`update-edge` itself landed in the
//!    language at T3/ADR198 — this is its first CONTENT-side use.)
//! 2. **`wages/value-flow`'s first WRITE is deferred to Task 5's `r06` —
//!    NOT claimed here.** This pack's own edges seed `wages/value-flow`
//!    (`.bscn`'s `edge-attr`, a landed idiom since `consciousness.bsl`'s
//!    `p2-wages-push` reader), but Task 1 writes only `exploitation/
//!    value-flow` (Spike 1, item (b)) — a brand-new namespace, not the
//!    reused `wages/*` one. No content pack writes `wages/value-flow` as of
//!    this commit.
//! 3. **This is the first carrier resolved by a declared discriminator
//!    (`institution/rent-carrier`) rather than a constant score.** Every
//!    landed carrier read before this train (`decomposition.bsl`'s 14
//!    `(select-max (nodes NodeType/INSTITUTION) 1)` sites) uses a CONSTANT
//!    score — D45's ascending-id tiebreak decides the winner by construction
//!    whenever more than one INSTITUTION node exists. THIS pack is the
//!    first to score by a per-node FIELD instead
//!    (`carrier_discriminator_resolves_over_a_lower_id_decoy` proves the
//!    two selection strategies diverge on a real fixture, not merely that
//!    the new syntax loads).
//!
//! # Frozen-mirror provenance
//!
//! Every state value below was printed by the frozen `ImperialRentSystem`
//! (@9.0), one tick of its five phases (`step()`'s own body, replicated
//! call-for-call — see the mirror's own fix-round-1 comment — so the
//! pre-quantization pool value is observable), over a fixture that mirrors
//! `imperial-rent-conformance.bscn` node for node and edge for edge — §9's
//! canonical mirror recipe (all three graph attributes seeded explicitly,
//! `persistent_data` left `{}`, no boundary register bound).
//!
//! **Header fact (d), fix round 1 (reviewer Important 1): the printed
//! `economy` graph attribute is QUANTIZED; BSL's own arithmetic is not.**
//! `GlobalEconomy`'s three fields each carry Pydantic's `SnapToGrid`
//! validator (`models/types.py:26-30,41-44`; `kernel/math.py:41-56`,
//! ROUND_HALF_UP to 6 decimals), and `_save_economy` (`economic.py:831-836`)
//! constructs a `GlobalEconomy(...)` on every save — a frozen-Python-ONLY
//! artifact with no BSL counterpart. The mirror below therefore prints BOTH
//! the quantized `economy` dict (what the frozen engine actually stores)
//! AND a separate RAW, pre-quantization `imperial_rent_pool` line, measured
//! (not hand-derived) from the same `tick_context` dict `_save_economy`
//! itself reads. **The RAW line, not the quantized dict's
//! `imperial_rent_pool`, is the correct oracle for a future `r09-pool-
//! decay` BSL comparison** — BSL has no Currency-quantization step, so its
//! own raw binary64 output will match the RAW print exactly and differ from
//! the quantized one by ~1.28e-7 in this world. Node `wealth`/
//! `effective_wealth`/etc. and edge `value_flow` are never quantized
//! (`graph.update_node`/`update_edge` write raw dict attributes, no
//! Pydantic validation on that path) — visible directly in the stdout below
//! as six-decimal `economy` values beside 15-digit `wealth` values.
//!
//! ```text
//! PYTHONPATH="$PWD/src" UV_FROZEN=1 uv run python \
//!     rust/crates/babylon-tick/content/scenarios/imperial_rent_conformance.py
//! ```
//!
//! Its output on 2026-08-18, verbatim:
//!
//! ```text
//! defines (src/babylon/data/defines.yaml, economy: section):
//!   economy.extraction_efficiency = 0.8
//!   economy.comprador_cut = 0.9
//!   economy.super_wage_rate = 0.2
//!   economy.superwage_multiplier = 1.0
//!   economy.superwage_ppp_impact = 0.5
//!   economy.initial_rent_pool = 100.0
//!   economy.pool_high_threshold = 0.7
//!   economy.pool_low_threshold = 0.3
//!   economy.pool_critical_threshold = 0.1
//!   economy.min_wage_rate = 0.05
//!   economy.max_wage_rate = 0.35
//!   economy.negligible_rent = 0.01
//!   economy.trpf_coefficient = 0.0005
//!   economy.rent_pool_decay = 0.002
//!   economy.bribery_wage_delta = 0.05
//!   economy.austerity_wage_delta = -0.05
//!   economy.iron_fist_repression_delta = 0.1
//!   economy.crisis_wage_delta = -0.15
//!   economy.crisis_repression_delta = 0.2
//!   economy.bribery_tension_threshold = 0.7
//!   economy.iron_fist_tension_threshold = 0.5
//!   economy.trpf_efficiency_floor = 0.1
//!   timescale.weeks_per_year = 52
//!
//! context.persistent_data (pre-tick) = {}
//! services.boundary_register = None
//!
//! post-tick social classes:
//!   core-bourgeoisie   wealth=10045.819420118343 effective_wealth=None unearned_increment=None ppp_multiplier=None w_paid=None v_produced=None
//!   periphery-worker   wealth=493.84923076923076 effective_wealth=None unearned_increment=None ppp_multiplier=None w_paid=None v_produced=None
//!   comprador          wealth=720.0 effective_wealth=None unearned_increment=None ppp_multiplier=None w_paid=None v_produced=None
//!   labor-aristocracy  wealth=340.33134911242604 effective_wealth=356.46388875739643 unearned_increment=16.13253964497041 ppp_multiplier=1.4 w_paid=40.33134911242603 v_produced=40.0
//!   petty-b            wealth=250.0 effective_wealth=None unearned_increment=None ppp_multiplier=None w_paid=None v_produced=None
//!
//! post-tick edges (value_flow):
//!   exploitation periphery-worker -> core-bourgeoisie: value_flow=6.150769230769232
//!   tribute comprador -> core-bourgeoisie: value_flow=80.0
//!   wages core-bourgeoisie -> labor-aristocracy: value_flow=40.33134911242603
//!
//! post-tick context.persistent_data = {}
//!
//! post-tick economy (ALREADY DECAYED, see header (b)) = {'imperial_rent_pool': 185.447781, 'current_super_wage_rate': 0.25, 'current_repression_level': 0.5}
//! post-tick economy.imperial_rent_pool RAW (pre-quantization, see header (d); THE ORACLE FOR BSL's r09) = 185.4477812781065
//!
//! events:
//!   surplus_extraction {'source_id': 'periphery-worker', 'target_id': 'core-bourgeoisie', 'amount': 6.150769230769232, 'mechanism': 'imperial_rent'}
//! ```
//!
//! `petty-b` (the non-participant witness — no edge touches it) is
//! untouched: `wealth=250.0` (its seed, unchanged) and every wages-only
//! field stays `None`. `comprador`'s `wealth=720.0` is the frozen §1.6-c
//! OVERWRITE (`source.wealth = cut_amount`, `800 * 0.9 = 720`), not an
//! additive mutation — the exact shape `r03` (Task 3) transcribes.
//!
//! # Why exact equality and no tolerance
//!
//! `Int * Real` and correctly-rounded binary64 arithmetic are the only
//! operations either engine performs to reach the numbers above — **with
//! ONE named exception, fix round 1 (Important 1): the quantized
//! `imperial_rent_pool`/`current_super_wage_rate`/`current_repression_level`
//! fields inside the printed `economy` dict**, which additionally pass
//! through Pydantic's `SnapToGrid` (ROUND_HALF_UP, 6 decimals) on their way
//! out of `_save_economy` — a frozen-Python-only step, header fact (d). For
//! every OTHER number above (every node field, every edge `value_flow`),
//! `bsl-language.rst` §4.3's claim holds without qualification, so later
//! tasks' Rust-side pins may assert exact equality against BSL-measured
//! values, not against these printed floats (ADR183: this mirror is a
//! structure/ordering oracle, not a byte oracle; no `imperial-rent/*` rule
//! exists yet in Task 1 to measure BSL-side numbers from). For the pool
//! specifically, compare against the mirror's separate RAW print, not the
//! quantized dict entry.

use babylon_bsl::scenario::load_scenario;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::substrate::{GraphSubstrate, NodeId};
use babylon_tick::run_once_into;

const SCENARIO: &str = include_str!("../content/scenarios/imperial-rent-conformance.bscn");

// Node ids, fixed by the scenario's own declaration order (the scenario's
// own header names the same map; `decomposition_conformance.rs`/
// `territory_conformance.rs` precedent) — asserted, not merely declared,
// by `the_scenario_loads_clean_with_the_declared_census` below (fix round
// 1, reviewer Minor 7).
const CORE_BOURGEOISIE: NodeId = NodeId(0);
const PERIPHERY_WORKER: NodeId = NodeId(1);
const COMPRADOR: NodeId = NodeId(2);
const LABOR_ARISTOCRACY: NodeId = NodeId(3);
const PETTY_B: NodeId = NodeId(4);
const IMPERIAL_RENT_REGISTER: NodeId = NodeId(5);

/// The load-smoke test, through the REAL `run_once_into` seam — proves the
/// scenario loads clean against the newly-registered `"imperial-rent"`
/// system. See the module doc's Step 1 red-phase note for the pre-
/// registration failure text this test produced before `lib.rs`'s
/// `HashSet` carried `"imperial-rent"`.
#[test]
fn scenario_and_empty_pack_load() {
    const PROBE_RULE: &str = r#"
(rule imperial-rent/probe
  :material-basis "load-only smoke: prove the scenario loads against a registered imperial-rent system"
  :fuel 8
  (bindings (binding wealth :field social-class/wealth))
  (when (< wealth 0))
  (effects
    (update-node self social-class/wealth (set wealth))))
"#;
    let mut graph = HypergraphStore::new();
    let mut sink = CollectingSink::default();
    run_once_into(SCENARIO, PROBE_RULE, &mut graph, &mut sink)
        .expect("the scenario must load and run against the registered-system probe rule");
}

/// The scenario's own node/edge census, independent of any rule pack — five
/// `SOCIAL_CLASS` fixtures plus the one `INSTITUTION` carrier, three edges
/// (EXPLOITATION, TRIBUTE, WAGES).
#[test]
fn the_scenario_loads_clean_with_the_declared_census() {
    let mut graph = HypergraphStore::new();
    let loaded = load_scenario(SCENARIO, &mut graph).expect("the scenario must load clean");
    assert_eq!(loaded.node_count, 6, "5 social classes + 1 carrier");
    assert_eq!(
        loaded.edge_count, 3,
        "EXPLOITATION + TRIBUTE + WAGES, one each"
    );
    assert_eq!(
        loaded.node_types.get("SOCIAL_CLASS").copied(),
        Some(5),
        "five social-class nodes"
    );
    assert_eq!(
        loaded.node_types.get("INSTITUTION").copied(),
        Some(1),
        "exactly one carrier in THIS world — the D198 discriminator vector \
         below builds its own second-INSTITUTION-node fixture separately"
    );

    // Fix round 1 (reviewer Minor 7): the six top-level `NodeId` constants
    // are asserted here, not merely declared — Tasks 2-8 key every
    // assertion off this exact map, and the one id most likely to surprise
    // a later reader is `IMPERIAL_RENT_REGISTER = NodeId(5)` (that the
    // INSTITUTION node continues the SAME ascending counter after the five
    // SOCIAL_CLASS nodes, rather than starting its own).
    for id in [
        CORE_BOURGEOISIE,
        PERIPHERY_WORKER,
        COMPRADOR,
        LABOR_ARISTOCRACY,
        PETTY_B,
        IMPERIAL_RENT_REGISTER,
    ] {
        assert!(
            graph.node_exists(id),
            "{id:?} must exist — the scenario's declaration order fixes \
             this map"
        );
    }
    assert_eq!(
        graph
            .node_attribute(CORE_BOURGEOISIE, "social-class/role")
            .expect("core-bourgeoisie has a role"),
        0.0, // CORE_BOURGEOISIE is ordinal 0, ADR195
        "NodeId(0) is core-bourgeoisie, not merely SOME social-class node"
    );
    assert_eq!(
        graph
            .node_attribute(IMPERIAL_RENT_REGISTER, "institution/rent-carrier")
            .expect("imperial-rent-register has rent-carrier"),
        1.0,
        "NodeId(5) is imperial-rent-register (rent-carrier == 1) — the \
         claim every later task's carrier read keys off"
    );
}

/// The `defenum` ordinal-parity test (Global Constraints: "`defenum` is not
/// shared across scenarios… the suite carries one ordinal-parity test
/// mirroring the mint's"), mirroring
/// `decomposition_conformance.rs::social_role_order_is_the_ruled_ordinal` —
/// THIS scenario's own `SocialRole` re-declaration must store the SAME
/// eight members in the SAME order as
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

/// THE SPIKE's item (f), kept PERMANENT (Step 6) rather than deleted with
/// the rest of the spike: `institution/rent-carrier` FIELD-GUARDED
/// resolution (D198, plan §3.1) over a naive ascending-id `select-max`
/// tiebreak. This is its own small inline fixture — `SCENARIO` above mints
/// exactly one INSTITUTION node by design (§3.1: "with exactly one
/// INSTITUTION node the constant score and the discriminator score agree
/// by construction"), so this is the world that actually exercises the
/// discriminator's REASON to exist: `decoy-carrier` is declared FIRST
/// (lower NodeId) with `rent-carrier 0`, `real-carrier` SECOND (higher
/// NodeId) with `rent-carrier 1` — a naive constant-score `select-max`
/// (D45's ascending-id-first-wins) would resolve `decoy-carrier`; the
/// discriminator score must resolve `real-carrier` instead.
#[test]
fn carrier_discriminator_resolves_over_a_lower_id_decoy() {
    const TWO_INSTITUTION_SCENARIO: &str = r#"
(scenario imperial-rent/carrier-discriminator-probe
  (defvocabulary NodeType (INSTITUTION))
  (deffield institution/rent-carrier int extensive)
  (deffield institution/rent-pool real extensive)

  (node decoy-carrier NodeType/INSTITUTION
    (institution/rent-carrier 0)
    (institution/rent-pool 0))

  (node real-carrier NodeType/INSTITUTION
    (institution/rent-carrier 1)
    (institution/rent-pool 0)))
"#;
    const DISCRIMINATOR_RULE: &str = r#"
(rule imperial-rent/discriminator-probe
  :material-basis "THE SPIKE item (f): the field-guarded select-max discriminator over a lower-id decoy INSTITUTION node (D198, plan §3.1)"
  :fuel 64
  (bindings (binding carrier :field institution/rent-carrier))
  (when (>= carrier 0))
  (effects
    (update-node
      (select-max (nodes NodeType/INSTITUTION) (field-of it institution/rent-carrier))
      institution/rent-pool
      (set 999))))
"#;
    const DECOY: NodeId = NodeId(0);
    const REAL_CARRIER: NodeId = NodeId(1);

    let mut graph = HypergraphStore::new();
    let mut sink = CollectingSink::default();
    run_once_into(
        TWO_INSTITUTION_SCENARIO,
        DISCRIMINATOR_RULE,
        &mut graph,
        &mut sink,
    )
    .expect("the two-INSTITUTION-node fixture must load and run clean");

    assert_eq!(
        graph
            .node_attribute(REAL_CARRIER, "institution/rent-pool")
            .expect("real-carrier has rent-pool"),
        999.0,
        "the discriminator resolves real-carrier (rent-carrier 1), the \
         higher-id node — NOT the lower-id decoy"
    );
    assert_eq!(
        graph
            .node_attribute(DECOY, "institution/rent-pool")
            .expect("decoy-carrier has rent-pool"),
        0.0,
        "the lower-id decoy (rent-carrier 0) is untouched — a naive \
         ascending-id constant-score select-max would have written HERE \
         instead, which is exactly the D198 hazard this discriminator \
         closes"
    );
}
