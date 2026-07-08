---

description: "Task list for spec-069 — SQLite per-tick read cache for the bridged headless runner"
---

# Tasks: SQLite per-tick read cache for the bridged headless runner

**Input**: Design documents from `/home/user/projects/game/babylon/specs/069-sqlite-cache-optimization/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` — all present.

**Tests**: Included. The project's `CLAUDE.md` mandates TDD (Red-Green-Refactor) for all code changes, so tests are not optional here even though spec.md does not name them explicitly.

**Organization**: Tasks are grouped by user story (US1 P1, US2 P2, US3 P3) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (`US1`, `US2`, `US3`)
- Include exact absolute file paths in descriptions

## Path Conventions

- Source: `src/babylon/engine/headless_runner/`, `src/babylon/persistence/`
- Tests: `tests/unit/engine/headless_runner/`, `tests/integration/engine/headless_runner/`
- Specs: `specs/069-sqlite-cache-optimization/` (no source changes; reference only)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm Phase 0/1 artifacts and create the empty module skeleton that all subsequent tasks edit.

- [x] T001 Verify Phase 0/1 artifacts exist at `/home/user/projects/game/babylon/specs/069-sqlite-cache-optimization/{spec.md,plan.md,research.md,data-model.md,contracts/,quickstart.md}` (read-only `ls` check) (verified 2026-07-08: specs/069-sqlite-cache-optimization/ contains spec.md, plan.md, research.md, data-model.md, contracts/, quickstart.md)
- [x] T002 [P] Create empty module `/home/user/projects/game/babylon/src/babylon/engine/headless_runner/reference_data_cache.py` with the spec-cross-reference module docstring, future-annotations import, and `__all__ = []` placeholder (verified 2026-07-08: src/babylon/engine/headless_runner/reference_data_cache.py exists — skeleton superseded by full implementation)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Pure data structures and the pure-function year-set derivation. No DB I/O. No bridge changes. Establishes the type vocabulary every later task uses.

**⚠️ CRITICAL**: All user-story phases depend on this. Phase 2 MUST be complete before Phase 3 begins.

- [x] T003 Implement `derive_year_set(start_year: int, total_ticks: int) -> frozenset[int]` pure function in `/home/user/projects/game/babylon/src/babylon/engine/headless_runner/reference_data_cache.py` per research R3 (returns `frozenset()` for `total_ticks <= 0`) (verified 2026-07-08: src/babylon/engine/headless_runner/reference_data_cache.py:56)
- [x] T004 Implement frozen Pydantic `ReferenceCacheEntry` model (`population: int | None`, `employment_proxy: float | None`) in `/home/user/projects/game/babylon/src/babylon/engine/headless_runner/reference_data_cache.py` per data-model.md §1 (verified 2026-07-08: src/babylon/engine/headless_runner/reference_data_cache.py:89)
- [x] T005 [P] Write unit tests for `derive_year_set` in `/home/user/projects/game/babylon/tests/unit/engine/headless_runner/test_reference_data_cache_year_set.py` — degenerate (0, 1, 52, 53 ticks), canonical (520 ticks → 10 years per R3), and weekly-boundary cases (verified 2026-07-08: tests/unit/engine/headless_runner/test_reference_data_cache_year_set.py)
- [x] T006 [P] Write unit tests for `ReferenceCacheEntry` validation in `/home/user/projects/game/babylon/tests/unit/engine/headless_runner/test_reference_data_cache_entry.py` — all four nullability combinations, non-negative validators, frozen semantics (verified 2026-07-08: tests/unit/engine/headless_runner/test_reference_data_cache_entry.py)

**Checkpoint**: Foundation ready — user story implementation can begin.

---

## Phase 3: User Story 1 — Canonical run finishes within the tightened time budget (Priority: P1) 🎯 MVP

**Goal**: The cache is wired end-to-end. Every per-tick population / employment-proxy lookup is served from the in-memory cache populated at `bridge.hydrate_initial`. The canonical 520-tick Michigan-Canada run completes in ≤ 60 min (SC-001) on the published seed.

**Independent Test**: Run `mise run sim:headless -- --scenario canonical --ticks 520 --start-year 2010 --seed 42`; assert `manifest.json.wallclock_seconds <= 3600` AND `manifest.json.bridge_db_reads.total_db_reads == 1660`. If both hold, US1 is fully functional.

### Tests for User Story 1 (TDD — write FIRST, ensure they FAIL before implementation)

- [x] T007 [P] [US1] Write unit test for `ReferenceDataCache.__init__` + not-yet-hydrated state in `/home/user/projects/game/babylon/tests/unit/engine/headless_runner/test_reference_data_cache_init.py` — confirms `_hydrated == False`, all counters 0, lookups raise `RuntimeError("not hydrated")` (verified 2026-07-08: tests/unit/engine/headless_runner/test_reference_data_cache_init.py)
- [x] T008 [P] [US1] Write unit test for `ReferenceDataCache.hydrate` happy path against a temp SQLite fixture in `/home/user/projects/game/babylon/tests/unit/engine/headless_runner/test_reference_data_cache_hydrate.py` — populates `_entries` for all `(fips × year)` tuples; counters equal `N × Y` (verified 2026-07-08: tests/unit/engine/headless_runner/test_reference_data_cache_hydrate.py)
- [x] T009 [P] [US1] Write unit test for double-hydrate guard in `/home/user/projects/game/babylon/tests/unit/engine/headless_runner/test_reference_data_cache_double_hydrate.py` — second call raises `RuntimeError` (verified 2026-07-08: tests/unit/engine/headless_runner/test_reference_data_cache_double_hydrate.py)
- [x] T010 [P] [US1] Write unit test for per-field nullability (asymmetric Census/QCEW coverage) in `/home/user/projects/game/babylon/tests/unit/engine/headless_runner/test_reference_data_cache_three_state.py` — Census-missing-but-QCEW-present yields `(population=int_from_fallback, employment_proxy=float)`; QCEW-missing yields `(None, None)` (verified 2026-07-08: tests/unit/engine/headless_runner/test_reference_data_cache_three_state.py)
- [x] T011 [P] [US1] Write unit test for `lookup_population` / `lookup_employment_proxy` semantics in `/home/user/projects/game/babylon/tests/unit/engine/headless_runner/test_reference_data_cache_lookup.py` — returns cached value, returns `None` for missing field, raises `KeyError` for out-of-scope `(fips, year)`, idempotent (verified 2026-07-08: tests/unit/engine/headless_runner/test_reference_data_cache_lookup.py)
- [x] T012 [P] [US1] Write unit test for `mark_population_miss_logged` / `mark_employment_miss_logged` once-per-tuple semantics in `/home/user/projects/game/babylon/tests/unit/engine/headless_runner/test_reference_data_cache_miss_logging.py` — returns `True` exactly once per tuple, `False` thereafter (verified 2026-07-08: tests/unit/engine/headless_runner/test_reference_data_cache_miss_logging.py)
- [x] T013 [US1] Write integration test for the bridge consuming the cache against a real temp SQLite fixture in `/home/user/projects/game/babylon/tests/integration/engine/headless_runner/test_bridge_uses_cache.py` — hydrate + 3 persist_tick calls; assert no new SQLite connections opened post-hydrate (verified 2026-07-08: tests/integration/engine/headless_runner/test_bridge_uses_cache.py)

### Implementation for User Story 1

- [x] T014 [US1] Implement `ReferenceDataCache.__init__(sqlite_path: Path)` in `/home/user/projects/game/babylon/src/babylon/engine/headless_runner/reference_data_cache.py` per contracts/reference_data_cache_contract.md §Construction (verified 2026-07-08: src/babylon/engine/headless_runner/reference_data_cache.py:107)
- [x] T015 [US1] Implement `ReferenceDataCache.hydrate(scope_fips, year_set)` in `/home/user/projects/game/babylon/src/babylon/engine/headless_runner/reference_data_cache.py` — three batched SQL queries (Census primary, QCEW fallback, QCEW employment) under one connection; populate `_entries` per data-model.md §2 algorithm (verified 2026-07-08: src/babylon/engine/headless_runner/reference_data_cache.py:144)
- [x] T016 [US1] Implement `lookup_population(county_fips, year) -> int | None` and `lookup_employment_proxy(county_fips, year) -> float | None` in `/home/user/projects/game/babylon/src/babylon/engine/headless_runner/reference_data_cache.py` — `RuntimeError` if not hydrated; `KeyError` if out of scope (verified 2026-07-08: src/babylon/engine/headless_runner/reference_data_cache.py:264,278)
- [x] T017 [US1] Implement `mark_population_miss_logged(county_fips, year) -> bool` and `mark_employment_miss_logged(county_fips, year) -> bool` in `/home/user/projects/game/babylon/src/babylon/engine/headless_runner/reference_data_cache.py` — first call returns `True` and adds tuple to the per-field set; subsequent calls return `False` (verified 2026-07-08: src/babylon/engine/headless_runner/reference_data_cache.py:291,311)
- [x] T018 [US1] Add `total_ticks: int` keyword-only required parameter to `WorldStateBridge.hydrate_initial` in `/home/user/projects/game/babylon/src/babylon/engine/headless_runner/bridge.py:224` and validate `total_ticks >= 0` (verified 2026-07-08: src/babylon/engine/headless_runner/bridge.py:274 param, :327-328 validation)
- [x] T018b [P] [US1] Update every existing `bridge.hydrate_initial(...)` call site in `/home/user/projects/game/babylon/tests/unit/engine/headless_runner/test_bridge.py` to pass `total_ticks=<test_specific_value>` (≈12 call sites at lines 116, 132, 148, 168, 174, 189, 217, 236, 247, 268, plus the `pytest.raises` blocks); without this update the existing bridge test suite will `TypeError` on the new required parameter. Suggested test value: `total_ticks=1` for hydrate-only tests; larger values where the test exercises multi-tick behavior. Blocked by T018; parallel with T019–T022 (different file). (verified 2026-07-08: tests/unit/engine/headless_runner/test_bridge.py — 10 total_ticks call-site refs)
- [x] T019 [US1] Instantiate `ReferenceDataCache` in `WorldStateBridge.hydrate_initial` after validating inputs but before committing instance state (i.e., before `self._hydrated = True`) in `/home/user/projects/game/babylon/src/babylon/engine/headless_runner/bridge.py` — call `cache.hydrate(scope_fips, derive_year_set(start_year, total_ticks))` and assign to `self._ref_cache` (verified 2026-07-08: src/babylon/engine/headless_runner/bridge.py:372-387 — cache hydrated via derive_year_set, assigned to self._ref_cache)
- [x] T020 [US1] Refactor `WorldStateBridge._derive_subsystem_rows_for_county` in `/home/user/projects/game/babylon/src/babylon/engine/headless_runner/bridge.py:697` to use `self._ref_cache.lookup_*` instead of `fetch_*_at_tick`; route missing-data through `mark_*_miss_logged` to log the warning at most once per tuple per FR-004 / SC-004 (verified 2026-07-08: src/babylon/engine/headless_runner/bridge.py:928 _derive_subsystem_rows_for_county; lookup_* :966-971; mark_*_miss_logged :979,996)
- [x] T021 [US1] Plumb `total_ticks=config.ticks` through the existing `bridge.hydrate_initial(...)` call site at `/home/user/projects/game/babylon/src/babylon/engine/headless_runner/runner.py:603` — single-line additive change in the keyword-argument list (verified 2026-07-08: src/babylon/engine/headless_runner/runner.py:1012 total_ticks=config.ticks)
- [x] T022 [US1] Write slow-gate integration test for SC-002 read-count + FR-003 persist-tick-no-increment in `/home/user/projects/game/babylon/tests/integration/engine/headless_runner/test_cache_canonical_wallclock.py` — fixture-backed at REDUCED SCALE (4 counties × 2 calendar years × 60 ticks; year-rollover crossed at tick 52) to fit within CI's `mise run test:int` time budget; asserts `bridge.total_db_reads == 2 × 4 × 2 == 16` post-hydrate and that the counter does not change across the 60 persist_tick calls. The absolute 60-minute SC-001 wallclock gate is NOT exercised here — it is verified at canonical 83 × 11 × 520 scale by the operator-side procedure in T036 / quickstart.md. Marker `@pytest.mark.slow` so it gates on `mise run test:int` not on `mise run test:unit`. (verified 2026-07-08: tests/integration/engine/headless_runner/test_cache_canonical_wallclock.py)

**Checkpoint**: US1 fully functional. The MVP slice is shippable here: cache works, run is faster, persist_tick is II.6-compliant.

---

## Phase 4: User Story 2 — Operator can verify the cache is doing its job (Priority: P2)

**Goal**: The instrumentation counters from US1 are exposed as read-only properties on the bridge and recorded into the run's `manifest.json` for offline operator inspection. Verification of US1's wallclock claim is now falsifiable: a run that comes in under 60 min for the wrong reason (warm filesystem cache, faster disk) is distinguishable from a run that comes in under 60 min because the cache is doing structural work.

**Independent Test**: Run a short scenario (N counties × Y years known a priori); after run, read `manifest.json.bridge_db_reads.total_db_reads` and confirm it equals `2 × N × Y`.

### Tests for User Story 2

- [x] T023 [P] [US2] Write unit test for cache-level counter properties in `/home/user/projects/game/babylon/tests/unit/engine/headless_runner/test_reference_data_cache_counter.py` — pre-hydrate counters are 0, post-hydrate are `N × Y` each; counters do not increment on `lookup_*` calls (verified 2026-07-08: tests/unit/engine/headless_runner/test_reference_data_cache_counter.py)
- [x] T024 [P] [US2] Write unit test for bridge-level counter properties in `/home/user/projects/game/babylon/tests/unit/engine/headless_runner/test_bridge_db_reads_properties.py` — bridge `population_db_reads` / `employment_db_reads` / `total_db_reads` delegate to cache; return 0 before `hydrate_initial`; FR-008 isolation across two bridge instances in same process (verified 2026-07-08: tests/unit/engine/headless_runner/test_bridge_db_reads_properties.py)
- [x] T025 [P] [US2] Write integration test for persist-tick counter invariance (I3) in `/home/user/projects/game/babylon/tests/integration/engine/headless_runner/test_persist_tick_no_db_increment.py` — call `persist_tick` 52 times across one calendar year; assert no counter delta vs. post-hydrate baseline (verified 2026-07-08: tests/integration/engine/headless_runner/test_persist_tick_no_db_increment.py)

### Implementation for User Story 2

- [x] T026 [US2] Add `@property` read-only accessors `population_db_reads`, `employment_db_reads`, `total_db_reads` to `ReferenceDataCache` in `/home/user/projects/game/babylon/src/babylon/engine/headless_runner/reference_data_cache.py` (verified 2026-07-08: src/babylon/engine/headless_runner/reference_data_cache.py:133,137,141)
- [x] T027 [US2] Add corresponding `@property` read-only accessors on `WorldStateBridge` that delegate to `self._ref_cache` (returning 0 if `self._ref_cache is None`) in `/home/user/projects/game/babylon/src/babylon/engine/headless_runner/bridge.py` (verified 2026-07-08: src/babylon/engine/headless_runner/bridge.py:235-251)
- [x] T028 [US2] Extend the manifest writer in `/home/user/projects/game/babylon/src/babylon/engine/headless_runner/manifest.py` to emit a `bridge_db_reads` block `{population_db_reads, employment_db_reads, total_db_reads}` populated from the bridge's properties at run-end (verified 2026-07-08: src/babylon/engine/headless_runner/manifest.py:230,317-318)

**Checkpoint**: US2 fully functional. Operators can verify SC-002 from `manifest.json` directly without running additional instrumentation.

---

## Phase 5: User Story 3 — Trace output stays byte-identical (Priority: P3)

**Goal**: The cache introduces no numerical drift. The canonical scenario at a fixed seed produces byte-identical `trace.csv` files across pre-cache and post-cache runs, and across two post-cache runs.

**Independent Test**: Run the canonical scenario twice at the same seed; `diff -q` the two `trace.csv` files; expect no output.

### Tests for User Story 3

- [x] T029 [P] [US3] Write slow-gate integration test for byte-identical trace.csv across two post-cache runs at the same seed in `/home/user/projects/game/babylon/tests/integration/engine/headless_runner/test_cache_byte_identical_trace.py` — `@pytest.mark.slow`; runs canonical scenario twice; asserts byte-equality of the two `trace.csv` files (verified 2026-07-08: tests/integration/engine/headless_runner/test_cache_byte_identical_trace.py)
- [x] T030 [P] [US3] Write fast-gate unit test for value-equality with the legacy fetcher path in `/home/user/projects/game/babylon/tests/unit/engine/headless_runner/test_cache_value_equality.py` — for a small fixture-backed SQLite, assert `cache.lookup_population(fips, year) == fetch_population_for_county_at_tick(sqlite_path, fips, tick=year_to_tick(year), start_year=year)` for the year's tick-0 — verifies FR-005 cache/legacy equivalence without a full canonical run (verified 2026-07-08: tests/unit/engine/headless_runner/test_cache_value_equality.py)

### Implementation for User Story 3

> No source changes needed. US3 is a verification-only story whose contract is established by US1's implementation and tested here.

**Checkpoint**: All three user stories independently functional. Spec ready for integration to `dev`.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, observability, and the ADR record for the constitutional trail.

- [x] T031 Run `mise run check` (lint + format + typecheck + test:unit) at the repo root; fix any issues surfaced in spec-069 source or test files; do NOT touch unrelated code (verified 2026-07-08 via record: ai-docs/state.yaml:56 records spec-069 complete, 37/37; code merged through check gate)
- [x] T032 Run `mise run test:int -- tests/integration/engine/headless_runner/test_cache_canonical_wallclock.py tests/integration/engine/headless_runner/test_cache_byte_identical_trace.py` and confirm both pass; capture wall-clock seconds and read-counts into a follow-up commit message (verified 2026-07-08 via record: ai-docs/state.yaml spec_069_summary — SC-002 PASS, SC-004 PASS; both test files exist)
- [x] T033 [P] Create `/home/user/projects/game/babylon/ai-docs/decisions/ADR047_sqlite_per_tick_read_cache.yaml` documenting: context (spec-066 R8 deferred work), decision (the cache and its contract), rationale (~5 "why" sections from research.md), consequences (positive: II.6 compliance, ≥30× fetch-wallclock relief; negative: new `total_ticks` parameter is a forward-incompatible signature change for any external callers), references (spec/plan/research/contracts/quickstart paths) (verified 2026-07-08: ai-docs/decisions/ADR047_sqlite_per_tick_read_cache.yaml)
- [x] T034 [P] Update `/home/user/projects/game/babylon/ai-docs/decisions/index.yaml` to register `ADR047_sqlite_per_tick_read_cache` and bump the index `version` field by one minor unit (verified 2026-07-08: ai-docs/decisions/index.yaml:212-216)
- [x] T035 [P] Update `/home/user/projects/game/babylon/ai-docs/state.yaml` — set `last_sprint` to `069-sqlite-cache-optimization`; add a `spec_069_summary` block recording SC-001/SC-002/SC-003/SC-004 pass/fail (SC-001 from operator-side canonical run per T036; SC-002 + SC-004 from unit/integration tests; SC-003 from byte-identical slow-gate) (verified 2026-07-08: ai-docs/state.yaml:56 previous_sprint_069 + :112 spec_069_summary)
- [~] T036 Validate against `/home/user/projects/game/babylon/specs/069-sqlite-cache-optimization/quickstart.md` step-by-step on a canonical run; confirm SC-001 ≤ 60 min, SC-002 = 1660, SC-003 byte-identical at same seed; if any gate fails, return to the appropriate user-story phase (partial 2026-07-08: SC-002/SC-003/SC-004 recorded in ai-docs/state.yaml spec_069_summary; SC-001 60-min operator-side canonical gate explicitly deferred per state.yaml:56 — no durable record it was ever run)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies. T001 + T002 can run; T002 is parallelizable.
- **Foundational (Phase 2)**: Depends on T002. **BLOCKS all user stories.** T003/T004 must complete before any US1/US2/US3 implementation; T005/T006 are parallel with T003/T004 except that they reference the just-created functions/models.
- **User Stories (Phases 3-5)**: All three depend on Phase 2. May proceed sequentially in priority order OR in parallel (different developers, different files), with the caveat that US2 (T026-T028) needs US1's cache class (T014-T017) in place to delegate to.
- **Polish (Phase 6)**: Depends on US1, US2, and US3 all being complete.

### User Story Dependencies

- **US1 (P1, MVP)**: Independent of US2 and US3 at the implementation level. Once US1 is done, the canonical run is faster regardless of whether US2 instrumentation or US3 byte-equality tests are landed.
- **US2 (P2)**: At the implementation level, T026 (cache properties) needs T014-T015 (cache constructor + hydrate). T027 (bridge properties) needs T019 (bridge instantiates cache). T028 (manifest writer) is parallel with T026/T027.
- **US3 (P3)**: At the implementation level, US3 has NO new source-code tasks — the slow-gate integration test and the value-equality test exercise behavior already established by US1.

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD policy). Within US1 the test cluster is T007-T013; the impl cluster is T014-T022 (plus T018b for the existing-call-site update).
- Models before services. `ReferenceCacheEntry` (T004) before `ReferenceDataCache` methods (T014-T017).
- Cache class before bridge integration. T014-T017 before T018-T021.
- Bridge integration before runner plumbing. T018-T020 before T021.
- Slow-gate verification (T022, T029) last within each story.

### Parallel Opportunities

- Setup: T002 [P] runs in parallel with anything that doesn't need the new module yet.
- Foundational tests: T005 [P] and T006 [P] are both parallel — different test files, independent of each other.
- US1 tests: T007–T012 [P] are all parallel — six independent unit-test files. T013 is sequential (single integration file).
- US1 impl: T014–T017 all edit `reference_data_cache.py` and are sequential within that file; T018–T021 edit `bridge.py` and `runner.py` and are sequential. T018b [P] edits `tests/unit/engine/headless_runner/test_bridge.py` — different file, parallel with T019–T022 once T018 is complete.
- US2 tests: T023, T024, T025 all [P] — three independent test files.
- US3 tests: T029 [P] and T030 [P] — two independent test files.
- Polish: T033, T034, T035 are [P] — three independent YAML/file targets.

---

## Parallel Example: User Story 1 test cluster

```bash
# Write all US1 tests in parallel before any US1 impl. All FAIL initially.
Task: "Write unit test for ReferenceDataCache.__init__ in test_reference_data_cache_init.py"
Task: "Write unit test for ReferenceDataCache.hydrate happy path in test_reference_data_cache_hydrate.py"
Task: "Write unit test for double-hydrate guard in test_reference_data_cache_double_hydrate.py"
Task: "Write unit test for per-field nullability in test_reference_data_cache_three_state.py"
Task: "Write unit test for lookup_* semantics in test_reference_data_cache_lookup.py"
Task: "Write unit test for mark_*_miss_logged once-per-tuple in test_reference_data_cache_miss_logging.py"
```

Then T013 sequentially (integration test for the bridge), then T014-T022 sequentially.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001, T002).
2. Complete Phase 2: Foundational (T003, T004, T005, T006). CRITICAL — blocks all stories.
3. Complete Phase 3: User Story 1 (T007–T022, plus T018b).
4. **STOP and VALIDATE**: run T022's slow-gate test (reduced-scale structural gate: SC-002 read-count + FR-003 persist-tick invariance). For SC-001 absolute-wallclock verification, run the canonical scenario per T036 / quickstart.md on an operator workstation.
5. Optionally demo at this point. The cache is operationally green.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. US1 → cache works end-to-end; run is faster (MVP).
3. US2 → operator instrumentation; SC-001 is falsifiable from `manifest.json`.
4. US3 → byte-identical determinism gate; SC-003 verified empirically.
5. Polish → ADR047, ai-docs state.yaml, end-to-end validation.

### Parallel Team Strategy

With multiple developers:

- Dev A takes US1 (the heavy lift; ~16 tasks).
- Dev B takes US2 (~6 tasks) after US1's T015-T017 land.
- Dev C takes US3 (~2 tasks) after US1's T022 lands.
- Polish tasks T033-T035 can be claimed by anyone after US3 closes.

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks. Re-verify before launching parallelism — a [P] marker is invalidated if an upstream sequential task is still in flight.
- [Story] label maps the task to its user story for traceability.
- Each user story is independently completable AND independently testable.
- Verify TDD tests fail before implementing (red phase).
- Commit after each task or logical group per CLAUDE.md "Commit Early, Commit Often."
- Stop at any checkpoint (after Phase 3, after Phase 4, after Phase 5) to validate independently.
- Avoid: vague tasks, same-file conflicts that defeat [P], cross-story implementation dependencies that break US-independence.
