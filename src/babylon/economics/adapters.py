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


__all__ = [
    "BEADataSource",
    "QCEWDataSource",
    "SQLiteQCEWSource",
]
