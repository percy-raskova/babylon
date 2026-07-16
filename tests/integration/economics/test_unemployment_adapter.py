"""Integration tests for the BLS LAUS county unemployment adapter (Wave 6 D8).

``SQLiteBLSUnemploymentSource`` reads ``fact_bls_unemployment_decomposition``
(U-3 numerator / labor force denominator) keyed by ``dim_county`` +
``dim_time``. Only the U-3 column carries real data in the reference DB —
the U-6/PTER/discouraged decomposition columns are all zero — so the adapter
deliberately exposes U-3 alone. These tests pin the adapter against the real
reference DB the same way ``test_melt_adapters.py`` pins the national MELT
sources.
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.throughput.adapters import SQLiteBLSUnemploymentSource
from babylon.reference.database import get_normalized_session_factory

# Needs the reference SQLite DB — CI provides it via the ci-data artifact.
pytestmark = [pytest.mark.integration, pytest.mark.requires_reference_db]

WAYNE = "26163"
TEST_YEAR = 2015


@pytest.fixture(scope="module")
def unemployment_source() -> SQLiteBLSUnemploymentSource:
    """Create the LAUS adapter against the normalized reference DB."""
    return SQLiteBLSUnemploymentSource(get_normalized_session_factory())


class TestSQLiteBLSUnemploymentSource:
    """Real-DB contract for the county U-3 read."""

    def test_wayne_2015_rate_is_plausible(
        self, unemployment_source: SQLiteBLSUnemploymentSource
    ) -> None:
        """Wayne County 2015 U-3 must exist and sit in a sane band.

        BLS LAUS puts Wayne County's 2015 annual U-3 around 6-7%; the bound
        here is a wiring regression guard, not a data-accuracy assertion.
        """
        rate = unemployment_source.get_county_unemployment_rate(WAYNE, TEST_YEAR)

        assert rate is not None, "Wayne 2015 should be present in LAUS data"
        assert 0.01 < rate < 0.30, f"U-3 rate {rate} outside sanity band"

    def test_unavailable_year_returns_none(
        self, unemployment_source: SQLiteBLSUnemploymentSource
    ) -> None:
        """A year outside the loaded range is an honest None, never a rate."""
        assert unemployment_source.get_county_unemployment_rate(WAYNE, 1900) is None

    def test_unknown_county_returns_none(
        self, unemployment_source: SQLiteBLSUnemploymentSource
    ) -> None:
        """A FIPS with no dim_county row is an honest None."""
        assert unemployment_source.get_county_unemployment_rate("99999", TEST_YEAR) is None
