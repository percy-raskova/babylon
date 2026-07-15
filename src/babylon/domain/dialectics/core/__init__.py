"""Core categorical machinery: adjunctions, cylinders, levels, oppositions.

Pure mathematics — no engine imports. Laws are enforced by Hypothesis
property tests in ``tests/property/dialectics/``.
"""

from babylon.domain.dialectics.core.composition import product, sum_
from babylon.domain.dialectics.core.coupling import (
    Coupling,
    CouplingGraph,
    CouplingKind,
    StanceIntervention,
    apply_interventions,
)
from babylon.domain.dialectics.core.cylinder import AdjointCylinder
from babylon.domain.dialectics.core.galois import GaloisConnection
from babylon.domain.dialectics.core.level import Level, LevelLattice, LevelOperators
from babylon.domain.dialectics.core.opposition import (
    BoundOpposition,
    GapMeasure,
    GapReading,
    OppositionRegistry,
    OppositionSpec,
    OppositionState,
    PoleBinding,
    PoleMeasure,
    PoleReading,
    PoleSample,
)
from babylon.domain.dialectics.core.regime import Regime, classify_regime

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
    "PoleMeasure",
    "PoleReading",
    "PoleSample",
    "Regime",
    "StanceIntervention",
    "apply_interventions",
    "classify_regime",
    "product",
    "sum_",
]
