"""Fast-gate value-equality test (spec-069 T030 / FR-005 / US3).

The cache MUST return values byte-identical (for ints) and
float-equality-identical (for floats) to what the legacy per-tick
fetchers would have returned for the same ``(fips, year)`` tuple
against the same DB state. This is the foundation of SC-003
(byte-identical trace.csv) — without value-equivalence at the
lookup layer, the trace cannot be byte-equal.

This test exercises a small fixture-backed SQLite (no canonical run
needed) and compares ``cache.lookup_*`` against
``fetch_*_for_county_at_tick`` directly.
"""

from __future__ import annotations

from pathlib import Path

from babylon.engine.headless_runner.reference_data_cache import ReferenceDataCache
from babylon.persistence.county_aggregation import (
    fetch_employment_proxy_for_county_at_tick,
    fetch_population_for_county_at_tick,
)


def _year_to_tick(year: int, start_year: int) -> int:
    """Return the tick number that maps to (year, start_year) under the weekly cadence.

    Mirror of ``_tick_to_year(tick, start_year) = start_year + tick // 52``.
    Returns the FIRST tick of ``year`` (tick number = (year - start_year) * 52).
    """
    return (year - start_year) * 52


class TestCacheLegacyEquivalence:
    """FR-005: cache and legacy fetcher return the same value for the same tuple."""

    def test_population_equals_legacy_fetcher(self, simple_ref_sqlite: Path) -> None:
        """``cache.lookup_population == fetch_population_for_county_at_tick``."""
        start_year = 2010
        years = (2010, 2011)
        fips_list = ("26163",)  # Census + QCEW both present

        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset(fips_list),
            year_set=frozenset(years),
        )

        for fips in fips_list:
            for year in years:
                cached = cache.lookup_population(fips, year)
                legacy = fetch_population_for_county_at_tick(
                    simple_ref_sqlite,
                    fips,
                    tick=_year_to_tick(year, start_year),
                    start_year=start_year,
                )
                assert cached == legacy, (
                    f"FR-005 violation at ({fips}, {year}): cache={cached!r} legacy={legacy!r}"
                )

    def test_employment_proxy_equals_legacy_fetcher(self, simple_ref_sqlite: Path) -> None:
        """``cache.lookup_employment_proxy == fetch_employment_proxy_for_county_at_tick``."""
        start_year = 2010
        years = (2010, 2011)
        fips_list = ("26163",)

        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset(fips_list),
            year_set=frozenset(years),
        )

        for fips in fips_list:
            for year in years:
                cached = cache.lookup_employment_proxy(fips, year)
                legacy = fetch_employment_proxy_for_county_at_tick(
                    simple_ref_sqlite,
                    fips,
                    tick=_year_to_tick(year, start_year),
                    start_year=start_year,
                )
                assert cached == legacy, (
                    f"FR-005 violation at ({fips}, {year}): cache={cached!r} legacy={legacy!r}"
                )

    def test_population_qcew_fallback_path_equivalence(self, simple_ref_sqlite: Path) -> None:
        """26125/2010: Census missing → QCEW × 0.33 fallback should match.

        The legacy fetcher computes ``int(qcew_emp * 0.33)``; the cache must
        produce the bit-identical int via the same formula.
        """
        cache = ReferenceDataCache(simple_ref_sqlite)
        cache.hydrate(
            scope_fips=frozenset({"26125"}),
            year_set=frozenset({2010}),
        )
        cached = cache.lookup_population("26125", 2010)
        legacy = fetch_population_for_county_at_tick(
            simple_ref_sqlite,
            "26125",
            tick=0,
            start_year=2010,
        )
        assert cached == legacy
        # And it should specifically be int(70 * 0.33) = 23.
        assert cached == 23
