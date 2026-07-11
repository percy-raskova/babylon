"""Type definitions for the surplus value distribution module.

Feature: 024-capital-volume-iii (US1)
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, Field, computed_field

# ============================================================================
# THRESHOLD CONSTANTS (Module-Level)
# ============================================================================

DEBT_SPIRAL_THRESHOLD: Final[float] = 0.5
"""Accumulated debt / annual surplus ratio triggering crisis flag.

Traceability: When cumulative enterprise losses (accumulated debt)
exceed 50% of a county's annual surplus value, the debt spiral is
structurally self-reinforcing. Derived from NBER recession analysis
of corporate debt-to-earnings ratios during 2001 and 2008 recessions.
"""

DISTRIBUTION_EPSILON: Final[float] = 1e-9
"""Floating-point tolerance for surplus distribution accounting identity.

The identity s = p + i + r + t must hold within this epsilon.
Standard IEEE 754 double-precision tolerance for financial accounting.
"""


# ============================================================================
# SURPLUS VALUE DISTRIBUTION
# ============================================================================


class SurplusValueDistribution(BaseModel):
    """Decomposition of surplus value into competing claims.

    Feature: 024-capital-volume-iii (FR-001)
    Identity: s = p + i + r + t (within DISTRIBUTION_EPSILON)

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
        return bool(abs(distributed - self.total_surplus_produced) < DISTRIBUTION_EPSILON)

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

        Args:
            current: Current debt state.
            enterprise_profit: Enterprise profit for the period (may be negative).
            new_year: Calendar year for the new state.

        Returns:
            New DebtAccumulation reflecting the update.
        """
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
