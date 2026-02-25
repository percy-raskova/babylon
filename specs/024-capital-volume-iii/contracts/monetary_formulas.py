"""Contract: Monetary Adjustment and Value Basis Conversion (US7, FR-013).

These are function signatures defining the public API contract.
Implementations go in src/babylon/economics/monetary/.
"""

from __future__ import annotations

from typing import Protocol

from babylon.economics.tensor import NoDataSentinel

# Placeholder type aliases
Currency = float


# ---------------------------------------------------------------------------
# Data Source Protocol
# ---------------------------------------------------------------------------


class PriceIndexSource(Protocol):
    """Protocol for CPI and GDP deflator data."""

    def get_cpi(self, year: int) -> float | None:
        """Get Consumer Price Index for year (base year = 100)."""
        ...

    def get_gdp_deflator(self, year: int) -> float | None:
        """Get GDP deflator for year (base year = 100)."""
        ...

    def get_total_labor_hours(self, year: int) -> float | None:
        """Get total annual labor hours (employment * avg hours)."""
        ...

    def get_nominal_gdp(self, year: int) -> Currency | None:
        """Get nominal GDP for year."""
        ...


# ---------------------------------------------------------------------------
# Calculator Protocol
# ---------------------------------------------------------------------------


class ValueBasisConverter(Protocol):
    """Protocol for value basis conversion (FR-013)."""

    def compute_monetary_adjustment(
        self,
        year: int,
        base_year: int,
    ) -> "MonetaryAdjustment | NoDataSentinel":
        """Compute conversion factors for a given year relative to base.

        Args:
            year: Target year for conversion factors.
            base_year: Reference year for real dollar conversion.

        Returns:
            MonetaryAdjustment with CPI, deflator, SNLT/dollar.
        """
        ...

    def nominal_to_real(
        self,
        nominal: Currency,
        adjustment: "MonetaryAdjustment",
        target_year_cpi: float,
    ) -> Currency:
        """Convert nominal to real (inflation-adjusted) dollars.

        Formula: nominal * (base_cpi / current_cpi)

        Post-conditions:
            - Round-trip: real_to_nominal(nominal_to_real(x)) == x (within EPSILON)
        """
        ...

    def nominal_to_labor_time(
        self,
        nominal: Currency,
        adjustment: "MonetaryAdjustment",
    ) -> float:
        """Convert nominal dollars to labor-time (SNLT hours).

        Formula: nominal * snlt_per_dollar

        Returns:
            Labor hours equivalent.
        """
        ...

    def real_to_nominal(
        self,
        real: Currency,
        adjustment: "MonetaryAdjustment",
        target_year_cpi: float,
    ) -> Currency:
        """Convert real (inflation-adjusted) to nominal dollars.

        Formula: real * (current_cpi / base_cpi)
        """
        ...
