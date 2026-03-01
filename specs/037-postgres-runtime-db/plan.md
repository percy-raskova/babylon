# Implementation Plan: Postgres Runtime Database

**Branch**: `037-postgres-runtime-db` | **Date**: 2026-03-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/037-postgres-runtime-db/spec.md`

## Summary

Replace all non-reference runtime storage with PostgreSQL. The current persistence layer consists of two parallel sqlite3-backed implementations (`RuntimeDatabase` and `SimulationDB`) with no formal protocol interface. This feature creates a `RuntimePersistence` protocol, implements `PostgresRuntime` using psycopg 3 for bulk simulation writes, adds Django ORM models for game management, introduces session-partitioned trace logging, spatial queries via PostGIS, vector search via pgvector (replacing ChromaDB), and a Parquet-based archival pipeline to R2. The SQLite reference database and in-memory computation remain unchanged.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: psycopg 3.x + psycopg_pool (bulk simulation writes), Django 5.x (game management ORM), PostGIS (spatial queries on hex geometries), pgvector (semantic search replacing ChromaDB), PyArrow (Parquet export), boto3/s3fs (R2 upload), DuckDB (cross-game analytics over archived Parquet)
**Storage**: PostgreSQL 16+ (runtime state), SQLite (read-only reference `marxist-data-3NF.sqlite`), Cloudflare R2 (archived Parquet files)
**Testing**: pytest (unit, integration, contract tests)
**Target Platform**: Linux VPS (single Postgres instance, localhost connections)
**Project Type**: Single project (extends existing `src/babylon/` package)
**Performance Goals**: <2s persist/tick, <1s hydrate/tick, <500ms semantic search, <20% trace overhead at DEBUG level
**Constraints**: Zero DB I/O during tick computation (Constitution II.6), full snapshots not diffs, session-scoped isolation for all data
**Scale/Scope**: 10 concurrent beta testers, ~1,500 hexes per game, ~125MB active data per 260-tick session, archival to ~15MB Parquet per session

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Rationale |
|-----------|--------|-----------|
| II.2 Primitives vs Derived | PASS | Node/edge state stores full `model_dump()` in JSONB (primitives). Promoted columns (wealth, consciousness, profit_rate) are redundant query accelerators — JSONB blob remains source of truth. |
| II.5 AI Observes, Never Controls | PASS | Persistence layer has no AI interaction. RAG migration replaces ChromaDB backend only — `RagPipeline` interface unchanged. |
| II.6 State is Data, Engine is Transformation | PASS | FR-011 explicitly preserves the no-DB-I/O-during-tick rule. Engine hydrates at tick start, persists after tick end. `WorldState` frozen Pydantic models unchanged. |
| III.1 No Magic Constants | PASS | All sizing estimates derived from measured data (1,500 hexes, 35 nodes, 55 edges per tri-county Detroit). No arbitrary tuning constants introduced. |
| III.4 Data Source Traceability | PASS | SQLite reference DB unchanged. Natural Earth (Feature 036 infrastructure) already approved in constitution v1.8.2. |

No violations detected. No complexity tracking needed.

**Post-Phase 1 Re-check** (2026-03-01): All gates re-confirmed after design artifacts completed. JSONB stores full model_dump() as source of truth (II.2). All contracts enforce persist-after-tick / hydrate-before-tick (II.6). TraceCollector buffers in memory during tick, flushes only after completion. No new data sources introduced.

## Project Structure

### Documentation (this feature)

```text
specs/037-postgres-runtime-db/
├── plan.md              # This file
├── research.md          # Phase 0: codebase analysis + technology decisions
├── data-model.md        # Phase 1: all 21 entity schemas
├── quickstart.md        # Phase 1: usage examples
├── contracts/           # Phase 1: protocol interfaces
│   ├── persistence.py   # RuntimePersistence protocol + PostgresRuntime extensions
│   ├── trace.py         # TraceRecorder observer interface
│   └── vector_store.py  # PgVectorStore protocol (replacing ChromaDB)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/babylon/persistence/
├── __init__.py               # Updated: export protocols + implementations
├── runtime_db.py             # EXISTING: SQLite RuntimeDatabase (kept for dev/test)
├── runtime_schema.py         # EXISTING: SQLite DDL (kept)
├── protocols.py              # NEW: RuntimePersistence protocol definition
├── postgres_runtime.py       # NEW: PostgresRuntime implementation (psycopg 3)
├── postgres_schema.py        # NEW: Postgres DDL for all 20 tables
├── trace_recorder.py         # NEW: TraceRecorder observer (buffered flush)
├── archival.py               # NEW: Parquet export + R2 upload pipeline
└── pgvector_store.py         # NEW: PgVectorStore (VectorStore protocol impl)

src/babylon/engine/
├── services.py               # MODIFIED: Add persistence + tracer fields to ServiceContainer
├── simulation.py             # MODIFIED: Wire PostgresRuntime via ServiceContainer
└── observers/
    └── session_recorder.py   # MODIFIED: Use RuntimePersistence protocol instead of SimulationDB

src/babylon/rag/
└── retrieval.py              # MODIFIED: Add VectorStoreProtocol, PgVectorStore option

tests/
├── unit/persistence/
│   ├── test_protocols.py             # Protocol compliance tests
│   ├── test_postgres_runtime.py      # Unit tests (mocked psycopg)
│   ├── test_trace_recorder.py        # TraceRecorder buffer/flush tests
│   ├── test_archival.py              # Parquet export unit tests
│   └── test_pgvector_store.py        # PgVectorStore unit tests
├── integration/
│   ├── test_postgres_integration.py  # End-to-end persist/hydrate with real Postgres
│   └── test_archival_integration.py  # Full export-upload-query cycle
└── contract/
    └── test_persistence_contracts.py # RuntimePersistence protocol compliance
```

**Structure Decision**: Extends the existing `src/babylon/persistence/` package where `RuntimeDatabase` already lives. New files follow the established protocol + default implementation pattern (e.g., `protocols.py` + `postgres_runtime.py`, mirroring Feature 036's `protocols.py` + concrete implementations). Django models for game management live in a future Django app, not in `src/babylon/persistence/` — the Postgres schema DDL creates the tables, and Django discovers them via `managed = False` or `RunSQL` migrations.

## Key Research Findings

### Current Persistence Architecture

1. **No RuntimePersistence Protocol exists in code** — the spec document defines it but no Python Protocol class has been written. Two parallel sqlite3 implementations exist: `RuntimeDatabase` (has `persist_tick`/`hydrate_graph`) and `SimulationDB` (used by `SessionRecorder`). Neither implements a shared interface.

2. **ServiceContainer has no persistence field** — the `database` field is a SQLAlchemy connection to the reference DB, not runtime persistence. The spec's intent to inject persistence via ServiceContainer is not yet wired.

3. **SessionRecorder uses SimulationDB directly** — it calls raw SQL on `self._db.con`. Migration requires either: (a) make SessionRecorder use RuntimePersistence protocol, or (b) create a new observer that replaces SessionRecorder.

4. **WorldState round-trip loses data** — `from_graph()` excludes computed fields and uses `.get()` defaults for missing fields. Systems write additional attributes (e.g., `edge_mode`, `contradiction_character`) that are silently dropped during reconstruction because `Relationship` has `extra="forbid"`. The JSONB blob in Postgres can preserve these, but the WorldState round-trip remains the bottleneck.

5. **tick_dynamics lives in persistent_context, not WorldState** — stored via `_save_graph_context()`/`_restore_graph_context()` in `simulation_engine.py`, bypassing WorldState serialization entirely. Must be separately persisted.

6. **Community hypergraph is NOT serialized** — `CommunityState` dict lives in `ServiceContainer.community_hypergraph`, rebuilt each tick from node `community_memberships` attributes. Must be separately persisted for cross-tick state (consciousness, legal_status, etc.).

### Infrastructure Topology (Feature 036) Storage

Infrastructure state lives in three standalone managers — NOT graph attributes:
- `DefaultInfrastructureInventory`: edge links, vertices, nonlocal edges (has `to_dict()`/`from_dict()`)
- `DefaultBiocapacityStore`: per-hex stock depletion (mutable `_MutableStock` dataclass)
- `DefaultInternetAccessManager`: per-hex internet state (has `to_dict()`/`from_dict()`)

These have no persistence mechanism today. The `to_dict()`/`from_dict()` methods provide serialization hooks.

### RAG/Vector Store Architecture

- No `VectorStore` Protocol — it's a concrete class wrapping ChromaDB
- Default embedding dimension is **768** (Ollama embeddinggemma), not 1536
- `RagPipeline` is the orchestrator; `VectorStore.add_chunks()` and `VectorStore.query_similar()` are the storage boundary
- Migration requires: (a) create `VectorStoreProtocol`, (b) implement `PgVectorStore`, (c) make `VectorStore` optional/configurable
