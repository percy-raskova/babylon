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
    # Policy delta parameters (extracted from hardcoded values)
    bribery_wage_delta: float = 0.05,
    austerity_wage_delta: float = -0.05,
    iron_fist_repression_delta: float = 0.10,
    crisis_wage_delta: float = -0.15,
    crisis_repression_delta: float = 0.20,
    # Tension threshold parameters
    bribery_tension_threshold: float = 0.3,
    iron_fist_tension_threshold: float = 0.5,
) -> tuple[str, float, float]:
    """Calculate bourgeoisie policy decision based on pool level and tension.

    Sprint 3.4.4: Dynamic Balance - The bourgeoisie as a rational actor
    responding to material conditions.

    Decision Matrix:
        pool_ratio >= high AND tension < bribery_tension -> BRIBERY
        pool_ratio < critical -> CRISIS (emergency measures)
        pool_ratio < low AND tension > iron_fist_tension -> IRON_FIST
        pool_ratio < low AND tension <= iron_fist_tension -> AUSTERITY
        else -> NO_CHANGE (maintain status quo)

    Args:
        pool_ratio: Current pool / initial pool (0.0 to 1.0+)
        aggregate_tension: Average tension across class relationships (0.0 to 1.0)
        high_threshold: Pool ratio above which prosperity is declared (default 0.7)
        low_threshold: Pool ratio below which austerity begins (default 0.3)
        critical_threshold: Pool ratio below which crisis fires (default 0.1)
        bribery_wage_delta: Wage increase during prosperity (default 0.05)
        austerity_wage_delta: Wage cut during austerity (default -0.05)
        iron_fist_repression_delta: Repression increase during iron fist (default 0.10)
        crisis_wage_delta: Emergency wage cut during crisis (default -0.15)
        crisis_repression_delta: Emergency repression spike (default 0.20)
        bribery_tension_threshold: Max tension for bribery policy (default 0.3)
        iron_fist_tension_threshold: Min tension for iron fist policy (default 0.5)

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
    # Decision logic priority (crisis first, then by pool level)

    # CRISIS: Pool critically low - emergency measures regardless of tension
    if pool_ratio < critical_threshold:
        return (
            BourgeoisieDecision.CRISIS,
            crisis_wage_delta,
            crisis_repression_delta,
        )

    # PROSPERITY: High pool - can afford bribery if tension is low
    if pool_ratio >= high_threshold and aggregate_tension < bribery_tension_threshold:
        return (
            BourgeoisieDecision.BRIBERY,
            bribery_wage_delta,
            0.0,
        )

    # AUSTERITY ZONE: Low pool - choose between iron fist and wage cuts
    if pool_ratio < low_threshold:
        if aggregate_tension > iron_fist_tension_threshold:
            # High tension + low resources = repression
            return (
                BourgeoisieDecision.IRON_FIST,
                0.0,
                iron_fist_repression_delta,
            )
        else:
            # Low tension + low resources = can cut wages safely
            return (
                BourgeoisieDecision.AUSTERITY,
                austerity_wage_delta,
                0.0,
            )

    # NEUTRAL ZONE: Mid-range pool - maintain status quo
    return (BourgeoisieDecision.NO_CHANGE, 0.0, 0.0)
