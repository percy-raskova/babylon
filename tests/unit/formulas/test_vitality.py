"""Tests for the Grinding Attrition formula (Mass Line Refactor Phase 3).

The coverage_ratio threshold model ensures that high inequality requires
proportionally more wealth to prevent deaths. With inequality=0.8, agents
need 1.8× subsistence coverage (not just 1.0×) to keep everyone alive.

Key Formula:
    threshold = 1.0 + inequality
    deficit = max(0, threshold - coverage_ratio)
    attrition_rate = clamp(deficit × (0.5 + inequality), 0, 1)

Theoretical Basis:
    - Zero inequality: coverage_ratio >= 1.0 means everyone survives
    - High inequality (0.8): coverage_ratio >= 1.8 required to prevent deaths
    - The (0.5 + inequality) multiplier accelerates attrition at high inequality
"""

import pytest
from tests.constants import TestConstants

from babylon.systems.formulas import calculate_mortality_rate

# Alias for readability
TC = TestConstants.Attrition


@pytest.mark.math
class TestCoverageThreshold:
    """Test the threshold = 1 + inequality invariant.

    The coverage threshold determines when ANY deaths occur.
    At or above threshold, even the poorest survive.
    """

    def test_coverage_exceeds_threshold_no_deaths(self) -> None:
        """When coverage > threshold, mortality rate is 0.

        coverage_ratio = 2.0 / 1.0 = 2.0
        threshold = 1.0 + 0.8 = 1.8
        2.0 >= 1.8, so rate = 0.0
        """
        rate = calculate_mortality_rate(
            wealth_per_capita=2.0,
            subsistence_needs=1.0,
            inequality=TC.HIGH_INEQUALITY,
        )
        assert rate == 0.0

    def test_coverage_equals_threshold_no_deaths(self) -> None:
        """When coverage = threshold exactly, mortality rate is 0.

        coverage_ratio = 1.8 / 1.0 = 1.8
        threshold = 1.0 + 0.8 = 1.8
        1.8 >= 1.8, so rate = 0.0
        """
        rate = calculate_mortality_rate(
            wealth_per_capita=1.8,
            subsistence_needs=1.0,
            inequality=TC.HIGH_INEQUALITY,
        )
        assert rate == 0.0

    def test_zero_inequality_exact_coverage(self) -> None:
        """With zero inequality, threshold = 1.0.

        coverage_ratio = 1.0 / 1.0 = 1.0
        threshold = 1.0 + 0.0 = 1.0
        1.0 >= 1.0, so rate = 0.0
        """
        rate = calculate_mortality_rate(
            wealth_per_capita=1.0,
            subsistence_needs=1.0,
            inequality=TC.ZERO_INEQUALITY,
        )
        assert rate == 0.0


@pytest.mark.math
class TestAttritionCalculation:
    """Test attrition_rate = deficit × (0.5 + inequality).

    When coverage falls below threshold, deficit determines attrition.
    The (0.5 + inequality) multiplier means high inequality kills faster.
    """

    def test_coverage_below_threshold_causes_attrition(self) -> None:
        """When coverage < threshold, attrition occurs.

        coverage_ratio = 1.0 / 1.0 = 1.0
        threshold = 1.0 + 0.8 = 1.8
        deficit = 1.8 - 1.0 = 0.8
        attrition = 0.8 × (0.5 + 0.8) = 0.8 × 1.3 = 1.04 → clamped to 1.0
        """
        rate = calculate_mortality_rate(
            wealth_per_capita=1.0,
            subsistence_needs=1.0,
            inequality=TC.HIGH_INEQUALITY,
        )
        assert rate == 1.0  # Clamped to maximum

    def test_moderate_deficit_partial_attrition(self) -> None:
        """Moderate deficit produces partial attrition rate.

        coverage_ratio = 1.4 / 1.0 = 1.4
        threshold = 1.0 + 0.8 = 1.8
        deficit = 1.8 - 1.4 = 0.4
        attrition = 0.4 × 1.3 = 0.52
        """
        rate = calculate_mortality_rate(
            wealth_per_capita=1.4,
            subsistence_needs=1.0,
            inequality=TC.HIGH_INEQUALITY,
        )
        expected = 0.4 * TC.MULTIPLIER_HIGH_INEQUALITY  # 0.52
        assert rate == pytest.approx(expected, abs=0.001)

    def test_zero_inequality_below_threshold_attrition(self) -> None:
        """Zero inequality with below-threshold coverage causes attrition.

        coverage_ratio = 0.5 / 1.0 = 0.5
        threshold = 1.0 + 0.0 = 1.0
        deficit = 1.0 - 0.5 = 0.5
        attrition = 0.5 × (0.5 + 0.0) = 0.5 × 0.5 = 0.25
        """
        rate = calculate_mortality_rate(
            wealth_per_capita=0.5,
            subsistence_needs=1.0,
            inequality=TC.ZERO_INEQUALITY,
        )
        expected = 0.5 * TC.MULTIPLIER_ZERO_INEQUALITY  # 0.25
        assert rate == pytest.approx(expected, abs=0.001)

    def test_multiplier_scales_with_inequality(self) -> None:
        """Higher inequality means faster attrition at same deficit.

        Both have deficit = 0.5, but higher inequality = faster attrition.
        """
        # Low inequality: deficit=0.5, multiplier=0.7
        rate_low = calculate_mortality_rate(
            wealth_per_capita=0.7,  # coverage=0.7, threshold=1.2
            subsistence_needs=1.0,
            inequality=TC.LOW_INEQUALITY,
        )

        # High inequality: deficit=0.5, multiplier=1.3
        rate_high = calculate_mortality_rate(
            wealth_per_capita=1.3,  # coverage=1.3, threshold=1.8
            subsistence_needs=1.0,
            inequality=TC.HIGH_INEQUALITY,
        )

        # Both have same deficit (0.5), but high inequality kills faster
        assert rate_high > rate_low


@pytest.mark.math
class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_zero_subsistence_no_deaths(self) -> None:
        """Zero subsistence needs means no deaths (division by zero guard).

        This is a guard against invalid inputs.
        """
        rate = calculate_mortality_rate(
            wealth_per_capita=1.0,
            subsistence_needs=0.0,
            inequality=TC.HIGH_INEQUALITY,
        )
        assert rate == 0.0

    def test_negative_subsistence_no_deaths(self) -> None:
        """Negative subsistence is treated as zero.

        Edge case: invalid inputs should not cause crashes.
        """
        rate = calculate_mortality_rate(
            wealth_per_capita=1.0,
            subsistence_needs=-1.0,
            inequality=TC.HIGH_INEQUALITY,
        )
        assert rate == 0.0

    def test_zero_wealth_full_attrition(self) -> None:
        """Zero wealth with any needs causes full attrition.

        coverage_ratio = 0.0 / 1.0 = 0.0
        threshold = 1.0 + 0.0 = 1.0
        deficit = 1.0 - 0.0 = 1.0
        attrition = 1.0 × 0.5 = 0.5
        """
        rate = calculate_mortality_rate(
            wealth_per_capita=0.0,
            subsistence_needs=1.0,
            inequality=TC.ZERO_INEQUALITY,
        )
        expected = 1.0 * TC.MULTIPLIER_ZERO_INEQUALITY  # 0.5
        assert rate == pytest.approx(expected, abs=0.001)

    def test_attrition_clamped_to_one(self) -> None:
        """Attrition rate cannot exceed 1.0.

        coverage_ratio = 0.0 / 1.0 = 0.0
        threshold = 1.0 + 0.95 = 1.95
        deficit = 1.95 - 0.0 = 1.95
        attrition = 1.95 × (0.5 + 0.95) = 1.95 × 1.45 = 2.8275 → clamped to 1.0
        """
        rate = calculate_mortality_rate(
            wealth_per_capita=0.0,
            subsistence_needs=1.0,
            inequality=TC.EXTREME_INEQUALITY,
        )
        assert rate == 1.0

    def test_attrition_clamped_to_zero(self) -> None:
        """Attrition rate cannot go negative (always >= 0).

        When coverage >> threshold, still returns 0.0 not negative.
        """
        rate = calculate_mortality_rate(
            wealth_per_capita=100.0,
            subsistence_needs=1.0,
            inequality=TC.ZERO_INEQUALITY,
        )
        assert rate == 0.0


@pytest.mark.math
class TestFormulaProperties:
    """Mathematical properties of the attrition formula."""

    def test_monotonic_in_inequality(self) -> None:
        """Higher inequality = higher attrition (all else equal).

        Fixed: coverage_ratio = 1.0, subsistence = 1.0
        As inequality increases, threshold increases, so deficit increases.
        """
        rates: list[float] = []
        for inequality in [0.0, 0.2, 0.5, 0.8]:
            rate = calculate_mortality_rate(
                wealth_per_capita=1.0,
                subsistence_needs=1.0,
                inequality=inequality,
            )
            rates.append(rate)

        # Each rate should be >= previous (monotonically increasing)
        for i in range(1, len(rates)):
            assert rates[i] >= rates[i - 1]

    def test_monotonic_in_wealth(self) -> None:
        """Higher wealth = lower attrition (all else equal).

        Fixed: subsistence = 1.0, inequality = 0.5
        As wealth increases, coverage increases, so deficit decreases.
        """
        rates: list[float] = []
        for wealth in [0.5, 1.0, 1.5, 2.0]:
            rate = calculate_mortality_rate(
                wealth_per_capita=wealth,
                subsistence_needs=1.0,
                inequality=TC.MODERATE_INEQUALITY,
            )
            rates.append(rate)

        # Each rate should be <= previous (monotonically decreasing)
        for i in range(1, len(rates)):
            assert rates[i] <= rates[i - 1]
