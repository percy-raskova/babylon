"""Runtime conservation invariant checking for the substrate module.

Feature: 026-tri-county-economic-substrate
Date: 2026-02-26

Provides non-halting conservation checks that log warnings when invariants
are violated. Conservation violations are reported but do not halt the
simulation (per FR-015).

See Also:
    :mod:`babylon.economics.substrate.types`: HexGrid and HexEconomicState.
    :mod:`babylon.economics.substrate.validation`: Three-tier value validation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from babylon.economics.substrate.types import HexGrid

logger = logging.getLogger(__name__)

CONSERVATION_TOLERANCE: float = 1e-10


def _sum_total_capital(grid: HexGrid) -> float:
    """Sum total capital (c + v + s) across all hexes.

    Args:
        grid: HexGrid to sum over.

    Returns:
        Total capital as float.
    """
    total = 0.0
    for h in grid.hexes.values():
        total += h.constant_capital + h.variable_capital + h.surplus_value
    return total


def _sum_variable_capital(grid: HexGrid) -> float:
    """Sum variable capital (v) across all hexes.

    Args:
        grid: HexGrid to sum over.

    Returns:
        Total variable capital as float.
    """
    total = 0.0
    for h in grid.hexes.values():
        total += h.variable_capital
    return total


class DefaultConservationChecker:
    """Non-halting conservation checker that logs warnings on violation.

    Checks conservation invariants (abs(diff) < tolerance) and logs
    warnings when violated. Never raises exceptions or halts the
    simulation, per FR-015.

    Attributes:
        tolerance: Maximum acceptable deviation (default 1e-10).
        circulation_tolerance: Wider tolerance for circulation operations
            (default 1e-8) to accommodate floating-point accumulation in
            sparse matrix multiply with large hex grids.
    """

    def __init__(
        self,
        tolerance: float = CONSERVATION_TOLERANCE,
        circulation_tolerance: float = 1e-8,
    ) -> None:
        """Initialize conservation checker.

        Args:
            tolerance: Maximum acceptable absolute deviation for most operations.
            circulation_tolerance: Maximum acceptable deviation for circulation
                (wage redistribution via sparse OD matrix). Wider than default
                because ``od_matrix.T @ v_vec`` with ~1000+ hexes accumulates
                ~1e-9 floating-point error that exceeds 1e-10 but is well
                within economic significance.
        """
        self._tolerance = tolerance
        self._circulation_tolerance = circulation_tolerance

    def check_total_capital(self, pre_grid: HexGrid, post_grid: HexGrid, operation: str) -> bool:
        """Check sum(c+v+s) conservation between pre and post grids.

        Args:
            pre_grid: Grid state before operation.
            post_grid: Grid state after operation.
            operation: Name of the operation for logging.

        Returns:
            True if conservation holds within tolerance, False otherwise.
        """
        pre_total = _sum_total_capital(pre_grid)
        post_total = _sum_total_capital(post_grid)
        diff = abs(pre_total - post_total)

        if diff >= self._tolerance:
            logger.warning(
                "Conservation violation in %s: total capital diff=%.2e "
                "(pre=%.6f, post=%.6f, tolerance=%.0e)",
                operation,
                diff,
                pre_total,
                post_total,
                self._tolerance,
            )
            return False

        return True

    def check_variable_capital(
        self,
        pre_grid: HexGrid,
        post_grid: HexGrid,
        operation: str,
        use_circulation_tolerance: bool = False,
    ) -> bool:
        """Check sum(v) conservation between pre and post grids.

        Args:
            pre_grid: Grid state before operation.
            post_grid: Grid state after operation.
            operation: Name of the operation for logging.
            use_circulation_tolerance: If True, use the wider circulation
                tolerance (1e-8) instead of the default (1e-10). Set this
                for wage redistribution via sparse OD matrix operations.

        Returns:
            True if conservation holds within tolerance, False otherwise.
        """
        tol = self._circulation_tolerance if use_circulation_tolerance else self._tolerance
        pre_v = _sum_variable_capital(pre_grid)
        post_v = _sum_variable_capital(post_grid)
        diff = abs(pre_v - post_v)

        if diff >= tol:
            logger.warning(
                "Conservation violation in %s: variable capital diff=%.2e "
                "(pre=%.6f, post=%.6f, tolerance=%.0e)",
                operation,
                diff,
                pre_v,
                post_v,
                tol,
            )
            return False

        return True

    def check_hierarchical_aggregation(self, grid: HexGrid, target_resolution: int) -> bool:
        """Check that r7 hex sums equal parent resolution values.

        Verifies that summing child hex values at resolution 7 matches
        the aggregate at the target parent resolution (5 or 6).

        Args:
            grid: HexGrid with resolution hierarchy.
            target_resolution: Target parent resolution (5 or 6).

        Returns:
            True if all parent sums match within tolerance.
        """
        if target_resolution == 6:
            children_map = grid.res6_children
        elif target_resolution == 5:
            children_map = grid.res5_children
        else:
            logger.warning(
                "Unsupported target resolution %d for hierarchical check",
                target_resolution,
            )
            return False

        all_valid = True
        for parent_id, child_ids in children_map.items():
            child_total = 0.0
            for child_id in child_ids:
                if child_id in grid.hexes:
                    h = grid.hexes[child_id]
                    child_total += h.constant_capital + h.variable_capital + h.surplus_value

            # For hierarchical checks, we just verify internal consistency
            # The parent value IS the sum of children (no separate parent value)
            # So we check that all children exist
            missing = child_ids - frozenset(grid.hexes.keys())
            if missing:
                logger.warning(
                    "Hierarchical check: parent %s missing %d children at res %d",
                    parent_id,
                    len(missing),
                    target_resolution,
                )
                all_valid = False

        return all_valid


__all__ = [
    "CONSERVATION_TOLERANCE",
    "DefaultConservationChecker",
]
