"""Unit tests for ``mark_*_miss_logged`` once-per-tuple semantics (spec-069 T012 / SC-004).

Per contracts/reference_data_cache_contract.md §mark_population_miss_logged:
- First call for a (county, year) tuple returns ``True``.
- All subsequent calls for the same tuple return ``False``.
- Tracker mutation is permanent for the lifetime of the cache.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.engine.headless_runner.reference_data_cache import ReferenceDataCache


class TestMissLoggingOncePerTuple:
    """SC-004 — missing-data warning emitted at most once per (fips, year)."""

    def test_first_call_returns_true(self, simple_ref_sqlite: Path) -> None:
        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset({"26125"}),
            year_set=frozenset({2011}),
        )
        # 26125/2011 is the both-missing tuple.
        assert cache.mark_population_miss_logged("26125", 2011) is True

    def test_second_call_returns_false(self, simple_ref_sqlite: Path) -> None:
        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset({"26125"}),
            year_set=frozenset({2011}),
        )
        cache.mark_population_miss_logged("26125", 2011)
        for _ in range(5):
            assert cache.mark_population_miss_logged("26125", 2011) is False

    def test_population_and_employment_independent(self, simple_ref_sqlite: Path) -> None:
        """Tracking sets are independent across population vs. employment."""
        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset({"26125"}),
            year_set=frozenset({2011}),
        )
        # Marking the population miss does NOT mark the employment miss.
        cache.mark_population_miss_logged("26125", 2011)
        assert cache.mark_employment_miss_logged("26125", 2011) is True

    def test_distinct_tuples_independent(self, simple_ref_sqlite: Path) -> None:
        """Marking (A, Y) does NOT mark (B, Y) or (A, Y2)."""
        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset({"26125", "26163"}),
            year_set=frozenset({2010, 2011}),
        )
        cache.mark_population_miss_logged("26125", 2011)
        assert cache.mark_population_miss_logged("26163", 2011) is True
        assert cache.mark_population_miss_logged("26125", 2010) is True

    def test_out_of_scope_tuple_raises(self, simple_ref_sqlite: Path) -> None:
        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset({"26163"}),
            year_set=frozenset({2010}),
        )
        with pytest.raises(KeyError):
            cache.mark_population_miss_logged("99999", 2010)
