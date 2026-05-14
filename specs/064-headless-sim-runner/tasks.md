---

description: "Tasks for Spec 064 - Headless Postgres-Backed Simulation Runner"
---

# Tasks: Headless Postgres-Backed Simulation Runner

**Input**: Design documents from `/specs/064-headless-sim-runner/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests ARE included. Project uses TDD per CLAUDE.md, and the
runner must surface conservation-invariant violations from the spec-053/054/
055/056 Hypothesis suite. Test tasks run before their corresponding
implementation tasks within each user story.

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project scaffolding for the new module.

- [ ] T001 Verify `tqdm` is present in `pyproject.toml` under `[tool.poetry.dependencies]`; add as `^4.66` if absent.
- [ ] T002 Create empty `src/babylon/engine/headless_runner/` package directory with `__init__.py` containing module docstring + `from .runner import run; __all__ = ["run"]`.
- [ ] T003 [P] Add the new `data:sim-e2e-michigan` and `sim:e2e-michigan` mise task scaffolds in `.mise.toml` (descriptions only, runs stubbed to `echo "not yet implemented"`).
- [ ] T004 [P] Create `tests/integration/test_headless_runner.py` skeleton with module-level `pytestmark` requiring `BABYLON_TEST_PG_DSN` env var + SQLite reference DB present (mirror `tests/integration/test_hex_hydration.py` pattern).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Pydantic data model + Postgres migration that ALL user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T005 [P] Create `src/babylon/engine/headless_runner/models.py` with `ExitReason` StrEnum (COMPLETED, EARLY_TERMINATED, USER_INTERRUPTED, ERRORED) per data-model.md §1.3.
- [ ] T006 [P] Create frozen Pydantic `SimulationRunConfig` model in `src/babylon/engine/headless_runner/models.py` per data-model.md §1.1. Include validators: `ticks ∈ [1, 100_000]`, `start_year ∈ [1900, 2100]`, all FIPS codes 5-digit strings.
- [ ] T007 [P] Create frozen Pydantic `PerformanceBreakdown` model in `src/babylon/engine/headless_runner/models.py` per data-model.md §1.4.
- [ ] T008 [P] Create frozen Pydantic `AuditEntry` model in `src/babylon/engine/headless_runner/models.py` per data-model.md §1.5.
- [ ] T009 [P] Create frozen Pydantic `TraceRow` model in `src/babylon/engine/headless_runner/models.py` per data-model.md §1.6 (22 fields, all nullable except identity fields).
- [ ] T010 Create frozen Pydantic `SimulationRunResult` model in `src/babylon/engine/headless_runner/models.py` per data-model.md §1.2 (depends on T005–T008).
- [ ] T011 Create Postgres migration `src/babylon/persistence/migrations/0019_trace_emission_view.sql` defining `view_runtime_trace_emission` per data-model.md §3.1. View JOINs `dynamic_county_economic_state` ⨝ `dynamic_county_consciousness_state` ⨝ `dynamic_county_territory_state` (LEFT joins on `session_id, tick, fips`) with computed `profit_rate` + `exploitation_rate`. Add `COMMENT ON VIEW` citing spec-064 + II.11.
- [ ] T012 Create predefined-scope resolver `src/babylon/engine/headless_runner/scopes.py` with the 4 named scopes from `contracts/cli_contract.yaml` (`michigan-canada`, `michigan-statewide-no-canada`, `detroit-tri-county`, `national`). Each scope yields `(scope_fips: frozenset[str], external_node_ids: frozenset[str])`.
- [ ] T013 [P] Create `src/babylon/engine/headless_runner/argparse_cli.py` with `build_parser()` returning an argparse parser implementing every flag from `contracts/cli_contract.yaml`. Pure parser construction; no run logic yet.
- [ ] T014 [P] Create `src/babylon/engine/headless_runner/__main__.py` (entry point for `python -m babylon.engine.headless_runner`) that invokes `argparse_cli.build_parser()` + dispatches to `runner.run()` (which is a stub at this stage).

**Checkpoint**: Foundation ready — entities, scopes, migration, CLI skeleton all in place. User-story implementation can now begin.

---

## Phase 3: User Story 1 — Headless 1000-tick Michigan run produces parseable artifacts (Priority: P1) 🎯 MVP

**Goal**: A single `mise run sim:e2e-michigan` invocation runs the full headless simulation against PostgresRuntime, emits `trace.csv` + `summary.json` + `manifest.json` matching the contracts in `contracts/`, and exits with the correct code per `cli_contract.yaml`.

**Independent Test**: Invoke `mise run sim:e2e-michigan -- --scope detroit-tri-county --ticks 100`; assert the artifact directory contains all 3 files, that each parses via standard library, and that the `manifest.input_hash` matches a re-run.

### Tests for User Story 1 (TDD — write first)

- [ ] T015 [P] [US1] Schema parity unit test in `tests/unit/persistence/test_trace_view_columns.py` — query `view_runtime_trace_emission` column list, assert it matches the 22 columns in `contracts/trace_csv_schema.yaml`.
- [ ] T016 [P] [US1] Unit test in `tests/unit/engine/test_trace_emitter.py` — feed synthetic per-tick rows into `TraceEmitter`, assert CSV header + per-row column ordering match `contracts/trace_csv_schema.yaml`.
- [ ] T017 [P] [US1] Unit test in `tests/unit/engine/test_run_summary.py` — build a `RunSummary` from fixture state, assert resulting JSON validates against `contracts/summary_json_schema.yaml` (use `jsonschema` from stdlib or jsonschema package).
- [ ] T018 [P] [US1] Unit test in `tests/unit/engine/test_manifest_builder.py` — build manifest from fixture run, assert `input_hash` is stable across two builds with identical inputs (deterministic JSON serialization).
- [ ] T019 [P] [US1] Unit test in `tests/unit/engine/test_scope_resolver.py` — assert all 4 predefined scopes resolve to documented FIPS sets; assert `detroit-tri-county` yields `{26163, 26125, 26099}`; assert `national` yields ≥3000 FIPS.
- [ ] T020 [P] [US1] Unit test in `tests/unit/engine/test_argparse_cli.py` — every flag in `contracts/cli_contract.yaml` is accepted; conflicting `--scope` + `--fips` exits with code 2; invalid FIPS exits 2.
- [ ] T021 [US1] Integration test in `tests/integration/test_headless_runner.py::test_smoke_tri_county` — full `runner.run()` with `--scope detroit-tri-county --ticks 100`. Assert exit 0, all 3 artifacts written, JSON validates against schemas, CSV row count == 3 × 100 = 300.
- [ ] T022 [US1] Integration test in `tests/integration/test_headless_runner.py::test_determinism` — run twice with identical config, assert `trace.csv` bytes-identical AND `summary.json` identical modulo wallclock fields.
- [ ] T023 [US1] Integration test in `tests/integration/test_headless_runner.py::test_sigint_partial_artifacts` — start a 1000-tick run, send SIGINT mid-run via `os.kill`, assert exit 130, partial artifacts written, `manifest.partial=true`, `summary.exit_reason="user_interrupted"`.
- [ ] T024 [US1] Integration test in `tests/integration/test_headless_runner.py::test_output_dir_overwrite` — invoke twice with same `--output-dir`, assert second run silently overwrites first (no error, no suffix).

### Implementation for User Story 1

- [ ] T025 [P] [US1] Implement `TraceEmitter` class in `src/babylon/engine/headless_runner/trace_emitter.py` that streams `view_runtime_trace_emission` query results to `trace.csv` via `csv.writer`. Header row matches `contracts/trace_csv_schema.yaml` column order. Empty string for None per spec FR-008.
- [ ] T026 [P] [US1] Implement `SummaryBuilder` class in `src/babylon/engine/headless_runner/run_summary.py` that builds `RunSummary` from session-end state: query terminal-tick aggregates, project `conservation_audit_log` rows to `AuditEntry[]`, compute `external_node_flows` via SUM(magnitude) over `dynamic_boundary_flow_log` per source/dest.
- [ ] T027 [P] [US1] Implement `ManifestBuilder` class in `src/babylon/engine/headless_runner/manifest.py` that builds the manifest payload per `contracts/manifest_json_schema.yaml`. `input_hash` = `hashlib.sha256(json.dumps(deterministic_inputs, sort_keys=True).encode())`. Read `git_sha` via `subprocess.run(["git", "rev-parse", "HEAD"])` with fallback to "unknown" on failure.
- [ ] T028 [US1] Implement core `run(config: SimulationRunConfig) -> SimulationRunResult` in `src/babylon/engine/headless_runner/runner.py`. Bootstrap Postgres pool, call `initialize_session` with `hex_hydration_counties=config.scope_fips`, enter tick loop, wire `TraceEmitter` + `SummaryBuilder` + `ManifestBuilder`. Depends on T025–T027.
- [ ] T029 [US1] Implement cooperative SIGINT handler in `runner.py` per research.md R3: module-level `_interrupt_requested` flag set by `signal.signal(signal.SIGINT, ...)`, checked at top of each iteration. After first SIGINT, restore `signal.SIG_DFL` so a second Ctrl-C aborts immediately.
- [ ] T030 [US1] Implement tqdm progress bar in `runner.py` per research.md R2: wrap the tick range with `tqdm(..., file=sys.stderr, disable=not sys.stderr.isatty(), mininterval=1.0, unit="tick")`.
- [ ] T031 [US1] Implement output directory creation + overwrite logic in `runner.py`: timestamp-based default (`reports/sim-runs/<UTC-ISO>/`), `shutil.rmtree(path, ignore_errors=True)` + `mkdir(parents=True)` per spec clarification Q2 / FR-007.
- [ ] T032 [US1] Implement CLI entry point in `__main__.py`: parse args via `argparse_cli.build_parser()`, build `SimulationRunConfig`, dispatch to `runner.run()`, map `ExitReason` → exit code per `contracts/cli_contract.yaml`, print only the artifact directory path on stdout for exit 0.
- [ ] T033 [US1] Wire end-game detection in `runner.py`: poll `EndgameDetector` after each tick (or accept whatever the existing observer surfaces), set `exit_reason = EARLY_TERMINATED` + `end_game_event` in summary on detection.
- [ ] T034 [US1] Update `.mise.toml` task `sim:e2e-michigan` to invoke `poetry run python -m babylon.engine.headless_runner --scope michigan-canada` (replacing T003's stub).
- [ ] T035 [US1] Apply migration `0019_trace_emission_view.sql` in test conftest (`tests/integration/conftest.py` or per-test fixture) so the view is present before integration tests run. Reuse the `apply_migrations` fixture pattern from `tests/integration/test_tiger_ingestion.py`.

**Checkpoint**: US1 fully functional. Operator + LLM agent can run the canonical simulation end-to-end and parse the artifacts.

---

## Phase 4: User Story 2 — Monte Carlo continues to work, now Postgres-backed (Priority: P2)

**Goal**: `mise run sim:monte-carlo N` runs N replicate headless simulations through the new runner, varying only the random seed across replicates. Pre-existing CSV-per-sample + aggregate-statistics output contract preserved.

**Independent Test**: `mise run sim:monte-carlo 5 -- --scope detroit-tri-county --ticks 50`; assert 5 sample rows in output CSV, non-zero variance across replicates, same top-level seed → byte-identical full output.

### Tests for User Story 2

- [ ] T036 [P] [US2] Integration test in `tests/integration/test_monte_carlo_postgres.py::test_n_samples_yields_n_rows` — 5 samples, assert exactly 5 rows in `results/monte_carlo.csv`.
- [ ] T037 [P] [US2] Integration test in `tests/integration/test_monte_carlo_postgres.py::test_top_level_seed_reproducible` — two runs with same top-level seed produce byte-identical aggregate output CSV.
- [ ] T038 [P] [US2] Integration test in `tests/integration/test_monte_carlo_postgres.py::test_per_sample_variance_nonzero` — assert std-dev across samples > 0 for at least one numeric column (proves real stochastic divergence).

### Implementation for User Story 2

- [ ] T039 [US2] Refactor `tools/shared.py:run_simulation()` to invoke `babylon.engine.headless_runner.run()` internally. Build `SimulationRunConfig` from the existing parameter dict; map result to the pre-existing return shape (list of tick dicts + metadata dict). Preserve function signature exactly.
- [ ] T040 [US2] Update `tools/monte_carlo.py` imports — remove `from babylon.engine.scenarios import create_imperial_circuit_scenario` and `from babylon.engine.simulation_engine import step` if present; rely entirely on `shared.run_simulation`. mise task name `sim:monte-carlo` unchanged.

**Checkpoint**: Monte Carlo functional via the new runner.

---

## Phase 5: User Story 3 — Parameter sweeps, sensitivity analysis, profiling continue to work (Priority: P2)

**Goal**: The 5 remaining `tools/` analysis scripts that today bypass Postgres are refactored to route through the new runner. All mise task names, flag names, and output-file shapes preserved (SC-004). No `tools/` script imports `create_imperial_circuit_scenario` / `WorldState` / `step` post-refactor (SC-007).

**Independent Test**: Each affected mise task runs to completion with small test parameters and produces non-empty output of the documented shape.

### Tests for User Story 3

- [ ] T041 [P] [US3] Import-boundary audit test in `tests/integration/test_tools_no_legacy_imports.py` — recursively `ast.parse()` every `.py` under `tools/`, assert NONE import `create_imperial_circuit_scenario`, `WorldState`, or `babylon.engine.simulation_engine.step`. Enforces SC-007.
- [ ] T042 [P] [US3] Smoke test in `tests/integration/test_sim_sweep_postgres.py` — `mise run sim:sweep` with a 3-point sweep produces a CSV with 3 distinct parameter values.
- [ ] T043 [P] [US3] Smoke test in `tests/integration/test_tune_morris_postgres.py` — `mise run tune:morris 8` produces `results/morris.json` with the documented schema and non-empty `mu_star` column.
- [ ] T044 [P] [US3] Smoke test in `tests/integration/test_profiler_postgres.py` — `mise run sim:profile 50` produces a `.prof` file readable by `pstats.Stats`.
- [ ] T045 [P] [US3] Smoke test in `tests/integration/test_qa_audit_postgres.py` — `mise run qa:audit` writes `reports/audit_latest.md` with the existing 3-scenario structure.

### Implementation for User Story 3

- [ ] T046 [P] [US3] Refactor `tools/parameter_analysis.py` — remove direct engine imports; route all sweep/trace logic through `tools.shared.run_simulation()`. Preserve `trace` + `sweep` subcommands and their CSV column conventions.
- [ ] T047 [P] [US3] Refactor `tools/sensitivity_analysis.py` (Morris + Sobol) — same pattern. Preserve `results/morris.json` + `results/sobol.json` schemas.
- [ ] T048 [P] [US3] Refactor `tools/profiler.py` — invoke `cProfile.Profile()` around `tools.shared.run_simulation()` instead of the legacy in-memory path. Preserve `.prof` output filename + `pstats` reporting.
- [ ] T049 [P] [US3] Refactor `tools/audit_simulation.py` — route through `tools.shared.run_simulation()` for each of the 3 scenarios (baseline, starvation, glut). Preserve `reports/audit_latest.md` markdown structure.
- [ ] T050 [P] [US3] Refactor `tools/landscape_analysis.py` — same pattern. Preserve `results/landscape.csv` 2D-grid output shape.

**Checkpoint**: All 6 in-scope `tools/` scripts now backed by the headless runner. SC-007 enforced by T041.

---

## Phase 6: User Story 4 — CI gate uses runner as long-form e2e regression check (Priority: P3)

**Goal**: A CI invocation runs the canonical Michigan run, gates on conservation invariants and baseline-comparison metrics, and surfaces violations as a CI failure.

**Independent Test**: Run the gating script locally against a fresh run; assert it passes for a clean run and fails when given an artifact bundle with seeded invariant violations.

### Tests for User Story 4

- [ ] T051 [P] [US4] Integration test in `tests/integration/test_ci_gate_clean.py` — full Michigan run, then assert `summary.conservation_audit` has zero entries with severity `critical`. Skipped unless `BABYLON_TEST_PG_DSN` set AND `BABYLON_SLOW_TESTS=1` (this is the long-form gate, opt-in).
- [ ] T052 [P] [US4] Integration test in `tests/integration/test_ci_gate_baseline_compare.py` — load the committed baseline from `tests/baselines/michigan-e2e.json`, run the simulation, assert key terminal aggregates within tolerance (`total_v` ±1%, `counties_alive` exact match).

### Implementation for User Story 4

- [ ] T053 [US4] Create `tests/baselines/michigan-e2e.json` by running the canonical headless simulation once and copying its `summary.json` (operator instruction documented in `quickstart.md`). Add a one-line `tests/baselines/README.md` explaining the regeneration procedure.
- [ ] T054 [US4] Extend `tools/regression_test.py` to compare a fresh artifact bundle's `summary.json` against `tests/baselines/michigan-e2e.json` under documented tolerances. Preserve existing mise task `qa:regression`.
- [ ] T055 [US4] Add `mise run qa:e2e-regression` task in `.mise.toml` that runs the headless runner, then invokes `tools/regression_test.py` with the produced bundle and the committed baseline; non-zero exit on tolerance violation.

**Checkpoint**: CI gate fully functional and opt-in. US4 can be wired into a nightly workflow when the team is ready.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Wallclock-budget verification, documentation updates, ai-docs sync, retirement decisions.

- [ ] T056 [P] Add wallclock-budget assertion to `tests/integration/test_headless_runner.py::test_smoke_full_michigan` — full Michigan + Canada 1000-tick run completes in ≤ 600s. Skipped unless `BABYLON_SLOW_TESTS=1`. Implements SC-002 verification per research.md R10.
- [ ] T057 [P] Add ADR entry `ADR037_headless_simulation_runner` to `ai-docs/decisions.yaml` documenting: (a) headless runner becomes canonical sim entry; (b) `tools/shared.py` is the migration seam; (c) `view_runtime_trace_emission` is the II.11-compliant trace contract.
- [ ] T058 [P] Update `ai-docs/state.yaml` test counts and add `spec-064: completed` once integration tests are green.
- [ ] T059 [P] Update `ai-docs/tooling.yaml` to document the new `sim:e2e-michigan`, `qa:e2e-regression`, and (if added) `data:sim-bootstrap` tasks.
- [ ] T060 Decide fate of legacy `sim:run` mise task (`python -m babylon`): either (a) retire and document removal in commit, or (b) keep as a smoke-test shim. Update `.mise.toml` accordingly. Default: keep with a description noting it's a legacy smoke-test.
- [ ] T061 Run the full `quickstart.md` walkthrough end-to-end (operator path + LLM-agent path + CI path) and update any drift discovered.
- [ ] T062 Run `mise run check` and fix any lint / mypy / pre-commit fallout introduced by the new module + refactored tools.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001–T004 can start immediately. T001 + T003 parallel; T002 + T004 parallel (independent).
- **Foundational (Phase 2)**: Depends on Setup. T005–T009 + T013 + T014 all parallel (different files). T010 sequential after T005–T008 (uses them). T011 + T012 independent. **BLOCKS all user stories.**
- **User Story 1 (P1)**: Depends on Foundational. T015–T020 parallel (test stubs). T025–T027 parallel (3 independent files). T028 depends on T025–T027. T029–T034 mostly sequential against `runner.py` (same file) except T034 (different file).
- **User Story 2 (P2)**: Depends on US1 (uses `headless_runner.run()`). T036–T038 parallel (separate test files). T039 sequential (modifies `shared.py`). T040 after T039.
- **User Story 3 (P2)**: Depends on US2 (uses migrated `shared.run_simulation()`). T041–T045 parallel (separate test files). T046–T050 parallel (different `tools/` files).
- **User Story 4 (P3)**: Depends on US1 + US3 (baseline must be regeneratable). T051 + T052 parallel. T053 sequential (writes baseline). T054 + T055 sequential after T053.
- **Polish (Phase 7)**: Depends on all desired user stories complete. T056–T061 mostly parallel.

### User Story Dependencies

- US1 (P1) is the MVP. Stop here for a viable v1 if needed.
- US2 (P2) depends on US1 — Monte Carlo wraps the runner.
- US3 (P2) depends on US2 — tools migration shares the `tools/shared.py` seam established by US2.
- US4 (P3) depends on US1 (artifact format) and US3 (regression script). Optional gate; can be deferred.

### Within Each User Story

- Tests (T015–T024 for US1; T036–T038 for US2; etc.) written first; expected to FAIL initially, then PASS after implementation tasks complete.
- Foundational models before services (T025–T027 before T028).
- Core implementation before CLI wiring (T028 before T032).
- T035 (migration application) must precede integration test execution.

### Parallel Opportunities

- **Phase 1**: T001 ∥ T003 ∥ T002 ∥ T004 — 4-way parallel.
- **Phase 2**: T005 ∥ T006 ∥ T007 ∥ T008 ∥ T009 ∥ T013 ∥ T014 — 7-way parallel; T011 + T012 ∥ in a second wave; T010 sequential after T005–T008.
- **Phase 3 tests**: T015 ∥ T016 ∥ T017 ∥ T018 ∥ T019 ∥ T020 — 6-way parallel.
- **Phase 3 impl**: T025 ∥ T026 ∥ T027 — 3-way parallel; T028 sequential.
- **Phase 5 tests**: T041 ∥ T042 ∥ T043 ∥ T044 ∥ T045 — 5-way parallel.
- **Phase 5 impl**: T046 ∥ T047 ∥ T048 ∥ T049 ∥ T050 — 5-way parallel (different files).
- **Phase 7**: T056 ∥ T057 ∥ T058 ∥ T059 — 4-way parallel.
- **Cross-story**: Once US1 is checkpoint-complete, US2 implementation can begin; once US2 checkpoints, US3 can begin in parallel with US4 setup work.

---

## Implementation Strategy

### MVP First (US1 only)

The runner is shippable as soon as US1 checkpoints:
- T001–T035 (Setup + Foundational + US1 tests + US1 impl).
- ~35 tasks; produces a working `mise run sim:e2e-michigan` + LLM-parseable artifacts.
- Defer US2/US3 (`tools/` migration) until after MVP confirms the runner's I/O contract is stable.

### Incremental Delivery After MVP

1. **Commit MVP** at end of US1. `tools/` continues to use the legacy in-memory path; SC-007 import audit fails (intentionally). Mark in commit message: "MVP only; tools/ migration pending US2 + US3."
2. **US2 sprint**: Migrate `tools/shared.py` + `monte_carlo`. Commit; ~5 tasks.
3. **US3 sprint**: Migrate remaining 5 tool scripts in parallel; one commit per tool OR one consolidated commit. ~10 tasks; SC-007 audit now passes.
4. **US4 sprint**: Generate baseline + wire regression gate; ~5 tasks; opt-in CI workflow.
5. **Polish**: Wallclock test, ai-docs updates, lint sweep; ~7 tasks.

### Suggested first commit

`feat(spec-064): land MVP headless Postgres simulation runner (T001-T035)` — covers MVP scope, leaves `tools/` migration as follow-up commits per user story.

---

## Parallel Example: User Story 1

After Phase 2 checkpoints, US1's parallel test-writing phase can run as
6 concurrent work items, one per test file:

```bash
# Open 6 editor tabs / 6 agent sessions, each tackles one test file:
- T015: tests/unit/persistence/test_trace_view_columns.py
- T016: tests/unit/engine/test_trace_emitter.py
- T017: tests/unit/engine/test_run_summary.py
- T018: tests/unit/engine/test_manifest_builder.py
- T019: tests/unit/engine/test_scope_resolver.py
- T020: tests/unit/engine/test_argparse_cli.py
```

All 6 should FAIL (red phase). Then the implementation tasks T025–T027
can also proceed in parallel (3 separate files), and T028 closes the loop.

---

## Format Validation

Every task in this file satisfies the strict format:
`- [ ] T### [P?] [Story?] Description with file path`

- ✓ All 62 tasks begin with `- [ ]`
- ✓ All tasks have sequential IDs T001–T062
- ✓ Parallelizable tasks marked `[P]`
- ✓ User-story tasks have `[US1]` / `[US2]` / `[US3]` / `[US4]` labels
- ✓ Setup / Foundational / Polish tasks have no story labels
- ✓ Every task description includes a concrete file path

---

## Summary

- **Total tasks**: 62
- **Phase 1 (Setup)**: 4 tasks
- **Phase 2 (Foundational)**: 10 tasks (T005–T014)
- **Phase 3 (US1, MVP)**: 21 tasks (T015–T035) — 10 tests + 11 implementation
- **Phase 4 (US2)**: 5 tasks (T036–T040) — 3 tests + 2 implementation
- **Phase 5 (US3)**: 10 tasks (T041–T050) — 5 tests + 5 refactors
- **Phase 6 (US4)**: 5 tasks (T051–T055) — 2 tests + 3 implementation
- **Phase 7 (Polish)**: 7 tasks (T056–T062)
- **MVP scope**: T001–T035 (35 tasks) — ships a working runner without `tools/` migration
- **Highest parallelism**: Phase 2 Foundational (7-way) and Phase 5 implementation (5-way)
- **Independent test criteria**: Documented per user story (see Phase 3/4/5/6 headers)
