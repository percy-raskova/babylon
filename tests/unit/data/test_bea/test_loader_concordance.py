"""Unit tests for BEA-NAICS concordance loader.

Tests the BEAConcordanceLoader class for:
- NAICS code expansion from various formats
- Industry name normalization
- Bridge table population
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from babylon.data.bea.loader_concordance import (
    BEAConcordanceLoader,
    expand_naics_codes,
    normalize_industry_name,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class TestNAICSCodeExpansion:
    """Test NAICS code string expansion."""

    def test_single_code(self) -> None:
        """Single code returns list with one element."""
        codes = expand_naics_codes("1112")
        assert codes == ["1112"]

    def test_range_pattern(self) -> None:
        """Range pattern expands to all codes in range."""
        codes = expand_naics_codes("11111-2")
        assert codes == ["11111", "11112"]

    def test_range_pattern_multiple_digits(self) -> None:
        """Range with multiple ending digits expands correctly."""
        codes = expand_naics_codes("11113-6")
        assert codes == ["11113", "11114", "11115", "11116"]

    def test_comma_separated(self) -> None:
        """Comma-separated codes return multiple codes."""
        codes = expand_naics_codes("11111, 11119")
        assert "11111" in codes
        assert "11119" in codes

    def test_mixed_range_and_codes(self) -> None:
        """Mixed ranges and codes expand correctly."""
        codes = expand_naics_codes("11113-6, 11119")
        assert "11113" in codes
        assert "11114" in codes
        assert "11115" in codes
        assert "11116" in codes
        assert "11119" in codes

    def test_empty_string(self) -> None:
        """Empty string returns empty list."""
        codes = expand_naics_codes("")
        assert codes == []

    def test_none_equivalent(self) -> None:
        """None or whitespace returns empty list."""
        assert expand_naics_codes("   ") == []

    def test_numeric_code(self) -> None:
        """Handles numeric input (from Excel as int)."""
        codes = expand_naics_codes("1112")
        assert codes == ["1112"]


class TestIndustryNameNormalization:
    """Test industry name normalization for matching."""

    def test_lowercase(self) -> None:
        """Names should be lowercased."""
        normalized = normalize_industry_name("Agriculture")
        assert normalized == "agriculture"

    def test_strip_whitespace(self) -> None:
        """Leading/trailing whitespace should be stripped."""
        normalized = normalize_industry_name("  Farms  ")
        assert normalized == "farms"

    def test_reduce_internal_whitespace(self) -> None:
        """Multiple internal spaces should be reduced to one."""
        normalized = normalize_industry_name("Oil  and   gas   extraction")
        assert normalized == "oil and gas extraction"

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        normalized = normalize_industry_name("")
        assert normalized == ""


class TestLoaderStructure:
    """Test loader structure and configuration."""

    def test_default_data_dir(self) -> None:
        """Should use 'data' as default data directory."""
        loader = BEAConcordanceLoader()
        assert loader.data_dir == Path("data")

    def test_custom_data_dir(self, tmp_path: Path) -> None:
        """Should accept custom data directory."""
        loader = BEAConcordanceLoader(data_dir=tmp_path)
        assert loader.data_dir == tmp_path

    def test_get_dimension_tables_empty(self) -> None:
        """Concordance loader doesn't create dimensions."""
        loader = BEAConcordanceLoader()
        assert loader.get_dimension_tables() == []

    def test_get_fact_tables(self) -> None:
        """Should declare BridgeNAICSBEA as fact table."""
        from babylon.data.normalize.schema import BridgeNAICSBEA

        loader = BEAConcordanceLoader()
        tables = loader.get_fact_tables()
        assert BridgeNAICSBEA in tables


@pytest.mark.integration
class TestActualFileLoading:
    """Integration tests against actual concordance file.

    These tests require:
    - The concordance file to exist
    - DimBEAIndustry to be populated (from BEANationalLoader)
    - DimIndustry to be populated (from CensusLoader or similar)
    """

    @pytest.fixture
    def session(self) -> Session:
        """Get a database session."""
        from babylon.data.normalize.database import get_normalized_session_factory

        session_factory = get_normalized_session_factory()
        return session_factory()

    @pytest.fixture
    def loader(self) -> BEAConcordanceLoader:
        """Create loader with actual data directory."""
        return BEAConcordanceLoader(data_dir=Path("data"))

    def test_concordance_file_exists(self, loader: BEAConcordanceLoader) -> None:
        """Concordance file should exist."""
        filepath = (
            loader.data_dir
            / "concordance/BEA-Industry-and-Commodity-Codes-and-NAICS-Concordance.xlsx"
        )
        assert filepath.exists()

    def test_load_creates_bridge_records(
        self, session: Session, loader: BEAConcordanceLoader
    ) -> None:
        """Should create bridge records if dependencies exist."""
        from sqlalchemy import text

        # Check if prerequisites exist
        bea_count = session.execute(text("SELECT COUNT(*) FROM dim_bea_industry")).scalar()
        naics_count = session.execute(text("SELECT COUNT(*) FROM dim_industry")).scalar()

        if bea_count == 0 or naics_count == 0:
            pytest.skip("Prerequisites (DimBEAIndustry, DimIndustry) not loaded")

        stats = loader.load(session, reset=True, verbose=False)

        # Should have created some mappings
        bridge_count = session.execute(text("SELECT COUNT(*) FROM bridge_naics_bea")).scalar()
        assert bridge_count > 0
        assert stats.facts_loaded.get("bridge_naics_bea", 0) == bridge_count
