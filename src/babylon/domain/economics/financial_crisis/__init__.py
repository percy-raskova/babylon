"""Integrated financial crisis assessment module (Capital Volume III).

Combines production crisis (Feature 018), circulation crisis (Feature 023),
and financial crisis indicators into unified assessment.

See Also:
    :mod:`babylon.domain.economics.crisis`: TRPF crisis mechanics (Feature 018)
    :mod:`babylon.domain.economics.circulation`: Capital Volume II circulation dynamics
    :mod:`babylon.domain.economics.credit`: Interest-bearing capital module
"""

from babylon.domain.economics.financial_crisis.assessment import (
    DefaultFinancialCrisisAssessor,
    FinancialCrisisAssessor,
)
from babylon.domain.economics.financial_crisis.types import (
    CreditCrisisIndicator,
    FinancialCrisisAssessment,
)

__all__: list[str] = [
    # Types
    "CreditCrisisIndicator",
    "FinancialCrisisAssessment",
    # Assessment
    "DefaultFinancialCrisisAssessor",
    "FinancialCrisisAssessor",
]
