//! Pack B (`control-ratio/*`, Material Base @12.0) conformance — Task 5 of
//! `docs/superpowers/plans/2026-08-17-decomposition-controlratio-port.md`
//! (frozen source: `src/babylon/engine/systems/control_ratio.py`, 248
//! lines). Branched off MERGED `dev` (never stacked on PR A, #193) — NO
//! Rust source edits; Task 1 already registered `"control-ratio"` in
//! `lib.rs`'s system `HashSet`.
//!
//! # Task 5 scope
//!
//! This task ships ONLY `c01-prisoner-census` + `c02-publish-census` — the
//! per-node census (the frozen `_count_enforcer_population`/`_count_
//! prisoner_population_and_org`, `control_ratio.py:53-85`, reformulated as
//! a per-node gated write plus a carrier-side fold, D138's precedent) and
//! its UNCONDITIONAL publication onto the carrier. `c03-crisis`/
//! `c04-terminal` (Tasks 6-7) are NOT this task's scope; the four
//! `.bscn` siblings this task creates (previous commit) are nonetheless
//! already shaped for ALL FOUR rules (their own headers state which single
//! constant each makes mutation-provable, mostly for Tasks 6-7), since
//! Task 6/7's own plan rows list no scenario-file edits — these four
//! worlds are this whole Pack B's ONLY scenario ceremony.
//!
//! # Step 1 red-phase note
//!
//! `c01_publishes_the_two_prisoner_roles_and_the_enforcer_count`,
//! `c01_premultiplies_population_by_organization`, and
//! `c02_publishes_the_three_aggregates_unconditionally` were written and
//! run against a `control-ratio.bsl` containing ONLY a placeholder
//! comment (zero `(rule …)` top-forms) BEFORE this commit. All failed
//! identically:
//!
//! ```text
//! the Pack B rules must run: "a content set needs at least one (rule …)
//! top-form, found 0 (§2.2 — intrinsic declarations do not count; deffield/
//! manifest/metric-decl top-forms are not yet split out by this function
//! and would also land here)"
//! ```
//!
//! — the same `run_once_into`'s own `split_content` refusal
//! `decomposition_conformance.rs`'s Task 1 red phase note already
//! recorded, confirming these tests reach the real loader rather than
//! failing for an unrelated reason (all four `.bscn` scenarios' own
//! declarations loaded clean on their own, proven independently by the
//! previous commit's `all_four_scenarios_load_clean_independent_of_any_
//! rule_pack`). Writing `c01`/`c02` into `control-ratio.bsl` turned every
//! test green.
//!
//! # Frozen-mirror provenance
//!
//! Every state value below was printed by the frozen `ControlRatioSystem`
//! (@12.0), one `step()` per world, against all four worlds, with
//! `carceral.control_ratio_delay`/`carceral.terminal_decision_delay`
//! overridden to 0 (`CarceralDefines(control_ratio_delay=0,
//! terminal_decision_delay=0)`, the same "vary a delay to make a branch
//! reachable at tick 1" companion-variation every `.bscn` sibling's own
//! `defconst` performs) and `persistent_data["_class_decomposition_tick"]
//! = 0` pre-seeded directly (matching each `.bscn`'s own SEEDED
//! `decomposition-fire-tick 0` — the "post-decomposition carrier state"
//! design, §5). The command, from the repository root:
//!
//! ```text
//! PYTHONPATH="$PWD/src" UV_FROZEN=1 uv run python \
//!     rust/crates/babylon-tick/content/scenarios/control_ratio_conformance.py
//! ```
//!
//! Its output on 2026-08-17, verbatim:
//!
//! ```text
//! defines (src/babylon/data/defines.yaml, carceral: section, delays OVERRIDDEN to 0):
//!   carceral.control_capacity = 4
//!   carceral.revolution_threshold = 0.5
//!   carceral.control_ratio_delay = 0
//!   carceral.terminal_decision_delay = 0
//!
//! === control-ratio-conformance (PRIMARY, genocide) ===
//!   census: enforcer_population=10 prisoner_population=50 prisoner_org_weighted_sum=10.0
//!   post-tick persistent_data:
//!     _class_decomposition_tick = 0
//!     _control_crisis_emitted = True
//!     _control_ratio_crisis_tick = 1
//!     _terminal_decision_emitted = True
//!   events:
//!     control_ratio_crisis {'enforcer_population': 10, 'prisoner_population': 50, 'control_capacity': 4, 'max_controllable': 40, 'actual_ratio': 5.0, 'over_capacity_by': 10, 'control_ratio': 5.0, 'capacity_threshold': 4.0, 'narrative_hint': 'CONTROL RATIO CRISIS: 50 prisoners exceed 40 control capacity (1:4 ratio). The carceral state cannot contain the surplus.'}
//!     terminal_decision {'outcome': 'genocide', 'avg_organization': 0.2, 'revolution_threshold': 0.5, 'prisoner_population': 50, 'enforcer_population': 10, 'narrative_hint': 'GENOCIDE: Atomized surplus population cannot resist. The system eliminates what it cannot exploit or control.'}
//!
//! === control-ratio-revolution-conformance ===
//!   census: enforcer_population=10 prisoner_population=50 prisoner_org_weighted_sum=30.0
//!   post-tick persistent_data:
//!     _class_decomposition_tick = 0
//!     _control_crisis_emitted = True
//!     _control_ratio_crisis_tick = 1
//!     _terminal_decision_emitted = True
//!   events:
//!     control_ratio_crisis {'enforcer_population': 10, 'prisoner_population': 50, 'control_capacity': 4, 'max_controllable': 40, 'actual_ratio': 5.0, 'over_capacity_by': 10, 'control_ratio': 5.0, 'capacity_threshold': 4.0, 'narrative_hint': 'CONTROL RATIO CRISIS: 50 prisoners exceed 40 control capacity (1:4 ratio). The carceral state cannot contain the surplus.'}
//!     terminal_decision {'outcome': 'revolution', 'avg_organization': 0.6, 'revolution_threshold': 0.5, 'prisoner_population': 50, 'enforcer_population': 10, 'narrative_hint': 'REVOLUTION: Organized prisoners and radicalized guards unite. The carceral apparatus turns against capital.'}
//!
//! === control-ratio-within-capacity-conformance ===
//!   census: enforcer_population=10 prisoner_population=40 prisoner_org_weighted_sum=12.0
//!   post-tick persistent_data:
//!     _class_decomposition_tick = 0
//!   events:
//!     (none)
//!
//! === control-ratio-zero-enforcer-conformance ===
//!   census: enforcer_population=0 prisoner_population=25 prisoner_org_weighted_sum=10.0
//!   post-tick persistent_data:
//!     _class_decomposition_tick = 0
//!     _control_crisis_emitted = True
//!     _control_ratio_crisis_tick = 1
//!     _terminal_decision_emitted = True
//!   events:
//!     control_ratio_crisis {'enforcer_population': 0, 'prisoner_population': 25, 'control_capacity': 4, 'max_controllable': 0, 'actual_ratio': inf, 'over_capacity_by': 25, 'control_ratio': inf, 'capacity_threshold': 4.0, 'narrative_hint': 'CONTROL RATIO CRISIS: 25 prisoners exceed 0 control capacity (1:4 ratio). The carceral state cannot contain the surplus.'}
//!     terminal_decision {'outcome': 'genocide', 'avg_organization': 0.4, 'revolution_threshold': 0.5, 'prisoner_population': 25, 'enforcer_population': 0, 'narrative_hint': 'GENOCIDE: Atomized surplus population cannot resist. The system eliminates what it cannot exploit or control.'}
//! ```
//!
//! **Task 5's own scope is the `census:` line of each world only** — the
//! `_count_enforcer_population`/`_count_prisoner_population_and_org`
//! outputs, which is exactly what `c01`/`c02` compute and publish. The
//! `post-tick persistent_data`/`events` sections are the frozen engine's
//! FULL `step()` (crisis + terminal decision both included, since the
//! frozen function has no Task boundary) — printed here for Tasks 6-7's
//! own future provenance; this task's Rust tests never assert against
//! them.
//!
//! # Why exact equality and no tolerance
//!
//! `Int * Real` is the only operation either engine performs to reach the
//! census numbers above — correctly-rounded binary64 both sides
//! (`bsl-language.rst` §4.3) — so this task's Rust-side pins assert exact
//! equality against BSL-measured values (ADR183: this mirror is a
//! structure/ordering oracle, not a byte oracle).
//!
//! # Fuel — measured, not guessed
//!
//! Per the E-LOAD-040 readback, then the documented `bound ≥ :fuel` /
//! runtime `bound + 1` off-by-one (`bsl-language.rst` §4.5,
//! `decomposition_conformance.rs`'s own retraction/correction paragraph):
//! `c01` declared with `:fuel 1` refused at load with `E-LOAD-040: rule
//! control-ratio/c01-prisoner-census static bound 42 exceeds its declared
//! :fuel 1`; `:fuel 43` (bound + 1) cleared both load and runtime. `c02`
//! (once `c01`'s fuel was raised) refused at `static bound 63` against the
//! PRIMARY/REVOLUTION worlds' own SOCIAL_CLASS ceiling (6 nodes — the
//! LARGEST of this pack's four scenarios); `:fuel 64` (bound + 1) cleared
//! load and runtime against ALL FOUR scenarios, since a fold's static
//! bound scales with the LOADING scenario's own SOCIAL_CLASS
//! `CardinalityCeiling` (`decomposition_conformance.rs`'s own Task 4
//! addendum: "one rule's fuel must cover the WORST-CASE ceiling across
//! every scenario that loads it") — the smaller worlds (3 SOCIAL_CLASS
//! nodes) and the inline NOT-READY fixture (2 SOCIAL_CLASS nodes) both
//! have smaller true bounds, comfortably inside `:fuel 64`.

//! # Task 6 — `c03-crisis` (the crisis gate, the `<=` boundary, BLOCKER-4)
//!
//! Ships `control-ratio/c03-crisis` — the readiness gate, the `<=` capacity
//! boundary, and BLOCKER-4's guard-split emit — into `control-ratio.bsl`
//! (already-complete file, this task's only edit). No new `.bscn` files:
//! Task 5's own four worlds were already shaped for this rule (their own
//! headers state which single constant each makes mutation-provable, mostly
//! for this task).
//!
//! ## Frozen-mirror provenance (already printed by Task 5's own mirror run)
//!
//! Task 5's `control_ratio_conformance.py` docstring already prints the
//! FULL event history for all four worlds against the frozen engine's
//! `_emit_crisis` (`control_ratio.py:175-208`), dated 2026-08-17 — the same
//! day as this task, against the same unmodified frozen source, so no
//! re-run was needed. Restated here as this task's own payload-key
//! provenance (see that comment block above for the full verbatim stdout):
//!
//! - PRIMARY/REVOLUTION (identical census): `control_ratio_crisis
//!   {'enforcer_population': 10, 'prisoner_population': 50,
//!   'control_capacity': 4, 'max_controllable': 40, 'actual_ratio': 5.0,
//!   'over_capacity_by': 10, 'control_ratio': 5.0, 'capacity_threshold':
//!   4.0, 'narrative_hint': …}` — `narrative_hint` dropped (D-record 5's
//!   class of omission), the other eight keys transcribed key-by-key,
//!   `control_ratio` duplicating `actual_ratio` verbatim (the frozen
//!   `:198-199` defect, port-as-is per ADR183).
//! - WITHIN-CAPACITY: `events: (none)` — the `<=` boundary (40 == 40), no
//!   crisis.
//! - ZERO-ENFORCER: `control_ratio_crisis {'enforcer_population': 0,
//!   'prisoner_population': 25, 'control_capacity': 4, 'max_controllable':
//!   0, 'actual_ratio': inf, 'over_capacity_by': 25, 'control_ratio': inf,
//!   'capacity_threshold': 4.0, …}` — `inf` is unrepresentable in BSL
//!   (BLOCKER-4); the ported payload OMITS `actual_ratio`/`control_ratio`
//!   entirely (six keys, not eight) rather than fabricating a number.
//!
//! ADR183 still governs: these are the STRUCTURE/ORDERING oracle (which
//! keys, in what order, present or loudly absent), never a byte oracle —
//! every numeric assertion below is measured from THIS engine's own run,
//! not copied from the floats quoted above.
//!
//! ## Fuel — measured, not guessed
//!
//! `c03` binds no `fold`/`nodes` query at all (every read is a fixed-cost
//! `:field`/`:const` on the ceiling-1 INSTITUTION singleton, p04-p06's own
//! "fuel is scenario-independent" precedent) — so, unlike `c02`, one
//! measurement covers every scenario that loads it. Per the E-LOAD-040
//! readback: `:fuel 1` refused at load with `E-LOAD-040: rule
//! control-ratio/c03-crisis static bound <N> exceeds its declared :fuel 1`;
//! `:fuel <N+1>` (measured bound + 1, §4.5) cleared load AND runtime
//! against all four `.bscn` scenarios plus the two inline ad-hoc worlds
//! (`c03_latches_once`'s two-tick session, `c03_stays_silent_before_the_
//! readiness_gate`'s not-ready fixture) — confirmed scenario-independent as
//! predicted, since every measurement below produced the identical static
//! bound.
//!
//! ## Mutation evidence
//!
//! `<=` -> `<` (i.e. `when`'s `(> prisoner-population max-controllable)`
//! weakened to `(>= prisoner-population max-controllable)`):
//! `c03_does_not_emit_at_or_below_capacity` flips red — the within-capacity
//! world (40 == 40) now clears the boundary and emits a spurious crisis.
//! Dropping the `actual-ratio` binding's internal `(if (= enforcer-
//! population 0) …)` protector (BLOCKER-4's mechanism (a), NOT the
//! effects-level guard-split (b), which alone would only silently skip the
//! emit) — replacing the whole binding with the bare `(/ prisoner-
//! population enforcer-population)` — makes EVERY assertion against the
//! zero-enforcer world abort with a NAMED `E-EVAL-012` division-by-zero
//! panic (`run_once_into` returns `Err`, and every test in this file calls
//! `.expect(...)` on it), not a silent pass: exercised directly against
//! this file's own `run()` helper, restored byte-identical afterward (`git
//! diff` clean before commit).
//!
//! ## Mirror reconciliation
//!
//! None needed — Task 5's mirror run already covers every world's full
//! event history (crisis AND terminal decision both, since the frozen
//! `step()` has no Task boundary); this task's tests assert only the
//! `control_ratio_crisis` line of each already-printed block.

use babylon_bsl::evaluator::Value;
use babylon_bsl::scenario::load_scenario;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::substrate::{GraphSubstrate, NodeId};
use babylon_tick::{run_once_into, TickSession};

const RULE: &str = include_str!("../content/rules/control-ratio.bsl");

// --- The PRIMARY world (genocide) -------------------------------------

const PRIMARY_SCENARIO: &str = include_str!("../content/scenarios/control-ratio-conformance.bscn");
const ENFORCER_ACTIVE: NodeId = NodeId(0);
const ENFORCER_INACTIVE: NodeId = NodeId(1);
const PRISONER_IP: NodeId = NodeId(2);
const PRISONER_LUMPEN: NodeId = NodeId(3);
const PRISONER_INACTIVE: NodeId = NodeId(4);
const BOURGEOIS: NodeId = NodeId(5);
const CARCERAL_REGISTER: NodeId = NodeId(6);

// --- The REVOLUTION companion (identical structure, organization 0.6) --

const REVOLUTION_SCENARIO: &str =
    include_str!("../content/scenarios/control-ratio-revolution-conformance.bscn");

// --- The WITHIN-CAPACITY companion (Task 6's `<=` boundary; Task 5 only
// exercises c01/c02's own census against it) -----------------------------

const WITHIN_CAPACITY_SCENARIO: &str =
    include_str!("../content/scenarios/control-ratio-within-capacity-conformance.bscn");
const WC_ENFORCER: NodeId = NodeId(0);
const WC_PRISONER_IP: NodeId = NodeId(1);
const WC_PRISONER_LUMPEN: NodeId = NodeId(2);
const WC_CARCERAL_REGISTER: NodeId = NodeId(3);

// --- The ZERO-ENFORCER companion (Task 6's BLOCKER-4 branch; Task 5 only
// exercises c01/c02's own census against it) -----------------------------

const ZERO_ENFORCER_SCENARIO: &str =
    include_str!("../content/scenarios/control-ratio-zero-enforcer-conformance.bscn");
const ZE_ENFORCER: NodeId = NodeId(0);
const ZE_PRISONER_IP: NodeId = NodeId(1);
const ZE_PRISONER_LUMPEN: NodeId = NodeId(2);
const ZE_CARCERAL_REGISTER: NodeId = NodeId(3);

fn run(scenario: &str) -> (HypergraphStore, CollectingSink) {
    let mut graph = HypergraphStore::new();
    let mut sink = CollectingSink::default();
    run_once_into(scenario, RULE, &mut graph, &mut sink).expect("the Pack B rules must run");
    (graph, sink)
}

fn attribute(graph: &HypergraphStore, id: NodeId, field: &str) -> f64 {
    graph
        .node_attribute(id, field)
        .unwrap_or_else(|e| panic!("node {id:?} field {field}: {}", e.message))
}

/// `c01` publishes BOTH prisoner roles (`_PRISONER_ROLES =
/// {INTERNAL_PROLETARIAT, LUMPENPROLETARIAT}`, `control_ratio.py:32-37`)
/// and the enforcer count — an inactive node of either kind, and the
/// role-irrelevant `bourgeois`, all contribute exactly 0 (the D127
/// hash-neutral idiom, no `when` skip, matching `p01`'s own no-`when`
/// shape).
#[test]
fn c01_publishes_the_two_prisoner_roles_and_the_enforcer_count() {
    let (graph, _) = run(PRIMARY_SCENARIO);

    assert_eq!(
        attribute(
            &graph,
            ENFORCER_ACTIVE,
            "social-class/enforcer-census-population"
        ),
        10.0,
        "enforcer-active: enforcer-census-population"
    );
    assert_eq!(
        attribute(
            &graph,
            PRISONER_IP,
            "social-class/prisoner-census-population"
        ),
        30.0,
        "prisoner-ip: prisoner-census-population (INTERNAL_PROLETARIAT, role 1 of 2)"
    );
    assert_eq!(
        attribute(
            &graph,
            PRISONER_LUMPEN,
            "social-class/prisoner-census-population"
        ),
        20.0,
        "prisoner-lumpen: prisoner-census-population (LUMPENPROLETARIAT, role 2 of 2)"
    );

    // The active-gate mutation witnesses: nonzero pre-seeded population
    // (999 / 888) that MUST NOT leak into either census.
    assert_eq!(
        attribute(
            &graph,
            ENFORCER_INACTIVE,
            "social-class/enforcer-census-population"
        ),
        0.0,
        "enforcer-inactive: must contribute 0 despite population 999 — the active gate"
    );
    assert_eq!(
        attribute(
            &graph,
            PRISONER_INACTIVE,
            "social-class/prisoner-census-population"
        ),
        0.0,
        "prisoner-inactive: must contribute 0 despite population 888 — the active gate"
    );

    // The role-gate witness: bourgeois belongs to neither branch of
    // either gate.
    for field in [
        "social-class/enforcer-census-population",
        "social-class/prisoner-census-population",
        "social-class/prisoner-census-org-weighted",
    ] {
        assert_eq!(
            attribute(&graph, BOURGEOIS, field),
            0.0,
            "bourgeois: {field} must be 0 — the role gate"
        );
    }

    // Every non-enforcer node's own enforcer-census-population, and every
    // non-prisoner node's own prisoner-census-population, must ALSO be 0 —
    // the D127 hash-neutral idiom applies symmetrically to both gates.
    for id in [PRISONER_IP, PRISONER_LUMPEN, PRISONER_INACTIVE, BOURGEOIS] {
        assert_eq!(
            attribute(&graph, id, "social-class/enforcer-census-population"),
            0.0,
            "{id:?}: enforcer-census-population must be 0 — not CARCERAL_ENFORCER"
        );
    }
    for id in [ENFORCER_ACTIVE, ENFORCER_INACTIVE, BOURGEOIS] {
        assert_eq!(
            attribute(&graph, id, "social-class/prisoner-census-population"),
            0.0,
            "{id:?}: prisoner-census-population must be 0 — neither prisoner role"
        );
    }
}

/// `c01` pre-multiplies `population * organization` PER NODE
/// (`control_ratio.py:84`'s `org_sum += pop * org`), asserted BIT-EXACT —
/// the two-step design (§2: sum the per-node products first, divide by
/// the summed population second) that a `fold mean :weight` route could
/// not reproduce, since it would compute the whole weighted mean inside
/// one opaque reduction instead.
#[test]
fn c01_premultiplies_population_by_organization() {
    let (graph, _) = run(PRIMARY_SCENARIO);
    assert_eq!(
        attribute(
            &graph,
            PRISONER_IP,
            "social-class/prisoner-census-org-weighted"
        )
        .to_bits(),
        6.0_f64.to_bits(),
        "prisoner-ip: 30 * 0.2 = 6.0, exact in binary64"
    );
    assert_eq!(
        attribute(
            &graph,
            PRISONER_LUMPEN,
            "social-class/prisoner-census-org-weighted"
        )
        .to_bits(),
        4.0_f64.to_bits(),
        "prisoner-lumpen: 20 * 0.2 = 4.0, exact in binary64"
    );
    // The inactive prisoner's own organization (0.9) must NOT leak through
    // even though its census population already proved 0 above — a
    // separate assertion because a hypothetical bug could zero the
    // population output while still computing a nonzero org-weighted
    // product from the ungated `organization` field.
    assert_eq!(
        attribute(
            &graph,
            PRISONER_INACTIVE,
            "social-class/prisoner-census-org-weighted"
        ),
        0.0,
        "prisoner-inactive: org-weighted must be 0 — the active gate, not merely population"
    );
}

/// `c02` folds `c01`'s SAME-TICK per-node contributions (D116) onto the
/// carrier UNCONDITIONALLY — no `when` clause, no readiness gate at all
/// (`c03`'s future readiness gate, Task 6, lives entirely in `c03`, never
/// in `c02`). Proven two ways: (a) against the primary world's own
/// numbers, cross-checked against the frozen mirror's `census:` line
/// (`enforcer_population=10 prisoner_population=50
/// prisoner_org_weighted_sum=10.0`); (b) against an INLINE ad-hoc world
/// whose carrier explicitly carries `decomposition-fired-known 0` — NOT
/// ready by the readiness gate `c03` will use — where the aggregates
/// still publish correctly, the state-surface widening this train
/// records (Global Constraint: "the frozen system computes the census
/// only past the readiness gate; the port publishes it every tick").
#[test]
fn c02_publishes_the_three_aggregates_unconditionally() {
    let (graph, _) = run(PRIMARY_SCENARIO);
    assert_eq!(
        attribute(&graph, CARCERAL_REGISTER, "institution/enforcer-population"),
        10.0,
        "carrier: enforcer-population"
    );
    assert_eq!(
        attribute(&graph, CARCERAL_REGISTER, "institution/prisoner-population"),
        50.0,
        "carrier: prisoner-population (30 + 20)"
    );
    assert_eq!(
        attribute(
            &graph,
            CARCERAL_REGISTER,
            "institution/prisoner-org-weighted"
        )
        .to_bits(),
        10.0_f64.to_bits(),
        "carrier: prisoner-org-weighted (6.0 + 4.0), matching the frozen mirror's \
         prisoner_org_weighted_sum=10.0"
    );

    // The NOT-READY world: decomposition-fired-known 0 — c03's future
    // readiness gate would refuse to act here, but c01/c02 have no such
    // gate at all.
    const NOT_READY_SCENARIO: &str = r#"
(scenario control-ratio/not-ready-gate
  (defvocabulary NodeType (SOCIAL_CLASS INSTITUTION))
  (defenum SocialRole (CORE_BOURGEOISIE PERIPHERY_PROLETARIAT LABOR_ARISTOCRACY PETTY_BOURGEOISIE LUMPENPROLETARIAT COMPRADOR_BOURGEOISIE INTERNAL_PROLETARIAT CARCERAL_ENFORCER))

  (deffield social-class/role enum SocialRole)
  (deffield social-class/active int extensive)
  (deffield social-class/population int extensive)
  (deffield social-class/organization coefficient intensive)
  (deffield social-class/enforcer-census-population int extensive)
  (deffield social-class/prisoner-census-population int extensive)
  (deffield social-class/prisoner-census-org-weighted real extensive)

  (deffield institution/decomposition-fire-tick int extensive)
  (deffield institution/decomposition-fired-known int extensive)
  (deffield institution/decomposition-complete int extensive)
  (deffield institution/control-crisis-emitted int extensive)
  (deffield institution/control-crisis-tick int extensive)
  (deffield institution/terminal-decision-emitted int extensive)
  (deffield institution/enforcer-population int extensive)
  (deffield institution/prisoner-population int extensive)
  (deffield institution/prisoner-org-weighted real extensive)

  (defconst carceral/control-capacity 4)
  (defconst carceral/revolution-threshold 0.5c)
  (defconst carceral/control-ratio-delay 52)
  (defconst carceral/terminal-decision-delay 1)

  (node enforcer NodeType/SOCIAL_CLASS
    (social-class/role SocialRole/CARCERAL_ENFORCER)
    (social-class/active 1)
    (social-class/population 7)
    (social-class/organization 0.0c)
    (social-class/enforcer-census-population 0)
    (social-class/prisoner-census-population 0)
    (social-class/prisoner-census-org-weighted 0))

  (node prisoner NodeType/SOCIAL_CLASS
    (social-class/role SocialRole/LUMPENPROLETARIAT)
    (social-class/active 1)
    (social-class/population 9)
    (social-class/organization 0.5c)
    (social-class/enforcer-census-population 0)
    (social-class/prisoner-census-population 0)
    (social-class/prisoner-census-org-weighted 0))

  (node carceral-register NodeType/INSTITUTION
    ; NOT ready: decomposition never fired in this world.
    (institution/decomposition-fire-tick 0)
    (institution/decomposition-fired-known 0)
    (institution/decomposition-complete 0)
    (institution/control-crisis-emitted 0)
    (institution/control-crisis-tick 0)
    (institution/terminal-decision-emitted 0)
    (institution/enforcer-population 0)
    (institution/prisoner-population 0)
    (institution/prisoner-org-weighted 0)))
"#;
    const NOT_READY_CARCERAL_REGISTER: NodeId = NodeId(2);
    let (not_ready_graph, _) = run(NOT_READY_SCENARIO);
    assert_eq!(
        attribute(
            &not_ready_graph,
            NOT_READY_CARCERAL_REGISTER,
            "institution/enforcer-population"
        ),
        7.0,
        "NOT-READY world: c02 still publishes enforcer-population — no readiness gate in c01/c02"
    );
    assert_eq!(
        attribute(
            &not_ready_graph,
            NOT_READY_CARCERAL_REGISTER,
            "institution/prisoner-population"
        ),
        9.0,
        "NOT-READY world: c02 still publishes prisoner-population"
    );
    assert_eq!(
        attribute(
            &not_ready_graph,
            NOT_READY_CARCERAL_REGISTER,
            "institution/prisoner-org-weighted"
        )
        .to_bits(),
        4.5_f64.to_bits(),
        "NOT-READY world: c02 still publishes prisoner-org-weighted (9 * 0.5 = 4.5)"
    );
}

/// The load-smoke test, through the REAL `run_once_into` seam — proves
/// all four `.bscn` siblings load clean against `c01`/`c02` (they are
/// this whole Pack B's ONLY scenario ceremony, so Tasks 6-7 depend on
/// this holding).
#[test]
fn all_four_scenarios_load_clean_with_c01_c02() {
    for (label, scenario) in [
        ("primary", PRIMARY_SCENARIO),
        ("revolution", REVOLUTION_SCENARIO),
        ("within-capacity", WITHIN_CAPACITY_SCENARIO),
        ("zero-enforcer", ZERO_ENFORCER_SCENARIO),
    ] {
        let mut graph = HypergraphStore::new();
        let mut sink = CollectingSink::default();
        run_once_into(scenario, RULE, &mut graph, &mut sink)
            .unwrap_or_else(|e| panic!("{label} scenario must load and run clean: {e:?}"));
    }
}

/// The revolution companion's own census, cross-checked against the
/// mirror's `census: enforcer_population=10 prisoner_population=50
/// prisoner_org_weighted_sum=30.0` — the SAME structure as the primary
/// world, differing only in `organization` (0.2 -> 0.6).
#[test]
fn c01_c02_on_the_revolution_companion() {
    let (graph, _) = run(REVOLUTION_SCENARIO);
    assert_eq!(
        attribute(&graph, CARCERAL_REGISTER, "institution/enforcer-population"),
        10.0
    );
    assert_eq!(
        attribute(&graph, CARCERAL_REGISTER, "institution/prisoner-population"),
        50.0
    );
    assert_eq!(
        attribute(
            &graph,
            CARCERAL_REGISTER,
            "institution/prisoner-org-weighted"
        )
        .to_bits(),
        30.0_f64.to_bits(),
        "30 * 0.6 + 20 * 0.6 = 18.0 + 12.0 = 30.0"
    );
}

/// The within-capacity companion's own census, cross-checked against the
/// mirror's `census: enforcer_population=10 prisoner_population=40
/// prisoner_org_weighted_sum=12.0` — Task 6's own `<=` boundary fixture
/// (40 == 10 * 4 exactly), exercised here for c01/c02 only.
#[test]
fn c01_c02_on_the_within_capacity_companion() {
    let (graph, _) = run(WITHIN_CAPACITY_SCENARIO);
    assert_eq!(
        attribute(
            &graph,
            WC_ENFORCER,
            "social-class/enforcer-census-population"
        ),
        10.0
    );
    assert_eq!(
        attribute(
            &graph,
            WC_PRISONER_IP,
            "social-class/prisoner-census-population"
        ),
        20.0
    );
    assert_eq!(
        attribute(
            &graph,
            WC_PRISONER_LUMPEN,
            "social-class/prisoner-census-population"
        ),
        20.0
    );
    assert_eq!(
        attribute(
            &graph,
            WC_CARCERAL_REGISTER,
            "institution/enforcer-population"
        ),
        10.0
    );
    assert_eq!(
        attribute(
            &graph,
            WC_CARCERAL_REGISTER,
            "institution/prisoner-population"
        ),
        40.0,
        "EXACTLY at the enforcer-population(10) * control-capacity(4) boundary"
    );
    assert_eq!(
        attribute(
            &graph,
            WC_CARCERAL_REGISTER,
            "institution/prisoner-org-weighted"
        )
        .to_bits(),
        12.0_f64.to_bits(),
        "20 * 0.3 + 20 * 0.3 = 6.0 + 6.0 = 12.0"
    );
}

/// The zero-enforcer companion's own census — BLOCKER-4's branch,
/// exercised here for c01/c02 only. `enforcer-population` publishes 0
/// from a REAL, active, zero-population CARCERAL_ENFORCER node (the
/// scenario's own header distinction from an ABSENT enforcer class),
/// cross-checked against the mirror's `census: enforcer_population=0
/// prisoner_population=25 prisoner_org_weighted_sum=10.0`.
#[test]
fn c01_c02_on_the_zero_enforcer_companion() {
    let (graph, _) = run(ZERO_ENFORCER_SCENARIO);
    assert_eq!(
        attribute(
            &graph,
            ZE_ENFORCER,
            "social-class/enforcer-census-population"
        ),
        0.0,
        "a REAL active CARCERAL_ENFORCER node, seeded population 0 — not absence"
    );
    assert_eq!(
        attribute(
            &graph,
            ZE_PRISONER_IP,
            "social-class/prisoner-census-population"
        ),
        15.0
    );
    assert_eq!(
        attribute(
            &graph,
            ZE_PRISONER_LUMPEN,
            "social-class/prisoner-census-population"
        ),
        10.0
    );
    assert_eq!(
        attribute(
            &graph,
            ZE_CARCERAL_REGISTER,
            "institution/enforcer-population"
        ),
        0.0
    );
    assert_eq!(
        attribute(
            &graph,
            ZE_CARCERAL_REGISTER,
            "institution/prisoner-population"
        ),
        25.0
    );
    assert_eq!(
        attribute(
            &graph,
            ZE_CARCERAL_REGISTER,
            "institution/prisoner-org-weighted"
        )
        .to_bits(),
        10.0_f64.to_bits(),
        "15 * 0.4 + 10 * 0.4 = 6.0 + 4.0 = 10.0"
    );
}

/// The scenario's own node census, independent of any rule pack — six
/// `SOCIAL_CLASS` fixtures plus the one `INSTITUTION` carrier, no edges
/// (the census is type-scoped via `nodes`, the same "why no edges are
/// needed" note Pack A's own scenario carries). Restated here (also
/// proven, differently, by the previous commit's own
/// `all_four_scenarios_load_clean_independent_of_any_rule_pack`) as a
/// direct `NodeId`-order sanity check for this file's own constants.
#[test]
fn the_primary_scenario_loads_clean_with_the_declared_census() {
    let mut graph = HypergraphStore::new();
    let loaded = load_scenario(PRIMARY_SCENARIO, &mut graph).expect("the scenario must load clean");
    assert_eq!(loaded.node_count, 7, "6 social classes + 1 carrier");
    assert_eq!(
        loaded.edge_count, 0,
        "the census is type-scoped, no edges needed"
    );
    assert_eq!(loaded.node_types.get("SOCIAL_CLASS").copied(), Some(6));
    assert_eq!(loaded.node_types.get("INSTITUTION").copied(), Some(1));
}

/// The `defenum` ordinal-parity test (class-surface plan amendment 7,
/// Global Constraints: "every scenario re-declares `(defenum SocialRole
/// …)` and the suite carries one ordinal-parity test mirroring the
/// mint's") — THIS scenario's own `SocialRole` re-declaration must store
/// the SAME eight members in the SAME order as
/// `src/babylon/models/enums/social.py:34-41` (ADR195).
#[test]
fn social_role_order_is_the_ruled_ordinal() {
    let mut graph = HypergraphStore::new();
    let loaded = load_scenario(PRIMARY_SCENARIO, &mut graph).expect("the scenario must load clean");
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

/// `c01`/`c02` ALONE emit nothing (`control_ratio.py`'s own census
/// helpers, `:53-85`, never publish an event; only `_emit_crisis`/
/// `_emit_terminal_decision` do). A named negative to catch an accidental
/// emit regression IN THOSE TWO RULES SPECIFICALLY. Retargeted for Task 6
/// (`git blame` note: this test originally ran the whole `RULE` constant
/// against the primary world and asserted zero events — true only while
/// `control-ratio.bsl` held nothing past `c02`; `c03-crisis` now
/// legitimately emits over this SAME primary world, a fact
/// `c03_emits_the_crisis_when_prisoners_exceed_capacity` covers instead).
/// This test now isolates `c01`/`c02`'s own rule text — everything in
/// `RULE` before `c03-crisis`'s own `(rule …)` form — and runs THAT alone.
#[test]
fn c01_c02_emit_nothing() {
    let c01_c02_only = RULE
        .split("\n(rule control-ratio/c03-crisis")
        .next()
        .expect("c03-crisis must exist in RULE to split on");
    let mut graph = HypergraphStore::new();
    let mut sink = CollectingSink::default();
    run_once_into(PRIMARY_SCENARIO, c01_c02_only, &mut graph, &mut sink)
        .expect("c01/c02 alone must run");
    assert_eq!(
        sink.events.len(),
        0,
        "c01/c02 are pure census/publication rules — no CONTROL_RATIO_CRISIS \
         or TERMINAL_DECISION from these two rules alone"
    );
}

/// The non-participant vector, restated as its own named test (mirroring
/// `decomposition_conformance.rs::the_bourgeois_class_is_untouched_by_
/// the_whole_pack`'s own convention) — `bourgeois`'s `population`/
/// `active`/`organization` stay exactly at their seeded values; `c01`/
/// `c02` only ever WRITE the three published census-contribution fields,
/// never a class's own frozen-input fields.
#[test]
fn the_bourgeois_class_is_untouched_by_the_whole_pack() {
    let (graph, _) = run(PRIMARY_SCENARIO);
    assert_eq!(
        attribute(&graph, BOURGEOIS, "social-class/population"),
        50.0
    );
    assert_eq!(attribute(&graph, BOURGEOIS, "social-class/active"), 1.0);
    assert_eq!(
        attribute(&graph, BOURGEOIS, "social-class/organization"),
        0.0
    );
}

// ---------------------------------------------------------------------
// Task 6 — `c03-crisis` (the crisis gate, the `<=` boundary, BLOCKER-4).
// ---------------------------------------------------------------------

/// `c03`'s crisis payload, key-by-key against the frozen `_emit_crisis`
/// (`control_ratio.py:188-206`, `narrative_hint` dropped, D-record 5's
/// class of omission): the primary world's own census (enforcer 10,
/// prisoner 50) clears the `<=` boundary (40) by 10, so `c03` guard-splits
/// into the `enforcer-population > 0` branch and emits all eight
/// transcribed keys, `control-ratio` duplicating `actual-ratio` verbatim
/// (the frozen `:198-199` defect, port-as-is per ADR183).
#[test]
fn c03_emits_the_crisis_when_prisoners_exceed_capacity() {
    let (graph, sink) = run(PRIMARY_SCENARIO);
    let crises: Vec<_> = sink
        .events
        .iter()
        .filter(|(ty, _)| ty == "CONTROL_RATIO_CRISIS")
        .collect();
    assert_eq!(crises.len(), 1, "exactly one crisis this tick");
    let (_, payload) = crises[0];
    assert_eq!(
        payload.len(),
        8,
        "eight keys — narrative_hint dropped, no string payloads on emit"
    );
    assert_eq!(
        payload[0],
        ("enforcer-population".to_owned(), Value::Real(10.0))
    );
    assert_eq!(
        payload[1],
        ("prisoner-population".to_owned(), Value::Real(50.0))
    );
    assert_eq!(payload[2], ("control-capacity".to_owned(), Value::Int(4)));
    assert_eq!(
        payload[3],
        ("max-controllable".to_owned(), Value::Real(40.0))
    );
    assert_eq!(payload[4], ("actual-ratio".to_owned(), Value::Real(5.0)));
    assert_eq!(
        payload[5],
        ("over-capacity-by".to_owned(), Value::Real(10.0))
    );
    assert_eq!(
        payload[6],
        ("control-ratio".to_owned(), Value::Real(5.0)),
        "control-ratio duplicates actual-ratio verbatim (:198-199, a frozen \
         defect, port-as-is)"
    );
    assert_eq!(
        payload[7],
        ("capacity-threshold".to_owned(), Value::Real(4.0))
    );

    // The two latch writes (control_ratio.py:158-159).
    assert_eq!(
        attribute(
            &graph,
            CARCERAL_REGISTER,
            "institution/control-crisis-emitted"
        ),
        1.0
    );
    assert_eq!(
        attribute(&graph, CARCERAL_REGISTER, "institution/control-crisis-tick"),
        1.0
    );
}

/// The `<=` boundary (`control_ratio.py:150`, the frozen suite's own
/// `TestControlRatioMutationKillers` pin): prisoner population (40) EXACTLY
/// equals `enforcer-population(10) * control-capacity(4)` — within
/// capacity, no crisis. The mutation killer: flipping `when`'s `(>
/// prisoner-population max-controllable)` conjunct to `(>= …)` flips this
/// test red (mutation evidence recorded in this commit's own message).
#[test]
fn c03_does_not_emit_at_or_below_capacity() {
    let (graph, sink) = run(WITHIN_CAPACITY_SCENARIO);
    assert_eq!(
        sink.events.len(),
        0,
        "prisoner-population (40) <= max-controllable (40) — no crisis"
    );
    assert_eq!(
        attribute(
            &graph,
            WC_CARCERAL_REGISTER,
            "institution/control-crisis-emitted"
        ),
        0.0
    );
}

/// BLOCKER-4's guard-split branch: `enforcer-population == 0` (a REAL,
/// active, zero-population CARCERAL_ENFORCER class, not an absent one).
/// The payload carries the OTHER six keys and OMITS `actual-ratio`/
/// `control-ratio` entirely — loud absence, not the frozen `float("inf")`
/// (`control_ratio.py:185`, unrepresentable — `E-EVAL-014`/`E-EVAL-012`) —
/// and the tick does not abort: this test's own `run()` call would panic
/// via its `.expect(...)` if it did.
#[test]
fn c03_omits_the_ratio_keys_when_there_are_no_enforcers() {
    let (graph, sink) = run(ZERO_ENFORCER_SCENARIO);
    let crises: Vec<_> = sink
        .events
        .iter()
        .filter(|(ty, _)| ty == "CONTROL_RATIO_CRISIS")
        .collect();
    assert_eq!(crises.len(), 1, "exactly one crisis this tick");
    let (_, payload) = crises[0];
    assert_eq!(
        payload.len(),
        6,
        "six keys — actual-ratio/control-ratio OMITTED (BLOCKER-4), not \
         merely zeroed"
    );
    assert_eq!(
        payload[0],
        ("enforcer-population".to_owned(), Value::Real(0.0)),
        "a REAL active zero-population CARCERAL_ENFORCER class, not absence"
    );
    assert_eq!(
        payload[1],
        ("prisoner-population".to_owned(), Value::Real(25.0))
    );
    assert_eq!(payload[2], ("control-capacity".to_owned(), Value::Int(4)));
    assert_eq!(
        payload[3],
        ("max-controllable".to_owned(), Value::Real(0.0)),
        "0 enforcers * 4 capacity = 0"
    );
    assert_eq!(
        payload[4],
        ("over-capacity-by".to_owned(), Value::Real(25.0))
    );
    assert_eq!(
        payload[5],
        ("capacity-threshold".to_owned(), Value::Real(4.0))
    );
    for (key, _) in payload {
        assert_ne!(
            key, "actual-ratio",
            "actual-ratio must be OMITTED, never present with any value"
        );
        assert_ne!(
            key, "control-ratio",
            "control-ratio must be OMITTED, never present with any value"
        );
    }

    assert_eq!(
        attribute(
            &graph,
            ZE_CARCERAL_REGISTER,
            "institution/control-crisis-emitted"
        ),
        1.0
    );
}

/// The latch (`_control_crisis_emitted`, `control_ratio.py:154,158`): a
/// two-tick `TickSession` run over the primary world (which stays
/// over-capacity at tick 2 — nothing in this pack ever reduces the
/// published census back down) emits exactly ONE `CONTROL_RATIO_CRISIS`
/// across both ticks, never a second one at tick 2 once `control-
/// crisis-emitted` is latched to 1.
#[test]
fn c03_latches_once() {
    let mut session = TickSession::new(PRIMARY_SCENARIO, RULE, HypergraphStore::new())
        .expect("the pack must load into a session");
    let mut sink = CollectingSink::default();
    session.advance(&mut sink).expect("tick 1");
    session.advance(&mut sink).expect("tick 2");
    let crises: Vec<_> = sink
        .events
        .iter()
        .filter(|(ty, _)| ty == "CONTROL_RATIO_CRISIS")
        .collect();
    assert_eq!(
        crises.len(),
        1,
        "exactly one CONTROL_RATIO_CRISIS across two ticks — the \
         control-crisis-emitted latch blocks a tick-2 re-fire"
    );
    assert_eq!(
        attribute(
            session.graph(),
            CARCERAL_REGISTER,
            "institution/control-crisis-tick"
        ),
        1.0,
        "control-crisis-tick stays pinned at tick 1, never overwritten to 2"
    );
}

/// The readiness gate (`control_ratio.py:128-134`), isolated from the
/// `<=` boundary and from the delay-elapsed half of the SAME gate: a fifth
/// ad-hoc fixture (`decomposition-fired-known 0`, `carceral/control-
/// ratio-delay 0` — the delay-elapsed check would trivially clear if it
/// were the only thing gating this) whose census is DELIBERATELY
/// over-capacity (enforcer 5, prisoner 50; `max-controllable` = 20 < 50)
/// — the same shape `c03_emits_the_crisis_when_prisoners_exceed_capacity`
/// would fire on — proving `decomposition-fired-known == 0` ALONE accounts
/// for the silence.
#[test]
fn c03_stays_silent_before_the_readiness_gate() {
    const NOT_READY_SCENARIO: &str = r#"
(scenario control-ratio/not-ready-readiness-gate
  (defvocabulary NodeType (SOCIAL_CLASS INSTITUTION))
  (defenum SocialRole (CORE_BOURGEOISIE PERIPHERY_PROLETARIAT LABOR_ARISTOCRACY PETTY_BOURGEOISIE LUMPENPROLETARIAT COMPRADOR_BOURGEOISIE INTERNAL_PROLETARIAT CARCERAL_ENFORCER))

  (deffield social-class/role enum SocialRole)
  (deffield social-class/active int extensive)
  (deffield social-class/population int extensive)
  (deffield social-class/organization coefficient intensive)
  (deffield social-class/enforcer-census-population int extensive)
  (deffield social-class/prisoner-census-population int extensive)
  (deffield social-class/prisoner-census-org-weighted real extensive)

  (deffield institution/decomposition-fire-tick int extensive)
  (deffield institution/decomposition-fired-known int extensive)
  (deffield institution/decomposition-complete int extensive)
  (deffield institution/control-crisis-emitted int extensive)
  (deffield institution/control-crisis-tick int extensive)
  (deffield institution/terminal-decision-emitted int extensive)
  (deffield institution/enforcer-population int extensive)
  (deffield institution/prisoner-population int extensive)
  (deffield institution/prisoner-org-weighted real extensive)

  (defconst carceral/control-capacity 4)
  (defconst carceral/revolution-threshold 0.5c)
  (defconst carceral/control-ratio-delay 0)
  (defconst carceral/terminal-decision-delay 0)

  (node enforcer NodeType/SOCIAL_CLASS
    (social-class/role SocialRole/CARCERAL_ENFORCER)
    (social-class/active 1)
    (social-class/population 5)
    (social-class/organization 0.0c)
    (social-class/enforcer-census-population 0)
    (social-class/prisoner-census-population 0)
    (social-class/prisoner-census-org-weighted 0))

  (node prisoner NodeType/SOCIAL_CLASS
    (social-class/role SocialRole/INTERNAL_PROLETARIAT)
    (social-class/active 1)
    (social-class/population 50)
    (social-class/organization 0.3c)
    (social-class/enforcer-census-population 0)
    (social-class/prisoner-census-population 0)
    (social-class/prisoner-census-org-weighted 0))

  (node carceral-register NodeType/INSTITUTION
    ; NOT ready: decomposition-fired-known 0 — isolated from the
    ; delay-elapsed half of the SAME frozen gate (control-ratio-delay 0,
    ; which would trivially clear on its own at tick 1).
    (institution/decomposition-fire-tick 0)
    (institution/decomposition-fired-known 0)
    (institution/decomposition-complete 0)
    (institution/control-crisis-emitted 0)
    (institution/control-crisis-tick 0)
    (institution/terminal-decision-emitted 0)
    (institution/enforcer-population 0)
    (institution/prisoner-population 0)
    (institution/prisoner-org-weighted 0)))
"#;
    const NOT_READY_CARCERAL_REGISTER: NodeId = NodeId(2);
    let (graph, sink) = run(NOT_READY_SCENARIO);

    // Sanity: c01/c02 still publish this world's census unconditionally
    // (no readiness gate of their own), and it IS over capacity —
    // 5 * 4 = 20 max-controllable < 50 prisoners — so the silence below is
    // attributable to c03's own readiness gate, not to an under-capacity
    // census.
    assert_eq!(
        attribute(
            &graph,
            NOT_READY_CARCERAL_REGISTER,
            "institution/enforcer-population"
        ),
        5.0
    );
    assert_eq!(
        attribute(
            &graph,
            NOT_READY_CARCERAL_REGISTER,
            "institution/prisoner-population"
        ),
        50.0
    );

    let crises: Vec<_> = sink
        .events
        .iter()
        .filter(|(ty, _)| ty == "CONTROL_RATIO_CRISIS")
        .collect();
    assert_eq!(
        crises.len(),
        0,
        "decomposition-fired-known == 0 blocks c03 even though the census \
         is over capacity and control-ratio-delay is 0 — the readiness \
         gate alone accounts for the silence"
    );
    assert_eq!(
        attribute(
            &graph,
            NOT_READY_CARCERAL_REGISTER,
            "institution/control-crisis-emitted"
        ),
        0.0
    );
}
