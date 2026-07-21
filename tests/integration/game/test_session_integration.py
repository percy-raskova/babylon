"""Integration test: one real tick through the composition root, real Postgres.

The PG-reachable leg of Unit C1's blueprint
(``tests/integration/archive/test_pilot_first_action.py`` proves the pure
engine loop against no Postgres; this proves the SAME loop actually
persists and crash-resumes through a real
:class:`~babylon.persistence.postgres_runtime.PostgresRuntime`). Skipped
automatically when Postgres is unreachable (the ``pg_pool`` fixture's own
skip — see ``tests/conftest.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from babylon.engine.scenarios import WayneCountyScenario
from babylon.game.session import create_new_campaign, ensure_schema, resume_campaign
from babylon.persistence import PostgresRuntime

if TYPE_CHECKING:
    from psycopg_pool import ConnectionPool

pytestmark = [pytest.mark.integration]


def test_create_advance_and_resume_one_real_tick(pg_pool: ConnectionPool) -> None:
    """Fresh boot -> one real tick -> crash-resume reconstructs the SAME state.

    Exercises the full C1 seam against real Postgres: ``create_session``,
    ``persist_tick``/``hydrate_graph`` (the Feature-037 full-graph
    snapshot), ``persist_tick_atomic``/``get_last_committed_tick`` (the
    spec-089 ``tick_commit`` marker), ``mark_turns_resolved``.
    """
    runtime = PostgresRuntime(pool=pg_pool)
    ensure_schema(runtime)

    session = create_new_campaign(runtime, scenario=WayneCountyScenario())
    session_id = session.session_id
    try:
        assert runtime.get_last_committed_tick(session_id) == 0

        result = session.advance_tick()
        assert result.tick == 1
        assert session.tick == 1
        assert runtime.get_last_committed_tick(session_id) == 1

        resumed = resume_campaign(runtime, session_id)
        assert resumed.tick == 1
        assert resumed.scenario_name == "wayne_county"
        # A genuine reconstruction: same node/edge census as the live,
        # in-memory post-tick graph — not merely "some graph".
        assert sorted(resumed.graph.nodes) == sorted(session.graph.nodes)
        assert resumed.graph.number_of_edges() == session.graph.number_of_edges()

        # A second real tick off the RESUMED session persists at tick 2 —
        # crash-resume is not a dead end; the loop continues from there.
        resumed_result = resumed.advance_tick()
        assert resumed_result.tick == 2
        assert runtime.get_last_committed_tick(session_id) == 2
    finally:
        with pg_pool.connection() as conn:
            conn.execute("DELETE FROM game_session WHERE id = %s", (session_id,))
