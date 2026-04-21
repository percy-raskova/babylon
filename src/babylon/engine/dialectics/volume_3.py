"""Capital Volume III dialectics — backward-compatibility re-export shim.

.. deprecated::
    Import directly from the individual modules instead:
    ``babylon.engine.dialectics.surplus_distribution``,
    ``babylon.engine.dialectics.trpf``, etc.
"""

from babylon.engine.dialectics.credit import CreditDialectic, CreditPole
from babylon.engine.dialectics.crises import (
    DebtSpiralCrisisDialectic,
    FinancialCrisisDialectic,
)
from babylon.engine.dialectics.imperial import (
    CoreEconomy,
    ImperialDialectic,
    PeripheryEconomy,
)
from babylon.engine.dialectics.rent import RentDialectic, RentPole
from babylon.engine.dialectics.surplus_distribution import (
    SurplusDistributionDialectic,
    SurplusDistributionPole,
)
from babylon.engine.dialectics.trpf import ProfitRateState, TRPFDialectic

__all__ = [
    "CoreEconomy",
    "CreditDialectic",
    "CreditPole",
    "DebtSpiralCrisisDialectic",
    "FinancialCrisisDialectic",
    "ImperialDialectic",
    "PeripheryEconomy",
    "ProfitRateState",
    "RentDialectic",
    "RentPole",
    "SurplusDistributionDialectic",
    "SurplusDistributionPole",
    "TRPFDialectic",
]
