"""Pydantic models for American Time Use Survey (ATUS) data.

This module defines data models for ATUS time diary records and household
summaries. These models represent reproductive labor hours that feed into
the shadow labor calculations in Department III.

**ATUS Background:**

The American Time Use Survey (ATUS), conducted by the Bureau of Labor
Statistics since 2003, measures how people allocate time across activities.
It captures both paid and unpaid work, including reproductive labor
(caregiving, housework, childcare) that typically goes unmeasured in
economic statistics.

**Shadow Labor Context:**

Reproductive labor hours from ATUS enable calculation of the "shadow subsidy"
that unpaid care work provides to capital accumulation. The visibility
coefficient (g_33) determines what fraction of this labor is monetized
versus provided as unpaid household work.

See Also:
    :mod:`babylon.data.atus.protocol`: Loader protocol definition.
    :mod:`babylon.data.atus.mock_loader`: Mock implementation for testing.
    :mod:`babylon.economics.shadow_labor`: Shadow labor service.
"""

from __future__ import annotations

import logging
from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

logger = logging.getLogger(__name__)


class ATUSActivityRecord(BaseModel):
    """Single ATUS activity record (time diary entry).

    Represents one activity from a respondent's time diary. ATUS collects
    24-hour diaries that track all activities, coded with 6-digit activity
    codes.

    **Activity Code Structure:**
    - First two digits: Major category (03 = Caring for household members)
    - Next two digits: Second-tier category
    - Last two digits: Detailed activity

    **Reproductive Labor Codes (Major Categories):**
    - 03xxxx: Caring for household members
    - 04xxxx: Caring for non-household members
    - 02xxxx: Household activities (cooking, cleaning)

    Args:
        respondent_id: Unique identifier for ATUS respondent.
        activity_code: ATUS 6-digit activity code.
        duration_minutes: Duration of activity (0-1440 minutes).
        is_reproductive: Whether this activity is reproductive labor.
        is_paid: Whether this activity is compensated work.

    Example:
        >>> record = ATUSActivityRecord(
        ...     respondent_id="R20220001",
        ...     activity_code="030101",  # Physical care of children
        ...     duration_minutes=60,
        ...     is_reproductive=True,
        ...     is_paid=False,
        ... )
        >>> record.duration_minutes
        60
    """

    model_config = ConfigDict(frozen=True)

    respondent_id: str = Field(description="Unique identifier for ATUS respondent")
    activity_code: str = Field(description="ATUS 6-digit activity code")
    duration_minutes: int = Field(
        ge=0,
        le=1440,
        description="Duration of activity in minutes (0-1440, 24 hours max)",
    )
    is_reproductive: bool = Field(
        default=False,
        description="Whether this activity is reproductive labor",
    )
    is_paid: bool = Field(
        default=False,
        description="Whether this activity is compensated work",
    )


class ATUSHouseholdSummary(BaseModel):
    """Aggregated reproductive labor hours for a household.

    Summarizes reproductive labor time use for a household, typically
    aggregated from individual ATUS time diaries. This summary feeds
    into the shadow labor calculation.

    **Key Metrics:**
    - total_reproductive_hours_weekly: All reproductive labor (paid + unpaid)
    - unpaid_care_hours_weekly: Shadow labor (unpaid household work)
    - paid_care_hours_weekly: Monetized care work (daycare, aides)

    **National Averages (ATUS 2022):**
    - Total reproductive hours: ~21 hours/week (average)
    - Unpaid care: ~15 hours/week (70%)
    - Paid care: ~6 hours/week (30%)

    Args:
        fips_code: 5-digit FIPS county code.
        year: Data year (>= 2003 for ATUS availability).
        total_reproductive_hours_weekly: Total reproductive labor hours per week.
        unpaid_care_hours_weekly: Unpaid (shadow) care hours per week.
        paid_care_hours_weekly: Paid (monetized) care hours per week.
        household_weight: Survey weight for aggregation (default 1.0).

    Example:
        >>> summary = ATUSHouseholdSummary(
        ...     fips_code="06001",  # Alameda County, CA
        ...     year=2022,
        ...     total_reproductive_hours_weekly=21.0,
        ...     unpaid_care_hours_weekly=15.0,
        ...     paid_care_hours_weekly=6.0,
        ... )
        >>> summary.unpaid_care_hours_weekly
        15.0
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
    """Four-category decomposition of Department III visibility (Feature 005).

    The visibility coefficient g₃₃ determines what fraction of reproductive
    labor is visible to the price system. This model decomposes g₃₃ into
    four structural categories, each with distinct visibility characteristics.

    **Categories:**

    - domestic_unpaid: Household labor invisible to price system (g=0.0)
    - migrant_care: Partially visible via cash economy (g=0.3)
    - peripheral_subsistence: Externalized to periphery, invisible (g=0.0)
    - state_socialized: Fully visible via public spending (g=1.0)

    **Formula:**

    g₃₃ = Σ(fraction_i × coefficient_i)

    **Invariants:**

    - Fractions must sum to 1.0 ± 0.001
    - All fractions must be in [0.0, 1.0]
    - total_g33 is clamped to [0.0, 1.0]

    Args:
        domestic_unpaid: Fraction of reproductive labor done unpaid at home.
        migrant_care: Fraction done by migrant/noncitizen care workers.
        peripheral_subsistence: Fraction externalized via remittances.
        state_socialized: Fraction provided by public sector.

    Example:
        >>> decomp = VisibilityDecomposition(
        ...     domestic_unpaid=0.70,
        ...     migrant_care=0.10,
        ...     peripheral_subsistence=0.05,
        ...     state_socialized=0.15,
        ... )
        >>> decomp.total_g33
        0.18

    See Also:
        Fortunati, Leopoldina. "The Arcane of Reproduction" (1981).
        specs/005-atus-department-iii/spec.md
    """

    model_config = ConfigDict(frozen=True)

    # Class-level visibility coefficients (constants per research.md)
    G_DOMESTIC: ClassVar[float] = 0.0  # Invisible by definition
    G_MIGRANT: ClassVar[float] = 0.3  # Partially visible via cash economy
    G_PERIPHERAL: ClassVar[float] = 0.0  # Invisible to core price system
    G_STATE: ClassVar[float] = 1.0  # Fully visible via taxation

    # Tolerance thresholds
    _SUM_TOLERANCE: ClassVar[float] = 0.001  # Exact sum tolerance
    _NORMALIZE_THRESHOLD: ClassVar[float] = 0.05  # Auto-normalize if drift <= this
    _WARN_THRESHOLD: ClassVar[float] = 0.01  # Warn if drift > this

    domestic_unpaid: float = Field(
        ge=0.0,
        le=1.0,
        description="Fraction of reproductive labor done unpaid at home",
    )
    migrant_care: float = Field(
        ge=0.0,
        le=1.0,
        description="Fraction done by migrant/noncitizen care workers",
    )
    peripheral_subsistence: float = Field(
        ge=0.0,
        le=1.0,
        description="Fraction externalized to periphery via remittances",
    )
    state_socialized: float = Field(
        ge=0.0,
        le=1.0,
        description="Fraction provided by public sector care",
    )

    @model_validator(mode="after")
    def validate_and_normalize_fractions(self) -> Self:
        """Ensure fractions sum to 1.0, with optional normalization.

        - If sum is within ±0.001 of 1.0: Accept as-is
        - If sum drift is > 0.01 but <= 0.05: Normalize with warning
        - If sum drift is > 0.05: Reject (too far from valid)
        """
        total = (
            self.domestic_unpaid
            + self.migrant_care
            + self.peripheral_subsistence
            + self.state_socialized
        )
        drift = abs(total - 1.0)

        if drift <= self._SUM_TOLERANCE:
            # Within exact tolerance, accept as-is
            return self

        if drift <= self._NORMALIZE_THRESHOLD:
            # Normalize with warning if drift > warn threshold
            if drift > self._WARN_THRESHOLD:
                logger.warning(
                    f"Visibility fractions sum to {total:.4f}, normalizing to 1.0 "
                    f"(drift={drift:.4f})"
                )
            # Normalize by scaling all fractions
            # Use object.__setattr__ since model is frozen
            object.__setattr__(self, "domestic_unpaid", self.domestic_unpaid / total)
            object.__setattr__(self, "migrant_care", self.migrant_care / total)
            object.__setattr__(self, "peripheral_subsistence", self.peripheral_subsistence / total)
            object.__setattr__(self, "state_socialized", self.state_socialized / total)
            return self

        # Drift too large, reject
        msg = (
            f"Visibility fractions must sum to 1.0 ± {self._NORMALIZE_THRESHOLD}. "
            f"Got {total:.4f} (drift={drift:.4f})"
        )
        raise ValueError(msg)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_g33(self) -> float:
        """Compute g₃₃ as weighted average of category coefficients.

        Formula: g₃₃ = Σ(fraction_i × g_i)

        The result is clamped to [0.0, 1.0] per spec.md edge case handling.
        """
        raw_g33 = (
            self.domestic_unpaid * self.G_DOMESTIC
            + self.migrant_care * self.G_MIGRANT
            + self.peripheral_subsistence * self.G_PERIPHERAL
            + self.state_socialized * self.G_STATE
        )

        # Clamp to valid range [0, 1] with warning if needed
        if raw_g33 < 0.0:
            logger.warning(f"Computed g₃₃={raw_g33:.4f} < 0.0, clamping to 0.0")
            return 0.0
        if raw_g33 > 1.0:
            logger.warning(f"Computed g₃₃={raw_g33:.4f} > 1.0, clamping to 1.0")
            return 1.0

        return raw_g33


__all__ = [
    "ATUSActivityRecord",
    "ATUSHouseholdSummary",
    "VisibilityDecomposition",
]
