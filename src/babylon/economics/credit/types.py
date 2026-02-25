"""Type definitions for the credit dynamics module.

Feature: 024-capital-volume-iii (US2, US3)
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class CreditCyclePhase(StrEnum):
    """Credit cycle phase for multi-period credit dynamics.

    Feature: 024-capital-volume-iii (FR-006)

    Valid transitions (directed state machine):
        EXPANSION -> OVEREXTENSION -> CRISIS -> RECOVERY -> EXPANSION (main cycle)
        OVEREXTENSION -> STAGNATION (shortcut)
        RECOVERY -> STAGNATION (shortcut)
        STAGNATION is terminal (no exits)

    Values:
        EXPANSION: Credit growing, profit rate rising or stable.
        OVEREXTENSION: Credit growing despite falling profit rate.
        CRISIS: Default rate exceeds threshold, credit contracting.
        RECOVERY: Profit rate above threshold for consecutive periods.
        STAGNATION: Neither expansion nor crisis; secular stagnation.
    """

    EXPANSION = "expansion"
    OVEREXTENSION = "overextension"
    CRISIS = "crisis"
    RECOVERY = "recovery"
    STAGNATION = "stagnation"


# ============================================================================
# VALID TRANSITIONS (FR-006)
# ============================================================================

VALID_CREDIT_TRANSITIONS: Final[dict[CreditCyclePhase, frozenset[CreditCyclePhase]]] = {
    CreditCyclePhase.EXPANSION: frozenset({CreditCyclePhase.OVEREXTENSION}),
    CreditCyclePhase.OVEREXTENSION: frozenset(
        {
            CreditCyclePhase.CRISIS,
            CreditCyclePhase.STAGNATION,
        }
    ),
    CreditCyclePhase.CRISIS: frozenset({CreditCyclePhase.RECOVERY}),
    CreditCyclePhase.RECOVERY: frozenset(
        {
            CreditCyclePhase.EXPANSION,
            CreditCyclePhase.STAGNATION,
        }
    ),
    CreditCyclePhase.STAGNATION: frozenset(),  # Terminal — no exits
}


# ============================================================================
# THRESHOLD CONSTANTS (Module-Level)
# ============================================================================

INTEREST_BURDEN_SQUEEZE: Final[float] = 0.4
"""Interest burden ratio threshold triggering profit squeeze signal.

Traceability: FRED NIPA Table 1.14 (Net Interest / Corporate Profits).
Historical ratio exceeded 0.4 during early 1990s recession and 2008-09
crisis. When interest payments consume >40% of enterprise profit, the
profit squeeze accelerates crisis dynamics.
"""

FINANCIALIZATION_BUBBLE: Final[float] = 3.5
"""Financialization index threshold triggering overaccumulation signal.

Traceability: FRED TCMDO/GDP ratio. Total credit market debt outstanding
divided by GDP peaked at ~3.7 in 2008 (pre-crisis). A ratio of 3.5
signals systemic overaccumulation of fictitious capital relative to real
production capacity.
"""

CREDIT_FRAGILITY_THRESHOLD: Final[float] = 0.02
"""Credit fragility index (default_rate * spread) crisis threshold.

Traceability: FRED BAA-AAA spread * Moody's default rate product. During
2008 crisis, the product of corporate bond spread (~6%) and default rate
(~4%) exceeded 0.02. Below this threshold, credit system is stable.
"""

STAGNATION_CREDIT_GROWTH: Final[float] = 0.01
"""Credit expansion rate threshold for stagnation diagnosis.

Traceability: FRED TCMDO YoY growth rate. When credit growth falls below
1% annually, the economy is in secular stagnation — insufficient credit
creation for expansion but insufficient defaults for crisis clearing.
"""

OVEREXTENSION_DEFAULT_RATE: Final[float] = 0.03
"""Default rate threshold triggering transition from OVEREXTENSION to CRISIS.

Traceability: FRED charge-off rates on commercial and industrial loans.
Historical average ~1.5%; rates above 3% correspond to recession-level
defaults triggering credit contraction.
"""

RECOVERY_CONSECUTIVE_PERIODS: Final[int] = 2
"""Consecutive periods of profit rate above threshold required for RECOVERY.

Traceability: Matches Feature 018 CrisisPhase m_recovery parameter
(default=2) for consistency across crisis detection systems.
"""
