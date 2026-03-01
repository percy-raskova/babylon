# Tasks: Postgres Runtime Database

**Input**: Design documents from `/specs/037-postgres-runtime-db/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included (TDD is the project standard per CLAUDE.md).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add dependencies, create directory structure, configure test infrastructure

- [ ] T001 Add psycopg[binary], psycopg_pool, and pgvector dependencies to pyproject.toml (psycopg already present; verify psycopg_pool, pgvector added)
- [ ] T002 [P] Create test fixture infrastructure for Postgres tests in tests/conftest.py (connection factory, test database setup/teardown, skip marker for missing Postgres)
- [ ] T003 [P] Create tests/integration/conftest.py with Postgres integration test fixtures (real psycopg connection pool, schema bootstrap, per-test transaction rollback)

______________________________________________________________________

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Protocol definitions, DDL schema, ServiceContainer wiring, and base class — MUST complete before ANY user story

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Create RuntimePersistence protocol, PostgresRuntimeExtensions protocol, TraceLevel enum, TraceCollector protocol, and VectorStoreProtocol in src/babylon/persistence/protocols.py (translate from specs/037-postgres-runtime-db/contracts/ to production code)
- [ ] T005 Write protocol compliance contract tests in tests/contract/test_persistence_contracts.py — verify RuntimeDatabase satisfies RuntimePersistence via isinstance() check (follow existing pattern in tests/contract/test_infrastructure_contracts.py)
- [ ] T006 [P] Add missing methods to RuntimeDatabase in src/babylon/persistence/runtime_db.py so it satisfies RuntimePersistence protocol (add session_id parameter to persist_tick and hydrate_graph; add log_tick system_timings parameter if missing)
- [ ] T007 Create Postgres DDL for all 21 tables in src/babylon/persistence/postgres_schema.py — Layer 1 (game_session, game_turn, action_result), Layer 2 (node_state, edge_state, graph_metadata, community_state, community_membership, contradiction_field, edge_curvature, simulation_event, tick_log, tick_summary), Layer 3 (hex_cell, hex_state, hex_terrain_state), Layer 4 (infrastructure_link_state), Layer 5 (trace_log UNLOGGED), Layer 6 (document_chunk with vector(768)) — reference data-model.md for exact schema
- [ ] T008 [P] Add persistence (RuntimePersistence | None) and tracer (TraceCollector | None) fields to ServiceContainer in src/babylon/engine/services.py — default None, add to create() factory
- [ ] T009 Create PostgresRuntime base class in src/babylon/persistence/postgres_runtime.py — __init__ with psycopg_pool.ConnectionPool, close(), context manager, _execute_batch() helper for bulk inserts via executemany/COPY
- [ ] T010 Update src/babylon/persistence/__init__.py — export RuntimePersistence, PostgresRuntimeExtensions, TraceLevel, TraceCollector, VectorStoreProtocol, PostgresRuntime, and existing RuntimeDatabase/RUNTIME_SCHEMA_DDL

**Checkpoint**: Foundation ready — protocol defined, schema DDL written, ServiceContainer wired, base class created. User story implementation can now begin.

______________________________________________________________________

## Phase 3: User Story 1 — Simulation State Survives Restarts (Priority: P1) MVP

**Goal**: Persist complete simulation state each tick and hydrate it on restart with zero data loss — nodes, edges, graph metadata, community hypergraph, hex economics, infrastructure topology, contradiction fields, events, tick log, and tick summary.

**Independent Test**: Start a game, advance 10 ticks, close, reopen, verify all state matches pre-restart values exactly.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T011 [P] [US1] Write unit tests for PostgresRuntime.persist_tick (node_state and edge_state inserts) in tests/unit/persistence/test_postgres_runtime.py — mock psycopg connection, verify SQL and parameter binding for 4 node types and all edge types
- [ ] T012 [P] [US1] Write unit tests for PostgresRuntime.hydrate_graph (graph reconstruction from node_state, edge_state, graph_metadata) in tests/unit/persistence/test_postgres_runtime.py — verify round-trip fidelity of JSONB attributes
- [ ] T013 [P] [US1] Write unit tests for persist_graph_metadata, persist_community_state, persist_hex_state, persist_infrastructure_state, persist_contradiction_fields in tests/unit/persistence/test_postgres_runtime.py — mock psycopg, verify bulk insert row counts
- [ ] T014 [P] [US1] Write integration test for full persist/hydrate round-trip in tests/integration/test_postgres_integration.py — real Postgres, persist tick with all subsystems, hydrate, compare graph node/edge attributes

### Implementation for User Story 1

- [ ] T015 [US1] Implement persist_tick in src/babylon/persistence/postgres_runtime.py — INSERT node_state (with promoted columns), edge_state (with promoted columns), simulation_event rows; use executemany for bulk insert; full model_dump() to JSONB attributes column
- [ ] T016 [US1] Implement persist_graph_metadata in src/babylon/persistence/postgres_runtime.py — INSERT graph_metadata row with economy, state_finances, tick_dynamics JSONB
- [ ] T017 [US1] Implement persist_community_state in src/babylon/persistence/postgres_runtime.py — INSERT community_state (14 rows) and community_membership (~200 rows) per tick
- [ ] T018 [US1] Implement persist_hex_state in src/babylon/persistence/postgres_runtime.py — bulk INSERT ~1,500 hex_state rows via executemany or COPY protocol
- [ ] T019 [US1] Implement persist_infrastructure_state in src/babylon/persistence/postgres_runtime.py — INSERT hex_terrain_state (~1,500 rows) and infrastructure_link_state (~100 rows) from Feature 036 manager to_dict() output
- [ ] T020 [US1] Implement persist_contradiction_fields in src/babylon/persistence/postgres_runtime.py — INSERT contradiction_field (4 fields × ~20 nodes) and edge_curvature (~50 edges) per tick
- [ ] T021 [US1] Implement log_tick and persist_tick_summary in src/babylon/persistence/postgres_runtime.py — INSERT tick_log (RNG state, mutations, timings) and tick_summary (pre-aggregated metrics)
- [ ] T022 [US1] Implement set_metadata and get_metadata in src/babylon/persistence/postgres_runtime.py — INSERT/UPDATE simulation_metadata or use game_session config_json
- [ ] T023 [US1] Implement hydrate_graph in src/babylon/persistence/postgres_runtime.py — SELECT from node_state, edge_state, graph_metadata for a given (session_id, tick), reconstruct nx.DiGraph with all attributes from JSONB
- [ ] T024 [US1] Implement hydrate_community_state in src/babylon/persistence/postgres_runtime.py — SELECT from community_state and community_membership, return (community_states dict, memberships list)
- [ ] T025 [US1] Wire Simulation class to persist subsystem state after tick via new PersistenceObserver in src/babylon/engine/observers/persistence_observer.py — observer calls persistence.persist_tick, persist_graph_metadata, persist_community_state, persist_hex_state, persist_infrastructure_state, persist_contradiction_fields, log_tick, persist_tick_summary after each tick

**Checkpoint**: At this point, User Story 1 should be fully functional — complete simulation state persists and hydrates with zero data loss.

______________________________________________________________________

## Phase 4: User Story 2 — Player Turn Submission and Resolution (Priority: P1)

**Goal**: Record player action submissions, resolve them during tick, persist outcomes with initiative scores and state deltas.

**Independent Test**: Submit a player action, advance the tick, verify the action was resolved and outcomes are retrievable.

### Tests for User Story 2

- [ ] T026 [P] [US2] Write unit tests for turn submission (game_turn INSERT with uniqueness constraint) and action result persistence in tests/unit/persistence/test_postgres_runtime.py

### Implementation for User Story 2

- [ ] T027 [US2] Implement submit_turn in src/babylon/persistence/postgres_runtime.py — INSERT game_turn with (session_id, tick, org_id) uniqueness, reject duplicates with constraint violation
- [ ] T028 [US2] Implement persist_action_results in src/babylon/persistence/postgres_runtime.py — bulk INSERT action_result rows with initiative_score, action_cost, success, consciousness_delta, heat_delta, details JSONB
- [ ] T029 [US2] Implement get_pending_turns and mark_turns_resolved in src/babylon/persistence/postgres_runtime.py — SELECT unresolved turns for current tick, UPDATE resolved=TRUE after tick execution

**Checkpoint**: Player actions recorded, resolved, and outcomes persisted. One action per org per tick enforced.

______________________________________________________________________

## Phase 5: User Story 3 — Multi-Session Game Management (Priority: P1)

**Goal**: Create, pause, resume, and complete game sessions with full isolation between concurrent games.

**Independent Test**: Create two sessions with different scenarios, advance each independently, verify no state leakage.

### Tests for User Story 3

- [ ] T030 [P] [US3] Write unit tests for session CRUD (create, get, update status) and isolation verification in tests/unit/persistence/test_postgres_runtime.py

### Implementation for User Story 3

- [ ] T031 [US3] Implement create_session in src/babylon/persistence/postgres_runtime.py — INSERT game_session with UUID, scenario, config_json (SimulationConfig.model_dump), game_defines_json (GameDefines.model_dump), rng_seed, trace_level
- [ ] T032 [US3] Implement get_session, update_session_status, and get_active_sessions in src/babylon/persistence/postgres_runtime.py — lifecycle transitions (active → paused → completed/abandoned/archived)
- [ ] T033 [US3] Write integration test for session isolation in tests/integration/test_postgres_integration.py — create two sessions, persist state in each, verify queries return only session-scoped data

**Checkpoint**: Full session lifecycle management. Sessions are isolated — no cross-contamination.

______________________________________________________________________

## Phase 6: User Story 4 — Execution Trace Debugging (Priority: P2)

**Goal**: Buffer trace events during tick computation (zero I/O), flush to Postgres after tick, support per-session partition create/drop for instant cleanup.

**Independent Test**: Enable DEBUG tracing, run 5 ticks, query traces to reconstruct formula evaluation history.

### Tests for User Story 4

- [ ] T034 [P] [US4] Write unit tests for TraceRecorder in tests/unit/persistence/test_trace_recorder.py — verify buffer accumulation during trace(), flush writes to persistence, level filtering, buffer_size property, NONE level is no-op

### Implementation for User Story 4

- [ ] T035 [US4] Implement TraceRecorder in src/babylon/persistence/trace_recorder.py — buffer trace events in memory list, flush() calls persistence.persist_traces(), level-based filtering, buffer_size property
- [ ] T036 [US4] Implement persist_traces in src/babylon/persistence/postgres_runtime.py — bulk INSERT trace_log rows via executemany (session_id, tick, system_name, level, event, node_id, data JSONB)
- [ ] T037 [US4] Implement create_session_partition and drop_session_partition in src/babylon/persistence/postgres_runtime.py — CREATE TABLE trace_log_{session_id} PARTITION OF trace_log FOR VALUES IN (session_id), DROP TABLE for instant cleanup
- [ ] T038 [US4] Wire TraceRecorder into Simulation lifecycle — create TraceRecorder from ServiceContainer.tracer config, add as observer or inject into PersistenceObserver, call flush() after each tick

**Checkpoint**: Trace debugging functional. Events buffer in memory during tick, flush to partitioned table after. Partition drop is instant cleanup.

______________________________________________________________________

## Phase 7: User Story 5 — Spatial Map Queries (Priority: P2)

**Goal**: Efficient spatial queries on hex grid via PostGIS — filter by county, aggregate by region, time-series per hex.

**Independent Test**: Load hex map for a specific tick, verify all ~1,500 cells render with correct values. Query by county FIPS.

### Tests for User Story 5

- [ ] T039 [P] [US5] Write unit tests for hex_cell reference table population and spatial query methods in tests/unit/persistence/test_postgres_runtime.py

### Implementation for User Story 5

- [ ] T040 [US5] Implement populate_hex_cells in src/babylon/persistence/postgres_runtime.py — bulk INSERT hex_cell reference rows with h3_index, county_fips, parent cells, PostGIS geometry (POLYGON) and centroid (POINT) from H3 cell boundaries
- [ ] T041 [US5] Implement get_hex_state_for_tick in src/babylon/persistence/postgres_runtime.py — SELECT hex_state JOIN hex_cell for a given (session_id, tick), with optional county_fips filter using GiST spatial index
- [ ] T042 [US5] Implement get_hex_time_series in src/babylon/persistence/postgres_runtime.py — SELECT hex_state for a given (session_id, h3_index) across tick range, return ordered time-series

**Checkpoint**: Spatial queries operational. Hex map renders efficiently, county-scoped aggregations work.

______________________________________________________________________

## Phase 8: User Story 6 — Game Archival and Cold Storage (Priority: P3)

**Goal**: Export completed sessions to Parquet, upload to R2, enable DuckDB analytics over archived data, purge active storage.

**Independent Test**: Complete a game, trigger archival, verify data removed from Postgres and queryable from Parquet.

### Tests for User Story 6

- [ ] T043 [P] [US6] Write unit tests for Parquet export (table-to-Parquet conversion, schema mapping) in tests/unit/persistence/test_archival.py
- [ ] T044 [P] [US6] Write integration test for full export-upload-query cycle in tests/integration/test_archival_integration.py (use local filesystem instead of R2 for CI)

### Implementation for User Story 6

- [ ] T045 [US6] Implement export_session_to_parquet in src/babylon/persistence/archival.py — SELECT all session data from each table, convert to PyArrow Tables, write Parquet files with zstd compression to output directory
- [ ] T046 [US6] Implement upload_to_r2 in src/babylon/persistence/archival.py — upload Parquet files to R2 bucket via boto3 S3 interface, verify checksums
- [ ] T047 [US6] Implement purge_session in src/babylon/persistence/archival.py — DELETE session data from all tables after verified export, preserve game_session record with status='archived'
- [ ] T048 [US6] Implement query_archived_session in src/babylon/persistence/archival.py — use DuckDB to read Parquet files directly from R2 (or local path), return query results
- [ ] T049 [US6] Create Django management command for archival in src/babylon/persistence/management/commands/archive_sessions.py — find completed sessions older than 24h, run export → upload → purge pipeline

**Checkpoint**: Archival pipeline functional. Completed games compressed to Parquet (~8:1 ratio), uploaded to R2, queryable via DuckDB.

______________________________________________________________________

## Phase 9: User Story 7 — Semantic Search Over Game Corpus (Priority: P3)

**Goal**: Replace ChromaDB with pgvector for RAG. Store document chunks with vector(768) embeddings, support scoped similarity search.

**Independent Test**: Embed theory documents, search for "imperial rent extraction", verify ranked results returned.

### Tests for User Story 7

- [ ] T050 [P] [US7] Write unit tests for PgVectorStore in tests/unit/persistence/test_pgvector_store.py — add_chunks, query_similar, delete_chunks, get_collection_count with mocked psycopg

### Implementation for User Story 7

- [ ] T051 [US7] Implement PgVectorStore in src/babylon/persistence/pgvector_store.py — add_chunks (INSERT with vector embedding), query_similar (SELECT ORDER BY embedding <=> query_vec LIMIT k), delete_chunks, get_collection_count; use HNSW index with cosine distance
- [ ] T052 [US7] Add VectorStoreProtocol support to Retriever in src/babylon/rag/retrieval.py — accept VectorStoreProtocol in __init__ (structural typing, no code change needed if method signatures match), verify Retriever works with PgVectorStore
- [ ] T053 [US7] Add session-scoped search to PgVectorStore in src/babylon/persistence/pgvector_store.py — WHERE clause on session_id when metadata filter includes session scope, NULL session_id for global theory corpus

**Checkpoint**: Semantic search operational via pgvector. ChromaDB replaceable. Session-scoped and global search both work.

______________________________________________________________________

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Migrate legacy observer, validate performance, update exports

- [ ] T054 Migrate SessionRecorder to use RuntimePersistence protocol in src/babylon/engine/observers/session_recorder.py — replace SimulationDB with RuntimePersistence, remove direct SQL, delegate to protocol methods
- [ ] T055 [P] Write performance validation test in tests/integration/test_postgres_integration.py — verify persist_tick < 2s, hydrate_graph < 1s for tri-county Detroit (~1,500 hexes, ~35 nodes, ~55 edges)
- [ ] T056 [P] Verify SQLite RuntimeDatabase still passes all existing tests in tests/unit/persistence/test_runtime_db.py after protocol changes (regression check)
- [ ] T057 Run protocol compliance contract tests (T005) to confirm both RuntimeDatabase and PostgresRuntime satisfy RuntimePersistence
- [ ] T058 Update src/babylon/persistence/__init__.py with final exports — all new types, PostgresRuntime, TraceRecorder, PgVectorStore, archival functions
- [ ] T059 Validate quickstart.md code examples against actual API — run each snippet mentally or as doctest to verify method signatures match implementation

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3-9)**: All depend on Foundational phase completion
  - US1 (P1): Can start after Phase 2 — no dependency on other stories
  - US2 (P1): Can start after Phase 2 — no dependency on US1 (separate tables)
  - US3 (P1): Can start after Phase 2 — no dependency on US1/US2
  - US4 (P2): Can start after Phase 2 — independent (trace subsystem)
  - US5 (P2): Can start after Phase 2 — benefits from US1 hex_state data but independently testable
  - US6 (P3): Depends on US1 (needs data to export) — start after US1 checkpoint
  - US7 (P3): Can start after Phase 2 — independent (vector subsystem)
- **Polish (Phase 10)**: Depends on US1 complete; T054 depends on protocol being stable

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD Red phase)
- Implementation tasks are sequential within the same file
- Integration tests run after implementation (Green phase)
- Commit after each task or logical group

### Parallel Opportunities

- T002, T003 can run in parallel (different conftest files)
- T005, T006, T007, T008 can run in parallel after T004 (different files)
- T011, T012, T013, T014 can run in parallel (test files, all RED phase)
- US2, US3, US4, US5, US7 can all start in parallel after Phase 2
- T043, T044 can run in parallel (different test files)
- T055, T056 can run in parallel (different test targets)

______________________________________________________________________

## Parallel Example: User Story 1

```text
# RED phase — Launch all tests in parallel (all should FAIL):
Task T011: "Unit tests for persist_tick in tests/unit/persistence/test_postgres_runtime.py"
Task T012: "Unit tests for hydrate_graph in tests/unit/persistence/test_postgres_runtime.py"
Task T013: "Unit tests for subsystem persist methods in tests/unit/persistence/test_postgres_runtime.py"
Task T014: "Integration test for persist/hydrate round-trip in tests/integration/test_postgres_integration.py"

# GREEN phase — Implement sequentially (same file):
Task T015 → T016 → T017 → T018 → T019 → T020 → T021 → T022 → T023 → T024 → T025

# VERIFY: Run all tests from RED phase — all should now PASS
```

## Parallel Example: Independent Stories After Phase 2

```text
# These stories can run simultaneously with separate developers/agents:
Agent A: US1 (T011-T025) — Core state persistence (MVP)
Agent B: US4 (T034-T038) — Trace debugging
Agent C: US7 (T050-T053) — Vector search

# After US1 completes:
Agent A: US6 (T043-T049) — Archival pipeline (needs US1 data)
```

______________________________________________________________________

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T010)
3. Complete Phase 3: User Story 1 (T011-T025)
4. **STOP and VALIDATE**: Persist 10 ticks, restart, hydrate, verify zero data loss
5. Deploy/demo if ready — simulation state survives restarts

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 (State Persistence) → Test independently → **MVP!**
3. US2 (Turn Submission) + US3 (Session Management) → Full gameplay loop
4. US4 (Trace Debugging) → Developer tooling
5. US5 (Spatial Queries) → Map visualization support
6. US6 (Archival) + US7 (Semantic Search) → Production readiness
7. Polish → Legacy migration, performance validation

### Task Summary

| Phase | Story | Tasks | Parallel |
|-------|-------|-------|----------|
| 1. Setup | — | 3 | 2 |
| 2. Foundational | — | 7 | 4 |
| 3. US1 State Persistence | P1 MVP | 15 | 4 |
| 4. US2 Turn Submission | P1 | 4 | 1 |
| 5. US3 Session Management | P1 | 4 | 1 |
| 6. US4 Trace Debugging | P2 | 5 | 1 |
| 7. US5 Spatial Queries | P2 | 4 | 1 |
| 8. US6 Archival | P3 | 7 | 2 |
| 9. US7 Semantic Search | P3 | 4 | 1 |
| 10. Polish | — | 6 | 2 |
| **Total** | | **59** | **19** |

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- TDD: Write tests first (RED), implement (GREEN), refactor
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All persist methods use executemany/COPY for bulk performance
- All test mocks use psycopg cursor mock (not real DB) for unit tests
- Integration tests require running Postgres (skip if unavailable)
