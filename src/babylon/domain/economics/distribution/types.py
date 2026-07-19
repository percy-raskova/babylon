"""Type definitions for the surplus value distribution module.

Feature: 024-capital-volume-iii (US1)
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel, ConfigDict, Field, computed_field

from babylon.config.defines import GameDefines
from babylon.domain.economics.tensor import year_within_modeled_range

# ============================================================================
# THRESHOLD ACCESSORS (GameDefines-backed)
# ============================================================================


@lru_cache(maxsize=1)
def _default_defines() -> GameDefines:
    """Process-cached ``GameDefines.load_default()`` for the accessors below.

    Cached on FIRST USE, not at import time — which is the whole point of the
    migration. A process that never touches these accessors (layer-0.5
    sentinels, the docs build) never reads the file, and any caller that holds
    a real ``GameDefines`` passes it explicitly and bypasses the cache
    entirely. Tests that need a different default call
    ``_default_defines.cache_clear()``.

    MEASURED REACHABILITY (U2.3 review finding 1 — corrected 2026-07-18). An
    earlier revision of this docstring justified the cache by claiming
    ``distribution_complete`` is "evaluated per county per tick". It is not:
    instrumenting these accessors across a full live Wayne run counted ZERO
    production invocations of either. ``distribution_complete`` has no
    production reader — ``graph_bridge.py`` publishes ``interest_payments``,
    ``ground_rent``, ``rentier_share``, ``profit_of_enterprise``,
    ``financialization_share`` and ``claims_exceed_surplus`` but not this
    field, and no county-state ``model_dump()`` occurs in the tick or
    persistence path, so the lazy ``computed_field`` never fires.
    ``debt_spiral_threshold`` has no consumer at all.

    The cache is still correct (an uncached ``load_default()`` re-parses
    ``defines.yaml`` from disk on every call), but it is currently insurance
    against a future hot path rather than a description of one. The live
    counts are pinned by
    ``tests/integration/economics/test_vol3_defines_reachability_live.py``;
    wiring is owed by U3 (graph publication) and U5 (debt_spiral opposition).

    RUN SCOPE (U2.3 review finding 3): this path resolves the ON-DISK
    ``defines.yaml`` and cannot see a headless-runner ``--defines`` overlay.
    Callers holding a run-scoped ``GameDefines`` must pass it explicitly.
    """
    return GameDefines.load_default()


def debt_spiral_threshold(defines: GameDefines | None = None) -> float:
    """Accumulated debt / annual surplus ratio triggering crisis flag.

    Traceability: When cumulative enterprise losses (accumulated debt)
    exceed 50% of a county's annual surplus value, the debt spiral is
    structurally self-reinforcing. Derived from NBER recession analysis
    of corporate debt-to-earnings ratios during 2001 and 2008 recessions.
    GameDefines-backed (``capital_vol3.debt_spiral_threshold``) since the
    2026-07-18 honesty sweep — moddable via defines.yaml.

    Reads ``capital_vol3.debt_spiral_threshold`` from the passed
    ``defines``, or from the process-cached default when omitted.
    """
    resolved = defines if defines is not None else _default_defines()
    return resolved.capital_vol3.debt_spiral_threshold


def distribution_epsilon(defines: GameDefines | None = None) -> float:
    """Floating-point tolerance for surplus distribution accounting identity.

    The identity s = p + i + r + t must hold within this epsilon.
    Standard IEEE 754 double-precision tolerance for financial accounting.
    GameDefines-backed (``capital_vol3.distribution_epsilon``) since the
    2026-07-18 honesty sweep.

    Reads ``capital_vol3.distribution_epsilon`` from the passed
    ``defines``, or from the process-cached default when omitted.
    """
    resolved = defines if defines is not None else _default_defines()
    return resolved.capital_vol3.distribution_epsilon


# ============================================================================
# SURPLUS VALUE DISTRIBUTION
# ============================================================================


class SurplusValueDistribution(BaseModel):
    """Decomposition of surplus value into competing claims.

    Feature: 024-capital-volume-iii (FR-001)
    Identity: s = p + i + r + t (within :func:`distribution_epsilon`)

    Profit of enterprise is the residual after interest, rent, and taxes
    are deducted from total surplus. It may go negative when claims exceed
    the surplus produced (debt spiral condition).

    Args:
        fips_code: 5-digit county FIPS code.
        year: Calendar year (2007-2040).
        total_surplus_produced: Total surplus value from ValueTensor4x3.
        interest_payments: Interest on borrowed capital.
        ground_rent: Rental income extracted by landowners.
        taxes_on_surplus: Corporate income taxes on surplus.
    """

    model_config = ConfigDict(frozen=True)

    fips_code: str = Field(..., min_length=5, max_length=5)
    year: int = Field(..., ge=2007, le=2040)
    total_surplus_produced: float = Field(..., ge=0)
    interest_payments: float = Field(..., ge=0)
    ground_rent: float = Field(..., ge=0)
    taxes_on_surplus: float = Field(..., ge=0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def profit_of_enterprise(self) -> float:
        """Residual: p = s - i - r - t. May be negative."""
        return (
            self.total_surplus_produced
            - self.interest_payments
            - self.ground_rent
            - self.taxes_on_surplus
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def distribution_complete(self) -> bool:
        """Verify accounting identity holds within epsilon."""
        distributed = (
            self.interest_payments
            + self.ground_rent
            + self.taxes_on_surplus
            + self.profit_of_enterprise
        )
        return bool(abs(distributed - self.total_surplus_produced) < distribution_epsilon())

    @computed_field  # type: ignore[prop-decorator]
    @property
    def financialization_share(self) -> float:
        """Interest as share of surplus. 0.0 if surplus is zero."""
        if self.total_surplus_produced == 0.0:
            return 0.0
        return self.interest_payments / self.total_surplus_produced

    @computed_field  # type: ignore[prop-decorator]
    @property
    def rentier_share(self) -> float:
        """Rent as share of surplus. 0.0 if surplus is zero."""
        if self.total_surplus_produced == 0.0:
            return 0.0
        return self.ground_rent / self.total_surplus_produced

    @computed_field  # type: ignore[prop-decorator]
    @property
    def claims_exceed_surplus(self) -> bool:
        """True when i + r + t > s (enterprise profit is negative)."""
        total_claims = self.interest_payments + self.ground_rent + self.taxes_on_surplus
        return bool(total_claims > self.total_surplus_produced)


# ============================================================================
# DEBT ACCUMULATION
# ============================================================================


class DebtAccumulation(BaseModel):
    """Cumulative debt tracker for enterprise profit shortfalls.

    Feature: 024-capital-volume-iii (FR-019)

    When enterprise profit is negative (claims exceed surplus), the deficit
    accumulates as debt. Positive profit retires debt up to the accumulated
    amount. Consecutive deficit ticks track how long the spiral persists.

    Args:
        fips_code: 5-digit county FIPS code.
        year: Calendar year (2007-2040).
        accumulated_debt: Total accumulated deficit (always >= 0).
        consecutive_deficit_ticks: Number of consecutive periods with negative profit.
    """

    model_config = ConfigDict(frozen=True)

    fips_code: str = Field(..., min_length=5, max_length=5)
    year: int = Field(..., ge=2007, le=2040)
    accumulated_debt: float = Field(default=0.0, ge=0)
    consecutive_deficit_ticks: int = Field(default=0, ge=0)

    @classmethod
    def default(cls, fips: str = "00000", year: int = 2020) -> DebtAccumulation:
        """Factory for zero-debt initial state.

        Args:
            fips: 5-digit county FIPS code. Defaults to "00000".
            year: Calendar year. Defaults to 2020.

        Returns:
            DebtAccumulation with zero debt and zero deficit ticks.
        """
        return cls(
            fips_code=fips,
            year=year,
            accumulated_debt=0.0,
            consecutive_deficit_ticks=0,
        )

    @classmethod
    def update(
        cls,
        current: DebtAccumulation,
        enterprise_profit: float,
        new_year: int,
    ) -> DebtAccumulation:
        """Create updated state based on current period profit.

        If profit < 0: debt increases by |profit|, deficit ticks increment.
        If profit >= 0: debt decreases by min(profit, debt), deficit ticks reset.

        Honest absence (Constitution III.11): if ``new_year`` falls outside
        Volume III's modeled financial-data window
        (:func:`babylon.domain.economics.tensor.year_within_modeled_range`),
        ``current`` is returned UNCHANGED — the debt state carries forward
        rather than raising a year-range ``ValidationError`` or fabricating
        a value for an unmodeled year (spec 2026-07-18
        vol3-money-scissors-design, D1's "endogenous thereafter" principle).

        Args:
            current: Current debt state.
            enterprise_profit: Enterprise profit for the period (may be negative).
            new_year: Calendar year for the new state.

        Returns:
            New DebtAccumulation reflecting the update, or ``current``
            unchanged if ``new_year`` is outside the modeled window.
        """
        if not year_within_modeled_range(new_year):
            return current
        if enterprise_profit < 0:
            new_debt = current.accumulated_debt + abs(enterprise_profit)
            new_ticks = current.consecutive_deficit_ticks + 1
        else:
            reduction = min(enterprise_profit, current.accumulated_debt)
            new_debt = current.accumulated_debt - reduction
            new_ticks = 0
        return cls(
            fips_code=current.fips_code,
            year=new_year,
            accumulated_debt=new_debt,
            consecutive_deficit_ticks=new_ticks,
        )
