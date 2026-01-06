"""Property-based tests for Survival Calculus formulas.

Uses Hypothesis to verify formula properties hold across the entire input space,
catching edge cases that example-based tests might miss.

Properties Verified:
- P(S|A): Valid probability [0, 1], monotonicity with wealth
- P(S|R): Valid probability [0, 1], ratio behavior
- Crossover Threshold: Bounded [0, 1], correct relationship
- Loss Aversion: Correct amplification of losses
"""

from __future__ import annotations

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from babylon.systems.formulas import (
    apply_loss_aversion,
    calculate_acquiescence_probability,
    calculate_crossover_threshold,
    calculate_revolution_probability,
)
from babylon.systems.formulas.constants import LOSS_AVERSION_COEFFICIENT

# =============================================================================
# P(S|A) - ACQUIESCENCE PROBABILITY PROPERTIES
# =============================================================================


@pytest.mark.math
@pytest.mark.property
class TestAcquiescenceProbabilityProperties:
    """Property-based tests for P(S|A) formula.

    Formula: P(S|A) = 1 / (1 + e^(-k(x - x_crit)))

    Properties:
    1. Output is always in [0, 1]
    2. Output is exactly 0.5 at threshold
    3. Output monotonically increases with wealth
    4. Steeper k produces sharper transitions
    """

    @given(
        wealth=st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
        subsistence_threshold=st.floats(
            min_value=0.01, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
        steepness_k=st.floats(
            min_value=0.001, max_value=10.0, allow_nan=False, allow_infinity=False
        ),
    )
    def test_psa_is_valid_probability(
        self, wealth: float, subsistence_threshold: float, steepness_k: float
    ) -> None:
        """P(S|A) is always in [0, 1]."""
        p_sa = calculate_acquiescence_probability(
            wealth=wealth,
            subsistence_threshold=subsistence_threshold,
            steepness_k=steepness_k,
        )
        assert 0.0 <= p_sa <= 1.0

    @given(
        threshold=st.floats(min_value=0.01, max_value=1e6, allow_nan=False, allow_infinity=False),
        steepness_k=st.floats(
            min_value=0.01, max_value=10.0, allow_nan=False, allow_infinity=False
        ),
    )
    def test_psa_is_half_at_threshold(self, threshold: float, steepness_k: float) -> None:
        """P(S|A) = 0.5 when wealth = subsistence_threshold."""
        p_sa = calculate_acquiescence_probability(
            wealth=threshold,
            subsistence_threshold=threshold,
            steepness_k=steepness_k,
        )
        assert p_sa == pytest.approx(0.5, abs=1e-9)

    @given(
        subsistence=st.floats(
            min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False
        ),
        steepness_k=st.floats(
            min_value=0.01, max_value=10.0, allow_nan=False, allow_infinity=False
        ),
    )
    def test_psa_increases_with_wealth(self, subsistence: float, steepness_k: float) -> None:
        """P(S|A) is monotonically increasing with wealth."""
        low_wealth = calculate_acquiescence_probability(
            wealth=subsistence * 0.5,
            subsistence_threshold=subsistence,
            steepness_k=steepness_k,
        )
        high_wealth = calculate_acquiescence_probability(
            wealth=subsistence * 2.0,
            subsistence_threshold=subsistence,
            steepness_k=steepness_k,
        )
        assert high_wealth >= low_wealth

    @given(
        wealth=st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        subsistence=st.floats(
            min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False
        ),
    )
    def test_higher_k_produces_sharper_transition(self, wealth: float, subsistence: float) -> None:
        """Higher steepness_k produces more extreme probabilities away from threshold."""
        # At wealth != subsistence, higher k should produce more extreme value
        assume(abs(wealth - subsistence) > 1.0)  # Not too close to threshold

        p_low_k = calculate_acquiescence_probability(
            wealth=wealth,
            subsistence_threshold=subsistence,
            steepness_k=0.1,
        )
        p_high_k = calculate_acquiescence_probability(
            wealth=wealth,
            subsistence_threshold=subsistence,
            steepness_k=1.0,
        )

        # Higher k pushes probability toward extremes (0 or 1)
        if wealth > subsistence:
            # Above threshold: higher k -> closer to 1
            assert p_high_k >= p_low_k
        else:
            # Below threshold: higher k -> closer to 0
            assert p_high_k <= p_low_k


# =============================================================================
# P(S|R) - REVOLUTION PROBABILITY PROPERTIES
# =============================================================================


@pytest.mark.math
@pytest.mark.property
class TestRevolutionProbabilityProperties:
    """Property-based tests for P(S|R) formula.

    Formula: P(S|R) = Cohesion / (Repression + epsilon)

    Properties:
    1. Output is always in [0, 1]
    2. Output is zero when cohesion is zero
    3. Output increases with cohesion
    4. Output decreases with repression
    """

    @given(
        cohesion=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        repression=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    )
    def test_psr_is_valid_probability(self, cohesion: float, repression: float) -> None:
        """P(S|R) is always in [0, 1]."""
        p_sr = calculate_revolution_probability(
            cohesion=cohesion,
            repression=repression,
        )
        assert 0.0 <= p_sr <= 1.0

    @given(
        repression=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    )
    def test_psr_is_zero_when_no_cohesion(self, repression: float) -> None:
        """P(S|R) = 0 when cohesion = 0."""
        p_sr = calculate_revolution_probability(
            cohesion=0.0,
            repression=repression,
        )
        assert p_sr == 0.0

    @given(
        repression=st.floats(min_value=0.1, max_value=0.9, allow_nan=False, allow_infinity=False),
    )
    def test_psr_increases_with_cohesion(self, repression: float) -> None:
        """P(S|R) increases with organization/cohesion level."""
        low_cohesion = calculate_revolution_probability(
            cohesion=0.2,
            repression=repression,
        )
        high_cohesion = calculate_revolution_probability(
            cohesion=0.8,
            repression=repression,
        )
        assert high_cohesion >= low_cohesion

    @given(
        cohesion=st.floats(min_value=0.1, max_value=0.9, allow_nan=False, allow_infinity=False),
    )
    def test_psr_decreases_with_repression(self, cohesion: float) -> None:
        """P(S|R) decreases with repression level."""
        low_repression = calculate_revolution_probability(
            cohesion=cohesion,
            repression=0.1,
        )
        high_repression = calculate_revolution_probability(
            cohesion=cohesion,
            repression=0.9,
        )
        assert low_repression >= high_repression

    @given(
        cohesion=st.floats(min_value=0.5, max_value=1.0, allow_nan=False, allow_infinity=False),
    )
    def test_psr_capped_at_one(self, cohesion: float) -> None:
        """P(S|R) is capped at 1.0 even when cohesion >> repression."""
        p_sr = calculate_revolution_probability(
            cohesion=cohesion,
            repression=0.01,  # Very low repression
        )
        assert p_sr <= 1.0


# =============================================================================
# CROSSOVER THRESHOLD PROPERTIES
# =============================================================================


@pytest.mark.math
@pytest.mark.property
class TestCrossoverThresholdProperties:
    """Property-based tests for crossover threshold formula.

    The crossover is where P(S|R) = P(S|A): revolution becomes rational.

    Properties:
    1. Crossover is always in [0, 1]
    2. Higher cohesion raises crossover (revolution viable at higher wealth)
    3. Higher repression lowers crossover (revolution needs more desperation)
    """

    @given(
        cohesion=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        repression=st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False),
        subsistence=st.floats(
            min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False
        ),
        steepness_k=st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False),
    )
    def test_crossover_is_bounded(
        self, cohesion: float, repression: float, subsistence: float, steepness_k: float
    ) -> None:
        """Crossover threshold is always in [0, 1]."""
        crossover = calculate_crossover_threshold(
            cohesion=cohesion,
            repression=repression,
            subsistence_threshold=subsistence,
            steepness_k=steepness_k,
        )
        assert 0.0 <= crossover <= 1.0

    @given(
        repression=st.floats(min_value=0.3, max_value=0.7, allow_nan=False, allow_infinity=False),
        subsistence=st.floats(
            min_value=10.0, max_value=100.0, allow_nan=False, allow_infinity=False
        ),
        steepness_k=st.floats(min_value=0.1, max_value=1.0, allow_nan=False, allow_infinity=False),
    )
    def test_higher_cohesion_raises_crossover(
        self, repression: float, subsistence: float, steepness_k: float
    ) -> None:
        """Higher cohesion raises crossover (revolution viable at higher wealth)."""
        crossover_low = calculate_crossover_threshold(
            cohesion=0.2,
            repression=repression,
            subsistence_threshold=subsistence,
            steepness_k=steepness_k,
        )
        crossover_high = calculate_crossover_threshold(
            cohesion=0.7,
            repression=repression,
            subsistence_threshold=subsistence,
            steepness_k=steepness_k,
        )
        # With higher P(S|R), workers can afford revolution at higher wealth
        # (less desperate conditions needed)
        assert crossover_high >= crossover_low

    @given(
        cohesion=st.floats(min_value=0.3, max_value=0.7, allow_nan=False, allow_infinity=False),
        subsistence=st.floats(
            min_value=10.0, max_value=100.0, allow_nan=False, allow_infinity=False
        ),
        steepness_k=st.floats(min_value=0.1, max_value=1.0, allow_nan=False, allow_infinity=False),
    )
    def test_higher_repression_lowers_crossover(
        self, cohesion: float, subsistence: float, steepness_k: float
    ) -> None:
        """Higher repression lowers crossover (workers must be more desperate)."""
        crossover_low_rep = calculate_crossover_threshold(
            cohesion=cohesion,
            repression=0.2,
            subsistence_threshold=subsistence,
            steepness_k=steepness_k,
        )
        crossover_high_rep = calculate_crossover_threshold(
            cohesion=cohesion,
            repression=0.8,
            subsistence_threshold=subsistence,
            steepness_k=steepness_k,
        )
        # With higher repression, P(S|R) is lower, so workers must be
        # more desperate (lower wealth) for revolution to be rational
        assert crossover_low_rep >= crossover_high_rep


# =============================================================================
# LOSS AVERSION PROPERTIES
# =============================================================================


@pytest.mark.math
@pytest.mark.property
class TestLossAversionProperties:
    """Property-based tests for loss aversion modifier.

    Formula: losses are amplified by 2.25x (Kahneman-Tversky)

    Properties:
    1. Positive values unchanged
    2. Negative values amplified by LOSS_AVERSION_COEFFICIENT
    3. Zero unchanged
    """

    @given(
        value=st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
    )
    def test_positive_values_unchanged(self, value: float) -> None:
        """Positive values are not modified (gains not amplified)."""
        result = apply_loss_aversion(value)
        assert result == pytest.approx(value, rel=1e-9)

    @given(
        value=st.floats(min_value=-1e6, max_value=0.0, allow_nan=False, allow_infinity=False),
    )
    def test_negative_values_amplified(self, value: float) -> None:
        """Negative values are amplified by loss aversion coefficient."""
        assume(value != 0.0)
        result = apply_loss_aversion(value)
        expected = value * LOSS_AVERSION_COEFFICIENT
        assert result == pytest.approx(expected, rel=1e-9)
        # Amplified loss is more negative
        assert result < value

    def test_zero_unchanged(self) -> None:
        """Zero is not modified."""
        result = apply_loss_aversion(0.0)
        assert result == 0.0

    @given(
        loss=st.floats(min_value=-1e6, max_value=-0.01, allow_nan=False, allow_infinity=False),
    )
    def test_loss_aversion_ratio_correct(self, loss: float) -> None:
        """Loss amplification ratio equals LOSS_AVERSION_COEFFICIENT."""
        result = apply_loss_aversion(loss)
        ratio = result / loss
        assert ratio == pytest.approx(LOSS_AVERSION_COEFFICIENT, rel=1e-9)

    @given(
        loss1=st.floats(min_value=-1e6, max_value=-0.01, allow_nan=False, allow_infinity=False),
        loss2=st.floats(min_value=-1e6, max_value=-0.01, allow_nan=False, allow_infinity=False),
    )
    def test_larger_loss_amplified_more(self, loss1: float, loss2: float) -> None:
        """Larger losses (more negative) are amplified to more negative values."""
        assume(loss1 != loss2)
        result1 = apply_loss_aversion(loss1)
        result2 = apply_loss_aversion(loss2)

        # If loss1 is more negative, result1 should be more negative
        if loss1 < loss2:
            assert result1 < result2
        else:
            assert result1 > result2
