"""Data source protocols for value basis conversion.

Feature: 024-capital-volume-iii (US7, FR-013)
"""

from __future__ import annotations

from typing import Protocol


class PriceIndexSource(Protocol):
    """Protocol for CPI and GDP deflator data.

    Data sources: BLS CPI (CPIAUCSL), BEA GDP deflator (GDPDEF).
    """

    def get_cpi(self, year: int) -> float | None:
        """Get Consumer Price Index for year (base year = 100).

        Args:
            year: Calendar year.

        Returns:
            CPI index value, or None if unavailable.
        """
        ...

    def get_gdp_deflator(self, year: int) -> float | None:
        """Get GDP deflator for year (base year = 100).

        Args:
            year: Calendar year.

        Returns:
            GDP deflator value, or None if unavailable.
        """
        ...

    def get_total_labor_hours(self, year: int) -> float | None:
        """Get total annual labor hours (employment * avg weekly hours * 52).

        Args:
            year: Calendar year.

        Returns:
            Total labor hours, or None if unavailable.
        """
        ...

    def get_nominal_gdp(self, year: int) -> float | None:
        """Get nominal GDP for year.

        Args:
            year: Calendar year.

        Returns:
            Nominal GDP in current dollars, or None if unavailable.
        """
        ...
