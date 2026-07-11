"""Tests for R8 → R7 aggregation and terrain classification (Feature 036-R8, Tasks 3-4).

TDD RED/GREEN: Tests for classify_r8_terrain, aggregate_terrain,
aggregate_utility_coverage, and aggregate_infrastructure_routing.
"""

from __future__ import annotations

import h3
import pytest


class TestClassifyR8Terrain:
    """Validate R8 terrain classification from water polygons."""

    def _get_r8_cells(self) -> list:
        """Generate R8 cells for a single R7 hex."""
        from babylon.domain.geography.r8_mesh import generate_r8_mesh

        r7_hex = h3.latlng_to_cell(42.3314, -83.0458, 7)
        return generate_r8_mesh({r7_hex}, {r7_hex: "26163"})

    def test_no_water_all_land(self) -> None:
        """With no water polygons, all cells remain LAND."""
        from babylon.domain.geography.r8_mesh import classify_r8_terrain

        r8_cells = self._get_r8_cells()
        result = classify_r8_terrain(r8_cells, [])

        for cell in result:
            assert cell.terrain_type == "LAND"
            assert cell.water_fraction == 0.0

    def test_water_polygon_classifies_water(self) -> None:
        """A large water polygon covering an R8 cell classifies it as WATER."""
        from shapely.geometry import Polygon  # type: ignore[import-untyped]

        from babylon.domain.geography.r8_mesh import classify_r8_terrain

        r8_cells = self._get_r8_cells()
        target_cell = r8_cells[0]

        # Create a massive polygon that fully covers the target cell
        boundary = h3.cell_to_boundary(target_cell.h3_index)
        lats = [lat for lat, _lon in boundary]
        lons = [lon for _lat, lon in boundary]
        # Expand to 10x the cell size to guarantee full coverage
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        big_polygon = Polygon(
            [
                (center_lon - 0.1, center_lat - 0.1),
                (center_lon + 0.1, center_lat - 0.1),
                (center_lon + 0.1, center_lat + 0.1),
                (center_lon - 0.1, center_lat + 0.1),
            ]
        )

        result = classify_r8_terrain(r8_cells, [big_polygon])

        # At least the target cell should be WATER
        water_cells = [c for c in result if c.terrain_type == "WATER"]
        assert len(water_cells) > 0

    def test_water_cells_utilities_false(self) -> None:
        """WATER cells must have all utility flags set to False."""
        from shapely.geometry import Polygon  # type: ignore[import-untyped]

        from babylon.domain.geography.r8_mesh import classify_r8_terrain

        r8_cells = self._get_r8_cells()
        target_cell = r8_cells[0]

        boundary = h3.cell_to_boundary(target_cell.h3_index)
        lats = [lat for lat, _ in boundary]
        lons = [lon for _, lon in boundary]
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        big_polygon = Polygon(
            [
                (center_lon - 0.1, center_lat - 0.1),
                (center_lon + 0.1, center_lat - 0.1),
                (center_lon + 0.1, center_lat + 0.1),
                (center_lon - 0.1, center_lat + 0.1),
            ]
        )

        result = classify_r8_terrain(r8_cells, [big_polygon])
        water_cells = [c for c in result if c.terrain_type == "WATER"]

        for cell in water_cells:
            assert cell.has_water_service is False
            assert cell.has_sewer is False
            assert cell.has_electric is False
            assert cell.has_gas is False
            assert cell.has_broadband is False

    def test_preserves_cell_count(self) -> None:
        """Classification does not add or remove cells."""
        from shapely.geometry import Polygon  # type: ignore[import-untyped]

        from babylon.domain.geography.r8_mesh import classify_r8_terrain

        r8_cells = self._get_r8_cells()

        boundary = h3.cell_to_boundary(r8_cells[0].h3_index)
        lats = [lat for lat, _ in boundary]
        lons = [lon for _, lon in boundary]
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        small_polygon = Polygon(
            [
                (center_lon - 0.001, center_lat - 0.001),
                (center_lon + 0.001, center_lat - 0.001),
                (center_lon + 0.001, center_lat + 0.001),
                (center_lon - 0.001, center_lat + 0.001),
            ]
        )

        result = classify_r8_terrain(r8_cells, [small_polygon])
        assert len(result) == len(r8_cells)


class TestAggregateTerrainR8ToR7:
    """Validate R8 → R7 terrain aggregation."""

    def test_all_land_children_produce_land_parent(self) -> None:
        """A R7 hex with all LAND R8 children is classified as LAND."""
        from babylon.domain.geography.r8_aggregation import aggregate_terrain
        from babylon.domain.geography.r8_mesh import generate_r8_mesh

        r7_hex = h3.latlng_to_cell(42.3314, -83.0458, 7)
        r8_cells = generate_r8_mesh({r7_hex}, {r7_hex: "26163"})

        result = aggregate_terrain(r8_cells)
        assert r7_hex in result
        tc = result[r7_hex]
        assert tc.terrain_type == "LAND"
        assert tc.water_coverage_fraction == 0.0

    def test_majority_water_produces_water_parent(self) -> None:
        """R7 hex with >50% WATER children is classified as WATER."""
        from babylon.domain.geography.r8_aggregation import aggregate_terrain
        from babylon.domain.geography.r8_mesh import generate_r8_mesh
        from babylon.domain.geography.r8_types import HexR8State

        r7_hex = h3.latlng_to_cell(42.3314, -83.0458, 7)
        r8_cells = generate_r8_mesh({r7_hex}, {r7_hex: "26163"})

        # Make 4 of 7 children WATER (majority)
        modified: list[HexR8State] = []
        for i, cell in enumerate(r8_cells):
            if i < 4:
                modified.append(
                    HexR8State(
                        h3_index=cell.h3_index,
                        parent_h3=cell.parent_h3,
                        county_fips=cell.county_fips,
                        terrain_type="WATER",
                        water_fraction=1.0,
                        elevation_m=None,
                        has_water_service=False,
                        has_sewer=False,
                        has_electric=False,
                        has_gas=False,
                        has_broadband=False,
                    )
                )
            else:
                modified.append(cell)

        result = aggregate_terrain(modified)
        tc = result[r7_hex]
        assert tc.terrain_type == "WATER"
        assert tc.water_coverage_fraction == pytest.approx(4.0 / 7.0)

    def test_minority_water_stays_land(self) -> None:
        """R7 hex with <50% WATER children stays LAND."""
        from babylon.domain.geography.r8_aggregation import aggregate_terrain
        from babylon.domain.geography.r8_mesh import generate_r8_mesh
        from babylon.domain.geography.r8_types import HexR8State

        r7_hex = h3.latlng_to_cell(42.3314, -83.0458, 7)
        r8_cells = generate_r8_mesh({r7_hex}, {r7_hex: "26163"})

        # Make 3 of 7 children WATER (minority)
        modified: list[HexR8State] = []
        for i, cell in enumerate(r8_cells):
            if i < 3:
                modified.append(
                    HexR8State(
                        h3_index=cell.h3_index,
                        parent_h3=cell.parent_h3,
                        county_fips=cell.county_fips,
                        terrain_type="WATER",
                        water_fraction=1.0,
                        elevation_m=None,
                        has_water_service=False,
                        has_sewer=False,
                        has_electric=False,
                        has_gas=False,
                        has_broadband=False,
                    )
                )
            else:
                modified.append(cell)

        result = aggregate_terrain(modified)
        tc = result[r7_hex]
        assert tc.terrain_type == "LAND"
        assert tc.water_coverage_fraction == pytest.approx(3.0 / 7.0)


class TestAggregateUtilityCoverage:
    """Validate R8 → R7 utility coverage aggregation."""

    def test_full_coverage_all_true(self) -> None:
        """All LAND children with service → 1.0 coverage."""
        from babylon.domain.geography.r8_aggregation import aggregate_utility_coverage
        from babylon.domain.geography.r8_mesh import generate_r8_mesh

        r7_hex = h3.latlng_to_cell(42.3314, -83.0458, 7)
        r8_cells = generate_r8_mesh({r7_hex}, {r7_hex: "26163"})

        result = aggregate_utility_coverage(r8_cells)
        assert r7_hex in result
        for utility in ("water_service", "sewer", "electric", "gas", "broadband"):
            assert result[r7_hex][utility] == pytest.approx(1.0)

    def test_partial_coverage(self) -> None:
        """Some LAND children without service → partial coverage fraction."""
        from babylon.domain.geography.r8_aggregation import aggregate_utility_coverage
        from babylon.domain.geography.r8_mesh import generate_r8_mesh
        from babylon.domain.geography.r8_types import HexR8State

        r7_hex = h3.latlng_to_cell(42.3314, -83.0458, 7)
        r8_cells = generate_r8_mesh({r7_hex}, {r7_hex: "26163"})

        # Remove water service from 2 of 7 LAND children
        modified: list[HexR8State] = []
        for i, cell in enumerate(r8_cells):
            if i < 2:
                modified.append(
                    HexR8State(
                        h3_index=cell.h3_index,
                        parent_h3=cell.parent_h3,
                        county_fips=cell.county_fips,
                        terrain_type="LAND",
                        water_fraction=0.0,
                        elevation_m=None,
                        has_water_service=False,
                        has_sewer=True,
                        has_electric=True,
                        has_gas=True,
                        has_broadband=True,
                    )
                )
            else:
                modified.append(cell)

        result = aggregate_utility_coverage(modified)
        assert result[r7_hex]["water_service"] == pytest.approx(5.0 / 7.0)
        assert result[r7_hex]["sewer"] == pytest.approx(1.0)

    def test_water_cells_excluded_from_denominator(self) -> None:
        """WATER cells should not count in the utility coverage denominator."""
        from babylon.domain.geography.r8_aggregation import aggregate_utility_coverage
        from babylon.domain.geography.r8_mesh import generate_r8_mesh
        from babylon.domain.geography.r8_types import HexR8State

        r7_hex = h3.latlng_to_cell(42.3314, -83.0458, 7)
        r8_cells = generate_r8_mesh({r7_hex}, {r7_hex: "26163"})

        # Make 2 cells WATER (utility False), rest LAND with full service
        modified: list[HexR8State] = []
        for i, cell in enumerate(r8_cells):
            if i < 2:
                modified.append(
                    HexR8State(
                        h3_index=cell.h3_index,
                        parent_h3=cell.parent_h3,
                        county_fips=cell.county_fips,
                        terrain_type="WATER",
                        water_fraction=1.0,
                        elevation_m=None,
                        has_water_service=False,
                        has_sewer=False,
                        has_electric=False,
                        has_gas=False,
                        has_broadband=False,
                    )
                )
            else:
                modified.append(cell)

        result = aggregate_utility_coverage(modified)
        # WATER cells excluded: 5 LAND children all with service → 1.0
        assert result[r7_hex]["water_service"] == pytest.approx(1.0)


class TestAggregateInfrastructureRouting:
    """Validate R8 linear feature → R7 edge routing."""

    def test_feature_crossing_r7_boundary(self) -> None:
        """Feature crossing from one R7 parent's R8 cell to another's
        should appear in the R7 edge results."""
        from babylon.domain.geography.r8_aggregation import aggregate_infrastructure_routing
        from babylon.domain.geography.r8_mesh import generate_r8_mesh
        from babylon.domain.geography.r8_types import R8LinearFeature

        # Use two adjacent R7 hexes
        r7_a = h3.latlng_to_cell(42.3314, -83.0458, 7)
        neighbors = set(h3.grid_disk(r7_a, 1)) - {r7_a}
        r7_b = sorted(neighbors)[0]

        r7_indices = {r7_a, r7_b}
        county_map = {r7_a: "26163", r7_b: "26163"}
        r8_cells = generate_r8_mesh(r7_indices, county_map)

        # Build a feature that crosses from an R8 child of r7_a
        # to an R8 child of r7_b
        r8_in_a = [c for c in r8_cells if c.parent_h3 == r7_a][0]
        r8_in_b = [c for c in r8_cells if c.parent_h3 == r7_b][0]

        features = [
            R8LinearFeature(
                h3_index=r8_in_a.h3_index,
                feature_type="HIGHWAY",
                feature_name="I-75",
                source_dataset="NE_10M_ROADS",
                source_feature_id="1",
            ),
            R8LinearFeature(
                h3_index=r8_in_b.h3_index,
                feature_type="HIGHWAY",
                feature_name="I-75",
                source_dataset="NE_10M_ROADS",
                source_feature_id="1",
            ),
        ]

        result = aggregate_infrastructure_routing(features, r8_cells)

        # The edge should be canonically ordered
        edge_key = tuple(sorted([r7_a, r7_b]))
        assert edge_key in result
        assert len(result[edge_key]) > 0

    def test_feature_within_single_r7_no_crossing(self) -> None:
        """Features staying within a single R7 parent produce no edge crossings."""
        from babylon.domain.geography.r8_aggregation import aggregate_infrastructure_routing
        from babylon.domain.geography.r8_mesh import generate_r8_mesh
        from babylon.domain.geography.r8_types import R8LinearFeature

        r7_hex = h3.latlng_to_cell(42.3314, -83.0458, 7)
        r8_cells = generate_r8_mesh({r7_hex}, {r7_hex: "26163"})

        # All features within same R7 parent
        features = [
            R8LinearFeature(
                h3_index=r8_cells[0].h3_index,
                feature_type="RAIL",
                feature_name="CSX",
                source_dataset="NE_10M_RAILROADS",
                source_feature_id="2",
            ),
            R8LinearFeature(
                h3_index=r8_cells[1].h3_index,
                feature_type="RAIL",
                feature_name="CSX",
                source_dataset="NE_10M_RAILROADS",
                source_feature_id="2",
            ),
        ]

        result = aggregate_infrastructure_routing(features, r8_cells)

        # No R7 edges crossed
        assert len(result) == 0
