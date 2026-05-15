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

- [ ] T018 [P] [US1] Hex hydrator source-discipline unit test in `tests/unit/persistence/test_hex_hydrator_sources.py` — AST-parse `hex_hydrator.py` and assert it imports/queries ONLY the SQLite tables declared in `contracts/hex_hydrator_input.yaml.sqlite_tables_read`. No `fact_atus_*`, no `fact_eviction_lab_*`, no unlisted sources.
- [ ] T019 [P] [US1] Hex hydrator schema-parity test in `tests/unit/persistence/test_trace_view_columns_v2.py` — apply migrations 0020-0023, query `view_runtime_trace_emission` column list, assert it matches the 22 contract columns (minus `simulated_year` which is Python-computed) in canonical order, with the previously-NULL columns sourced from the new subsystem tables.
- [ ] T020 [P] [US1] Hex hydrator real-data integration test in `tests/integration/test_hex_hydrator_real_data.py::test_wayne_county_v_within_qcew_band` — SC-005 acceptance: at `start_year=2010`, `hydrate_hex_state(counties={"26163"})` writes a tick-0 hex_state whose summed `v` per county is within ±50% of `SELECT SUM(total_wages) FROM fact_qcew_annual WHERE county_id = 26163 AND year = 2010` / 52.
- [ ] T021 [P] [US1] Hex hydrator 5-county sample test in `tests/integration/test_hex_hydrator_real_data.py::test_five_counties_v_within_qcew_band` — FR-002b: randomly sample 5 Michigan FIPS, assert each tick-0 `v` is within ±50% of the underlying QCEW reference.
- [ ] T022 [P] [US1] Hex hydrator c/v ratio plausibility test in `tests/integration/test_hex_hydrator_real_data.py::test_c_v_ratio_within_band` — for 5 sampled counties, assert `0.5 ≤ c / v ≤ 5.0` (R2 cross-check).
- [ ] T023 [P] [US1] Bridge hydrate_initial unit test in `tests/unit/engine/headless_runner/test_bridge.py::test_hydrate_initial_builds_worldstate` — given a populated `dynamic_hex_state` at tick 0, `bridge.hydrate_initial(session_id, scope_fips)` returns a `WorldState` whose `entities` and `territories` maps are non-empty.
- [ ] T024 [P] [US1] Bridge persist_tick unit test in `tests/unit/engine/headless_runner/test_bridge.py::test_persist_tick_writes_all_subsystem_tables` — given a `WorldState` with consciousness + demographics + employment fields populated, `bridge.persist_tick(world, tick=5, hash="…")` writes rows to ALL FIVE per-tick subsystem tables (hex_state, external_node_state, boundary_flow_register, consciousness_state, demographics_state, employment_state). Verify via `SELECT COUNT(*) FROM <table>`.
- [ ] T025 [P] [US1] Reference-data window policy test in `tests/integration/test_reference_data_window_policy.py` — three scenarios per FR-022: (a) `start_year=2010 ticks=520` proceeds silently; (b) `start_year=2010 ticks=1000` emits `WARN REFERENCE_DATA_CLAMP: LODES data ends 2021; ticks >= 624` to stderr at session init; (c) requested `start_year=1950` (no QCEW coverage) exits 3 with `ERROR REFERENCE_DATA_MISSING: fact_qcew_annual missing (county=26163, year=1950)`.
- [ ] T026 [US1] Integration smoke `tests/integration/test_engine_bridge.py::test_smoke_tri_county_full_fidelity` — invoke runner with `--scope detroit-tri-county --ticks 5`. Assert exit 0, all 3 artifacts written, `trace.csv` has exactly 15 data rows (3 × 5), every county-applicable cell is non-empty, `summary.terminal_state.counties_alive = 3` with non-zero `total_v` / `total_c` / `total_s` / `total_k`.
- [ ] T027 [US1] Integration determinism `tests/integration/test_engine_bridge.py::test_determinism` — two runs with `--seed 2010 --ticks 5 --scope detroit-tri-county`, `trace.csv` files MUST be byte-identical; manifest `input_hash` MUST match.
- [ ] T028 [US1] Integration tick-over-tick evolution `tests/integration/test_engine_bridge.py::test_tick_over_tick_evolution` — SC-004: assert ≥3 columns from `{v, c, s, k, p_acquiescence, p_revolution, ideology_r/l/f, surveillance_coupling, internet_access_pct, biocapacity_stock, energy_stock, raw_material_stock, employment_proxy}` show ≥5% relative change between tick 0 and tick 5 for ≥1 county.
- [ ] T029 [US1] Integration zero-empty-cells `tests/integration/test_engine_bridge.py::test_zero_empty_cells` — SC-001: for every `entity_kind="county"` row in `trace.csv`, every column declared `applies_to: ["county", ...]` carries a non-null value.

### Hex hydrator upgrade (FR-002a + FR-002b — sequential edits to same file)

- [ ] T030 [US1] Refactor `src/babylon/persistence/hex_hydrator.py` — replace placeholder ratio `c = 2v` with the BEA county GDP × intermediate-inputs-fraction formula per `contracts/hex_hydrator_input.yaml.per_column_sources.c` and `research.md §R2`. Read from `fact_bea_county_gdp` and `fact_bea_national_industry`.
- [ ] T031 [US1] Refactor `src/babylon/persistence/hex_hydrator.py` — replace placeholder `v` formula with `SUM(fact_qcew_annual.total_wages) / 52` per `contracts/hex_hydrator_input.yaml.per_column_sources.v` and `research.md §R7`.
- [ ] T032 [US1] Refactor `src/babylon/persistence/hex_hydrator.py` — replace `s = 0` with the derived residual `(GDP / 52) - v - c`, clamped to `≥ 0`. On negative residual, emit an audit row with `severity="warn"` (defer to a single audit-row-emission helper).
- [ ] T033 [US1] Refactor `src/babylon/persistence/hex_hydrator.py` — replace `k = 10v` with `capital_output_ratio × fact_bea_county_gdp.gdp_millions × 1e6` where `capital_output_ratio = 3.0` per `contracts/hex_hydrator_input.yaml.per_column_sources.k.constants`.
- [ ] T034 [US1] Refactor `src/babylon/persistence/hex_hydrator.py` — replace uniform `surveillance_coupling = 0.3` and `internet_access_pct = 0.7` with the per-county FCC formulas: `clip(0.3 + 0.4 × broadband.pct_100_20 + 0.3 × coercive.facility_count_normalized, 0, 1)` and `broadband.pct_25_3` directly.
- [ ] T035 [US1] Refactor `src/babylon/persistence/hex_hydrator.py` — replace `energy_stock = raw_material_stock = biocapacity/2` with the per-county allocations per `contracts/hex_hydrator_input.yaml.per_column_sources` (`fact_state_minerals` × population-share for energy, × area-share for raw materials, `fact_hickel_erdi_annual` × land-area-share for biocapacity).
- [ ] T036 [US1] Extend `src/babylon/persistence/postgres_initialization.py::initialize_session` with the FR-022 three-mode reference-data window preflight: silent / warn-and-clamp / hard-refuse (exit 3 with named-triple error message). Implement the per-metric data-window probe as a set of `SELECT MAX(year), MIN(year)` queries against the listed reference tables.

### Subsystem row writers (parallel — distinct files)

- [ ] T037 [P] [US1] Implement `DynamicConsciousnessState.from_worldstate(world, tick, fips)` constructor helper in `src/babylon/persistence/county_state.py`: reads `world.consciousness_simplex[fips]` and `world.entities[fips].p_acquiescence/p_revolution`.
- [ ] T038 [P] [US1] Implement `DynamicDemographicsState.from_worldstate(world, tick, fips)` in `src/babylon/persistence/county_state.py`: reads `world.demographics_per_county[fips]`.
- [ ] T039 [P] [US1] Implement `DynamicEmploymentState.from_worldstate(world, tick, fips)` in `src/babylon/persistence/county_state.py`: reads `world.employment_per_county[fips]`.

### Bridge implementation (sequential — same file)

- [ ] T040 [US1] Implement `WorldStateBridge.hydrate_initial(session_id, scope_fips) → WorldState` in `src/babylon/engine/headless_runner/bridge.py`. Queries `view_runtime_trace_emission` at `tick = 0` for the scope, plus `dynamic_external_node_state` for boundary nodes, and assembles a `WorldState` Pydantic instance.
- [ ] T041 [US1] Implement `WorldStateBridge.persist_tick(world, tick, determinism_hash) → None` in `src/babylon/engine/headless_runner/bridge.py`. Serializes WorldState → 6 row-lists (hex/external/boundary/audit/consciousness/demographics/employment); constructs envelope; calls `runtime.persist_tick_atomic`.

### Runner refactor (sequential — same file)

- [ ] T042 [US1] Replace `_carry_forward_tick` (current no-op) in `src/babylon/engine/headless_runner/runner.py` with a real tick body that invokes `engine.run_tick(world.graph, services, context)` on the in-memory `WorldState`. Remove the tick-virtualization optimization (`_query_trace` no longer materializes per-tick copies; `_query_terminal_aggregates` and `_county_terminal_snapshot` read the actual terminal tick).
- [ ] T043 [US1] Wire `WorldStateBridge` into `runner.run()`: replace direct `runtime.persist_tick_atomic` calls with `bridge.persist_tick(world, tick, hash)`. Move `world = bridge.hydrate_initial(...)` into the session-init phase, after `initialize_session()` returns.
- [ ] T044 [US1] Update `_query_terminal_aggregates` and `_county_terminal_snapshot` in `runner.py` to query the actual terminal tick (from `result.ticks_completed - 1`), not hardcoded tick 0.

**Checkpoint**: US1 MVP fully functional. The 22-column trace.csv contract is populated with real per-tick-varying values for the canonical 520-tick Michigan + Canada run.

---

## Phase 4: User Story 2 — Conservation invariants continuously audited (Priority: P2)

**Goal**: ConservationAuditor runs end-of-tick; violations surface in `summary.conservation_audit`; `--strict` flag exits 1 on first `critical` row; `qa:e2e-regression` mise task enables `--strict`.

**Independent Test**: Run with a monkey-patched ImperialRentSystem that skips a phi-distribution write for one tick. Confirm `summary.conservation_audit` contains at least one entry with `severity ∈ {"error", "critical"}` at the injected tick. Run again with `--strict`; confirm exit 1.

### Tests for User Story 2

- [ ] T045 [P] [US2] ConservationAuditor wiring unit test in `tests/unit/engine/headless_runner/test_runner_audit_wiring.py` — assert `SimulationEngine` is constructed with `auditor=ConservationAuditor(...)` and `auditor.audit_end_of_tick(...)` is invoked once per tick.
- [ ] T046 [P] [US2] Severity mapping test in `tests/unit/engine/headless_runner/test_audit_severity_mapping.py` — assert Postgres severities (`ok` / `warn` / `alarm`) map to contract severities (`info` / `warning` / `error`) deterministically.
- [ ] T047 [P] [US2] `--strict` early-exit integration test in `tests/integration/test_conservation_audit_strict.py::test_strict_exits_one_on_critical` — inject a critical audit row at tick 50, run with `--strict --ticks 100`, assert exit code 1, `summary.run_metadata.ticks_completed = 51`, partial artifacts written, stderr matches `ERROR ENGINE_FAILURE: critical conservation violation at tick 50 | partial_artifacts=/...`.
- [ ] T048 [P] [US2] `--strict-off` continues-on-critical test in `tests/integration/test_conservation_audit_strict.py::test_non_strict_continues_on_critical` — same injection without `--strict`, assert exit 0, full ticks completed, violation visible in `summary.conservation_audit`.

### Implementation for User Story 2

- [ ] T049 [US2] Construct `ConservationAuditor` in `runner.run()` (before the tick loop) and pass to `SimulationEngine(systems=..., auditor=auditor)`. Wire `auditor.audit_end_of_tick(...)` to be called at end of each tick after `engine.run_tick`, before `bridge.persist_tick`.
- [ ] T050 [US2] Implement `--strict` early-exit logic in `_tick_loop`: after each `bridge.persist_tick`, query the just-committed audit rows from `auditor.audit_log_buffer`; if any row has `severity = "alarm"` (Postgres) and `config.strict` is True, raise `_StrictAbort` which the outer `try` block catches and translates to exit code 1.
- [ ] T051 [US2] Implement `_query_audit_log` severity remapping in `runner.py` per FR-011: `ok → info`, `warn → warning`, `alarm → error` (or `critical` per case heuristic).
- [ ] T052 [US2] Update `.mise.toml` `qa:e2e-regression` task to invoke runner with `--strict` (per FR-012a).

**Checkpoint**: Conservation auditor wired; `--strict` semantics tested; CI gate uses strict mode.

---

## Phase 5: User Story 3 — External boundary flows persist per tick (Priority: P2)

**Goal**: `BoundaryFlowRegister` flushed per tick; rows land in `boundary_flow_register` Postgres table; `summary.external_node_flows` aggregates real per-tick Canada inflows/outflows.

**Independent Test**: Run the canonical sim. Query `boundary_flow_register` for the session; confirm > 0 rows. Cross-check `summary.external_node_flows.canada.total_phi_inflow` against the sum of `magnitude` for `flow_type="drain_edge"` rows targeting Canada. Match within 1 cent.

### Tests for User Story 3

- [ ] T053 [P] [US3] BoundaryFlowRegister wiring test in `tests/integration/test_external_node_flows.py::test_register_rows_persisted` — run canonical sim; assert `SELECT COUNT(*) FROM boundary_flow_register WHERE session_id = … AND dest_node_id = 'canada' AND flow_type = 'drain_edge'` returns > 0.
- [ ] T054 [P] [US3] Aggregation cross-check test in `tests/integration/test_external_node_flows.py::test_aggregation_matches_register` — `summary.external_node_flows.canada.total_phi_inflow` equals the Postgres-side `SUM(magnitude)` query (per FR-014). Tolerance: 1 cent.

### Implementation for User Story 3

- [ ] T055 [US3] Wire `BoundaryFlowRegister` instantiation into `runner.run()` (one register per session). Pass into `engine.run_tick(...)` via `services` container.
- [ ] T056 [US3] After each `engine.run_tick`, call `register.flush()` and add the resulting rows to `envelope.boundary_register_rows` before `bridge.persist_tick`.
- [ ] T057 [US3] Implement `_aggregate_external_node_flows(pool, session_id)` in `src/babylon/engine/headless_runner/run_summary.py`: SQL `SUM(magnitude) FILTER (WHERE flow_type = ...)` grouped by `(source_node_id, dest_node_id)`; produces one entry per external node with `total_phi_inflow`, `total_trade_inbound`, `total_commute_outbound`, `tick_count_with_inflow` fields.

**Checkpoint**: External boundary flows populate `summary.external_node_flows` with real per-tick magnitudes.

---

## Phase 6: User Story 4 — End-game detection wired (Priority: P3)

**Goal**: `--endgame-detector` CLI flag accepts a dotted import path; runner resolves via `importlib`; polls detector at end of every tick; on positive detection halts loop, sets `exit_reason="early_terminated"` and `end_game_event` in summary. Closes spec-064 T024a + T033.

**Independent Test**: Inject an `EndgameDetector` that fires `IMPERIAL_COLLAPSE` at tick 250. Run with `--ticks 1000 --endgame-detector tests.integration.fixtures.endgame.ImperialCollapseAtTick250`. Confirm exit 0, `ticks_completed = 251`, `summary.run_metadata.exit_reason = "early_terminated"`, `summary.end_game_event.tick = 250`, `summary.end_game_event.condition = "IMPERIAL_COLLAPSE"`.

### Tests for User Story 4

- [ ] T058 [P] [US4] `--endgame-detector` argparse acceptance test in `tests/unit/engine/test_argparse_cli.py::test_endgame_detector_accepts_dotted_path` — assert the flag accepts a string and stores it in `args.endgame_detector`.
- [ ] T059 [P] [US4] Detector resolution unit test in `tests/unit/engine/headless_runner/test_endgame_resolution.py` — `bridge.set_endgame_detector("invalid.module.NotADetector")` raises `ConfigError`; valid path resolves to an instance implementing the `EndgameDetector` Protocol.
- [ ] T060 [P] [US4] Test fixture `tests/integration/fixtures/endgame.py` exposing `ImperialCollapseAtTick250` (always fires at tick 250) and `NeverFires` (returns None always).
- [ ] T061 [P] [US4] End-game round-trip integration test in `tests/integration/test_endgame_detection_round_trip.py::test_imperial_collapse_at_tick_250` — per US4 Independent Test above.
- [ ] T062 [P] [US4] No-detector default test in `tests/integration/test_endgame_detection_round_trip.py::test_no_detector_runs_full_ticks` — without `--endgame-detector`, run to full `--ticks`, `exit_reason = "completed"`, `end_game_event` absent from summary.

### Implementation for User Story 4

- [ ] T063 [US4] Implement `WorldStateBridge.set_endgame_detector(dotted_path)` and `WorldStateBridge.poll_endgame(world, tick)` in `bridge.py` per `contracts/engine_bridge_protocol.yaml.methods`. Use `importlib.import_module` + `getattr` for resolution; raise `ConfigError` on failure or Protocol mismatch.
- [ ] T064 [US4] Wire `poll_endgame` into `runner._tick_loop`: after `bridge.persist_tick(...)`, call `bridge.poll_endgame(world, tick)`; if it returns a non-None `EndgameEvent`, store it on the result and break out of the loop with `exit_reason = EARLY_TERMINATED`.
- [ ] T065 [US4] Populate `summary.end_game_event` in `run_summary.build_summary(...)` when `exit_reason == EARLY_TERMINATED` and an `end_game_event` payload was captured.

**Checkpoint**: End-game detection wired; spec-064 T024a + T033 closed.

---

## Phase 7: User Story 5 — Artifacts capture discrete narrative events (Priority: P3)

**Goal**: Every `EventType` fired during the tick loop appears in `summary.json.events` in deterministic emission order (FR-018). LLM agents can answer "what happened narratively" from artifacts alone.

**Independent Test**: Run canonical sim. Confirm `summary.events` is a list (possibly empty). For each entry: `tick ∈ [0, ticks_completed)`, `event_type` is a documented enum value, `entity_ids` is a list (possibly empty), `severity ∈ {info, warning, error, critical}`, `details` is an object.

### Tests for User Story 5

- [ ] T066 [P] [US5] EventCapture core unit test in `tests/unit/engine/headless_runner/test_event_capture.py::test_capture_appends_in_order` — call `set_tick(3)` then `on_event(e1); on_event(e2)`, then `set_tick(4)` and `on_event(e3)`; `drain()` returns `(e1, e2, e3)` in that order with tick 3, 3, 4 respectively.
- [ ] T067 [P] [US5] Determinism test in `tests/unit/engine/headless_runner/test_event_capture.py::test_emission_order_deterministic` — same fixture inputs across two `EventCapture` instances produce byte-identical `drain()` output.
- [ ] T068 [P] [US5] Events schema integration test in `tests/integration/test_events_capture.py::test_events_array_schema` — run canonical sim; assert `summary.events` is a list; each entry has the 5 required keys; cross-check that `summary.events[*].tick` is strictly non-decreasing (FR-018 inter-tick ordering).
- [ ] T069 [P] [US5] Events round-trip integration test in `tests/integration/test_events_capture.py::test_engine_emitted_event_visible_in_summary` — monkey-patch `ImperialRentSystem` to fire a synthetic `SuperwageCrisisEvent` at tick 7 for FIPS `26163`; assert `summary.events` contains an entry with `tick=7`, `event_type="SUPERWAGE_CRISIS"`, `entity_ids=["26163"]`.

### Implementation for User Story 5

- [ ] T070 [US5] Implement `EngineEvent` Pydantic model + `EventCapture` class in `src/babylon/engine/headless_runner/event_capture.py` per `data-model.md §1.2 + §1.3`. Methods: `set_tick(tick)`, `on_event(event)`, `drain() -> tuple[EngineEvent, ...]`.
- [ ] T071 [US5] Subscribe `EventCapture.on_event` to the engine's `EventBus` inside `bridge.hydrate_initial` (per `contracts/engine_bridge_protocol.yaml.hydrate_initial.side_effects`).
- [ ] T072 [US5] In runner's tick loop, call `event_capture.set_tick(tick)` BEFORE `engine.run_tick(...)` so emissions during that tick are tagged correctly.
- [ ] T073 [US5] In `run_summary.build_summary(...)`, drain `event_capture` and pass the resulting list as the new `events` argument; emit into `summary.events` per `data-model.md §3.1`.

**Checkpoint**: Engine events captured to artifact; FR-018 emission-order rule enforced by unit test.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: SC-002 wallclock budget verification, SC-012 invariant suite gate, SC-011 `final_state` restoration, manifest extensions, ai-docs sync, baseline refresh.

### Performance gates

- [ ] T074 [P] Per-system wallclock tracking in `run_summary.py` — add `per_system_ms: dict[str, float]` to the `performance` block (per `data-model.md §3.2`). Source: time each `system.step(...)` call inside `engine.run_tick` via a thin wrapper, accumulate over the run.
- [ ] T075 [P] Tri-county wallclock smoke test in `tests/integration/test_engine_bridge.py::test_tri_county_wallclock_smoke` (R9 pass 1) — `--scope detroit-tri-county --ticks 520`, assert exit 0, record per-tick mean ms.
- [ ] T076 SC-002 canonical wallclock budget test in `tests/integration/test_engine_bridge.py::test_canonical_wallclock_budget` (R9 pass 3) — `--scope michigan-canada --ticks 520`, assert `summary.performance.tick_loop_sec ≤ 600`. Skipped unless `BABYLON_SLOW_TESTS=1`.

### Invariant suite gate (SC-012)

- [ ] T077 Run the full spec-053/054/055/056 Hypothesis invariant suite against a fully-bridged canonical run via `tests/integration/test_invariant_suite_under_bridge.py`. Skipped unless `BABYLON_SLOW_TESTS=1`. Asserts every property in the suite passes against the engine-bridged trace.

### SC-011 `tools/shared.run_simulation` fidelity restoration

- [ ] T078 [P] Signature-snapshot test update in `tests/unit/tools/test_shared_signature.py` — confirm the byte-stable signature still matches per spec-064 FR-015 (no signature change).
- [ ] T079 Restore `final_state = result.final_world_state` in `tools/shared.run_simulation` so legacy callers regain `state.entities` / `state.territories` access per SC-011.
- [ ] T080 Restore `max_tension` (max EXPLOITATION edge tension across all ticks), `final_wealth` (sum of terminal-tick entity wealth), `phase_milestones` (per-phase tick numbers filtered from `result.events`), and `terminal_outcome` (from `TerminalDecisionEvent` in events) in `tools/shared.run_simulation` per `research.md §R8`.

### Manifest extensions

- [ ] T081 [P] Add `engine_systems_invoked: list[str]` field to `manifest.json.reproducibility.deterministic_inputs` in `src/babylon/engine/headless_runner/manifest.py` per `data-model.md §4.1`. Source: `[s.__class__.__name__ for s in engine.systems]`. Ensure it participates in `input_hash` computation.

### ai-docs sync

- [ ] T082 [P] Author `ai-docs/decisions/ADR042_spec_065_engine_bridging.yaml` documenting: (a) the hex hydrator becomes real-data-driven; (b) the bridge is the canonical hydrate-run-write surface; (c) the canonical run is rescoped to 520 ticks / 2010-2020; (d) `view_runtime_trace_emission` v2 sources from three new subsystem tables. Update `ai-docs/decisions/index.yaml` accordingly.
- [ ] T083 [P] Update `ai-docs/state.yaml` to v2.8.0 with `spec_065_summary` block (mirror the v2.7.0 spec-064 summary structure).
- [ ] T084 [P] Update `ai-docs/tooling.yaml` to document the new `--strict` and `--endgame-detector` flags and the changed `--ticks` defaults for `sim:e2e-michigan` / `qa:e2e-regression`.

### Baseline refresh

- [ ] T085 Regenerate `tests/baselines/michigan-e2e.json` from a fresh full Michigan-statewide bridged run. Document the regeneration command in the commit message. The new baseline includes real `terminal_state` aggregates + populated `events` array + populated `external_node_flows`.

### Final sweeps

- [ ] T086 Run the full `quickstart.md` walkthrough end-to-end (operator path + LLM-agent path + CI engineer path) and fix any drift discovered.
- [ ] T087 Run `mise run check` and fix any lint / mypy / pre-commit fallout introduced by the new modules + refactored hex hydrator + runner refactor.

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
  - Subsystem writers T037-T039 parallel.
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
- **Phase 3 US1 subsystem writers**: T037 ∥ T038 ∥ T039 — 3-way parallel.
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
upgrade), T037–T039 (subsystem writers), and T040–T044 (bridge + runner
refactor) take them green.

---

## Format Validation

Every task in this file satisfies the strict format:
`- [ ] T### [P?] [Story?] Description with file path`

- ✓ All 87 tasks begin with `- [ ]`
- ✓ All tasks have unique sequential IDs T001–T087
- ✓ Parallelizable tasks marked `[P]`
- ✓ User-story tasks have `[US1]` / `[US2]` / `[US3]` / `[US4]` / `[US5]` labels
- ✓ Setup / Foundational / Polish tasks have no story labels
- ✓ Every task description includes a concrete file path

---

## Summary

- **Total tasks**: 87
- **Phase 1 (Setup)**: 5 tasks (T001–T005)
- **Phase 2 (Foundational)**: 12 tasks (T006–T017)
- **Phase 3 (US1, MVP)**: 27 tasks (T018–T044) — 12 tests + 15 implementation
- **Phase 4 (US2)**: 8 tasks (T045–T052) — 4 tests + 4 implementation
- **Phase 5 (US3)**: 5 tasks (T053–T057) — 2 tests + 3 implementation
- **Phase 6 (US4)**: 8 tasks (T058–T065) — 5 tests + 3 implementation
- **Phase 7 (US5)**: 8 tasks (T066–T073) — 4 tests + 4 implementation
- **Phase 8 (Polish)**: 14 tasks (T074–T087)
- **MVP scope**: T001–T044 (~44 tasks) — ships full-fidelity trace.csv + summary terminal aggregates from real engine math; audit/boundary/endgame/events follow as US2-US5
- **Highest parallelism**: Phase 3 US1 tests (8-way), Phase 8 polish (7-way), Phase 6 US4 tests (5-way)
- **Independent test criteria**: Documented per user story (see Phase 3/4/5/6/7 headers)
