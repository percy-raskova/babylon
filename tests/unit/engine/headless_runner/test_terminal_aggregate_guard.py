"""Spec-102 STEP 0: fail-loud guard for hex-rows-exist-but-zero-counties.

Regression coverage for the hex_spatial_map contention bug (spec-088 S3)
that nearly shipped spec-101's auto-refreshed baseline with a silent
``counties_alive=0``/``total_v=0`` terminal aggregate: hex rows persist
with inline ``county_fips=NULL`` by design, so county resolution depends
entirely on the global ``hex_spatial_map`` table. If that table is
transiently empty (or unpopulated) while hex rows already exist for this
session, ``view_runtime_trace_emission``'s COALESCE join resolves every
row to NULL and the terminal aggregate would silently report zero
counties. ``_query_terminal_aggregates`` / ``_county_terminal_snapshot``
must raise :class:`TerminalAggregateResolutionError` instead.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from babylon.engine.headless_runner.runner import (
    TerminalAggregateResolutionError,
    _county_terminal_snapshot,
    _query_terminal_aggregates,
)


class _FakeCursor:
    """Cursor whose ``fetchone``/``fetchall`` replay a scripted call queue.

    Each entry in ``scripted_calls`` corresponds to one ``execute()`` call,
    in order, and is returned verbatim by the following ``fetchone`` (if a
    single row/None) or ``fetchall`` (if a list) call.
    """

    def __init__(self, scripted_calls: list[Any]) -> None:
        self._queue = list(scripted_calls)
        self._current: Any = None

    def execute(self, _sql: str, _params: tuple[Any, ...]) -> _FakeCursor:
        self._current = self._queue.pop(0)
        return self

    def fetchone(self) -> Any:
        return self._current

    def fetchall(self) -> Any:
        return self._current if self._current is not None else []


class _FakeConn:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor

    def cursor(self) -> _FakeConnCursorCtx:
        return _FakeConnCursorCtx(self._cursor)

    def __enter__(self) -> _FakeConn:
        return self

    def __exit__(self, *_a: Any) -> None:
        return None


class _FakeConnCursorCtx:
    """``conn.cursor()`` context manager wrapper (mirrors psycopg usage)."""

    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor

    def __enter__(self) -> _FakeCursor:
        return self._cursor

    def __exit__(self, *_a: Any) -> None:
        return None


class _FakePoolConnCtx:
    def __init__(self, conn: _FakeConn) -> None:
        self._conn = conn

    def __enter__(self) -> _FakeConn:
        return self._conn

    def __exit__(self, *_a: Any) -> None:
        return None


class _FakePool:
    def __init__(self, scripted_calls: list[Any]) -> None:
        self._cursor = _FakeCursor(scripted_calls)
        self._conn = _FakeConn(self._cursor)

    def connection(self) -> _FakePoolConnCtx:
        return _FakePoolConnCtx(self._conn)


class TestQueryTerminalAggregatesGuard:
    """STEP 0 guard as invoked from ``_query_terminal_aggregates``."""

    def test_raises_when_hex_rows_exist_but_zero_counties_resolved(self) -> None:
        # Main aggregate query: row[6] (resolved county count) == 0.
        # Guard's hex-row-count query: (5,) — hex rows DO exist.
        pool = _FakePool(
            scripted_calls=[
                (0, 100.0, 50.0, 25.0, 500.0, 0, 0),
                (5,),
            ]
        )
        with pytest.raises(TerminalAggregateResolutionError, match="hex_spatial_map"):
            _query_terminal_aggregates(pool=pool, session_id=uuid4(), terminal_tick=519)

    def test_ok_when_counties_resolved(self) -> None:
        # resolved_county_count = row[6] = 83 > 0 -> guard short-circuits,
        # no second query issued.
        pool = _FakePool(
            scripted_calls=[
                (83, 1000.0, 500.0, 250.0, 5000.0, 83, 83),
            ]
        )
        result = _query_terminal_aggregates(pool=pool, session_id=uuid4(), terminal_tick=519)
        assert result["counties_alive"] == 83
        assert result["total_v"] == 1000.0

    def test_ok_when_zero_counties_and_zero_hex_rows(self) -> None:
        """Legitimate all-dead outcome: zero counties AND zero hex rows.

        Must NOT raise — this is a genuine (if extreme) terminal state,
        not the contention bug.
        """
        pool = _FakePool(
            scripted_calls=[
                (0, 0.0, 0.0, 0.0, 0.0, 0, 0),
                (0,),
            ]
        )
        result = _query_terminal_aggregates(pool=pool, session_id=uuid4(), terminal_tick=519)
        assert result["counties_alive"] == 0
        assert result["total_v"] == 0.0


class TestCountyTerminalSnapshotGuard:
    """STEP 0 guard as invoked from ``_county_terminal_snapshot``."""

    def test_raises_when_hex_rows_exist_but_zero_counties_resolved(self) -> None:
        # Main per-county query returns rows but every entity_id is NULL.
        pool = _FakePool(
            scripted_calls=[
                [(None, 10.0, 5.0, 2.0, 50.0, None, None, None, None, None, None)],
                (5,),  # hex rows exist
            ]
        )
        with pytest.raises(TerminalAggregateResolutionError, match="hex_spatial_map"):
            _county_terminal_snapshot(pool=pool, session_id=uuid4(), terminal_tick=519)

    def test_ok_when_counties_resolved(self) -> None:
        pool = _FakePool(
            scripted_calls=[
                [("26163", 10.0, 5.0, 2.0, 50.0, 0.3, 0.4, 0.1, 0.1, 0.1, 1000)],
                [("26163", 40.0)],
            ]
        )
        result = _county_terminal_snapshot(pool=pool, session_id=uuid4(), terminal_tick=519)
        assert len(result) == 1
        assert result[0]["entity_id"] == "26163"
        assert result[0]["delta_k_vs_initial"] == pytest.approx(10.0)

    def test_ok_when_zero_counties_and_zero_hex_rows(self) -> None:
        """Legitimate empty snapshot (no hex rows at all) must NOT raise."""
        pool = _FakePool(
            scripted_calls=[
                [],
                (0,),
                [],
            ]
        )
        result = _county_terminal_snapshot(pool=pool, session_id=uuid4(), terminal_tick=519)
        assert result == []
