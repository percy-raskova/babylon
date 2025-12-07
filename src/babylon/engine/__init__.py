"""Simulation engine for the Babylon game loop.

This package contains the core game loop logic:
- simulation_engine: The step() function for state transformation
- scenarios: Factory functions for creating initial states

Sprint 5-6: Phase 2 game loop implementation.
"""

from babylon.engine.scenarios import (
    create_high_tension_scenario,
    create_labor_aristocracy_scenario,
    create_two_node_scenario,
)
from babylon.engine.simulation_engine import step

__all__ = [
    "step",
    "create_two_node_scenario",
    "create_high_tension_scenario",
    "create_labor_aristocracy_scenario",
]
