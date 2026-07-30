"""Torn-tick recovery tests (ADR176 ruling 28 — the P-J defect train).

The tear (``reports/postgres-brief-2026-07-29.md`` §D1): the interactive
session persisted the adjudicating topology (``node_state``/``edge_state``/
graph metadata) in its OWN transaction (``persist_tick``), separate from
the envelope + ``tick_commit`` marker (``persist_tick_atomic``). A crash
between the two leaves topology rows for a tick whose commit marker never
landed — and ``hydrate_graph(tick=None)`` resolved "latest" via
``MAX(tick) FROM node_state``, the documented anti-pattern (``CLAUDE.md``:
``MAX(tick)`` != last committed tick) applied to the graph: the engine
could rehydrate from a torn tick.

The law these tests pin (the fix, ruling 28's declared freeze exception +
ruling 31's checkpoint-only-hydration direction): ``tick_commit`` is the
ONLY adjudicator of "latest" — ``hydrate_graph(tick=None)`` returns the
last COMMITTED tick's graph no matter what uncommitted topology rows
exist beyond it; and the topology rides ``persist_tick_atomic``'s single
transaction, so a mid-envelope failure leaves NO topology rows at all.

Same pg_pool gating as the sibling atomicity suite: integration-marked,
skips cleanly when Postgres is unavailable.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from babylon.persistence.envelope import PerTickTransactionEnvelope
from babylon.persistence.postgres_runtime import PostgresRuntime
from babylon.topology.graph import BabylonGraph

pytestmark = [pytest.mark.integration]


@pytest.fixture
def migrated(pg_pool):  # type: ignore[no-untyped-def]
    """Apply the full migration chain (idempotent; digest-stamped).

    ``tick_commit`` (migration 0029) MUST exist for these tests to mean
    anything: ``persist_tick_atomic`` gracefully skips the marker on
    pre-0029 databases, and a silently-skipped marker would make the
    torn-tick reproduction pass vacuously.
    """
    from babylon.persistence.postgres_schema import ensure_ddl_applied

    migrations_dir = Path("src/babylon/persistence/migrations").resolve()
    sql_files = sorted(migrations_dir.glob("00*.sql"))
    assert sql_files, "expected the migration chain to exist"
    with pg_pool.connection() as conn:
        conn.autocommit = True
        ensure_ddl_applied(conn, [sql_file.read_text() for sql_file in sql_files])


@pytest.fixture
def runtime(pg_pool, migrated) -> PostgresRuntime:  # type: ignore[no-untyped-def]
    """PostgresRuntime over the test pool with the full schema applied."""
    return PostgresRuntime(pg_pool)


@pytest.fixture
def session_id(runtime: PostgresRuntime) -> uuid.UUID:
    """Unique session ID per test."""
    return runtime.create_session(
        scenario="torn-tick-recovery",
        config_json={},
        game_defines_json={},
        rng_seed=42,
    )


def _graph(marker: str) -> BabylonGraph:
    """One-node graph with a distinguishing payload (sibling-suite style)."""
    g = BabylonGraph()
    g.add_node("payload_node", type="Test", marker=marker)
    return g


def _marker_of(graph: BabylonGraph) -> str | None:
    if "payload_node" not in graph.nodes:
        return None
    return dict(graph.nodes["payload_node"]).get("marker")


def _envelope(session_id: uuid.UUID, tick: int) -> PerTickTransactionEnvelope:
    return PerTickTransactionEnvelope(
        session_id=session_id,
        tick=tick,
        determinism_hash="0" * 64,
    )


class TestTornTickNeverAdjudicates:
    """``hydrate_graph(tick=None)`` reads only COMMITTED ticks."""

    def test_topology_beyond_the_last_commit_marker_never_hydrates(
        self, runtime: PostgresRuntime, session_id: uuid.UUID
    ) -> None:
        """The torn-tick reproduction: tick 1 fully committed (topology +
        marker); tick 2's topology written with NO marker — exactly the
        state a crash between the session's two transactions left behind.
        Latest-hydration must return tick 1's graph, never tick 2's."""
        runtime.persist_tick(tick=1, graph=_graph("committed"), session_id=session_id)
        runtime.persist_tick_atomic(_envelope(session_id, 1))

        # The tear: adjudicating topology lands, the commit marker does not.
        runtime.persist_tick(tick=2, graph=_graph("torn"), session_id=session_id)

        assert runtime.get_last_committed_tick(session_id) == 1
        hydrated = runtime.hydrate_graph(tick=None, session_id=session_id)
        assert _marker_of(hydrated) == "committed", (
            "hydrate_graph(tick=None) adjudicated a tick with no tick_commit "
            "marker — the MAX(tick)-from-node_state anti-pattern rehydrates "
            "the engine from a torn tick (postgres brief §D1)"
        )

    def test_no_committed_tick_hydrates_empty_even_when_torn_rows_exist(
        self, runtime: PostgresRuntime, session_id: uuid.UUID
    ) -> None:
        """A session whose ONLY topology rows are torn (no marker anywhere)
        hydrates honestly empty — nothing committed is nothing to load."""
        runtime.persist_tick(tick=1, graph=_graph("torn"), session_id=session_id)

        assert runtime.get_last_committed_tick(session_id) is None
        hydrated = runtime.hydrate_graph(tick=None, session_id=session_id)
        assert _marker_of(hydrated) is None

    def test_explicit_tick_hydration_is_unchanged(
        self, runtime: PostgresRuntime, session_id: uuid.UUID
    ) -> None:
        """An explicitly-requested tick still hydrates whatever rows exist —
        forensic reads of a torn tick stay possible; only the LATEST
        resolution adjudicates through tick_commit."""
        runtime.persist_tick(tick=3, graph=_graph("forensic"), session_id=session_id)
        hydrated = runtime.hydrate_graph(tick=3, session_id=session_id)
        assert _marker_of(hydrated) == "forensic"


class TestTopologyRidesTheEnvelope:
    """The single-transaction closure: graph rows commit with the marker."""

    def test_atomic_persist_carries_the_graph(
        self, runtime: PostgresRuntime, session_id: uuid.UUID
    ) -> None:
        """One call persists topology + envelope + marker together; the
        committed graph hydrates as latest."""
        runtime.persist_tick_atomic(_envelope(session_id, 1), graph=_graph("atomic"))

        assert runtime.get_last_committed_tick(session_id) == 1
        hydrated = runtime.hydrate_graph(tick=None, session_id=session_id)
        assert _marker_of(hydrated) == "atomic"

    def test_mid_envelope_failure_leaves_no_topology_rows(
        self, runtime: PostgresRuntime, session_id: uuid.UUID, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A failure AFTER the graph writes but INSIDE the envelope
        transaction rolls the topology back with everything else — the
        crash window between 'graph landed' and 'marker landed' no longer
        exists. The commit-marker INSERT is poisoned to simulate the crash
        at the worst possible point."""
        import babylon.persistence.postgres_runtime._spec_062 as spec_062

        monkeypatch.setattr(
            spec_062, "_TICK_COMMIT_INSERT", "INSERT INTO tick_commit (nonexistent) VALUES (1)"
        )
        with pytest.raises(Exception):  # noqa: B017, PT011 - any DB error proves the rollback path
            runtime.persist_tick_atomic(_envelope(session_id, 1), graph=_graph("crashed"))

        with runtime._pool.connection() as conn:  # noqa: SLF001 - forensic read
            count = conn.execute(
                "SELECT COUNT(*) FROM node_state WHERE session_id = %s AND tick = 1",
                (str(session_id),),
            ).fetchone()
        assert count is not None and count[0] == 0, (
            "topology rows survived a failed envelope transaction — the "
            "torn-tick crash window is still open"
        )
