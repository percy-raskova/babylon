"""Type definitions for the MELT and Basket Visibility module.

Feature: 013-melt-basket-visibility
Date: 2026-02-01

This module defines the core type: ClassPosition enum for wage-based
class position classification per TVT Axiom E2.
"""

from __future__ import annotations

from enum import Enum, auto


class ClassPosition(Enum):
    """Wage-based class position for imperial rent analysis.

    This enumeration represents the three wage-based class positions
    derived from TVT (Topological Value Theory) Axiom E2.

    Scope Limitation:
        This classification is *wage-based* only. It classifies workers by
        their wage relative to value thresholds. It does NOT identify:

        - **Bourgeoisie**: Non-wage income from capital ownership
        - **Lumpen**: Excluded from production entirely (V_produced ≈ 0)

        Note: Subproletariat ≠ Lumpen. A subproletarian is *working* but paid
        below reproduction cost. A lumpen is *excluded* from wage labor entirely.

    Classification Rules:
        - LABOR_ARISTOCRACY: W > τ_effective (Φ_hour > 0, net extractor)
        - PROLETARIAT: τ_effective ≥ W > V_reproduction (exploited but reproducing)
        - SUBPROLETARIAT: W ≤ V_reproduction (working below reproduction cost)

    TVT Axiom References:
        - E1: V_reproduction (subsistence floor)
        - E2: Class position determination rules
        - E3-E4: Imperial rent formulas for each position

    Example:
        >>> from babylon.economics.melt import ClassPosition, NationalParameters
        >>> params = NationalParameters(year=2022, tau=65.0, tau_effective=44.0, ...)
        >>> if wage > params.tau_effective:
        ...     position = ClassPosition.LABOR_ARISTOCRACY
        >>> elif wage > params.v_reproduction:
        ...     position = ClassPosition.PROLETARIAT
        >>> else:
        ...     position = ClassPosition.SUBPROLETARIAT

    See Also:
        :class:`NationalParameters`: Contains threshold values
        :class:`ClassPositionClassifier`: Service for classification
    """

    LABOR_ARISTOCRACY = auto()
    """W > τ_effective: Net extractor of peripheral labor (Φ_hour > 0).

    Workers in this position earn wages above the effective MELT threshold,
    meaning they can command more labor through consumption than they expend
    in production. They extract imperial rent from peripheral workers.
    """

    PROLETARIAT = auto()
    """τ_effective ≥ W > V_reproduction: Exploited but self-reproducing.

    Workers in this position earn enough to reproduce their labor power
    but do not extract imperial rent. They are exploited within the
    standard capitalist framework but can sustain themselves.
    """

    SUBPROLETARIAT = auto()
    """W ≤ V_reproduction: Working but below reproduction cost.

    Workers in this position earn below the minimum needed to reproduce
    their labor power. They require external subsidies (family, state,
    informal economy) to survive. This is NOT the same as lumpen -
    subproletarians are *working* but underpaid.
    """


__all__ = ["ClassPosition"]
