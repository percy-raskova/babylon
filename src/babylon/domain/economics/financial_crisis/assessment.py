"""Integrated financial crisis assessment.

Feature: 024-capital-volume-iii (US6, FR-012)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from babylon.domain.economics.credit.types import (
    FINANCIALIZATION_BUBBLE,
    INTEREST_BURDEN_SQUEEZE,
    credit_fragility_threshold,
)
from babylon.domain.economics.financial_crisis.types import FinancialCrisisAssessment

if TYPE_CHECKING:
    from babylon.config.defines import GameDefines


class FinancialCrisisAssessor(Protocol):
    """Protocol for integrated financial crisis assessment.

    Combines interest burden, financialization, credit fragility,
    and surplus-claims signals into a unified assessment.
    """

    def assess(
        self,
        fips: str,
        year: int,
        interest_burden_ratio: float,
        financialization_ratio: float | None,
        default_rate: float,
        credit_spread: float | None,
        claims_exceed_surplus: bool,
    ) -> FinancialCrisisAssessment:
        """Assess financial crisis probability for a county-year.

        Args:
            fips: 5-digit FIPS code.
            year: Assessment year.
            interest_burden_ratio: Interest payments / enterprise profit.
            financialization_ratio: Total credit / GDP, or ``None`` when the
                fictitious-capital calculator had no data — the resulting
                ``overaccumulation`` signal is then ``None``, not ``False``.
            default_rate: Loan default fraction [0, 1].
            credit_spread: Risk premium (BAA10Y) as a DECIMAL, or ``None``
                when the interest calculator had no data. NOT the effective
                borrowing rate — passing base+spread here overstates the
                fragility product by roughly a factor of three.
            claims_exceed_surplus: Whether financial claims exceed surplus value.

        Returns:
            FinancialCrisisAssessment with computed signals.
        """
        ...


class DefaultFinancialCrisisAssessor:
    """Default implementation using thresholds from credit/types.py.

    Thresholds:
        INTEREST_BURDEN_SQUEEZE (0.4): Profit squeeze signal.
        FINANCIALIZATION_BUBBLE (3.5): Overaccumulation signal.
        credit_fragility_threshold() (1.0e-3, GameDefines-backed): Credit
        fragility signal.

    Args:
        defines: Optional run-scoped ``GameDefines``. Supplied, the fragility
            threshold resolves from it; omitted, it resolves the process
            default, which cannot see a headless-runner ``--defines`` overlay
            (U2.3 review finding 3).
    """

    def __init__(self, defines: GameDefines | None = None) -> None:
        self._defines = defines

    def assess(
        self,
        fips: str,
        year: int,
        interest_burden_ratio: float,
        financialization_ratio: float | None,
        default_rate: float,
        credit_spread: float | None,
        claims_exceed_surplus: bool,
    ) -> FinancialCrisisAssessment:
        """Assess financial crisis probability for a county-year.

        Honest absence (Constitution III.11): a signal whose inputs are
        unavailable is published as ``None``. Publishing ``False`` would be
        byte-identical to a genuine measurement of a healthy county, which is
        what the caller's fabricated ``financialization_ratio = 0.0`` used to
        produce whenever the fictitious-capital calculator returned a
        ``NoDataSentinel`` (U2.3 review finding 4).

        Args:
            fips: 5-digit FIPS code.
            year: Assessment year.
            interest_burden_ratio: Interest payments / enterprise profit.
            financialization_ratio: Total credit / GDP, or ``None`` if absent.
            default_rate: Loan default fraction [0, 1].
            credit_spread: Risk premium (BAA10Y) as a DECIMAL, or ``None``.
            claims_exceed_surplus: Whether financial claims exceed surplus value.

        Returns:
            FinancialCrisisAssessment whose ``overaccumulation`` and
            ``credit_fragility`` are ``None`` when their inputs were absent.
        """
        return FinancialCrisisAssessment(
            fips_code=fips,
            year=year,
            profit_squeeze=interest_burden_ratio > INTEREST_BURDEN_SQUEEZE,
            overaccumulation=(
                None
                if financialization_ratio is None
                else financialization_ratio > FINANCIALIZATION_BUBBLE
            ),
            credit_fragility=(
                None
                if credit_spread is None
                else (default_rate * credit_spread) > credit_fragility_threshold(self._defines)
            ),
            claims_exceed_surplus=claims_exceed_surplus,
        )
