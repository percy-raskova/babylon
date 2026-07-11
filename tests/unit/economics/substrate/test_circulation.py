"""Unit tests for Volume II wage circulation (T020).

Feature: 026-tri-county-economic-substrate
Date: 2026-02-26

Tests DefaultHexCirculationComputer: OD matrix construction,
row normalization, wage redistribution conservation.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy import sparse

from babylon.domain.economics.substrate.circulation import DefaultHexCirculationComputer
from babylon.domain.economics.substrate.types import (
    HexGrid,
)

from .conftest import MockCommuterFlowSource


def _sum_variable_capital(grid: HexGrid) -> float:
    """Sum variable capital across all hexes."""
    return sum(h.variable_capital for h in grid.hexes.values())


@pytest.mark.unit
class TestBuildOdMatrix:
    """Tests for DefaultHexCirculationComputer.build_od_matrix."""

    def test_od_matrix_shape(
        self,
        hydrated_hex_grid: HexGrid,
        mock_commuter_source: MockCommuterFlowSource,
    ) -> None:
        """Test OD matrix is N_hexes x N_hexes."""
        computer = DefaultHexCirculationComputer()
        od = computer.build_od_matrix(hydrated_hex_grid, mock_commuter_source, 2021)

        n = len(hydrated_hex_grid.hexes)
        assert od.shape == (n, n)

    def test_od_matrix_is_sparse(
        self,
        hydrated_hex_grid: HexGrid,
        mock_commuter_source: MockCommuterFlowSource,
    ) -> None:
        """Test OD matrix is a scipy sparse CSR matrix."""
        computer = DefaultHexCirculationComputer()
        od = computer.build_od_matrix(hydrated_hex_grid, mock_commuter_source, 2021)

        assert sparse.issparse(od)

    def test_row_normalization(
        self,
        hydrated_hex_grid: HexGrid,
        mock_commuter_source: MockCommuterFlowSource,
    ) -> None:
        """Test that each row of OD matrix sums to 1.0 (or 0.0 for empty rows)."""
        computer = DefaultHexCirculationComputer()
        od = computer.build_od_matrix(hydrated_hex_grid, mock_commuter_source, 2021)

        row_sums = np.array(od.sum(axis=1)).flatten()
        for i, row_sum in enumerate(row_sums):
            if row_sum > 0:
                assert row_sum == pytest.approx(1.0, abs=1e-10), (
                    f"Row {i} sums to {row_sum}, expected 1.0"
                )

    def test_od_matrix_nonnegative(
        self,
        hydrated_hex_grid: HexGrid,
        mock_commuter_source: MockCommuterFlowSource,
    ) -> None:
        """Test that all OD matrix entries are non-negative."""
        computer = DefaultHexCirculationComputer()
        od = computer.build_od_matrix(hydrated_hex_grid, mock_commuter_source, 2021)

        if od.nnz > 0:
            assert od.min() >= 0.0

    def test_empty_grid_od_matrix(
        self,
        mock_commuter_source: MockCommuterFlowSource,
    ) -> None:
        """Test OD matrix for empty grid."""
        grid = HexGrid(
            hexes={},
            county_hex_ids={},
            res6_parents={},
            res5_parents={},
            res6_children={},
            res5_children={},
        )
        computer = DefaultHexCirculationComputer()
        od = computer.build_od_matrix(grid, mock_commuter_source, 2021)

        assert od.shape == (0, 0)


@pytest.mark.unit
class TestCirculateWages:
    """Tests for DefaultHexCirculationComputer.circulate_wages."""

    def test_wage_conservation(
        self,
        hydrated_hex_grid: HexGrid,
        mock_commuter_source: MockCommuterFlowSource,
    ) -> None:
        """Test that sum(v) is conserved within 1e-8 after circulation.

        Tolerance is 1e-8 (not 1e-10) because the sparse matrix multiply
        ``od_matrix.T @ v_vec`` accumulates floating-point error proportional
        to hex count. With ~1000+ hexes the error reaches ~1e-9, well within
        economic significance but beyond 1e-10.
        """
        computer = DefaultHexCirculationComputer()
        od = computer.build_od_matrix(hydrated_hex_grid, mock_commuter_source, 2021)

        pre_v = _sum_variable_capital(hydrated_hex_grid)
        result_grid, boundary = computer.circulate_wages(hydrated_hex_grid, od)
        post_v = _sum_variable_capital(result_grid)

        assert abs(pre_v - post_v) < 1e-8

    def test_all_hexes_preserved(
        self,
        hydrated_hex_grid: HexGrid,
        mock_commuter_source: MockCommuterFlowSource,
    ) -> None:
        """Test that circulation preserves all hex IDs."""
        computer = DefaultHexCirculationComputer()
        od = computer.build_od_matrix(hydrated_hex_grid, mock_commuter_source, 2021)

        result_grid, _ = computer.circulate_wages(hydrated_hex_grid, od)

        assert set(result_grid.hexes.keys()) == set(hydrated_hex_grid.hexes.keys())

    def test_boundary_flow_register_returned(
        self,
        hydrated_hex_grid: HexGrid,
        mock_commuter_source: MockCommuterFlowSource,
    ) -> None:
        """Test that circulate_wages returns a BoundaryFlowRegister."""
        computer = DefaultHexCirculationComputer()
        od = computer.build_od_matrix(hydrated_hex_grid, mock_commuter_source, 2021)

        _, boundary = computer.circulate_wages(hydrated_hex_grid, od)

        # BoundaryFlowRegister should be valid (passes model validator)
        assert boundary.net_flow == boundary.external_inflow_v - boundary.external_outflow_v

    def test_constant_capital_unchanged(
        self,
        hydrated_hex_grid: HexGrid,
        mock_commuter_source: MockCommuterFlowSource,
    ) -> None:
        """Test that circulation does not modify constant capital."""
        computer = DefaultHexCirculationComputer()
        od = computer.build_od_matrix(hydrated_hex_grid, mock_commuter_source, 2021)

        result_grid, _ = computer.circulate_wages(hydrated_hex_grid, od)

        for h3_id in hydrated_hex_grid.hexes:
            assert result_grid.hexes[h3_id].constant_capital == (
                hydrated_hex_grid.hexes[h3_id].constant_capital
            )

    def test_surplus_value_unchanged(
        self,
        hydrated_hex_grid: HexGrid,
        mock_commuter_source: MockCommuterFlowSource,
    ) -> None:
        """Test that circulation does not modify surplus value."""
        computer = DefaultHexCirculationComputer()
        od = computer.build_od_matrix(hydrated_hex_grid, mock_commuter_source, 2021)

        result_grid, _ = computer.circulate_wages(hydrated_hex_grid, od)

        for h3_id in hydrated_hex_grid.hexes:
            assert result_grid.hexes[h3_id].surplus_value == (
                hydrated_hex_grid.hexes[h3_id].surplus_value
            )

    def test_rates_recomputed_after_circulation(
        self,
        hydrated_hex_grid: HexGrid,
        mock_commuter_source: MockCommuterFlowSource,
    ) -> None:
        """Test that profit_rate and exploitation_rate are recomputed."""
        computer = DefaultHexCirculationComputer()
        od = computer.build_od_matrix(hydrated_hex_grid, mock_commuter_source, 2021)

        result_grid, _ = computer.circulate_wages(hydrated_hex_grid, od)

        for _h3_id, hex_state in result_grid.hexes.items():
            v = hex_state.variable_capital
            c = hex_state.constant_capital
            s = hex_state.surplus_value

            expected_pr = s / (c + v) if (c + v) > 0 else 0.0
            expected_er = s / v if v > 0 else 0.0

            assert hex_state.profit_rate == pytest.approx(expected_pr)
            assert hex_state.exploitation_rate == pytest.approx(expected_er)

    def test_identity_od_matrix_no_change(
        self,
        hydrated_hex_grid: HexGrid,
    ) -> None:
        """Test that identity OD matrix produces no redistribution."""
        hex_ids = sorted(hydrated_hex_grid.hexes.keys())
        n = len(hex_ids)
        identity_od = sparse.eye(n, dtype=np.float64, format="csr")

        computer = DefaultHexCirculationComputer()
        result_grid, _ = computer.circulate_wages(hydrated_hex_grid, identity_od)

        # Variable capital should be unchanged with identity matrix
        for h3_id in hex_ids:
            pre_v = hydrated_hex_grid.hexes[h3_id].variable_capital
            post_v = result_grid.hexes[h3_id].variable_capital
            assert post_v == pytest.approx(pre_v, abs=1e-8)
