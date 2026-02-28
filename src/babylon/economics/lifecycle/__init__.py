"""D-P-D' Lifecycle Circuit (Feature 030).

Models intergenerational class reproduction through the three-phase lifecycle:
Dependent (D) → Productive (P) → Dependent' (D'). Tracks population cohorts,
computes legitimation indices, models inheritance flows, and encodes
differential transition rates for racial/carceral inequality.

See Also:
    :mod:`babylon.economics.lifecycle.types`: Core data models.
    :mod:`babylon.economics.lifecycle.cohort_dynamics`: Population transitions.
    :mod:`babylon.economics.lifecycle.legitimation`: Legitimation bargain.
    :mod:`babylon.economics.lifecycle.inheritance`: Pareto inheritance flows.
    :mod:`babylon.economics.lifecycle.dual_circuit`: D-P-D' × P-D-P' interference.
    :mod:`babylon.economics.lifecycle.mobility`: Chetty-derived class mobility.
    ``specs/030-dpd-lifecycle-circuit/spec.md``: Feature specification.
"""

from babylon.economics.lifecycle.types import (
    ClassMobilityParams,
    DPDState,
    InheritanceFlow,
    LegitimationState,
)

__all__ = [
    "ClassMobilityParams",
    "DPDState",
    "InheritanceFlow",
    "LegitimationState",
]
