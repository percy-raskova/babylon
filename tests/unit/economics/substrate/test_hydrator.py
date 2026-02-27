"""Unit tests for QCEW-to-hex hydration (T015).

Feature: 026-tri-county-economic-substrate
Date: 2026-02-26

Tests hydrate_hex_grid: county-to-hex allocation, conservation,
zero-employment handling, uniform allocation.
"""

from __future__ import annotations

import pytest

from babylon.economics.substrate.hydrator import (
    DEFAULT_COUNTY_ECONOMICS,
    hydrate_hex_grid,
)
from babylon.economics.substrate.types import (
    TRI_COUNTY_FIPS,
    HexGrid,
)

from .conftest import (
    MACOMB_HEX_IDS,
    OAKLAND_HEX_IDS,
    WAYNE_HEX_IDS,
    MockTractDemographicSource,
)


@pytest.mark.unit
class TestHydrateHexGrid:
    """Tests for hydrate_hex_grid function."""

    def test_allocates_county_totals(
        self,
        sample_hex_grid: HexGrid,
        mock_tract_source: MockTractDemographicSource,
    ) -> None:
        """Test that county totals are allocated to hexes."""
        result = hydrate_hex_grid(sample_hex_grid, tract_source=mock_tract_source)

        # All hexes should now have nonzero capital
        for h3_id, hex_state in result.hexes.items():
            assert hex_state.constant_capital > 0.0, (
                f"Hex {h3_id} has zero constant_capital after hydration"
            )
            assert hex_state.variable_capital > 0.0, (
                f"Hex {h3_id} has zero variable_capital after hydration"
            )
            assert hex_state.surplus_value > 0.0, (
                f"Hex {h3_id} has zero surplus_value after hydration"
            )

    def test_conservation_constant_capital(
        self,
        sample_hex_grid: HexGrid,
        mock_tract_source: MockTractDemographicSource,
    ) -> None:
        """Test sum(hex.c) == county_total for each county."""
        result = hydrate_hex_grid(sample_hex_grid, tract_source=mock_tract_source)

        county_hex_map = {
            "26163": WAYNE_HEX_IDS,
            "26125": OAKLAND_HEX_IDS,
            "26099": MACOMB_HEX_IDS,
        }

        for fips, hex_ids in county_hex_map.items():
            county_c = sum(result.hexes[h].constant_capital for h in hex_ids)
            expected_c = DEFAULT_COUNTY_ECONOMICS[fips]["constant_capital"]
            assert abs(county_c - expected_c) < 1e-10, (
                f"County {fips}: sum(c)={county_c} != expected {expected_c}"
            )

    def test_conservation_variable_capital(
        self,
        sample_hex_grid: HexGrid,
        mock_tract_source: MockTractDemographicSource,
    ) -> None:
        """Test sum(hex.v) == county_total for each county."""
        result = hydrate_hex_grid(sample_hex_grid, tract_source=mock_tract_source)

        county_hex_map = {
            "26163": WAYNE_HEX_IDS,
            "26125": OAKLAND_HEX_IDS,
            "26099": MACOMB_HEX_IDS,
        }

        for fips, hex_ids in county_hex_map.items():
            county_v = sum(result.hexes[h].variable_capital for h in hex_ids)
            expected_v = DEFAULT_COUNTY_ECONOMICS[fips]["variable_capital"]
            assert abs(county_v - expected_v) < 1e-10, (
                f"County {fips}: sum(v)={county_v} != expected {expected_v}"
            )

    def test_conservation_surplus_value(
        self,
        sample_hex_grid: HexGrid,
        mock_tract_source: MockTractDemographicSource,
    ) -> None:
        """Test sum(hex.s) == county_total for each county."""
        result = hydrate_hex_grid(sample_hex_grid, tract_source=mock_tract_source)

        county_hex_map = {
            "26163": WAYNE_HEX_IDS,
            "26125": OAKLAND_HEX_IDS,
            "26099": MACOMB_HEX_IDS,
        }

        for fips, hex_ids in county_hex_map.items():
            county_s = sum(result.hexes[h].surplus_value for h in hex_ids)
            expected_s = DEFAULT_COUNTY_ECONOMICS[fips]["surplus_value"]
            assert abs(county_s - expected_s) < 1e-10, (
                f"County {fips}: sum(s)={county_s} != expected {expected_s}"
            )

    def test_uniform_allocation_without_tract_source(
        self,
        sample_hex_grid: HexGrid,
    ) -> None:
        """Test uniform allocation when no tract source provided."""
        result = hydrate_hex_grid(sample_hex_grid, tract_source=None)

        # Wayne County: 3 hexes, uniform allocation -> each gets 1/3
        wayne_c_total = DEFAULT_COUNTY_ECONOMICS["26163"]["constant_capital"]
        expected_per_hex = wayne_c_total / 3.0

        for h3_id in WAYNE_HEX_IDS:
            assert result.hexes[h3_id].constant_capital == pytest.approx(expected_per_hex)

    def test_uniform_conservation(
        self,
        sample_hex_grid: HexGrid,
    ) -> None:
        """Test conservation holds under uniform allocation."""
        result = hydrate_hex_grid(sample_hex_grid, tract_source=None)

        for fips in TRI_COUNTY_FIPS:
            hex_ids = sample_hex_grid.county_hex_ids[fips]
            county_c = sum(result.hexes[h].constant_capital for h in hex_ids)
            expected_c = DEFAULT_COUNTY_ECONOMICS[fips]["constant_capital"]
            assert abs(county_c - expected_c) < 1e-10

    def test_dept_shares_set_from_county(
        self,
        sample_hex_grid: HexGrid,
    ) -> None:
        """Test that dept_shares are set from county-level data."""
        result = hydrate_hex_grid(sample_hex_grid, tract_source=None)

        # Wayne County dept_shares from DEFAULT_COUNTY_ECONOMICS
        expected = (0.20, 0.35, 0.25, 0.20)
        for h3_id in WAYNE_HEX_IDS:
            assert result.hexes[h3_id].dept_shares == expected

        # Macomb County
        expected_macomb = (0.35, 0.25, 0.20, 0.20)
        for h3_id in MACOMB_HEX_IDS:
            assert result.hexes[h3_id].dept_shares == expected_macomb

    def test_employment_allocated(
        self,
        sample_hex_grid: HexGrid,
    ) -> None:
        """Test that employment is allocated to hexes."""
        result = hydrate_hex_grid(sample_hex_grid, tract_source=None)

        for fips in TRI_COUNTY_FIPS:
            hex_ids = sample_hex_grid.county_hex_ids[fips]
            county_emp = sum(result.hexes[h].employment for h in hex_ids)
            expected_emp = DEFAULT_COUNTY_ECONOMICS[fips]["employment"]
            assert abs(county_emp - expected_emp) < 1e-10

    def test_hex_count_preserved(
        self,
        sample_hex_grid: HexGrid,
    ) -> None:
        """Test that hydration does not add or remove hexes."""
        result = hydrate_hex_grid(sample_hex_grid, tract_source=None)
        assert len(result.hexes) == len(sample_hex_grid.hexes)
        assert set(result.hexes.keys()) == set(sample_hex_grid.hexes.keys())

    def test_resolution_hierarchy_preserved(
        self,
        sample_hex_grid: HexGrid,
    ) -> None:
        """Test that hydration preserves resolution hierarchy."""
        result = hydrate_hex_grid(sample_hex_grid, tract_source=None)
        assert result.res6_parents == sample_hex_grid.res6_parents
        assert result.res5_parents == sample_hex_grid.res5_parents
        assert result.res6_children == sample_hex_grid.res6_children
        assert result.res5_children == sample_hex_grid.res5_children

    def test_county_hex_ids_preserved(
        self,
        sample_hex_grid: HexGrid,
    ) -> None:
        """Test that hydration preserves county-to-hex mapping."""
        result = hydrate_hex_grid(sample_hex_grid, tract_source=None)
        assert result.county_hex_ids == sample_hex_grid.county_hex_ids
