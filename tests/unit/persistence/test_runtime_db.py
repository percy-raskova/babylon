"""Unit tests for RuntimeDatabase (TDD-style).

Tests focus on:
1. Schema creation and table existence
2. Tick-keyed temporal queries (ADR031)
3. Graph round-trip integrity (common gotcha: losing mutations)
4. Event persistence (per-tick, not cumulative)
5. Metadata storage
6. Transaction semantics
7. Edge cases: empty graphs, missing data, concurrent access
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

import networkx as nx
import pytest

from babylon.engine.graph import BabylonGraph
from babylon.persistence import RuntimeDatabase


class TestRuntimeDatabaseCreation:
    """Tests for RuntimeDatabase instantiation."""

    def test_create_in_memory_database(self) -> None:
        """RuntimeDatabase can be created in-memory."""
        with RuntimeDatabase(in_memory=True) as db:
            assert db.in_memory is True
            assert db.db_path is None
            assert db.con is not None

    def test_run_id_defaults_to_timestamp(self) -> None:
        """run_id should default to a timestamp-based identifier."""
        with RuntimeDatabase(in_memory=True) as db:
            assert db.run_id.startswith("run_")
            assert len(db.run_id) > 10  # Timestamp should be substantial

    def test_custom_run_id(self) -> None:
        """Custom run_id should be preserved."""
        with RuntimeDatabase(run_id="test_run_123", in_memory=True) as db:
            assert db.run_id == "test_run_123"

    def test_repr_shows_memory(self) -> None:
        """repr should indicate :memory: for in-memory databases."""
        with RuntimeDatabase(in_memory=True) as db:
            repr_str = repr(db)
            assert ":memory:" in repr_str
            assert db.run_id in repr_str


class TestRuntimeDatabaseSchema:
    """Tests for schema creation - verify all tables exist."""

    def test_node_history_table_exists(self) -> None:
        """node_history table should be created."""
        with RuntimeDatabase(in_memory=True) as db:
            tables = self._get_tables(db)
            assert "node_history" in tables

    def test_edge_history_table_exists(self) -> None:
        """edge_history table should be created."""
        with RuntimeDatabase(in_memory=True) as db:
            tables = self._get_tables(db)
            assert "edge_history" in tables

    def test_events_table_exists(self) -> None:
        """events table should be created."""
        with RuntimeDatabase(in_memory=True) as db:
            tables = self._get_tables(db)
            assert "events" in tables

    def test_tick_log_table_exists(self) -> None:
        """tick_log table should be created (ADR033)."""
        with RuntimeDatabase(in_memory=True) as db:
            tables = self._get_tables(db)
            assert "tick_log" in tables

    def test_simulation_metadata_table_exists(self) -> None:
        """simulation_metadata table should be created."""
        with RuntimeDatabase(in_memory=True) as db:
            tables = self._get_tables(db)
            assert "simulation_metadata" in tables

    def test_legacy_agent_state_table_exists(self) -> None:
        """agent_state table should exist for API compatibility."""
        with RuntimeDatabase(in_memory=True) as db:
            tables = self._get_tables(db)
            assert "agent_state" in tables

    def test_legacy_tick_summary_table_exists(self) -> None:
        """tick_summary table should exist for API compatibility."""
        with RuntimeDatabase(in_memory=True) as db:
            tables = self._get_tables(db)
            assert "tick_summary" in tables

    def _get_tables(self, db: RuntimeDatabase) -> list[str]:
        """Helper to get list of table names."""
        result = db.con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return [row[0] for row in result]


class TestGraphPersistence:
    """Tests for graph snapshot persistence (ADR031/032).

    CRITICAL: These tests verify the graph round-trip preserves all attributes.
    This is a common gotcha - mutations can be lost during serialization.
    """

    def test_persist_empty_graph(self) -> None:
        """Persisting empty graph should not fail."""
        with RuntimeDatabase(in_memory=True) as db:
            graph: nx.DiGraph = BabylonGraph()
            db.persist_tick(tick=0, graph=graph)

            # Verify no crash and empty result
            loaded = db.hydrate_graph(tick=0)
            assert len(loaded.nodes()) == 0
            assert len(loaded.edges()) == 0

    def test_persist_and_hydrate_nodes(self) -> None:
        """Nodes should round-trip with all attributes preserved."""
        with RuntimeDatabase(in_memory=True) as db:
            graph: nx.DiGraph = BabylonGraph()
            graph.add_node(
                "proletariat_detroit",
                type="SocialClass",
                wealth=50.0,
                consciousness=0.3,
                organization=0.2,
                ideology="neutral",
            )
            graph.add_node(
                "bourgeoisie_detroit",
                type="SocialClass",
                wealth=1000.0,
                consciousness=0.1,
                organization=0.8,
                ideology="liberal",
            )

            db.persist_tick(tick=0, graph=graph)
            loaded = db.hydrate_graph(tick=0)

            assert len(loaded.nodes()) == 2
            assert "proletariat_detroit" in loaded.nodes()
            assert "bourgeoisie_detroit" in loaded.nodes()

            # Verify attributes preserved (common gotcha: losing mutations)
            prole_data = loaded.nodes["proletariat_detroit"]
            assert prole_data["wealth"] == 50.0
            assert prole_data["consciousness"] == 0.3
            assert prole_data["organization"] == 0.2
            assert prole_data["ideology"] == "neutral"
            assert prole_data["type"] == "SocialClass"

    def test_persist_and_hydrate_edges(self) -> None:
        """Edges should round-trip with all attributes preserved."""
        with RuntimeDatabase(in_memory=True) as db:
            graph: nx.DiGraph = BabylonGraph()
            graph.add_node("proletariat", type="SocialClass")
            graph.add_node("bourgeoisie", type="SocialClass")
            graph.add_edge(
                "proletariat",
                "bourgeoisie",
                type="EXPLOITATION",
                weight=0.85,
                extraction_rate=0.3,
            )

            db.persist_tick(tick=0, graph=graph)
            loaded = db.hydrate_graph(tick=0)

            assert loaded.has_edge("proletariat", "bourgeoisie")
            edge_data = loaded.edges["proletariat", "bourgeoisie"]
            assert edge_data["type"] == "EXPLOITATION"
            assert edge_data["weight"] == 0.85
            assert edge_data["extraction_rate"] == 0.3

    def test_tick_keyed_isolation(self) -> None:
        """State at different ticks should be isolated (ADR031).

        Each tick is a complete snapshot. Loading tick N should not
        include mutations from tick N+1.
        """
        with RuntimeDatabase(in_memory=True) as db:
            # Tick 0: proletariat has wealth=50
            graph0: nx.DiGraph = BabylonGraph()
            graph0.add_node("proletariat", type="SocialClass", wealth=50.0)
            db.persist_tick(tick=0, graph=graph0)

            # Tick 1: proletariat has wealth=40 (extracted)
            graph1: nx.DiGraph = BabylonGraph()
            graph1.add_node("proletariat", type="SocialClass", wealth=40.0)
            db.persist_tick(tick=1, graph=graph1)

            # Loading tick 0 should give wealth=50
            loaded0 = db.hydrate_graph(tick=0)
            assert loaded0.nodes["proletariat"]["wealth"] == 50.0

            # Loading tick 1 should give wealth=40
            loaded1 = db.hydrate_graph(tick=1)
            assert loaded1.nodes["proletariat"]["wealth"] == 40.0

    def test_hydrate_latest_tick(self) -> None:
        """hydrate_graph(tick=None) should load the latest tick."""
        with RuntimeDatabase(in_memory=True) as db:
            for tick in range(5):
                graph: nx.DiGraph = BabylonGraph()
                graph.add_node("test", type="Test", tick_value=tick)
                db.persist_tick(tick=tick, graph=graph)

            latest = db.hydrate_graph(tick=None)
            assert latest.nodes["test"]["tick_value"] == 4

    def test_persist_same_payload_is_idempotent(self) -> None:
        """Spec 056 (F7=B): re-persisting the same tick with the SAME
        payload succeeds idempotently — preserves the canonical
        UPSERT-retry pattern used by ``persistence_observer.py:146``
        and ``session_recorder.py:168``.

        Pre-spec-056 contract was "INSERT OR REPLACE" (silent upsert
        on any re-persist). The contract is now monotonic-idempotent:
        same payload OK, different payload raises (see the paired
        ``test_persist_different_payload_raises`` below).
        """
        with RuntimeDatabase(in_memory=True) as db:
            graph: nx.DiGraph = BabylonGraph()
            graph.add_node("node1", type="Test", value=1)
            db.persist_tick(tick=0, graph=graph)

            # Re-persist with IDENTICAL payload — must succeed silently
            graph_identical: nx.DiGraph = BabylonGraph()
            graph_identical.add_node("node1", type="Test", value=1)
            db.persist_tick(tick=0, graph=graph_identical)  # no exception

            loaded = db.hydrate_graph(tick=0)
            assert loaded.nodes["node1"]["value"] == 1

            # Verify only one row in database (no duplication)
            count = db.con.execute("SELECT COUNT(*) FROM node_history WHERE tick = 0").fetchone()[0]
            assert count == 1

    def test_persist_different_payload_raises(self) -> None:
        """Spec 056 (F7=B): re-persisting the same tick with a
        DIFFERENT payload raises ``MonotonicityViolationError`` —
        blocks silent rewrite of historical state per Constitution
        II.6 + III.7.

        This replaces the pre-spec-056 ``test_persist_overwrites_same_tick``
        test (which asserted UPSERT semantics that the new monotonic
        contract forbids).
        """
        import pytest

        from babylon.persistence import MonotonicityViolationError

        with RuntimeDatabase(in_memory=True) as db:
            graph: nx.DiGraph = BabylonGraph()
            graph.add_node("node1", type="Test", value=1)
            db.persist_tick(tick=0, graph=graph)

            # Re-persist with DIFFERENT payload — must raise
            graph_different: nx.DiGraph = BabylonGraph()
            graph_different.add_node("node1", type="Test", value=2)

            with pytest.raises(MonotonicityViolationError) as exc_info:
                db.persist_tick(tick=0, graph=graph_different)

            assert exc_info.value.tick == 0

            # After the failed write, original payload must still be returned
            loaded = db.hydrate_graph(tick=0)
            assert loaded.nodes["node1"]["value"] == 1  # original, not 2


class TestEventPersistence:
    """Tests for event persistence.

    CRITICAL: Events are PER-TICK, not cumulative. Each tick has its own events.
    """

    def test_persist_events(self) -> None:
        """Events should be persisted with tick."""
        with RuntimeDatabase(in_memory=True) as db:
            graph: nx.DiGraph = BabylonGraph()
            events = [
                {"type": "UPRISING", "entity_id": "proletariat", "intensity": 0.8},
                {"type": "REPRESSION", "entity_id": "state", "force": 0.5},
            ]
            db.persist_tick(tick=0, graph=graph, events=events)

            loaded_events = db.get_events(tick=0)
            assert len(loaded_events) == 2
            assert loaded_events[0]["type"] == "UPRISING"
            assert loaded_events[1]["type"] == "REPRESSION"

    def test_persist_events_with_datetime_timestamp(self) -> None:
        """Bug P0 #6: SimulationEvent.model_dump() carries a datetime timestamp.

        The persist path must serialize it (isoformat) instead of raising
        ``TypeError: Object of type datetime is not JSON serializable``.
        """
        with RuntimeDatabase(in_memory=True) as db:
            graph: nx.DiGraph = BabylonGraph()
            graph.add_node("w1", type="SocialClass")
            events = [
                {"type": "UPRISING", "entity_id": "w1", "timestamp": datetime(2026, 7, 8, 1, 0)},
            ]
            db.persist_tick(tick=0, graph=graph, events=events)

            loaded_events = db.get_events(tick=0)
            assert len(loaded_events) == 1
            assert loaded_events[0]["timestamp"] == "2026-07-08T01:00:00"

    def test_retry_with_regenerated_timestamp_is_idempotent(self) -> None:
        """Spec-056 B': a retry differing only in event wall-clock timestamps
        must return silently, not raise MonotonicityViolationError."""
        with RuntimeDatabase(in_memory=True) as db:
            graph: nx.DiGraph = BabylonGraph()
            graph.add_node("w1", type="SocialClass")
            ev = {"type": "UPRISING", "entity_id": "w1", "timestamp": datetime(2026, 7, 8, 1, 0)}
            db.persist_tick(tick=0, graph=graph, events=[ev])

            retry = dict(ev, timestamp=datetime(2026, 7, 8, 1, 5))
            db.persist_tick(tick=0, graph=graph, events=[retry])  # must NOT raise

            # ... and must not duplicate the event row
            assert len(db.get_events(tick=0)) == 1

    def test_events_are_per_tick_not_cumulative(self) -> None:
        """Events should be isolated per tick (common gotcha)."""
        with RuntimeDatabase(in_memory=True) as db:
            graph: nx.DiGraph = BabylonGraph()

            # Tick 0: one event
            db.persist_tick(tick=0, graph=graph, events=[{"type": "EVENT_A"}])

            # Tick 1: different event
            db.persist_tick(tick=1, graph=graph, events=[{"type": "EVENT_B"}])

            # Loading tick 0 events should NOT include tick 1 events
            tick0_events = db.get_events(tick=0)
            assert len(tick0_events) == 1
            assert tick0_events[0]["type"] == "EVENT_A"

            tick1_events = db.get_events(tick=1)
            assert len(tick1_events) == 1
            assert tick1_events[0]["type"] == "EVENT_B"

    def test_get_all_events(self) -> None:
        """get_events(tick=None) should return all events ordered."""
        with RuntimeDatabase(in_memory=True) as db:
            graph: nx.DiGraph = BabylonGraph()
            db.persist_tick(tick=0, graph=graph, events=[{"type": "A"}])
            db.persist_tick(tick=1, graph=graph, events=[{"type": "B"}, {"type": "C"}])

            all_events = db.get_events(tick=None)
            assert len(all_events) == 3
            # Should be ordered by tick, then event_id
            assert all_events[0]["type"] == "A"
            assert all_events[1]["type"] == "B"
            assert all_events[2]["type"] == "C"


class TestTickSummaryRecording:
    """Tests for tick_summary recording (legacy API compatibility)."""

    def test_record_tick_summary_inserts_row(self) -> None:
        """record_tick_summary should insert a row."""
        with RuntimeDatabase(in_memory=True) as db:
            db.record_tick_summary(
                tick=0,
                total_c=100.0,
                total_v=50.0,
                total_s=25.0,
                avg_consciousness=0.3,
                uprising_count=0,
            )

            result = db.con.execute("SELECT * FROM tick_summary WHERE tick = 0").fetchone()
            assert result is not None
            assert result[0] == 0  # tick

    def test_record_tick_summary_calculates_exploitation_rate(self) -> None:
        """record_tick_summary should calculate exploitation rate (s/v)."""
        with RuntimeDatabase(in_memory=True) as db:
            db.record_tick_summary(
                tick=1,
                total_c=100.0,
                total_v=50.0,
                total_s=25.0,  # s/v = 25/50 = 0.5
                avg_consciousness=0.3,
                uprising_count=0,
            )

            result = db.con.execute(
                "SELECT exploitation_rate FROM tick_summary WHERE tick = 1"
            ).fetchone()
            assert result is not None
            assert abs(result[0] - 0.5) < 0.001

    def test_record_tick_summary_calculates_profit_rate(self) -> None:
        """record_tick_summary should calculate profit rate (s/(c+v))."""
        with RuntimeDatabase(in_memory=True) as db:
            db.record_tick_summary(
                tick=2,
                total_c=100.0,
                total_v=50.0,
                total_s=30.0,  # s/(c+v) = 30/150 = 0.2
                avg_consciousness=0.3,
                uprising_count=0,
            )

            result = db.con.execute(
                "SELECT profit_rate FROM tick_summary WHERE tick = 2"
            ).fetchone()
            assert result is not None
            assert abs(result[0] - 0.2) < 0.001

    def test_record_tick_summary_handles_zero_v(self) -> None:
        """record_tick_summary should handle zero variable capital."""
        with RuntimeDatabase(in_memory=True) as db:
            db.record_tick_summary(
                tick=3,
                total_c=100.0,
                total_v=0.0,  # Zero wages
                total_s=0.0,
                avg_consciousness=0.0,
                uprising_count=0,
            )

            result = db.con.execute(
                "SELECT exploitation_rate FROM tick_summary WHERE tick = 3"
            ).fetchone()
            assert result is not None
            assert result[0] == 0.0  # Should be 0, not NaN


class TestMetadataStorage:
    """Tests for simulation metadata."""

    def test_set_metadata_stores_value(self) -> None:
        """set_metadata should store key-value pair."""
        with RuntimeDatabase(in_memory=True) as db:
            db.set_metadata("scenario", "baseline")

            result = db.con.execute(
                "SELECT value FROM simulation_metadata WHERE key = 'scenario'"
            ).fetchone()
            assert result is not None
            assert result[0] == "baseline"

    def test_get_metadata_retrieves_value(self) -> None:
        """get_metadata should retrieve stored value."""
        with RuntimeDatabase(in_memory=True) as db:
            db.set_metadata("config_hash", "abc123")
            value = db.get_metadata("config_hash")
            assert value == "abc123"

    def test_get_metadata_returns_none_for_missing(self) -> None:
        """get_metadata should return None for missing keys."""
        with RuntimeDatabase(in_memory=True) as db:
            value = db.get_metadata("nonexistent")
            assert value is None

    def test_set_metadata_upserts(self) -> None:
        """set_metadata should update existing key."""
        with RuntimeDatabase(in_memory=True) as db:
            db.set_metadata("version", "1.0")
            db.set_metadata("version", "2.0")

            value = db.get_metadata("version")
            assert value == "2.0"


class TestTickLog:
    """Tests for tick_log (ADR033 deterministic replay)."""

    def test_log_tick_stores_data(self) -> None:
        """log_tick should store replay data."""
        with RuntimeDatabase(in_memory=True) as db:
            db.log_tick(
                tick=0,
                rng_state=b"random_state_bytes",
                mutations={"wealth_delta": {"proletariat": -10.0}},
                invariant_checks={"positive_wealth": True, "valid_probabilities": True},
                wall_time_ms=150,
            )

            log = db.get_tick_log(tick=0)
            assert log is not None
            assert log["rng_state"] == b"random_state_bytes"
            assert log["mutations"]["wealth_delta"]["proletariat"] == -10.0
            assert log["invariant_checks"]["positive_wealth"] is True
            assert log["wall_time_ms"] == 150

    def test_get_tick_log_returns_none_for_missing(self) -> None:
        """get_tick_log should return None for non-existent tick."""
        with RuntimeDatabase(in_memory=True) as db:
            log = db.get_tick_log(tick=999)
            assert log is None


class TestTransactionContext:
    """Tests for transaction context manager."""

    def test_transaction_commits_on_success(self) -> None:
        """transaction should commit on successful exit."""
        with RuntimeDatabase(in_memory=True) as db:
            with db.transaction() as con:
                con.execute(
                    """
                    INSERT INTO agent_state
                    (tick, agent_id, agent_type, consciousness, organization,
                     wealth_millions)
                    VALUES (0, 'worker_1', 'proletariat', 0.3, 0.2, 10.0)
                    """
                )

            # Verify row persisted after transaction
            result = db.con.execute("SELECT COUNT(*) FROM agent_state").fetchone()
            assert result[0] == 1

    def test_transaction_rollbacks_on_exception(self) -> None:
        """transaction should rollback on exception."""
        with RuntimeDatabase(in_memory=True) as db:
            with pytest.raises(ValueError), db.transaction() as con:
                con.execute(
                    """
                    INSERT INTO agent_state
                    (tick, agent_id, agent_type, consciousness, organization,
                     wealth_millions)
                    VALUES (0, 'worker_1', 'proletariat', 0.3, 0.2, 10.0)
                    """
                )
                raise ValueError("Intentional error")

            # Verify row was not persisted
            result = db.con.execute("SELECT COUNT(*) FROM agent_state").fetchone()
            assert result[0] == 0


class TestContextManager:
    """Tests for context manager protocol."""

    def test_context_manager_closes_connection(self) -> None:
        """Context manager should close connection on exit."""
        db = RuntimeDatabase(in_memory=True)
        with db:
            # Connection should be open
            db.con.execute("SELECT 1")

        # After exit, connection should be closed
        with pytest.raises(sqlite3.ProgrammingError):
            db.con.execute("SELECT 1")

    def test_context_manager_closes_on_exception(self) -> None:
        """Context manager should close connection even on exception."""
        db = RuntimeDatabase(in_memory=True)
        with pytest.raises(ValueError), db:
            raise ValueError("Intentional error")

        # Connection should still be closed
        with pytest.raises(sqlite3.ProgrammingError):
            db.con.execute("SELECT 1")


class TestEdgeCases:
    """Edge cases and potential failure modes."""

    def test_persist_non_serializable_attribute_is_skipped(self) -> None:
        """Non-JSON-serializable attributes should be skipped, not crash."""
        with RuntimeDatabase(in_memory=True) as db:
            graph: nx.DiGraph = BabylonGraph()
            # Add a node with a non-serializable attribute
            graph.add_node(
                "test",
                type="Test",
                serializable=42,
                non_serializable=lambda x: x,  # Functions are not JSON serializable
            )

            # Should not raise
            db.persist_tick(tick=0, graph=graph)

            loaded = db.hydrate_graph(tick=0)
            # Serializable attribute should be preserved
            assert loaded.nodes["test"]["serializable"] == 42
            # Non-serializable attribute should be skipped
            assert "non_serializable" not in loaded.nodes["test"]

    def test_persist_multiple_edge_types_between_same_nodes(self) -> None:
        """Multiple edge types between same nodes should all be preserved."""
        with RuntimeDatabase(in_memory=True) as db:
            graph: nx.DiGraph = BabylonGraph()
            graph.add_node("A", type="Test")
            graph.add_node("B", type="Test")

            # In NetworkX DiGraph, we can't have multiple edges with same (src, tgt)
            # but we store edge_type as part of the key in our schema
            # So this tests that a single edge is properly stored
            graph.add_edge("A", "B", type="EXPLOITATION", weight=0.5)

            db.persist_tick(tick=0, graph=graph)
            loaded = db.hydrate_graph(tick=0)

            assert loaded.has_edge("A", "B")
            assert loaded.edges["A", "B"]["type"] == "EXPLOITATION"

    def test_hydrate_empty_database_returns_empty_graph(self) -> None:
        """Hydrating from empty database should return empty graph."""
        with RuntimeDatabase(in_memory=True) as db:
            graph = db.hydrate_graph(tick=0)
            assert len(graph.nodes()) == 0
            assert len(graph.edges()) == 0

    def test_unicode_in_attributes(self) -> None:
        """Unicode strings in attributes should round-trip correctly."""
        with RuntimeDatabase(in_memory=True) as db:
            graph: nx.DiGraph = BabylonGraph()
            graph.add_node(
                "test",
                type="Test",
                name="工人阶级",  # Chinese for "working class"
                description="Пролетариат",  # Russian for "Proletariat"
            )

            db.persist_tick(tick=0, graph=graph)
            loaded = db.hydrate_graph(tick=0)

            assert loaded.nodes["test"]["name"] == "工人阶级"
            assert loaded.nodes["test"]["description"] == "Пролетариат"

    def test_nested_dict_in_attributes(self) -> None:
        """Nested dictionaries in attributes should round-trip."""
        with RuntimeDatabase(in_memory=True) as db:
            graph: nx.DiGraph = BabylonGraph()
            graph.add_node(
                "test",
                type="Test",
                nested={
                    "level1": {"level2": {"value": 42}},
                    "list": [1, 2, 3],
                },
            )

            db.persist_tick(tick=0, graph=graph)
            loaded = db.hydrate_graph(tick=0)

            assert loaded.nodes["test"]["nested"]["level1"]["level2"]["value"] == 42
            assert loaded.nodes["test"]["nested"]["list"] == [1, 2, 3]
