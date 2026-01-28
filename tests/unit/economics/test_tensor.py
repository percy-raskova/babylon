"""Unit tests for Marxian value tensor models.

Tests for DepartmentRow and ValueTensor4x3 Pydantic models that represent
the 4x3 Marxian reproduction schema (4 departments x 3 value categories).

TDD RED PHASE: These tests will fail until tensor.py is implemented.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

# These imports will fail until we implement the module (RED phase)
from babylon.economics.tensor import DepartmentRow, ValueTensor4x3


class TestDepartmentRow:
    """Tests for DepartmentRow model representing a single department's value composition."""

    def test_create_valid_department_row(self) -> None:
        """DepartmentRow accepts valid c, v, s values."""
        row = DepartmentRow(c=100.0, v=50.0, s=75.0)
        assert row.c == 100.0
        assert row.v == 50.0
        assert row.s == 75.0

    def test_department_row_is_frozen(self) -> None:
        """DepartmentRow is immutable after creation."""
        row = DepartmentRow(c=100.0, v=50.0, s=75.0)
        with pytest.raises(ValidationError):
            row.c = 200.0  # type: ignore[misc]

    def test_rejects_negative_constant_capital(self) -> None:
        """Constant capital (c) must be non-negative Currency."""
        with pytest.raises(ValidationError):
            DepartmentRow(c=-10.0, v=50.0, s=75.0)

    def test_rejects_negative_variable_capital(self) -> None:
        """Variable capital (v) must be non-negative Currency."""
        with pytest.raises(ValidationError):
            DepartmentRow(c=100.0, v=-5.0, s=75.0)

    def test_rejects_negative_surplus_value(self) -> None:
        """Surplus value (s) must be non-negative Currency."""
        with pytest.raises(ValidationError):
            DepartmentRow(c=100.0, v=50.0, s=-25.0)

    def test_allows_zero_values(self) -> None:
        """DepartmentRow allows zero for any value component."""
        row = DepartmentRow(c=0.0, v=0.0, s=0.0)
        assert row.c == 0.0
        assert row.v == 0.0
        assert row.s == 0.0

    def test_total_value_computed_field(self) -> None:
        """total_value = c + v + s (commodity value)."""
        row = DepartmentRow(c=100.0, v=50.0, s=75.0)
        assert row.total_value == 225.0

    def test_organic_composition_computed_field(self) -> None:
        """organic_composition = c / v (Marx's organic composition of capital)."""
        row = DepartmentRow(c=100.0, v=50.0, s=75.0)
        assert row.organic_composition == pytest.approx(2.0)

    def test_organic_composition_zero_v_returns_infinity(self) -> None:
        """Division by zero for organic_composition returns float('inf')."""
        row = DepartmentRow(c=100.0, v=0.0, s=0.0)
        assert row.organic_composition == float("inf")

    def test_exploitation_rate_computed_field(self) -> None:
        """exploitation_rate = s / v (rate of surplus value extraction)."""
        row = DepartmentRow(c=100.0, v=50.0, s=75.0)
        assert row.exploitation_rate == pytest.approx(1.5)

    def test_exploitation_rate_zero_v_returns_infinity(self) -> None:
        """Division by zero for exploitation_rate returns float('inf')."""
        row = DepartmentRow(c=100.0, v=0.0, s=75.0)
        assert row.exploitation_rate == float("inf")

    def test_large_values(self) -> None:
        """DepartmentRow handles large economic values."""
        row = DepartmentRow(
            c=1_000_000_000.0,  # $1B
            v=500_000_000.0,  # $500M
            s=750_000_000.0,  # $750M
        )
        assert row.total_value == 2_250_000_000.0
        assert row.organic_composition == pytest.approx(2.0)


class TestValueTensor4x3:
    """Tests for ValueTensor4x3 representing full 4-department reproduction schema."""

    @pytest.fixture
    def dept_I(self) -> DepartmentRow:
        """Dept I: Means of Production (capital-intensive)."""
        return DepartmentRow(c=300.0, v=100.0, s=200.0)

    @pytest.fixture
    def dept_IIa(self) -> DepartmentRow:
        """Dept IIa: Necessary Consumption (wage goods)."""
        return DepartmentRow(c=150.0, v=100.0, s=100.0)

    @pytest.fixture
    def dept_IIb(self) -> DepartmentRow:
        """Dept IIb: Luxury Consumption (bourgeois goods)."""
        return DepartmentRow(c=250.0, v=100.0, s=300.0)

    @pytest.fixture
    def dept_III(self) -> DepartmentRow:
        """Dept III: Social Reproduction (care work)."""
        return DepartmentRow(c=50.0, v=100.0, s=70.0)

    def test_create_valid_tensor(
        self,
        dept_I: DepartmentRow,
        dept_IIa: DepartmentRow,
        dept_IIb: DepartmentRow,
        dept_III: DepartmentRow,
    ) -> None:
        """ValueTensor4x3 accepts valid FIPS code, year, and four departments."""
        tensor = ValueTensor4x3(
            fips_code="26163",  # Wayne County, MI
            year=2022,
            dept_I=dept_I,
            dept_IIa=dept_IIa,
            dept_IIb=dept_IIb,
            dept_III=dept_III,
            naics_granularity=0.85,
            excluded_wages=50000.0,
        )
        assert tensor.fips_code == "26163"
        assert tensor.year == 2022
        assert tensor.dept_I.c == 300.0

    def test_tensor_is_frozen(
        self,
        dept_I: DepartmentRow,
        dept_IIa: DepartmentRow,
        dept_IIb: DepartmentRow,
        dept_III: DepartmentRow,
    ) -> None:
        """ValueTensor4x3 is immutable after creation."""
        tensor = ValueTensor4x3(
            fips_code="26163",
            year=2022,
            dept_I=dept_I,
            dept_IIa=dept_IIa,
            dept_IIb=dept_IIb,
            dept_III=dept_III,
            naics_granularity=0.85,
            excluded_wages=50000.0,
        )
        with pytest.raises(ValidationError):
            tensor.year = 2023  # type: ignore[misc]

    def test_fips_code_validation_5_digits(
        self,
        dept_I: DepartmentRow,
        dept_IIa: DepartmentRow,
        dept_IIb: DepartmentRow,
        dept_III: DepartmentRow,
    ) -> None:
        """FIPS code must be a 5-character string."""
        with pytest.raises(ValidationError):
            ValueTensor4x3(
                fips_code="123",  # Invalid: too short
                year=2022,
                dept_I=dept_I,
                dept_IIa=dept_IIa,
                dept_IIb=dept_IIb,
                dept_III=dept_III,
                naics_granularity=0.85,
                excluded_wages=50000.0,
            )

    def test_fips_code_validation_numeric_string(
        self,
        dept_I: DepartmentRow,
        dept_IIa: DepartmentRow,
        dept_IIb: DepartmentRow,
        dept_III: DepartmentRow,
    ) -> None:
        """FIPS code must be numeric (digits only)."""
        with pytest.raises(ValidationError):
            ValueTensor4x3(
                fips_code="26ABC",  # Invalid: contains letters
                year=2022,
                dept_I=dept_I,
                dept_IIa=dept_IIa,
                dept_IIb=dept_IIb,
                dept_III=dept_III,
                naics_granularity=0.85,
                excluded_wages=50000.0,
            )

    def test_profit_rate_computed_field(
        self,
        dept_I: DepartmentRow,
        dept_IIa: DepartmentRow,
        dept_IIb: DepartmentRow,
        dept_III: DepartmentRow,
    ) -> None:
        """profit_rate = total_s / (total_c + total_v) across all departments."""
        tensor = ValueTensor4x3(
            fips_code="26163",
            year=2022,
            dept_I=dept_I,
            dept_IIa=dept_IIa,
            dept_IIb=dept_IIb,
            dept_III=dept_III,
            naics_granularity=0.85,
            excluded_wages=50000.0,
        )
        # total_s = 200 + 100 + 300 + 70 = 670
        # total_c = 300 + 150 + 250 + 50 = 750
        # total_v = 100 + 100 + 100 + 100 = 400
        # profit_rate = 670 / (750 + 400) = 670 / 1150 = 0.5826...
        expected_rate = 670.0 / 1150.0
        assert tensor.profit_rate == pytest.approx(expected_rate)

    def test_total_value_property(
        self,
        dept_I: DepartmentRow,
        dept_IIa: DepartmentRow,
        dept_IIb: DepartmentRow,
        dept_III: DepartmentRow,
    ) -> None:
        """total_value sums all department values."""
        tensor = ValueTensor4x3(
            fips_code="26163",
            year=2022,
            dept_I=dept_I,
            dept_IIa=dept_IIa,
            dept_IIb=dept_IIb,
            dept_III=dept_III,
            naics_granularity=0.85,
            excluded_wages=50000.0,
        )
        # I=600, IIa=350, IIb=650, III=220 => total=1820
        assert tensor.total_value == 1820.0

    def test_naics_granularity_bounds(
        self,
        dept_I: DepartmentRow,
        dept_IIa: DepartmentRow,
        dept_IIb: DepartmentRow,
        dept_III: DepartmentRow,
    ) -> None:
        """naics_granularity must be in [0.0, 1.0]."""
        with pytest.raises(ValidationError):
            ValueTensor4x3(
                fips_code="26163",
                year=2022,
                dept_I=dept_I,
                dept_IIa=dept_IIa,
                dept_IIb=dept_IIb,
                dept_III=dept_III,
                naics_granularity=1.5,  # Invalid: > 1.0
                excluded_wages=50000.0,
            )

    def test_excluded_wages_non_negative(
        self,
        dept_I: DepartmentRow,
        dept_IIa: DepartmentRow,
        dept_IIb: DepartmentRow,
        dept_III: DepartmentRow,
    ) -> None:
        """excluded_wages must be non-negative."""
        with pytest.raises(ValidationError):
            ValueTensor4x3(
                fips_code="26163",
                year=2022,
                dept_I=dept_I,
                dept_IIa=dept_IIa,
                dept_IIb=dept_IIb,
                dept_III=dept_III,
                naics_granularity=0.85,
                excluded_wages=-1000.0,  # Invalid: negative
            )

    def test_year_reasonable_range(
        self,
        dept_I: DepartmentRow,
        dept_IIa: DepartmentRow,
        dept_IIb: DepartmentRow,
        dept_III: DepartmentRow,
    ) -> None:
        """Year must be within a reasonable range (e.g., >= 1900)."""
        with pytest.raises(ValidationError):
            ValueTensor4x3(
                fips_code="26163",
                year=1800,  # Invalid: before QCEW data exists
                dept_I=dept_I,
                dept_IIa=dept_IIa,
                dept_IIb=dept_IIb,
                dept_III=dept_III,
                naics_granularity=0.85,
                excluded_wages=50000.0,
            )

    def test_tensor_serialization_roundtrip(
        self,
        dept_I: DepartmentRow,
        dept_IIa: DepartmentRow,
        dept_IIb: DepartmentRow,
        dept_III: DepartmentRow,
    ) -> None:
        """ValueTensor4x3 can serialize to JSON and deserialize back."""
        tensor = ValueTensor4x3(
            fips_code="26163",
            year=2022,
            dept_I=dept_I,
            dept_IIa=dept_IIa,
            dept_IIb=dept_IIb,
            dept_III=dept_III,
            naics_granularity=0.85,
            excluded_wages=50000.0,
        )
        json_str = tensor.model_dump_json()
        restored = ValueTensor4x3.model_validate_json(json_str)
        assert restored.fips_code == tensor.fips_code
        assert restored.dept_I.c == tensor.dept_I.c
        assert restored.profit_rate == pytest.approx(tensor.profit_rate)


class TestDepartmentRowMarxianInvariants:
    """Tests for Marxian economic invariants in DepartmentRow.

    These tests verify that the model correctly represents Marx's value theory:
    - Total value = c + v + s (dead labor + living labor + unpaid labor)
    - OCC = c/v (organic composition of capital)
    - s/v = rate of exploitation (rate of surplus value)
    """

    @pytest.mark.parametrize(
        "c,v,s,expected_occ",
        [
            (50.0, 100.0, 100.0, 0.5),  # Early capitalism (labor-intensive)
            (100.0, 100.0, 100.0, 1.0),  # Balanced
            (400.0, 100.0, 100.0, 4.0),  # Advanced capitalism (capital-intensive)
        ],
        ids=["occ_0.5", "occ_1.0", "occ_4.0"],
    )
    def test_organic_composition_examples(
        self, c: float, v: float, s: float, expected_occ: float
    ) -> None:
        """Organic composition matches Marx's Capital Vol. 3 examples."""
        row = DepartmentRow(c=c, v=v, s=s)
        assert row.organic_composition == pytest.approx(expected_occ)

    def test_exploitation_rate_100_percent(self) -> None:
        """100% exploitation rate means s = v (all surplus labor extracted)."""
        row = DepartmentRow(c=100.0, v=100.0, s=100.0)
        assert row.exploitation_rate == pytest.approx(1.0)

    def test_exploitation_rate_200_percent(self) -> None:
        """200% exploitation rate (s = 2v) - extreme extraction."""
        row = DepartmentRow(c=100.0, v=100.0, s=200.0)
        assert row.exploitation_rate == pytest.approx(2.0)
