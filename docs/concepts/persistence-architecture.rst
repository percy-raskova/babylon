Persistence Architecture
========================

A simulation engine that cannot recover from crashes, isolate concurrent
sessions, or answer analytical queries about past runs is a toy. The
persistence layer exists to turn the simulation into a reliable system
by recording every tick's state in a form that survives process death
and supports structured queries.

Why Two Backends?
-----------------

The persistence layer supports two storage backends behind a single
``RuntimePersistence`` protocol:

**SQLite** (``RuntimeDatabase``): Zero configuration, in-memory option,
no external dependencies. A developer clones the repository and runs
tests without installing PostgreSQL. CI pipelines use in-memory SQLite
for speed. The cost is limited functionality: SQLite implements only
the 5-method ``RuntimePersistence`` protocol — no community state, no
spatial queries, no trace partitioning.

**PostgreSQL** (``PostgresRuntime``): Concurrent session support, PostGIS
spatial queries, pgvector semantic search, JSONB analytical queries, and
native table partitioning. PostgreSQL implements ``RuntimePersistence``
(5 methods) plus ``PostgresRuntimeExtensions`` (12 additional methods)
for subsystem state added by Features 002, 022, 029, 032, and 036.

The protocol boundary means the simulation engine never knows which
backend is active. ``PersistenceObserver`` receives a ``RuntimePersistence``
handle at construction time. It calls the 5 base methods unconditionally,
then uses ``isinstance(persistence, PostgresRuntimeExtensions)`` to call
extended methods when the backend supports them.

This is not a leaky abstraction — SQLite genuinely cannot persist
community hypergraph state or contradiction fields. The protocol
boundary makes this explicit rather than hiding it behind silent no-ops
or feature flags.

The Protocol Boundary
---------------------

Constitution II.6 mandates zero database I/O during tick computation.
All seven simulation systems read and write graph node attributes in
memory. Persistence happens *after* the tick completes, triggered by
the ``PersistenceObserver``.

The sequence per tick:

1. ``SimulationEngine.run_tick()`` mutates the graph in memory.
2. ``WorldState.from_graph()`` validates the result.
3. Observer dispatch calls ``PersistenceObserver.on_tick()``.
4. ``on_tick()`` calls ``persist_tick()`` on the backend.
5. If the backend implements ``PostgresRuntimeExtensions``,
   extended persist methods are called.
6. ``TraceRecorder.flush()`` writes buffered trace events.

The protocol uses structural typing (``typing.Protocol``) rather than
abstract base classes. ``RuntimeDatabase`` satisfies ``RuntimePersistence``
without inheriting from it — it simply has methods with matching
signatures. This follows the project's established pattern of Protocol
plus default implementation, as used throughout the economics modules.

Session-Scoped Isolation
------------------------

Every row in the PostgreSQL schema is keyed by ``(session_id, tick,
entity_id)``. Multiple concurrent simulations share one PostgreSQL
instance without interference. Each session gets its own UUID,
and all queries are scoped by it.

The SQLite backend ignores ``session_id`` parameters (they are accepted
for protocol compatibility but unused). SQLite databases are inherently
single-session: one file per simulation run.

Trace logging uses PostgreSQL native list partitioning on ``session_id``.
Each traced session gets its own partition table. This enables instant
cleanup: ``DROP TABLE trace_log_{session_hex}`` removes all trace data
for a session with zero dead tuples and no ``VACUUM`` required.

Three-Database Topology
-----------------------

The system uses three distinct database roles, each with different
access patterns:

**DuckDB** (``data/duckdb/marxist-data-3NF.duckdb``): Empirical research
data — Census ACS, FRED economic indicators, BEA input-output tables,
QCEW employment data, HIFLD infrastructure, BTS freight flows. Read-only
during simulation. Feeds county-level parameter initialization.

**SQLite or PostgreSQL**: Runtime simulation state — graph snapshots,
events, tick logs, community state, spatial hex data, contradiction
fields. Read-write every tick. The active backend depends on deployment
context (SQLite for dev/test, PostgreSQL for production).

**Cloudflare R2** (planned): Archived Parquet files exported from
completed sessions. Write-once, read via DuckDB's native Parquet reader
for cross-game analytics. The archival pipeline
(``babylon.persistence.archival``) is currently stubbed.

These three roles never overlap. DuckDB does not store simulation state.
The runtime database does not store empirical research data. R2 stores
only completed, exported sessions.

UPSERT Semantics and Idempotency
---------------------------------

Every persist method uses ``ON CONFLICT DO UPDATE`` (PostgreSQL) or
``INSERT OR REPLACE`` (SQLite). Persisting the same tick twice produces
the same result as persisting it once.

This matters for crash recovery. If the process dies between persisting
node state and edge state for tick *n*, restarting the simulation can
re-persist tick *n* from the in-memory graph without checking what was
already written. The UPSERT overwrites any partial state from the
interrupted persist.

The alternative — checking which rows exist before inserting — would
require read-before-write logic that contradicts the write-only nature
of the persist path.

Trace Logging and Observability
-------------------------------

``TraceRecorder`` buffers structured events in a Python list during tick
computation. No database I/O occurs during the tick. After the tick
completes, ``flush()`` writes the buffer to the ``trace_log`` table in
a single ``executemany`` call, then clears the buffer.

``TraceLevel`` controls verbosity:

- ``NONE`` (0): Tracing disabled. ``trace()`` is a no-op.
- ``SUMMARY`` (1): High-level tick summaries.
- ``DEBUG`` (2): Detailed system-level events.
- ``TRACE`` (3): Full per-node event logging.

The ``trace_log`` table is ``UNLOGGED`` — PostgreSQL skips WAL writes
for it. This provides faster bulk inserts at the cost of durability:
trace data is lost on crash. This is an acceptable trade-off because
simulations are deterministically replayable from their RNG seed. Trace
data is ephemeral debugging output, not source of truth.

Vector Search Migration
-----------------------

The existing ``VectorStore`` wraps ChromaDB as a concrete class with no
protocol interface. Feature 037 introduces ``VectorStoreProtocol`` as a
formal contract and ``PgVectorStore`` as a PostgreSQL-native
implementation using the pgvector extension.

``PgVectorStore`` stores document embeddings in the ``document_chunk``
table with an HNSW index using cosine distance (the ``<=>`` operator).
The schema defines ``vector(768)`` columns matching the default Ollama
embeddinggemma model dimension.

Both ChromaDB and pgvector implement the same 4-method protocol
(``add_chunks``, ``query_similar``, ``delete_chunks``,
``get_collection_count``). The ``Retriever`` is backend-agnostic — it
interacts only through ``VectorStoreProtocol``.

The motivation for pgvector over ChromaDB: colocation with simulation
data in the same PostgreSQL instance eliminates a separate persistence
system, reduces operational complexity, and enables SQL joins between
vector search results and simulation state.

See Also
--------

- :doc:`/reference/persistence` — Persistence API reference
- :doc:`/concepts/architecture` — Embedded Trinity architecture overview
