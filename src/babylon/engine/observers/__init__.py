# ruff: noqa: D104
"""Observer implementations for simulation state monitoring.

This package contains concrete SimulationObserver implementations that
monitor specific aspects of the simulation state:

- EconomyMonitor: Detects sudden drops in imperial_rent_pool (>20%)
- CausalChainObserver: Detects Shock Doctrine pattern (Crash -> Austerity -> Radicalization)
- EndgameDetector: Detects game ending conditions (Slice 1.6)
- PersistenceObserver: Persists state via RuntimePersistence protocol (Feature 037)
- SessionRecorder: Persists tick-by-tick state via RuntimePersistence protocol (Feature 037)

Observers follow the Observer Pattern: they receive state change
notifications but cannot modify simulation state. This separation
allows AI components to generate narrative from state changes without
affecting the deterministic mechanics.

Schema validation is provided for observer JSON outputs:

- validate_narrative_frame: Validate NarrativeFrame against JSON schema
- is_valid_narrative_frame: Boolean check for NarrativeFrame validity
"""

from babylon.engine.observers.causal import CausalChainObserver
from babylon.engine.observers.economic import EconomyMonitor
from babylon.engine.observers.endgame_detector import EndgameDetector
from babylon.engine.observers.metrics import TickStateRecorder
from babylon.engine.observers.persistence_observer import PersistenceObserver
from babylon.engine.observers.schema_validator import (
    is_valid_narrative_frame,
    validate_narrative_frame,
)
from babylon.engine.observers.session_recorder import SessionRecorder

__all__ = [
    "CausalChainObserver",
    "EconomyMonitor",
    "EndgameDetector",
    "PersistenceObserver",
    "SessionRecorder",
    "TickStateRecorder",
    "is_valid_narrative_frame",
    "validate_narrative_frame",
]
