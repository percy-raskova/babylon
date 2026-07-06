# Tasks: Observatory Foundation

**Input**: `/specs/096-observatory-foundation/` (spec.md, plan.md, research.md,
data-model.md, contracts/observatory-api.md)
**TDD**: mandatory (Red → Green). Each test task is written and observed RED
before its implementation task. Commit after each unit (conventional commits).

## Format: `[ID] [P?] [Story] Description`

- **[P]** = parallelizable (different files, no ordering dependency)
- Stories: US1 (series), US2 (commit chain + hex), US3 (read-only), US4 (gating)

---

## Phase 1: Foundational (blocking) — the read-only bridge

**Commit unit A: `feat(observatory): read-only sim DB alias + router`**

- [ ] T001 [US3] `web/observatory/__init__.py`, `apps.py` (ObservatoryConfig),
  `migrations/__init__.py` (empty — no models).
- [ ] T002 [US3] RED `tests/unit/observatory/test_db_alias.py`:
  `build_sim_database_alias(dsn)` parses the tick_probe DSN → ENGINE
  `postgresql`, HOST/PORT/NAME/USER/PASSWORD, and
  `OPTIONS.options == "-c default_transaction_read_only=on"`.
- [ ] T003 [US3] GREEN `web/observatory/db.py`: `build_sim_database_alias`.
- [ ] T004 [US3] RED `tests/unit/observatory/test_router.py`:
  `SimDatabaseRouter.allow_migrate("sim", …) is False`; `allow_migrate("default",
  …) is None`; `db_for_read/db_for_write` return `None`.
- [ ] T005 [US3] GREEN `web/observatory/router.py`: `SimDatabaseRouter`.
- [ ] T006 [US3][US4] Settings wiring: `base.py` adds `observatory` to
  INSTALLED_APPS, `DATABASES["sim"] = build_sim_database_alias(env)`,
  `DATABASE_ROUTERS = ["observatory.router.SimDatabaseRouter"]`,
  `OBSERVATORY_ENABLED` default; `development.py` True, `production.py` False.
- [ ] T007 [US4] RED+GREEN `tests/unit/observatory/test_settings.py`: app
  installed, router registered, flag True in development / False in production,
  `build_sim_database_alias` present.

---

## Phase 2: US3 read-only proof + US4 gating (no data yet)

**Commit unit B: `feat(observatory): flag-gated endpoints skeleton + query layer`**

- [ ] T008 [US1][US2] RED `tests/unit/observatory/test_queries_sql.py`: query
  builders reference only `v_national/state/county_value_aggregate`,
  `v_hex_state_asof`, `tick_commit`, `game_session` — and NEVER
  `dynamic_hex_state`; SQL is parameterized (no f-string values).
- [ ] T009 [US1][US2] GREEN `web/observatory/queries.py`: `list_sessions`,
  `tick_range`, `value_series(scope,…)`, `commit_chain`, `hex_frame` — pure
  functions returning `(sql, params)` or executing against a passed cursor.
- [ ] T010 [US1][US2] `web/observatory/serializers.py`: typed payload shapes
  (SessionSummary, TickRange, ValueAggregatePoint, CommitRecord, HexStatePoint).
- [ ] T011 [US4] RED `tests/unit/observatory/test_endpoints_gating.py`:
  every endpoint 404 when `OBSERVATORY_ENABLED=False`; 403/401 unauthenticated;
  `status/` 200/404 by flag — all without touching the sim DB.
- [ ] T012 [US1][US2][US4] GREEN `web/observatory/views.py` + `urls.py` +
  `web/babylon_web/urls.py` route include: `status`, `sessions`, `ticks`,
  `series`, `series.csv`, `commits`, `hex` — each flag-gated + auth-gated,
  reading via `connections["sim"]`.

---

## Phase 3: US1 + US2 data integration (Postgres-gated)

**Commit unit C: `test(observatory): integration read-only + endpoint data`**

- [ ] T013 [US3] `tests/integration/observatory/conftest.py`: seed a unique
  session (apply `migrations/00*.sql` + `PerTickTransactionEnvelope` via
  `pg_pool`), register the Django `sim` alias at the same DSN.
- [ ] T014 [US3] RED→GREEN `tests/integration/observatory/test_read_only.py`:
  a write via `connections["sim"]` raises `ReadOnlySqlTransaction`;
  `SimDatabaseRouter.allow_migrate` False against the live alias.
- [ ] T015 [US1][US2] `tests/integration/observatory/test_endpoints_data.py`:
  seeded session appears in `sessions/`; `ticks/` returns the range;
  national/state/county `series/` return one point per committed tick;
  `series.csv/` has header + one row per tick; `commits/` returns the chain;
  `hex/` returns the frame at a tick.

---

## Phase 4: US1 + US2 frontend (Vitest + MSW)

**Commit unit D: `feat(observatory): React /observatory route group + contracts`**

- [ ] T016 [P] `web/frontend/src/observatory/types.ts`, `api.ts`, `csv.ts`.
- [ ] T017 [US1] RED MSW contract tests
  `web/frontend/src/observatory/__tests__/api.contract.test.tsx`: each endpoint
  parsed from the standard envelope; disabled-state (status 404) handled.
- [ ] T018 [US1] GREEN `ObservatoryChart.tsx` (Recharts, Tufte-minimal, tokens),
  `SessionPicker.tsx`, `SeriesBrowser.tsx`, `ObservatoryPage.tsx` (shell +
  status gating).
- [ ] T019 [US1] RED→GREEN component tests: picker renders a session list;
  browser renders a chart from a mocked series; CSV builder output; disabled
  banner when `status/` 404.
- [ ] T020 [US1] `App.tsx`: ONE lazy route line
  `<Route path="/observatory/*" element={<Suspense…><ObservatoryPage/></…>} />`.

---

## Phase 5: Docs + close-out

**Commit unit E: `docs(observatory): two-DB alias map + close-out`**

- [ ] T021 `web/HOW-TO-LOCAL-DEV.md`: two-DB alias map section (default vs sim).
- [ ] T022 Close-out: `project/01-state-of-the-world.md`, `09` §2 spec-096
  status, `ai-docs/state.yaml`; report at `.superpowers/sdd/reports/096.md`.

---

## Dependencies

- Phase 1 blocks all others (alias + router + settings).
- Phase 2 depends on Phase 1 (endpoints need queries + gating).
- Phase 3 (integration) depends on Phase 2 (endpoints exist).
- Phase 4 (frontend) depends on the contract in `contracts/observatory-api.md`
  (can proceed in parallel with Phase 3 since it mocks the API via MSW).
- Phase 5 last.

## Parallelizable

- T016 (frontend types/api/csv) [P] with backend Phase 3.
- Within Phase 1, T002/T004 (unit tests) are independent files.

## Independent test criteria (per story)

- **US1**: seed a session → `series/` returns one point per committed tick +
  CSV row per tick (SC-002, SC-003).
- **US2**: `commits/` returns hash+rows+checkpoint per tick (SC-007); `hex/`
  returns a reconstructed frame.
- **US3**: write via `sim` alias rejected (SC-004); migrate makes no sim schema
  change (SC-005).
- **US4**: flag off → all endpoints 404, no data leaked (SC-006).
