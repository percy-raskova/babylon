# Research: Postgres Runtime Database

**Feature**: 037-postgres-runtime-db
**Date**: 2026-03-01

## Decision 1: RuntimePersistence Protocol Design

**Decision**: Create a new `RuntimePersistence` Protocol in `src/babylon/persistence/protocols.py` that unifies the `RuntimeDatabase` and `SimulationDB` interfaces.

**Rationale**: Currently two parallel sqlite3 implementations exist with no shared interface. `RuntimeDatabase` has `persist_tick`/`hydrate_graph` (ADR030 pattern). `SimulationDB` is used by `SessionRecorder` with raw SQL inserts. Neither implements a Protocol. The Postgres spec's intent — "the Simulation class receives a persistence handle via ServiceContainer; it doesn't know or care which backend" — requires a formal Protocol.

**Alternatives considered**:
- Extend `RuntimeDatabase` with ABC: Rejected — ABC forces inheritance rather than structural typing, violating the project's Protocol + default impl pattern.
- Create PostgresRuntime without protocol: Rejected — would couple the engine to Postgres, preventing local dev with SQLite.

## Decision 2: Dual Connection Architecture

**Decision**: Django ORM handles game management tables (`auth_user`, `game_session`, `game_turn`) via `django.db.backends.postgresql`. A separate `psycopg_pool.ConnectionPool` handles bulk simulation writes via raw SQL.

**Rationale**: The simulation persists ~1,900 rows per tick (1,500 hex + 200 membership + 35 nodes + 55 edges + 80 contradiction + 14 community + metadata). Django ORM overhead (object creation, signal dispatch, individual INSERTs) is unacceptable for this volume. `psycopg` 3 with `executemany()` and `COPY` protocol provides 5-10x throughput for bulk operations. Same database, same credentials, separate connection pools.

**Alternatives considered**:
- Django ORM for everything: Rejected — ORM overhead on 1,500+ hex rows per tick is prohibitive.
- psycopg for everything: Rejected — Django needs ORM for auth, sessions, admin, and API endpoints.
- Two databases: Rejected — cross-database FKs require `dblink`/`postgres_fdw`, adding fragility.

## Decision 3: JSONB + Promoted Columns

**Decision**: Node and edge state store full `model_dump()` in a JSONB `attributes` column, with frequently-queried scalars promoted to indexed columns alongside.

**Rationale**: The engine writes full attribute blobs via `model_dump()`. Promoted columns (wealth, consciousness, org_type, profit_rate) provide indexed access for analytical queries without parsing JSONB. The JSONB blob remains source of truth — promoted columns are redundant accelerators. This matches Constitution II.2 (store primitives, compute derived).

**Alternatives considered**:
- Fully normalized columns: Rejected — 4 node types with 15-30 fields each would require either one massive table or 4 separate tables with type-specific columns. JSONB handles the polymorphism naturally.
- JSONB only (no promoted columns): Rejected — GIN index on JSONB handles containment queries but not range scans on numeric fields needed for analytical queries.

## Decision 4: Session-Partitioned Trace Logging

**Decision**: `trace_log` is an UNLOGGED table partitioned by `session_id`. Each traced session gets its own partition. Partition drop is instant cleanup.

**Rationale**: Trace data has different durability requirements than game state — loss is acceptable (games are deterministically replayable from RNG seed). UNLOGGED tables skip WAL writes, providing 5-10x faster bulk inserts. Partition-per-session enables instant cleanup via `DROP TABLE partition_name` with zero dead tuples and no VACUUM.

**Alternatives considered**:
- Regular logged table: Rejected — WAL overhead for potentially 2,000 trace rows/tick at TRACE level is wasteful for ephemeral debugging data.
- Application-level file logging: Rejected — loses queryability. The ability to query traces with SQL (e.g., "why did profit_rate spike at tick 47?") is the key value proposition.
- Separate trace database: Rejected — adds operational complexity for negligible benefit at beta scale.

## Decision 5: Infrastructure Topology Persistence

**Decision**: Add three new tables: `terrain_biocapacity_state` (per-hex terrain + biocapacity), `infrastructure_link_state` (per-edge links), `internet_access_state` (per-hex internet). Use the existing `to_dict()`/`from_dict()` serialization methods on Feature 036 managers.

**Rationale**: Feature 036's infrastructure state is stored in three standalone manager objects (`DefaultInfrastructureInventory`, `DefaultBiocapacityStore`, `DefaultInternetAccessManager`), not as graph node/edge attributes. These managers already have `to_dict()`/`from_dict()` methods for snapshot serialization. Persisting to dedicated tables (not JSONB blobs) enables spatial and analytical queries on infrastructure state.

**Alternatives considered**:
- Store as JSONB on node_state/edge_state: Rejected — infrastructure managers are not part of the graph. Their data structures don't map to node types. The clarification session explicitly chose dedicated entities (Option B).
- Single `infrastructure_state` catch-all table: Rejected — three distinct data shapes (per-hex terrain, per-edge links, per-hex internet) with different query patterns warrant separate tables.

## Decision 6: Vector Store Migration

**Decision**: Create `PgVectorStore` implementing a new `VectorStoreProtocol`. Replace ChromaDB with pgvector HNSW index on `vector(768)` columns. The `RagPipeline` interface remains unchanged.

**Rationale**: The current `VectorStore` is a concrete class wrapping ChromaDB with no protocol interface. Creating a `VectorStoreProtocol` enables backend-agnostic vector search. pgvector in the same Postgres instance eliminates the ChromaDB dependency and persistence directory. Default embedding dimension is 768 (Ollama embeddinggemma), not 1536 as originally assumed. The `Embeddable` protocol and `DocumentChunk` model remain unchanged.

**Alternatives considered**:
- Keep ChromaDB: Rejected — adds a second persistence system (file-based) alongside Postgres. Consolidation reduces operational complexity.
- Use sqlite-vss: Rejected — SQLite stays read-only for reference data. Adding vector search to SQLite violates the separation.
- Use FAISS: Rejected — in-memory only, no persistence. Would need separate serialization.

## Decision 7: Archival Pipeline Design

**Decision**: Background job (Django management command) exports completed sessions to Parquet via PyArrow, uploads to R2 via boto3 S3 interface, verifies checksums, then purges from Postgres. DuckDB queries archived Parquet directly from R2.

**Rationale**: Parquet provides 8-10x compression with columnar layout ideal for analytical queries. R2 has zero egress fees. DuckDB reads Parquet natively from S3-compatible storage — no ETL or import step. The management command approach integrates with Django's existing task infrastructure.

**Alternatives considered**:
- Celery worker: Rejected — adds dependency for a simple periodic job. Django management command + cron is sufficient at beta scale.
- Keep data in Postgres indefinitely: Rejected — unbounded growth (~125MB per completed game). At 1,000 games that's 125GB.
- Delete without archival: Rejected — loses cross-game analytical capability, the "divine omens from tea leaves" workflow.

## Decision 8: Embedding Dimension

**Decision**: Use `vector(768)` for the `document_chunk.embedding` column, matching the default Ollama embeddinggemma model. Make dimension configurable at migration time.

**Rationale**: The codebase defaults to `embeddinggemma:latest` (768 dimensions) via Ollama, not OpenAI (1536). The source spec assumed 1536 but that's incorrect for the current setup. The dimension should be defined once in migration SQL and referenced by the `PgVectorStore` implementation.

**Alternatives considered**:
- Hardcode 1536 for future OpenAI compatibility: Rejected — wastes 2x storage for unused dimensions. Dimension change is a simple migration.
- Dynamic dimension per collection: Rejected — pgvector requires fixed dimension per column. Different models would need separate columns or tables.
