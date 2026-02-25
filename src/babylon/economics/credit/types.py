"""Type definitions for the credit dynamics module.

Feature: 024-capital-volume-iii (US2, US3)
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, computed_field


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


# ============================================================================
# PYDANTIC MODELS (US2)
# ============================================================================


class InterestRateState(BaseModel):
    """National interest rate environment snapshot.

    Captures the FRED-sourced interest rate data for a given year.
    The effective_rate computed field provides the borrowing cost
    relevant for industrial capital (base rate + credit spread).

    Feature: 024-capital-volume-iii (FR-002, FR-003)
    """

    model_config = ConfigDict(frozen=True)

    year: int = Field(..., ge=2007, le=2040)
    base_rate: float = Field(..., ge=0.0, description="Federal funds rate (FEDFUNDS)")
    treasury_10y: float = Field(..., ge=0.0, description="10-year Treasury yield (DGS10)")
    baa_spread: float = Field(..., ge=0.0, description="Baa corporate spread (BAA10Y)")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def effective_rate(self) -> float:
        """Effective borrowing rate = base_rate + baa_spread."""
        return self.base_rate + self.baa_spread


class CreditState(BaseModel):
    """National credit system health snapshot.

    Tracks aggregate credit conditions and the current credit cycle phase.
    The credit_fragility computed field provides a crisis signal when
    the product of default_rate and spread_to_treasuries exceeds the
    CREDIT_FRAGILITY_THRESHOLD constant.

    Feature: 024-capital-volume-iii (FR-002, FR-006)
    """

    model_config = ConfigDict(frozen=True)

    year: int = Field(..., ge=2007, le=2040)
    total_credit: float = Field(..., ge=0.0, description="Total credit market debt (TCMDO)")
    credit_expansion_rate: float = Field(default=0.0, description="YoY credit growth rate")
    default_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Loan default fraction")
    spread_to_treasuries: float = Field(default=0.0, ge=0.0, description="Risk premium (BAA10Y)")
    phase: CreditCyclePhase = Field(default=CreditCyclePhase.EXPANSION)
    prev_phase: CreditCyclePhase | None = Field(default=None)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def credit_fragility(self) -> float:
        """Credit fragility index = default_rate * spread_to_treasuries."""
        return self.default_rate * self.spread_to_treasuries
