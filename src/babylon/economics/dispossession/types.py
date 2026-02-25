"""Dispossession Events domain types (Feature 021, FR-004/FR-005).

Frozen Pydantic models for dispossession event records and territory state.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.enums import DispossessionType, SocialRole


class DispossessionEvent(BaseModel):
    """Aggregate record of primitive accumulation activity per territory-tick.

    One record per dispossession type per territory per tick, containing
    event count and total value transferred.

    Args:
        fips_code: 5-digit county FIPS code.
        tick: Simulation tick.
        dispossession_type: One of 8 categories.
        event_count: Number of events this tick.
        total_value_transferred: Total value moved (Currency >= 0).
        affected_class: Class category losing wealth.
        receiving_category: Entity category gaining wealth.
    """

    model_config = ConfigDict(frozen=True)

    fips_code: str = Field(min_length=5, max_length=5)
    tick: int = Field(ge=0)
    dispossession_type: DispossessionType
    event_count: int = Field(ge=0)
    total_value_transferred: float = Field(ge=0.0)
    affected_class: SocialRole
    receiving_category: str = Field(max_length=50)


class TerritoryDispossessionState(BaseModel):
    """Aggregate dispossession metrics for a territory.

    Args:
        fips_code: 5-digit county FIPS code.
        year: Calendar year.
        foreclosure_rate: Foreclosures per mortgaged unit, in [0, 1].
        eviction_rate: Evictions per renter household, in [0, 1].
        displacement_rate: Net out-migration due to housing costs, in [0, 1].
        concentrated_ownership: Fraction owned by institutional investors, in [0, 1].
        absentee_landlord_share: Fraction of rentals owned by non-residents, in [0, 1].
    """

    model_config = ConfigDict(frozen=True)

    fips_code: str = Field(min_length=5, max_length=5)
    year: int = Field(ge=2005, le=2030)
    foreclosure_rate: float = Field(ge=0.0, le=1.0)
    eviction_rate: float = Field(ge=0.0, le=1.0)
    displacement_rate: float = Field(ge=0.0, le=1.0)
    concentrated_ownership: float = Field(ge=0.0, le=1.0)
    absentee_landlord_share: float = Field(ge=0.0, le=1.0)
