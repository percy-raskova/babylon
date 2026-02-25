"""Data source protocols for surplus value distribution.

Feature: 024-capital-volume-iii (US1, FR-001, FR-017)
"""

from __future__ import annotations

from typing import Protocol


class RentalIncomeSource(Protocol):
    """Protocol for BEA rental income data (county-level).

    Provides ground rent component of surplus distribution.
    Data source: BEA NIPA Table (B230RC0Q173SBEA).
    """

    def get_rental_income(self, fips: str, year: int) -> float | None:
        """Get total rental income of persons for a county-year.

        Args:
            fips: 5-digit county FIPS code.
            year: Calendar year.

        Returns:
            Rental income in current dollars, or None if unavailable.
        """
        ...


class TaxOnSurplusSource(Protocol):
    """Protocol for IRS/BEA corporate income tax data (county-level).

    Provides tax component of surplus distribution.
    Data source: BEA NIPA Table (A054RC1Q027SBEA).
    """

    def get_corporate_tax(self, fips: str, year: int) -> float | None:
        """Get corporate income tax for a county-year.

        Args:
            fips: 5-digit county FIPS code.
            year: Calendar year.

        Returns:
            Tax amount in current dollars, or None if unavailable.
        """
        ...


class InterestIncomeSource(Protocol):
    """Protocol for FRED/BEA net interest data (national-level).

    Provides interest component of surplus distribution.
    National-level data allocated to counties by capital stock share.
    Data source: FRED net interest income series.
    """

    def get_national_net_interest(self, year: int) -> float | None:
        """Get national net interest income for a year.

        Args:
            year: Calendar year.

        Returns:
            Net interest in current dollars, or None if unavailable.
        """
        ...
