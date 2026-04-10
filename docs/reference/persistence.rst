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

23 PostgreSQL tables and views across 9 layers. Full DDL in
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
     - ``hex_cell``, ``hex_map``, ``hex_terrain_state``
     - H3 hex geometries (PostGIS), county-to-hex mapping, per-hex terrain
   * - Snapshot (4)
     - ``territory_snapshot``, ``hex_activity``, ``economic_summary``, ``tick_event``
     - Append-only per-tick journals for county economics, sparse hex events, aggregates, and events
   * - Hex Cache (2)
     - ``hex_latest``, ``hex_substrate``
     - Denormalized R7 frontend cache and static R8 terrain/infrastructure
   * - Composition Views (5)
     - ``v_hex_economic``, ``v_hex_mobilize``, ``v_hex_heat``, ``v_hex_aid``, ``v_hex_intel``
     - Column projections from ``hex_latest`` for frontend map layers
   * - Infrastructure (1)
     - ``infrastructure_link_state``
     - Per-edge infrastructure capacity and condition
   * - Trace (1)
     - ``trace_log``
     - Execution trace events (UNLOGGED, partitioned by ``session_id``)
   * - Semantic (1)
     - ``document_chunk``
     - Document embeddings for vector search (pgvector)

All snapshot tables use composite primary keys of ``(game_id, tick, entity_id)``
for session-scoped temporal isolation. ``game_session`` uses UUID PK.
``hex_latest`` uses ``(game_id, h3_index)`` PK (current state only).

Required PostgreSQL extensions: ``postgis``, ``vector`` (pgvector),
``uuid-ossp``.

Multi-Resolution Hex Journal (Feature 037)
------------------------------------------

The multi-resolution hex journal is a tiered persistence architecture
optimized for national-scale simulation at H3 resolution 7 (~243K hexes
for CONUS). It achieves a **305× storage reduction** compared to flat
per-hex per-tick snapshots.

Architecture
^^^^^^^^^^^^

Four tables at three resolution tiers:

.. list-table::
   :header-rows: 1
   :widths: 20 15 20 45

   * - Table
     - Resolution
     - Cardinality
     - Purpose
   * - ``territory_snapshot``
     - County
     - ~3,100 rows/tick
     - Economic state (ValueTensor4x3, profit rate, class distribution)
   * - ``hex_activity``
     - R7 (sparse)
     - ~5K rows/tick
     - Heat, organizations, player/AI actions (only hexes with events)
   * - ``hex_substrate``
     - R8 (static)
     - ~1.7M rows (once)
     - Terrain, water, broadband, surveillance (written at init)
   * - ``hex_latest``
     - R7 (all)
     - ~243K rows (current)
     - Denormalized cache merging all tiers for frontend O(1) reads

Data Flow
^^^^^^^^^

::

    territory_snapshot ──► Phase 1: Broadcast ──► hex_latest ──► Frontend
    hex_activity ──────► Phase 2: Overlay ───┘
    hex_substrate ─────► Aggregated at init ─┘

**Write path** (each tick):

1. Systems write ``territory_snapshot`` (~3,100 rows) and ``hex_activity``
   (sparse, ~5K rows).
2. ``refresh_hex_latest()`` runs two SQL UPDATEs to synchronize the cache.

**Read path** (frontend): ``SELECT`` from ``hex_latest`` or composition
views. No JOINs required.

refresh_hex_latest (Two-Phase UPSERT)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   pg.refresh_hex_latest(game_id=game_id, tick=tick)

**Phase 1 — Territory broadcast** (~20ms for 243K hexes):
   ``UPDATE hex_latest FROM territory_snapshot JOIN hex_map``.
   All hexes in a county receive identical economic values.

**Phase 2 — Hex activity overlay** (~0.5ms for ~5K sparse rows):
   ``UPDATE hex_latest FROM hex_activity`` for heat, org, and action
   fields. Only hexes with activity this tick are touched.

seed_hex_latest (Tick-0 ETL)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from babylon.persistence.hex_init import seed_hex_latest

   inserted = seed_hex_latest(pool, game_id)  # After territory_snapshot + hex_map init

``INSERT...SELECT`` that JOINs ``territory_snapshot`` (tick 0),
``hex_map``, and optionally ``hex_substrate`` (R8 terrain via
``MODE()``, ``AVG()``, ``BOOL_OR()`` aggregation).

reconstruct_hex_state (Historical Queries)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   rows = pg.reconstruct_hex_state(game_id=game_id, tick=42)

Reconstructs any past tick by JOINing the append-only
``territory_snapshot`` and ``hex_activity`` journals via ``hex_map``.
Uses ``LATERAL`` join for efficient sparse event lookup. Returns a
list of per-hex dicts with economic, demographic, and activity fields.

.. note::

   ``hex_latest`` only holds the current tick. For historical or
   time-series analysis, always use ``reconstruct_hex_state()``.

Composition Views
^^^^^^^^^^^^^^^^^

Five views project subsets of ``hex_latest`` columns for frontend map
layers. All are trivial ``SELECT`` projections — no JOINs.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - View
     - Columns
   * - ``v_hex_economic``
     - profit_rate, exploitation_rate, occ, imperial_rent, pop_total, heat
   * - ``v_hex_mobilize``
     - mobilizable_pop, org_presence, hex_heat, dominant_class
   * - ``v_hex_heat``
     - heat, heat_delta, org_count (filtered: heat > 0)
   * - ``v_hex_aid``
     - internet_access, terrain_type, water_coverage
   * - ``v_hex_intel``
     - faction_*, dominant_class, org_count, actions_taken

Storage Budget
^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 25 20 20 35

   * - Component
     - Rows / tick
     - Bytes / tick
     - 260 ticks (10-year sim)
   * - ``territory_snapshot``
     - 3,100
     - ~770 KB
     - ~200 MB
   * - ``hex_activity``
     - ~5,000
     - ~200 KB
     - ~52 MB
   * - ``hex_substrate`` (once)
     - 1,700,000
     - ~300 MB
     - 300 MB (fixed)
   * - ``hex_latest`` (once)
     - 243,000
     - ~30 MB
     - 30 MB (fixed)
   * - **Total**
     -
     -
     - **~582 MB / session**

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
