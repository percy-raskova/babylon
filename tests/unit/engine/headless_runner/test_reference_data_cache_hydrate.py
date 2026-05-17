"""Unit tests for ``ReferenceDataCache.hydrate`` happy path (spec-069 T008).

Per contracts/reference_data_cache_contract.md §hydrate and
data-model.md §2 algorithm:
- For every (fips, year) in scope_fips × year_set, an entry exists.
- Counters equal len(scope_fips) × len(year_set).
- Exactly one sqlite3.Connection opened and closed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.engine.headless_runner.reference_data_cache import ReferenceDataCache


class TestHydrateHappyPath:
    """Hydrate against a fixture-backed temp SQLite."""

    def test_hydrate_populates_all_tuples(self, simple_ref_sqlite: Path) -> None:
        """Every (fips × year) tuple in scope yields a cache entry."""
        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset({"26163", "26125"}),
            year_set=frozenset({2010, 2011}),
        )
        assert cache._hydrated is True
        assert len(cache._entries) == 4
        for fips in ("26163", "26125"):
            for year in (2010, 2011):
                assert (fips, year) in cache._entries

    def test_hydrate_counter_equals_n_times_y(self, simple_ref_sqlite: Path) -> None:
        """``population_db_reads == employment_db_reads == N × Y``."""
        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset({"26163", "26125"}),
            year_set=frozenset({2010, 2011}),
        )
        assert cache.population_db_reads == 4
        assert cache.employment_db_reads == 4
        assert cache.total_db_reads == 8

    def test_hydrate_resolves_concrete_values(self, simple_ref_sqlite: Path) -> None:
        """26163/2010: Census=100, QCEW=50 → pop=100, emp=50.0."""
        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset({"26163"}),
            year_set=frozenset({2010}),
        )
        assert cache.lookup_population("26163", 2010) == 100
        assert cache.lookup_employment_proxy("26163", 2010) == 50.0

    def test_hydrate_empty_year_set_is_noop(self, simple_ref_sqlite: Path) -> None:
        """Degenerate zero-tick: empty year_set yields hydrated cache with 0 entries."""
        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(scope_fips=frozenset({"26163"}), year_set=frozenset())
        assert cache._hydrated is True
        assert len(cache._entries) == 0
        assert cache.total_db_reads == 0

    def test_hydrate_empty_scope_raises(self, simple_ref_sqlite: Path) -> None:
        """Empty scope_fips is ValueError per contract."""
        cache = ReferenceDataCache(simple_ref_sqlite)
        with pytest.raises(ValueError, match="scope_fips"):
            cache.hydrate(scope_fips=frozenset(), year_set=frozenset({2010}))

    def test_hydrate_missing_sqlite_path_raises(self, tmp_path: Path) -> None:
        """Nonexistent SQLite path is FileNotFoundError per contract."""
        cache = ReferenceDataCache(tmp_path / "missing.sqlite")
        with pytest.raises(FileNotFoundError):
            cache.hydrate(scope_fips=frozenset({"26163"}), year_set=frozenset({2010}))
