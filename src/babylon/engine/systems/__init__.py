"""Simulation systems for the Babylon engine.

Phase 2.1: Dialectical Refactor - modular system architecture.
"""

from babylon.engine.systems.contradiction import ContradictionSystem
from babylon.engine.systems.economic import ImperialRentSystem
from babylon.engine.systems.ideology import ConsciousnessSystem
from babylon.engine.systems.protocol import System
from babylon.engine.systems.survival import SurvivalSystem

__all__ = [
    "System",
    "ImperialRentSystem",
    "ConsciousnessSystem",
    "SurvivalSystem",
    "ContradictionSystem",
]
