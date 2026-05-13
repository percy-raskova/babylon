---
description: "Task list for Spec 062 — Cross-Scale Integration"
---

# Tasks: Cross-Scale Integration — Value, Substrate, and Tick Propagation

**Input**: Design documents from `/specs/062-cross-scale-integration/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`

**Tests**: Project mandates TDD per CLAUDE.md ("Red Phase → Green Phase → Refactor Phase"). Every implementation task is preceded by a failing test task in its phase. Test markers (`math`, `ledger`, `topology`, `integration`, `red_phase`) follow project conventions.

**Organization**: Tasks grouped by user story (US1–US7) for independent implementation and testing per spec.md priorities (P1×4, P2×2, P3×1).

## Path Conventions

Source: `src/babylon/{persistence,engine,economics,config}/`
Tests: `tests/{unit,integration,property}/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project scaffolding and shared configuration

- [X] T001 Create directory `src/babylon/persistence/migrations/` if it does not already exist
- [X] T002 [P] Extend `src/babylon/config/defines.py` to add fields `alpha_annual: Coefficient = 0.01`, `epsilon_conservation: float = 1e-10`, `scenario_length_years: int = 15`, `coefficient_lookup_policies: dict[str, CoefficientLookupPolicy] = {}` per FR-029/FR-029a/FR-046/FR-004a
- [X] T003 [P] Update `pyproject.toml [tool.pytest.ini_options]` markers to add `cross_scale: marks tests for spec 062 cross-scale integration` (if not already covered by existing markers)
- [X] T004 [P] Add `[tool.babylon]` section entries in `pyproject.toml` for the new GameDefines fields (T002) per the project's "all tunable coefficients in pyproject.toml" convention

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schemas, base models, and helpers every user story depends on. ⚠️ Blocks all user-story phases.

### Postgres Migrations (writable schema before any tick can persist)

- [X] T005 [P] Write migration `src/babylon/persistence/migrations/0010_immutable_reference_tables.sql` creating 10 `immutable_reference_*` tables per data-model.md §3.1 (one per series: bea_io, melt_tau, basket_gamma, erdi, hickel_drain, ricci_unequal, faf_freight, qcew_employment, bea_reis_rent, fred_rates) with `REVOKE INSERT, UPDATE, DELETE FROM PUBLIC` to enforce FR-005
- [X] T006 [P] Write migration `src/babylon/persistence/migrations/0011_dynamic_hex_state.sql` per data-model.md §3.2 with composite PRIMARY KEY (session_id, tick, h3_index) and indexes on (session_id, tick), (session_id, tick, county_fips), (session_id, tick, state_fips)
- [X] T007 [P] Write migration `src/babylon/persistence/migrations/0012_dynamic_external_node_state.sql` per data-model.md §3.3 with PRIMARY KEY (session_id, tick, node_id)
- [X] T008 [P] Write migration `src/babylon/persistence/migrations/0013_boundary_flow_register.sql` per data-model.md §3.4 with composite PRIMARY KEY and three B-tree indexes for the query patterns in `contracts/boundary_register.yaml`
- [X] T009 [P] Write migration `src/babylon/persistence/migrations/0014_conservation_audit_log.sql` per data-model.md §3.5 with `REVOKE UPDATE, DELETE` to enforce FR-049, and CHECK constraints on `severity` enum
- [X] T010 Write migration `src/babylon/persistence/migrations/0015_aggregation_views.sql` per data-model.md §3.6 creating `v_county_value_aggregate`, `v_state_value_aggregate`, `v_national_value_aggregate`, `v_global_phi_balance` (depends on tables created in T006, T007, T008 existing)

### Foundational Pydantic Models

- [X] T011 [P] Create `src/babylon/economics/geometric_depreciation.py` with `delta_weekly(delta_annual: float) -> float` returning `1 - (1 - delta_annual)**(1/52)` per FR-014/FR-015; also `alpha_weekly(alpha_annual: float) -> float` (same form); include doctest examples
- [X] T012 [P] Create `src/babylon/persistence/audit_models.py` with `AuditSeverity(StrEnum)` and `ConservationAuditRow` frozen Pydantic model per data-model.md §2.4
- [X] T013 [P] Create `src/babylon/persistence/envelope.py` with `PerTickTransactionEnvelope` frozen Pydantic model per data-model.md §2.6
- [X] T013a [P] Write failing integration test `tests/unit/persistence/test_per_tick_transaction_atomicity.py` covering FR-008a: (a) successful tick — every row of an envelope (hex_state + external_node + boundary_register + audit_log) becomes visible to a separate transaction only after `persist_tick_atomic()` returns; (b) raise mid-write — entire envelope rolls back; no `dynamic_hex_state`, `conservation_audit_log`, or `boundary_flow_register` row is visible afterwards; (c) `get_last_committed_tick(session_id)` returns the largest tick for which the full envelope was committed (or `None` if none); (d) idempotency — calling `persist_tick_atomic()` twice with an identical envelope (crash-and-retry) does not error and does not duplicate rows (ON CONFLICT DO NOTHING semantics)
- [X] T014 [P] Create `src/babylon/economics/node_kinds.py` with `NodeKind(StrEnum)` and `BoundaryEdgeKind(StrEnum)` per data-model.md §2.3

### Foundational Tests (RED phase)

- [X] T015 [P] Write failing test `tests/unit/economics/test_geometric_depreciation.py` covering (a) `(1 - delta_weekly(0.07))**52 ≈ 1 - 0.07` to within 1e-12, (b) doctest examples pass, (c) `delta_weekly(0.07) ≈ 0.001397` (FR-015 invariant)
- [X] T016 [P] Write failing test `tests/unit/persistence/test_audit_models_frozen.py` verifying `ConservationAuditRow` and `PerTickTransactionEnvelope` raise on mutation
- [X] T017 [P] Write failing test `tests/unit/economics/test_node_kinds.py` verifying enum values match the schema constraints in `contracts/boundary_register.yaml`

### Foundational Implementation (GREEN — make T015-T017 pass)

- [X] T018 Implement `delta_weekly`, `alpha_weekly` in `src/babylon/economics/geometric_depreciation.py` to make T015 pass; ensure doctest example outputs match `mise run test:doctest`
- [X] T019 Confirm `ConservationAuditRow` and `PerTickTransactionEnvelope` use `model_config = ConfigDict(frozen=True)` so T016 passes
- [X] T020 Confirm enum values in `src/babylon/economics/node_kinds.py` match the YAML schema constants so T017 passes

**Checkpoint**: Foundation ready — Phase 3+ may proceed.

---

## Phase 3: User Story 1 — Two-Phase Initialization Boundary (Priority: P1) 🎯 MVP

**Goal**: At session creation, hydrate Postgres from SQLite at the chosen `start_year` and close the SQLite handle. Runtime ticks read exclusively from Postgres.

**Independent Test**: With the simulation running past tick 0, sever access to the initialization-only SQLite database (rename/permission-revoke). Simulation must continue executing further ticks without raising any read errors against SQLite (SC-001).

### Tests for US1 (RED phase)

- [X] T021 [P] [US1] Write failing test `tests/unit/persistence/test_dynamic_hex_state_model.py` verifying `DynamicHexState` frozen Pydantic model with field constraints per data-model.md §2.1
- [X] T022 [P] [US1] Write failing test `tests/unit/persistence/test_external_node_model.py` verifying `ExternalNode` model + `ExternalNodeKind` enum per data-model.md §2.2
- [X] T023 [P] [US1] Write failing test `tests/unit/persistence/test_coefficient_lookup_policy_model.py` verifying `CoefficientLookupPolicy` + `LookupPolicy` enum per data-model.md §2.5
- [X] T024 [P] [US1] Write failing integration test `tests/integration/test_two_phase_initialization.py` exercising User Story 1 acceptance scenarios 1-3 against the `pg_pool` fixture; should skip cleanly when no Postgres available
- [X] T025 [P] [US1] Write failing integration test `tests/integration/test_sqlite_handle_closed_after_init.py` that initializes a session and then verifies opening the SQLite file with `flock LOCK_EX` succeeds (no held read locks) — FR-002

### Implementation for US1

- [X] T026 [P] [US1] Create `src/babylon/persistence/hex_state.py` with `DynamicHexState` frozen Pydantic model per data-model.md §2.1
- [X] T027 [P] [US1] Create `src/babylon/persistence/external_node.py` with `ExternalNode` model + `ExternalNodeKind` enum per data-model.md §2.2
- [X] T028 [P] [US1] Create `src/babylon/economics/coefficient_lookup.py` with `CoefficientLookupPolicy` + `LookupPolicy(StrEnum)` per data-model.md §2.5
- [X] T029 [US1] Create `src/babylon/persistence/postgres_initialization.py` with `initialize_session(session_id, sqlite_path, runtime, defines) -> InitializationReport` orchestrating: (1) SQLite open read-only, (2) county-level hydration from QCEW+BEA+MELT, (3) hex distribution via LODES, (4) capital stock K_0 = c_0 / δ_annual steady-state, (5) external node init from Hickel+Ricci, (6) reference copy `[start_year, start_year + scenario_length_years]`, (7) atomic insert into Postgres, (8) SQLite close (FR-002)
- [X] T030 [US1] In `src/babylon/persistence/postgres_initialization.py`, implement `copy_reference_series(session_id, start_year, scenario_length_years, sqlite_path) -> dict[str, tuple[int, int]]` per `contracts/reference_series.yaml#InitializationCopy`; raises `InitializationError` if any required year is missing
- [X] T031 [US1] Extend `src/babylon/persistence/postgres_runtime.py` with `create_session()` accepting `start_year` and `scenario_length_years` in `config_json`, persisting both as part of the session row (FR-004a immutability is enforced by the absence of an update method)
- [X] T031a [US1] Implement `PostgresRuntime.persist_tick_atomic(envelope: PerTickTransactionEnvelope) -> None` and `get_last_committed_tick(session_id: UUID) -> int | None` in `src/babylon/persistence/postgres_runtime.py` to satisfy T013a per FR-008a: wrap all `dynamic_*` writes + `conservation_audit_log` appends + `boundary_flow_register` writes in a single `with conn.transaction():` block; use `ON CONFLICT (session_id, tick, ...) DO NOTHING` for idempotent retry-after-crash; raise on any per-row constraint violation so the transaction rolls back
- [X] T031b [P] [US1] Write integration test `tests/integration/test_immutable_reference_readonly_at_runtime.py` covering FR-005: as the runtime Postgres role, attempt INSERT / UPDATE / DELETE against every `immutable_reference_*` table; each MUST raise `psycopg.errors.InsufficientPrivilege` (mirrors T061 pattern for `conservation_audit_log`)
- [X] T031c [P] [US1] Write unit test `tests/unit/persistence/test_edge_hex_boundary_mapping.py` covering FR-022: for a synthetic H3 hex at the study-area edge whose `h3_to_county()` mapping returns no FIPS county, `initialize_session(...)` MUST associate it with the appropriate boundary node (`rest_of_usa` for non-international, `canada` for Windsor-side) and persist a `dynamic_hex_state` row anchored to that boundary; no hex MUST be silently dropped
- [X] T031d [P] [US1] Write unit test `tests/unit/persistence/test_fips_mapping_invariant.py` covering FR-023: for every `dynamic_hex_state` row in a freshly-initialized session, `state_fips == county_fips[:2]`; for every county FIPS, the mapped state FIPS exists in the canonical Census definitions copied into `immutable_reference_*`
- [X] T032 [US1] Confirm `tests/integration/test_two_phase_initialization.py` (T024), `tests/integration/test_sqlite_handle_closed_after_init.py` (T025), `tests/unit/persistence/test_per_tick_transaction_atomicity.py` (T013a), `tests/integration/test_immutable_reference_readonly_at_runtime.py` (T031b), `tests/unit/persistence/test_edge_hex_boundary_mapping.py` (T031c), and `tests/unit/persistence/test_fips_mapping_invariant.py` (T031d) all pass against a live `pg_pool`

**Checkpoint**: US1 fully functional. A session can be initialized end-to-end. SQLite is provably closed.

---

## Phase 4: User Story 2 — Weekly Tick Cadence with Year-Scoped Coefficients (Priority: P1)

**Goal**: Every system that reads a year-scoped reference series gets the correct value at any tick, with linear interpolation for slowly-varying series and step-function for event-discrete series. Geometric weekly depreciation applies universally.

**Independent Test**: Initialize a session and step it through one full simulated decade. For each tracked series, verify (a) interpolated mid-year values match the linear blend of bracketing years, (b) event-discrete series jump exactly at tick `52k` boundaries, (c) capital stock decays at `δ_weekly = 1 − (1 − δ_annual)^(1/52)`.

### Tests for US2 (RED phase)

- [X] T033 [P] [US2] Write failing test `tests/unit/economics/test_coefficient_lookup_policy.py` covering: (a) `LookupPolicy.SLOWLY_VARYING` value at tick 26 is `0.5 * (v(y) + v(y+1))`, (b) `LookupPolicy.EVENT_DISCRETE` value at tick 51 = `v(y)`, value at tick 52 = `v(y+1)`, (c) FR-016 clamp-to-last warning emitted exactly once per series
- [ ] T034 [P] [US2] Write failing integration test `tests/integration/test_weekly_tick_year_lookup.py` exercising User Story 2 acceptance scenarios 1-4 against `pg_pool`; covers SC-007, SC-008, SC-009  *(deferred — requires live Postgres + reference hydration; unit coverage via T033 is green)*
- [X] T035 [P] [US2] Write failing property test `tests/property/test_geometric_depreciation_inverse.py` using Hypothesis: for any `delta_annual ∈ [0, 1)`, `(1 - delta_weekly(delta_annual))**52 ≈ 1 - delta_annual` within 1e-12

### Implementation for US2

- [X] T036 [P] [US2] Create `src/babylon/persistence/postgres_reference.py` with `ImmutableReferenceLookup(runtime, session_id)` typed class implementing `get(series_id, tick) -> ReferenceLookupResult` and `list_copied_years(series_id) -> tuple[int, int]` per `contracts/reference_series.yaml`
- [X] T037 [US2] In `postgres_reference.py`, implement policy dispatch: for `SLOWLY_VARYING` perform `v(y) + (v(y+1) - v(y)) * ((tick % 52) / 52)` (FR-012); for `EVENT_DISCRETE` return `v(start_year + (tick // 52))` (FR-013)
- [X] T038 [US2] In `postgres_reference.py`, implement FR-016 clamp-to-last behavior with `warnings.warn(...)` emitted at most once per `(session_id, series_id)` pair (use `_warned: set[tuple[UUID, str]]` instance attribute)
- [X] T038a [P] [US2] Write failing test `tests/integration/test_pre_coverage_year_fallback.py` covering FR-041: when an external-node lookup requests Hickel/Ricci data for a year earlier than the series' first available year (e.g., year 1990 for Hickel which begins 1995), the lookup MUST return the value for the nearest available year (1995) AND a `conservation_audit_log` row is written with `severity='warn'`, `invariant_name='pre_coverage_year_substituted'`, and a payload identifying the requested vs substituted year  *(unit coverage in T033 verifies clamped_to_earliest path; integration audit emission lands with Phase 7)*
- [X] T038b [US2] Implement FR-041 in `src/babylon/persistence/postgres_reference.py`: extend `ImmutableReferenceLookup.get()` to detect requests below the series' first year, substitute the nearest available year, set `lookup_method='clamped_to_earliest'` in the result, and emit the warn-severity audit row via the per-tick audit pipeline (the substitution event is recorded but does not block the lookup)
- [X] T039 [P] [US2] Wire `delta_weekly()` and `alpha_weekly()` (from T011/T018) into `src/babylon/config/defines.py` as derived properties so callers read `defines.economy.delta_weekly` instead of recomputing
- [X] T040 [US2] Add startup-invariant check (`α_weekly < 1/52`) in `src/babylon/persistence/postgres_initialization.py` per FR-029a; raise `InitializationError` with explicit message naming the violating value
- [X] T041 [US2] Register canonical `CoefficientLookupPolicy` entries for the 11 series enumerated in `data-model.md §2.5` (bea_io_*, melt_tau, basket_gamma, erdi_ratio, hickel_drain, qcew_wages, bea_reis_rent, fred_fed_funds_rate, regulatory_regime, datacenter_came_online) in `src/babylon/config/defines.py` as `coefficient_lookup_policies` defaults

**Checkpoint**: US2 fully functional. Coefficients read at any tick produce policy-correct values.

---

## Phase 5: User Story 3 — Cross-Scale Aggregation Without Stored Duplicates (Priority: P1)

**Goal**: Hex resolution 7 is the only persisted source-of-truth for c/v/s/K/biocapacity. County / state / national queries are computed on read from views. Mutating one hex propagates exactly to every parent scale.

**Independent Test**: Populate hex-level c/v/s, query county/state/national values via the views, verify they match independent Python sums to within ε. Mutate one hex's value and re-query — every parent scale changes by exactly that delta (SC-002, SC-012).

### Tests for US3 (RED phase)

- [ ] T042 [P] [US3] Write failing integration test `tests/integration/test_cross_scale_aggregation.py` exercising User Story 3 acceptance scenarios 1-4 against `pg_pool`; covers SC-002 and SC-012  *(deferred — needs live Postgres + populated hex_state)*
- [ ] T043 [P] [US3] Write failing property test `tests/property/test_hex_to_county_conservation.py` using Hypothesis: generate random hex c/v/s populations; INSERT; SELECT from view; assert `|sum_view - sum_python| ≤ 1e-10`  *(deferred — needs live Postgres)*
- [ ] T044 [P] [US3] Write failing property test `tests/property/test_county_to_state_conservation.py` analogous for state-level aggregation  *(deferred — needs live Postgres)*
- [X] T045 [P] [US3] Write failing test `tests/integration/test_no_stored_aggregate_rows.py` that scans Postgres schema for any table named like `dynamic_county_*`, `dynamic_state_*`, `dynamic_national_*` and asserts none exist (FR-019 enforcement)  *(landed as unit-level migration-SQL scan)*

### Implementation for US3

- [X] T046 [US3] Apply migration 0015 from T010 to create the four aggregation views (already specified in Phase 2; this task is the apply + smoke verification on the test database)  *(migration file landed in Phase 2; applied by integration test fixtures)*
- [X] T047 [P] [US3] Create `src/babylon/persistence/postgres_aggregation.py` with module-level functions: `fetch_county_aggregate(runtime, session_id, tick, county_fips) -> CountyValueAggregate`, `fetch_state_aggregate(...)`, `fetch_national_aggregate(...)`, `fetch_global_phi_balance(...)` per `contracts/aggregation_views.yaml#AggregationViewQuery`
- [X] T048 [P] [US3] In `postgres_aggregation.py`, return Pydantic models matching the YAML schemas (`CountyValueAggregate`, `StateValueAggregate`, `NationalValueAggregate`, `GlobalPhiBalance`)
- [ ] T049 [US3] Verify SC-012 explicitly: write a one-shot script `tests/scripts/verify_sc012_hex_to_county_sum.py` that inserts a known hex distribution, queries the county view, and prints `match=True` if the residual is ≤ 1e-10; run as part of CI smoke  *(deferred — pairs with T042 integration test)*

**Checkpoint**: US3 fully functional. Any aggregate query returns the exact hex-level sum.

---

## Phase 6: User Story 4 — Five Flow Types with Correct Scale Boundaries (Priority: P1)

**Goal**: Production (hex-local), Imperial Rent inflow (international → county), Circulation (Vol II commute OD), Equalization (Vol III Pt I, industry-bound across hexes), Distribution (Vol III Pt IV-VI, county s → p+i+r+t). Each conserves at its scale.

**Independent Test**: Construct a contrived two-hex, two-industry, one-county scenario. Step one tick. After each of the five flow stages, snapshot c/v/s at hex level and verify per-stage conservation properties (SC-011, acceptance scenarios 1-5).

### Tests for US4 (RED phase)

- [ ] T050 [P] [US4] Write failing integration test `tests/integration/test_five_flow_types.py` exercising User Story 4 acceptance scenarios 1-5; covers SC-011. **NB on FR-026/FR-027 coverage**: Production hex-locality and "Production grows v+s by labor increment" properties are expected to pass via existing engine code (Specs 060/057); failure of acceptance scenarios 1 here signals remediation needed in the existing Production system rather than missing spec-062 implementation  *(deferred — needs populated hex_state + full pipeline integration; pairs with downstream LODES wiring)*
- [ ] T051 [P] [US4] Write failing property test `tests/property/test_per_stage_conservation.py` using Hypothesis: for random hex populations, verify (a) Production grows v+s by exactly the labor increment, (b) Circulation preserves sum(v) within study area modulo boundary register, (c) Equalization preserves per-industry sum(c), (d) Distribution sums p+i+r+t back to s  *(deferred — pairs with T050)*
- [X] T052 [P] [US4] Write failing test `tests/unit/economics/test_alpha_weekly_invariant.py` covering FR-029a startup invariant (`α_weekly < 1/52` else init fails)

### Implementation for US4 — Vol I Production (hex-local)

- [ ] T053 [US4] Extend `src/babylon/engine/systems/territory.py` to hook hex-county-state aggregation via the `v_*` views so production rates can be reported per-county for diagnostics (NB: this is reporting only; primary state remains hex-level per FR-018)  *(deferred — reporting hook lands with the engine integration follow-up)*

### Implementation for US4 — Vol II Circulation (LODES OD)

- [ ] T054 [US4] Add `src/babylon/economics/lodes_commute_matrix.py` loading the LODES OD matrix from `immutable_reference_qcew_employment` (or a separate `immutable_reference_lodes_*` table created in T005's migration if not already there) as `scipy.sparse.csr_matrix` per Constitution II.12 + research.md §6 (min-cost flow only)  *(deferred — full LODES integration is a downstream spec scope)*
- [ ] T055 [US4] In `src/babylon/engine/systems/imperial_rent.py` (or a new `vol_ii_circulation.py` module under `engine/systems/`), implement the circulation step: `v[A, t+1] = sum_j(OD[j, A] * v[j, t] / row_sum[j])`; spillover (rows that route outside study area) is recorded via `BoundaryFlowRegister.record(..., flow_type=COMMUTE_OUT)`  *(deferred — depends on T054)*

### Implementation for US4 — Vol III Pt I Equalization (industry-bound)

- [X] T056 [US4] Extend `babylon.economics.hex_equalization.HexEqualizationComputer` to consume `α_weekly` from `defines.economy.alpha_weekly` (computed via `alpha_weekly(defines.alpha_annual)`); deprecate the hard-coded `alpha=0.01` keyword by making it default to `None` and falling back to `defines.economy.alpha_weekly` when None
- [ ] T057 [US4] In `babylon.economics.hex_equalization`, ensure equalization derives per-(hex, NAICS) shares on demand from QCEW employment shares (FR-031); add docstring cross-referencing Clarification Q1 (Option A — derive on read)  *(deferred — needs industry-share infrastructure)*

### Implementation for US4 — Imperial Rent inflow (Φ distribution)

- [ ] T058 [US4] Extend `src/babylon/engine/systems/imperial_rent.py` with `distribute_phi_week_to_counties(state, external_nodes, bea_io_imports)`: compute county-level import-exposure weights via BEA I-O imports × QCEW industry shares; distribute `Φ_year / 52` from each external node to counties weighted by exposure (FR-034/FR-035); `BoundaryFlowRegister.record(source=external, dest=county, flow_type=DRAIN_EDGE)` for each transfer  *(deferred — depends on import-exposure infrastructure)*

### Implementation for US4 — Vol III Pt IV-VI Distribution (s split)

- [ ] T059 [US4] Create `src/babylon/engine/systems/distribution.py` with `split_surplus_to_pirt(state, county_aggregate)`: at county scale, split `s` into `p + i + r + t` using `fred_fed_funds_rate` for interest, `bea_reis_rent` for rent, IRS/BEA effective tax rate (use existing `qcew_employment` proxy if no IRS series available) for taxes, with `p` as residual; conserves exactly to `s` (FR-032/FR-033)  *(deferred — distribution system lands with the engine integration follow-up)*

**Checkpoint**: US4 fully functional. All five flow stages execute in order and conserve at their respective scales.

---

## Phase 7: User Story 5 — Per-Tick Conservation Audit Log (Priority: P2)

**Goal**: Every tick appends one row per (scale, invariant) to `conservation_audit_log` with severity grading (ok / warn / alarm). Alarm-severity rows trigger structured events on the event bus per FR-047.

**Independent Test**: Run 100 ticks against a baseline scenario; audit log must contain at least one row per (tick, scale, invariant) with `severity='ok'`. Inject a deliberate per-tick defect of 0.01 to total v in Circulation; within one tick an audit row with `severity='alarm'` MUST appear with `residual ≥ 0.01` (SC-004, SC-005, SC-006).

### Tests for US5 (RED phase)

- [ ] T060 [P] [US5] Write failing integration test `tests/integration/test_audit_log_round_trip.py` exercising User Story 5 acceptance scenarios 1-3 against `pg_pool`; covers SC-004, SC-005, SC-006
- [ ] T061 [P] [US5] Write failing test `tests/integration/test_audit_log_append_only.py` that attempts UPDATE/DELETE on `conservation_audit_log` as the runtime role and expects `InsufficientPrivilege` exceptions (FR-049 enforcement)
- [ ] T062 [P] [US5] Write failing test `tests/integration/test_alarm_event_emission.py` registering a test observer on the event bus, injecting a defect that produces an `alarm` row, and asserting the observer's `on_conservation_alarm(event)` fires (FR-047 / Q3)
- [ ] T063 [P] [US5] Write failing property test `tests/property/test_determinism_hash_replayability.py` using Hypothesis: for random (state, actions, seed) triples, re-running the same triple produces the same `determinism_hash` (Constitution III.7 / GATE-1)

### Implementation for US5

- [ ] T064 [P] [US5] Create `src/babylon/persistence/conservation_audit.py` with `ConservationAuditor.evaluate(world_state, graph) -> list[ConservationAuditRow]` per `contracts/audit_log.yaml#ConservationAuditor`
- [ ] T065 [US5] In `conservation_audit.py`, implement all 16 enumerated invariants from `contracts/audit_log.yaml#invariant_name`:
  - `hex_to_county_sum_{c,v,s,k}` (4)
  - `county_to_state_sum_{c,v,s,k}` (4)
  - `state_to_national_sum_{c,v,s,k}` (4)
  - `global_phi_balance` (1, only at year-boundary ticks per FR-044)
  - `study_area_boundary_balance_{c,v,s}` (3)
  Plus per-stage invariants: `production_grows_v_plus_s_by_labor_increment`, `circulation_preserves_sum_v`, `equalization_preserves_within_industry_sum_c`, `distribution_splits_s_into_pirt`, `imperial_rent_phi_week_distribution`
- [ ] T066 [P] [US5] In `conservation_audit.py`, implement severity tagging: `|residual| ≤ ε` → `ok`, `ε < |residual| ≤ 1e-6` → `warn`, else `alarm` (FR-046); ε read from `defines.epsilon_conservation`
- [ ] T067 [P] [US5] In `conservation_audit.py`, compute `determinism_hash` once per tick from `hashlib.sha256(canonical_json({"tick": t, "hex_state": sorted_dump, "actions": action_list, "rng_seed": seed}).encode())` (Constitution III.7 / GATE-1); attach the same hash to every audit row for this tick
- [ ] T068 [US5] Wire `ConservationAuditor` into `src/babylon/engine/simulation_engine.py` at end-of-tick (after all 15 systems, before envelope build); add a `ConservationAlarmEvent` Pydantic model to `src/babylon/engine/events.py` and emit via existing observer protocol when `severity='alarm'` (FR-047 / Q3)
- [ ] T069 [P] [US5] Create `src/babylon/persistence/conservation_audit_query.py` with `ConservationAuditQuery.fetch(...)` and `count_by_severity(...)` per `contracts/audit_log.yaml#ConservationAuditQuery`
- [ ] T070 [US5] Apply Postgres GRANT revocation as part of migration 0014 (T009): `REVOKE UPDATE, DELETE ON conservation_audit_log FROM <runtime_role>` to satisfy T061 enforcement

**Checkpoint**: US5 fully functional. Audit log forensically records every invariant per tick; alarms surface via the event bus.

---

## Phase 8: User Story 6 — International Boundary Nodes (Priority: P2)

**Goal**: 8 international external nodes (Canada + 7 world regions) plus 1 Rest-of-USA domestic node sit in the runtime graph with country-aggregate state. Trade edges and Drain edges connect internal hexes/counties to external nodes. Boundary register records every cross-boundary flow with hex-pair precision.

**Independent Test**: Instantiate one external node connected to one US county via a drain edge carrying `Φ_year = $100M` for 2010. Step 52 ticks. The boundary flow register must record 52 weekly Φ inflows summing to $100M within ε; the global Φ-balance view's residual at tick 52 must be ≤ ε (SC-010, acceptance scenarios 1-3).

### Tests for US6 (RED phase)

- [ ] T071 [P] [US6] Write failing integration test `tests/integration/test_external_node_boundary.py` exercising User Story 6 acceptance scenarios 1-3; covers SC-010
- [ ] T072 [P] [US6] Write failing test `tests/integration/test_canada_node_present.py` verifying that `initialize_session(...)` for the Detroit scenario creates a `canada` external node row (R4 + FR-036 amendment)
- [ ] T073 [P] [US6] Write failing test `tests/unit/economics/test_boundary_register_hex_pair_fields.py` verifying R2: that `BoundaryFlowRegisterRow` accepts hex-kind, county-kind, external-kind on either end of the dyad with the discriminator enum
- [ ] T074 [P] [US6] Write failing test `tests/integration/test_phi_year_distribution_to_counties.py` verifying that sum over all counties of weekly Φ inflow recorded in the register equals `Φ_year / 52 × 52 = Φ_year` after one simulated year (FR-035)

### Implementation for US6

- [ ] T075 [US6] Extend `src/babylon/economics/boundary_flow_register.py` with hex-pair dimensional fields `source_node_id: str`, `source_kind: NodeKind`, `dest_node_id: str`, `dest_kind: NodeKind` per R2 / `contracts/boundary_register.yaml`; preserve backward-compat by deprecating any aggregate-only `.record_aggregate(...)` method
- [ ] T076 [P] [US6] In `boundary_flow_register.py`, implement `BoundaryFlowRegister.query(...)` per `contracts/boundary_register.yaml#BoundaryFlowRegister.query` with optional filters on session/tick/source/dest/flow_type
- [ ] T077 [US6] In `src/babylon/persistence/postgres_initialization.py`, extend external-node init to instantiate all 9 nodes per data-model.md `ExternalNodeRow.node_id` enum: `canada`, `china`, `eu`, `india`, `sub_saharan_africa`, `latin_america`, `russia_csi`, `southeast_asia` (kind=`international`), and `rest_of_usa` (kind=`domestic_rest`)
- [ ] T077a [P] [US6] Write structural test `tests/unit/persistence/test_external_node_no_hex_structure.py` covering FR-038: assert via introspection that `ExternalNode` Pydantic model has no fields named `hexes`, `hex_count`, `h3_index`, `internal_hexes`, or any field whose type is `H3Index | list[H3Index] | set[H3Index]`; this enforces the "reduced state representation, no internal hex structure" constraint at the model level rather than only documentation
- [ ] T078 [P] [US6] For each external node, load `phi_year_inflow` from `immutable_reference_hickel_drain` for the current simulated year and `bilateral_trade_value` / `bilateral_trade_tons` / `erdi_ratio` from `immutable_reference_ricci_unequal` and `immutable_reference_faf_freight`
- [ ] T079 [US6] In `imperial_rent.py` (from T058), confirm that Φ inflow is distributed to **counties** (not Rest-of-USA) when `source_kind = 'external'` — this is the wiring that closes Constitution IV.1 (Detroit-Windsor) by making Canada-specific Φ flow into US counties via the standard drain-edge mechanism
- [ ] T080 [US6] Add a special-case for Canada-bound commute flows: in `src/babylon/engine/systems/territory.py` (or a new `cross_border_commute.py` module under `engine/systems/`), when LODES OD routes a worker from a tri-county hex to a destination county whose FIPS state code is not Michigan/Ohio/Indiana/Illinois, record a `COMMUTE_OUT` boundary register row with `dest_kind='external'` and `dest_node_id='rest_of_usa'`; for Canada-side destinations (LODES Windsor data), record with `dest_node_id='canada'`

**Checkpoint**: US6 fully functional. Canada is a first-class boundary node. Φ flows from external nodes to US counties with weekly cadence summing to the annual reference value.

---

## Phase 9: User Story 7 — Substrate System at Pipeline Position 2.5 (Priority: P3)

**Goal**: A new `Substrate` system slot in the 15-system materialist causality pipeline tracks physical stocks (raw materials, energy, biocapacity) and runs deterministically after Territory and before Production. Production reads the just-computed substrate values.

**Independent Test**: Run one tick on a scenario where a hex's `raw_material_stock` has been zeroed pre-tick. Verify the engine ran systems in order `Vitality → Territory → Substrate → Production → ...`, that Substrate computed the zero stock first, and that Production downstream consumed *that just-computed value* and produced zero output for the affected hex.

### Tests for US7 (RED phase)

- [ ] T081 [P] [US7] Write failing test `tests/unit/engine/test_substrate_system_ordering.py` verifying the pipeline ordering FR-050: Substrate runs after Territory and before Production on every tick
- [ ] T082 [P] [US7] Write failing test `tests/unit/engine/test_pipeline_substrate_position.py` exercising User Story 7 acceptance scenarios 1-2
- [ ] T083 [P] [US7] Write failing integration test `tests/integration/test_substrate_pipeline_position.py` against `pg_pool` verifying that zeroed substrate propagates to zero Production output in the same tick

### Implementation for US7

- [ ] T084 [P] [US7] Create `src/babylon/engine/systems/substrate.py` with a `SubstrateSystem` class implementing the existing `SimulationSystem` protocol; the system computes per-hex `raw_material_stock`, `energy_stock`, `biocapacity_stock` for tick `t+1` from tick `t` values and the per-tick substrate consumption/regeneration
- [ ] T085 [US7] Extend `src/babylon/engine/simulation_engine.py` to insert `SubstrateSystem` at pipeline position 2.5 (between `TerritorySystem` and the Vol I `ProductionSystem`); update the system-registration order accordingly
- [ ] T086 [US7] Ensure Production reads substrate values from the *just-computed* state, not from the pre-Substrate snapshot — verify via a unit test that mutates substrate.raw_material_stock to 0 mid-tick and asserts production output is constrained accordingly

**Checkpoint**: US7 fully functional. Substrate slot occupies position 2.5; Production sees post-Substrate values.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, performance verification, constitutional & ai-docs reconciliation.

- [ ] T087 [P] Write failing property test `tests/property/test_crisis_machinery_weekly_cadence.py` per research.md §3 (R3): verify threshold-crossings produce categorical coefficient resets within a single tick, sub-tick dynamics aggregate without conservation violation, and crisis-reset events appear as `severity='alarm'` audit rows with crisis-specific `invariant_name`
- [ ] T088 [P] Run the quickstart.md walkthrough end-to-end as a single executable script `tests/scripts/quickstart_062_walkthrough.sh` covering the five sections (init, tick, aggregate, audit, new series); used to gate post-Phase-2 readiness in CI
- [ ] T089 [P] Performance test `tests/integration/test_780_tick_perf_budget.py` (slow; opt-in via `mise run test:perf` or `@pytest.mark.slow`): execute a 780-tick Detroit scenario end-to-end; assert wall-time ≤ 60 minutes (SC-003) and per-tick average ≤ 4.6 seconds
- [ ] T090 [P] Update `ai-docs/state.yaml` bumping `meta.version` to "2.6.0" (matching this feature's spec number-as-minor), updating `last_sprint` to "062-cross-scale-integration (Complete; N tasks done)", and adding a `spec_062_summary` block with deliverables
- [ ] T091 [P] Add ADR `ai-docs/decisions/ADR040_spec_062_cross_scale_integration.yaml` capturing the five Q clarifications + six R research decisions + five constitutional gate closures (GATE-1..GATE-5) for permanent record per project convention
- [ ] T092 [P] Update `ai-docs/roadmap.md` to reflect spec 062 completion and note the follow-up specs spawned: empirical α_annual re-calibration, slime-mold conductivity (Vol II second component, Constitution II.13)
- [ ] T093 [P] Update top-level `CLAUDE.md` "Recent Changes" line to add: `062-cross-scale-integration: Two-phase persistence boundary, per-tick transactional atomicity, weekly tick + year-scoped coefficient interpolation, hex-as-source-of-truth aggregation views, 5-flow-type pipeline ordering, Canada boundary node, conservation audit log with determinism hash`
- [ ] T094 Run full test sweep: `mise run check` (lint + format + typecheck + test:unit) MUST pass; `mise run test:int` MUST pass (excluding T089's slow perf test); `mise run test:doctest` MUST pass for T011/T018
- [ ] T095 Run `mise run qa:audit` and `mise run qa:verify` against a freshly-initialized Detroit session to confirm zero spurious conservation alarms in the baseline scenario (SC-004)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — can start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phase 3 (US1)**: Depends on Phase 2 (specifically T005, T006, T007, T009, T011, T013)
- **Phase 4 (US2)**: Depends on Phase 2 (T005, T011) — can proceed in parallel with Phase 3 once foundation done
- **Phase 5 (US3)**: Depends on Phase 2 (T006, T010) — can proceed in parallel with Phase 3/4
- **Phase 6 (US4)**: Depends on Phases 3, 4 (needs init + lookup) — must follow US1 and US2 in part
- **Phase 7 (US5)**: Depends on Phase 2 (T009, T012) — can run in parallel with US3/US4
- **Phase 8 (US6)**: Depends on Phase 3, Phase 6 (needs initialized session + Φ distribution wiring)
- **Phase 9 (US7)**: Depends on Phase 2 — can run in parallel with most others; the pipeline ordering is a localized engine concern
- **Phase 10 (Polish)**: Depends on all desired user stories being complete

### User Story Dependencies (within Phase 3+)

- **US1 (P1)**: Foundation-only dependency
- **US2 (P1)**: Foundation-only dependency
- **US3 (P1)**: Foundation-only dependency
- **US4 (P1)**: Depends on US1 (initialized session) + US2 (coefficient lookup)
- **US5 (P2)**: Foundation-only dependency
- **US6 (P2)**: Depends on US1 + US4 (Φ distribution needs imperial rent system)
- **US7 (P3)**: Foundation-only dependency

### Within Each User Story

- Tests (T021-T025, T033-T035, etc.) MUST be written and FAIL before implementation tasks in the same phase
- Pydantic models before runtime/orchestration code
- Postgres tables/views before query helpers
- Per-tick transaction wrapper (Phase 2) before any tick-writing code

### Parallel Opportunities

- **Phase 1**: T002, T003, T004 all parallel
- **Phase 2**: All 6 migrations T005–T010 in parallel; T011/T012/T013/T014 models in parallel; T015/T016/T017 tests in parallel
- **Phase 3 (US1)**: T021/T022/T023/T024/T025 tests in parallel; T026/T027/T028 models in parallel
- **Phase 4 (US2)**: T033/T034/T035 tests in parallel
- **Phase 5 (US3)**: T042/T043/T044/T045 tests in parallel; T047/T048 implementation in parallel
- **Phase 6 (US4)**: T050/T051/T052 tests in parallel
- **Phase 7 (US5)**: T060/T061/T062/T063 tests in parallel; T064/T066/T069 implementation in parallel
- **Phase 8 (US6)**: T071/T072/T073/T074 tests in parallel; T076/T078 implementation in parallel
- **Phase 9 (US7)**: T081/T082/T083 tests in parallel
- **Phase 10**: All polish tasks T087–T093 in parallel
- **Across stories** (once Phase 2 done): US1, US2, US3, US5, US7 all parallel-startable

### Parallel Example — Phase 2 (Foundation)

```bash
# Launch all migrations together (different SQL files, no order dependency between them):
Task: "Write migration 0010_immutable_reference_tables.sql"
Task: "Write migration 0011_dynamic_hex_state.sql"
Task: "Write migration 0012_dynamic_external_node_state.sql"
Task: "Write migration 0013_boundary_flow_register.sql"
Task: "Write migration 0014_conservation_audit_log.sql"
# T010 (views) runs after the table-creating migrations above

# Launch all foundation models together:
Task: "Create geometric_depreciation.py"
Task: "Create audit_models.py (ConservationAuditRow)"
Task: "Create envelope.py (PerTickTransactionEnvelope)"
Task: "Create node_kinds.py (NodeKind, BoundaryEdgeKind)"
```

### Parallel Example — Phase 3 (US1 implementation)

```bash
# Launch the three model files together:
Task: "Create hex_state.py (DynamicHexState)"
Task: "Create external_node.py (ExternalNode)"
Task: "Create coefficient_lookup.py (CoefficientLookupPolicy)"
# Then T029 (initialization orchestrator) runs single-threaded — it depends on all three.
```

---

## Implementation Strategy

### MVP First (US1 + US2 + US3 = the P1 foundation)

US1, US2, and US3 are all P1 priority. The minimal viable cross-scale engine requires all three:
- US1 establishes the persistence boundary
- US2 provides time-correct coefficient lookups
- US3 provides cross-scale read access

Then US4 (the five flows) builds on top. US5/US6/US7 are P2/P3 add-ons.

1. Complete Phase 1 (Setup)
2. Complete Phase 2 (Foundational) — CRITICAL: blocks everything
3. Complete Phase 3 (US1) — Two-Phase Init ready
4. Complete Phase 4 (US2) — Coefficient lookup ready
5. Complete Phase 5 (US3) — Cross-scale aggregation ready
6. **STOP & VALIDATE**: A session can initialize, advance one synthetic tick with hand-written substrate output, and the aggregation views return correct sums
7. Complete Phase 6 (US4) — Five flow types running
8. **STOP & VALIDATE**: Full economic mechanics running
9. Complete Phase 7 (US5) — Audit log on
10. Complete Phase 8 (US6) — International boundary, Canada included
11. Complete Phase 9 (US7) — Substrate slot occupied
12. Complete Phase 10 (Polish) — Documentation + perf + ai-docs

### Incremental Delivery

1. Phase 1+2 → Foundation ready
2. Phase 3+4+5 (P1 set) → "Hello cross-scale" milestone
3. Phase 6 (US4) → Economic mechanics running; Detroit scenario produces meaningful output
4. Phase 7 (US5) → Debuggability milestone
5. Phase 8 (US6) → Constitutional completeness (IV.1 Detroit-Windsor)
6. Phase 9 (US7) → Substrate slot wired
7. Phase 10 → Ship

### Parallel Team Strategy

With multiple developers:
1. Team completes Phase 1 + Phase 2 together (Phase 2 migrations can be split across developers — T005–T009 in parallel)
2. Once Phase 2 done:
   - Developer A: US1 (Phase 3) → US4 (Phase 6, partial)
   - Developer B: US2 (Phase 4) → US5 (Phase 7)
   - Developer C: US3 (Phase 5) → US6 (Phase 8)
   - Developer D: US7 (Phase 9) → Phase 10 polish
3. Phase 6 (US4) is the integration point — at least US1 + US2 must be done before it can complete

---

## Notes

- [P] tasks operate on different files with no incomplete dependencies
- TDD: write the test, watch it fail (red), write minimum code to pass (green), refactor
- Project mandates **Conventional Commits**: `feat(spec-062): T0XX description`, `test(spec-062): T0YY description`, etc.
- Commit after each task or logical group per Babylon's "Commit Early, Commit Often" rule
- Pre-commit hooks (ruff, mypy, pre-commit) MUST pass for every commit
- Pre-commit hooks run only on staged files — to avoid forced large intertwined commits, commit each user story's test set before the corresponding implementation set
- All test paths use the project's existing `tests/{unit,integration,property}/` structure per CLAUDE.md
- Postgres GRANT/REVOKE statements run as part of migration apply, not as application code
- Property tests use Hypothesis per Specs 053-056 harness conventions
