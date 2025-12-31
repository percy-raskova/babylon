"""Tests for the Fundamental Theorem of MLM-TW.

The mathematical core of Babylon: Revolution in the Imperial Core
is impossible while Imperial Rent flows. These tests verify the
deterministic formulas that drive the simulation.

Key Formulas:
- Imperial Rent: Φ(Wp, Ψp) = α × Wp × (1 - Ψp)
- Consciousness Drift: dΨc/dt = k(1 - Wc/Vc) - λΨc
- Labor Aristocracy Condition: Wc/Vc > 1 defines labor aristocracy
"""

import pytest
from tests.constants import TestConstants

from babylon.systems.formulas import (
    calculate_consciousness_drift,
    calculate_imperial_rent,
    calculate_labor_aristocracy_ratio,
    is_labor_aristocracy,
)

# Alias for readability
TC = TestConstants.Behavioral


@pytest.mark.math
class TestImperialRent:
    """Φ(Wp, Ψp) = α × Wp × (1 - Ψp)

    Imperial Rent is the value extracted from the periphery that
    flows to the core, enabling the labor aristocracy.

    Variables:
        α (alpha): Extraction efficiency coefficient (0 to 1)
        Wp: Periphery wage share (0 to 1)
        Ψp (psi_p): Periphery consciousness/resistance (0 = submissive, 1 = revolutionary)
    """

    def test_rent_zero_when_periphery_revolts(self) -> None:
        """When Ψp = 1.0 (full revolution), rent must be 0.

        A fully revolutionary periphery cannot be exploited.
        This is the mathematical basis for anti-imperialism.
        """
        alpha = 0.5
        periphery_wages = 0.3
        periphery_consciousness = 1.0  # Full revolution

        rent = calculate_imperial_rent(
            alpha=alpha,
            periphery_wages=periphery_wages,
            periphery_consciousness=periphery_consciousness,
        )

        assert rent == 0.0

    def test_rent_maximum_when_periphery_submits(self) -> None:
        """When Ψp = 0.0 (submission), rent = α × Wp.

        Maximum extraction occurs when there is no resistance.
        """
        alpha = 0.5
        periphery_wages = 0.3
        periphery_consciousness = 0.0  # Full submission

        rent = calculate_imperial_rent(
            alpha=alpha,
            periphery_wages=periphery_wages,
            periphery_consciousness=periphery_consciousness,
        )

        expected = alpha * periphery_wages  # 0.5 * 0.3 = 0.15
        assert rent == pytest.approx(expected, abs=0.001)

    def test_rent_decreases_with_consciousness(self) -> None:
        """Rent monotonically decreases as consciousness rises."""
        alpha = 0.6
        periphery_wages = 0.4

        rent_low_consciousness = calculate_imperial_rent(
            alpha=alpha,
            periphery_wages=periphery_wages,
            periphery_consciousness=0.2,
        )
        rent_high_consciousness = calculate_imperial_rent(
            alpha=alpha,
            periphery_wages=periphery_wages,
            periphery_consciousness=0.8,
        )

        assert rent_low_consciousness > rent_high_consciousness

    def test_rent_always_non_negative(self) -> None:
        """Imperial rent cannot be negative (no reverse flow)."""
        # Test with various parameters
        test_cases = [
            (0.5, 0.3, 0.5),
            (0.0, 0.5, 0.5),  # Zero alpha
            (1.0, 0.0, 0.5),  # Zero wages
            (1.0, 1.0, 1.0),  # Maximum resistance
        ]

        for alpha, wages, consciousness in test_cases:
            rent = calculate_imperial_rent(
                alpha=alpha,
                periphery_wages=wages,
                periphery_consciousness=consciousness,
            )
            assert rent >= 0.0, f"Negative rent for α={alpha}, Wp={wages}, Ψp={consciousness}"


@pytest.mark.math
class TestLaborAristocracy:
    """Wc/Vc > 1 defines labor aristocracy.

    When core wages exceed value produced, the difference
    comes from Imperial Rent (extracted from the periphery).
    """

    def test_labor_aristocracy_ratio_calculation(self) -> None:
        """Wc/Vc correctly calculated."""
        core_wages = 80.0
        value_produced = 50.0

        ratio = calculate_labor_aristocracy_ratio(
            core_wages=core_wages,
            value_produced=value_produced,
        )

        assert ratio == pytest.approx(1.6, abs=0.001)

    def test_is_labor_aristocracy_true(self) -> None:
        """Worker is labor aristocracy when Wc/Vc > 1."""
        # Wages exceed value produced - living on rent
        assert is_labor_aristocracy(core_wages=80.0, value_produced=50.0) is True

    def test_is_labor_aristocracy_false(self) -> None:
        """Worker is NOT labor aristocracy when Wc/Vc <= 1."""
        # Wages less than or equal to value - productive worker
        assert is_labor_aristocracy(core_wages=40.0, value_produced=50.0) is False
        assert is_labor_aristocracy(core_wages=50.0, value_produced=50.0) is False

    def test_ratio_handles_zero_production(self) -> None:
        """Division by zero returns infinity (or raises)."""
        with pytest.raises(ValueError, match="value_produced must be > 0"):
            calculate_labor_aristocracy_ratio(core_wages=80.0, value_produced=0.0)

    def test_wages_slightly_above_value_is_aristocracy(self) -> None:
        """When wages are marginally above value, worker is labor aristocracy.

        This boundary test catches mutation survival where > is mutated to >=.
        """
        # 100.001 > 100.0 -> True (labor aristocracy)
        assert is_labor_aristocracy(core_wages=100.001, value_produced=100.0) is True

    def test_wages_slightly_below_value_is_not_aristocracy(self) -> None:
        """When wages are marginally below value, worker is NOT labor aristocracy.

        This boundary test catches mutation survival where > is mutated to >=.
        """
        # 99.999 < 100.0 -> False (not labor aristocracy)
        assert is_labor_aristocracy(core_wages=99.999, value_produced=100.0) is False

    def test_exact_equality_is_not_aristocracy(self) -> None:
        """When wages exactly equal value, worker is NOT labor aristocracy.

        Wc/Vc > 1 (strictly greater) defines labor aristocracy.
        Exact equality means no rent extraction is occurring.
        """
        # 100.0 == 100.0 -> False (Wc/Vc = 1.0, not > 1)
        assert is_labor_aristocracy(core_wages=100.0, value_produced=100.0) is False

    def test_zero_wages_is_not_aristocracy(self) -> None:
        """When wages are zero, worker is NOT labor aristocracy.

        A worker receiving no wages cannot be benefiting from imperial rent.
        """
        # 0.0 / 100.0 = 0.0 < 1 -> False
        assert is_labor_aristocracy(core_wages=0.0, value_produced=100.0) is False

    def test_negative_value_raises_error(self) -> None:
        """Negative value_produced is invalid and should raise ValueError.

        Value produced must be positive for the ratio to be meaningful.
        """
        with pytest.raises(ValueError, match="value_produced must be > 0"):
            is_labor_aristocracy(core_wages=100.0, value_produced=-50.0)


@pytest.mark.math
class TestConsciousnessDrift:
    """dΨc/dt = k(1 - Wc/Vc) - λΨc

    Core consciousness drifts based on rent flow.
    - When Wc/Vc > 1 (receiving rent): consciousness drifts reactionary
    - When Wc/Vc < 1 (no rent): consciousness drifts revolutionary

    Variables:
        k: Sensitivity coefficient
        λ (lambda): Decay coefficient (consciousness fades without material basis)
        Ψc: Core consciousness (0 = reactionary, 1 = revolutionary)
    """

    def test_drift_negative_under_rent(self) -> None:
        """When Wc/Vc > 1, consciousness drifts reactionary (negative drift).

        Workers receiving rent from imperialism have no material
        basis for revolutionary consciousness.
        """
        drift = calculate_consciousness_drift(
            core_wages=80.0,
            value_produced=50.0,  # Wc/Vc = 1.6 > 1
            current_consciousness=0.5,
            sensitivity_k=1.0,
            decay_lambda=0.1,
        )

        assert drift < 0.0, "Consciousness should drift reactionary under rent"

    def test_drift_positive_when_rent_cut(self) -> None:
        """When Wc/Vc < 1, consciousness drifts revolutionary (positive drift).

        Without rent, workers face true exploitation and gain
        revolutionary consciousness.
        """
        drift = calculate_consciousness_drift(
            core_wages=40.0,
            value_produced=50.0,  # Wc/Vc = 0.8 < 1
            current_consciousness=0.3,
            sensitivity_k=1.0,
            decay_lambda=0.1,
        )

        assert drift > 0.0, "Consciousness should drift revolutionary without rent"

    def test_drift_zero_at_equilibrium(self) -> None:
        """At Wc/Vc = 1, base drift is zero (only decay remains)."""
        drift = calculate_consciousness_drift(
            core_wages=50.0,
            value_produced=50.0,  # Wc/Vc = 1.0
            current_consciousness=0.0,  # No consciousness to decay
            sensitivity_k=1.0,
            decay_lambda=0.1,
        )

        assert drift == pytest.approx(0.0, abs=0.001)

    def test_consciousness_decay(self) -> None:
        """High consciousness decays over time without reinforcement."""
        # Even at Wc/Vc = 1, high consciousness decays
        drift = calculate_consciousness_drift(
            core_wages=50.0,
            value_produced=50.0,  # Neutral material conditions
            current_consciousness=0.8,  # High consciousness
            sensitivity_k=1.0,
            decay_lambda=0.2,
        )

        # Decay term: -0.2 * 0.8 = -0.16
        assert drift < 0.0, "High consciousness should decay"


@pytest.mark.math
class TestConsciousnessDriftBifurcation:
    """Test the Fascist Bifurcation mechanic in consciousness drift.

    Sprint 3.4.2b: When wages are FALLING (wage_change < 0), crisis creates
    "agitation energy" that channels into either:
    - Revolution (if solidarity_pressure > 0) - positive drift
    - Fascism (if solidarity_pressure = 0) - negative drift via loss aversion

    This encodes the historical insight: "Agitation without solidarity
    produces fascism, not revolution." (Germany 1933 vs Russia 1917)
    """

    def test_falling_wages_with_solidarity_increases_consciousness(self) -> None:
        """Crisis + solidarity channels agitation into revolutionary consciousness.

        When wages fall AND solidarity exists, the agitation energy
        produces revolutionary drift (more class consciousness).

        This is the Russia 1917 scenario: crisis plus solidarity = revolution.
        """
        # Base scenario at Wc/Vc = 1.0 (neutral material conditions)
        # Use minimal decay to isolate the bifurcation effect
        drift = calculate_consciousness_drift(
            core_wages=50.0,
            value_produced=50.0,  # Wc/Vc = 1.0 (neutral base drift)
            current_consciousness=0.3,
            sensitivity_k=1.0,
            decay_lambda=0.0,  # No decay to isolate bifurcation
            solidarity_pressure=0.5,  # Solidarity present
            wage_change=-10.0,  # Wages FALLING (crisis)
        )

        # Base drift = k(1 - 1.0) - 0.0*0.3 = 0.0
        # Agitation energy = |-10| * LOSS_AVERSION = 22.5
        # Crisis modifier = 22.5 * min(1.0, 0.5) = 11.25
        # Total drift = 0.0 + 11.25 = 11.25 (positive = revolutionary)
        assert drift > 0.0, "Crisis with solidarity should increase consciousness"
        assert drift == pytest.approx(11.25, abs=0.01)

    def test_falling_wages_without_solidarity_decreases_consciousness(self) -> None:
        """Crisis without solidarity channels agitation into fascist reaction.

        When wages fall AND NO solidarity exists, the agitation energy
        produces reactionary drift (less class consciousness, more national identity).

        This is the Germany 1933 scenario: crisis without solidarity = fascism.
        """
        # Base scenario at Wc/Vc = 1.0 (neutral material conditions)
        drift = calculate_consciousness_drift(
            core_wages=50.0,
            value_produced=50.0,  # Wc/Vc = 1.0 (neutral base drift)
            current_consciousness=0.3,
            sensitivity_k=1.0,
            decay_lambda=0.0,  # No decay to isolate bifurcation
            solidarity_pressure=0.0,  # NO solidarity - the fascist condition
            wage_change=-10.0,  # Wages FALLING (crisis)
        )

        # Base drift = k(1 - 1.0) - 0.0*0.3 = 0.0
        # Agitation energy = |-10| * LOSS_AVERSION = 22.5
        # No solidarity -> subtract agitation: drift = 0.0 - 22.5 = -22.5
        # Total drift = -22.5 (negative = fascist/reactionary)
        assert drift < 0.0, "Crisis without solidarity should decrease consciousness"
        assert drift == pytest.approx(-22.5, abs=0.01)

    def test_rising_wages_no_bifurcation_triggered(self) -> None:
        """Rising wages do not trigger the bifurcation mechanic.

        The bifurcation only activates when wage_change < 0 (crisis).
        Rising wages = stability, no agitation energy generated.
        """
        # Compare with and without wage_change when wages rising
        drift_no_change = calculate_consciousness_drift(
            core_wages=50.0,
            value_produced=50.0,
            current_consciousness=0.3,
            sensitivity_k=1.0,
            decay_lambda=0.1,
            solidarity_pressure=0.5,
            wage_change=0.0,  # No change
        )

        drift_rising = calculate_consciousness_drift(
            core_wages=50.0,
            value_produced=50.0,
            current_consciousness=0.3,
            sensitivity_k=1.0,
            decay_lambda=0.1,
            solidarity_pressure=0.5,
            wage_change=10.0,  # Wages RISING (prosperity)
        )

        # Rising wages should NOT trigger bifurcation
        # Both should be the same (only base drift + decay)
        assert drift_no_change == pytest.approx(drift_rising, abs=0.001)

    def test_loss_aversion_coefficient_applied(self) -> None:
        """Verify the loss aversion multiplier is correctly applied.

        Kahneman-Tversky: Losses loom larger than equivalent gains.
        This amplifies the agitation energy during crisis.
        """
        # With solidarity: agitation energy = |wage_change| * LOSS_AVERSION
        drift = calculate_consciousness_drift(
            core_wages=50.0,
            value_produced=50.0,
            current_consciousness=0.0,
            sensitivity_k=1.0,
            decay_lambda=0.0,
            solidarity_pressure=1.0,  # Full solidarity
            wage_change=-1.0,  # Minimal wage loss
        )

        # Expected: base_drift (0) + crisis_modifier
        # crisis_modifier = |(-1)| * LOSS_AVERSION * min(1.0, 1.0) = LOSS_AVERSION
        assert drift == pytest.approx(TC.LOSS_AVERSION, abs=0.01)

    def test_solidarity_pressure_clamped_to_one(self) -> None:
        """Verify solidarity_pressure is clamped via min(1.0, solidarity_pressure).

        Even if solidarity_pressure > 1.0 (multiple solidarity edges),
        the maximum modifier is still clamped.
        """
        # Test with solidarity_pressure > 1.0
        drift_high = calculate_consciousness_drift(
            core_wages=50.0,
            value_produced=50.0,
            current_consciousness=0.0,
            sensitivity_k=1.0,
            decay_lambda=0.0,
            solidarity_pressure=2.0,  # Exceeds 1.0 (multiple edges)
            wage_change=-10.0,
        )

        drift_max = calculate_consciousness_drift(
            core_wages=50.0,
            value_produced=50.0,
            current_consciousness=0.0,
            sensitivity_k=1.0,
            decay_lambda=0.0,
            solidarity_pressure=1.0,  # Exactly 1.0
            wage_change=-10.0,
        )

        # Both should produce the same result because min(1.0, 2.0) = 1.0
        assert drift_high == pytest.approx(drift_max, abs=0.001)

    def test_zero_wage_change_no_bifurcation(self) -> None:
        """Zero wage change does not trigger bifurcation.

        Only negative wage_change (falling wages) triggers the mechanic.
        """
        drift = calculate_consciousness_drift(
            core_wages=50.0,
            value_produced=50.0,
            current_consciousness=0.0,
            sensitivity_k=1.0,
            decay_lambda=0.0,
            solidarity_pressure=0.5,
            wage_change=0.0,  # No change
        )

        # Base drift = k(1 - 1.0) - 0.0*0.0 = 0.0
        # No bifurcation triggered
        assert drift == pytest.approx(0.0, abs=0.001)

    def test_value_produced_validation_in_bifurcation(self) -> None:
        """ValueError raised for zero/negative value_produced even with bifurcation params."""
        with pytest.raises(ValueError, match="value_produced must be > 0"):
            calculate_consciousness_drift(
                core_wages=50.0,
                value_produced=0.0,  # Invalid
                current_consciousness=0.3,
                sensitivity_k=1.0,
                decay_lambda=0.1,
                solidarity_pressure=0.5,
                wage_change=-10.0,
            )
