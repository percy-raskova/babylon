"""Economic-Conservation sentinel — instance #3 of the ``babylon.sentinels`` family.

Mechanical enforcement of the per-tick accounting identities the engine
guarantees over a deterministic dense trace (Constitution III.11 Loud Failure;
Amendment Q behavioral contracts). This package exposes only the **declared
data** — :data:`CONSERVATION_REGISTRY` and its :class:`ConservationIdentity`
type — because it sits at the sentinels' layer-0.5 import boundary (it imports
nothing above :mod:`babylon.models`). The *checking* logic that walks a live
trace lives in the test layer (``tests/unit/sentinels/test_conservation.py``),
which may build the trace with the engine.

The declared identities (both verified across all 53 rows of the
``imperial_circuit`` scenario):

- **economic_columns_finite** — no ``NaN``/``inf`` in any numeric economic cell.
- **imperial_rent_pool_depletion** — the imperial-rent reserve is non-negative,
  bounded by its initial value, and non-increasing tick-over-tick.
"""

from babylon.sentinels.conservation.registry import (
    ALL_NUMERIC_COLUMNS,
    CONSERVATION_REGISTRY,
    IMPERIAL_RENT_POOL_COLUMN,
    ConservationIdentity,
)

__all__ = [
    "ALL_NUMERIC_COLUMNS",
    "CONSERVATION_REGISTRY",
    "IMPERIAL_RENT_POOL_COLUMN",
    "ConservationIdentity",
]
