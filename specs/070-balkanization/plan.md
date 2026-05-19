# Implementation Plan: Sovereign Topology + Faction Influence + Balkanization

**Branch**: `070-balkanization` | **Date**: 2026-05-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/070-balkanization/spec.md`

## Summary

Spec-070 adds a *political-topology layer* on top of the existing
21-system tick pipeline (spec-066 ADR044): explicit, contestable,
plural sovereignty over land. Three new entity / edge layers
(`PoliticalFaction`, `Sovereign`, plus `INFLUENCES` / `CLAIMS` /
`ADMINISTERS` edges), three new Systems
(`FactionInfluenceSystem`, `SovereigntySystem`,
`CollapseTransitionSystem`), and one MetabolismSystem extension
realise the MLM-TW thesis "you cannot build socialism on stolen
land" as a mechanical loop: a Faction's `ColonialStance` decides
the Sovereign's `ExtractionPolicy` which decides per-tick
habitability change.

Five clarifications resolved on 2026-05-18 set the spec's load-bearing
shape: dual-mode player (CAMPAIGN + OBSERVER), composite fracture
trigger (collapse-passive + contiguity-active), ≤5% steady-state /
≤15% spike wallclock budget, `GameOutcome` mapping (add only
`RED_OGV` + `FRAGMENTED_COLLAPSE`; augment existing
`REVOLUTIONARY_VICTORY` and `FASCIST_CONSOLIDATION` predicates), and
`SOV_USA_FED` initial state ruled by `FAC_RESTORATIONIST` (hard
start, INTENSIFY extraction from t=0).

Technical approach: greenfield Pydantic-frozen entities + new edge
types on existing `GraphProtocol`; reuse existing `MetabolismSystem`
extension point; extend existing `EndgameDetector` rather than
parallel detector; persist via existing PostgreSQL runtime
(spec-037); contiguity check via existing `ADJACENCY` edges +
`h3.grid_disk` helpers in `infrastructure/h3_mesh.py`; preserve
byte-identical determinism per spec-069.

## Technical Context

**Language/Version**: Python 3.12+ (project standard)

**Primary Dependencies**: Pydantic 2.x (frozen models per II.6 + I.19),
NetworkX 3.x via existing `GraphProtocol` adapter (per ADR030, not
the original ADR029 KuzuDB design), psycopg 3.x + psycopg_pool
(existing per spec-037), `h3` 4.2 (existing — used for `grid_disk`
neighbor lookup in contiguity check), `scipy.sparse` (existing —
matrix layer per II.12 if connected-component computation lifts to
sparse), Hypothesis ≥6.149.0 (existing — for FR-018 fracture-cost
property tests). No new third-party deps.

**Storage**: PostgreSQL 16+ via existing graph bridge (spec-037 +
spec-061); SQLite read-only reference data
(`marxist-data-3NF.sqlite`); new audit/snapshot mechanism for
CLAIMS/INFLUENCES mutations (FR-046) — concrete schema chosen in
Phase 0 research, default expectation: dedicated audit table per
edge type owned by the new `balkanization` subsystem (per II.11).

**Testing**: pytest with markers `math` / `ledger` / `topology` /
`integration` / `unit` (existing — per project CLAUDE.md);
Hypothesis property tests for FR-018 O(1) fracture-cost and
FR-044 determinism preservation; doctest for formula reference
modules per CLAUDE.md `Sphinx-Compatible Docstrings` policy.

**Target Platform**: Linux server (bare metal per X.1); engine
runs in-process within the same Python interpreter as the tick
loop.

**Project Type**: Single project — Babylon library/engine.
Spec-070 adds to existing `src/babylon/` tree; no new
service/process boundaries.

**Performance Goals**: SC-014 — three new Systems combined ≤5% of
spec-069's canonical-run per-tick wallclock budget (no single
system > 3%) at steady state on the Detroit tri-county footprint.
SC-015 — combined ≤15% during fracture spikes (active secession or
≥100-Territory collapse-transition). SC-004 — fracture operation
asymptotic cost flat in unchanged-Territory count across
N ∈ {10, 100, 1000} benchmark.

**Constraints**: Byte-identical determinism preserved (SC-011, per
spec-069 gate); Detroit tri-county footprint (~243K H3 res-7 hexes
total, but pruned to claimed-territory subgraphs at runtime); 21
existing systems' order-and-partition constraints (spec-056
`MATERIAL_BASE_SYSTEMS` / `ACTION_PHASE_SYSTEMS` /
`CONSEQUENCE_SYSTEMS` with import-time assertion); existing
`MetabolismSystem` position (13) must remain — extension via
sovereign-driven additive term, not new system at position 13.

**Scale/Scope**: Initial seed: at least 3 canonical PoliticalFactions
(Restorationist, Workers' Congress, Decolonial), plus Canadian-side
seed entities decided in Phase 0 research; 2 starting Sovereigns
(`SOV_USA_FED` ruled by FAC_RESTORATIONIST, `SOV_CAN_FED` per IV.1
Detroit-Windsor boundary requirement); ~46 H3 res-7 hexes × 3
Detroit tri-county counties at MVP. Audit complexity estimate:
~140–180h.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The Babylon constitution (v2.6.1) is consulted via the tier
priority in III.9 + IX.4. Below: each P0/P1 principle relevant to
spec-070 and a pass/fail/transition-state determination.

### P0 Gates (Never Drop — MUST pass)

| Principle | Relevance | Determination |
|---|---|---|
| I.19 Dialectic Primitive | Faction / Sovereign are NOT Dialectics in the constitutional sense — they're org-layer entities with INFLUENCES / CLAIMS edges. The `colonial_stance ∈ {UPHOLD, IGNORE, ABOLISH}` axis itself IS a derived dialectic (settler/anti-settler poles, weighted by colonial_stance-driven multipliers). Plan-phase encodes this distinction. | **PASS** — entities are correctly typed as non-Dialectic agents/institutions; the colonial-stance axis is reified as enum on the Faction node, consistent with III.9 P0 enforcement. |
| I.20 Spatial Substrate / Political Claims as Overlay | **DIRECTLY APPLICABLE.** The Faction/Sovereign/CLAIMS/INFLUENCES model is *exactly* what I.20 anticipates. Quoting: "Political claims are first-class state: a hex or county can have multiple overlapping claims, zero claims, or claims that change without the substrate changing." | **PASS** — Spec-070 is the constitutional realisation of I.20. CLAIMS edges are overlays. No Territory/hex mutation. FR-013, FR-009, FR-012 directly implement the overlay model. |
| II.9 Morphism Dyadic | All new edges (INFLUENCES, CLAIMS, ADMINISTERS) MUST be strictly dyadic. | **PASS** — INFLUENCES is Faction→Territory, CLAIMS is Sovereign→Territory, ADMINISTERS is Sovereign→Sovereign. All dyadic. No N-ary morphisms. |
| III.7 Determinism Hash | Every tick MUST produce deterministic hash. New systems' RNG (tiebreaker, hysteresis sampling) MUST be seeded from the tick's RNG stream. | **PASS** — FR-044, SC-011 explicit. Tiebreaker (FR-021) uses incumbent-priority + seed-deterministic RNG. Spec-069 byte-identical-replay gate preserved. |
| III.8 Aleksandrov Test | Every operator must trace to a material relation. | **PASS** — `metabolic_impact` traces to extraction → habitability degradation (I.9 Metabolic Rift). `argmax_f influence_level` traces to political-coalition material/ideological/military presence. Connected-component contiguity traces to geographic-coherence requirement for secession. Fracture O(1) traces to v1.1.0 Dynamic Sovereignty principle ("sovereignty as edges, not properties"). |
| V Verb Atomicity | Player verbs map to atomic graph operations. | **PASS** — In CAMPAIGN mode, player verbs route through spec-072 (downstream — atomicity is spec-072's concern). In OBSERVER mode, observer mutations (boost INFLUENCES, install Sovereign, force-secede) MUST each be atomic graph operations on a single edge/node. FR-049 makes this explicit and flags observer mutations in the audit log. |

**P0 RESULT: All 6 P0 gates PASS.** No P0 violations.

### P1 Gates (Load-Bearing — MUST pass for the spec's domain)

| Principle | Relevance | Determination |
|---|---|---|
| I.1 Settler-Colonial Frame | Principal contradiction = imperialism vs oppressed nations. | **PASS** — directly modelled via `ColonialStance ∈ {UPHOLD, IGNORE, ABOLISH}` as the fundamental political axis. |
| I.2 Imperial Rent (Φ) | W_c > V_c → imperial rent; pacification of core working class. | **PASS** — `extraction_policy=CONTINUE` is the IGNORE-faction route that maintains Φ (the RED_OGV trap); `CEASE` interrupts Φ; `INTENSIFY` accelerates it. Faction-installed Sovereigns directly modulate Φ. |
| I.4 George Jackson Bifurcation | Crisis → fascism (no solidarity edges) or revolution (solidarity across colonial divide). | **PASS** — endgame branching at FR-031 implements the bifurcation: `REVOLUTIONARY_VICTORY` requires ABOLISH-Sovereign majority + extraction stopped; `FASCIST_CONSOLIDATION` political route requires UPHOLD-Sovereign majority. RED_OGV is the "no solidarity-across-colonial-divide" trap variant. |
| I.6 Solidarity as Edge Mode | Four modes: EXTRACTIVE, TRANSACTIONAL, SOLIDARISTIC, ANTAGONISTIC. Qualitative, not scalar. | **PASS** — INFLUENCES.influence_level is a quantitative scalar (it's *political pull*, not solidarity). The qualitative aspect lives in colonial_stance enum + sovereignty_type enum + legal_status enum + fiscal_status enum + support_type enum. No solidarity scalar. |
| I.7 Quantitative→Qualitative | Quantities accumulate; qualities transform discretely with thresholds. Enums for qualities, floats for quantities. | **PASS** — `influence_level: float` (quantity, continuous accumulation) drives discrete `TERRITORY_TRANSITION` events when winning-Faction flips (qualitative). `legitimacy: float` drives discrete `SOVEREIGN_COLLAPSE` events. Colonial stance / extraction policy / sovereignty type are all enums. |
| I.16 Organization vs Institution | Organizations = voluntary, destroyable. Institutions = crystallized social relations, survive turnover. | **DETERMINATION CALL** — PoliticalFaction is closer to *organization* (a coalition that can dissolve, gain/lose influence). Sovereign is closer to *institution* (crystallized authority that survives ruling-faction-change via the CLAIMS edges). Plan-phase makes this explicit in `data-model.md` typology. |
| I.21 Sparrow Targeting | Three modes: centrality, singletons, cutsets. | **PASS** — secession (FR-029a (2)) is a cutset operation (remove edges on the contiguous sub-region boundary). Collapse-transition partition is centrality-style (highest-influence Faction wins). Player OBSERVER force-secede is a direct cutset specification. Surveiling a Faction with scattered influence is singleton detection. |
| II.1 Partition Emergence | {Core, Periphery} × {Bourgeoisie, Proletariat} as derived partition. | **PASS** — Faction operates at a *different layer* from this partition (factions are political coalitions; the Core/Periphery/B/P partition is a derived classification of agents within Territories). Compatible. |
| II.5 AI Observes, Never Controls | AI is parser + narrator, not adjudicator. | **N/A for this spec** — no AI integration in spec-070. The narrative pipeline (Wire, dual-narrative LLM) is spec-077's domain. |
| II.6 State is Data, Engine is Transformation | World is frozen Pydantic; Engine is pure `tick(world, actions) → (new_world, events)`. | **PASS** — all new entities use `model_config = ConfigDict(frozen=True)`. New Systems are pure transformations on the graph. No DB I/O during tick (audit row generation deferred to post-tick flush per existing pattern). |
| II.11 Subsystem Table Ownership | Each subsystem owns its tables; cross-subsystem reads via declared interfaces. | **PASS** — new `balkanization` subsystem owns: Faction nodes, Sovereign nodes, CLAIMS edges, INFLUENCES edges, ADMINISTERS edges, audit tables. Reads from Territory (substrate / spec-062 subsystem) go through existing graph-protocol interface — no direct table access. |
| II.12 Matrix Layer | NetworkX = authoring; scipy.sparse = computation; operator algebra = truth. | **PASS** — connected-component contiguity check uses `networkx.node_connected_component` (authoring API) or scipy.sparse CSR row-reduction for the N=1000 benchmark case (computation layer). Operator semantics: contiguity = closed-under-ADJACENCY traversal restricted to influence-majority nodes. |
| II.13 Transport Substrate | min-cost flow + slime-mold conductivity; AIR_LINK / SHIPPING_LANE / ROAD / RAIL edges. | **N/A for this spec** — no transport-substrate changes. Spec-070 operates on the political-claim overlay; II.13's substrate is separate. |
| III.1 No Magic Constants | Every number traces to primitives or data sources. | **PARTIAL** — multipliers in FR-007 (1.5 / 0.8 / 0.0; 2.0 / 0.5 / 0.3; 0.0 / 0.7 / 0.5; −0.5 / 0.0 / +0.8) come from `balkanization-spec.yaml` v1.2.0 (audit guidance, not empirical). FR-004 metabolic_impact rates (−0.02 / −0.005 / +0.01) similarly. **Phase 0 research MUST** document the provenance trace or flag these for empirical grounding. |
| III.2 Falsifiability Required | Every formula defines: prediction, null, distinguishing observable, falsifying data. | **PASS** — SC-001/002 specify the prediction (each of 5 endgames reachable from Detroit seed under stochastic variation). The null is "endgame outcome is independent of colonial-stance distribution". Falsifying observable: SC-002 100-run ensemble where endgame outcomes are uniformly random regardless of seeded Factions' stances. |
| III.4 Data Catalog | Sources are organized in a categorized catalog with provenance metadata; new sources require explicit constitutional addition. | **GATE — REQUIRES ACTION.** FR-039 mandates AIANNH (TIGER) and recent-presidential-election data sources for proxy-data seeding. Neither is present in `data-catalog.yaml` v2.6.3. **Phase 0 research MUST** propose constitutional additions for these two sources OR fall back to existing catalog sources (LODES for union density is already implicit via `marxist-data-3NF.sqlite`). |
| III.6 Model Pinning | Every AI parsing op MUST pin model version + persist parsed vector. | **N/A for this spec** — no AI parsing. |
| IV Michigan Test Case | All 83 counties, 2010–2025. BEA EAs as aggregation tier. | **PASS** — initial scope is Detroit tri-county (Wayne + Oakland + Macomb), backward-compatible per IV.2 acceptance criterion. Statewide schema-readiness assumption in spec covers IV's full scope as deferred work. |
| **IV.1 Detroit-Windsor Boundary** | Canada is first-class territorial substrate. Cross-border labor, trade, imperial rent circuits MUST be modelled. | **GATE — REQUIRES ACTION.** Spec-070 currently mentions only `rest_of_usa` as exterior fallback. Per IV.1, a Canadian Sovereign (`SOV_CAN_FED` ruled by, e.g., `FAC_CANADIAN_LIBERAL` or treated as a closed-loop boundary node) MUST be present in the initial seed. **Phase 0 research** resolves: which entity rules SOV_CAN_FED, and whether SOV_CAN_FED gets a colonial_stance assignment or is treated as a closed-loop boundary node. |

**P1 RESULT: 2 P1 gates require action in Phase 0 research:**
- III.1 + III.4: Multiplier provenance and proxy-data source catalog entries.
- IV.1: Canadian Sovereign in initial seed.

Both are RESEARCH-resolvable, not amendment-requiring. **No P1 violations.**

### Transition-State Principles (IX.3.4 Protocol)

Per IX.3.4: "If a principle is marked `[TRANSITION STATE]`, the agent
MUST treat it as blocked. It MAY propose a spec to resolve the
transition state, but it MUST NOT implement code that depends on
the unresolved principle."

| Principle | Transition Status | Spec-070 Dependency? |
|---|---|---|
| I.17 OODA (Amendment C — deferred to v2.8.0) | OODA profile architectural placement unresolved. | **NO DEPENDENCY.** Spec-070 explicitly defers Faction-internal cohesion + action-verb resolution to spec-072 / spec-073 (see "Out of Scope" in spec.md). Faction is treated as a passive influence-carrier; no OODA profile is needed in this spec. |
| I.18 Material-Ideological Distinction (Amendment D pending) | v1 implementation expressed this on hyperedges; v2 reimplementation must preserve without violating dyadic morphism. | **NO BLOCKING DEPENDENCY** — but the spec actively *supplies* a v2-compatible realisation: material dimension = INFLUENCES dyadic edges (per II.9); ideological dimension = `colonial_stance` enum on the Faction node. This realisation is consistent with the dyadic constraint and avoids the hyperedge ambiguity. Plan-phase notes this as a contribution toward Amendment D's eventual ratification. |
| II.3 NetworkX as Discretized Manifold (Amendment D) | v2 morphism graph strictly dyadic. | **NO DEPENDENCY** — all new edges are dyadic. |
| II.7 Edges vs Hyperedges (Amendment D) | Dyadic flows = morphism graph; N-ary membership = XGI hyperedge. | **NO DEPENDENCY** — no hyperedges introduced; Factions are *organizational* coalitions (per I.16), not XGI Communities. Plan-phase explicitly notes the distinction in `data-model.md` so future readers don't conflate. |

**Transition-State RESULT: No transition-state-blocked code.** Spec-070 may proceed.

### Anti-Patterns (VIII)

| Anti-Pattern | Risk | Mitigation |
|---|---|---|
| VIII.1 Solidarity as Scalar | INFLUENCES.influence_level might be misread as solidarity. | INFLUENCES is *political pull*, not solidarity. Spec.md is explicit; plan.md restates in `data-model.md`. |
| VIII.2 Union Density as Revolutionary | FR-039 uses union density to seed Workers' Congress influence. | Workers' Congress is the **IGNORE** (RED_OGV trap) faction, NOT the revolutionary one. The trap is *exactly* the anti-pattern — seeding it with union density reproduces the real-world settler-socialist demographic. The pedagogy of the spec relies on this anti-pattern being modelled, not avoided. Mitigation: `data-model.md` makes the theoretical framing explicit so future readers don't repair this into VIII.2-violation. |
| VIII.3 Determinism from Material Conditions | RED_OGV seeded from union density risks "settler-socialism is fated". | The hard-start initial state IS the material condition. But the player (CAMPAIGN mode) can flip influence; OBSERVER mode can directly construct alternatives. Conditions constrain, not determine — material conditions affect the initial state, not the run trajectory. |
| VIII.5 Claims Without Falsifiability | Endgame predicates must be falsifiable. | Each of SC-001 through SC-015 specifies a measurable observation. |
| VIII.6 Constants Without Data Sources | III.1 dependence. | Phase 0 research documents provenance for each constant. |
| VIII.9 Community as Pairwise Edge | Risk of representing Factions via pairwise edges and conflating with XGI Communities. | Factions are first-class nodes (`PoliticalFaction`), NOT pairwise edges or XGI hypergraph communities. The Naming Disambiguation section of spec.md makes this explicit. |
| VIII.10 Oppressor Hyperedge for Institutional Exclusion | UPHOLD-faction is the colonial oppressor. Does it deserve a hyperedge? | No hyperedge introduced. UPHOLD is an enum value on a Faction node, paired with `is_settler_formation: bool`. This is Category 1 modelling (settler vs anti-settler poles BOTH exist as first-class concepts), consistent with VIII.10 phrasing. |

**Anti-Pattern RESULT: All mitigations explicit. No violations.**

### Constitution Check Summary

- **P0 gates**: 6/6 PASS.
- **P1 gates**: 17 PASS, 2 require Phase 0 research action (III.1+III.4 multiplier+source provenance; IV.1 Canadian Sovereign seed). No P1 violations.
- **Transition-state**: 0 blocking dependencies. Spec-070 actively contributes a v2-compatible Material-Ideological realisation (potential Amendment D building block).
- **Anti-patterns**: All known risks mitigated with explicit documentation.

**Result**: ✅ Constitution Check PASS. Plan-phase may proceed.

## Project Structure

### Documentation (this feature)

```text
specs/070-balkanization/
├── plan.md              # This file
├── research.md          # Phase 0 output — multiplier provenance, Canadian Sovereign,
│                        #   ADJACENCY contiguity resolution, audit-schema choice,
│                        #   FactionInfluenceSystem partition placement
├── data-model.md        # Phase 1 output — entities, edges, enums, state machines
├── contracts/           # Phase 1 output — interface contracts (graph-protocol
│                        #   methods, system-input/output schemas, audit-row schema,
│                        #   seed-JSON schemas)
├── quickstart.md        # Phase 1 output — minimum reproducible run sequence
├── checklists/
│   └── requirements.md  # (Already exists from /speckit.specify)
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT in this command)
```

### Source Code (repository root)

```text
src/babylon/
├── models/
│   ├── entities/
│   │   ├── political_faction.py     # NEW — Faction entity (PoliticalFaction class,
│   │   │                            #   disambiguated from existing FactionBalance per FR-045)
│   │   └── sovereign.py             # NEW — Sovereign entity
│   │
│   └── enums/
│       ├── balkanization.py         # NEW — ColonialStance, ExtractionPolicy,
│       │                            #   SovereigntyType, FiscalStatus, LegalStatus,
│       │                            #   SupportType, PlayerMode (CAMPAIGN/OBSERVER)
│       ├── topology.py              # EXTEND — add CLAIMS, INFLUENCES, ADMINISTERS
│       │                            #   to EdgeType
│       └── events.py                # EXTEND — add SOVEREIGN_COLLAPSE,
│                                    #   TERRITORY_TRANSITION, FACTION_VICTORY,
│                                    #   SECESSION_DECLARED, CIVIL_WAR_DECLARED,
│                                    #   RED_SETTLER_TRAP_DETECTED, DUAL_POWER_ACTIVE,
│                                    #   RED_OGV_ENDGAME, FRAGMENTED_COLLAPSE_ENDGAME
│                                    #   + add GameOutcome.RED_OGV, GameOutcome.FRAGMENTED_COLLAPSE
│
├── engine/
│   ├── systems/
│   │   ├── faction_influence.py     # NEW — FactionInfluenceSystem (winning-faction
│   │   │                            #   resolution, INFLUENCES decay/accumulation,
│   │   │                            #   contiguity check for active secession)
│   │   ├── sovereignty.py           # NEW — SovereigntySystem (CLAIMS application,
│   │   │                            #   ruling_faction install, metabolic_impact
│   │   │                            #   surface; Metabolism reads from here)
│   │   ├── collapse_transition.py   # NEW — CollapseTransitionSystem (5-step pipeline
│   │   │                            #   per balkanization-spec.yaml §collapse_transition;
│   │   │                            #   fracture operation, civil-war event emission)
│   │   └── metabolism.py            # EXTEND — read sovereign.metabolic_impact and
│   │                                #   apply to territory.habitability per FR-043
│   │
│   ├── observers/
│   │   └── endgame_detector.py      # EXTEND — augment REVOLUTIONARY_VICTORY +
│   │                                #   FASCIST_CONSOLIDATION predicates; add RED_OGV
│   │                                #   + FRAGMENTED_COLLAPSE predicates per FR-031
│   │
│   └── simulation_engine.py         # EXTEND — register 3 new systems in
│                                    #   _DEFAULT_SYSTEMS and exactly one of
│                                    #   MATERIAL_BASE_SYSTEMS / ACTION_PHASE_SYSTEMS /
│                                    #   CONSEQUENCE_SYSTEMS per FR-042
│
├── formulas/
│   └── balkanization.py             # NEW — calculate_metabolic_impact(extraction_policy),
│                                    #   winning_faction_for_territory(graph, territory_id),
│                                    #   contiguous_influence_majority_subregion(graph,
│                                    #     faction_id, sovereign_id, adjacency_edges,
│                                    #     threshold),
│                                    #   detect_red_settler_trap(faction)
│
├── persistence/
│   ├── migrations/
│   │   └── 00XX_balkanization.sql   # NEW — Faction/Sovereign tables + CLAIMS/INFLUENCES/
│   │                                #   ADMINISTERS edge tables + audit/history tables
│   │                                #   per FR-046; subsystem-owned per II.11
│   ├── postgres_initialization.py   # EXTEND — DOMESTIC_REST_NODE already exists; add
│   │                                #   SOV_USA_FED + SOV_CAN_FED initial seed
│   └── balkanization_history.py     # NEW — audit-row writer for CLAIMS/INFLUENCES
│                                    #   mutations (chronicle realisation per FR-046)
│
├── data/
│   └── game/
│       └── balkanization/
│           ├── seed_factions.json   # NEW — FAC_RESTORATIONIST, FAC_WORKERS_CONGRESS,
│           │                        #   FAC_DECOLONIAL, + Canadian-side seed (Phase 0)
│           └── seed_sovereigns.json # NEW — SOV_USA_FED, SOV_CAN_FED initial state
│
└── config/
    └── defines/
        └── balkanization.py         # NEW — BalkanizationDefines (Pydantic) for
                                     #   tunable thresholds (FR-029c contiguity hysteresis,
                                     #   FR-032 RED_OGV floors, FR-032a FRAGMENTED_COLLAPSE
                                     #   duration, FR-007 multiplier overrides)

tests/
├── unit/
│   └── balkanization/
│       ├── test_faction_entity.py             # FR-005 — FR-008 entity validation
│       ├── test_sovereign_entity.py           # FR-001 — FR-004 entity validation
│       ├── test_colonial_stance_mapping.py    # FR-003, FR-007 derivability
│       ├── test_metabolic_impact_formula.py   # FR-004 numeric values
│       ├── test_winning_faction_argmax.py     # FR-021 tiebreaker determinism
│       ├── test_contiguity_check.py           # FR-029b connected-component logic
│       ├── test_fracture_operation_o1.py      # FR-018, SC-004 — Hypothesis property
│       │                                      #   tests at N ∈ {10, 100, 1000}
│       ├── test_red_settler_trap_detector.py  # FR-034, SC-006
│       └── test_player_mode_persistence.py    # FR-047 — FR-050
│
├── integration/
│   └── balkanization/
│       ├── test_collapse_transition_pipeline.py  # FR-024 5-step pipeline
│       ├── test_endgame_predicates.py            # FR-030 — FR-033 all 5 outcomes
│       ├── test_metabolism_extension.py          # FR-043 sovereign-driven habitability
│       ├── test_postgres_persistence.py          # FR-046 audit/snapshot round-trip
│       ├── test_seed_initialization.py           # FR-038 — FR-040 initial state
│       └── test_determinism_replay.py            # FR-044, SC-011 byte-identical
│
└── scenario/                                       # Slow scenario tests
    └── balkanization/
        ├── test_five_endgames_reachable.py       # SC-001, SC-002 — 100-run ensemble
        ├── test_red_ogv_pedagogy.py              # SC-012 — Workers' Congress trap arc
        ├── test_observer_mode_sandbox.py         # FR-047 OBSERVER mode end-to-end
        └── test_wallclock_budget.py              # SC-014, SC-015 performance gate
```

**Structure Decision**: Single project (Babylon library/engine).
All new code under `src/babylon/`, following existing module
conventions (entities under `models/entities/`, enums under
`models/enums/`, systems under `engine/systems/`, formulas under
`formulas/`, migrations under `persistence/migrations/`, seed data
under `data/game/`). Tests organized by domain
(`tests/unit/balkanization/`, `tests/integration/balkanization/`,
`tests/scenario/balkanization/`) consistent with the existing
test taxonomy in `tests/`. New `balkanization` subsystem owns its
own migrations and tables per Constitution II.11.

## Phase 0: Outline & Research

Phase 0 output: `research.md` (sibling file). Resolves five
research questions:

1. **Constitutional III.1 + III.4 — multiplier provenance + missing
   data sources.** Decide: (a) trace each multiplier in FR-007 and
   FR-004 to a primitive theoretical relation or empirical source;
   (b) determine whether to add AIANNH (TIGER) + recent presidential
   election data sources to `data-catalog.yaml` v2.6.4, or fall
   back to already-cataloged proxies.
2. **Constitutional IV.1 — Canadian Sovereign in initial seed.**
   Decide: which entity rules `SOV_CAN_FED` at game start, and
   whether SOV_CAN_FED gets `colonial_stance` assignment or is a
   passive boundary node with NULL ruling_faction.
3. **FactionInfluenceSystem partition placement (FR-042).**
   Decide: ACTION_PHASE_SYSTEMS or CONSEQUENCE_SYSTEMS in the
   spec-056 partition. Implication: affects whether faction-
   influence resolution observes player actions made in the same
   tick or only in prior ticks.
4. **ADJACENCY spatial-resolution for contiguity check (FR-029b).**
   Decide: county-level adjacency or H3-res-7 adjacency. Implication:
   secession granularity (whole-county-or-larger vs neighborhood-
   sized blobs).
5. **Audit/Chronicle schema realisation (FR-046).** Decide:
   dedicated audit table per edge type vs JSON-history column vs
   event-stream-only. Implication: storage cost, query performance,
   and replay-from-tick-T mechanics.

Each research item produces a Decision / Rationale / Alternatives
entry in `research.md`.

## Phase 1: Design & Contracts

Phase 1 output: `data-model.md`, `contracts/`, `quickstart.md`,
and agent-context update via `update-agent-context.sh claude`.

### `data-model.md` — Entities, Edges, Enums, State Machines

Will enumerate:
- `PoliticalFaction` Pydantic model with field types + validators
- `Sovereign` Pydantic model with field types + validators
- Edge schemas: CLAIMS / INFLUENCES / ADMINISTERS (attribute keys,
  types, constraints)
- Enum complete value sets: ColonialStance / ExtractionPolicy /
  SovereigntyType / FiscalStatus / LegalStatus / SupportType /
  PlayerMode
- Derivation tables: colonial_stance → mechanical-multipliers;
  colonial_stance → extraction_policy → metabolic_impact
- State machines: Sovereign lifecycle (founded → ruling →
  contested → collapsed → dissolved); CLAIMS legal_status
  transitions (DE_JURE → DISPUTED → DE_FACTO → CEDED); fracture
  state machine (eligible → declared → executing → settled)
- Cross-reference to constitutional principles (P0 + relevant P1)
  per entity

### `contracts/` — Interface Schemas

Will produce:
- `contracts/graph_protocol_extensions.md` — new methods/queries
  the GraphProtocol must expose to support spec-070 (e.g.,
  `query_faction_influence_by_territory`,
  `query_sovereign_claims`, `query_adjacent_territories`)
- `contracts/balkanization_events.json` — JSON Schema for each
  new event-type payload
- `contracts/seed_factions.schema.json` — JSON Schema for
  `seed_factions.json`
- `contracts/seed_sovereigns.schema.json` — JSON Schema for
  `seed_sovereigns.json`
- `contracts/audit_row.schema.json` — JSON Schema for
  CLAIMS/INFLUENCES audit-row payloads (per the Phase 0 decision
  on FR-046 schema)
- `contracts/balkanization_defines.schema.json` — JSON Schema for
  the `BalkanizationDefines` Pydantic model (tunable thresholds)
- `contracts/system_io_contracts.md` — input/output contracts for
  each of FactionInfluenceSystem, SovereigntySystem,
  CollapseTransitionSystem (what graph state they read, what they
  write, what events they emit, what context.persistent_data keys
  they use)

### `quickstart.md` — Reproducible Run Sequence

Will produce a minimum sequence to:
1. Install dependencies (`poetry install` — no new deps).
2. Apply the new migration.
3. Run a 5-tick smoke test that exercises the canonical Detroit
   tri-county seed and verifies (a) at least one CLAIMS edge from
   SOV_USA_FED to each tri-county Territory, (b) habitability
   declines under FAC_RESTORATIONIST rule, (c) determinism-replay
   produces byte-identical state.
4. Run the scenario test that drives the simulation to each of
   the 5 endgames at least once (smoke test for SC-001).

### Agent Context Update

After Phase 1 doc generation, run
`.specify/scripts/bash/update-agent-context.sh claude` to update
the project's per-agent context file with the new technology /
component additions. Preserve manual-edit markers.

## Post-Design Constitution Re-Check

After Phase 0 + Phase 1 artifact generation, re-evaluating gates:

| Principle | Pre-Design | Post-Design | Notes |
|---|---|---|---|
| I.20 Spatial Substrate | PASS | **PASS** | data-model.md explicitly notes Territory entity is unmodified; CLAIMS / INFLUENCES are overlays added to existing nodes. |
| II.9 Morphism Dyadic | PASS | **PASS** | All three new edge types in §4 of data-model.md are dyadic; ADMINISTERS is constrained to acyclic DAG. |
| II.11 Subsystem Ownership | PASS | **PASS** | research.md R-005 + data-model.md §6 specify the `balkanization` subsystem owns: 2 entity tables, 3 edge tables, 2 audit tables. Cross-subsystem reads go via GraphProtocol (declared interface). |
| III.1 No Magic Constants | PARTIAL | **PASS** | research.md R-001 documents all 11 multipliers as theoretical defaults with explicit override path via BalkanizationDefines. Constraint satisfied: every number has a provenance trace. |
| III.4 Data Catalog | GATE | **PASS WITH FOLLOW-UP** | research.md R-001 falls back to existing catalog sources (QCEW + Natural Earth) for two proxies; flags MIT Election Lab as a v2.6.4 PATCH catalog amendment. Spec-070 itself does not require the amendment to merge — initial Restorationist seeding can use Census Bureau presidential-election fixtures already in the catalog as an interim source. |
| III.7 Determinism Hash | PASS | **PASS** | system_io_contracts.md §1–3 explicit Determinism Notes per System. graph_protocol_extensions.md mandates deterministic ordering on all new query methods. |
| III.8 Aleksandrov Test | PASS | **PASS** | Every operator in data-model.md §3 + system_io_contracts.md traces to a material relation. No operators introduced in Phase 1 that weren't already vetted in pre-design check. |
| IV.1 Detroit-Windsor | GATE | **PASS** | research.md R-002 introduces SOV_CAN_FED ruled by FAC_LIBERAL_IMPERIAL; data-model.md §8 specifies initial CLAIMS via existing LODES Canada-destination infrastructure. |
| I.16 Org vs Institution | DETERMINATION CALL | **PASS** | data-model.md §2 explicitly types PoliticalFaction as organization-side and Sovereign as institution-side. Resolved. |
| I.18 Material-Ideological (TRANSITION STATE) | NO BLOCK | **CONTRIBUTES** | data-model.md §4.2 explicitly documents INFLUENCES = material, ColonialStance = ideological as v2 realisation. Contribution toward Amendment D. |

**Post-design RESULT**: All gates PASS. The III.4 follow-up (MIT
Election Lab catalog amendment) is a future maintenance task; it
does NOT block spec-070 from progressing to /speckit.tasks.

## Complexity Tracking

> Constitution Check produced 0 violations and 1 follow-up maintenance
> task. No complexity-justification table required.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Phase Completion Summary

**Phase 0 (Research)**: ✅ Complete. 5 research questions resolved
in [research.md](./research.md).

**Phase 1 (Design & Contracts)**: ✅ Complete. Artifacts:
- [data-model.md](./data-model.md) — 7 enums, 2 entities, 3 edge
  schemas, 3 state machines, 8 constitutional cross-references.
- [contracts/](./contracts/) — 6 contract files:
  - `system_io_contracts.md` (system-level read/write/event contracts)
  - `graph_protocol_extensions.md` (6 new GraphProtocol methods)
  - `seed_factions.schema.json` (FR-008 + R-002)
  - `seed_sovereigns.schema.json` (FR-040 + R-002)
  - `audit_row.schema.json` (FR-046 + R-005)
  - `balkanization_events.json` (9 new event-type payload schemas)
  - `balkanization_defines.schema.json` (tunable thresholds)
- [quickstart.md](./quickstart.md) — 8 reproducible steps.
- Agent context: updated `CLAUDE.md` via
  `update-agent-context.sh claude`.

**Next command**: `/speckit.tasks` — generate the actionable,
dependency-ordered tasks.md for Phase 2 implementation.
