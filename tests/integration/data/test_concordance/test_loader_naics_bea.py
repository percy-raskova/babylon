"""Integration tests for NAICS-BEA concordance loader.

Tests against actual database with concordance data.
Requires:
- DimIndustry to be populated (from QCEWLoader)
- DimBEAIndustry to be populated (from BEANationalLoader)
- Concordance Excel file in data/concordance/

Extracted from tests/unit/data/test_concordance/test_loader_naics_bea.py
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from babylon.data.concordance import NAICSBEAConcordanceLoader


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
