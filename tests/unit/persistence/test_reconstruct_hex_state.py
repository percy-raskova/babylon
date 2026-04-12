"""Unit tests for PostgresRuntime.reconstruct_hex_state().

Validates historical hex reconstruction SQL that uses LATERAL join
between territory_snapshot, hex_map, and hex_activity to reconstruct
any past tick's hex state from the append-only journals.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from babylon.persistence.postgres_runtime import PostgresRuntime

GAME_ID = UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture()
def mock_cursor() -> MagicMock:
    """Mock psycopg cursor."""
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchall = MagicMock(return_value=[])
    return cursor


@pytest.fixture()
def mock_conn(mock_cursor: MagicMock) -> MagicMock:
    """Mock psycopg connection."""
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor = MagicMock(return_value=mock_cursor)
    return conn


@pytest.fixture()
def mock_pool(mock_conn: MagicMock) -> MagicMock:
    """Mock psycopg ConnectionPool."""
    pool = MagicMock()

    @contextmanager
    def mock_connection() -> Any:
        yield mock_conn

    pool.connection = mock_connection
    return pool


@pytest.fixture()
def runtime(mock_pool: MagicMock) -> PostgresRuntime:
    """PostgresRuntime with mocked pool."""
    return PostgresRuntime(mock_pool)


class TestReconstructHexState:
    """Tests for historical hex reconstruction."""

    def test_executes_reconstruct_sql(
        self,
        runtime: PostgresRuntime,
        mock_cursor: MagicMock,
    ) -> None:
        """reconstruct_hex_state executes a SELECT with JOINs."""
        runtime.reconstruct_hex_state(GAME_ID, tick=5)

        mock_cursor.execute.assert_called_once()
        sql = mock_cursor.execute.call_args[0][0]
        assert "SELECT" in sql
        assert "hex_map" in sql

    def test_passes_game_id_and_tick(
        self,
        runtime: PostgresRuntime,
        mock_cursor: MagicMock,
    ) -> None:
        """reconstruct_hex_state binds game_id and tick as parameters."""
        runtime.reconstruct_hex_state(GAME_ID, tick=42)

        params = mock_cursor.execute.call_args[0][1]
        assert params == (GAME_ID, 42)

    def test_returns_list_of_dicts(
        self,
        runtime: PostgresRuntime,
        mock_cursor: MagicMock,
    ) -> None:
        """reconstruct_hex_state returns list of dict rows."""
        mock_cursor.fetchall.return_value = [
            {"h3_index": "872830828ffffff", "tick": 5, "profit_rate": 0.04},
        ]
        result = runtime.reconstruct_hex_state(GAME_ID, tick=5)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["h3_index"] == "872830828ffffff"

    def test_returns_empty_for_no_data(
        self,
        runtime: PostgresRuntime,
        mock_cursor: MagicMock,
    ) -> None:
        """reconstruct_hex_state returns empty list when no data exists."""
        mock_cursor.fetchall.return_value = []
        result = runtime.reconstruct_hex_state(GAME_ID, tick=999)
        assert result == []

    def test_sql_uses_lateral_join(self) -> None:
        """Reconstruction SQL uses LATERAL join for hex_activity."""
        sql = PostgresRuntime._RECONSTRUCT_HEX_STATE
        assert "LATERAL" in sql
        assert "hex_activity" in sql

    def test_sql_joins_territory_and_hex_map(self) -> None:
        """Reconstruction SQL JOINs territory_snapshot and hex_map."""
        sql = PostgresRuntime._RECONSTRUCT_HEX_STATE
        assert "territory_snapshot" in sql
        assert "hex_map" in sql
        assert "county_fips" in sql

    def test_sql_coalesces_missing_activity(self) -> None:
        """Reconstruction SQL uses COALESCE for optional hex_activity fields."""
        sql = PostgresRuntime._RECONSTRUCT_HEX_STATE
        for col in ("heat_total", "heat_delta", "org_count", "actions_taken"):
            assert f"COALESCE(ha.{col}" in sql, f"Missing COALESCE for {col}"

    def test_sql_includes_economic_columns(self) -> None:
        """Reconstruction SQL selects all Marxian economic indicators."""
        sql = PostgresRuntime._RECONSTRUCT_HEX_STATE
        for col in ("profit_rate", "exploitation_rate", "occ", "imperial_rent"):
            assert f"ts.{col}" in sql, f"Missing column: ts.{col}"

    def test_sql_includes_geographic_columns(self) -> None:
        """Reconstruction SQL includes geographic identification."""
        sql = PostgresRuntime._RECONSTRUCT_HEX_STATE
        for col in ("center_lat", "center_lng", "county_name", "state_fips"):
            assert col in sql, f"Missing column: {col}"
