"""Unit tests for CFSLoader.

Tests loader initialization, SCTG categorization, and disaggregation logic
with mocked database sessions.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from babylon.data.cfs.loader import CFSLoader
from babylon.data.loader_base import LoaderConfig
from babylon.data.normalize.schema import DimSCTGCommodity, FactCommodityFlow


@pytest.mark.unit
class TestCFSLoaderInit:
    """Tests for loader initialization."""

    def test_init_with_default_config(self) -> None:
        """Loader initializes with default LoaderConfig."""
        loader = CFSLoader()
        assert loader.config is not None
        assert loader.config.census_years == list(range(2009, 2024))

    def test_init_with_custom_config(self) -> None:
        """Loader accepts custom LoaderConfig."""
        config = LoaderConfig(census_years=[2017])
        loader = CFSLoader(config)
        assert loader.config.census_years == [2017]


@pytest.mark.unit
class TestCFSLoaderTables:
    """Tests for table declarations."""

    def test_get_dimension_tables_returns_sctg(self) -> None:
        """get_dimension_tables returns DimSCTGCommodity."""
        loader = CFSLoader()
        tables = loader.get_dimension_tables()
        assert DimSCTGCommodity in tables

    def test_get_fact_tables_returns_commodity_flow(self) -> None:
        """get_fact_tables returns FactCommodityFlow."""
        loader = CFSLoader()
        tables = loader.get_fact_tables()
        assert FactCommodityFlow in tables


@pytest.mark.unit
class TestSCTGCategorization:
    """Tests for SCTG category determination."""

    def test_agriculture_codes(self) -> None:
        """Codes 01-09 are agriculture."""
        loader = CFSLoader()
        for code in ["01", "02", "03", "04", "05", "06", "07", "08", "09"]:
            assert loader._get_sctg_category(code) == "agriculture"

    def test_mining_codes(self) -> None:
        """Codes 10-19 are mining."""
        loader = CFSLoader()
        for code in ["10", "11", "12", "13", "14", "15", "16", "17", "18", "19"]:
            assert loader._get_sctg_category(code) == "mining"

    def test_chemicals_codes(self) -> None:
        """Codes 20-30 are chemicals."""
        loader = CFSLoader()
        for code in ["20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30"]:
            assert loader._get_sctg_category(code) == "chemicals"

    def test_manufacturing_codes(self) -> None:
        """Codes 31-40 are manufacturing."""
        loader = CFSLoader()
        for code in ["31", "32", "33", "34", "35", "36", "37", "38", "39", "40"]:
            assert loader._get_sctg_category(code) == "manufacturing"

    def test_other_codes(self) -> None:
        """Codes 41+ are other."""
        loader = CFSLoader()
        for code in ["41", "43"]:
            assert loader._get_sctg_category(code) == "other"


@pytest.mark.unit
class TestStrategicValueAssignment:
    """Tests for strategic value determination."""

    def test_critical_energy_commodities(self) -> None:
        """Energy commodities are critical."""
        loader = CFSLoader()
        critical_codes = ["15", "16", "17", "18", "19"]  # Coal, oil, gas
        for code in critical_codes:
            assert loader._get_strategic_value(code) == "critical"

    def test_critical_industrial_commodities(self) -> None:
        """Base metals and chemicals are critical."""
        loader = CFSLoader()
        assert loader._get_strategic_value("20") == "critical"  # Basic chemicals
        assert loader._get_strategic_value("32") == "critical"  # Base metals

    def test_high_value_food_commodities(self) -> None:
        """Food commodities are high value."""
        loader = CFSLoader()
        assert loader._get_strategic_value("02") == "high"  # Grains
        assert loader._get_strategic_value("05") == "high"  # Meat
        assert loader._get_strategic_value("07") == "high"  # Prepared foods

    def test_high_value_industrial_commodities(self) -> None:
        """Machinery and electronics are high value."""
        loader = CFSLoader()
        assert loader._get_strategic_value("34") == "high"  # Machinery
        assert loader._get_strategic_value("35") == "high"  # Electronics
        assert loader._get_strategic_value("36") == "high"  # Vehicles

    def test_default_medium_value(self) -> None:
        """Other commodities default to medium value."""
        loader = CFSLoader()
        medium_codes = ["01", "03", "10", "25", "29", "39", "41"]
        for code in medium_codes:
            assert loader._get_strategic_value(code) == "medium"


@pytest.mark.unit
class TestLoadStatsReporting:
    """Tests for LoadStats reporting."""

    def test_load_stats_reports_source(self) -> None:
        """LoadStats reports 'cfs' as source."""
        loader = CFSLoader()

        # Create a mock session that returns no hierarchy
        mock_session = MagicMock()
        mock_session.execute.return_value = []
        mock_session.query.return_value.filter.return_value.delete.return_value = 0

        stats = loader.load(mock_session, verbose=False)

        assert stats.source == "cfs"

    def test_load_reports_error_without_hierarchy(self) -> None:
        """LoadStats reports error when no hierarchy data found."""
        loader = CFSLoader()

        mock_session = MagicMock()
        mock_session.execute.return_value = []
        mock_session.query.return_value.filter.return_value.delete.return_value = 0

        stats = loader.load(mock_session, verbose=False)

        assert stats.has_errors
        assert "geographic hierarchy" in stats.errors[0].lower()


@pytest.mark.unit
class TestFactCommodityFlowRecord:
    """Tests for FactCommodityFlow record creation."""

    def test_fact_record_has_required_fields(self) -> None:
        """FactCommodityFlow can be instantiated with required fields."""
        fact = FactCommodityFlow(
            origin_county_id=101,
            dest_county_id=201,
            sctg_id=1,
            source_id=1,
            year=2022,
        )

        assert fact.origin_county_id == 101
        assert fact.dest_county_id == 201
        assert fact.sctg_id == 1
        assert fact.year == 2022

    def test_fact_record_accepts_flow_values(self) -> None:
        """FactCommodityFlow accepts value, tons, and tmiles."""
        fact = FactCommodityFlow(
            origin_county_id=101,
            dest_county_id=201,
            sctg_id=1,
            source_id=1,
            year=2022,
            value_millions=Decimal("150.50"),
            tons_thousands=Decimal("250.00"),
            ton_miles_millions=Decimal("1500.00"),
        )

        assert fact.value_millions == Decimal("150.50")
        assert fact.tons_thousands == Decimal("250.00")
        assert fact.ton_miles_millions == Decimal("1500.00")


@pytest.mark.unit
class TestDimSCTGCommodityRecord:
    """Tests for DimSCTGCommodity record creation."""

    def test_sctg_record_has_required_fields(self) -> None:
        """DimSCTGCommodity can be instantiated with required fields."""
        sctg = DimSCTGCommodity(
            sctg_code="02",
            sctg_name="Cereal grains",
        )

        assert sctg.sctg_code == "02"
        assert sctg.sctg_name == "Cereal grains"

    def test_sctg_record_accepts_optional_fields(self) -> None:
        """DimSCTGCommodity accepts category and strategic_value."""
        sctg = DimSCTGCommodity(
            sctg_code="16",
            sctg_name="Crude petroleum",
            category="mining",
            strategic_value="critical",
        )

        assert sctg.category == "mining"
        assert sctg.strategic_value == "critical"
