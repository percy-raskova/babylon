"""Type definitions for the MELT and Basket Visibility module.

Feature: 013-melt-basket-visibility
Date: 2026-02-01

This module defines the core type: ClassPosition enum for wealth-based
class position classification per TVT Axiom E1 (revised).

Theoretical Clarification: Class vs Imperial Rent
    **Class position** is determined by **wealth percentile** (accumulated extraction):
    - The structural relationship to the means of production is measured by wealth
    - A proletarian can have Φ_hour > 0 (benefit from cheap imports) while remaining
      proletarian - they consume rather than accumulate the imperial subsidy

    **Imperial rent (Φ_hour)** measures **extraction rate** (flow):
    - Φ_hour is used for aggregate drain validation (Hickel), NOT class position
    - See ImperialRentCalculator for flow-based extraction metrics

    This separation resolves the 30-50% vs 50-70% LA share debate:
    - 40% LA emerges naturally from wealth distribution (50th-90th percentile)
    - γ_basket stays empirically grounded (0.68)
    - No parameter tuning required
"""

from __future__ import annotations

from enum import Enum, auto


class ClassPosition(Enum):
    """Wealth-based class position in Babylon's class analysis.

    Class position is determined by **wealth percentile** (stock), NOT income
    threshold (flow). This separation resolves the theoretical tension between:
    1. Imperial rent flow (Φ_hour) - how much you extract per hour via consumption
    2. Class position - your structural relationship to the means of production

    Classification (Wealth-Based):
        | Class             | Wealth Percentile | Pop Share | Description |
        |-------------------|-------------------|-----------|-------------|
        | BOURGEOISIE       | Top 1%            | 1%        | Owns means of production |
        | PETIT_BOURGEOISIE | 90th-99th         | 9%        | Small capital, PMC |
        | LABOR_ARISTOCRACY | 50th-90th         | 40%       | Positive net wealth |
        | PROLETARIAT       | Bottom 50%, empl. | ~35%      | Sells labor, no wealth |
        | LUMPENPROLETARIAT | Bottom 50%, excl. | ~15%      | Outside labor market |

    Key Insight:
        A proletarian (bottom 50% wealth) CAN have Φ_hour > 0 (benefit from cheap
        imports) while remaining proletarian. They consume the imperial subsidy
        rather than accumulating it as wealth. Class position is about accumulated
        extraction, not flow rate.

    TVT Axiom References:
        - E1 (Revised): Wealth-based classification
        - E2 (Revised): Imperial rent is separate concern
        - E3-E4: Imperial rent formulas (unchanged)

    Example:
        >>> from babylon.economics.melt import ClassPosition
        >>> # Wealth-based classification
        >>> if wealth_percentile >= 99:
        ...     position = ClassPosition.BOURGEOISIE
        >>> elif wealth_percentile >= 90:
        ...     position = ClassPosition.PETIT_BOURGEOISIE
        >>> elif wealth_percentile >= 50:
        ...     position = ClassPosition.LABOR_ARISTOCRACY
        >>> elif employed:
        ...     position = ClassPosition.PROLETARIAT
        >>> else:
        ...     position = ClassPosition.LUMPENPROLETARIAT

    See Also:
        :class:`NationalParameters`: Contains threshold values
        :class:`ClassPositionClassifier`: Service for classification
        :class:`ImperialRentCalculator`: Flow-based extraction metrics (separate concern)
    """

    BOURGEOISIE = auto()
    """Top 1% wealth: Owns means of production.

    The capitalist class derives income primarily from capital ownership,
    not wage labor. Wealth percentile ≥ 99 (approximately top 1% of net worth).

    Note: This classification requires wealth data (Fed SCF nationally,
    home ownership proxy at county level), not income data.
    """

    PETIT_BOURGEOISIE = auto()
    """90th-99th percentile wealth: Small capital, professional-managerial class.

    Small business owners, high-wealth professionals, and upper management
    with significant capital accumulation but not owning means of production
    at bourgeoisie scale.

    Population share: ~9% (90th to 99th percentile = 9 percentage points)
    """

    LABOR_ARISTOCRACY = auto()
    """50th-90th percentile wealth: Positive net wealth, material system stake.

    Workers with accumulated wealth (primarily home equity) who have material
    stake in system stability. They may benefit from imperial rent flows
    (Φ_hour > 0) AND accumulate that benefit as wealth.

    Population share: ~40% (50th to 90th percentile = 40 percentage points)
    This emerges naturally from wealth distribution, not parameter tuning.

    Note: The old income-based definition (W > τ_effective) is deprecated.
    See classify() method for backward compatibility.
    """

    PROLETARIAT = auto()
    """Bottom 50% wealth, employed: Sells labor, no significant net wealth.

    Workers with little or no accumulated wealth who sell their labor power.
    They may have Φ_hour > 0 (benefit from cheap imports) but consume the
    subsidy rather than accumulating it as wealth.

    Population share: ~35% (bottom 50% minus lumpenproletariat)
    """

    LUMPENPROLETARIAT = auto()
    """Bottom 50% wealth, excluded from labor market.

    Those excluded from formal wage labor entirely: chronically unemployed,
    incarcerated, disabled without support, informal economy participants.
    This is distinct from PROLETARIAT who are employed but poor.

    Population share: ~15% (estimated from labor force participation)
    """


# Legacy alias for backward compatibility
SUBPROLETARIAT = ClassPosition.LUMPENPROLETARIAT
"""DEPRECATED: Use LUMPENPROLETARIAT for excluded workers.

The old SUBPROLETARIAT (W ≤ V_reproduction) conflated two distinct concepts:
1. Workers paid below reproduction cost (still employed, just underpaid)
2. Those excluded from labor market entirely (lumpenproletariat)

The wealth-based model handles both through PROLETARIAT (employed but no wealth)
and LUMPENPROLETARIAT (excluded from labor market).
"""


__all__ = ["ClassPosition", "SUBPROLETARIAT"]
