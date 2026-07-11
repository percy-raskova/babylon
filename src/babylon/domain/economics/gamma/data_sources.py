"""Data source protocols for Gamma Visibility Tensor module.

Feature: 015-gamma-visibility-tensor
Date: 2026-02-05

This module defines data source protocols for:
- Unpaid care hours (ATUS data)
- Paid care hours (QCEW employment data)
- ERDI values (Penn World Tables)

See Also:
    :mod:`babylon.domain.economics.melt.data_sources`: BEA/QCEW protocols (Feature 013)
"""

from __future__ import annotations

from typing import Protocol


class UnpaidCareHoursSource(Protocol):
    """Protocol for unpaid care hours data from ATUS.

    Data Source:
        American Time Use Survey (ATUS), BLS
        https://www.bls.gov/tus/

    Units:
        Billions of hours per year (national aggregate).

    Example:
        >>> source = ATUSUnpaidCareSource()
        >>> hours = source.get_unpaid_care_hours(2022)
        >>> print(f"Unpaid care: {hours:.1f}B hours")
        Unpaid care: 33.0B hours
    """

    def get_unpaid_care_hours(self, year: int) -> float | None:
        """Get annual unpaid care hours for a given year.

        Args:
            year: Calendar year (2003+ for ATUS availability).

        Returns:
            Unpaid care hours in billions, or None if data unavailable.
        """
        ...


class PaidCareHoursSource(Protocol):
    """Protocol for paid care hours data from QCEW.

    Data Source:
        QCEW employment in care NAICS sectors * 2080 hours/year * care fraction.
        https://www.bls.gov/cew/

    Units:
        Billions of hours per year (national aggregate).

    Example:
        >>> source = QCEWCareAdapter()
        >>> hours = source.get_paid_care_hours(2022)
        >>> print(f"Paid care: {hours:.1f}B hours")
        Paid care: 16.5B hours
    """

    def get_paid_care_hours(self, year: int) -> float | None:
        """Get annual paid care hours for a given year.

        Args:
            year: Calendar year.

        Returns:
            Paid care hours in billions, or None if data unavailable.
        """
        ...


class ERDISource(Protocol):
    """Protocol for ERDI (Exchange Rate Deviation Index) data.

    Data Source:
        Penn World Tables 10.01
        https://www.rug.nl/ggdc/productivity/pwt/

    Example:
        >>> source = PennWorldTablesERDISource()
        >>> erdi = source.get_erdi("CHN")
        >>> print(f"China ERDI: {erdi:.2f}")
        China ERDI: 1.80
    """

    def get_erdi(self, country_code: str) -> float | None:
        """Get ERDI value for a country.

        Args:
            country_code: ISO 3-letter country code (e.g., "CHN", "MEX").

        Returns:
            ERDI value (>= 1.0 for periphery), or None if unavailable.
        """
        ...

    def get_import_shares(self, year: int) -> dict[str, float] | None:
        """Get US import shares by country of origin.

        Args:
            year: Calendar year for trade data.

        Returns:
            Dict of country_code -> import share [0, 1] summing to ~1.0,
            or None if data unavailable.
        """
        ...


__all__ = [
    "ERDISource",
    "PaidCareHoursSource",
    "UnpaidCareHoursSource",
]
