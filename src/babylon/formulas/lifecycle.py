"""D-P-D' lifecycle circuit formulas (Feature 030).

Pure functions for population flow, legitimation index, Pareto inheritance,
ideology transmission, and shadow subsidy computation.

See Also:
    :mod:`babylon.economics.lifecycle.types`: Data models consuming these formulas.
    ``specs/030-dpd-lifecycle-circuit/quickstart.md``: Scenario test values.
"""

from __future__ import annotations

import math


def compute_population_flow(
    *,
    pop_d: float,
    pop_p: float,
    pop_d_prime: float,
    birth_rate: float,
    rate_d_to_p: float,
    rate_p_to_d_prime: float,
    rate_d_prime_to_death: float,
) -> tuple[float, float, float, float, float]:
    """Compute one-tick population transitions across D/P/D' phases.

    Applies birth, transition, and death rates to compute new population
    in each phase. All outputs are clamped to non-negative.

    Args:
        pop_d: Current D phase population.
        pop_p: Current P phase population.
        pop_d_prime: Current D' phase population.
        birth_rate: Births per P-phase person per tick.
        rate_d_to_p: D → P transition rate per tick.
        rate_p_to_d_prime: P → D' transition rate per tick.
        rate_d_prime_to_death: D' mortality rate per tick.

    Returns:
        Tuple of (new_pop_d, new_pop_p, new_pop_d_prime, births, deaths).

    Examples:
        >>> result = compute_population_flow(
        ...     pop_d=2150, pop_p=6050, pop_d_prime=1800,
        ...     birth_rate=0.0107, rate_d_to_p=0.0556,
        ...     rate_p_to_d_prime=0.0213, rate_d_prime_to_death=0.039,
        ... )
        >>> abs(result[3] - 64.735) < 1  # births ≈ 64.7
        True
    """
    births = birth_rate * pop_p
    d_to_p = rate_d_to_p * pop_d
    p_to_d_prime = rate_p_to_d_prime * pop_p
    deaths = rate_d_prime_to_death * pop_d_prime

    new_d = max(0.0, pop_d + births - d_to_p)
    new_p = max(0.0, pop_p + d_to_p - p_to_d_prime)
    new_d_prime = max(0.0, pop_d_prime + p_to_d_prime - deaths)

    return new_d, new_p, new_d_prime, births, deaths


def compute_dependency_ratio(
    *,
    pop_d: float,
    pop_p: float,
    pop_d_prime: float,
) -> float:
    """Compute dependency ratio: non-productive to productive population.

    Args:
        pop_d: D phase population.
        pop_p: P phase population.
        pop_d_prime: D' phase population.

    Returns:
        (pop_d + pop_d_prime) / pop_p, or inf if pop_p is zero.

    Examples:
        >>> compute_dependency_ratio(pop_d=2150, pop_p=6050, pop_d_prime=1800)
        0.6528...
    """
    if pop_p == 0.0:
        return math.inf
    return (pop_d + pop_d_prime) / pop_p


def compute_legitimation_index(
    *,
    pension_coverage: float,
    ss_replacement_rate: float,
    healthcare_security: float,
    home_ownership_rate: float,
    retirement_confidence: float,
    w_home: float,
    w_health: float,
    w_retire: float,
    w_pension: float,
    w_ss: float,
) -> float:
    """Compute weighted legitimation index from five material components.

    The index measures how credibly the D' promise is underwritten. Weight
    ordering reflects political judgment about which conditions most credibly
    back the promise.

    Args:
        pension_coverage: Fraction with pension access [0, 1].
        ss_replacement_rate: Social Security replacement ratio [0, 1].
        healthcare_security: Fraction with secure healthcare [0, 1].
        home_ownership_rate: Home ownership rate [0, 1].
        retirement_confidence: Subjective security assessment [0, 1].
        w_home: Weight for home ownership.
        w_health: Weight for healthcare security.
        w_retire: Weight for retirement confidence.
        w_pension: Weight for pension coverage.
        w_ss: Weight for SS replacement.

    Returns:
        Legitimation index [0, 1].

    Examples:
        >>> compute_legitimation_index(
        ...     pension_coverage=0.73, ss_replacement_rate=0.43,
        ...     healthcare_security=0.60, home_ownership_rate=0.66,
        ...     retirement_confidence=0.50,
        ...     w_home=0.35, w_health=0.30, w_retire=0.20,
        ...     w_pension=0.10, w_ss=0.05,
        ... )
        0.6055
    """
    index = (
        w_home * home_ownership_rate
        + w_health * healthcare_security
        + w_retire * retirement_confidence
        + w_pension * pension_coverage
        + w_ss * ss_replacement_rate
    )
    return max(0.0, min(1.0, index))


def compute_pareto_gini(*, alpha: float) -> float:
    """Compute Gini coefficient from Pareto shape parameter.

    For a Pareto distribution with shape α > 0.5:
        Gini = 1 / (2α - 1)

    Args:
        alpha: Pareto shape parameter (must be > 0.5).

    Returns:
        Gini coefficient [0, 1].

    Raises:
        ValueError: If alpha <= 0.5 (Gini would be >= 1.0 or undefined).

    Examples:
        >>> compute_pareto_gini(alpha=1.5)
        0.5
    """
    if alpha <= 0.5:
        msg = f"Pareto alpha must be > 0.5 for valid Gini, got {alpha}"
        raise ValueError(msg)
    return 1.0 / (2.0 * alpha - 1.0)


def compute_ideology_transmission(
    *,
    caregiver_ideology: float,
    institutional_hegemony: float,
    caregiver_weight: float,
    institutional_weight: float,
) -> float:
    """Compute ideology transmitted during D→P phase transition.

    Blends caregiver (family) influence with institutional hegemony
    (schools, media, state) to determine P-phase entry ideology.

    Args:
        caregiver_ideology: Caregiver consciousness level.
        institutional_hegemony: Institutional hegemonic pressure.
        caregiver_weight: Weight for caregiver influence.
        institutional_weight: Weight for institutional influence.

    Returns:
        Transmitted ideology value.

    Examples:
        >>> compute_ideology_transmission(
        ...     caregiver_ideology=0.3, institutional_hegemony=0.8,
        ...     caregiver_weight=0.7, institutional_weight=0.3,
        ... )
        0.45
    """
    return caregiver_weight * caregiver_ideology + institutional_weight * institutional_hegemony


def compute_shadow_subsidy(
    *,
    p_g2_labor_value: float,
    wage_paid_for_d_g2: float,
) -> float:
    """Compute shadow subsidy from intergenerational labor reproduction.

    The shadow subsidy is the difference between the value of labor-power
    produced (P_g2) and the wages paid to P_g1 for raising D_g2. This
    measures the unpaid reproductive labor externalized to households.

    Args:
        p_g2_labor_value: Value of next-generation labor-power produced.
        wage_paid_for_d_g2: Investment in D phase child-rearing.

    Returns:
        Shadow subsidy (always >= 0).

    Examples:
        >>> compute_shadow_subsidy(p_g2_labor_value=60000, wage_paid_for_d_g2=12000)
        48000.0
    """
    return max(0.0, p_g2_labor_value - wage_paid_for_d_g2)


__all__ = [
    "compute_dependency_ratio",
    "compute_ideology_transmission",
    "compute_legitimation_index",
    "compute_pareto_gini",
    "compute_population_flow",
    "compute_shadow_subsidy",
]
