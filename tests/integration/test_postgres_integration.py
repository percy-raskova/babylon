"""Integration tests for PostgresRuntime (Feature 037).

Covers persistent state writing/reading, session isolation,
throughput, and trace overhead against a live PostgreSQL database.
Requires BABYLON_TEST_PG_DSN to be set.
"""

from __future__ import annotations

import time
import uuid

import networkx as nx
import pytest

from babylon.persistence.postgres_runtime import PostgresRuntime

# Mark all tests in this module as requiring the pg_pool fixture,
# which skips testing if PostgreSQL is unavailable.
pytestmark = pytest.mark.integration


@pytest.fixture
def runtime(pg_pool) -> PostgresRuntime:
    """Provides a configured PostgresRuntime connected to the test database."""
    return PostgresRuntime(pg_pool)


@pytest.fixture
def session_id(runtime: PostgresRuntime) -> uuid.UUID:
    """Unique session ID for each test."""
    return runtime.create_session(
        scenario="test_integration",
        config_json={},
        game_defines_json={},
        rng_seed=42,
    )


def build_large_graph(num_nodes: int = 1000) -> nx.DiGraph[str]:
    """Helper to build a large graph for throughput testing."""
    graph: nx.DiGraph[str] = nx.DiGraph()
    for i in range(num_nodes):
        graph.add_node(
            f"c_{i}",
            type="SocialClass",
            wealth=100.0,
            ideology={"class_consciousness": 0.5},
            organization=0.5,
            class_position="proletariat",
        )
    for i in range(num_nodes - 1):
        graph.add_edge(
            f"c_{i}",
            f"c_{i + 1}",
            type="EXPLOITATION",
            edge_mode="DIRECT",
            value_flow=10.0,
            tension=0.5,
            weight=1.0,
        )
    return graph


class TestPersistAndHydrateCycle:
    """T014: Full persist and hydrate cycle tests."""

    def test_round_trip_fidelity(self, runtime: PostgresRuntime, session_id: uuid.UUID) -> None:
        """Verify graph survives serialization directly to/from PostgreSQL."""
        graph = build_large_graph(10)

        # Add diverse attribute types
        graph.nodes["c_0"]["null_field"] = None
        graph.nodes["c_0"]["complex_list"] = [1, {"nested": True}, 3.14]

        # Persist
        runtime.persist_tick(tick=1, graph=graph, session_id=session_id)

        # Hydrate
        hydrated = runtime.hydrate_graph(tick=1, session_id=session_id)

        assert len(hydrated.nodes) == 10
        assert len(hydrated.edges) == 9

        # Complex attributes should be faithfully reconstructed via JSONB
        assert hydrated.nodes["c_0"]["null_field"] is None
        assert hydrated.nodes["c_0"]["complex_list"] == [1, {"nested": True}, 3.14]
        assert hydrated.nodes["c_0"]["wealth"] == 100.0


class TestSessionIsolation:
    """T033: Verify different sessions do not leak data."""

    def test_sessions_are_isolated(self, runtime: PostgresRuntime) -> None:
        """Data persisted in one session should not appear in another."""
        session_a = runtime.create_session(
            scenario="test_A", config_json={}, game_defines_json={}, rng_seed=1
        )
        session_b = runtime.create_session(
            scenario="test_B", config_json={}, game_defines_json={}, rng_seed=2
        )

        graph_a = build_large_graph(5)
        # B gets slightly different attributes to ensure isolation
        graph_b = build_large_graph(10)

        runtime.persist_tick(tick=1, graph=graph_a, session_id=session_a)
        runtime.persist_tick(tick=1, graph=graph_b, session_id=session_b)

        # Hydrate A and verify it only has 5 nodes
        hydrated_a = runtime.hydrate_graph(tick=1, session_id=session_a)
        assert len(hydrated_a.nodes) == 5

        # Hydrate B and verify it has 10 nodes
        hydrated_b = runtime.hydrate_graph(tick=1, session_id=session_b)
        assert len(hydrated_b.nodes) == 10


class TestThroughput:
    """T055: Write throughput and T060: Trace overhead benchmarking."""

    def test_large_graph_throughput(self, runtime: PostgresRuntime, session_id: uuid.UUID) -> None:
        """Verify large graphs can be persisted with acceptable latency."""
        # Note: True performance testing should use `pytest-benchmark`, but this
        # acts as a safety limit against gross inefficiencies (e.g. N+1 queries).
        graph = build_large_graph(2000)  # 2000 nodes, 1999 edges

        start = time.perf_counter()
        runtime.persist_tick(tick=1, graph=graph, session_id=session_id)
        duration = time.perf_counter() - start

        # A 2000-node graph should easily insert in < 1 second on any modern machine
        # via the psycopg3 executemany pipeline implementation.
        assert duration < 1.0


class TestConcurrentSessions:
    """T062: Concurrent session recording."""

    def test_interleaved_ticks(self, runtime: PostgresRuntime) -> None:
        """Verify multiple sessions can persist interleaved ticks without issue."""
        sessions = [
            runtime.create_session(
                scenario=f"test_conc_{i}", config_json={}, game_defines_json={}, rng_seed=i
            )
            for i in range(3)
        ]
        graph = build_large_graph(5)

        for tick in range(1, 4):
            for sid in sessions:
                # We modify the state slightly per tick to simulate progression
                graph.nodes["c_0"]["tick"] = tick
                runtime.persist_tick(tick=tick, graph=graph, session_id=sid)

        # Ensure all sessions can be independently hydrated to their max tick
        for sid in sessions:
            hydrated = runtime.hydrate_graph(session_id=sid)
            assert hydrated.nodes["c_0"]["tick"] == 3
