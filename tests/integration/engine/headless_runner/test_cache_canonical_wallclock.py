"""Slow-gate integration test for SC-002 + FR-003 (spec-069 T022).

Reduced-scale rather than canonical-scale (per tasks.md T022 footnote):
- 4 counties × 2 calendar years × 60 ticks (year rollover at tick 52).
- Asserts ``bridge.total_db_reads == 2 × 4 × 2 == 16`` post-hydrate.
- Asserts the counter does NOT change across 60 persist_tick calls.

The absolute SC-001 60-min wallclock gate is exercised by the operator
at canonical 83 × 11 × 520 scale per quickstart.md (T036).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from babylon.config.defines import GameDefines
from babylon.engine.headless_runner.bridge import WorldStateBridge
from babylon.models.world_state import WorldState
from babylon.persistence.envelope import PerTickTransactionEnvelope
from tests.unit.engine.headless_runner.conftest import build_test_sqlite

_SESSION_ID = UUID("00000000-0000-0000-0000-000000000020")
_DETERMINISM_HASH = "0" * 64
_N_COUNTIES = 4
_N_YEARS = 2  # 2010..2011
_N_TICKS = 60  # crosses year rollover at tick 52


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


@pytest.fixture
def reduced_scale_sqlite(tmp_path: Path) -> Path:
    """4 counties × 2 calendar years, fully populated."""
    fips_list = ["26163", "26125", "26099", "26049"]
    years = (2010, 2011)
    census_rows = {
        (fips, year): 100_000 + i * 10_000 + (year - 2010) * 1_000
        for i, fips in enumerate(fips_list)
        for year in years
    }
    qcew_rows = {
        (fips, year): 50_000 + i * 5_000 + (year - 2010) * 500
        for i, fips in enumerate(fips_list)
        for year in years
    }
    return build_test_sqlite(
        tmp_path / "reduced_scale.sqlite",
        census_rows=census_rows,
        qcew_rows=qcew_rows,
    )


@pytest.mark.slow
class TestSC002ReducedScale:
    """SC-002 + FR-003 at reduced scale (4 × 2 × 60)."""

    def test_post_hydrate_counter_equals_2_n_y(self, reduced_scale_sqlite: Path) -> None:
        """SC-002: ``total_db_reads == 2 × N × Y`` post-hydrate."""
        scope_fips = frozenset({"26163", "26125", "26099", "26049"})
        bridge = WorldStateBridge(runtime=_FakeRuntime(), defines=GameDefines())
        bridge.hydrate_initial(
            session_id=_SESSION_ID,
            scope_fips=scope_fips,
            total_ticks=_N_TICKS,
            start_year=2010,
            sqlite_path=reduced_scale_sqlite,
        )
        assert bridge._ref_cache is not None
        assert bridge._ref_cache.population_db_reads == _N_COUNTIES * _N_YEARS
        assert bridge._ref_cache.employment_db_reads == _N_COUNTIES * _N_YEARS
        assert bridge._ref_cache.total_db_reads == 2 * _N_COUNTIES * _N_YEARS

    def test_persist_tick_counter_does_not_increment(self, reduced_scale_sqlite: Path) -> None:
        """FR-003 / I3: 60 persist_tick calls leave the counters frozen."""
        scope_fips = frozenset({"26163", "26125", "26099", "26049"})
        bridge = WorldStateBridge(runtime=_FakeRuntime(), defines=GameDefines())
        bridge.hydrate_initial(
            session_id=_SESSION_ID,
            scope_fips=scope_fips,
            total_ticks=_N_TICKS,
            start_year=2010,
            sqlite_path=reduced_scale_sqlite,
        )
        assert bridge._ref_cache is not None
        baseline = bridge._ref_cache.total_db_reads

        world = WorldState(tick=0)
        for tick in range(_N_TICKS):
            bridge.persist_tick(world, tick, _DETERMINISM_HASH)
            assert bridge._ref_cache.total_db_reads == baseline, (
                f"FR-003 violation at tick {tick}: counter changed from "
                f"{baseline} to {bridge._ref_cache.total_db_reads}"
            )
