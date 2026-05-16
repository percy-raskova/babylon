# Babylon: ai-docs vs Code Reality Audit — 2026-05-16

**Branch**: `066-marx-coherence-fixes` (v2.9.0, post-spec-066)
**Method**: 6 parallel subagents cross-referenced every spec under `ai-docs/` and `specs/` against the live `src/babylon/`, `web/frontend/`, and `/media/user/data/babylon-data/` trees
**Scope**: Epochs 1–3 with implementation focus on Epoch 3

---

## TL;DR

| Epoch | Status | One-line verdict |
|---|---|---|
| 1 — Engine | **DONE** | Mechanics intact; docs stale (13 systems → 21, 25 events → ~70, 31 formulas → ~52). |
| 2 — Foundation | **2.1–2.4 DONE · 2.5 PARTIAL · 2.6 OBSOLETE · 2.7 PARTIAL · 2.8 HALF · 2.9 MOSTLY MISSING** | Data layer real; UI pivoted to React+Django; ISA mapping still aspirational. |
| 3 — Game | **SUBSTRATE BUILT · GAMEPLAY LAYER MOSTLY MISSING** | 60–70 % of materialist primitives shipped via specs 011–066; the player-facing verbs, factions, doctrine, and trap mechanics are stubs. |
| 4 — Platform | **NOT STARTED** (DuckDB unification dropped) | RAG already pivoted to pgvector in Epoch 2 work; remaining vision is multi-scenario + API layer. |

**The single highest-leverage piece of unimplemented work**: Balkanization (Faction → Sovereign → INFLUENCES edges → branching endgames). It is theoretically central ("you cannot build socialism on stolen land"), independent in dependency terms, and unblocks Reactionary Subject, Doctrine Tree, and Warlord Trajectory.

**What "Epoch 3" actually needs to be playable** — see **Part 3-FULL** below for the consolidated 27-spec full-vision catalog (the original 14-spec MVP-scoped table here is superseded).

Note: spec numbers 067-069 are already reserved (per ADR044) for QCEW v2, BEA Input-Output, and SQLite read caching respectively. New specs start at 070.

---

## Part 1 — Implementation Status by Epoch

### Epoch 1: "The Engine" — COMPLETE

Per `ai-docs/epochs/epoch1-complete.md` Epoch 1 closed 2026-01-05 with 13 systems, 25 events, 31 formulas, 4646 tests. Audit confirms:

**Confirmed in code**:
- All 13 named systems exist as code symbols (`VitalitySystem`, `TerritorySystem`, `ImperialRentSystem`, `SolidaritySystem`, `ConsciousnessSystem`, `SurvivalSystem`, `StruggleSystem`, `ContradictionSystem`, `MetabolismSystem`, `DecompositionSystem`, `ControlRatioSystem`, `EventTemplateSystem`, plus `EndgameSystem` refactored to `EndgameDetector` observer).
- Fundamental Theorem implemented (`calculate_imperial_rent`, `calculate_labor_aristocracy_ratio`).
- Survival Calculus (`P(S|A)`, `P(S|R)`, crossover threshold, Kahneman-Tversky λ=2.25) in `formulas/survival_calculus.py`.
- George Floyd Dynamic (EXCESSIVE_FORCE → UPRISING cascade) in `engine/systems/struggle.py`.
- Metabolic Rift (ΔB, overshoot_ratio) in `formulas/metabolic_rift.py` + `engine/systems/metabolism.py`.
- Carceral Geography (5-type TerritoryType, DisplacementPriorityMode, heat dynamics) in `engine/systems/territory.py`.
- Terminal Crisis cascade (SUPERWAGE_CRISIS → CLASS_DECOMPOSITION → CONTROL_RATIO_CRISIS → TERMINAL_DECISION) — all four events fire.
- Three endgame outcomes (Revolutionary Victory, Ecological Collapse, Fascist Consolidation) wired in `observers/endgame_detector.py`.

**Documentation drift since Epoch 1 closed**:

| Doc claim | Code reality | Where drift was introduced |
|---|---|---|
| 13 systems in `_DEFAULT_SYSTEMS` | **21 systems** | spec-002 (3), spec-017 (1), spec-021 (1), spec-022 (1), spec-030 (1), spec-032 (1), spec-056 (reorder), spec-062 (Substrate), spec-066 (ADR044) |
| 25 EventTypes | **~70 EventTypes** | Specs 030, 032, 033, 039, 040, etc. each added events |
| 31 formulas | **~52 formula functions** across 17 modules | Specs 002 curvature, 022 community, 030 lifecycle, 034 ternary consciousness, 043 routing |
| `EndgameSystem` in pipeline | **Refactored to `EndgameDetector` observer** | Architectural cleanup |
| `EventTemplateSystem` in pipeline | **Orphaned** — file exists but not in `_DEFAULT_SYSTEMS` | Deprecation drift |
| DearPyGui dashboard | **DELETED** (`src/babylon/ui/dashboard/` empty); UI is React + Django | spec-041 / spec-042 / spec-061 |
| Pipeline order: ImperialRent first, Metabolism at 2.5 | **Materialist causality reorder**: ImperialRent at position 9, Metabolism at 13 | spec-056 F6=α reorder |

**Genuinely missing Epoch 1 work** (small):
- Three balance-targets verification tests (`test_crisis_timing`, `test_outcome_distribution`, `test_visual_dynamics`) — never written.
- `extraction_intensity` wiring from `ImperialRentSystem` → `Territory` (deferred to Epoch 2 in the spec; still deferred).
- React UI components for metabolic gauge / rift trend / territory health.
- TerritorySystem AUTO displacement mode (configs exist, switching logic doesn't).
- "Synopticon" named primitives (`SynopticView`, gloom state, degradation/clarity model) — work diffused across `observers/`, `topology_monitor.py`, `ai/director.py`.

---

### Epoch 2: "The Foundation" — PARTIAL, with three slices superseded by pivots

| Slice | Doc status | Code reality |
|---|---|---|
| 2.1 | COMPLETE | ✅ `reference/schema.py` has 86+ SQLAlchemy ORM models (33 dim + 34 fact + bridges). `data/sqlite/marxist-data-3NF.sqlite` (8.79 GB) populated. **Exceeds spec** (adds LODES, ATUS, FAF, eviction, foreclosure, TIGER tables not in original list). |
| 2.2 | COMPLETE | ✅ Census + QCEW + CBP loaders ran; data is in SQLite. ⚠️ Python modules live out-of-tree at `/media/user/data/babylon-data/` (symlinked as `src/babylon_data`) per ADR037. |
| 2.3 | COMPLETE | ✅ FRED, BEA, Energy, Trade, Materials loaders ran. |
| 2.4 | COMPLETE | ✅ HIFLD (RSA), FCC broadband loaders ran. |
| 2.5 H3 | PLANNED | ⚠️ **Partial; different resolution.** Spec asked for res-4 (county-grain, ~288K cells continental US). Code uses **res-7** for the hex hydrator (Detroit tri-county MVP, ~243K hexes), with res-4 retained only in `BridgeCountyH3`. H3 mesh ops exist (`infrastructure/h3_mesh.py`, `r8_mesh.py`); frontend uses `H3HexagonLayer` via deck.gl. |
| 2.6 PyQt | PLANNED | ❌ **OBSOLETE.** PyQt6, PyQt6-WebEngine, pydeck, pytest-qt all removed from `pyproject.toml`. `src/babylon/ui/dashboard/` is empty. **Superseded by**: React 19 + Vite + Django + deck.gl + Tailwind v4 + Zustand + Recharts in `web/frontend/` (specs 041, 042, 061). |
| 2.7 Schema Integration | PLANNED | ⚠️ **Partial; renamed modules.** No `scenario_loader.py`; instead hydration is split across `engine/hydration/reference.py`, `persistence/hex_hydrator.py`, `persistence/postgres_initialization.py`, `economics/hydrator.py`. The dim_county → territory → SocialClass mapping is at hex grain (res-7), not county grain. |
| 2.8 LODES & Freight | PLANNED | ⚠️ **Half done.** LODES OD matrix loaded into `FactLodesCommuterFlow` and consumed via `economics/lodes_commute_matrix.py` (sparse CSR, H3-res-7 indexed). FAF/CAS freight: **schema exists, no loader, no `EdgeType.CIRCULATION` weighting from tonnage**. 12 LODES integration tests still skipped per ADR037. |
| 2.9 Ideological Cartography | PLANNED | ❌ **Mostly missing.** `Institution` entity model exists (spec-040) with `ApparatusType.ISA_EDUCATIONAL/RELIGIOUS/MEDIA`. **No HIFLD schools/colleges/worship loader**; **no FCC FM/AM/TV broadcasting tower loader** (only broadband); **no `FactInstitution` table** with per-hex density. Bible Belt / Red Belt cartography is unrepresented. |

**Top-level pivots that retroactively rewrote Epoch 2** (each documented in an ADR):

| Original direction | What replaced it | ADR / spec |
|---|---|---|
| NiceGUI + ECharts + Tailwind dashboard | PyQt6 + QWebEngineView + pydeck (transient) | ADR026, ADR027 |
| PyQt6 + QWebEngineView + pydeck | React 19 + Vite + deck.gl + MapLibre + Tailwind v4 + Django | spec-041, spec-042, spec-061 (ADR039) |
| ChromaDB for RAG | pgvector inside PostgreSQL (768-dim, sentence-transformers all-mpnet-base-v2 pinned by SHA) | spec-037, ADR039, ADR034 (now historical) |
| ADR002 SQLite-only runtime | Hybrid: SQLite read-only for reference data; PostgreSQL 16 + PostGIS + pgvector for runtime | spec-037 |
| ADR029 NetworkX + KuzuDB hybrid graph | NetworkX-only via GraphProtocol + adapters; persistence to PostgreSQL | ADR030 supersedes ADR029 |
| DuckDB as "Phase 3" columnar graph adapter | DuckDB removed entirely from runtime; survives only as analytical reader over archived R2 Parquet | commit `d704eece`, ADR030 |
| H3 res-4 county-grain MVP | H3 res-7 Detroit tri-county MVP for spec-062 / spec-063 / spec-065 work | ADR040, ADR042, ADR044 |
| In-tree `src/babylon/data/{loaders}` | Out-of-tree at `/media/user/data/babylon-data/`, symlinked as `src/babylon_data` | commit `4ce7c96a`, ADR037 |
| US-continental scope, 50 states + DC + PR | 9-boundary-node model (Canada first-class + 7 world regions + `rest_of_usa` exterior) | spec-062 R4 amendment |
| 7-system Epoch 1 MVP pipeline (from spec-001) | 21-system materialist-causality pipeline w/ Substrate at 2.5 | spec-066 ADR044 |

**Remaining real Epoch 2 work** (not pivoted away, just unfinished):
- FAF/CAS freight loader + `TRIBUTE`/`CIRCULATION` edge weighting from commodity tonnage.
- HIFLD schools / worship / colleges + FCC broadcasting tower loaders.
- `FactInstitution` table + per-hex density metrics (`schools_per_capita`, `dominant_isa`, `hegemony_index`).
- Ideological-cartography → `Territory` attribute pipeline (the "DSA-velvet-glove" / military-town multipliers from `census-insights.yaml` remain aspirational).

---

### Epoch 3: "The Game" — SUBSTANTIAL FOUNDATION, GAMEPLAY LAYER MOSTLY MISSING

Epoch 3 was marked PLANNED in `epochs/overview.md`. Reality is more nuanced: through specs 011–040 and 062–066, **roughly 60–70 % of the *materialist substrate* under Epoch 3 has been built**, but **almost none of the *player-facing systems*** the 3A/3B/3C/3D specs describe exist as wired engine systems.

#### Sub-Epoch 3A (Materialism): Demographics + Vanguard Economy

| Spec | Implemented? | Where |
|---|---|---|
| Class consumption (s_bio + s_class fields) | ✅ | `models/entities/social_class.py:348-357` |
| Subsistence multipliers (class hierarchy) | ✅ | `social_class.py:29-34` (P=1.5, LA=5, C=10, B=20) |
| Metabolic rift formula + system | ✅ | `formulas/metabolic_rift.py`, `engine/systems/metabolism.py` (pos 13) |
| D-P-D' lifecycle (age cohorts, birth/death, mobility, race-conditional Chetty gaps) | ✅ | `economics/lifecycle/`, `engine/systems/lifecycle.py` (pos 7), spec-030 |
| Race / gender / colonial-position as Community hyperedges | ✅ | `models/enums/community.py` (SETTLER/NEW_AFRIKAN/FIRST_NATIONS/CHICANO/WOMEN/TRANS/PATRIARCHAL/etc.) |
| Imperial Rent 5-phase circuit + labor-aristocracy classification | ✅ | `engine/systems/economic.py`, spec-013 MELT |
| StateFinance, RevolutionaryFinance, PrecarityState models | ✅ | `models/entities/{state_finance,revolutionary_finance,precarity_state}.py` |
| Organization base + VanguardResources skeleton | ✅ | `models/entities/organization.py`, `models/vanguard_resources.py` (spec-031) |
| Trap detection (Liberal/Ultra-Left/Rightist) | ✅ | `engine/trap_detection.py` |
| **Coherence Factor formula** | ❌ | No `formulas/coherence.py`; `CF = sigmoid((CL/SL)/K)` unimplemented |
| **Vanguard Economy System** (decay + maintenance + action resolution) | ❌ | No `engine/systems/vanguard_economy.py`; REPRODUCE/EDUCATE/MOBILIZE resolvers are `pass` stubs |
| **Reproductive Labor Tier-1** (subsistence floor, capped extraction, ReproductionSystem) | ❌ | No `engine/systems/reproduction.py`; `ImperialRentSystem` doesn't cap at floor |
| **Demographic crisis detector + resolution pathway selector** | ❌ | No `consumption_balance` metric; no `select_resolution_pathway()`; no `DEMOGRAPHIC_CRISIS` event |
| **FiscalSystem / FundraisingSystem / PrecaritySystem** | ❌ | Models exist; per-tick orchestration doesn't |
| **S_imperial explicit accounting** (labor-aristocracy subsidy as a tracked field) | ❌ | Subsidy phase exists but doesn't write `s_imperial` to LA entities |

#### Sub-Epoch 3B (Organization): Cohesion Mechanic

| Spec | Implemented? |
|---|---|
| `Organization.cohesion` field | ✅ exists, but cosmetic — not driven by Michels-style entropy/cadre_ratio dynamics |
| Iron Law of Oligarchy (entropy growth, cohesion decay, factionalism) | ❌ no `CohesionSystem` |
| Three laws (Transmission `min(s, c_src, c_tgt)`, Scale `entropy ∝ log(N)·(1-cadre_ratio)`, Decay) | ❌ |
| MASS_RECRUITMENT / RECTIFICATION / POLITICAL_EDUCATION player actions | ❌ stub or absent |
| `ORGANIZATIONAL_SPLIT` event with node-split (one org → `_Revisionist` + `_UltraLeft` w/ severed SOLIDARITY edges) | ❌ |

**Estimated coverage: ~5 %**

#### Sub-Epoch 3C (Information): Fog of War, Wire, Repression, State Attention

| Spec | Implemented? | Notes |
|---|---|---|
| 3.4 Fog of War — Mass Receptivity `M_r = (1-P(S\|A))·I_a·C_f` | ❌ | No `IntelligenceSystem`; `resolve_investigate` is a `pass` stub |
| 3.4 — Intel Confidence + decay + masked attributes | ❌ | No `PlayerIntelLayer`, no falsified UI data |
| 3.5 The Wire — Dual-narrative LLM director (MVP) | ✅ | `ai/director.py` has `CORPORATE_SYSTEM_PROMPT` + `LIBERATED_SYSTEM_PROMPT` + `_dual_narratives` |
| 3.5 — Hegemony resource + Manufacturing-Consent linguistic patterns | ❌ | No `HegemonySystem`, no `corporate_reach`/`liberated_reach` |
| 3.5 — RAG corpus split (HEGEMONIC vs COUNTER_HEGEMONIC) | ❌ | RAG pipeline exists, corpus tagging doesn't |
| 3.5 — Player narrative-warfare verbs (JAM_SIGNAL / DISTRIBUTE_SAMIZDAT / CAPTURE_MEDIA / VIRAL_CAMPAIGN) | ❌ | |
| 3.6 Repression Logic — state verb taxonomy (INFILTRATE/RAID/PROSECUTE/LIQUIDATE w/ COINTELPRO double-bind) | ✅ | spec-039, `ooda/state_ai/`. Six verbs with sub-verbs, faction balance, escalation. |
| 3.6 — **ROE Tier state machine** (CIVIL_ORDER/STATE_OF_EXCEPTION/OPEN_WAR with verb gating + economic coupling) | ❌ | Legitimacy is a single scalar without tier transitions or hysteresis |
| 3.6 — Bad-jacketing (`edge.suspicion` on SOLIDARITY edges, `INTERNAL_PURGE`) | ❌ | |
| 3.6 — False-flag missions (Mission queue, trap types EXPOSURE/ATROCITY/SEIZURE/ARREST) | ❌ | |
| 3.6 — Snitch budget (lumpen recruitment via desperation, INFORMANT edge type) | ❌ | |
| 3.6 — Malinovsky Paradox (spy_labor_output vs intel_leak, MALINOVSKY_CONDITION event) | ❌ | |
| 3.7 State Attention — AttentionThread model, Sparrow centrality | ✅ | spec-039 + `ooda/attention/sparrow.py` |
| 3.7 — **Θ-budget enforcement** (Monitor=1Θ, Investigate=2Θ, Suppress=3Θ, QRF=allΘ) | ❌ | Only money budget is enforced |
| 3.7 — Expansion mechanics (Mass Surveillance Act / Algorithmic Policing / Emergency Powers as Faustian-bargain upgrades w/ agitation_floor + legitimacy_modifier) | ❌ | EMERGENCY_POWERS exists but has no thread-multiplier or rent-efficiency coupling |
| 3.7 — Saturation/DDoS detection (`Active_Threats/Effective_Threads`, `BLIND_SPOT_OPENED`) | ❌ | |
| 3.13 Synopticon/Lavender — DigitalDossier + risk scoring + Gospel targeting queue | ❌ | Centrality computed (Sparrow), but no risk-score scalar / strike queue / decoy mechanic |

**Estimated coverage: 3.3 ~5 % · 3.4 ~5 % · 3.5 ~15 % · 3.6 ~40 % · 3.7 ~50 % · 3.13 ~25 %**

#### Sub-Epoch 3D (Conflict): Kinetic, Balkanization, Doctrine, Strategy, Reactionary, Warlord

| Spec | Implemented? | Notes |
|---|---|---|
| Bifurcation routing (`route_agitation_to_ternary`) | ✅ | spec-043, `formulas/consciousness_routing.py` |
| EXCESSIVE_FORCE / UPRISING / SOLIDARITY_SPIKE / POWER_VACUUM / REVOLUTIONARY_OFFENSIVE / FASCIST_REVANCHISM (NPC mechanics) | ✅ | `engine/systems/struggle.py` |
| Heat dynamics + eviction pipeline + carceral necropolitics | ✅ | `engine/systems/territory.py` |
| Class Decomposition (LA → 30 % CARCERAL_ENFORCER + 70 % INTERNAL_PROLETARIAT) | ✅ | spec-001 + `engine/systems/decomposition.py` |
| State-internal faction balance (Finance-Capital/Security-State/Settler-Populist) | ✅ | spec-039, `ooda/state_ai/faction_dynamics.py` |
| Trap detection (Liberal/Ultra-Left/Rightist) | ✅ | `engine/trap_detection.py` (read-only diagnostic) |
| ATTACK API endpoint design | ⚠️ | spec-046 fully designed; **no engine implementation**. `ActionType.ATTACK_INFRASTRUCTURE` is an enum value with no resolver branch |
| **KineticSystem** (force power, success prob, blowback, QRF, isolation index, surgical vs blind) | ❌ | |
| **Reactionary Subject analysis layer** (Entitlement field, Chauvinism accumulation, FascistFactionSystem, `Fascist_Pull = Agitation·(E/(S+0.1))`, defection probability) | ❌ | Math substrate exists in §1; *analysis layer* doesn't |
| Fascist faction action verbs (POGROM / LOCKOUT / VIGILANTISM / RED_BROWN_COUP) | ❌ | |
| **Balkanization** (Faction entity, Sovereign entity, INFLUENCES/CLAIMS edges, ColonialStance UPHOLD/IGNORE/ABOLISH, ExtractionPolicy, sovereign collapse transitions) | ❌ | Zero code |
| Endgame outcomes for 3D (TRUE_LIBERATION / RED_OGV / FASCIST_VICTORY / FRAGMENTED_COLLAPSE) | ❌ | |
| **Doctrine Tree** (Tag system, DoctrineNode, Theoretical Labor resource, Party Congress, 4 trunks, traps liquidationism/adventurism, PatSoc Pipeline) | ❌ | MVP spec (`doctrine-tree-mvp.yaml`) and full spec (`doctrine-tree.yaml`) — both untouched in code |
| Strategy Layer trap mechanics (INSTITUTIONAL_DISSOLUTION / NETWORK_COLLAPSE / LABOR_ARISTOCRACY_CAPTURE trigger events, resource economy CL/SL/SOL/COH) | ❌ | Detection exists; trap-trigger events + economic costs don't |
| **Warlord Trajectory branching** (Trajectory A Classical / B Necropolitical / C Revolutionary, military vs local police split, prisoner_organization aggregator, enforcer_radicalization) | ❌ | Substrate (PENAL_COLONY territory + CARCERAL_ENFORCER role + DecompositionSystem) exists; branch selector doesn't |

**Estimated coverage: ~15–20 % overall for 3D**

---

## Part 2 — Top-Level ai-docs Drift Matrix

(Non-epoch YAMLs in `ai-docs/*.yaml`. Audit cross-referenced 17 files against the code.)

| File | Drift | Verdict |
|---|---|---|
| `theory.yaml` | LOW (paths only) | Conceptually current. Update `src/babylon/systems/formulas/` → `src/babylon/formulas/` everywhere. |
| `terminal-crisis.yaml` | NONE | Accurate. |
| `carceral-equilibrium.yaml` | NONE | Accurate. |
| `class-dynamics.yaml` | LOW (path only) | Accurate. ODE matches `formulas/class_dynamics.py`. |
| `shadow-labor-spec.yaml` | NONE | Recent (spec-005). Accurate. |
| `marxian-tensor-spec.yaml` | NONE | Recent (specs 011-016). Accurate. |
| `imperial-rent-spec.yaml` | LOW | Accurate baseline; Phase 2-5 (regional differentiation, World Bank/ILO, value-chain split, per-worker metrics) unbuilt. |
| `observer-layer.yaml` | MEDIUM | TopologyMonitor + 4-phase percolation accurate. Test counts (57, 144) outdated. Observer ecosystem now broader than spec. |
| `formulas-spec.yaml` | **HIGH** | "28 formulas / 11 modules" inventory is ~6 months stale. Reality: 17 modules, ~40 exported public functions (curvature, community, lifecycle, ternary consciousness, routing all added post-spec). |
| `topology-system.yaml` | MEDIUM | Percolation theory + metrics accurate; "Epoch 3 DuckDB" plan obsolete; scale assumption (10 nodes) gone (243K hexes now). |
| `entities.yaml` | MEDIUM | Core entity model preserved. Triple-Layer Trait System (flags/modifiers/properties) partially implemented; secret_* namespace + Fog-of-War filtering absent. New entities (Organization, Institution, OrganizationUnit, Substrate, KeyFigure, CommunityHyperedge) not listed. |
| `state-ai-algorithm.yaml` | **HIGH** | "StateSystem at `engine/systems/state.py`" was never built. Replaced by OODA-based design at `src/babylon/ooda/state_ai/` (spec-039). Threat-scoring formula, Thread allocation algorithm, behavioral biases (legibility_bias, institutional_inertia), DDoS strategy: **none implemented**. |
| `architecture.yaml` | HIGH (concepts current; stack rotated) | Embedded Trinity concept preserved. Each layer's implementation has rotated: Ledger SQLite → PostgreSQL; Topology NetworkX → GraphProtocol w/ adapters; Archive ChromaDB → pgvector. References to "10 Systems" out of date (21 now). DearPyGui presentation layer obsolete. |
| `game-loop-architecture.yaml` | HIGH (system list) | Concepts (Engine/State separation, Interceptor architecture) current. System list ("7 Systems") replaced by 21-system materialist-causality pipeline (spec-056). "1445 tests" stale. |
| `graph-abstraction-spec.yaml` | **HIGH (mostly superseded)** | GraphProtocol IS implemented (`engine/graph_protocol.py`) — but `PopFragment`/`OrganizationUnit`/`Chapter`/`Cell` hierarchy replaced by `_node_type` polymorphism. Signal/Effect pattern superseded by spec-032 OODA. DuckDB `ColumnarAdapter` never built. |
| `persistence-spec.yaml` | **SPLIT**: HIGH top / CURRENT bottom | JSON save/load with SHA-256 checksums + F5/F6/F7 hotkeys: never built; replaced by Postgres-driven persistence + Django web sessions. "Multi-Resolution Hex Journal" section (lines 411-513) is fully accurate (spec-037). |
| `database-spec.yaml` | **HIGH (obsolete)** | Entire `babylon.db` SQLite schema + 3-table DDL (social_classes/territories/relationships) gone. Reference data lives in `marxist-data-3NF.sqlite` (read-only); runtime state lives in PostgreSQL (spec-037). |

**Highest-priority files to retire or aggressively update**:
1. `database-spec.yaml` — write a "superseded by ADR037 + spec-037 + ADR040 + spec-062" header.
2. `state-ai-algorithm.yaml` — same, point to `src/babylon/ooda/state_ai/`.
3. `graph-abstraction-spec.yaml` — mark "superseded by current GraphProtocol implementation"; the design that survived is different from what's described.
4. `formulas-spec.yaml` — regenerate from `src/babylon/formulas/__init__.py` exports.
5. `epochs/epoch1-complete.md` — update system count to 21, list new systems added since 2026-01-05, note Spec 056 reorder.
6. `epochs/epoch2/pyqt-visualization.yaml` + `echarts-patterns.yaml` — mark "OBSOLETE — superseded by `web/frontend/` React stack (spec-041, spec-042)".
7. `epochs/epoch1/dpg-patterns.yaml` + `ui-wireframes.yaml` — already marked DEPRECATED (2026-02-01) but reference PyQt6 which is also gone now; update second-level deprecation.

---

## Part 3 — [SUPERSEDED] Initial 14-Spec Roadmap

> **The roadmap below was the initial MVP-scoped pass. It is preserved for traceability but is superseded by Part 3-FULL further down**, which expands every spec to full feature surface (no MVPs), adds 11 specs the initial audit missed (Music, Tutorial, Game-Data, RAG, TRPF, Synopticon, Strategy, Error-Recovery, Repro Tier 2/3, Resource Decay, State Verb Closure, Religious Topology, Prison Labor), and incorporates corrections from the second-pass audit.

## Part 3 — Recommended Implementation Roadmap for Epoch 3

Spec numbers 067-069 reserved per ADR044 follow-up plan (QCEW v2, BEA Input-Output, SQLite read caching). New gameplay specs start at 070. Below is the recommended dependency-aware sequence.

### Wave 1: Political Topology (unblocks 3D)

#### spec-070 — Balkanization (Faction + Sovereign + Collapse Transitions)

**Why first**: Independent in dependency terms; theoretically central ("you cannot build socialism on stolen land"); unblocks Reactionary Subject, Doctrine, Warlord Trajectory.

**What to build**:
- New entities: `Faction`, `Sovereign` (`models/entities/faction.py`, `sovereign.py`).
- New enums: `ColonialStance(UPHOLD/IGNORE/ABOLISH)`, `ExtractionPolicy(INTENSIFY/CONTINUE/CEASE)` in `models/enums/ideology.py`.
- New edge types: `INFLUENCES` (Faction → Territory), `CLAIMS` (Sovereign → Territory) in `models/enums/topology.py`.
- New systems (insert positions in `_DEFAULT_SYSTEMS`):
  - `FactionInfluenceSystem` (~position 14.5, after OODA, before Survival)
  - `SovereigntySystem` (~position 17.5, after Consciousness, before Contradiction)
  - `CollapseTransitionSystem` (~position 19.5, after FieldDerivative, before EdgeTransition)
- Formula module `formulas/balkanization.py`: `calculate_metabolic_impact(extraction_policy)`, `winning_faction_for_territory()`.
- New event types: `SOVEREIGN_COLLAPSE`, `TERRITORY_TRANSITION`, `FACTION_VICTORY`, `RED_OGV_ENDGAME`, `TRUE_LIBERATION_ENDGAME`, `FASCIST_VICTORY_ENDGAME`, `FRAGMENTED_COLLAPSE`.
- New `GameOutcome` values: `FASCIST_VICTORY`, `RED_OGV`, `TRUE_LIBERATION`, `FRAGMENTED_COLLAPSE`.
- Three starter factions seeded in `data/game/factions/seed_factions.json` (FAC_RESTORATIONIST, FAC_WORKERS_CONGRESS, FAC_DECOLONIAL).
- MetabolismSystem extension to apply `sovereign.metabolic_impact` to `territory.habitability`.

**Key formula**:
```
metabolic_impact = -0.02 (INTENSIFY) | -0.005 (CONTINUE) | +0.01 (CEASE)
territory.habitability += sovereign.metabolic_impact  # per tick
winning_faction = argmax(f, sum(INFLUENCES[f,t].influence_level for t))
```

**Complexity**: L (~60–90 h). **Touches**: 3 new systems · 2 new entity types · 2 new edge types · 7 events · 4 outcomes · seed JSON · MetabolismSystem extension.

**Dependencies**: None.

---

#### spec-071 — Reactionary Subject (Entitlement + Chauvinism + FascistFactionSystem)

**Why second**: Depends on 070's Faction model to assign drifted nodes to fascist faction; provides material for Doctrine NATIONALISM tag.

**What to build**:
- New fields on `SocialClass`: `entitlement: Intensity` (defaults: P=0.2, L_u=0.0, C_pb=0.7, C_la=0.8), `volatility: Intensity` (L_u default 0.8), `fascist_alignment: Intensity` (0.0→1.0 drift counter).
- Track `chauvinism: Intensity` on organization member records (specifically LA recruits).
- New system: `FascistFactionSystem` at ~position 17.5 (between Consciousness and Contradiction; coexists with SovereigntySystem from 070).
  - Per-tick for C_pb and C_la nodes: `Fascist_Pull = Agitation · (Entitlement / (Solidarity + 0.1))`. If > 1.0, `fascist_alignment += 0.05`, emit `FASCIST_DRIFT`. If ≥ 1.0, reassign node to fascist Faction.
  - For LA members of player orgs: accumulate Chauvinism (+0.01/tick base, +0.02 if super-waged); on CRISIS event, roll `P_defection = sigmoid(chi - D)`; if defects, fire `ORGANIZATIONAL_FRACTURE`. If >50 %, fire `RED_BROWN_COUP`.
- Volatility integration in `StruggleSystem`: L_u peripheral revolt gated on `V·(1-org_discipline)`.
- Fascist action verbs added to `ActionType` + resolved in OODA: `POGROM`, `LOCKOUT`, `VIGILANTISM`, `RED_BROWN_COUP` (auto-triggered).
- New events: `FASCIST_DRIFT`, `FASCIST_RECRUITMENT`, `ORGANIZATIONAL_FRACTURE`, `RED_BROWN_COUP`, `POGROM`, `LOCKOUT`, `VIGILANTISM`, `SPONTANEOUS_RIOT`.
- Formulas in `formulas/reactionary.py`: `calculate_fascist_pull`, `calculate_defection_probability`, `calculate_spontaneous_riot_risk`, `calculate_entitlement_effective`.

**Complexity**: L (~50–70 h).

**Dependencies**: 070 Balkanization (for fascist Faction target).

---

### Wave 2: Player Organizational Economy (unblocks 3D doctrine + game loop)

#### spec-072 — Vanguard Economy System

**Why**: Existing Organization + VanguardResources models are static. No system applies coherence checks, decay, or maintenance per tick. REPRODUCE/EDUCATE/MOBILIZE resolvers are `pass` stubs.

**What to build**:
- Formula module `formulas/coherence.py`:
  - `calculate_coherence_factor(cl, sl, k_coherence=0.1) -> Probability` — `sigmoid((cl/sl) / k)`.
  - `calculate_effective_output(sl, reputation, cf) -> float`.
  - `calculate_wasted_energy(sl, cf) -> float`.
- New system: `VanguardEconomySystem` (~position 14.5, after OODA, before Survival; coexists with FactionInfluenceSystem from 070).
  - Per-tick per org: refresh VanguardResources via `from_organization()`. Apply passive decay (burnout 0.02, defection 0.01, enthusiasm decay 0.03, reputation attention decay 0.05). Apply maintenance (0.1 CL/cadre under surveillance, 0.05 CL/cadre upkeep). If pending action: roll vs `coherence_factor`; on failure, trigger spontaneous-action consequences (heat spike, reputation crash, sympathizer loss).
- `VanguardDefines` model in `config/defines/vanguard.py` mirroring `vanguard-economy.yaml §game_defines` + `resource-sinks.yaml` rates.
- Flesh out `engine/actions/{reproduce,educate,mobilize,attack,investigate,negotiate,aid,move,campaign}.py` resolvers per spec-048 design (currently `pass`).
- New events: `COHERENCE_CRISIS`, `WASTED_ENERGY_SPILL`, `REPUTATION_CRASH`.

**Complexity**: L (~2–3 sprints). **Touches**: 1 new system · 4 new formulas · ~7 action resolvers · 3 events.

**Dependencies**: spec-031 Organization (DONE), spec-032 OODA (DONE), spec-048 verb endpoints (drafted).

---

#### spec-073 — Cohesion Mechanic (Iron Law of Oligarchy)

**Why**: The deepest organizational dynamics layer — entropy, factionalism, organizational split. Distinct from 072 (which handles per-action energy economy); this is per-tick org-state evolution.

**What to build**:
- Extend `Organization` with: `entropy: Intensity = 0.1`, `cadre_ratio: Probability = 0.15`, `member_count: int = 100`, `heat_accumulated: float = 0.0`.
- New system: `CohesionSystem` — runs AFTER SolidaritySystem, BEFORE ConsciousnessSystem (~position 8.5 or 9.5).
  - Three laws per tick:
    - Transmission: `effective_solidarity = min(s, min(c_src, c_tgt))`; `heat = s - effective`.
    - Scale: `entropy_delta = base_rate · log(N+1) · (1 - cadre_ratio)`.
    - Decay: `cohesion_delta = regeneration - entropy · decay_coef`.
  - Trigger `ORGANIZATIONAL_SPLIT` when `cohesion < 0.2 AND crisis_active` — fork node into `_Revisionist` + `_UltraLeft` w/ severed SOLIDARITY and new HOSTILITY edge.
  - Trigger `ORGANIZATIONAL_COLLAPSE` when `cohesion < 0.1 AND entropy > 0.8`.
- Modify `SolidaritySystem` to apply Transmission Law.
- Modify `ConsciousnessSystem` so entropy amplifies drift confusion.
- Three new player actions in `engine/actions/`:
  - `mass_recruitment.py` — N×1.5, entropy +0.15, cohesion −0.10, cadre_ratio −0.05.
  - `rectification.py` — N×0.8, entropy −0.25, cohesion +0.20, cadre_ratio +0.08.
  - `political_education.py` — cohesion_regen +0.05, cadre_ratio +0.02, entropy −0.05.
- Topology monitor: weight percolation by cohesion so phase transitions depend on *effective* solidarity.
- New events: `ORGANIZATIONAL_SPLIT`, `ORGANIZATIONAL_COLLAPSE`, `RECTIFICATION_STARTED`, `MASS_RECRUITMENT`, `FACTIONALISM_WARNING`, `HEAT_GENERATED`.

**Complexity**: L. Node-split (one node → two w/ edge migration) is the load-bearing complexity.

**Dependencies**: spec-031 Organization (DONE), spec-034 ternary consciousness (DONE for the entropy-amplifies-drift coupling).

---

#### spec-074 — Demographic Crisis & Resolution Pathway Selector

**Why**: Closes the necropolitical-fascism feedback loop already half-built in TerritorySystem. Connects MetabolismSystem output to political branching.

**What to build**:
- Formulas in `formulas/demographics.py`:
  - `calculate_consumption_balance(B_global, total_consumption) -> Currency`.
  - `calculate_class_reproduction_cost(class_pop, s_class) -> Currency`.
  - `select_resolution_pathway(deficit, imperial_rent_pool, core_consciousness, periphery_consciousness) -> ResolutionPathway`.
- New `ResolutionPathway` enum: `FASCIST`, `SOCIALIST`, `IMPERIAL`, `NONE`.
- New system: `DemographicsSystem` (~position 13.5, after Metabolism).
  - Aggregate `Sum(pop · (s_bio + s_class))` from active SocialClass entities.
  - Compute `consumption_balance = total_biocapacity - total_consumption`.
  - If `balance < -CRISIS_THRESHOLD` (default −0.3): emit `DEMOGRAPHIC_CRISIS`.
  - Run resolution decision tree from `demographics-spec.yaml` lines 451-456.
  - Apply chosen pathway: FASCIST sets `s_bio=0` on selected PERIPHERY territories; SOCIALIST reduces `s_class` on BOURGEOISIE; IMPERIAL transfers biocap stock from periphery to core.
- New events: `DEMOGRAPHIC_CRISIS`, `NECROPOLITICS_ACTIVE`, `REDISTRIBUTION_ACTIVE`, `IMPERIAL_EXTRACTION_INTENSIFIED`.

**Complexity**: M (~1–2 sprints).

**Dependencies**: MetabolismSystem (DONE), ImperialRentSystem (DONE), carceral geography (DONE), spec-070 Balkanization (for IMPERIAL pathway's biocap-transfer along EXPLOITATION edges).

---

### Wave 3: Player Action Verbs (3D Conflict + 3C Information)

#### spec-075 — Kinetic Warfare (ATTACK Verb Engine)

**Why**: ATTACK API is fully designed (spec-046); engine lift is most-defined of all unimplemented 3D features.

**What to build** (per `kinetic-warfare.yaml` + spec-046):
- New models in `models/entities/attack.py`:
  - `AttackingForce(cadre_count, sympathizer_count, preparation_level, extraction_plan)`.
  - `AttackOutcome(success, damage_ratio, c_destroyed, wealth_destroyed, s_flow_disruption, collateral_wealth_loss, heat_generated, opsec_exposure)`.
- `TargetType` enum: `EXTRACTION`, `CIRCULATION`, `REALIZATION` in `models/enums/territory.py`.
- New Territory fields: `security_rating`, `collateral_risk`, `strategic_value`, `target_type`, `last_attack_tick`, `qrf_response_time`.
- `AttackDefines` in `config/defines/kinetic.py` per spec-046 lines 691-774: `targeted_cl_cost=4.0`, `mass_sl_cost=15.0`, `c_destruction_rate=0.3`, `flow_disruption_rate=0.5`, `heat_per_damage=1.0`, `collateral_fraction=0.15`, `opsec_base_exposure=0.3`, `warsaw_ghetto_threshold=0.05`.
- Formulas in `formulas/kinetic.py`:
  - `Force_Power = cadres·10 + sympathizers`
  - `Effective_Force = Force_Power · cohesion · (1 - entropy·0.5)`
  - `Success_Prob = clamp(Effective/(Security·100) + Preparation·0.3, 0.05, 0.95)`
  - `Blowback = collateral_risk · damage · (1 - 0.8·surgical)`
  - `Isolation_Index = Heat / max(public_support, 0.01)`
- New system: `KineticSystem` at position 14.5 (between OODA and Survival).
  - Reads queued attacks from `context.persistent_data["pending_attacks"]`.
  - Dispatches to `resolve_attack()` → `trigger_qrf()` for REALIZATION targets.
  - Applies wealth/c destruction + edge severing + heat + collateral + OPSEC exposure.
- New events: `ATTACK_CONDUCTED`, `COLLATERAL_DAMAGE`, `QRF_ENGAGEMENT`, `TOTAL_PARTY_KILL`, `ISOLATION_THRESHOLD_BREACHED`, `EXTRACTION_NODE_DISABLED`, `CIRCULATION_EDGE_SEVERED`.
- Helper on GraphProtocol consumers: `sever_edge_temporarily(source, target, edge_type, recovery_ticks)`.

**Complexity**: **XL** (~80–120 h). 6 new event types, full QRF + blowback + isolation tracking + surgical/blind branching.

**Dependencies**: spec-072 Vanguard Economy (for CL/SL/Coherence inputs to Force_Power), spec-073 Cohesion (for cohesion/entropy modifiers), spec-046 ATTACK API (drafted).

---

#### spec-076 — Fog of War & Intel Layer

**Why**: Mirrors the state-side attention threads (spec-039) with a player-side intel layer. Required for the player to make any informed decision.

**What to build**:
- New Territory fields: `mass_receptivity`, `intel_confidence`, `masked_attributes: dict[str, Any]`.
- Formulas in `formulas/intelligence.py`:
  - `Mass_Receptivity M_r = (1 - P(S|A)) · I_a · C_f`
  - `Intel_Confidence I_c = B_o + (C_p · M_r)`
  - `decay_rate(M_r) = 0.01 (Water, M_r≥0.8) | 0.05 (Mud, 0.2≤M_r<0.8) | 0.20 (Desert, M_r<0.2)`
- Class Factor lookup table: P_w=1.0, L_u=1.0, C_pb=0.3, C_la=0.2.
- New system: `IntelligenceSystem` (~position 15.5, after Survival, before OODA).
  - Compute M_r per territory.
  - Update I_c and apply decay.
  - Maintain a `PlayerIntelLayer` (`models/intel_layer.py`) — per-territory snapshot of what the player can see vs true state.
  - In Desert mode (`M_r < 0.2`): generate falsified `masked_attributes` (plausible but false values for agitation, organization_strength, hostile_threats).
- Player actions (fill out stubs in `engine/actions/`):
  - `agitate_locally.py` — +0.05 ideological_alignment, costs 5 CL, +0.02 state_attention (+0.2 in Desert).
  - `social_investigation.py` — +0.2 intel_confidence, reveals one hidden attribute, requires `M_r ≥ 0.3`.
  - `establish_contact_network.py` — persistent intel network, requires `M_r ≥ 0.5` + prior social_investigation, reduces decay to 0.01.
  - Backfill `resolve_investigate` (currently `pass`).
- New events: `SECURITY_BREACH`, `NETWORK_COMPROMISE`, `INTEL_DECAY`, `AMBUSH`.
- Integration with state attention: cadre presence in low-M_r territory feeds `target_scores` in `allocate_threads`.
- UI confidence indicators (frontend task): solid / `~` / `?` / no-warning prefixes.

**Complexity**: L. Mask-generation logic is game-design subtle.

**Dependencies**: spec-039 state attention (DONE — mirror needs this), spec-034 ternary consciousness (DONE).

---

#### spec-077 — Gramscian Hegemony System (player narrative warfare)

**Why**: MVP dual-narrative LLM director exists; full hegemony resource, RAG corpus split, and four player verbs are absent.

**What to build**:
- New WorldState fields: `hegemony: Probability = 0.7`, `corporate_reach: dict[TerritoryId, Probability]`, `liberated_reach: dict[TerritoryId, Probability]`.
- New system: `HegemonySystem` (~position 17.6, after ConsciousnessSystem and FascistFactionSystem).
  - `Hegemony_Delta = (stability · media_control) - (crisis_visibility · counter_action)`.
  - High Hegemony (>0.7) accelerates acquiescence drift; low Hegemony (<0.3) accelerates revolutionary drift.
- Extend `NarrativeDirector`:
  - Add `INTEL` channel (deterministic structured-data dump, no LLM) alongside `CORPORATE` + `LIBERATED`.
  - Add `WireEntry` model in `models/wire.py` storing all three narrative versions per significant event.
  - Add Manufacturing-Consent linguistic-pattern dictionaries (euphemism maps, lines 165-175 of spec).
- RAG corpus split (`rag/rag_pipeline.py`):
  - Add `corpus_id` parameter to `query()`.
  - Define `HEGEMONIC_CORPUS` (WSJ-style sources) and `COUNTER_HEGEMONIC_CORPUS` (Marx, Lenin, Fanon).
- Four player actions in `engine/actions/`:
  - `jam_signal.py` — hegemony −0.05/tick for 5 ticks; corporate_reach[territory] −0.20; heat +0.15.
  - `distribute_samizdat.py` — consciousness_drift +0.02/tick; liberated_reach[territory] +0.10; permanent until decay.
  - `capture_media_node.py` — hegemony −0.15 permanently; requires territory control + organization > 0.5.
  - `viral_campaign.py` — instant hegemony −0.10; consciousness_spike +0.15 on connected nodes; 20-tick cooldown.
- New events: `HEGEMONY_SHIFT`, `MEDIA_CAPTURED`, `JAMMING_DETECTED`, `VIRAL_BREAKTHROUGH`.

**Complexity**: L.

**Dependencies**: spec-039 state PROPAGANDIZE (DONE — needs hegemony coupling); RAG pipeline (DONE — needs corpus tagging); spec-073 Cohesion (optional for solidarity-based viral propagation).

---

#### spec-078 — Repression Logic Full (ROE Tiers + COINTELPRO + Malinovsky + Snitch Budget)

**Why**: Largest spec (54 KB). spec-039 covered ~40 %; ROE tier state machine + COINTELPRO bad-jacketing + false flags + snitch budget + Malinovsky paradox all missing.

**Decompose into 5 user stories** (each independently testable):

**US1 — ROE Tier State Machine**:
- `ROETier` enum (`CIVIL_ORDER`, `STATE_OF_EXCEPTION`, `OPEN_WAR`) in `models/enums/state.py`.
- `RepressionState` model in `models/entities/repression_state.py`: `legitimacy` (0-100 or rescaled to [0,1]), `current_tier`, `repression_budget`, `intel_level`, `active_infiltrators`, `snitch_network_size`, `tier_buffer_active`.
- Tier-gated verb availability in `RuleBasedStateAI._generate_candidates`:
  - CIVIL_ORDER: exclude RAID, LIQUIDATE, SCORCHED_EARTH.
  - STATE_OF_EXCEPTION: allow RAID + PROSECUTE; LIQUIDATE only if EMERGENCY_POWERS active.
  - OPEN_WAR: all verbs available; ADMINISTER/CO_OPT near-zero effect.
- Tier transition events with 5-point hysteresis buffer: `LEGITIMACY_CRISIS` (down), `LEGITIMACY_RECOVERY` (up).
- Economic coupling: `ImperialRentSystem` reads tier — efficiency `1.0 / 0.75 / 0.0`, capital_flight `0.0 / 0.25 / 1.0`.

**US2 — Bad-jacketing**:
- Add `suspicion: float` to SOLIDARITY edge attributes.
- New resolver `resolve_bad_jacket(edge, intel_budget, defines)` in `ooda/state_ai/repress_effects.py`:
  - `cost = base · edge.solidarity_strength`
  - `paranoia_factor = 1 + (1 - cell_discipline)`
  - `suspicion_delta = injection_rate · paranoia_factor`
  - If `edge.suspicion > edge.solidarity_strength`: remove edge, emit `INTERNAL_PURGE`.
- New REPRESS sub-verb `BAD_JACKET`.
- Counter-measure: `transparency_culture` flag on Organization (decays suspicion 10%/tick).

**US3 — False-flag missions**:
- `Mission` model in `models/entities/mission.py`: `is_false_flag`, `trap_type` (EXPOSURE/ATROCITY/SEIZURE/ARREST), `presented_value`, `actual_value`.
- Mission queue on Organization.
- Resolver `generate_false_flag(infiltrator, target_org)` — when INFILTRATOR edge exists, state injects false missions.
- Detection: `detection_chance = base + discipline·0.5 + ci_investment·0.3`.
- Events: `FALSE_FLAG_PROPOSED`, `FALSE_FLAG_EXPOSED`, `FALSE_FLAG_SPRUNG`.

**US4 — Snitch budget**:
- New edge type `INFORMANT` (Population → State, one-way).
- Resolver `recruit_snitches(lumpen, budget)`:
  - For LUMPEN node: `desperation = (1 - wealth/subsistence) · (1 - class_consciousness)`.
  - Recruit if `desperation > 0.6` with chance `desperation · recruitment_effectiveness`.
  - Cost: `payment_per_informant = 50`.
- Per tick: each INFORMANT edge reveals nearby SOLIDARITY edges to `state.intel_level`.
- Reliability decay 0.1/tick; expose 2 %/tick.
- Events: `INFORMANT_RECRUITED`, `INFORMANT_EXPOSED`, `INTEL_GATHERED`.

**US5 — Malinovsky Paradox**:
- `Infiltrator` model in `models/entities/infiltrator.py`: id, target_cell_id, competence, cover_integrity, intel_gathered, labor_contributed, deployed_tick, status.
- `process_infiltrator(infiltrator, cell)` resolver:
  - `labor_output = discipline · competence · cover_factor`
  - `intel_leak = (1-discipline) · competence · extraction`
  - `net_value = labor_output - intel_leak · intel_value`
  - If `net > 0`: emit `MALINOVSKY_CONDITION`.
  - `exposure_risk = discipline · exposure_rate`.
- Extraction mechanic: state burns infiltrator for max damage at `cover_integrity < 0.3`.
- Events: `MALINOVSKY_CONDITION`, `INFILTRATOR_SUSPECTED`, `SPY_EXPOSED`, `INFILTRATOR_EXTRACTED`.

**Complexity**: **XL** (largest spec; 5 cross-coupled sub-systems). Estimate ~3–4 months.

**Dependencies**: spec-039 (DONE), spec-031 Organization w/ discipline/cohesion (mostly DONE).

---

#### spec-079 — Panopticon Economy (State Attention Θ-budget)

**Why**: Threads + Sparrow exist; Θ-budget enforcement, expansion mechanics, saturation/DDoS detection all missing.

**What to build**:
- `StateAttention` model in `models/entities/state_attention.py`:
  - Fields: `threads: int = 2`, `surveillance_acts: int = 0`, `algorithmic_systems: int = 0`, `emergency_active: bool`, `emergency_ticks_remaining: int`.
  - Computed: `effective_threads`, `agitation_floor = 0.1·surveillance_acts + 0.05·algorithmic`, `legitimacy_modifier = -0.2·algorithmic - 0.3·emergency`.
- Per-verb thread costs `_THREAD_COSTS` in `ooda/state_ai/decision.py`:
  - Monitor (SURVEIL): 1Θ
  - Investigate (INFILTRATE w/ provocateur): 2Θ
  - Suppress (RAID-TARGETED): 3Θ
  - QRF Strike (RAID-MASS): all-Θ
- Modify `RuleBasedStateAI.select_action` to enforce thread budget alongside money.
- New system: `PanopticonSystem` (~position 14.6, after OODA, before Kinetic).
  - Compute saturation = `active_threats / effective_threads`.
  - Emit `BLIND_SPOT_OPENED` when saturation > 1.0.
  - Apply `agitation_floor` permanently to all territories.
- Three new LEGISLATE sub-actions:
  - `MASS_SURVEILLANCE_ACT` → `surveillance_acts +=1`, `threads +=2`, `agitation_floor +=0.1`.
  - `ALGORITHMIC_POLICING` → `algorithmic_systems +=1`, free Monitor +1, `legitimacy -=20`.
  - `EMERGENCY_POWERS` (exists) → `threads ×2` for 5 ticks, `imperial_rent_efficiency ×0.5`.
- Auto-allocate "noise threats" via priority queue (pseudocode in `state-attention-economy.yaml` lines 567-590).
- Events: `THREAD_SATURATION`, `BLIND_SPOT_OPENED`, `EXPANSION_PASSED`, `MARTIAL_LAW_DECLARED`, `MARTIAL_LAW_LIFTED`.

**Complexity**: M-L.

**Dependencies**: spec-039 (DONE), spec-078 ROE tiers (recommended for full economic coupling).

---

### Wave 4: Strategic Choice (Doctrine + Endgames)

#### spec-080 — Doctrine Tree MVP (3 trunks · 3 tags · 15 nodes)

**Why**: Ideological tech tree gates player verbs and creates branching strategy. Start with MVP scope (`doctrine-tree-mvp.yaml`) not full (`doctrine-tree.yaml`).

**What to build**:
- Theoretical Labor resource: add `theoretical_labor: float` to organization. Per-tick gen: `TL = cadre_count · study_allocation · coherence_factor`. New OODA action `STUDY` (1 AP, no target).
- `Tag` enum: MVP `CLASS_ANALYSIS`, `MASS_LINK`, `MILITANCY`.
- `DoctrineNode` + `DoctrineTree` models.
- Per-org `doctrine_tree: DoctrineTree`.
- New system: `DoctrineSystem` (~position 17.7, after Consciousness/Hegemony, before Contradiction).
  - Regenerate TL; recompute tags from acquired nodes; check trap conditions; fire trap events.
- New OODA action `ADVANCE_DOCTRINE` with `node_id` param.
- Tag-based action gating in `action_eligibility.py`:
  - `KINETIC_ATTACK` requires `MILITANCY ≥ 4`.
  - `MASS_MOBILIZATION` requires `MASS_LINK ≥ 5`.
- 15-node MVP tree in `data/game/doctrine_tree_mvp.json` per `doctrine-tree-mvp.yaml` lines 105-300:
  - `class_consciousness` → `trade_unionism` → three branches:
    - `electoral_socialism` → `liquidationism` trap (if CLASS_ANALYSIS ≤ 0 AND MILITANCY ≤ 0)
    - `democratic_centralism` → `united_front` goal
    - `armed_vanguard` → `adventurism` trap (if MASS_LINK ≤ 0)
- Events: `DOCTRINE_ACQUIRED`, `DOCTRINE_TRAP_TRIGGERED`, `LIQUIDATIONISM_TRAP`, `ADVENTURISM_TRAP`, `UNITED_FRONT_ACHIEVED`.

**Phase 2 (full spec, deferred to spec 084+)**: LEGALITY/SECRECY/RESILIENCE/NATIONALISM tags; Autonomist trunk; Party Congress action (trunk_shift, rectification, theoretical_offensive, self_criticism); maintenance/decay mechanics; PatSoc Pipeline.

**Complexity**: L for MVP (~50-70 h). XL for full (deferred).

**Dependencies**: spec-072 Vanguard Economy (CL/coherence inputs to TL generation); spec-070 Balkanization (for colonial_stance filtering of trunks); spec-071 Reactionary Subject (for NATIONALISM tag meaning in full spec).

---

#### spec-081 — Warlord Trajectory Branching

**Why**: Substrate (PENAL_COLONY + CARCERAL_ENFORCER + DecompositionSystem) exists. Branch selector + military/police split don't.

**What to build**:
- State apparatus refactor: split monolithic `StateApparatus` into `MILITARY` (federal loyalty) + `LOCAL_POLICE` (territorial loyalty). Significant schema change.
- New system: `WarlordTrajectorySystem` (~position 19.5).
  - Per-tick when terminal-crisis conditions met:
    - `bourgeois_solvency = C_b_wealth > payment_threshold`
    - `military_loyalty = f(ideology_strength, payment_history)`
    - `revanchist_cohesion = f(police_organization, petitb_alignment, la_decomposition)`
    - `settler_consciousness = f(territory_heat, racial_hierarchy_strength)`
    - `prisoner_organization = avg(organization for PENAL_COLONY-resident SocialClasses)`
    - `enforcer_radicalization = solidarity_transmission(enforcers, prisoners)`
  - Branch per `warlord-trajectory.yaml` lines 151-171:
    - A: bourgeois solvent + military loyal → Classical Concentration
    - B: revanchist cohesion + settler consciousness high → Necropolitical Prison-Plantation
    - C: prisoner_org ≥ 0.5 OR enforcer_radicalization > threshold → Revolutionary Rupture
    - Else: Contested Collapse
- New `GameOutcome` values: `TRAJECTORY_A_CLASSICAL`, `TRAJECTORY_B_WARLORD`, `TRAJECTORY_C_REVOLUTION`, `CONTESTED_COLLAPSE`.

**Complexity**: L. State apparatus refactor is the heaviest piece.

**Dependencies**: spec-070 Balkanization (factional sovereignty model needed for endgame attribution).

---

### Wave 5: Cleanup & Loop Closure

#### spec-082 — Reproductive Labor Tier-1 + S_imperial Explicit Accounting

**Why**: Small surgical change that closes the Imperial Rent → labor-aristocracy subsidy feedback loop.

**What to build**:
- Add fields to `EconomyDefines`: `core_subsistence_floor = 0.08`, `periphery_subsistence_floor = 0.02`, `regeneration_rate = 0.01`, `solidarity_regeneration_bonus = 0.005`.
- Modify `ImperialRentSystem._process_extraction_phase`: cap extraction at `worker.wealth - subsistence_floor`. Track `crisis_pressure` for unextracted amount.
- New system: `ReproductionSystem` between ImperialRent (pos 9) and DispossessionEvents (pos 10).
  - Per tick per worker: `solidarity_count = count_solidarity_edges(worker)`. `regen = base_rate + solidarity_count · solidarity_bonus`. `wealth = min(wealth + regen, subsistence_floor)`.
- Add `s_imperial: Currency` to `SocialClass`. Modify `ImperialRentSystem._process_subsidy_phase` to write s_imperial to LA recipients. When imperial_rent_pool depletes, decrement s_imperial; once 0, effective s_class drops to unsubsidized → triggers SUPERWAGE_CRISIS (already exists).

**Complexity**: S (~3-5 days).

**Dependencies**: None blocking.

---

#### spec-083 — Political Economy of Liquidity (Fiscal + Fundraising + Precarity Systems)

**Why**: Closes the master feedback loop: imperial rent → state budget → debt → inflation → real wages → precarity → consciousness.

**What to build** (three systems in one spec):
- `FiscalSystem` (state side):
  - Compute burn_rate; collect `tax_revenue = bourgeoisie_wealth · tax_rate · collection_efficiency`; add tribute_income from CLIENT_STATE edges; if revenue < burn_rate, issue debt up to ceiling else trigger austerity_crisis; update `inflation_index = 1 + (debt_level/debt_ceiling) · inflation_sensitivity`.
- `FundraisingSystem` (org side):
  - Per revolutionary org: collect dues, process expropriation actions (heat), donor income (drift), heat decay, drift threshold checks.
- `PrecaritySystem` (population side):
  - For each SocialClass: compute `real_wage` from PrecarityState, update `precarity_index`, feed into ConsciousnessSystem drift modifier. Trigger `EventType.PROLETARIANIZATION` when real_wage < proletarian_threshold for LA.
- New events: `FISCAL_CRISIS`, `ORGANIZATION_SPLIT` (renamed to avoid clash with cohesion's), `PROLETARIANIZATION`, `HYPERINFLATION`.
- Add `ActionType.EXPROPRIATION` to `enums/actions.py`.

**Complexity**: L (~2-3 sprints). Three new systems, 4 new event types, ConsciousnessSystem integration.

**Dependencies**: spec-072 Vanguard Economy (war_chest accounting interop), models (DONE).

---

## Part 4 — Dependency Graph

```mermaid
flowchart TD
    A[Existing substrate:&lt;br/&gt;21 systems, formulas,&lt;br/&gt;spec 039 state AI,&lt;br/&gt;spec 031/032/040 orgs/OODA/inst,&lt;br/&gt;spec 062 cross-scale,&lt;br/&gt;spec 066 marx coherence]

    A --&gt; S070[spec-070&lt;br/&gt;Balkanization]
    A --&gt; S072[spec-072&lt;br/&gt;Vanguard Economy]
    A --&gt; S082[spec-082&lt;br/&gt;Repro Labor + S_imperial]

    S070 --&gt; S071[spec-071&lt;br/&gt;Reactionary Subject]
    S070 --&gt; S074[spec-074&lt;br/&gt;Demographic Crisis]
    S070 --&gt; S081[spec-081&lt;br/&gt;Warlord Trajectory]

    S072 --&gt; S073[spec-073&lt;br/&gt;Cohesion Mechanic]
    S072 --&gt; S075[spec-075&lt;br/&gt;Kinetic Warfare]
    S072 --&gt; S080[spec-080&lt;br/&gt;Doctrine Tree MVP]

    S071 --&gt; S075
    S073 --&gt; S075

    A --&gt; S076[spec-076&lt;br/&gt;Fog of War]
    A --&gt; S079[spec-079&lt;br/&gt;Panopticon Economy]
    S076 --&gt; S077[spec-077&lt;br/&gt;Gramscian Hegemony]
    S079 --&gt; S078[spec-078&lt;br/&gt;Repression Logic Full]

    S072 --&gt; S083[spec-083&lt;br/&gt;Political Economy of Liquidity]
    S082 --&gt; S083
```

**Critical path (longest-dependency chain to a playable Epoch 3)**:
`spec-070 → spec-071 → spec-075 → spec-081` (Balkanization → Reactionary → Kinetic → Warlord)

This is ~280–350 hours of focused work.

---

## Part 5 — Doc Hygiene Recommendations

### Mark OBSOLETE / superseded (add header banner)

1. `ai-docs/database-spec.yaml` — superseded by ADR037 + spec-037 + ADR040 + spec-062.
2. `ai-docs/state-ai-algorithm.yaml` — superseded by spec-039 (`src/babylon/ooda/state_ai/`).
3. `ai-docs/graph-abstraction-spec.yaml` — partially superseded (GraphProtocol exists but model differs).
4. `ai-docs/persistence-spec.yaml` (top section, save/load UI) — superseded by spec-037/spec-061. Bottom section (multi-resolution hex journal) is fine.
5. `ai-docs/epochs/epoch1/dpg-patterns.yaml` — already deprecated for PyQt6; PyQt6 is also gone now. Mark "double-deprecated; live UI is React + Django at `web/frontend/`".
6. `ai-docs/epochs/epoch1/ui-wireframes.yaml` — same.
7. `ai-docs/epochs/epoch1/synopticon-spec.yaml` — diffused into `engine/observers/` + `topology_monitor.py` + `ai/director.py`. Mark "design diffused; named primitives never built".
8. `ai-docs/epochs/epoch2/pyqt-visualization.yaml` — superseded by React stack (spec-041 / spec-042 / spec-061).
9. `ai-docs/epochs/epoch2/echarts-patterns.yaml` — superseded by Recharts in `web/frontend/`.
10. `ai-docs/decisions/ADR027_frontend_stack.yaml` (NiceGUI native) — superseded by Django + React; ADR not formally retracted.
11. `ai-docs/decisions/ADR029_hybrid_graph_architecture.yaml` (KuzuDB) — superseded by ADR030 unified SQLite, then by spec-037 PostgreSQL.
12. `ai-docs/decisions/ADR030_unified_sqlite_runtime.yaml` — superseded by spec-037 PostgreSQL runtime (hybrid: SQLite-as-reference + PG-as-runtime).
13. `ai-docs/decisions/ADR034_deferred_rag_architecture.yaml` (ChromaDB) — `rag_pipeline.py` comments now say "ChromaDB removed; use PgVectorStore".

### Update with current state

14. `ai-docs/epochs/epoch1-complete.md` — system count 13 → 21; list new systems (ProductionSystem, TickDynamicsSystem, ReserveArmySystem, CommunitySystem, LifecycleSystem, DispossessionEventSystem, SubstrateSystem, OODASystem, ContradictionFieldSystem, FieldDerivativeSystem, EdgeTransitionSystem). Note Spec 056 materialist-causality reorder; EndgameSystem → EndgameDetector observer; EventTemplateSystem orphaned.
15. `ai-docs/formulas-spec.yaml` — regenerate from `src/babylon/formulas/__init__.py`. Add curvature, community, lifecycle, ternary consciousness, routing.
16. `ai-docs/architecture.yaml` — update Embedded Trinity layer implementations: Ledger=PG, Topology=NetworkX-via-GraphProtocol, Archive=pgvector. Update system count.
17. `ai-docs/game-loop-architecture.yaml` — system list "7 Systems" → 21-system materialist-causality pipeline.
18. `ai-docs/decisions/index.yaml` — index is stale; ADRs 021-025, 030-044 are not listed but their files exist.
19. `ai-docs/entities.yaml` — add Organization, Institution, OrganizationUnit, Substrate, KeyFigure, CommunityHyperedge entity types.
20. `ai-docs/topology-system.yaml` — DuckDB future is gone; 10-node scale assumption gone (243K hexes now).
21. `ai-docs/observer-layer.yaml` — refresh test counts and observer ecosystem.

### Keep as-is (accurate)

- `ai-docs/theory.yaml` (path updates only)
- `ai-docs/terminal-crisis.yaml`
- `ai-docs/carceral-equilibrium.yaml`
- `ai-docs/class-dynamics.yaml`
- `ai-docs/shadow-labor-spec.yaml`
- `ai-docs/marxian-tensor-spec.yaml`
- `ai-docs/imperial-rent-spec.yaml`
- `ai-docs/persistence-spec.yaml` (hex journal section only)
- `ai-docs/ontology.yaml`
- `ai-docs/mantras.yaml`
- `ai-docs/anti-patterns.yaml`
- `ai-docs/patterns.yaml`
- `ai-docs/pydantic-patterns.yaml`
- `ai-docs/documentation-standards.yaml`
- `ai-docs/tuning-standard.yaml`
- `ai-docs/exceptions-architecture.yaml`
- `ai-docs/tooling.yaml`
- `ai-docs/ci-workflow.yaml`

---

## Part 6 — Quick Reference Files

**Key engine code paths** (verified current):
- `src/babylon/engine/simulation_engine.py:319-345` — `_DEFAULT_SYSTEMS` (21-system materialist-causality pipeline)
- `src/babylon/engine/systems/` — 21 system implementations
- `src/babylon/engine/graph_protocol.py` — 18-method protocol
- `src/babylon/engine/observer.py` — `SimulationObserver` Protocol
- `src/babylon/engine/topology_monitor.py:273` — percolation phase detection
- `src/babylon/engine/observers/{endgame_detector,metrics,session_recorder,persistence,causal,economic,schema_validator}.py`
- `src/babylon/formulas/` — 17 modules, ~40 exported public functions
- `src/babylon/persistence/{postgres_runtime/,pgvector_store.py,runtime_schema.py,conservation_audit.py,hex_init.py,hex_state.py,trace_recorder.py,archival.py}` — Postgres runtime (spec-037 + spec-062)
- `src/babylon/reference/schema.py` — 86+ SQLAlchemy ORM models, 3NF schema
- `src/babylon/economics/{tensor.py,hydrator.py,department_mapper.py,shadow_labor.py,lifecycle/,melt/,gamma/}` — Marxian economic infrastructure
- `src/babylon/ooda/state_ai/` — spec-039 State Apparatus AI (~2744 LOC)
- `src/babylon/organizations/`, `src/babylon/institution/` — spec-031 + spec-040 entity systems
- `src/babylon/ai/director.py:42-73,228-237` — dual-narrative LLM director (MVP Wire)
- `web/frontend/` — React 19 + Vite + Django + deck.gl frontend (specs 041, 042, 061)
- `data/sqlite/marxist-data-3NF.sqlite` — 8.79 GB read-only reference DB
- `/media/user/data/babylon-data/` — out-of-tree data trove (QCEW, LODES, Census, FCC, FAF, TIGER, energy)

**Critical ADRs to read for context**:
- ADR016 — Fascist Bifurcation (the theoretical core)
- ADR029 → ADR030 → spec-037 (storage evolution)
- ADR037 — orphan schemas + test skip remediation (the big cleanup pass)
- ADR039 — spec-061 backend wireup (DearPyGui → React/Django pivot)
- ADR040 — spec-062 cross-scale integration
- ADR042 — spec-065 engine bridging
- ADR043 — spec-066 ideology baseline placeholder
- ADR044 — spec-066 engine integration into bridged runner

---

## Closing notes

The project has done substantially more *materialist substrate* work than the Epoch 3 docs anticipated (~60-70% of 3A built quietly through specs 011-040, 062-066). What remains is concentrated and high-leverage: **the gameplay loop** — player verbs, faction politics, doctrine choice, branching endgames. The 13-spec roadmap above ships that gameplay loop in roughly 4 waves over 6-12 months of focused work, with `spec-070 Balkanization` as the single highest-leverage starting point because it's independent, theoretically central, and unblocks four downstream specs.

The documentation-side reality is sharper: the top-level YAMLs partition cleanly into "accurate and recent" (specs 005, 011-024, 030-044 era) vs "Epoch 1→2 Bridge era 2025-12 / 2026-01" (highly drifted). A doc-hygiene sweep marking the latter as superseded with pointers to the actual code paths would close the gap between aspiration and reality without needing to rewrite anything.

---

## Part 3-FULL — Full-Vision Implementation Roadmap (Supersedes Part 3)

**Reframing**: The user views the *full feature surface* of every Epoch 3 spec as their minimum viable plan. The 14-spec MVP-scoped roadmap in Part 3 is replaced by the 27-spec full-vision catalog below.

### Second-pass corrections to Part 3

Five parallel agents reread the specs Part 3 either skipped or under-scoped (music-system, tutorial-design, game-data, rag-architecture, doctrine-tree FULL, synopticon FULL, strategy-layer FULL, error-recovery, epoch2-persistence, epoch2-trpf, reproductive-labor Tier 2/3, resource-sinks, state-verb-system gap, COIN/MIM research, edge-mode completeness, religious topology). The corrections to Part 3:

1. **spec-080 was wrongly scoped as Doctrine Tree MVP** (3 trunks / 3 tags / 15 nodes, with the full vision "deferred to spec 084+"). Promoted to **spec-080 Doctrine Tree FULL** — 4 trunks, 7 tags (RESILIENCE added), 50+ nodes, Party Congress (4 sub-actions: trunk_shift / rectification / theoretical_offensive / self_criticism), PatSoc Pipeline (national_liberation → patriotic_socialism → national_syndicalism → strasserism auto-acquire), maintenance/decay, full trap-node binding (Liquidationism, Adventurism, Dissociation, Bureaucratic-Centralism/Commandism/Tailism), shared praxis tactics, Sigma.js frontend.

2. **spec-070 Balkanization and the spec-087-proposed Sovereign Topology + Faction Influence are the same spec** with overlapping data models (Faction + Sovereign + INFLUENCES + CLAIMS + ColonialStance UPHOLD/IGNORE/ABOLISH). Merged into spec-070 with the more detailed plan from the persistence-residuals pass (~140-180h, includes O(1) edge rewiring fracture operation, secession/civil-war mechanics, real proxy data bootstrap from union density / AIANNH / election results).

3. **Tier 1 reproductive labor (spec-082) is NOT actually in code today** despite Part 3 framing it as "small surgical change." Reframed: spec-082 must land before spec-092 (Tier 2/3); both are pending.

4. **Resource sinks are NOT covered by spec-072 Vanguard Economy.** Part 3 conflated generation (072 scope) with decay (separate scope). Resource decay is its own spec-093 — 12 decay mechanisms (burnout, defection, death_capture, enthusiasm decay, life pressures, repression_fear, disillusionment, attention_decay, scandal_risk, knowledge_atrophy, generational_loss, crisis drains) plus 4 crisis-drain handlers, equilibrium telemetry, calibration regression.

5. **GenderedAgent is NOT obsolete** despite Part 3 calling it superseded by hypergraph CommunityType. Different layers of resolution: hypergraph models the social fact (gendered labor allocation at collective level via WOMEN/PATRIARCHAL/TRANS hyperedges); GenderedAgent models the per-agent survival arithmetic (do women in a community face a different P(S|A) than men?). Both needed in spec-092.

6. **Edge-mode completeness analysis (`ai-docs/spec-prompts/edge-mode-completeness-analysis.md`) is fully closed** — `CO_OPTIVE` is in `EdgeMode` enum, 17 transitions are coded in `engine/systems/edge_transition/_legacy.py`. No spec needed.

7. **State Verb System (`spec-prompts/enemy-ai/036-state-verb-system.md`) has small remaining gaps** despite spec-039 covering most of it: NEGOTIATE resolution mechanic, StateBudget model, Detroit 2010 init, player appropriation pipeline for RESEARCH, VC-001 through VC-010 validation suite. These become spec-094.

8. **COIN/MIM research notes contain 12 empirically-grounded coefficients** (Jones-Libicki endpoint distribution, religious-ideology resilience 1.62×, Sparrow temporal decay 0.85×, backfire adaptive learning, observation incompleteness 0.25, coordination tax 0.8×, OODA cycle latency, policing baseline 0.40, prison wage extraction 165:1-275:1, repression budget growth 3.7×, racial disparity 8:1) — folded into spec-078 (Repression Logic Full) as §4 Empirical Calibration. +20-25h on top of spec-078 baseline.

9. **Religious topology IS warranted** at Tier 1 (capture vector + field-source contribution + edge myelination + 3 falsifiable-prediction tests). Higher-dimensional ideology manifold deferred until foundational questions resolved (manifold dimensionality, basis vectors). Spec-095.

10. **Prison Labor Value Extraction is the only standalone new mechanic from MIM research** (165:1-275:1 surplus-value ratio). Spec-096.

11. **epoch2-persistence.yaml (in epoch3/ folder, 1490 lines) is 80 % superseded** by ADR037 + spec-061 + spec-062 persistence work. The residual is the *political-topology gameplay layer* (Sovereign-as-Node, Faction with colonial_stance, CLAIMS/INFLUENCES edges, Red Settler Trap) — already absorbed into spec-070.

12. **epoch2-trpf.yaml is 80 % implemented** across spec-021, spec-024, dialectical-topology. Residual is engine wiring (canonical 21-system tick still uses Epoch 1 time-decay surrogate at `engine/systems/economic.py:272-277`; per-organization c/v fields populated but unread; bourgeois decision tree from counter-tendency factors with INTENSIFY/AUTOMATE/CUT_WAGES choices absent). Becomes spec-088.

---

### The full-vision catalog (27 specs)

Reserved (per ADR044): **067** QCEW v2 · **068** BEA Input-Output · **069** SQLite read caching.

#### Wave 1 — Political topology (unblocks 3D)

| # | Title | Complexity | Hours | Hard dependencies | Status of substrate |
|---|---|---|---|---|---|
| **070** | Sovereign Topology + Faction Influence + Balkanization | XL | 140–180 | spec-037, spec-062 ✅ | New entities (Faction/Sovereign), new edge types (CLAIMS/INFLUENCES/ADMINISTERS), new enums (ColonialStance, ExtractionPolicy, SovereigntyType), 3 new systems, real proxy data bootstrap |
| **071** | Reactionary Subject (Entitlement + Chauvinism + FascistFactionSystem) | L | 50–70 | 070 | Math substrate exists (`route_agitation_to_ternary`); analysis layer (Entitlement field, Chauvinism accumulation, FascistFactionSystem, defection probability, fascist verbs POGROM/LOCKOUT/VIGILANTISM/RED_BROWN_COUP) all new |

#### Wave 2 — Player organizational economy

| # | Title | Complexity | Hours | Hard dependencies | Status of substrate |
|---|---|---|---|---|---|
| **072** | Vanguard Economy System (Coherence + Decay + Action Resolution) | L | 80–120 | spec-031 ✅, spec-032 ✅ | VanguardResources model exists; Coherence formula + 7 action resolvers + maintenance/decay all new |
| **073** | Cohesion Mechanic (Iron Law of Oligarchy + organizational split) | L | 60–90 | 072 | Organization.cohesion field exists; entropy/cadre_ratio/factionalism mechanics + 3 actions (MASS_RECRUITMENT/RECTIFICATION/POLITICAL_EDUCATION) + node-split logic all new |
| **074** | Demographic Crisis & Resolution Pathway selector | M | 30–50 | 070 | MetabolismSystem at pos 13 emits ECOLOGICAL_OVERSHOOT; consumption_balance metric + ResolutionPathway selector (FASCIST/SOCIALIST/IMPERIAL) + 3 resolution effects all new |

#### Wave 3 — Player action verbs (3D + 3C)

| # | Title | Complexity | Hours | Hard dependencies | Status of substrate |
|---|---|---|---|---|---|
| **075** | Kinetic Warfare (ATTACK verb engine + QRF + blowback) | XL | 80–120 | 072, 073, spec-046 ✅ (API designed) | `ActionType.ATTACK_INFRASTRUCTURE` is an unresolved enum value; KineticSystem, AttackingForce/AttackOutcome models, TargetType enum, all 6 formulas (Force_Power, Effective_Force, Success_Prob, Blowback, Isolation_Index, QRF), heat/c/edge-severing all new |
| **076** | Fog of War + Intel Layer (Mass Receptivity + Intel Confidence + masked attrs) | L | 60–90 | spec-039 ✅, spec-034 ✅, 087 RAG (citations) | `PRESENCE` edge type exists; IntelligenceSystem, M_r/I_c formulas, masked-attribute generator, 3 player actions (agitate_locally/social_investigation/establish_contact_network), UI confidence indicators all new |
| **077** | Gramscian Hegemony System (player narrative warfare) | L | 50–80 | 076, 087 RAG | Dual-narrative LLM director MVP exists; Hegemony resource, 4 player verbs (JAM_SIGNAL/DISTRIBUTE_SAMIZDAT/CAPTURE_MEDIA/VIRAL_CAMPAIGN), RAG corpus split (HEGEMONIC/COUNTER_HEGEMONIC), Manufacturing-Consent linguistic patterns, INTEL channel all new |
| **078** | Repression Logic Full + COIN/MIM Empirical Calibration | XL | 140–185 (incl. +20-25 calibration) | spec-039 ✅, 073 | spec-039 covers ~40 %. NEW: ROE Tier state machine (CIVIL_ORDER/STATE_OF_EXCEPTION/OPEN_WAR with verb gating + economic coupling), bad-jacketing (`edge.suspicion`, INTERNAL_PURGE), false-flag missions (Mission queue, 4 trap types), snitch budget (`INFORMANT` edge, desperation recruitment), Malinovsky Paradox (Infiltrator model, spy_labor_output vs intel_leak), 12 empirical coefficients from Jones-Libicki + Sparrow + MIM |
| **079** | Panopticon Economy (Θ-budget + expansion + saturation) | M–L | 40–60 | spec-039 ✅, 078 ROE tiers | AttentionThread model + Sparrow centrality exist; Θ-budget enforcement (Monitor=1Θ/Investigate=2Θ/Suppress=3Θ/QRF=allΘ), 3 expansion LEGISLATE sub-actions (MASS_SURVEILLANCE_ACT/ALGORITHMIC_POLICING/EMERGENCY_POWERS coupling), PanopticonSystem, saturation/DDoS detection, agitation_floor coupling all new |

#### Wave 4 — Strategic choice + endgames

| # | Title | Complexity | Hours | Hard dependencies | Status of substrate |
|---|---|---|---|---|---|
| **080** | Doctrine Tree FULL (4 trunks · 7 tags · 50+ nodes · Party Congress · PatSoc Pipeline · maintenance/decay) | XL | 120–160 | 072, 073, 071 (Strasserite terminal) | 100% greenfield. Trap detector exists as wiring point. New: DoctrineNode/DoctrineTree models, 7-tag system (CLASS_ANALYSIS/MASS_LINK/MILITANCY/LEGALITY/SECRECY/NATIONALISM/RESILIENCE), Theoretical Labor resource, 50-node JSON tree, Party Congress (4 sub-actions), automated PatSoc degeneration pipeline, full Sigma.js DAG frontend |
| **081** | Warlord Trajectory Branching (4 endgames + military/police split) | L | 60–80 | 070 | PENAL_COLONY + CARCERAL_ENFORCER + DecompositionSystem substrate exists. NEW: State apparatus refactor (MILITARY vs LOCAL_POLICE), WarlordTrajectorySystem branch selector (Classical/Necropolitical/Revolutionary/Contested), revanchist_cohesion + settler_consciousness + prisoner_organization + enforcer_radicalization computations, 4 new GameOutcomes |

#### Wave 5 — Loop closure (material reality)

| # | Title | Complexity | Hours | Hard dependencies | Status of substrate |
|---|---|---|---|---|---|
| **082** | Reproductive Labor Tier 1 + S_imperial Explicit Accounting | S | 8–16 | 071 | **CORRECTION FROM PART 3**: Not actually in code today. Subsistence floor + capped extraction + regeneration cycle + ReproductionSystem at pos 9.5 + S_imperial field on SocialClass all genuinely new |
| **083** | Political Economy of Liquidity (Fiscal + Fundraising + Precarity) | L | 80–120 | 072 | StateFinance/RevolutionaryFinance/PrecarityState models exist; FiscalSystem (state side, debt + inflation), FundraisingSystem (org side, dues + expropriation + donor drift), PrecaritySystem (real_wage → consciousness pipeline), PROLETARIANIZATION + HYPERINFLATION + EXPROPRIATION verbs all new |

#### Wave 6 — Content, voice, and infrastructure

| # | Title | Complexity | Hours | Hard dependencies | Status of substrate |
|---|---|---|---|---|---|
| **084** | Adaptive Music Director (regime selector + layer mixing + 6 missing MIDI generators + Web Audio frontend) | XL | 80–100 | 071, 078 | 14 MIDI assets exist (~`assets/music/`); 6 missing generator files; no runtime music integration; no frontend Web Audio infrastructure |
| **085** | Tutorial & Progressive Disclosure System (Epoch 1 observer mode + 3 sub-epoch lessons + 3 trap reveals + theory deep-links) | XL | 110–140 | 073, 076, 077, 080 | Tooltip primitives exist (`BblTooltip`); no TutorialState/TutorialStep symbols; no "Awakening" scenario; ~12 new React components needed |
| **086** | Reality-Grounded Game-Data Pipeline (6 external-data fetchers + 12 JSON schemas + content registry + ~6500 lines of game-content JSON) | XL | 100–130 | 070-083 (all, for full content) | SQLite 3NF reference DB exists; existing ingestion scripts cover ~half the sources; `data/external/{fred,bls,census}` empty; `src/babylon/data/game/` mostly empty (only personas) |
| **087** | RAG Full Architecture (CANON/CHRONICLE/ZEITGEIST collections + ResonanceEngine + 6-stage Validation Pipeline + persona catalog + citation tracking + evaluation framework) | XL | 60–80 | spec-061 ✅, 077 (concurrent) | Single-corpus single-perspective MVP exists (`PgVectorStore` + dual-narrative `NarrativeDirector` + `NarrativeCommissar` judge); multi-collection routing, Marxist corpus ingestion (~5000 chunks), VectorStateBridge, ResonanceEngine, 6-stage validation, 6 new personas (Bondi + 5), citation/provenance, red-team eval suites all new |
| **088** | TRPF Game-Mechanic Activation (engine wiring + bourgeois decision tree + automation OCC dynamics) | M–L | 90–120 | spec-021 ✅, spec-024 ✅ | Formulas exist (`calculate_rate_of_profit`, `calculate_organic_composition`); CounterTendencyStrength model + calculator exist; `TRPFDialectic` exists but **not in `_DEFAULT_SYSTEMS`** — Epoch 1 time-decay surrogate still active. NEW: TRPFSystem at pos 9.5, BourgeoisDecisionSystem + BourgeoisActionSystem at 14a/14b, 7 actions (INTENSIFY_EXPLOITATION/CUT_WAGES/AUTOMATE/CHEAPEN_INPUTS/EXPAND_RESERVE_ARMY/BANKRUPTCY/NO_CHANGE), PROFIT_CRISIS events |
| **089** | Synopticon / Lavender + Gospel Algorithmic Targeting | L | 70–100 | 078, 076, 079 | Sparrow centrality + AttentionThread model exist; DigitalDossier + 4-feature Lavender scoring + Gospel queue + 4 player counter-measures (CREATE_DECOY/ORGANIZE_CELLS/GO_DARK/EMBED_POPULATION) + decoy blowback + CDE policy switch all new |
| **090** | Strategy Layer Full (4-resource economy + 3 trap-trigger events + recovery mechanics + 3 trap actions) | L | 80–110 | 072, 073, 075, 080 (two-way) | `trap_detection.py` is read-only diagnostic; INSTITUTIONAL_DISSOLUTION/NETWORK_COLLAPSE/LABOR_ARISTOCRACY_CAPTURE trigger events absent; resource pools (CL/SL/SOL/COH) not formalized at org level; recovery mechanics, hidden-cost reveal, narrator foreshadowing all new |
| **091** | Error Recovery Framework (severity mixins + state snapshot rollback + 5 validation layers + degradation modes + chaos harness + frontend error UX) | L | 80–110 | None hard (foundational) | ADR019 4-layer hierarchy exists (BabylonError → 4 layer classes); severity mixin axis (Recoverable/Degraded/SaveAndExit/Critical), snapshot rollback wrap of engine loop, 5 validation layers, REDUCED/EMERGENCY degradation, save/load integrity + backup-on-save, `tools/chaos.py`, React ErrorBoundary all new |

#### Wave 7 — Deep mechanics

| # | Title | Complexity | Hours | Hard dependencies | Status of substrate |
|---|---|---|---|---|---|
| **092** | Reproductive Labor Full Cycle (Tier 2 debt + extraction sigmoid + Tier 3 GenderedAgent + Household pooling) | L | 60–80 | 082 (Tier 1) | Tier 1 not in code yet; Tier 2 debt mechanism, sigmoid extraction efficiency, reproduction_pressure metric + Tier 3 GenderedAgent (F/M/NB) + Household entity + HOUSEHOLD_MEMBER edge type all new |
| **093** | Vanguard Resource Decay & Equilibrium (12 decay mechanisms + 4 crisis drains + equilibrium telemetry) | L | 50–70 | 072, 078, 073 | Spec-072 covers generation only. 12 named decay functions, DecaySystem at pos 14.5, 4 crisis drain event handlers, per-resource pressure metrics, calibration regression baselines all new |
| **094** | State Verb System Closure (NEGOTIATE + StateBudget + Detroit 2010 init + RESEARCH appropriation + VC validation suite) | M | 35–45 | spec-039 ✅ | Spec-039 implements 6 verbs + 23 sub-verbs + faction balance + effects; NegotiationResolution, StateBudget (revenue + factional claims), Detroit init, CLASSIFIED/BLACK research appropriation pipeline, VC-001-VC-010 test suite all new |
| **095** | Religious Institution as Field Source (Tier 1: capture vector + field contribution + edge myelination + falsifiable predictions) | M–L | 45–60 | spec-040 ✅, spec-002 ✅ | `ApparatusType.ISA_RELIGIOUS` enum value exists; capture vector (`dict[StateFaction, float]`), drift equation `dc/dt = η(f-c)`, religious_field_contribution formula, edge myelination dynamics + 3 falsifiable-prediction tests all new. Tier 2 (higher-dimensional manifold, gravitational mass derivation) deferred pending unresolved foundational questions |
| **096** | Prison Labor Value Extraction System | M | 25 | spec-039 ✅ | NEW: PrisonLaborExtractionSystem at pos 12.5, Phi_prison computation per tick (165:1-275:1 surplus-value ratio per MIM research), routing to LABOR_ARISTOCRACY class via imperial rent flow; test against MIM-cited $710-810M/yr Michigan figure |

### Total effort estimate

| Wave | Specs | Sum (hours) |
|---|---|---|
| Wave 1 — Political topology | 070, 071 | 190–250 |
| Wave 2 — Player org economy | 072, 073, 074 | 170–260 |
| Wave 3 — Player action verbs | 075, 076, 077, 078, 079 | 370–535 |
| Wave 4 — Strategic choice + endgames | 080, 081 | 180–240 |
| Wave 5 — Loop closure | 082, 083 | 88–136 |
| Wave 6 — Content, voice, infrastructure | 084, 085, 086, 087, 088, 089, 090, 091 | 670–890 |
| Wave 7 — Deep mechanics | 092, 093, 094, 095, 096 | 215–280 |
| **TOTAL** | **27 specs** | **1,883–2,591 hours** |

At 30 hr/week of focused engineering this is **~14–20 months calendar time** for a single senior engineer; with AI assistance and parallel work streams, compressing into **~6–10 months** is realistic.

### Dependency graph (full vision)

```mermaid
flowchart TD
    A[Existing substrate&lt;br/&gt;21 systems, formulas,&lt;br/&gt;spec 037 PG runtime,&lt;br/&gt;spec 039 state AI,&lt;br/&gt;spec 062 cross-scale,&lt;br/&gt;spec 066 marx coherence]

    A --&gt; S091[091&lt;br/&gt;Error Recovery&lt;br/&gt;cross-cutting]

    A --&gt; S070[070&lt;br/&gt;Sovereign Topology&lt;br/&gt;+ Balkanization]
    A --&gt; S072[072&lt;br/&gt;Vanguard Economy]
    A --&gt; S082[082&lt;br/&gt;Repro T1 + S_imperial]
    A --&gt; S088[088&lt;br/&gt;TRPF Activation]
    A --&gt; S094[094&lt;br/&gt;State Verb Closure]
    A --&gt; S095[095&lt;br/&gt;Religious Field Source]
    A --&gt; S096[096&lt;br/&gt;Prison Labor]

    S070 --&gt; S071[071&lt;br/&gt;Reactionary Subject]
    S070 --&gt; S074[074&lt;br/&gt;Demographic Crisis]
    S070 --&gt; S081[081&lt;br/&gt;Warlord Trajectory]

    S072 --&gt; S073[073&lt;br/&gt;Cohesion Mechanic]
    S072 --&gt; S075[075&lt;br/&gt;Kinetic Warfare]
    S072 --&gt; S080[080&lt;br/&gt;Doctrine Tree FULL]
    S072 --&gt; S083[083&lt;br/&gt;Pol Econ Liquidity]
    S072 --&gt; S090[090&lt;br/&gt;Strategy Layer Full]
    S072 --&gt; S093[093&lt;br/&gt;Resource Decay]

    S071 --&gt; S080
    S073 --&gt; S075
    S073 --&gt; S090

    A --&gt; S076[076&lt;br/&gt;Fog of War]
    A --&gt; S087[087&lt;br/&gt;RAG Full Architecture]
    S076 --&gt; S077[077&lt;br/&gt;Gramscian Hegemony]
    S087 --&gt; S077
    S087 --&gt; S076

    A --&gt; S078[078&lt;br/&gt;Repression Logic Full&lt;br/&gt;+ COIN/MIM calibration]
    S078 --&gt; S079[079&lt;br/&gt;Panopticon Economy]
    S078 --&gt; S089[089&lt;br/&gt;Synopticon / Lavender]
    S079 --&gt; S089
    S078 --&gt; S093

    S080 --&gt; S090
    S075 --&gt; S089
    S076 --&gt; S089

    S082 --&gt; S092[092&lt;br/&gt;Repro T2+T3]

    A --&gt; S084[084&lt;br/&gt;Music Director]
    A --&gt; S085[085&lt;br/&gt;Tutorial System]
    A --&gt; S086[086&lt;br/&gt;Game-Data Pipeline]
    S073 --&gt; S085
    S076 --&gt; S085
    S077 --&gt; S085
    S078 --&gt; S085
    S080 --&gt; S085
    S071 --&gt; S084
    S078 --&gt; S084
```

### Recommended sequencing

**Foundational first** — these unblock the most downstream work:

1. **091 Error Recovery** — cross-cutting; makes every other system safe to fail. Land first.
2. **070 Sovereign Topology + Balkanization** — independent; unblocks 071, 074, 081.
3. **072 Vanguard Economy** — independent; unblocks 073, 075, 080, 083, 090, 093.
4. **078 Repression Logic Full** — independent (spec-039 already shipped 40 %); unblocks 079, 089, 084, 085.
5. **087 RAG Full Architecture** — independent of gameplay specs; unblocks 076, 077.

**Parallel work streams** — after the 5 foundations, four streams can proceed in parallel:

- **Stream A (Class & Faction)**: 071 → 080 → 081
- **Stream B (Organization)**: 073 → 090 → 075 (075 also waits on 072) → 089
- **Stream C (Information)**: 076 → 077
- **Stream D (Material Reality)**: 082 → 092, 083, 088, 093, 074
- **Stream E (Content & Polish)** (can start anytime after 084-data infrastructure exists): 086 → 085, 084
- **Stream F (Deep mechanics)** (low priority): 094, 095, 096

**Critical-path chain to playable Epoch 3**: `091 → 070 → 071 → 075 → 081` (Error Recovery → Sovereign/Balkanization → Reactionary Subject → Kinetic Warfare → Warlord Trajectory). ~480-630 hours.

### Specs to retire / mark superseded after the catalog lands

These ai-docs files are pre-empted by the catalog above and should be marked superseded:

- `ai-docs/epochs/epoch3/doctrine-tree-mvp.yaml` — superseded by spec-080 (FULL)
- `ai-docs/epochs/epoch3/epoch2-persistence.yaml` — superseded by ADR037/061/062 (persistence) and spec-070 (political topology residual)
- `ai-docs/epochs/epoch3/epoch2-trpf.yaml` — superseded by specs 021/024 (Capital volumes) and spec-088 (engine activation)
- `ai-docs/spec-prompts/edge-mode-completeness-analysis.md` — fully closed; no spec needed (`CO_OPTIVE` already in EdgeMode enum + 17 transitions coded)

---

## Appendix — Audit Trail

### Round 1 (Part 3 — 14 specs, some MVP-scoped)
Six agents analyzed: Epoch 1 verification, Epoch 2 verification, Epoch 3A (Materialism), Epoch 3B/3C (Organization/Information), Epoch 3D (Conflict), top-level YAML drift.

### Round 2 (Part 3-FULL — corrections + 13 additional specs at full vision)
Five agents analyzed: music+tutorial+game-data, RAG-full-architecture, persistence+TRPF residuals, doctrine-FULL+synopticon+strategy+error-recovery, reproductive-labor Tier 2/3 + resource-sinks + state-verb gap + COIN/MIM + edge-mode + religious topology.

### Memory commitment
User feedback "I want all of those features implemented" saved as `feedback_full_vision_no_mvps.md` so future sessions plan against full feature surface, not MVP scoping.
