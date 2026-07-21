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
from uuid import uuid4

import pytest

from babylon.engine.scenarios import WayneCountyScenario
from babylon.game.session import create_new_campaign, ensure_schema, resume_campaign
from babylon.persistence import PostgresRuntime
from babylon.persistence.babylon_meta import BabylonMetaStore

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


def test_progress_store_keeps_the_lobby_row_live_through_create_advance_and_resume(
    pg_pool: ConnectionPool,
) -> None:
    """Review fix, against a real ``babylon_meta`` catalog: the lobby row's
    ``last_tick`` tracks the Ledger's own tick through creation, an advance,
    and a crash-resume — never stuck at its creation-time ``0`` forever
    (:meth:`~babylon.persistence.babylon_meta.BabylonMetaStore.
    record_progress`, previously wired to zero production callers).
    """
    runtime = PostgresRuntime(pool=pg_pool)
    ensure_schema(runtime)
    catalog = BabylonMetaStore(pg_pool)
    catalog.ensure_schema()

    minted = catalog.create_campaign(
        slug=f"progress-wiring-{uuid4().hex[:12]}", engine_version="test", defines_hash="d" * 16
    )
    session_id = minted.campaign_id
    try:
        session = create_new_campaign(
            runtime,
            scenario=WayneCountyScenario(),
            session_id=session_id,
            progress_store=catalog,
        )
        after_create = catalog.get_campaign(session_id)
        assert after_create is not None
        assert after_create.last_tick == 0

        session.advance_tick()
        after_advance = catalog.get_campaign(session_id)
        assert after_advance is not None
        assert after_advance.last_tick == 1

        resumed = resume_campaign(runtime, session_id, progress_store=catalog)
        assert resumed.tick == 1
        after_resume = catalog.get_campaign(session_id)
        assert after_resume is not None
        assert after_resume.last_tick == 1
    finally:
        catalog.delete_campaign(session_id)
        with pg_pool.connection() as conn:
            conn.execute("DELETE FROM game_session WHERE id = %s", (session_id,))
