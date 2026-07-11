"""Type definitions for the ground rent extraction module.

Feature: 024-capital-volume-iii (US4)
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, computed_field


class RentCategory(StrEnum):
    """Category of ground rent extraction.

    Feature: 024-capital-volume-iii (FR-007)

    Marx distinguished differential rent (surplus profit from better
    land/location) and absolute rent (monopoly payment for any land
    access). Both operate across three economic sectors.

    Values:
        AGRICULTURAL: Farmland rent (differential by soil fertility/location).
        RESOURCE: Mining, oil/gas rent (differential by deposit quality).
        URBAN: Building site rent, commercial real estate (differential by location).
    """

    AGRICULTURAL = "agricultural"
    RESOURCE = "resource"
    URBAN = "urban"


class RentExtraction(BaseModel):
    """Ground rent decomposition by category.

    Feature: 024-capital-volume-iii (FR-007)

    Decomposes total ground rent into agricultural, resource, and urban
    components. Provides computed total and surplus share.

    Args:
        fips_code: 5-digit county FIPS code.
        year: Calendar year.
        agricultural_rent: Farmland rental income (dollars, >= 0).
        resource_rent: Mining/oil/gas rental income (dollars, >= 0).
        urban_rent: Building site / commercial rent (dollars, >= 0).
    """

    model_config = ConfigDict(frozen=True)

    fips_code: str = Field(..., min_length=5, max_length=5)
    year: int = Field(..., ge=2007, le=2040)
    agricultural_rent: float = Field(..., ge=0.0)
    resource_rent: float = Field(..., ge=0.0)
    urban_rent: float = Field(..., ge=0.0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_rent(self) -> float:
        """Sum of all three rent categories."""
        return self.agricultural_rent + self.resource_rent + self.urban_rent

    def rent_share_of_surplus(self, total_surplus: float) -> float:
        """Compute rent as a fraction of total surplus value.

        Args:
            total_surplus: Total surplus value in the county (dollars).

        Returns:
            Fraction of surplus captured as ground rent. Returns 0.0
            when total_surplus is zero or negative.
        """
        if total_surplus <= 0.0:
            return 0.0
        return self.total_rent / total_surplus


class HousingValueDecomposition(BaseModel):
    """Housing price decomposition into value components.

    Feature: 024-capital-volume-iii (FR-008, FR-009)

    Decomposes housing market price into three components following
    Marx's theory of ground rent: real construction value (concrete
    labor), capitalized ground rent, and speculative premium (fictitious
    capital in housing form).

    Args:
        fips_code: 5-digit county FIPS code.
        year: Calendar year.
        construction_value: Replacement cost of the structure (dollars, >= 0).
        ground_rent_capitalized: Capitalized annual rent (dollars, >= 0).
        speculative_premium: Excess above fundamentals (dollars, >= 0).
    """

    model_config = ConfigDict(frozen=True)

    fips_code: str = Field(..., min_length=5, max_length=5)
    year: int = Field(..., ge=2007, le=2040)
    construction_value: float = Field(..., ge=0.0)
    ground_rent_capitalized: float = Field(..., ge=0.0)
    speculative_premium: float = Field(..., ge=0.0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def market_price(self) -> float:
        """Total market price = construction + rent_cap + speculation."""
        return self.construction_value + self.ground_rent_capitalized + self.speculative_premium

    @computed_field  # type: ignore[prop-decorator]
    @property
    def fictitious_fraction(self) -> float:
        """Fraction of market price that is fictitious capital.

        Fictitious fraction = (rent_capitalized + speculation) / market_price.
        Returns 0.0 when market_price is zero.
        """
        mp = self.construction_value + self.ground_rent_capitalized + self.speculative_premium
        if mp == 0.0:
            return 0.0
        return (self.ground_rent_capitalized + self.speculative_premium) / mp
