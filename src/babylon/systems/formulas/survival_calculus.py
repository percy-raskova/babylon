"""Survival Calculus formulas.

Core formulas for revolutionary decision-making:

- P(S|A) = 1 / (1 + e^(-k(x - x_crit))) : Survival via acquiescence (sigmoid)
- P(S|R) = Cohesion / (Repression + eps) : Survival via revolution
- Crossover: wealth where P(S|R) = P(S|A) (revolution becomes rational)
- Loss Aversion: lambda = 2.25 (Kahneman-Tversky)
"""

import math

from babylon.systems.formulas.constants import EPSILON, LOSS_AVERSION_COEFFICIENT


def calculate_acquiescence_probability(
    wealth: float,
    subsistence_threshold: float,
    steepness_k: float,
) -> float:
    """P(S|A) sigmoid. At threshold, probability = 0.5.

    Args:
        wealth: Current wealth/resources.
        subsistence_threshold: Minimum for survival (x_critical).
        steepness_k: Curve steepness.

    Returns:
        Probability [0, 1].

    Examples:
        >>> calculate_acquiescence_probability(100.0, 100.0, 0.1)
        0.5
    """
    exponent = -steepness_k * (wealth - subsistence_threshold)
    exponent = max(-500, min(500, exponent))  # Prevent overflow
    return 1.0 / (1.0 + math.exp(exponent))


def calculate_revolution_probability(cohesion: float, repression: float) -> float:
    """P(S|R) = Cohesion / (Repression + eps). Capped at 1.0.

    Args:
        cohesion: Organization level [0, 1].
        repression: State violence capacity [0, 1].

    Returns:
        Probability [0, 1].

    Examples:
        >>> calculate_revolution_probability(0.8, 0.2)
        1.0
        >>> calculate_revolution_probability(0.0, 0.5)
        0.0
    """
    if cohesion <= 0:
        return 0.0
    return min(1.0, cohesion / (repression + EPSILON))


def calculate_crossover_threshold(
    cohesion: float,
    repression: float,
    subsistence_threshold: float,
    steepness_k: float,
) -> float:
    """Wealth level where P(S|R) = P(S|A) (revolution becomes rational).

    Args:
        cohesion: Organization level.
        repression: State violence capacity.
        subsistence_threshold: Acquiescence threshold.
        steepness_k: Acquiescence curve steepness.

    Returns:
        Crossover wealth level [0, 1].
    """
    p_rev = calculate_revolution_probability(cohesion, repression)

    if p_rev <= 0 or p_rev >= 1:
        return 0.0 if p_rev <= 0 else 1.0

    ln_term = math.log(1.0 / p_rev - 1.0)
    crossover = subsistence_threshold - ln_term / steepness_k
    return max(0.0, min(1.0, crossover))


def apply_loss_aversion(value: float) -> float:
    """Amplify losses by 2.25x (Kahneman-Tversky).

    Args:
        value: Raw value change (negative = loss).

    Returns:
        Perceived value (losses amplified).

    Examples:
        >>> apply_loss_aversion(100.0)
        100.0
        >>> apply_loss_aversion(-100.0)
        -225.0
    """
    return value * LOSS_AVERSION_COEFFICIENT if value < 0 else value
