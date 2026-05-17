"""Unit tests for ``ReferenceDataCache`` construction (spec-069 T007).

Per contracts/reference_data_cache_contract.md §Construction:
- Constructor does NOT open a connection (path validity deferred).
- Post-ctor state: ``_hydrated == False``, all counters 0, lookups raise.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.engine.headless_runner.reference_data_cache import ReferenceDataCache


class TestConstruction:
    """Construction contract per `reference_data_cache_contract.md` §Construction."""

    def test_construction_records_path(self, tmp_path: Path) -> None:
        """Path is recorded; no connection opened (file need not exist yet)."""
        nonexistent = tmp_path / "does_not_exist.sqlite"
        cache = ReferenceDataCache(nonexistent)
        assert cache._sqlite_path == nonexistent

    def test_construction_initial_unhydrated(self, tmp_path: Path) -> None:
        cache = ReferenceDataCache(tmp_path / "ref.sqlite")
        assert cache._hydrated is False
        assert cache.population_db_reads == 0
        assert cache.employment_db_reads == 0
        assert cache.total_db_reads == 0

    def test_lookup_population_raises_before_hydrate(self, tmp_path: Path) -> None:
        cache = ReferenceDataCache(tmp_path / "ref.sqlite")
        with pytest.raises(RuntimeError, match="not hydrated"):
            cache.lookup_population("26163", 2010)

    def test_lookup_employment_raises_before_hydrate(self, tmp_path: Path) -> None:
        cache = ReferenceDataCache(tmp_path / "ref.sqlite")
        with pytest.raises(RuntimeError, match="not hydrated"):
            cache.lookup_employment_proxy("26163", 2010)

    def test_mark_population_miss_raises_before_hydrate(self, tmp_path: Path) -> None:
        cache = ReferenceDataCache(tmp_path / "ref.sqlite")
        with pytest.raises(RuntimeError, match="not hydrated"):
            cache.mark_population_miss_logged("26163", 2010)

    def test_mark_employment_miss_raises_before_hydrate(self, tmp_path: Path) -> None:
        cache = ReferenceDataCache(tmp_path / "ref.sqlite")
        with pytest.raises(RuntimeError, match="not hydrated"):
            cache.mark_employment_miss_logged("26163", 2010)
