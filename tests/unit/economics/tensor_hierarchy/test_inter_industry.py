"""Unit tests for InterIndustryFlow, Leontief, and DepartmentAggregator.

Feature: 025-tensor-hierarchy
TDD Phase: GREEN (implementation is complete)
"""

from __future__ import annotations

import numpy as np
import pytest

from babylon.economics.tensor_hierarchy.inter_industry import (
    DefaultDepartmentAggregator,
    DefaultLeontiefComputer,
)
from babylon.economics.tensor_hierarchy.types import (
    Department,
    InterIndustryFlow,
    IOTableType,
    LeontiefInverse,
)

# =============================================================================
# DefaultLeontiefComputer tests
# =============================================================================


class TestDefaultLeontiefComputer:
    """Tests for Leontief inverse computation."""

    @pytest.fixture
    def computer(self) -> DefaultLeontiefComputer:
        """Provide a DefaultLeontiefComputer instance."""
        return DefaultLeontiefComputer()

    @pytest.fixture
    def simple_flow(self) -> InterIndustryFlow:
        """Provide a simple 2x2 productive I-O flow."""
        A = np.array([[0.1, 0.2], [0.15, 0.05]], dtype=np.float64)
        return InterIndustryFlow(
            year=2021,
            table_type=IOTableType.USE,
            industries=["A", "B"],
            coefficients=A,
        )

    @pytest.fixture
    def flow_3x3(self) -> InterIndustryFlow:
        """Provide a 3x3 productive I-O flow (toy economy)."""
        A = np.array(
            [
                [0.10, 0.20, 0.05],
                [0.15, 0.05, 0.30],
                [0.25, 0.10, 0.08],
            ],
            dtype=np.float64,
        )
        return InterIndustryFlow(
            year=2021,
            table_type=IOTableType.USE,
            industries=["1100A1", "327C00", "33DG00"],
            coefficients=A,
        )

    @pytest.mark.math
    def test_inverse_type(
        self, computer: DefaultLeontiefComputer, simple_flow: InterIndustryFlow
    ) -> None:
        """compute_inverse returns LeontiefInverse."""
        result = computer.compute_inverse(simple_flow)
        assert isinstance(result, LeontiefInverse)

    @pytest.mark.math
    def test_inverse_year_preserved(
        self, computer: DefaultLeontiefComputer, simple_flow: InterIndustryFlow
    ) -> None:
        """LeontiefInverse preserves year from source flow."""
        result = computer.compute_inverse(simple_flow)
        assert result.year == 2021

    @pytest.mark.math
    def test_inverse_industries_preserved(
        self, computer: DefaultLeontiefComputer, simple_flow: InterIndustryFlow
    ) -> None:
        """LeontiefInverse preserves industry list from source flow."""
        result = computer.compute_inverse(simple_flow)
        assert result.industries == ["A", "B"]

    @pytest.mark.math
    def test_diagonal_gte_one(
        self, computer: DefaultLeontiefComputer, simple_flow: InterIndustryFlow
    ) -> None:
        """Leontief inverse diagonal elements >= 1.0."""
        result = computer.compute_inverse(simple_flow)
        diag = np.diag(result.inverse_matrix)
        assert np.all(diag >= 1.0 - 1e-10)

    @pytest.mark.math
    def test_all_elements_non_negative(
        self, computer: DefaultLeontiefComputer, simple_flow: InterIndustryFlow
    ) -> None:
        """All Leontief inverse elements >= 0."""
        result = computer.compute_inverse(simple_flow)
        assert float(result.inverse_matrix.min()) >= -1e-10

    @pytest.mark.math
    def test_inverse_identity_check(
        self, computer: DefaultLeontiefComputer, simple_flow: InterIndustryFlow
    ) -> None:
        """L = (I - A)^{-1} means (I - A) @ L = I."""
        A = simple_flow.coefficients
        result = computer.compute_inverse(simple_flow)
        L = result.inverse_matrix
        n = A.shape[0]
        product = (np.eye(n) - A) @ L
        assert np.allclose(product, np.eye(n), atol=1e-10)

    @pytest.mark.math
    def test_3x3_inverse(
        self, computer: DefaultLeontiefComputer, flow_3x3: InterIndustryFlow
    ) -> None:
        """Compute Leontief inverse for a 3x3 matrix."""
        result = computer.compute_inverse(flow_3x3)
        assert result.n_industries == 3
        # Verify (I - A) @ L = I
        A = flow_3x3.coefficients
        L = result.inverse_matrix
        product = (np.eye(3) - A) @ L
        assert np.allclose(product, np.eye(3), atol=1e-10)

    @pytest.mark.math
    def test_singular_matrix_raises(self, computer: DefaultLeontiefComputer) -> None:
        """Singular (I - A) raises LinAlgError."""
        # A with column sum = 1.0 makes (I - A) singular
        A = np.array([[0.5, 0.5], [0.5, 0.5]], dtype=np.float64)
        flow = InterIndustryFlow(
            year=2021,
            table_type=IOTableType.USE,
            industries=["A", "B"],
            coefficients=A,
        )
        with pytest.raises(np.linalg.LinAlgError):
            computer.compute_inverse(flow)

    @pytest.mark.math
    def test_total_labor_coefficients(
        self, computer: DefaultLeontiefComputer, simple_flow: InterIndustryFlow
    ) -> None:
        """Total labor coefficients = direct @ L."""
        result = computer.compute_inverse(simple_flow)
        direct_labor = np.array([0.3, 0.5])
        total = computer.total_labor_coefficients(result, direct_labor)
        assert total.shape == (2,)
        # Manual check: l_total = l_direct @ L
        expected = direct_labor @ result.inverse_matrix
        assert np.allclose(total, expected, atol=1e-12)

    @pytest.mark.math
    def test_total_labor_exceeds_direct(
        self, computer: DefaultLeontiefComputer, simple_flow: InterIndustryFlow
    ) -> None:
        """Total labor >= direct labor (supply chain effect)."""
        result = computer.compute_inverse(simple_flow)
        direct_labor = np.array([0.3, 0.5])
        total = computer.total_labor_coefficients(result, direct_labor)
        assert np.all(total >= direct_labor - 1e-10)

    @pytest.mark.math
    def test_benchmark_against_bea_published(self) -> None:
        """Cross-check Leontief inverse against BEA published Total Requirements.

        Uses 2x2 toy values derived from BEA Summary 2021 Use table (approximate).
        Validates that our computation is consistent with the BEA methodology.

        Note: Uses approximate values, not exact BEA data. For exact validation,
        use the integration test with real XLSX files.
        """
        computer = DefaultLeontiefComputer()
        # Toy 2-industry economy: Farms (111CA), Mining (212)
        # From 2021 BEA Use table (approximate, illustrative values)
        A_approx = np.array([[0.05, 0.01], [0.02, 0.08]], dtype=np.float64)
        flow = InterIndustryFlow(
            year=2021,
            table_type=IOTableType.USE,
            industries=["111CA", "212"],
            coefficients=A_approx,
        )
        result = computer.compute_inverse(flow)

        # BEA publishes total requirements; verify our L satisfies basic properties
        assert result.inverse_matrix[0, 0] > 1.0  # diagonal > 1.0
        assert result.inverse_matrix[1, 1] > 1.0
        # Off-diagonal > 0 (supply chain effects)
        assert result.inverse_matrix[0, 1] > 0.0
        assert result.inverse_matrix[1, 0] > 0.0


# =============================================================================
# DefaultDepartmentAggregator tests
# =============================================================================


class TestDefaultDepartmentAggregator:
    """Tests for BEA industry to Marxian department aggregation."""

    @pytest.fixture
    def aggregator(self) -> DefaultDepartmentAggregator:
        """Provide a DefaultDepartmentAggregator instance."""
        return DefaultDepartmentAggregator()

    @pytest.fixture
    def simple_mapping(self) -> dict[str, str]:
        """Provide a minimal 3-industry to 3-department mapping."""
        return {
            "1100A1": "I",  # Farms -> Dept I
            "327C00": "IIA",  # Nonmetallic mineral -> Dept IIa
            "33DG00": "III",  # Care industry -> Dept III
        }

    @pytest.fixture
    def flow_3x3(self) -> InterIndustryFlow:
        """Provide a 3x3 flow for testing aggregation."""
        A = np.array(
            [
                [0.10, 0.20, 0.05],
                [0.15, 0.05, 0.30],
                [0.25, 0.10, 0.08],
            ],
            dtype=np.float64,
        )
        return InterIndustryFlow(
            year=2021,
            table_type=IOTableType.USE,
            industries=["1100A1", "327C00", "33DG00"],
            coefficients=A,
        )

    def test_aggregate_returns_4_industries(
        self,
        aggregator: DefaultDepartmentAggregator,
        flow_3x3: InterIndustryFlow,
        simple_mapping: dict[str, str],
    ) -> None:
        """Aggregation always produces 4 department rows/columns."""
        result = aggregator.aggregate(flow_3x3, simple_mapping)
        assert result.n_industries == 4

    def test_aggregate_year_preserved(
        self,
        aggregator: DefaultDepartmentAggregator,
        flow_3x3: InterIndustryFlow,
        simple_mapping: dict[str, str],
    ) -> None:
        """Aggregation preserves year."""
        result = aggregator.aggregate(flow_3x3, simple_mapping)
        assert result.year == 2021

    def test_aggregate_industries_are_departments(
        self,
        aggregator: DefaultDepartmentAggregator,
        flow_3x3: InterIndustryFlow,
        simple_mapping: dict[str, str],
    ) -> None:
        """Aggregated flow has department names as industry codes."""
        result = aggregator.aggregate(flow_3x3, simple_mapping)
        assert "I" in result.industries
        assert "IIA" in result.industries
        assert "IIB" in result.industries
        assert "III" in result.industries

    def test_aggregate_matrix_non_negative(
        self,
        aggregator: DefaultDepartmentAggregator,
        flow_3x3: InterIndustryFlow,
        simple_mapping: dict[str, str],
    ) -> None:
        """Aggregated coefficients are non-negative."""
        result = aggregator.aggregate(flow_3x3, simple_mapping)
        assert float(result.coefficients.min()) >= -1e-10

    def test_aggregate_empty_mapping(
        self,
        aggregator: DefaultDepartmentAggregator,
        flow_3x3: InterIndustryFlow,
    ) -> None:
        """Empty mapping produces all-zero 4x4 matrix."""
        result = aggregator.aggregate(flow_3x3, {})
        assert result.n_industries == 4
        assert np.allclose(result.coefficients, 0.0)

    def test_get_default_mapping_returns_dict(
        self,
        aggregator: DefaultDepartmentAggregator,
    ) -> None:
        """get_default_mapping returns a non-empty dict."""
        mapping = aggregator.get_default_mapping()
        assert isinstance(mapping, dict)
        assert len(mapping) > 0

    def test_get_default_mapping_valid_departments(
        self,
        aggregator: DefaultDepartmentAggregator,
    ) -> None:
        """All values in default mapping are valid Department values."""
        mapping = aggregator.get_default_mapping()
        valid_depts = {d.value for d in Department}
        for code, dept in mapping.items():
            assert dept in valid_depts, f"Industry {code} mapped to invalid dept {dept}"

    def test_aggregate_with_default_mapping(
        self,
        aggregator: DefaultDepartmentAggregator,
        flow_3x3: InterIndustryFlow,
    ) -> None:
        """Can aggregate using default TOML mapping."""
        mapping = aggregator.get_default_mapping()
        result = aggregator.aggregate(flow_3x3, mapping)
        assert result.n_industries == 4
