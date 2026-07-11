"""Working Day data source protocols (Feature 021, FR-007).

Defines the protocol for accessing productivity and hours data.
"""

from __future__ import annotations

from typing import Protocol

from babylon.domain.economics.working_day.types import WorkingDayState


class ProductivityDataSource(Protocol):
    """Protocol for accessing sector-level productivity data.

    Implementations provide working day characteristics for a given
    county, NAICS sector, and year.
    """

    def get_working_day_state(
        self,
        fips_code: str,
        naics_sector: str,
        year: int,
    ) -> WorkingDayState | None:
        """Retrieve working day state for a territory-sector-year.

        Args:
            fips_code: 5-digit county FIPS code.
            naics_sector: 2-digit NAICS sector code.
            year: Calendar year.

        Returns:
            WorkingDayState if data exists, None otherwise.
        """
        ...
