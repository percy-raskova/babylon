"""RuntimePersistence contract: datetime-carrying events (P0 #6).

Runs the SAME scenario against BOTH ``RuntimePersistence`` implementations:

- ``RuntimeDatabase`` (SQLite) — always runs.
- ``PostgresRuntime`` — guarded by the ``pg_pool`` fixture
  (``tests/conftest.py``), which skips with "PostgreSQL not available"
  when the local test server is down — the same availability-guard
  pattern as :mod:`tests.integration.persistence.test_migration_idempotency`.

Scenario (the exact bridge payload shape from
``web/game/engine_bridge.py`` ``resolve_tick``): a real
:class:`~babylon.models.events.SimulationEvent` is ``model_dump()``-ed
(python mode — ``timestamp`` stays a :class:`datetime.datetime`) and
passed through ``persist_tick``. Then the tick is re-persisted with a
regenerated wall-clock timestamp: per the spec-056 monotonic-idempotent
contract (Predicate B') the retry must return silently and must not
duplicate the stored event.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest

from babylon.models.enums import EventType
from babylon.models.events import SimulationEvent
from babylon.persistence import RuntimeDatabase
from babylon.persistence.postgres_runtime import PostgresRuntime
from babylon.topology.graph import BabylonGraph

if TYPE_CHECKING:
    from collections.abc import Generator

pytestmark = pytest.mark.integration


@pytest.fixture(params=["sqlite", "postgres"])
def backend(
    request: pytest.FixtureRequest,
) -> Generator[tuple[Any, UUID | None], None, None]:
    """Yield ``(persistence, session_id)`` for each RuntimePersistence impl.

    SQLite always runs. The Postgres branch requests ``pg_pool`` lazily so
    an unavailable server skips ONLY the postgres parametrization.
    """
    if request.param == "sqlite":
        with RuntimeDatabase(in_memory=True) as db:
            yield db, None
    else:
        pool = request.getfixturevalue("pg_pool")  # skips when PG unavailable
        runtime = PostgresRuntime(pool)
        session_id = runtime.create_session(
            scenario="p0-6-datetime-contract",
            config_json={},
            game_defines_json={},
            rng_seed=42,
        )
        # Do NOT close the runtime: pg_pool is session-scoped and shared.
        yield runtime, session_id


def _stored_event_count(persistence: Any, session_id: UUID | None, tick: int) -> int:
    """Count events persisted for ``tick`` on either backend."""
    if isinstance(persistence, RuntimeDatabase):
        return len(persistence.get_events(tick=tick))
    with persistence.pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM simulation_event WHERE session_id = %s AND tick = %s",
            (session_id, tick),
        )
        row = cur.fetchone()
        return int(row[0]) if row is not None else 0


class TestDatetimeEventContract:
    """Same datetime-event persist + idempotent-retry scenario, both backends."""

    def test_datetime_event_persist_and_retry_idempotent(
        self, backend: tuple[Any, UUID | None]
    ) -> None:
        """A SimulationEvent with a real datetime persists; a retry whose
        only difference is a regenerated timestamp neither raises nor
        duplicates the stored event."""
        persistence, session_id = backend
        graph = BabylonGraph()
        graph.add_node("w1", type="SocialClass")

        event = SimulationEvent(
            event_type=EventType.UPRISING,
            tick=0,
            timestamp=datetime(2026, 7, 8, 1, 0),
        )
        persistence.persist_tick(
            tick=0, graph=graph, events=[event.model_dump()], session_id=session_id
        )

        retry = SimulationEvent(
            event_type=EventType.UPRISING,
            tick=0,
            timestamp=datetime(2026, 7, 8, 1, 5),  # regenerated wall clock
        )
        persistence.persist_tick(
            tick=0, graph=graph, events=[retry.model_dump()], session_id=session_id
        )  # must NOT raise MonotonicityViolationError

        assert _stored_event_count(persistence, session_id, tick=0) == 1
