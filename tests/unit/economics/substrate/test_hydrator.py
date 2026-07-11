"""Unit tests for QCEW-to-hex hydration (T015).

Feature: 026-tri-county-economic-substrate
Date: 2026-02-26

Tests hydrate_hex_grid: county-to-hex allocation, conservation,
zero-employment handling, uniform allocation.
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.substrate.hydrator import (
    DEFAULT_COUNTY_ECONOMICS,
    hydrate_hex_grid,
)
from babylon.domain.economics.substrate.types import (
    TRI_COUNTY_FIPS,
    HexGrid,
)

from .conftest import (
    MACOMB_HEX_IDS,
    OAKLAND_HEX_IDS,
    WAYNE_HEX_IDS,
    MockMarxianHydrator,
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


@pytest.mark.unit
class TestHydrateWithMarxianHydrator:
    """Tests for hydrate_hex_grid with MarxianHydrator integration."""

    def test_marxian_hydrator_values_used(
        self,
        sample_hex_grid: HexGrid,
        mock_marxian_hydrator: MockMarxianHydrator,
    ) -> None:
        """Test that MarxianHydrator c/v/s values replace defaults."""
        result = hydrate_hex_grid(
            sample_hex_grid,
            tract_source=None,
            marxian_hydrator=mock_marxian_hydrator,
        )

        # Wayne County total c from mock: 5000 + 8000 + 6000 + 4000 = 23000
        wayne_c = sum(result.hexes[h].constant_capital for h in WAYNE_HEX_IDS)
        assert wayne_c == pytest.approx(23000.0, abs=1e-10)

        # Wayne County total v from mock: 2000 + 3500 + 2500 + 2000 = 10000
        wayne_v = sum(result.hexes[h].variable_capital for h in WAYNE_HEX_IDS)
        assert wayne_v == pytest.approx(10000.0, abs=1e-10)

        # Wayne County total s from mock: 1000 + 1500 + 1200 + 800 = 4500
        wayne_s = sum(result.hexes[h].surplus_value for h in WAYNE_HEX_IDS)
        assert wayne_s == pytest.approx(4500.0, abs=1e-10)

    def test_marxian_hydrator_differs_from_defaults(
        self,
        sample_hex_grid: HexGrid,
        mock_marxian_hydrator: MockMarxianHydrator,
    ) -> None:
        """Test that MarxianHydrator values differ from DEFAULT_COUNTY_ECONOMICS."""
        default_result = hydrate_hex_grid(sample_hex_grid, tract_source=None)
        marxian_result = hydrate_hex_grid(
            sample_hex_grid,
            tract_source=None,
            marxian_hydrator=mock_marxian_hydrator,
        )

        # Values should differ because MarxianHydrator uses different c/v/s
        wayne_c_default = sum(default_result.hexes[h].constant_capital for h in WAYNE_HEX_IDS)
        wayne_c_marxian = sum(marxian_result.hexes[h].constant_capital for h in WAYNE_HEX_IDS)
        assert wayne_c_default != pytest.approx(wayne_c_marxian)

    def test_marxian_hydrator_lower_profit_rate(
        self,
        sample_hex_grid: HexGrid,
        mock_marxian_hydrator: MockMarxianHydrator,
    ) -> None:
        """Test that MarxianHydrator produces lower profit rate than defaults."""
        default_result = hydrate_hex_grid(sample_hex_grid, tract_source=None)
        marxian_result = hydrate_hex_grid(
            sample_hex_grid,
            tract_source=None,
            marxian_hydrator=mock_marxian_hydrator,
        )

        def _metro_profit_rate(grid: HexGrid) -> float:
            total_c = sum(h.constant_capital for h in grid.hexes.values())
            total_v = sum(h.variable_capital for h in grid.hexes.values())
            total_s = sum(h.surplus_value for h in grid.hexes.values())
            return total_s / (total_c + total_v) if (total_c + total_v) > 0 else 0.0

        default_pr = _metro_profit_rate(default_result)
        marxian_pr = _metro_profit_rate(marxian_result)

        # Default profit rate ~15.8%, MarxianHydrator ~13.6%
        assert marxian_pr < default_pr

    def test_marxian_hydrator_conservation(
        self,
        sample_hex_grid: HexGrid,
        mock_marxian_hydrator: MockMarxianHydrator,
    ) -> None:
        """Test conservation holds when using MarxianHydrator."""
        result = hydrate_hex_grid(
            sample_hex_grid,
            tract_source=None,
            marxian_hydrator=mock_marxian_hydrator,
        )

        # Check all three counties
        tensor_data = MockMarxianHydrator.DEFAULT_TENSORS
        county_hex_map = {
            "26163": WAYNE_HEX_IDS,
            "26125": OAKLAND_HEX_IDS,
            "26099": MACOMB_HEX_IDS,
        }

        for fips, hex_ids in county_hex_map.items():
            depts = tensor_data[fips]
            expected_c = sum(
                float(depts[d].c) for d in ["dept_I", "dept_IIa", "dept_IIb", "dept_III"]
            )
            actual_c = sum(result.hexes[h].constant_capital for h in hex_ids)
            assert abs(actual_c - expected_c) < 1e-10, (
                f"County {fips}: sum(c)={actual_c} != expected {expected_c}"
            )

    def test_marxian_hydrator_dept_shares_from_tensor(
        self,
        sample_hex_grid: HexGrid,
        mock_marxian_hydrator: MockMarxianHydrator,
    ) -> None:
        """Test that dept_shares are computed from tensor department values."""
        result = hydrate_hex_grid(
            sample_hex_grid,
            tract_source=None,
            marxian_hydrator=mock_marxian_hydrator,
        )

        # Wayne County total value per dept:
        # I: 5000+2000+1000 = 8000, IIa: 8000+3500+1500 = 13000
        # IIb: 6000+2500+1200 = 9700, III: 4000+2000+800 = 6800
        # Total: 37500
        total_val = 37500.0
        expected_shares = (
            8000.0 / total_val,
            13000.0 / total_val,
            9700.0 / total_val,
            6800.0 / total_val,
        )

        wayne_hex = result.hexes[WAYNE_HEX_IDS[0]]
        for actual, expected in zip(wayne_hex.dept_shares, expected_shares, strict=True):
            assert actual == pytest.approx(expected, abs=1e-10)

    def test_fallback_when_hydrator_returns_zero(
        self,
        sample_hex_grid: HexGrid,
    ) -> None:
        """Test fallback to defaults when MarxianHydrator returns zero tensor."""
        from babylon.domain.economics.tensor import DepartmentRow

        # Create hydrator that returns zero for all counties
        zero_row = DepartmentRow(c=0.0, v=0.0, s=0.0)
        zero_tensors: dict[str, dict[str, DepartmentRow]] = {
            fips: {
                "dept_I": zero_row,
                "dept_IIa": zero_row,
                "dept_IIb": zero_row,
                "dept_III": zero_row,
            }
            for fips in ["26163", "26125", "26099"]
        }
        zero_hydrator = MockMarxianHydrator(tensors=zero_tensors)

        result = hydrate_hex_grid(
            sample_hex_grid,
            tract_source=None,
            marxian_hydrator=zero_hydrator,
        )

        # Should fall back to DEFAULT_COUNTY_ECONOMICS
        wayne_c = sum(result.hexes[h].constant_capital for h in WAYNE_HEX_IDS)
        assert wayne_c == pytest.approx(
            DEFAULT_COUNTY_ECONOMICS["26163"]["constant_capital"], abs=1e-10
        )
