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


class TestQCEWMedianHourlyWage:
    """Real-DB contract for the employment-weighted p50 hourly wage.

    Owner-queue item 60: the estimator is the p50 of the county's
    employment distribution sorted by 6-digit-industry mean wage — a
    genuine median approximation (within-industry dispersion invisible),
    unlike the raw QCEW mean it replaces as the bootstrap.
    """

    @pytest.fixture(scope="class")
    def wage_source(self):  # type: ignore[no-untyped-def]
        from babylon.domain.economics.throughput.adapters import SQLiteQCEWCountyNAICSSource

        return SQLiteQCEWCountyNAICSSource(get_normalized_session_factory())

    def test_wayne_2015_p50_is_plausible(self, wage_source) -> None:  # type: ignore[no-untyped-def]
        """Wayne 2015 median hourly wage must exist and sit in a sane band."""
        wage = wage_source.get_county_median_hourly_wage(WAYNE, TEST_YEAR)

        assert wage is not None, "Wayne 2015 should have QCEW 6-digit leaves"
        assert 5.0 < wage < 60.0, f"p50 hourly wage {wage} outside sanity band"

    def test_unavailable_year_returns_none(self, wage_source) -> None:  # type: ignore[no-untyped-def]
        assert wage_source.get_county_median_hourly_wage(WAYNE, 1900) is None

    def test_unknown_county_returns_none(self, wage_source) -> None:  # type: ignore[no-untyped-def]
        assert wage_source.get_county_median_hourly_wage("99999", TEST_YEAR) is None


class TestSQLiteCensusIncomeSource:
    """Real-DB contract for the top/bottom ACS B19001 bracket-ratio read.

    Wave 6 C3 (epochs audit item 167): ``fact_census_income`` had been
    "collapsed to SUM" with no bracket-aware reader. This adapter's ratio is
    a household-COUNT proxy (top-band households / bottom-band households),
    not an income-level percentile ratio — see
    ``SQLiteCensusIncomeSource``'s docstring for the exact band choice and
    the race='Total' aggregation rationale.
    """

    @pytest.fixture(scope="class")
    def income_source(self):  # type: ignore[no-untyped-def]
        from babylon.domain.economics.throughput.adapters import SQLiteCensusIncomeSource

        return SQLiteCensusIncomeSource(get_normalized_session_factory())

    def test_wayne_2015_ratio_is_plausible(self, income_source) -> None:  # type: ignore[no-untyped-def]
        """Wayne 2015 top/bottom bracket ratio must exist and be sane.

        This is a wiring regression guard (bounds wide enough to tolerate a
        county with either far more or far fewer high-income households than
        low-income ones), not a data-accuracy assertion.
        """
        ratio = income_source.get_county_bracket_ratio(WAYNE, TEST_YEAR)

        assert ratio is not None, "Wayne 2015 should have fact_census_income rows"
        assert 0.0 < ratio < 1000.0, f"bracket ratio {ratio} outside sanity band"

    def test_unavailable_year_returns_none(self, income_source) -> None:  # type: ignore[no-untyped-def]
        """A year outside the loaded range is an honest None, never a ratio."""
        assert income_source.get_county_bracket_ratio(WAYNE, 1900) is None

    def test_unknown_county_returns_none(self, income_source) -> None:  # type: ignore[no-untyped-def]
        """A FIPS with no dim_county row is an honest None."""
        assert income_source.get_county_bracket_ratio("99999", TEST_YEAR) is None
