"""QCEW Care Sector Adapter for computing paid care hours.

Feature: 015-gamma-visibility-tensor
Date: 2026-02-05

This module adapts QCEW employment data to compute paid care hours by
applying care fraction coefficients to employment in care-related NAICS sectors.

NAICS Sectors and Care Fractions:
    - 61: Educational Services (60% instruction/care)
    - 62: Healthcare and Social Assistance (30% direct care)
    - 814: Private Households (100% care work)

Note on NAICS 624 (Social Assistance):
    NAICS 624 is a subset of NAICS 62. To avoid double-counting, we use
    only the top-level sector codes (61, 62, 814). The 30% care fraction
    for NAICS 62 already accounts for the mix of direct care (higher in 624)
    and administrative/billing work (lower care fraction).

See Also:
    :mod:`babylon.economics.melt.data_sources`: QCEW protocol definitions
    :mod:`babylon.economics.gamma.data_sources`: PaidCareHoursSource protocol
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# =============================================================================
# CARE SECTOR CONSTANTS
# =============================================================================

CARE_NAICS_CODES: dict[str, float] = {
    "61": 0.60,  # Educational Services - 60% instruction/direct care
    "62": 0.30,  # Healthcare & Social Assistance - 30% direct patient care
    "814": 1.00,  # Private Households - 100% domestic/care work
}
"""NAICS sector codes mapped to care fraction coefficients.

Care fractions represent the estimated proportion of employment hours
that constitute direct care work (as opposed to administrative, billing,
or other non-care activities within the sector).

Sources:
    - Education (61): NCES Teacher Time-Use surveys
    - Healthcare (62): CMS staffing data
    - Private Households (814): BLS Occupational Employment Statistics
"""

HOURS_PER_YEAR: int = 2080
"""Standard annual work hours: 40 hours/week * 52 weeks/year."""

# MVP employment estimates by sector (2022, thousands of workers)
# Used as fallback when QCEW sector data is not available
MVP_CARE_EMPLOYMENT_2022: dict[str, int] = {
    "61": 3_950_000,  # ~3.95 million in educational services
    "62": 21_500_000,  # ~21.5 million in healthcare & social assistance
    "814": 600_000,  # ~600k in private households
}


class QCEWCareAdapter:
    """Adapter that computes paid care hours from QCEW employment data.

    Implements the ``PaidCareHoursSource`` protocol by:
    1. Getting employment for each care NAICS sector
    2. Multiplying by 2080 hours/year
    3. Applying the care fraction coefficient
    4. Summing across sectors

    Formula:
        L_paid_care = sum(employment_i * 2080 * care_fraction_i) for each NAICS sector

    Args:
        employment_by_sector: Dict mapping NAICS code to employment count.
            If None, uses MVP estimates for 2022.

    Example:
        >>> adapter = QCEWCareAdapter()
        >>> hours = adapter.get_paid_care_hours(2022)
        >>> print(f"Paid care: {hours:.1f}B hours")
    """

    def __init__(
        self,
        employment_by_sector: dict[int, dict[str, int]] | None = None,
    ) -> None:
        """Initialize with optional employment data by year and sector.

        Args:
            employment_by_sector: Dict mapping year -> (NAICS code -> employment).
                If None, uses MVP estimates.
        """
        self._employment_by_sector = employment_by_sector

    def get_paid_care_hours(self, year: int) -> float | None:
        """Get annual paid care hours for a given year.

        Args:
            year: Calendar year.

        Returns:
            Paid care hours in billions, or None if data unavailable.
        """
        sector_employment: dict[str, int] | None = None

        if self._employment_by_sector is not None:
            sector_employment = self._employment_by_sector.get(year)
        elif year == 2022:
            sector_employment = MVP_CARE_EMPLOYMENT_2022

        if sector_employment is None:
            return None

        total_care_hours: float = 0.0
        for naics_code, care_fraction in CARE_NAICS_CODES.items():
            employment = sector_employment.get(naics_code)
            if employment is None:
                logger.warning("No employment data for NAICS %s in year %d", naics_code, year)
                continue
            sector_hours = employment * HOURS_PER_YEAR * care_fraction
            total_care_hours += sector_hours

        # Convert to billions
        return total_care_hours / 1_000_000_000


__all__ = [
    "CARE_NAICS_CODES",
    "HOURS_PER_YEAR",
    "QCEWCareAdapter",
]
