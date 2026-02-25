"""Contract: Ground Rent and Housing Decomposition (US4, FR-007..FR-009).

These are function signatures defining the public API contract.
Implementations go in src/babylon/economics/rent/.
"""

from __future__ import annotations

from typing import Protocol

from babylon.economics.tensor import NoDataSentinel

# Placeholder type aliases
Currency = float


# ---------------------------------------------------------------------------
# Data Source Protocols
# ---------------------------------------------------------------------------


class HousingDataSource(Protocol):
    """Protocol for Census/ACS housing data (county-level)."""

    def get_median_home_value(self, fips: str, year: int) -> Currency | None:
        """Get median value of owner-occupied housing (ACS B25077)."""
        ...

    def get_median_gross_rent(self, fips: str, year: int) -> Currency | None:
        """Get median gross rent (ACS B25064)."""
        ...

    def get_construction_cost_index(self, year: int) -> float | None:
        """Get construction cost index (national, RSMeans or Census)."""
        ...


class CountyRentalIncomeSource(Protocol):
    """Protocol for BEA rental income at county level."""

    def get_agricultural_rent(self, fips: str, year: int) -> Currency | None:
        """Get farmland rental income."""
        ...

    def get_resource_rent(self, fips: str, year: int) -> Currency | None:
        """Get mining/oil/gas rental income."""
        ...

    def get_urban_rent(self, fips: str, year: int) -> Currency | None:
        """Get building site / commercial real estate rent."""
        ...


# ---------------------------------------------------------------------------
# Calculator Protocols
# ---------------------------------------------------------------------------


class RentCalculator(Protocol):
    """Protocol for ground rent computation (FR-007)."""

    def compute_rent_extraction(
        self,
        fips: str,
        year: int,
    ) -> "RentExtraction | NoDataSentinel":
        """Compute ground rent decomposition for a county-year.

        Returns:
            RentExtraction with agricultural, resource, and urban components.
        """
        ...

    def compute_rent_share(
        self,
        rent_extraction: "RentExtraction",
        total_surplus: Currency,
    ) -> float:
        """Compute rentier share of surplus (FR-007).

        Returns:
            total_rent / total_surplus, in [0, 1] for positive surplus.
            Returns 0.0 if total_surplus <= 0.
        """
        ...


class HousingDecompositionCalculator(Protocol):
    """Protocol for housing value decomposition (FR-008, FR-009)."""

    def decompose_housing_value(
        self,
        fips: str,
        year: int,
        national_interest_rate: float,
    ) -> "HousingValueDecomposition | NoDataSentinel":
        """Decompose housing price into construction + rent + speculation.

        Args:
            fips: County FIPS code.
            year: Assessment year.
            national_interest_rate: Used to capitalize ground rent.

        Returns:
            HousingValueDecomposition or NoDataSentinel if data unavailable.

        Post-conditions:
            - market_price = construction + rent_capitalized + speculation
            - fictitious_fraction in [0, 1]
        """
        ...
