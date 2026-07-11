"""Value basis conversion between nominal, real, and labor-time.

Feature: 024-capital-volume-iii (US7, FR-013)
"""

from __future__ import annotations

from typing import Protocol

from babylon.domain.economics.monetary.data_sources import PriceIndexSource
from babylon.domain.economics.monetary.types import MonetaryAdjustment
from babylon.domain.economics.tensor import NoDataSentinel


class ValueBasisConverter(Protocol):
    """Protocol for value basis conversion.

    Converts between nominal dollars, real (inflation-adjusted) dollars,
    and labor-time (SNLT hours) representations.
    """

    def compute_monetary_adjustment(
        self,
        year: int,
        base_year: int,
    ) -> MonetaryAdjustment | NoDataSentinel:
        """Compute conversion factors for a given year.

        Args:
            year: Target year for conversion factors.
            base_year: Reference year for real-dollar conversion.

        Returns:
            MonetaryAdjustment with conversion factors, or NoDataSentinel if data unavailable.
        """
        ...

    def nominal_to_real(self, nominal: float, current_cpi: float, base_cpi: float) -> float:
        """Convert nominal dollars to real (constant) dollars.

        Args:
            nominal: Amount in current dollars.
            current_cpi: CPI index for the current year.
            base_cpi: CPI index for the base year.

        Returns:
            Amount in base-year constant dollars.
        """
        ...

    def nominal_to_labor_time(self, nominal: float, snlt_per_dollar: float) -> float:
        """Convert nominal dollars to labor-time (SNLT hours).

        Args:
            nominal: Amount in current dollars.
            snlt_per_dollar: Labor-hours per dollar of GDP.

        Returns:
            Amount in hours of socially necessary labor time.
        """
        ...

    def real_to_nominal(self, real: float, current_cpi: float, base_cpi: float) -> float:
        """Convert real (constant) dollars to nominal dollars.

        Args:
            real: Amount in base-year constant dollars.
            current_cpi: CPI index for the current year.
            base_cpi: CPI index for the base year.

        Returns:
            Amount in current dollars.
        """
        ...


class DefaultValueBasisConverter:
    """Default implementation using PriceIndexSource for data.

    SNLT computation: snlt_per_dollar = total_labor_hours / nominal_gdp.
    """

    def __init__(self, price_source: PriceIndexSource) -> None:
        self._price_source = price_source

    def compute_monetary_adjustment(
        self,
        year: int,
        base_year: int,
    ) -> MonetaryAdjustment | NoDataSentinel:
        """Compute conversion factors for a given year.

        Args:
            year: Target year for conversion factors.
            base_year: Reference year for real-dollar conversion.

        Returns:
            MonetaryAdjustment with conversion factors, or NoDataSentinel if data unavailable.
        """
        cpi = self._price_source.get_cpi(year)
        if cpi is None:
            return NoDataSentinel(fips="USA", year=year, reason=f"CPI data unavailable for {year}")

        deflator = self._price_source.get_gdp_deflator(year)
        if deflator is None:
            return NoDataSentinel(
                fips="USA",
                year=year,
                reason=f"GDP deflator unavailable for {year}",
            )

        labor_hours = self._price_source.get_total_labor_hours(year)
        if labor_hours is None:
            return NoDataSentinel(
                fips="USA",
                year=year,
                reason=f"Total labor hours unavailable for {year}",
            )

        gdp = self._price_source.get_nominal_gdp(year)
        if gdp is None:
            return NoDataSentinel(
                fips="USA",
                year=year,
                reason=f"Nominal GDP unavailable for {year}",
            )

        snlt = labor_hours / gdp if gdp > 0 else 0.0

        return MonetaryAdjustment(
            year=year,
            cpi_index=cpi,
            gdp_deflator=deflator,
            snlt_per_dollar=snlt,
            base_year=base_year,
        )

    def nominal_to_real(self, nominal: float, current_cpi: float, base_cpi: float) -> float:
        """Convert nominal dollars to real (constant) dollars.

        Args:
            nominal: Amount in current dollars.
            current_cpi: CPI index for the current year.
            base_cpi: CPI index for the base year.

        Returns:
            Amount in base-year constant dollars.
        """
        return nominal * (base_cpi / current_cpi)

    def nominal_to_labor_time(self, nominal: float, snlt_per_dollar: float) -> float:
        """Convert nominal dollars to labor-time (SNLT hours).

        Args:
            nominal: Amount in current dollars.
            snlt_per_dollar: Labor-hours per dollar of GDP.

        Returns:
            Amount in hours of socially necessary labor time.
        """
        return nominal * snlt_per_dollar

    def real_to_nominal(self, real: float, current_cpi: float, base_cpi: float) -> float:
        """Convert real (constant) dollars to nominal dollars.

        Args:
            real: Amount in base-year constant dollars.
            current_cpi: CPI index for the current year.
            base_cpi: CPI index for the base year.

        Returns:
            Amount in current dollars.
        """
        return real * (current_cpi / base_cpi)
