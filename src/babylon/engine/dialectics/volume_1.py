"""Capital Volume I dialectics — backward-compatibility re-export shim.

.. deprecated::
    Import directly from the individual modules instead:
    ``babylon.engine.dialectics.commodity``,
    ``babylon.engine.dialectics.labor_process``, etc.
"""

from babylon.economics.value import AbstractLabor, ConcreteLabor, ExchangeValue, UseValue
from babylon.engine.dialectics.accumulation import (
    AccumulationDialectic,
    ConcentrationOfCapital,
    ReserveArmyExpansion,
)
from babylon.engine.dialectics.base import EmptyPole
from babylon.engine.dialectics.commodity import CommodityDialectic
from babylon.engine.dialectics.labor_process import LaborProcessDialectic
from babylon.engine.dialectics.primitive_accumulation import (
    ColonialExpropriation,
    PrimitiveAccumulationDialectic,
    SettlerFormation,
)
from babylon.engine.dialectics.production import ProductionDialectic
from babylon.engine.dialectics.wage import (
    PriceOfLaborPower,
    ValueOfLaborPower,
    WageDialectic,
)

__all__ = [
    "AbstractLabor",
    "AccumulationDialectic",
    "ColonialExpropriation",
    "CommodityDialectic",
    "ConcentrationOfCapital",
    "ConcreteLabor",
    "EmptyPole",
    "ExchangeValue",
    "LaborProcessDialectic",
    "PriceOfLaborPower",
    "PrimitiveAccumulationDialectic",
    "ProductionDialectic",
    "ReserveArmyExpansion",
    "SettlerFormation",
    "UseValue",
    "ValueOfLaborPower",
    "WageDialectic",
]
