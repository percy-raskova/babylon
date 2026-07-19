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
    profit_squeeze: bool | None = Field(
        default=False,
        description="Interest burden > INTEREST_BURDEN_SQUEEZE; None if unmeasured",
    )
    overaccumulation: bool | None = Field(
        default=False,
        description="Financialization > FINANCIALIZATION_BUBBLE; None if unmeasured",
    )
    credit_fragility: bool | None = Field(
        default=False,
        description="default_rate * spread > credit_fragility_threshold(); None if unmeasured",
    )
    claims_exceed_surplus: bool | None = Field(
        default=False,
        description="i + r + t > s; None if unmeasured",
    )

    @property
    def _signals(self) -> tuple[bool | None, ...]:
        """The four crisis signals in declaration order."""
        return (
            self.profit_squeeze,
            self.overaccumulation,
            self.credit_fragility,
            self.claims_exceed_surplus,
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def active_signals(self) -> int:
        """Count of signals measured AND firing.

        A ``None`` signal is unmeasured, not quiescent (Constitution III.11),
        so it is excluded here rather than counted as a ``False``.
        """
        return sum(1 for signal in self._signals if signal is True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def measured_signals(self) -> int:
        """Count of signals that carry a real measurement (not ``None``).

        Published alongside :attr:`crisis_probability` so a consumer can tell
        "0.0 because nothing is wrong" from "0.0 because nothing was measured"
        — the distinction a fabricated ``False`` destroyed (U2.3 review
        findings 4 and 5).
        """
        return sum(1 for signal in self._signals if signal is not None)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def crisis_probability(self) -> float:
        """Fraction of MEASURED crisis signals that are firing (0.0 to 1.0).

        The denominator is :attr:`measured_signals`, not a fixed 4: dividing an
        unmeasured signal into the total would silently dilute the probability
        toward zero and report a calmer system than the data supports. When
        nothing was measured the probability is ``0.0`` — read it together with
        ``measured_signals == 0``, which is the honest "no assessment" state.
        """
        measured = self.measured_signals
        if measured == 0:
            return 0.0
        return self.active_signals / measured

    @classmethod
    def normal(cls, fips: str = "00000", year: int = 2020) -> FinancialCrisisAssessment:
        """Factory for a MEASURED no-crisis state.

        Every signal is explicitly ``False`` — measured and quiescent — which
        is deliberately distinct from the unmeasured ``None`` state.

        Args:
            fips: FIPS code (default "00000").
            year: Assessment year (default 2020).

        Returns:
            FinancialCrisisAssessment with all four signals measured False.
        """
        return cls(
            fips_code=fips,
            year=year,
            profit_squeeze=False,
            overaccumulation=False,
            credit_fragility=False,
            claims_exceed_surplus=False,
        )
