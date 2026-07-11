"""Unit tests for PostgresRuntime trace and spatial query methods.

Phase 6 (T034-T038): Trace debugging.
Phase 7 (T039-T042): Spatial queries.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from babylon.persistence.postgres_runtime import PostgresRuntime

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
