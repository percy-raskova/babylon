"""Tests for R8 mesh generation (Feature 036-R8, Task 2).

TDD RED phase: Tests for generate_r8_mesh function.
"""

from __future__ import annotations

import h3


class TestGenerateR8Mesh:
    """Validate R8 mesh generation from R7 hex indices."""

    def _get_tri_county_r7_sample(self) -> tuple[set[str], dict[str, str]]:
        """Get a small sample of R7 hexes with county assignments.

        Uses 3 R7 hexes—one from each tri-county.
        """
        # Detroit downtown area (Wayne)
        wayne_hex = h3.latlng_to_cell(42.3314, -83.0458, 7)
        # Troy area (Oakland)
        oakland_hex = h3.latlng_to_cell(42.6064, -83.1498, 7)
        # Sterling Heights (Macomb)
        macomb_hex = h3.latlng_to_cell(42.5803, -83.0302, 7)

        r7_indices = {wayne_hex, oakland_hex, macomb_hex}
        county_map = {
            wayne_hex: "26163",
            oakland_hex: "26125",
            macomb_hex: "26099",
        }
        return r7_indices, county_map

    def test_each_r7_produces_7_children(self) -> None:
        """Every R7 hex must produce exactly 7 R8 children."""
        from babylon.domain.geography.r8_mesh import generate_r8_mesh

        r7_indices, county_map = self._get_tri_county_r7_sample()
        r8_cells = generate_r8_mesh(r7_indices, county_map)

        # 3 R7 hexes * 7 children = 21 R8 cells
        assert len(r8_cells) == 21

    def test_parent_consistency(self) -> None:
        """h3.cell_to_parent(r8, 7) must equal parent_h3 for all cells."""
        from babylon.domain.geography.r8_mesh import generate_r8_mesh

        r7_indices, county_map = self._get_tri_county_r7_sample()
        r8_cells = generate_r8_mesh(r7_indices, county_map)

        for cell in r8_cells:
            computed_parent = h3.cell_to_parent(cell.h3_index, 7)
            assert cell.parent_h3 == computed_parent, (
                f"R8 cell {cell.h3_index} has parent_h3={cell.parent_h3} "
                f"but cell_to_parent gives {computed_parent}"
            )

    def test_all_children_are_resolution_8(self) -> None:
        """All generated cells must be at H3 resolution 8."""
        from babylon.domain.geography.r8_mesh import generate_r8_mesh

        r7_indices, county_map = self._get_tri_county_r7_sample()
        r8_cells = generate_r8_mesh(r7_indices, county_map)

        for cell in r8_cells:
            assert h3.get_resolution(cell.h3_index) == 8

    def test_county_inheritance(self) -> None:
        """All children inherit their parent's county_fips."""
        from babylon.domain.geography.r8_mesh import generate_r8_mesh

        r7_indices, county_map = self._get_tri_county_r7_sample()
        r8_cells = generate_r8_mesh(r7_indices, county_map)

        for cell in r8_cells:
            parent = cell.parent_h3
            expected_fips = county_map[parent]
            assert cell.county_fips == expected_fips

    def test_default_terrain_is_land(self) -> None:
        """All cells default to terrain_type=LAND."""
        from babylon.domain.geography.r8_mesh import generate_r8_mesh

        r7_indices, county_map = self._get_tri_county_r7_sample()
        r8_cells = generate_r8_mesh(r7_indices, county_map)

        for cell in r8_cells:
            assert cell.terrain_type == "LAND"

    def test_default_utilities_true(self) -> None:
        """All cells default to all utility flags True."""
        from babylon.domain.geography.r8_mesh import generate_r8_mesh

        r7_indices, county_map = self._get_tri_county_r7_sample()
        r8_cells = generate_r8_mesh(r7_indices, county_map)

        for cell in r8_cells:
            assert cell.has_water_service is True
            assert cell.has_sewer is True
            assert cell.has_electric is True
            assert cell.has_gas is True
            assert cell.has_broadband is True

    def test_elevation_stub_is_none(self) -> None:
        """All cells have elevation_m=None (stub)."""
        from babylon.domain.geography.r8_mesh import generate_r8_mesh

        r7_indices, county_map = self._get_tri_county_r7_sample()
        r8_cells = generate_r8_mesh(r7_indices, county_map)

        for cell in r8_cells:
            assert cell.elevation_m is None

    def test_no_duplicate_r8_indices(self) -> None:
        """All R8 cell indices must be unique."""
        from babylon.domain.geography.r8_mesh import generate_r8_mesh

        r7_indices, county_map = self._get_tri_county_r7_sample()
        r8_cells = generate_r8_mesh(r7_indices, county_map)

        indices = [cell.h3_index for cell in r8_cells]
        assert len(indices) == len(set(indices))

    def test_empty_input(self) -> None:
        """Empty input produces empty output."""
        from babylon.domain.geography.r8_mesh import generate_r8_mesh

        r8_cells = generate_r8_mesh(set(), {})
        assert r8_cells == []
