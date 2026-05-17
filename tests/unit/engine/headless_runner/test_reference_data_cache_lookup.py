"""Unit tests for ``lookup_*`` semantics (spec-069 T011).

Per contracts/reference_data_cache_contract.md §lookup_population:
- Returns the cached value (or None) for in-scope tuples.
- Raises KeyError for out-of-scope tuples.
- Idempotent (same call → same value, no counter mutation).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.engine.headless_runner.reference_data_cache import ReferenceDataCache


class TestLookupSemantics:
    """Post-hydrate lookup behavior per the contract."""

    def test_lookup_population_returns_cached_value(self, simple_ref_sqlite: Path) -> None:
        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset({"26163"}),
            year_set=frozenset({2010, 2011}),
        )
        assert cache.lookup_population("26163", 2010) == 100
        assert cache.lookup_population("26163", 2011) == 200

    def test_lookup_employment_returns_cached_value(self, simple_ref_sqlite: Path) -> None:
        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset({"26163"}),
            year_set=frozenset({2010, 2011}),
        )
        assert cache.lookup_employment_proxy("26163", 2010) == 50.0
        assert cache.lookup_employment_proxy("26163", 2011) == 60.0

    def test_lookup_out_of_scope_fips_raises_keyerror(self, simple_ref_sqlite: Path) -> None:
        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset({"26163"}),
            year_set=frozenset({2010}),
        )
        with pytest.raises(KeyError):
            cache.lookup_population("99999", 2010)

    def test_lookup_out_of_scope_year_raises_keyerror(self, simple_ref_sqlite: Path) -> None:
        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset({"26163"}),
            year_set=frozenset({2010}),
        )
        with pytest.raises(KeyError):
            cache.lookup_population("26163", 2011)

    def test_lookup_idempotent(self, simple_ref_sqlite: Path) -> None:
        """Repeated calls return the same value; counters do not increment."""
        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset({"26163"}),
            year_set=frozenset({2010}),
        )
        baseline_count = cache.total_db_reads
        first = cache.lookup_population("26163", 2010)
        for _ in range(5):
            assert cache.lookup_population("26163", 2010) == first
        assert cache.total_db_reads == baseline_count
