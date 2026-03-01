"""Bifurcation topology analysis (Feature 033).

Consciousness-weighted solidarity analysis predicting whether crisis
produces fascism or revolution.

See Also:
    :mod:`babylon.bifurcation.analysis`: Full orchestrator (US5).
    :mod:`babylon.bifurcation.axis`: Per-axis contradiction analysis (US2).
    :mod:`babylon.bifurcation.bridges`: Community bridge detection (US3).
    :mod:`babylon.bifurcation.ceiling`: Material solidarity ceiling (US6).
    :mod:`babylon.bifurcation.consciousness`: Sigmoid weighting (US1).
    :mod:`babylon.bifurcation.legitimation`: Legitimation amplifier (US7).
    :mod:`babylon.bifurcation.resilience`: Topological resilience (US4).
    :mod:`babylon.bifurcation.types`: Result types for analysis snapshots.
"""

from babylon.bifurcation.analysis import bifurcation_tendency
from babylon.bifurcation.axis import (
    classify_edge_antagonism,
    compute_axis_tendency,
    crosses_contradiction_axis,
)
from babylon.bifurcation.bridges import detect_bridges
from babylon.bifurcation.ceiling import compute_solidarity_ceiling
from babylon.bifurcation.consciousness import (
    consciousness_sigmoid,
    consciousness_weighted_solidarity,
)
from babylon.bifurcation.legitimation import compute_legitimation_amplifier
from babylon.bifurcation.resilience import (
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
