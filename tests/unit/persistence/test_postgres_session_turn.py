"""Unit tests for PostgresRuntime session management and turn submission.

Phase 4-5 (T026-T033): Turn CRUD, session lifecycle, isolation.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid4

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
# T030-T032: Session Management
# ══════════════════════════════════════════════════════════════════════


class TestCreateSession:
    """Tests for create_session."""

    def test_creates_session_and_returns_uuid(
        self,
        runtime: PostgresRuntime,
        mock_cursor: MagicMock,
    ) -> None:
        """create_session inserts game_session and returns UUID."""
        new_id = uuid4()
        mock_cursor.fetchone.return_value = {"id": new_id}

        result = runtime.create_session(
            scenario="detroit_collapse",
            config_json={"max_ticks": 100},
            game_defines_json={"economy": {}},
            rng_seed=42,
        )

        assert result == new_id
        sql = mock_cursor.execute.call_args[0][0]
        assert "INSERT INTO game_session" in sql
        assert "RETURNING id" in sql

    def test_creates_trace_partition_when_enabled(
        self,
        runtime: PostgresRuntime,
        mock_cursor: MagicMock,
        mock_conn: MagicMock,
    ) -> None:
        """create_session creates trace partition when trace_level != NONE."""
        new_id = uuid4()
        mock_cursor.fetchone.return_value = {"id": new_id}

        runtime.create_session(
            scenario="test",
            config_json={},
            game_defines_json={},
            rng_seed=1,
            trace_level="DEBUG",
        )

        # The second conn.execute call is for the partition DDL
        # (first is the INSERT game_session)
        assert mock_conn.execute.call_count >= 1

    def test_no_partition_when_trace_none(
        self,
        runtime: PostgresRuntime,
        mock_cursor: MagicMock,
        mock_conn: MagicMock,
    ) -> None:
        """create_session skips partition when trace_level is NONE."""
        new_id = uuid4()
        mock_cursor.fetchone.return_value = {"id": new_id}

        runtime.create_session(
            scenario="test",
            config_json={},
            game_defines_json={},
            rng_seed=1,
            trace_level="NONE",
        )

        # Only the cursor.execute for INSERT, no autocommit DDL
        assert mock_cursor.execute.call_count == 1

    def test_raises_on_failed_insert(
        self,
        runtime: PostgresRuntime,
        mock_cursor: MagicMock,
    ) -> None:
        """create_session raises RuntimeError if INSERT returns no row."""
        mock_cursor.fetchone.return_value = None

        with pytest.raises(RuntimeError, match="Failed to create game session"):
            runtime.create_session(
                scenario="test",
                config_json={},
                game_defines_json={},
                rng_seed=1,
            )


class TestGetSession:
    """Tests for get_session."""

    def test_returns_session_dict(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """get_session returns session details as dict."""
        mock_cursor.fetchone.return_value = {
            "id": session_id,
            "scenario": "detroit_collapse",
            "status": "active",
        }

        result = runtime.get_session(session_id)

        assert result is not None
        assert result["id"] == session_id
        assert result["scenario"] == "detroit_collapse"

    def test_returns_none_for_missing(
        self,
        runtime: PostgresRuntime,
        mock_cursor: MagicMock,
    ) -> None:
        """get_session returns None for nonexistent session."""
        mock_cursor.fetchone.return_value = None

        result = runtime.get_session(uuid4())
        assert result is None


class TestUpdateSessionStatus:
    """Tests for update_session_status."""

    def test_updates_status(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_conn: MagicMock,
    ) -> None:
        """update_session_status issues UPDATE with new status."""
        runtime.update_session_status(session_id, "completed")

        mock_conn.execute.assert_called_once()
        sql = mock_conn.execute.call_args[0][0]
        params = mock_conn.execute.call_args[0][1]

        assert "UPDATE game_session" in sql
        assert "status" in sql
        assert params[0] == "completed"
        assert params[1] == session_id


class TestGetActiveSessions:
    """Tests for get_active_sessions."""

    def test_returns_active_sessions(
        self,
        runtime: PostgresRuntime,
        mock_cursor: MagicMock,
    ) -> None:
        """get_active_sessions returns list of active sessions."""
        mock_cursor.fetchall.return_value = [
            {"id": uuid4(), "scenario": "a", "status": "active"},
            {"id": uuid4(), "scenario": "b", "status": "active"},
        ]

        result = runtime.get_active_sessions()

        assert len(result) == 2
        sql = mock_cursor.execute.call_args[0][0]
        assert "status = 'active'" in sql

    def test_returns_empty_list_when_none(
        self,
        runtime: PostgresRuntime,
        mock_cursor: MagicMock,
    ) -> None:
        """get_active_sessions returns empty list when no active sessions."""
        mock_cursor.fetchall.return_value = []

        result = runtime.get_active_sessions()
        assert result == []


# ══════════════════════════════════════════════════════════════════════
# T026-T029: Turn Management
# ══════════════════════════════════════════════════════════════════════


class TestSubmitTurn:
    """Tests for submit_turn."""

    def test_submits_turn_and_returns_id(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """submit_turn inserts game_turn and returns turn ID."""
        mock_cursor.fetchone.return_value = {"id": 42}

        turn_id = runtime.submit_turn(
            session_id=session_id,
            tick=0,
            org_id="org_1",
            verb="AGITATE",
            action_type="CONSCIOUSNESS_RAISE",
            target_id="worker_1",
            target_community="NEIGHBORHOOD",
            params_json={"intensity": 0.8},
        )

        assert turn_id == 42
        sql = mock_cursor.execute.call_args[0][0]
        assert "INSERT INTO game_turn" in sql
        assert "RETURNING id" in sql

    def test_submits_minimal_turn(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """submit_turn works with minimal required params."""
        mock_cursor.fetchone.return_value = {"id": 1}

        turn_id = runtime.submit_turn(
            session_id=session_id,
            tick=0,
            org_id="org_1",
            verb="WAIT",
        )

        assert turn_id == 1
        params = mock_cursor.execute.call_args[0][1]
        assert params[4] is None  # action_type
        assert params[5] is None  # target_id
        assert params[6] is None  # target_community
        assert params[7] is None  # params_json

    def test_raises_on_failed_insert(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """submit_turn raises RuntimeError if INSERT returns no row."""
        mock_cursor.fetchone.return_value = None

        with pytest.raises(RuntimeError, match="Failed to submit turn"):
            runtime.submit_turn(
                session_id=session_id,
                tick=0,
                org_id="org_1",
                verb="AGITATE",
            )


class TestGetPendingTurns:
    """Tests for get_pending_turns."""

    def test_returns_unresolved_turns(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """get_pending_turns returns unresolved turns ordered by submitted_at."""
        mock_cursor.fetchall.return_value = [
            {"id": 1, "org_id": "org_1", "verb": "AGITATE", "resolved": False},
            {"id": 2, "org_id": "org_2", "verb": "WAIT", "resolved": False},
        ]

        result = runtime.get_pending_turns(session_id, tick=0)

        assert len(result) == 2
        sql = mock_cursor.execute.call_args[0][0]
        assert "resolved = FALSE" in sql
        assert "ORDER BY submitted_at" in sql

    def test_returns_empty_when_no_pending(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """get_pending_turns returns empty list when all resolved."""
        mock_cursor.fetchall.return_value = []

        result = runtime.get_pending_turns(session_id, tick=0)
        assert result == []


class TestMarkTurnsResolved:
    """Tests for mark_turns_resolved."""

    def test_marks_turns_and_returns_count(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """mark_turns_resolved updates turns and returns count."""
        mock_cursor.rowcount = 3

        count = runtime.mark_turns_resolved(session_id, tick=0)

        assert count == 3
        sql = mock_cursor.execute.call_args[0][0]
        assert "UPDATE game_turn" in sql
        assert "resolved = TRUE" in sql

    def test_returns_zero_when_none_pending(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """mark_turns_resolved returns 0 when no pending turns."""
        mock_cursor.rowcount = 0

        count = runtime.mark_turns_resolved(session_id, tick=0)
        assert count == 0


class TestPersistActionResults:
    """Tests for persist_action_results."""

    def test_persists_action_results(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """persist_action_results writes action resolution outcomes."""
        results = [
            {
                "org_id": "org_1",
                "action_type": "AGITATE",
                "initiative_score": 0.8,
                "action_cost": 10.0,
                "success": True,
                "consciousness_delta": 0.05,
                "heat_delta": 0.1,
                "details": {"message": "Workers radicalized"},
            },
        ]

        runtime.persist_action_results(tick=0, results=results, session_id=session_id)

        assert mock_cursor.executemany.called
        sql = mock_cursor.executemany.call_args[0][0]
        rows = mock_cursor.executemany.call_args[0][1]

        assert "INSERT INTO action_result" in sql
        assert len(rows) == 1
        assert rows[0][2] == "org_1"  # org_id
        assert rows[0][8] is True  # success

    def test_empty_results_is_noop(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """persist_action_results returns early on empty list."""
        runtime.persist_action_results(tick=0, results=[], session_id=session_id)
        assert mock_cursor.executemany.call_count == 0
