"""Unit tests for ImperialRentCalculator (User Story 5).

Feature: 013-melt-basket-visibility
Date: 2026-02-01

TDD Red Phase: These tests define the expected behavior for imperial rent
computation per TVT Axioms E3 and E4.
"""

from __future__ import annotations

from babylon.economics.melt import DefaultImperialRentCalculator, NationalParameters


class TestPhiHourFormula:
    """Tests for Φ_hour = (W/τ) × (1/γ_basket) - 1 formula."""

    def test_phi_hour_formula_labor_aristocracy(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test Φ_hour for Labor Aristocracy wage (W > τ_effective).

        With τ=$65, γ_basket=0.68, τ_effective=$44.2:
        At W=$65:
        Φ_hour = (65/65) × (1/0.68) - 1 = 1.47 - 1 = 0.47
        """
        calculator = DefaultImperialRentCalculator()

        phi = calculator.compute_phi_hour(65.0, sample_national_params)

        # Φ_hour = (65/65) × (1/0.68) - 1 ≈ 0.47
        expected = (65.0 / 65.0) * (1.0 / 0.68) - 1.0
        assert abs(phi - expected) < 0.01
        assert phi > 0  # LA extracts labor

    def test_phi_hour_formula_proletariat(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test Φ_hour for Proletariat wage (V < W ≤ τ_effective).

        With τ=$65, γ_basket=0.68:
        At W=$30:
        Φ_hour = (30/65) × (1/0.68) - 1 ≈ -0.32
        """
        calculator = DefaultImperialRentCalculator()

        phi = calculator.compute_phi_hour(30.0, sample_national_params)

        expected = (30.0 / 65.0) * (1.0 / 0.68) - 1.0
        assert abs(phi - expected) < 0.01
        assert phi < 0  # Proletariat is net exploited

    def test_phi_hour_formula_subproletariat(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test Φ_hour for Subproletariat wage (W ≤ V_reproduction).

        With τ=$65, γ_basket=0.68:
        At W=$8:
        Φ_hour = (8/65) × (1/0.68) - 1 ≈ -0.82
        """
        calculator = DefaultImperialRentCalculator()

        phi = calculator.compute_phi_hour(8.0, sample_national_params)

        expected = (8.0 / 65.0) * (1.0 / 0.68) - 1.0
        assert abs(phi - expected) < 0.01
        assert phi < 0  # Subproletariat heavily exploited


class TestLaborCommandedFormula:
    """Tests for L_commanded = (W/τ) × (1/γ_basket) formula."""

    def test_labor_commanded_labor_aristocracy(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test L_commanded for Labor Aristocracy (L_cmd > 1).

        At W=$65, τ=$65, γ_basket=0.68:
        L_commanded = (65/65) × (1/0.68) = 1.47
        """
        calculator = DefaultImperialRentCalculator()

        l_cmd = calculator.compute_labor_commanded(65.0, sample_national_params)

        expected = (65.0 / 65.0) * (1.0 / 0.68)
        assert abs(l_cmd - expected) < 0.01
        assert l_cmd > 1.0  # LA commands more than 1 hour per hour worked

    def test_labor_commanded_proletariat(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test L_commanded for Proletariat (L_cmd < 1).

        At W=$30, τ=$65, γ_basket=0.68:
        L_commanded = (30/65) × (1/0.68) ≈ 0.68
        """
        calculator = DefaultImperialRentCalculator()

        l_cmd = calculator.compute_labor_commanded(30.0, sample_national_params)

        expected = (30.0 / 65.0) * (1.0 / 0.68)
        assert abs(l_cmd - expected) < 0.01
        assert l_cmd < 1.0  # Proletariat commands less than 1 hour

    def test_labor_commanded_always_non_negative(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test L_commanded is always ≥ 0 for non-negative wages."""
        calculator = DefaultImperialRentCalculator()

        for wage in [0.0, 1.0, 10.0, 50.0, 100.0]:
            l_cmd = calculator.compute_labor_commanded(wage, sample_national_params)
            assert l_cmd >= 0.0


class TestPhiLcmdRelationship:
    """Tests for the relationship Φ_hour = L_commanded - 1."""

    def test_phi_equals_lcmd_minus_one(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that Φ_hour = L_commanded - 1 for all wages."""
        calculator = DefaultImperialRentCalculator()

        for wage in [8.0, 25.0, 44.2, 50.0, 65.0, 80.0, 100.0]:
            phi = calculator.compute_phi_hour(wage, sample_national_params)
            l_cmd = calculator.compute_labor_commanded(wage, sample_national_params)

            assert abs(phi - (l_cmd - 1.0)) < 1e-10


class TestBreakEvenCase:
    """Tests for break-even case W = τ_effective → Φ_hour = 0."""

    def test_break_even_at_tau_effective(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test break-even: W = τ_effective → Φ_hour = 0.

        Break-Even Algebra:
        At W = τ_effective = τ × γ_basket = 65 × 0.68 = 44.2:
        Φ_hour = (τ × γ_basket / τ) × (1/γ_basket) - 1
               = γ_basket × (1/γ_basket) - 1
               = 1 - 1 = 0 ✓
        """
        calculator = DefaultImperialRentCalculator()

        # W = τ_effective = 44.2
        phi = calculator.compute_phi_hour(44.2, sample_national_params)

        assert abs(phi) < 0.01  # Should be ~0

    def test_break_even_l_commanded_equals_one(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test break-even: W = τ_effective → L_commanded = 1."""
        calculator = DefaultImperialRentCalculator()

        l_cmd = calculator.compute_labor_commanded(44.2, sample_national_params)

        assert abs(l_cmd - 1.0) < 0.01


class TestClassPositionBoundaries:
    """Tests for class position boundaries in imperial rent metrics."""

    def test_labor_aristocracy_phi_positive(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that W > τ_effective always gives Φ_hour > 0."""
        calculator = DefaultImperialRentCalculator()

        # All wages above τ_effective = 44.2
        for wage in [45.0, 50.0, 65.0, 80.0, 100.0]:
            phi = calculator.compute_phi_hour(wage, sample_national_params)
            assert phi > 0, f"Expected Φ_hour > 0 at W={wage}"

    def test_proletariat_phi_negative(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that W < τ_effective always gives Φ_hour < 0."""
        calculator = DefaultImperialRentCalculator()

        # All wages below τ_effective = 44.2
        for wage in [8.0, 15.0, 25.0, 35.0, 44.0]:
            phi = calculator.compute_phi_hour(wage, sample_national_params)
            assert phi < 0, f"Expected Φ_hour < 0 at W={wage}"


class TestTheoreticalBounds:
    """Tests for theoretical bounds from get_theoretical_bounds()."""

    def test_phi_at_zero_approaches_minus_one(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that Φ_hour approaches -1 as W approaches 0."""
        calculator = DefaultImperialRentCalculator()

        bounds = calculator.get_theoretical_bounds(sample_national_params)

        assert bounds["phi_at_zero"] == -1.0

    def test_phi_at_threshold_equals_zero(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that Φ_hour = 0 at W = τ_effective."""
        calculator = DefaultImperialRentCalculator()

        bounds = calculator.get_theoretical_bounds(sample_national_params)

        assert bounds["phi_at_threshold"] == 0.0

    def test_phi_at_tau_depends_on_gamma(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that Φ_hour at W = τ depends on γ_basket.

        At W = τ:
        Φ_hour = (1/γ_basket) - 1 = (1/0.68) - 1 ≈ 0.47
        """
        calculator = DefaultImperialRentCalculator()

        bounds = calculator.get_theoretical_bounds(sample_national_params)

        expected = (1.0 / 0.68) - 1.0
        assert abs(bounds["phi_at_tau"] - expected) < 0.01

    def test_l_cmd_at_threshold_equals_one(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that L_commanded = 1 at W = τ_effective."""
        calculator = DefaultImperialRentCalculator()

        bounds = calculator.get_theoretical_bounds(sample_national_params)

        assert bounds["l_cmd_at_threshold"] == 1.0

    def test_bounds_dict_has_all_keys(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that bounds dict contains all expected keys."""
        calculator = DefaultImperialRentCalculator()

        bounds = calculator.get_theoretical_bounds(sample_national_params)

        assert "phi_at_zero" in bounds
        assert "phi_at_threshold" in bounds
        assert "phi_at_tau" in bounds
        assert "l_cmd_at_threshold" in bounds
        assert "l_cmd_at_tau" in bounds


class TestIsLaborAristocracy:
    """Tests for is_labor_aristocracy predicate."""

    def test_is_labor_aristocracy_above_threshold(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test is_labor_aristocracy returns True for W > τ_effective."""
        calculator = DefaultImperialRentCalculator()

        assert calculator.is_labor_aristocracy(50.0, sample_national_params) is True
        assert calculator.is_labor_aristocracy(65.0, sample_national_params) is True
        assert calculator.is_labor_aristocracy(100.0, sample_national_params) is True

    def test_is_not_labor_aristocracy_below_threshold(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test is_labor_aristocracy returns False for W ≤ τ_effective."""
        calculator = DefaultImperialRentCalculator()

        assert calculator.is_labor_aristocracy(30.0, sample_national_params) is False
        assert calculator.is_labor_aristocracy(8.0, sample_national_params) is False
        assert calculator.is_labor_aristocracy(44.0, sample_national_params) is False

    def test_is_not_labor_aristocracy_at_threshold(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test is_labor_aristocracy returns False at exact threshold.

        At W = τ_effective, the worker is NOT Labor Aristocracy
        (they are at the boundary, break-even).
        """
        calculator = DefaultImperialRentCalculator()

        assert calculator.is_labor_aristocracy(44.2, sample_national_params) is False


class TestEdgeCases:
    """Tests for edge cases in imperial rent computation."""

    def test_zero_wage_phi_approaches_minus_one(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that Φ_hour approaches -1 as W approaches 0."""
        calculator = DefaultImperialRentCalculator()

        # Very small wage
        phi = calculator.compute_phi_hour(0.001, sample_national_params)

        # Should be very close to -1
        assert phi < -0.99
        assert phi > -1.01

    def test_zero_wage_l_commanded_approaches_zero(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that L_commanded approaches 0 as W approaches 0."""
        calculator = DefaultImperialRentCalculator()

        l_cmd = calculator.compute_labor_commanded(0.001, sample_national_params)

        assert l_cmd < 0.01

    def test_very_high_wage(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test computation with very high wage."""
        calculator = DefaultImperialRentCalculator()

        # CEO-level wage
        phi = calculator.compute_phi_hour(1000.0, sample_national_params)
        l_cmd = calculator.compute_labor_commanded(1000.0, sample_national_params)

        # Should be positive and large
        assert phi > 10.0
        assert l_cmd > 10.0
        assert abs(phi - (l_cmd - 1.0)) < 1e-10


class TestConsistencyWithClassPosition:
    """Tests ensuring imperial rent metrics align with ClassPosition classification."""

    def test_labor_aristocracy_predicate_matches_class_position(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that is_labor_aristocracy aligns with ClassPosition.LABOR_ARISTOCRACY."""
        from babylon.economics.melt import ClassPosition, DefaultClassPositionClassifier

        rent_calc = DefaultImperialRentCalculator()
        class_calc = DefaultClassPositionClassifier()

        for wage in [8.0, 30.0, 44.0, 44.2, 45.0, 50.0, 65.0, 100.0]:
            is_la_rent = rent_calc.is_labor_aristocracy(wage, sample_national_params)
            class_pos = class_calc.classify(wage, sample_national_params)
            is_la_class = class_pos == ClassPosition.LABOR_ARISTOCRACY

            assert is_la_rent == is_la_class, (
                f"Mismatch at W={wage}: "
                f"is_labor_aristocracy={is_la_rent}, "
                f"ClassPosition={class_pos}"
            )
