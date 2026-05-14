# Implementation Plan: Vol II Circulation System with LODES OD Integration

**Branch**: `063-vol-ii-circulation` | **Date**: 2026-05-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/063-vol-ii-circulation/spec.md` (3 user stories, 40 functional requirements, 12 success criteria, 4 clarifications resolved — including Option B border-commute synthesis scope)

## Summary

This feature lands the **Vol II Circulation** stage of the per-tick five-flow pipeline established by spec 062, wiring LODES (LEHD Origin-Destination Employment Statistics) commute data into the engine as the deterministic min-cost flow component of Constitution II.13's Transport Substrate. Three load-bearing decisions, all clarified in the prior pass:

1. **JT00 + S000 segments only** (FR-001a/FR-001b): one OD matrix per simulated year, capturing all jobs at the all-workers aggregate. Worker-segment stratification (age/earnings/industry) is deferred to a future spec when downstream consumers materialize.
2. **Sub-stage 5c of the existing ImperialRent slot** (FR-015): Circulation runs between Imperial Rent inflow (5b) and Equalization (5d) in spec 062's pipeline ordering. No new top-level System slot is added; the existing slot owns five sub-stages.
3. **Cross-border `COMMUTE_OUT` paired with observational `TRADE_EDGE` inbound** (FR-030a/b/c): every boundary-exiting commute row gets a paired wage-repatriation row in the same tick. The paired row is observational (does not modify v conservation arithmetic FR-010), preserving spec 062's per-tick conservation contract while making the round-trip auditable.

Two engine seams from spec 062 close concurrently: **T079** (`ImperialRentSystem.step()` invokes the existing `distribute_phi_week_to_counties()` helper per tick) and **T080** (Detroit-Windsor cross-border commute routes to `dest_node_id='canada'` via the LODES classifier). The technical approach extends three already-shipped surfaces (`BoundaryFlowRegister`, `ImperialRentSystem`, `phi_distribution.py`) and introduces four new ones: (a) a `LODESCommuteMatrixLoader` reading from the on-disk LODES dataset, (b) a `Vol2CirculationStep` running as ImperialRent sub-stage 5c, (c) a `CrossBorderCommuteClassifier` resolving LODES destinations to `{hex, rest_of_usa, canada}`, and (d) — *added per Option B clarification 2026-05-13* — a `BorderCommuteSynthesisLoader` that reads BTS Border Crossing Data + StatCan Frontier Counts and synthesizes aggregate Detroit-Windsor commute rows when the `enable_border_commute_synthesis` flag is set. Postgres schema gets two new immutable-reference table families: `immutable_reference_lodes_od_matrix` plus `immutable_reference_border_commute_synthesis` (the latter storing pre-computed weekly Canadian-bound aggregate flows derived from BTS+WWE inputs at session-init time). No new dynamic tables — boundary register absorbs all per-tick output.

## Technical Context

**Language/Version**: Python 3.12+ (existing project standard)

**Primary Dependencies**:
- **Pydantic 2.x** — frozen models for `LODESLoaderConfig`, `CirculationStepResult`, `CrossBorderClassification`
- **scipy.sparse** — `csr_matrix` for the year-scoped OD matrix per Constitution II.12 (already in `pyproject.toml`)
- **NumPy** — vectorized row-sum, weighted-share, and conservation residual computation
- **psycopg 3.x + psycopg_pool** — Postgres reads of `immutable_reference_lodes_od_matrix` rows during runtime materialization (per Spec 037)
- **NetworkX 3.x** — graph attribute access for hex `v` reads and writes via spec 062's `NetworkXAdapter`
- **h3 4.2** — block-group → res-7 hex resolution (LODES coords use 2010 Census block-groups; the existing `us_xwalk.csv.gz` from `data-trove/lodes/` is the authoritative crosswalk)
- **Hypothesis ^6.149** — property-based tests for FR-010 conservation invariant (per Specs 053-056)
- No new third-party dependencies introduced by this feature.

**Storage**:
- **PostgreSQL 16+** — runtime store; new immutable-reference table `immutable_reference_lodes_od_matrix` (one row per (year, origin_hex, dest_node_id, dest_kind) tuple, magnitude = LODES JT00 S000 worker count). Table is fixture-derived per Constitution III.4.2; populated once during session initialization from the on-disk LODES files; never mutated at runtime.
- **On-disk LODES dataset** at `/media/user/data/babylon-data/lodes/od/` — read once at session initialization (Phase 1 of two-phase persistence per spec 062). Contains LODES JT00 OD CSV files per state per year. The crosswalk `us_xwalk.csv.gz` lives at `/media/user/data/babylon-data/lodes/us_xwalk.csv.gz`.
- **In-memory** — the loaded OD matrix lives as a `scipy.sparse.csr_matrix` per `LODESCommuteMatrixLoader` instance for the duration of the simulated year; year rollover triggers a fresh load at the tick boundary (FR-006).

**Testing**:
- `pytest` with markers `math` (for the conservation property tests), `topology` (for the matrix-vector behavior), `integration` (for end-to-end Postgres-backed sessions)
- Hypothesis property suites on `tests/property/circulation/test_v_conservation.py` for FR-010
- Live-Postgres integration tests gated by `BABYLON_TEST_PG_DSN` and the existing `pg_pool` fixture (spec 037 + 062 convention)

**Target Platform**: Linux server (Hetzner bare metal per Constitution X — Ansible-managed PGDG Postgres, systemd-supervised processes). Local dev environment uses `babylon-pg-isolated` container at port 5433.

**Project Type**: Engine library (Python package consumed by the Django backend per Spec 037/061, the React frontend per Specs 041/042, and the DearPyGui Synopticon dashboard).

**Performance Goals**:
- Vol II Circulation step executes in ≤ 10% of the existing four-flow per-tick wall-time budget for the Detroit tri-county scenario (SC-007). With ~1700 hexes the OD matrix is ~3M nonzeros at most; CSR matrix-vector multiplication should dominate at well under 100ms per tick on the established Hetzner test pool (per Constitution X — bare-metal Postgres + Python 3.12+ on AMD/Intel x86_64 commodity CPUs).
- LODES year load completes in ≤ 30 seconds per year at session init (no hard SLA — runs once per scenario year, not per tick).
- Conservation residual ≤ 1e-9 × pre-circulation total at every tick (SC-002).
- Bit-identical re-run across same-seed sessions (SC-005), inheriting determinism from spec 062's hash discipline.

**Constraints**:
- Per-tick atomic Postgres transaction (spec 062 FR-008a, inherited) — paired emission per FR-030a lands in the same envelope as the originating COMMUTE_OUT
- Constitution II.12: sparse-matrix representation is non-negotiable for OD matrix
- Constitution II.13: this feature implements only the deterministic min-cost flow component; slime-mold conductivity is explicitly out of scope (spec 063 Assumptions, anchored by spec 062 research §6 forward-pointer)
- Constitution III.7 determinism: same seed + same LODES year → bit-identical Circulation post-state and boundary register rows
- Constitution IV.1: Canada is a first-class boundary node; FR-026 invariant requires Canada present in external-node registry before any Windsor flow can route
- Spec 062 FR-053: Circulation is sub-stage 5c within ImperialRent slot — no new top-level System slot

**Scale/Scope**:
- ~1700 study-area hexes (Detroit tri-county)
- 16 simulated years × 1 OD matrix per year = 16 sparse matrices (loaded lazily, retained for current year only)
- ~10K–100K LODES OD pairs per year for tri-county scope (block-group resolution — pruned to in-study-area + boundary destinations per FR-007)
- Per-tick: ~1700 v-vector entries × ~2K avg destinations per origin = ~3.4M sparse multiplications worst-case → < 100ms expected
- 780 ticks (15 years × 52 weeks) ≈ 26K cross-border commute rows (estimating ~30 cross-border ODs per tick) plus paired TRADE_EDGE = ~52K boundary-register rows attributable to this feature alone

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

This feature touches a focused subset of constitutional domains. The check below evaluates against the relevant principles, organized by the AI Context Budget tiers from III.9.

### P0 (Never-Drop) Principles — All Retained

| Principle | Application in this feature | Status |
|---|---|---|
| **I.19 Dialectic as Primitive** | Circulation moves the variable-capital pole `v` of the c/v/s dialectic between hexes; does not introduce a new primitive. | ✅ Aligned |
| **I.20 Spatial Substrate as Immutable Ground Truth** | LODES OD matrix references the H3 res-7 grid via the existing crosswalk; does not mutate the substrate. Cross-border destinations resolve to existing external-node overlays per Constitution IV.1, not to substrate cells. | ✅ Aligned |
| **II.9 Morphism as Dyadic Relation** | Every emitted row (`COMMUTE_OUT`, paired `TRADE_EDGE`, `DRAIN_EDGE`) is a single dyadic source→dest tuple per the spec 062 BoundaryFlowRegister schema. The paired-row pattern (FR-030a) preserves dyadic morphism — two distinct rows, each strictly dyadic — rather than introducing a 4-tuple or hyperedge. | ✅ Aligned |
| **III.7 Determinism Hash and Replayability** | LODES OD matrix is a year-scoped immutable input; Circulation step is a pure function of `(v_pre, OD_year)`. Same inputs → bit-identical outputs (SC-005). The determinism hash from spec 062 (over per-tick state) extends naturally to the new Circulation post-state. | ✅ Aligned — **GATE-1 inherited** from spec 062's per-tick hash |
| **III.8 Aleksandrov Test** | Conservation invariant FR-010 represents material conservation of variable capital — the labor allocated at production sites equals the labor consumed at workplace sites plus the labor that exits the study-area boundary. The paired TRADE_EDGE represents the wage-flow back, which is the material monetary correlate of the labor-power expended. All operators trace to material relations. | ✅ Aligned |
| **V Verb Atomicity** | No new player or state-AI verbs introduced. Existing verbs (Educate/Aid/Attack/etc.) operate on the substrate this feature merely extends. | ✅ N/A — not modified by this feature |

### P1 (Load-Bearing) Principles — Domain-Relevant Retained

| Principle | Application | Status |
|---|---|---|
| **I.2 Imperial Rent (Φ)** | T079 closes the wiring that distributes Φ inflow from external nodes (per Hickel) to US counties via `ImperialRentSystem.step()` — making the Fundamental Theorem operational for the live engine, not just for the helper. | ✅ Aligned |
| **II.2 Primitives vs Derived** | LODES OD is a derived input (loaded once per year, immutable for the year); per-hex `v` is the primitive (carried by spec 062 FR-018). Cross-border classification is a derived attribute on emitted boundary rows, not a stored primitive. | ✅ Aligned |
| **II.6 State is Data, Engine is Transformation** | Circulation step is a pure `step(world, OD_matrix) → world'` transformation. No DB I/O during tick body — the OD matrix lives in-memory after Phase 1 load. **GATE-2** — no Postgres reads during the tick body for this feature; LODES rows are read only during session initialization. | ✅ Aligned — **GATE-2 explicit** |
| **II.11 Subsystem Table Ownership** | New `immutable_reference_lodes_od_matrix` table is owned by the **economics** subsystem (sibling of `immutable_reference_qcew_employment` per spec 062's ownership table). Cross-subsystem access goes through the loader API, not direct SQL. | ✅ Aligned — **GATE-3** documented in data-model.md |
| **II.12 Matrix Representation Layer** | OD matrix MUST be `scipy.sparse.csr_matrix` per principle. The CSR layout makes row-sum and matrix-vector multiplication O(nnz) and naturally fits the FR-009 formula. NetworkX is the authoring/inspection API; scipy.sparse is the compute layer. | ✅ Aligned — **GATE-4 satisfied** |
| **II.13 Transport Substrate** | Vol II circulation implements only the **min-cost flow** component (deterministic LODES OD). Slime-mold conductivity routing (the emergent informal-economy half) is explicitly out of scope (spec 063 Assumptions; anchored by spec 062 research §6 forward-pointer to spec 063 or 064 as the integration site). | ✅ Aligned — **GATE-5 satisfied** by explicit deferral |
| **III.1 No Magic Constants** | All numbers in this feature trace to either (a) federal LODES data (worker counts) or (b) spec-062 GameDefines (no new constants introduced). The `1e-9` tolerance in SC-002/SC-003 is the established conservation epsilon from spec 062. | ✅ Aligned |
| **III.4 Data Catalog** | LODES dataset classified as **fixture** per III.4.2 (pinned snapshot, never re-fetched at runtime). The `immutable_reference_lodes_od_matrix` Postgres copy is **fixture-derived runtime cache** per the catalog's existing pattern (matches `immutable_reference_qcew_employment`). | ✅ Aligned |
| **III.9 AI Context Budget** | Plan-phase agent retains P0 + listed P1 principles. P2 retention documented at end of this section. | ✅ Aligned |
| **IV Michigan Test Case** + **IV.1 Detroit-Windsor Boundary Condition** | Detroit tri-county study area is the canonical scope per IV.1. **GATE-6** — Canada must be a first-class international boundary node before any Windsor-bound LODES OD can route to it. Spec 062 T078 already operationalized this (Canada is bootstrapped during `initialize_session()`). FR-026 in this spec adds the fail-fast invariant: initialization MUST refuse to start if LODES contains Windsor destinations but Canada is missing from the external-node registry. | ✅ Aligned — **GATE-6 closed** by FR-026 |

### P2 Principles Dropped from Active Context

The following P2 principles are not load-bearing for this feature and are dropped per III.9 budget:

- I.3 TRPF, I.5 Department III, I.8 Tragedy of Inevitability, I.9 Metabolic Rift, I.10 Terminal Crisis, I.11 Emergent Pedagogy, I.13 Principal Contradiction, I.14 Contradiction Internals, I.15 Edge Mode Transitions, I.17 OODA, I.18 Material-Ideological — these are downstream consumers of the v-vector this feature redistributes, but their internal mechanics are unchanged
- II.3 NetworkX Manifold, II.4 Quantities vs Coefficients, II.7 Edges vs Hyperedges, II.8 Client Layer, II.10 World Runtime — preserved by inheritance from spec 062, not modified here
- III.3 Physics Cosplay, III.5 Empirical vs Strategic — unchanged
- VI Scope Control, VII Visual Design, VIII Anti-Patterns, X Deployment — orthogonal to this feature

**Note**: VIII.9 (Anti-Pattern Preserving) was explicitly checked — the paired-row pattern in FR-030a does NOT violate the dyadic-morphism constraint because each emitted row is independently dyadic. Two paired dyadic rows ≠ one tetradic relation.

### Constitution Check Result: **PASS** — proceed to Phase 0.

All six gates close in research.md or by inheritance from spec 062:
- **GATE-1** (determinism hash compatibility): inherited from spec 062's per-tick hash; circulation post-state contributes to the existing hash
- **GATE-2** (no DB I/O during tick body): explicit in research.md §2; loader runs at session init only
- **GATE-3** (subsystem ownership): documented in data-model.md ownership table
- **GATE-4** (sparse matrix representation): scipy.sparse.csr_matrix is the only allowed form
- **GATE-5** (Vol II = min-cost flow + slime-mold deferral): explicit in research.md §3
- **GATE-6** (Canada first-class boundary): closed by FR-026 fail-fast invariant + spec 062 T078 inheritance

## Project Structure

### Documentation (this feature)

```text
specs/063-vol-ii-circulation/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output — LODES schema, classification rule, perf budget, deferred slime-mold
├── data-model.md        # Phase 1 output — LODESCommuteMatrixLoader, Vol2CirculationStep, CrossBorderCommuteClassifier entities
├── quickstart.md        # Phase 1 output — end-to-end: hydrate Detroit session, run one tick, verify v conservation
├── contracts/           # Phase 1 output — loader API, circulation step API, boundary register row contract
│   ├── lodes_loader.yaml
│   ├── circulation_step.yaml
│   └── cross_border_classifier.yaml
└── checklists/
    └── requirements.md  # Created by /speckit.specify
```

### Source Code (repository root)

```text
src/babylon/
├── economics/
│   ├── lodes_commute_matrix.py        # NEW — LODESCommuteMatrixLoader (T054)
│   ├── border_commute_synthesis.py    # NEW — BorderCommuteSynthesisLoader (Option B; FR-031..FR-036)
│   ├── boundary_flow_register.py      # MODIFIED — extend record() helper for paired emission convenience
│   ├── node_kinds.py                  # UNCHANGED — NodeKind/BoundaryEdgeKind already cover the 5-tuple
│   └── phi_distribution.py            # UNCHANGED — existing helper invoked by ImperialRentSystem.step
│
├── economics/tick/system/
│   └── imperial_rent.py              # MODIFIED — wire distribute_phi_week_to_counties (T079) + invoke vol2_circulation (NOTE: actual repo path; sibling `engine/systems/imperial_rent.py` does NOT exist)
│
├── engine/
│   └── systems/
│       ├── vol2_circulation.py       # NEW — Vol2CirculationStep (T055), sub-stage 5c
│       └── cross_border_commute.py   # NEW — CrossBorderCommuteClassifier (T080)
│
├── persistence/
│   ├── postgres_initialization.py    # MODIFIED — call LODES + border-synthesis hydration during initialize_session()
│   ├── sqlite_hydrator.py            # UNCHANGED — LODES is not in SQLite; reads on-disk LODES files separately
│   └── migrations/
│       ├── 0014_lodes_od_matrix.py             # NEW — immutable_reference_lodes_od_matrix table + indexes
│       └── 0015_border_commute_synthesis.py    # NEW — immutable_reference_border_commute_synthesis table
│
└── config/
    └── defines/
        └── economy_basic.py          # MODIFIED — add `border_commute_share: float = 0.50` (cited from WWE 2017 report) + `enable_border_commute_synthesis: bool = False`

tests/
├── unit/
│   └── economics/
│       └── circulation/
│           ├── test_lodes_loader.py              # T054 unit tests (matrix shape, JT00/S000, year clamp)
│           ├── test_vol2_circulation_step.py     # T055 unit tests (formula correctness, zero-row-sum guard)
│           └── test_cross_border_classifier.py   # T080 unit tests (Windsor → canada, Toledo → rest_of_usa)
│
├── property/
│   └── circulation/
│       └── test_v_conservation.py    # FR-010 property test (50 random v vectors × fixed OD)
│
└── integration/
    ├── test_circulation_paired_emission.py       # FR-030a paired TRADE_EDGE round-trip test
    ├── test_phi_wiring_county_drain.py           # T079 end-to-end (county-level DRAIN_EDGE rows after one tick)
    ├── test_detroit_windsor_routing.py           # T080 end-to-end (Windsor-bound row → canada)
    └── test_circulation_pipeline_position.py     # FR-015 sub-stage 5c ordering

tests/scripts/
└── verify_063_circulation_walkthrough.py         # Quickstart-mirror smoke script (analogous to spec 062 T088)
```

**Structure Decision**: Engine-library structure consistent with the established Babylon layout. Source code lives under `src/babylon/{economics, engine/systems, persistence}/`; tests mirror the structure under `tests/{unit, property, integration, scripts}/`. The new `vol2_circulation.py` and `cross_border_commute.py` modules sit alongside the existing system modules at `src/babylon/engine/systems/` so they're auto-discoverable by the simulation engine. The new `lodes_commute_matrix.py` lives under `src/babylon/economics/` as a sibling of `boundary_flow_register.py` and `phi_distribution.py` — the loader is an economics primitive, the system step that consumes it is an engine system. Migration `0014_lodes_od_matrix.py` follows spec 062's migration numbering convention.

## Complexity Tracking

> No constitution violations to justify. The complexity table is intentionally empty.

The spec is deliberately scope-bounded:
- Slime-mold conductivity routing is explicitly out of scope (Constitution II.13 deferred half)
- Worker-segment stratification (LODES SA*/SE*/SI*) is explicitly out of scope (FR-001b)
- Per-(hex, NAICS) industry breakdown is out of scope (spec 062 FR-031 inheritance)
- Wage-repatriation magnitude refinement (taxes, on-site consumption) is explicitly deferred to Department III (FR-030a parenthetical)

Each deferral has a named downstream spec opportunity, ensuring the deferred work has a home and isn't lost.

## Re-evaluation Post-Phase-1

After data-model.md, contracts/, and quickstart.md are generated, all six gates remain closed:

- **GATE-1**: data-model.md confirms `Vol2CirculationStep` produces deterministic post-state from `(v_pre, OD_matrix)` inputs; contributes to the existing per-tick determinism hash unchanged.
- **GATE-2**: contracts/circulation_step.yaml shows the step takes the OD matrix as a constructor-injected parameter — no DB reads during `step()` execution.
- **GATE-3**: data-model.md §3 lists `immutable_reference_lodes_od_matrix` as economics-subsystem-owned; cross-subsystem reads go through `LODESCommuteMatrixLoader.load_year(year)` not raw SQL.
- **GATE-4**: contracts/lodes_loader.yaml mandates `scipy.sparse.csr_matrix` as the loader's return type.
- **GATE-5**: research.md §3 names the exact integration point for slime-mold conductivity (a future spec) without including it here.
- **GATE-6**: quickstart.md walks through the `initialize_session()` → external-node bootstrap → LODES load order, demonstrating the FR-026 fail-fast invariant fires correctly when Canada is missing.

**Final Constitution Check Result: PASS — proceed to /speckit.tasks.**
