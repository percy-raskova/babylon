"""Unit tests for PostgresRuntime trace and spatial query methods.

Phase 6 (T034-T038): Trace debugging.
Phase 7 (T039-T042): Spatial queries.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from babylon.persistence.postgres_runtime import PostgresRuntime
from babylon.persistence.protocols import TraceLevel
from babylon.persistence.trace_recorder import TraceRecorder

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture()
def session_id() -> UUID:
    return UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture()
def mock_cursor() -> MagicMock:
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchone = MagicMock(return_value=None)
    cursor.fetchall = MagicMock(return_value=[])
    cursor.rowcount = 0
    return cursor


@pytest.fixture()
def mock_conn(mock_cursor: MagicMock) -> MagicMock:
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor = MagicMock(return_value=mock_cursor)

    @contextmanager
    def mock_transaction() -> Any:
        yield

    conn.transaction = mock_transaction
    return conn


@pytest.fixture()
def mock_pool(mock_conn: MagicMock) -> MagicMock:
    pool = MagicMock()

    @contextmanager
    def mock_connection() -> Any:
        yield mock_conn

    pool.connection = mock_connection
    return pool


@pytest.fixture()
def runtime(mock_pool: MagicMock) -> PostgresRuntime:
    return PostgresRuntime(mock_pool)


# ══════════════════════════════════════════════════════════════════════
# T034-T035: TraceRecorder
# ══════════════════════════════════════════════════════════════════════


class TestTraceRecorder:
    """Tests for TraceRecorder."""

    def test_trace_noop_when_level_none(self) -> None:
        """trace() is a no-op when level is NONE."""
        recorder = TraceRecorder(level=TraceLevel.NONE)
        recorder.trace("EconomicSystem", "formula_eval", {"rent": 42.0})
        assert recorder.buffer_size == 0

    def test_trace_buffers_event_at_matching_level(self) -> None:
        """trace() buffers event when level matches."""
        recorder = TraceRecorder(level=TraceLevel.DEBUG)
        recorder.trace(
            "EconomicSystem",
            "formula_eval",
            {"rent": 42.0},
            level=TraceLevel.DEBUG,
        )
        assert recorder.buffer_size == 1

    def test_trace_skips_higher_level_events(self) -> None:
        """trace() skips events above configured level."""
        recorder = TraceRecorder(level=TraceLevel.SUMMARY)
        recorder.trace(
            "EconomicSystem",
            "formula_eval",
            {"rent": 42.0},
            level=TraceLevel.TRACE,
        )
        assert recorder.buffer_size == 0

    def test_trace_includes_lower_level_events(self) -> None:
        """trace() includes events at or below configured level."""
        recorder = TraceRecorder(level=TraceLevel.TRACE)
        recorder.trace("A", "event1", {}, level=TraceLevel.SUMMARY)
        recorder.trace("B", "event2", {}, level=TraceLevel.DEBUG)
        recorder.trace("C", "event3", {}, level=TraceLevel.TRACE)
        assert recorder.buffer_size == 3

    def test_trace_records_node_id(self) -> None:
        """trace() records optional node_id."""
        recorder = TraceRecorder(level=TraceLevel.DEBUG)
        recorder.trace(
            "SurvivalSystem",
            "ps_calc",
            {"p_acquiescence": 0.7},
            node_id="worker_1",
        )
        assert recorder.buffer_size == 1

    def test_flush_calls_persistence(self) -> None:
        """flush() writes buffered events to persistence backend."""
        captured_events: list[list[dict[str, Any]]] = []

        def capture_traces(sid: UUID, tick: int, events: list[dict[str, Any]]) -> None:
            # Capture a copy since the buffer is cleared after this call
            captured_events.append(list(events))

        mock_persistence = MagicMock()
        mock_persistence.persist_traces.side_effect = capture_traces
        recorder = TraceRecorder(level=TraceLevel.DEBUG, persistence=mock_persistence)
        recorder.trace("A", "event1", {"x": 1})
        recorder.trace("B", "event2", {"y": 2})

        sid = uuid4()
        recorder.flush(session_id=sid, tick=5)

        mock_persistence.persist_traces.assert_called_once()
        assert len(captured_events) == 1
        assert len(captured_events[0]) == 2
        assert captured_events[0][0]["system"] == "A"
        assert captured_events[0][1]["system"] == "B"
        assert recorder.buffer_size == 0

    def test_flush_clears_buffer(self) -> None:
        """flush() clears the buffer after writing."""
        recorder = TraceRecorder(level=TraceLevel.DEBUG)
        recorder.trace("A", "event1", {})
        assert recorder.buffer_size == 1

        recorder.flush(session_id=uuid4(), tick=0)
        assert recorder.buffer_size == 0

    def test_flush_noop_on_empty_buffer(self) -> None:
        """flush() is a no-op when buffer is empty."""
        mock_persistence = MagicMock()
        recorder = TraceRecorder(level=TraceLevel.DEBUG, persistence=mock_persistence)
        recorder.flush(session_id=uuid4(), tick=0)

        mock_persistence.persist_traces.assert_not_called()

    def test_flush_without_persistence_clears_buffer(self) -> None:
        """flush() clears buffer even without persistence backend."""
        recorder = TraceRecorder(level=TraceLevel.DEBUG, persistence=None)
        recorder.trace("A", "event1", {})
        recorder.flush(session_id=uuid4(), tick=0)
        assert recorder.buffer_size == 0

    def test_level_property(self) -> None:
        """level property returns configured level."""
        recorder = TraceRecorder(level=TraceLevel.SUMMARY)
        assert recorder.level == TraceLevel.SUMMARY


# ══════════════════════════════════════════════════════════════════════
# T036: persist_traces
# ══════════════════════════════════════════════════════════════════════


class TestPersistTraces:
    """Tests for PostgresRuntime.persist_traces."""

    def test_persists_trace_events(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """persist_traces bulk inserts trace_log rows."""
        trace_events = [
            {
                "system": "EconomicSystem",
                "event": "formula_eval",
                "data": {"rent": 42.0},
                "level": "DEBUG",
                "node_id": "worker_1",
            },
            {
                "system": "SolidaritySystem",
                "event": "edge_transmission",
                "data": {"delta": 0.05},
            },
        ]

        runtime.persist_traces(session_id, tick=0, trace_events=trace_events)

        assert mock_cursor.executemany.called
        sql = mock_cursor.executemany.call_args[0][0]
        rows = mock_cursor.executemany.call_args[0][1]

        assert "INSERT INTO trace_log" in sql
        assert len(rows) == 2
        assert rows[0][2] == "EconomicSystem"  # system_name
        assert rows[0][4] == "formula_eval"  # event
        assert rows[0][5] == "worker_1"  # node_id

    def test_empty_traces_is_noop(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """persist_traces returns early on empty list."""
        runtime.persist_traces(session_id, tick=0, trace_events=[])
        assert mock_cursor.executemany.call_count == 0


# ══════════════════════════════════════════════════════════════════════
# T037: Session partition management
# ══════════════════════════════════════════════════════════════════════


class TestSessionPartitions:
    """Tests for create_session_partition / drop_session_partition."""

    def test_create_partition_issues_ddl(
        self,
        runtime: PostgresRuntime,
        mock_conn: MagicMock,
    ) -> None:
        """create_session_partition executes DDL in autocommit mode."""
        sid = uuid4()
        runtime.create_session_partition(sid)

        mock_conn.execute.assert_called_once()
        sql = mock_conn.execute.call_args[0][0]
        assert "CREATE UNLOGGED TABLE" in sql
        assert "PARTITION OF trace_log" in sql
        assert sid.hex in sql

    def test_drop_partition_issues_ddl(
        self,
        runtime: PostgresRuntime,
        mock_conn: MagicMock,
    ) -> None:
        """drop_session_partition executes DROP TABLE DDL."""
        sid = uuid4()
        runtime.drop_session_partition(sid)

        mock_conn.execute.assert_called_once()
        sql = mock_conn.execute.call_args[0][0]
        assert "DROP TABLE" in sql
        assert sid.hex in sql


# ══════════════════════════════════════════════════════════════════════
# T039-T042: Spatial Queries
# ══════════════════════════════════════════════════════════════════════


class TestPopulateHexCells:
    """Tests for populate_hex_cells."""

    def test_inserts_hex_cells(
        self,
        runtime: PostgresRuntime,
        mock_cursor: MagicMock,
    ) -> None:
        """populate_hex_cells bulk inserts reference data."""
        hex_cells = [
            {
                "h3_index": "872830828ffffff",
                "county_fips": "26163",
                "res6_parent": "862830828ffffff",
                "res5_parent": "852830828ffffff",
                "geometry_wkt": "POLYGON((...))...",
                "centroid_wkt": "POINT(-83.0 42.3)",
            },
        ]

        count = runtime.populate_hex_cells(hex_cells)

        assert count == 1
        assert mock_cursor.executemany.called
        sql = mock_cursor.executemany.call_args[0][0]
        assert "INSERT INTO hex_cell" in sql
        assert "ST_GeomFromText" in sql

    def test_empty_list_returns_zero(
        self,
        runtime: PostgresRuntime,
        mock_cursor: MagicMock,
    ) -> None:
        """populate_hex_cells returns 0 for empty list."""
        count = runtime.populate_hex_cells([])
        assert count == 0
        assert mock_cursor.executemany.call_count == 0


class TestGetHexStateForTick:
    """Tests for get_hex_state_for_tick."""

    def test_returns_all_hex_states(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """get_hex_state_for_tick returns all hex states for a tick."""
        mock_cursor.fetchall.return_value = [
            {"h3_index": "872830828ffffff", "constant_capital": 1000.0},
        ]

        result = runtime.get_hex_state_for_tick(session_id, tick=0)

        assert len(result) == 1
        sql = mock_cursor.execute.call_args[0][0]
        assert "hex_state" in sql
        assert "session_id" in sql

    def test_filters_by_county_fips(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """get_hex_state_for_tick filters by county_fips when provided."""
        mock_cursor.fetchall.return_value = []

        runtime.get_hex_state_for_tick(session_id, tick=0, county_fips="26163")

        sql = mock_cursor.execute.call_args[0][0]
        assert "county_fips" in sql
        params = mock_cursor.execute.call_args[0][1]
        assert "26163" in params


class TestGetHexTimeSeries:
    """Tests for get_hex_time_series."""

    def test_returns_time_series(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """get_hex_time_series returns ordered hex data across ticks."""
        mock_cursor.fetchall.return_value = [
            {"tick": 0, "constant_capital": 1000.0},
            {"tick": 1, "constant_capital": 1050.0},
        ]

        result = runtime.get_hex_time_series(
            session_id, "872830828ffffff", tick_start=0, tick_end=1
        )

        assert len(result) == 2
        sql = mock_cursor.execute.call_args[0][0]
        assert "ORDER BY tick" in sql

    def test_open_ended_range(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """get_hex_time_series works without tick_end."""
        mock_cursor.fetchall.return_value = []

        runtime.get_hex_time_series(session_id, "872830828ffffff")

        sql = mock_cursor.execute.call_args[0][0]
        assert "tick >= %s" in sql
        # Should not have tick <= %s
        assert "tick <=" not in sql


# ══════════════════════════════════════════════════════════════════════
# Context Manager
# ══════════════════════════════════════════════════════════════════════


class TestContextManager:
    """Tests for PostgresRuntime context manager."""

    def test_context_manager_closes_pool(
        self,
        mock_pool: MagicMock,
    ) -> None:
        """PostgresRuntime context manager closes pool on exit."""
        with PostgresRuntime(mock_pool) as runtime:
            assert runtime.pool is mock_pool

        mock_pool.close.assert_called_once()

    def test_init_schema_applies_ddl(
        self,
        mock_conn: MagicMock,
        mock_pool: MagicMock,
    ) -> None:
        """init_schema applies all DDL statements via connection."""
        runtime = PostgresRuntime(mock_pool)
        runtime.init_schema()

        # Verify at least one execute was called for DDL
        assert mock_conn.execute.called
