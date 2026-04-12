"""Tests for the R8 pipeline integration (Feature 036-R8, Task 6).

Wires NaturalEarthReader into the R8 mesh generation, terrain classification,
and linear feature extraction pipeline.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import h3
import pytest

# Detroit tri-county bounding box (approximate)
DETROIT_BBOX = (-83.50, 42.15, -82.80, 42.75)


@pytest.fixture()
def ne_reader() -> MagicMock:
    """Mock NaturalEarthReader for unit tests."""
    reader = MagicMock()
    reader.load_lakes.return_value = []
    reader.load_roads.return_value = []
    reader.load_railroads.return_value = []
    return reader


class TestBuildR8Substrate:
    """Validate the end-to-end R8 substrate pipeline."""

    def _get_sample_inputs(self) -> tuple[set[str], dict[str, str]]:
        """Get 3 R7 hexes from tri-county."""
        wayne = h3.latlng_to_cell(42.3314, -83.0458, 7)
        oakland = h3.latlng_to_cell(42.6064, -83.1498, 7)
        macomb = h3.latlng_to_cell(42.5803, -83.0302, 7)

        r7_indices = {wayne, oakland, macomb}
        county_map = {wayne: "26163", oakland: "26125", macomb: "26099"}
        return r7_indices, county_map

    def test_pipeline_produces_r8_cells(self, ne_reader: MagicMock) -> None:
        """Pipeline returns R8 cells for all input R7 hexes."""
        from babylon.infrastructure.r8_pipeline import build_r8_substrate

        r7_indices, county_map = self._get_sample_inputs()
        result = build_r8_substrate(r7_indices, county_map, DETROIT_BBOX, ne_reader)

        # 3 R7 hexes * 7 children = 21 R8 cells
        assert len(result.r8_cells) == 21

    def test_pipeline_classifies_water_from_lakes(self, ne_reader: MagicMock) -> None:
        """Pipeline classifies WATER when lake polygons overlap R8 cells."""
        from shapely.geometry import Polygon  # type: ignore[import-untyped]

        from babylon.infrastructure.natural_earth_reader import LakeFeature
        from babylon.infrastructure.r8_pipeline import build_r8_substrate

        r7_indices, county_map = self._get_sample_inputs()

        # Create a big lake polygon covering the Detroit hex
        wayne = h3.latlng_to_cell(42.3314, -83.0458, 7)
        wayne_children = list(h3.cell_to_children(wayne, 8))
        boundary = h3.cell_to_boundary(wayne_children[0])
        lats = [lat for lat, _ in boundary]
        lons = [lon for _, lon in boundary]
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        big_lake = Polygon(
            [
                (center_lon - 0.1, center_lat - 0.1),
                (center_lon + 0.1, center_lat - 0.1),
                (center_lon + 0.1, center_lat + 0.1),
                (center_lon - 0.1, center_lat + 0.1),
            ]
        )

        ne_reader.load_lakes.return_value = [
            LakeFeature(ogc_fid=1, name="Lake Test", scalerank=0, geometry=big_lake),
        ]

        result = build_r8_substrate(r7_indices, county_map, DETROIT_BBOX, ne_reader)
        water_cells = [c for c in result.r8_cells if c.terrain_type == "WATER"]
        assert len(water_cells) > 0

    def test_pipeline_extracts_road_features(self, ne_reader: MagicMock) -> None:
        """Pipeline converts NE road features to R8LinearFeature objects."""
        from shapely.geometry import LineString  # type: ignore[import-untyped]

        from babylon.infrastructure.natural_earth_reader import RoadFeature
        from babylon.infrastructure.r8_pipeline import build_r8_substrate

        r7_indices, county_map = self._get_sample_inputs()

        # Create a road LineString through the Wayne hex area
        road_line = LineString([(-83.10, 42.30), (-83.00, 42.35)])

        ne_reader.load_roads.return_value = [
            RoadFeature(
                ogc_fid=1,
                name="I-75",
                prefix="I",
                number="75",
                road_class="Interstate",
                road_type="Major Highway",
                expressway=1,
                scalerank=3,
                geometry=road_line,
                source_table="ne_10m_roads",
            ),
        ]

        result = build_r8_substrate(r7_indices, county_map, DETROIT_BBOX, ne_reader)
        assert len(result.r8_features) > 0

    def test_pipeline_extracts_railroad_features(self, ne_reader: MagicMock) -> None:
        """Pipeline converts NE railroad features to R8LinearFeature objects."""
        from shapely.geometry import LineString  # type: ignore[import-untyped]

        from babylon.infrastructure.natural_earth_reader import RailroadFeature
        from babylon.infrastructure.r8_pipeline import build_r8_substrate

        r7_indices, county_map = self._get_sample_inputs()

        rail_line = LineString([(-83.10, 42.30), (-83.00, 42.35)])

        ne_reader.load_railroads.return_value = [
            RailroadFeature(
                ogc_fid=1,
                name="CSX",
                scalerank=5,
                mult_track=1,
                geometry=rail_line,
                source_table="ne_10m_railroads",
            ),
        ]

        result = build_r8_substrate(r7_indices, county_map, DETROIT_BBOX, ne_reader)
        rail_features = [f for f in result.r8_features if f.feature_type == "RAIL"]
        assert len(rail_features) > 0

    def test_pipeline_maps_road_type_to_feature_type(self, ne_reader: MagicMock) -> None:
        """Major Highway maps to HIGHWAY, Secondary Highway to ARTERIAL."""
        from shapely.geometry import LineString  # type: ignore[import-untyped]

        from babylon.infrastructure.natural_earth_reader import RoadFeature
        from babylon.infrastructure.r8_pipeline import build_r8_substrate

        r7_indices, county_map = self._get_sample_inputs()

        road_line = LineString([(-83.10, 42.30), (-83.00, 42.35)])

        ne_reader.load_roads.return_value = [
            RoadFeature(
                ogc_fid=1,
                name="M-53",
                prefix="M",
                number="53",
                road_class="State",
                road_type="Secondary Highway",
                expressway=0,
                scalerank=6,
                geometry=road_line,
                source_table="ne_10m_roads",
            ),
        ]

        result = build_r8_substrate(r7_indices, county_map, DETROIT_BBOX, ne_reader)
        arterial_features = [f for f in result.r8_features if f.feature_type == "ARTERIAL"]
        assert len(arterial_features) > 0

    def test_pipeline_returns_r7_terrain(self, ne_reader: MagicMock) -> None:
        """Pipeline returns aggregated R7 terrain classifications."""
        from babylon.infrastructure.r8_pipeline import build_r8_substrate

        r7_indices, county_map = self._get_sample_inputs()
        result = build_r8_substrate(r7_indices, county_map, DETROIT_BBOX, ne_reader)

        assert len(result.r7_terrain) == 3
        for r7_hex in r7_indices:
            assert r7_hex in result.r7_terrain

    def test_pipeline_returns_r7_utility_coverage(self, ne_reader: MagicMock) -> None:
        """Pipeline returns aggregated R7 utility coverage fractions."""
        from babylon.infrastructure.r8_pipeline import build_r8_substrate

        r7_indices, county_map = self._get_sample_inputs()
        result = build_r8_substrate(r7_indices, county_map, DETROIT_BBOX, ne_reader)

        assert len(result.r7_utility_coverage) == 3
        for r7_hex in r7_indices:
            cov = result.r7_utility_coverage[r7_hex]
            for utility in ("water_service", "sewer", "electric", "gas", "broadband"):
                assert utility in cov

    def test_pipeline_no_reader_uses_default(self) -> None:
        """When no reader is provided, pipeline attempts to use the default NE database."""
        from babylon.infrastructure.r8_pipeline import build_r8_substrate

        r7_indices, county_map = self._get_sample_inputs()

        # This should work if NE database exists, skip if not
        ne_path = Path(
            "/media/user/data/babylon-data/natural-earth/packages/natural_earth_vector.sqlite"
        )
        if not ne_path.exists():
            pytest.skip("NE database not available")

        result = build_r8_substrate(r7_indices, county_map, DETROIT_BBOX)
        assert len(result.r8_cells) == 21
