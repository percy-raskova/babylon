"""Mock implementation of ReproductionLoaderProtocol for testing.

This module provides a mock ATUS data loader that returns configurable
national averages. This enables testing the shadow labor service without
requiring real ATUS data or BLS API integration.

**Mock Defaults (ATUS 2022 National Averages):**
- Unpaid care hours: 21 hours/week (average for all adults)
- Shadow wage: $15.43/hour (BLS OES May 2023, SOC 31-1120)

**Future Roadmap:**
- Replace with real ATUSLoader when BLS microdata integrated
- Add county-level variation based on demographic factors
- Integrate inflation-adjusted wage series

See Also:
    :mod:`babylon.data.atus.protocol`: Protocol definition.
    :mod:`babylon.economics.shadow_labor`: Service that uses this loader.
"""

from __future__ import annotations

from babylon.data.atus.models import ATUSHouseholdSummary
from babylon.data.atus.protocol import ReproductionLoaderProtocol

# =============================================================================
# Constants (ATUS 2022 National Averages)
# =============================================================================

# National average unpaid care hours per week (ATUS 2022)
# Source: BLS ATUS tables, Table A-1
# Average for all persons 15 years and over: ~3 hours/day on household activities
# This translates to approximately 21 hours/week average
NATIONAL_AVG_UNPAID_CARE_WEEKLY: float = 21.0

# BLS Occupational Employment Statistics (May 2023)
# SOC 31-1120: Home Health and Personal Care Aides
# Median hourly wage: $15.43
# This represents the market replacement cost for unpaid care work
REPLACEMENT_COST_HOURLY: float = 15.43


class MockReproductionLoader(ReproductionLoaderProtocol):
    """Mock ATUS data loader returning configurable national averages.

    This mock implementation provides consistent, configurable values
    for testing the shadow labor service. It does not model county-level
    variation or inflation adjustment.

    **Default Values:**
    - Weekly hours: 21 hours/week (ATUS 2022 national average)
    - Shadow wage: $15.43/hour (BLS home health aide median)

    **Usage Pattern:**
    1. Instantiate with optional custom values
    2. Inject into ShadowLaborService
    3. Service calculates shadow decomposition using mock data

    Args:
        default_weekly_hours: Unpaid care hours per week (default 21.0).
        shadow_wage_hourly: Replacement cost wage (default $15.43/hour).

    Example:
        >>> loader = MockReproductionLoader()
        >>> summary = loader.load_county_summary("06001", 2022)
        >>> summary.unpaid_care_hours_weekly
        21.0
        >>> loader.get_shadow_wage("06001", 2022)
        15.43

        >>> # Custom values for testing
        >>> loader = MockReproductionLoader(
        ...     default_weekly_hours=1000/52,  # 1000 annual hours
        ...     shadow_wage_hourly=15.43,
        ... )
    """

    def __init__(
        self,
        default_weekly_hours: float = NATIONAL_AVG_UNPAID_CARE_WEEKLY,
        shadow_wage_hourly: float = REPLACEMENT_COST_HOURLY,
    ) -> None:
        """Initialize mock loader with configurable defaults.

        Args:
            default_weekly_hours: Unpaid care hours per week.
            shadow_wage_hourly: Replacement cost wage (USD/hour).
        """
        self._default_weekly_hours = default_weekly_hours
        self._shadow_wage_hourly = shadow_wage_hourly

    def load_county_summary(
        self,
        fips_code: str,
        year: int,
    ) -> ATUSHouseholdSummary:
        """Load mock reproductive labor summary (national average).

        Returns the same values for all counties (no county-level variation).
        Future implementations will provide geographic variation.

        Args:
            fips_code: 5-digit FIPS county code (passed through to result).
            year: Data year (passed through to result).

        Returns:
            ATUSHouseholdSummary with configured defaults.
        """
        # Mock assumes ~30% of care is paid (g_33 default)
        # This is just for mock data; actual split is in shadow_labor.py
        return ATUSHouseholdSummary(
            fips_code=fips_code,
            year=year,
            total_reproductive_hours_weekly=self._default_weekly_hours,
            unpaid_care_hours_weekly=self._default_weekly_hours,
            paid_care_hours_weekly=0.0,  # All unpaid in mock (visibility logic applies later)
        )

    def get_shadow_wage(
        self,
        fips_code: str,  # noqa: ARG002 - future: regional wage variation
        year: int,  # noqa: ARG002 - future: inflation adjustment
    ) -> float:
        """Get shadow wage (replacement cost).

        Returns configured shadow wage (no regional variation in mock).

        Args:
            fips_code: 5-digit FIPS county code (unused in mock).
            year: Data year (unused in mock).

        Returns:
            Shadow wage in USD/hour.
        """
        return self._shadow_wage_hourly


__all__ = [
    "MockReproductionLoader",
    "NATIONAL_AVG_UNPAID_CARE_WEEKLY",
    "REPLACEMENT_COST_HOURLY",
]
