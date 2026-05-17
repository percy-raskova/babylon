"""Unit tests for per-field nullability semantics (spec-069 T010 / R2).

Census + QCEW coverage is asymmetric (research.md R2):
- Census missing AND QCEW missing → population=None, employment_proxy=None
- Census missing, QCEW present → population=int(QCEW × 0.33), employment_proxy=float(QCEW)
- Census present, QCEW missing → population=Census, employment_proxy=None
- Census present, QCEW present → population=Census, employment_proxy=float(QCEW)
"""

from __future__ import annotations

from pathlib import Path

from babylon.engine.headless_runner.reference_data_cache import ReferenceDataCache


class TestThreeStateNullability:
    """Per-field nullability matches the legacy fetchers."""

    def test_census_and_qcew_present(self, simple_ref_sqlite: Path) -> None:
        """26163/2010: Census=100, QCEW=50 → (100, 50.0)."""
        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset({"26163"}),
            year_set=frozenset({2010}),
        )
        assert cache.lookup_population("26163", 2010) == 100
        assert cache.lookup_employment_proxy("26163", 2010) == 50.0

    def test_census_missing_qcew_present_uses_fallback(self, simple_ref_sqlite: Path) -> None:
        """26125/2010: Census=missing, QCEW=70 → pop=int(70*0.33)=23, emp=70.0."""
        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset({"26125"}),
            year_set=frozenset({2010}),
        )
        assert cache.lookup_population("26125", 2010) == 23
        assert cache.lookup_employment_proxy("26125", 2010) == 70.0

    def test_both_missing_returns_none(self, simple_ref_sqlite: Path) -> None:
        """26125/2011: Census=missing, QCEW=missing → (None, None)."""
        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset({"26125"}),
            year_set=frozenset({2011}),
        )
        assert cache.lookup_population("26125", 2011) is None
        assert cache.lookup_employment_proxy("26125", 2011) is None

    def test_independent_nullability_across_tuples(self, simple_ref_sqlite: Path) -> None:
        """Two tuples for the same FIPS can have independent nullability."""
        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset({"26125"}),
            year_set=frozenset({2010, 2011}),
        )
        # 2010: Census missing, QCEW=70 → pop=23, emp=70.0
        # 2011: both missing → (None, None)
        assert cache.lookup_population("26125", 2010) == 23
        assert cache.lookup_population("26125", 2011) is None
        assert cache.lookup_employment_proxy("26125", 2010) == 70.0
        assert cache.lookup_employment_proxy("26125", 2011) is None
