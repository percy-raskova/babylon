"""National rent differential calculator (Feature 038, US4).

Computes nation-specific imperial rent differentials from ACS earnings
data by race x NAICS at county level (FR-007). Measures wage gaps between
settler workers and internal colony workers within the same occupation at
the same location, operationalizing the theoretical claim that imperial rent
is withheld from internally colonized populations.

Positive differentials indicate settler advantage (standard case).
Suppressed ACS data (small sample sizes) propagates NoDataSentinel rather
than imputing, following the NoDataSentinel pattern from tensor.py.

Feature: 038-unified-class-system
Date: 2026-03-01
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from babylon.domain.economics.protocol_kit import CachedSource
from babylon.domain.economics.tensor import NoDataSentinel
from babylon.models.enums import CommunityType


class RentDifferentialResult(BaseModel):
    """Result of rent differential computation for a county x nation pair.

    Args:
        fips: 5-digit FIPS code for county.
        nation: Target nation (CommunityType).
        year: Calendar year.
        differential: Employment-weighted average differential ($/year).
        naics_count: Number of NAICS codes with valid data.
        suppressed_count: Number of NAICS codes with suppressed data.
    """

    model_config = ConfigDict(frozen=True)

    fips: str = Field(min_length=5, max_length=5)
    nation: CommunityType
    year: int = Field(ge=2000, le=2100)
    differential: float
    naics_count: int = Field(ge=0)
    suppressed_count: int = Field(ge=0)

    @model_validator(mode="after")
    def _validate_has_data(self) -> RentDifferentialResult:
        """Ensure at least one NAICS code was evaluated."""
        if self.naics_count + self.suppressed_count == 0:
            msg = "naics_count + suppressed_count must be > 0"
            raise ValueError(msg)
        return self


class RentDifferentialCalculator(Protocol):
    """Protocol for computing nation-specific imperial rent differentials."""

    def compute_differential(
        self,
        fips: str,
        nation: CommunityType,
        naics: str,
        year: int,
    ) -> float | NoDataSentinel:
        """Compute Phi_differential for a specific county x nation x NAICS.

        Args:
            fips: 5-digit FIPS code.
            nation: Target nation.
            naics: NAICS sector code.
            year: Calendar year.

        Returns:
            Differential in $/year, or NoDataSentinel if data suppressed.
        """
        ...

    def compute_county_aggregate(
        self,
        fips: str,
        nation: CommunityType,
        year: int,
    ) -> float | NoDataSentinel:
        """Compute employment-weighted county-level aggregate differential.

        Args:
            fips: 5-digit FIPS code.
            nation: Target nation.
            year: Calendar year.

        Returns:
            Employment-weighted average differential, or NoDataSentinel.
        """
        ...


# Mock ACS earnings data: {fips: {naics: {nation_value: median_earnings}}}
# In production, this comes from ACS data loader
_MOCK_EARNINGS: dict[str, dict[str, dict[str, float]]] = {
    # Wayne County (Detroit proper) — larger wage gaps
    "26163": {
        "31-33": {  # Manufacturing
            CommunityType.SETTLER.value: 55000.0,
            CommunityType.NEW_AFRIKAN.value: 38000.0,
            CommunityType.CHICANO.value: 40000.0,
        },
        "44-45": {  # Retail Trade
            CommunityType.SETTLER.value: 32000.0,
            CommunityType.NEW_AFRIKAN.value: 25000.0,
            CommunityType.CHICANO.value: 26000.0,
        },
        "62": {  # Health Care
            CommunityType.SETTLER.value: 65000.0,
            CommunityType.NEW_AFRIKAN.value: 48000.0,
            CommunityType.CHICANO.value: 50000.0,
        },
    },
    # Oakland County (suburbs) — smaller wage gaps
    "26125": {
        "31-33": {  # Manufacturing
            CommunityType.SETTLER.value: 62000.0,
            CommunityType.NEW_AFRIKAN.value: 50000.0,
            CommunityType.CHICANO.value: 52000.0,
        },
        "44-45": {  # Retail Trade
            CommunityType.SETTLER.value: 35000.0,
            CommunityType.NEW_AFRIKAN.value: 30000.0,
            CommunityType.CHICANO.value: 31000.0,
        },
        "62": {  # Health Care
            CommunityType.SETTLER.value: 72000.0,
            CommunityType.NEW_AFRIKAN.value: 62000.0,
            CommunityType.CHICANO.value: 63000.0,
        },
    },
}

# Mock QCEW employment counts: {fips: {naics: employment}}
_MOCK_EMPLOYMENT: dict[str, dict[str, int]] = {
    "26163": {
        "31-33": 45000,
        "44-45": 38000,
        "62": 52000,
    },
    "26125": {
        "31-33": 32000,
        "44-45": 28000,
        "62": 41000,
    },
}


class DefaultRentDifferentialCalculator(CachedSource[float]):
    """Default implementation with mock ACS earnings data.

    Uses mock data following the same pattern as DefaultWealthProxyCalculator.
    In production, this would be backed by ACS data loaders.
    """

    def __init__(
        self,
        earnings_data: dict[str, dict[str, dict[str, float]]] | None = None,
        employment_data: dict[str, dict[str, int]] | None = None,
    ) -> None:
        """Initialize with optional data overrides.

        Args:
            earnings_data: Optional ACS earnings data.
            employment_data: Optional QCEW employment data.
        """
        super().__init__()
        self._earnings = earnings_data if earnings_data is not None else _MOCK_EARNINGS
        self._employment = employment_data if employment_data is not None else _MOCK_EMPLOYMENT

    def compute_differential(
        self,
        fips: str,
        nation: CommunityType,
        naics: str,
        year: int,
    ) -> float | NoDataSentinel:
        """Compute Phi_differential for a specific county x nation x NAICS.

        Args:
            fips: 5-digit FIPS code.
            nation: Target nation.
            naics: NAICS sector code.
            year: Calendar year.

        Returns:
            Differential in $/year, or NoDataSentinel if data suppressed.
        """
        # SETTLER vs SETTLER = 0 (no differential)
        if nation == CommunityType.SETTLER:
            return 0.0

        county_data = self._earnings.get(fips)
        if county_data is None:
            return NoDataSentinel(fips, year, f"ACS suppressed: no data for FIPS {fips}")

        naics_data = county_data.get(naics)
        if naics_data is None:
            return NoDataSentinel(
                fips, year, f"ACS suppressed: no NAICS {naics} data for FIPS {fips}"
            )

        settler_earnings = naics_data.get(CommunityType.SETTLER.value)
        nation_earnings = naics_data.get(nation.value)

        if settler_earnings is None or nation_earnings is None:
            return NoDataSentinel(
                fips,
                year,
                f"ACS suppressed: missing earnings for {nation.value} in NAICS {naics}",
            )

        return settler_earnings - nation_earnings

    def compute_county_aggregate(
        self,
        fips: str,
        nation: CommunityType,
        year: int,
    ) -> float | NoDataSentinel:
        """Compute employment-weighted county-level aggregate differential.

        Args:
            fips: 5-digit FIPS code.
            nation: Target nation.
            year: Calendar year.

        Returns:
            Employment-weighted average differential, or NoDataSentinel.
        """
        # SETTLER vs SETTLER = 0 (no differential)
        if nation == CommunityType.SETTLER:
            return 0.0

        county_earnings = self._earnings.get(fips)
        county_employment = self._employment.get(fips)

        if county_earnings is None or county_employment is None:
            return NoDataSentinel(fips, year, f"No valid NAICS data: FIPS {fips} not in dataset")

        weighted_sum = 0.0
        total_employment = 0
        valid_count = 0
        suppressed_count = 0

        for naics in county_earnings:
            diff = self.compute_differential(fips, nation, naics, year)
            if isinstance(diff, NoDataSentinel):
                suppressed_count += 1
                continue

            employment = county_employment.get(naics, 0)
            if employment > 0:
                weighted_sum += diff * employment
                total_employment += employment
                valid_count += 1
            else:
                suppressed_count += 1

        if total_employment == 0:
            return NoDataSentinel(
                fips, year, f"No valid NAICS data: all suppressed for {nation.value}"
            )

        return weighted_sum / total_employment


__all__ = [
    "DefaultRentDifferentialCalculator",
    "RentDifferentialCalculator",
    "RentDifferentialResult",
]
