"""Integration tests for TIGER county geometry loader.

Tests against actual TIGER shapefile and database.
Requires:
- The TIGER shapefile to exist at data/tiger/county/tl_2024_us_county.shp
- DimCounty to be populated (from CensusLoader)

Extracted from tests/unit/data/test_tiger/test_loader.py
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from babylon.data.tiger import TIGERCountyLoader


@pytest.mark.integration
class TestActualFileLoading:
    """Integration tests against actual TIGER shapefile.

    These tests require:
    - The TIGER shapefile to exist at data/tiger/county/tl_2024_us_county.shp
    - DimCounty to be populated (from CensusLoader)
    """

    @pytest.fixture(scope="class")
    def session_factory(self) -> Callable:
        """Get session factory."""
        from babylon.data.reference.database import get_normalized_session_factory

        return get_normalized_session_factory()

    @pytest.fixture
    def loader(self) -> TIGERCountyLoader:
        """Create loader with actual data directory."""
        from babylon.data.tiger import TIGERCountyLoader

        return TIGERCountyLoader(data_dir=Path("data"))

    def test_shapefile_exists(self, loader: TIGERCountyLoader) -> None:
        """TIGER shapefile should exist."""
        filepath = loader.data_dir / "tiger/county/tl_2024_us_county.shp"
        assert filepath.exists()

    def test_load_creates_geometry_records(
        self, session_factory: Callable, loader: TIGERCountyLoader
    ) -> None:
        """Should create geometry records for counties that exist in DimCounty."""
        from sqlalchemy import text

        with session_factory() as session:
            # Check if DimCounty is populated
            county_count = session.execute(text("SELECT COUNT(*) FROM dim_county")).scalar()

            if county_count == 0:
                pytest.skip("DimCounty not populated (requires CensusLoader)")

            # Load geometries
            stats = loader.load(session, reset=True, verbose=False)

            # Should have created geometry records
            geom_count = session.execute(text("SELECT COUNT(*) FROM dim_county_geometry")).scalar()

            assert geom_count > 0
            assert stats.dimensions_loaded.get("dim_county_geometry", 0) == geom_count

    def test_all_geometries_have_valid_centroids(
        self, session_factory: Callable, loader: TIGERCountyLoader
    ) -> None:
        """All loaded geometries should have valid lat/lon centroids."""
        from sqlalchemy import text

        with session_factory() as session:
            county_count = session.execute(text("SELECT COUNT(*) FROM dim_county")).scalar()

            if county_count == 0:
                pytest.skip("DimCounty not populated")

            # Load if not already loaded
            geom_count = session.execute(text("SELECT COUNT(*) FROM dim_county_geometry")).scalar()

            if geom_count == 0:
                loader.load(session, reset=True, verbose=False)

            # Check centroid bounds (CONUS + Alaska + Hawaii + territories)
            result = session.execute(
                text("""
                    SELECT
                        MIN(centroid_lat), MAX(centroid_lat),
                        MIN(centroid_lon), MAX(centroid_lon)
                    FROM dim_county_geometry
                """)
            ).fetchone()

            min_lat, max_lat, min_lon, max_lon = result

            # US latitude range: ~18 (Puerto Rico) to ~71 (Alaska)
            assert float(min_lat) > 17.0
            assert float(max_lat) < 72.0

            # US longitude range: ~-180 (Alaska) to ~-65 (Puerto Rico)
            assert float(min_lon) > -180.0
            assert float(max_lon) < -64.0

    def test_areas_are_positive(self, session_factory: Callable, loader: TIGERCountyLoader) -> None:
        """All areas should be positive values."""
        from sqlalchemy import text

        with session_factory() as session:
            county_count = session.execute(text("SELECT COUNT(*) FROM dim_county")).scalar()

            if county_count == 0:
                pytest.skip("DimCounty not populated")

            # Check all areas are positive
            result = session.execute(
                text("""
                    SELECT MIN(area_sq_km)
                    FROM dim_county_geometry
                    WHERE area_sq_km IS NOT NULL
                """)
            ).scalar()

            if result is not None:
                assert float(result) > 0
