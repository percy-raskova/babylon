"""FRED data parsing utilities.

Transforms raw API responses and SeriesData into database-ready records.
Handles date parsing, year/month extraction, and quarter calculation.
"""

from dataclasses import dataclass
from datetime import datetime

from babylon.data.fred.api_client import (
    DFA_WEALTH_LEVEL_SERIES,
    DFA_WEALTH_SHARE_SERIES,
    INDUSTRY_UNEMPLOYMENT_SERIES,
    NATIONAL_SERIES,
    US_STATES,
    SeriesData,
)


@dataclass
class NationalRecord:
    """Parsed national series observation ready for database insertion."""

    series_id: str
    date: str
    year: int
    month: int | None
    quarter: int | None
    value: float | None


@dataclass
class StateUnemploymentRecord:
    """Parsed state unemployment observation ready for database insertion."""

    fips_code: str
    state_name: str
    abbreviation: str
    date: str
    year: int
    month: int | None
    unemployment_rate: float | None


@dataclass
class IndustryUnemploymentRecord:
    """Parsed industry unemployment observation ready for database insertion."""

    lnu_code: str
    industry_name: str
    naics_sector: str
    date: str
    year: int
    month: int | None
    unemployment_rate: float | None


def parse_date(date_str: str) -> tuple[int, int | None, int | None]:
    """Parse date string into year, month, and quarter.

    Args:
        date_str: Date in YYYY-MM-DD format.

    Returns:
        Tuple of (year, month, quarter). Month/quarter may be None for annual data.
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        year = dt.year
        month = dt.month
        quarter = (month - 1) // 3 + 1
        return year, month, quarter
    except ValueError:
        # Handle annual data (just year)
        try:
            year = int(date_str[:4])
            return year, None, None
        except ValueError:
            return 0, None, None


def filter_observations_by_year(
    series_data: SeriesData,
    year: int,
) -> SeriesData:
    """Filter observations to only include specified year.

    Args:
        series_data: Full series data with observations.
        year: Year to filter to.

    Returns:
        SeriesData with only observations from specified year.
    """
    filtered_obs = [obs for obs in series_data.observations if obs.date.startswith(str(year))]
    return SeriesData(
        metadata=series_data.metadata,
        observations=filtered_obs,
    )


def parse_national_series(
    series_data: SeriesData,
    year: int | None = None,
) -> list[NationalRecord]:
    """Parse national series data into database records.

    Args:
        series_data: SeriesData from API client.
        year: Optional year to filter to.

    Returns:
        List of NationalRecord objects ready for insertion.
    """
    if year:
        series_data = filter_observations_by_year(series_data, year)

    records: list[NationalRecord] = []
    for obs in series_data.observations:
        parsed_year, month, quarter = parse_date(obs.date)

        records.append(
            NationalRecord(
                series_id=series_data.metadata.series_id,
                date=obs.date,
                year=parsed_year,
                month=month,
                quarter=quarter,
                value=obs.value,
            )
        )

    return records


def parse_state_unemployment(
    series_data: SeriesData,
    fips_code: str,
    year: int | None = None,
) -> list[StateUnemploymentRecord]:
    """Parse state unemployment data into database records.

    Args:
        series_data: SeriesData from API client.
        fips_code: 2-digit state FIPS code.
        year: Optional year to filter to.

    Returns:
        List of StateUnemploymentRecord objects ready for insertion.
    """
    if year:
        series_data = filter_observations_by_year(series_data, year)

    state_info = US_STATES.get(fips_code, ("Unknown", "??"))
    state_name, abbreviation = state_info

    records: list[StateUnemploymentRecord] = []
    for obs in series_data.observations:
        parsed_year, month, _ = parse_date(obs.date)

        records.append(
            StateUnemploymentRecord(
                fips_code=fips_code,
                state_name=state_name,
                abbreviation=abbreviation,
                date=obs.date,
                year=parsed_year,
                month=month,
                unemployment_rate=obs.value,
            )
        )

    return records


def parse_industry_unemployment(
    series_data: SeriesData,
    lnu_code: str,
    year: int | None = None,
) -> list[IndustryUnemploymentRecord]:
    """Parse industry unemployment data into database records.

    Args:
        series_data: SeriesData from API client.
        lnu_code: LNU series code.
        year: Optional year to filter to.

    Returns:
        List of IndustryUnemploymentRecord objects ready for insertion.
    """
    if year:
        series_data = filter_observations_by_year(series_data, year)

    industry_info = INDUSTRY_UNEMPLOYMENT_SERIES.get(lnu_code, ("Unknown", ""))
    industry_name, naics_sector = industry_info

    records: list[IndustryUnemploymentRecord] = []
    for obs in series_data.observations:
        parsed_year, month, _ = parse_date(obs.date)

        records.append(
            IndustryUnemploymentRecord(
                lnu_code=lnu_code,
                industry_name=industry_name,
                naics_sector=naics_sector,
                date=obs.date,
                year=parsed_year,
                month=month,
                unemployment_rate=obs.value,
            )
        )

    return records


def get_national_series_list() -> list[str]:
    """Get list of national series IDs to fetch.

    Returns:
        List of series ID strings.
    """
    return list(NATIONAL_SERIES.keys())


def get_state_fips_list() -> list[str]:
    """Get list of state FIPS codes.

    Returns:
        List of 2-digit FIPS code strings.
    """
    return list(US_STATES.keys())


def get_industry_series_list() -> list[str]:
    """Get list of industry unemployment series IDs.

    Returns:
        List of LNU series ID strings.
    """
    return list(INDUSTRY_UNEMPLOYMENT_SERIES.keys())


# =============================================================================
# DFA Wealth Distribution Parsing
# =============================================================================


@dataclass
class WealthLevelRecord:
    """Parsed DFA wealth level observation ready for database insertion.

    Represents a quarterly observation of absolute wealth ($ millions)
    held by a specific percentile class in a specific asset category.

    Attributes:
        series_id: FRED series identifier (e.g., "WFRBLT01000").
        percentile_code: DFA percentile code (LT01, N09, N40, B50).
        asset_category: Asset category (TOTAL_ASSETS, REAL_ESTATE, NET_WORTH).
        date: Observation date (YYYY-MM-DD format, quarterly).
        year: Year for filtering.
        quarter: Quarter (1-4) for quarterly aggregation.
        value_millions: Wealth in millions of USD.
    """

    series_id: str
    percentile_code: str
    asset_category: str
    date: str
    year: int
    quarter: int | None
    value_millions: float | None


@dataclass
class WealthShareRecord:
    """Parsed DFA wealth share observation ready for database insertion.

    Represents a quarterly observation of wealth share (percentage)
    held by a specific percentile class in a specific asset category.

    Attributes:
        series_id: FRED series identifier (e.g., "WFRBST01134").
        percentile_code: DFA percentile code (LT01, N09, N40, B50).
        asset_category: Asset category (TOTAL_ASSETS, NET_WORTH).
        date: Observation date (YYYY-MM-DD format, quarterly).
        year: Year for filtering.
        quarter: Quarter (1-4) for quarterly aggregation.
        share_percent: Share of total as percentage (0-100).
    """

    series_id: str
    percentile_code: str
    asset_category: str
    date: str
    year: int
    quarter: int | None
    share_percent: float | None


def parse_wealth_level(
    series_data: SeriesData,
    percentile_code: str,
    asset_category: str,
    year: int | None = None,
) -> list[WealthLevelRecord]:
    """Parse DFA wealth level data into database records.

    Args:
        series_data: SeriesData from API client.
        percentile_code: DFA percentile code (LT01, N09, N40, B50).
        asset_category: Asset category (TOTAL_ASSETS, REAL_ESTATE, NET_WORTH).
        year: Optional year to filter to.

    Returns:
        List of WealthLevelRecord objects ready for insertion.
    """
    if year:
        series_data = filter_observations_by_year(series_data, year)

    records: list[WealthLevelRecord] = []
    for obs in series_data.observations:
        parsed_year, _, quarter = parse_date(obs.date)

        records.append(
            WealthLevelRecord(
                series_id=series_data.metadata.series_id,
                percentile_code=percentile_code,
                asset_category=asset_category,
                date=obs.date,
                year=parsed_year,
                quarter=quarter,
                value_millions=obs.value,
            )
        )

    return records


def parse_wealth_share(
    series_data: SeriesData,
    percentile_code: str,
    asset_category: str,
    year: int | None = None,
) -> list[WealthShareRecord]:
    """Parse DFA wealth share data into database records.

    Args:
        series_data: SeriesData from API client.
        percentile_code: DFA percentile code (LT01, N09, N40, B50).
        asset_category: Asset category (TOTAL_ASSETS, NET_WORTH).
        year: Optional year to filter to.

    Returns:
        List of WealthShareRecord objects ready for insertion.
    """
    if year:
        series_data = filter_observations_by_year(series_data, year)

    records: list[WealthShareRecord] = []
    for obs in series_data.observations:
        parsed_year, _, quarter = parse_date(obs.date)

        records.append(
            WealthShareRecord(
                series_id=series_data.metadata.series_id,
                percentile_code=percentile_code,
                asset_category=asset_category,
                date=obs.date,
                year=parsed_year,
                quarter=quarter,
                share_percent=obs.value,
            )
        )

    return records


def get_dfa_level_series_list() -> list[tuple[str, str, str]]:
    """Get list of DFA wealth level series.

    Returns:
        List of (series_id, percentile_code, asset_category) tuples.
    """
    return [
        (series_id, percentile_code, asset_category)
        for (percentile_code, asset_category), series_id in DFA_WEALTH_LEVEL_SERIES.items()
    ]


def get_dfa_share_series_list() -> list[tuple[str, str, str]]:
    """Get list of DFA wealth share series.

    Returns:
        List of (series_id, percentile_code, asset_category) tuples.
    """
    return [
        (series_id, percentile_code, asset_category)
        for (percentile_code, asset_category), series_id in DFA_WEALTH_SHARE_SERIES.items()
    ]
