# ruff: noqa: D104
"""Observer implementations for simulation state monitoring.

This package contains concrete SimulationObserver implementations that
monitor specific aspects of the simulation state:

- EconomyMonitor: Detects sudden drops in imperial_rent_pool (>20%)

Observers follow the Observer Pattern: they receive state change
notifications but cannot modify simulation state. This separation
allows AI components to generate narrative from state changes without
affecting the deterministic mechanics.
"""

from babylon.engine.observers.economic import EconomyMonitor

__all__ = ["EconomyMonitor"]
