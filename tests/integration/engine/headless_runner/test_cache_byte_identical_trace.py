"""Slow-gate integration test for SC-003 (spec-069 T029).

Per ``contracts/reference_data_cache_contract.md`` §Determinism contract:
- Given the same ``sqlite_path`` content, the same ``scope_fips``, and the
  same ``year_set``, ``hydrate`` produces a cache whose lookups return
  byte-identical values across runs.

This test verifies the SAME PROPERTY at the cache layer (the layer that
spec-069 actually introduces). The trace.csv-level byte-equality (the
quickstart's `diff -q reports/sim-runs/<run1>/trace.csv
reports/sim-runs/<run2>/trace.csv` check) is exercised by the operator
during T036 canonical validation, since it requires the full bridged
runner pipeline (Postgres runtime, engine systems, trace emission).

At the cache level: two ``ReferenceDataCache`` instances constructed
against the same SQLite file with the same scope MUST produce
byte-identical entries.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.engine.headless_runner.reference_data_cache import ReferenceDataCache
from tests.unit.engine.headless_runner.conftest import build_test_sqlite

_SCOPE = frozenset({"26163", "26125", "26099", "26049"})
_YEARS = frozenset({2010, 2011, 2012, 2013, 2014})


@pytest.mark.slow
class TestCacheByteIdenticalAcrossRuns:
    """SC-003 at the cache layer — same inputs ⇒ byte-identical outputs."""

    def test_two_hydrates_produce_identical_entries(self, tmp_path: Path) -> None:
        """Two cache instances against the same DB yield identical state.

        Tests every dict entry by ``(fips, year)`` for both fields. Any
        deviation indicates a determinism regression in the cache layer.
        """
        sqlite_path = build_test_sqlite(
            tmp_path / "byte_identical.sqlite",
            census_rows={
                (fips, year): 1_000_000 + i * 10_000 + j * 100
                for i, fips in enumerate(sorted(_SCOPE))
                for j, year in enumerate(sorted(_YEARS))
            },
            qcew_rows={
                (fips, year): 500_000 + i * 5_000 + j * 50
                for i, fips in enumerate(sorted(_SCOPE))
                for j, year in enumerate(sorted(_YEARS))
            },
        )

        cache_a = ReferenceDataCache(sqlite_path)
        cache_a.hydrate(scope_fips=_SCOPE, year_set=_YEARS)

        cache_b = ReferenceDataCache(sqlite_path)
        cache_b.hydrate(scope_fips=_SCOPE, year_set=_YEARS)

        # Per-key byte-equality (ints are exact; floats are IEEE-exact since
        # the same SQL aggregate is computed against the same data).
        assert sorted(cache_a._entries.keys()) == sorted(cache_b._entries.keys())
        for key in cache_a._entries:
            ea = cache_a._entries[key]
            eb = cache_b._entries[key]
            assert ea.population == eb.population, f"population drift at {key}: {ea} vs {eb}"
            assert ea.employment_proxy == eb.employment_proxy, (
                f"employment_proxy drift at {key}: {ea} vs {eb}"
            )

    def test_counters_byte_identical_across_runs(self, tmp_path: Path) -> None:
        """The instrumentation counters are themselves deterministic."""
        sqlite_path = build_test_sqlite(
            tmp_path / "counter_byte_identical.sqlite",
            census_rows={(fips, 2010): 100_000 for fips in _SCOPE},
            qcew_rows={(fips, 2010): 50_000 for fips in _SCOPE},
        )

        cache_a = ReferenceDataCache(sqlite_path)
        cache_a.hydrate(scope_fips=_SCOPE, year_set=frozenset({2010}))

        cache_b = ReferenceDataCache(sqlite_path)
        cache_b.hydrate(scope_fips=_SCOPE, year_set=frozenset({2010}))

        assert cache_a.population_db_reads == cache_b.population_db_reads
        assert cache_a.employment_db_reads == cache_b.employment_db_reads
        assert cache_a.total_db_reads == cache_b.total_db_reads
