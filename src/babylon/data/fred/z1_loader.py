"""Fed Z.1 Financial Accounts loader.

Feature: 024-capital-volume-iii (FR-017)
Constitution III.4 approved: Fed Z.1 Financial Accounts.

Loads sectoral balance sheet data from the Federal Reserve's
Financial Accounts of the United States (Z.1 release).
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import ClassVar


class Z1Loader:
    """Loader for Fed Z.1 Financial Accounts data.

    Implements :class:`~babylon.economics.credit.data_sources.Z1FinancialAccountsSource`
    protocol.

    Provides in-memory access to corporate debt, household debt, and
    derivatives notional data from the Z.1 L.1 tables.

    Args:
        data: Optional dict mapping year to field values.
            Falls back to hardcoded defaults if not provided.
    """

    # Hardcoded defaults from Z.1 L.1 tables (in dollars, not billions)
    # Source: Federal Reserve Financial Accounts, Table L.1
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
            csv_path: Path to CSV file with columns:
                year, corporate_debt, household_debt, derivatives_notional.

        Returns:
            Z1Loader populated with parsed data.

        Raises:
            FileNotFoundError: If csv_path does not exist.
            KeyError: If required 'year' column is missing.
        """
        data: dict[int, dict[str, float]] = {}
        with csv_path.open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                year = int(row["year"])
                data[year] = {
                    "corporate_debt": float(row.get("corporate_debt", "0")),
                    "household_debt": float(row.get("household_debt", "0")),
                    "derivatives": float(row.get("derivatives_notional", "0")),
                }
        return cls(data=data)

    def get_corporate_debt(self, year: int) -> float | None:
        """Get total corporate debt outstanding for a given year.

        Args:
            year: Calendar year.

        Returns:
            Corporate debt in current dollars, or None if unavailable.
        """
        entry = self._data.get(year)
        return entry["corporate_debt"] if entry else None

    def get_household_debt(self, year: int) -> float | None:
        """Get total household debt for a given year.

        Args:
            year: Calendar year.

        Returns:
            Household debt in current dollars, or None if unavailable.
        """
        entry = self._data.get(year)
        return entry["household_debt"] if entry else None

    def get_derivatives_notional(self, year: int) -> float | None:
        """Get notional value of derivative contracts for a given year.

        Args:
            year: Calendar year.

        Returns:
            Derivatives notional in current dollars, or None if unavailable.
        """
        entry = self._data.get(year)
        return entry.get("derivatives") if entry else None
