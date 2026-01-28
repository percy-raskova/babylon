"""Unit tests for FRED data parser.

Tests parsing logic for transforming FRED API responses into database records.
"""

from __future__ import annotations

import pytest

from babylon.data.fred.api_client import Observation, SeriesData, SeriesMetadata
from babylon.data.fred.parser import (
    IndustryUnemploymentRecord,
    NationalRecord,
    StateUnemploymentRecord,
    WealthLevelRecord,
    WealthShareRecord,
    filter_observations_by_year,
    get_dfa_level_series_list,
    get_dfa_share_series_list,
    get_industry_series_list,
    get_national_series_list,
    get_state_fips_list,
    parse_date,
    parse_industry_unemployment,
    parse_national_series,
    parse_state_unemployment,
    parse_wealth_level,
    parse_wealth_share,
)


def _make_metadata(series_id: str = "TEST") -> SeriesMetadata:
    """Create test metadata fixture."""
    return SeriesMetadata(
        series_id=series_id,
        title="Test Series",
        units="Test Units",
        frequency="Monthly",
        seasonal_adjustment="Not Seasonally Adjusted",
        observation_start="2020-01-01",
        observation_end="2020-12-01",
        last_updated="2024-01-01",
    )


def _make_series_data(
    observations: list[tuple[str, float | None]],
    series_id: str = "TEST",
) -> SeriesData:
    """Create test SeriesData with given observations."""
    return SeriesData(
        metadata=_make_metadata(series_id),
        observations=[Observation(date=d, value=v) for d, v in observations],
    )


@pytest.mark.unit
class TestParseDateFunction:
    """Tests for parse_date utility function."""

    def test_parse_full_date(self) -> None:
        """Parses YYYY-MM-DD format correctly."""
        year, month, quarter = parse_date("2020-06-15")
        assert year == 2020
        assert month == 6
        assert quarter == 2

    def test_parse_date_january(self) -> None:
        """January is quarter 1."""
        year, month, quarter = parse_date("2020-01-01")
        assert year == 2020
        assert month == 1
        assert quarter == 1

    def test_parse_date_december(self) -> None:
        """December is quarter 4."""
        year, month, quarter = parse_date("2020-12-15")
        assert year == 2020
        assert month == 12
        assert quarter == 4

    def test_parse_date_quarterly_boundaries(self) -> None:
        """Quarter boundaries are correct."""
        # Q1: Jan, Feb, Mar
        _, _, q = parse_date("2020-03-01")
        assert q == 1

        # Q2: Apr, May, Jun
        _, _, q = parse_date("2020-04-01")
        assert q == 2

        # Q3: Jul, Aug, Sep
        _, _, q = parse_date("2020-09-01")
        assert q == 3

        # Q4: Oct, Nov, Dec
        _, _, q = parse_date("2020-10-01")
        assert q == 4

    def test_parse_annual_date(self) -> None:
        """Handles annual data (just year)."""
        year, month, quarter = parse_date("2020")
        assert year == 2020
        assert month is None
        assert quarter is None

    def test_parse_invalid_date(self) -> None:
        """Returns zeros for invalid date formats."""
        year, month, quarter = parse_date("invalid")
        assert year == 0
        assert month is None
        assert quarter is None


@pytest.mark.unit
class TestFilterObservationsByYear:
    """Tests for year filtering."""

    def test_filters_to_single_year(self) -> None:
        """Filters observations to requested year."""
        series = _make_series_data(
            [
                ("2019-12-01", 100.0),
                ("2020-01-01", 101.0),
                ("2020-06-01", 102.0),
                ("2021-01-01", 103.0),
            ]
        )

        filtered = filter_observations_by_year(series, 2020)
        assert len(filtered.observations) == 2
        assert all(o.date.startswith("2020") for o in filtered.observations)

    def test_preserves_metadata(self) -> None:
        """Filtering preserves series metadata."""
        series = _make_series_data([("2020-01-01", 100.0)])
        filtered = filter_observations_by_year(series, 2020)

        assert filtered.metadata.series_id == series.metadata.series_id
        assert filtered.metadata.title == series.metadata.title

    def test_empty_result_for_no_matching_year(self) -> None:
        """Returns empty observations if year not found."""
        series = _make_series_data([("2020-01-01", 100.0)])
        filtered = filter_observations_by_year(series, 2019)

        assert len(filtered.observations) == 0


@pytest.mark.unit
class TestParseNationalSeries:
    """Tests for national series parsing."""

    def test_creates_national_records(self) -> None:
        """Parses observations into NationalRecord objects."""
        series = _make_series_data(
            [
                ("2020-01-01", 100.0),
                ("2020-02-01", 101.5),
            ],
            series_id="CPIAUCSL",
        )

        records = parse_national_series(series)

        assert len(records) == 2
        assert all(isinstance(r, NationalRecord) for r in records)

    def test_record_contains_expected_fields(self) -> None:
        """NationalRecord has all expected fields populated."""
        series = _make_series_data([("2020-06-15", 100.5)], series_id="GDP")
        records = parse_national_series(series)

        record = records[0]
        assert record.series_id == "GDP"
        assert record.date == "2020-06-15"
        assert record.year == 2020
        assert record.month == 6
        assert record.quarter == 2
        assert record.value == 100.5

    def test_handles_none_values(self) -> None:
        """Handles missing values correctly."""
        series = _make_series_data([("2020-01-01", None)])
        records = parse_national_series(series)

        assert records[0].value is None

    def test_year_filter_applied(self) -> None:
        """Year filter reduces results."""
        series = _make_series_data(
            [
                ("2019-12-01", 100.0),
                ("2020-01-01", 101.0),
            ]
        )

        records = parse_national_series(series, year=2020)
        assert len(records) == 1
        assert records[0].year == 2020


@pytest.mark.unit
class TestParseStateUnemployment:
    """Tests for state unemployment parsing."""

    def test_creates_state_records(self) -> None:
        """Parses state unemployment data correctly."""
        series = _make_series_data([("2020-01-01", 3.5)])
        records = parse_state_unemployment(series, fips_code="06")

        assert len(records) == 1
        assert isinstance(records[0], StateUnemploymentRecord)

    def test_record_has_state_info(self) -> None:
        """Record includes state name and abbreviation."""
        series = _make_series_data([("2020-01-01", 3.5)])
        records = parse_state_unemployment(series, fips_code="06")

        record = records[0]
        assert record.fips_code == "06"
        assert record.state_name == "California"
        assert record.abbreviation == "CA"

    def test_unknown_fips_handled(self) -> None:
        """Unknown FIPS code uses fallback values."""
        series = _make_series_data([("2020-01-01", 3.5)])
        records = parse_state_unemployment(series, fips_code="99")

        record = records[0]
        assert record.fips_code == "99"
        assert record.state_name == "Unknown"
        assert record.abbreviation == "??"


@pytest.mark.unit
class TestParseIndustryUnemployment:
    """Tests for industry unemployment parsing."""

    def test_creates_industry_records(self) -> None:
        """Parses industry unemployment data correctly."""
        series = _make_series_data([("2020-01-01", 5.2)])
        records = parse_industry_unemployment(series, lnu_code="LNU04032231")

        assert len(records) == 1
        assert isinstance(records[0], IndustryUnemploymentRecord)

    def test_record_has_industry_info(self) -> None:
        """Record includes industry name and NAICS sector."""
        series = _make_series_data([("2020-01-01", 5.2)])
        records = parse_industry_unemployment(series, lnu_code="LNU04032231")

        record = records[0]
        assert record.lnu_code == "LNU04032231"
        assert record.industry_name == "Construction"
        assert record.naics_sector == "23"


@pytest.mark.unit
class TestParseWealthLevel:
    """Tests for DFA wealth level parsing."""

    def test_creates_wealth_level_records(self) -> None:
        """Parses wealth level data correctly."""
        series = _make_series_data([("2020-03-31", 50000.0)], series_id="WFRBLT01000")
        records = parse_wealth_level(series, percentile_code="LT01", asset_category="TOTAL_ASSETS")

        assert len(records) == 1
        assert isinstance(records[0], WealthLevelRecord)

    def test_record_has_classification_info(self) -> None:
        """Record includes percentile and asset category."""
        series = _make_series_data([("2020-03-31", 50000.0)], series_id="WFRBLT01000")
        records = parse_wealth_level(series, percentile_code="LT01", asset_category="TOTAL_ASSETS")

        record = records[0]
        assert record.series_id == "WFRBLT01000"
        assert record.percentile_code == "LT01"
        assert record.asset_category == "TOTAL_ASSETS"
        assert record.value_millions == 50000.0


@pytest.mark.unit
class TestParseWealthShare:
    """Tests for DFA wealth share parsing."""

    def test_creates_wealth_share_records(self) -> None:
        """Parses wealth share data correctly."""
        series = _make_series_data([("2020-03-31", 31.5)], series_id="WFRBST01134")
        records = parse_wealth_share(series, percentile_code="LT01", asset_category="NET_WORTH")

        assert len(records) == 1
        assert isinstance(records[0], WealthShareRecord)

    def test_record_has_share_percent(self) -> None:
        """Record includes share percentage."""
        series = _make_series_data([("2020-03-31", 31.5)], series_id="WFRBST01134")
        records = parse_wealth_share(series, percentile_code="LT01", asset_category="NET_WORTH")

        record = records[0]
        assert record.share_percent == 31.5


@pytest.mark.unit
class TestSeriesListFunctions:
    """Tests for series list helper functions."""

    def test_get_national_series_list(self) -> None:
        """Returns list of national series IDs."""
        series_list = get_national_series_list()

        assert isinstance(series_list, list)
        assert len(series_list) > 0
        assert "CPIAUCSL" in series_list  # Consumer Price Index
        assert "UNRATE" in series_list  # Unemployment Rate

    def test_get_state_fips_list(self) -> None:
        """Returns list of state FIPS codes."""
        fips_list = get_state_fips_list()

        assert isinstance(fips_list, list)
        assert len(fips_list) >= 50  # 50 states + DC
        assert "06" in fips_list  # California
        assert "48" in fips_list  # Texas

    def test_get_industry_series_list(self) -> None:
        """Returns list of industry series IDs."""
        series_list = get_industry_series_list()

        assert isinstance(series_list, list)
        assert len(series_list) > 0
        assert "LNU04032231" in series_list  # Construction

    def test_get_dfa_level_series_list(self) -> None:
        """Returns list of DFA wealth level series tuples."""
        series_list = get_dfa_level_series_list()

        assert isinstance(series_list, list)
        assert len(series_list) > 0

        # Each entry is (series_id, percentile_code, asset_category)
        for entry in series_list:
            assert len(entry) == 3

    def test_get_dfa_share_series_list(self) -> None:
        """Returns list of DFA wealth share series tuples."""
        series_list = get_dfa_share_series_list()

        assert isinstance(series_list, list)
        assert len(series_list) > 0
