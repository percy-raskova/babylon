"""Census/ACS housing data loader.

Feature: 024-capital-volume-iii (FR-017)
Loads ACS 5-year estimates for housing: B25077 (home values), B25064 (gross rent).
"""

from __future__ import annotations

from typing import ClassVar


class CensusHousingLoader:
    """Loader for Census/ACS housing data.

    Implements :class:`~babylon.economics.rent.data_sources.HousingDataSource`
    protocol.

    Provides in-memory access to median home values, gross rents, and
    construction cost indices at the county level.

    Args:
        home_values: Optional dict mapping (fips, year) to median home value.
        gross_rent: Optional dict mapping (fips, year) to median gross rent.
        construction_index: Optional dict mapping year to construction cost index.
    """

    # Hardcoded defaults from ACS 5-Year Estimates
    _DEFAULT_HOME_VALUES: ClassVar[dict[tuple[str, int], float]] = {
        ("26163", 2015): 44_800.0,  # Wayne County
        ("26163", 2020): 52_000.0,
        ("26163", 2022): 68_000.0,
        ("26125", 2015): 190_000.0,  # Oakland County
        ("26125", 2020): 235_000.0,
        ("26125", 2022): 275_000.0,
    }

    _DEFAULT_GROSS_RENT: ClassVar[dict[tuple[str, int], float]] = {
        ("26163", 2015): 780.0,
        ("26163", 2020): 850.0,
        ("26163", 2022): 950.0,
        ("26125", 2015): 980.0,
        ("26125", 2020): 1100.0,
        ("26125", 2022): 1250.0,
    }

    _DEFAULT_CONSTRUCTION_INDEX: ClassVar[dict[int, float]] = {
        2015: 95.0,
        2018: 100.0,
        2020: 105.0,
        2022: 118.0,
    }

    def __init__(
        self,
        home_values: dict[tuple[str, int], float] | None = None,
        gross_rent: dict[tuple[str, int], float] | None = None,
        construction_index: dict[int, float] | None = None,
    ) -> None:
        self._home_values: dict[tuple[str, int], float] = (
            home_values if home_values is not None else self._DEFAULT_HOME_VALUES.copy()
        )
        self._gross_rent: dict[tuple[str, int], float] = (
            gross_rent if gross_rent is not None else self._DEFAULT_GROSS_RENT.copy()
        )
        self._construction_index: dict[int, float] = (
            construction_index
            if construction_index is not None
            else self._DEFAULT_CONSTRUCTION_INDEX.copy()
        )

    def get_median_home_value(self, fips: str, year: int) -> float | None:
        """Get median value of owner-occupied housing (ACS B25077).

        Args:
            fips: 5-digit county FIPS code.
            year: Calendar year.

        Returns:
            Median home value in current dollars, or None if unavailable.
        """
        return self._home_values.get((fips, year))

    def get_median_gross_rent(self, fips: str, year: int) -> float | None:
        """Get median gross rent (ACS B25064).

        Args:
            fips: 5-digit county FIPS code.
            year: Calendar year.

        Returns:
            Monthly gross rent in current dollars, or None if unavailable.
        """
        return self._gross_rent.get((fips, year))

    def get_construction_cost_index(self, year: int) -> float | None:
        """Get construction cost index (national, RSMeans or Census).

        Args:
            year: Calendar year.

        Returns:
            Index value (base year = 100), or None if unavailable.
        """
        return self._construction_index.get(year)
