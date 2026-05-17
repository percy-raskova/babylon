"""Integration test: bridge consumes the cache, not the legacy fetchers (spec-069 T013).

Per contracts/instrumentation_contract.md §I3 (Persist-tick invariance):
- The cache hydrates at ``bridge.hydrate_initial``.
- The per-tick path opens NO new SQLite connection.
- Read counters never increment after hydrate.

This test uses a real temporary SQLite file (not a mock) so that any
regression to per-tick SQLite-connection-opening would be visible in
the patch on ``sqlite3.connect``.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import UUID

import pytest

from babylon.config.defines import GameDefines
from babylon.engine.headless_runner.bridge import WorldStateBridge
from babylon.persistence.envelope import PerTickTransactionEnvelope

# Reuse the test-fixture builder from the unit-test conftest. This file
# is the only integration test that needs it; for cleanliness we import
# the function directly rather than register a duplicate fixture.
from tests.unit.engine.headless_runner.conftest import build_test_sqlite

_SESSION_ID = UUID("00000000-0000-0000-0000-000000000010")
_DETERMINISM_HASH = "0" * 64


class _FakeCursor:
    """Returns canned rows for the Postgres template queries."""

    def __init__(self) -> None:
        self._call_idx = 0

    def execute(self, sql: str, params: tuple[Any, ...]) -> _FakeCursor:  # noqa: ARG002
        return self

    def fetchall(self) -> list[list[Any]]:
        self._call_idx += 1
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


@pytest.fixture
def cache_test_sqlite(tmp_path: Path) -> Path:
    """A reference DB with 1 county × 2 years — exercises year rollover at tick 52."""
    return build_test_sqlite(
        tmp_path / "cache_test.sqlite",
        census_rows={
            ("26163", 2010): 100_000,
            ("26163", 2011): 110_000,
        },
        qcew_rows={
            ("26163", 2010): 50_000,
            ("26163", 2011): 55_000,
        },
    )


class TestBridgeConsumesCache:
    """Bridge integration: persist_tick reads from cache, not from SQLite."""

    def test_hydrate_initial_populates_cache(self, cache_test_sqlite: Path) -> None:
        """After hydrate_initial, the bridge has a populated cache."""
        bridge = WorldStateBridge(runtime=_FakeRuntime(), defines=GameDefines())
        bridge.hydrate_initial(
            session_id=_SESSION_ID,
            scope_fips=frozenset({"26163"}),
            total_ticks=53,  # crosses year boundary → year_set = {2010, 2011}
            start_year=2010,
            sqlite_path=cache_test_sqlite,
        )
        # 1 county × 2 years = 2 tuples, each producing both pop + emp reads.
        assert bridge._ref_cache is not None
        assert bridge._ref_cache.population_db_reads == 2
        assert bridge._ref_cache.employment_db_reads == 2
        assert bridge._ref_cache.total_db_reads == 4

    def test_persist_tick_opens_no_new_sqlite_connection(self, cache_test_sqlite: Path) -> None:
        """Per FR-003 / II.6: persist_tick must NOT open new SQLite connections.

        Patches ``sqlite3.connect`` AFTER hydrate_initial. If persist_tick
        attempts any SQLite I/O, the mock raises.
        """
        from babylon.models.world_state import WorldState

        runtime = _FakeRuntime()
        bridge = WorldStateBridge(runtime=runtime, defines=GameDefines())
        bridge.hydrate_initial(
            session_id=_SESSION_ID,
            scope_fips=frozenset({"26163"}),
            total_ticks=53,
            start_year=2010,
            sqlite_path=cache_test_sqlite,
        )

        original_connect = sqlite3.connect

        def _fail_if_called(*args: Any, **kwargs: Any) -> None:
            raise AssertionError(
                "persist_tick opened a SQLite connection — "
                "FR-003 / II.6 violation; cache not being consulted"
            )

        # Patch the actual sqlite3.connect (the cache imports it from
        # the stdlib module). Any persist_tick code path that reopens
        # SQLite — anywhere — will trip this guard.
        with patch("sqlite3.connect", _fail_if_called):
            world = WorldState(tick=0)
            for tick in (0, 1, 26, 52, 53):
                bridge.persist_tick(world, tick, _DETERMINISM_HASH)

        # Sanity: the original sqlite3.connect is still importable.
        assert sqlite3.connect is original_connect

    def test_persist_tick_counters_invariant_post_hydrate(self, cache_test_sqlite: Path) -> None:
        """Per contracts/instrumentation_contract.md §I3."""
        from babylon.models.world_state import WorldState

        bridge = WorldStateBridge(runtime=_FakeRuntime(), defines=GameDefines())
        bridge.hydrate_initial(
            session_id=_SESSION_ID,
            scope_fips=frozenset({"26163"}),
            total_ticks=53,
            start_year=2010,
            sqlite_path=cache_test_sqlite,
        )
        assert bridge._ref_cache is not None
        baseline = bridge._ref_cache.total_db_reads

        world = WorldState(tick=0)
        for tick in range(0, 53):
            bridge.persist_tick(world, tick, _DETERMINISM_HASH)
            assert bridge._ref_cache.total_db_reads == baseline, (
                f"counter incremented at tick {tick}: "
                f"baseline={baseline} now={bridge._ref_cache.total_db_reads}"
            )
