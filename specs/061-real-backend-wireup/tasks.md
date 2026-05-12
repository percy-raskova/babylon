# Tasks: Real Backend Wire-Up

**Input**: Design documents from `/home/user/projects/game/babylon/specs/061-real-backend-wireup/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests ARE included per the project's TDD philosophy (CLAUDE.md: "We use Test Driven Development. That means: 1. Red Phase — write tests that fail; 2. Green phase — Adjust code to pass tests; 3. Refactor Phase"). Each user story has its own test set written first.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- All paths are absolute under `/home/user/projects/game/babylon/`

## Path Conventions

- **Engine**: `src/babylon/`
- **Web backend**: `web/babylon_web/` + `web/game/`
- **Frontend**: `web/frontend/src/`
- **Tests**: `tests/unit/`, `tests/integration/`, `tests/property/`
- **Migrations**: `web/game/migrations/`
- **Deploy**: `deploy/ansible/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the new dependency and the embedding-model pinning constants. No code that depends on Phase 2 work yet.

- [X] T001 Add `sentence-transformers ^3.x` dependency to `pyproject.toml` `[tool.poetry.dependencies]` and run `poetry lock --no-update` then `poetry install` to materialize. Verify import works: `poetry run python -c "from sentence_transformers import SentenceTransformer; print(SentenceTransformer.__module__)"`
- [X] T002 [P] Add embedding model pinning constants to `src/babylon/config/llm_config.py`: `CANONICAL_EMBEDDING_MODEL_ID = "sentence-transformers/all-mpnet-base-v2"`, `CANONICAL_EMBEDDING_DIM = 768`, `CANONICAL_EMBEDDING_REVISION = "<sha-from-deploy>"` (placeholder; the actual SHA is captured and pinned by T120 in the Polish phase)
- [X] T003 [P] Define exception class `EmbeddingDimensionError(ValueError)` in `src/babylon/persistence/pgvector_store.py` (used by FR-002)
- [X] T004 [P] Confirm Postgres extensions are installed in dev DB: `psql babylon -c "SELECT extname FROM pg_extension WHERE extname IN ('postgis', 'vector', 'uuid-ossp');"` — should list all three. If missing, install via `CREATE EXTENSION IF NOT EXISTS ...` and document in `deploy/ansible/roles/dbservers/`
- [X] T005 [P] Verify systemd version is 254+ on target deploy hosts: `systemctl --version | head -1` — required for `RestartSteps`/`RestartMaxDelaySec`. If older, document Debian 13 / Ubuntu 24.04 upgrade path in `deploy/HOW-TO-DEPLOY-HETZNER.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema migrations, transactional wrap, boot retry, immutability guard. These BLOCK all user-story work because every story depends on the engine being correctly initialized and the snapshot writes being atomic.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Schema migrations (run in order)

- [X] T006 Create migration `web/game/migrations/0006_drop_sim_hex_states.py`: `RunSQL(["DROP TABLE IF EXISTS sim.hex_states CASCADE;", "DROP SCHEMA IF EXISTS sim CASCADE;"], reverse_sql=migrations.RunSQL.noop)`. Cleanup of orphan from migration 0002 (FR-030)
- [X] T007 Create migration `web/game/migrations/0007_purge_fixture_sessions.py`: `RunSQL("DELETE FROM game_session;", reverse_sql=migrations.RunSQL.noop)`. Cascades to game_turn, action_result, simulation_event, node_state, edge_state, etc. (FR-033)
- [X] T008 Create migration `web/game/migrations/0008_drop_snapshot_json.py`: `RunSQL("ALTER TABLE game_session DROP COLUMN IF EXISTS snapshot_json;", reverse_sql="ALTER TABLE game_session ADD COLUMN snapshot_json JSONB NOT NULL DEFAULT '{}'::jsonb;")`. Removes the mock-bridge-only column added by 0005
- [X] T009 Create migration `web/game/migrations/0009_action_result_unique.py`: `RunSQL` adding `UNIQUE (session_id, tick, action_id)` constraint to `action_result` and `UNIQUE (session_id, tick, event_type, entity_id)` constraint to `simulation_event`. Required for `ON CONFLICT DO NOTHING` idempotency (FR-004)
- [X] T010 Create migration `web/game/migrations/0010_document_chunk_reconciliation.py`: drop the broken `document_chunk` table and recreate per `data-model.md` §1 with corrected DDL — columns `(chunk_id PK, collection, content, embedding vector(768), metadata jsonb, source, chunk_index, created_at)`, plus indexes `idx_document_chunk_collection (B-tree)` and `idx_document_chunk_embedding (HNSW vector_cosine_ops)`. Use `migrations.RunSQL` with `reverse_sql=migrations.RunSQL.noop` (FR-001)
- [X] T011 Update `src/babylon/persistence/postgres_schema.py` `DOCUMENT_CHUNK_DDL` constant to match the corrected DDL in T010 (single source of truth — both the constant and the migration must agree)
- [X] T012 Run all five migrations against a clean dev DB: `mise run web:migrate` — verify with `psql babylon -c "\dt sim.*"` (none), `psql babylon -c "SELECT count(*) FROM game_session;"` (0), `psql babylon -c "\d document_chunk"` (new shape)

### Atomic snapshot transactional wrap (FR-003, R2 decision)

- [X] T013 Refactor `src/babylon/persistence/postgres_runtime/_legacy.py:persist_full_tick()` to acquire one connection from `self._pool.connection()`, wrap all 7 per-table writes in a single `with conn.transaction():` block, and pass the cursor down to per-table helpers instead of having each helper acquire its own connection
- [X] T014 Update `_persist_territory_snapshots`, `_persist_org_snapshots`, `_persist_edge_snapshots`, `_persist_community_snapshots`, `_persist_hex_activity`, `_persist_economic_summary`, `_persist_tick_events` (all in `src/babylon/persistence/postgres_runtime/_legacy.py`) to accept `cursor` parameter and use it instead of acquiring their own
- [X] T015 Add `ON CONFLICT DO NOTHING` clauses to all INSERT statements in the seven helpers from T014, split by table category for clarity:
  - **(a)** For the five snapshot tables `territory_snapshot`, `org_snapshot`, `edge_snapshot`, `community_snapshot`, `economic_summary`, and the supporting `hex_activity` / `tick_event` tables — use their **existing composite primary keys** as the ON CONFLICT target (e.g., `ON CONFLICT (game_id, tick, county_fips) DO NOTHING` for territory_snapshot). No new constraints needed; the PKs already enforce uniqueness.
  - **(b)** For `action_result` and `simulation_event` — use the **new unique constraints added by T009** as the ON CONFLICT target (`(session_id, tick, action_id)` and `(session_id, tick, event_type, entity_id)` respectively). Append-only retry safety per FR-004.
- [X] T016 Refactor `src/babylon/persistence/postgres_runtime/_legacy.py:_resolve_tick_atomic()` (or create if absent) to use the `INSERT ... ON CONFLICT (session_id, tick) DO NOTHING RETURNING id` pattern against `tick_log`. If `RETURNING id` yields nothing, raise `TickAlreadyResolved` exception (FR-005, race-safe per R2)
- [X] T017 Define `TickAlreadyResolved(Exception)` in `src/babylon/persistence/protocols.py`. Importable from `babylon.persistence`

### Engine bridge boot retry + hard-exit (FR-006, FR-007, R4 decision)

- [X] T018 Refactor `web/game/apps.py:GameConfig.ready()` to add class-level `_initialized` flag and the 3-attempt retry loop calling `sys.exit(1)` on exhaustion. Use the exact pattern from `research.md` R4. Replace the silent `except Exception: logger.exception(...)` with the retry loop. Preserve `RUN_MAIN` and engine-check guards
- [X] T019 Extract the retry loop body into a `_initialize_engine_with_retry(self, max_attempts: int = 3) -> None` method on `GameConfig` for testability
- [X] T020 Audit and fix `--preload-app` usage in Gunicorn template:
  - **(a)** Inspect `deploy/ansible/roles/web/templates/gunicorn_start.j2` for any occurrence of `--preload-app` or `preload_app = True`. Report findings.
  - **(b)** If the flag is present in (a), remove it and add a comment citing research R4 rationale ("fork-safety with psycopg connection pools — preload causes file-descriptor sharing across workers"). If the flag is absent in (a), no further action; document the verification in the task PR. **Verified absent — no action needed.**
- [X] T021 [P] Configure systemd unit per R3 decision in `deploy/ansible/roles/web/templates/babylon-web.service.j2` (create new file): `Type=notify`, `Restart=on-failure`, `RestartSec=5s`, `RestartSteps=4`, `RestartMaxDelaySec=60s` in `[Service]`; `StartLimitIntervalSec=300`, `StartLimitBurst=5` in `[Unit]`. Reference the gunicorn ExecStart from existing template
- [X] T022 [P] Update Ansible play `deploy/ansible/roles/web/tasks/main.yml` to install the new systemd unit file from T021 and run `systemctl daemon-reload` + `systemctl enable babylon-web.service`

### Foundational tests

- [X] T023 [P] Write integration test `tests/integration/test_persist_tick_atomic.py` asserting that when one of the seven snapshot helpers raises mid-call, NO rows are committed to ANY of the seven tables for that tick (rollback verification, SC-011)
- [X] T024 [P] Write integration test `tests/integration/test_tick_immutability.py` asserting that calling `persist_full_tick()` twice for the same `(session_id, tick)` returns rows from the first call only and raises `TickAlreadyResolved` on the second call. Race condition test using two threads invoking the same tick simultaneously (FR-005)
- [X] T025 [P] Write integration test `tests/integration/test_engine_bridge_boot.py` with three scenarios: (a) reachable DB → succeeds on attempt 1; (b) DB unreachable for entire window → 3 retries logged then `sys.exit(1)`; (c) DB unreachable on attempts 1-2, reachable on attempt 3 → succeeds on attempt 3 and worker continues. Use a mock `init_persistence` that raises N times then succeeds

**Checkpoint**: Foundation ready — schema clean, transactions atomic, boot retries hard-fail loudly, immutability enforced. User story implementation can now begin.

---

## Phase 3: User Story 1 — Semantic Search Functions At All (Priority: P1)

**Goal**: Reconcile the `document_chunk` schema/code mismatch and the dimension default. Every RAG/semantic-search call returns results instead of raising `UndefinedColumn`.

**Independent Test**: Add 5 embeddings under collection `rag_documents`, query with `k=3`, get 3 results sorted by ascending cosine distance. Wrong-dimension write raises at the application layer before reaching the database.

### Tests for User Story 1 (TDD — write FIRST)

- [X] T026 [P] [US1] Write unit test `tests/unit/persistence/test_pgvector_store.py::test_add_chunks_succeeds_with_canonical_dim` — uses real psycopg connection (or transaction-rollback fixture against test DB) instead of mocked cursor. Adds 5 entries, asserts no exception
- [X] T027 [P] [US1] Write unit test `tests/unit/persistence/test_pgvector_store.py::test_query_similar_returns_k_results` — adds 5 embeddings, queries with k=3, asserts len(results) == 3 and distances are monotonically increasing
- [X] T028 [P] [US1] Write unit test `tests/unit/persistence/test_pgvector_store.py::test_add_chunks_rejects_wrong_dimension` — calls `add_chunks` with 384-dim vectors, asserts `EmbeddingDimensionError` raised before any DB call (mock the cursor and assert it was never called)

### Implementation for User Story 1

- [X] T029 [US1] Update `src/babylon/persistence/pgvector_store.py:PgVectorStore.__init__()` signature to default `dimension` to `CANONICAL_EMBEDDING_DIM` (imported from `babylon.config.llm_config`). Remove the `dimension: int = 1536` literal default
- [X] T030 [US1] Add a dimension preflight check in `PgVectorStore.add_chunks()` that iterates `embeddings` and raises `EmbeddingDimensionError` with a clear message if any element's length != `self._dimension`. This is BEFORE the SQL INSERT (FR-002)
- [X] T031 [US1] Verify the SQL in `PgVectorStore.add_chunks()` and `PgVectorStore.query_similar()` matches the corrected `document_chunk` columns from T010/T011 — no `id`/`session_id`/`source_file` references; uses `chunk_id`/`collection`/`source`. Should already match the existing code (the bug was DDL/code mismatch); confirm by running T026
- [X] T032 [US1] Update `src/babylon/rag/__init__.py:25-28` instantiation `PgVectorStore(pool=pool, collection="rag_documents")` — verify it does not pass an explicit `dimension=` arg (so it picks up the canonical default from T029)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Run `mise run test:unit -- tests/unit/persistence/test_pgvector_store.py` and `mise run test:int -- tests/integration/test_engine_bridge_boot.py`.

---

## Phase 4: User Story 2 — Engine Failures Are Visible, Not Silent (Priority: P1)

**Goal**: Public `/health/` is up/down only. Auth-gated `/health/detail/` reveals bridge identity, retry count, version. Unauthenticated callers to `/health/detail/` get standard 404. Boot retry hard-fails the worker on persistent DB unreachability.

**Independent Test**: Boot with reachable DB → `/health/detail/` reports `EngineBridge`. Boot with unreachable DB → 3 retries logged, worker exits non-zero, systemd restarts. Unauthenticated GET on `/health/detail/` → 404 (not 401).

### Tests for User Story 2 (TDD)

- [X] T033 [P] [US2] Write integration test `tests/integration/test_health_public.py` asserting `GET /health/` returns 200 with `{"status": "ok"}` regardless of auth state
- [X] T034 [P] [US2] Write integration test `tests/integration/test_health_detail.py::test_unauthenticated_returns_404` asserting unauthenticated GET on `/health/detail/` returns 404 with body `{"detail": "Not found."}` (NOT 401, NOT 403, NOT empty body)
- [X] T035 [P] [US2] Write integration test `tests/integration/test_health_detail.py::test_non_staff_returns_404` asserting authenticated non-staff GET returns same 404 shape
- [X] T036 [P] [US2] Write integration test `tests/integration/test_health_detail.py::test_staff_returns_diagnostic` asserting staff GET returns 200 with payload matching `contracts/health.yaml#/components/schemas/HealthDetailResponse`
- [X] T037 [P] [US2] Write integration test `tests/integration/test_health_detail.py::test_implementation_field_is_real_bridge` asserting `data.engine.implementation == "EngineBridge"` after a clean boot (NOT `"StubEngineBridge"`)

### Implementation for User Story 2

- [X] T038 [US2] Create `web/babylon_web/health/__init__.py` (new package) and `web/babylon_web/health/views.py` containing `class HealthDetailView(APIView)` with `permission_classes = [IsAuthenticated, IsStaff]`. Implement GET handler returning the diagnostic payload from `contracts/health.yaml`
- [X] T039 [US2] Create `web/babylon_web/health/permissions.py` containing `class IsStaff(BasePermission)` with `has_permission()` returning `bool(request.user and request.user.is_staff)`
- [X] T040 [US2] Create `web/babylon_web/health/exceptions.py` containing `health_obscuring_exception_handler(exc, context)` per `research.md` R5: intercepts `NotAuthenticated`/`PermissionDenied` raised by `HealthDetailView` and returns `Response({"detail": "Not found."}, status=404)`. Delegates to DRF default handler otherwise
- [X] T041 [US2] Register the custom exception handler in `web/babylon_web/settings/base.py` under `REST_FRAMEWORK['EXCEPTION_HANDLER'] = "babylon_web.health.exceptions.health_obscuring_exception_handler"`
- [X] T042 [US2] Add `path("health/detail/", HealthDetailView.as_view(), name="health-detail")` to `web/babylon_web/urls.py` (alongside the existing `path("health/", health_check, name="health")`)
- [X] T043 [US2] Implement the diagnostic payload assembly in `HealthDetailView.get()`:
  - `engine.implementation`: `type(game_api._bridge_instance).__name__`
  - `engine.boot_attempts`: track via a class-level counter on `GameConfig`, exposed as `GameConfig.last_boot_attempts`
  - `engine.boot_succeeded_at`: set in `GameConfig._initialize_engine_with_retry` on success
  - `engine.last_tick_resolved_at`: query `MAX(resolved_at) FROM tick_log` (cached for 30s)
  - `database.reachable`: `try: bridge._persistence._pool.connection() ... except: False`
  - `database.pool_size`: read from `bridge._persistence._pool.get_stats()` (psycopg_pool method)
  - `embedding_model.model_id`: `babylon.config.llm_config.CANONICAL_EMBEDDING_MODEL_ID`
  - `embedding_model.dimension`: `babylon.config.llm_config.CANONICAL_EMBEDDING_DIM`
  - `version`: read from `pyproject.toml` `[tool.poetry] version`
  - `git_sha`: read from `.git/HEAD` resolved (helper in `babylon_web/health/version.py`)

### Mid-session DB loss handling (FR-010, added per /speckit.analyze remediation)

- [X] T126 [P] [US2] Write integration test `tests/integration/test_mid_session_503.py::test_db_lost_after_boot_returns_503` — boot the app with reachable DB, confirm `/api/games/<id>/state/` returns 200, then close the connection pool (simulate DB outage via `pool.close()` or by stopping a sidecar Postgres test container), assert subsequent calls to engine-dependent endpoints (`/state/`, `/resolve/`, `/timeseries/`, `/communities/`) return HTTP 503 with body `{"detail": "Service temporarily unavailable. The simulation engine cannot reach its data layer."}`. Health-detail endpoint MUST still return 200 with `database.reachable: false` (already covered by T036's contract)
- [X] T127 [US2] Implement mid-session DB-loss handling per FR-010. Add a DRF middleware (or a base view mixin used by all engine-dependent views) that catches `psycopg.OperationalError`/`psycopg_pool.PoolTimeout` raised during request handling and returns 503 with the standard error body. Wire it as middleware `web/babylon_web/middleware/engine_availability.py:EngineAvailabilityMiddleware` and add to `MIDDLEWARE` in `web/babylon_web/settings/base.py`. Health endpoints (`/health/`, `/health/detail/`) MUST NOT be 503'd by this middleware (they have their own degraded-state reporting)

**Checkpoint**: User Story 2 functional. Run `mise run test:int -- tests/integration/test_health*.py tests/integration/test_engine_bridge_boot.py tests/integration/test_mid_session_503.py` (the boot tests from T025 are also part of US2 verification).

---

## Phase 5: User Story 3 — Briefing Page Shows Real Session State (Priority: P2)

**Goal**: Briefing page displays current tick, real priority events from latest tick, sparklines from session's tick history. Different sessions show different data.

**Independent Test**: Create session, advance 3 ticks, load Briefing page → tick badge matches; sparklines show ≥3 distinct values per metric; Priority Dispatch sorts critical before informational.

### Tests for User Story 3 (TDD)

- [X] T044 [P] [US3] Write integration test `tests/integration/test_timeseries_endpoint.py::test_returns_six_metric_arrays` — POST to `/resolve/` 3 times, GET `/timeseries/`, assert response has `imperial_rent`, `consciousness`, `solidarity`, `heat`, `wealth`, `biocapacity` arrays each of length 4 (ticks 0..3)
- [X] T045 [P] [US3] Write integration test `tests/integration/test_event_serialization.py::test_event_includes_severity_title_body_id` — resolve a tick that produces events, GET `/state/`, assert each event has stable `id`, `severity ∈ {critical,warning,informational}`, non-empty `title`, present `body`
- [X] T046 [P] [US3] Write Playwright e2e test `web/frontend/e2e/briefing-live-data.spec.ts` — navigate to `/games/<session>`, assert tick badge matches session's tick from API, assert sparklines have multiple distinct points after 3 resolves

### Engine-side data model additions

- [X] T047 [P] [US3] Add `event_id: str` (UUID4 generated at construction), `severity: Literal["critical","warning","informational"] = "informational"`, `title: str = ""`, `body: str = ""` fields to the `WorldEvent` Pydantic model in `src/babylon/models/event.py` (or wherever the model lives — verify location) — **derived at bridge serialization boundary instead of on the model itself; spec deviation documented in commit 71f34694**
- [X] T048 [US3] Update all `WorldEvent` constructors throughout the engine systems (`engine/systems/*.py`) to populate `severity` and `title` where the event type implies a clear classification. Default mapping: state-violation events → critical; threshold-cross events → warning; informational → informational — **no-op given T047 derivation choice**

### Bridge-side serializer expansion

- [X] T049 [P] [US3] Extend `web/game/serializers.py:EventSerializer` with `id`, `severity`, `title`, `body` fields (preserve existing `type`, `tick`, `data`). Match `contracts/snapshot.yaml#/components/schemas/Event`
- [X] T050 [US3] Implement `web/game/engine_bridge.py:EngineBridge.get_game_timeseries()` (currently returns `{}`). Query `tick_summary` table via the persistence layer for the session, ORDER BY tick. Return `{"ticks": [...], "imperial_rent": [...], "consciousness": [...], ...}` matching `contracts/timeseries.yaml`. Use `RuntimePersistence.query_tick_summary_series()` (add the method to the protocol if absent)
- [X] T051 [US3] Add `query_tick_summary_series(session_id) -> list[TickSummaryRow]` to `src/babylon/persistence/protocols.py:RuntimePersistence` and implement in both `RuntimeDatabase` (SQLite — read from existing tick_summary table or return empty) and `PostgresRuntime._legacy.py` (read all rows ORDER BY tick) — implemented on PostgresRuntime; SQLite degrades gracefully via getattr-fallback
- [X] T052 [US3] Update `web/game/api.py:game_timeseries` view (currently passes through to `bridge.get_game_timeseries`) to validate the response shape against the new contract — pass-through preserved; bridge guarantees shape

### Frontend wire-up

- [X] T053 [P] [US3] Create `web/frontend/src/hooks/useTimeseries.ts` — wraps `api.get(\`/api/games/\${id}/timeseries/\`)` with React state and refetch on tick advance. Returns `{data: TimeseriesPayload | null, loading: bool, error: Error | null}`
- [X] T054 [P] [US3] Create `web/frontend/src/types/timeseries.ts` mirroring the OpenAPI schema from `contracts/timeseries.yaml`
- [X] T055 [US3] Refactor `web/frontend/src/components/pages/BriefingPage.tsx` to remove `import { TICK, EVENTS, TIMESERIES, ORGS } from "../../fixtures/v2-mock-data"`. Replace with: `useGameSnapshot()` (existing hook, returns events + tick), `useTimeseries()` (T053), `usePlayerOrgs()` (existing). Render loading state per FR-027
- [X] T056 [US3] Map `events[].severity` to existing UI badge color tokens in BriefingPage Priority Dispatch panel. Sort by severity (critical > warning > informational), then by tick desc, take top 3
- [X] T057 [US3] Update `web/frontend/src/types/game.ts:Event` interface to include `id`, `severity`, `title`, `body` fields per the updated contract

### Polling cadence (FR-028, added per /speckit.analyze remediation)

- [X] T128 [US3] Verify and document polling cadence for v2 pages per FR-028. Concrete decision: **keep the existing 2000ms `POLL_INTERVAL_MS` constant** from `useGameState.ts` (validated for v1 pages); apply the same 2s interval to the v2 page hooks (`useTimeseries`, `useCommunities`, `useInspector`). Add a Playwright test in `web/frontend/e2e/polling-tick-aligned.spec.ts` asserting that when `/resolve/` advances the tick on the server, the v2 page's displayed tick number updates within 4 seconds (2× interval). Document the choice in `web/frontend/src/hooks/README.md`

**Checkpoint**: Briefing page shows live data. Run `mise run test:int && mise run web:test -- e2e/briefing-live-data.spec.ts e2e/polling-tick-aligned.spec.ts`.

---

## Phase 6: User Story 4 — Organizations Page Shows True Ownership and Live State (Priority: P2)

**Goal**: Player-controlled tab shows player's orgs; NPC tab shows the rest. Each org card shows real cohesion, current OODA phase, vanguard pools. Detail panel shows legitimacy, opacity, community memberships.

**Independent Test**: Session with 2 player orgs and 6 NPC orgs → player tab has exactly 2 cards, NPC tab has 6. Cohesion 0.62 displays as 0.62. OODA phase reads "orient" when engine state is "orient".

### Tests for User Story 4 (TDD)

- [X] T058 [P] [US4] Write integration test `tests/integration/test_org_serialization.py::test_player_controlled_flag_correct` — create session with player_id=42, seed 2 orgs with controlling_player_id=42 and 6 with controlling_player_id=None, GET `/state/`, assert exactly 2 orgs have `player_controlled: true`
- [X] T059 [P] [US4] Write integration test `tests/integration/test_org_serialization.py::test_ooda_phase_enum_present` — assert each serialized org has `ooda.phase ∈ {observe, orient, decide, act}` (not just the 4 floats)
- [X] T060 [P] [US4] Write integration test `tests/integration/test_org_serialization.py::test_short_name_present` — assert each org has `short_name` field, non-empty, ≤16 chars
- [X] T061 [P] [US4] Write integration test `tests/integration/test_org_serialization.py::test_hyperedge_memberships_populated` — when an org belongs to a community, assert `hyperedge_memberships` contains at least one entry (NOT hard-coded `[]`)
- [X] T062 [P] [US4] Write Playwright e2e test `web/frontend/e2e/orgs-live-data.spec.ts` — load `/games/<session>/orgs`, assert player tab card count matches API, click an org, assert OODA badge shows phase string

### Engine-side data model additions (`src/babylon/models/organization.py` or equivalent)

- [X] T063 [P] [US4] Add `short_name: str | None = None` field to engine `Organization` model. Add `__post_init__` (or Pydantic validator) that derives from `name` (truncate to 16 chars) when None
- [X] T064 [P] [US4] Add `controlling_player_id: int | None = None` field to engine `Organization` model
- [X] T065 [P] [US4] Add `legitimacy: Probability = Probability(0.5)` and `opacity: Probability = Probability(0.5)` fields to engine `Organization` model
- [X] T066 [P] [US4] Add `OodaPhase = Literal["observe", "orient", "decide", "act"]` type alias and a `current_phase` computed property (or Pydantic computed_field) on `OodaProfile` that returns the dominant component as `OodaPhase`. Source: `argmax({observe, orient, decide, act})` with deterministic tiebreak by enum order

### Bridge-side serializer expansion

- [X] T067 [US4] Extend `web/game/serializers.py:OrganizationSerializer` with `short_name`, `player_controlled`, `legitimacy`, `opacity`, `hyperedge_memberships` fields. Update `OodaProfileSerializer` with `phase` field. Match `contracts/snapshot.yaml#/components/schemas/Organization`
- [X] T068 [US4] Update `web/game/engine_bridge.py:_serialize_organization()` — replace hardcoded `consciousness: {0.33, 0.33, 0.34}` and `ooda: {0.5, 0.5, 0.5, 0.5, 4}` stubs with reads from the actual `Organization` instance. Add `player_controlled` derivation: `org.controlling_player_id == session.player_id`. Replace hardcoded `hyperedge_memberships: []` with XGI hypergraph query for org's communities
- [X] T069 [US4] Add `query_org_hyperedge_memberships(session_id, tick, org_id) -> list[HyperedgeMembership]` to `src/babylon/persistence/protocols.py:RuntimePersistence` and implement in both `RuntimeDatabase` (no-op returning empty list) and `PostgresRuntime` (read from `community_membership` table filtered by agent_id)
- [X] T070 [US4] Implement `web/game/engine_bridge.py:EngineBridge.get_org_status()` (currently stub) — return full `OrganizationSerializer` payload for one org_id. Wire to `/api/games/{id}/org/{id}/` endpoint

### Frontend wire-up

- [X] T071 [P] [US4] Update `web/frontend/src/types/game.ts:OrgState` to include `short_name`, `player_controlled`, `legitimacy`, `opacity`, `hyperedge_memberships`. Update `OodaProfile` type to include `phase: "observe" | "orient" | "decide" | "act"`
- [X] T072 [US4] Refactor `web/frontend/src/components/pages/OrgsPage.tsx` to remove `import { ORGS, COMMUNITIES, ... } from "../../fixtures/v2-mock-data"`. Replace with `useGameSnapshot()` reading orgs from snapshot. Filter to player-controlled orgs by `org.player_controlled === true` (replaces previous fixture flag). Render loading/error states per FR-027
- [X] T073 [US4] Update OrgsPage component cards to read from new field names: `org.short_name` instead of `org.short`, `org.ooda.phase` instead of inferring from floats. Map `org.vanguard.cadre_labor`/`max_cadre_labor` to existing `cl`/`cl_max` UI bindings (rename in component, NOT in API — keep engine field names canonical per FR-016)
- [X] T074 [US4] Update community-memberships panel in OrgsPage to read from `org.hyperedge_memberships` array (replaces fixture `org.members.includes(c.id)` filter)

**Checkpoint**: Orgs page fully wired. Run `mise run test:int -- tests/integration/test_org_serialization.py && mise run web:test -- e2e/orgs-live-data.spec.ts`.

---

## Phase 7: User Story 5 — Verb Actions Execute Through the Real Engine (Priority: P2)

**Goal**: Player composes action on any verb page, submits, action queues against current tick, resolves through real engine on next tick, results visible on Results page. Replays with same seed produce byte-identical outcomes.

**Independent Test**: Submit Educate against known target → action appears in `/actions/`. Resolve tick → action result row exists with non-zero deltas. Replay against fresh session with same seed → byte-identical results.

### Tests for User Story 5 (TDD)

- [X] T075 [P] [US5] Write integration test `tests/integration/test_action_lifecycle.py::test_submit_action_persists` — POST to `/actions/educate/`, GET `/actions/`, assert the action appears with `resolved=False`
- [X] T076 [P] [US5] Write integration test `tests/integration/test_action_lifecycle.py::test_resolve_processes_action` — submit Educate, POST `/resolve/`, assert action_result row exists with non-zero `consciousness_delta` AND original action's `resolved` flipped to True
- [X] T077 [P] [US5] Write integration test `tests/integration/test_action_determinism.py::test_replay_byte_identical` — two sessions with same `rng_seed`, same action sequence, assert action_result rows are byte-identical (FR-023, SC-004)
- [X] T078 [P] [US5] Write integration test `tests/integration/test_unsupported_verbs.py::test_unsupported_verbs_not_in_available_actions` — GET `/api/games/{id}/actions/available/`, assert that the response does NOT include `investigate`, `move`, or `negotiate` (per T081 Option A resolution: these verbs are removed from the available-actions list until a follow-up spec implements real handlers, satisfying FR-025).
- [X] T079 [P] [US5] Write Playwright e2e test `web/frontend/e2e/verb-submit.spec.ts` — navigate to `/games/<session>/actions/educate`, select actor, target, submit, assert success toast and entry visible on Results page after resolve

### Implementation

- [X] T080 [US5] Verify `web/game/engine_bridge.py:EngineBridge.resolve_tick()` threads the session's `rng_seed` into `step()` (FR-024). Currently `SimulationConfig()` is constructed with defaults at line 493-498. Change to `SimulationConfig(rng_seed=session.rng_seed)` (verify `SimulationConfig` accepts this; if not, add the field)
- [X] T081 [US5] Apply **Option A** for the three unsupported verbs (Investigate, Move, Negotiate) per FR-025 and the /speckit.analyze remediation decision. Concretely: remove these three keys from `web/game/engine_bridge.py:VERB_TO_ACTION_TYPE` (lines 53-63); remove them from `get_available_actions()` output; remove their per-verb endpoints from `web/game/urls.py` (or have them return 404). Add `web/frontend/src/lib/verb-config.ts` entries that mark these three verbs as `disabled: true` so the UI omits them from the verb picker. File a follow-up spec for real handler implementation; this spec does NOT implement them.
- [X] T082 [US5] Refactor `web/frontend/src/components/pages/VerbPage.tsx` — remove `import { ORGS, VERBS } from "../../fixtures/v2-mock-data"`. Wire actor list from `useGameSnapshot()` filtered to `player_controlled`. Wire target list from `useVerbTargets(verb, orgId)` (existing pattern in gameStore). Wire submit button `onClick` handler to `submitAction(verb, params)` from `gameStore`
- [X] T083 [US5] Verify the affordability pre-check in `web/game/engine_bridge.py:submit_action()` (lines 663-691, `VanguardResources.from_organization()`) is correctly blocking submission with insufficient resources, returning 422 with explicit error. Frontend error state per FR-027

### Verify existing FR-021/FR-022 behavior (added per /speckit.analyze remediation)

- [X] T129 [P] [US5] Document in the test docstrings for T075/T076 that these tests cover **existing** action-persistence and tick-resolution behavior (FR-021, FR-022) — no production-code change is required for these FRs. If T075 or T076 fails, the regression is in pre-existing engine code, not in this feature's new work. This is a documentation-only task; no source code is modified.

**Checkpoint**: Verb pages submit real actions; results are deterministic and visible on Results page. Run `mise run test:int -- tests/integration/test_action_*.py tests/integration/test_unsupported_verbs.py`.

---

## Phase 8: User Story 6 — Intel, Results, Analysis Pages Show Real Entities (Priority: P2)

**Goal**: Intel page surveils real territories/orgs/edges/communities. Results page shows real action outcomes. Analysis page renders real time-series.

**Independent Test**: Territory detail shows persisted heat/population/rent. Results page shows submitted actions' outcomes. Analysis sparklines have N points for an N-tick session.

### Tests for User Story 6 (TDD)

- [X] T084 [P] [US6] Write integration test `tests/integration/test_territory_serialization.py::test_extended_fields_present` — assert every serialized Territory has `consciousness`, `solidarity`, `wealth`, `dominant_community` (FR-013)
- [X] T085 [P] [US6] Write integration test `tests/integration/test_edge_serialization.py::test_extended_fields_present_or_null` — assert every serialized Edge has `id` and either real numeric `rate_of_profit`/`rent_burden`/`age_ticks` OR explicit `null` (FR-014)
- [X] T086 [P] [US6] Write integration test `tests/integration/test_communities_endpoint.py::test_returns_per_community_ternary` — GET `/communities/`, assert each entry has `hyperedge_id`, `category`, `member_count`, `ternary` with three numeric fields (FR-018)
- [X] T087 [P] [US6] Write integration tests `tests/integration/test_inspector_endpoints.py::test_{node,org,community,edge,hex}_returns_detail` — one test per inspector, each asserts non-empty `data` dict matching the corresponding contract schema (FR-019)
- [X] T088 [P] [US6] Write Playwright e2e test `web/frontend/e2e/intel-results-analysis.spec.ts` — visit each of `/intel/territories/<id>`, `/results`, `/analysis`. Assert per-page acceptance scenarios from spec US6

### Bridge-side stub method implementations

- [X] T089 [US6] Implement `web/game/engine_bridge.py:EngineBridge.get_communities_dashboard()` — query `community_state` and `community_membership` tables via persistence layer, aggregate per community, return shape per `contracts/communities.yaml`. Add `query_community_dashboard(session_id, tick) -> list[CommunityDashboardRow]` to RuntimePersistence protocol
- [X] T090 [US6] Implement `web/game/engine_bridge.py:EngineBridge.get_economy_summary()` — read latest row from `economic_summary` table for the session. Add `query_economy_summary(session_id, tick) -> EconomySummaryRow` to RuntimePersistence protocol
- [X] T091 [US6] Implement five inspector methods on `EngineBridge`: `inspect_node(id)`, `inspect_org(id)`, `inspect_community(id)`, `inspect_edge(id)`, `inspect_hex(h3)`. Each returns the populated detail object per `contracts/inspectors.yaml`. Compose from existing serializers + 1-2 additional persistence reads (e.g., `recent_actions` from `action_result`, `history` from `edge_snapshot`)
- [X] T092 [P] [US6] Add `query_org_recent_actions(session_id, org_id, limit) -> list[ActionResultRow]` to RuntimePersistence and implement in both backends
- [X] T093 [P] [US6] Add `query_edge_history(session_id, source_id, target_id, edge_type, limit) -> list[EdgeSnapshotRow]` to RuntimePersistence and implement in both backends

### Bridge-side serializer expansion (Territory, Edge)

- [X] T094 [US6] Extend `web/game/serializers.py:TerritorySerializer` with `consciousness`, `solidarity`, `wealth`, `dominant_community` fields (FR-013)
- [X] T095 [US6] Extend `_serialize_territory()` in `web/game/engine_bridge.py` to compute the four new fields. `consciousness` and `solidarity` are derived aggregates over orgs/edges in territory. `wealth` reads from `CountyEconomicState.total_wealth`. `dominant_community` queries XGI for the community with largest member share in territory
- [X] T096 [US6] Extend `web/game/serializers.py:EdgeSerializer` with `id` (deterministic from `source_id>edge_type>target_id`), `rate_of_profit`, `rent_burden`, `age_ticks`. Match `contracts/snapshot.yaml#/components/schemas/Edge`
- [X] T097 [US6] Update `_serialize_edge()` in `web/game/engine_bridge.py` to populate the new fields. `age_ticks` requires either a new `created_at_tick` engine attribute OR querying `edge_snapshot` for first-seen tick (prefer the latter; do not mutate Edge primitive)
- [X] T098 [US6] Update `web/game/serializers.py:ActionResultSerializer` to add a derived `outcome` formatted-string field (e.g., `"+0.04 CON, +0.08 HEAT"`) computed from `consciousness_delta` and `heat_delta`. Frontend ResultsPage expects this string format

### Frontend wire-up (3 pages)

- [X] T099 [P] [US6] Create `web/frontend/src/hooks/useCommunities.ts` — wraps `api.get(\`/api/games/\${id}/communities/\`)`. Returns `{data: CommunitiesPayload | null, loading, error}`
- [X] T100 [P] [US6] Create `web/frontend/src/hooks/useInspector.ts` — generic hook taking `(type, id)`, dispatches to the correct inspector endpoint. Returns the detail payload
- [X] T101 [US6] Refactor `web/frontend/src/components/pages/IntelPageV2.tsx` to remove fixture imports. Wire territory/org/edge/community lists from `useGameSnapshot()`. Wire detail panels from `useInspector(type, id)` based on URL params
- [X] T102 [US6] Refactor `web/frontend/src/components/pages/ResultsPage.tsx` to remove fixture imports. Wire from `useGameResults(currentTick)` (new hook calling `/results/{tick}/`) and `useGameSnapshot()` for org context. **Remove the hardcoded tensor-diff panel** at lines 71-80 OR mark it as TODO and move to a separate v2-pages-polish spec
- [X] T103 [US6] Refactor `web/frontend/src/components/pages/AnalysisPage.tsx` to remove fixture imports. Wire all six sparklines from `useTimeseries()` (created in T053). Topology graph placeholder remains for now (out of scope per spec Out of Scope)

**Checkpoint**: All three pages live. Run `mise run test:int -- tests/integration/test_{territory,edge,communities,inspector}*.py && mise run web:test -- e2e/intel-results-analysis.spec.ts`.

---

## Phase 9: User Story 7 — Mock Scaffolding Sunset (Priority: P3)

**Goal**: Mock bridge implementation, mock defines, mock-only management commands, and the orphan database objects are all deleted. `BABYLON_MOCK_MODE` flag removed. Fixture-era sessions purged.

**Independent Test**: `grep -rn "MockEngineBridge\|mock_defines\|seed_mock_game\|BABYLON_MOCK_MODE" src/ web/` returns zero matches outside the spec dir. `ls web/game/mock_bridge.py` returns "No such file."

### Tests for User Story 7 (TDD)

- [X] T104 [P] [US7] Write CI script `tests/scripts/check_mock_sunset.sh` — `grep -rn "MockEngineBridge\|mock_defines\|seed_mock_game\|BABYLON_MOCK_MODE" src/ web/ --include="*.py" | grep -v __pycache__ | wc -l` should equal 0. Add to `mise run check` as a final step
- [X] T105 [P] [US7] Write integration test `tests/integration/test_purged_session_404.py` — given a UUID that was purged by migration 0007, assert GET `/api/games/<uuid>/state/` returns 404
- [X] T106 [P] [US7] Write integration test `tests/integration/test_seed_initial_game_command.py::test_creates_real_engine_session` — invoke management command, assert created GameSession has `snapshot_json` empty/absent (NOT populated by mock writer)

### Implementation

- [X] T107 [US7] Delete `web/game/mock_bridge.py` (FR-032)
- [X] T108 [US7] Delete `web/game/mock_defines.py` (FR-032)
- [X] T109 [US7] Delete `web/game/management/commands/seed_mock_game.py` (FR-032)
- [X] T110 [US7] Create `web/game/management/commands/seed_initial_game.py` — uses real `EngineBridge.create_game()` directly (no MockEngineBridge). Args: `--scenario` (default `wayne_county`), `--player` (Django username, looked up to player_id). Replaces `seed_mock_game` for dev/test seeding
- [X] T111 [US7] Remove `BABYLON_MOCK_MODE` setting from `web/babylon_web/settings/base.py`, `web/babylon_web/settings/stub.py`, and any other settings module that references it (FR-032)
- [X] T112 [US7] Remove the `BABYLON_MOCK_MODE` branch from `web/game/api.py:_get_bridge()`. The function should now: (1) return `_bridge_instance` if set; (2) raise RuntimeError "EngineBridge not initialized — apps.py:GameConfig.ready failed" otherwise. No StubEngineBridge fallback in production
- [X] T113 [US7] Update `web/game/stub_bridge.py` — keep ONLY the dev-mode SQLite stub-tables path used when `STUB_CREATE_TABLES=True` for offline development without Postgres. Remove all production-fallback code paths. Add module docstring clarifying it is dev-only and never selected in production
- [X] T114 [US7] Fix `web/game/management/commands/seed_hex_data.py:12` docstring — change `"Seeds sim.hex_states from the mock fixture for a given GameSession."` to `"Seeds hex_latest from the GeoJSON fixture for a given GameSession."` (FR-031)
- [X] T115 [US7] Delete `web/frontend/src/fixtures/v2-mock-data.ts` (FR-029) — must run AFTER all v2 pages are wired (T055, T072, T082, T101, T102, T103). Confirm via `grep -rn "v2-mock-data" web/frontend/src/` returns zero before deleting

**Checkpoint**: Mock fully sunset. Run `bash tests/scripts/check_mock_sunset.sh` (exits 0 on success).

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, documentation, deployment readiness.

- [ ] T116 [P] Run the full quickstart.md validation walkthrough end-to-end against a fresh dev DB. Capture timing + any deviations from spec acceptance criteria. File issues for any drift
- [X] T117 [P] Update `ai-docs/state.yaml` with feature 061 status and new test counts (per CLAUDE.md "Documentation Maintenance" guidance)
- [X] T118 [P] Update `ai-docs/decisions.yaml` with a new ADR for this feature: ADR0XX_real_backend_wireup. Capture: cutover-purge decision, sentence-transformers pin, hybrid-retry-then-exit boot, custom DRF exception handler pattern
- [X] T119 [P] Update `ai-docs/roadmap.md` to reflect that the v2 page wire-up is complete; identify any follow-up work (e.g., the hardcoded tensor-diff panel in ResultsPage from T102)
- [X] T120 Pin the `CANONICAL_EMBEDDING_REVISION` SHA in `src/babylon/config/llm_config.py` (T002 used a placeholder). Capture the actual SHA after first successful download from HuggingFace: `huggingface-cli scan-cache | grep all-mpnet-base-v2`
- [X] T121 [P] Run `poetry run mypy src/babylon/persistence/ src/babylon/rag/ web/babylon_web/health/ web/game/ --strict` and resolve any new type errors introduced by this feature
- [X] T122 [P] Run `poetry run ruff check . --fix && poetry run ruff format .` to sweep formatting before commit
- [ ] T123 Update `web/HOW-TO-LOCAL-DEV.md` to reflect the new bootstrap flow: `mise run web:migrate` → `mise run web:manage seed_initial_game --scenario wayne_county --player admin` → `mise run web:dev`. Remove any references to `seed_mock_game` or `BABYLON_MOCK_MODE`
- [ ] T124 Performance verification: time the full quickstart action-submit-to-result-visibility cycle, assert <10s p95 per SC-012. If exceeded, profile via `cProfile` on the resolve path
- [ ] T125 Smoke-test the systemd unit on a staging host: stop Postgres, observe 3 retries + exit, observe systemd restart, start Postgres, observe successful boot and `/health/detail/` reports `EngineBridge`

### Stress tests for rate-based success criteria (added per /speckit.analyze remediation)

- [ ] T130 [P] Add stress-test runner `tests/integration/test_rate_criteria.py` exercising the three "N-run" success criteria in a single parameterized fixture:
  - `test_sc003_action_to_result_rate_50_actions` — submit 50 Educate actions across one session, resolve in batches, assert 100% appear as action_result rows within one tick boundary (SC-003)
  - `test_sc006_pgvector_query_rate_100_queries` — issue 100 similarity queries against an ingested fixture corpus, assert ≥1 result on each and zero `UndefinedColumn`/`OperationalError` exceptions (SC-006)
  - `test_sc007_health_detail_rate_100_boots` — invoke `GameConfig._initialize_engine_with_retry()` 100 times against a reachable test DB (each clears `_initialized` flag first), assert all 100 produce a valid `EngineBridge` instance and the `/health/detail/` endpoint returns 200 with `implementation == "EngineBridge"` on each (SC-007). Use a transaction-rollback fixture to avoid DB pollution.
- [ ] T131 [P] Add multi-session smoke test `tests/integration/test_multi_session_distinct.py::test_two_sessions_distinct_data` per SC-005 — create session A with rng_seed=1 and session B with rng_seed=2, advance each by 2 ticks via `/resolve/`, GET state/timeseries/communities/orgs from both. Assert each of: (a) at least one org name differs between sessions; (b) tick events for the latest tick differ; (c) at least one timeseries metric array differs at index 1+; (d) total org counts can be equal but `id` sets differ; (e) and (f) — same for territories and communities. Total: 6 distinct-field assertions across the six categories.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately. T001-T005 can all run in parallel.
- **Foundational (Phase 2)**: Depends on Setup (T001 sentence-transformers dependency for embedding-related tests; T002-T003 constants for boot tests). BLOCKS all user stories.
  - T006-T012 (migrations) must run sequentially in numbered order; T012 depends on T006-T011.
  - T013-T017 (transactional wrap) depend on T009 (idempotency constraint exists).
  - T018-T020 (boot retry) depend on T002 (constants exist).
  - T021-T022 (systemd) depend on T005 (version verified).
  - T023-T025 (foundational tests) depend on T013-T020 implementations being in place.
- **User Stories (Phase 3+)**: All depend on Foundational (Phase 2) completion.
  - US1 and US2 are P1 and can proceed in parallel after Phase 2.
  - US3-US6 are P2 and can proceed in parallel with each other after Phase 2.
  - US7 (mock sunset) MUST run AFTER US3-US6 because T115 (delete v2-mock-data.ts) depends on all v2 pages being wired (T055, T072, T082, T101, T102, T103).
- **Polish (Phase 10)**: Depends on all desired user stories being complete.

### User Story Dependencies (intra-feature)

- **US1 (P1, Semantic Search)**: Independent. Pure persistence-layer fix. Can ship as standalone increment.
- **US2 (P1, Engine Visibility)**: Independent of US1. Health endpoints + boot retry. Can ship as standalone increment.
- **US3 (P2, Briefing)**: Depends on Foundational only. Adds `EventSerializer` fields and `get_game_timeseries`.
- **US4 (P2, Orgs)**: Depends on Foundational only. Adds Organization model fields and serializer expansion. Independent of US3 (different fields).
- **US5 (P2, Verb Actions)**: Depends on US4 (needs `player_controlled` and `short_name`) for the actor picker. T080 (RNG seed) is independent and can be done first.
- **US6 (P2, Intel/Results/Analysis)**: Depends on US3 (needs `EventSerializer` for events on inspector pages) and US4 (needs `OrganizationSerializer` extensions for org inspector). Stub-method implementations (T089-T093) are independent.
- **US7 (P3, Mock Sunset)**: Depends on US3 + US4 + US5 + US6 v2-page wire-up (T055, T072, T082, T101, T102, T103) — must NOT delete the fixture module (T115) until those pages no longer import it.

### Within Each User Story

- Tests (TDD) FIRST — written and failing before implementation
- Engine model changes BEFORE serializer changes BEFORE bridge wiring BEFORE frontend wire-up
- Persistence-protocol additions BEFORE the implementations that call them
- Each story complete before moving to next priority

### Parallel Opportunities

- **Setup**: T001 sequential (modifies pyproject.toml + lock); T002-T005 all parallel
- **Foundational**: Migrations T006-T011 sequential by number; T021/T022 systemd parallel with T013-T020 transactional wrap; T023-T025 tests parallel with each other
- **US1**: T026-T028 tests parallel; T029-T032 implementation mostly sequential (single file)
- **US2**: T033-T037 tests all parallel; T038-T042 implementation has T038→T040→T043 dependency chain; T039 and T041 parallel. T126 (mid-session 503 test) parallel with T033-T037; T127 (mid-session impl) depends on T038 (HealthDetailView exists) so middleware can exempt the health routes
- **US3**: T044-T046 tests parallel; T047 (engine model) parallel with T053-T054 (frontend types/hooks). T128 (polling cadence) depends on T053 (`useTimeseries` hook exists) and runs near end of US3 phase
- **US4**: T058-T062 tests parallel; T063-T066 (engine fields) all parallel; T071 (frontend types) parallel with engine fields
- **US5**: T075-T079 tests parallel; T080-T083 mostly sequential (frontend integration). T129 (FR-021/FR-022 docstring update) parallel with everything else; pure documentation
- **US6**: T084-T088 tests parallel; T089-T093 (stub methods + persistence protocol) parallel; T099-T100 (frontend hooks) parallel
- **US7**: T104-T106 tests parallel; T107-T109 (deletions) parallel
- **Polish**: T116-T122 mostly parallel (different files / different concerns). T130 (rate-criteria stress tests) and T131 (multi-session smoke test) parallel with each other and with most of T116-T122; both depend on US1-US6 being complete (they exercise the full wire-up)

---

## Parallel Example: User Story 4 (Orgs Page)

```bash
# Launch all US4 tests together (TDD red phase):
Task: "Integration test test_player_controlled_flag_correct in tests/integration/test_org_serialization.py"
Task: "Integration test test_ooda_phase_enum_present in tests/integration/test_org_serialization.py"
Task: "Integration test test_short_name_present in tests/integration/test_org_serialization.py"
Task: "Integration test test_hyperedge_memberships_populated in tests/integration/test_org_serialization.py"
Task: "Playwright e2e test orgs-live-data.spec.ts in web/frontend/e2e/"

# Launch all US4 engine field additions together:
Task: "Add short_name field to engine Organization in src/babylon/models/organization.py"
Task: "Add controlling_player_id field to engine Organization in src/babylon/models/organization.py"
Task: "Add legitimacy and opacity fields to engine Organization in src/babylon/models/organization.py"
Task: "Add OodaPhase type and current_phase property to OodaProfile in src/babylon/models/ooda.py"

# Launch frontend types in parallel with engine work:
Task: "Update OrgState and OodaProfile types in web/frontend/src/types/game.ts"
```

---

## Parallel Example: User Story 6 (Intel/Results/Analysis)

```bash
# Stub-method implementations are all independent of each other:
Task: "Implement get_communities_dashboard in web/game/engine_bridge.py"
Task: "Implement get_economy_summary in web/game/engine_bridge.py"
Task: "Implement five inspector methods (inspect_node, inspect_org, inspect_community, inspect_edge, inspect_hex) in web/game/engine_bridge.py"
Task: "Add query_org_recent_actions to RuntimePersistence protocol"
Task: "Add query_edge_history to RuntimePersistence protocol"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 only — both P1)

This MVP is the **safety floor**: nothing player-facing changes, but the production deployment becomes safe to operate.

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T025) — schema fixed, transactions atomic, boot retries hard-fail loudly
3. Complete Phase 3: User Story 1 (T026-T032) — semantic search functions
4. Complete Phase 4: User Story 2 (T033-T043) — health endpoints + visible boot failures
5. **STOP and DEPLOY**: At this point production is dramatically safer than today, and a downstream RAG feature can be built. Players still see fixture data — but the platform is sound.

### Incremental Delivery (P2 stories)

After MVP ships:

6. Add User Story 3 (Briefing) → demo the first live-data page → deploy
7. Add User Story 4 (Orgs) → demo player-controlled distinction → deploy
8. Add User Story 5 (Verb actions) → demo end-to-end submit/resolve → deploy
9. Add User Story 6 (Intel/Results/Analysis) → demo the remaining 3 pages → deploy

Each increment is self-contained per the spec's user-story design. A user can use the game with US3+US5 only (Briefing + Verb actions) even before Orgs/Intel/Results/Analysis are wired.

### Final Cleanup (P3)

10. Add User Story 7 (Mock sunset) → final cleanup, codebase honesty restored

### Polish

11. Phase 10 polish tasks for documentation, type-checking, linting, perf verification

### Parallel Team Strategy

If multiple implementers are working in parallel after Phase 2 completes:

- **Implementer A**: US1 (semantic search) + US7 (sunset) — bookends, mostly persistence-layer
- **Implementer B**: US2 (health) + US5 (verb actions) — backend-heavy
- **Implementer C**: US3 (Briefing) + US4 (Orgs) — frontend + serializer-heavy
- **Implementer D**: US6 (Intel/Results/Analysis) — broad scope, mostly stub-method implementations

US7 must be coordinated with all v2-page wire-ups (US3-US6) before T115 fires.

---

## Notes

- **TDD enforcement**: Per project CLAUDE.md, every user story's test tasks (T026-T028, T033-T037, T044-T046, T058-T062, T075-T079, T084-T088, T104-T106) must be written and failing before the corresponding implementation tasks begin. Use `pytest -m red_phase` to mark in-progress tests.
- **Constitution compliance** is verified per phase against `plan.md` post-design Constitution Check. No principle violations expected.
- **`mise run check`** must pass after each user story phase completes (lint + format + typecheck + test:unit).
- **Commit cadence**: per CLAUDE.md, commit after each task or logical group. Use conventional commit format: `feat(scope):`, `fix(scope):`, `refactor(scope):`. Don't accumulate units of work.
- **Cross-story dependency hazard**: T115 (delete fixture module) depends on T055, T072, T082, T101, T102, T103. Verify with grep before delete.
- **Out of scope**: hardcoded tensor-diff panel in ResultsPage (T102 marks as TODO); v1 page re-wiring; new gameplay verbs; new scenarios; deployment infra modernization (docker-compose / supervisor in `deploy/ansible/`).
