"""Bifurcation topology analysis (Feature 033).

Consciousness-weighted solidarity analysis predicting whether crisis
produces fascism or revolution.

See Also:
    :mod:`babylon.bifurcation.axis`: Per-axis contradiction analysis (US2).
    :mod:`babylon.bifurcation.bridges`: Community bridge detection (US3).
    :mod:`babylon.bifurcation.consciousness`: Sigmoid weighting (US1).
    :mod:`babylon.bifurcation.types`: Result types for analysis snapshots.
"""

from babylon.bifurcation.axis import (
    classify_edge_antagonism,
    compute_axis_tendency,
    crosses_contradiction_axis,
)
from babylon.bifurcation.bridges import detect_bridges
from babylon.bifurcation.consciousness import (
    consciousness_sigmoid,
    consciousness_weighted_solidarity,
)

__all__ = [
    "classify_edge_antagonism",
    "compute_axis_tendency",
    "consciousness_sigmoid",
    "consciousness_weighted_solidarity",
    "crosses_contradiction_axis",
    "detect_bridges",
]
