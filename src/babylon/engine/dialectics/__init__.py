"""Babylon v2 Dialectic-First Engine.

This package implements the dialectic primitive and its composition operators.
Every world object is a ``Dialectic[A, B]``; the simulation is the
time-evolution of a graph of dialectics under their motion laws.

Modules:
    base: The generic ``Dialectic[A, B]`` base class and supporting types.
    commodity: CommodityDialectic (V1 Ch1).
    labor_process: LaborProcessDialectic (V1 Ch7§1).
    production: ProductionDialectic (V1 Ch7§2).
    wage: WageDialectic (V1 Ch19-22).
    accumulation: AccumulationDialectic (V1 Ch23-25).
    primitive_accumulation: PrimitiveAccumulationDialectic (V1 Ch26-33).
    circulation: CirculationDialectic (V2 Ch1-4).
    turnover: TurnoverDialectic (V2 Part 2).
    reproduction: ReproductionDialectic (V2 Ch20-21).
    distribution: DistributionDialectic (Grundrisse).
    consumption: ConsumptionDialectic (Grundrisse).
    surplus_distribution: SurplusDistributionDialectic (V3 Ch9-10).
    trpf: TRPFDialectic (V3 Ch13-15).
    credit: CreditDialectic (V3 Ch21-33).
    rent: RentDialectic (V3 Ch37-47).
    imperial: ImperialDialectic (V3 Ch14 §V + MLM-TW).
    crises: All crisis sublation dialectics.
    consciousness: ClassConsciousnessDialectic (Lukacs/MIM(P)).
    world: ``World``, ``Morphism``, and ``Event`` models.
    tick: The pure ``tick()`` function.
    invariants_v2: Universal and per-type invariant checkers.
    registry: Type-tag → Dialectic subclass mapping.
"""

# Core infrastructure
# Individual dialectics — flat module structure
from babylon.engine.dialectics.accumulation import (
    AccumulationDialectic,
    ConcentrationOfCapital,
    ReserveArmyExpansion,
)
from babylon.engine.dialectics.base import Dialectic, TickInputs, WorldView
from babylon.engine.dialectics.circulation import CirculationDialectic
from babylon.engine.dialectics.commodity import CommodityDialectic
from babylon.engine.dialectics.consciousness import ClassConsciousnessDialectic
from babylon.engine.dialectics.consumption import (
    ConsumptionDialectic,
    IndividualConsumption,
    ProductiveConsumption,
)
from babylon.engine.dialectics.credit import CreditDialectic, CreditPole
from babylon.engine.dialectics.crises import (
    DebtSpiralCrisisDialectic,
    DisproportionalityCrisisDialectic,
    FinancialCrisisDialectic,
    RealizationCrisisDialectic,
)
from babylon.engine.dialectics.distribution import (
    DistributionDialectic,
    SurplusShares,
    Wages,
)
from babylon.engine.dialectics.imperial import (
    CoreEconomy,
    ImperialDialectic,
    PeripheryEconomy,
)
from babylon.engine.dialectics.labor_process import LaborProcessDialectic
from babylon.engine.dialectics.primitive_accumulation import (
    ColonialExpropriation,
    PrimitiveAccumulationDialectic,
    SettlerFormation,
)
from babylon.engine.dialectics.production import ProductionDialectic
from babylon.engine.dialectics.rent import RentDialectic, RentPole
from babylon.engine.dialectics.reproduction import ReproductionDialectic
from babylon.engine.dialectics.surplus_distribution import (
    SurplusDistributionDialectic,
    SurplusDistributionPole,
)
from babylon.engine.dialectics.trpf import ProfitRateState, TRPFDialectic
from babylon.engine.dialectics.turnover import TurnoverDialectic
from babylon.engine.dialectics.wage import (
    PriceOfLaborPower,
    ValueOfLaborPower,
    WageDialectic,
)

__all__ = [
    # Core
    "Dialectic",
    "TickInputs",
    "WorldView",
    # V1 dialectics
    "CommodityDialectic",
    "LaborProcessDialectic",
    "ProductionDialectic",
    "WageDialectic",
    "ValueOfLaborPower",
    "PriceOfLaborPower",
    "AccumulationDialectic",
    "ConcentrationOfCapital",
    "ReserveArmyExpansion",
    "PrimitiveAccumulationDialectic",
    "ColonialExpropriation",
    "SettlerFormation",
    # V2 dialectics
    "CirculationDialectic",
    "TurnoverDialectic",
    "ReproductionDialectic",
    "DistributionDialectic",
    "Wages",
    "SurplusShares",
    "ConsumptionDialectic",
    "ProductiveConsumption",
    "IndividualConsumption",
    # V3 dialectics
    "SurplusDistributionDialectic",
    "SurplusDistributionPole",
    "TRPFDialectic",
    "ProfitRateState",
    "CreditDialectic",
    "CreditPole",
    "RentDialectic",
    "RentPole",
    "ImperialDialectic",
    "CoreEconomy",
    "PeripheryEconomy",
    # Consciousness
    "ClassConsciousnessDialectic",
    # Crises
    "RealizationCrisisDialectic",
    "DisproportionalityCrisisDialectic",
    "DebtSpiralCrisisDialectic",
    "FinancialCrisisDialectic",
]
