# Implementation Brief — P0 #6: tick resolve 500s with "Object of type datetime is not JSON serializable"

Branch: `fix/tick-resolve-datetime` (from `dev`). All line numbers verified against `chore/test-infra-rearm` @ 9101dddf on 2026-07-08.

## 1. Root cause (verified end-to-end)

1. `SimulationEvent.timestamp: datetime = Field(default_factory=datetime.now)` — `src/babylon/models/events/_legacy.py:99-102`. Every engine event carries a wall-clock `datetime`. (`event_type` is a `StrEnum` — `src/babylon/models/enums/events.py:30` — and is JSON-safe; `timestamp` is the ONLY offending key.)
2. `web/game/engine_bridge.py:1982` (in `resolve_tick`):
   ```python
   events_as_dicts: list[dict[str, Any]] = [e.model_dump() for e in new_state.events]
   ```
   `model_dump()` (python mode) preserves the `datetime` object. Passed to `self._persistence.persist_tick(...)` at 1983-1988.
3. `src/babylon/persistence/postgres_runtime/_legacy.py:145` — `persist_tick` calls `new_payload = self._canonical_payload(graph, events)` UNCONDITIONALLY, *before* the tick-exists check at 148-161. So the crash fires on the FIRST persist of any tick with events, not only on retries.
4. **The crash site** — `_legacy.py:203` inside `_canonical_payload` (169-204):
   ```python
   events_list = sorted(json.dumps(event, sort_keys=True) for event in (events or []))
   ```
   No `default=` → `TypeError: Object of type datetime is not JSON serializable`.
5. `web/game/api.py:1028-1034` catches `Exception`, restores session status, returns 500 "Tick resolution failed" — the observed P0 symptom.

A working `_json_default` helper already exists at `_legacy.py:45-53`:
```python
def _json_default(obj: object) -> str:
    """Fallback serializer for ``json.dumps`` — handles datetime/date/UUID."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
```

## 2. Why `default=` alone is NOT enough — timestamp must be EXCLUDED from canonical comparison

`_persist_events` (`_legacy.py:2205-2231`) is already safe (line 2227: `json.dumps(e, default=_json_default)`) and stores the isoformat timestamp inside `simulation_event.details`. The stored-side reconstructor `_canonical_payload_for_tick` (`_legacy.py:206-264`) reads it back at **256-262**:
```python
            events_list = sorted(
                json.dumps(
                    row["details"] if isinstance(row["details"], dict) else {},
                    sort_keys=True,
                )
                for row in cur.fetchall()
            )
```
(Latent, doesn't crash — JSONB decodes to primitives — but it is the comparison's stored side.)

A retried resolve (api.py restores `status="active"` on failure; the client retries) re-runs `step()` → brand-new `datetime.now()` timestamps → new canonical payload ≠ stored payload → `MonotonicityViolationError` → another 500. Spec-056's contract (`test_same_payload_re_persist_idempotent`, Predicate B') requires same-payload retries to return silently. Therefore: **exclude the top-level `timestamp` key from BOTH sides of the canonical comparison, keep it in storage.**

Downstream safety of exclusion (verified — nothing reads persisted event timestamps):
- `simulation_event` is write-only in the product: only `_canonical_payload_for_tick` SELECTs it; repo-wide rg finds only schema/migration/archival-docstring references.
- Journal/alerts read `tick_event`, written by `_persist_tick_events_safe` (engine_bridge.py:3228-3260) from `_serialize_event`, which **already excludes timestamp** — engine_bridge.py:3168: `data = event.model_dump(exclude={"event_type", "tick", "timestamp"})`.
- Frontend `GameEvent` (web/frontend/src/types/game.ts:296-308) has no timestamp field; `wire.ts:19 timestamp_utc` is envelope metadata, not event data.

## 3. Full json.dumps audit — `postgres_runtime` package (`_spec_062.py` and `__init__.py` contain none; all sites in `_legacy.py`)

| Line | Context | Verdict |
|---|---|---|
| 62 | `_is_json_serializable` probe, **uses** `default=_json_default` | see asymmetry note below |
| 184-187 | `_canonical_payload` node attrs — filter admits datetimes (probe has default) but dump lacks `default=` | **UNSAFE-latent** (TypeError if a node attr is ever a datetime; none today) |
| 196-199 | `_canonical_payload` edge attrs — same pattern | **UNSAFE-latent** |
| 203 | `_canonical_payload` events | **CRASH SITE (P0)** |
| 226-229 / 244-247 | `_canonical_payload_for_tick` nodes/edges (JSONB-decoded dicts) | safe |
| 256-262 | `_canonical_payload_for_tick` events | **latent idempotency breaker** (fix with exclusion) |
| 369-371 | `log_tick` mutations/invariant_checks/system_timings (`dict[str, bool/int]` per signature) | safe-in-practice |
| 395 | `set_metadata` `{key: value}` (str) | safe |
| 447-449 | `persist_graph_metadata` economy/state_finances/tick_dynamics (numeric dicts) | safe-in-practice |
| 647, 677, 737, 776, 900, 990-991, 1093 | biocapacity_stocks / capacity / gradient / action details / trace data / config+defines model_dump / params_json | safe-in-practice (primitive payload contracts) |
| 1302, 1361, 1435, 1493, 1547, 1602, 1689, 1749, 2227 | all already `default=_json_default` | **safe** |
| 2131, 2180 | `_persist_nodes`/`_persist_edges` via `_make_serializable` (2290-2300, plain-dumps probe, NO default → datetimes silently dropped from storage) | safe by exclusion |
| 2296 | the `_make_serializable` probe itself | safe (filter) |

**Asymmetry finding (fix as part of this branch):** `_is_json_serializable` (`_legacy.py:56-65`) probes WITH `default=_json_default`, so a datetime node attr would pass the canonical filter — then crash at 184 (no default), and even with a default it could never equal the stored side because `_make_serializable` (2290-2300) DROPS datetimes from stored attrs. The SQLite twin's probe (`runtime_db.py:290-296`) has NO default. **Minimal correct alignment: remove `default=_json_default` from line 62** so datetime attrs are filtered from the canonical payload exactly as they are filtered from storage. Update the docstring at 57-60 accordingly. (Do NOT add default at 184/196 — that would create the new-vs-stored mismatch described above.)

## 4. The SQLite twin has the identical bug (plan drift — must fix for contract parity + fast-gate RED test)

`src/babylon/persistence/runtime_db.py` (`RuntimeDatabase`, same `RuntimePersistence` protocol, parametrized in the fast-gate property suite):
- **line 206** — the actual persist path crashes: `json.dumps(event)` (inside `persist_tick`'s events loop, 194-208)
- **line 245** — `_canonical_payload` events: `events_list = sorted(json.dumps(event, sort_keys=True) for event in (events or []))` (verbatim same bug)
- **lines 284-287** — `_canonical_payload_for_tick` events: `_re_canonical(details)` includes the stored timestamp → same retry mismatch

## 5. Implementation steps

### Step 0 — RED tests first (see §6), confirm they fail with the exact TypeError / MonotonicityViolationError.

### Step 1 — new shared module `src/babylon/persistence/serialization.py` (DRY: both backends need it)
```python
"""Shared JSON canonicalization helpers for persistence backends.

Both :class:`~babylon.persistence.runtime_db.RuntimeDatabase` and
:class:`~babylon.persistence.postgres_runtime.PostgresRuntime` persist
per-tick event dicts and compare canonical payloads for the spec-056
monotonic-idempotent contract. Event ``timestamp`` values are wall-clock
(:class:`~babylon.models.events.SimulationEvent` uses
``default_factory=datetime.now``) and therefore differ across retries of
the same tick; they are excluded from canonical comparison but preserved
in storage.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any
from uuid import UUID


def json_default(obj: object) -> str:
    """Fallback serializer for ``json.dumps`` — handles datetime/date/UUID.

    Raises:
        TypeError: For any other non-serializable type.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def canonical_event_json(event: dict[str, Any]) -> str:
    """Canonical JSON for one event dict, excluding wall-clock ``timestamp``.

    Used by both sides of the spec-056 monotonic-idempotent comparison so
    that a retried tick whose only difference is regenerated event
    timestamps compares equal to the stored payload.
    """
    return json.dumps(
        {k: v for k, v in event.items() if k != "timestamp"},
        sort_keys=True,
        default=json_default,
    )
```
(Full RST docstrings per project standard; mypy strict clean.)

### Step 2 — `src/babylon/persistence/postgres_runtime/_legacy.py`
1. Delete the local `_json_default` def (lines 45-53); delete `from datetime import date, datetime` (line 22 — `date`/`datetime` are used ONLY inside that def; `UUID` stays, used at 386/407 etc.). Add:
   ```python
   from babylon.persistence.serialization import canonical_event_json, json_default as _json_default
   ```
   The 10 existing `default=_json_default` call sites plus line 62 need no edits from the rename.
2. Line 62 probe: change `json.dumps(value, default=_json_default)` → `json.dumps(value)`; update docstring 57-60 to note it intentionally matches `_make_serializable`'s storage filter (datetimes excluded from both canonical AND stored node/edge attrs).
3. Line 203 →
   ```python
   events_list = sorted(canonical_event_json(event) for event in (events or []))
   ```
4. Lines 256-262 →
   ```python
   events_list = sorted(
       canonical_event_json(row["details"] if isinstance(row["details"], dict) else {})
       for row in cur.fetchall()
   )
   ```

### Step 3 — `src/babylon/persistence/runtime_db.py`
1. Add `from babylon.persistence.serialization import canonical_event_json, json_default` to the import block (after line 33's protocols import).
2. Line 206 (persist path — keep timestamp IN storage, parity with Postgres `_persist_events`): `json.dumps(event)` → `json.dumps(event, default=json_default)`.
3. Line 245 → `events_list = sorted(canonical_event_json(event) for event in (events or []))`.
4. Lines 284-287 →
   ```python
   events_list = sorted(
       canonical_event_json(json.loads(details) if details else {})
       for (details,) in self.con.execute("SELECT details FROM events WHERE tick = ?", (tick,))
   )
   ```
   (keep `_re_canonical` for the node/edge branches at 265-283).

### Step 4 — `web/game/engine_bridge.py` defense-in-depth (all three persist_tick callers)
- **Line 1982**: `[e.model_dump() for e in new_state.events]` → `[e.model_dump(mode="json") for e in new_state.events]`
- **Line 791** (create_game tick-0 seed): `events=[event.model_dump() for event in initial_state.events] or None` → add `mode="json"`
- **Line 831** (hydrate_state backfill seed): same change.
`mode="json"` renders `timestamp` as an ISO string and `event_type` (StrEnum) as plain str; the canonical exclusion is by key name, unaffected.

### Out of scope — note in commit body, do NOT fix here
- `_persist_events` reads `e.get("type", "UNKNOWN")` / `e.get("entity_id")` (`_legacy.py:2224-2225`) but `model_dump()` produces the key `event_type` → the `simulation_event.event_type` column is always "UNKNOWN" for bridge events. Pre-existing; separate ticket.

## 6. Tests

### Existing coverage (verified nodeids)
- `tests/property/invariants/test_tick_persistence_monotonic.py::TestTickPersistenceMonotonic::{test_sequential_persists_succeed, test_different_payload_re_persist_raises, test_same_payload_re_persist_idempotent, test_back_in_time_rewrite_raises}` — fast gate, RuntimeDatabase only; never passes `events=` (which is why the bug survived). Runtime `pytest.skip` at line 195 is only a vacuous-Hypothesis-draw guard — nothing to un-skip.
- `tests/integration/test_persistence_monotonic_postgres.py` (same 4 predicates vs PostgresRuntime; `pytestmark = pytest.mark.integration`; `pg_pool` fixture in `tests/conftest.py:322` skips with "PostgreSQL not available (set BABYLON_TEST_PG_DSN)" — default DSN is the port-5433 `mise run db:up` container).
- `tests/unit/persistence/test_postgres_runtime.py::TestPersistTick::test_persists_events` (line 257; mocked pool; event dicts WITHOUT timestamp — passes today, extend beside it).
- `tests/unit/persistence/test_runtime_db.py::TestEventPersistence::test_persist_events` (line 284) and `::TestGraphPersistence::test_persist_same_payload_is_idempotent` (line 217).
- `tests/unit/web/test_engine_bridge.py::TestResolveTick*` — MagicMock persistence, so serialization is never exercised; can only assert call-arg shapes.
- Skipped-by-env integration: `tests/integration/web/test_game_lifecycle.py` (`test_resolve_tick_advances_state` line 79, `test_full_lifecycle_create_submit_resolve` line 105) and `tests/integration/web/test_bridge_roundtrip.py` (`test_resolve_produces_different_tick` line 105, `test_multiple_resolves_are_monotonic` line 118). Both are `pytest.mark.requires_postgres` + `skipif(not os.environ.get("POSTGRES_HOST"))`. **Both fixtures are STALE** (see drift alerts): they call `PostgresRuntime(host=..., port=..., database=..., user=..., password=...)` but `PostgresRuntime.__init__` (`_legacy.py:78`) takes only `pool`.

### NEW tests — RED first

**A. Fast gate, SQLite (`tests/unit/persistence/test_runtime_db.py`, inside `TestEventPersistence`):**
```python
    def test_persist_events_with_datetime_timestamp(self) -> None:
        """Bug #6: SimulationEvent.model_dump() carries a datetime timestamp."""
        with RuntimeDatabase(in_memory=True) as db:
            graph = BabylonGraph()
            graph.add_node("w1", type="SocialClass")
            events = [
                {"type": "UPRISING", "entity_id": "w1", "timestamp": datetime(2026, 7, 8, 1, 0)},
            ]
            db.persist_tick(tick=0, graph=graph, events=events)  # RED: TypeError
            assert len(db.get_events(tick=0)) == 1

    def test_retry_with_regenerated_timestamp_is_idempotent(self) -> None:
        """Spec-056 B': a retry differing only in event wall-clock timestamps
        must return silently, not raise MonotonicityViolationError."""
        with RuntimeDatabase(in_memory=True) as db:
            graph = BabylonGraph()
            graph.add_node("w1", type="SocialClass")
            ev = {"type": "UPRISING", "entity_id": "w1", "timestamp": datetime(2026, 7, 8, 1, 0)}
            db.persist_tick(tick=0, graph=graph, events=[ev])
            retry = dict(ev, timestamp=datetime(2026, 7, 8, 1, 5))
            db.persist_tick(tick=0, graph=graph, events=[retry])  # must NOT raise
```
(Match the file's existing style: `with RuntimeDatabase(in_memory=True) as db:`; use whatever event accessor `test_persist_events` at line 284 uses.)

**B. Fast gate, Postgres mocked pool (`tests/unit/persistence/test_postgres_runtime.py`, inside `TestPersistTick`):**
```python
    def test_persists_events_with_datetime_timestamp(
        self, runtime: PostgresRuntime, session_id: UUID, mock_cursor: MagicMock
    ) -> None:
        """Bug #6: datetime timestamps must not crash canonicalization.

        _canonical_payload runs before any DB access (persist_tick line
        145), so the mocked pool is sufficient to reproduce the TypeError.
        """
        events = [{"type": "UPRISING", "entity_id": "w1",
                   "timestamp": datetime(2026, 7, 8, 1, 0)}]
        graph = _build_graph(nodes={"w1": {"type": "SocialClass"}})
        runtime.persist_tick(tick=5, graph=graph, events=events, session_id=session_id)  # RED: TypeError
        rows = mock_cursor.executemany.call_args_list[-1][0][1]
        assert "timestamp" in json.loads(rows[0][5])  # stored details keep the timestamp

    def test_retry_with_regenerated_timestamp_is_idempotent(
        self, runtime: PostgresRuntime, session_id: UUID, mock_cursor: MagicMock
    ) -> None:
        """Stored-side exclusion: fetchone→tick exists; fetchall feeds
        _canonical_payload_for_tick (nodes, edges, events in that order)."""
        mock_cursor.fetchone.return_value = (1,)
        mock_cursor.fetchall.side_effect = [
            [],  # node_state rows
            [],  # edge_state rows
            [{"details": {"type": "UPRISING", "entity_id": "w1",
                          "timestamp": "2026-07-08T01:00:00"}}],
        ]
        events = [{"type": "UPRISING", "entity_id": "w1",
                   "timestamp": datetime(2026, 7, 8, 1, 5)}]  # DIFFERENT wall clock
        # empty graph so node/edge canonical sides are trivially equal
        runtime.persist_tick(tick=5, graph=_build_graph(), events=events, session_id=session_id)
        # RED today: MonotonicityViolationError (after the TypeError is fixed)
```
Needs `from datetime import datetime` added to the file's imports.

**C. Postgres integration (extend `tests/integration/test_persistence_monotonic_postgres.py`):**
```python
    def test_datetime_event_retry_is_idempotent(
        self, runtime: PostgresRuntime, session_id: uuid.UUID
    ) -> None:
        """P0 #6 regression: datetime-carrying events persist, and a retry
        differing only in timestamps is idempotent (Predicate B')."""
        graph = _payload_to_graph("with_events", 1)
        ev = {"type": "UPRISING", "entity_id": "payload_node",
              "timestamp": datetime(2026, 7, 8, 1, 0)}
        runtime.persist_tick(tick=0, graph=graph, events=[ev], session_id=session_id)
        retry = dict(ev, timestamp=datetime(2026, 7, 8, 1, 5))
        runtime.persist_tick(tick=0, graph=graph, events=[retry], session_id=session_id)
        different = dict(ev, entity_id="other")
        with pytest.raises(MonotonicityViolationError):
            runtime.persist_tick(tick=0, graph=graph, events=[different], session_id=session_id)
```

**D. wayne_county resolve integration (extend `tests/integration/web/test_game_lifecycle.py`)** — a Postgres-marked resolve test EXISTS to extend, but its fixture must be repaired first (lines 42-48):
```python
@pytest.fixture
def bridge(_django_setup: None) -> object:
    """Create an EngineBridge connected to PostgreSQL."""
    from psycopg_pool import ConnectionPool

    from babylon.persistence.postgres_runtime import PostgresRuntime

    conninfo = (
        f"dbname={os.environ.get('POSTGRES_DB', 'babylon_test')} "
        f"host={os.environ.get('POSTGRES_HOST', 'localhost')} "
        f"port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"user={os.environ.get('POSTGRES_USER', 'babylon')} "
        f"password={os.environ.get('POSTGRES_PASSWORD', 'babylon')}"
    )
    pool = ConnectionPool(conninfo=conninfo, min_size=1, max_size=2, open=True)
    persistence = PostgresRuntime(pool)

    from game.engine_bridge import EngineBridge

    return EngineBridge(persistence)
```
Then add to `TestGameLifecycle`:
```python
    def test_resolve_tick_wayne_county_with_engine_events(self, bridge: object) -> None:
        """P0 #6 e2e: wayne_county resolve persists datetime-carrying engine
        events without a 500 (engine_bridge.py:1982 → persist_tick)."""
        from game.engine_bridge import EngineBridge

        assert isinstance(bridge, EngineBridge)
        session_id = bridge.create_game(scenario="wayne_county", rng_seed=42)
        for expected_tick in (1, 2, 3):  # events appear on engine ticks
            result = bridge.resolve_tick(session_id)
            assert result["tick"] == expected_tick
```
(`wayne_county` is recognized at engine_bridge.py:3062: `if normalized in {"wayne_county", "wayne", "detroit"}: create_wayne_county_scenario()`.) Apply the same fixture repair to `tests/integration/web/test_bridge_roundtrip.py:39-46` in the same commit (it's a copy of the same stale code), which un-strands `test_resolve_produces_different_tick` / `test_multiple_resolves_are_monotonic`.

## 7. Verification commands (in order)

```bash
# RED phase (before any src change):
poetry run pytest tests/unit/persistence/test_runtime_db.py -k "datetime or regenerated" -vv          # TypeError
poetry run pytest tests/unit/persistence/test_postgres_runtime.py -k "datetime or regenerated" -vv    # TypeError / MonotonicityViolationError

# GREEN phase:
mise run test:q -- tests/unit/persistence/
mise run test:q -- tests/unit/web/test_engine_bridge.py
mise run test:q -- tests/property/invariants/test_tick_persistence_monotonic.py
mise run check:quick                                   # ruff + format + mypy strict

# Postgres integration (runner test DB, port 5433):
mise run db:up
poetry run pytest tests/integration/test_persistence_monotonic_postgres.py -vv

# wayne_county resolve e2e (web DB, port 5432, migrated Django DB):
POSTGRES_HOST=localhost POSTGRES_PORT=5432 POSTGRES_DB=babylon POSTGRES_USER=babylon POSTGRES_PASSWORD=babylon \
  poetry run pytest tests/integration/web/test_game_lifecycle.py -vv

# Full fast gate + live proof:
mise run test:unit
mise run web:dev    # create wayne_county game in UI, POST /api/games/{id}/resolve/ → 200, tick advances
mise run web:stop

mise run commit -- "fix(persistence): tick resolve datetime serialization + timestamp-excluded canonical idempotency (P0 #6)"
```

## 8. Files touched (complete list)
- NEW `src/babylon/persistence/serialization.py`
- `src/babylon/persistence/postgres_runtime/_legacy.py` (lines 22, 45-53, 56-65, 203, 256-262)
- `src/babylon/persistence/runtime_db.py` (imports, 206, 245, 284-287)
- `web/game/engine_bridge.py` (791, 831, 1982)
- `tests/unit/persistence/test_runtime_db.py`, `tests/unit/persistence/test_postgres_runtime.py`, `tests/integration/test_persistence_monotonic_postgres.py`, `tests/integration/web/test_game_lifecycle.py`, `tests/integration/web/test_bridge_roundtrip.py`
