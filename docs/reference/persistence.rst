Persistence Layer
=================

Runtime state persistence for the simulation engine.

Module: ``babylon.persistence``

Package Exports
---------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Export
     - Description
   * - ``RuntimePersistence``
     - Protocol for backend-agnostic tick persistence (5 methods)
   * - ``PostgresRuntimeExtensions``
     - Protocol for Postgres-specific subsystem persistence (12 methods)
   * - ``TraceCollector``
     - Protocol for buffered execution trace collection
   * - ``VectorStoreProtocol``
     - Protocol for backend-agnostic vector search
   * - ``TraceLevel``
     - IntEnum controlling trace verbosity
   * - ``PostgresRuntime``
     - PostgreSQL implementation of both persistence protocols
   * - ``RuntimeDatabase``
     - SQLite implementation of ``RuntimePersistence``
   * - ``PgVectorStore``
     - pgvector implementation of ``VectorStoreProtocol``
   * - ``TraceRecorder``
     - Buffered in-memory implementation of ``TraceCollector``
   * - ``RUNTIME_SCHEMA_DDL``
     - SQLite schema DDL statements (from ``runtime_schema``)

Protocols
---------

RuntimePersistence
^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from babylon.persistence.protocols import RuntimePersistence

``@runtime_checkable`` protocol. The simulation engine interacts with storage
exclusively through this interface. Both SQLite and PostgreSQL backends
implement it.

.. list-table::
   :header-rows: 1
   :widths: 40 15 45

   * - Method
     - Returns
     - Description
   * - ``persist_tick(tick, graph, events=None, *, session_id=None)``
     - ``None``
     - Full graph snapshot at tick. Idempotent via UPSERT.
   * - ``hydrate_graph(tick=None, *, session_id=None)``
     - ``nx.DiGraph[str]``
     - Load state snapshot. ``None`` tick loads latest.
   * - ``log_tick(tick, rng_state=None, mutations=None, invariant_checks=None, wall_time_ms=None, system_timings=None, *, session_id=None)``
     - ``None``
     - Record tick replay metadata (RNG state, timings).
   * - ``set_metadata(key, value)``
     - ``None``
     - Store key-value metadata pair.
   * - ``get_metadata(key)``
     - ``str | None``
     - Retrieve metadata value by key.

**Implementations**: ``RuntimeDatabase`` (SQLite), ``PostgresRuntime`` (PostgreSQL).

PostgresRuntimeExtensions
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from babylon.persistence.protocols import PostgresRuntimeExtensions

``@runtime_checkable`` protocol for subsystem state added by Features 002,
022, 029, 032, and 036. ``PersistenceObserver`` accesses these via
``isinstance()`` check.

.. list-table::
   :header-rows: 1
   :widths: 45 15 40

   * - Method
     - Returns
     - Description
   * - ``persist_graph_metadata(tick, economy, state_finances, tick_dynamics, *, session_id)``
     - ``None``
     - Graph-level metadata (economy, state finances, tick dynamics).
   * - ``persist_community_state(tick, community_states, memberships, *, session_id)``
     - ``None``
     - Hypergraph community state and membership records.
   * - ``hydrate_community_state(tick, *, session_id)``
     - ``tuple[dict, list]``
     - Load community state and memberships at tick.
   * - ``persist_hex_state(tick, hex_states, *, session_id)``
     - ``None``
     - Per-hex economic state. Bulk insert ~1,500 rows.
   * - ``persist_infrastructure_state(tick, terrain_states, link_states, *, session_id)``
     - ``None``
     - Feature 036 infrastructure topology state.
   * - ``persist_contradiction_fields(tick, fields, curvatures, *, session_id)``
     - ``None``
     - Feature 002 contradiction field values and edge curvatures.
   * - ``persist_action_results(tick, results, *, session_id)``
     - ``None``
     - OODA action resolution outcomes (Feature 032).
   * - ``persist_tick_summary(tick, summary, *, session_id)``
     - ``None``
     - Pre-aggregated tick summary for time-series endpoints.
   * - ``persist_traces(session_id, tick, trace_events)``
     - ``None``
     - Bulk insert trace events to ``trace_log``.
   * - ``create_session_partition(session_id)``
     - ``None``
     - Create ``trace_log`` partition for a new session.
   * - ``drop_session_partition(session_id)``
     - ``None``
     - Drop ``trace_log`` partition for a completed session.
   * - ``export_session_to_parquet(session_id, output_dir)``
     - ``list[str]``
     - Export session data to Parquet files.

**Implementation**: ``PostgresRuntime`` only.

TraceCollector
^^^^^^^^^^^^^^

.. code-block:: python

   from babylon.persistence.protocols import TraceCollector

``@runtime_checkable`` protocol for execution trace collection. Systems
call ``trace()`` during tick computation (in-memory buffer, no I/O).
``flush()`` writes buffered events to storage after tick completion.

.. list-table::
   :header-rows: 1
   :widths: 45 15 40

   * - Method / Property
     - Returns
     - Description
   * - ``trace(system, event, data, *, level=TraceLevel.DEBUG, node_id=None)``
     - ``None``
     - Buffer a trace event (no I/O).
   * - ``flush(session_id, tick)``
     - ``None``
     - Write buffered events to storage and clear buffer.
   * - ``level`` *(property)*
     - ``TraceLevel``
     - Configured verbosity level.
   * - ``buffer_size`` *(property)*
     - ``int``
     - Number of events currently buffered.

**Implementation**: ``TraceRecorder``.

VectorStoreProtocol
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from babylon.persistence.protocols import VectorStoreProtocol

``@runtime_checkable`` protocol for semantic search. The ``Retriever``
interacts with vector storage only through this interface.

.. list-table::
   :header-rows: 1
   :widths: 45 15 40

   * - Method
     - Returns
     - Description
   * - ``add_chunks(chunks)``
     - ``None``
     - Store document chunks with embeddings.
   * - ``query_similar(query_embedding, k=10, where=None, include=None)``
     - ``tuple[list, list, list, list, list]``
     - Find *k* most similar chunks. Returns (ids, documents, embeddings, metadatas, distances).
   * - ``delete_chunks(chunk_ids)``
     - ``None``
     - Delete chunks by ID.
   * - ``get_collection_count()``
     - ``int``
     - Total number of chunks in the store.

**Implementations**: ``VectorStore`` (ChromaDB, existing), ``PgVectorStore`` (pgvector).

TraceLevel
^^^^^^^^^^

.. code-block:: python

   from babylon.persistence.protocols import TraceLevel

``IntEnum`` controlling trace verbosity. Each level includes everything below it.

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Name
     - Value
     - Description
   * - ``NONE``
     - 0
     - Tracing disabled. ``trace()`` is a no-op.
   * - ``SUMMARY``
     - 1
     - High-level tick summaries only.
   * - ``DEBUG``
     - 2
     - Detailed system-level events.
   * - ``TRACE``
     - 3
     - Full per-node event logging.

Concrete Implementations
------------------------

PostgresRuntime
^^^^^^^^^^^^^^^

.. code-block:: python

   from psycopg_pool import ConnectionPool
   from babylon.persistence import PostgresRuntime

   pool = ConnectionPool(conninfo="dbname=babylon")
   with PostgresRuntime(pool) as pg:
       pg.init_schema()
       pg.persist_tick(tick=0, graph=graph, session_id=session_id)

**Constructor**: ``PostgresRuntime(pool: ConnectionPool[Connection[Any]])``

**Context manager**: ``__enter__`` / ``__exit__`` (calls ``close()``).

**Additional methods**:

- ``init_schema()`` — Execute all DDL statements. Safe to call multiple times
  (uses ``IF NOT EXISTS``).
- ``close()`` — Close the connection pool.
- ``pool`` *(property)* — The underlying ``ConnectionPool`` instance.

**Implements**: ``RuntimePersistence`` + ``PostgresRuntimeExtensions``.

Uses ``psycopg`` 3 with ``executemany()`` for bulk writes. Batch size
capped at 1,000 rows per ``executemany`` call.

RuntimeDatabase
^^^^^^^^^^^^^^^

.. code-block:: python

   from babylon.persistence import RuntimeDatabase

   # In-memory for tests
   with RuntimeDatabase(in_memory=True) as db:
       db.persist_tick(tick=0, graph=graph)

   # File-based
   with RuntimeDatabase(run_id="experiment_001") as db:
       graph = db.hydrate_graph(tick=5)

**Constructor**: ``RuntimeDatabase(run_id: str | None = None, in_memory: bool = False)``

- ``run_id`` defaults to a timestamp-based ID.
- ``in_memory=True`` uses ``:memory:`` SQLite database.
- File-based databases are stored in ``data/runs/{run_id}.sqlite``.

**Context manager**: ``__enter__`` / ``__exit__`` (calls ``close()``).

**Additional methods** (beyond ``RuntimePersistence``):

- ``get_events(tick=None)`` — Retrieve events for a tick or all events.
- ``record_tick_summary(tick, total_c, total_v, total_s,
  avg_consciousness, uprising_count)`` — Record aggregate metrics
  (legacy ``SimulationDB`` compatible).
- ``get_tick_log(tick)`` — Retrieve tick log for replay.
- ``transaction()`` — Context manager for explicit transactions.

**Implements**: ``RuntimePersistence`` only.

PgVectorStore
^^^^^^^^^^^^^

.. code-block:: python

   from psycopg_pool import ConnectionPool
   from babylon.persistence import PgVectorStore

   pool = ConnectionPool(conninfo="dbname=babylon")
   store = PgVectorStore(pool, dimension=768)
   store.add_chunks(chunks)
   ids, docs, embeddings, metadatas, distances = store.query_similar(
       query_embedding=embedding, k=5
   )

**Constructor**:
``PgVectorStore(pool: ConnectionPool[Connection[Any]],``
``dimension: int = 1536, collection: str = "default")``

- ``dimension``: Embedding vector dimension. The ``document_chunk`` schema
  defines ``vector(768)`` for Ollama embeddinggemma.
- ``collection``: Logical namespace for multi-tenant isolation.

Uses HNSW index with cosine distance (``<=>`` operator) for approximate
nearest neighbor search. Metadata filtering via JSONB containment (``@>``).

**Implements**: ``VectorStoreProtocol``.

TraceRecorder
^^^^^^^^^^^^^

.. code-block:: python

   from babylon.persistence import TraceRecorder
   from babylon.persistence.protocols import TraceLevel

   recorder = TraceRecorder(level=TraceLevel.DEBUG, persistence=pg_runtime)

   # During tick (in-memory only):
   recorder.trace("ImperialRentSystem", "formula_eval", {"rent": 42.0})

   # After tick (flushes to DB):
   recorder.flush(session_id=session_id, tick=0)

**Constructor**: ``TraceRecorder(level: TraceLevel = TraceLevel.NONE, persistence: Any = None)``

- When ``level`` is ``NONE``, ``trace()`` is a no-op.
- When ``persistence`` is ``None``, ``flush()`` clears the buffer without
  writing.
- ``persistence`` should implement ``PostgresRuntimeExtensions.persist_traces()``.

**Implements**: ``TraceCollector``.

PersistenceObserver
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from babylon.engine.observers.persistence_observer import PersistenceObserver

   observer = PersistenceObserver(
       persistence=postgres_runtime,
       session_id=session_id,
       tracer=trace_recorder,
   )
   simulation.attach_observer(observer)

**Module**: ``babylon.engine.observers.persistence_observer``

**Constructor**:
``PersistenceObserver(persistence: RuntimePersistence,``
``session_id: UUID, tracer: TraceCollector | None = None)``

**Implements**: ``SimulationObserver`` protocol.

**Lifecycle**:

1. ``on_simulation_start(initial_state, config)`` — Stores config as metadata,
   persists initial state (tick 0).
2. ``on_tick(previous_state, new_state)`` — Calls ``persist_tick()`` on the
   ``RuntimePersistence`` backend. If the backend also implements
   ``PostgresRuntimeExtensions``, calls ``persist_graph_metadata()`` and
   other extended methods. Flushes tracer after each tick.
3. ``on_simulation_end(final_state)`` — Sets ``end_tick`` and ``status``
   metadata. Flushes any remaining trace events.

Database Schema (Summary)
-------------------------

19 PostgreSQL tables across 6 layers. Full DDL in
``babylon.persistence.postgres_schema.POSTGRES_SCHEMA_DDL``.

.. list-table::
   :header-rows: 1
   :widths: 25 30 45

   * - Layer
     - Tables
     - Purpose
   * - Game Management (3)
     - ``game_session``, ``game_turn``, ``action_result``
     - Session lifecycle, player turns, OODA action outcomes
   * - Simulation State (10)
     - ``node_state``, ``edge_state``, ``graph_metadata``, ``community_state``, ``community_membership``, ``contradiction_field``, ``edge_curvature``, ``simulation_event``, ``tick_log``, ``tick_summary``
     - Full graph snapshots, community hypergraph, contradiction fields, events, replay metadata, aggregated summaries
   * - Spatial (3)
     - ``hex_cell``, ``hex_state``, ``hex_terrain_state``
     - H3 hex geometries (PostGIS), per-hex economic and terrain state
   * - Infrastructure (1)
     - ``infrastructure_link_state``
     - Per-edge infrastructure capacity and condition
   * - Trace (1)
     - ``trace_log``
     - Execution trace events (UNLOGGED, partitioned by ``session_id``)
   * - Semantic (1)
     - ``document_chunk``
     - Document embeddings for vector search (pgvector)

All data tables use composite primary keys of ``(session_id, tick, entity_id)``
for session-scoped temporal isolation. ``game_session`` uses UUID PK.
``trace_log`` uses ``BIGSERIAL`` within each partition.

Required PostgreSQL extensions: ``postgis``, ``vector`` (pgvector),
``uuid-ossp``.

Archival Pipeline (Stubs)
-------------------------

Four functions in ``babylon.persistence.archival``. All raise
``NotImplementedError`` (Phase 8, tasks T045-T048).

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Function
     - Description
   * - ``export_session_to_parquet(pool, session_id, output_dir)``
     - Export session data to Parquet files via PyArrow.
   * - ``upload_to_r2(parquet_paths, bucket, prefix="")``
     - Upload Parquet files to Cloudflare R2.
   * - ``purge_session(pool, session_id)``
     - Delete session data from Postgres after verified export.
   * - ``query_archived_session(parquet_path, query)``
     - Query archived session data via DuckDB.

See Also
--------

- :doc:`/concepts/persistence-architecture` — Design rationale for the persistence layer
- :doc:`/concepts/architecture` — Embedded Trinity architecture overview
