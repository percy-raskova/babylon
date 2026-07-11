"""Interest-bearing capital and credit dynamics module (Capital Volume III).

Models interest rate dynamics, credit cycle phase detection, and fictitious
capital accumulation. Computes financialization index as crisis indicator.

See Also:
    :mod:`babylon.domain.economics.distribution`: Surplus value distribution
    :mod:`babylon.domain.economics.financial_crisis`: Integrated crisis assessment
"""

# Data source protocols and adapters
# Types and constants
# Credit cycle detection
from babylon.domain.economics.credit.credit_cycle import (
    CreditCycleDetector,
    DefaultCreditCycleDetector,
)
from babylon.domain.economics.credit.data_sources import (
    CreditAggregateSource,
    FredCreditAggregateAdapter,
    FredInterestRateAdapter,
    InterestRateSource,
    Z1FinancialAccountsSource,
)

# Fictitious capital computation
from babylon.domain.economics.credit.fictitious_capital import (
    DefaultFictitiousCapitalCalculator,
    FictitiousCapitalCalculator,
)

# Interest rate computation
from babylon.domain.economics.credit.interest import (
    DefaultInterestCalculator,
    InterestCalculator,
)
from babylon.domain.economics.credit.types import (
    CREDIT_FRAGILITY_THRESHOLD,
    FINANCIALIZATION_BUBBLE,
    INTEREST_BURDEN_SQUEEZE,
    OVEREXTENSION_DEFAULT_RATE,
    RECOVERY_CONSECUTIVE_PERIODS,
    STAGNATION_CREDIT_GROWTH,
    VALID_CREDIT_TRANSITIONS,
    CreditCyclePhase,
    CreditState,
    FictitiousCapitalStock,
    InterestRateState,
)
from babylon.domain.economics.credit.validation import (
    validate_financialization_index,
    validate_interest_burden_ratio,
)

__all__: list[str] = [
    # Types (enums and models)
    "CreditCyclePhase",
    "InterestRateState",
    "CreditState",
    "FictitiousCapitalStock",
    # Transition map
    "VALID_CREDIT_TRANSITIONS",
    # Threshold constants
    "INTEREST_BURDEN_SQUEEZE",
    "FINANCIALIZATION_BUBBLE",
    "CREDIT_FRAGILITY_THRESHOLD",
    "STAGNATION_CREDIT_GROWTH",
    "OVEREXTENSION_DEFAULT_RATE",
    "RECOVERY_CONSECUTIVE_PERIODS",
    # Interest calculation
    "InterestCalculator",
    "DefaultInterestCalculator",
    # Credit cycle detection
    "CreditCycleDetector",
    "DefaultCreditCycleDetector",
    # Fictitious capital computation
    "FictitiousCapitalCalculator",
    "DefaultFictitiousCapitalCalculator",
    # Data source protocols (Feature 024)
    "InterestRateSource",
    "CreditAggregateSource",
    "Z1FinancialAccountsSource",
    # Concrete adapters (Feature 024)
    "FredInterestRateAdapter",
    "FredCreditAggregateAdapter",
    # Validation (Feature 024, Phase 12)
    "validate_financialization_index",
    "validate_interest_burden_ratio",
]
