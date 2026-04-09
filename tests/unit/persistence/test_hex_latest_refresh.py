"""Unit tests for PostgresRuntime.refresh_hex_latest().

Tests the two-phase UPSERT that reconstitutes hex_latest from:
  - territory_snapshot (county economics → all hexes)
  - hex_activity (sparse heat/org events → touched hexes only)

Uses mocked psycopg — no live Postgres required.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from babylon.persistence.postgres_runtime import PostgresRuntime

# ── Fixtures ──────────────────────────────────────────────────────────

GAME_ID = UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture()
def mock_cursor() -> MagicMock:
    """Mock psycopg cursor."""
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchone = MagicMock(return_value=None)
    cursor.fetchall = MagicMock(return_value=[])
    cursor.rowcount = 0
    return cursor


@pytest.fixture()
def mock_conn(mock_cursor: MagicMock) -> MagicMock:
    """Mock psycopg connection."""
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


# ══════════════════════════════════════════════════════════════════════
# refresh_hex_latest — two-phase UPSERT
# ══════════════════════════════════════════════════════════════════════


class TestRefreshHexLatest:
    """Tests for refresh_hex_latest two-phase UPSERT."""

    def test_executes_phase1_territory_broadcast(
        self,
        runtime: PostgresRuntime,
        mock_cursor: MagicMock,
    ) -> None:
        """Phase 1 UPDATE broadcasts territory economics to hex_latest."""
        runtime.refresh_hex_latest(game_id=GAME_ID, tick=5)

        # At least one execute call should contain the territory → hex_latest UPDATE
        sql_calls = [c[0][0] for c in mock_cursor.execute.call_args_list]
        phase1_calls = [
            s for s in sql_calls if "UPDATE hex_latest" in s and "territory_snapshot" in s
        ]
        assert len(phase1_calls) >= 1, "Phase 1 territory broadcast UPDATE not found"

    def test_executes_phase2_hex_activity_overlay(
        self,
        runtime: PostgresRuntime,
        mock_cursor: MagicMock,
    ) -> None:
        """Phase 2 UPDATE overlays hex_activity events onto hex_latest."""
        runtime.refresh_hex_latest(game_id=GAME_ID, tick=5)

        sql_calls = [c[0][0] for c in mock_cursor.execute.call_args_list]
        phase2_calls = [s for s in sql_calls if "UPDATE hex_latest" in s and "hex_activity" in s]
        assert len(phase2_calls) >= 1, "Phase 2 hex_activity overlay UPDATE not found"

    def test_phase1_uses_correct_tick(
        self,
        runtime: PostgresRuntime,
        mock_cursor: MagicMock,
    ) -> None:
        """Phase 1 passes game_id and tick as parameters."""
        runtime.refresh_hex_latest(game_id=GAME_ID, tick=7)

        # Check that the game_id and tick appear in parameter tuples
        for c in mock_cursor.execute.call_args_list:
            params = c[0][1] if len(c[0]) > 1 else ()
            if params and GAME_ID in params:
                assert 7 in params, "tick=7 not found in parameters alongside game_id"
                return
        pytest.fail("No execute call contained game_id parameter")

    def test_phase_ordering(
        self,
        runtime: PostgresRuntime,
        mock_cursor: MagicMock,
    ) -> None:
        """Phase 1 (territory) executes before Phase 2 (hex_activity)."""
        runtime.refresh_hex_latest(game_id=GAME_ID, tick=3)

        sql_calls = [c[0][0] for c in mock_cursor.execute.call_args_list]
        phase1_idx = None
        phase2_idx = None
        for i, sql in enumerate(sql_calls):
            if "territory_snapshot" in sql and phase1_idx is None:
                phase1_idx = i
            if "hex_activity" in sql and phase2_idx is None:
                phase2_idx = i

        assert phase1_idx is not None, "Phase 1 not found"
        assert phase2_idx is not None, "Phase 2 not found"
        assert phase1_idx < phase2_idx, (
            f"Phase 1 (idx={phase1_idx}) must precede Phase 2 (idx={phase2_idx})"
        )

    def test_phase1_updates_economic_columns(
        self,
        runtime: PostgresRuntime,
        mock_cursor: MagicMock,
    ) -> None:
        """Phase 1 SQL updates Marxian economic indicators."""
        runtime.refresh_hex_latest(game_id=GAME_ID, tick=0)

        sql_calls = [c[0][0] for c in mock_cursor.execute.call_args_list]
        phase1_sql = next(s for s in sql_calls if "territory_snapshot" in s)

        for col in ("profit_rate", "exploitation_rate", "occ", "imperial_rent"):
            assert col in phase1_sql, f"Phase 1 must update {col}"

    def test_phase1_updates_class_distribution(
        self,
        runtime: PostgresRuntime,
        mock_cursor: MagicMock,
    ) -> None:
        """Phase 1 SQL updates class population columns."""
        runtime.refresh_hex_latest(game_id=GAME_ID, tick=0)

        sql_calls = [c[0][0] for c in mock_cursor.execute.call_args_list]
        phase1_sql = next(s for s in sql_calls if "territory_snapshot" in s)

        for col in ("pop_proletariat", "pop_bourgeoisie", "pop_total"):
            assert col in phase1_sql, f"Phase 1 must update {col}"

    def test_phase2_updates_heat_columns(
        self,
        runtime: PostgresRuntime,
        mock_cursor: MagicMock,
    ) -> None:
        """Phase 2 SQL updates hex-specific heat and org columns."""
        runtime.refresh_hex_latest(game_id=GAME_ID, tick=0)

        sql_calls = [c[0][0] for c in mock_cursor.execute.call_args_list]
        phase2_sql = next(s for s in sql_calls if "hex_activity" in s)

        for col in ("heat", "heat_delta", "org_count"):
            assert col in phase2_sql, f"Phase 2 must update {col}"

    def test_phase1_joins_via_hex_map(
        self,
        runtime: PostgresRuntime,
        mock_cursor: MagicMock,
    ) -> None:
        """Phase 1 joins territory_snapshot → hex_map → hex_latest via county_fips."""
        runtime.refresh_hex_latest(game_id=GAME_ID, tick=0)

        sql_calls = [c[0][0] for c in mock_cursor.execute.call_args_list]
        phase1_sql = next(s for s in sql_calls if "territory_snapshot" in s)

        assert "hex_map" in phase1_sql, "Phase 1 must JOIN through hex_map"
        assert "county_fips" in phase1_sql, "Phase 1 must JOIN on county_fips"
