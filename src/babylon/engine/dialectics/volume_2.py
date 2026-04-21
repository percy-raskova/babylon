"""Capital Volume II dialectics — backward-compatibility re-export shim.

.. deprecated::
    Import directly from the individual modules instead:
    ``babylon.engine.dialectics.circulation``,
    ``babylon.engine.dialectics.turnover``, etc.
"""

from babylon.engine.dialectics.base import EmptyPole
from babylon.engine.dialectics.circulation import CirculationDialectic
from babylon.engine.dialectics.consumption import (
    ConsumptionDialectic,
    IndividualConsumption,
    ProductiveConsumption,
)
from babylon.engine.dialectics.crises import (
    DisproportionalityCrisisDialectic,
    RealizationCrisisDialectic,
)
from babylon.engine.dialectics.distribution import (
    DistributionDialectic,
    SurplusShares,
    Wages,
)
from babylon.engine.dialectics.reproduction import ReproductionDialectic
from babylon.engine.dialectics.turnover import TurnoverDialectic

__all__ = [
    "CirculationDialectic",
    "ConsumptionDialectic",
    "DisproportionalityCrisisDialectic",
    "DistributionDialectic",
    "EmptyPole",
    "IndividualConsumption",
    "ProductiveConsumption",
    "RealizationCrisisDialectic",
    "ReproductionDialectic",
    "SurplusShares",
    "TurnoverDialectic",
    "Wages",
]
