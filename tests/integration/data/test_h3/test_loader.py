"""Integration tests for H3 grid persistence loader.

Tests against actual database with county geometries.
Requires:
- DimCounty to be populated (from CensusLoader)
- DimCountyGeometry to be populated (from TIGERCountyLoader)

Extracted from tests/unit/data/test_h3/test_loader.py
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from babylon.data.h3 import H3GridLoader


@pytest.mark.integration
class TestActualDatabaseLoading:
    """Integration tests against actual database.

    These tests require:
    - DimCounty to be populated (from CensusLoader)
    - DimCountyGeometry to be populated (from TIGERCountyLoader)
    """

    @pytest.fixture(scope="class")
    def session_factory(self) -> Callable:
        """Get session factory."""
        from babylon.data.reference.database import get_normalized_session_factory

        return get_normalized_session_factory()

    @pytest.fixture
    def loader(self) -> H3GridLoader:
        """Create loader with default resolution."""
        from babylon.data.h3 import H3GridLoader

        return H3GridLoader(resolution=5)

    def test_load_creates_h3_records(self, session_factory: Callable, loader: H3GridLoader) -> None:
        """Should create H3 bridge records."""
        from sqlalchemy import text

        with session_factory() as session:
            # Check prerequisites
            geom_count = session.execute(text("SELECT COUNT(*) FROM dim_county_geometry")).scalar()

            if geom_count == 0:
                pytest.skip("DimCountyGeometry not populated (requires TIGERCountyLoader)")

            # Load H3 grid
            stats = loader.load(session, reset=True, verbose=False)

            # Should have created H3 records
            h3_count = session.execute(text("SELECT COUNT(*) FROM bridge_county_h3")).scalar()

            assert h3_count > 0
            assert stats.facts_loaded.get("bridge_county_h3", 0) == h3_count

    def test_all_h3_cells_have_valid_county(
        self, session_factory: Callable, loader: H3GridLoader
    ) -> None:
        """All H3 cells should reference valid counties."""
        from sqlalchemy import text

        with session_factory() as session:
            geom_count = session.execute(text("SELECT COUNT(*) FROM dim_county_geometry")).scalar()

            if geom_count == 0:
                pytest.skip("DimCountyGeometry not populated")

            # Check FK integrity
            result = session.execute(
                text("""
                    SELECT COUNT(*)
                    FROM bridge_county_h3 h
                    LEFT JOIN dim_county c ON h.county_id = c.county_id
                    WHERE c.county_id IS NULL
                """)
            ).scalar()

            assert result == 0

    def test_resolution_matches_loader(
        self, session_factory: Callable, loader: H3GridLoader
    ) -> None:
        """All records should have the loader's resolution."""
        from sqlalchemy import text

        with session_factory() as session:
            geom_count = session.execute(text("SELECT COUNT(*) FROM dim_county_geometry")).scalar()

            if geom_count == 0:
                pytest.skip("DimCountyGeometry not populated")

            # Check all resolutions match the loader's configured resolutions
            result = session.execute(
                text("SELECT DISTINCT resolution FROM bridge_county_h3")
            ).fetchall()

            if result:
                db_resolutions = {r[0] for r in result}
                expected_resolutions = set(loader.resolutions)
                assert db_resolutions == expected_resolutions
