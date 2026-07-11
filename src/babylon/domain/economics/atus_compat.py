"""ATUS compatibility types for shadow labor calculations.

Contains the essential Pydantic models and mock implementations originally
from babylon-data's ATUS module. These are needed by the shadow labor
service and its tests until babylon-data is available as a package.

See Also:
    :mod:`babylon.domain.economics.shadow_labor`: Shadow labor service.
"""

from __future__ import annotations

import logging
from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from babylon.domain.economics.shadow_labor import ReproductionLoaderProtocol

logger = logging.getLogger(__name__)


class ATUSActivityRecord(BaseModel):
    """Single ATUS activity record (time diary entry).

    Args:
        respondent_id: Unique identifier for ATUS respondent.
        activity_code: ATUS 6-digit activity code.
        duration_minutes: Duration of activity (0-1440 minutes).
        is_reproductive: Whether this activity is reproductive labor.
        is_paid: Whether this activity is compensated work.
    """

    model_config = ConfigDict(frozen=True)

    respondent_id: str = Field(description="Unique identifier for ATUS respondent")
    activity_code: str = Field(description="ATUS 6-digit activity code")
    duration_minutes: int = Field(
        ge=0,
        le=1440,
        description="Duration in minutes (0 = 24 hours)",
    )
    is_reproductive: bool = Field(
        default=False,
        description="Whether this is reproductive labor",
    )
    is_paid: bool = Field(
        default=False,
        description="Whether this activity is compensated",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def duration_hours(self) -> float:
        """Duration in hours (computed from minutes)."""
        return self.duration_minutes / 60.0


class ATUSHouseholdSummary(BaseModel):
    """Aggregated reproductive labor hours for a household.

    Args:
        fips_code: 5-digit FIPS county code.
        year: Data year (>= 2003 for ATUS availability).
        total_reproductive_hours_weekly: Total reproductive labor hours per week.
        unpaid_care_hours_weekly: Unpaid (shadow) care hours per week.
        paid_care_hours_weekly: Paid (monetized) care hours per week.
        household_weight: Survey weight for aggregation (default 1.0).
    """

    model_config = ConfigDict(frozen=True)

    fips_code: str = Field(
        pattern=r"^\d{5}$",
        description="5-digit FIPS county code",
    )
    year: int = Field(
        ge=2003,
        description="Data year (ATUS began in 2003)",
    )
    total_reproductive_hours_weekly: float = Field(
        ge=0.0,
        description="Total reproductive labor hours per week",
    )
    unpaid_care_hours_weekly: float = Field(
        ge=0.0,
        description="Unpaid (shadow) care hours per week",
    )
    paid_care_hours_weekly: float = Field(
        ge=0.0,
        description="Paid (monetized) care hours per week",
    )
    household_weight: float = Field(
        default=1.0,
        ge=0.0,
        description="Survey weight for aggregation",
    )


class VisibilityDecomposition(BaseModel):
    """Four-category decomposition of Department III visibility.

    Args:
        domestic_unpaid: Fraction of reproductive labor done unpaid at home.
        migrant_care: Fraction done by migrant/noncitizen care workers.
        peripheral_subsistence: Fraction externalized via remittances.
        state_socialized: Fraction provided by public sector.
    """

    model_config = ConfigDict(frozen=True)

    domestic_unpaid: float = Field(ge=0.0, le=1.0)
    migrant_care: float = Field(ge=0.0, le=1.0)
    peripheral_subsistence: float = Field(ge=0.0, le=1.0)
    state_socialized: float = Field(ge=0.0, le=1.0)

    VISIBILITY_COEFFICIENTS: ClassVar[dict[str, float]] = {
        "domestic_unpaid": 0.0,
        "migrant_care": 0.3,
        "peripheral_subsistence": 0.0,
        "state_socialized": 1.0,
    }

    @model_validator(mode="after")
    def fractions_sum_to_one(self) -> Self:
        """Validate that fractions sum to 1.0 within tolerance."""
        total = (
            self.domestic_unpaid
            + self.migrant_care
            + self.peripheral_subsistence
            + self.state_socialized
        )
        if abs(total - 1.0) > 0.001:
            msg = f"Fractions must sum to 1.0 (got {total:.6f})"
            raise ValueError(msg)
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_g33(self) -> float:
        """Computed national visibility coefficient g_33."""
        coeffs = self.VISIBILITY_COEFFICIENTS
        raw = (
            self.domestic_unpaid * coeffs["domestic_unpaid"]
            + self.migrant_care * coeffs["migrant_care"]
            + self.peripheral_subsistence * coeffs["peripheral_subsistence"]
            + self.state_socialized * coeffs["state_socialized"]
        )
        return max(0.0, min(1.0, raw))


# =============================================================================
# Mock loader
# =============================================================================

NATIONAL_AVG_UNPAID_CARE_WEEKLY: float = 21.0
REPLACEMENT_COST_HOURLY: float = 15.43


class MockReproductionLoader(ReproductionLoaderProtocol):
    """Mock ATUS data loader returning configurable national averages.

    Args:
        default_weekly_hours: Unpaid care hours per week (default 21.0).
        shadow_wage_hourly: Replacement cost wage (default $15.43/hour).
    """

    def __init__(
        self,
        default_weekly_hours: float = NATIONAL_AVG_UNPAID_CARE_WEEKLY,
        shadow_wage_hourly: float = REPLACEMENT_COST_HOURLY,
    ) -> None:
        self._default_weekly_hours = default_weekly_hours
        self._shadow_wage_hourly = shadow_wage_hourly

    def load_county_summary(
        self,
        fips_code: str,
        year: int,
    ) -> ATUSHouseholdSummary:
        """Load mock reproductive labor summary (national average)."""
        return ATUSHouseholdSummary(
            fips_code=fips_code,
            year=year,
            total_reproductive_hours_weekly=self._default_weekly_hours,
            unpaid_care_hours_weekly=self._default_weekly_hours,
            paid_care_hours_weekly=0.0,
        )

    def get_shadow_wage(
        self,
        fips_code: str,  # noqa: ARG002
        year: int,  # noqa: ARG002
    ) -> float:
        """Get shadow wage (replacement cost)."""
        return self._shadow_wage_hourly
