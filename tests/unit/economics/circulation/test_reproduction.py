"""Tests for Capital Volume II: Reproduction Schema (US4).

Feature: 023-capital-volume-ii
Tasks: T048-T054 (FR-012, FR-013, FR-014)

Tests for combine_departments_ii, check_simple_reproduction,
check_extended_reproduction, and compute_disproportionality functions.
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.circulation.reproduction import (
    check_extended_reproduction,
    check_simple_reproduction,
    combine_departments_ii,
    compute_disproportionality,
)
from babylon.domain.economics.circulation.types import (
    DisproportionalityCrisis,
)
from babylon.domain.economics.tensor import DepartmentRow
from babylon.models.types import Currency, LaborHours

# =============================================================================
# T048: combine_departments_ii
# =============================================================================


class TestCombineDepartmentsII:
    """Tests for combine_departments_ii (FR-012)."""

    def test_sums_correctly(self) -> None:
        """IIa + IIb components sum into combined Department II."""
        dept_iia = DepartmentRow(
            c=LaborHours(150.0),
            v=LaborHours(75.0),
            s=LaborHours(75.0),
        )
        dept_iib = DepartmentRow(
            c=LaborHours(50.0),
            v=LaborHours(25.0),
            s=LaborHours(25.0),
        )
        result = combine_departments_ii(dept_iia, dept_iib)
        assert result.c == pytest.approx(200.0)
        assert result.v == pytest.approx(100.0)
        assert result.s == pytest.approx(100.0)

    def test_total_value_of_combined(self) -> None:
        """Combined total_value equals sum of IIa and IIb total_values."""
        dept_iia = DepartmentRow(
            c=LaborHours(100.0),
            v=LaborHours(50.0),
            s=LaborHours(50.0),
        )
        dept_iib = DepartmentRow(
            c=LaborHours(30.0),
            v=LaborHours(20.0),
            s=LaborHours(10.0),
        )
        result = combine_departments_ii(dept_iia, dept_iib)
        expected_total = 100.0 + 50.0 + 50.0 + 30.0 + 20.0 + 10.0
        assert result.total_value == pytest.approx(expected_total)

    def test_zero_dept_iib(self) -> None:
        """When IIb is zero, combined equals IIa."""
        dept_iia = DepartmentRow(
            c=LaborHours(100.0),
            v=LaborHours(50.0),
            s=LaborHours(50.0),
        )
        dept_iib = DepartmentRow(
            c=LaborHours(0.0),
            v=LaborHours(0.0),
            s=LaborHours(0.0),
        )
        result = combine_departments_ii(dept_iia, dept_iib)
        assert result.c == pytest.approx(100.0)
        assert result.v == pytest.approx(50.0)
        assert result.s == pytest.approx(50.0)


# =============================================================================
# T049-T051: check_simple_reproduction (SC-003)
# =============================================================================


class TestCheckSimpleReproduction:
    """Tests for check_simple_reproduction (FR-013).

    The simple reproduction condition is I(v+s) = IIc.
    If I(v+s) > IIc, overproduction in Dept I.
    If I(v+s) < IIc, underproduction in Dept I.
    """

    def test_balanced_reproduction(self) -> None:
        """SC-003 case 1: I(v=30, s=20), II(c=50) -> gap=0, BALANCED."""
        dept_i = DepartmentRow(
            c=LaborHours(100.0),
            v=LaborHours(30.0),
            s=LaborHours(20.0),
        )
        dept_ii = DepartmentRow(
            c=LaborHours(50.0),
            v=LaborHours(25.0),
            s=LaborHours(25.0),
        )
        result = check_simple_reproduction(dept_i, dept_ii)
        assert result.condition_met is True
        assert result.gap == pytest.approx(0.0)
        assert result.interpretation == "BALANCED"

    def test_overproduction_dept_i(self) -> None:
        """SC-003 case 2: I(v=30, s=30), II(c=40) -> gap=+20, OVERPRODUCTION."""
        dept_i = DepartmentRow(
            c=LaborHours(100.0),
            v=LaborHours(30.0),
            s=LaborHours(30.0),
        )
        dept_ii = DepartmentRow(
            c=LaborHours(40.0),
            v=LaborHours(25.0),
            s=LaborHours(25.0),
        )
        result = check_simple_reproduction(dept_i, dept_ii)
        assert result.condition_met is False
        assert result.gap == pytest.approx(20.0)
        assert result.interpretation == "OVERPRODUCTION_DEPT_I"

    def test_underproduction_dept_i(self) -> None:
        """SC-003 case 3: I(v=20, s=10), II(c=50) -> gap=-20, UNDERPRODUCTION."""
        dept_i = DepartmentRow(
            c=LaborHours(100.0),
            v=LaborHours(20.0),
            s=LaborHours(10.0),
        )
        dept_ii = DepartmentRow(
            c=LaborHours(50.0),
            v=LaborHours(25.0),
            s=LaborHours(25.0),
        )
        result = check_simple_reproduction(dept_i, dept_ii)
        assert result.condition_met is False
        assert result.gap == pytest.approx(-20.0)
        assert result.interpretation == "UNDERPRODUCTION_DEPT_I"

    def test_large_balanced_surplus(self) -> None:
        """SC-003 case 4: I(v=100, s=200), II(c=300) -> gap=0, BALANCED."""
        dept_i = DepartmentRow(
            c=LaborHours(500.0),
            v=LaborHours(100.0),
            s=LaborHours(200.0),
        )
        dept_ii = DepartmentRow(
            c=LaborHours(300.0),
            v=LaborHours(100.0),
            s=LaborHours(100.0),
        )
        result = check_simple_reproduction(dept_i, dept_ii)
        assert result.condition_met is True
        assert result.gap == pytest.approx(0.0)
        assert result.interpretation == "BALANCED"

    def test_zero_v_balanced(self) -> None:
        """SC-003 case 5: I(v=0, s=50), II(c=50) -> gap=0, BALANCED."""
        dept_i = DepartmentRow(
            c=LaborHours(200.0),
            v=LaborHours(0.0),
            s=LaborHours(50.0),
        )
        dept_ii = DepartmentRow(
            c=LaborHours(50.0),
            v=LaborHours(30.0),
            s=LaborHours(20.0),
        )
        result = check_simple_reproduction(dept_i, dept_ii)
        assert result.condition_met is True
        assert result.gap == pytest.approx(0.0)
        assert result.interpretation == "BALANCED"

    def test_tolerance_within_threshold(self) -> None:
        """A gap smaller than tolerance should still be BALANCED."""
        dept_i = DepartmentRow(
            c=LaborHours(100.0),
            v=LaborHours(30.0),
            s=LaborHours(20.005),
        )
        dept_ii = DepartmentRow(
            c=LaborHours(50.0),
            v=LaborHours(25.0),
            s=LaborHours(25.0),
        )
        result = check_simple_reproduction(dept_i, dept_ii, tolerance=0.01)
        assert result.condition_met is True
        assert result.interpretation == "BALANCED"

    def test_custom_tolerance(self) -> None:
        """Custom tolerance changes what counts as balanced."""
        dept_i = DepartmentRow(
            c=LaborHours(100.0),
            v=LaborHours(30.0),
            s=LaborHours(25.0),
        )
        dept_ii = DepartmentRow(
            c=LaborHours(50.0),
            v=LaborHours(25.0),
            s=LaborHours(25.0),
        )
        # gap = (30 + 25) - 50 = 5.0
        # With tolerance=0.01, not balanced
        result_strict = check_simple_reproduction(dept_i, dept_ii, tolerance=0.01)
        assert result_strict.condition_met is False

        # With tolerance=10.0, balanced
        result_loose = check_simple_reproduction(dept_i, dept_ii, tolerance=10.0)
        assert result_loose.condition_met is True


# =============================================================================
# T052-T053: check_extended_reproduction
# =============================================================================


class TestCheckExtendedReproduction:
    """Tests for check_extended_reproduction (FR-013).

    Extended reproduction checks if Dept III can reproduce all
    departments' labor power: labor_power_demand = I.v + II.v + III.v,
    reproduction_capacity = III.c + III.v + III.s.
    """

    def test_sustainable_reproduction(self) -> None:
        """Reproduction capacity >= demand means sustainable."""
        dept_i = DepartmentRow(
            c=LaborHours(200.0),
            v=LaborHours(100.0),
            s=LaborHours(100.0),
        )
        dept_ii = DepartmentRow(
            c=LaborHours(150.0),
            v=LaborHours(75.0),
            s=LaborHours(75.0),
        )
        dept_iii = DepartmentRow(
            c=LaborHours(100.0),
            v=LaborHours(50.0),
            s=LaborHours(100.0),
        )
        result = check_extended_reproduction(dept_i, dept_ii, dept_iii)
        # demand = 100 + 75 + 50 = 225
        # capacity = 100 + 50 + 100 = 250
        # gap = 225 - 250 = -25
        assert result.labor_power_demand == pytest.approx(225.0)
        assert result.reproduction_capacity == pytest.approx(250.0)
        assert result.gap == pytest.approx(-25.0)
        assert result.sustainability is True

    def test_unsustainable_reproduction(self) -> None:
        """Reproduction capacity < demand means unsustainable."""
        dept_i = DepartmentRow(
            c=LaborHours(200.0),
            v=LaborHours(150.0),
            s=LaborHours(100.0),
        )
        dept_ii = DepartmentRow(
            c=LaborHours(150.0),
            v=LaborHours(100.0),
            s=LaborHours(75.0),
        )
        dept_iii = DepartmentRow(
            c=LaborHours(30.0),
            v=LaborHours(20.0),
            s=LaborHours(10.0),
        )
        result = check_extended_reproduction(dept_i, dept_ii, dept_iii)
        # demand = 150 + 100 + 20 = 270
        # capacity = 30 + 20 + 10 = 60
        # gap = 270 - 60 = 210
        assert result.labor_power_demand == pytest.approx(270.0)
        assert result.reproduction_capacity == pytest.approx(60.0)
        assert result.gap == pytest.approx(210.0)
        assert result.sustainability is False

    def test_dept_iii_zero_output(self) -> None:
        """Dept III with zero output cannot reproduce any labor power."""
        dept_i = DepartmentRow(
            c=LaborHours(100.0),
            v=LaborHours(50.0),
            s=LaborHours(50.0),
        )
        dept_ii = DepartmentRow(
            c=LaborHours(80.0),
            v=LaborHours(40.0),
            s=LaborHours(40.0),
        )
        dept_iii = DepartmentRow(
            c=LaborHours(0.0),
            v=LaborHours(0.0),
            s=LaborHours(0.0),
        )
        result = check_extended_reproduction(dept_i, dept_ii, dept_iii)
        # demand = 50 + 40 + 0 = 90
        # capacity = 0 + 0 + 0 = 0
        # gap = 90 - 0 = 90
        assert result.labor_power_demand == pytest.approx(90.0)
        assert result.reproduction_capacity == pytest.approx(0.0)
        assert result.gap == pytest.approx(90.0)
        assert result.sustainability is False

    def test_exact_balance(self) -> None:
        """When demand exactly equals capacity, sustainable (gap=0)."""
        dept_i = DepartmentRow(
            c=LaborHours(100.0),
            v=LaborHours(50.0),
            s=LaborHours(50.0),
        )
        dept_ii = DepartmentRow(
            c=LaborHours(80.0),
            v=LaborHours(30.0),
            s=LaborHours(40.0),
        )
        dept_iii = DepartmentRow(
            c=LaborHours(30.0),
            v=LaborHours(20.0),
            s=LaborHours(50.0),
        )
        result = check_extended_reproduction(dept_i, dept_ii, dept_iii)
        # demand = 50 + 30 + 20 = 100
        # capacity = 30 + 20 + 50 = 100
        # gap = 100 - 100 = 0
        assert result.gap == pytest.approx(0.0)
        assert result.sustainability is True


# =============================================================================
# T054: compute_disproportionality
# =============================================================================


class TestComputeDisproportionality:
    """Tests for compute_disproportionality (FR-014)."""

    def test_over_industrialized(self) -> None:
        """Dept I output exceeds required share -> over-industrialized."""
        result = compute_disproportionality(
            dept_i_output=Currency(600.0),
            dept_ii_output=Currency(400.0),
            dept_i_share_required=0.55,
        )
        assert isinstance(result, DisproportionalityCrisis)
        assert result.actual_i_share == pytest.approx(0.6)
        assert result.imbalance == pytest.approx(0.05)
        assert result.imbalance_direction == "OVERPRODUCTION_MEANS_PRODUCTION"

    def test_under_industrialized(self) -> None:
        """Dept I output below required share -> under-industrialized."""
        result = compute_disproportionality(
            dept_i_output=Currency(400.0),
            dept_ii_output=Currency(600.0),
            dept_i_share_required=0.55,
        )
        assert result.actual_i_share == pytest.approx(0.4)
        assert result.imbalance == pytest.approx(-0.15)
        assert result.imbalance_direction == "OVERPRODUCTION_CONSUMPTION_GOODS"

    def test_balanced_departments(self) -> None:
        """Dept I share matches required -> BALANCED."""
        result = compute_disproportionality(
            dept_i_output=Currency(550.0),
            dept_ii_output=Currency(450.0),
            dept_i_share_required=0.55,
        )
        assert result.actual_i_share == pytest.approx(0.55)
        assert result.imbalance == pytest.approx(0.0)
        assert result.imbalance_direction == "BALANCED"

    def test_year_is_current(self) -> None:
        """Result includes year field (default current year)."""
        result = compute_disproportionality(
            dept_i_output=Currency(500.0),
            dept_ii_output=Currency(500.0),
            dept_i_share_required=0.5,
        )
        assert isinstance(result.year, int)

    def test_extreme_imbalance(self) -> None:
        """Nearly all output in Dept I."""
        result = compute_disproportionality(
            dept_i_output=Currency(950.0),
            dept_ii_output=Currency(50.0),
            dept_i_share_required=0.5,
        )
        assert result.actual_i_share == pytest.approx(0.95)
        assert result.imbalance == pytest.approx(0.45)
        assert result.imbalance_direction == "OVERPRODUCTION_MEANS_PRODUCTION"
