"""Data source protocols and implementations for the MarxianHydrator.

This module defines the protocols that abstract data access for QCEW wage data
and BEA industry ratios, enabling dependency injection and testability.

Protocols:
    QCEWDataSource: Fetches county-level wage data by NAICS code.
    BEADataSource: Provides industry-level c/v and s/v ratios.

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


__all__ = [
    "BEADataSource",
    "QCEWDataSource",
]
