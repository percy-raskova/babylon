"""Data source protocols and implementations for the MarxianHydrator.

This module defines the protocols that abstract data access for QCEW wage data
and BEA industry ratios, enabling dependency injection and testability.

Protocols:
    QCEWDataSource: Fetches county-level wage data by NAICS code.
    BEADataSource: Provides industry-level c/v and s/v ratios.

Implementations:
    SQLiteQCEWSource: Queries the 3NF normalized QCEW database via SQLAlchemy.

Example:
    >>> from babylon.economics.adapters import QCEWDataSource, BEADataSource
    >>> class MyQCEWSource:
    ...     def fetch_county_wages(self, fips: str, year: int) -> list[tuple[str, float, int]]:
    ...         return [("336111", 1000000.0, 500)]  # (naics, wages, employment)

See Also:
    :mod:`babylon.economics.hydrator`: Uses these protocols for transformation.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from sqlalchemy.orm import Session


@runtime_checkable
class QCEWDataSource(Protocol):
    """Protocol for fetching QCEW (Quarterly Census of Employment and Wages) data.

    Implementations provide county-level wage data by NAICS industry code.
    The protocol enables dependency injection for testing with mock data.

    Example:
        >>> class SQLiteQCEWSource:
        ...     def fetch_county_wages(self, fips_code: str, year: int):
        ...         # Query fact_qcew_annual with dim_county join
        ...         return [(naics, wages, employment), ...]
    """

    def fetch_county_wages(self, fips_code: str, year: int) -> list[tuple[str, float, int]]:
        """Fetch wage data for a county-year.

        Args:
            fips_code: 5-digit FIPS county code (e.g., "26163" for Wayne County).
            year: Data year (e.g., 2022).

        Returns:
            List of (naics_code, total_wages, employment) tuples.
            naics_code: 2-6 digit NAICS industry code.
            total_wages: Annual wages for the industry in the county.
            employment: Average annual employment count.
        """
        ...


@runtime_checkable
class BEADataSource(Protocol):
    """Protocol for fetching BEA (Bureau of Economic Analysis) industry ratios.

    Implementations provide industry-level ratios for deriving constant capital
    and surplus value from variable capital (wages).

    Example:
        >>> class SQLiteBEASource:
        ...     def get_sv_ratio(self, naics_code: str, year: int) -> float | None:
        ...         # Query fact_bea_national_industry with bridge_naics_bea
        ...         return computed_ratio or None
    """

    def get_sv_ratio(self, naics_code: str, year: int) -> float | None:
        """Get the surplus value to variable capital ratio (s/v) for an industry.

        The s/v ratio represents the rate of surplus value extraction.
        A ratio of 1.0 means surplus value equals wages paid.

        Args:
            naics_code: NAICS industry code (2-6 digits).
            year: Data year.

        Returns:
            s/v ratio, or None if data is unavailable for this industry.
        """
        ...

    def get_cv_ratio(self, naics_code: str, year: int) -> float | None:
        """Get the constant to variable capital ratio (c/v) for an industry.

        The c/v ratio represents the organic composition of capital.
        Higher ratios indicate more capital-intensive production.

        Args:
            naics_code: NAICS industry code (2-6 digits).
            year: Data year.

        Returns:
            c/v ratio, or None if data is unavailable for this industry.
        """
        ...


# =============================================================================
# IMPLEMENTATIONS
# =============================================================================


class SQLiteQCEWSource:
    """QCEW data source reading from 3NF normalized SQLite database.

    Queries the FactQcewAnnual table with joins to dimension tables
    (DimCounty, DimIndustry, DimTime) to fetch county-level wage data.

    This implementation queries the production database schema using raw SQL
    for performance and simplicity. The query:
    1. Joins fact table with county, industry, and time dimensions
    2. Filters by FIPS code and year
    3. Aggregates wages across ownership types
    4. Returns only records with non-null wage data

    Args:
        session: SQLAlchemy Session for database queries.

    Example:
        >>> from sqlalchemy.orm import Session
        >>> source = SQLiteQCEWSource(session)
        >>> records = source.fetch_county_wages("26163", 2022)
        >>> for naics, wages, employment in records:
        ...     print(f"{naics}: ${wages:,.0f}")
    """

    def __init__(self, session: Session) -> None:
        """Initialize with SQLAlchemy session.

        Args:
            session: SQLAlchemy session for database queries.
        """
        self._session = session

    def fetch_county_wages(self, fips_code: str, year: int) -> list[tuple[str, float, int]]:
        """Fetch wage data for a county-year from the 3NF schema.

        Queries the normalized QCEW schema, joining:
        - FactQcewAnnual (fact table with wages, employment)
        - DimCounty (to filter by FIPS code)
        - DimIndustry (to get NAICS codes)
        - DimTime (to filter by year)

        Aggregates across ownership types (private, government) to get
        total wages and employment per NAICS code.

        Args:
            fips_code: 5-digit FIPS county code (e.g., "26163" for Wayne County).
            year: Data year (e.g., 2022).

        Returns:
            List of (naics_code, total_wages, employment) tuples.
            naics_code: NAICS industry code (2-6 digits).
            total_wages: Annual wages for the industry in the county.
            employment: Average annual employment count.
        """
        # Use raw SQL for performance and explicit control over the query
        query = """
            SELECT
                di.naics_code,
                COALESCE(SUM(f.total_wages_usd), 0.0) as total_wages,
                COALESCE(SUM(f.employment), 0) as employment
            FROM fact_qcew_annual f
            JOIN dim_county dc ON f.county_id = dc.county_id
            JOIN dim_industry di ON f.industry_id = di.industry_id
            JOIN dim_time dt ON f.time_id = dt.time_id
            WHERE dc.fips = :fips
              AND dt.year = :year
              AND dt.is_annual = 1
              AND f.total_wages_usd IS NOT NULL
            GROUP BY di.naics_code
            ORDER BY total_wages DESC
        """

        result = self._session.execute(
            __import__("sqlalchemy").text(query),
            {"fips": fips_code, "year": year},
        )

        # Convert to list of tuples with proper types
        records: list[tuple[str, float, int]] = []
        for row in result:
            naics_code = str(row[0])
            total_wages = float(row[1])
            employment = int(row[2])
            records.append((naics_code, total_wages, employment))

        return records


class InterpolatingBEASource:
    """BEA data source with temporal interpolation.

    This implementation queries the 3NF normalized BEA tables and applies
    temporal interpolation when exact year data is unavailable.

    The interpolation algorithm:
    1. Query for exact year match
    2. If no match, find nearest available year within max_delta
    3. If still no match, return None (caller falls back to YAML defaults)

    For inter-year data:
    - Linear interpolation between the two nearest years
    - Extrapolation beyond known years (up to max_delta) uses nearest value

    Args:
        session: SQLAlchemy Session for database queries.
        max_delta: Maximum years to search for data (default 5).

    Example:
        >>> source = InterpolatingBEASource(session, max_delta=5)
        >>> ratio = source.get_sv_ratio("336111", 2023)  # May interpolate from 2022
    """

    # Default maximum years for interpolation
    DEFAULT_MAX_DELTA: int = 5

    def __init__(self, session: Session, max_delta: int = DEFAULT_MAX_DELTA) -> None:
        """Initialize with SQLAlchemy session and interpolation parameters.

        Args:
            session: SQLAlchemy session for database queries.
            max_delta: Maximum years to search for data. If no data exists
                within ±max_delta years, returns None.
        """
        self._session = session
        self._max_delta = max_delta
        # Cache for available years per industry to avoid repeated queries
        self._year_cache: dict[str, list[int]] = {}

    def get_sv_ratio(self, naics_code: str, year: int) -> float | None:
        """Get the surplus value to variable capital ratio (s/v) with interpolation.

        The s/v ratio is derived from BEA data:
        s/v = (gross_output - intermediate_inputs - compensation) / compensation

        Where:
        - gross_output = total output value
        - intermediate_inputs = purchases from other industries
        - compensation = employee wages and benefits (our "v")
        - surplus = gross_output - intermediate_inputs - compensation (our "s")

        Args:
            naics_code: NAICS industry code (2-6 digits).
            year: Target data year.

        Returns:
            Interpolated s/v ratio, or None if no data available within max_delta.
        """
        return self._get_interpolated_ratio(naics_code, year, "sv")

    def get_cv_ratio(self, naics_code: str, year: int) -> float | None:
        """Get the constant to variable capital ratio (c/v) with interpolation.

        The c/v ratio is derived from BEA data:
        c/v = intermediate_inputs / compensation

        Where:
        - intermediate_inputs = purchases from other industries (our "c")
        - compensation = employee wages and benefits (our "v")

        Args:
            naics_code: NAICS industry code (2-6 digits).
            year: Target data year.

        Returns:
            Interpolated c/v ratio, or None if no data available within max_delta.
        """
        return self._get_interpolated_ratio(naics_code, year, "cv")

    def _get_interpolated_ratio(self, naics_code: str, year: int, ratio_type: str) -> float | None:
        """Get ratio with temporal interpolation.

        Args:
            naics_code: NAICS code to look up.
            year: Target year.
            ratio_type: "sv" or "cv".

        Returns:
            Interpolated ratio or None.
        """
        # Get available years for this industry
        available_years = self._get_available_years(naics_code)
        if not available_years:
            return None

        # Check for exact match first
        if year in available_years:
            return self._query_ratio(naics_code, year, ratio_type)

        # Find nearest years within max_delta
        years_before = [y for y in available_years if y < year]
        years_after = [y for y in available_years if y > year]

        nearest_before = max(years_before) if years_before else None
        nearest_after = min(years_after) if years_after else None

        # Check if we're within max_delta
        before_in_range = nearest_before is not None and (year - nearest_before <= self._max_delta)
        after_in_range = nearest_after is not None and (nearest_after - year <= self._max_delta)

        if before_in_range and after_in_range:
            # Type narrowing: we know both are not None due to the checks above
            assert nearest_before is not None
            assert nearest_after is not None

            # Interpolate between two years
            ratio_before = self._query_ratio(naics_code, nearest_before, ratio_type)
            ratio_after = self._query_ratio(naics_code, nearest_after, ratio_type)

            if ratio_before is not None and ratio_after is not None:
                # Linear interpolation
                weight = (year - nearest_before) / (nearest_after - nearest_before)
                return ratio_before + weight * (ratio_after - ratio_before)
            elif ratio_before is not None:
                return ratio_before
            elif ratio_after is not None:
                return ratio_after
            else:
                return None

        elif before_in_range and nearest_before is not None:
            # Extrapolate from earlier year (use nearest value)
            return self._query_ratio(naics_code, nearest_before, ratio_type)

        elif after_in_range and nearest_after is not None:
            # Extrapolate from later year (use nearest value)
            return self._query_ratio(naics_code, nearest_after, ratio_type)

        else:
            # No data within max_delta
            return None

    def _get_available_years(self, naics_code: str) -> list[int]:
        """Get list of available years for a NAICS code.

        Args:
            naics_code: NAICS code to look up.

        Returns:
            Sorted list of years with data.
        """
        if naics_code in self._year_cache:
            return self._year_cache[naics_code]

        # Query available years from BEA national industry data
        # We join through bridge_naics_bea to map NAICS to BEA industries
        query = """
            SELECT DISTINCT dt.year
            FROM fact_bea_national_industry f
            JOIN bridge_naics_bea bnb ON f.bea_industry_id = bnb.bea_industry_id
            JOIN dim_time dt ON f.time_id = dt.time_id
            WHERE bnb.naics_code = :naics_code
              AND dt.is_annual = 1
            ORDER BY dt.year
        """

        result = self._session.execute(
            __import__("sqlalchemy").text(query),
            {"naics_code": naics_code},
        )

        years = [int(row[0]) for row in result]
        self._year_cache[naics_code] = years
        return years

    def _query_ratio(self, naics_code: str, year: int, ratio_type: str) -> float | None:
        """Query BEA ratio for a specific NAICS code and year.

        Args:
            naics_code: NAICS code to look up.
            year: Specific year to query.
            ratio_type: "sv" or "cv".

        Returns:
            Computed ratio or None.
        """
        # Query BEA national industry data with NAICS bridge
        query = """
            SELECT
                f.gross_output,
                f.intermediate_inputs,
                f.compensation
            FROM fact_bea_national_industry f
            JOIN bridge_naics_bea bnb ON f.bea_industry_id = bnb.bea_industry_id
            JOIN dim_time dt ON f.time_id = dt.time_id
            WHERE bnb.naics_code = :naics_code
              AND dt.year = :year
              AND dt.is_annual = 1
        """

        result = self._session.execute(
            __import__("sqlalchemy").text(query),
            {"naics_code": naics_code, "year": year},
        )

        row = result.fetchone()
        if row is None:
            return None

        gross_output_raw = row[0]
        intermediate_inputs_raw = row[1]
        compensation_raw = row[2]  # This is "v" (variable capital)

        # Handle null values
        if gross_output_raw is None or intermediate_inputs_raw is None or compensation_raw is None:
            return None

        # Cast to float for calculation
        gross_output: float = float(gross_output_raw)
        intermediate_inputs: float = float(intermediate_inputs_raw)
        compensation: float = float(compensation_raw)

        if compensation <= 0:
            return None

        if ratio_type == "sv":
            # s/v = (gross_output - intermediate_inputs - compensation) / compensation
            # surplus = value_added - compensation = (gross_output - intermediate_inputs) - compensation
            surplus = gross_output - intermediate_inputs - compensation
            if surplus < 0:
                # Negative surplus can happen in loss-making industries
                # Return 0 to indicate no surplus extraction
                return 0.0
            return surplus / compensation

        elif ratio_type == "cv":
            # c/v = intermediate_inputs / compensation
            return intermediate_inputs / compensation

        return None


__all__ = [
    "BEADataSource",
    "InterpolatingBEASource",
    "QCEWDataSource",
    "SQLiteQCEWSource",
]
