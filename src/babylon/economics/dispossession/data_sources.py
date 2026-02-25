"""Dispossession data source protocols (Feature 021, FR-004).

Defines the protocol for accessing dispossession-related data,
including foreclosure rates, eviction rates, and institutional ownership.
"""

from __future__ import annotations

from typing import Protocol

from babylon.economics.dispossession.types import TerritoryDispossessionState


class TerritoryDispossessionDataSource(Protocol):
    """Protocol for accessing territory dispossession data.

    Implementations provide aggregated dispossession metrics for a given
    county and year.
    """

    def get_dispossession_state(
        self,
        fips_code: str,
        year: int,
    ) -> TerritoryDispossessionState | None:
        """Retrieve aggregate dispossession metrics for a county-year.

        Args:
            fips_code: 5-digit county FIPS code.
            year: Calendar year.

        Returns:
            TerritoryDispossessionState if data exists, None otherwise.
        """
        ...
