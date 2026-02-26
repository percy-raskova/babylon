"""Surplus value distribution module (Capital Volume III).

Decomposes surplus value into competing claims: profit of enterprise,
interest, ground rent, and taxes. Tracks cumulative debt accumulation
when claims exceed surplus.

See Also:
    :mod:`babylon.economics.circulation`: Capital Volume II circulation dynamics
    :mod:`babylon.economics.credit`: Interest-bearing capital module
    :mod:`babylon.economics.rent`: Ground rent extraction module
"""

__all__: list[str] = [
    # Types (types.py)
    "DEBT_SPIRAL_THRESHOLD",
    "DISTRIBUTION_EPSILON",
    "SurplusValueDistribution",
    "DebtAccumulation",
    # Calculator (calculator.py)
    "DistributionCalculator",
    "DefaultDistributionCalculator",
    # Data sources (data_sources.py)
    "RentalIncomeSource",
    "TaxOnSurplusSource",
    "InterestIncomeSource",
    # Validation (Feature 024, Phase 12)
    "validate_rentier_share",
]

from babylon.economics.distribution.calculator import (
    DefaultDistributionCalculator,
    DistributionCalculator,
)
from babylon.economics.distribution.data_sources import (
    InterestIncomeSource,
    RentalIncomeSource,
    TaxOnSurplusSource,
)
from babylon.economics.distribution.types import (
    DEBT_SPIRAL_THRESHOLD,
    DISTRIBUTION_EPSILON,
    DebtAccumulation,
    SurplusValueDistribution,
)
from babylon.economics.distribution.validation import (
    validate_rentier_share,
)
