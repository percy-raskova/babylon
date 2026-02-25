"""Data source protocols for ground rent and housing.

Feature: 024-capital-volume-iii (US4, FR-007, FR-008, FR-017)
"""

from __future__ import annotations

from typing import Protocol


class HousingDataSource(Protocol):
    """Protocol for Census/ACS housing data (county-level).

    Data sources: ACS B25077 (home values), B25064 (gross rent).
    """

    def get_median_home_value(self, fips: str, year: int) -> float | None:
        """Get median value of owner-occupied housing (ACS B25077).

        Args:
            fips: 5-digit county FIPS code.
            year: Calendar year.

        Returns:
            Median home value in current dollars, or None if unavailable.
        """
        ...

    def get_median_gross_rent(self, fips: str, year: int) -> float | None:
        """Get median gross rent (ACS B25064).

        Args:
            fips: 5-digit county FIPS code.
            year: Calendar year.

        Returns:
            Monthly gross rent in current dollars, or None if unavailable.
        """
        ...

    def get_construction_cost_index(self, year: int) -> float | None:
        """Get construction cost index (national, RSMeans or Census).

        Args:
            year: Calendar year.

        Returns:
            Index value (base year = 100), or None if unavailable.
        """
        ...


class CountyRentalIncomeSource(Protocol):
    """Protocol for BEA rental income at county level by category.

    Data source: BEA REIS (Regional Economic Information System).
    """

    def get_agricultural_rent(self, fips: str, year: int) -> float | None:
        """Get farmland rental income.

        Args:
            fips: 5-digit county FIPS code.
            year: Calendar year.

        Returns:
            Agricultural rent in current dollars, or None if unavailable.
        """
        ...

    def get_resource_rent(self, fips: str, year: int) -> float | None:
        """Get mining/oil/gas rental income.

        Args:
            fips: 5-digit county FIPS code.
            year: Calendar year.

        Returns:
            Resource rent in current dollars, or None if unavailable.
        """
        ...

    def get_urban_rent(self, fips: str, year: int) -> float | None:
        """Get building site / commercial real estate rent.

        Args:
            fips: 5-digit county FIPS code.
            year: Calendar year.

        Returns:
            Urban rent in current dollars, or None if unavailable.
        """
        ...
