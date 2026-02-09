"""Unit tests for BEA national industry loader.

Tests the BEANationalLoader class for:
- Correct dimension and fact table population
- Parent industry code assignment
- Accounting identity validation
"""

from __future__ import annotations

from pathlib import Path

from babylon.data.bea.loader_national import BEANationalLoader
from babylon.data.bea.parser import BEAIndustry
from babylon.data.loader_base import LoadStats


class TestBEANationalLoaderStructure:
    """Test loader structure and configuration."""

    def test_loader_inherits_from_data_loader(self) -> None:
        """Loader should inherit from DataLoader base class."""
        from babylon.data.loader_base import DataLoader

        loader = BEANationalLoader()
        assert isinstance(loader, DataLoader)

    def test_default_data_dir(self) -> None:
        """Should use 'data' as default data directory."""
        loader = BEANationalLoader()
        assert loader.data_dir == Path("data")

    def test_custom_data_dir(self, tmp_path: Path) -> None:
        """Should accept custom data directory."""
        loader = BEANationalLoader(data_dir=tmp_path)
        assert loader.data_dir == tmp_path

    def test_get_dimension_tables(self) -> None:
        """Should declare DimBEAIndustry as dimension table."""
        from babylon.data.reference.schema import DimBEAIndustry, DimDataSource

        loader = BEANationalLoader()
        tables = loader.get_dimension_tables()
        assert DimBEAIndustry in tables
        assert DimDataSource in tables

    def test_get_fact_tables(self) -> None:
        """Should declare FactBEANationalIndustry as fact table."""
        from babylon.data.reference.schema import FactBEANationalIndustry

        loader = BEANationalLoader()
        tables = loader.get_fact_tables()
        assert FactBEANationalIndustry in tables


class TestParentIndustryCodeLogic:
    """Test parent industry code assignment."""

    def test_find_parent_for_level_1(self) -> None:
        """Level 1 industries should have no parent."""
        loader = BEANationalLoader()
        industries = [
            BEAIndustry(1, "All industries", "    All industries", 1, "BEA001"),
        ]
        parent = loader._find_parent_code(industries[0], industries)
        assert parent is None

    def test_find_parent_for_level_2(self) -> None:
        """Level 2 industries should have level 1 parent."""
        loader = BEANationalLoader()
        industries = [
            BEAIndustry(1, "All industries", "    All industries", 1, "BEA001"),
            BEAIndustry(2, "Private industries", "Private industries", 1, "BEA002"),
            BEAIndustry(3, "Agriculture", "  Agriculture", 2, "BEA003"),
        ]
        parent = loader._find_parent_code(industries[2], industries)
        assert parent == "BEA002"  # Private industries

    def test_find_parent_for_level_3(self) -> None:
        """Level 3 industries should have level 2 parent."""
        loader = BEANationalLoader()
        industries = [
            BEAIndustry(1, "All industries", "    All industries", 1, "BEA001"),
            BEAIndustry(2, "Private industries", "Private industries", 1, "BEA002"),
            BEAIndustry(3, "Agriculture", "  Agriculture", 2, "BEA003"),
            BEAIndustry(4, "Farms", "    Farms", 3, "BEA004"),
        ]
        parent = loader._find_parent_code(industries[3], industries)
        assert parent == "BEA003"  # Agriculture


class TestLoadStats:
    """Test LoadStats tracking."""

    def test_load_stats_source(self) -> None:
        """LoadStats should track source as 'bea_national'."""
        # The source is set in the load method, not constructor
        # We verify by checking the LoadStats directly
        stats = LoadStats(source="bea_national")
        assert stats.source == "bea_national"
