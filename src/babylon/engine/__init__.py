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

from babylon.engine.database import DatabaseConnection
from babylon.engine.event_bus import Event, EventBus
from babylon.engine.factories import create_bourgeoisie, create_proletariat
from babylon.engine.formula_registry import FormulaRegistry
from babylon.engine.history_formatter import format_class_struggle_history
from babylon.engine.observer import SimulationObserver
from babylon.engine.scenarios import (
    create_high_tension_scenario,
    create_labor_aristocracy_scenario,
    create_two_node_scenario,
)
from babylon.engine.services import ServiceContainer
from babylon.engine.simulation import Simulation
from babylon.engine.simulation_engine import SimulationEngine, step

__all__ = [
    # Core engine
    "step",
    "SimulationEngine",
    "Simulation",
    # Entity factories
    "create_proletariat",
    "create_bourgeoisie",
    # History
    "format_class_struggle_history",
    # Scenarios
    "create_two_node_scenario",
    "create_high_tension_scenario",
    "create_labor_aristocracy_scenario",
    # Dependency Injection (Sprint 3)
    "Event",
    "EventBus",
    "DatabaseConnection",
    "FormulaRegistry",
    "ServiceContainer",
    # Observer Pattern (Sprint 3.1)
    "SimulationObserver",
]
