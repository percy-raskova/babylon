"""Ground rent extraction and housing decomposition computation.

Feature: 024-capital-volume-iii (US4, FR-007, FR-008, FR-009)

Computes ground rent extraction by category from BEA rental income data,
and decomposes housing market prices into construction value, capitalized
rent, and speculative premium using Census/ACS housing data.

See Also:
    :class:`RentExtraction`: Data model for rent by category.
    :class:`HousingValueDecomposition`: Data model for housing decomposition.
    :mod:`babylon.economics.rent.data_sources`: Data source protocols.
"""

from __future__ import annotations

from typing import Protocol

from babylon.economics.rent.data_sources import (
    CountyRentalIncomeSource,
    HousingDataSource,
)
from babylon.economics.rent.types import HousingValueDecomposition, RentExtraction
from babylon.economics.tensor import NoDataSentinel

_INTEREST_RATE_FLOOR: float = 0.01
"""Minimum interest rate for rent capitalization (prevents division by near-zero)."""


class RentCalculator(Protocol):
    """Protocol for ground rent extraction computation.

    Implementations assemble rental income data from BEA REIS by category.
    """

    def compute_rent_extraction(self, fips: str, year: int) -> RentExtraction | NoDataSentinel:
        """Compute rent extraction by category for a county-year.

        Args:
            fips: 5-digit county FIPS code.
            year: Calendar year.

        Returns:
            RentExtraction if all category data available,
            NoDataSentinel otherwise.
        """
        ...

    def compute_rent_share(self, rent: RentExtraction, total_surplus: float) -> float:
        """Compute rent as fraction of total surplus.

        Args:
            rent: Rent extraction snapshot.
            total_surplus: Total surplus value (dollars).

        Returns:
            Fraction of surplus captured as ground rent.
        """
        ...


class HousingDecompositionCalculator(Protocol):
    """Protocol for housing value decomposition.

    Implementations decompose housing market prices into construction
    value, capitalized ground rent, and speculative premium.
    """

    def decompose_housing_value(
        self, fips: str, year: int
    ) -> HousingValueDecomposition | NoDataSentinel:
        """Decompose housing value for a county-year.

        Args:
            fips: 5-digit county FIPS code.
            year: Calendar year.

        Returns:
            HousingValueDecomposition if all data available,
            NoDataSentinel otherwise.
        """
        ...


class DefaultRentCalculator:
    """Default implementation of ground rent extraction computation.

    Assembles rental income data from BEA REIS by three categories:
    agricultural, resource (mining/oil/gas), and urban (building site).

    Args:
        rental_source: BEA REIS county-level rental income data source.
    """

    def __init__(self, rental_source: CountyRentalIncomeSource) -> None:
        self._rental_source = rental_source

    def compute_rent_extraction(self, fips: str, year: int) -> RentExtraction | NoDataSentinel:
        """Compute rent extraction by category for a county-year.

        Args:
            fips: 5-digit county FIPS code.
            year: Calendar year.

        Returns:
            RentExtraction if all category data available,
            NoDataSentinel with reason otherwise.
        """
        agricultural = self._rental_source.get_agricultural_rent(fips, year)
        if agricultural is None:
            return NoDataSentinel(
                fips=fips,
                year=year,
                reason=f"Agricultural rent unavailable for {fips}/{year}",
            )

        resource = self._rental_source.get_resource_rent(fips, year)
        if resource is None:
            return NoDataSentinel(
                fips=fips,
                year=year,
                reason=f"Resource rent unavailable for {fips}/{year}",
            )

        urban = self._rental_source.get_urban_rent(fips, year)
        if urban is None:
            return NoDataSentinel(
                fips=fips,
                year=year,
                reason=f"Urban rent unavailable for {fips}/{year}",
            )

        return RentExtraction(
            fips_code=fips,
            year=year,
            agricultural_rent=agricultural,
            resource_rent=resource,
            urban_rent=urban,
        )

    def compute_rent_share(self, rent: RentExtraction, total_surplus: float) -> float:
        """Compute rent as fraction of total surplus.

        Delegates to RentExtraction.rent_share_of_surplus.

        Args:
            rent: Rent extraction snapshot.
            total_surplus: Total surplus value (dollars).

        Returns:
            Fraction of surplus captured as ground rent.
        """
        return rent.rent_share_of_surplus(total_surplus)


class DefaultHousingDecompositionCalculator:
    """Default implementation of housing value decomposition.

    Decomposes housing market prices using Census/ACS data:

    - Construction value = home_value * (construction_cost_index / 200)
    - Ground rent capitalized = (median_gross_rent * 12) / interest_rate
    - Speculative premium = max(0, home_value - construction - rent_cap)

    Args:
        housing_source: Census/ACS housing data source.
        national_interest_rate: National average interest rate for rent
            capitalization (floored at 0.01).
    """

    def __init__(
        self,
        housing_source: HousingDataSource,
        national_interest_rate: float,
    ) -> None:
        self._housing_source = housing_source
        self._interest_rate = max(national_interest_rate, _INTEREST_RATE_FLOOR)

    def decompose_housing_value(
        self, fips: str, year: int
    ) -> HousingValueDecomposition | NoDataSentinel:
        """Decompose housing value for a county-year.

        Args:
            fips: 5-digit county FIPS code.
            year: Calendar year.

        Returns:
            HousingValueDecomposition if all data available,
            NoDataSentinel with reason otherwise.
        """
        home_value = self._housing_source.get_median_home_value(fips, year)
        if home_value is None:
            return NoDataSentinel(
                fips=fips,
                year=year,
                reason=f"Median home value unavailable for {fips}/{year}",
            )

        gross_rent = self._housing_source.get_median_gross_rent(fips, year)
        if gross_rent is None:
            return NoDataSentinel(
                fips=fips,
                year=year,
                reason=f"Median gross rent unavailable for {fips}/{year}",
            )

        cost_index = self._housing_source.get_construction_cost_index(year)
        if cost_index is None:
            return NoDataSentinel(
                fips=fips,
                year=year,
                reason=f"Construction cost index unavailable for {year}",
            )

        construction_value = home_value * (cost_index / 200.0)
        ground_rent_capitalized = (gross_rent * 12.0) / self._interest_rate
        speculative_premium = max(0.0, home_value - construction_value - ground_rent_capitalized)

        return HousingValueDecomposition(
            fips_code=fips,
            year=year,
            construction_value=construction_value,
            ground_rent_capitalized=ground_rent_capitalized,
            speculative_premium=speculative_premium,
        )
