"""Lawverian dialectics: the categorical foundation of the Babylon engine.

"The main pairs of opposing tendencies in mathematics take the form of
adjoint functors" — F. W. Lawvere, Quantifiers and Sheaves (1970).

This package makes contradiction a structured, measured, consumed
object: oppositions are adjoint cylinders with a gap (distance from
closure), a rate (direction of development), a leading pole (the
principal aspect), and a level (where in the spatial/social hierarchy
they live, with Aufhebung as the computable resolution condition).

Layout:
    - ``core/``: pure machinery (GaloisConnection, AdjointCylinder,
      LevelLattice, OppositionRegistry). No engine imports.
    - ``instances/``: bindings to Babylon's actual carriers (Phase B+ —
      connectivity over the solidarity graph, value-form via MELT,
      scale maps along the spatial hierarchy).

Design contract: ``project/06-lawverian-dialectics.md``.
"""

from babylon.domain.dialectics.core import (
    AdjointCylinder,
    BoundOpposition,
    Coupling,
    CouplingGraph,
    CouplingKind,
    GaloisConnection,
    GapMeasure,
    GapReading,
    Level,
    LevelLattice,
    LevelOperators,
    OppositionRegistry,
    OppositionSpec,
    OppositionState,
    PoleBinding,
    StanceIntervention,
    apply_interventions,
    product,
    sum_,
)

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
    "StanceIntervention",
    "apply_interventions",
    "product",
    "sum_",
]
