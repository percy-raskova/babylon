"""Unit tests for Trade data parser.

Tests parsing logic for UN trade data Excel files.
"""

from __future__ import annotations

import pandas as pd
import pytest

from babylon.data.trade.parser import (
    EXPORT_MONTHS,
    IMPORT_MONTHS,
    REGIONAL_NAMES,
    TradeCountryData,
    TradeRowData,
    safe_float,
    safe_int,
)


@pytest.mark.unit
class TestSafeFloat:
    """Tests for safe float conversion."""

    def test_converts_valid_float(self) -> None:
        """Converts valid float values."""
        assert safe_float(123.45) == 123.45

    def test_converts_int_to_float(self) -> None:
        """Converts integers to floats."""
        result = safe_float(100)
        assert result == 100.0
        assert isinstance(result, float)

    def test_returns_none_for_nan(self) -> None:
        """Returns None for pandas NaN."""
        assert safe_float(pd.NA) is None
        assert safe_float(float("nan")) is None

    def test_returns_none_for_invalid(self) -> None:
        """Returns None for non-numeric values."""
        assert safe_float("invalid") is None


@pytest.mark.unit
class TestSafeInt:
    """Tests for safe integer conversion."""

    def test_converts_valid_int(self) -> None:
        """Converts valid integer values."""
        assert safe_int(2023) == 2023

    def test_converts_float_to_int(self) -> None:
        """Truncates floats to integers."""
        assert safe_int(2023.5) == 2023

    def test_returns_none_for_nan(self) -> None:
        """Returns None for pandas NaN."""
        assert safe_int(pd.NA) is None
        assert safe_int(float("nan")) is None


@pytest.mark.unit
class TestConstants:
    """Tests for parser constants."""

    def test_import_months_count(self) -> None:
        """IMPORT_MONTHS has 12 entries."""
        assert len(IMPORT_MONTHS) == 12

    def test_import_months_format(self) -> None:
        """IMPORT_MONTHS entries start with 'I'."""
        for month in IMPORT_MONTHS:
            assert month.startswith("I")

    def test_import_months_order(self) -> None:
        """IMPORT_MONTHS are in calendar order."""
        assert IMPORT_MONTHS[0] == "IJAN"  # January
        assert IMPORT_MONTHS[11] == "IDEC"  # December

    def test_export_months_count(self) -> None:
        """EXPORT_MONTHS has 12 entries."""
        assert len(EXPORT_MONTHS) == 12

    def test_export_months_format(self) -> None:
        """EXPORT_MONTHS entries start with 'E'."""
        for month in EXPORT_MONTHS:
            assert month.startswith("E")

    def test_export_months_order(self) -> None:
        """EXPORT_MONTHS are in calendar order."""
        assert EXPORT_MONTHS[0] == "EJAN"
        assert EXPORT_MONTHS[11] == "EDEC"

    def test_regional_names_set(self) -> None:
        """REGIONAL_NAMES is a non-empty set."""
        assert isinstance(REGIONAL_NAMES, set)
        assert len(REGIONAL_NAMES) > 0

    def test_regional_names_includes_continents(self) -> None:
        """REGIONAL_NAMES includes continent names."""
        assert "Africa" in REGIONAL_NAMES
        assert "Asia" in REGIONAL_NAMES
        assert "Europe" in REGIONAL_NAMES

    def test_regional_names_includes_blocs(self) -> None:
        """REGIONAL_NAMES includes trade blocs."""
        assert "European Union" in REGIONAL_NAMES
        assert "OPEC" in REGIONAL_NAMES


@pytest.mark.unit
class TestTradeCountryData:
    """Tests for TradeCountryData dataclass."""

    def test_country_has_required_fields(self) -> None:
        """TradeCountryData has required fields."""
        country = TradeCountryData(
            cty_code="5700",
            name="China",
        )
        assert country.cty_code == "5700"
        assert country.name == "China"

    def test_country_default_is_region_false(self) -> None:
        """is_region defaults to False."""
        country = TradeCountryData(cty_code="5700", name="China")
        assert country.is_region is False

    def test_country_regional_flag(self) -> None:
        """Regional areas can be flagged."""
        country = TradeCountryData(
            cty_code="0001",
            name="Africa",
            is_region=True,
        )
        assert country.is_region is True


@pytest.mark.unit
class TestTradeRowData:
    """Tests for TradeRowData dataclass."""

    def test_row_has_required_fields(self) -> None:
        """TradeRowData has required fields."""
        row = TradeRowData(
            cty_code="5700",
            year=2023,
        )
        assert row.cty_code == "5700"
        assert row.year == 2023

    def test_row_default_lists_empty(self) -> None:
        """Monthly lists default to empty."""
        row = TradeRowData(cty_code="5700", year=2023)
        assert row.monthly_imports == []
        assert row.monthly_exports == []

    def test_row_default_annuals_none(self) -> None:
        """Annual totals default to None."""
        row = TradeRowData(cty_code="5700", year=2023)
        assert row.annual_imports is None
        assert row.annual_exports is None

    def test_row_with_monthly_data(self) -> None:
        """TradeRowData accepts monthly data lists."""
        row = TradeRowData(
            cty_code="5700",
            year=2023,
            monthly_imports=[
                1000.0,
                1100.0,
                1200.0,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            ],
            monthly_exports=[
                500.0,
                550.0,
                600.0,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            ],
        )
        assert len(row.monthly_imports) == 12
        assert len(row.monthly_exports) == 12
        assert row.monthly_imports[0] == 1000.0
        assert row.monthly_imports[3] is None

    def test_row_with_annual_data(self) -> None:
        """TradeRowData accepts annual totals."""
        row = TradeRowData(
            cty_code="5700",
            year=2023,
            annual_imports=12000000.0,
            annual_exports=6000000.0,
        )
        assert row.annual_imports == 12000000.0
        assert row.annual_exports == 6000000.0


@pytest.mark.unit
class TestTradeRowDataWithFixture:
    """Tests using shared trade fixtures."""

    def test_parse_fixture_row(self, sample_trade_row: dict[str, object]) -> None:
        """Creates row data from fixture."""
        year = safe_int(sample_trade_row["year"])
        assert year is not None

        monthly_imports = [safe_float(sample_trade_row.get(col)) for col in IMPORT_MONTHS]
        monthly_exports = [safe_float(sample_trade_row.get(col)) for col in EXPORT_MONTHS]

        row = TradeRowData(
            cty_code=str(sample_trade_row["CTY_CODE"]),
            year=year,
            monthly_imports=monthly_imports,
            monthly_exports=monthly_exports,
            annual_imports=safe_float(sample_trade_row.get("IYR")),
            annual_exports=safe_float(sample_trade_row.get("EYR")),
        )

        assert row.cty_code == "5700"
        assert row.year == 2023
        assert row.monthly_imports[0] == 1000000.0
        assert row.annual_imports == 12000000.0
