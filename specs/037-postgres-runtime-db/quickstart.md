# Quickstart: Postgres Runtime Database

**Feature**: 037-postgres-runtime-db
**Date**: 2026-03-01

## Prerequisites

- PostgreSQL 16+ with extensions: `pgvector`, `postgis`
- Python packages: `psycopg[binary]`, `psycopg_pool`, `pyarrow`

## 1. Protocol-Based Persistence (RuntimePersistence)

The engine interacts with persistence through protocols only.

```python
from babylon.persistence.protocols import RuntimePersistence
from babylon.engine.services import ServiceContainer

# ServiceContainer provides the persistence handle
container = ServiceContainer(
    persistence=postgres_runtime,  # or sqlite_runtime for dev/test
    # ... other services
)

# Persist after tick completes (Constitution II.6: no I/O during tick)
container.persistence.persist_tick(
    tick=current_tick,
    graph=graph,
    events=tick_events,
    session_id=session.id,
)

# Hydrate before tick starts
graph = container.persistence.hydrate_graph(
    tick=last_tick,
    session_id=session.id,
)
```

## 2. PostgresRuntime Initialization

```python
from babylon.persistence.postgres_runtime import PostgresRuntime

runtime = PostgresRuntime(
    dsn="postgresql://babylon:secret@localhost:5432/babylon",
    pool_min=2,
    pool_max=10,
)

# Persist full simulation state (called by Simulation after each tick)
runtime.persist_tick(tick=42, graph=graph, session_id=session_id)

# Extended methods for subsystem state
runtime.persist_graph_metadata(
    tick=42,
    economy=global_economy.model_dump(),
    state_finances={sid: sf.model_dump() for sid, sf in finances.items()},
    tick_dynamics=tick_dynamics_dict,
    session_id=session_id,
)

runtime.persist_community_state(
    tick=42,
    community_states=community_dict,
    memberships=membership_list,
    session_id=session_id,
)

runtime.persist_hex_state(
    tick=42,
    hex_states=[h.model_dump() for h in hex_economic_states],
    session_id=session_id,
)

runtime.persist_infrastructure_state(
    tick=42,
    terrain_states=terrain_dicts,
    link_states=link_dicts,
    session_id=session_id,
)

runtime.persist_contradiction_fields(
    tick=42,
    fields=field_value_dicts,
    curvatures=curvature_dicts,
    session_id=session_id,
)
```

## 3. Trace Logging

```python
from babylon.persistence.trace_recorder import TraceRecorder
from babylon.persistence.protocols import TraceLevel

# Create recorder with desired verbosity
tracer = TraceRecorder(
    persistence=runtime,
    level=TraceLevel.DEBUG,
)

# During tick computation: buffer events in memory (no I/O)
tracer.trace(
    system="ImperialRentSystem",
    event="formula_eval",
    data={"node": "proletariat_wayne", "phi": 0.35, "wages": 100.0},
    level=TraceLevel.DEBUG,
)

# After tick completes: flush to Postgres
tracer.flush(session_id=session_id, tick=42)

# Monitor buffer size
print(f"Buffered events: {tracer.buffer_size}")
```

## 4. Vector Store (pgvector)

```python
from babylon.persistence.pgvector_store import PgVectorStore

store = PgVectorStore(
    dsn="postgresql://babylon:secret@localhost:5432/babylon",
)

# Add document chunks (same interface as ChromaDB VectorStore)
store.add_chunks(chunks)  # list of Embeddable objects with embeddings

# Semantic search
ids, docs, embeddings, metadatas, distances = store.query_similar(
    query_embedding=query_vec,
    k=10,
    where={"session_id": str(session_id)},
)

# Collection stats
count = store.get_collection_count()
```

## 5. Session Lifecycle

```python
# Create session with trace partition
runtime.create_session_partition(session_id)

# ... run game (persist_tick each tick) ...

# Export completed session to Parquet
paths = runtime.export_session_to_parquet(
    session_id=session_id,
    output_dir="/data/archive/",
)
# Returns: ["/data/archive/node_state.parquet", ...]

# Cleanup: drop trace partition (instant, zero dead tuples)
runtime.drop_session_partition(session_id)
```

## 6. SQLite Fallback (Dev/Test)

```python
from babylon.persistence.runtime_db import RuntimeDatabase

# Existing SQLite backend satisfies RuntimePersistence protocol
sqlite_runtime = RuntimeDatabase(db_path=":memory:")

# Same interface, no Postgres required
sqlite_runtime.persist_tick(tick=1, graph=graph)
graph = sqlite_runtime.hydrate_graph(tick=1)
```

## 7. Protocol Compliance Check

```python
from babylon.persistence.protocols import RuntimePersistence

# Structural typing: verify at runtime
assert isinstance(postgres_runtime, RuntimePersistence)
assert isinstance(sqlite_runtime, RuntimePersistence)
```
