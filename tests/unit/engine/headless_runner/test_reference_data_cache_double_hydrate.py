"""Unit tests for ``ReferenceDataCache.hydrate`` double-call guard (spec-069 T009).

Per contracts/reference_data_cache_contract.md §hydrate Exceptions table:
- Called twice → ``RuntimeError("ReferenceDataCache.hydrate called twice")``
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.engine.headless_runner.reference_data_cache import ReferenceDataCache


class TestDoubleHydrateGuard:
    """A second hydrate on the same instance raises RuntimeError."""

    def test_second_hydrate_raises(self, simple_ref_sqlite: Path) -> None:
        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset({"26163"}),
            year_set=frozenset({2010}),
        )
        with pytest.raises(RuntimeError, match="called twice"):
            cache.hydrate(
                scope_fips=frozenset({"26163"}),
                year_set=frozenset({2010}),
            )

    def test_second_hydrate_does_not_double_counter(self, simple_ref_sqlite: Path) -> None:
        """The aborted second call must not increment counters."""
        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset({"26163"}),
            year_set=frozenset({2010}),
        )
        baseline = cache.total_db_reads
        with pytest.raises(RuntimeError):
            cache.hydrate(
                scope_fips=frozenset({"26163"}),
                year_set=frozenset({2010, 2011}),
            )
        assert cache.total_db_reads == baseline
