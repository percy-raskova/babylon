"""Integration test for persist-tick counter invariance (spec-069 T025 / I3).

Per contracts/instrumentation_contract.md §I3 (Persist-tick invariance):
For all valid ticks ``t in [0, T)``::

    counts_before = bridge.{population,employment,total}_db_reads
    bridge.persist_tick(...)
    assert bridge.{population,employment,total}_db_reads == counts_before

This test exercises 52 ticks within a single calendar year and asserts
the counters are frozen across the whole batch — the strongest local
form of FR-003 (no DB I/O during tick).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from babylon.config.defines import GameDefines
from babylon.engine.headless_runner.bridge import WorldStateBridge
from babylon.models.world_state import WorldState
from babylon.persistence.envelope import PerTickTransactionEnvelope
from tests.unit.engine.headless_runner.conftest import build_test_sqlite

_SESSION_ID = UUID("00000000-0000-0000-0000-000000000040")
_DETERMINISM_HASH = "0" * 64


class _FakeCursor:
    def execute(self, sql: str, params: tuple[Any, ...]) -> _FakeCursor:  # noqa: ARG002
        return self

    def fetchall(self) -> list[list[Any]]:
        return []


class _FakeConnection:
    def __init__(self) -> None:
        self._cursor = _FakeCursor()

    def execute(self, sql: str, params: tuple[Any, ...]) -> _FakeCursor:
        return self._cursor.execute(sql, params)

    def __enter__(self) -> _FakeConnection:
        return self

    def __exit__(self, *_exc: Any) -> None:
        return None


class _FakePool:
    def connection(self) -> _FakeConnection:
        return _FakeConnection()


class _FakeRuntime:
    def __init__(self) -> None:
        self._pool = _FakePool()
        self.persisted_envelopes: list[PerTickTransactionEnvelope] = []

    def persist_tick_atomic(self, envelope: PerTickTransactionEnvelope) -> None:
        self.persisted_envelopes.append(envelope)


class TestPersistTickCounterInvariance:
    """52 persist_tick calls in one year — counters must not budge."""

    def test_single_year_invariance(self, tmp_path: Path) -> None:
        sqlite_path = build_test_sqlite(
            tmp_path / "ref.sqlite",
            census_rows={("26163", 2010): 100_000},
            qcew_rows={("26163", 2010): 50_000},
        )
        bridge = WorldStateBridge(runtime=_FakeRuntime(), defines=GameDefines())
        bridge.hydrate_initial(
            session_id=_SESSION_ID,
            scope_fips=frozenset({"26163"}),
            total_ticks=52,  # all ticks within year 2010
            start_year=2010,
            sqlite_path=sqlite_path,
        )
        baseline_pop = bridge.population_db_reads
        baseline_emp = bridge.employment_db_reads
        baseline_tot = bridge.total_db_reads
        assert baseline_tot == 2  # 1 county × 1 year × 2 fields

        world = WorldState(tick=0)
        for tick in range(52):
            bridge.persist_tick(world, tick, _DETERMINISM_HASH)
            assert bridge.population_db_reads == baseline_pop
            assert bridge.employment_db_reads == baseline_emp
            assert bridge.total_db_reads == baseline_tot
