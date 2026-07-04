# Tasks: Observatory Deep Panes

**Input**: `/specs/099-observatory-deep-panes/` (spec, plan). TDD mandatory
(red → green). Commit per unit via `mise run commit`; verify HEAD moves.
Stories: US1 archive, US2 verify, US3 boundary, US4 conservation, US5 diff.

## Format: `[ID] [Story] Description`

## Phase 0: 096 re-review nits — DONE (commit `66abe9bd`)

- [x] `__all__` hex-limit exports; `logger.exception` in the 503 handlers.

## Phase 1: Source abstraction (foundational, blocks all)

**Commit A: `feat(observatory): live|archive source abstraction + DuckDB reader`**

- [ ] T001 [US1] RED `tests/unit/observatory/test_sources.py`: `parse_source`
  (default live; archive; invalid → error); `archive_dir(session_id)` resolves
  `<root>/<sid>/` and honours `BABYLON_ARCHIVE_ROOT`.
- [ ] T002 [US1] GREEN `web/observatory/sources.py`: `Source` enum/parse,
  `archive_dir`, `archive_query(session_id, sql, params)` (wraps
  `babylon.persistence.archival.query_archived_session`; empty result when a
  referenced table's Parquet is absent), `live_cursor()` (096's `_sim_cursor`).

## Phase 2: US2 verification + source= on commits (gate-critical)

**Commit B: `feat(observatory): hash-chain verification pane + source param`**

- [ ] T003 [US2] RED `tests/unit/observatory/test_verify.py`: `verify_chain`
  pure logic over commit rows — valid session (contiguous, cadence, 64-char),
  gap flagged, duplicate flagged, bad-cadence checkpoint flagged.
- [ ] T004 [US2] GREEN `web/observatory/deep_queries.py::verify_chain` +
  `web/observatory/deep_views.py::observatory_verify` (source-aware).
- [ ] T005 [US2] Wire `source=` into 096's `sessions/ticks/series/commits/hex`
  via `sources.py` (archive commit chain reads `tick_commit` Parquet directly).

## Phase 3: US3 boundary + US4 conservation (empty-state-first)

**Commit C: `feat(observatory): boundary-flow explorer + conservation browser`**

- [ ] T006 [US3][US4] RED unit SQL sweeps in `test_deep_queries_sql.py`
  (boundary reads `boundary_flow_register`, audit reads `conservation_audit_log`;
  parameterized; grouped by flow_type / filterable by severity).
- [ ] T007 [US3] GREEN `observatory_boundary` endpoint (grouped by flow type,
  empty-state).
- [ ] T008 [US4] GREEN `observatory_conservation` endpoint (severity filter,
  empty-state).

## Phase 4: US5 diff

**Commit D: `feat(observatory): two-session diff endpoint`**

- [ ] T009 [US5] `observatory_diff`: two national series aligned by tick + delta,
  commit-chain range/count comparison; self-diff = zero deltas.

## Phase 5: Integration (Postgres + real archive)

**Commit E: `test(observatory): deep-pane integration incl. archived session`**

- [ ] T010 [US1][US2] `tests/integration/observatory/test_archive.py`: read the
  real `edf07b2e-…` archived session via `source=archive` — sessions list,
  commit chain (520 ticks, checkpoints), verify valid, national series; assert
  read-only (no file mtime change).
- [ ] T011 [US3][US4][US5] live-source deep integration over a seeded session
  (boundary empty, audit rows via a seeded audit envelope, verify ok, diff).

## Phase 6: Frontend panes

**Commit F: `feat(observatory): deep-pane UI + source selector + MSW contracts`**

- [ ] T012 `deepApi.ts` + `types` + MSW contracts (RED) for the 4 endpoints.
- [ ] T013 `SourceSelector.tsx`, `panes/VerificationPane`, `BoundaryPane`,
  `ConservationPane`, `DiffPane`; tab them into `ObservatoryPage`.

## Phase 7: Docs + close-out

**Commit G: `docs(observatory): source map + spec-099 close-out`**

- [ ] T014 `web/HOW-TO-LOCAL-DEV.md` source=live|archive; `project/01`, `09` §2,
  `ai-docs/state.yaml`; report `.superpowers/sdd/reports/099.md`.

## Dependencies

Phase 1 blocks all. Phase 2 (verify + source wiring) is the gate path. Phases
3/4/5 depend on 1–2. Frontend (6) depends on the contracts. Docs (7) last.
