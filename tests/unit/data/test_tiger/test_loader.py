"""Unit tests for TIGER county geometry loader.

Tests the TIGERCountyLoader class for:
- Correct schema population (DimCountyGeometry)
- Centroid calculation
- Area calculation
- WKT geometry storage
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from babylon.data.tiger import TIGERCountyLoader


class TestLoaderStructure:
    """Test loader structure and configuration."""

    def test_loader_inherits_from_data_loader(self) -> None:
        """Loader should inherit from DataLoader base class."""
        from babylon.data.loader_base import DataLoader
        from babylon.data.tiger import TIGERCountyLoader

        loader = TIGERCountyLoader()
        assert isinstance(loader, DataLoader)

    def test_default_data_dir(self) -> None:
        """Should use 'data' as default data directory."""
        from babylon.data.tiger import TIGERCountyLoader

        loader = TIGERCountyLoader()
        assert loader.data_dir == Path("data")

    def test_custom_data_dir(self, tmp_path: Path) -> None:
        """Should accept custom data directory."""
        from babylon.data.tiger import TIGERCountyLoader

        loader = TIGERCountyLoader(data_dir=tmp_path)
        assert loader.data_dir == tmp_path

    def test_get_dimension_tables(self) -> None:
        """Should declare DimCountyGeometry as dimension table."""
        from babylon.data.normalize.schema import DimCountyGeometry
        from babylon.data.tiger import TIGERCountyLoader

        loader = TIGERCountyLoader()
        tables = loader.get_dimension_tables()
        assert DimCountyGeometry in tables

    def test_get_fact_tables_empty(self) -> None:
        """Geometry loader doesn't create fact tables."""
        from babylon.data.tiger import TIGERCountyLoader

        loader = TIGERCountyLoader()
        assert loader.get_fact_tables() == []


class TestCentroidCalculation:
    """Test centroid extraction from geometries."""

    def test_calculate_centroid_returns_lat_lon(self) -> None:
        """Should calculate centroid from polygon geometry."""
        from shapely.geometry import Polygon

        from babylon.data.tiger.loader import calculate_centroid

        # Simple square polygon centered at (10, 20)
        square = Polygon([(9, 19), (11, 19), (11, 21), (9, 21)])
        lat, lon = calculate_centroid(square)

        assert abs(lat - 20.0) < 0.01  # Centroid lat
        assert abs(lon - 10.0) < 0.01  # Centroid lon

    def test_calculate_centroid_multipolygon(self) -> None:
        """Should handle MultiPolygon geometries (islands)."""
        from shapely.geometry import MultiPolygon, Polygon

        from babylon.data.tiger.loader import calculate_centroid

        # Two squares
        poly1 = Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])
        poly2 = Polygon([(8, 8), (10, 8), (10, 10), (8, 10)])
        multi = MultiPolygon([poly1, poly2])

        lat, lon = calculate_centroid(multi)
        # Centroid should be between the two polygons
        assert 0 < lat < 10
        assert 0 < lon < 10


class TestAreaCalculation:
    """Test area calculation from geometries."""

    def test_calculate_area_returns_sq_km(self) -> None:
        """Should calculate area in square kilometers."""
        from shapely.geometry import Polygon

        from babylon.data.tiger.loader import calculate_area_sq_km

        # 1 degree square at equator (roughly 111km x 111km)
        # Actual area depends on projection
        square = Polygon([(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)])
        area = calculate_area_sq_km(square)

        # Should be positive and reasonable (not exact due to projection)
        assert area > 0
        assert isinstance(area, (int, float, Decimal))


class TestFIPSExtraction:
    """Test FIPS code extraction from TIGER attributes."""

    def test_extract_fips_from_geoid(self) -> None:
        """Should extract 5-digit FIPS from GEOID column."""
        from babylon.data.tiger.loader import extract_county_fips

        # TIGER GEOID format is just the 5-digit FIPS
        fips = extract_county_fips("06001")  # Alameda County, CA
        assert fips == "06001"

    def test_extract_fips_pads_with_zeros(self) -> None:
        """Should pad FIPS codes to 5 digits."""
        from babylon.data.tiger.loader import extract_county_fips

        fips = extract_county_fips("1001")  # Alabama, Autauga
        assert fips == "01001"

    def test_extract_fips_handles_string_geoid(self) -> None:
        """Should handle string GEOID values."""
        from babylon.data.tiger.loader import extract_county_fips

        fips = extract_county_fips("36001")  # Albany County, NY
        assert fips == "36001"


class TestWKTConversion:
    """Test geometry to WKT string conversion."""

    def test_geometry_to_wkt(self) -> None:
        """Should convert geometry to WKT string."""
        from shapely.geometry import Polygon

        from babylon.data.tiger.loader import geometry_to_wkt

        poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        wkt = geometry_to_wkt(poly)

        assert wkt.startswith("POLYGON")
        assert "0 0" in wkt or "0.0 0.0" in wkt

    def test_geometry_to_wkt_none_when_disabled(self) -> None:
        """Should return None when WKT storage is disabled."""
        from shapely.geometry import Polygon

        from babylon.data.tiger.loader import geometry_to_wkt

        poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        wkt = geometry_to_wkt(poly, store_wkt=False)

        assert wkt is None


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
        from babylon.data.normalize.database import get_normalized_session_factory

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
