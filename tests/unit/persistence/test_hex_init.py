"""Unit tests for hex_init.seed_hex_latest().

Validates tick-0 ETL SQL construction and parameter binding
using mocked psycopg — no live Postgres required.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from babylon.persistence.hex_init import SEED_HEX_LATEST_SQL, seed_hex_latest

GAME_ID = UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture()
def mock_cursor() -> MagicMock:
    """Mock psycopg cursor."""
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.rowcount = 500
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


class TestSeedHexLatest:
    """Tests for seed_hex_latest ETL function."""

    def test_executes_seed_sql(
        self,
        mock_pool: MagicMock,
        mock_cursor: MagicMock,
    ) -> None:
        """seed_hex_latest executes the INSERT...SELECT SQL."""
        seed_hex_latest(mock_pool, GAME_ID)

        mock_cursor.execute.assert_called_once()
        sql = mock_cursor.execute.call_args[0][0]
        assert "INSERT INTO hex_latest" in sql
        assert "SELECT" in sql

    def test_passes_game_id_parameter(
        self,
        mock_pool: MagicMock,
        mock_cursor: MagicMock,
    ) -> None:
        """seed_hex_latest binds game_id as the only parameter."""
        seed_hex_latest(mock_pool, GAME_ID)

        params = mock_cursor.execute.call_args[0][1]
        assert params == (GAME_ID,)

    def test_returns_rowcount(
        self,
        mock_pool: MagicMock,
        mock_cursor: MagicMock,
    ) -> None:
        """seed_hex_latest returns the number of inserted rows."""
        mock_cursor.rowcount = 243_000
        result = seed_hex_latest(mock_pool, GAME_ID)
        assert result == 243_000

    def test_sql_joins_territory_and_hex_map(self) -> None:
        """Seed SQL JOINs territory_snapshot and hex_map."""
        assert "territory_snapshot" in SEED_HEX_LATEST_SQL
        assert "hex_map" in SEED_HEX_LATEST_SQL
        assert "county_fips" in SEED_HEX_LATEST_SQL

    def test_sql_left_joins_hex_substrate(self) -> None:
        """Seed SQL LEFT JOINs hex_substrate for terrain aggregation."""
        assert "LEFT JOIN" in SEED_HEX_LATEST_SQL
        assert "hex_substrate" in SEED_HEX_LATEST_SQL
        assert "r7_parent" in SEED_HEX_LATEST_SQL

    def test_sql_aggregates_terrain(self) -> None:
        """Seed SQL uses MODE, AVG, BOOL_OR for R8 → R7 aggregation."""
        assert "MODE()" in SEED_HEX_LATEST_SQL
        assert "AVG(water_coverage)" in SEED_HEX_LATEST_SQL
        assert "BOOL_OR(internet_access)" in SEED_HEX_LATEST_SQL

    def test_sql_filters_tick_zero(self) -> None:
        """Seed SQL only reads territory_snapshot at tick = 0."""
        assert "ts.tick = 0" in SEED_HEX_LATEST_SQL

    def test_sql_computes_dominant_class(self) -> None:
        """Seed SQL derives dominant_class via CASE expression."""
        assert "CASE" in SEED_HEX_LATEST_SQL
        assert "proletariat" in SEED_HEX_LATEST_SQL
        assert "bourgeoisie" in SEED_HEX_LATEST_SQL

    def test_sql_includes_economic_columns(self) -> None:
        """Seed SQL inserts all Marxian economic indicators."""
        for col in ("profit_rate", "exploitation_rate", "occ", "imperial_rent"):
            assert col in SEED_HEX_LATEST_SQL, f"Missing column: {col}"

    def test_sql_includes_class_distribution(self) -> None:
        """Seed SQL inserts all class population columns."""
        for col in (
            "pop_bourgeoisie",
            "pop_proletariat",
            "pop_total",
            "pop_lumpenproletariat",
        ):
            assert col in SEED_HEX_LATEST_SQL, f"Missing column: {col}"
