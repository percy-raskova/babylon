# Data Model: Real Backend Wire-Up

**Feature**: 061-real-backend-wireup
**Status**: Draft (Phase 1)
**Updated**: 2026-05-11

## Scope

This document specifies data-model changes required by the spec. It is organized by subsystem so each change can be cross-checked against Constitution II.11 (Subsystem Table Ownership).

Subsystems affected:

| Subsystem | Owner | Changes |
|---|---|---|
| Engine persistence (snapshots + tick log) | `src/babylon/persistence/` | Added FK/unique constraints for idempotency; wrap-in-transaction pattern |
| Embedding store (RAG) | `src/babylon/rag/` + `src/babylon/persistence/pgvector_store.py` | DDL reconciliation; canonical 768-dim pin |
| Web bridge serializers | `web/game/` | Field additions to existing serialized shapes; no new tables |
| Web health endpoints | `web/babylon_web/` | New auth-gated `/health/detail/` payload schema |
| Cutover migrations | `web/game/migrations/` | New migrations 0006/0007/0008 |

No new entities are introduced. All changes are field additions, constraint additions, or migrations against existing structures.

## 1. Embedding Store Reconciliation

### Current state (broken)

Schema (`postgres_schema.py:374-385`):

```sql
CREATE TABLE document_chunk (
    id              VARCHAR(128) PRIMARY KEY,
    session_id      UUID REFERENCES game_session(id) ON DELETE SET NULL,
    source_file     VARCHAR(256) NOT NULL,
    chunk_index     INTEGER NOT NULL,
    content         TEXT NOT NULL,
    embedding       vector(768) NOT NULL,
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
)
```

Code (`pgvector_store.py:99`) inserts into:

```text
chunk_id, collection, content, embedding, metadata, source, chunk_index
```

Mismatched columns: `id` vs `chunk_id`, `session_id` vs `collection`, `source_file` vs `source`. The schema also defines a FK to `game_session`, which is incompatible with the multi-collection RAG design.

### Target state

```sql
CREATE TABLE document_chunk (
    chunk_id        VARCHAR(128) PRIMARY KEY,
    collection      VARCHAR(64)  NOT NULL,
    content         TEXT         NOT NULL,
    embedding       vector(768)  NOT NULL,
    metadata        JSONB        NOT NULL DEFAULT '{}'::jsonb,
    source          VARCHAR(256),
    chunk_index     INTEGER,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_document_chunk_collection ON document_chunk(collection);
CREATE INDEX idx_document_chunk_embedding
    ON document_chunk USING hnsw (embedding vector_cosine_ops);
```

Notes:
- `chunk_id` is the canonical PK (matches existing application code).
- `collection` namespaces embeddings across feature uses (theory corpus, scenario narrative, prompt fragments). Mandatory.
- `session_id` FK is removed entirely: embeddings are not session-scoped in the project's actual RAG design. Session affinity, if ever needed, belongs in `metadata` JSONB.
- `vector(768)` is the canonical dimension across DDL + code default + RAG initialization + fixtures (FR-001).
- HNSW index uses `vector_cosine_ops` (matches the `<=>` distance operator used in `pgvector_store.py` queries).

### Embedding model pin

Per Constitution III.6 (Model Pinning) and research R1:

- **Model identifier**: `sentence-transformers/all-mpnet-base-v2`
- **Vector dimension**: 768 (canonical, per spec FR-001)
- **License**: Apache 2.0
- **Weights hash**: HuggingFace `main` branch revision SHA captured at first deploy and pinned via `SentenceTransformer(..., revision=<sha>)`
- **Recorded in**: `src/babylon/config/llm_config.py` as frozen module-level constants:
  ```python
  CANONICAL_EMBEDDING_MODEL_ID = "sentence-transformers/all-mpnet-base-v2"
  CANONICAL_EMBEDDING_DIM = 768
  CANONICAL_EMBEDDING_REVISION = "<sha-from-deploy>"
  ```

### Validation rules

- Embeddings written via `PgVectorStore.add_chunks()` MUST be exactly 768-dimensional. Wrong-dimension inputs raise `EmbeddingDimensionError` at the application layer **before** the SQL INSERT is attempted (FR-002).
- The dimension check reads the canonical dimension from a single module-level constant (`CANONICAL_EMBEDDING_DIM = 768`) imported by both `pgvector_store.py` and the RAG initialization. No magic number duplication.

## 2. Snapshot Atomicity and Idempotency

### Persist-tick transactional wrapper

Per FR-003 and FR-004, the seven append-only snapshot tables written by `PostgresRuntime.persist_full_tick()` (currently lines 1627-1663 of `_legacy.py`) must commit atomically. The patched call structure:

```python
def persist_full_tick(self, *, game_id, tick, ...):
    with self._pool.connection() as conn:
        with conn.transaction():
            self._persist_territory_snapshots(conn, ...)
            self._persist_org_snapshots(conn, ...)
            self._persist_edge_snapshots(conn, ...)
            self._persist_community_snapshots(conn, ...)
            self._persist_hex_activity(conn, ...)
            self._persist_economic_summary(conn, ...)
            self._persist_tick_events(conn, ...)
        # COMMIT on clean exit; ROLLBACK on any raise
```

This relies on:
- A single `conn` from the pool used by all seven helpers (eliminates the current multi-connection bug).
- psycopg 3's `with conn.transaction():` block: commits on clean exit, rolls back on any exception (canonical pattern, per psycopg 3.x transaction docs).
- Each per-table helper accepts a `cursor` from the outer connection rather than acquiring its own.

### Idempotency constraints

The existing schema has no unique constraints on `action_result` or `simulation_event`. Per FR-004, we add:

```sql
-- action_result: prevent duplicate rows on retry for same action+tick
ALTER TABLE action_result
    ADD CONSTRAINT action_result_unique
    UNIQUE (session_id, tick, action_id);

-- simulation_event: prevent duplicate events for same tick+entity+type
ALTER TABLE simulation_event
    ADD CONSTRAINT simulation_event_unique
    UNIQUE (session_id, tick, event_type, entity_id);
```

Insert helpers use `ON CONFLICT DO NOTHING` to allow safe retry:

```sql
INSERT INTO action_result (...) VALUES (...)
ON CONFLICT (session_id, tick, action_id) DO NOTHING;
```

Caveat: this requires every `action_result` write to carry a stable `action_id` (the originating `PlayerAction.id`). Verified — the current `_persist_action_result()` already has access to `action.id`.

### Race-safe tick immutability (FR-005)

Resolved ticks are immutable. The race-safe check uses the existing `tick_log` table's composite PK `(session_id, tick)`:

```sql
INSERT INTO tick_log (session_id, tick, resolved_at, ...)
VALUES (%s, %s, now(), ...)
ON CONFLICT (session_id, tick) DO NOTHING
RETURNING id;
```

If the `RETURNING id` is empty, the tick was already resolved → the resolver raises `TickAlreadyResolved` and returns 409 Conflict to the API caller. This pattern is concurrent-safe at the database level (the PK uniqueness check is the atomic guard); no advisory locks needed.

## 3. Serializer Field Additions

The 36 gap fields identified in the investigation are added at the serializer boundary. No new database columns are introduced — every field has an existing source in the engine or is derivable from existing fields.

### Organization (`OrganizationSerializer`)

| Field | Type | Source | Notes |
|---|---|---|---|
| `short_name` | `str` (≤16 chars) | New attribute on engine `Organization` model OR deterministic-truncation of `name` | If new attribute: defaults to truncated `name`; can be overridden in scenario data |
| `player_controlled` | `bool` | Derived: `session.player_id == org.controlling_player_id` (engine attribute) | New attribute on engine `Organization` — defaults to `None` for NPCs |
| `ooda_phase` | `Literal["observe","orient","decide","act"]` | Engine `Organization.ooda_profile.current_phase` | Currently emitted as a 4-float dict; serializer reads the highest-valued component as the active phase OR engine emits the phase enum directly. Decision: **engine emits phase enum directly**; the 4 floats stay for telemetry. |
| `legitimacy` | `float ∈ [0, 1]` | Engine `Organization.legitimacy` | New attribute; default `0.5` for orgs without explicit value |
| `opacity` | `float ∈ [0, 1]` | Engine `Organization.opacity` | New attribute; default `0.5` for orgs without explicit value |
| `hyperedge_memberships` | `list[HyperedgeMembership]` | Engine `Organization.community_memberships` (via XGI hypergraph query) | Each item: `{hyperedge_id: str, role: str, strength: float}`. Replaces current hard-coded `[]` |

Engine-side changes required (in `src/babylon/models/organization.py` or equivalent):
- Add `short_name: str | None = None` field
- Add `controlling_player_id: int | None = None` field
- Add `legitimacy: Probability = Probability(0.5)` field
- Add `opacity: Probability = Probability(0.5)` field
- `OodaProfile` already has phase floats; add `current_phase` computed property returning the dominant phase as `OodaPhase` enum
- `OodaPhase` enum: `Literal["observe", "orient", "decide", "act"]`

### Event (`EventSerializer`)

| Field | Type | Source | Notes |
|---|---|---|---|
| `id` | `str` | Engine `WorldEvent.event_id` | New attribute (UUID4 string) — stable across snapshot lifecycle |
| `severity` | `Literal["critical","warning","informational"]` | Engine `WorldEvent.severity` | New attribute; default `informational` for legacy events |
| `title` | `str` (≤80 chars) | Engine `WorldEvent.title` | New attribute; defaults to derived label from `event_type` when absent |
| `body` | `str` | Engine `WorldEvent.body` | New attribute; defaults to empty string when absent |
| `data` | `dict[str, Any]` | Existing | Preserved as-is |

Engine-side changes required:
- `WorldEvent` model: add `event_id`, `severity`, `title`, `body` fields with sensible defaults
- Existing event constructors must be updated to populate these fields (or accept defaults)

### Territory (`TerritorySerializer`)

| Field | Type | Source | Notes |
|---|---|---|---|
| `consciousness` | `float ∈ [0, 1]` | Engine — aggregate over orgs in territory | New aggregate; computed in `_serialize_territory()` from member orgs |
| `solidarity` | `float ∈ [0, 1]` | Engine — average SOLIDARITY edge weight to other territories | New aggregate; computed in `_serialize_territory()` |
| `wealth` | `float (Currency)` | Engine `Territory.economy.total_wealth` | Already in `CountyEconomicState`; surface it |
| `dominant_community` | `str` (hyperedge_id) | Engine — XGI query for community with largest member share in territory | New aggregate |

These are **derived** fields per Constitution II.2 (Primitives vs Derived). They are computed at serialization time, not persisted as columns.

### Edge (`EdgeSerializer`)

| Field | Type | Source | Notes |
|---|---|---|---|
| `id` | `str` | New: deterministic from `(source_id, target_id, edge_type)` | E.g., `f"{source}>{edge_type}>{target}"` |
| `rate_of_profit` | `float \| None` | Engine — when edge mode is EXTRACTIVE/TRANSACTIONAL | Optional; `null` when not applicable |
| `rent_burden` | `float \| None` | Engine — when edge involves tribute or rent | Optional |
| `age_ticks` | `int` | Derived: `current_tick − edge.created_at_tick` | Requires new `created_at_tick` field on edges (or read from `edge_snapshot` history — preferred to avoid mutating Edge primitive) |

### Inspector endpoint payloads

The five inspector endpoints (`/api/games/{id}/node/{id}/`, `/org/{id}/`, `/community/{id}/`, `/edge/{id}/`, `/hex/{h3}/`) currently return `{}`. Each must return a structured detail object:

| Endpoint | Returns |
|---|---|
| `/node/{id}/` | `NodeDetailSerializer`: id, type, attributes (full graph-node dict), incoming-edges, outgoing-edges (capped at 50 each) |
| `/org/{id}/` | Full `OrganizationSerializer` payload + recent action history (last 10 ticks) + community memberships |
| `/community/{id}/` | `CommunityDetailSerializer`: hyperedge_id, category, member roster (sorted by role+strength), contradiction_partner_id, material_basis dict, ideological_dimension dict, ternary consciousness vector |
| `/edge/{id}/` | `EdgeDetailSerializer`: full edge attributes + last 10 tick value-flow history (queried from `edge_snapshot`) |
| `/hex/{h3}/` | `HexDetailSerializer`: full `hex_latest` row + parent county/CZ/BEA aggregates + orgs/communities present |

### Time-series payload

`GET /api/games/{id}/timeseries/` returns:

```json
{
  "status": "ok",
  "data": {
    "ticks": [0, 1, 2, ..., N],
    "imperial_rent": [..., ..., ...],
    "consciousness": [...],
    "solidarity": [...],
    "heat": [...],
    "wealth": [...],
    "biocapacity": [...]
  }
}
```

All seven arrays have the same length as `ticks`. Source: `tick_summary` table — every metric is already aggregated there per tick. No new computation; just a SELECT ORDER BY tick.

### Communities dashboard payload

`GET /api/games/{id}/communities/` returns:

```json
{
  "status": "ok",
  "data": {
    "communities": [
      {
        "hyperedge_id": "...",
        "category": "class | identity | ideological",
        "member_count": N,
        "ternary": {"reformist": float, "liberal": float, "fascist": float},
        "contradiction_partner_id": "..." | null,
        "infiltration_resistance": float
      }
    ]
  }
}
```

Source: `community_state` and `community_membership` tables — already populated by `persist_community_state()`. New query, no new tables.

## 4. Health Endpoint Schemas

### Public `GET /health/`

Existing endpoint, preserved as-is:

```json
{"status": "ok"}
```

Returns HTTP 200 with this payload regardless of engine bridge state. Suitable for systemd watchdog and Cloudflare health probes.

### Auth-gated `GET /health/detail/`

New endpoint. Authentication: Django session, staff-only (`request.user.is_staff == True`).

Authenticated 200 response:

```json
{
  "engine": {
    "implementation": "EngineBridge | StubEngineBridge",
    "boot_attempts": 1,
    "boot_succeeded_at": "2026-05-11T15:00:00Z",
    "last_tick_resolved_at": "2026-05-11T15:30:42Z" | null
  },
  "database": {
    "reachable": true | false,
    "pool_size": {"min": 1, "max": 4, "active": 2}
  },
  "embedding_model": {
    "model_id": "[from R1]",
    "dimension": 768
  },
  "version": "0.X.Y",
  "git_sha": "abc1234"
}
```

Unauthenticated callers receive HTTP 404 with body `{"detail": "Not found."}` — byte-identical to DRF's standard not-found response. This prevents information disclosure about the endpoint's existence (FR-009, security-by-obscurity clarification).

Implementation pattern (per research R5):
- Standard DRF permission classes on the view: `permission_classes = [IsAuthenticated, IsStaff]`. These raise `NotAuthenticated`/`PermissionDenied` on failure (mapping to 401/403 by default).
- A **custom DRF exception handler** registered in `REST_FRAMEWORK['EXCEPTION_HANDLER']` intercepts `NotAuthenticated`/`PermissionDenied` raised by this specific view class (`HealthDetailView`) and rewrites the response to HTTP 404 with body `{"detail": "Not found."}`.
- This pattern avoids DRF issue #7529 (raising `Http404` from `has_permission()` breaks `BrowsableAPIRenderer`).
- Scope: only `HealthDetailView` is remapped; all other endpoints retain DRF's default 401/403 behavior.

## 5. Migration Sequence

Three new Django migrations are added in order:

### `0006_drop_sim_hex_states.py`

```python
operations = [
    migrations.RunSQL(
        sql=[
            "DROP TABLE IF EXISTS sim.hex_states CASCADE;",
            "DROP SCHEMA IF EXISTS sim CASCADE;",
        ],
        reverse_sql=migrations.RunSQL.noop,
    ),
]
```

Removes the orphan from migration 0002. Cascading is safe (no other table references `sim.hex_states`).

### `0007_purge_fixture_sessions.py`

```python
operations = [
    migrations.RunSQL(
        sql=[
            # CASCADE deletes game_turn, action_result, simulation_event, node_state, edge_state, etc.
            "DELETE FROM game_session;",
        ],
        reverse_sql=migrations.RunSQL.noop,
    ),
]
```

Per FR-033 (clarified): purges every pre-existing `game_session` row. After cutover, the DB contains no fixture-era sessions. Subsequent session creates use `EngineBridge.create_session()` and produce real-engine sessions by construction.

### `0008_drop_snapshot_json.py` (optional — runs after the mock bridge is verified deleted)

```python
operations = [
    migrations.RunSQL(
        sql="ALTER TABLE game_session DROP COLUMN IF EXISTS snapshot_json;",
        reverse_sql="ALTER TABLE game_session ADD COLUMN snapshot_json JSONB NOT NULL DEFAULT '{}'::jsonb;",
    ),
]
```

The `snapshot_json` column was added in migration 0005 specifically for `MockEngineBridge`. Once the mock is deleted (FR-032), the column is dead weight. Dropping it is optional but recommended.

### `0009_action_result_unique.py`

```python
operations = [
    migrations.RunSQL(
        sql=[
            "ALTER TABLE action_result ADD CONSTRAINT action_result_unique "
            "UNIQUE (session_id, tick, action_id);",
            "ALTER TABLE simulation_event ADD CONSTRAINT simulation_event_unique "
            "UNIQUE (session_id, tick, event_type, entity_id);",
        ],
        reverse_sql=[
            "ALTER TABLE action_result DROP CONSTRAINT IF EXISTS action_result_unique;",
            "ALTER TABLE simulation_event DROP CONSTRAINT IF EXISTS simulation_event_unique;",
        ],
    ),
]
```

Adds the idempotency constraints (FR-004). Safe to run on empty post-cutover tables.

### `0010_document_chunk_reconciliation.py`

```python
operations = [
    migrations.RunSQL(
        sql=[
            "DROP TABLE IF EXISTS document_chunk CASCADE;",
            # Re-create using the corrected DDL from postgres_schema.py:
            DOCUMENT_CHUNK_DDL_CORRECTED,
            "CREATE INDEX idx_document_chunk_collection ON document_chunk(collection);",
            "CREATE INDEX idx_document_chunk_embedding ON document_chunk "
            "USING hnsw (embedding vector_cosine_ops);",
        ],
        reverse_sql=migrations.RunSQL.noop,
    ),
]
```

Note: this is a DROP-and-recreate, not an ALTER. The current table has no production data (it's been broken since creation — every read/write would have raised `UndefinedColumn`), so no data preservation is needed.

## 6. State Transitions (unchanged but documented)

| Entity | Transitions |
|---|---|
| `GameSession.status` | `active → paused → active` (player toggle); `active → resolving → active` (during tick resolution); `active → ended` (terminal) |
| `PlayerAction` | `pending → resolved` (one-way, on tick resolution); `pending → cancelled` (via DELETE before resolution) |
| `Tick` | `unresolved → resolved` (one-way, immutable per FR-005 clarification) |

No new state transitions are introduced by this feature.

## 7. Cross-References

- **Spec sections**: Overview, FR-001 to FR-033, Edge Cases (Partial tick persistence; Re-resolution; Reference to purged session)
- **Constitution principles enforced**: I.20 (substrate untouched), II.6 (state is data — persistence after tick, not during), II.11 (subsystem ownership preserved — engine layer mediates), III.6 (model pinning), III.7 (determinism preserved through transactional writes)
