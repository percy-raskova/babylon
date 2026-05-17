"""Spec-065 T045/T046: ConservationAuditor wiring + severity mapping unit tests.

T045: Verify the runner's _check_strict_alarms helper queries the
      conservation_audit_log table and returns the first alarm row.
T046: Verify _AUDIT_SEVERITY_MAP maps Postgres severities to contract values.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from babylon.engine.headless_runner.runner import (
    _AUDIT_SEVERITY_MAP,
    _check_strict_alarms,
)

# ----------------------------------------------------------------------
# T046: Severity mapping
# ----------------------------------------------------------------------


class TestAuditSeverityMapping:
    def test_ok_maps_to_info(self) -> None:
        assert _AUDIT_SEVERITY_MAP["ok"] == "info"

    def test_warn_maps_to_warning(self) -> None:
        assert _AUDIT_SEVERITY_MAP["warn"] == "warning"

    def test_alarm_maps_to_error(self) -> None:
        assert _AUDIT_SEVERITY_MAP["alarm"] == "error"

    def test_only_three_postgres_severities(self) -> None:
        assert set(_AUDIT_SEVERITY_MAP.keys()) == {"ok", "warn", "alarm"}


# ----------------------------------------------------------------------
# T045: _check_strict_alarms wiring
# ----------------------------------------------------------------------


class _FakeCursor:
    def __init__(self, scripted: list[Any]) -> None:
        self._rows = scripted

    def execute(self, sql: str, params: tuple[Any, ...]) -> _FakeCursor:  # noqa: ARG002
        return self

    def fetchone(self) -> Any:
        return self._rows[0] if self._rows else None


class _FakeConn:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor

    def execute(self, sql: str, params: tuple[Any, ...]) -> _FakeCursor:
        return self._cursor.execute(sql, params)

    def __enter__(self) -> _FakeConn:
        return self

    def __exit__(self, *_a: Any) -> None:
        return None


class _FakePool:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor

    def connection(self) -> _FakeConn:
        return _FakeConn(self._cursor)


class _FakeRuntime:
    def __init__(self, scripted_rows: list[Any]) -> None:
        self._pool = _FakePool(_FakeCursor(scripted_rows))


class TestCheckStrictAlarms:
    def test_no_alarm_rows_returns_none(self) -> None:
        rt = _FakeRuntime([])
        result = _check_strict_alarms(runtime=rt, session_id=uuid4(), up_to_tick=10)
        assert result is None

    def test_alarm_row_returns_tick_and_invariant(self) -> None:
        rt = _FakeRuntime([(50, "global_phi_balance")])
        result = _check_strict_alarms(runtime=rt, session_id=uuid4(), up_to_tick=100)
        assert result == (50, "global_phi_balance")
