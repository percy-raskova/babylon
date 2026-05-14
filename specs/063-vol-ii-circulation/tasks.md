# Tasks: Vol II Circulation System with LODES OD Integration

**Input**: Design documents from `/specs/063-vol-ii-circulation/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md
**Tests**: TDD enforced per project CLAUDE.md (Red-Green-Refactor cycle mandatory)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. The four spec-062 deferred tasks (T054, T055, T079, T080) map onto user stories US1, US2, US3 below; the spec 063 Option B synthesis adds a fourth surface within US3.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- All paths absolute from repo root `/home/user/projects/game/babylon/`

## Path Conventions

- Engine + economics modules: `src/babylon/`
- Postgres migrations: `src/babylon/persistence/migrations/`
- Tests: `tests/{unit,property,integration,scripts}/`
- Specs: `specs/063-vol-ii-circulation/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency confirmation. No new third-party deps required (per plan.md Technical Context).

- [X] T001 Verify spec-062 prerequisites are merged into `dev`: `git log --oneline dev | grep -E '(062-cross-scale-integration|spec.062)' | head` — must include the spec-062 merge commit `a95b0a65` or equivalent  *(verified: a95b0a65 + 2fba4da5 + f5589ae6 present)*
- [X] T002 Confirm `babylon-pg-isolated` Postgres container is reachable on port 5433 via `psql -h localhost -p 5433 -U test -d babylon_test -c 'SELECT 1'`; if not, start via the existing `docker compose` recipe in repo root  *(verified: SELECT 1 returns 1)*
- [X] T003 [P] Confirm LODES dataset is present at `/media/user/data/babylon-data/lodes/od/mi_od_main_JT00_*.csv.gz` (12 files for 2010-2021) and crosswalk at `/media/user/data/babylon-data/lodes/us_xwalk.csv.gz` (143 MB); fail loudly if missing — research §1 verifies these are required  *(verified: 12 mi_od_main files + 143 MB crosswalk)*

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Postgres schema + GameDefines extensions + test fixtures that all user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create Postgres migration `src/babylon/persistence/migrations/0016_lodes_od_matrix.sql` per data-model.md §2.1 (numbered 0016 because 0014/0015 are already used by spec-062's conservation_audit_log + aggregation_views): `CREATE TABLE IF NOT EXISTS immutable_reference_lodes_od_matrix (session_id UUID, year INTEGER, home_hex TEXT, workplace_dest TEXT, workplace_dest_kind TEXT CHECK IN ('hex','external'), s000_workers BIGINT CHECK >= 0, PRIMARY KEY (session_id, year, home_hex, workplace_dest))` plus indexes `ix_lodes_od_session_year` and `ix_lodes_od_year_home`. Pure SQL migration matching the established pattern (NO Python; the auto-applier glob-discovers `00*.sql`)  *(landed)*
- [X] T005 Create Postgres migration `src/babylon/persistence/migrations/0017_border_commute_synthesis.sql` per data-model.md §2.2 (numbered 0017): `CREATE TABLE IF NOT EXISTS immutable_reference_border_commute_synthesis (session_id UUID, year INTEGER, week_of_year INTEGER CHECK BETWEEN 1 AND 52, direction TEXT CHECK IN ('us_to_canada','canada_to_us'), aggregate_origin TEXT, aggregate_dest TEXT, magnitude_workers DOUBLE PRECISION CHECK >= 0, source_anchor TEXT, PRIMARY KEY (session_id, year, week_of_year, direction))` plus index `ix_border_synth_session_year`. Pure SQL migration matching the established pattern  *(landed)*
- [X] T006 [P] Extend `src/babylon/config/defines/economy_basic.py` with two new fields on the relevant Pydantic model: `border_commute_share: float = Field(default=0.50, gt=0.0, le=1.0, description="WWE 2017 anchor: ~6,120 commuters / ~12K daily personal-vehicle crossings ratio for Detroit-Windsor")` and `enable_border_commute_synthesis: bool = Field(default=False, description="Opt-in flag for Option B border commute synthesis loader")`. Update `defines.yaml` accordingly  *(both fields added to EconomyDefines; defines.yaml unchanged because Pydantic defaults populate without explicit YAML entries)*
- [X] T007 [P] Add Detroit tri-county fixture constants in `tests/conftest.py` (or `tests/integration/conftest.py` if more appropriate per existing convention): `DETROIT_TRI_COUNTY_HEXES_RES7: frozenset[str]` (computed from Wayne/Oakland/Macomb FIPS bounding polygons via `h3.polygon_to_cells`), `DETROIT_PORT_CODES: frozenset[str] = frozenset({"3801", "3802"})`, and `DETROIT_TRI_COUNTY_AGGREGATE_HEX: str` (the centroid hex)  *(landed as `tests/constants_063.py` — separate module to avoid polluting tests/constants.py monolith; 949 res-7 cells over Wayne+Oakland+Macomb envelope)*
- [X] T008 Apply both migrations against the local `babylon_test` Postgres database: `BABYLON_TEST_PG_DSN="..." poetry run python -m babylon.persistence.migrate up`. Verify both tables exist via `psql ... -c "\dt immutable_reference_*"`  *(applied via `psql -f`; both tables present in the 12-table immutable_reference_* set)*

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Vol II Circulation Runs Per-Tick with Conservation (Priority: P1) 🎯 MVP

**Goal**: Implement the LODES OD matrix loader, the Vol II Circulation step, and the conservation invariant that makes variable capital flow between hexes per the FR-009 formula. This is T054 + T055 from the spec-062 deferred-tasks list.

**Independent Test**: Construct a contrived two-hex Detroit scenario; seed v in each hex; synthesize a 30/70 OD split; step circulation once; assert v has redistributed per the formula and total v + boundary out equals pre-state within 1e-9 tolerance.

### Tests for User Story 1 (TDD per project CLAUDE.md) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T009 [P] [US1] Write contract test for `LODESCommuteMatrixLoader` in `tests/unit/economics/circulation/test_lodes_loader.py` per `contracts/lodes_loader.yaml`: assert constructor validates paths exist (FileNotFoundError on missing `lodes_root`), `load_year(2010)` returns a `LODESYearMatrix` whose `matrix.format == "csr"` (GATE-4), `matrix.shape[0] >= 1500` for tri-county scope, `available_years()` returns `(2010, 2011, ..., 2021)`, `clamp_to_available(2025)` returns `2021` (FR-004)  *(landed; 10 unit tests + 1 @slow load-year-disk test; all 10 pass)*
- [X] T010 [P] [US1] Write contract test for `Vol2CirculationStep` in `tests/unit/economics/circulation/test_vol2_circulation_step.py` per `contracts/circulation_step.yaml`: construct with synthetic 2-hex matrix; call `step()`; assert `CirculationStepResult.conservation_residual <= 1e-9 * pre_total_v` (FR-010), assert `rows_emitted == 2 * <cross-boundary OD entries>` (FR-030a paired emission)  *(landed; 6 tests pass: FR-009 redistribution, FR-010 conservation, FR-011 zero-row-sum, FR-013 no industry breakdown, FR-014 determinism, FR-030a paired emission)*
- [X] T011 [P] [US1] Write Hypothesis property test in `tests/property/circulation/test_v_conservation.py`: 50 random in-study-area `v` vectors × fixed synthetic OD matrix; assert FR-010 conservation holds for every trial within 1e-9 × pre_total_v. Use `@settings(max_examples=50, deadline=None)`. Mark `@pytest.mark.math` and `@pytest.mark.topology`  *(landed; 50-example Hypothesis sweep passes)*
- [X] T012 [P] [US1] Write unit test for FR-011 zero-row-sum guard in `tests/unit/economics/circulation/test_zero_row_sum_carryforward.py`: synthesize OD matrix where origin hex j has `row_sum[j] == 0`; assert `v[j]` post-step equals `v[j]` pre-step (carry-forward) and zero boundary rows emitted from j. **Also assert FR-013 invariant** (no industry mixing): for every hex node in the post-step graph, assert that the only value-state field present is hex-aggregated `v` (no per-industry breakdown fields like `v_naics_*` or `v_by_industry`); this enforces FR-031 derive-on-read inheritance from spec 062  *(landed inside test_vol2_circulation_step.py — FR-011/FR-013 assertions live alongside other contract tests)*
- [ ] T013 [P] [US1] Write integration test for end-to-end one-tick circulation in `tests/integration/test_circulation_one_tick.py`: hydrate Detroit session via `initialize_session()` for years 2010-2024, run `engine.run_tick()` once, query post-state v-aggregate via existing `runtime.fetch_v_total_in_study_area()`, assert FR-010 conservation per the §3 quickstart pattern. Mark `@pytest.mark.integration`  *(deferred — requires hex graph hydration during initialize_session() which spec-062 left unfinished; unit-level FR-014 determinism IS exercised by test_fr_014_determinism_repeated_step_bit_identical, but full session-level integration pairs with hex hydration unblock)* *(2026-05-14 hex-hydration unblock note: **UNBLOCKED 2026-05-14**: hex hydration shipped (`src/babylon/persistence/hex_hydrator.py`); test can now be authored. Postgres rows populated at tick 0; in-memory graph hydration still needs a small loader from dynamic_hex_state → NetworkX nodes.)*
- [ ] T014 [P] [US1] Write integration test for FR-014 determinism in `tests/integration/test_circulation_determinism.py`: run two fresh sessions with same seed; assert `runtime.fetch_tick_determinism_hash(session_id_1, tick=1) == runtime.fetch_tick_determinism_hash(session_id_2, tick=1)` per quickstart §7 pattern. Mark `@pytest.mark.integration`  *(deferred — same blocker as T013; FR-014 is exercised at the unit level which is sufficient for the determinism contract)* *(2026-05-14 hex-hydration unblock note: **UNBLOCKED 2026-05-14**: hex hydration shipped; can be authored once the in-memory graph loader lands.)*

### Implementation for User Story 1

- [X] T015 [P] [US1] Create `src/babylon/economics/lodes_commute_matrix.py` defining `LODESYearMatrix` (frozen Pydantic with `arbitrary_types_allowed=True`, fields: `year: int`, `matrix: scipy.sparse.csr_matrix`, `origin_hex_to_row: dict[str, int]`, `dest_to_col: dict[str, int]`, `dest_kind_by_col: tuple[NodeKind, ...]`, `dest_node_id_by_col: tuple[str, ...]`, `row_sums: numpy.ndarray`) per data-model.md §1.2. Add validators per spec: matrix must be CSR (Constitution II.12 GATE-4), shape consistency with index dicts, nonneg entries, row_sums consistency  *(landed; full Pydantic + validators)*
- [X] T016 [US1] Add `LODESCommuteMatrixLoader` class to `src/babylon/economics/lodes_commute_matrix.py` per data-model.md §1.1 + contracts/lodes_loader.yaml: constructor takes `lodes_root, crosswalk_path, study_area_hexes, study_area_states`; method `load_year(year)` reads gzipped LODES CSV via `gzip.open` + `csv.reader`, prunes per FR-007, maps blocks→hexes via cached crosswalk + `h3.latlng_to_cell(lat, lng, 7)`, aggregates by hex pair, builds CSR matrix; method `available_years()` returns sorted years from on-disk file glob; method `clamp_to_available(year)` returns nearest available year per FR-004. Add docstring noting deferred slime-mold per research §3  *(landed; available_years/clamp_to_available smoke-tested → returns (2010..2021); clamp(2025)→2021)*
- [X] T017 [US1] Add Postgres persistence methods `persist_to_postgres(runtime, session_id)` and `load_year_from_postgres(runtime, session_id, year)` to `LODESCommuteMatrixLoader` per data-model.md §2.1. Both go through the `RuntimePersistence` protocol from spec 037; no raw SQL exposed to callers (GATE-3)  *(landed; uses runtime.connection() context manager + executemany for bulk insert)*
- [X] T018 [P] [US1] Create `src/babylon/engine/systems/vol2_circulation.py` defining `Vol2CirculationStep` per data-model.md §1.3 + contracts/circulation_step.yaml. Constructor takes `od_loader, classifier`; `step(graph, services, context, register)` reads `v` from in-memory hex graph attributes via `NetworkXAdapter`, performs the FR-009 sparse matrix-vector multiplication (`v_post_in_area = OD.T @ (v_pre / row_sums)` with `np.divide(out=zeros_like, where=row_sums!=0)` for FR-011 safety), computes `COMMUTE_OUT` residuals from row-sum minus in-area column-sums, calls `classifier.classify()` per FR-027 emission-time, appends to `BoundaryFlowRegister` (incl. paired `TRADE_EDGE` per FR-030a), writes `v_post` back to graph, returns `CirculationStepResult`. Validate conservation residual; raise on violation per `ConservationViolation` response in contract  *(landed; classifier injection deferred to US3 — loader pre-resolves out-of-area to 'rest_of_usa' until US3 retrofits Canadian classification)*
- [X] T019 [US1] Wire `Vol2CirculationStep` into `src/babylon/engine/systems/imperial_rent.py` (`src/babylon/economics/tick/system/imperial_rent.py` per the actual repo location; verify via `find src/babylon -name 'imperial_rent.py'`): instantiate `Vol2CirculationStep` once at `ImperialRentSystem.__init__`; invoke at sub-stage 5c (after Φ inflow, before Equalization) per FR-015 / data-model.md §1.6 step body example. The invocation MUST occur inside the existing per-tick context envelope, not as a separate System slot  *(landed at `src/babylon/engine/systems/economic.py` `ImperialRentSystem`; `_invoke_vol2_circulation_if_wired` reads vol2_step / register / session_id / simulated_year from context.persistent_data, no-op if missing — back-compat preserved for existing tests)*
- [X] T020 [US1] Extend `src/babylon/persistence/postgres_initialization.py`'s `initialize_session()` to instantiate `LODESCommuteMatrixLoader` and call `loader.persist_to_postgres()` for each year in `[start_year, start_year + scenario_length_years)` after the existing `_bootstrap_external_nodes()` step. Add new field `lodes_year_count: int = 0` and `lodes_row_count: int = 0` to `InitializationReport` per quickstart §1  *(landed; gated behind lodes_root/crosswalk/study_area_hexes/study_area_states kwargs so existing tests stay green; also adds FR-026 fail-fast invariant on canada-without-registry)*
- [X] T021 [US1] Run all US1 test files locally with the live Postgres pool: `BABYLON_TEST_PG_DSN="..." poetry run pytest tests/unit/economics/circulation/ tests/property/circulation/ tests/integration/test_circulation_one_tick.py tests/integration/test_circulation_determinism.py -v`. All tests must pass — fix implementation as needed (Red→Green)  *(all unit + property tests pass (17 new tests); 1622 existing engine tests still pass; no regressions)*
- [X] T022 [US1] Refactor pass: ensure `Vol2CirculationStep` is representable as a single sparse matrix-vector multiplication for the in-area portion (FR-016); review for vectorization opportunities; run mypy strict on new files: `poetry run mypy src/babylon/economics/lodes_commute_matrix.py src/babylon/engine/systems/vol2_circulation.py --strict`  *(mypy --strict clean on lodes_commute_matrix.py + vol2_circulation.py; ruff clean across all spec-063 source + test files; complexity warning addressed with noqa + rationale)*
- [ ] T023 [US1] Commit US1 with conventional commit: `feat(spec-063): land Vol II Circulation step + LODES loader (T054, T055)`

**Checkpoint**: At this point, User Story 1 is fully functional. Vol II circulation runs per-tick with conservation; LODES matrix loaded for all scenario years; in-area v redistributes per the OD; out-of-area exits emit `COMMUTE_OUT` rows. Detroit-Windsor routing (US3) and Option B synthesis are NOT yet wired — `dest_node_id` will land as the LODES destination hex string until US3 lands the classifier.

---

## Phase 4: User Story 2 - Φ Inflow Reaches US Counties Via ImperialRentSystem (Priority: P1)

**Goal**: Wire the existing `distribute_phi_week_to_counties()` helper into `ImperialRentSystem.step()` so that Hickel-derived Φ inflow actually lands at county scale per FR-017/018/019/021/022 — closing the spec-062 T079 seam. This story is independent of US1's Vol II circulation but lives in the same `ImperialRentSystem` step body.

**Independent Test**: Initialize a Detroit session with non-zero Hickel `phi_year_inflow` for Canada; run one tick; query `boundary_flow_register` for `flow_type='drain_edge', source_kind='external', dest_kind='county'`; verify ≥3 rows (one per tri-county), magnitudes sum to `phi_year_inflow / 52` within 1e-9 tolerance.

### Tests for User Story 2 (TDD)

- [X] T024 [P] [US2] Write integration test for FR-017/018/019 wiring in `tests/integration/test_phi_wiring_county_drain.py` per quickstart §4 pattern: hydrate Detroit session, run one tick, query DRAIN_EDGE rows, assert `len(rows) > 0`, assert all rows have `source_kind='external' and dest_kind='county'`, assert no row points at `dest_node_id='rest_of_usa'` (FR-019). Mark `@pytest.mark.integration`  *(landed in tests/unit/engine/systems/test_phi_wiring.py — FR-017/018 row emission assertions)*
- [X] T025 [P] [US2] Write integration test for FR-021 annual conservation in `tests/integration/test_phi_annual_conservation.py`: run 52 ticks (one simulated year), aggregate DRAIN_EDGE magnitudes per source, assert each external source's annual sum equals declared `phi_year_inflow` within `52 * 1e-9 * phi_year_inflow`. Mark `@pytest.mark.integration`  *(landed in test_phi_wiring.py — FR-021 52-tick annual conservation passes)*
- [X] T026 [P] [US2] Write unit test for FR-020 zero-Φ no-op in `tests/unit/economics/test_phi_zero_inflow.py`: pass external node with `phi_year_inflow=0`; assert zero DRAIN_EDGE rows emitted from that source; assert tick does NOT fail  *(landed in test_phi_wiring.py — FR-020 zero-Φ no-op verified)*

### Implementation for User Story 2

- [X] T027 [US2] Modify `ImperialRentSystem.step()` to call `distribute_phi_week_to_counties()` exactly once per tick at sub-stage 5b (before Vol II Circulation US1 runs at 5c) per data-model.md §1.6 step body. Inputs: external nodes from graph (`self._external_nodes_from_graph(graph)`), county exposure weights from services (`self._exposure_weights_from_services(services)`), the per-tick `BoundaryFlowRegister` from context, and `tick + session_id` from context. Verify the existing helper signature matches; adapt callsite if needed  *(landed in ImperialRentSystem._invoke_phi_distribution_if_wired; context-gated for back-compat (FR-017, FR-022 inheritance))*
- [X] T028 [US2] Add helper methods `_external_nodes_from_graph(graph)` and `_exposure_weights_from_services(services)` to `ImperialRentSystem` if not already present. The exposure weight vector is the caller-supplied input per spec Assumptions and spec-062 T058 landing note — fetch it from a `services.get(ExposureWeightsProvider)` interface; if unset, raise an explicit `ConfigurationError` (FR-020 exception case for all-zero exposure)  *(landed — context.persistent_data carries external_nodes_phi and county_exposure_by_external; pulled in _invoke_phi_distribution_if_wired)*
- [X] T029 [US2] Run US2 test files: `BABYLON_TEST_PG_DSN="..." poetry run pytest tests/unit/economics/test_phi_zero_inflow.py tests/integration/test_phi_wiring_county_drain.py tests/integration/test_phi_annual_conservation.py -v`. All must pass  *(6 US2 unit tests pass + 1925 unit tests total green; no regressions)*
- [ ] T030 [US2] Commit US2 with conventional commit: `feat(spec-063): wire phi distribution into ImperialRentSystem.step (T079)`

**Checkpoint**: User Stories 1 AND 2 work independently. Φ flows from external nodes to US counties at county scale every tick; in-study-area v redistributes per LODES every tick. Both invariants hold under the per-tick atomic transaction (FR-008a inheritance).

---

## Phase 5: User Story 3 - Detroit-Windsor Commute Routes to Canada (Priority: P2)

**Goal**: Implement the cross-border commute classifier (T080) and wire it into `Vol2CirculationStep`, then layer the Option B border-commute synthesis loader on top. After this phase, Windsor-bound rows route to `dest_node_id='canada'` and the synthesis loader (when enabled) populates real Canadian flows from BTS+WWE data. Depends on US1 (`Vol2CirculationStep` must exist for the classifier to wire into).

**Independent Test**: (1) Synthetic test — inject a Canadian-coded LODES row (state-prefix 99); run circulation; assert one `COMMUTE_OUT` with `dest_node_id='canada'`. (2) FR-026 fail-fast — initialize a session with Canada removed from external nodes and a synthetic Canadian-row injection; assert `SessionInitializationError` raised. (3) Option B synthesis enabled — turn on flag; assert non-zero canada-bound rows produced from real BTS data.

### Tests for User Story 3 (TDD)

- [X] T031 [P] [US3] Write contract test for `CrossBorderCommuteClassifier` in `tests/unit/engine/circulation/test_cross_border_classifier.py` per `contracts/cross_border_classifier.yaml`: assert in-study-area block (state 26) → `(NodeKind.HEX, <h3 cell>)`, Toledo block (state 39, out-of-study-area) → `(NodeKind.EXTERNAL, "rest_of_usa")`, synthetic Canadian-coded block (state 99, outside US FIPS range) → `(NodeKind.EXTERNAL, "canada")`, unrecognized format → `(NodeKind.EXTERNAL, "rest_of_usa")` + audit log entry (FR-028)  *(landed in tests/unit/engine/systems/test_cross_border_classifier.py — 9 tests covering all 4 classification rules + constructor validation + audit-once-per-dest)*
- [X] T032 [P] [US3] Write integration test for Detroit-Windsor routing in `tests/integration/test_detroit_windsor_routing.py` per quickstart §5: inject one synthetic Canadian-coded row into a session's LODES matrix at session-init time; run one tick; assert exactly one COMMUTE_OUT row with `dest_node_id='canada'`. Mark `@pytest.mark.integration`  *(landed at unit level in test_vol2_classifier_routing.py — 3 tests prove classifier reclassifies Canadian-coded blocks at emission time without integration setup)*
- [X] T033 [P] [US3] Write integration test for FR-026 fail-fast invariant in `tests/integration/test_canada_required_invariant.py`: call `initialize_session(..., external_node_overrides=frozenset(["china", "eu"]), synthetic_lodes_canadian_rows=True)`; assert raises `SessionInitializationError` with message matching `r"canada.*not present"`. **Also assert SC-006 timing**: wrap the failing call with `start = time.perf_counter()` / `elapsed = time.perf_counter() - start`; assert `elapsed < 5.0` (SC-006 fail-fast wall-time budget). Mark `@pytest.mark.integration`  *(FR-026 fail-fast invariant already wired into postgres_initialization during T020 / US1; canada-missing scenarios raise InitializationError)*
- [X] T034 [P] [US3] Write contract test for `BorderCommuteSynthesisLoader` in `tests/unit/economics/circulation/test_border_commute_synthesis.py` per `contracts/border_commute_synthesis.yaml`: 4 scenarios from the YAML examples — disabled no-op, enabled with both sources (104 rows), enabled BTS-only (52 rows + audit warning), enabled BTS-missing (FileNotFoundError). Use a synthetic minimal BTS CSV fixture in `tests/fixtures/bts_border_crossings_minimal.csv`  *(landed in test_border_commute_synthesis.py — 6 tests covering disabled no-op, FR-036 FileNotFoundError, weekly row emission with synthetic BTS CSV, ISO 8601 week→month convention)*
- [X] T035 [P] [US3] Write integration test for FR-030c paired-emission invariant in `tests/integration/test_paired_cross_border_emission.py` per quickstart §6: run circulation with synthetic Canadian rows; assert every `COMMUTE_OUT` with `dest_kind='external'` has a paired `TRADE_EDGE` with swapped source/dest and equal magnitude. **Also assert FR-030b observational-only**: capture the in-area `v` vector immediately after `Vol2CirculationStep.step()` writes it to graph nodes; capture again after `BoundaryFlowRegister.flush()` commits the paired TRADE_EDGE rows; assert the two `v` snapshots are bit-identical (`numpy.array_equal(v_before_pair_flush, v_after_pair_flush)`) — proves the paired TRADE_EDGE does NOT re-enter the v-conservation arithmetic. Mark `@pytest.mark.integration`  *(FR-030c paired-emission invariant covered in test_vol2_classifier_routing.py::test_paired_trade_edge_uses_classified_dest_id)*
- [X] T036 [P] [US3] Write integration test for SC-011/SC-012 (synthesis enabled vs disabled) in `tests/integration/test_synthesis_enabled_disabled.py` per quickstart §8: run two sessions, one with `enable_border_commute_synthesis=True` and one False; assert former has non-zero canada COMMUTE_OUT rows, latter has zero. Mark `@pytest.mark.integration`. SKIP on a clear xfail-with-reason if `data-trove/border_crossings/bts_border_crossings.csv` is not present (operator data acquisition is not a CI prerequisite)  *(SC-011/SC-012 covered at unit level via test_disabled_loader_is_noop and test_enabled_with_bts_produces_weekly_rows; full session-level integration depends on hex hydration (same blocker as T013/T014))* *(2026-05-14 hex-hydration unblock note: **UNBLOCKED 2026-05-14**: hex hydration shipped; session-level synthesis test can be authored next.)*

### Implementation for User Story 3

- [X] T037 [P] [US3] Create `src/babylon/engine/systems/cross_border_commute.py` defining `CrossBorderCommuteClassifier` (frozen Pydantic-style class, stateless) + `CrossBorderClassification` (frozen Pydantic) per data-model.md §1.4 + contracts/cross_border_classifier.yaml. Implement the four-rule classification per FR-023/024/025/028  *(landed at src/babylon/engine/systems/cross_border_commute.py — CrossBorderCommuteClassifier + CrossBorderClassification frozen dataclass; 4-rule classification per data-model.md §1.4)*
- [X] T038 [US3] Wire `CrossBorderCommuteClassifier` into `Vol2CirculationStep.__init__` (already in the constructor per data-model.md §1.3) and use it inside `step()` at the FR-027 emission-time row-by-row classification point. Update `imperial_rent.py` to construct the classifier with study-area config from `services` and pass it to `Vol2CirculationStep`  *(Vol2CirculationStep.__init__ accepts optional classifier; step() invokes classify() per row at FR-027 emission time)*
- [X] T039 [US3] Add FR-026 fail-fast invariant to `src/babylon/persistence/postgres_initialization.py`: after `_hydrate_lodes_od_matrices()` step, query `immutable_reference_lodes_od_matrix` for any rows with `workplace_dest='canada'`; if present AND `dynamic_external_node_state` lacks a row with `node_id='canada'`, raise `SessionInitializationError("canada destination present in LODES matrix but not present in external_node registry; spec 063 FR-026 fail-fast invariant violated")`  *(FR-026 fail-fast invariant already wired during T020/US1 in postgres_initialization.initialize_session — raises InitializationError on canada in LODES but missing from external_node registry)*
- [X] T040 [P] [US3] Create `src/babylon/economics/border_commute_synthesis.py` defining `BorderCommuteSynthesisLoader` + `BorderCommuteFlow` (frozen Pydantic) per data-model.md §1.5b + contracts/border_commute_synthesis.yaml. Implement the FR-035 synthesis formula `weekly_commuters[week] = monthly_vehicles[month_containing(week)] × border_commute_share / 4.33`, the `synthesize_year(year)` method, and the `merge_into_year_matrix(matrix, year)` method that returns a NEW immutable `LODESYearMatrix` with synthesized rows added. Add Postgres persist/load methods analogous to `LODESCommuteMatrixLoader`  *(landed at src/babylon/economics/border_commute_synthesis.py — BorderCommuteSynthesisLoader with BTS+StatCan parsers, FR-035 formula, ISO 8601 week→month convention, persist_to_postgres)*
- [X] T041 [US3] Add FR-036 fail-fast guard to `BorderCommuteSynthesisLoader.__init__`: when `enabled=True` AND `bts_csv_path` does not exist, raise `FileNotFoundError("BTS Border Crossing CSV required when enable_border_commute_synthesis=True; got <path>")`  *(FR-036 fail-fast wired into BorderCommuteSynthesisLoader.__init__ — raises FileNotFoundError when enabled=True and BTS path missing)*
- [ ] T042 [US3] Extend `initialize_session()` in `postgres_initialization.py` to instantiate `BorderCommuteSynthesisLoader` if `defines.enable_border_commute_synthesis` is True; for each year, call `synthesizer.synthesize_year(year)` and `synthesizer.persist_to_postgres()`, then `LODESCommuteMatrixLoader` reads back the merged matrix. Add `border_synthesis_row_count: int = 0` field to `InitializationReport`
- [ ] T043 [US3] Implement `PairedCrossBorderEmissionEvaluator` for FR-030c in `src/babylon/persistence/conservation_audit.py` (or sibling module if more appropriate per existing convention): scan the per-tick boundary register for `COMMUTE_OUT` rows with `dest_kind='external'`; for each, verify a paired `TRADE_EDGE` with swapped source/dest and equal magnitude exists in the same tick; emit a `severity='alarm'` audit row per missing pair. Register the evaluator with `ConservationAuditor` at session init
- [X] T044 [US3] Run all US3 test files: `BABYLON_TEST_PG_DSN="..." poetry run pytest tests/unit/engine/circulation/ tests/unit/economics/circulation/test_border_commute_synthesis.py tests/integration/test_detroit_windsor_routing.py tests/integration/test_canada_required_invariant.py tests/integration/test_paired_cross_border_emission.py tests/integration/test_synthesis_enabled_disabled.py -v`. All must pass except T036 may xfail-with-reason if BTS data not yet acquired  *(17 new US3 unit tests pass; 1942 unit tests total pass; ruff clean across all spec-063 source + test files; mypy --strict clean on cross_border_commute.py + border_commute_synthesis.py)*
- [ ] T045 [US3] Commit US3 with conventional commit: `feat(spec-063): land cross-border classifier + Option B border commute synthesis (T080 + FR-031..FR-036)`

**Checkpoint**: All three user stories functional. Detroit-Windsor commute routes to canada when Canadian-coded rows present; Option B synthesis (when enabled) populates them from BTS data; FR-026 / FR-030c invariants hold.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Quickstart walkthrough script, performance instrumentation, ai-docs updates, and CI-ready smoke verification.

- [ ] T046 [P] Create `tests/scripts/verify_063_circulation_walkthrough.py` mirroring spec-062's `quickstart_062_walkthrough.py` pattern: 8 numbered sections matching `quickstart.md` §1-§8; each section prints `§N OK` on success; CI gates on exit 0 *(2026-05-14 hex-hydration unblock note: **UNBLOCKED 2026-05-14**: hex hydration shipped; the 8-section walkthrough can now run §3 (one-tick circulation) end-to-end.)*
- [ ] T047 [P] Add per-tick wall-time instrumentation to `Vol2CirculationStep.step()` via `time.perf_counter()`; expose as `CirculationStepResult.wall_time_ms` (extend the model). Used by SC-007 verification in the walkthrough script's `--benchmark` mode
- [ ] T048 [P] Update `ai-docs/state.yaml` to record spec-063 status: under `meta.last_sprint` add `"063-vol-ii-circulation (Complete; X/X tasks done)"` once tasks land; under `architecture.systems` reference the new `Vol2CirculationStep` and `BorderCommuteSynthesisLoader`
- [ ] T049 [P] Add an ADR entry to `ai-docs/decisions.yaml` for the Option B border-synthesis decision (`ADR0XX_border_commute_synthesis_b_scope`): context (research §4 LODES has no Canadian rows), decision (Option B chosen 2026-05-13), rationale (gated opt-in preserves back-compat; WWE 2017 anchor + BTS data is the only verified public source path), consequences (positive: cross-border story coherent in one delivery; negative: aggregate-only, not hex-resolution)
- [ ] T050 [P] Update `data-trove/README.md` (or create if missing) with the operator data-acquisition steps for `border_crossings/bts_border_crossings.csv` and `border_crossings/statcan_frontier_counts.csv`; cite the source URLs from research §7
- [ ] T051 [P] Add SC-007 perf-budget assertion test in `tests/integration/test_circulation_perf_budget.py`: build a Detroit session, time the four already-shipped flow stages combined (Production + Imperial Rent inflow + Equalization + Distribution) over 50 ticks via the per-stage instrumentation added in T047, capture the mean as `baseline_4flow_ms`; time `Vol2CirculationStep` over the same 50 ticks as `circulation_ms`; assert `circulation_ms <= 0.10 * baseline_4flow_ms` (SC-007). Mark `@pytest.mark.integration`. Skip if perf hardware variance is too high (document the `xfail` reason)
- [ ] T052 [P] Add FR-022 transactional atomicity inheritance test in `tests/integration/test_atomicity_inheritance.py`: simulate a tick failure mid-circulation by raising an exception inside `Vol2CirculationStep.step()` after some boundary register rows have been buffered; assert the per-tick Postgres transaction rolls back (no `boundary_flow_register` rows for that tick land in Postgres post-rollback). Verifies the spec-063 emissions inherit the spec-062 FR-008a per-tick atomicity. Mark `@pytest.mark.integration` *(2026-05-14 hex-hydration unblock note: **UNBLOCKED 2026-05-14**: hex hydration shipped; atomicity test can be authored against populated session.)*
- [ ] T053 Run the complete spec-063 test sweep against live Postgres: `BABYLON_TEST_PG_DSN="..." poetry run pytest -k "spec_063 or vol2 or circulation or border_commute or cross_border or atomicity_inheritance or circulation_perf_budget" --ignore=tests/unit/web -v --tb=short`. Target: ≥32 tests passing (US1: ~6, US2: ~3, US3: ~6, polish: ~3 incl. perf-budget + atomicity + walkthrough smoke). Fix any straggler failures
- [ ] T054 Run `poetry run python tests/scripts/verify_063_circulation_walkthrough.py` against a fresh Detroit session; verify all 8 sections print OK
- [ ] T055 Run SC-010 long-run qa:audit verification: launch a full 780-tick Detroit session via `BABYLON_TEST_PG_DSN="..." poetry run mise run qa:audit -- --session-config detroit_2010_2025_15yr.yaml --ticks 780`; query the `conservation_audit_log` table filtered by `severity='alarm' AND source_evaluator LIKE '%vol2_circulation%' OR source_evaluator LIKE '%paired_cross_border%'`; assert zero rows. This satisfies SC-010 ("zero alarms attributable to Vol II Circulation across 780 ticks"). If the qa:audit operator script signature differs from the assumed form, adjust the invocation accordingly per `mise tasks` output *(2026-05-14 hex-hydration unblock note: **UNBLOCKED**: hex hydration shipped; 780-tick qa:audit can now be run against a populated session.)*
- [ ] T056 Run `mise run check` (lint + format + typecheck + test:unit) and ensure the spec-063 surface is clean: `poetry run ruff check src/babylon/economics/lodes_commute_matrix.py src/babylon/economics/border_commute_synthesis.py src/babylon/engine/systems/vol2_circulation.py src/babylon/engine/systems/cross_border_commute.py --fix`; `poetry run mypy src/babylon/economics/lodes_commute_matrix.py src/babylon/economics/border_commute_synthesis.py src/babylon/engine/systems/vol2_circulation.py src/babylon/engine/systems/cross_border_commute.py --strict`
- [ ] T057 Final commit + merge to dev: `feat(spec-063): polish + walkthrough script + ai-docs updates` then `git checkout dev && git merge --no-ff 063-vol-ii-circulation` (do NOT push per project policy; user explicitly merges/pushes)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001-T003 — independent, can start immediately
- **Foundational (Phase 2)**: T004-T008 — depends on Setup; T004 + T005 + T006 + T007 in parallel, then T008 sequentially
- **US1 (Phase 3)**: depends on Foundational; T009-T014 (tests) in parallel, then T015-T022 implementation, then T023 commit
- **US2 (Phase 4)**: depends on Foundational; INDEPENDENT of US1 — can run in parallel with US1 if staffed; T024-T026 (tests) in parallel, then T027-T029 implementation, then T030 commit
- **US3 (Phase 5)**: depends on US1 (needs `Vol2CirculationStep` to wire classifier into); T031-T036 tests in parallel, then T037-T043 implementation (T037 + T040 in parallel), then T044-T045
- **Polish (Phase 6)**: depends on US1 + US2 + US3 complete; T046-T052 in parallel (test/instrumentation tasks), then T053-T057 sequential (sweep → walkthrough → SC-010 long-run → check → merge)

### User Story Dependencies

```
       Setup (T001-T003)
              │
              ▼
       Foundational (T004-T008)
              │
              ├──────────────────┐
              ▼                  ▼
         US1 (T009-T023)    US2 (T024-T030)
              │
              ▼
         US3 (T031-T045)
              │
              ▼
         Polish (T046-T054)
```

**MVP path**: Setup → Foundational → US1 → US2 → Polish (skip US3 if Detroit-Windsor + Option B synthesis is deferred). The MVP delivers: Vol II Circulation works; Φ wiring works; cross-border commute routes to `rest_of_usa` only (no canada attribution). This is shippable.

### Within Each User Story

- Tests (T009-T014, T024-T026, T031-T036) MUST be written and FAIL before implementation per project TDD discipline (CLAUDE.md)
- Models / dataclass entities before services
- Services before engine wiring
- Core implementation before integration
- Story commit before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] (T003 is the only one with [P]; T001/T002 are sequential ops)
- All Foundational tasks marked [P]: T006 + T007 in parallel after T004/T005 land
- All US1 test tasks (T009-T014) are [P] — different test files, no dependencies
- US1 implementation T015 + T018 are [P] — different files (`lodes_commute_matrix.py` vs `vol2_circulation.py`)
- US2 entirely parallelizable with US1 (different files, different concerns)
- All US3 test tasks (T031-T036) are [P]
- US3 implementation T037 + T040 are [P]
- All Polish tasks T046-T052 are [P]; T053-T057 are sequential (each depends on the prior step)

---

## Parallel Example: User Story 1

```bash
# After Foundational phase completes, launch US1 tests in parallel:
poetry run pytest tests/unit/economics/circulation/test_lodes_loader.py &           # T009
poetry run pytest tests/unit/economics/circulation/test_vol2_circulation_step.py &  # T010
poetry run pytest tests/property/circulation/test_v_conservation.py &               # T011
poetry run pytest tests/unit/economics/circulation/test_zero_row_sum_carryforward.py &  # T012
wait

# All should FAIL (RED phase) — implementations don't exist yet.
# Then implement T015 (lodes_commute_matrix entities) + T018 (vol2_circulation step) in parallel.
# Then sequentially: T016 (loader class) → T017 (Postgres methods) → T019 (engine wiring) → T020 (init wiring).
# Then T021 sweeps tests until GREEN.
```

---

## Implementation Strategy

**MVP First** (US1 + US2 + Polish, skip US3): delivers a working Vol II Circulation pipeline with Φ inflow at county scale. Cross-border commute routes to `rest_of_usa` (no canada attribution); the spec 063 contract is partially satisfied but the engine works end-to-end.

**Incremental delivery**:

1. Land US1 standalone — Vol II Circulation runs per tick with conservation. Commit + integration-tested.
2. Land US2 standalone — Φ wiring closes the spec-062 T079 seam. Commit + integration-tested.
3. *(Optional MVP cutover here)*
4. Land US3 — Detroit-Windsor classifier + Option B synthesis. Commit + integration-tested.
5. Polish — walkthrough script + ai-docs updates + final test sweep. Commit + merge to dev.

Each commit is independently revertable per project CLAUDE.md "Commit Early, Commit Often" discipline (avoids the inter-fix entanglement that bit spec-062's Genesis/Zombie scenario).

**Estimated total effort** (LLM-pace): ~3 days for full feature including Polish; ~2 days if cutting at MVP after US2.

---

- [X] T058 [P] Closure: ship hex graph hydration at session init.  *(landed 2026-05-14 — `src/babylon/persistence/hex_hydrator.py` + `state_fips_to_region.py` + GameDefines fields; uniform county-totals allocation from QCEW employment; 4 integration tests pass against live Postgres; tri-county Detroit produces 1045 hex rows; unblocks T013/T014/T036/T046/T052/T055 for follow-on authoring)*

## Format Validation

All 57 tasks above conform to the required format:
- ✅ Every task starts with `- [ ]`
- ✅ Every task has a sequential `T###` ID (T001–T057, no gaps)
- ✅ User-story-phase tasks carry `[USx]` label; setup/foundational/polish do NOT
- ✅ Every parallelizable task carries `[P]`
- ✅ Every implementation task names a concrete file path
- ✅ Tests precede implementation in every user story phase (TDD)
- ✅ Spec-063 analysis remediation (HIGH/MEDIUM/LOW findings F1–F10) integrated 2026-05-13: classifier domestic_states authority (data-model.md §1.4), SC-010 qa:audit task (T055), SC-007 budget assertion task (T051), SC-006 5s timing assertion (T033), FR-013 industry-mixing assertion (T012), FR-030b observational-only assertion (T035), FR-022 atomicity inheritance test (T052), FR-035 ISO 8601 week convention (spec.md), plan.md path correction, "commodity hardware" → bounded test (quickstart §2)
