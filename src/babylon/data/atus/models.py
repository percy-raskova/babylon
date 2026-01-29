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

from pydantic import BaseModel, ConfigDict, Field


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


__all__ = [
    "ATUSActivityRecord",
    "ATUSHouseholdSummary",
]
