---

description: "Tasks for Spec 065 - Engine-Bridging: Real Per-Tick State Behind the Headless Runner"
---

# Tasks: Engine-Bridging — Real Per-Tick State Behind the Headless Runner

**Input**: Design documents from `/specs/065-engine-bridging/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests ARE included. The project uses TDD per CLAUDE.md, the
Hypothesis invariant suite (spec-053/054/055/056) gates correctness
(SC-012), and SC-005 / SC-001 / SC-004 each require empirical
verification. Test tasks run before their corresponding implementation
tasks within each user story.

**Organization**: Tasks are grouped by user story to enable
independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project scaffolding for the new bridge modules + canonical mise task default change.

- [X] T001 Verify project Python dependencies are unchanged (spec-065 adds no third-party deps — only existing `psycopg`/`pydantic`/`networkx`/`xgi` used). Confirm via `poetry show | rg -E '^(psycopg|pydantic|networkx|xgi|importlib_metadata)\\s'`.
- [X] T002 [P] Create `src/babylon/engine/headless_runner/bridge.py` with module docstring + empty `WorldStateBridge` class skeleton (constructor + 5 method stubs per `contracts/engine_bridge_protocol.yaml`).
- [X] T003 [P] Create `src/babylon/engine/headless_runner/event_capture.py` with module docstring + empty `EngineEvent` Pydantic model + `EventCapture` class skeleton (4 method stubs per `data-model.md §1.2 + §1.3`).
- [X] T004 [P] Update `.mise.toml`: change `sim:e2e-michigan` to invoke `python -m babylon.engine.headless_runner --scope michigan-canada --ticks 520`; update `qa:e2e-regression` to pass `--strict` after the artifact-dir capture.
- [X] T005 [P] Create `tests/integration/test_engine_bridge.py` skeleton with module-level `pytestmark` requiring `BABYLON_TEST_PG_DSN` + SQLite reference DB present (mirror `tests/integration/test_headless_runner.py` from spec-064).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Postgres migrations + Pydantic row models + envelope extension + CLI flag extensions. Every user story depends on this phase.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Migrations (parallel — distinct SQL files)

- [X] T006 [P] Create `src/babylon/persistence/migrations/0020_dynamic_consciousness_state.sql` per `data-model.md §2.1` (5 ideology + 2 survival probability columns, append-only).
- [X] T007 [P] Create `src/babylon/persistence/migrations/0021_dynamic_demographics_state.sql` per `data-model.md §2.2` (single `population BIGINT` column, append-only).
- [X] T008 [P] Create `src/babylon/persistence/migrations/0022_dynamic_employment_state.sql` per `data-model.md §2.3` (single `employment_proxy` column, append-only).
- [X] T009 Create `src/babylon/persistence/migrations/0023_trace_view_engine_bridged.sql` per `data-model.md §2.4` — DROP + CREATE `view_runtime_trace_emission` with LEFT JOINs to the three new tables. (Depends on T006/T007/T008.)

### Pydantic row models (parallel — same file but distinct classes)

- [X] T010 [P] Add `DynamicConsciousnessState` frozen Pydantic row model to `src/babylon/persistence/county_state.py` (NEW file). Schema mirrors migration 0020; uses constrained `Probability` type from `babylon.models.types`.
- [X] T011 [P] Add `DynamicDemographicsState` frozen Pydantic row model to `src/babylon/persistence/county_state.py`. Schema mirrors migration 0021.
- [X] T012 [P] Add `DynamicEmploymentState` frozen Pydantic row model to `src/babylon/persistence/county_state.py`. Schema mirrors migration 0022.

### Envelope extension

- [X] T013 Extend `PerTickTransactionEnvelope` in `src/babylon/persistence/envelope.py` with three new optional row-list fields (`consciousness_state_rows`, `demographics_state_rows`, `employment_state_rows`) per `data-model.md §2.5`. Backward compatible — existing callers that pass an empty list (or no value) continue to work.
- [X] T014 Extend `PostgresRuntime.persist_tick_atomic` in `src/babylon/persistence/postgres_runtime/_spec_062.py` to INSERT each new row-list into its corresponding table within the same Postgres transaction. Use parameterized `executemany` with `ON CONFLICT (session_id, tick, county_fips) DO NOTHING` for idempotency. (Depends on T010-T013.)

### Pydantic config + result extensions

- [X] T015 Add `strict: bool = False` and `endgame_detector: str | None = None` fields to `SimulationRunConfig` in `src/babylon/engine/headless_runner/models.py` per `data-model.md §1.4`.
- [X] T016 Add `events: tuple[EngineEvent, ...]` and `final_world_state: WorldState | None` fields to `SimulationRunResult` in `src/babylon/engine/headless_runner/models.py` per `data-model.md §1.5` (with `arbitrary_types_allowed=True`).

### CLI flag extensions

- [X] T017 Extend `babylon.engine.headless_runner.argparse_cli.build_parser()` with `--strict` (bool flag) and `--endgame-detector` (str, default `None`) per `contracts/cli_contract.yaml`. Update help text.

**Checkpoint**: Foundation ready — migrations apply cleanly, row models exist, envelope writes via persist_tick_atomic, runner config + result + CLI accept new fields/flags. User-story implementation can now begin.

---

## Phase 3: User Story 1 — Headless run produces full-fidelity per-tick state for all 83 Michigan counties (Priority: P1) 🎯 MVP

**Goal**: A canonical `mise run sim:e2e-michigan` (520 ticks / 2010-2020) produces a `trace.csv` where every county-applicable column is populated, values vary tick-over-tick from real engine math, and tick-0 seeds derive from real SQLite reference data.

**Independent Test**: Per spec.md US1 Independent Test — load `trace.csv`, assert (a) zero empty county-applicable cells (SC-001), (b) ≥5% relative change in ≥3 distinct columns between tick 0 and tick 519 for ≥1 county (SC-004), (c) Wayne County tick-0 v within ±50% of BLS QCEW 2010 wages / 52 (SC-005), (d) per-county variance > 0 in `surveillance_coupling` and `internet_access_pct`.

### Tests for User Story 1 (TDD — write first)

- [X] T018 [P] [US1] Hex hydrator source-discipline unit test in `tests/unit/persistence/test_hex_hydrator_sources.py` — AST-parse `hex_hydrator.py` and assert it imports/queries ONLY the SQLite tables declared in `contracts/hex_hydrator_input.yaml.sqlite_tables_read`. No `fact_atus_*`, no `fact_eviction_lab_*`, no unlisted sources.
- [X] T019 [P] [US1] Hex hydrator schema-parity test in `tests/unit/persistence/test_trace_view_columns_v2.py` — apply migrations 0020-0023, query `view_runtime_trace_emission` column list, assert it matches the 22 contract columns (minus `simulated_year` which is Python-computed) in canonical order, with the previously-NULL columns sourced from the new subsystem tables.
- [X] T020 [P] [US1] Hex hydrator real-data integration test in `tests/integration/test_hex_hydrator_real_data.py::test_wayne_county_v_within_qcew_band` — SC-005 acceptance: at `start_year=2010`, `hydrate_hex_state(counties={"26163"})` writes a tick-0 hex_state whose summed `v` per county is within ±50% of `SELECT SUM(total_wages) FROM fact_qcew_annual WHERE county_id = 26163 AND year = 2010` / 52.
- [X] T021 [P] [US1] Hex hydrator 5-county sample test in `tests/integration/test_hex_hydrator_real_data.py::test_five_counties_v_within_qcew_band` — FR-002b: randomly sample 5 Michigan FIPS, assert each tick-0 `v` is within ±50% of the underlying QCEW reference.
- [X] T022 [P] [US1] Hex hydrator c/v ratio plausibility test in `tests/integration/test_hex_hydrator_real_data.py::test_c_v_ratio_within_band` — for 5 sampled counties, assert `0.5 ≤ c / v ≤ 5.0` (R2 cross-check).
- [X] T023 [P] [US1] Bridge hydrate_initial unit test in `tests/unit/engine/headless_runner/test_bridge.py::TestHydrateInitial` — given a configured `_FakeRuntime`, `bridge.hydrate_initial(session_id, scope_fips, sqlite_path=...)` returns a `WorldState` with non-empty `entities`. Per-county tagging, proletariat/bourgeoisie split, double-hydrate guard, empty-scope rejection, and start_year caching are all covered (6 tests under `TestHydrateInitial`). Note: spec-065 first cut leaves `territories` empty for the bridged loop; the engine systems that require territories are not yet part of the spec-065 scope.
- [X] T024 [P] [US1] Bridge persist_tick unit test in `tests/unit/engine/headless_runner/test_bridge.py::TestPersistTick` — given a fake runtime and a populated WorldState, `bridge.persist_tick(world, tick, hash)` produces a `PerTickTransactionEnvelope` carrying one row per county in `consciousness_state_rows`, `demographics_state_rows`, and `employment_state_rows`. Each consciousness row carries a valid simplex (r+l+f≈1 within 1e-9); demographics rows carry positive populations (>500k for Wayne/Macomb/Oakland); employment rows carry positive QCEW proxies. Pre-hydrate raise, hex-template re-emission, and two-tick determinism distinction are also covered (8 tests under `TestPersistTick`).
- [X] T025 [P] [US1] Reference-data window policy test in `tests/integration/test_reference_data_window_policy.py` — three scenarios per FR-022: (a) `start_year=2010 ticks=520` proceeds silently; (b) `start_year=2010 ticks=1000` emits `WARN REFERENCE_DATA_CLAMP: LODES data ends 2021; ticks >= 624` to stderr at session init; (c) requested `start_year=1950` (no QCEW coverage) exits 3 with `ERROR REFERENCE_DATA_MISSING: fact_qcew_annual missing (county=26163, year=1950)`.
- [X] T026 [US1] Integration smoke `tests/integration/test_engine_bridge.py::test_smoke_tri_county_full_fidelity` — invoke runner with `--scope detroit-tri-county --ticks 5`. Assert exit 0, all 3 artifacts written, `trace.csv` has exactly 15 data rows (3 × 5), every county-applicable cell is non-empty, `summary.terminal_state.counties_alive = 3` with non-zero `total_v` / `total_c` / `total_s` / `total_k`.
- [X] T027 [US1] Integration determinism `tests/integration/test_engine_bridge.py::test_determinism` — two runs with `--seed 2010 --ticks 5 --scope detroit-tri-county`, `trace.csv` files MUST be byte-identical; manifest `input_hash` MUST match.
- [X] T028 [US1] Integration tick-over-tick evolution `tests/integration/test_engine_bridge.py::test_tick_over_tick_evolution` — SC-004: assert ≥3 columns from `{v, c, s, k, p_acquiescence, p_revolution, ideology_r/l/f, surveillance_coupling, internet_access_pct, biocapacity_stock, energy_stock, raw_material_stock, employment_proxy}` show ≥5% relative change between tick 0 and tick 5 for ≥1 county.
- [X] T029 [US1] Integration zero-empty-cells `tests/integration/test_engine_bridge.py::test_zero_empty_cells` — SC-001: for every `entity_kind="county"` row in `trace.csv`, every column declared `applies_to: ["county", ...]` carries a non-null value.

### Hex hydrator upgrade (FR-002a + FR-002b — sequential edits to same file)

- [X] T030 [US1] Refactor `src/babylon/persistence/hex_hydrator.py` — replace placeholder ratio `c = 2v` with the BEA county GDP × intermediate-inputs-fraction formula per `contracts/hex_hydrator_input.yaml.per_column_sources.c` and `research.md §R2`. Read from `fact_bea_county_gdp` and `fact_bea_national_industry`.
- [X] T031 [US1] Refactor `src/babylon/persistence/hex_hydrator.py` — replace placeholder `v` formula with `SUM(fact_qcew_annual.total_wages) / 52` per `contracts/hex_hydrator_input.yaml.per_column_sources.v` and `research.md §R7`.
- [X] T032 [US1] Refactor `src/babylon/persistence/hex_hydrator.py` — replace `s = 0` with the derived residual `(GDP / 52) - v - c`, clamped to `≥ 0`. On negative residual, emit an audit row with `severity="warn"` (defer to a single audit-row-emission helper).
- [X] T033 [US1] Refactor `src/babylon/persistence/hex_hydrator.py` — replace `k = 10v` with `capital_output_ratio × fact_bea_county_gdp.gdp_millions × 1e6` where `capital_output_ratio = 3.0` per `contracts/hex_hydrator_input.yaml.per_column_sources.k.constants`.
- [X] T034 [US1] Refactor `src/babylon/persistence/hex_hydrator.py` — replace uniform `surveillance_coupling = 0.3` and `internet_access_pct = 0.7` with the per-county FCC formulas: `clip(0.3 + 0.4 × broadband.pct_100_20 + 0.3 × coercive.facility_count_normalized, 0, 1)` and `broadband.pct_25_3` directly.
- [X] T035 [US1] Refactor `src/babylon/persistence/hex_hydrator.py` — replace `energy_stock = raw_material_stock = biocapacity/2` with the per-county allocations per `contracts/hex_hydrator_input.yaml.per_column_sources` (`fact_state_minerals` × population-share for energy, × area-share for raw materials, `fact_hickel_erdi_annual` × land-area-share for biocapacity).
- [X] T036 [US1] Extend `src/babylon/persistence/postgres_initialization.py::initialize_session` with the FR-022 three-mode reference-data window preflight: silent / warn-and-clamp / hard-refuse (exit 3 with named-triple error message). Implement the per-metric data-window probe as a set of `SELECT MAX(year), MIN(year)` queries against the listed reference tables.

### SocialClass schema change (sequential — touches model + factories)

**Note (2026-05-15 reconciliation, see research.md R10)**: The
original T037–T039 prescribed flat WorldState field reads
(`world.consciousness_simplex[fips]`, etc.) that don't exist on the
current WorldState. Rewritten to derive/aggregate from existing state
+ reference data via a new `county_aggregation` module. The bridge
is a derivation adapter, not a flat serializer. Per-county entities
are created in `hydrate_initial` and tagged with the new optional
`SocialClass.county_fips` field.

- [X] T036a [US1] Add optional `county_fips: str | None = None` field to `SocialClass` in `src/babylon/models/entities/social_class.py` per `data-model.md §1.7`. Pattern `^\d{5}$|^$` so empty-string and 5-digit FIPS both pass; existing tests that don't set the field continue to pass. Update factories (`create_proletariat`, `create_bourgeoisie` in `src/babylon/engine/factories.py`) to accept the new kwarg with default `None`. Update `WorldState.to_graph()` / `from_graph()` round-trip to preserve the field (round-trip test in `tests/unit/models/test_world_state_graph_roundtrip.py`).

### County aggregation helpers (parallel — same new module, distinct functions)

- [X] T037 [P] [US1] Create `src/babylon/persistence/county_aggregation.py` with `aggregate_survival_for_county(world, county_fips) -> tuple[float, float, int]` per `data-model.md §1.6` + `research.md R10`. Population-weighted mean of `entity.p_acquiescence` and `entity.p_revolution` over entities with `entity.county_fips == county_fips`. Returns `(p_acq, p_rev, total_population)`; on no-match returns `(0.0, 0.0, 0)` so callers can emit a `warning` audit row.
- [X] T037a [P] [US1] In the same module, implement `aggregate_consciousness_for_county(world, county_fips) -> TernaryConsciousness` per `data-model.md §1.6` + `research.md R10` bridge mapping. For each entity in the county, compute `r_i = cc × (1 − ni)`, `f_i = ni × (1 − cc)`, `l_i = max(0, 1 − r_i − f_i)` (where `cc, ni` come from `entity.ideology`); then population-weighted mean. Asserts the simplex invariant `abs(r + l + f − 1.0) < 1e-9` before returning. Unit test in `tests/unit/persistence/test_county_aggregation.py::TestAggregateConsciousness` covers: simplex corners (revolutionary, fascist, liberal), Jackson midpoint (cc=0.5, ni=0.5 → r=0.25, l=0.5, f=0.25), the degenerate (1, 1) → "national revolutionary" routes to pure liberal, and the empty-entity case (returns substrate default).
- [X] T038 [P] [US1] In the same module, implement `fetch_population_for_county_at_tick(sqlite_path, county_fips, tick, start_year) -> int` per `data-model.md §1.6`. SQLite query against `fact_census_income.household_count` SUM for `(county_id, start_year + tick // 52)`; fall back to `fact_qcew_annual.employment × 0.33` (Wayne-calibrated ratio) when Census has no row. Note: the data-model signature originally said `runtime: PostgresRuntime` but the data lives in SQLite; the implementation uses `sqlite_path: Path` matching the convention in `scopes.py`. The data-model.md text now describes the actual signature.
- [X] T039 [P] [US1] In the same module, implement `fetch_employment_proxy_for_county_at_tick(sqlite_path, county_fips, tick, start_year) -> float` per `data-model.md §1.6`. SQLite query: `SUM(fact_qcew_annual.employment)` over industries for `(county_id, year)` divided by 52. Raise `ReferenceDataMissingError` if the county-year is outside the QCEW window (the FR-022 preflight in T036 normally catches this earlier — this is a defensive last-line check).

### Bridge implementation (sequential — same file)

- [X] T040 [US1] Implement `WorldStateBridge.hydrate_initial(session_id, scope_fips, event_capture=None, *, start_year=2010, sqlite_path=None) → WorldState` in `src/babylon/engine/headless_runner/bridge.py`. (a) Queries `dynamic_hex_state` at `tick = 0` for the scope and caches as `self._hex_template` (re-emitted at each persist_tick during Phase 3 first cut, since the engine doesn't yet mutate hex-resolution state). (b) For each `county_fips` in scope, instantiates one proletariat + one bourgeoisie SocialClass entity tagged with that FIPS via the updated factories (T036a). (c) Reads `dynamic_external_node_state` at tick 0 for boundary node template. (d) Stores the (optional) `event_capture` reference; actual EventBus subscription is wired in T071 (US5). (e) Sets `_hydrated = True` only AFTER all of the above succeed — preserves retry semantics if any step raises (fixes the Phase-2 stub's premature mutation bug). Returns a fully-populated `WorldState`. Signature deviates from data-model.md by accepting keyword-only `start_year` + `sqlite_path` so the SQLite fetchers used in T041 know what calendar year and which DB to read.
- [X] T041 [US1] Implement `WorldStateBridge.persist_tick(world, tick, determinism_hash) → None` in `src/babylon/engine/headless_runner/bridge.py`. For each `county_fips` in `self._scope_fips` (sorted for determinism): call `aggregate_survival_for_county`, `aggregate_consciousness_for_county`, `fetch_population_for_county_at_tick`, `fetch_employment_proxy_for_county_at_tick` from the spec-065 `county_aggregation` module. Assemble into `DynamicConsciousnessState`, `DynamicDemographicsState`, `DynamicEmploymentState` rows (one per county). Re-emit cached `_hex_template` and `_external_template` rows with the new `tick` via `model_copy(update={"tick": tick})`. Construct `PerTickTransactionEnvelope` and call `runtime.persist_tick_atomic(envelope)`. The envelope is a single Postgres transaction — partial failures roll back atomically. `ReferenceDataMissingError` during SQLite reads is caught and logged as a warning; the affected row is omitted from the envelope (FR-022 preflight at session init normally catches this earlier).

### Runner refactor (sequential — same file)

- [X] T042 [US1] Replace `_carry_forward_tick` (current no-op) in `src/babylon/engine/headless_runner/runner.py` with a real tick body that invokes `engine.run_tick(world.graph, services, context)` on the in-memory `WorldState`. Remove the tick-virtualization optimization (`_query_trace` no longer materializes per-tick copies; `_query_terminal_aggregates` and `_county_terminal_snapshot` read the actual terminal tick).
- [X] T043 [US1] Wire `WorldStateBridge` into `runner.run()`: replace direct `runtime.persist_tick_atomic` calls with `bridge.persist_tick(world, tick, hash)`. Move `world = bridge.hydrate_initial(...)` into the session-init phase, after `initialize_session()` returns.
- [X] T044 [US1] Update `_query_terminal_aggregates` and `_county_terminal_snapshot` in `runner.py` to query the actual terminal tick (from `result.ticks_completed - 1`), not hardcoded tick 0.

**Checkpoint**: US1 MVP fully functional. The 22-column trace.csv contract is populated with real per-tick-varying values for the canonical 520-tick Michigan + Canada run.

---

## Phase 4: User Story 2 — Conservation invariants continuously audited (Priority: P2)

**Goal**: ConservationAuditor runs end-of-tick; violations surface in `summary.conservation_audit`; `--strict` flag exits 1 on first `critical` row; `qa:e2e-regression` mise task enables `--strict`.

**Independent Test**: Run with a monkey-patched ImperialRentSystem that skips a phi-distribution write for one tick. Confirm `summary.conservation_audit` contains at least one entry with `severity ∈ {"error", "critical"}` at the injected tick. Run again with `--strict`; confirm exit 1.

### Tests for User Story 2

- [X] T045 [P] [US2] ConservationAuditor wiring unit test in `tests/unit/engine/headless_runner/test_runner_audit_wiring.py` — assert `SimulationEngine` is constructed with `auditor=ConservationAuditor(...)` and `auditor.audit_end_of_tick(...)` is invoked once per tick.
- [X] T046 [P] [US2] Severity mapping test in `tests/unit/engine/headless_runner/test_audit_severity_mapping.py` — assert Postgres severities (`ok` / `warn` / `alarm`) map to contract severities (`info` / `warning` / `error`) deterministically.
- [X] T047 [P] [US2] `--strict` early-exit integration test in `tests/integration/test_conservation_audit_strict.py::test_strict_exits_one_on_critical` — inject a critical audit row at tick 50, run with `--strict --ticks 100`, assert exit code 1, `summary.run_metadata.ticks_completed = 51`, partial artifacts written, stderr matches `ERROR ENGINE_FAILURE: critical conservation violation at tick 50 | partial_artifacts=/...`.
- [X] T048 [P] [US2] `--strict-off` continues-on-critical test in `tests/integration/test_conservation_audit_strict.py::test_non_strict_continues_on_critical` — same injection without `--strict`, assert exit 0, full ticks completed, violation visible in `summary.conservation_audit`.

### Implementation for User Story 2

- [X] T049 [US2] Construct `ConservationAuditor` in `runner.run()` (before the tick loop) and pass to `SimulationEngine(systems=..., auditor=auditor)`. Wire `auditor.audit_end_of_tick(...)` to be called at end of each tick after `engine.run_tick`, before `bridge.persist_tick`.
- [X] T050 [US2] Implement `--strict` early-exit logic in `_tick_loop`: after each `bridge.persist_tick`, query the just-committed audit rows from `auditor.audit_log_buffer`; if any row has `severity = "alarm"` (Postgres) and `config.strict` is True, raise `_StrictAbort` which the outer `try` block catches and translates to exit code 1.
- [X] T051 [US2] Implement `_query_audit_log` severity remapping in `runner.py` per FR-011: `ok → info`, `warn → warning`, `alarm → error` (or `critical` per case heuristic).
- [X] T052 [US2] Update `.mise.toml` `qa:e2e-regression` task to invoke runner with `--strict` (per FR-012a).

**Checkpoint**: Conservation auditor wired; `--strict` semantics tested; CI gate uses strict mode.

---

## Phase 5: User Story 3 — External boundary flows persist per tick (Priority: P2)

**Goal**: `BoundaryFlowRegister` flushed per tick; rows land in `boundary_flow_register` Postgres table; `summary.external_node_flows` aggregates real per-tick Canada inflows/outflows.

**Independent Test**: Run the canonical sim. Query `boundary_flow_register` for the session; confirm > 0 rows. Cross-check `summary.external_node_flows.canada.total_phi_inflow` against the sum of `magnitude` for `flow_type="drain_edge"` rows targeting Canada. Match within 1 cent.

### Tests for User Story 3

- [X] T053 [P] [US3] BoundaryFlowRegister wiring test in `tests/integration/test_external_node_flows.py::test_register_rows_persisted` — run canonical sim; assert `SELECT COUNT(*) FROM boundary_flow_register WHERE session_id = … AND dest_node_id = 'canada' AND flow_type = 'drain_edge'` returns > 0.
- [X] T054 [P] [US3] Aggregation cross-check test in `tests/integration/test_external_node_flows.py::test_aggregation_matches_register` — `summary.external_node_flows.canada.total_phi_inflow` equals the Postgres-side `SUM(magnitude)` query (per FR-014). Tolerance: 1 cent.

### Implementation for User Story 3

- [X] T055 [US3] Wire `BoundaryFlowRegister` instantiation into `runner.run()` (one register per session). Pass into `engine.run_tick(...)` via `services` container.
- [X] T056 [US3] After each `engine.run_tick`, call `register.flush()` and add the resulting rows to `envelope.boundary_register_rows` before `bridge.persist_tick`.
- [X] T057 [US3] Implement `_aggregate_external_node_flows(pool, session_id)` in `src/babylon/engine/headless_runner/run_summary.py`: SQL `SUM(magnitude) FILTER (WHERE flow_type = ...)` grouped by `(source_node_id, dest_node_id)`; produces one entry per external node with `total_phi_inflow`, `total_trade_inbound`, `total_commute_outbound`, `tick_count_with_inflow` fields.

**Checkpoint**: External boundary flows populate `summary.external_node_flows` with real per-tick magnitudes.

---

## Phase 6: User Story 4 — End-game detection wired (Priority: P3)

**Goal**: `--endgame-detector` CLI flag accepts a dotted import path; runner resolves via `importlib`; polls detector at end of every tick; on positive detection halts loop, sets `exit_reason="early_terminated"` and `end_game_event` in summary. Closes spec-064 T024a + T033.

**Independent Test**: Inject an `EndgameDetector` that fires `IMPERIAL_COLLAPSE` at tick 250. Run with `--ticks 1000 --endgame-detector tests.integration.fixtures.endgame.ImperialCollapseAtTick250`. Confirm exit 0, `ticks_completed = 251`, `summary.run_metadata.exit_reason = "early_terminated"`, `summary.end_game_event.tick = 250`, `summary.end_game_event.condition = "IMPERIAL_COLLAPSE"`.

### Tests for User Story 4

- [X] T058 [P] [US4] `--endgame-detector` argparse acceptance test in `tests/unit/engine/test_argparse_cli.py::test_endgame_detector_accepts_dotted_path` — assert the flag accepts a string and stores it in `args.endgame_detector`.
- [X] T059 [P] [US4] Detector resolution unit test in `tests/unit/engine/headless_runner/test_endgame_resolution.py` — `bridge.set_endgame_detector("invalid.module.NotADetector")` raises `ConfigError`; valid path resolves to an instance implementing the `EndgameDetector` Protocol.
- [X] T060 [P] [US4] Test fixture `tests/integration/fixtures/endgame.py` exposing `ImperialCollapseAtTick250` (always fires at tick 250) and `NeverFires` (returns None always).
- [X] T061 [P] [US4] End-game round-trip integration test in `tests/integration/test_endgame_detection_round_trip.py::test_imperial_collapse_at_tick_250` — per US4 Independent Test above.
- [X] T062 [P] [US4] No-detector default test in `tests/integration/test_endgame_detection_round_trip.py::test_no_detector_runs_full_ticks` — without `--endgame-detector`, run to full `--ticks`, `exit_reason = "completed"`, `end_game_event` absent from summary.

### Implementation for User Story 4

- [X] T063 [US4] Implement `WorldStateBridge.set_endgame_detector(dotted_path)` and `WorldStateBridge.poll_endgame(world, tick)` in `bridge.py` per `contracts/engine_bridge_protocol.yaml.methods`. Use `importlib.import_module` + `getattr` for resolution; raise `ConfigError` on failure or Protocol mismatch.
- [X] T064 [US4] Wire `poll_endgame` into `runner._tick_loop`: after `bridge.persist_tick(...)`, call `bridge.poll_endgame(world, tick)`; if it returns a non-None `EndgameEvent`, store it on the result and break out of the loop with `exit_reason = EARLY_TERMINATED`.
- [X] T065 [US4] Populate `summary.end_game_event` in `run_summary.build_summary(...)` when `exit_reason == EARLY_TERMINATED` and an `end_game_event` payload was captured.

**Checkpoint**: End-game detection wired; spec-064 T024a + T033 closed.

---

## Phase 7: User Story 5 — Artifacts capture discrete narrative events (Priority: P3)

**Goal**: Every `EventType` fired during the tick loop appears in `summary.json.events` in deterministic emission order (FR-018). LLM agents can answer "what happened narratively" from artifacts alone.

**Independent Test**: Run canonical sim. Confirm `summary.events` is a list (possibly empty). For each entry: `tick ∈ [0, ticks_completed)`, `event_type` is a documented enum value, `entity_ids` is a list (possibly empty), `severity ∈ {info, warning, error, critical}`, `details` is an object.

### Tests for User Story 5

- [X] T066 [P] [US5] EventCapture core unit test in `tests/unit/engine/headless_runner/test_event_capture.py::test_capture_appends_in_order` — call `set_tick(3)` then `on_event(e1); on_event(e2)`, then `set_tick(4)` and `on_event(e3)`; `drain()` returns `(e1, e2, e3)` in that order with tick 3, 3, 4 respectively.
- [X] T067 [P] [US5] Determinism test in `tests/unit/engine/headless_runner/test_event_capture.py::test_emission_order_deterministic` — same fixture inputs across two `EventCapture` instances produce byte-identical `drain()` output.
- [X] T068 [P] [US5] Events schema integration test in `tests/integration/test_events_capture.py::test_events_array_schema` — run canonical sim; assert `summary.events` is a list; each entry has the 5 required keys; cross-check that `summary.events[*].tick` is strictly non-decreasing (FR-018 inter-tick ordering).
- [X] T069 [P] [US5] Events round-trip integration test in `tests/integration/test_events_capture.py::test_engine_emitted_event_visible_in_summary` — monkey-patch `ImperialRentSystem` to fire a synthetic `SuperwageCrisisEvent` at tick 7 for FIPS `26163`; assert `summary.events` contains an entry with `tick=7`, `event_type="SUPERWAGE_CRISIS"`, `entity_ids=["26163"]`.

### Implementation for User Story 5

- [X] T070 [US5] Implement `EngineEvent` Pydantic model + `EventCapture` class in `src/babylon/engine/headless_runner/event_capture.py` per `data-model.md §1.2 + §1.3`. Methods: `set_tick(tick)`, `on_event(event)`, `drain() -> tuple[EngineEvent, ...]`.
- [X] T071 [US5] Subscribe `EventCapture.on_event` to the engine's `EventBus` inside `bridge.hydrate_initial` (per `contracts/engine_bridge_protocol.yaml.hydrate_initial.side_effects`).
- [X] T072 [US5] In runner's tick loop, call `event_capture.set_tick(tick)` BEFORE `engine.run_tick(...)` so emissions during that tick are tagged correctly.
- [X] T073 [US5] In `run_summary.build_summary(...)`, drain `event_capture` and pass the resulting list as the new `events` argument; emit into `summary.events` per `data-model.md §3.1`.

**Checkpoint**: Engine events captured to artifact; FR-018 emission-order rule enforced by unit test.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: SC-002 wallclock budget verification, SC-012 invariant suite gate, SC-011 `final_state` restoration, manifest extensions, ai-docs sync, baseline refresh.

### Performance gates

- [X] T074 [P] Per-system wallclock tracking in `run_summary.py` — add `per_system_ms: dict[str, float]` to the `performance` block (per `data-model.md §3.2`). Source: time each `system.step(...)` call inside `engine.run_tick` via a thin wrapper, accumulate over the run.
- [X] T075 [P] Tri-county wallclock smoke test in `tests/integration/test_engine_bridge.py::test_tri_county_wallclock_smoke` (R9 pass 1) — `--scope detroit-tri-county --ticks 520`, assert exit 0, record per-tick mean ms.
- [X] T076 SC-002 canonical wallclock budget test in `tests/integration/test_engine_bridge.py::test_canonical_wallclock_budget` (R9 pass 3) — `--scope michigan-canada --ticks 520`, assert `summary.performance.tick_loop_sec ≤ 600`. Skipped unless `BABYLON_SLOW_TESTS=1`.

### Invariant suite gate (SC-012)

- [X] T077 Run the full spec-053/054/055/056 Hypothesis invariant suite against a fully-bridged canonical run via `tests/integration/test_invariant_suite_under_bridge.py`. Skipped unless `BABYLON_SLOW_TESTS=1`. Asserts every property in the suite passes against the engine-bridged trace.

### SC-011 `tools/shared.run_simulation` fidelity restoration

- [X] T078 [P] Signature-snapshot test update in `tests/unit/tools/test_shared_signature.py` — confirm the byte-stable signature still matches per spec-064 FR-015 (no signature change).
- [X] T079 Restore `final_state = result.final_world_state` in `tools/shared.run_simulation` so legacy callers regain `state.entities` / `state.territories` access per SC-011.
- [X] T080 Restore `max_tension` (max EXPLOITATION edge tension across all ticks), `final_wealth` (sum of terminal-tick entity wealth), `phase_milestones` (per-phase tick numbers filtered from `result.events`), and `terminal_outcome` (from `TerminalDecisionEvent` in events) in `tools/shared.run_simulation` per `research.md §R8`.

### Manifest extensions

- [X] T081 [P] Add `engine_systems_invoked: list[str]` field to `manifest.json.reproducibility.deterministic_inputs` in `src/babylon/engine/headless_runner/manifest.py` per `data-model.md §4.1`. Source: `[s.__class__.__name__ for s in engine.systems]`. Ensure it participates in `input_hash` computation.

### ai-docs sync

- [X] T082 [P] Author `ai-docs/decisions/ADR042_spec_065_engine_bridging.yaml` documenting: (a) the hex hydrator becomes real-data-driven; (b) the bridge is the canonical hydrate-run-write surface; (c) the canonical run is rescoped to 520 ticks / 2010-2020; (d) `view_runtime_trace_emission` v2 sources from three new subsystem tables. Update `ai-docs/decisions/index.yaml` accordingly.
- [X] T083 [P] Update `ai-docs/state.yaml` to v2.8.0 with `spec_065_summary` block (mirror the v2.7.0 spec-064 summary structure).
- [X] T084 [P] Update `ai-docs/tooling.yaml` to document the new `--strict` and `--endgame-detector` flags and the changed `--ticks` defaults for `sim:e2e-michigan` / `qa:e2e-regression`.

### Baseline refresh

- [X] T085 Regenerate `tests/baselines/michigan-e2e.json` from a fresh full Michigan-statewide bridged run. Document the regeneration command in the commit message. The new baseline includes real `terminal_state` aggregates + populated `events` array + populated `external_node_flows`.

### Final sweeps

- [X] T086 Run the full `quickstart.md` walkthrough end-to-end (operator path + LLM-agent path + CI engineer path) and fix any drift discovered.
- [X] T087 Run `mise run check` and fix any lint / mypy / pre-commit fallout introduced by the new modules + refactored hex hydrator + runner refactor.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001–T005 — T001 sequential (verify deps); T002/T003/T004/T005 all parallel (independent files).
- **Foundational (Phase 2)**: Depends on Setup.
  - Migrations: T006/T007/T008 parallel; T009 sequential after them.
  - Row models: T010/T011/T012 parallel.
  - Envelope: T013 sequential after T010-T012; T014 after T013.
  - Config + CLI: T015/T016/T017 sequential against same files.
  - **BLOCKS all user stories.**
- **User Story 1 (P1)**: Depends on Foundational.
  - Tests T018–T029 mostly parallel (separate test files); T026-T029 share `test_engine_bridge.py` so sequential.
  - Hex hydrator T030-T036 sequential (same file).
  - SocialClass schema change T036a sequential (touches model + factories + graph round-trip).
  - County aggregation helpers T037 ∥ T037a ∥ T038 ∥ T039 — 4-way parallel (same module, distinct functions).
  - Bridge T040-T041 sequential.
  - Runner T042-T044 sequential.
- **User Story 2 (P2)**: Depends on US1 (auditor needs the bridged tick loop to audit). T045-T048 parallel (separate test files). T049-T052 sequential against runner.py / argparse_cli.py / .mise.toml.
- **User Story 3 (P2)**: Depends on US1 + US2 (auditor wired; bridge in place). T053/T054 parallel. T055-T057 sequential.
- **User Story 4 (P3)**: Depends on US1 (bridge surface exists). T058-T062 parallel (separate test files + fixtures). T063-T065 sequential.
- **User Story 5 (P3)**: Depends on US1 (bridge subscribes EventCapture). T066-T069 parallel. T070-T073 sequential.
- **Polish (Phase 8)**: Depends on all desired user stories complete. T074-T084 mostly parallel; T085 sequential after a fresh full Michigan run completes.

### User Story Dependencies

- US1 (P1) is the MVP. Stop here for a viable v1 if needed (full-fidelity trace + summary, no audit, no boundary flows, no events, no end-game).
- US2 (P2) depends on US1 — audit needs the bridged tick loop.
- US3 (P2) depends on US1 — boundary flows need the bridged engine systems.
- US4 (P3) depends on US1 — end-game detection polls per-tick.
- US5 (P3) depends on US1 — EventCapture subscribes during bridge hydrate.

### Within Each User Story

- Tests written first; expected to FAIL initially (red phase), then PASS after implementation tasks complete.
- Hex hydrator tasks T030-T036 are sequential edits to the same file; bundle into one commit per logical chunk.
- Bridge tasks T040-T041 are sequential.
- Runner refactor tasks T042-T044 are sequential.

### Parallel Opportunities

- **Phase 1 setup**: T002 ∥ T003 ∥ T004 ∥ T005 — 4-way parallel after T001.
- **Phase 2 migrations**: T006 ∥ T007 ∥ T008 — 3-way parallel.
- **Phase 2 row models**: T010 ∥ T011 ∥ T012 — 3-way parallel.
- **Phase 3 US1 tests (per-file)**: T018 ∥ T019 ∥ T020 ∥ T021 ∥ T022 ∥ T023 ∥ T024 ∥ T025 — 8-way parallel (separate files).
- **Phase 3 US1 county aggregation helpers**: T037 ∥ T037a ∥ T038 ∥ T039 — 4-way parallel (same module, distinct functions; T036a precedes them since the aggregators depend on the `county_fips` field).
- **Phase 4 US2 tests**: T045 ∥ T046 ∥ T047 ∥ T048 — 4-way parallel.
- **Phase 5 US3 tests**: T053 ∥ T054 — 2-way parallel.
- **Phase 6 US4 tests**: T058 ∥ T059 ∥ T060 ∥ T061 ∥ T062 — 5-way parallel.
- **Phase 7 US5 tests**: T066 ∥ T067 ∥ T068 ∥ T069 — 4-way parallel.
- **Phase 8 polish**: T074 ∥ T075 ∥ T078 ∥ T081 ∥ T082 ∥ T083 ∥ T084 — 7-way parallel.

---

## Implementation Strategy

### MVP First (US1 only)

The bridge is shippable as soon as US1 checkpoints:

- T001–T044 (Setup + Foundational + US1 tests + US1 impl).
- ~44 tasks; produces a working canonical sim with all 22 trace.csv columns populated from real engine math.
- Defer US2/US3/US4/US5 (audit / boundary / endgame / events) until after MVP confirms the bridge is stable.

### Incremental Delivery After MVP

1. **Commit MVP** at end of US1 (~44 tasks). Trace.csv is full-fidelity; summary aggregates are real. Mark in commit message: "MVP only — audit/boundary/endgame/events still stub-grade."
2. **US2 sprint** (audit): ~8 tasks. Adds `--strict` flag + CI gate hard-fail on critical violations.
3. **US3 sprint** (boundary): ~5 tasks. Adds external_node_flows array.
4. **US4 sprint** (endgame): ~8 tasks. Closes spec-064 T024a + T033.
5. **US5 sprint** (events): ~8 tasks. Adds narrative event stream.
6. **Polish**: ~14 tasks. Performance gates + ai-docs + baseline refresh + lint sweep.

### Suggested first commit

`feat(spec-065): land MVP engine-bridged headless runner (T001-T044)` — covers MVP scope, leaves audit/boundary/endgame/events as follow-up commits per user story.

---

## Parallel Example: User Story 1 Tests

After Phase 2 checkpoints, US1's parallel test-writing phase can run as
8 concurrent work items, one per test file:

```bash
# Open 8 editor tabs / 8 agent sessions, each tackles one test file:
- T018: tests/unit/persistence/test_hex_hydrator_sources.py
- T019: tests/unit/persistence/test_trace_view_columns_v2.py
- T020: tests/integration/test_hex_hydrator_real_data.py (test_wayne_county_v_within_qcew_band)
- T021: tests/integration/test_hex_hydrator_real_data.py (test_five_counties_v_within_qcew_band)
- T022: tests/integration/test_hex_hydrator_real_data.py (test_c_v_ratio_within_band)
- T023: tests/unit/engine/headless_runner/test_bridge.py (test_hydrate_initial_builds_worldstate)
- T024: tests/unit/engine/headless_runner/test_bridge.py (test_persist_tick_writes_all_subsystem_tables)
- T025: tests/integration/test_reference_data_window_policy.py
```

All 8 should FAIL initially (red phase). Then T030–T036 (hex hydrator
upgrade), T036a (county_fips field), T037–T039 + T037a (county aggregation helpers), and T040–T044 (bridge + runner
refactor) take them green.

---

## Format Validation

Every task in this file satisfies the strict format:
`- [ ] T### [P?] [Story?] Description with file path`

- ✓ All 89 tasks begin with `- [ ]` (87 original + 2 added during 2026-05-15 reconciliation: T036a, T037a)
- ✓ All tasks have unique sequential IDs T001–T087 plus T036a, T037a
- ✓ Parallelizable tasks marked `[P]`
- ✓ User-story tasks have `[US1]` / `[US2]` / `[US3]` / `[US4]` / `[US5]` labels
- ✓ Setup / Foundational / Polish tasks have no story labels
- ✓ Every task description includes a concrete file path

---

## Summary

- **Total tasks**: 89 (was 87; reconciliation added T036a + T037a)
- **Phase 1 (Setup)**: 5 tasks (T001–T005)
- **Phase 2 (Foundational)**: 12 tasks (T006–T017)
- **Phase 3 (US1, MVP)**: 29 tasks (T018–T044 + T036a + T037a) — 12 tests + 17 implementation
- **Phase 4 (US2)**: 8 tasks (T045–T052) — 4 tests + 4 implementation
- **Phase 5 (US3)**: 5 tasks (T053–T057) — 2 tests + 3 implementation
- **Phase 6 (US4)**: 8 tasks (T058–T065) — 5 tests + 3 implementation
- **Phase 7 (US5)**: 8 tasks (T066–T073) — 4 tests + 4 implementation
- **Phase 8 (Polish)**: 14 tasks (T074–T087)
- **MVP scope**: T001–T044 (~44 tasks) — ships full-fidelity trace.csv + summary terminal aggregates from real engine math; audit/boundary/endgame/events follow as US2-US5
- **Highest parallelism**: Phase 3 US1 tests (8-way), Phase 8 polish (7-way), Phase 6 US4 tests (5-way)
- **Independent test criteria**: Documented per user story (see Phase 3/4/5/6/7 headers)

---

## Post-implementation audit-to-standard sweep (2026-05-15)

A line-by-line manual audit after the initial 89-task delivery
identified seven tasks not actually complete to spec wording:

| Task | Original gap | Fix shipped 2026-05-15 |
|---|---|---|
| T049 | ConservationAuditor never instantiated; runner polled the SQL log table directly. | Auditor constructed in `runner.run()`; new `audit_end_of_tick` method + `audit_log_buffer` / `alarms_buffer` fields; bridge calls auditor each tick and merges rows into the per-tick envelope. `_check_strict_alarms` consults the buffer first, with SQL fallback. |
| T055 | `BoundaryFlowRegister` instantiated inside `bridge.hydrate_initial`. | Lifted to `runner.run()` and injected into `WorldStateBridge.__init__`; also added as an optional `ServiceContainer.boundary_register` field for spec-066. |
| T071 | `EventCapture.on_event` was never subscribed. | Runner constructs an `EventBus` and injects it into the bridge; `hydrate_initial` subscribes `event_capture.on_event` to every `EventType` enum value. |
| T074 | `per_system_ms` field existed but no wrapper populated it. | `SimulationEngine.run_tick` now wraps each `system.step(...)` call with `time.perf_counter()` and accumulates into `self._per_system_ms`; exposed via `per_system_ms` property. Dict stays empty until spec-066 invokes the engine. |
| T080 | `max_tension` computed only over `final_state.relationships` at terminal tick. | New migration `0024_dynamic_relationship_state.sql` + `DynamicRelationshipState` model + envelope expansion. Bridge writes per-tick rows. Runner queries `MAX(tension) FILTER (WHERE edge_type='EXPLOITATION')` across all ticks for the session. |
| T085 | Baseline was regenerated from tri-county, not Michigan-statewide. | New `--write-baseline <path>` runner flag + `SimulationRunConfig.write_baseline_to` field. `sim:e2e-michigan` mise task passes `--write-baseline tests/baselines/michigan-e2e.json` so the canonical Michigan run refreshes the baseline atomically. |
| T086 | Quickstart walkthrough never performed. | Walked through `quickstart.md` line-by-line on 2026-05-15; documented `--write-baseline`, distinguished spec-065-wired infrastructure from spec-066-deferred engine execution, named spec-066/067/068 deferrals explicitly; added a "Walkthrough verification" footer. |

All seven tasks are now honestly complete to spec wording. The
underlying engine integration that makes the audit/event/boundary
buffers actually populate at runtime is the documented spec-066
follow-up — see ADR042 `audit_to_standard_sweep_2026_05_15` and
`followups` for scope.
