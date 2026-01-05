"""Unit tests for USGS Materials parser.

Tests parsing logic for USGS Mineral Commodity Summaries CSV files.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from babylon.data.materials.parser import (
    CommodityRecord,
    ImportSourceRecord,
    StateRecord,
    TrendRecord,
    discover_aggregate_files,
    discover_commodity_files,
    extract_commodity_code,
    get_metric_category,
    normalize_metric_code,
    parse_commodity_csv,
    parse_import_sources_csv,
    parse_state_csv,
    parse_trends_csv,
    parse_value,
)


@pytest.mark.unit
class TestParseValue:
    """Tests for USGS special value parsing."""

    def test_parses_numeric_value(self) -> None:
        """Parses standard numeric values."""
        value, text = parse_value("28.5")
        assert value == 28.5
        assert text is None

    def test_parses_integer_value(self) -> None:
        """Parses integer values."""
        value, text = parse_value("100")
        assert value == 100.0
        assert text is None

    def test_parses_value_with_commas(self) -> None:
        """Parses values with thousand separators."""
        value, text = parse_value("1,234")
        assert value == 1234.0
        assert text is None

    def test_withheld_returns_none_with_marker(self) -> None:
        """Returns None with 'W' marker for withheld data."""
        value, text = parse_value("W")
        assert value is None
        assert text == "W"

    def test_withheld_case_insensitive(self) -> None:
        """Handles lowercase withheld marker."""
        value, text = parse_value("w")
        assert value is None
        assert text == "W"

    def test_na_returns_none(self) -> None:
        """Returns None for NA values."""
        for na_val in ("NA", "N/A", "", "--", "-"):
            value, text = parse_value(na_val)
            assert value is None

    def test_greater_than_extracts_threshold(self) -> None:
        """Extracts numeric threshold from >N notation."""
        value, text = parse_value(">50")
        assert value == 50.0
        assert text == ">50"

    def test_less_than_extracts_threshold(self) -> None:
        """Extracts numeric threshold from <N notation."""
        value, text = parse_value("<1")
        assert value == 1.0
        assert text == "<1"

    def test_net_exporter_marker(self) -> None:
        """Handles 'E' net exporter marker."""
        value, text = parse_value("E")
        assert value is None
        assert text == "E"

    def test_none_input(self) -> None:
        """Handles None input."""
        value, text = parse_value(None)
        assert value is None
        assert text is None


@pytest.mark.unit
class TestExtractCommodityCode:
    """Tests for commodity code extraction from filename."""

    def test_extracts_from_standard_filename(self) -> None:
        """Extracts code from mcs2025-*_salient.csv pattern."""
        assert extract_commodity_code("mcs2025-lithium_salient.csv") == "lithium"

    def test_extracts_from_rare_earth(self) -> None:
        """Extracts rare earth code."""
        assert extract_commodity_code("mcs2025-reare_salient.csv") == "reare"

    def test_case_insensitive(self) -> None:
        """Handles case variations."""
        assert extract_commodity_code("MCS2025-LITHIUM_salient.csv") == "lithium"

    def test_fallback_for_non_matching(self) -> None:
        """Falls back for non-standard filenames."""
        result = extract_commodity_code("other_format.csv")
        assert isinstance(result, str)


@pytest.mark.unit
class TestNormalizeMetricCode:
    """Tests for metric code normalization."""

    def test_preserves_valid_code(self) -> None:
        """Preserves properly formatted codes."""
        assert normalize_metric_code("USprod_Primary_kt") == "USprod_Primary_kt"

    def test_strips_whitespace(self) -> None:
        """Strips leading/trailing whitespace."""
        assert normalize_metric_code("  NIR_pct  ") == "NIR_pct"


@pytest.mark.unit
class TestGetMetricCategory:
    """Tests for metric category determination."""

    def test_production_category(self) -> None:
        """Identifies production metrics."""
        assert get_metric_category("USprod_t") == "production"
        assert get_metric_category("MINE_PROD_kt") == "production"

    def test_trade_category(self) -> None:
        """Identifies trade metrics."""
        assert get_metric_category("IMPORT_kt") == "trade"
        assert get_metric_category("EXPORT_kt") == "trade"

    def test_consumption_category(self) -> None:
        """Identifies consumption metrics."""
        assert get_metric_category("CONSUMP_kt") == "consumption"
        assert get_metric_category("SUPPLY_kt") == "consumption"

    def test_price_category(self) -> None:
        """Identifies price metrics."""
        assert get_metric_category("PRICE_usd") == "price"
        assert get_metric_category("AVG_PRICE") == "price"

    def test_strategic_category(self) -> None:
        """Identifies strategic metrics."""
        assert get_metric_category("NIR_pct") == "strategic"
        assert get_metric_category("STOCK_kt") == "strategic"

    def test_employment_category(self) -> None:
        """Identifies employment metrics."""
        assert get_metric_category("EMPLOY_count") == "employment"

    def test_other_category_fallback(self) -> None:
        """Falls back to other for unrecognized codes."""
        assert get_metric_category("UNKNOWN_metric") == "other"


@pytest.mark.unit
class TestCommodityRecord:
    """Tests for CommodityRecord dataclass."""

    def test_record_has_required_fields(self) -> None:
        """CommodityRecord has all expected fields."""
        record = CommodityRecord(
            commodity_code="lithium",
            commodity_name="Lithium",
            metric_code="USprod_kt",
            metric_name="US Production (kt)",
            year=2023,
            value=23.5,
            value_text=None,
        )
        assert record.commodity_code == "lithium"
        assert record.commodity_name == "Lithium"
        assert record.year == 2023
        assert record.value == 23.5

    def test_record_with_withheld_value(self) -> None:
        """CommodityRecord handles withheld values."""
        record = CommodityRecord(
            commodity_code="lithium",
            commodity_name="Lithium",
            metric_code="USprod_kt",
            metric_name="US Production (kt)",
            year=2023,
            value=None,
            value_text="W",
        )
        assert record.value is None
        assert record.value_text == "W"


@pytest.mark.unit
class TestTrendRecord:
    """Tests for TrendRecord dataclass."""

    def test_record_has_required_fields(self) -> None:
        """TrendRecord has all expected fields."""
        record = TrendRecord(
            year=2023,
            values={"Employment_thousands": 85.2, "Production_index": 102.5},
        )
        assert record.year == 2023
        assert record.values["Employment_thousands"] == 85.2

    def test_record_default_values(self) -> None:
        """TrendRecord has empty dict by default."""
        record = TrendRecord(year=2023)
        assert record.values == {}


@pytest.mark.unit
class TestStateRecord:
    """Tests for StateRecord dataclass."""

    def test_record_has_required_fields(self) -> None:
        """StateRecord has all expected fields."""
        record = StateRecord(
            state_name="Nevada",
            year=2024,
            value_millions=10500.0,
            rank=1,
            percent_total=12.5,
            principal_commodities="gold, copper, lithium",
        )
        assert record.state_name == "Nevada"
        assert record.rank == 1
        assert record.percent_total == 12.5

    def test_record_with_none_values(self) -> None:
        """StateRecord accepts None for optional fields."""
        record = StateRecord(
            state_name="Unknown",
            year=2024,
            value_millions=None,
            rank=None,
            percent_total=None,
            principal_commodities=None,
        )
        assert record.value_millions is None
        assert record.rank is None


@pytest.mark.unit
class TestImportSourceRecord:
    """Tests for ImportSourceRecord dataclass."""

    def test_record_has_required_fields(self) -> None:
        """ImportSourceRecord has all expected fields."""
        record = ImportSourceRecord(
            country="China",
            commodity_count=12,
            map_class="10 or more",
        )
        assert record.country == "China"
        assert record.commodity_count == 12
        assert record.map_class == "10 or more"


@pytest.mark.unit
class TestParseCommodityCsv:
    """Tests for commodity CSV parsing."""

    def test_parses_commodity_file(self) -> None:
        """Parses commodity CSV into records."""
        csv_content = """DataSource,Commodity,Year,USprod_kt,Import_kt
MCS2025,Lithium,2023,1.5,2.0
MCS2025,Lithium,2024,1.8,W
"""
        with TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "mcs2025-lithium_salient.csv"
            csv_path.write_text(csv_content)

            records = parse_commodity_csv(csv_path)

        assert len(records) > 0
        # Check first record
        lithium_records = [r for r in records if r.commodity_code == "lithium"]
        assert len(lithium_records) > 0
        assert lithium_records[0].commodity_name == "Lithium"

    def test_returns_empty_for_missing_file(self) -> None:
        """Returns empty list for non-existent file."""
        records = parse_commodity_csv(Path("/nonexistent/file.csv"))
        assert records == []

    def test_handles_withheld_values(self) -> None:
        """Handles withheld (W) values correctly."""
        csv_content = """DataSource,Commodity,Year,USprod_kt
MCS2025,Test,2023,W
"""
        with TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "mcs2025-test_salient.csv"
            csv_path.write_text(csv_content)

            records = parse_commodity_csv(csv_path)

        withheld = [r for r in records if r.value_text == "W"]
        assert len(withheld) > 0
        assert withheld[0].value is None


@pytest.mark.unit
class TestParseTrendsCsv:
    """Tests for trends CSV parsing."""

    def test_parses_trends_file(self) -> None:
        """Parses trends CSV into records."""
        csv_content = """Source,Year,Employment,Production_Index
MCS2025,2023,85000,102.5
MCS2025,2024,86000,103.0
"""
        with TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "MCS2025_T1_Mineral_Industry_Trends.csv"
            csv_path.write_text(csv_content)

            records = parse_trends_csv(csv_path)

        assert len(records) == 2
        assert records[0].year == 2023
        assert "Employment" in records[0].values

    def test_returns_empty_for_missing_file(self) -> None:
        """Returns empty list for non-existent file."""
        records = parse_trends_csv(Path("/nonexistent/file.csv"))
        assert records == []


@pytest.mark.unit
class TestParseStateCsv:
    """Tests for state CSV parsing."""

    def test_parses_state_file(self) -> None:
        """Parses state CSV into records."""
        csv_content = """State,Year,Value _millions_prelim_2024,State_Rank_prelim_2024,State_percent_total_prelim,Principal_commodities
Nevada,2024,10500,1,12.5,gold copper
Arizona,2024,9800,2,11.7,copper molybdenum
"""
        with TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "MCS2025_T3_State_Value_Rank.csv"
            csv_path.write_text(csv_content)

            records = parse_state_csv(csv_path)

        assert len(records) == 2
        nevada = [r for r in records if r.state_name == "Nevada"][0]
        assert nevada.rank == 1
        assert nevada.value_millions == 10500.0

    def test_returns_empty_for_missing_file(self) -> None:
        """Returns empty list for non-existent file."""
        records = parse_state_csv(Path("/nonexistent/file.csv"))
        assert records == []


@pytest.mark.unit
class TestParseImportSourcesCsv:
    """Tests for import sources CSV parsing."""

    def test_parses_import_sources_file(self) -> None:
        """Parses import sources CSV into records."""
        csv_content = """Source,Country,Commodity_Count,Map_Class
MCS2025,China,12,10 or more
MCS2025,Australia,6,4 to 6
"""
        with TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "MCS2025_Fig3_Major_Import_Sources.csv"
            csv_path.write_text(csv_content)

            records = parse_import_sources_csv(csv_path)

        assert len(records) == 2
        china = [r for r in records if r.country == "China"][0]
        assert china.commodity_count == 12
        assert china.map_class == "10 or more"


@pytest.mark.unit
class TestDiscoverCommodityFiles:
    """Tests for commodity file discovery."""

    def test_discovers_files_in_commodities_dir(self) -> None:
        """Discovers files in commodities subdirectory."""
        with TemporaryDirectory() as tmpdir:
            materials_dir = Path(tmpdir)
            commodities_dir = materials_dir / "commodities"
            commodities_dir.mkdir()

            (commodities_dir / "mcs2025-lithium_salient.csv").write_text("")
            (commodities_dir / "mcs2025-copper_salient.csv").write_text("")

            files = discover_commodity_files(materials_dir)

        assert len(files) == 2
        filenames = [f.name for f in files]
        assert "mcs2025-lithium_salient.csv" in filenames
        assert "mcs2025-copper_salient.csv" in filenames

    def test_returns_empty_for_missing_dir(self) -> None:
        """Returns empty list for non-existent directory."""
        files = discover_commodity_files(Path("/nonexistent/dir"))
        assert files == []

    def test_deduplicates_across_directories(self) -> None:
        """Deduplicates files present in both commodities/ and minerals/."""
        with TemporaryDirectory() as tmpdir:
            materials_dir = Path(tmpdir)

            # Same file in both directories
            commodities_dir = materials_dir / "commodities"
            commodities_dir.mkdir()
            (commodities_dir / "mcs2025-lithium_salient.csv").write_text("commodities")

            minerals_dir = materials_dir / "minerals"
            minerals_dir.mkdir()
            (minerals_dir / "mcs2025-lithium_salient.csv").write_text("minerals")

            files = discover_commodity_files(materials_dir)

        assert len(files) == 1
        # Should prefer commodities/ over minerals/
        assert "commodities" in str(files[0])


@pytest.mark.unit
class TestDiscoverAggregateFiles:
    """Tests for aggregate file discovery."""

    def test_discovers_aggregate_files(self) -> None:
        """Discovers trends, states, and import sources files."""
        with TemporaryDirectory() as tmpdir:
            materials_dir = Path(tmpdir)

            (materials_dir / "MCS2025_T1_Mineral_Industry_Trends.csv").write_text("")
            (materials_dir / "MCS2025_T3_State_Value_Rank.csv").write_text("")
            (materials_dir / "MCS2025_Fig3_Major_Import_Sources.csv").write_text("")

            result = discover_aggregate_files(materials_dir)

        assert result["trends"] is not None
        assert result["states"] is not None
        assert result["import_sources"] is not None

    def test_returns_none_for_missing_files(self) -> None:
        """Returns None for missing aggregate files."""
        with TemporaryDirectory() as tmpdir:
            materials_dir = Path(tmpdir)
            result = discover_aggregate_files(materials_dir)

        assert result["trends"] is None
        assert result["states"] is None
        assert result["import_sources"] is None

    def test_returns_empty_dict_for_missing_dir(self) -> None:
        """Returns dict with None values for non-existent directory."""
        result = discover_aggregate_files(Path("/nonexistent/dir"))
        assert result["trends"] is None
        assert result["states"] is None


@pytest.mark.unit
class TestMaterialsWithFixture:
    """Tests using shared materials fixtures."""

    def test_parse_fixture_row(self, sample_materials_row: dict[str, str]) -> None:
        """Creates record from fixture data."""
        value, value_text = parse_value(sample_materials_row["USprod_Primary_kt"])

        record = CommodityRecord(
            commodity_code="lithium",
            commodity_name=sample_materials_row["Commodity"],
            metric_code="USprod_Primary_kt",
            metric_name="US Primary Production (kt)",
            year=int(sample_materials_row["Year"]),
            value=value,
            value_text=value_text,
        )

        assert record.commodity_name == "Lithium"
        assert record.year == 2023
        assert record.value == 920.0
