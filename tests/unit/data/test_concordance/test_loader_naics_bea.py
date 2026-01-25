"""Unit tests for NAICS-BEA concordance loader.

Tests the NAICSBEAConcordanceLoader class for:
- NAICS code pattern expansion (ranges, lists)
- Concordance parsing from Excel files
- Bridge record creation
- Error handling for missing prerequisites
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from babylon.data.concordance import NAICSBEAConcordanceLoader


class TestNAICSCodeExpansion:
    """Test NAICS code pattern expansion."""

    def test_expand_single_code(self) -> None:
        """Should return single code as-is."""
        from babylon.data.concordance import expand_naics_codes

        result = expand_naics_codes("1112")
        assert result == ["1112"]

    def test_expand_simple_range(self) -> None:
        """Should expand range like '11111-2' to ['11111', '11112']."""
        from babylon.data.concordance import expand_naics_codes

        result = expand_naics_codes("11111-2")
        assert result == ["11111", "11112"]

    def test_expand_longer_range(self) -> None:
        """Should expand range like '11113-6' to 4 codes."""
        from babylon.data.concordance import expand_naics_codes

        result = expand_naics_codes("11113-6")
        assert result == ["11113", "11114", "11115", "11116"]

    def test_expand_comma_separated(self) -> None:
        """Should split comma-separated codes."""
        from babylon.data.concordance import expand_naics_codes

        result = expand_naics_codes("1112, 1113, 1114")
        assert result == ["1112", "1113", "1114"]

    def test_expand_mixed_ranges_and_codes(self) -> None:
        """Should handle mix of ranges and single codes."""
        from babylon.data.concordance import expand_naics_codes

        result = expand_naics_codes("1122, 1124-5, 1129")
        assert result == ["1122", "1124", "1125", "1129"]

    def test_expand_complex_pattern(self) -> None:
        """Should handle complex multi-range patterns."""
        from babylon.data.concordance import expand_naics_codes

        result = expand_naics_codes("11113-6, 11119")
        assert result == ["11113", "11114", "11115", "11116", "11119"]

    def test_expand_none_value(self) -> None:
        """Should return empty list for None."""
        from babylon.data.concordance import expand_naics_codes

        result = expand_naics_codes(None)
        assert result == []

    def test_expand_empty_string(self) -> None:
        """Should return empty list for empty string."""
        from babylon.data.concordance import expand_naics_codes

        result = expand_naics_codes("")
        assert result == []

    def test_expand_whitespace_only(self) -> None:
        """Should return empty list for whitespace-only string."""
        from babylon.data.concordance import expand_naics_codes

        result = expand_naics_codes("   ")
        assert result == []

    def test_expand_preserves_leading_zeros(self) -> None:
        """Should preserve leading zeros in expanded codes."""
        from babylon.data.concordance import expand_naics_codes

        # Range where suffix determines padding
        result = expand_naics_codes("11110-2")
        assert result == ["11110", "11111", "11112"]


class TestLoaderStructure:
    """Test loader structure and configuration."""

    def test_loader_inherits_from_data_loader(self) -> None:
        """Loader should inherit from DataLoader base class."""
        from babylon.data.concordance import NAICSBEAConcordanceLoader
        from babylon.data.loader_base import DataLoader

        loader = NAICSBEAConcordanceLoader()
        assert isinstance(loader, DataLoader)

    def test_default_data_dir(self) -> None:
        """Should use 'data' as default data directory."""
        from babylon.data.concordance import NAICSBEAConcordanceLoader

        loader = NAICSBEAConcordanceLoader()
        assert loader.data_dir == Path("data")

    def test_custom_data_dir(self, tmp_path: Path) -> None:
        """Should accept custom data directory."""
        from babylon.data.concordance import NAICSBEAConcordanceLoader

        loader = NAICSBEAConcordanceLoader(data_dir=tmp_path)
        assert loader.data_dir == tmp_path

    def test_get_dimension_tables_empty(self) -> None:
        """Concordance loader doesn't create dimensions."""
        from babylon.data.concordance import NAICSBEAConcordanceLoader

        loader = NAICSBEAConcordanceLoader()
        assert loader.get_dimension_tables() == []

    def test_get_fact_tables_empty(self) -> None:
        """Concordance loader creates bridge, not facts."""
        from babylon.data.concordance import NAICSBEAConcordanceLoader

        loader = NAICSBEAConcordanceLoader()
        assert loader.get_fact_tables() == []


class TestLoaderPrerequisites:
    """Test loader prerequisite checking."""

    def test_fails_when_dim_industry_empty(self) -> None:
        """Should fail with error when DimIndustry is empty."""
        from babylon.data.concordance import NAICSBEAConcordanceLoader

        loader = NAICSBEAConcordanceLoader()

        mock_session = MagicMock()
        # DimIndustry count returns 0
        mock_session.query.return_value.count.side_effect = [0, 100]

        stats = loader.load(mock_session, verbose=False)

        assert len(stats.errors) > 0
        assert "DimIndustry is empty" in stats.errors[0]

    def test_fails_when_dim_bea_industry_empty(self) -> None:
        """Should fail with error when DimBEAIndustry is empty."""
        from babylon.data.concordance import NAICSBEAConcordanceLoader

        loader = NAICSBEAConcordanceLoader()

        mock_session = MagicMock()
        # DimIndustry count returns 100, DimBEAIndustry returns 0
        mock_session.query.return_value.count.side_effect = [100, 0]

        stats = loader.load(mock_session, verbose=False)

        assert len(stats.errors) > 0
        assert "DimBEAIndustry is empty" in stats.errors[0]

    def test_fails_when_concordance_file_missing(self, tmp_path: Path) -> None:
        """Should fail with error when concordance file not found."""
        from babylon.data.concordance import NAICSBEAConcordanceLoader

        # Create loader with tmp_path that has no concordance file
        loader = NAICSBEAConcordanceLoader(data_dir=tmp_path)

        mock_session = MagicMock()
        # Both dimensions have data
        mock_session.query.return_value.count.side_effect = [100, 100]

        stats = loader.load(mock_session, verbose=False)

        assert len(stats.errors) > 0
        assert "Concordance file not found" in stats.errors[0]


class TestCacheBuilding:
    """Test cache building methods."""

    def test_build_bea_name_cache(self) -> None:
        """Should build BEA name -> (id, line_number) cache."""
        from babylon.data.concordance import NAICSBEAConcordanceLoader

        loader = NAICSBEAConcordanceLoader()

        mock_session = MagicMock()
        mock_session.query.return_value.all.return_value = [
            (701, "All industries", 1),
            (704, "Farms", 4),
            (710, "Utilities", 10),
        ]

        cache = loader._build_bea_name_cache(mock_session)

        assert "all industries" in cache
        assert cache["all industries"] == (701, 1)
        assert "farms" in cache
        assert cache["farms"] == (704, 4)
        assert "utilities" in cache
        assert cache["utilities"] == (710, 10)

    def test_build_naics_cache(self) -> None:
        """Should build NAICS code -> industry_id cache."""
        from babylon.data.concordance import NAICSBEAConcordanceLoader

        loader = NAICSBEAConcordanceLoader()

        mock_session = MagicMock()
        mock_session.query.return_value.all.return_value = [
            (1, "11"),
            (2, "1111"),
            (3, "11111"),
        ]

        cache = loader._build_naics_cache(mock_session)

        assert cache["11"] == 1
        assert cache["1111"] == 2
        assert cache["11111"] == 3


@pytest.mark.integration
class TestActualDatabaseLoading:
    """Integration tests against actual database.

    These tests require:
    - DimIndustry to be populated (from QCEWLoader)
    - DimBEAIndustry to be populated (from BEANationalLoader)
    - Concordance Excel file in data/concordance/
    """

    @pytest.fixture(scope="class")
    def session_factory(self):
        """Get session factory."""
        from babylon.data.reference.database import get_normalized_session_factory

        return get_normalized_session_factory()

    @pytest.fixture
    def loader(self) -> NAICSBEAConcordanceLoader:
        """Create loader."""
        from babylon.data.concordance import NAICSBEAConcordanceLoader

        return NAICSBEAConcordanceLoader()

    def test_load_creates_bridge_records(
        self, session_factory, loader: NAICSBEAConcordanceLoader
    ) -> None:
        """Should create bridge records linking NAICS to BEA."""
        from pathlib import Path

        from sqlalchemy import text

        # Check prerequisites
        concordance_path = Path(
            "data/concordance/BEA-Industry-and-Commodity-Codes-and-NAICS-Concordance.xlsx"
        )
        if not concordance_path.exists():
            pytest.skip("Concordance file not available")

        with session_factory() as session:
            naics_count = session.execute(text("SELECT COUNT(*) FROM dim_industry")).scalar()
            if naics_count == 0:
                pytest.skip("DimIndustry not populated (requires QCEWLoader)")

            bea_count = session.execute(text("SELECT COUNT(*) FROM dim_bea_industry")).scalar()
            if bea_count == 0:
                pytest.skip("DimBEAIndustry not populated (requires BEANationalLoader)")

            # Load concordance
            stats = loader.load(session, reset=True, verbose=False)

            # Should have created records
            bridge_count = session.execute(text("SELECT COUNT(*) FROM bridge_naics_bea")).scalar()

            assert bridge_count > 0
            assert stats.dimensions_loaded.get("bridge_naics_bea", 0) == bridge_count
            assert len(stats.errors) == 0

    def test_all_bridge_records_have_valid_fks(
        self, session_factory, loader: NAICSBEAConcordanceLoader
    ) -> None:
        """All bridge records should reference valid dimensions."""
        from pathlib import Path

        from sqlalchemy import text

        concordance_path = Path(
            "data/concordance/BEA-Industry-and-Commodity-Codes-and-NAICS-Concordance.xlsx"
        )
        if not concordance_path.exists():
            pytest.skip("Concordance file not available")

        with session_factory() as session:
            bridge_count = session.execute(text("SELECT COUNT(*) FROM bridge_naics_bea")).scalar()
            if bridge_count == 0:
                pytest.skip("bridge_naics_bea not populated")

            # Check FK integrity for industry_id
            orphan_industry = session.execute(
                text("""
                    SELECT COUNT(*)
                    FROM bridge_naics_bea b
                    LEFT JOIN dim_industry i ON b.industry_id = i.industry_id
                    WHERE i.industry_id IS NULL
                """)
            ).scalar()
            assert orphan_industry == 0

            # Check FK integrity for bea_industry_id
            orphan_bea = session.execute(
                text("""
                    SELECT COUNT(*)
                    FROM bridge_naics_bea b
                    LEFT JOIN dim_bea_industry i ON b.bea_industry_id = i.bea_industry_id
                    WHERE i.bea_industry_id IS NULL
                """)
            ).scalar()
            assert orphan_bea == 0
