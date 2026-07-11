"""Simulation engine for the Babylon game loop.

This package contains the core game loop logic:
- simulation_engine: The step() function for state transformation
- simulation: Simulation facade class for multi-tick runs with history
- scenarios: Factory functions for creating initial states
- factories: Entity factory functions (create_proletariat, create_bourgeoisie)
- history_formatter: Narrative generation from simulation history
- Dependency injection: ServiceContainer, EventBus, FormulaRegistry

Phase 2.1: Refactored to modular System architecture.
Sprint 3: Central Committee (Dependency Injection)
Sprint 9: Integration proof with Simulation facade
"""

# Slice 1.7: Graph Abstraction Layer
from typing import Any

from babylon.engine.database import DatabaseConnection
from babylon.engine.factories import create_bourgeoisie, create_proletariat
from babylon.engine.formula_registry import FormulaRegistry
from babylon.engine.history_formatter import format_class_struggle_history
from babylon.engine.observer import SimulationObserver
from babylon.engine.runner import AsyncSimulationRunner
from babylon.engine.scenarios import (
    create_high_tension_scenario,
    create_imperial_circuit_scenario,
    create_labor_aristocracy_scenario,
    create_two_node_scenario,
)
from babylon.engine.services import ServiceContainer

# Note: ``Simulation`` and ``SimulationEngine`` are loaded lazily via
# ``__getattr__`` below. Eager-importing them here triggers a circular import:
# engine.__init__ → engine.simulation → engine.simulation_engine →
# economics.tick.system (which itself imports engine.systems.base.SystemBase
# post-Spec-059 ADR-003 migration). PEP 562 module-level ``__getattr__`` keeps
# the public ``from babylon.engine import Simulation`` API while deferring the
# import to first access. (Spec 059 / ADR-003 fix.)
from babylon.engine.topology_monitor import TopologyMonitor


def __getattr__(name: str) -> Any:  # PEP 562 module-level lazy attribute
    if name == "Simulation":
        from babylon.engine.simulation import Simulation as _Simulation

        return _Simulation
    if name == "SimulationEngine":
        from babylon.engine.simulation_engine import SimulationEngine as _SimulationEngine

        return _SimulationEngine
    if name == "step":
        from babylon.engine.simulation_engine import step as _step

        return _step
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Core engine
    "step",
    "SimulationEngine",
    "Simulation",
    "AsyncSimulationRunner",
    # Entity factories
    "create_proletariat",
    "create_bourgeoisie",
    # History
    "format_class_struggle_history",
    # Scenarios
    "create_two_node_scenario",
    "create_imperial_circuit_scenario",
    "create_high_tension_scenario",
    "create_labor_aristocracy_scenario",
    # Dependency Injection (Sprint 3). Event/EventBus/GraphProtocol moved to
    # babylon.kernel (Program 14 Phase 1) — import them from there directly.
    "DatabaseConnection",
    "FormulaRegistry",
    "ServiceContainer",
    # Observer Pattern (Sprint 3.1)
    "SimulationObserver",
    "TopologyMonitor",
]
