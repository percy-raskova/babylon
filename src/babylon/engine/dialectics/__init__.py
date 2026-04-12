"""Babylon v2 Dialectic-First Engine.

This package implements the dialectic primitive and its composition operators.
Every world object is a ``Dialectic[A, B]``; the simulation is the
time-evolution of a graph of dialectics under their motion laws.

Modules:
    base: The generic ``Dialectic[A, B]`` base class and supporting types.
    volume_1: Capital Volume I dialectics (CommodityDialectic, etc.).
    volume_2: Capital Volume II dialectics (Circulation, Turnover, Reproduction).
    world: ``World``, ``Morphism``, and ``Event`` models.
    tick: The pure ``tick()`` function.
    invariants: Universal and per-type invariant checkers.
    registry: Type-tag → Dialectic subclass mapping.
"""

from babylon.engine.dialectics.base import Dialectic, TickInputs, WorldView
from babylon.engine.dialectics.consciousness import ClassConsciousnessDialectic

__all__ = [
    "Dialectic",
    "TickInputs",
    "WorldView",
    "ClassConsciousnessDialectic",
]
