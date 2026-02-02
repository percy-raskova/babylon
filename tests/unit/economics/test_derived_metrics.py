"""Unit tests for DerivedTensorMetrics.

Tests for the derived metrics container used in TRPF analysis.

Feature: 012-capital-stock-dynamics
Phase: 4-5 (User Stories 2-3)
Tasks: T035-T054
"""

from __future__ import annotations

import pytest

from babylon.economics.derived_metrics import DerivedTensorMetrics
from babylon.economics.tensor import DepartmentRow, ValueTensor4x3
from babylon.models.types import LaborHours, Probability


def create_test_tensor(
    fips: str = "26163",
    year: int = 2022,
    total_c: float = 400.0,
    total_v: float = 100.0,
    total_s: float = 200.0,
) -> ValueTensor4x3:
    """Create a test tensor with specified totals.

    Distributes values evenly across departments for simplicity.
    """
    c_per_dept = total_c / 4
    v_per_dept = total_v / 4
    s_per_dept = total_s / 4

    return ValueTensor4x3(
        fips_code=fips,
        year=year,
        dept_I=DepartmentRow(c=c_per_dept, v=v_per_dept, s=s_per_dept),
        dept_IIa=DepartmentRow(c=c_per_dept, v=v_per_dept, s=s_per_dept),
        dept_IIb=DepartmentRow(c=c_per_dept, v=v_per_dept, s=s_per_dept),
        dept_III=DepartmentRow(c=c_per_dept, v=v_per_dept, s=s_per_dept),
        naics_granularity=Probability(0.85),
        excluded_wages=LaborHours(0.0),
    )


# =============================================================================
# USER STORY 2: PROFIT RATE TIME SERIES
# =============================================================================


class TestDerivedTensorMetricsCreation:
    """Tests for DerivedTensorMetrics creation and basic attributes."""

    def test_creation_with_all_fields(self) -> None:
        """T035: DerivedTensorMetrics should be creatable with all required fields."""
        tensor = create_test_tensor()

        metrics = DerivedTensorMetrics(
            fips_code="26163",
            year=2022,
            capital_stock=1000.0,
            profit_rate_stock=0.18,  # 200 / (1000 + 100)
            organic_composition=4.0,  # 400 / 100
            exploitation_rate=2.0,  # 200 / 100
            tensor=tensor,
            depreciation_rate=0.07,
        )

        assert metrics.fips_code == "26163"
        assert metrics.year == 2022
        assert metrics.capital_stock == 1000.0
        assert metrics.profit_rate_stock == pytest.approx(0.18)
        assert metrics.organic_composition == pytest.approx(4.0)
        assert metrics.exploitation_rate == pytest.approx(2.0)
        assert metrics.depreciation_rate == 0.07


class TestProfitRateStock:
    """Tests for stock-based profit rate r = s / (K + v)."""

    def test_profit_rate_stock_formula(self) -> None:
        """T036: profit_rate_stock should equal s / (K + v)."""
        tensor = create_test_tensor(total_c=400.0, total_v=100.0, total_s=200.0)
        K = 1000.0

        # r_stock = s / (K + v) = 200 / (1000 + 100) = 200 / 1100 ≈ 0.1818
        expected_r = 200.0 / (1000.0 + 100.0)

        metrics = DerivedTensorMetrics(
            fips_code="26163",
            year=2022,
            capital_stock=K,
            profit_rate_stock=expected_r,
            organic_composition=tensor.organic_composition,
            exploitation_rate=tensor.exploitation_rate,
            tensor=tensor,
            depreciation_rate=0.07,
        )

        assert metrics.profit_rate_stock == pytest.approx(expected_r, rel=0.001)

    def test_profit_rate_stock_returns_inf_when_denominator_zero(self) -> None:
        """T037: profit_rate_stock should be inf when K + v = 0."""
        tensor = create_test_tensor(total_v=0.0, total_s=100.0)
        K = 0.0  # K + v = 0

        metrics = DerivedTensorMetrics(
            fips_code="26163",
            year=2022,
            capital_stock=K,
            profit_rate_stock=float("inf"),
            organic_composition=tensor.organic_composition,
            exploitation_rate=tensor.exploitation_rate,
            tensor=tensor,
            depreciation_rate=0.07,
        )

        assert metrics.profit_rate_stock == float("inf")


class TestProfitRateFlow:
    """Tests for flow-based profit rate from tensor."""

    def test_profit_rate_flow_delegates_to_tensor(self) -> None:
        """T038: profit_rate_flow should return tensor.profit_rate."""
        tensor = create_test_tensor(total_c=400.0, total_v=100.0, total_s=200.0)

        metrics = DerivedTensorMetrics(
            fips_code="26163",
            year=2022,
            capital_stock=1000.0,
            profit_rate_stock=0.18,
            organic_composition=tensor.organic_composition,
            exploitation_rate=tensor.exploitation_rate,
            tensor=tensor,
            depreciation_rate=0.07,
        )

        # Flow rate = s / (c + v) = 200 / (400 + 100) = 0.4
        assert metrics.profit_rate_flow == pytest.approx(tensor.profit_rate)
        assert metrics.profit_rate_flow == pytest.approx(0.4)


class TestToDict:
    """Tests for to_dict() method."""

    def test_to_dict_returns_expected_keys(self) -> None:
        """T039: to_dict() should return dict with expected keys."""
        tensor = create_test_tensor()

        metrics = DerivedTensorMetrics(
            fips_code="26163",
            year=2022,
            capital_stock=1000.0,
            profit_rate_stock=0.18,
            organic_composition=4.0,
            exploitation_rate=2.0,
            tensor=tensor,
            depreciation_rate=0.07,
        )

        result = metrics.to_dict()

        expected_keys = {
            "fips_code",
            "year",
            "capital_stock",
            "profit_rate_stock",
            "profit_rate_flow",
            "organic_composition",
            "exploitation_rate",
            "depreciation_rate",
            "total_c",
            "total_v",
            "total_s",
        }

        assert set(result.keys()) == expected_keys

    def test_to_dict_values_are_serializable(self) -> None:
        """to_dict() values should be JSON-serializable."""
        import json

        tensor = create_test_tensor()

        metrics = DerivedTensorMetrics(
            fips_code="26163",
            year=2022,
            capital_stock=1000.0,
            profit_rate_stock=0.18,
            organic_composition=4.0,
            exploitation_rate=2.0,
            tensor=tensor,
            depreciation_rate=0.07,
        )

        result = metrics.to_dict()

        # Should not raise
        json_str = json.dumps(result)
        assert len(json_str) > 0


# =============================================================================
# USER STORY 3: OCC AND EXPLOITATION RATE
# =============================================================================


class TestOrganicComposition:
    """Tests for organic composition of capital (OCC = c/v)."""

    def test_organic_composition_formula(self) -> None:
        """T048: organic_composition should equal c / v."""
        tensor = create_test_tensor(total_c=400.0, total_v=100.0)

        metrics = DerivedTensorMetrics(
            fips_code="26163",
            year=2022,
            capital_stock=1000.0,
            profit_rate_stock=0.18,
            organic_composition=tensor.organic_composition,
            exploitation_rate=tensor.exploitation_rate,
            tensor=tensor,
            depreciation_rate=0.07,
        )

        # OCC = c/v = 400/100 = 4.0
        assert metrics.organic_composition == pytest.approx(4.0)

    def test_organic_composition_returns_inf_when_v_zero(self) -> None:
        """T050: OCC should return inf when v = 0."""
        tensor = create_test_tensor(total_c=400.0, total_v=0.0)

        metrics = DerivedTensorMetrics(
            fips_code="26163",
            year=2022,
            capital_stock=1000.0,
            profit_rate_stock=0.0,
            organic_composition=tensor.organic_composition,
            exploitation_rate=tensor.exploitation_rate,
            tensor=tensor,
            depreciation_rate=0.07,
        )

        assert metrics.organic_composition == float("inf")


class TestExploitationRate:
    """Tests for exploitation rate (e = s/v)."""

    def test_exploitation_rate_formula(self) -> None:
        """T049: exploitation_rate should equal s / v."""
        tensor = create_test_tensor(total_v=100.0, total_s=200.0)

        metrics = DerivedTensorMetrics(
            fips_code="26163",
            year=2022,
            capital_stock=1000.0,
            profit_rate_stock=0.18,
            organic_composition=tensor.organic_composition,
            exploitation_rate=tensor.exploitation_rate,
            tensor=tensor,
            depreciation_rate=0.07,
        )

        # e = s/v = 200/100 = 2.0
        assert metrics.exploitation_rate == pytest.approx(2.0)

    def test_exploitation_rate_returns_inf_when_v_zero(self) -> None:
        """T051: exploitation_rate should return inf when v = 0."""
        tensor = create_test_tensor(total_v=0.0, total_s=200.0)

        metrics = DerivedTensorMetrics(
            fips_code="26163",
            year=2022,
            capital_stock=1000.0,
            profit_rate_stock=float("inf"),
            organic_composition=tensor.organic_composition,
            exploitation_rate=tensor.exploitation_rate,
            tensor=tensor,
            depreciation_rate=0.07,
        )

        assert metrics.exploitation_rate == float("inf")


# =============================================================================
# IMMUTABILITY
# =============================================================================


class TestDerivedTensorMetricsImmutability:
    """Tests for DerivedTensorMetrics immutability."""

    def test_is_frozen_dataclass(self) -> None:
        """DerivedTensorMetrics should be immutable (frozen dataclass)."""
        tensor = create_test_tensor()

        metrics = DerivedTensorMetrics(
            fips_code="26163",
            year=2022,
            capital_stock=1000.0,
            profit_rate_stock=0.18,
            organic_composition=4.0,
            exploitation_rate=2.0,
            tensor=tensor,
            depreciation_rate=0.07,
        )

        from dataclasses import FrozenInstanceError

        with pytest.raises(FrozenInstanceError):
            metrics.capital_stock = 2000.0  # type: ignore[misc]
