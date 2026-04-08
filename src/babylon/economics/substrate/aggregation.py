"""Multi-resolution aggregation for the substrate module.

Feature: 026-tri-county-economic-substrate
Date: 2026-02-26

Aggregates hex-level values to coarser H3 resolutions (r6, r5)
using the parent-child hierarchy stored in HexGrid.

See Also:
    :mod:`babylon.economics.substrate.types`: HexGrid resolution hierarchy.
    :mod:`babylon.economics.substrate.conservation`: Hierarchical conservation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from babylon.economics.substrate.types import HexGrid


class DefaultResolutionAggregator:
    """Aggregate hex-level values to parent resolutions.

    Uses the res6_children / res5_children mappings in HexGrid
    to sum child hex values into parent resolution totals.
    """

    def aggregate(self, grid: HexGrid, target_resolution: int) -> dict[str, float]:
        """Sum hex total capital to parent resolution.

        Args:
            grid: Source hex grid at resolution 7.
            target_resolution: Target parent resolution (5 or 6).

        Returns:
            Mapping of parent h3_index to summed total capital (c+v+s).

        Raises:
            ValueError: If target_resolution is not 5 or 6.
        """
        children_map = self._get_children_map(grid, target_resolution)

        result: dict[str, float] = {}
        for parent_id, child_ids in children_map.items():
            total = 0.0
            for child_id in child_ids:
                if child_id in grid.hexes:
                    h = grid.hexes[child_id]
                    total += h.constant_capital + h.variable_capital + h.surplus_value
            result[parent_id] = total

        return result

    def compute_weighted_profit_rate(
        self, grid: HexGrid, target_resolution: int
    ) -> dict[str, float]:
        """Capital-weighted average profit rate at parent resolution.

        For each parent hex, computes:
            r_weighted = sum(child.s) / sum(child.c + child.v)

        Args:
            grid: Source hex grid at resolution 7.
            target_resolution: Target parent resolution (5 or 6).

        Returns:
            Mapping of parent h3_index to capital-weighted profit rate.
        """
        children_map = self._get_children_map(grid, target_resolution)

        result: dict[str, float] = {}
        for parent_id, child_ids in children_map.items():
            total_s = 0.0
            total_cv = 0.0
            for child_id in child_ids:
                if child_id in grid.hexes:
                    h = grid.hexes[child_id]
                    total_s += h.surplus_value
                    total_cv += h.constant_capital + h.variable_capital

            result[parent_id] = total_s / total_cv if total_cv > 0 else 0.0

        return result

    def compute_weighted_exploitation_rate(
        self, grid: HexGrid, target_resolution: int
    ) -> dict[str, float]:
        """Capital-weighted exploitation rate at parent resolution.

        For each parent hex, computes:
            e_weighted = sum(child.s) / sum(child.v)

        Args:
            grid: Source hex grid at resolution 7.
            target_resolution: Target parent resolution (5 or 6).

        Returns:
            Mapping of parent h3_index to capital-weighted exploitation rate.
        """
        children_map = self._get_children_map(grid, target_resolution)

        result: dict[str, float] = {}
        for parent_id, child_ids in children_map.items():
            total_s = 0.0
            total_v = 0.0
            for child_id in child_ids:
                if child_id in grid.hexes:
                    h = grid.hexes[child_id]
                    total_s += h.surplus_value
                    total_v += h.variable_capital

            result[parent_id] = total_s / total_v if total_v > 0 else 0.0

        return result

    def compute_weighted_organic_composition(
        self, grid: HexGrid, target_resolution: int
    ) -> dict[str, float]:
        """Capital-weighted organic composition at parent resolution.

        For each parent hex, computes:
            occ = sum(child.c) / sum(child.v)

        Args:
            grid: Source hex grid at resolution 7.
            target_resolution: Target parent resolution (5 or 6).

        Returns:
            Mapping of parent h3_index to organic composition of capital.
        """
        children_map = self._get_children_map(grid, target_resolution)

        result: dict[str, float] = {}
        for parent_id, child_ids in children_map.items():
            total_c = 0.0
            total_v = 0.0
            for child_id in child_ids:
                if child_id in grid.hexes:
                    h = grid.hexes[child_id]
                    total_c += h.constant_capital
                    total_v += h.variable_capital

            result[parent_id] = total_c / total_v if total_v > 0 else 0.0

        return result

    def compute_employment(self, grid: HexGrid, target_resolution: int) -> dict[str, float]:
        """Sum employment at parent resolution.

        Args:
            grid: Source hex grid at resolution 7.
            target_resolution: Target parent resolution (5 or 6).

        Returns:
            Mapping of parent h3_index to summed employment.
        """
        children_map = self._get_children_map(grid, target_resolution)

        result: dict[str, float] = {}
        for parent_id, child_ids in children_map.items():
            total = 0.0
            for child_id in child_ids:
                if child_id in grid.hexes:
                    total += grid.hexes[child_id].employment
            result[parent_id] = total

        return result

    def compute_component_capitals(
        self, grid: HexGrid, target_resolution: int
    ) -> dict[str, tuple[float, float, float]]:
        """Sum individual capital components at parent resolution.

        Args:
            grid: Source hex grid at resolution 7.
            target_resolution: Target parent resolution (5 or 6).

        Returns:
            Mapping of parent h3_index to (c, v, s) tuple.
        """
        children_map = self._get_children_map(grid, target_resolution)

        result: dict[str, tuple[float, float, float]] = {}
        for parent_id, child_ids in children_map.items():
            total_c = 0.0
            total_v = 0.0
            total_s = 0.0
            for child_id in child_ids:
                if child_id in grid.hexes:
                    h = grid.hexes[child_id]
                    total_c += h.constant_capital
                    total_v += h.variable_capital
                    total_s += h.surplus_value
            result[parent_id] = (total_c, total_v, total_s)

        return result

    def compute_dept_share_weighted(
        self, grid: HexGrid, target_resolution: int
    ) -> dict[str, tuple[float, float, float, float]]:
        """Employment-weighted department shares at parent resolution.

        For each parent hex, computes weighted average of child dept_shares
        using child employment as weights.

        Args:
            grid: Source hex grid at resolution 7.
            target_resolution: Target parent resolution (5 or 6).

        Returns:
            Mapping of parent h3_index to (dept_I, dept_IIa, dept_IIb, dept_III).
        """
        children_map = self._get_children_map(grid, target_resolution)

        result: dict[str, tuple[float, float, float, float]] = {}
        for parent_id, child_ids in children_map.items():
            total_emp = 0.0
            weighted = [0.0, 0.0, 0.0, 0.0]
            for child_id in child_ids:
                if child_id in grid.hexes:
                    h = grid.hexes[child_id]
                    total_emp += h.employment
                    for i in range(4):
                        weighted[i] += h.employment * h.dept_shares[i]

            if total_emp > 0:
                result[parent_id] = (
                    weighted[0] / total_emp,
                    weighted[1] / total_emp,
                    weighted[2] / total_emp,
                    weighted[3] / total_emp,
                )
            else:
                result[parent_id] = (0.25, 0.25, 0.25, 0.25)

        return result

    def _get_children_map(self, grid: HexGrid, target_resolution: int) -> dict[str, frozenset[str]]:
        """Get the children map for the target resolution.

        Args:
            grid: Source hex grid.
            target_resolution: 5 or 6.

        Returns:
            Mapping of parent h3_id to frozenset of child h3_ids.

        Raises:
            ValueError: If target_resolution is not 5 or 6.
        """
        if target_resolution == 6:
            return grid.res6_children
        elif target_resolution == 5:
            return grid.res5_children
        else:
            msg = f"target_resolution must be 5 or 6, got {target_resolution}"
            raise ValueError(msg)


__all__ = [
    "DefaultResolutionAggregator",
]
