"""Aggregation sentinel: partial-coverage symmetry across fog-masked rollups.

Instance of the Sentinel pattern guarding the "aggregation partial-coverage
symmetry" invariant (Track 1 audit, 2026-07-18): two aggregations —
``_aggregate_hex_features`` (``heat`` over hexes) and
``_build_state_apparatus_dashboard`` (``heat`` over state-apparatus orgs) —
must treat "every member fog-masked" identically: the group aggregate must
be an honest ``None``, never a fabricated ``0.0``. Only the *declared
contract* (the registry of which functions/fields this applies to) lives in
this layer-0.5 package; the dynamic harness that calls the real functions
(needs ``web.game.engine_bridge``, a Django app above the engine) lives in
``tools/aggregation_symmetry_probe.py`` — see that module's own docstring,
and the registry module's "why dynamic, not static" note.
"""

from babylon.sentinels.aggregation.registry import (
    AGGREGATION_EXEMPTIONS,
    DECLARED_AGGREGATES,
    DeclaredPartialCoverageAggregate,
)

__all__ = [
    "AGGREGATION_EXEMPTIONS",
    "DECLARED_AGGREGATES",
    "DeclaredPartialCoverageAggregate",
]
