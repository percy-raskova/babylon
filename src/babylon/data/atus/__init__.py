"""ATUS (American Time Use Survey) data loading infrastructure.

This package provides data loading infrastructure for reproductive labor
hours from the American Time Use Survey (ATUS). These hours feed into
the shadow labor calculations in Department III.

**Package Contents:**
- models: ATUSActivityRecord, ATUSHouseholdSummary Pydantic models
- protocol: ReproductionLoaderProtocol abstract base class
- mock_loader: MockReproductionLoader for testing

**Current Implementation:**

The MockReproductionLoader provides configurable national averages for
testing without requiring real ATUS data. This is the "workaround"
solution for the Shadow Labor Sprint.

**Future Roadmap:**
- ATUSLoader: Real ATUS microdata loader (BLS API integration)
- County-level variation based on demographic factors
- Inflation-adjusted wage series
- Integration with World Bank/ILO time-use surveys

Example:
    >>> from babylon.data.atus import (
    ...     MockReproductionLoader,
    ...     ATUSHouseholdSummary,
    ...     ReproductionLoaderProtocol,
    ... )
    >>> loader = MockReproductionLoader()
    >>> summary = loader.load_county_summary("06001", 2022)
    >>> summary.unpaid_care_hours_weekly
    21.0

See Also:
    :mod:`babylon.economics.shadow_labor`: Shadow labor service.
    :mod:`babylon.economics.reproduction`: Imperial rent calculation.
"""

from babylon.data.atus.mock_loader import (
    NATIONAL_AVG_UNPAID_CARE_WEEKLY,
    REPLACEMENT_COST_HOURLY,
    MockReproductionLoader,
)
from babylon.data.atus.models import ATUSActivityRecord, ATUSHouseholdSummary
from babylon.data.atus.protocol import ReproductionLoaderProtocol

__all__ = [
    # Models
    "ATUSActivityRecord",
    "ATUSHouseholdSummary",
    # Protocol
    "ReproductionLoaderProtocol",
    # Mock implementation
    "MockReproductionLoader",
    # Constants
    "NATIONAL_AVG_UNPAID_CARE_WEEKLY",
    "REPLACEMENT_COST_HOURLY",
]
