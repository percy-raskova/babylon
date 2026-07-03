"""Core categorical machinery: adjunctions, cylinders, levels, oppositions.

Pure mathematics — no engine imports. Laws are enforced by Hypothesis
property tests in ``tests/property/dialectics/``.
"""

from babylon.dialectics.core.composition import product, sum_
from babylon.dialectics.core.coupling import (
    Coupling,
    CouplingGraph,
    CouplingKind,
    StanceIntervention,
    apply_interventions,
)
from babylon.dialectics.core.cylinder import AdjointCylinder
from babylon.dialectics.core.galois import GaloisConnection
from babylon.dialectics.core.level import Level, LevelLattice, LevelOperators
from babylon.dialectics.core.opposition import (
    BoundOpposition,
    GapMeasure,
    GapReading,
    OppositionRegistry,
    OppositionSpec,
    OppositionState,
    PoleBinding,
)
from babylon.dialectics.core.regime import Regime, classify_regime

__all__ = [
    "AdjointCylinder",
    "BoundOpposition",
    "Coupling",
    "CouplingGraph",
    "CouplingKind",
    "GaloisConnection",
    "GapMeasure",
    "GapReading",
    "Level",
    "LevelLattice",
    "LevelOperators",
    "OppositionRegistry",
    "OppositionSpec",
    "OppositionState",
    "PoleBinding",
    "Regime",
    "StanceIntervention",
    "apply_interventions",
    "classify_regime",
    "product",
    "sum_",
]
