"""Type definitions for the credit dynamics module.

Feature: 024-capital-volume-iii (US2, US3)
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from babylon.config.defines import GameDefines


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


@lru_cache(maxsize=1)
def _default_defines() -> GameDefines:
    """Process-cached ``GameDefines.load_default()``.

    Same rationale as ``distribution.types._default_defines``: cached on
    FIRST USE rather than at import time, and bypassed entirely when a
    caller passes an explicit ``defines``.
    """
    return GameDefines.load_default()


def stagnation_credit_growth(defines: GameDefines | None = None) -> float:
    """Credit expansion rate threshold for stagnation diagnosis.

    Traceability: FRED TCMDO YoY growth rate. When credit growth falls below
    1% annually, the economy is in secular stagnation — insufficient credit
    creation for expansion but insufficient defaults for crisis clearing.

    Reads ``crisis.stagnation_credit_growth`` from the passed ``defines``, or
    from the process-cached default when omitted. Was a module-level ``Final``
    initialised from a bare ``GameDefines()`` — which read the dataclass
    defaults and ignored ``defines.yaml`` entirely — until the 2026-07-18
    honesty sweep.
    """
    resolved = defines if defines is not None else _default_defines()
    return resolved.crisis.stagnation_credit_growth


def credit_fragility_threshold(defines: GameDefines | None = None) -> float:
    """Expected-loss product above which the credit_fragility signal fires.

    The signal is ``default_rate * credit_spread > credit_fragility_threshold()``,
    where both inputs are DECIMALS: ``factory.py`` divides the FRED percent
    series (``FEDFUNDS``, ``DGS10``, ``BAA10Y``) by 100 at load time.

    Traceability: BAA10Y peaked at 5.56% (0.0556) in Dec 2008; with the
    documented 2% default-rate estimate (``capital_vol3.default_rate_estimate``)
    the crisis-peak product is 1.11e-3, while a calm year (1.8% spread) yields
    3.6e-4. The 1.0e-3 default therefore separates crisis from calm.

    Was a module-level ``Final`` of ``0.02`` — a value calibrated for
    PERCENT-scaled inputs — until the U2.3 code review measured that it
    required a 100% annual borrowing rate to cross, so ``credit_fragility``
    published ``False`` for every county in every modeled year, including the
    height of the 2008 credit crisis (review finding 5).

    Reads ``capital_vol3.credit_fragility_threshold`` from the passed
    ``defines``, or from the process-cached default when omitted.

    Args:
        defines: Optional run-scoped ``GameDefines``. Pass this whenever the
            caller holds one — the no-arg path resolves the on-disk
            ``defines.yaml`` and cannot see a ``--defines`` overlay.

    Returns:
        The expected-loss threshold as a decimal product.
    """
    resolved = defines if defines is not None else _default_defines()
    return resolved.capital_vol3.credit_fragility_threshold


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
    :func:`credit_fragility_threshold` accessor.

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


# ============================================================================
# FICTITIOUS CAPITAL (US3, FR-004, FR-005)
# ============================================================================


class FictitiousCapitalStock(BaseModel):
    """Accumulated financial claims on future value production.

    Feature: 024-capital-volume-iii (FR-004, FR-005)
    Derivatives tracked but excluded from primary index (double-counting).
    """

    model_config = ConfigDict(frozen=True)

    year: int = Field(..., ge=2007, le=2040)
    government_debt: float = Field(..., ge=0.0, description="Federal debt (GFDEBTN)")
    corporate_equity: float = Field(..., ge=0.0, description="Stock market cap (Wilshire)")
    corporate_debt: float = Field(..., ge=0.0, description="Corporate bonds and loans (Z.1)")
    household_debt: float = Field(..., ge=0.0, description="Mortgages, consumer, student (Z.1)")
    derivatives_notional: float = Field(
        default=0.0,
        ge=0.0,
        description="Derivative contracts (tracked, excluded from index)",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_claims(self) -> float:
        """Total fictitious capital excluding derivatives."""
        return (
            self.government_debt + self.corporate_equity + self.corporate_debt + self.household_debt
        )

    def ratio_to_real(self, real_gdp: float) -> float:
        """Financialization index = total_claims / real_gdp.

        Args:
            real_gdp: Real GDP in current dollars.

        Returns:
            Ratio of total financial claims to real production.
            Returns float('inf') if real_gdp <= 0.
        """
        if real_gdp <= 0.0:
            return float("inf")
        return self.total_claims / real_gdp


class EndogenousInterestRate(BaseModel):
    """Endogenous national interest rate (Capital Vol. III Part V).

    Marx: interest has no natural rate (ch. 22) — it is a *share of the
    profit* (ch. 23/24) set by the supply and demand of loanable
    money-capital (ch. 22). This model carries the computed rate together
    with the average rate of profit that bounds it, and encodes the ch. 22
    maximum ("the maximum limit of interest is the profit itself") as a
    construction invariant: ``rate < profit_rate_ceiling`` whenever there is
    a profit to divide, ``rate == 0`` when there is none.

    Feature: vol3-money-scissors U9.

    :ivar year: Simulation year (no upper ceiling — the campaign runs to
        2109; deliberately unlike ``InterestRateState.year``'s le=2040, which
        was a latent post-2040 crash on the live path).
    :ivar profit_rate_ceiling: Economy-wide realized general rate of profit
        ``r = Sum(s)/Sum(c+v)`` (surplus-weighted over the county tensors);
        ``0.0`` when no county carries a realized profit rate.
    :ivar rate: National interest rate ``i`` = ``r * share(tightness)``, or
        ``0.0`` when ``profit_rate_ceiling`` is ``0.0``.
    :ivar fragility_premium: Endogenous spread = ``i - r*base`` (>= 0); the
        crisis lift of the rate above its calm level. Replaces the BAA10Y
        runtime read.
    :ivar tightness: Loan-market tightness ``tau`` in [0, 1] (provenance).
    :ivar reserve_army_signal: The downturn demand signal ``s_r`` in [0, 1]
        (provenance).
    """

    model_config = ConfigDict(frozen=True)

    year: int = Field(..., ge=2007)
    profit_rate_ceiling: float = Field(..., ge=0.0)
    rate: float = Field(..., ge=0.0)
    fragility_premium: float = Field(..., ge=0.0)
    tightness: float = Field(..., ge=0.0, le=1.0)
    reserve_army_signal: float = Field(..., ge=0.0, le=1.0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def base_component(self) -> float:
        """The calm interest ``r*base`` = ``rate - fragility_premium``."""
        return self.rate - self.fragility_premium

    @model_validator(mode="after")
    def _verify_interest_below_profit(self) -> EndogenousInterestRate:
        """Enforce Marx's ch. 22 bound as a loud construction invariant.

        ``rate < profit_rate_ceiling`` when a profit exists; ``rate == 0``
        when it does not (Constitution III.11 — a violated bound is a loud
        ValueError at construction, never a silently wrong rate).
        """
        if self.profit_rate_ceiling <= 0.0:
            if self.rate != 0.0:
                raise ValueError(
                    f"rate must be 0.0 when profit_rate_ceiling is "
                    f"{self.profit_rate_ceiling!r} (no profit to divide), got "
                    f"{self.rate!r}"
                )
        elif self.rate >= self.profit_rate_ceiling:
            raise ValueError(
                f"rate ({self.rate!r}) must be strictly below "
                f"profit_rate_ceiling ({self.profit_rate_ceiling!r}) — "
                f"Capital Vol. III ch. 22: interest is a portion of the profit"
            )
        return self
