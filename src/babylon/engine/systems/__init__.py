"""Simulation systems for the Babylon engine.

Phase 2.1: Dialectical Refactor - modular system architecture.
Agency Layer: StruggleSystem for political agency of oppressed classes.
Feature 002: Dialectical Field Topology systems (positions 14-16).
"""

from babylon.engine.systems.contradiction import ContradictionSystem
from babylon.engine.systems.contradiction_field import ContradictionFieldSystem
from babylon.engine.systems.economic import ImperialRentSystem
from babylon.engine.systems.edge_transition import EdgeTransitionSystem
from babylon.engine.systems.field_derivative import FieldDerivativeSystem
from babylon.engine.systems.ideology import ConsciousnessSystem
from babylon.engine.systems.production import ProductionSystem
from babylon.engine.systems.protocol import System
from babylon.engine.systems.solidarity import SolidaritySystem
from babylon.engine.systems.struggle import StruggleSystem
from babylon.engine.systems.survival import SurvivalSystem
from babylon.engine.systems.territory import TerritorySystem
from babylon.engine.systems.vitality import VitalitySystem

__all__ = [
    "System",
    "VitalitySystem",
    "ProductionSystem",
    "ImperialRentSystem",
    "ConsciousnessSystem",
    "SurvivalSystem",
    "StruggleSystem",
    "ContradictionSystem",
    "SolidaritySystem",
    "TerritorySystem",
    # Dialectical Field Topology (Feature 002)
    "ContradictionFieldSystem",
    "FieldDerivativeSystem",
    "EdgeTransitionSystem",
]
