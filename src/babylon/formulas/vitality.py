"""Vitality formulas for demographic mortality calculations.

The Grinding Attrition formula models how inequality exposes marginal
workers to mortality even when average wealth is sufficient.

See Also:
    :doc:`/reference/vitality` for theoretical background.
    :class:`VitalitySystem` for system integration.
"""


def calculate_mortality_rate(
    wealth_per_capita: float,
    subsistence_needs: float,
    inequality: float,
) -> float:
    """Calculate mortality rate using coverage_ratio threshold.

    The formula ensures that with high inequality (e.g., 0.8), you need
    almost 2x subsistence (1.8 coverage) to prevent deaths.

    Args:
        wealth_per_capita: Total wealth / population.
        subsistence_needs: Per-capita subsistence requirement (s_bio + s_class).
        inequality: Gini coefficient [0, 1].

    Returns:
        Attrition rate [0, 1] representing fraction of population that dies.
    """
    if subsistence_needs <= 0:
        return 0.0

    coverage_ratio = wealth_per_capita / subsistence_needs
    threshold = 1.0 + inequality

    # If coverage exceeds threshold, even the poorest survive
    if coverage_ratio >= threshold:
        return 0.0

    # Risk tail is exposed - calculate attrition
    deficit = threshold - coverage_ratio
    attrition_rate = deficit * (0.5 + inequality)

    # Clamp to valid range
    return max(0.0, min(1.0, attrition_rate))
