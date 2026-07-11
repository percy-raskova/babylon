"""Unit tests for spatial substrate source (T011).

Feature: 026-tri-county-economic-substrate
Date: 2026-02-26

Tests MockSpatialSubstrateSource: hex generation, county assignment,
resolution hierarchy. Real geometry tests are not possible without
a database, so we test via the mock.
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.substrate.types import (
    TRI_COUNTY_FIPS,
)

from .conftest import (
    MACOMB_HEX_IDS,
    OAKLAND_HEX_IDS,
    WAYNE_HEX_IDS,
    MockSpatialSubstrateSource,
)


@pytest.mark.unit
class TestMockSpatialSubstrateSource:
    """Tests for MockSpatialSubstrateSource generating hex meshes."""

    def test_generates_nine_hexes(
        self,
        mock_spatial_source: MockSpatialSubstrateSource,
    ) -> None:
        """Test that mock source generates 9 hexes (3 per county)."""
        grid = mock_spatial_source.generate_hex_mesh(
            county_fips_list=["26163", "26125", "26099"],
        )
        assert len(grid.hexes) == 9

    def test_every_hex_assigned_to_one_county(
        self,
        mock_spatial_source: MockSpatialSubstrateSource,
    ) -> None:
        """Test that every hex is assigned to exactly one county."""
        grid = mock_spatial_source.generate_hex_mesh(
            county_fips_list=["26163", "26125", "26099"],
        )

        # Collect all hex IDs across all counties
        all_assigned: set[str] = set()
        for _fips, hex_ids in grid.county_hex_ids.items():
            # Verify no overlap with previously assigned hexes
            overlap = all_assigned & hex_ids
            assert len(overlap) == 0, f"Hex IDs {overlap} assigned to multiple counties"
            all_assigned |= hex_ids

        # Every hex in the grid should be assigned
        assert all_assigned == set(grid.hexes.keys())

    def test_hex_county_fips_matches_assignment(
        self,
        mock_spatial_source: MockSpatialSubstrateSource,
    ) -> None:
        """Test that hex.county_fips matches its county_hex_ids assignment."""
        grid = mock_spatial_source.generate_hex_mesh(
            county_fips_list=["26163", "26125", "26099"],
        )

        for fips, hex_ids in grid.county_hex_ids.items():
            for h3_id in hex_ids:
                assert grid.hexes[h3_id].county_fips == fips, (
                    f"Hex {h3_id} county_fips={grid.hexes[h3_id].county_fips} "
                    f"but assigned to county {fips}"
                )

    def test_resolution_hierarchy_built(
        self,
        mock_spatial_source: MockSpatialSubstrateSource,
    ) -> None:
        """Test that resolution hierarchy maps are built correctly."""
        grid = mock_spatial_source.generate_hex_mesh(
            county_fips_list=["26163", "26125", "26099"],
        )

        # Every r7 hex should have a r6 and r5 parent
        for h3_id in grid.hexes:
            assert h3_id in grid.res6_parents, f"Hex {h3_id} has no r6 parent"
            assert h3_id in grid.res5_parents, f"Hex {h3_id} has no r5 parent"

    def test_county_hex_ids_keys_match_fips(
        self,
        mock_spatial_source: MockSpatialSubstrateSource,
    ) -> None:
        """Test that county_hex_ids keys match requested FIPS codes."""
        grid = mock_spatial_source.generate_hex_mesh(
            county_fips_list=["26163", "26125", "26099"],
        )

        assert set(grid.county_hex_ids.keys()) == {"26163", "26125", "26099"}

    def test_wayne_hexes(
        self,
        mock_spatial_source: MockSpatialSubstrateSource,
    ) -> None:
        """Test Wayne County hex IDs match expected values."""
        grid = mock_spatial_source.generate_hex_mesh(
            county_fips_list=["26163", "26125", "26099"],
        )
        assert grid.county_hex_ids["26163"] == frozenset(WAYNE_HEX_IDS)

    def test_oakland_hexes(
        self,
        mock_spatial_source: MockSpatialSubstrateSource,
    ) -> None:
        """Test Oakland County hex IDs match expected values."""
        grid = mock_spatial_source.generate_hex_mesh(
            county_fips_list=["26163", "26125", "26099"],
        )
        assert grid.county_hex_ids["26125"] == frozenset(OAKLAND_HEX_IDS)

    def test_macomb_hexes(
        self,
        mock_spatial_source: MockSpatialSubstrateSource,
    ) -> None:
        """Test Macomb County hex IDs match expected values."""
        grid = mock_spatial_source.generate_hex_mesh(
            county_fips_list=["26163", "26125", "26099"],
        )
        assert grid.county_hex_ids["26099"] == frozenset(MACOMB_HEX_IDS)

    def test_r6_children_inversion(
        self,
        mock_spatial_source: MockSpatialSubstrateSource,
    ) -> None:
        """Test r6 children map is inverse of r6 parents map."""
        grid = mock_spatial_source.generate_hex_mesh(
            county_fips_list=["26163", "26125", "26099"],
        )

        # Rebuild children from parents and verify
        for parent_id, child_ids in grid.res6_children.items():
            for child_id in child_ids:
                assert grid.res6_parents[child_id] == parent_id

    def test_r5_children_inversion(
        self,
        mock_spatial_source: MockSpatialSubstrateSource,
    ) -> None:
        """Test r5 children map is inverse of r5 parents map."""
        grid = mock_spatial_source.generate_hex_mesh(
            county_fips_list=["26163", "26125", "26099"],
        )

        for parent_id, child_ids in grid.res5_children.items():
            for child_id in child_ids:
                assert grid.res5_parents[child_id] == parent_id

    def test_single_county_mesh(self) -> None:
        """Test generating mesh for only one county."""
        source = MockSpatialSubstrateSource()
        grid = source.generate_hex_mesh(county_fips_list=["26163"])

        assert len(grid.hexes) == 3
        assert set(grid.county_hex_ids.keys()) == {"26163"}

    def test_hexes_initialized_with_zero_capital(
        self,
        mock_spatial_source: MockSpatialSubstrateSource,
    ) -> None:
        """Test that generated hexes start with zero economic values."""
        grid = mock_spatial_source.generate_hex_mesh(
            county_fips_list=["26163", "26125", "26099"],
        )

        for hex_state in grid.hexes.values():
            assert hex_state.constant_capital == 0.0
            assert hex_state.variable_capital == 0.0
            assert hex_state.surplus_value == 0.0
            assert hex_state.employment == 0.0

    def test_get_county_boundary_returns_none(
        self,
        mock_spatial_source: MockSpatialSubstrateSource,
    ) -> None:
        """Test that mock get_county_boundary returns None."""
        result = mock_spatial_source.get_county_boundary("26163")
        assert result is None

    def test_tri_county_fips_constant(self) -> None:
        """Test TRI_COUNTY_FIPS contains the expected counties."""
        assert frozenset({"26163", "26125", "26099"}) == TRI_COUNTY_FIPS
