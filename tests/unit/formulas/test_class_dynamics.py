"""Tests for Class Wealth Dynamics ODE System.

Empirically derived from FRED Distributional Financial Accounts (DFA) data
(2015-2025). Models wealth flows between four Marxian classes:

- Core Bourgeoisie (Top 1%)
- Petty Bourgeoisie (90-99%)
- Labor Aristocracy (50-90%)
- Internal Proletariat (Bottom 50%)

Key Findings:
- Wealth distribution is remarkably stable
- Top 1% maintains ~30% homeostasis (self-reinforcing)
- 90-99% slowly loses ground (-0.3%/year)
- Bottom classes gain slightly through redistribution

Theoretical Basis:
- FRED DFA: https://www.federalreserve.gov/releases/z1/dataviz/dfa/
- MLM-TW: Imperial rent, labor aristocracy dynamics
"""

import pytest

from babylon.systems.formulas import (
    ClassDynamicsParams,
    SecondOrderParams,
    calculate_class_dynamics_derivative,
    calculate_equilibrium_deviation,
    calculate_full_dynamics,
    calculate_wealth_acceleration,
    calculate_wealth_flow,
    invert_wealth_to_population,
)


# Test constants for class dynamics
class ClassDynamicsConstants:
    """Constants for class dynamics tests."""

    # FRED-fitted equilibrium values (2015-2025)
    EQUILIBRIUM_BOURGEOISIE = 0.305  # ~30.5%
    EQUILIBRIUM_PETTY_BOURGEOISIE = 0.382  # ~38.2%
    EQUILIBRIUM_LABOR_ARISTOCRACY = 0.294  # ~29.4%
    EQUILIBRIUM_PROLETARIAT = 0.020  # ~2.0%

    # Default extraction rates (per quarter)
    ALPHA_21_EXTRACTION = 0.0006  # petty bourgeoisie → bourgeoisie

    # Redistribution rates
    DELTA_1_REDISTRIBUTION = 0.0010  # from bourgeoisie
    DELTA_2_REDISTRIBUTION = 0.0020  # from petty bourgeoisie
    DELTA_3_REDISTRIBUTION = 0.0010  # from labor aristocracy

    # Imperial rent formation
    GAMMA_3_IMPERIAL_RENT = 0.0057  # quarterly injection rate

    # Test wealth shares
    INITIAL_SHARES = (0.30, 0.36, 0.30, 0.04)
    EQUILIBRIUM_SHARES = (0.305, 0.382, 0.294, 0.020)


TC = ClassDynamicsConstants


@pytest.mark.math
class TestClassDynamicsParams:
    """Test ClassDynamicsParams dataclass defaults.

    These defaults are fitted from FRED 2015-2025 data and represent
    the empirically observed wealth flow rates.
    """

    def test_params_are_frozen(self) -> None:
        """Params should be immutable once created."""
        from dataclasses import FrozenInstanceError

        params = ClassDynamicsParams()
        with pytest.raises(FrozenInstanceError):
            params.alpha_21 = 0.999  # type: ignore[misc]

    def test_default_extraction_rates(self) -> None:
        """Default extraction rates should match FRED-fitted values."""
        params = ClassDynamicsParams()

        # Only alpha_21 (petty bourgeoisie → bourgeoisie) is non-zero
        assert params.alpha_21 == TC.ALPHA_21_EXTRACTION
        assert params.alpha_41 == 0.0
        assert params.alpha_31 == 0.0
        assert params.alpha_32 == 0.0
        assert params.alpha_42 == 0.0
        assert params.alpha_43 == 0.0

    def test_default_redistribution_rates(self) -> None:
        """Default redistribution rates should match FRED-fitted values."""
        params = ClassDynamicsParams()

        assert params.delta_1 == TC.DELTA_1_REDISTRIBUTION
        assert params.delta_2 == TC.DELTA_2_REDISTRIBUTION
        assert params.delta_3 == TC.DELTA_3_REDISTRIBUTION

    def test_default_imperial_rent_rate(self) -> None:
        """Imperial rent formation rate should match FRED-fitted value."""
        params = ClassDynamicsParams()
        assert params.gamma_3 == TC.GAMMA_3_IMPERIAL_RENT


@pytest.mark.math
class TestSecondOrderParams:
    """Test SecondOrderParams dataclass for momentum dynamics.

    Second-order terms model acceleration and damping effects
    that cause the system to oscillate around equilibrium values.
    """

    def test_params_are_frozen(self) -> None:
        """Params should be immutable once created."""
        from dataclasses import FrozenInstanceError

        params = SecondOrderParams()
        with pytest.raises(FrozenInstanceError):
            params.beta = (0.0, 0.0, 0.0, 0.0)  # type: ignore[misc]

    def test_damping_coefficients_are_negative(self) -> None:
        """Damping coefficients should be negative for mean-reversion."""
        params = SecondOrderParams()
        for beta in params.beta:
            assert beta < 0.0, "Damping should be negative (mean-reverting)"

    def test_natural_frequencies_are_positive(self) -> None:
        """Natural frequencies should be positive for oscillation."""
        params = SecondOrderParams()
        for omega in params.omega:
            assert omega > 0.0, "Frequencies should be positive"

    def test_equilibrium_sums_to_one(self) -> None:
        """Equilibrium wealth shares should sum to 1.0 (100%)."""
        params = SecondOrderParams()
        total = sum(params.equilibrium)
        assert total == pytest.approx(1.0, abs=0.001)

    def test_equilibrium_matches_fred_data(self) -> None:
        """Equilibrium values should match FRED 2015-2025 averages."""
        params = SecondOrderParams()

        assert params.equilibrium[0] == pytest.approx(TC.EQUILIBRIUM_BOURGEOISIE, abs=0.001)
        assert params.equilibrium[1] == pytest.approx(TC.EQUILIBRIUM_PETTY_BOURGEOISIE, abs=0.001)
        assert params.equilibrium[2] == pytest.approx(TC.EQUILIBRIUM_LABOR_ARISTOCRACY, abs=0.001)
        assert params.equilibrium[3] == pytest.approx(TC.EQUILIBRIUM_PROLETARIAT, abs=0.001)


@pytest.mark.math
class TestCalculateWealthFlow:
    """Test calculate_wealth_flow function.

    Calculates per-tick wealth flow from source class based on
    extraction rate and class consciousness resistance.
    """

    def test_flow_proportional_to_source_share(self) -> None:
        """Larger source share should produce larger flow."""
        flow_small = calculate_wealth_flow(source_share=0.1, extraction_rate=0.01)
        flow_large = calculate_wealth_flow(source_share=0.5, extraction_rate=0.01)

        assert flow_large == 5 * flow_small

    def test_flow_proportional_to_extraction_rate(self) -> None:
        """Higher extraction rate should produce larger flow."""
        flow_low = calculate_wealth_flow(source_share=0.5, extraction_rate=0.01)
        flow_high = calculate_wealth_flow(source_share=0.5, extraction_rate=0.02)

        assert flow_high == 2 * flow_low

    def test_zero_extraction_means_no_flow(self) -> None:
        """Zero extraction rate should produce zero flow."""
        flow = calculate_wealth_flow(source_share=0.5, extraction_rate=0.0)
        assert flow == 0.0

    def test_full_resistance_blocks_extraction(self) -> None:
        """100% class consciousness resistance should block all extraction."""
        flow = calculate_wealth_flow(source_share=0.5, extraction_rate=0.01, resistance=1.0)
        assert flow == 0.0

    def test_partial_resistance_reduces_flow(self) -> None:
        """50% resistance should halve the flow."""
        flow_no_resistance = calculate_wealth_flow(source_share=0.5, extraction_rate=0.01)
        flow_half_resistance = calculate_wealth_flow(
            source_share=0.5, extraction_rate=0.01, resistance=0.5
        )

        assert flow_half_resistance == pytest.approx(flow_no_resistance / 2, abs=0.0001)

    def test_basic_flow_calculation(self) -> None:
        """Verify basic flow: 0.5 * 0.01 * (1 - 0) = 0.005."""
        flow = calculate_wealth_flow(source_share=0.5, extraction_rate=0.01, resistance=0.0)
        assert flow == pytest.approx(0.005, abs=0.0001)


@pytest.mark.math
class TestCalculateClassDynamicsDerivative:
    """Test first-order class dynamics ODE.

    Implements:
        dW₁/dt = α₄₁W₄ + α₃₁W₃ + α₂₁W₂ - δ₁W₁
        dW₂/dt = α₃₂W₃ + α₄₂W₄ - α₂₁W₂ - δ₂W₂
        dW₃/dt = α₄₃W₄ + γ₃ - α₃₁W₃ - α₃₂W₃ - δ₃W₃
        dW₄/dt = -(dW₁ + dW₂ + dW₃)
    """

    def test_derivatives_sum_to_zero(self) -> None:
        """Conservation: total wealth is constant, so dW/dt sums to zero."""
        shares = TC.INITIAL_SHARES
        dw = calculate_class_dynamics_derivative(shares)

        total = sum(dw)
        assert abs(total) < 1e-10, f"Derivatives should sum to zero, got {total}"

    def test_derivatives_with_custom_params(self) -> None:
        """Custom parameters should affect derivative values."""
        shares = TC.INITIAL_SHARES

        # Default params
        dw_default = calculate_class_dynamics_derivative(shares)

        # Custom params with higher extraction
        custom_params = ClassDynamicsParams(alpha_21=0.01)
        dw_custom = calculate_class_dynamics_derivative(shares, params=custom_params)

        # Higher extraction should benefit bourgeoisie more
        assert dw_custom[0] > dw_default[0]

    def test_resistance_reduces_extraction(self) -> None:
        """Class consciousness resistance should reduce wealth flows."""
        shares = TC.INITIAL_SHARES

        # No resistance
        dw_no_resist = calculate_class_dynamics_derivative(shares)

        # Full resistance for petty bourgeoisie (class 2)
        resistances = (0.0, 1.0, 0.0, 0.0)
        dw_resist = calculate_class_dynamics_derivative(shares, resistances=resistances)

        # With petty bourgeoisie resistance, less extraction to bourgeoisie
        assert dw_resist[0] < dw_no_resist[0]

    def test_equilibrium_has_small_derivatives(self) -> None:
        """At equilibrium, derivatives should be small (near steady state)."""
        shares = TC.EQUILIBRIUM_SHARES
        dw = calculate_class_dynamics_derivative(shares)

        # Each derivative should be small
        for derivative in dw:
            assert abs(derivative) < 0.01, f"Derivative too large at equilibrium: {derivative}"

    def test_imperial_rent_benefits_labor_aristocracy(self) -> None:
        """Imperial rent (gamma_3) should increase labor aristocracy wealth."""
        shares = TC.INITIAL_SHARES

        # Default has gamma_3 = 0.0057
        dw = calculate_class_dynamics_derivative(shares)

        # dW₃ should be positive due to imperial rent injection
        # (assuming redistribution doesn't dominate)
        params = ClassDynamicsParams(gamma_3=0.1, delta_3=0.0)  # High rent, no redistribution
        dw_high_rent = calculate_class_dynamics_derivative(shares, params=params)

        assert dw_high_rent[2] > dw[2]


@pytest.mark.math
class TestCalculateWealthAcceleration:
    """Test second-order wealth dynamics.

    d²W/dt² = β(dW/dt) - ω²(W - W*)

    Models momentum effects and oscillation around equilibrium.
    """

    def test_damped_oscillation_to_equilibrium(self) -> None:
        """Positive velocity with wealth above equilibrium should decelerate."""
        # Wealth above equilibrium with positive velocity
        accel = calculate_wealth_acceleration(
            wealth_share=0.32,  # Above equilibrium (0.30)
            velocity=0.001,  # Moving up
            equilibrium=0.30,
            damping=-0.1,  # Negative = mean-reverting
            frequency=0.05,
        )

        # Should be negative (decelerating the upward movement)
        assert accel < 0

    def test_restoring_force_toward_equilibrium(self) -> None:
        """Wealth far from equilibrium should have restoring force."""
        # Wealth below equilibrium
        accel_below = calculate_wealth_acceleration(
            wealth_share=0.25,  # Below equilibrium
            velocity=0.0,
            equilibrium=0.30,
            damping=-0.1,
            frequency=0.05,
        )

        # Wealth above equilibrium
        accel_above = calculate_wealth_acceleration(
            wealth_share=0.35,  # Above equilibrium
            velocity=0.0,
            equilibrium=0.30,
            damping=-0.1,
            frequency=0.05,
        )

        # Below equilibrium should accelerate upward (positive)
        assert accel_below > 0
        # Above equilibrium should accelerate downward (negative)
        assert accel_above < 0

    def test_damping_opposes_velocity(self) -> None:
        """Damping term should oppose velocity direction."""
        # Positive velocity with negative damping
        accel_pos_vel = calculate_wealth_acceleration(
            wealth_share=0.30,  # At equilibrium
            velocity=0.01,  # Moving up
            equilibrium=0.30,
            damping=-0.1,
            frequency=0.0,  # No restoring force
        )

        # Negative velocity with negative damping
        accel_neg_vel = calculate_wealth_acceleration(
            wealth_share=0.30,  # At equilibrium
            velocity=-0.01,  # Moving down
            equilibrium=0.30,
            damping=-0.1,
            frequency=0.0,  # No restoring force
        )

        # Damping should oppose both
        assert accel_pos_vel < 0  # Opposes upward
        assert accel_neg_vel > 0  # Opposes downward

    def test_zero_frequency_means_no_restoring_force(self) -> None:
        """With omega=0, only damping affects acceleration."""
        accel = calculate_wealth_acceleration(
            wealth_share=0.50,  # Far from equilibrium
            velocity=0.01,
            equilibrium=0.30,
            damping=-0.1,
            frequency=0.0,  # No restoring force
        )

        expected = -0.1 * 0.01  # Only damping term
        assert accel == pytest.approx(expected, abs=0.0001)


@pytest.mark.math
class TestCalculateFullDynamics:
    """Test combined first and second order dynamics."""

    def test_returns_both_derivative_tuples(self) -> None:
        """Should return both first and second order derivatives."""
        shares = TC.INITIAL_SHARES
        velocities = (0.0, -0.001, 0.0006, 0.0004)

        dw, d2w = calculate_full_dynamics(shares, velocities)

        assert len(dw) == 4
        assert len(d2w) == 4

    def test_first_order_sum_constraint(self) -> None:
        """First-order derivatives should sum to zero."""
        shares = TC.INITIAL_SHARES
        velocities = (0.0, -0.001, 0.0006, 0.0004)

        dw, _ = calculate_full_dynamics(shares, velocities)

        assert abs(sum(dw)) < 1e-10

    def test_custom_params_propagate(self) -> None:
        """Custom params should affect both orders."""
        shares = TC.INITIAL_SHARES
        # Non-zero velocities so beta affects acceleration
        velocities = (0.01, -0.01, 0.005, -0.005)

        # Default params
        dw_default, d2w_default = calculate_full_dynamics(shares, velocities)

        # Custom second-order params with different damping
        custom_second = SecondOrderParams(beta=(-0.5, -0.5, -0.5, -0.5))
        dw_custom, d2w_custom = calculate_full_dynamics(
            shares, velocities, second_order=custom_second
        )

        # First-order should be same (doesn't use second-order params)
        assert dw_default == dw_custom

        # Second-order should differ (beta affects damping term)
        assert d2w_default != d2w_custom


@pytest.mark.math
class TestCalculateEquilibriumDeviation:
    """Test equilibrium deviation metric."""

    def test_at_equilibrium_deviation_is_zero(self) -> None:
        """At equilibrium, deviation should be approximately zero."""
        shares = TC.EQUILIBRIUM_SHARES
        deviation = calculate_equilibrium_deviation(shares)

        assert deviation == pytest.approx(0.0, abs=0.001)

    def test_away_from_equilibrium_has_positive_deviation(self) -> None:
        """Away from equilibrium, deviation should be positive."""
        shares = (0.40, 0.30, 0.25, 0.05)  # Far from equilibrium
        deviation = calculate_equilibrium_deviation(shares)

        assert deviation > 0.01

    def test_deviation_increases_with_distance(self) -> None:
        """Deviation should increase as shares move away from equilibrium."""
        close_shares = (0.31, 0.38, 0.29, 0.02)  # Close to equilibrium
        far_shares = (0.40, 0.30, 0.25, 0.05)  # Far from equilibrium

        close_dev = calculate_equilibrium_deviation(close_shares)
        far_dev = calculate_equilibrium_deviation(far_shares)

        assert far_dev > close_dev

    def test_custom_equilibrium(self) -> None:
        """Should work with custom equilibrium values."""
        shares = (0.25, 0.25, 0.25, 0.25)  # Equal shares
        custom_eq = (0.25, 0.25, 0.25, 0.25)

        deviation = calculate_equilibrium_deviation(shares, equilibrium=custom_eq)

        assert deviation == pytest.approx(0.0, abs=0.001)


@pytest.mark.math
class TestInvertWealthToPopulation:
    """Test wealth distribution inversion algorithm.

    Transforms FRED's fixed-population/variable-wealth data into
    fixed-wealth-thirds/variable-population data.
    """

    def test_bottom_50_holds_bottom_wealth_band(self) -> None:
        """With realistic shares, bottom 50% holds the poorest slice."""
        shares = (30.7, 36.4, 30.3, 2.5)  # FRED 2025 Q1 data

        # Bottom 50% holds 2.5% of wealth
        # So 33.3% wealth threshold should be around 90% of population
        pop_at_33 = invert_wealth_to_population(shares, target_wealth_pct=33.333)

        # Should be around 90% of population
        assert 88.0 < pop_at_33 < 92.0

    def test_top_1_holds_top_wealth_band(self) -> None:
        """Top 1% holds approximately the top third of wealth."""
        shares = (30.7, 36.4, 30.3, 2.5)

        # At 66.7% wealth threshold
        pop_at_67 = invert_wealth_to_population(shares, target_wealth_pct=66.667)

        # Should be around 98% of population (99% - some of top 1%)
        assert 97.0 < pop_at_67 < 99.0

    def test_returns_100_at_100_wealth(self) -> None:
        """100% wealth threshold should return 100% population."""
        shares = (30.7, 36.4, 30.3, 2.5)
        pop_at_100 = invert_wealth_to_population(shares, target_wealth_pct=100.0)

        assert pop_at_100 == pytest.approx(100.0, abs=0.01)

    def test_monotonically_increasing(self) -> None:
        """Higher wealth thresholds should include more population."""
        shares = (30.7, 36.4, 30.3, 2.5)

        pop_at_10 = invert_wealth_to_population(shares, target_wealth_pct=10.0)
        pop_at_50 = invert_wealth_to_population(shares, target_wealth_pct=50.0)
        pop_at_90 = invert_wealth_to_population(shares, target_wealth_pct=90.0)

        assert pop_at_10 < pop_at_50 < pop_at_90

    def test_handles_zero_bottom_share(self) -> None:
        """Should handle case where bottom class has zero wealth."""
        shares = (33.3, 33.3, 33.4, 0.0)  # Bottom 50% has nothing

        pop_at_1 = invert_wealth_to_population(shares, target_wealth_pct=1.0)

        # With zero bottom share, interpolation starts at 50%
        assert pop_at_1 > 0.0


@pytest.mark.math
class TestClassDynamicsIntegration:
    """Integration tests verifying class dynamics across formulas.

    These tests verify that the mathematical relationships hold across
    multiple formula calls, demonstrating wealth flow dynamics.
    """

    def test_equilibrium_stability(self) -> None:
        """System at equilibrium should have minimal derivatives."""
        shares = TC.EQUILIBRIUM_SHARES
        velocities = (0.0, 0.0, 0.0, 0.0)

        dw, d2w = calculate_full_dynamics(shares, velocities)

        # First-order derivatives should be small
        for derivative in dw:
            assert abs(derivative) < 0.01

        # Second-order derivatives should also be small (at equilibrium with zero velocity)
        for accel in d2w:
            assert abs(accel) < 0.01

    def test_perturbation_response(self) -> None:
        """System perturbed from equilibrium should show restoring dynamics."""
        # Perturb: bourgeoisie gains at labor aristocracy's expense
        perturbed = (0.35, 0.382, 0.244, 0.024)  # Sum = 1.0
        velocities = (0.0, 0.0, 0.0, 0.0)

        dw, d2w = calculate_full_dynamics(perturbed, velocities)

        # Second-order should show restoring force:
        # - Bourgeoisie (above equilibrium) should decelerate
        # - Labor aristocracy (below equilibrium) should accelerate
        assert d2w[0] < 0  # Restoring force on bourgeoisie
        assert d2w[2] > 0  # Restoring force on labor aristocracy

    def test_conservation_of_wealth_over_simulation(self) -> None:
        """Simulated steps should conserve total wealth."""
        shares = list(TC.INITIAL_SHARES)
        dt = 0.01  # Small time step

        for _ in range(100):
            dw = calculate_class_dynamics_derivative(tuple(shares))

            # Euler step
            for i in range(4):
                shares[i] += dw[i] * dt

            # Verify conservation
            total = sum(shares)
            assert total == pytest.approx(1.0, abs=0.001)
