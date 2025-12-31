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
from tests.constants import TestConstants

from babylon.systems.formulas import (
    apply_loss_aversion,
    calculate_acquiescence_probability,
    calculate_crossover_threshold,
    calculate_revolution_probability,
)

# Alias for readability
TC = TestConstants.Behavioral


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

    def test_below_crossover_revolution_wins(self) -> None:
        """Below crossover wealth, revolution becomes rational.

        When wealth falls below the crossover point, P(S|R) > P(S|A).
        """
        # Parameters where P(S|R) is moderate and crossover is meaningful
        cohesion = 0.4
        repression = 0.5  # P(S|R) = 0.4/0.5 = 0.8
        threshold = 0.5
        steepness = 3.0

        crossover = calculate_crossover_threshold(
            cohesion=cohesion,
            repression=repression,
            subsistence_threshold=threshold,
            steepness_k=steepness,
        )

        # Test a wealth level below crossover
        low_wealth = max(crossover - 0.3, 0.05)

        p_a = calculate_acquiescence_probability(
            wealth=low_wealth,
            subsistence_threshold=threshold,
            steepness_k=steepness,
        )
        p_r = calculate_revolution_probability(
            cohesion=cohesion,
            repression=repression,
        )

        assert p_r > p_a, "Below crossover, revolution should be rational"

    def test_p_revolution_zero_returns_zero(self) -> None:
        """When P(S|R) = 0 (no cohesion), crossover returns 0.0.

        With zero cohesion, revolution is never rational regardless of wealth.
        """
        crossover = calculate_crossover_threshold(
            cohesion=0.0,  # No organization = P(S|R) = 0
            repression=0.5,
            subsistence_threshold=0.5,
            steepness_k=2.0,
        )

        assert crossover == 0.0

    def test_p_revolution_one_returns_one(self) -> None:
        """When P(S|R) = 1 (capped), crossover returns 1.0.

        Maximum revolutionary probability is capped at 1.0.
        """
        crossover = calculate_crossover_threshold(
            cohesion=0.9,
            repression=0.001,  # Very low repression -> P(S|R) capped at 1.0
            subsistence_threshold=0.5,
            steepness_k=2.0,
        )

        assert crossover == 1.0

    def test_crossover_clamped_to_valid_range(self) -> None:
        """Crossover value is always in [0, 1] range.

        The result is clamped: max(0.0, min(1.0, crossover))
        """
        # Test various parameter combinations
        test_cases = [
            (0.1, 0.9, 0.5, 2.0),  # Low cohesion
            (0.9, 0.1, 0.5, 2.0),  # High cohesion
            (0.5, 0.5, 0.1, 5.0),  # Low threshold
            (0.5, 0.5, 0.9, 5.0),  # High threshold
        ]

        for cohesion, repression, threshold, steepness in test_cases:
            crossover = calculate_crossover_threshold(
                cohesion=cohesion,
                repression=repression,
                subsistence_threshold=threshold,
                steepness_k=steepness,
            )
            assert 0.0 <= crossover <= 1.0, (
                f"Crossover out of bounds for c={cohesion}, r={repression}, "
                f"t={threshold}, k={steepness}"
            )

    def test_crossover_at_exact_fifty_percent_revolution(self) -> None:
        """When P(S|R) = 0.5, crossover equals subsistence threshold.

        At 50% revolution probability, sigmoid crosses at its midpoint.
        """
        cohesion = 0.25
        repression = 0.5  # P(S|R) = 0.25 / 0.5 = 0.5
        threshold = 0.6
        steepness = 2.0

        crossover = calculate_crossover_threshold(
            cohesion=cohesion,
            repression=repression,
            subsistence_threshold=threshold,
            steepness_k=steepness,
        )

        # At P(S|R) = 0.5, ln(1/0.5 - 1) = ln(1) = 0
        # So crossover = threshold - 0/k = threshold
        assert crossover == pytest.approx(threshold, abs=0.01)

    def test_steepness_affects_crossover_position(self) -> None:
        """Higher steepness concentrates the crossover region.

        With same parameters, different steepness values affect crossover.
        The crossover formula is: crossover = threshold - ln_term / k
        where ln_term = ln(1/p_revolution - 1)

        With P(S|R) = 0.6 > 0.5:
        ln_term = ln(1/0.6 - 1) = ln(0.667) < 0 (negative)
        crossover = threshold - (negative / k) = threshold + |ln_term|/k

        Higher k means smaller |ln_term|/k, so crossover closer to threshold.
        """
        cohesion = 0.3
        repression = 0.5  # P(S|R) = 0.6
        threshold = 0.5

        crossover_low_k = calculate_crossover_threshold(
            cohesion=cohesion,
            repression=repression,
            subsistence_threshold=threshold,
            steepness_k=1.0,  # Low steepness
        )

        crossover_high_k = calculate_crossover_threshold(
            cohesion=cohesion,
            repression=repression,
            subsistence_threshold=threshold,
            steepness_k=5.0,  # High steepness
        )

        # Both should be valid but different due to steepness effect on ln_term/k
        assert 0.0 <= crossover_low_k <= 1.0
        assert 0.0 <= crossover_high_k <= 1.0
        # With P(S|R) = 0.6 > 0.5, ln_term is negative
        # crossover = 0.5 - (neg/k) = 0.5 + |ln_term|/k
        # Higher k means smaller |ln_term|/k, so crossover is closer to threshold (smaller)
        assert crossover_high_k < crossover_low_k


@pytest.mark.math
class TestLossAversion:
    """Loss aversion coefficient λ (Kahneman-Tversky).

    Losses loom larger than gains in decision-making.
    This affects how agents evaluate revolutionary risk.
    """

    def test_loss_aversion_coefficient(self) -> None:
        """λ per prospect theory (Kahneman-Tversky)."""
        loss = -10.0
        gain = 10.0

        perceived_loss = apply_loss_aversion(loss)
        perceived_gain = apply_loss_aversion(gain)

        # Loss should feel LOSS_AVERSION times as impactful
        assert abs(perceived_loss) == pytest.approx(
            abs(perceived_gain) * TC.LOSS_AVERSION,
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

        expected = loss * TC.LOSS_AVERSION
        assert perceived == pytest.approx(expected, abs=0.01)
