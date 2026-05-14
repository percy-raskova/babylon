# Implementation Plan: Cross-Scale Integration — Value, Substrate, and Tick Propagation

**Branch**: `062-cross-scale-integration` | **Date**: 2026-05-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/062-cross-scale-integration/spec.md` (315 lines, 56 functional requirements, 15 success criteria, 5 clarifications resolved)

## Summary

This feature codifies the **cross-scale propagation engine** that ties together every previously-specified component of the Babylon simulation. Three load-bearing decisions, all clarified in the prior pass:

1. **Two-phase persistence**: SQLite (`marxist-data-3NF.sqlite`) is the read-only initialization-time reference; Postgres is the sole runtime store. After tick 0, SQLite is not touched.
2. **Per-tick transactional atomicity** (FR-008a): every tick wraps `dynamic_*` writes and `conservation_audit_log` appends in one Postgres transaction; crash recovery resumes from the last committed tick.
3. **Hex resolution 7 as the only primary persisted scale** for c/v/s/K/biocapacity (FR-018/FR-019). All coarser-scale values are computed on read via SQL views — no stored aggregates.

The technical approach is to extend three existing systems (`HexEqualizationComputer`, `BoundaryFlowRegister`, `InterpolatingBEASource`) and introduce three new ones (a `Substrate` system at pipeline position 2.5, a `ConservationAuditor` running at end-of-tick, and `ImmutableReferenceLookup` providing year-scoped coefficient access). Postgres schema migrations add five table families (`immutable_reference_*`, `dynamic_hex_state`, `dynamic_external_node_state`, `boundary_flow_register`, `conservation_audit_log`) plus four read-only aggregation views (`v_county_value_aggregate`, `v_state_value_aggregate`, `v_national_value_aggregate`, `v_global_phi_balance`).

## Technical Context

**Language/Version**: Python 3.12+ (existing project standard)

**Primary Dependencies**:
- **Pydantic 2.x** — frozen models for `DynamicHexState`, `ExternalNode`, `CoefficientLookupPolicy`, `ConservationAuditRow`, etc.
- **psycopg 3.x + psycopg_pool** — Postgres runtime connection pool; transactional per-tick writes via `with conn.transaction():` (established by Spec 037)
- **SQLAlchemy 2.x** — read-only ORM bindings against `marxist-data-3NF.sqlite` during initialization only
- **NetworkX 3.x** — hex graph in-memory representation; aggregation queries operate on graph + SQL views
- **XGI 0.10** — hypergraph community memberships (consumed but not modified by this feature)
- **scipy.sparse** — large-scale matrix operations on hex-hex commute OD matrix (per Constitution II.12)
- **Hypothesis 6.149+** — property-based testing for conservation invariants (per Specs 053-056)
- **NumPy** — geometric depreciation, vector aggregation, residual computation
- No new third-party dependencies introduced by this feature.

**Storage**:
- **PostgreSQL 16+** with PostGIS, pgvector, uuid-ossp extensions — runtime state via Spec 037 `RuntimePersistence` protocol
- **SQLite** (`data/sqlite/marxist-data-3NF.sqlite`) — read-only initialization-only federal reference data; classified as **fixture data per Constitution III.4.2** (pinned snapshot, never re-fetched at runtime)

**Testing**:
- `pytest` with markers `math`, `ledger`, `topology`, `integration`, `red_phase`
- Hypothesis property-based suites for conservation invariants (specs 053/054/055/056 harness)
- Integration tests gated behind `mise run test:int` via `pytest.mark.integration` and the `pg_pool` fixture (existing convention from Spec 061)
- Doctest examples in formula modules per project standard

**Target Platform**: Linux server (Hetzner bare metal per Constitution X — Ansible-managed PGDG Postgres, systemd-supervised processes)

**Project Type**: Engine library (Python package consumed by the Django backend per Spec 037/061, DearPyGui Synopticon dashboard, and React frontend per Specs 041/042)

**Performance Goals**:
- 780-tick Detroit run (~1700 hexes × 7 external nodes) completes in ≤ 60 minutes wall time (SC-003)
- Per-tick average ≤ ~4.6 seconds budget
- Conservation residual ≤ 1e-10 at every audit row (SC-002)
- Aggregate query (county/state/national c/v/s) returns in < 1 second on populated study area
- Boundary register query (tick-scoped or hex-scoped slice) returns in single-second range after 780-tick accumulation

**Constraints**:
- Per-tick atomic Postgres transaction (FR-008a) — non-negotiable
- SQLite read-only and closed before tick 0 (FR-001/FR-002) — non-negotiable
- Hex resolution 7 is the only persisted c/v/s/K/biocapacity (FR-018/FR-019) — non-negotiable
- Constitution III.7 determinism — same seed + same inputs → same hex state at every tick
- Constitution II.11 subsystem table ownership — each new table family declares its owner subsystem
- Constitution III.4.2 fixture vs runtime distinction — SQLite reference is fixture; `immutable_reference_*` runtime copy is fixture-derived and never re-fetched

**Scale/Scope**:
- ~1700 study-area hexes (Detroit tri-county) × 780 ticks (15 years × 52 weeks) ≈ 1.33M hex-state rows
- 7 external nodes × 1700 hexes × 780 ticks ≈ 9.3M boundary-flow rows worst-case
- 16+ conservation invariants × 780 ticks ≈ 12,500 audit rows
- ~10 immutable reference series × 16 years × variable row count (annual) ≈ 5,000 reference rows
- Total Postgres state after 780-tick run: ~10–12M rows, ~1–2 GB before archival

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

This feature touches multiple constitutional domains. The check below evaluates this feature against the relevant principles, organized by the AI Context Budget tiers from III.9.

### P0 (Never-Drop) Principles — All Retained

| Principle | Application in this feature | Status |
|---|---|---|
| **I.19 Dialectic as Primitive** | Hex c/v/s is the persisted primitive (FR-018); ValueTensor4x3 derivation from hex state confirmed | ✅ Aligned |
| **I.20 Spatial Substrate as Immutable Ground Truth** | H3 hex grid is immutable substrate; aggregations are overlays, never mutations. FR-019 forbids stored aggregates above hex resolution 7. | ✅ Aligned |
| **II.9 Morphism as Dyadic Relation** | Trade and drain edges between US hexes/counties and external nodes are dyadic (FR-039). Boundary register rows are tuples on dyadic edges, not n-ary structures. | ✅ Aligned |
| **III.7 Determinism Hash and Replayability** | FR-053 implies determinism; explicitly added below as **GATE-1** — the per-tick pipeline ordering MUST be deterministic and the engine MUST produce a determinism hash for each tick. SC-013 already mandates run-to-run identical state. | ⚠️ **Gap closed — explicit determinism hash added to data model below** |
| **III.8 Aleksandrov Test** | Conservation invariants represent material conservation of value-substance (c/v/s = constant capital + variable capital + surplus value, all tracing to labor-time per MELT τ). All operators trace to material relations. Audit log itself is a forensic record of material conservation. | ✅ Aligned |
| **V Verb Atomicity** | No new verbs introduced; existing verbs (Educate/Aid/Attack/etc.) operate within the per-tick pipeline this feature codifies. | ✅ N/A — not modified by this feature |

### P1 (Load-Bearing) Principles — Domain-Relevant Retained

| Principle | Application | Status |
|---|---|---|
| **I.2 Imperial Rent (Φ)** | FR-034/FR-035 + User Story 6 codify Φ flow from international boundary to US counties via Hickel drain + BEA I-O import shares. The Fundamental Theorem (W_c > V_c → Φ) is operationalized as the boundary inflow distributed by import-exposure. | ✅ Aligned |
| **II.2 Primitives vs Derived** | FR-018 (hex c/v/s primitive); FR-019 (no stored aggregates); FR-031 (industry shares derived on read from QCEW). Constitutional principle directly satisfied. | ✅ Aligned |
| **II.6 State is Data, Engine is Transformation** | Frozen Pydantic models for state; pure `step(World, SimulationConfig) → World` per-tick transformation. Postgres reads/writes happen at hydration/dehydration boundary, not during tick. | ✅ Aligned — added explicit gate **GATE-2** below |
| **II.11 Subsystem Table Ownership** | New tables introduced. **GATE-3**: each table family declares its owner subsystem in data-model.md; cross-subsystem reads go through views (`v_county_value_aggregate`, etc.) per the principle. | ⚠️ **Gap closed by data-model.md ownership table** |
| **II.12 Matrix Representation Layer** | LODES commute OD matrix consumed by Vol II circulation (FR-028) MUST be a scipy.sparse CSR matrix per principle. NetworkX is the authoring/inspection API; scipy.sparse is the compute layer. | ✅ Aligned |
| **II.13 Transport Substrate** | Vol II circulation flow (FR-028) maps to a min-cost-flow form over the LODES OD matrix per principle. **GATE-4**: research.md confirms the LODES OD matrix is the deterministic component (min-cost) and notes that slime-mold conductivity is out of scope for this feature (Vol II only requires the deterministic component). | ⚠️ Resolved in research.md |
| **III.1 No Magic Constants** | All numbers in this feature trace to either (a) federal data series (Hickel, BEA, MELT τ, QCEW) or (b) GameDefines configuration (δ_annual = 0.07, α_annual = 0.01, ε = 1e-10). FR-029 + FR-029a make α_annual a configurable, documented `GameDefines` field. ε is a numerical constant tied to IEEE-754 double precision floor. | ✅ Aligned |
| **III.4 Data Catalog** | SQLite reference DB classified as **fixture** per III.4.2 (pinned snapshot, never re-fetched at runtime); `immutable_reference_*` Postgres copy classified as **fixture-derived runtime cache** (read at runtime, not re-fetched). Aligned with the catalog. | ✅ Aligned |
| **III.9 AI Context Budget** | Plan-phase agent retains P0 + listed P1 principles. P2 retention documented at end of this section. | ✅ Aligned |
| **IV Michigan Test Case** + **IV.1 Detroit-Windsor Boundary Condition** | The spec's "tri-county study area" + 7 external world-region nodes is satisfied. **GATE-5** — the constitution requires Canada to be a first-class international boundary, not Rest-of-USA. The spec's external node list (FR-036) MUST include Canada (Windsor as the canonical cross-border city). **This is closed in research.md** with a recommendation to add Canada to FR-036's list. | ⚠️ **Gap to close in research.md + spec update if needed** |

### P2 Principles Dropped from Active Context

The following P2 principles are not load-bearing for this feature and are dropped from active context per III.9:
I.3 TRPF, I.5 Department III, I.8 Tragedy of Inevitability, I.10 Terminal Crisis Arc, I.11 Emergent Pedagogy, I.13 Principal Contradiction, I.14 Contradiction Internals, I.15 Edge Mode Transitions, I.17 OODA Loop, I.18 Material-Ideological Distinction, II.3 NetworkX Manifold (covered by II.12 retention), II.4 Quantities vs Coefficients (covered by FR-011), II.7 Edges vs Hyperedges (covered by II.9 retention), II.8 Client Layer, II.10 World Runtime (covered by II.6 retention), III.3 Physics Cosplay (covered by III.8 retention), III.5 Empirical vs Strategic, VI Scope Control, VII Visual Design, VIII Anti-Patterns (II.7-related anti-patterns covered by II.9 retention), X Deployment.

### Constitutional Gates (Summary)

| Gate | Principle | Status |
|---|---|---|
| GATE-1 | III.7 Determinism Hash | **Will close** by adding `determinism_hash` field to per-tick audit row in data-model.md |
| GATE-2 | II.6 No DB I/O during tick | Hydration is pre-tick; dehydration is post-tick; the tick itself is pure Python; codified in pipeline ordering doc |
| GATE-3 | II.11 Subsystem Table Ownership | **Will close** by including ownership-registry table in data-model.md |
| GATE-4 | II.13 Transport Substrate | **Will close** by documenting Vol II circulation = min-cost-flow component only; slime-mold conductivity is out-of-scope for v1 |
| GATE-5 | IV.1 Detroit-Windsor Boundary | **Will close** by adding Canada (with Windsor anchor) to the FR-036 external node list; documented in research.md |

All gates close after Phase 0/1 design — no constitutional violations carry into implementation. No Complexity Tracking row required.

## Project Structure

### Documentation (this feature)

```text
specs/062-cross-scale-integration/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output: deferred-item resolution + gate closures
├── data-model.md        # Phase 1 output: Pydantic models + Postgres DDL + ownership registry
├── quickstart.md        # Phase 1 output: developer onboarding for init / tick / aggregate / audit
├── contracts/           # Phase 1 output: inter-spec schema contracts
│   ├── persistence.yaml        # Hydration/dehydration contract Postgres ↔ NetworkX+XGI
│   ├── aggregation_views.yaml  # Read-view contract for county/state/national queries
│   ├── audit_log.yaml          # Conservation audit row schema
│   ├── boundary_register.yaml  # Boundary flow register row schema
│   └── reference_series.yaml   # Immutable reference series schema
├── checklists/
│   └── requirements.md  # Validation checklist (already generated by /speckit.specify)
├── spec.md              # Feature specification (already generated by /speckit.specify + /speckit.clarify)
└── tasks.md             # Phase 2 output (/speckit.tasks command — NOT created by /speckit.plan)
```

### Source Code (repository root)

This is a backend-engine feature (Python package). The frontend touches it only via the existing Django REST observe-endpoints (Spec 061's read paths), and is not modified by this feature.

```text
src/babylon/
├── persistence/                          # owner of `dynamic_*` and `immutable_reference_*`
│   ├── postgres_runtime.py               # extended: per-tick transaction wrapper (FR-008a)
│   ├── postgres_schema.py                # extended: DDL for 5 new table families + 4 views
│   ├── postgres_reference.py             # NEW: ImmutableReferenceLookup (coefficient access)
│   ├── postgres_aggregation.py           # NEW: read views and Python query helpers
│   ├── postgres_initialization.py        # NEW: SQLite→Postgres hydration orchestration
│   ├── conservation_audit.py             # NEW: ConservationAuditor (end-of-tick invariant runner)
│   └── migrations/
│       ├── 0010_immutable_reference_tables.sql
│       ├── 0011_dynamic_hex_state.sql
│       ├── 0012_dynamic_external_node_state.sql
│       ├── 0013_boundary_flow_register.sql
│       ├── 0014_conservation_audit_log.sql
│       └── 0015_aggregation_views.sql
├── engine/
│   ├── simulation_engine.py              # extended: 15-system pipeline with Substrate at 2.5
│   └── systems/
│       ├── substrate.py                  # NEW: physical-stock substrate at pipeline pos 2.5
│       ├── imperial_rent.py              # extended: per-week Φ distribution to counties
│       └── territory.py                  # extended: hex-county-state aggregation hookups
├── economics/
│   ├── boundary_flow_register.py         # extended: hex-pair dimensional fields (FR-040)
│   ├── coefficient_lookup.py             # NEW: slowly-varying vs event-discrete classifier
│   └── geometric_depreciation.py         # NEW: δ_weekly + α_weekly derivation helpers
└── config/
    └── defines.py                        # extended: α_annual, ε, scenario_length_years
                                          # (FR-029, FR-029a, FR-046, FR-004a)

tests/
├── unit/
│   ├── persistence/
│   │   ├── test_postgres_reference.py
│   │   ├── test_postgres_aggregation_views.py
│   │   ├── test_conservation_audit.py
│   │   ├── test_postgres_initialization.py
│   │   └── test_per_tick_transaction_atomicity.py    # FR-008a
│   ├── engine/
│   │   ├── test_substrate_system_ordering.py         # FR-050, FR-051
│   │   └── test_pipeline_substrate_position.py
│   └── economics/
│       ├── test_geometric_depreciation.py            # FR-014, FR-015
│       ├── test_coefficient_lookup_policy.py         # FR-011, FR-012, FR-013
│       ├── test_boundary_register_hex_pair_fields.py # FR-040
│       └── test_alpha_weekly_invariant.py            # FR-029a
├── integration/                                       # marker: integration; pg_pool fixture
│   ├── test_two_phase_initialization.py              # User Story 1 / SC-001
│   ├── test_weekly_tick_year_lookup.py               # User Story 2 / SC-007, SC-008
│   ├── test_cross_scale_aggregation.py               # User Story 3 / SC-002, SC-012
│   ├── test_five_flow_types.py                       # User Story 4 / SC-011
│   ├── test_audit_log_round_trip.py                  # User Story 5 / SC-004, SC-005, SC-006
│   ├── test_external_node_boundary.py                # User Story 6 / SC-010
│   ├── test_substrate_pipeline_position.py           # User Story 7
│   └── test_780_tick_perf_budget.py                  # SC-003 (slow; opt-in)
└── property/                                          # Hypothesis-based (specs 053-056 harness)
    ├── test_hex_to_county_conservation.py
    ├── test_county_to_state_conservation.py
    ├── test_global_phi_balance.py
    ├── test_per_stage_conservation.py
    └── test_geometric_depreciation_inverse.py        # (1-δ_w)^52 ≈ 1-δ_annual
```

**Structure Decision**: This is a **single backend-engine package** with no frontend changes. Source code lives under `src/babylon/{persistence,engine,economics,config}/` following the existing package layout. Tests use the existing three-tier structure (unit / integration / property-based). The Django backend and React frontend (Spec 037/041/042/061) consume the new Postgres views via existing observe-endpoints; no API surface is added by this feature.

## Phase 0: Outline & Research

Six items require Phase 0 resolution. Five are deferred from prior decisions; one is a constitutional gap. Each generates one entry in `research.md` with the `Decision / Rationale / Alternatives considered` format from the speckit template.

| # | Item | Origin | Output |
|---|---|---|---|
| R1 | α_annual empirical calibration target | Q5 deferred from `/speckit.clarify` | research.md §1 |
| R2 | BoundaryFlowRegister hex-pair dimensional fields | Architectural input ~75% confidence | research.md §2 |
| R3 | Crisis machinery weekly-cadence verification | Architectural input ~70% confidence | research.md §3 |
| R4 | Canada (Windsor) as Detroit-Windsor boundary node | **Constitutional gap (Gate-5, IV.1)** | research.md §4 |
| R5 | Subsystem table ownership registry | **Constitutional gap (Gate-3, II.11)** | research.md §5 |
| R6 | Vol II circulation as min-cost flow component | **Constitutional gap (Gate-4, II.13)** | research.md §6 |

## Phase 1: Design & Contracts

**Prerequisites**: `research.md` complete (Phase 0).

Phase 1 produces four artifacts, written sequentially:

1. **data-model.md** — Pydantic model definitions, Postgres DDL with PRIMARY KEY/INDEX choices, subsystem ownership registry (per Gate-3), and the lifecycle/state-transition narrative for each entity.

2. **contracts/** — five YAML files specifying inter-spec schema contracts:
   - `persistence.yaml` — hydration ↔ dehydration contract (Postgres ↔ NetworkX/XGI in-memory representation)
   - `aggregation_views.yaml` — the four read-only views (`v_county_value_aggregate`, `v_state_value_aggregate`, `v_national_value_aggregate`, `v_global_phi_balance`)
   - `audit_log.yaml` — `conservation_audit_log` row schema
   - `boundary_register.yaml` — `boundary_flow_register` row schema (with hex-pair fields per R2)
   - `reference_series.yaml` — `immutable_reference_*` table-family schema

3. **quickstart.md** — five-section developer onboarding: initialization, tick advance, aggregate query, audit-log inspection, adding a new reference series.

4. **Agent context update** — run `update-agent-context.sh claude` to absorb new tech additions into `CLAUDE.md`. Manual additions between markers are preserved by the script.

## Post-Design Constitution Re-Check

Performed after Phase 1 outputs are complete. All five gates close as projected in the initial Constitution Check:

| Gate | How Closed |
|---|---|
| GATE-1 (III.7 Determinism) | `data-model.md` adds `determinism_hash` field to per-tick `conservation_audit_log` row; computed from sorted SHA-256 of (tick, hex-state hash, action-list hash, rng_seed) |
| GATE-2 (II.6 No DB I/O in tick) | `contracts/persistence.yaml` codifies the hydrate-tick-dehydrate boundary; no Postgres handle is held during the in-process tick computation |
| GATE-3 (II.11 Subsystem Ownership) | `data-model.md` includes "Subsystem Ownership Registry" table mapping every new table to its owner subsystem (persistence, economics, engine) |
| GATE-4 (II.13 Transport Substrate) | `research.md` §6 documents Vol II circulation as min-cost-flow over the LODES OD matrix; slime-mold conductivity is explicitly out of scope for v1 with a forward note for Spec 063+ |
| GATE-5 (IV.1 Detroit-Windsor) | `research.md` §4 adds Canada (with Windsor anchor) to FR-036; `spec.md` FR-036 is updated by an addendum during Phase 0 |

No new violations introduced. No Complexity Tracking row required.

## Complexity Tracking

*No Constitution Check violations exist after the gates above close. This section is intentionally empty per the speckit convention.*
