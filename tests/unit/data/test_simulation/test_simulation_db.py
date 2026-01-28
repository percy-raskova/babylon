"""Unit tests for SimulationDB class."""

from __future__ import annotations

import duckdb
import pytest

from babylon.data.simulation import SimulationDB


class TestSimulationDBCreation:
    """Tests for SimulationDB instantiation."""

    def test_create_in_memory_database(self) -> None:
        """SimulationDB can be created in-memory."""
        with SimulationDB(in_memory=True, attach_reference=False) as sim:
            assert sim.in_memory is True
            assert sim.db_path is None
            assert sim.con is not None

    def test_run_id_defaults_to_timestamp(self) -> None:
        """run_id should default to a timestamp-based identifier."""
        with SimulationDB(in_memory=True, attach_reference=False) as sim:
            assert sim.run_id.startswith("run_")
            assert len(sim.run_id) > 10  # Timestamp should be substantial

    def test_custom_run_id(self) -> None:
        """Custom run_id should be preserved."""
        with SimulationDB(
            run_id="test_run_123",
            in_memory=True,
            attach_reference=False,
        ) as sim:
            assert sim.run_id == "test_run_123"

    def test_repr_shows_memory(self) -> None:
        """repr should indicate :memory: for in-memory databases."""
        with SimulationDB(in_memory=True, attach_reference=False) as sim:
            repr_str = repr(sim)
            assert ":memory:" in repr_str
            assert sim.run_id in repr_str


class TestSimulationDBSchema:
    """Tests for schema creation."""

    def test_agent_state_table_exists(self) -> None:
        """agent_state table should be created."""
        with SimulationDB(in_memory=True, attach_reference=False) as sim:
            tables = sim.con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            table_names = [t[0] for t in tables]
            assert "agent_state" in table_names

    def test_production_event_table_exists(self) -> None:
        """production_event table should be created."""
        with SimulationDB(in_memory=True, attach_reference=False) as sim:
            tables = sim.con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            table_names = [t[0] for t in tables]
            assert "production_event" in table_names

    def test_network_edge_table_exists(self) -> None:
        """network_edge table should be created."""
        with SimulationDB(in_memory=True, attach_reference=False) as sim:
            tables = sim.con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            table_names = [t[0] for t in tables]
            assert "network_edge" in table_names

    def test_territorial_control_table_exists(self) -> None:
        """territorial_control table should be created."""
        with SimulationDB(in_memory=True, attach_reference=False) as sim:
            tables = sim.con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            table_names = [t[0] for t in tables]
            assert "territorial_control" in table_names

    def test_tick_summary_table_exists(self) -> None:
        """tick_summary table should be created."""
        with SimulationDB(in_memory=True, attach_reference=False) as sim:
            tables = sim.con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            table_names = [t[0] for t in tables]
            assert "tick_summary" in table_names

    def test_simulation_metadata_table_exists(self) -> None:
        """simulation_metadata table should be created."""
        with SimulationDB(in_memory=True, attach_reference=False) as sim:
            tables = sim.con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            table_names = [t[0] for t in tables]
            assert "simulation_metadata" in table_names


class TestTickSummaryRecording:
    """Tests for tick_summary recording."""

    def test_record_tick_summary_inserts_row(self) -> None:
        """record_tick_summary should insert a row."""
        with SimulationDB(in_memory=True, attach_reference=False) as sim:
            sim.record_tick_summary(
                tick=0,
                total_c=100.0,
                total_v=50.0,
                total_s=25.0,
                avg_consciousness=0.3,
                uprising_count=0,
            )

            result = sim.con.execute("SELECT * FROM tick_summary WHERE tick = 0").fetchone()
            assert result is not None
            assert result[0] == 0  # tick

    def test_record_tick_summary_calculates_exploitation_rate(self) -> None:
        """record_tick_summary should calculate exploitation rate (s/v)."""
        with SimulationDB(in_memory=True, attach_reference=False) as sim:
            sim.record_tick_summary(
                tick=1,
                total_c=100.0,
                total_v=50.0,
                total_s=25.0,  # s/v = 25/50 = 0.5
                avg_consciousness=0.3,
                uprising_count=0,
            )

            result = sim.con.execute(
                "SELECT exploitation_rate FROM tick_summary WHERE tick = 1"
            ).fetchone()
            assert result is not None
            assert abs(float(result[0]) - 0.5) < 0.001

    def test_record_tick_summary_calculates_profit_rate(self) -> None:
        """record_tick_summary should calculate profit rate (s/(c+v))."""
        with SimulationDB(in_memory=True, attach_reference=False) as sim:
            sim.record_tick_summary(
                tick=2,
                total_c=100.0,
                total_v=50.0,
                total_s=30.0,  # s/(c+v) = 30/150 = 0.2
                avg_consciousness=0.3,
                uprising_count=0,
            )

            result = sim.con.execute(
                "SELECT profit_rate FROM tick_summary WHERE tick = 2"
            ).fetchone()
            assert result is not None
            assert abs(float(result[0]) - 0.2) < 0.001

    def test_record_tick_summary_handles_zero_v(self) -> None:
        """record_tick_summary should handle zero variable capital."""
        with SimulationDB(in_memory=True, attach_reference=False) as sim:
            sim.record_tick_summary(
                tick=3,
                total_c=100.0,
                total_v=0.0,  # Zero wages
                total_s=0.0,
                avg_consciousness=0.0,
                uprising_count=0,
            )

            result = sim.con.execute(
                "SELECT exploitation_rate FROM tick_summary WHERE tick = 3"
            ).fetchone()
            assert result is not None
            assert result[0] == 0.0  # Should be 0, not NaN


class TestMetadataStorage:
    """Tests for simulation metadata."""

    def test_set_metadata_stores_value(self) -> None:
        """set_metadata should store key-value pair."""
        with SimulationDB(in_memory=True, attach_reference=False) as sim:
            sim.set_metadata("scenario", "baseline")

            result = sim.con.execute(
                "SELECT value FROM simulation_metadata WHERE key = 'scenario'"
            ).fetchone()
            assert result is not None
            assert result[0] == "baseline"

    def test_get_metadata_retrieves_value(self) -> None:
        """get_metadata should retrieve stored value."""
        with SimulationDB(in_memory=True, attach_reference=False) as sim:
            sim.set_metadata("config_hash", "abc123")
            value = sim.get_metadata("config_hash")
            assert value == "abc123"

    def test_get_metadata_returns_none_for_missing(self) -> None:
        """get_metadata should return None for missing keys."""
        with SimulationDB(in_memory=True, attach_reference=False) as sim:
            value = sim.get_metadata("nonexistent")
            assert value is None

    def test_set_metadata_upserts(self) -> None:
        """set_metadata should update existing key."""
        with SimulationDB(in_memory=True, attach_reference=False) as sim:
            sim.set_metadata("version", "1.0")
            sim.set_metadata("version", "2.0")

            value = sim.get_metadata("version")
            assert value == "2.0"


class TestTransactionContext:
    """Tests for transaction context manager."""

    def test_transaction_commits_on_success(self) -> None:
        """transaction should commit on successful exit."""
        with SimulationDB(in_memory=True, attach_reference=False) as sim:
            with sim.transaction() as con:
                con.execute(
                    """
                    INSERT INTO agent_state
                    (tick, agent_id, agent_type, consciousness, organization,
                     wealth_millions)
                    VALUES (0, 'worker_1', 'proletariat', 0.3, 0.2, 10.0)
                    """
                )

            # Verify row persisted after transaction
            result = sim.con.execute("SELECT COUNT(*) FROM agent_state").fetchone()
            assert result[0] == 1

    def test_transaction_rollbacks_on_exception(self) -> None:
        """transaction should rollback on exception."""
        with SimulationDB(in_memory=True, attach_reference=False) as sim:
            with pytest.raises(ValueError), sim.transaction() as con:
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
            result = sim.con.execute("SELECT COUNT(*) FROM agent_state").fetchone()
            assert result[0] == 0


class TestDirectSQLOperations:
    """Tests for direct SQL operations."""

    def test_insert_agent_state(self) -> None:
        """Can insert into agent_state table."""
        with SimulationDB(in_memory=True, attach_reference=False) as sim:
            sim.con.execute(
                """
                INSERT INTO agent_state
                (tick, agent_id, agent_type, county_id, consciousness,
                 organization, wealth_millions, ideology)
                VALUES (0, 'bourgeoisie_1', 'bourgeoisie', 6001, 0.1, 0.8, 1000.0,
                        'liberal')
                """
            )

            result = sim.con.execute(
                "SELECT agent_id, ideology FROM agent_state WHERE tick = 0"
            ).fetchone()
            assert result[0] == "bourgeoisie_1"
            assert result[1] == "liberal"

    def test_insert_production_event(self) -> None:
        """Can insert into production_event table."""
        with SimulationDB(in_memory=True, attach_reference=False) as sim:
            sim.con.execute(
                """
                INSERT INTO production_event
                (event_id, tick, territory_id, sector_code, c_millions,
                 v_millions, s_millions, workers)
                VALUES (1, 0, 'CA-06001', '31-33', 500.0, 200.0, 100.0, 5000)
                """
            )

            result = sim.con.execute(
                "SELECT c_millions, v_millions, s_millions FROM production_event"
            ).fetchone()
            assert result[0] == 500.0
            assert result[1] == 200.0
            assert result[2] == 100.0

    def test_insert_network_edge(self) -> None:
        """Can insert into network_edge table."""
        with SimulationDB(in_memory=True, attach_reference=False) as sim:
            sim.con.execute(
                """
                INSERT INTO network_edge
                (tick, source_id, target_id, edge_type, weight)
                VALUES (0, 'proletariat', 'bourgeoisie', 'EXPLOITATION', 0.85)
                """
            )

            result = sim.con.execute(
                "SELECT weight FROM network_edge WHERE edge_type = 'EXPLOITATION'"
            ).fetchone()
            assert abs(float(result[0]) - 0.85) < 0.001


class TestContextManager:
    """Tests for context manager protocol."""

    def test_context_manager_closes_connection(self) -> None:
        """Context manager should close connection on exit."""
        sim = SimulationDB(in_memory=True, attach_reference=False)
        with sim:
            # Connection should be open
            sim.con.execute("SELECT 1")

        # After exit, connection should be closed
        with pytest.raises(duckdb.ConnectionException):
            sim.con.execute("SELECT 1")

    def test_context_manager_closes_on_exception(self) -> None:
        """Context manager should close connection even on exception."""
        sim = SimulationDB(in_memory=True, attach_reference=False)
        with pytest.raises(ValueError), sim:
            raise ValueError("Intentional error")

        # Connection should still be closed
        with pytest.raises(duckdb.ConnectionException):
            sim.con.execute("SELECT 1")
