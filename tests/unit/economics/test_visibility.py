"""Tests for visibility tensor shadow labor calculations.

Sprint 2.1: The Visibility Tensor
Verifies the Fortunati model of shadow labor visibility.

The visibility scalar g₃₃ controls what fraction of Department III
(reproductive labor) is visible to the price system:
- g₃₃ = 1.0: All Dept III labor is monetized (standard Marxian analysis)
- g₃₃ = 0.0: All Dept III labor is unpaid (extreme invisibility)
- g₃₃ = 0.5: Half paid, half unpaid (realistic estimate)

See Also:
    Fortunati, Leopoldina. "The Arcane of Reproduction" (1981).
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.tensor import DepartmentRow, ValueTensor4x3
from babylon.models import Currency


class TestVisibilityG33Field:
    """Test visibility_g33 field validation."""

    def test_default_visibility_is_fully_visible(self) -> None:
        """Default g33=1.0 for backward compatibility."""
        tensor = self._create_tensor()
        assert tensor.visibility_g33 == 1.0

    def test_visibility_accepts_zero(self) -> None:
        """g33=0.0 means all Dept III labor is unwaged."""
        tensor = self._create_tensor(visibility_g33=0.0)
        assert tensor.visibility_g33 == 0.0

    def test_visibility_accepts_fractional(self) -> None:
        """g33=0.5 means half visible, half shadow."""
        tensor = self._create_tensor(visibility_g33=0.5)
        assert tensor.visibility_g33 == 0.5

    def test_visibility_rejects_negative(self) -> None:
        """Negative visibility is invalid."""
        with pytest.raises(ValueError):
            self._create_tensor(visibility_g33=-0.1)

    def test_visibility_rejects_over_one(self) -> None:
        """Visibility > 1.0 is invalid."""
        with pytest.raises(ValueError):
            self._create_tensor(visibility_g33=1.1)

    @staticmethod
    def _create_tensor(visibility_g33: float = 1.0) -> ValueTensor4x3:
        """Factory for test tensors."""
        dept = DepartmentRow(c=Currency(100.0), v=Currency(50.0), s=Currency(50.0))
        return ValueTensor4x3(
            fips_code="12345",
            year=2020,
            dept_I=dept,
            dept_IIa=dept,
            dept_IIb=dept,
            dept_III=dept,
            naics_granularity=0.85,
            excluded_wages=Currency(0.0),
            visibility_g33=visibility_g33,
        )


class TestTotalS:
    """Test total_s computed property."""

    def test_total_s_sums_all_departments(self) -> None:
        """total_s should sum surplus value across all departments."""
        tensor = self._create_tensor()
        # Each dept has s=50, so total_s = 50*4 = 200
        assert tensor.total_s == pytest.approx(200.0)

    def test_total_s_with_varying_departments(self) -> None:
        """total_s handles departments with different surplus values."""
        dept_I = DepartmentRow(c=Currency(100.0), v=Currency(50.0), s=Currency(100.0))
        dept_IIa = DepartmentRow(c=Currency(100.0), v=Currency(50.0), s=Currency(50.0))
        dept_IIb = DepartmentRow(c=Currency(100.0), v=Currency(50.0), s=Currency(75.0))
        dept_III = DepartmentRow(c=Currency(100.0), v=Currency(50.0), s=Currency(25.0))
        tensor = ValueTensor4x3(
            fips_code="12345",
            year=2020,
            dept_I=dept_I,
            dept_IIa=dept_IIa,
            dept_IIb=dept_IIb,
            dept_III=dept_III,
            naics_granularity=0.85,
            excluded_wages=Currency(0.0),
        )
        # total_s = 100 + 50 + 75 + 25 = 250
        assert tensor.total_s == pytest.approx(250.0)

    @staticmethod
    def _create_tensor() -> ValueTensor4x3:
        dept = DepartmentRow(c=Currency(100.0), v=Currency(50.0), s=Currency(50.0))
        return ValueTensor4x3(
            fips_code="12345",
            year=2020,
            dept_I=dept,
            dept_IIa=dept,
            dept_IIb=dept,
            dept_III=dept,
            naics_granularity=0.85,
            excluded_wages=Currency(0.0),
        )


class TestMonetizedValue:
    """Test monetized_value computed property."""

    def test_full_visibility_equals_total_value(self) -> None:
        """When g33=1.0, monetized_value equals total_value."""
        tensor = self._create_tensor(visibility_g33=1.0)
        assert tensor.monetized_value == pytest.approx(tensor.total_value)

    def test_zero_visibility_excludes_dept_iii(self) -> None:
        """When g33=0.0, Dept III is fully excluded from monetized value."""
        tensor = self._create_tensor(visibility_g33=0.0)
        expected = (
            tensor.dept_I.total_value + tensor.dept_IIa.total_value + tensor.dept_IIb.total_value
        )
        assert tensor.monetized_value == pytest.approx(expected)

    def test_half_visibility_includes_half_dept_iii(self) -> None:
        """When g33=0.5, half of Dept III is monetized."""
        tensor = self._create_tensor(visibility_g33=0.5)
        expected = (
            tensor.dept_I.total_value
            + tensor.dept_IIa.total_value
            + tensor.dept_IIb.total_value
            + tensor.dept_III.total_value * 0.5
        )
        assert tensor.monetized_value == pytest.approx(expected)

    @staticmethod
    def _create_tensor(visibility_g33: float) -> ValueTensor4x3:
        dept = DepartmentRow(c=Currency(100.0), v=Currency(50.0), s=Currency(50.0))
        return ValueTensor4x3(
            fips_code="12345",
            year=2020,
            dept_I=dept,
            dept_IIa=dept,
            dept_IIb=dept,
            dept_III=dept,
            naics_granularity=0.85,
            excluded_wages=Currency(0.0),
            visibility_g33=visibility_g33,
        )


class TestShadowSubsidy:
    """Test shadow_subsidy computed property."""

    def test_full_visibility_has_zero_shadow(self) -> None:
        """When g33=1.0, no shadow subsidy (all labor paid)."""
        tensor = self._create_tensor(dept_iii_v=100.0, visibility_g33=1.0)
        assert tensor.shadow_subsidy == pytest.approx(0.0)

    def test_zero_visibility_full_shadow(self) -> None:
        """When g33=0.0, shadow_subsidy equals Dept III variable capital."""
        tensor = self._create_tensor(dept_iii_v=100.0, visibility_g33=0.0)
        assert tensor.shadow_subsidy == pytest.approx(100.0)

    def test_half_visibility_half_shadow(self) -> None:
        """When g33=0.5, shadow_subsidy is half of Dept III v."""
        tensor = self._create_tensor(dept_iii_v=100.0, visibility_g33=0.5)
        assert tensor.shadow_subsidy == pytest.approx(50.0)

    @staticmethod
    def _create_tensor(dept_iii_v: float, visibility_g33: float) -> ValueTensor4x3:
        standard_dept = DepartmentRow(c=Currency(100.0), v=Currency(50.0), s=Currency(50.0))
        dept_iii = DepartmentRow(c=Currency(50.0), v=Currency(dept_iii_v), s=Currency(30.0))
        return ValueTensor4x3(
            fips_code="12345",
            year=2020,
            dept_I=standard_dept,
            dept_IIa=standard_dept,
            dept_IIb=standard_dept,
            dept_III=dept_iii,
            naics_granularity=0.85,
            excluded_wages=Currency(0.0),
            visibility_g33=visibility_g33,
        )


class TestMonetizedV:
    """Test monetized_v computed property."""

    def test_full_visibility_equals_total_v(self) -> None:
        """When g33=1.0, monetized_v equals total_v."""
        tensor = self._create_tensor(visibility_g33=1.0)
        assert tensor.monetized_v == pytest.approx(tensor.total_v)

    def test_zero_visibility_excludes_dept_iii_v(self) -> None:
        """When g33=0.0, Dept III wages are excluded."""
        tensor = self._create_tensor(visibility_g33=0.0)
        expected = tensor.dept_I.v + tensor.dept_IIa.v + tensor.dept_IIb.v
        assert tensor.monetized_v == pytest.approx(expected)

    def test_half_visibility_includes_half_dept_iii_v(self) -> None:
        """When g33=0.5, half of Dept III wages are monetized."""
        tensor = self._create_tensor(visibility_g33=0.5)
        expected = tensor.dept_I.v + tensor.dept_IIa.v + tensor.dept_IIb.v + tensor.dept_III.v * 0.5
        assert tensor.monetized_v == pytest.approx(expected)

    @staticmethod
    def _create_tensor(visibility_g33: float) -> ValueTensor4x3:
        dept = DepartmentRow(c=Currency(100.0), v=Currency(50.0), s=Currency(50.0))
        return ValueTensor4x3(
            fips_code="12345",
            year=2020,
            dept_I=dept,
            dept_IIa=dept,
            dept_IIb=dept,
            dept_III=dept,
            naics_granularity=0.85,
            excluded_wages=Currency(0.0),
            visibility_g33=visibility_g33,
        )


class TestExploitationRateFortunati:
    """Test exploitation_rate_fortunati computed property.

    Key insight from Fortunati: Shadow labor is APPROPRIATED SURPLUS,
    not merely reduced costs. The denominator is monetized_v (wages
    actually paid), not total_v minus shadow.
    """

    def test_full_visibility_equals_standard_rate(self) -> None:
        """When g33=1.0, Fortunati rate equals standard exploitation rate."""
        tensor = self._create_tensor(visibility_g33=1.0)
        # When fully visible, monetized_v = total_v, shadow = 0
        standard_rate = tensor.total_s / tensor.total_v
        assert tensor.exploitation_rate_fortunati == pytest.approx(standard_rate)

    def test_reduced_visibility_increases_rate(self) -> None:
        """Shadow labor increases apparent exploitation."""
        tensor_full = self._create_tensor(visibility_g33=1.0)
        tensor_half = self._create_tensor(visibility_g33=0.5)

        # Fortunati rate should be higher when shadow labor is recognized
        assert tensor_half.exploitation_rate_fortunati > tensor_full.exploitation_rate_fortunati

    def test_fortunati_formula_300_percent(self) -> None:
        """Verify the canonical 300% exploitation rate example.

        Scenario (Dept III only focus):
            - Dept III: v=100, s=100, g₃₃=0.5
            - monetized_v = 100 * 0.5 = 50
            - shadow_subsidy = 100 * (1 - 0.5) = 50
            - total_surplus = 100 (market) + 50 (shadow) = 150
            - Fortunati rate = 150 / 50 = 3.0 = 300%

        Compare to standard rate: 100 / 100 = 100%
        The shadow labor TRIPLES the apparent exploitation.
        """
        # Isolate Dept III by giving other depts zero v and s
        dept_zero = DepartmentRow(c=Currency(100.0), v=Currency(0.0), s=Currency(0.0))
        dept_iii = DepartmentRow(c=Currency(50.0), v=Currency(100.0), s=Currency(100.0))
        tensor = ValueTensor4x3(
            fips_code="12345",
            year=2020,
            dept_I=dept_zero,
            dept_IIa=dept_zero,
            dept_IIb=dept_zero,
            dept_III=dept_iii,
            naics_granularity=0.85,
            excluded_wages=Currency(0.0),
            visibility_g33=0.5,
        )

        # Verify intermediate values
        assert tensor.total_s == pytest.approx(100.0)  # Only Dept III s
        assert tensor.shadow_subsidy == pytest.approx(50.0)  # 100 * 0.5
        assert tensor.monetized_v == pytest.approx(50.0)  # 100 * 0.5

        # Fortunati rate = (100 + 50) / 50 = 3.0 = 300%
        assert tensor.exploitation_rate_fortunati == pytest.approx(3.0)

    def test_fortunati_vs_standard_comparison(self) -> None:
        """Explicitly compare Fortunati rate to standard rate."""
        dept_zero = DepartmentRow(c=Currency(100.0), v=Currency(0.0), s=Currency(0.0))
        dept_iii = DepartmentRow(c=Currency(50.0), v=Currency(100.0), s=Currency(100.0))
        tensor = ValueTensor4x3(
            fips_code="12345",
            year=2020,
            dept_I=dept_zero,
            dept_IIa=dept_zero,
            dept_IIb=dept_zero,
            dept_III=dept_iii,
            naics_granularity=0.85,
            excluded_wages=Currency(0.0),
            visibility_g33=0.5,
        )

        # Standard rate (ignores shadow): s/v = 100/100 = 1.0
        standard_rate = tensor.total_s / tensor.total_v
        assert standard_rate == pytest.approx(1.0)

        # Fortunati rate (recognizes shadow): (s + shadow) / monetized_v = 150/50 = 3.0
        assert tensor.exploitation_rate_fortunati == pytest.approx(3.0)

        # Fortunati rate is 3x the standard rate
        assert tensor.exploitation_rate_fortunati / standard_rate == pytest.approx(3.0)

    def test_zero_monetized_v_returns_infinity(self) -> None:
        """When all labor is unpaid (monetized_v=0), rate is infinite."""
        # g33=0.0 and only Dept III has wages → monetized_v = 0
        dept_zero_v = DepartmentRow(c=Currency(100.0), v=Currency(0.0), s=Currency(50.0))
        dept_iii = DepartmentRow(c=Currency(50.0), v=Currency(200.0), s=Currency(30.0))
        tensor = ValueTensor4x3(
            fips_code="12345",
            year=2020,
            dept_I=dept_zero_v,
            dept_IIa=dept_zero_v,
            dept_IIb=dept_zero_v,
            dept_III=dept_iii,
            naics_granularity=0.85,
            excluded_wages=Currency(0.0),
            visibility_g33=0.0,
        )
        # monetized_v = 0 + 0 + 0 + (200 * 0.0) = 0
        assert tensor.monetized_v == pytest.approx(0.0)
        assert tensor.exploitation_rate_fortunati == float("inf")

    @staticmethod
    def _create_tensor(visibility_g33: float) -> ValueTensor4x3:
        dept = DepartmentRow(c=Currency(100.0), v=Currency(50.0), s=Currency(50.0))
        return ValueTensor4x3(
            fips_code="12345",
            year=2020,
            dept_I=dept,
            dept_IIa=dept,
            dept_IIb=dept,
            dept_III=dept,
            naics_granularity=0.85,
            excluded_wages=Currency(0.0),
            visibility_g33=visibility_g33,
        )
