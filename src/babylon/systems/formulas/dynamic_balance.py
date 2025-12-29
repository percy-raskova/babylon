"""Dynamic Balance formulas (Sprint 3.4.4).

The bourgeoisie as a rational actor responding to material conditions:
- BRIBERY: High pool, low tension -> increase wages
- AUSTERITY: Low pool, low tension -> cut wages
- IRON_FIST: Low pool, high tension -> increase repression
- CRISIS: Critical pool -> emergency measures
"""


class BourgeoisieDecision:
    """Enumeration of bourgeoisie decision types.

    Sprint 3.4.4: Dynamic Balance - The "Driver" decisions based on
    imperial rent pool level and aggregate class tension.
    """

    NO_CHANGE = "no_change"
    BRIBERY = "bribery"
    AUSTERITY = "austerity"
    IRON_FIST = "iron_fist"
    CRISIS = "crisis"


def calculate_bourgeoisie_decision(
    pool_ratio: float,
    aggregate_tension: float,
    high_threshold: float = 0.7,
    low_threshold: float = 0.3,
    critical_threshold: float = 0.1,
) -> tuple[str, float, float]:
    """Calculate bourgeoisie policy decision based on pool level and tension.

    Sprint 3.4.4: Dynamic Balance - The bourgeoisie as a rational actor
    responding to material conditions.

    Decision Matrix:
        pool_ratio >= high AND tension < 0.3 -> BRIBERY (increase wages +5%)
        pool_ratio < critical -> CRISIS (wages to minimum, repression +20%)
        pool_ratio < low AND tension > 0.5 -> IRON_FIST (repression +10%)
        pool_ratio < low AND tension <= 0.5 -> AUSTERITY (wages -5%)
        else -> NO_CHANGE (maintain status quo)

    Args:
        pool_ratio: Current pool / initial pool (0.0 to 1.0+)
        aggregate_tension: Average tension across class relationships (0.0 to 1.0)
        high_threshold: Pool ratio above which prosperity is declared (default 0.7)
        low_threshold: Pool ratio below which austerity begins (default 0.3)
        critical_threshold: Pool ratio below which crisis fires (default 0.1)

    Returns:
        Tuple of (decision: str, wage_delta: float, repression_delta: float)
        - decision: One of BourgeoisieDecision values
        - wage_delta: Change to wage rate (positive = increase)
        - repression_delta: Change to repression level (positive = increase)

    Example:
        # Prosperity: high pool, low tension -> increase wages
        decision, wage_d, repr_d = calculate_bourgeoisie_decision(0.8, 0.2)
        # Returns ("bribery", 0.05, 0.0)

        # Crisis: pool below critical -> emergency measures
        decision, wage_d, repr_d = calculate_bourgeoisie_decision(0.05, 0.5)
        # Returns ("crisis", -0.15, 0.20)
    """
    # Standard deltas for each policy
    bribery_wage_increase = 0.05
    austerity_wage_cut = -0.05
    iron_fist_repression_boost = 0.10
    crisis_wage_slash = -0.15
    crisis_repression_spike = 0.20

    # Decision logic priority (crisis first, then by pool level)

    # CRISIS: Pool critically low - emergency measures regardless of tension
    if pool_ratio < critical_threshold:
        return (
            BourgeoisieDecision.CRISIS,
            crisis_wage_slash,
            crisis_repression_spike,
        )

    # PROSPERITY: High pool - can afford bribery if tension is low
    if pool_ratio >= high_threshold and aggregate_tension < 0.3:
        return (
            BourgeoisieDecision.BRIBERY,
            bribery_wage_increase,
            0.0,
        )

    # AUSTERITY ZONE: Low pool - choose between iron fist and wage cuts
    if pool_ratio < low_threshold:
        if aggregate_tension > 0.5:
            # High tension + low resources = repression
            return (
                BourgeoisieDecision.IRON_FIST,
                0.0,
                iron_fist_repression_boost,
            )
        else:
            # Low tension + low resources = can cut wages safely
            return (
                BourgeoisieDecision.AUSTERITY,
                austerity_wage_cut,
                0.0,
            )

    # NEUTRAL ZONE: Mid-range pool - maintain status quo
    return (BourgeoisieDecision.NO_CHANGE, 0.0, 0.0)
