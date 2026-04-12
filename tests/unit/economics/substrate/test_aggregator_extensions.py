"""Unit tests for ResolutionAggregator extensions (hex-to-graph bridge).

RED phase: Tests for new DefaultResolutionAggregator methods:
- compute_weighted_exploitation_rate
- compute_weighted_organic_composition
- compute_employment
- compute_component_capitals
- compute_dept_share_weighted

Feature: hex-substrate-graph-bridge
"""

from __future__ import annotations

import pytest

from babylon.economics.substrate.aggregation import DefaultResolutionAggregator
from babylon.economics.substrate.types import HexGrid


@pytest.mark.unit
class TestAggregatorExploitationRate:
    """Tests for compute_weighted_exploitation_rate."""

    def test_exploitation_rate_r6(self, hydrated_hex_grid: HexGrid) -> None:
        """Capital-weighted exploitation rate Σs/Σv at R6."""
        aggregator = DefaultResolutionAggregator()
        rates = aggregator.compute_weighted_exploitation_rate(
            hydrated_hex_grid,
            target_resolution=6,
        )

        assert len(rates) == 3

        # Verify by manual calculation for each parent
        for parent_id, rate in rates.items():
            child_ids = hydrated_hex_grid.res6_children[parent_id]
            total_s = sum(
                hydrated_hex_grid.hexes[cid].surplus_value
                for cid in child_ids
                if cid in hydrated_hex_grid.hexes
            )
            total_v = sum(
                hydrated_hex_grid.hexes[cid].variable_capital
                for cid in child_ids
                if cid in hydrated_hex_grid.hexes
            )
            expected = total_s / total_v if total_v > 0 else 0.0
            assert rate == pytest.approx(expected)

    def test_exploitation_rate_zero_variable(self) -> None:
        """Exploitation rate is 0.0 when variable capital is zero."""
        from babylon.economics.substrate.types import HexEconomicState

        hexes = {
            "872830828ffffff": HexEconomicState(
                h3_index="872830828ffffff",
                county_fips="26163",
                constant_capital=100.0,
                variable_capital=0.0,
                surplus_value=0.0,
                employment=0.0,
                dept_shares=(0.25, 0.25, 0.25, 0.25),
            ),
        }
        grid = HexGrid(
            hexes=hexes,
            county_hex_ids={"26163": frozenset(["872830828ffffff"])},
            res6_parents={"872830828ffffff": "8626163ffffff"},
            res5_parents={"872830828ffffff": "8526163fffffff"},
            res6_children={"8626163ffffff": frozenset(["872830828ffffff"])},
            res5_children={"8526163fffffff": frozenset(["872830828ffffff"])},
        )

        aggregator = DefaultResolutionAggregator()
        rates = aggregator.compute_weighted_exploitation_rate(grid, target_resolution=6)
        assert rates["8626163ffffff"] == pytest.approx(0.0)


@pytest.mark.unit
class TestAggregatorOrganicComposition:
    """Tests for compute_weighted_organic_composition."""

    def test_organic_composition_r6(self, hydrated_hex_grid: HexGrid) -> None:
        """Capital-weighted organic composition Σc/Σv at R6."""
        aggregator = DefaultResolutionAggregator()
        occs = aggregator.compute_weighted_organic_composition(
            hydrated_hex_grid,
            target_resolution=6,
        )

        assert len(occs) == 3

        for parent_id, occ in occs.items():
            child_ids = hydrated_hex_grid.res6_children[parent_id]
            total_c = sum(
                hydrated_hex_grid.hexes[cid].constant_capital
                for cid in child_ids
                if cid in hydrated_hex_grid.hexes
            )
            total_v = sum(
                hydrated_hex_grid.hexes[cid].variable_capital
                for cid in child_ids
                if cid in hydrated_hex_grid.hexes
            )
            expected = total_c / total_v if total_v > 0 else 0.0
            assert occ == pytest.approx(expected)


@pytest.mark.unit
class TestAggregatorEmployment:
    """Tests for compute_employment."""

    def test_employment_r6(self, hydrated_hex_grid: HexGrid) -> None:
        """Sum employment at R6."""
        aggregator = DefaultResolutionAggregator()
        emp = aggregator.compute_employment(
            hydrated_hex_grid,
            target_resolution=6,
        )

        assert len(emp) == 3

        for parent_id, total_emp in emp.items():
            child_ids = hydrated_hex_grid.res6_children[parent_id]
            expected = sum(
                hydrated_hex_grid.hexes[cid].employment
                for cid in child_ids
                if cid in hydrated_hex_grid.hexes
            )
            assert total_emp == pytest.approx(expected)

    def test_employment_conservation(self, hydrated_hex_grid: HexGrid) -> None:
        """Total employment at R6 equals sum of all R7 hexes."""
        aggregator = DefaultResolutionAggregator()
        emp = aggregator.compute_employment(hydrated_hex_grid, target_resolution=6)

        total_r7 = sum(h.employment for h in hydrated_hex_grid.hexes.values())
        total_r6 = sum(emp.values())
        assert total_r6 == pytest.approx(total_r7)


@pytest.mark.unit
class TestAggregatorComponentCapitals:
    """Tests for compute_component_capitals."""

    def test_component_capitals_r6(self, hydrated_hex_grid: HexGrid) -> None:
        """Individual c, v, s sums at R6."""
        aggregator = DefaultResolutionAggregator()
        components = aggregator.compute_component_capitals(
            hydrated_hex_grid,
            target_resolution=6,
        )

        assert len(components) == 3

        for parent_id, (c, v, s) in components.items():
            child_ids = hydrated_hex_grid.res6_children[parent_id]
            exp_c = sum(
                hydrated_hex_grid.hexes[cid].constant_capital
                for cid in child_ids
                if cid in hydrated_hex_grid.hexes
            )
            exp_v = sum(
                hydrated_hex_grid.hexes[cid].variable_capital
                for cid in child_ids
                if cid in hydrated_hex_grid.hexes
            )
            exp_s = sum(
                hydrated_hex_grid.hexes[cid].surplus_value
                for cid in child_ids
                if cid in hydrated_hex_grid.hexes
            )
            assert c == pytest.approx(exp_c)
            assert v == pytest.approx(exp_v)
            assert s == pytest.approx(exp_s)

    def test_conservation_via_components(self, hydrated_hex_grid: HexGrid) -> None:
        """c + v + s at R6 equals total capital from aggregate()."""
        aggregator = DefaultResolutionAggregator()
        components = aggregator.compute_component_capitals(
            hydrated_hex_grid,
            target_resolution=6,
        )
        totals = aggregator.aggregate(hydrated_hex_grid, target_resolution=6)

        for parent_id in totals:
            c, v, s = components[parent_id]
            assert c + v + s == pytest.approx(totals[parent_id])


@pytest.mark.unit
class TestAggregatorDeptShareWeighted:
    """Tests for compute_dept_share_weighted."""

    def test_dept_shares_r6(self, hydrated_hex_grid: HexGrid) -> None:
        """Employment-weighted department shares at R6."""
        aggregator = DefaultResolutionAggregator()
        shares = aggregator.compute_dept_share_weighted(
            hydrated_hex_grid,
            target_resolution=6,
        )

        assert len(shares) == 3

        for _parent_id, dept_shares in shares.items():
            assert len(dept_shares) == 4
            # Shares must sum to 1.0 (within tolerance)
            assert sum(dept_shares) == pytest.approx(1.0, abs=1e-10)
            # All shares non-negative
            for share in dept_shares:
                assert share >= 0.0

    def test_dept_shares_manual_calculation(self, hydrated_hex_grid: HexGrid) -> None:
        """Verify employment-weighted shares match manual calculation."""
        aggregator = DefaultResolutionAggregator()
        shares = aggregator.compute_dept_share_weighted(
            hydrated_hex_grid,
            target_resolution=6,
        )

        # Manual for Wayne (R6 parent "8626163ffffff")
        wayne_parent = "8626163ffffff"
        child_ids = hydrated_hex_grid.res6_children[wayne_parent]

        total_emp = 0.0
        weighted_shares = [0.0, 0.0, 0.0, 0.0]
        for cid in child_ids:
            h = hydrated_hex_grid.hexes[cid]
            total_emp += h.employment
            for dept_idx in range(4):
                weighted_shares[dept_idx] += h.employment * h.dept_shares[dept_idx]

        expected = (
            tuple(ws / total_emp for ws in weighted_shares)
            if total_emp > 0
            else (0.25, 0.25, 0.25, 0.25)
        )
        actual = shares[wayne_parent]

        for i in range(4):
            assert actual[i] == pytest.approx(expected[i])
