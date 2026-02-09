"""Unit tests for H3 grid persistence loader.

Tests the H3GridLoader class for:
- H3 cell generation from county geometries
- Bridge table population
- Resolution parameter handling
"""

from __future__ import annotations


class TestLoaderStructure:
    """Test loader structure and configuration."""

    def test_loader_inherits_from_data_loader(self) -> None:
        """Loader should inherit from DataLoader base class."""
        from babylon.data.h3 import H3GridLoader
        from babylon.data.loader_base import DataLoader

        loader = H3GridLoader()
        assert isinstance(loader, DataLoader)

    def test_default_resolution(self) -> None:
        """Should use resolution 5 by default."""
        from babylon.data.h3 import H3GridLoader

        loader = H3GridLoader()
        assert loader.resolution == 5

    def test_custom_resolution(self) -> None:
        """Should accept custom resolution."""
        from babylon.data.h3 import H3GridLoader

        loader = H3GridLoader(resolution=4)
        assert loader.resolution == 4
        assert loader.resolutions == [4]

    def test_multiple_resolutions(self) -> None:
        """Should accept multiple resolutions."""
        from babylon.data.h3 import H3GridLoader

        loader = H3GridLoader(resolutions=[3, 4, 5])
        assert loader.resolutions == [3, 4, 5]
        assert loader.resolution == 3  # First resolution

    def test_resolutions_takes_precedence(self) -> None:
        """resolutions parameter should take precedence over resolution."""
        from babylon.data.h3 import H3GridLoader

        loader = H3GridLoader(resolution=6, resolutions=[3, 4])
        assert loader.resolutions == [3, 4]
        assert loader.resolution == 3

    def test_get_dimension_tables_empty(self) -> None:
        """H3 grid loader doesn't create dimensions."""
        from babylon.data.h3 import H3GridLoader

        loader = H3GridLoader()
        assert loader.get_dimension_tables() == []

    def test_get_fact_tables(self) -> None:
        """Should declare BridgeCountyH3 as fact table."""
        from babylon.data.h3 import H3GridLoader
        from babylon.data.reference.schema import BridgeCountyH3

        loader = H3GridLoader()
        tables = loader.get_fact_tables()
        assert BridgeCountyH3 in tables


class TestH3CellGeneration:
    """Test H3 cell generation from geometries."""

    def test_generate_cells_from_polygon(self) -> None:
        """Should generate H3 cells from polygon geometry."""
        from shapely.geometry import Polygon

        from babylon.data.h3.loader import generate_h3_cells

        # Small polygon (should have at least 1 cell at res 5)
        poly = Polygon([(-122.5, 37.5), (-122.0, 37.5), (-122.0, 38.0), (-122.5, 38.0)])
        cells = generate_h3_cells(poly, resolution=5)

        assert len(cells) > 0
        # All cells should be valid H3 indices
        for cell in cells:
            assert len(cell) == 15  # H3 index length

    def test_generate_cells_resolution_affects_count(self) -> None:
        """Higher resolution should generate more cells."""
        from shapely.geometry import Polygon

        from babylon.data.h3.loader import generate_h3_cells

        poly = Polygon([(-122.5, 37.5), (-122.0, 37.5), (-122.0, 38.0), (-122.5, 38.0)])

        cells_res4 = generate_h3_cells(poly, resolution=4)
        cells_res5 = generate_h3_cells(poly, resolution=5)

        # Resolution 5 should have more cells than resolution 4
        assert len(cells_res5) > len(cells_res4)


class TestCellCentroidResolution:
    """Test resolving cell centroid to county."""

    def test_cell_to_latlon(self) -> None:
        """Should convert H3 cell to lat/lon centroid."""
        import h3

        from babylon.data.h3.loader import cell_to_latlon

        # Create a cell in San Francisco area
        cell = h3.latlng_to_cell(37.77, -122.42, 5)
        lat, lon = cell_to_latlon(cell)

        # Should be close to original coordinates
        assert abs(lat - 37.77) < 1.0
        assert abs(lon - (-122.42)) < 1.0


class TestWKTPolygonParsing:
    """Test parsing WKT polygons from DimCountyGeometry."""

    def test_wkt_to_polygon(self) -> None:
        """Should parse WKT string to Shapely polygon."""
        from babylon.data.h3.loader import wkt_to_polygon

        wkt = "POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))"
        poly = wkt_to_polygon(wkt)

        assert poly is not None
        assert poly.is_valid
        assert poly.area > 0

    def test_wkt_to_polygon_none_input(self) -> None:
        """Should return None for None input."""
        from babylon.data.h3.loader import wkt_to_polygon

        result = wkt_to_polygon(None)
        assert result is None

    def test_wkt_to_polygon_empty_string(self) -> None:
        """Should return None for empty string."""
        from babylon.data.h3.loader import wkt_to_polygon

        result = wkt_to_polygon("")
        assert result is None
