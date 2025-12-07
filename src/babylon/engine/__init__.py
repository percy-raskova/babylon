"""Simulation engine for the Babylon game loop.

This package contains the core game loop logic:
- simulation_engine: The step() function for state transformation
- scenarios: Factory functions for creating initial states

Phase 2.1: Refactored to modular System architecture.
"""

from babylon.engine.scenarios import (
    create_high_tension_scenario,
    create_labor_aristocracy_scenario,
    create_two_node_scenario,
)
from babylon.engine.simulation_engine import SimulationEngine, step

__all__ = [
    "step",
    "SimulationEngine",
    "create_two_node_scenario",
    "create_high_tension_scenario",
    "create_labor_aristocracy_scenario",
]
