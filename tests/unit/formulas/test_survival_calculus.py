"""Tests for Survival Calculus - the decision theory of class struggle.

Agents act to maximize P(S) - probability of survival.
Two paths exist:
1. Acquiescence: P(S|A) - survive by compliance
2. Revolution: P(S|R) - survive by collective action

When P(S|R) > P(S|A), revolution becomes rational.
This is the mathematical basis for class consciousness.

Key Formulas:
- P(S|A) = 1 / (1 + e^(-k(x - x_critical))) - Sigmoid survival
- P(S|R) = Cohesion / (Repression + ε) - Collective survival
- Loss Aversion: λ = 2.25 (Kahneman-Tversky prospect theory)
"""

import pytest

from babylon.systems.formulas import (
    apply_loss_aversion,
    calculate_acquiescence_probability,
    calculate_crossover_threshold,
    calculate_revolution_probability,
)


@pytest.mark.math
class TestAcquiescenceProbability:
    """P(S|A) = 1 / (1 + e^(-k(x - x_critical)))

    Sigmoid function modeling survival through compliance.
    - x: Current wealth/resources
    - x_critical: Subsistence threshold
    - k: Steepness of survival curve
    """

    def test_sigmoid_bounds_zero_to_one(self) -> None:
        """P(S|A) must always be in [0, 1] range."""
        test_cases = [
            (0.0, 1.0, 1.0),  # Zero wealth
            (0.5, 0.5, 1.0),  # At threshold
            (1.0, 0.5, 1.0),  # Above threshold
            (0.1, 0.9, 2.0),  # High steepness
            (0.9, 0.1, 0.5),  # Low steepness
        ]

        for wealth, threshold, steepness in test_cases:
            prob = calculate_acquiescence_probability(
                wealth=wealth,
                subsistence_threshold=threshold,
                steepness_k=steepness,
            )
            assert 0.0 <= prob <= 1.0, (
                f"P(S|A) out of bounds for x={wealth}, x_c={threshold}, k={steepness}"
            )

    def test_crosses_50_at_threshold(self) -> None:
        """P(S|A) = 0.5 when x = x_critical (at subsistence threshold)."""
        wealth = 0.5
        threshold = 0.5  # At threshold
        steepness = 1.0

        prob = calculate_acquiescence_probability(
            wealth=wealth,
            subsistence_threshold=threshold,
            steepness_k=steepness,
        )

        assert prob == pytest.approx(0.5, abs=0.001)

    def test_probability_increases_with_wealth(self) -> None:
        """Higher wealth → higher P(S|A)."""
        threshold = 0.5
        steepness = 1.0

        prob_poor = calculate_acquiescence_probability(
            wealth=0.2,
            subsistence_threshold=threshold,
            steepness_k=steepness,
        )
        prob_rich = calculate_acquiescence_probability(
            wealth=0.8,
            subsistence_threshold=threshold,
            steepness_k=steepness,
        )

        assert prob_rich > prob_poor

    def test_steepness_affects_transition(self) -> None:
        """Higher k makes transition sharper around threshold."""
        wealth = 0.6  # Slightly above threshold
        threshold = 0.5

        prob_gradual = calculate_acquiescence_probability(
            wealth=wealth,
            subsistence_threshold=threshold,
            steepness_k=1.0,
        )
        prob_sharp = calculate_acquiescence_probability(
            wealth=wealth,
            subsistence_threshold=threshold,
            steepness_k=5.0,
        )

        # Higher k should push probability closer to 1.0 above threshold
        assert prob_sharp > prob_gradual

    def test_extreme_poverty_approaches_zero(self) -> None:
        """With very low wealth, P(S|A) approaches 0."""
        prob = calculate_acquiescence_probability(
            wealth=0.0,
            subsistence_threshold=0.5,
            steepness_k=5.0,
        )

        assert prob < 0.1  # Very low survival through compliance


@pytest.mark.math
class TestRevolutionProbability:
    """P(S|R) = Cohesion / (Repression + ε)

    Survival through collective action depends on:
    - Cohesion: Unity and organization of the working class
    - Repression: State violence capacity
    - ε (epsilon): Small constant to prevent division by zero
    """

    def test_monotonic_with_cohesion(self) -> None:
        """Higher cohesion → higher P(S|R)."""
        repression = 0.5

        prob_low = calculate_revolution_probability(
            cohesion=0.2,
            repression=repression,
        )
        prob_high = calculate_revolution_probability(
            cohesion=0.8,
            repression=repression,
        )

        assert prob_high > prob_low

    def test_inverse_with_repression(self) -> None:
        """Higher repression → lower P(S|R)."""
        cohesion = 0.6

        prob_low_repression = calculate_revolution_probability(
            cohesion=cohesion,
            repression=0.2,
        )
        prob_high_repression = calculate_revolution_probability(
            cohesion=cohesion,
            repression=0.8,
        )

        assert prob_low_repression > prob_high_repression

    def test_handles_zero_repression(self) -> None:
        """With ε, zero repression doesn't cause division by zero."""
        # Should not raise, epsilon prevents divide by zero
        prob = calculate_revolution_probability(
            cohesion=0.5,
            repression=0.0,
        )

        assert prob > 0.0
        assert prob <= 1.0  # Clamped to valid probability

    def test_probability_capped_at_one(self) -> None:
        """P(S|R) is clamped to maximum 1.0."""
        # Very high cohesion, very low repression
        prob = calculate_revolution_probability(
            cohesion=1.0,
            repression=0.01,
        )

        assert prob <= 1.0

    def test_zero_cohesion_gives_zero_probability(self) -> None:
        """No organization = no successful revolution."""
        prob = calculate_revolution_probability(
            cohesion=0.0,
            repression=0.5,
        )

        assert prob == 0.0


@pytest.mark.math
class TestCrossoverEvent:
    """The moment when P(S|R) > P(S|A) - revolution becomes rational."""

    def test_crossover_threshold_calculation(self) -> None:
        """Find the wealth level where revolution becomes rational."""
        # Use parameters where P(S|R) < 1.0 so crossover is calculable
        cohesion = 0.3
        repression = 0.5  # P(S|R) = 0.3/0.5 = 0.6
        subsistence_threshold = 0.5
        steepness = 2.0

        crossover_wealth = calculate_crossover_threshold(
            cohesion=cohesion,
            repression=repression,
            subsistence_threshold=subsistence_threshold,
            steepness_k=steepness,
        )

        # At crossover, P(S|A) should equal P(S|R)
        p_acquiesce = calculate_acquiescence_probability(
            wealth=crossover_wealth,
            subsistence_threshold=subsistence_threshold,
            steepness_k=steepness,
        )
        p_revolt = calculate_revolution_probability(
            cohesion=cohesion,
            repression=repression,
        )

        assert p_acquiesce == pytest.approx(p_revolt, abs=0.01)

    def test_above_crossover_acquiescence_wins(self) -> None:
        """Above crossover wealth, acquiescence is rational."""
        # Parameters where P(S|R) is moderate and crossover is meaningful
        cohesion = 0.2
        repression = 0.5  # P(S|R) = 0.2/0.5 = 0.4
        threshold = 0.5
        steepness = 3.0

        crossover = calculate_crossover_threshold(
            cohesion=cohesion,
            repression=repression,
            subsistence_threshold=threshold,
            steepness_k=steepness,
        )

        # Test a wealth level well above crossover
        high_wealth = min(crossover + 0.3, 0.95)

        p_a = calculate_acquiescence_probability(
            wealth=high_wealth,
            subsistence_threshold=threshold,
            steepness_k=steepness,
        )
        p_r = calculate_revolution_probability(
            cohesion=cohesion,
            repression=repression,
        )

        assert p_a > p_r, "Above crossover, acquiescence should be rational"


@pytest.mark.math
class TestLossAversion:
    """Loss aversion coefficient λ = 2.25 (Kahneman-Tversky).

    Losses loom larger than gains in decision-making.
    This affects how agents evaluate revolutionary risk.
    """

    LOSS_AVERSION_COEFFICIENT = 2.25

    def test_loss_aversion_coefficient(self) -> None:
        """λ = 2.25 per prospect theory."""
        loss = -10.0
        gain = 10.0

        perceived_loss = apply_loss_aversion(loss)
        perceived_gain = apply_loss_aversion(gain)

        # Loss should feel 2.25x as impactful
        assert abs(perceived_loss) == pytest.approx(
            abs(perceived_gain) * self.LOSS_AVERSION_COEFFICIENT,
            abs=0.01,
        )

    def test_gains_unchanged(self) -> None:
        """Positive values (gains) are not amplified."""
        gain = 10.0
        perceived = apply_loss_aversion(gain)

        assert perceived == gain

    def test_losses_amplified(self) -> None:
        """Negative values (losses) are multiplied by λ."""
        loss = -10.0
        perceived = apply_loss_aversion(loss)

        expected = loss * self.LOSS_AVERSION_COEFFICIENT
        assert perceived == pytest.approx(expected, abs=0.01)
