"""Reserve Army data source protocols (Feature 021, FR-001).

Defines the protocol for accessing unemployment decomposition data,
with a SQLite implementation reading from FactBLSUnemploymentDecomposition.
"""

from __future__ import annotations

from typing import Protocol

from babylon.economics.reserve_army.types import ReserveArmyState


class ReserveArmyDataSource(Protocol):
    """Protocol for accessing reserve army labor market data.

    Implementations provide unemployment decomposition data for a given
    county and year, returning a ReserveArmyState snapshot.
    """

    def get_unemployment_decomposition(
        self,
        fips_code: str,
        year: int,
    ) -> ReserveArmyState | None:
        """Retrieve unemployment decomposition for a county-year.

        Args:
            fips_code: 5-digit county FIPS code.
            year: Calendar year.

        Returns:
            ReserveArmyState if data exists, None otherwise.
        """
        ...
