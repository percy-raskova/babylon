"""Surplus value distribution module (Capital Volume III).

Decomposes surplus value into competing claims: profit of enterprise,
interest, ground rent, and taxes. Tracks cumulative debt accumulation
when claims exceed surplus.

See Also:
    :mod:`babylon.domain.economics.circulation`: Capital Volume II circulation dynamics
    :mod:`babylon.domain.economics.credit`: Interest-bearing capital module
    :mod:`babylon.domain.economics.rent`: Ground rent extraction module
"""

__all__: list[str] = [
    # Threshold accessors (types.py) — GameDefines-backed since the
    # 2026-07-18 honesty sweep; these are functions, not constants.
    "debt_spiral_threshold",
    "distribution_epsilon",
    # Types (types.py)
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
    # Sovereign fiscal ledger (P25 U9, ADR135)
    "SovereignFiscalState",
    "bond_discipline_binds",
    "borrow",
    "finance_shortfall",
    "sovereign_debt_service",
]

from babylon.domain.economics.distribution.calculator import (
    DefaultDistributionCalculator,
    DistributionCalculator,
)
from babylon.domain.economics.distribution.data_sources import (
    InterestIncomeSource,
    RentalIncomeSource,
    TaxOnSurplusSource,
)
from babylon.domain.economics.distribution.sovereign_fiscal import (
    SovereignFiscalState,
    bond_discipline_binds,
    borrow,
    finance_shortfall,
    sovereign_debt_service,
)
from babylon.domain.economics.distribution.types import (
    DebtAccumulation,
    SurplusValueDistribution,
    debt_spiral_threshold,
    distribution_epsilon,
)
from babylon.domain.economics.distribution.validation import (
    validate_rentier_share,
)
