---

description: "Tasks for Spec 066 - Marx-Coherence Fixes"
---

# Tasks: Marx-Coherence Fixes

**Input**: Design documents from `/specs/066-marx-coherence-fixes/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests ARE included. The project uses TDD per CLAUDE.md, the
Hypothesis invariant suite (spec-053/054/055/056) gates correctness,
and SC-001 through SC-015 each require empirical verification. Test
tasks run before their corresponding implementation tasks within each
user story.

**Organization**: Tasks are grouped by user story to enable
independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Test scaffolding and infrastructure for the spec-066 bug-fix sweep.

- [ ] T001 Verify project Python dependencies are unchanged (spec-066 adds no third-party deps — only Pydantic 2.x, NetworkX 3.x, psycopg 3.x, scipy already in pyproject.toml). Confirm via `poetry show | rg -E '^(psycopg|pydantic|networkx|xgi|scipy|hypothesis)\\s'`.
- [ ] T002 [P] Create `tests/integration/test_marx_identities.py` skeleton with module-level `pytestmark = [pytest.mark.integration, pytest.mark.skipif(not BABYLON_TEST_PG_DSN, ...)]` mirroring `tests/integration/test_engine_bridge.py`.
- [ ] T003 [P] Create `tests/integration/test_consciousness_evolution.py` skeleton with the same pytestmark plus `pytest.mark.skipif(BABYLON_SLOW_TESTS != "1", ...)` for the 520-tick assertions.
- [ ] T004 [P] Create `tests/unit/persistence/test_hex_hydrator_marx.py` skeleton (Bug A unit tests).
- [ ] T005 [P] Create `tests/unit/persistence/test_employment_proxy_units.py` skeleton (Bug B unit tests).
- [ ] T006 [P] Create `tests/unit/persistence/test_substrate_apportionment.py` skeleton (Bug C unit tests).
- [ ] T007 [P] Create `tests/unit/engine/test_factories_ideology_seed.py` skeleton (Bug D unit tests).
- [ ] T008 [P] Create `tests/unit/engine/headless_runner/test_runner_engine_invocation.py` skeleton (Bug E unit tests).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Coefficient calibration + bridge ServiceContainer wiring helper. These touch the same files multiple stories will modify, so they must happen first to avoid merge conflicts within the same branch.

**⚠️ CRITICAL**: No user story implementation can begin until this phase is complete.

- [ ] T009 [P] Bump `routing_scale` default from `0.1` to `0.2` in `src/babylon/config/defines/consciousness.py` (FR-027 + Phase 0 R4). Document the bump rationale in the field's docstring referencing spec-066 + the empirical drift analysis.
- [ ] T010 [P] Verify `WorldState.to_graph()` and `WorldState.from_graph()` round-trip preserves the fields needed by spec-066 (per Phase 0 R1). Add a unit test `tests/unit/models/test_world_state_round_trip_spec066.py::test_relationships_survive_round_trip` that creates a WorldState with one EXPLOITATION Relationship, calls `to_graph()` then `from_graph()`, and asserts the relationship is recovered.
- [ ] T011 Add a code comment in `src/babylon/engine/factories.py` documenting the spec-066 baseline IdeologicalProfile values: `class_consciousness=0.1, national_identity=0.5`. These solve the bridge ternary mapping for `(r=0.05, l=0.50, f=0.45)` per data-model.md §2. Cite the rejected high-cc/high-ni alternative `(cc=0.5, ni=0.9)` as theoretically dubious (Marx treats class consciousness and national identity as antagonistic; co-existing high values are unstable). Comment-only — no doctest, since `factories.py` is not currently in the project's doctest path.

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 — Surplus Value > 0 (Priority: P1) 🎯 MVP-A

**Goal**: Fix the Bug A formula error + QCEW denormalization so that `summary.terminal_state.total_s > 0` and the implied state rate of profit lies in [0.05, 0.50].

**Independent Test**: Run a 5-tick tri-county sim → assert `total_s > 0`. Run a 520-tick Michigan run → assert `total_s / (total_c + total_v) ∈ [0.05, 0.50]`.

### Tests for User Story 1 (write FIRST, fail, then make pass)

- [ ] T012 [P] [US1] Write `tests/unit/persistence/test_hex_hydrator_marx.py::test_s_formula_uses_value_added_identity` — assert that the hex hydrator's `_compute_per_county_marx_data` (or equivalent) function computes `s = max(0, GDP/52 - v)` (NOT `max(0, GDP/52 - v - c)`) for a fabricated input case. Mock the SQLite reads.
- [ ] T013 [P] [US1] Write `tests/unit/persistence/test_hex_hydrator_marx.py::test_qcew_query_filters_industry_id_1` — patch the SQLite cursor and assert the SUM query includes `AND fq.industry_id = 1` in its WHERE clause.
- [ ] T014 [P] [US1] Write `tests/unit/persistence/test_hex_hydrator_marx.py::test_negative_residual_emits_alarm_audit_row` — fabricate inputs where `GDP/52 < v` (clamping to 0) and assert that an audit row with `severity='alarm'` and `invariant_name='s_residual_negative'` was emitted to the auditor's buffer.
- [ ] T015 [US1] Write `tests/integration/test_marx_identities.py::test_total_s_strictly_positive_5tick_tri_county` — run the runner programmatically for 5 ticks on `detroit-tri-county`, assert `summary.terminal_state.total_s > 0`.
- [ ] T016 [US1] Write `tests/integration/test_marx_identities.py::test_value_added_identity_per_county_per_tick` — for every row in trace.csv, assert `|v + s - GDP_per_week_implied| / GDP_per_week_implied <= 0.05`. GDP_per_week_implied derived from `c × 2` since c = 0.5 × GDP/52.
- [ ] T017 [US1] Write `tests/integration/test_marx_identities.py::test_state_rate_of_profit_in_relaxed_band` — assert `0.05 ≤ total_s / (total_c + total_v) ≤ 0.50` for the terminal tick of a 5-tick tri-county run.

### Implementation for User Story 1

- [ ] T018 [US1] Modify `src/babylon/persistence/hex_hydrator.py:373` — change `s_per_week = max(0.0, gdp_per_week - v_per_week - c_per_week)` to `s_per_week = max(0.0, gdp_per_week - v_per_week)`. Update the function docstring to cite Marx Vol I Ch 9 + BEA value-added accounting.
- [ ] T019 [US1] Modify `src/babylon/persistence/hex_hydrator.py:~310-320` — add `AND fq.industry_id = 1` to the WHERE clause of the QCEW SUM query. Add a code comment explaining the BLS publication-granularity rationale.
- [ ] T020 [US1] Modify `src/babylon/persistence/hex_hydrator.py:~373-385` — when `s_raw < 0` (i.e., before the max-clamp), append a `ConservationAuditRow` with `severity='alarm'`, `invariant_name='s_residual_negative'`, `details={county_fips, year, gdp_per_week, v_per_week}` to a returned list of audit rows. The hex hydrator may need a thin extension to its return signature OR an audit-collector parameter; choose the smallest invasive change.
- [ ] T021 [US1] Verify hex_hydrator.py keeps `_INTERMEDIATE_INPUTS_FRACTION = 0.5` unchanged per Phase 0 R7. Add a comment at line 80 explaining the Shaikh-tractable c/v invariant rationale and pointing to the spec-068 deferral.

### Verification for User Story 1

- [ ] T022 [US1] Run `poetry run pytest tests/unit/persistence/test_hex_hydrator_marx.py -v` → all 3 unit tests pass.
- [ ] T023 [US1] Run `BABYLON_TEST_PG_DSN='dbname=babylon_test host=localhost port=5433 user=test password=test' poetry run pytest tests/integration/test_marx_identities.py -v` → all 3 integration tests pass.

**Checkpoint**: US1 (Bug A) closed. SC-001 + SC-002 + SC-003 + SC-004 verifiable. Bridge still doesn't run engine — that's US2.

---

## Phase 4: User Story 2 — Consciousness Evolution + Edge Bootstrap (Priority: P1) 🎯 MVP-B

**Goal**: Wire `engine.run_tick(graph, services, context)` into the bridged runner. Seed EXPLOITATION edges per county. Bump consciousness coefficients. Verify `ideology_f` drifts ≥5% over 520 ticks AND Wayne ≠ Keweenaw Pearson < 0.95.

**Independent Test**: Run a 520-tick Michigan-Canada simulation under `BABYLON_SLOW_TESTS=1`. Assert: (a) summary.performance.per_system_ms has 21 non-zero entries; (b) at least one county shows ≥5% relative drift on `ideology_f`; (c) Wayne (26163) and Keweenaw (26083) `ideology_f` time-series Pearson correlation < 0.95.

**Dependencies**: US1 must be complete. Without US1's `s > 0`, ImperialRentSystem extracts no Φ → wealth doesn't change → consciousness can't drift.

### Tests for User Story 2 (write FIRST)

- [ ] T024 [P] [US2] Write `tests/unit/engine/headless_runner/test_runner_engine_invocation.py::test_service_container_constructed_once_before_tick_loop` — patch `ServiceContainer.create` with a counter, run the runner for 5 ticks, assert `create` was called exactly once.
- [ ] T025 [P] [US2] Write `tests/unit/engine/headless_runner/test_runner_engine_invocation.py::test_engine_run_tick_called_per_tick` — patch `SimulationEngine.run_tick` with a counter, run the runner for 5 ticks, assert `run_tick` was called exactly 5 times (once per tick from tick 0 through tick 4).
- [ ] T026 [P] [US2] Write `tests/unit/engine/headless_runner/test_bridge.py::test_hydrate_initial_seeds_one_exploitation_edge_per_county` — call `bridge.hydrate_initial(scope_fips=frozenset({"26163","26125","26099"}), ...)`, assert `world.relationships` has exactly 3 Relationship objects, all with `edge_type=EdgeType.EXPLOITATION`.
- [ ] T027 [P] [US2] Write `tests/unit/engine/headless_runner/test_bridge.py::test_hydrate_initial_no_solidarity_edges` — same setup as T026, assert NO Relationship has `edge_type=EdgeType.SOLIDARITY` (per FR-026 + Constitution III.5).
- [ ] T028 [US2] Write `tests/integration/test_consciousness_evolution.py::test_ideology_f_drifts_geq_5pct_over_520_ticks` — run the canonical Michigan-Canada 520-tick sim, parse trace.csv, assert at least one county shows `|ideology_f(519) - ideology_f(0)| / ideology_f(0) >= 0.05`.
- [ ] T029 [US2] Write `tests/integration/test_consciousness_evolution.py::test_wayne_keweenaw_pearson_lt_0_95` — same canonical run, compute Pearson correlation between Wayne (26163) and Keweenaw (26083) `ideology_f` time-series, assert `r < 0.95`.
- [ ] T030 [US2] Write `tests/integration/test_consciousness_evolution.py::test_per_system_ms_has_21_nonzero_entries` — assert `summary.performance.per_system_ms` has exactly 21 keys AND every value is strictly positive.
- [ ] T031 [US2] Write `tests/integration/test_consciousness_evolution.py::test_expected_event_families_fire` — assert `summary.events` contains at least one event with `event_type` in `{BIFURCATION_THRESHOLD, CONSCIOUSNESS_SHIFT}` AND at least one in `{EXCESSIVE_FORCE, FASCIST_REVANCHISM, FASCIST_CONVERGENCE}`.

### Implementation for User Story 2

- [ ] T032 [US2] Add `_build_per_county_relationships(self, scope_fips: frozenset[str], entities: dict[str, Any]) -> list[Relationship]` private helper to `src/babylon/engine/headless_runner/bridge.py`. For each county in sorted(scope_fips), construct one `Relationship(source_id=proletariat_id, target_id=bourgeoisie_id, edge_type=EdgeType.EXPLOITATION, value_flow=0.0, tension=0.1)` and append to a list. Return the list.
- [ ] T033 [US2] Modify `bridge.hydrate_initial(...)` in `src/babylon/engine/headless_runner/bridge.py` — after `_build_per_county_entities()` call, call `_build_per_county_relationships()` and pass the result as `relationships=` to the `WorldState(tick=0, entities=entities, relationships=rels)` constructor.
- [ ] T034 [US2] Modify `src/babylon/engine/headless_runner/runner.py:run()` — before the tick loop, construct `services = ServiceContainer.create(config=SimulationConfig(), defines=defines, event_bus=bridge.event_bus, auditor=bridge.auditor, boundary_register=bridge.boundary_register)`. Store in a local variable for reuse.
- [ ] T035 [US2] Modify `src/babylon/engine/headless_runner/runner.py:_tick_loop(...)` — inside the per-tick loop, BEFORE the `_advance_tick(...)` call (which triggers `bridge.persist_tick`), call: (a) `graph = world.to_graph()` ONCE before the loop (cached, mutated in-place); (b) per tick: `engine.run_tick(graph, services, context)`; (c) per tick: `world = WorldState.from_graph(graph)` to reconstitute the world model with the engine's mutations. The `graph` instance is shared across all 520 ticks.
- [ ] T036 [US2] Pass the canonical engine instance to `_tick_loop`. Use `from babylon.engine.simulation_engine import _DEFAULT_ENGINE as engine` (or construct a fresh `SimulationEngine(_DEFAULT_SYSTEMS)` if `_DEFAULT_ENGINE` is a singleton that conflicts with test isolation).
- [ ] T037 [US2] Verify the EventCapture ↔ EventBus subscription that spec-065 shipped (per spec-065 T071) still functions when engine systems publish events. Add a unit test `tests/unit/engine/headless_runner/test_event_capture.py::test_event_capture_drains_engine_published_events` if not already covered — emit a synthetic event via the bridge-owned EventBus and assert the EventCapture buffer receives it.
- [ ] T038 [US2] Update the engine context (the `context` parameter to `engine.run_tick`) — construct a `TickContext(tick=tick, correlation_id=str(uuid4()))` per tick using the existing `babylon.engine.context.TickContext` class. Use a `persistent_data` dict OR `TickContext` itself depending on the existing system expectations (the codebase has `ContextType = Union[dict[str, Any], "TickContext"]` per `src/babylon/engine/systems/protocol.py:14`).
- [ ] T039 [US2] Remove the `@pytest.mark.xfail` decorator from `tests/integration/test_engine_bridge.py::test_tick_over_tick_evolution`. Verify the test now passes per FR-023 / SC-013.

### Verification for User Story 2

- [ ] T040 [US2] Run `poetry run pytest tests/unit/engine/headless_runner/ -v` → all unit tests pass (existing spec-065 + new US2 tests).
- [ ] T041 [US2] Run `BABYLON_TEST_PG_DSN='...' poetry run pytest tests/integration/test_engine_bridge.py -v` → no xfails remain; all tests pass.
- [ ] T042 [US2] Run `BABYLON_SLOW_TESTS=1 BABYLON_TEST_PG_DSN='...' poetry run pytest tests/integration/test_consciousness_evolution.py -v -s` → all 4 slow-gate tests pass.

**Checkpoint**: MVP COMPLETE. US1 (Bug A) + US2 (Bug E + Bug F) closed. SC-001 through SC-006 + SC-010 + SC-012 + SC-013 verifiable. The simulation now produces non-zero surplus value AND consciousness evolves with material conditions. **Suggested commit point**: `feat(spec-066): MVP — surplus value coherence + engine integration + edge bootstrap (US1 + US2 closed)`.

---

## Phase 5: User Story 3 — Ideology Baseline Placeholder (Priority: P2)

**Goal**: Initialize every county's ideology to (0.05, 0.50, 0.45) at tick 0. Document the placeholder explicitly in ADR043 + quickstart.md so future readers don't mistake it for a hidden assumption.

**Independent Test**: Inspect tick-0 trace.csv for any county; assert `ideology_r=0.05, ideology_l=0.50, ideology_f=0.45` within ±1e-9.

### Tests for User Story 3

- [ ] T043 [P] [US3] Write `tests/unit/engine/test_factories_ideology_seed.py::test_create_proletariat_accepts_ideology_kwarg` — call `create_proletariat(id="C001", county_fips="26163", ideology=IdeologicalProfile(class_consciousness=0.1, national_identity=0.5))`, assert returned SocialClass has the passed ideology.
- [ ] T044 [P] [US3] Write `tests/unit/engine/test_factories_ideology_seed.py::test_create_bourgeoisie_accepts_ideology_kwarg` — same as T043 for bourgeoisie.
- [ ] T045 [P] [US3] Write `tests/unit/engine/test_factories_ideology_seed.py::test_uniform_baseline_solves_to_target_ternary` — given `cc=0.1, ni=0.5`, compute the bridge ternary mapping and assert `r ≈ 0.05, l ≈ 0.50, f ≈ 0.45` within ±1e-9.
- [ ] T046 [US3] Write `tests/integration/test_engine_bridge.py::test_tick_0_ideology_uniform_across_counties` — run a 1-tick tri-county sim, parse trace.csv tick=0, assert all 3 counties have identical ideology values matching `(ideology_r=0.05, ideology_l=0.50, ideology_f=0.45)` within ±1e-9.
- [ ] T047 [US3] Write `tests/integration/test_engine_bridge.py::test_ternary_simplex_preserved_at_hydrate` — same run, assert `r + l + f` sums to 1.0 ± 1e-9 for every county at every tick.

### Implementation for User Story 3

- [ ] T048 [US3] Add `ideology: IdeologicalProfile | None = None` keyword-only argument to `create_proletariat()` in `src/babylon/engine/factories.py`. When provided, override the default `IdeologicalProfile`. When None, preserve existing default behavior (backward compat).
- [ ] T049 [US3] Add the same `ideology: IdeologicalProfile | None = None` keyword-only argument to `create_bourgeoisie()` in `src/babylon/engine/factories.py`.
- [ ] T050 [US3] Modify `src/babylon/engine/headless_runner/bridge.py:_build_per_county_entities()` — construct a single `BASELINE_IDEOLOGY = IdeologicalProfile(class_consciousness=0.1, national_identity=0.5)` (frozen, sharable) at module level; pass it as `ideology=BASELINE_IDEOLOGY` to every `create_proletariat()` and `create_bourgeoisie()` call.
- [ ] T051 [US3] Author `ai-docs/decisions/ADR043_ideology_baseline_placeholder.yaml` with the (0.05, 0.50, 0.45) decision: context (per-county data-driven seeding deferred per Clarifications Q3), decision (uniform placeholder), rationale, consequences (positive: documented placeholder; negative: counties don't reflect 2010 political diversity), and a `replace_when` clause naming the future spec.
- [ ] T052 [US3] Update `specs/066-marx-coherence-fixes/quickstart.md` Section 5 to call out the (0.05, 0.50, 0.45) placeholder explicitly, with a link to ADR043.

### Verification for User Story 3

- [ ] T053 [US3] Run `poetry run pytest tests/unit/engine/test_factories_ideology_seed.py -v` → all 3 unit tests pass.
- [ ] T054 [US3] Run `BABYLON_TEST_PG_DSN='...' poetry run pytest tests/integration/test_engine_bridge.py::test_tick_0_ideology_uniform_across_counties -v` → passes.

**Checkpoint**: US3 (Bug D) closed. SC-009 + SC-014 verifiable.

---

## Phase 6: User Story 4 — Employment Unit Fix (Priority: P2)

**Goal**: Fix `employment_proxy = SUM(qcew.employment) / 52` → `/ 12`. State-aggregate employment must land in [3.5M, 4.8M].

**Independent Test**: Sum `employment_proxy` across all 83 Michigan counties at tick 0; assert sum ∈ [3.5M, 4.8M].

### Tests for User Story 4

- [ ] T055 [P] [US4] Write `tests/unit/persistence/test_employment_proxy_units.py::test_divides_by_12_not_52` — patch the SQLite cursor to return a known QCEW employment SUM (e.g., 1,200,000 for Wayne), assert the hydrator output is `1,200,000 / 12 = 100,000` (not `1,200,000 / 52 = ~23,077`).
- [ ] T056 [US4] Write `tests/integration/test_marx_identities.py::test_state_aggregate_employment_in_BLS_band` — run a 1-tick Michigan sim, sum employment_proxy across all 83 counties at tick 0, assert sum in [3,500,000, 4,800,000].
- [ ] T057 [US4] Write `tests/integration/test_marx_identities.py::test_per_county_LFPR_plausible` — for every county-tick row, assert `0.30 <= employment_proxy / population <= 0.65`.

### Implementation for User Story 4

- [ ] T058 [US4] Modify `src/babylon/persistence/hex_hydrator.py:~410` — find the line `employment_proxy_per_week = sum_employment / _WEEKS_PER_YEAR` (or equivalent dividing by 52) and change to `employment_proxy = sum_employment / 12`. Rename the local variable from `_per_week` to remove the misleading suffix. Update the docstring to clarify that the value is "annual average employment" not a per-week rate.

### Verification for User Story 4

- [ ] T059 [US4] Run `poetry run pytest tests/unit/persistence/test_employment_proxy_units.py -v` → passes.
- [ ] T060 [US4] Run `BABYLON_TEST_PG_DSN='...' poetry run pytest tests/integration/test_marx_identities.py::test_state_aggregate_employment_in_BLS_band tests/integration/test_marx_identities.py::test_per_county_LFPR_plausible -v` → both pass.

**Checkpoint**: US4 (Bug B) closed. SC-007 verifiable.

---

## Phase 7: User Story 5 — Substrate Apportionment (Priority: P3)

**Goal**: Wire area-weighted formula for `raw_material_stock`; keep population-weighted for `energy_stock`. ≥50% of counties must show distinct values.

**Independent Test**: For tick-0 trace.csv, count rows where `energy_stock != raw_material_stock`; assert ≥42 of 83.

### Tests for User Story 5

- [ ] T061 [P] [US5] Write `tests/unit/persistence/test_substrate_apportionment.py::test_energy_population_weighted` — fabricate a 2-county scenario with population_share=(0.7, 0.3) and state_energy_value=1000, assert energy_stocks are (700, 300).
- [ ] T062 [P] [US5] Write `tests/unit/persistence/test_substrate_apportionment.py::test_raw_material_area_weighted` — same 2 counties with area_share=(0.4, 0.6), assert raw_material_stocks are (400, 600).
- [ ] T063 [P] [US5] Write `tests/unit/persistence/test_substrate_apportionment.py::test_energy_neq_raw_material_majority` — for the 83-county Michigan scope at tick 0, assert ≥42 counties show distinct values.
- [ ] T064 [US5] Write `tests/integration/test_engine_bridge.py::test_substrate_distinguishability` — run a 1-tick Michigan sim, parse tick-0 trace.csv, assert ≥42 of 83 counties have `energy_stock != raw_material_stock`.

### Implementation for User Story 5

- [ ] T065 [US5] Modify `src/babylon/persistence/hex_hydrator.py` — find the per-county substrate stock computation. Add a JOIN to `dim_county_geometry` (or equivalent table holding `land_area_sqmi`) to obtain the county's land area. Compute `state_total_area_sqmi = SUM(land_area_sqmi)` for the state.
- [ ] T066 [US5] Modify the same file — split the substrate stock formulas: `energy_stock = state_energy_value × (county_population / state_population)` (existing population-weighted); `raw_material_stock = state_nonfuel_mineral_value × (county_land_area_sqmi / state_total_area_sqmi)` (NEW area-weighted). Document the asymmetry in a code comment.
- [ ] T067 [US5] If `dim_county_geometry.land_area_sqmi` is unpopulated for any Michigan county, emit a `severity='warning'` audit row identifying the county AND fall back to area-share equal to the population-share (degraded mode). Document the fallback in the code comment.

### Verification for User Story 5

- [ ] T068 [US5] Run `poetry run pytest tests/unit/persistence/test_substrate_apportionment.py -v` → all 3 unit tests pass.
- [ ] T069 [US5] Run `BABYLON_TEST_PG_DSN='...' poetry run pytest tests/integration/test_engine_bridge.py::test_substrate_distinguishability -v` → passes.

**Checkpoint**: US5 (Bug C) closed. SC-008 verifiable.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, baseline regeneration, ADR authoring, CI gate validation. Closes SC-011 + SC-015.

- [ ] T070 [P] Author `ai-docs/decisions/ADR044_engine_integration_into_bridged_runner.yaml` documenting the spec-066 engine wiring approach: (a) ServiceContainer construction pattern; (b) graph round-trip via to_graph/from_graph; (c) 21 systems canonical order; (d) coefficient calibration (`routing_scale 0.1 → 0.2`). Reference Phase 0 R1/R2/R3/R4.
- [ ] T071 [P] Update `ai-docs/state.yaml` to v2.9.0 — bump version, add spec_066 status block (mvp_phase: complete, all_phases: complete), reference ADR043 + ADR044.
- [ ] T072 [P] Update project-root `CLAUDE.md` "Engine Architecture" section: replace the outdated 7-system list (lines ~214-231) with the canonical 21-system list per `simulation_engine.py:_DEFAULT_SYSTEMS`. Add a note pointing to spec-066 ADR044 for the integration history.
- [ ] T073 [P] Update `specs/066-marx-coherence-fixes/quickstart.md` — verify each command/snippet in Sections 1-5 matches the as-shipped behavior. Apply targeted edits where drift exists. Add a "Walkthrough verified 2026-XX-XX" footer matching the spec-065 T086 pattern.
- [ ] T074 Run `mise run check` (lint + format + typecheck + test:unit) AND `BABYLON_TEST_PG_DSN='...' poetry run pytest tests/integration/test_engine_bridge.py -v` to verify all spec-065 integration tests still pass (closes SC-015 per /speckit.analyze G2). Ensure spec-066 changes do not introduce new failures. Pre-existing failures from spec-065 audit (3 in `tests/unit/web/test_schema_parity.py`, 1 in `test_import_boundary.py`, 2 flaky in `test_game_app_init.py`) remain documented in ADR042 and are out of spec-066 scope.
- [ ] T075 Run `BABYLON_SLOW_TESTS=1 mise run sim:e2e-michigan` and capture wallclock + artifact outputs. Verify SC-011 (≤90 min). The mise task auto-refreshes `tests/baselines/michigan-e2e.json` via spec-065 T085's `--write-baseline` flag.
- [ ] T076 Verify the new baseline `tests/baselines/michigan-e2e.json` shows the spec-066 transition: `total_s > 0`, `max_tension > 0`, `total_population` non-null, `events[]` non-empty, AND `trace.csv` has zero empty cells across the 22 county-applicable columns (preserves spec-065 SC-001 contract per FR-022). Diff against the spec-065 baseline (commit `4e641a84`) to document the headline change.
- [ ] T077 Author the spec-069 placeholder file `specs/069-sqlite-cache-optimization/spec.md` (single-line ADR-equivalent or a complete spec stub) to capture the SQLite per-tick read optimization deferral identified in Phase 0 R8. Document: scope = move per-tick `fetch_population_for_county_at_tick` + `fetch_employment_proxy_for_county_at_tick` calls out of the per-tick path into a hydrate-once cache; expected wallclock reduction ~3.5s/tick; closes the path to a future SC-011 tightening.
- [ ] T078 Update `specs/066-marx-coherence-fixes/tasks.md` — mark all completed tasks as `[X]`; add a "Post-implementation status" section noting SC-001..SC-015 verification status with measured numeric values (SC-002 actual rate of profit, SC-005 actual ideology drift %, SC-007 actual employment total, SC-011 actual wallclock, etc.).
- [ ] T079 Final sanity check: re-read `specs/066-marx-coherence-fixes/spec.md` end-to-end to confirm every FR has been addressed by at least one shipped task. Note any FR with no closing task as a residual gap (should be zero).

**Checkpoint**: Spec-066 fully shipped. All 5 user stories closed. All 28 FRs satisfied. All 15 SCs verifiable.

---

## Dependencies & Execution Order

### User story dependency graph

```
Phase 1 (Setup, T001-T008)
   ↓
Phase 2 (Foundational, T009-T011)
   ↓
   ├─→ Phase 3 (US1 Bug A, T012-T023)
   │      ↓
   │      └─→ Phase 4 (US2 Bug E+F, T024-T042) [REQUIRES US1: no surplus → no agitation]
   │
   ├─→ Phase 5 (US3 Bug D, T043-T054) [INDEPENDENT — can run parallel to US1/US2]
   │
   ├─→ Phase 6 (US4 Bug B, T055-T060) [INDEPENDENT — can run parallel to US1/US2/US3]
   │
   └─→ Phase 7 (US5 Bug C, T061-T069) [INDEPENDENT — can run parallel to US1/US2/US3/US4]

Phase 8 (Polish, T070-T079) [REQUIRES all 5 user stories complete]
```

### MVP scope

**MVP commit** = US1 + US2 closed simultaneously (T001 through T042).
This delivers the headline value: `total_s > 0` AND `consciousness evolves with material conditions`.

US3, US4, US5 are independent additive landings on the same `066-marx-coherence-fixes` branch, each shippable as its own commit per Clarifications Q3.

### Parallel execution opportunities

**Phase 1**: T002–T008 are all `[P]` (different test files; no dependencies). 7-way parallel.
**Phase 2**: T009 + T010 are `[P]` (different files). T011 is sequential (depends on T010 verification). 2-way + 1.
**Phase 3 (US1)**: Tests T012/T013/T014 are `[P]` (different test methods, same file but isolated). Tests T015–T017 are sequential against the integration test file. Implementation T018–T021 are sequential against `hex_hydrator.py`.
**Phase 4 (US2)**: Tests T024/T025/T026/T027 are `[P]` (different test methods, separable files). Tests T028–T031 are sequential against `test_consciousness_evolution.py`. Implementation T032–T039 are mostly sequential against `bridge.py` + `runner.py` (file-level conflicts).
**Phase 5 (US3)**: Tests T043/T044/T045 are `[P]`. Implementation T048/T049 are `[P]` (different functions in `factories.py` could conflict; test before paralleling). T050/T051/T052 are sequential.
**Phase 6 (US4)**: Single hex_hydrator change; minimal parallelism.
**Phase 7 (US5)**: Tests T061/T062/T063 are `[P]`. Implementation sequential against `hex_hydrator.py`.
**Phase 8 (Polish)**: T070/T071/T072/T073 are `[P]` (different doc files). T074–T079 are sequential.

### Independent test criteria

- **US1**: `summary.terminal_state.total_s > 0` for any 5-tick run; state rate of profit ∈ [0.05, 0.50] for terminal tick of canonical run.
- **US2**: `summary.performance.per_system_ms` has 21 non-zero entries; at least one county shows ≥5% `ideology_f` drift over 520 ticks; Wayne-Keweenaw Pearson < 0.95.
- **US3**: tick-0 trace.csv has `(ideology_r, ideology_l, ideology_f) = (0.05, 0.50, 0.45) ± 1e-9` for every county.
- **US4**: tick-0 state-aggregate `employment_proxy` ∈ [3.5M, 4.8M].
- **US5**: ≥42 of 83 counties at tick 0 show `energy_stock != raw_material_stock`.

---

## Implementation Strategy

**Recommended sequence** (to maximize incremental value delivery):

1. **Sprint 1 (1 day)**: Phase 1 + Phase 2 (T001-T011). Foundation ready.
2. **Sprint 2 (2-3 days)**: Phase 3 (US1, T012-T023). MVP-A shipped.
3. **Sprint 3 (3-4 days)**: Phase 4 (US2, T024-T042). MVP-B shipped. **Headline commit**.
4. **Sprint 4 (1-2 days)**: Phase 5 + Phase 6 + Phase 7 (US3 + US4 + US5, T043-T069) — these are independent; can be done in parallel by separate agents/contributors if desired.
5. **Sprint 5 (1 day)**: Phase 8 (T070-T079) + the canonical Michigan e2e run + baseline regen.

**Total estimate**: ~10 working days for full delivery; MVP-only (US1+US2) is ~6 days.

---

## Summary

- **Total tasks**: 79 (T001-T079)
- **Phase 1 (Setup)**: 8 tasks (T001-T008)
- **Phase 2 (Foundational)**: 3 tasks (T009-T011)
- **Phase 3 (US1, MVP-A)**: 12 tasks (T012-T023) — 6 tests + 4 implementation + 2 verification
- **Phase 4 (US2, MVP-B)**: 19 tasks (T024-T042) — 8 tests + 8 implementation + 3 verification
- **Phase 5 (US3)**: 12 tasks (T043-T054) — 5 tests + 5 implementation + 2 verification
- **Phase 6 (US4)**: 6 tasks (T055-T060) — 3 tests + 1 implementation + 2 verification
- **Phase 7 (US5)**: 9 tasks (T061-T069) — 4 tests + 3 implementation + 2 verification
- **Phase 8 (Polish)**: 10 tasks (T070-T079)
- **MVP scope**: T001-T042 (42 tasks) — ships full Marxist-coherence + consciousness evolution; US3/4/5 follow as separate commits
- **Highest parallelism**: Phase 1 setup (7-way), Phase 4 US2 unit tests (4-way), Phase 8 polish (4-way)
- **Slow-gate tests** (BABYLON_SLOW_TESTS=1 required): T028, T029, T030, T031, T042, T075
- **Dependencies enforced**: US2 requires US1 (no surplus → no agitation → no consciousness drift). US3/4/5 are mutually independent and parallel to US1/US2.
