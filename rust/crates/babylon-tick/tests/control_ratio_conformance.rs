//! Pack B (`control-ratio/*`, Material Base @12.0) conformance — Task 5 of
//! `docs/superpowers/plans/2026-08-17-decomposition-controlratio-port.md`
//! (frozen source: `src/babylon/engine/systems/control_ratio.py`, 248
//! lines). Branched off MERGED `dev` (never stacked on PR A, #193) — NO
//! Rust source edits; Task 1 already registered `"control-ratio"` in
//! `lib.rs`'s system `HashSet`.
//!
//! # This commit's scope — the scenario ceremony, before any rule exists
//!
//! This commit creates the four `.bscn` scenarios this whole Pack B ever
//! needs (`control-ratio-conformance.bscn` PRIMARY/genocide,
//! `-revolution-conformance.bscn`, `-within-capacity-conformance.bscn`,
//! `-zero-enforcer-conformance.bscn` — Tasks 6-7's own plan rows list no
//! further scenario-file edits) plus their frozen-mirror provenance
//! (`control_ratio_conformance.py`), and proves ONLY that the scenarios
//! themselves load clean and declare `SocialRole` in the ruled ordinal —
//! independent of any `control-ratio/*` rule pack, which does not exist
//! yet (`content/rules/control-ratio.bsl` lands in the next commit). The
//! `c01`/`c02` census tests (`c01_publishes_the_two_prisoner_roles_and_the_
//! enforcer_count`, `c01_premultiplies_population_by_organization`,
//! `c02_publishes_the_three_aggregates_unconditionally`) were written and
//! run RED against these same four scenarios first — TDD's red phase —
//! then land, GREEN, in the commit that creates `control-ratio.bsl`,
//! exactly mirroring `decomposition_conformance.rs`'s own Task-1/Task-2
//! split (Task 1 shipped the scenario + mirror + validity tests only;
//! Task 2 added the rule pack and its own tests to the SAME file).
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
//! This commit's own scope is the `census:` line of each world only — the
//! `_count_enforcer_population`/`_count_prisoner_population_and_org`
//! outputs, which is exactly what `c01`/`c02` (next commit) will compute
//! and publish. The `post-tick persistent_data`/`events` sections are the
//! frozen engine's FULL `step()` (crisis + terminal decision both
//! included, since the frozen function has no Task boundary) — printed
//! here for Tasks 6-7's own future provenance.

use babylon_bsl::scenario::load_scenario;
use babylon_graph::hypergraph_store::HypergraphStore;

const PRIMARY_SCENARIO: &str = include_str!("../content/scenarios/control-ratio-conformance.bscn");
const REVOLUTION_SCENARIO: &str =
    include_str!("../content/scenarios/control-ratio-revolution-conformance.bscn");
const WITHIN_CAPACITY_SCENARIO: &str =
    include_str!("../content/scenarios/control-ratio-within-capacity-conformance.bscn");
const ZERO_ENFORCER_SCENARIO: &str =
    include_str!("../content/scenarios/control-ratio-zero-enforcer-conformance.bscn");

/// All four `.bscn` siblings load clean, entirely independent of any
/// `control-ratio/*` rule pack (`load_scenario` alone, no `RULE` source at
/// all) — the load-bearing proof that this whole Pack B's ONLY scenario
/// ceremony is syntactically sound before a single rule exists.
#[test]
fn all_four_scenarios_load_clean_independent_of_any_rule_pack() {
    for (label, scenario, expected_social_class) in [
        ("primary", PRIMARY_SCENARIO, 6),
        ("revolution", REVOLUTION_SCENARIO, 6),
        ("within-capacity", WITHIN_CAPACITY_SCENARIO, 3),
        ("zero-enforcer", ZERO_ENFORCER_SCENARIO, 3),
    ] {
        let mut graph = HypergraphStore::new();
        let loaded = load_scenario(scenario, &mut graph)
            .unwrap_or_else(|e| panic!("{label} scenario must load clean: {e:?}"));
        assert_eq!(
            loaded.node_types.get("SOCIAL_CLASS").copied(),
            Some(expected_social_class),
            "{label}: SOCIAL_CLASS count"
        );
        assert_eq!(
            loaded.node_types.get("INSTITUTION").copied(),
            Some(1),
            "{label}: exactly one carrier"
        );
        assert_eq!(loaded.edge_count, 0, "{label}: no edges needed");
    }
}

/// The primary scenario's own node census in detail — six `SOCIAL_CLASS`
/// fixtures plus the one `INSTITUTION` carrier, no edges (the census is
/// type-scoped via `nodes`, the same "why no edges are needed" note
/// Pack A's own scenario carries).
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
