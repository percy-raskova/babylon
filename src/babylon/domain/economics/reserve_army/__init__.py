"""Reserve Army of Labor economics module (Feature 021, US1).

Computes reserve army composition from labor market data and derives
wage pressure coefficients that modify variable capital (v) in the
value tensor.
"""

from babylon.domain.economics.reserve_army.calculator import DefaultWagePressureCalculator
from babylon.domain.economics.reserve_army.data_sources import ReserveArmyDataSource
from babylon.domain.economics.reserve_army.types import ReserveArmyDynamics, ReserveArmyState

__all__ = [
    "ReserveArmyState",
    "ReserveArmyDynamics",
    "ReserveArmyDataSource",
    "DefaultWagePressureCalculator",
]
