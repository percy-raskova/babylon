"""Unit tests for Sprint 2.3: The Rent Trinity.

Tests the expanded imperial rent calculation that aggregates three forms
of value capture:

1. Φ_UE (Unequal Exchange) - Andrea Ricci: price distortion via wage gap
2. Φ_Shadow (Shadow Labor) - Leopoldina Fortunati: unpaid domestic labor
3. Φ_Repro (Externalized Reproduction) - Claude Meillassoux: migrant labor "free gift"

**Canonical Example:**
    Wage Gap = 1.5 (Core wages 50% higher than value)
    Paid V = 100
    Shadow Subsidy = 20

    Old Model (Wage Gap only): Rent = 50
    New Model (Trinity):
        Φ_UE = 100 × (1.5 - 1.0) = 50
        Φ_Shadow = 20
        Φ_Repro = 50 × 0.2 = 10
        Total = 50 + 20 + 10 = 80

This demonstrates the "Expanded View" of exploitation is active:
total_phi > phi_ue.

See Also:
    :mod:`babylon.economics.reproduction`: Implementation module.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.economics.reproduction import ImperialRentCalculator, RentStructure
from babylon.economics.tensor import DepartmentRow, ValueTensor4x3


class TestRentStructureModel:
    """Test the RentStructure Pydantic model."""

    def test_rent_structure_fields_exist(self) -> None:
        """RentStructure has all required fields."""
        structure = RentStructure(
            total_phi=80.0,
            component_ue=50.0,
            component_shadow=20.0,
            component_repro=10.0,
        )

        assert structure.total_phi == 80.0
        assert structure.component_ue == 50.0
        assert structure.component_shadow == 20.0
        assert structure.component_repro == 10.0

    def test_rent_structure_is_frozen(self) -> None:
        """RentStructure is immutable (frozen)."""
        structure = RentStructure(
            total_phi=80.0,
            component_ue=50.0,
            component_shadow=20.0,
            component_repro=10.0,
        )

        with pytest.raises(ValidationError):
            structure.total_phi = 999.0  # type: ignore[misc]

    def test_rent_structure_sum_equals_total(self) -> None:
        """Components should sum to total_phi."""
        structure = RentStructure(
            total_phi=80.0,
            component_ue=50.0,
            component_shadow=20.0,
            component_repro=10.0,
        )

        expected_sum = (
            structure.component_ue + structure.component_shadow + structure.component_repro
        )
        assert structure.total_phi == pytest.approx(expected_sum, rel=1e-9)


class TestRentTrinityCalculation:
    """Test the three-component rent calculation."""

    @pytest.fixture
    def canonical_tensor(self) -> ValueTensor4x3:
        """Canonical tensor for Trinity calculation.

        Sets up a scenario where:
        - Total monetized_v = 100 (paid variable capital)
        - Shadow subsidy = 20 (unpaid reproductive labor)
        - This means Dept III has v=40 with g33=0.5 (20 paid, 20 shadow)
        """
        # Dept I, IIa, IIb contribute v = 80 total (no shadow labor)
        # Dept III contributes v = 40 with g33 = 0.5, so:
        #   - monetized_v from III = 40 * 0.5 = 20
        #   - shadow_subsidy = 40 * (1 - 0.5) = 20
        # Total monetized_v = 80 + 20 = 100
        return ValueTensor4x3(
            fips_code="26163",
            year=2022,
            dept_I=DepartmentRow(c=100.0, v=30.0, s=50.0),
            dept_IIa=DepartmentRow(c=80.0, v=25.0, s=40.0),
            dept_IIb=DepartmentRow(c=60.0, v=25.0, s=60.0),
            dept_III=DepartmentRow(c=40.0, v=40.0, s=30.0),
            naics_granularity=0.85,
            excluded_wages=0.0,
            visibility_g33=0.5,  # 50% of Dept III is shadow labor
        )

    def test_canonical_example_component_ue(self, canonical_tensor: ValueTensor4x3) -> None:
        """Φ_UE = v_paid × (wage_gap - 1.0).

        With wage_gap = 1.5 and v_paid = 100:
        Φ_UE = 100 × (1.5 - 1.0) = 50
        """
        calculator = ImperialRentCalculator.default()
        wage_gap_ratio = 1.5

        result = calculator.calculate_rent_trinity(
            tensor=canonical_tensor,
            wage_gap_ratio=wage_gap_ratio,
        )

        assert result.component_ue == pytest.approx(50.0, rel=1e-9)

    def test_canonical_example_component_shadow(self, canonical_tensor: ValueTensor4x3) -> None:
        """Φ_Shadow = tensor.shadow_subsidy.

        With Dept III v=40, g33=0.5:
        shadow_subsidy = 40 × (1 - 0.5) = 20
        """
        calculator = ImperialRentCalculator.default()
        wage_gap_ratio = 1.5

        result = calculator.calculate_rent_trinity(
            tensor=canonical_tensor,
            wage_gap_ratio=wage_gap_ratio,
        )

        assert result.component_shadow == pytest.approx(20.0, rel=1e-9)

    def test_canonical_example_component_repro(self, canonical_tensor: ValueTensor4x3) -> None:
        """Φ_Repro = Φ_UE × 0.2 (heuristic placeholder).

        With Φ_UE = 50:
        Φ_Repro = 50 × 0.2 = 10
        """
        calculator = ImperialRentCalculator.default()
        wage_gap_ratio = 1.5

        result = calculator.calculate_rent_trinity(
            tensor=canonical_tensor,
            wage_gap_ratio=wage_gap_ratio,
        )

        assert result.component_repro == pytest.approx(10.0, rel=1e-9)

    def test_canonical_example_total_phi(self, canonical_tensor: ValueTensor4x3) -> None:
        """Total Φ = Φ_UE + Φ_Shadow + Φ_Repro = 50 + 20 + 10 = 80."""
        calculator = ImperialRentCalculator.default()
        wage_gap_ratio = 1.5

        result = calculator.calculate_rent_trinity(
            tensor=canonical_tensor,
            wage_gap_ratio=wage_gap_ratio,
        )

        assert result.total_phi == pytest.approx(80.0, rel=1e-9)

    def test_expanded_view_exceeds_wage_gap_only(self, canonical_tensor: ValueTensor4x3) -> None:
        """The Gross Differential Check: total_phi > phi_ue.

        This proves the "Expanded View" of exploitation is active -
        the Trinity model captures more value extraction than the
        simple wage gap model alone.
        """
        calculator = ImperialRentCalculator.default()
        wage_gap_ratio = 1.5

        result = calculator.calculate_rent_trinity(
            tensor=canonical_tensor,
            wage_gap_ratio=wage_gap_ratio,
        )

        # Old model would only see 50 (wage gap)
        # New model sees 80 (trinity)
        assert result.total_phi > result.component_ue, (
            f"Expanded view ({result.total_phi}) should exceed "
            f"wage-gap-only view ({result.component_ue})"
        )


class TestRentTrinityEdgeCases:
    """Edge cases for the Trinity calculation."""

    @pytest.fixture
    def tensor_no_shadow(self) -> ValueTensor4x3:
        """Tensor with g33=1.0 (no shadow labor)."""
        return ValueTensor4x3(
            fips_code="26163",
            year=2022,
            dept_I=DepartmentRow(c=100.0, v=30.0, s=50.0),
            dept_IIa=DepartmentRow(c=80.0, v=30.0, s=40.0),
            dept_IIb=DepartmentRow(c=60.0, v=20.0, s=60.0),
            dept_III=DepartmentRow(c=40.0, v=20.0, s=30.0),
            naics_granularity=0.85,
            excluded_wages=0.0,
            visibility_g33=1.0,  # Fully monetized - no shadow labor
        )

    def test_no_shadow_labor_component_shadow_is_zero(
        self, tensor_no_shadow: ValueTensor4x3
    ) -> None:
        """When g33=1.0, Φ_Shadow should be 0."""
        calculator = ImperialRentCalculator.default()

        result = calculator.calculate_rent_trinity(
            tensor=tensor_no_shadow,
            wage_gap_ratio=1.5,
        )

        assert result.component_shadow == pytest.approx(0.0, rel=1e-9)

    def test_wage_gap_at_parity_component_ue_is_zero(
        self, tensor_no_shadow: ValueTensor4x3
    ) -> None:
        """When wage_gap=1.0, Φ_UE should be 0 (no unequal exchange)."""
        calculator = ImperialRentCalculator.default()

        result = calculator.calculate_rent_trinity(
            tensor=tensor_no_shadow,
            wage_gap_ratio=1.0,  # No wage gap
        )

        assert result.component_ue == pytest.approx(0.0, rel=1e-9)

    def test_wage_gap_below_parity_component_ue_clamped(
        self, tensor_no_shadow: ValueTensor4x3
    ) -> None:
        """When wage_gap<1.0, Φ_UE should be clamped to 0.

        If periphery wages exceed core wages, there's no unequal exchange
        flowing TO the core. We don't model reverse flows in this Sprint.
        """
        calculator = ImperialRentCalculator.default()

        result = calculator.calculate_rent_trinity(
            tensor=tensor_no_shadow,
            wage_gap_ratio=0.8,  # Core wages BELOW periphery (reverse case)
        )

        # Φ_UE should be 0 (clamped), not negative
        assert result.component_ue == pytest.approx(0.0, rel=1e-9)

    def test_zero_monetized_v_returns_zero_ue(self) -> None:
        """When monetized_v=0, Φ_UE should be 0 (no wages to extract)."""
        tensor = ValueTensor4x3(
            fips_code="26163",
            year=2022,
            dept_I=DepartmentRow(c=100.0, v=0.0, s=50.0),
            dept_IIa=DepartmentRow(c=80.0, v=0.0, s=40.0),
            dept_IIb=DepartmentRow(c=60.0, v=0.0, s=60.0),
            dept_III=DepartmentRow(c=40.0, v=0.0, s=30.0),
            naics_granularity=0.85,
            excluded_wages=0.0,
            visibility_g33=0.5,
        )
        calculator = ImperialRentCalculator.default()

        result = calculator.calculate_rent_trinity(
            tensor=tensor,
            wage_gap_ratio=1.5,
        )

        assert result.component_ue == pytest.approx(0.0, rel=1e-9)
        assert result.component_repro == pytest.approx(0.0, rel=1e-9)  # 20% of 0


class TestRentTrinityDefaultCalculator:
    """Test ImperialRentCalculator.default() factory method."""

    def test_default_factory_exists(self) -> None:
        """ImperialRentCalculator should have a default() factory."""
        calculator = ImperialRentCalculator.default()
        assert calculator is not None
        assert isinstance(calculator, ImperialRentCalculator)

    def test_default_calculator_has_periphery_baseline(self) -> None:
        """Default calculator should have standard periphery baseline."""
        calculator = ImperialRentCalculator.default()
        # Standard periphery basket is ~$2000/year
        assert calculator.periphery_baseline > 0
