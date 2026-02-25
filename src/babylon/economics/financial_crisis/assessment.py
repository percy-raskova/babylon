"""Integrated financial crisis assessment.

Feature: 024-capital-volume-iii (US6, FR-012)
"""

from __future__ import annotations

from typing import Protocol

from babylon.economics.credit.types import (
    CREDIT_FRAGILITY_THRESHOLD,
    FINANCIALIZATION_BUBBLE,
    INTEREST_BURDEN_SQUEEZE,
)
from babylon.economics.financial_crisis.types import FinancialCrisisAssessment


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
        financialization_ratio: float,
        default_rate: float,
        credit_spread: float,
        claims_exceed_surplus: bool,
    ) -> FinancialCrisisAssessment:
        """Assess financial crisis probability for a county-year.

        Args:
            fips: 5-digit FIPS code.
            year: Assessment year.
            interest_burden_ratio: Interest payments / enterprise profit.
            financialization_ratio: Total credit / GDP.
            default_rate: Loan default fraction [0, 1].
            credit_spread: Risk premium (BAA-AAA or BAA10Y).
            claims_exceed_surplus: Whether financial claims exceed surplus value.

        Returns:
            FinancialCrisisAssessment with computed signals.
        """
        ...


class DefaultFinancialCrisisAssessor:
    """Default implementation using threshold constants from credit/types.py.

    Threshold constants:
        INTEREST_BURDEN_SQUEEZE (0.4): Profit squeeze signal.
        FINANCIALIZATION_BUBBLE (3.5): Overaccumulation signal.
        CREDIT_FRAGILITY_THRESHOLD (0.02): Credit fragility signal.
    """

    def assess(
        self,
        fips: str,
        year: int,
        interest_burden_ratio: float,
        financialization_ratio: float,
        default_rate: float,
        credit_spread: float,
        claims_exceed_surplus: bool,
    ) -> FinancialCrisisAssessment:
        """Assess financial crisis probability for a county-year.

        Args:
            fips: 5-digit FIPS code.
            year: Assessment year.
            interest_burden_ratio: Interest payments / enterprise profit.
            financialization_ratio: Total credit / GDP.
            default_rate: Loan default fraction [0, 1].
            credit_spread: Risk premium (BAA-AAA or BAA10Y).
            claims_exceed_surplus: Whether financial claims exceed surplus value.

        Returns:
            FinancialCrisisAssessment with computed signals.
        """
        return FinancialCrisisAssessment(
            fips_code=fips,
            year=year,
            profit_squeeze=interest_burden_ratio > INTEREST_BURDEN_SQUEEZE,
            overaccumulation=financialization_ratio > FINANCIALIZATION_BUBBLE,
            credit_fragility=(default_rate * credit_spread) > CREDIT_FRAGILITY_THRESHOLD,
            claims_exceed_surplus=claims_exceed_surplus,
        )
