"""Unit tests for tensor hierarchy type models.

Feature: 025-tensor-hierarchy
TDD Phase: GREEN (types are implemented)
"""

from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError

from babylon.domain.economics.tensor_hierarchy.types import (
    ClassTransitionMatrix,
    Department,
    GeographicFlow,
    ImperialRentField,
    InterIndustryFlow,
    IOTableType,
    LeontiefInverse,
    ReproductionRequirements,
    ShadowSubsidyTensor,
    StationaryDistribution,
    VisibilityMetric,
)

# =============================================================================
# IOTableType enum
# =============================================================================


class TestIOTableType:
    """Tests for IOTableType enum."""

    def test_values(self) -> None:
        """All four BEA table types are defined."""
        assert IOTableType.USE.value == "USE"
        assert IOTableType.MAKE.value == "MAKE"
        assert IOTableType.SUPPLY.value == "SUPPLY"
        assert IOTableType.TOTAL_REQ.value == "TOTAL_REQ"

    def test_is_string_enum(self) -> None:
        """IOTableType is a string enum."""
        assert isinstance(IOTableType.USE, str)


# =============================================================================
# Department enum
# =============================================================================


class TestDepartment:
    """Tests for Department enum."""

    def test_four_departments(self) -> None:
        """All four Marxian departments are defined."""
        assert Department.I.value == "I"
        assert Department.IIA.value == "IIA"
        assert Department.IIB.value == "IIB"
        assert Department.III.value == "III"


# =============================================================================
# InterIndustryFlow
# =============================================================================


class TestInterIndustryFlow:
    """Tests for InterIndustryFlow model."""

    def test_basic_construction(self, sample_inter_industry_flow: InterIndustryFlow) -> None:
        """Can construct with valid arguments."""
        assert sample_inter_industry_flow.year == 2021
        assert sample_inter_industry_flow.table_type == IOTableType.USE
        assert sample_inter_industry_flow.n_industries == 3

    def test_list_coerced_to_ndarray(self) -> None:
        """List of lists is coerced to ndarray."""
        flow = InterIndustryFlow(
            year=2021,
            table_type=IOTableType.USE,
            industries=["A", "B"],
            coefficients=[[0.1, 0.2], [0.3, 0.4]],
        )
        assert isinstance(flow.coefficients, np.ndarray)
        assert flow.coefficients.dtype == np.float64

    def test_shape_validation(self) -> None:
        """Mismatched shape raises ValueError."""
        with pytest.raises(ValidationError, match="shape"):
            InterIndustryFlow(
                year=2021,
                table_type=IOTableType.USE,
                industries=["A", "B", "C"],  # 3 industries
                coefficients=np.eye(2),  # but 2x2 matrix
            )

    def test_frozen(self, sample_inter_industry_flow: InterIndustryFlow) -> None:
        """Model is frozen (immutable)."""
        with pytest.raises(ValidationError):
            sample_inter_industry_flow.year = 2020  # type: ignore[misc]

    def test_year_minimum(self) -> None:
        """Year must be >= 1997."""
        with pytest.raises(ValidationError):
            InterIndustryFlow(
                year=1996,
                table_type=IOTableType.USE,
                industries=["A"],
                coefficients=np.array([[0.1]]),
            )


# =============================================================================
# VisibilityMetric
# =============================================================================


class TestVisibilityMetric:
    """Tests for VisibilityMetric model."""

    def test_basic_construction(self, sample_visibility_metric: VisibilityMetric) -> None:
        """Can construct with valid arguments."""
        assert sample_visibility_metric.year == 2022
        assert sample_visibility_metric.g_33 == pytest.approx(0.333)
        assert sample_visibility_metric.g_11 == pytest.approx(1.0)

    def test_g_diagonal_shape(self, sample_visibility_metric: VisibilityMetric) -> None:
        """g_diagonal has shape (4,)."""
        assert sample_visibility_metric.g_diagonal.shape == (4,)

    def test_g_diagonal_wrong_shape(self) -> None:
        """g_diagonal with wrong shape raises ValidationError."""
        with pytest.raises(ValidationError, match="shape"):
            VisibilityMetric(
                year=2022,
                g_diagonal=np.array([1.0, 1.0, 1.0]),  # needs 4 elements
                g_11=1.0,
                g_22a=1.0,
                g_22b=1.0,
                g_33=0.33,
            )

    def test_g33_less_than_g11(self, sample_visibility_metric: VisibilityMetric) -> None:
        """g_33 < g_11 is the expected relationship."""
        assert sample_visibility_metric.g_33 < sample_visibility_metric.g_11

    def test_list_coerced(self) -> None:
        """List is coerced to ndarray."""
        vm = VisibilityMetric(
            year=2022,
            g_diagonal=[1.0, 1.0, 1.0, 0.333],
            g_11=1.0,
            g_22a=1.0,
            g_22b=1.0,
            g_33=0.333,
        )
        assert isinstance(vm.g_diagonal, np.ndarray)

    def test_year_minimum(self) -> None:
        """Year must be >= 2003 (ATUS availability)."""
        with pytest.raises(ValidationError):
            VisibilityMetric(
                year=2002,
                g_diagonal=np.array([1.0, 1.0, 1.0, 0.333]),
                g_11=1.0,
                g_22a=1.0,
                g_22b=1.0,
                g_33=0.333,
            )

    def test_g_bounds(self) -> None:
        """Visibility coefficients must be in [0, 1]."""
        with pytest.raises(ValidationError):
            VisibilityMetric(
                year=2022,
                g_diagonal=np.array([1.0, 1.0, 1.0, 0.333]),
                g_11=1.5,  # > 1.0 is invalid
                g_22a=1.0,
                g_22b=1.0,
                g_33=0.333,
            )


# =============================================================================
# GeographicFlow
# =============================================================================


class TestGeographicFlow:
    """Tests for GeographicFlow model."""

    def test_basic_construction(self) -> None:
        """Can construct with valid arguments."""
        gf = GeographicFlow(
            year=2017,
            areas=["11", "12", "13"],
            flow_matrix=np.eye(3) * 100.0,
        )
        assert gf.n_areas == 3
        assert gf.commodity_code is None

    def test_with_commodity_code(self) -> None:
        """Can specify a SCTG commodity code."""
        gf = GeographicFlow(
            year=2017,
            areas=["11", "12"],
            flow_matrix=np.array([[50.0, 10.0], [5.0, 80.0]]),
            commodity_code="01",
        )
        assert gf.commodity_code == "01"

    def test_shape_mismatch(self) -> None:
        """Matrix shape must match areas list."""
        with pytest.raises(ValidationError, match="shape"):
            GeographicFlow(
                year=2017,
                areas=["11", "12", "13"],
                flow_matrix=np.eye(2),  # 2x2 but 3 areas
            )

    def test_year_minimum(self) -> None:
        """Year must be >= 2012 (FAF5 data)."""
        with pytest.raises(ValidationError):
            GeographicFlow(
                year=2011,
                areas=["11"],
                flow_matrix=np.array([[100.0]]),
            )


# =============================================================================
# LeontiefInverse
# =============================================================================


class TestLeontiefInverse:
    """Tests for LeontiefInverse model."""

    def test_basic_construction(self) -> None:
        """Can construct with valid arguments."""
        A = np.array([[0.1, 0.2], [0.15, 0.05]])
        I_minus_A = np.eye(2) - A
        L = np.linalg.inv(I_minus_A)
        li = LeontiefInverse(year=2021, industries=["A", "B"], inverse_matrix=L)
        assert li.n_industries == 2

    def test_diagonal_gte_one(self) -> None:
        """Leontief diagonal elements >= 1.0 for productive economy."""
        A = np.array([[0.1, 0.2], [0.15, 0.05]])
        L = np.linalg.inv(np.eye(2) - A)
        li = LeontiefInverse(year=2021, industries=["A", "B"], inverse_matrix=L)
        assert np.all(np.diag(li.inverse_matrix) >= 1.0)

    def test_shape_mismatch(self) -> None:
        """Shape must match industry list."""
        with pytest.raises(ValidationError, match="shape"):
            LeontiefInverse(
                year=2021,
                industries=["A", "B", "C"],
                inverse_matrix=np.eye(2),
            )


# =============================================================================
# ImperialRentField
# =============================================================================


class TestImperialRentField:
    """Tests for ImperialRentField model."""

    def test_basic_construction(self) -> None:
        """Can construct with balanced phi."""
        phi = np.array([50.0, -30.0, -20.0])
        irf = ImperialRentField(year=2017, areas=["11", "12", "13"], phi=phi)
        assert irf.n_areas == 3
        assert abs(irf.phi.sum()) < 1e-10

    def test_shape_mismatch(self) -> None:
        """phi shape must match areas list."""
        with pytest.raises(ValidationError, match="shape"):
            ImperialRentField(
                year=2017,
                areas=["11", "12"],
                phi=np.array([50.0, -30.0, -20.0]),  # 3 elements, 2 areas
            )


# =============================================================================
# ShadowSubsidyTensor
# =============================================================================


class TestShadowSubsidyTensor:
    """Tests for ShadowSubsidyTensor model."""

    def test_basic_construction(self) -> None:
        """Can construct with valid arguments."""
        ss = ShadowSubsidyTensor(
            year=2022,
            phi_iii_labor_hours=22.0,
            phi_iii_dollars=None,
            melt_available=False,
        )
        assert ss.phi_iii_labor_hours == pytest.approx(22.0)
        assert ss.phi_iii_dollars is None

    def test_with_dollars(self) -> None:
        """Can specify dollar value when MELT available."""
        ss = ShadowSubsidyTensor(
            year=2022,
            phi_iii_labor_hours=22.0,
            phi_iii_dollars=1.5e12,
            melt_available=True,
        )
        assert ss.melt_available is True
        assert ss.phi_iii_dollars == pytest.approx(1.5e12)

    def test_labor_hours_non_negative(self) -> None:
        """Labor hours must be non-negative."""
        with pytest.raises(ValidationError):
            ShadowSubsidyTensor(year=2022, phi_iii_labor_hours=-1.0)

    def test_frozen(self) -> None:
        """Model is frozen."""
        ss = ShadowSubsidyTensor(year=2022, phi_iii_labor_hours=10.0)
        with pytest.raises(ValidationError):
            ss.year = 2023  # type: ignore[misc]


# =============================================================================
# ClassTransitionMatrix
# =============================================================================


class TestClassTransitionMatrix:
    """Tests for ClassTransitionMatrix model."""

    def test_basic_construction(self) -> None:
        """Can construct a valid stochastic matrix."""
        P = np.array([[0.9, 0.1], [0.3, 0.7]])
        ctm = ClassTransitionMatrix(
            period=(2015, 2020),
            classes=["proletariat", "petit_bourgeois"],
            transition_matrix=P,
        )
        assert ctm.n_classes == 2

    def test_non_stochastic_rejected(self) -> None:
        """Non-stochastic matrix (rows not summing to 1) is rejected."""
        P = np.array([[0.9, 0.2], [0.3, 0.7]])  # row 0 sums to 1.1
        with pytest.raises(ValidationError, match="sum to 1.0"):
            ClassTransitionMatrix(
                period=(2015, 2020),
                classes=["proletariat", "petit_bourgeois"],
                transition_matrix=P,
            )

    def test_shape_mismatch(self) -> None:
        """Shape mismatch raises ValidationError."""
        with pytest.raises(ValidationError, match="shape"):
            ClassTransitionMatrix(
                period=(2015, 2020),
                classes=["A", "B", "C"],
                transition_matrix=np.eye(2),
            )


# =============================================================================
# StationaryDistribution
# =============================================================================


class TestStationaryDistribution:
    """Tests for StationaryDistribution model."""

    def test_basic_construction(self) -> None:
        """Can construct valid stationary distribution."""
        dist = np.array([0.75, 0.25])
        sd = StationaryDistribution(
            period=(2015, 2020),
            classes=["proletariat", "petit_bourgeois"],
            distribution=dist,
        )
        assert sd.n_classes == 2
        assert abs(sd.distribution.sum() - 1.0) < 1e-10

    def test_non_normalized_rejected(self) -> None:
        """Distribution not summing to 1 is rejected."""
        with pytest.raises(ValidationError, match="sum to 1.0"):
            StationaryDistribution(
                period=(2015, 2020),
                classes=["A", "B"],
                distribution=np.array([0.8, 0.3]),  # sums to 1.1
            )

    def test_shape_mismatch(self) -> None:
        """Shape mismatch raises ValidationError."""
        with pytest.raises(ValidationError, match="shape"):
            StationaryDistribution(
                period=(2015, 2020),
                classes=["A", "B", "C"],
                distribution=np.array([0.5, 0.5]),
            )


# =============================================================================
# ReproductionRequirements
# =============================================================================


class TestReproductionRequirements:
    """Tests for ReproductionRequirements model."""

    def test_basic_construction(self) -> None:
        """Can construct with nested dicts."""
        rr = ReproductionRequirements(
            year=2022,
            consumption={"proletariat": {"IIA": {"food": 1500.0, "shelter": 800.0}}},
            reproductive_labor={"proletariat": {"proletariat": {"care": 1200.0}}},
        )
        assert rr.year == 2022

    def test_frozen(self) -> None:
        """Model is frozen."""
        rr = ReproductionRequirements(
            year=2022,
            consumption={},
            reproductive_labor={},
        )
        with pytest.raises(ValidationError):
            rr.year = 2023  # type: ignore[misc]
