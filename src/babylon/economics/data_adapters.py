"""Default data adapters for economics module.

Self-contained data loaders with hardcoded defaults for financial
and housing data. These implement protocol interfaces expected by
economics calculators.

Originally in babylon-data (census/housing_loader.py, fred/z1_loader.py).
Moved here since they are pure in-memory data with no ETL dependency.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import ClassVar


class Z1Loader:
    """Loader for Fed Z.1 Financial Accounts data.

    Implements the Z1FinancialAccountsSource protocol.

    Provides in-memory access to corporate debt, household debt, and
    derivatives notional data from the Z.1 L.1 tables.

    Args:
        data: Optional dict mapping year to field values.
            Falls back to hardcoded defaults if not provided.
    """

    _DEFAULT_DATA: ClassVar[dict[int, dict[str, float]]] = {
        2007: {
            "corporate_debt": 6_900_000_000_000,
            "household_debt": 13_800_000_000_000,
            "derivatives": 595_000_000_000_000,
        },
        2008: {
            "corporate_debt": 7_200_000_000_000,
            "household_debt": 13_600_000_000_000,
            "derivatives": 592_000_000_000_000,
        },
        2010: {
            "corporate_debt": 7_000_000_000_000,
            "household_debt": 13_200_000_000_000,
            "derivatives": 583_000_000_000_000,
        },
        2015: {
            "corporate_debt": 8_500_000_000_000,
            "household_debt": 14_100_000_000_000,
            "derivatives": 550_000_000_000_000,
        },
        2018: {
            "corporate_debt": 9_800_000_000_000,
            "household_debt": 15_600_000_000_000,
            "derivatives": 594_000_000_000_000,
        },
        2020: {
            "corporate_debt": 11_200_000_000_000,
            "household_debt": 16_100_000_000_000,
            "derivatives": 600_000_000_000_000,
        },
        2022: {
            "corporate_debt": 12_500_000_000_000,
            "household_debt": 18_200_000_000_000,
            "derivatives": 632_000_000_000_000,
        },
    }

    def __init__(self, data: dict[int, dict[str, float]] | None = None) -> None:
        self._data: dict[int, dict[str, float]] = (
            data if data is not None else self._DEFAULT_DATA.copy()
        )

    @classmethod
    def from_csv(cls, csv_path: Path) -> Z1Loader:
        """Parse Z.1 bulk CSV into loader.

        Args:
            csv_path: Path to Z.1 CSV export file.

        Returns:
            Z1Loader populated from CSV data.
        """
        data: dict[int, dict[str, float]] = {}
        with csv_path.open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                year = int(row["year"])
                if year not in data:
                    data[year] = {}
                data[year][row["field"]] = float(row["value"])
        return cls(data=data)

    def get_corporate_debt(self, year: int) -> float | None:
        """Get total nonfinancial corporate debt (L.103 line 32)."""
        entry = self._data.get(year)
        return entry.get("corporate_debt") if entry else None

    def get_household_debt(self, year: int) -> float | None:
        """Get total household sector debt (L.101 line 25)."""
        entry = self._data.get(year)
        return entry.get("household_debt") if entry else None

    def get_derivatives_notional(self, year: int) -> float | None:
        """Get OTC derivatives notional outstanding (L.1 line 1)."""
        entry = self._data.get(year)
        return entry.get("derivatives") if entry else None


class CensusHousingLoader:
    """Loader for Census/ACS housing data.

    Implements the HousingDataSource protocol.

    Args:
        home_values: Optional dict mapping (fips, year) to median home value.
        gross_rent: Optional dict mapping (fips, year) to median gross rent.
        construction_index: Optional dict mapping year to construction cost index.
    """

    _DEFAULT_HOME_VALUES: ClassVar[dict[tuple[str, int], float]] = {
        ("26163", 2015): 44_800.0,
        ("26163", 2020): 52_000.0,
        ("26163", 2022): 68_000.0,
        ("26125", 2015): 190_000.0,
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
        """Get median value of owner-occupied housing (ACS B25077)."""
        return self._home_values.get((fips, year))

    def get_median_gross_rent(self, fips: str, year: int) -> float | None:
        """Get median gross rent (ACS B25064)."""
        return self._gross_rent.get((fips, year))

    def get_construction_cost_index(self, year: int) -> float | None:
        """Get construction cost index (national, RSMeans or Census)."""
        return self._construction_index.get(year)
