"""D-P-D' Lifecycle Circuit (Feature 030).

Models intergenerational class reproduction through the three-phase lifecycle:
Dependent (D) → Productive (P) → Dependent' (D'). Tracks population cohorts,
computes legitimation indices, models inheritance flows, and encodes
differential transition rates for racial/carceral inequality.

See Also:
    :mod:`babylon.domain.economics.lifecycle.types`: Core data models.
    :mod:`babylon.domain.economics.lifecycle.cohort_dynamics`: Population transitions.
    :mod:`babylon.domain.economics.lifecycle.legitimation`: Legitimation bargain.
    :mod:`babylon.domain.economics.lifecycle.inheritance`: Pareto inheritance flows.
    :mod:`babylon.domain.economics.lifecycle.dual_circuit`: D-P-D' × P-D-P' interference.
    :mod:`babylon.domain.economics.lifecycle.mobility`: Chetty-derived class mobility.
    ``specs/030-dpd-lifecycle-circuit/spec.md``: Feature specification.
"""

from babylon.domain.economics.lifecycle.cohort_dynamics import (
    CohortDynamicsCalculator,
    DefaultCohortDynamicsCalculator,
)
from babylon.domain.economics.lifecycle.dispossession import (
    DispossessionResult,
    compute_crisis_dispossession,
)
from babylon.domain.economics.lifecycle.dual_circuit import (
    DefaultDualCircuitCalculator,
    DualCircuitCalculator,
)
from babylon.domain.economics.lifecycle.inheritance import (
    DefaultInheritanceCalculator,
    InheritanceCalculator,
)
from babylon.domain.economics.lifecycle.legitimation import (
    DefaultLegitimationCalculator,
    LegitimationCalculator,
)
from babylon.domain.economics.lifecycle.mobility import (
    ClassMobilityCalculator,
    DefaultClassMobilityCalculator,
)
from babylon.domain.economics.lifecycle.types import (
    ClassMobilityParams,
    DPDState,
    InheritanceFlow,
    LegitimationState,
)

__all__ = [
    # Types
    "ClassMobilityParams",
    "DPDState",
    "DispossessionResult",
    "InheritanceFlow",
    "LegitimationState",
    # Calculators (Protocol + Default)
    "CohortDynamicsCalculator",
    "DefaultCohortDynamicsCalculator",
    "DualCircuitCalculator",
    "DefaultDualCircuitCalculator",
    "InheritanceCalculator",
    "DefaultInheritanceCalculator",
    "LegitimationCalculator",
    "DefaultLegitimationCalculator",
    "ClassMobilityCalculator",
    "DefaultClassMobilityCalculator",
    # Functions (Feature 038)
    "compute_crisis_dispossession",
]
