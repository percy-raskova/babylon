"""Property-based tests for H3 hierarchical sum conservation (INV-002 / Spec 053 US2).

See ``specs/053-conservation-invariants/contracts/h3_hierarchical.md`` for
the full predicate specification.

The H3 hierarchy is treated as a sheaf: at any tick, sum(c+v+s) over the
res-7 children of a parent must equal that parent's res-6 (or res-5)
aggregate. This is the gluing condition that justifies treating per-county
and per-state aggregates as derived rather than independent state.

Tolerance combines an absolute floor (1e-10) with a relative-ULP component
(1e-13 × |sum|) per FR-005 / FR-012. The relative component is necessary
because float64 accumulation drift at sum ≈ 1e6 reaches ~1e-10 absolute,
purely from machine-epsilon round-off (machine ε ≈ 2.22e-16).
"""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings

from babylon.domain.economics.substrate.aggregation import DefaultResolutionAggregator
from babylon.domain.economics.substrate.types import HexGrid
from tests.property.strategies.hex_grid import hex_grid_strategy


def _tol(magnitude: float = 0.0) -> float:
    """Sheaf-gluing tolerance with relative-ULP component."""
    return max(1e-10, 1e-13 * abs(magnitude))


def _sum_cvs(grid: HexGrid) -> float:
    return sum(
        h.constant_capital + h.variable_capital + h.surplus_value for h in grid.hexes.values()
    )


@pytest.mark.unit
class TestSheafGluingPerParent:
    """INV-002: each res-6 / res-5 parent equals the sum of its res-7 children."""

    @given(grid=hex_grid_strategy(min_hexes=1, max_hexes=100))
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_sheaf_gluing_at_res6(self, grid: HexGrid) -> None:
        """For every res-6 parent, sum_children(c+v+s) == aggregator value."""
        aggregator = DefaultResolutionAggregator()
        r6_totals = aggregator.aggregate(grid, target_resolution=6)
        for parent_id, child_ids in grid.res6_children.items():
            child_sum = sum(
                grid.hexes[c].constant_capital
                + grid.hexes[c].variable_capital
                + grid.hexes[c].surplus_value
                for c in child_ids
                if c in grid.hexes
            )
            parent_total = r6_totals.get(parent_id, 0.0)
            drift = abs(child_sum - parent_total)
            tol = _tol(magnitude=max(abs(child_sum), abs(parent_total)))
            assert drift < tol, (
                f"INV-002: sheaf gluing violated at res-6 parent={parent_id}, "
                f"child_sum={child_sum:.10f}, parent_aggregate={parent_total:.10f}, "
                f"drift={drift:.3e}, tol={tol:.3e}"
            )

    @given(grid=hex_grid_strategy(min_hexes=1, max_hexes=100))
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_sheaf_gluing_at_res5(self, grid: HexGrid) -> None:
        """For every res-5 parent, sum_children(c+v+s) == aggregator value."""
        aggregator = DefaultResolutionAggregator()
        r5_totals = aggregator.aggregate(grid, target_resolution=5)
        for parent_id, child_ids in grid.res5_children.items():
            child_sum = sum(
                grid.hexes[c].constant_capital
                + grid.hexes[c].variable_capital
                + grid.hexes[c].surplus_value
                for c in child_ids
                if c in grid.hexes
            )
            parent_total = r5_totals.get(parent_id, 0.0)
            drift = abs(child_sum - parent_total)
            tol = _tol(magnitude=max(abs(child_sum), abs(parent_total)))
            assert drift < tol, (
                f"INV-002: sheaf gluing violated at res-5 parent={parent_id}, "
                f"child_sum={child_sum:.10f}, parent_aggregate={parent_total:.10f}, "
                f"drift={drift:.3e}, tol={tol:.3e}"
            )


@pytest.mark.unit
class TestSheafGlobalConsistency:
    """INV-002: cross-resolution global totals all agree within tolerance."""

    @given(grid=hex_grid_strategy(min_hexes=1, max_hexes=100))
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_global_consistency_r6_r5_hex(self, grid: HexGrid) -> None:
        """Sum of r6 totals == sum of r5 totals == per-hex sum."""
        aggregator = DefaultResolutionAggregator()
        r6_global = sum(aggregator.aggregate(grid, target_resolution=6).values())
        r5_global = sum(aggregator.aggregate(grid, target_resolution=5).values())
        hex_total = _sum_cvs(grid)
        magnitude = max(abs(hex_total), abs(r6_global), abs(r5_global))
        tol = _tol(magnitude=magnitude)
        assert abs(hex_total - r6_global) < tol, (
            f"INV-002: hex_total={hex_total:.10f} != r6_global={r6_global:.10f}, "
            f"drift={abs(hex_total - r6_global):.3e}, tol={tol:.3e}"
        )
        assert abs(hex_total - r5_global) < tol, (
            f"INV-002: hex_total={hex_total:.10f} != r5_global={r5_global:.10f}, "
            f"drift={abs(hex_total - r5_global):.3e}, tol={tol:.3e}"
        )
        assert abs(r6_global - r5_global) < tol, (
            f"INV-002: r6_global={r6_global:.10f} != r5_global={r5_global:.10f}, "
            f"drift={abs(r6_global - r5_global):.3e}, tol={tol:.3e}"
        )
