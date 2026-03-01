"""Tests for terrain classification and biocapacity (Feature 036, T011-T016).

Uses mock NaturalEarthReader with canned Shapely polygons.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import h3
import pytest
from shapely.geometry import Polygon  # type: ignore[import-untyped]

from babylon.config.defines import InfraTerrainDefines
from babylon.infrastructure.natural_earth_reader import LakeFeature, RegionFeature
from babylon.infrastructure.terrain import DefaultBiocapacityStore, DefaultTerrainClassifier
from babylon.infrastructure.types import TerrainClassification
from babylon.models.enums import BiocapacityType, TerrainType


@pytest.fixture()
def terrain_defines() -> InfraTerrainDefines:
    """Default terrain defines."""
    return InfraTerrainDefines()


@pytest.fixture()
def detroit_center() -> str:
    """H3 cell at Detroit center, resolution 7."""
    return h3.latlng_to_cell(42.33, -83.05, 7)


def _hex_polygon(h3_index: str) -> Polygon:
    """Convert H3 cell boundary to Shapely polygon (lon/lat order)."""
    boundary = h3.cell_to_boundary(h3_index)
    return Polygon([(lon, lat) for lat, lon in boundary])


def _make_mock_reader(
    lakes: list[LakeFeature] | None = None,
    regions: list[RegionFeature] | None = None,
) -> MagicMock:
    """Create a mock NaturalEarthReader returning canned features."""
    reader = MagicMock()
    reader.load_lakes.return_value = lakes or []
    reader.load_roads.return_value = []
    reader.load_railroads.return_value = []
    reader.load_airports.return_value = []
    reader.load_ports.return_value = []
    reader.load_geography_regions.return_value = regions or []
    return reader


@pytest.mark.unit
class TestDefaultTerrainClassifier:
    """Tests for DefaultTerrainClassifier."""

    def test_land_classification_no_features(
        self,
        detroit_center: str,
        terrain_defines: InfraTerrainDefines,
    ) -> None:
        """Hex with no overlapping water/resource features is LAND."""
        reader = _make_mock_reader()
        classifier = DefaultTerrainClassifier(reader, terrain_defines)

        result = classifier.classify_hex(detroit_center)

        assert result.terrain_type == TerrainType.LAND
        assert result.water_coverage_fraction == 0.0
        assert result.resource_coverage_fraction == 0.0
        assert result.h3_index == detroit_center

    def test_water_classification_full_coverage(
        self,
        detroit_center: str,
        terrain_defines: InfraTerrainDefines,
    ) -> None:
        """Hex fully covered by lake polygon is classified WATER."""
        hex_poly = _hex_polygon(detroit_center)
        # Create a lake larger than the hex
        lake_geom = hex_poly.buffer(0.01)
        lake = LakeFeature(
            ogc_fid=1,
            name="Test Lake",
            scalerank=3,
            geometry=lake_geom,
        )
        reader = _make_mock_reader(lakes=[lake])
        classifier = DefaultTerrainClassifier(reader, terrain_defines)

        result = classifier.classify_hex(detroit_center)

        assert result.terrain_type == TerrainType.WATER
        assert result.water_coverage_fraction >= 0.5
        assert "Test Lake" in result.source_features

    def test_resource_classification(
        self,
        detroit_center: str,
        terrain_defines: InfraTerrainDefines,
    ) -> None:
        """Hex covered by resource region is classified RESOURCE."""
        hex_poly = _hex_polygon(detroit_center)
        region_geom = hex_poly.buffer(0.01)
        region = RegionFeature(
            ogc_fid=1,
            name="Test Range",
            featurecla="Range/mtn",
            scalerank=3,
            geometry=region_geom,
        )
        reader = _make_mock_reader(regions=[region])
        classifier = DefaultTerrainClassifier(reader, terrain_defines)

        result = classifier.classify_hex(detroit_center)

        assert result.terrain_type == TerrainType.RESOURCE
        assert result.resource_coverage_fraction >= 0.5
        assert "Test Range" in result.source_features

    def test_water_beats_resource_when_both_above_threshold(
        self,
        detroit_center: str,
        terrain_defines: InfraTerrainDefines,
    ) -> None:
        """WATER takes priority over RESOURCE (checked first)."""
        hex_poly = _hex_polygon(detroit_center)
        cover = hex_poly.buffer(0.01)
        lake = LakeFeature(ogc_fid=1, name="Lake", scalerank=3, geometry=cover)
        region = RegionFeature(
            ogc_fid=2,
            name="Range",
            featurecla="Range/mtn",
            scalerank=3,
            geometry=cover,
        )
        reader = _make_mock_reader(lakes=[lake], regions=[region])
        classifier = DefaultTerrainClassifier(reader, terrain_defines)

        result = classifier.classify_hex(detroit_center)
        assert result.terrain_type == TerrainType.WATER

    def test_below_threshold_is_land(
        self,
        detroit_center: str,
    ) -> None:
        """Coverage below threshold classifies as LAND (EC-001)."""
        hex_poly = _hex_polygon(detroit_center)
        # Create small lake covering ~20% of hex
        centroid = hex_poly.centroid
        small_lake = centroid.buffer(0.001)
        lake = LakeFeature(ogc_fid=1, name="Puddle", scalerank=10, geometry=small_lake)
        reader = _make_mock_reader(lakes=[lake])

        # High threshold ensures small coverage doesn't trigger WATER
        defines = InfraTerrainDefines(majority_coverage_threshold=0.8)
        classifier = DefaultTerrainClassifier(reader, defines)

        result = classifier.classify_hex(detroit_center)
        assert result.terrain_type == TerrainType.LAND
        assert result.water_coverage_fraction > 0.0
        assert result.water_coverage_fraction < 0.8

    def test_non_resource_featurecla_ignored(
        self,
        detroit_center: str,
        terrain_defines: InfraTerrainDefines,
    ) -> None:
        """Regions with non-resource featurecla don't count as resource."""
        hex_poly = _hex_polygon(detroit_center)
        cover = hex_poly.buffer(0.01)
        region = RegionFeature(
            ogc_fid=1,
            name="Plain",
            featurecla="Plain",
            scalerank=3,
            geometry=cover,
        )
        reader = _make_mock_reader(regions=[region])
        classifier = DefaultTerrainClassifier(reader, terrain_defines)

        result = classifier.classify_hex(detroit_center)
        assert result.terrain_type == TerrainType.LAND
        assert result.resource_coverage_fraction == 0.0

    def test_classify_mesh(
        self,
        terrain_defines: InfraTerrainDefines,
    ) -> None:
        """classify_mesh processes multiple hexes."""
        center = h3.latlng_to_cell(42.33, -83.05, 7)
        cells = list(h3.grid_disk(center, 1))
        reader = _make_mock_reader()
        classifier = DefaultTerrainClassifier(reader, terrain_defines)

        result = classifier.classify_mesh(cells)

        assert len(result) == len(cells)
        for cell in cells:
            assert cell in result
            assert result[cell].terrain_type == TerrainType.LAND

    def test_source_features_audit_trail(
        self,
        detroit_center: str,
        terrain_defines: InfraTerrainDefines,
    ) -> None:
        """Source features list provides audit trail."""
        hex_poly = _hex_polygon(detroit_center)
        cover = hex_poly.buffer(0.01)
        lake = LakeFeature(ogc_fid=1, name="Lake Saint Clair", scalerank=3, geometry=cover)
        reader = _make_mock_reader(lakes=[lake])
        classifier = DefaultTerrainClassifier(reader, terrain_defines)

        result = classifier.classify_hex(detroit_center)
        assert "Lake Saint Clair" in result.source_features


@pytest.mark.unit
class TestDefaultBiocapacityStore:
    """Tests for DefaultBiocapacityStore."""

    def test_initialize_water_stocks(
        self,
        terrain_defines: InfraTerrainDefines,
    ) -> None:
        """WATER hex gets FRESHWATER, FISHERY, SHIPPING_ACCESS stocks."""
        store = DefaultBiocapacityStore(terrain_defines)
        classifications = {
            "hex_water": TerrainClassification(
                h3_index="hex_water",
                terrain_type=TerrainType.WATER,
                water_coverage_fraction=0.8,
            ),
        }
        result = store.initialize_stocks(classifications)

        assert "hex_water" in result
        stock_types = {s.stock_type for s in result["hex_water"]}
        assert stock_types == {
            BiocapacityType.FRESHWATER,
            BiocapacityType.FISHERY,
            BiocapacityType.SHIPPING_ACCESS,
        }

    def test_initialize_resource_stocks(
        self,
        terrain_defines: InfraTerrainDefines,
    ) -> None:
        """RESOURCE hex gets MINERAL, TIMBER, HYDROELECTRIC stocks."""
        store = DefaultBiocapacityStore(terrain_defines)
        classifications = {
            "hex_resource": TerrainClassification(
                h3_index="hex_resource",
                terrain_type=TerrainType.RESOURCE,
                resource_coverage_fraction=0.7,
            ),
        }
        result = store.initialize_stocks(classifications)

        assert "hex_resource" in result
        stock_types = {s.stock_type for s in result["hex_resource"]}
        assert stock_types == {
            BiocapacityType.MINERAL,
            BiocapacityType.TIMBER,
            BiocapacityType.HYDROELECTRIC,
        }

    def test_land_hex_no_stocks(
        self,
        terrain_defines: InfraTerrainDefines,
    ) -> None:
        """LAND hex gets no biocapacity stocks."""
        store = DefaultBiocapacityStore(terrain_defines)
        classifications = {
            "hex_land": TerrainClassification(
                h3_index="hex_land",
                terrain_type=TerrainType.LAND,
            ),
        }
        result = store.initialize_stocks(classifications)
        assert "hex_land" not in result

    def test_get_stock_returns_dto(
        self,
        terrain_defines: InfraTerrainDefines,
    ) -> None:
        """get_stock returns current stock state."""
        store = DefaultBiocapacityStore(terrain_defines)
        classifications = {
            "hex_w": TerrainClassification(
                h3_index="hex_w",
                terrain_type=TerrainType.WATER,
                water_coverage_fraction=0.8,
            ),
        }
        store.initialize_stocks(classifications)

        stock = store.get_stock("hex_w", BiocapacityType.FRESHWATER)
        assert stock is not None
        assert stock.initial_value == terrain_defines.initial_freshwater
        assert stock.current_value == stock.initial_value
        assert not stock.depleted

    def test_get_stock_returns_none_for_missing(
        self,
        terrain_defines: InfraTerrainDefines,
    ) -> None:
        """get_stock returns None for missing hex or type."""
        store = DefaultBiocapacityStore(terrain_defines)
        assert store.get_stock("nonexistent", BiocapacityType.FRESHWATER) is None

    def test_extraction_reduces_stock(
        self,
        terrain_defines: InfraTerrainDefines,
    ) -> None:
        """Extraction reduces current_value by extracted amount (FR-007)."""
        store = DefaultBiocapacityStore(terrain_defines)
        classifications = {
            "src": TerrainClassification(
                h3_index="src",
                terrain_type=TerrainType.WATER,
                water_coverage_fraction=0.9,
            ),
        }
        store.initialize_stocks(classifications)

        result = store.extract(
            source_h3="src",
            target_h3="tgt",
            stock_type=BiocapacityType.FRESHWATER,
            infrastructure_capacity=10.0,
            depletion_rate=0.05,
        )

        expected_amount = 0.05 * terrain_defines.initial_freshwater  # 5.0
        assert result.amount_extracted == pytest.approx(expected_amount)
        assert result.remaining_stock == pytest.approx(
            terrain_defines.initial_freshwater - expected_amount
        )

    def test_extraction_capped_by_infrastructure(
        self,
        terrain_defines: InfraTerrainDefines,
    ) -> None:
        """Extraction is min(infra_cap, rate*current, current)."""
        store = DefaultBiocapacityStore(terrain_defines)
        classifications = {
            "src": TerrainClassification(
                h3_index="src",
                terrain_type=TerrainType.WATER,
                water_coverage_fraction=0.9,
            ),
        }
        store.initialize_stocks(classifications)

        # Very low infrastructure capacity
        result = store.extract(
            source_h3="src",
            target_h3="tgt",
            stock_type=BiocapacityType.FRESHWATER,
            infrastructure_capacity=1.0,
            depletion_rate=0.05,
        )

        assert result.amount_extracted == pytest.approx(1.0)
        assert result.infrastructure_constraint == 1.0

    def test_depleted_stock_zero_extraction(
        self,
        terrain_defines: InfraTerrainDefines,
    ) -> None:
        """Depleted stock yields zero extraction (FR-008)."""
        defines = InfraTerrainDefines(initial_freshwater=1.0)
        store = DefaultBiocapacityStore(defines)
        classifications = {
            "src": TerrainClassification(
                h3_index="src",
                terrain_type=TerrainType.WATER,
                water_coverage_fraction=0.9,
            ),
        }
        store.initialize_stocks(classifications)

        # Extract all stock
        store.extract("src", "tgt", BiocapacityType.FRESHWATER, 100.0, 1.0)

        # Second extraction should be zero
        result = store.extract("src", "tgt", BiocapacityType.FRESHWATER, 100.0, 1.0)
        assert result.amount_extracted == 0.0
        assert result.remaining_stock == 0.0

        stock = store.get_stock("src", BiocapacityType.FRESHWATER)
        assert stock is not None
        assert stock.depleted

    def test_depletion_history_tracked(
        self,
        terrain_defines: InfraTerrainDefines,
    ) -> None:
        """Each extraction is recorded in depletion_history."""
        store = DefaultBiocapacityStore(terrain_defines)
        classifications = {
            "src": TerrainClassification(
                h3_index="src",
                terrain_type=TerrainType.WATER,
                water_coverage_fraction=0.9,
            ),
        }
        store.initialize_stocks(classifications)

        store.extract("src", "tgt", BiocapacityType.FRESHWATER, 10.0, 0.05)
        store.extract("src", "tgt", BiocapacityType.FRESHWATER, 10.0, 0.05)

        stock = store.get_stock("src", BiocapacityType.FRESHWATER)
        assert stock is not None
        assert len(stock.depletion_history) == 2

    def test_serialization_roundtrip(
        self,
        terrain_defines: InfraTerrainDefines,
    ) -> None:
        """to_dict/from_dict preserves store state."""
        store = DefaultBiocapacityStore(terrain_defines)
        classifications = {
            "src": TerrainClassification(
                h3_index="src",
                terrain_type=TerrainType.WATER,
                water_coverage_fraction=0.9,
            ),
        }
        store.initialize_stocks(classifications)
        store.extract("src", "tgt", BiocapacityType.FRESHWATER, 5.0, 0.05)

        data = store.to_dict()
        restored = DefaultBiocapacityStore.from_dict(data, terrain_defines)

        original = store.get_stock("src", BiocapacityType.FRESHWATER)
        restored_stock = restored.get_stock("src", BiocapacityType.FRESHWATER)
        assert original is not None
        assert restored_stock is not None
        assert restored_stock.current_value == pytest.approx(original.current_value)
        assert len(restored_stock.depletion_history) == len(original.depletion_history)
