"""Type definitions for integrated financial crisis assessment.

Feature: 024-capital-volume-iii (US6, FR-012)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, computed_field


class CreditCrisisIndicator(BaseModel):
    """Composite credit-specific crisis signals.

    Three boolean signals (overproduction, profit squeeze, liquidity crisis)
    with a computed crisis_probability = sum(signals) / 3.

    Feature: 024-capital-volume-iii (FR-012)
    """

    model_config = ConfigDict(frozen=True)

    overproduction_signal: bool = Field(
        default=False,
        description="Overproduction detected in commodity markets",
    )
    profit_squeeze: bool = Field(
        default=False,
        description="Interest burden exceeds profit threshold",
    )
    liquidity_crisis: bool = Field(
        default=False,
        description="Credit system unable to roll over debt",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def crisis_probability(self) -> float:
        """Fraction of active crisis signals (0.0 to 1.0)."""
        signals = [self.overproduction_signal, self.profit_squeeze, self.liquidity_crisis]
        return sum(signals) / len(signals)


class FinancialCrisisAssessment(BaseModel):
    """Integrated assessment combining production, circulation, and financial signals.

    Four boolean signals with computed active_signals count and crisis_probability.

    Feature: 024-capital-volume-iii (FR-012, FR-016)
    """

    model_config = ConfigDict(frozen=True)

    fips_code: str = Field(..., min_length=5, max_length=5)
    year: int = Field(..., ge=2007, le=2040)
    profit_squeeze: bool = Field(
        default=False,
        description="Interest burden > INTEREST_BURDEN_SQUEEZE",
    )
    overaccumulation: bool = Field(
        default=False,
        description="Financialization > FINANCIALIZATION_BUBBLE",
    )
    credit_fragility: bool = Field(
        default=False,
        description="default_rate * spread > CREDIT_FRAGILITY_THRESHOLD",
    )
    claims_exceed_surplus: bool = Field(
        default=False,
        description="i + r + t > s",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def active_signals(self) -> int:
        """Count of active (True) crisis signals."""
        return sum(
            [
                self.profit_squeeze,
                self.overaccumulation,
                self.credit_fragility,
                self.claims_exceed_surplus,
            ]
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def crisis_probability(self) -> float:
        """Fraction of active crisis signals (0.0 to 1.0)."""
        return self.active_signals / 4

    @classmethod
    def normal(cls, fips: str = "00000", year: int = 2020) -> FinancialCrisisAssessment:
        """Factory for no-crisis state.

        Args:
            fips: FIPS code (default "00000").
            year: Assessment year (default 2020).

        Returns:
            FinancialCrisisAssessment with all signals False.
        """
        return cls(fips_code=fips, year=year)
