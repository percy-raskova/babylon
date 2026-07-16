"""PostgresRuntime branch of spec-056 US4 monotonic-idempotent tests
(T027). Mirrors the four predicates from
``tests/property/invariants/test_tick_persistence_monotonic.py`` against
``PostgresRuntime`` with a transient test database via the existing
``pg_pool`` fixture (``tests/conftest.py:250``).

Gated behind ``mise run test:integration`` via the
``pytestmark = pytest.mark.integration`` declaration.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from babylon.persistence import MonotonicityViolationError
from babylon.persistence.postgres_runtime import PostgresRuntime
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.integration


@pytest.fixture
def runtime(pg_pool) -> PostgresRuntime:
    """PostgresRuntime over the test database connection pool."""
    return PostgresRuntime(pg_pool)


@pytest.fixture
def session_id(runtime: PostgresRuntime) -> uuid.UUID:
    """Unique session ID per test."""
    return runtime.create_session(
        scenario="spec-056-us4",
        config_json={},
        game_defines_json={},
        rng_seed=42,
    )


def _payload_to_graph(marker: str, value: int) -> BabylonGraph:
    """One-node graph with a distinguishing payload."""
    g = BabylonGraph()
    g.add_node("payload_node", type="Test", marker=marker, value=value)
    return g


def _graph_payload(graph: BabylonGraph) -> dict:
    """Extract the payload dict from a hydrated graph."""
    if "payload_node" not in graph.nodes:
        return {}
    attrs = dict(graph.nodes["payload_node"])
    attrs.pop("type", None)
    attrs.pop("_node_type", None)
    return attrs


class TestPostgresMonotonicIdempotent:
    """INV-016 against PostgresRuntime — monotonic-idempotent contract."""

    def test_sequential_persists_succeed(
        self, runtime: PostgresRuntime, session_id: uuid.UUID
    ) -> None:
        """Predicate A: 5 sequential persists + reads."""
        payloads = [(N, f"marker_{N}", N * 10) for N in range(5)]
        for tick, marker, value in payloads:
            runtime.persist_tick(
                tick=tick, graph=_payload_to_graph(marker, value), session_id=session_id
            )
        for tick, marker, value in payloads:
            hydrated = runtime.hydrate_graph(tick=tick, session_id=session_id)
            actual = _graph_payload(hydrated)
            assert actual.get("marker") == marker
            assert actual.get("value") == value

    def test_different_payload_re_persist_raises(
        self, runtime: PostgresRuntime, session_id: uuid.UUID
    ) -> None:
        """Predicate B: different-payload re-persist raises
        MonotonicityViolationError; original payload survives."""
        runtime.persist_tick(tick=0, graph=_payload_to_graph("original", 42), session_id=session_id)
        with pytest.raises(MonotonicityViolationError) as exc_info:
            runtime.persist_tick(
                tick=0,
                graph=_payload_to_graph("different", 99),
                session_id=session_id,
            )
        assert exc_info.value.tick == 0

        hydrated = runtime.hydrate_graph(tick=0, session_id=session_id)
        actual = _graph_payload(hydrated)
        assert actual.get("marker") == "original"
        assert actual.get("value") == 42

    def test_same_payload_re_persist_idempotent(
        self, runtime: PostgresRuntime, session_id: uuid.UUID
    ) -> None:
        """Predicate B': same-payload re-persist succeeds idempotently —
        preserves observer/recorder retry semantics."""
        runtime.persist_tick(tick=0, graph=_payload_to_graph("same", 42), session_id=session_id)
        # Re-persist with IDENTICAL payload — must not raise
        runtime.persist_tick(tick=0, graph=_payload_to_graph("same", 42), session_id=session_id)
        hydrated = runtime.hydrate_graph(tick=0, session_id=session_id)
        actual = _graph_payload(hydrated)
        assert actual.get("marker") == "same"
        assert actual.get("value") == 42

    def test_back_in_time_rewrite_raises(
        self, runtime: PostgresRuntime, session_id: uuid.UUID
    ) -> None:
        """Predicate C: back-in-time rewrite of an already-persisted
        earlier tick raises; all 5 records remain intact."""
        for N in range(5):
            runtime.persist_tick(
                tick=N,
                graph=_payload_to_graph(f"marker_{N}", N * 10),
                session_id=session_id,
            )
        with pytest.raises(MonotonicityViolationError) as exc_info:
            runtime.persist_tick(
                tick=2,
                graph=_payload_to_graph("rewrite", 999),
                session_id=session_id,
            )
        assert exc_info.value.tick == 2

        # ALL 5 records intact
        for N in range(5):
            hydrated = runtime.hydrate_graph(tick=N, session_id=session_id)
            actual = _graph_payload(hydrated)
            assert actual.get("marker") == f"marker_{N}", (
                f"Tick {N}: failed-rewrite caused spurious side-effect"
            )
            assert actual.get("value") == N * 10

    def test_datetime_event_retry_is_idempotent(
        self, runtime: PostgresRuntime, session_id: uuid.UUID
    ) -> None:
        """P0 #6 regression: datetime-carrying events persist, and a retry
        differing only in timestamps is idempotent (Predicate B')."""
        graph = _payload_to_graph("with_events", 1)
        ev = {
            "type": "UPRISING",
            "entity_id": "payload_node",
            "timestamp": datetime(2026, 7, 8, 1, 0),
        }
        runtime.persist_tick(tick=0, graph=graph, events=[ev], session_id=session_id)

        retry = dict(ev, timestamp=datetime(2026, 7, 8, 1, 5))
        runtime.persist_tick(tick=0, graph=graph, events=[retry], session_id=session_id)

        different = dict(ev, entity_id="other")
        with pytest.raises(MonotonicityViolationError):
            runtime.persist_tick(tick=0, graph=graph, events=[different], session_id=session_id)


class TestSimulationEventTypeKey:
    """spec-113 engine defect: ``_persist_events`` must read the ``"event_type"``
    key — the field name on ``SimulationEvent`` and therefore the key
    ``model_dump(mode="json")`` emits — not ``"type"``. Reading ``"type"``
    persisted EVERY event as ``"UNKNOWN"``, so two distinct events at one tick
    collapsed onto the same ``ux_simulation_event_session_tick_natural`` key
    (resolve-loop UniqueViolation, session death ~tick 18) and the web layer
    never saw a real type (silent wire / no toasts)."""

    def test_distinct_event_types_at_one_tick_persist_as_distinct_rows(
        self, runtime: PostgresRuntime, session_id: uuid.UUID, pg_pool
    ) -> None:
        # Same tick, same (empty) entity, DIFFERENT event_type. Pre-fix both
        # serialized to "UNKNOWN" -> identical natural key -> UniqueViolation
        # inside persist_tick's transaction. Post-fix they carry real, distinct
        # types and both rows land.
        events = [
            {"event_type": "SURPLUS_EXTRACTION", "tick": 4},
            {"event_type": "RADICALIZATION", "tick": 4},
        ]
        runtime.persist_tick(
            tick=4, graph=_payload_to_graph("evt", 1), events=events, session_id=session_id
        )
        with pg_pool.connection() as conn:
            rows = conn.execute(
                "SELECT event_type FROM simulation_event "
                "WHERE session_id = %s AND tick = %s ORDER BY event_type",
                (session_id, 4),
            ).fetchall()
        assert [r[0] for r in rows] == ["RADICALIZATION", "SURPLUS_EXTRACTION"]
