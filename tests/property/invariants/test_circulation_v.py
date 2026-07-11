"""Property-based tests for variable capital conservation under circulation
(INV-003 / Spec 053 US3).

See ``specs/053-conservation-invariants/contracts/circulation_v.md`` for
the full predicate specification.

The invariant: for any sparse OD matrix and any starting hex state,
``circulate_wages`` preserves ``sum(v)`` within a hex-count-scaled tolerance,
and leaves ``sum(c)`` and ``sum(s)`` exactly unchanged.

Tolerance derivation (per FR-006/FR-012): the sparse-matrix multiply
``od_matrix.T @ v_vec`` accumulates floating-point error proportional to hex
count, hence ``tol(N) = max(1e-10, 1e-11 * N, 1e-13 * |sum_v|)``.
"""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from babylon.domain.economics.substrate.circulation import DefaultHexCirculationComputer
from babylon.domain.economics.substrate.types import HexGrid
from tests.property.strategies.hex_grid import hex_grid_strategy
from tests.property.strategies.od_matrix import od_matrix_strategy


def _sum_v(grid: HexGrid) -> float:
    return sum(h.variable_capital for h in grid.hexes.values())


def _sum_c(grid: HexGrid) -> float:
    return sum(h.constant_capital for h in grid.hexes.values())


def _sum_s(grid: HexGrid) -> float:
    return sum(h.surplus_value for h in grid.hexes.values())


def _tol(n: int, magnitude: float = 0.0) -> float:
    """Combined absolute + linear-in-N + relative-ULP tolerance.

    See test_value_conservation._tol for full derivation. The relative
    component (1e-13 × |magnitude|) handles float64 accumulation drift
    when sums get large.
    """
    return max(1e-10, 1e-11 * n, 1e-13 * abs(magnitude))


# Composite strategies that draw a (HexGrid, OD matrix) pair where the OD
# matrix dimension matches the grid's hex count. Without this pairing, calling
# `.example()` inside @given (which is forbidden — it's for interactive use)
# would be the only alternative.
@st.composite
def _grid_with_od(
    draw: st.DrawFn,
    min_hexes: int,
    max_hexes: int,
    flavor: str,
) -> tuple[HexGrid, object]:
    grid = draw(hex_grid_strategy(min_hexes=min_hexes, max_hexes=max_hexes))
    n = len(grid.hexes)
    od = draw(od_matrix_strategy(n, flavor=flavor))  # type: ignore[arg-type]
    return grid, od


@pytest.mark.unit
class TestCirculationConserved:
    """INV-003: ``circulate_wages`` preserves sum(v); leaves sum(c), sum(s) exact."""

    @given(pair=_grid_with_od(min_hexes=1, max_hexes=100, flavor="random"))
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_random_od_conserves_v(self, pair: tuple[HexGrid, object]) -> None:
        """Random sparse OD: |sum(v)_post - sum(v)_pre| < tol(N)."""
        grid, od = pair
        n = len(grid.hexes)
        pre_v = _sum_v(grid)
        pre_c = _sum_c(grid)
        pre_s = _sum_s(grid)
        post_grid, _boundary = DefaultHexCirculationComputer().circulate_wages(grid, od)
        post_v = _sum_v(post_grid)
        post_c = _sum_c(post_grid)
        post_s = _sum_s(post_grid)
        tol = _tol(n, magnitude=max(abs(pre_v), abs(post_v)))
        drift_v = abs(post_v - pre_v)
        assert drift_v < tol, (
            f"INV-003: circulation drifted sum(v) by {drift_v:.3e} > tol={tol:.3e} "
            f"(N={n}, pre={pre_v:.6f}, post={post_v:.6f})"
        )
        assert post_c == pre_c, (
            f"INV-003: circulation mutated sum(c) by {post_c - pre_c:.3e} (must be 0)"
        )
        assert post_s == pre_s, (
            f"INV-003: circulation mutated sum(s) by {post_s - pre_s:.3e} (must be 0)"
        )

    @given(pair=_grid_with_od(min_hexes=1, max_hexes=100, flavor="identity"))
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_identity_od_no_redistribution(self, pair: tuple[HexGrid, object]) -> None:
        """Identity OD: per-hex v unchanged within tol(N)."""
        grid, od = pair
        n = len(grid.hexes)
        pre_v_per_hex = {h: hs.variable_capital for h, hs in grid.hexes.items()}
        post_grid, _boundary = DefaultHexCirculationComputer().circulate_wages(grid, od)
        for h3_id, post_hex in post_grid.hexes.items():
            pre = pre_v_per_hex[h3_id]
            post = post_hex.variable_capital
            drift = abs(post - pre)
            tol = _tol(n, magnitude=max(abs(pre), abs(post)))
            assert drift < tol, (
                f"INV-003: identity OD redistributed v at hex={h3_id} "
                f"by {drift:.3e} > tol={tol:.3e} (pre={pre}, post={post})"
            )

    @given(pair=_grid_with_od(min_hexes=2, max_hexes=100, flavor="empty_rows"))
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_empty_row_od_conserves_v(self, pair: tuple[HexGrid, object]) -> None:
        """OD with at least one zero row: sum(v) still conserved."""
        grid, od = pair
        n = len(grid.hexes)
        pre_v = _sum_v(grid)
        post_grid, _boundary = DefaultHexCirculationComputer().circulate_wages(grid, od)
        post_v = _sum_v(post_grid)
        tol = _tol(n, magnitude=max(abs(pre_v), abs(post_v)))
        drift = abs(post_v - pre_v)
        assert drift < tol, (
            f"INV-003: empty-row OD drifted sum(v) by {drift:.3e} > tol={tol:.3e} "
            f"(N={n}, pre={pre_v:.6f}, post={post_v:.6f})"
        )
