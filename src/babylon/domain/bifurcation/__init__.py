"""Bifurcation topology analysis (Feature 033).

Consciousness-weighted solidarity analysis predicting whether crisis
produces fascism or revolution.

See Also:
    :mod:`babylon.domain.bifurcation.analysis`: Full orchestrator (US5).
    :mod:`babylon.domain.bifurcation.axis`: Per-axis contradiction analysis (US2).
    :mod:`babylon.domain.bifurcation.bridges`: Community bridge detection (US3).
    :mod:`babylon.domain.bifurcation.ceiling`: Material solidarity ceiling (US6).
    :mod:`babylon.domain.bifurcation.consciousness`: Sigmoid weighting (US1).
    :mod:`babylon.domain.bifurcation.legitimation`: Legitimation amplifier (US7).
    :mod:`babylon.domain.bifurcation.resilience`: Topological resilience (US4).
    :mod:`babylon.domain.bifurcation.types`: Result types for analysis snapshots.
"""

from babylon.domain.bifurcation.analysis import bifurcation_tendency
from babylon.domain.bifurcation.axis import (
    classify_edge_antagonism,
    compute_axis_tendency,
    crosses_contradiction_axis,
)
from babylon.domain.bifurcation.bridges import detect_bridges
from babylon.domain.bifurcation.ceiling import compute_solidarity_ceiling
from babylon.domain.bifurcation.consciousness import (
    consciousness_sigmoid,
    consciousness_weighted_solidarity,
)
from babylon.domain.bifurcation.legitimation import compute_legitimation_amplifier
from babylon.domain.bifurcation.resilience import (
    compute_betti_numbers,
    compute_equivalence_classes,
    compute_purge_resilience,
    find_critical_cutsets,
    find_critical_singletons,
)

__all__ = [
    "bifurcation_tendency",
    "classify_edge_antagonism",
    "compute_axis_tendency",
    "compute_betti_numbers",
    "compute_equivalence_classes",
    "compute_legitimation_amplifier",
    "compute_purge_resilience",
    "compute_solidarity_ceiling",
    "consciousness_sigmoid",
    "consciousness_weighted_solidarity",
    "crosses_contradiction_axis",
    "detect_bridges",
    "find_critical_cutsets",
    "find_critical_singletons",
]
