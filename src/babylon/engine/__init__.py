"""Simulation engine for the Babylon game loop.

This package contains the core game loop logic:
- simulation_engine: The step() function for state transformation
- scenarios: Factory functions for creating initial states
- Dependency injection: ServiceContainer, EventBus, FormulaRegistry

Phase 2.1: Refactored to modular System architecture.
Sprint 3: Central Committee (Dependency Injection)
"""

from babylon.engine.database import DatabaseConnection
from babylon.engine.event_bus import Event, EventBus
from babylon.engine.formula_registry import FormulaRegistry
from babylon.engine.scenarios import (
    create_high_tension_scenario,
    create_labor_aristocracy_scenario,
    create_two_node_scenario,
)
from babylon.engine.services import ServiceContainer
from babylon.engine.simulation_engine import SimulationEngine, step

__all__ = [
    # Core engine
    "step",
    "SimulationEngine",
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
]
