"""Unit tests for cache-level counter properties (spec-069 T023 / R6).

Per contracts/reference_data_cache_contract.md §Property contracts:
- Pre-hydrate: counters are 0.
- Post-hydrate: counters are ``len(scope_fips) × len(year_set)`` each.
- Counters do NOT increment on ``lookup_*`` calls.
- ``total_db_reads == population_db_reads + employment_db_reads``.
"""

from __future__ import annotations

from pathlib import Path

from babylon.engine.headless_runner.reference_data_cache import ReferenceDataCache


class TestCacheCounters:
    """Cache property contract from `reference_data_cache_contract.md`."""

    def test_pre_hydrate_counters_are_zero(self, tmp_path: Path) -> None:
        cache = ReferenceDataCache(tmp_path / "ref.sqlite")
        assert cache.population_db_reads == 0
        assert cache.employment_db_reads == 0
        assert cache.total_db_reads == 0

    def test_post_hydrate_counter_equals_n_times_y(self, simple_ref_sqlite: Path) -> None:
        """``population_db_reads == employment_db_reads == N × Y``."""
        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset({"26163", "26125"}),
            year_set=frozenset({2010, 2011}),
        )
        assert cache.population_db_reads == 4  # 2 × 2
        assert cache.employment_db_reads == 4

    def test_total_db_reads_sums_individual_counters(self, simple_ref_sqlite: Path) -> None:
        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset({"26163", "26125"}),
            year_set=frozenset({2010, 2011}),
        )
        assert cache.total_db_reads == cache.population_db_reads + cache.employment_db_reads
        assert cache.total_db_reads == 8

    def test_lookup_calls_do_not_increment_counter(self, simple_ref_sqlite: Path) -> None:
        """Per R6: counter is hydrate-time only. Lookups must not mutate it."""
        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset({"26163"}),
            year_set=frozenset({2010, 2011}),
        )
        baseline = cache.total_db_reads
        for _ in range(20):
            cache.lookup_population("26163", 2010)
            cache.lookup_employment_proxy("26163", 2011)
        assert cache.total_db_reads == baseline

    def test_mark_miss_calls_do_not_increment_counter(self, simple_ref_sqlite: Path) -> None:
        """mark_*_miss_logged is observability, not a read — no counter change."""
        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset({"26125"}),
            year_set=frozenset({2011}),
        )
        baseline = cache.total_db_reads
        cache.mark_population_miss_logged("26125", 2011)
        cache.mark_employment_miss_logged("26125", 2011)
        assert cache.total_db_reads == baseline
