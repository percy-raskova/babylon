"""Integration tests for BEA county GDP loader.

Tests against actual database with real county GDP data.
Requires:
- DimCounty to be populated (from CensusLoader)
- DimBEAIndustry to be populated (from BEANationalLoader)
- CAGDP2.zip to exist in data/bea/regional/

Extracted from tests/unit/data/test_bea/test_loader_county.py
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

    from babylon.data.bea.loader_county import BEACountyGDPLoader


@pytest.mark.integration
class TestActualDatabaseLoading:
    """Integration tests against actual database.

    These tests require:
    - DimCounty to be populated (from CensusLoader)
    - DimBEAIndustry to be populated (from BEANationalLoader)
    - CAGDP2.zip to exist in data/bea/regional/
    """

    @pytest.fixture(scope="class")
    def session_factory(self) -> Callable:
        """Get session factory."""
        from babylon.data.reference.database import get_normalized_session_factory

        return get_normalized_session_factory()

    @pytest.fixture
    def loader(self) -> BEACountyGDPLoader:
        """Create loader."""
        from babylon.data.bea.loader_county import BEACountyGDPLoader

        return BEACountyGDPLoader()

    def test_load_creates_county_gdp_records(
        self, session_factory: Callable, loader: BEACountyGDPLoader
    ) -> None:
        """Should create county GDP records."""
        from sqlalchemy import text

        # Check prerequisites
        zip_path = Path("data/bea/regional/CAGDP2.zip")
        if not zip_path.exists():
            pytest.skip("CAGDP2.zip not downloaded")

        with session_factory() as session:
            county_count = session.execute(text("SELECT COUNT(*) FROM dim_county")).scalar()
            if county_count == 0:
                pytest.skip("DimCounty not populated (requires CensusLoader)")

            industry_count = session.execute(text("SELECT COUNT(*) FROM dim_bea_industry")).scalar()
            if industry_count == 0:
                pytest.skip("DimBEAIndustry not populated (requires BEANationalLoader)")

            # Load county GDP
            stats = loader.load(session, reset=True, verbose=False)

            # Should have created records
            gdp_count = session.execute(text("SELECT COUNT(*) FROM fact_bea_county_gdp")).scalar()

            assert gdp_count > 0
            assert stats.facts_loaded.get("fact_bea_county_gdp", 0) == gdp_count

    def test_all_gdp_records_have_valid_county(
        self, session_factory: Callable, loader: BEACountyGDPLoader
    ) -> None:
        """All GDP records should reference valid counties."""
        from sqlalchemy import text

        zip_path = Path("data/bea/regional/CAGDP2.zip")
        if not zip_path.exists():
            pytest.skip("CAGDP2.zip not downloaded")

        with session_factory() as session:
            gdp_count = session.execute(text("SELECT COUNT(*) FROM fact_bea_county_gdp")).scalar()
            if gdp_count == 0:
                pytest.skip("fact_bea_county_gdp not populated")

            # Check FK integrity
            result = session.execute(
                text("""
                    SELECT COUNT(*)
                    FROM fact_bea_county_gdp g
                    LEFT JOIN dim_county c ON g.county_id = c.county_id
                    WHERE c.county_id IS NULL
                """)
            ).scalar()

            assert result == 0

    def test_all_gdp_records_have_valid_industry(
        self, session_factory: Callable, loader: BEACountyGDPLoader
    ) -> None:
        """All GDP records should reference valid industries."""
        from sqlalchemy import text

        zip_path = Path("data/bea/regional/CAGDP2.zip")
        if not zip_path.exists():
            pytest.skip("CAGDP2.zip not downloaded")

        with session_factory() as session:
            gdp_count = session.execute(text("SELECT COUNT(*) FROM fact_bea_county_gdp")).scalar()
            if gdp_count == 0:
                pytest.skip("fact_bea_county_gdp not populated")

            # Check FK integrity
            result = session.execute(
                text("""
                    SELECT COUNT(*)
                    FROM fact_bea_county_gdp g
                    LEFT JOIN dim_bea_industry i ON g.bea_industry_id = i.bea_industry_id
                    WHERE i.bea_industry_id IS NULL
                """)
            ).scalar()

            assert result == 0
