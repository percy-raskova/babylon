"""Tests for Z1Loader (Feature 024, T071).

Verifies Z1Loader returns data for known years, None for unknown years,
and that from_csv classmethod works correctly.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from babylon.data.fred.z1_loader import Z1Loader


@pytest.mark.unit
class TestZ1LoaderDefaults:
    """Tests for Z1Loader with default data."""

    def test_init_loads_defaults(self) -> None:
        """Default constructor populates data from _DEFAULT_DATA."""
        loader = Z1Loader()
        assert loader.get_corporate_debt(2007) is not None

    def test_corporate_debt_known_year(self) -> None:
        """Returns corporate debt for a known year."""
        loader = Z1Loader()
        result = loader.get_corporate_debt(2007)
        assert result == 6_900_000_000_000

    def test_household_debt_known_year(self) -> None:
        """Returns household debt for a known year."""
        loader = Z1Loader()
        result = loader.get_household_debt(2022)
        assert result == 18_200_000_000_000

    def test_derivatives_notional_known_year(self) -> None:
        """Returns derivatives notional for a known year."""
        loader = Z1Loader()
        result = loader.get_derivatives_notional(2020)
        assert result == 600_000_000_000_000

    def test_corporate_debt_unknown_year(self) -> None:
        """Returns None for unknown year."""
        loader = Z1Loader()
        assert loader.get_corporate_debt(1999) is None

    def test_household_debt_unknown_year(self) -> None:
        """Returns None for unknown year."""
        loader = Z1Loader()
        assert loader.get_household_debt(2050) is None

    def test_derivatives_notional_unknown_year(self) -> None:
        """Returns None for unknown year."""
        loader = Z1Loader()
        assert loader.get_derivatives_notional(1900) is None

    def test_all_default_years_have_data(self) -> None:
        """All hardcoded default years return data for all fields."""
        loader = Z1Loader()
        for year in (2007, 2008, 2010, 2015, 2018, 2020, 2022):
            assert loader.get_corporate_debt(year) is not None, f"Missing corporate_debt for {year}"
            assert loader.get_household_debt(year) is not None, f"Missing household_debt for {year}"
            assert loader.get_derivatives_notional(year) is not None, (
                f"Missing derivatives for {year}"
            )

    def test_corporate_debt_increases_over_time(self) -> None:
        """Corporate debt generally increases from 2007 to 2022."""
        loader = Z1Loader()
        debt_2007 = loader.get_corporate_debt(2007)
        debt_2022 = loader.get_corporate_debt(2022)
        assert debt_2007 is not None
        assert debt_2022 is not None
        assert debt_2022 > debt_2007


@pytest.mark.unit
class TestZ1LoaderCustomData:
    """Tests for Z1Loader with custom injected data."""

    def test_custom_data_overrides_defaults(self) -> None:
        """Custom data dict replaces defaults entirely."""
        custom = {2000: {"corporate_debt": 1.0, "household_debt": 2.0, "derivatives": 3.0}}
        loader = Z1Loader(data=custom)
        assert loader.get_corporate_debt(2000) == 1.0
        assert loader.get_corporate_debt(2007) is None  # Default year gone

    def test_empty_data_returns_none(self) -> None:
        """Empty data dict returns None for all years."""
        loader = Z1Loader(data={})
        assert loader.get_corporate_debt(2022) is None
        assert loader.get_household_debt(2022) is None
        assert loader.get_derivatives_notional(2022) is None


@pytest.mark.unit
class TestZ1LoaderFromCSV:
    """Tests for Z1Loader.from_csv classmethod."""

    def test_from_csv_parses_data(self, tmp_path: Path) -> None:
        """from_csv loads data from a CSV file."""
        csv_file = tmp_path / "z1_test.csv"
        with csv_file.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["year", "corporate_debt", "household_debt", "derivatives_notional"])
            writer.writerow(["2019", "10000", "15000", "500000"])
            writer.writerow(["2020", "11000", "16000", "600000"])

        loader = Z1Loader.from_csv(csv_file)
        assert loader.get_corporate_debt(2019) == 10_000.0
        assert loader.get_household_debt(2020) == 16_000.0
        assert loader.get_derivatives_notional(2019) == 500_000.0

    def test_from_csv_missing_columns_default_to_zero(self, tmp_path: Path) -> None:
        """from_csv handles missing optional columns by defaulting to 0."""
        csv_file = tmp_path / "z1_partial.csv"
        with csv_file.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["year", "corporate_debt"])
            writer.writerow(["2019", "10000"])

        loader = Z1Loader.from_csv(csv_file)
        assert loader.get_corporate_debt(2019) == 10_000.0
        assert loader.get_household_debt(2019) == 0.0
        assert loader.get_derivatives_notional(2019) == 0.0

    def test_from_csv_unknown_year_returns_none(self, tmp_path: Path) -> None:
        """from_csv loader returns None for years not in CSV."""
        csv_file = tmp_path / "z1_small.csv"
        with csv_file.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["year", "corporate_debt", "household_debt", "derivatives_notional"])
            writer.writerow(["2019", "10000", "15000", "500000"])

        loader = Z1Loader.from_csv(csv_file)
        assert loader.get_corporate_debt(2020) is None

    def test_from_csv_file_not_found(self) -> None:
        """from_csv raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            Z1Loader.from_csv(Path("/nonexistent/z1.csv"))


@pytest.mark.unit
class TestZ1LoaderProtocolCompliance:
    """Tests that Z1Loader satisfies Z1FinancialAccountsSource protocol."""

    def test_has_get_corporate_debt(self) -> None:
        """Z1Loader has get_corporate_debt method."""
        loader = Z1Loader()
        assert callable(loader.get_corporate_debt)

    def test_has_get_household_debt(self) -> None:
        """Z1Loader has get_household_debt method."""
        loader = Z1Loader()
        assert callable(loader.get_household_debt)

    def test_has_get_derivatives_notional(self) -> None:
        """Z1Loader has get_derivatives_notional method."""
        loader = Z1Loader()
        assert callable(loader.get_derivatives_notional)

    def test_satisfies_protocol_structurally(self) -> None:
        """Z1Loader is structurally compatible with Z1FinancialAccountsSource.

        Uses static type annotation assignment (same pattern as conftest.py)
        to verify structural protocol compliance without runtime_checkable.
        """
        from babylon.economics.credit.data_sources import Z1FinancialAccountsSource

        # Static protocol check via type annotation assignment
        source: Z1FinancialAccountsSource = Z1Loader()
        assert source.get_corporate_debt(2007) is not None
