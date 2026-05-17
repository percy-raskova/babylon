"""Unit tests for bridge-level read-counter properties (spec-069 T024).

Per contracts/instrumentation_contract.md §Behavioral invariants:
- I1: Pre-hydrate, all three properties return 0.
- I2: Post-hydrate, ``bridge.{population,employment}_db_reads == N × Y``.
- I4: Two bridge instances in the same process don't share counters.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from babylon.config.defines import GameDefines
from babylon.engine.headless_runner.bridge import WorldStateBridge
from babylon.persistence.envelope import PerTickTransactionEnvelope

_SESSION_ID = UUID("00000000-0000-0000-0000-000000000030")
_SESSION_ID_2 = UUID("00000000-0000-0000-0000-000000000031")


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


class TestBridgeDbReadsProperties:
    """Bridge property contract per `instrumentation_contract.md`."""

    def test_pre_hydrate_properties_are_zero(self) -> None:
        """I1: an unhydrated bridge reports 0 for all three counters."""
        bridge = WorldStateBridge(runtime=_FakeRuntime(), defines=GameDefines())
        assert bridge.population_db_reads == 0
        assert bridge.employment_db_reads == 0
        assert bridge.total_db_reads == 0

    def test_post_hydrate_properties_match_cache(self, simple_ref_sqlite: Path) -> None:
        """I2: bridge counters delegate to the underlying cache."""
        bridge = WorldStateBridge(runtime=_FakeRuntime(), defines=GameDefines())
        bridge.hydrate_initial(
            session_id=_SESSION_ID,
            scope_fips=frozenset({"26163"}),
            total_ticks=53,  # year_set = {2010, 2011}
            start_year=2010,
            sqlite_path=simple_ref_sqlite,
        )
        # 1 county × 2 years = 2 (population) + 2 (employment) = 4 total.
        assert bridge.population_db_reads == 2
        assert bridge.employment_db_reads == 2
        assert bridge.total_db_reads == 4

    def test_two_bridges_have_independent_counters(self, simple_ref_sqlite: Path) -> None:
        """I4 / FR-008: per-bridge scope, no cross-instance sharing."""
        bridge_a = WorldStateBridge(runtime=_FakeRuntime(), defines=GameDefines())
        bridge_b = WorldStateBridge(runtime=_FakeRuntime(), defines=GameDefines())

        bridge_a.hydrate_initial(
            session_id=_SESSION_ID,
            scope_fips=frozenset({"26163"}),
            total_ticks=1,
            start_year=2010,
            sqlite_path=simple_ref_sqlite,
        )
        bridge_b.hydrate_initial(
            session_id=_SESSION_ID_2,
            scope_fips=frozenset({"26163", "26125"}),
            total_ticks=53,
            start_year=2010,
            sqlite_path=simple_ref_sqlite,
        )
        # bridge_a: 1 × 1 = 1 per field, total 2.
        # bridge_b: 2 × 2 = 4 per field, total 8.
        assert bridge_a.total_db_reads == 2
        assert bridge_b.total_db_reads == 8

    def test_total_db_reads_sums_individual(self, simple_ref_sqlite: Path) -> None:
        bridge = WorldStateBridge(runtime=_FakeRuntime(), defines=GameDefines())
        bridge.hydrate_initial(
            session_id=_SESSION_ID,
            scope_fips=frozenset({"26163"}),
            total_ticks=53,
            start_year=2010,
            sqlite_path=simple_ref_sqlite,
        )
        assert bridge.total_db_reads == bridge.population_db_reads + bridge.employment_db_reads
