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

from babylon.systems.formulas import (
    calculate_consciousness_drift,
    calculate_imperial_rent,
    calculate_labor_aristocracy_ratio,
    is_labor_aristocracy,
)


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
