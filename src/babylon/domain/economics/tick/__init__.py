"""Simulation Tick Dynamics package (Feature 017).

Integrates Features 012-016 economics calculators into a unified per-tick
state evolution pipeline conforming to the engine's System protocol.

This package provides:
    - TickDynamicsSystem: Engine System for per-tick economics
    - SimulationTickState: Root state container
    - NationalTickParameters: National economic context per tick
    - CountyEconomicState: Per-county economic snapshot
    - SmoothedCoefficients: Alpha-smoothed coefficient history
    - TickSummary: Aggregate statistics after tick completion
    - DerivedRates: Per-county derived economic indicators

See Also:
    :mod:`babylon.domain.economics.melt`: MELT and basket visibility (Feature 013)
    :mod:`babylon.domain.economics.throughput`: Throughput position (Feature 014)
    :mod:`babylon.domain.economics.gamma`: Gamma visibility tensor (Feature 015)
    :mod:`babylon.domain.economics.dynamics`: Class dynamics engine (Feature 016)
"""

from babylon.domain.economics.tick.crisis_detector import ThresholdCrisisDetector
from babylon.domain.economics.tick.derived_rates import DerivedRateCalculator
from babylon.domain.economics.tick.graph_bridge import (
    TICK_DYNAMICS_KEY,
    read_tick_state_from_graph,
    write_tick_state_to_graph,
)
from babylon.domain.economics.tick.initializer import DefaultTickInitializer
from babylon.domain.economics.tick.precarity import PrecarityDeriver
from babylon.domain.economics.tick.smoothing import CoefficientSmoother
from babylon.domain.economics.tick.system import TickDynamicsSystem
from babylon.domain.economics.tick.types import (
    CountyEconomicState,
    DerivedRates,
    NationalTickParameters,
    SimulationTickState,
    SmoothedCoefficients,
    TickSummary,
)

__all__ = [
    # System
    "TickDynamicsSystem",
    # Types
    "CountyEconomicState",
    "DerivedRates",
    "NationalTickParameters",
    "SimulationTickState",
    "SmoothedCoefficients",
    "TickSummary",
    # Graph Bridge
    "TICK_DYNAMICS_KEY",
    "read_tick_state_from_graph",
    "write_tick_state_to_graph",
    # Components
    "CoefficientSmoother",
    "DefaultTickInitializer",
    "DerivedRateCalculator",
    "PrecarityDeriver",
    "ThresholdCrisisDetector",
]
