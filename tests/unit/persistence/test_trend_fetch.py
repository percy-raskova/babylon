"""Unit pins for the M6 Task 41 fetch layer (``postgres_aggregation``).

Fixture-fed (CI's unit shard has no database — ADR074): a pool shim
returning canned rows proves the row→model construction, the
oldest→newest re-ordering, and — the II.11 point — that the SELECT list
is BUILT FROM ``declared_view("v_national_trend").columns``, never
hand-duplicated (the declared view IS the interface; a registry column
added without this fetch noticing would silently drop at parse, which
the ``dict(zip(...))`` construction + the registry's own
columns==model_fields sync assert make impossible).

The live-database proof (the SQL actually executes, ``LIMIT``/order
against real rows) lives in ``tests/integration/persistence/
test_trend_playability_view.py``. ``fetch_latest_national_aggregate``
gets its SQL-shape pin here; its view (``v_national_value_aggregate``,
migration 0015 over migration-created hex tables) is deliberately not
re-scaffolded into a fresh-DB fixture for a LIMIT-1 read — the runtime
exercises it wherever hex hydration runs (P26 U5g).
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from babylon.persistence.postgres_aggregation import (
    _LATEST_NATIONAL_SQL,
    _national_trend_sql,
    fetch_latest_national_aggregate,
    fetch_national_trend,
)
from babylon.projection.registry import declared_view

pytestmark = pytest.mark.unit


class _FakeCursor:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._rows = rows

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._rows

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._rows[0] if self._rows else None


class _FakeConn:
    def __init__(self, rows: list[tuple[Any, ...]], executed: list[tuple[str, Any]]) -> None:
        self._rows = rows
        self._executed = executed

    def execute(self, sql: str, params: Any) -> _FakeCursor:
        self._executed.append((sql, params))
        return _FakeCursor(self._rows)

    def __enter__(self) -> _FakeConn:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


class _FakePool:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self.executed: list[tuple[str, Any]] = []
        self._rows = rows

    def connection(self) -> _FakeConn:
        return _FakeConn(self._rows, self.executed)


class _FakeRuntime:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._pool = _FakePool(rows)


def _trend_tuple(tick: int) -> tuple[Any, ...]:
    """One v_national_trend row tuple in DECLARED column order."""
    columns = declared_view("v_national_trend").columns
    values: dict[str, Any] = dict.fromkeys(columns)
    values["session_id"] = uuid.uuid4()
    values["tick"] = tick
    values["imperial_rent"] = float(tick)
    return tuple(values[c] for c in columns)


class TestNationalTrendSql:
    def test_select_list_is_the_declared_column_tuple(self) -> None:
        sql = _national_trend_sql()
        for column in declared_view("v_national_trend").columns:
            assert column in sql
        assert "SELECT *" not in sql

    def test_windows_newest_first_then_the_fetch_reverses(self) -> None:
        assert "ORDER BY tick DESC" in _national_trend_sql()
        assert "LIMIT" in _national_trend_sql()


class TestFetchNationalTrend:
    def test_rows_come_back_oldest_to_newest(self) -> None:
        # The SQL serves newest-first (DESC LIMIT n); the fetch reverses.
        runtime = _FakeRuntime([_trend_tuple(5), _trend_tuple(4), _trend_tuple(3)])

        rows = fetch_national_trend(
            runtime=runtime,  # type: ignore[arg-type]
            session_id=uuid.uuid4(),
            last_n=3,
        )

        assert [r.tick for r in rows] == [3, 4, 5]
        assert rows[0].imperial_rent == pytest.approx(3.0)

    def test_binds_session_and_last_n(self) -> None:
        runtime = _FakeRuntime([])
        session_id = uuid.uuid4()

        fetch_national_trend(runtime=runtime, session_id=session_id, last_n=25)  # type: ignore[arg-type]

        [(sql, params)] = runtime._pool.executed
        assert params == (str(session_id), 25)
        assert "v_national_trend" in sql


class TestFetchLatestNationalAggregate:
    def test_sql_is_a_desc_limit_one_over_the_view(self) -> None:
        assert "v_national_value_aggregate" in _LATEST_NATIONAL_SQL
        assert "ORDER BY tick DESC" in _LATEST_NATIONAL_SQL
        assert "LIMIT 1" in _LATEST_NATIONAL_SQL

    def test_absent_row_is_none(self) -> None:
        runtime = _FakeRuntime([])
        assert (
            fetch_latest_national_aggregate(
                runtime=runtime,  # type: ignore[arg-type]
                session_id=uuid.uuid4(),
            )
            is None
        )

    def test_present_row_constructs_the_model(self) -> None:
        session_id = uuid.uuid4()
        runtime = _FakeRuntime([(session_id, 0, "USA", 100.0, 50.0, 75.0, 10.0, 0.0, 3)])

        row = fetch_latest_national_aggregate(
            runtime=runtime,  # type: ignore[arg-type]
            session_id=session_id,
        )

        assert row is not None
        assert row.tick == 0
        assert row.s_sum == pytest.approx(75.0)
