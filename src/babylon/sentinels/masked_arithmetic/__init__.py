"""Masked-arithmetic sentinel: no unguarded arithmetic on a fog-masked field.

Instance of the Sentinel pattern guarding a Track-1-discovered failure mode
(2026-07-18 audit): fog masks a political field to ``None`` while keeping
its dict key present. ``dict.get(key, default)``'s ``default`` only fires
on an ABSENT key, so an already-fogged consumer that "defends" with
``.get("heat", 0.0)`` gets no protection at all — a masked value still
reaches ``float(None)`` and crashes.

Founding incident: ``web/game/engine_bridge.py::
_build_state_apparatus_dashboard`` did exactly this and raised
``TypeError`` the first time a state-apparatus org left the player's
organizing reach. The shipped fix guards with an explicit ``is not None``
check; this sentinel pins that fix as a declared invariant.
"""

from babylon.sentinels.masked_arithmetic.checks import (
    find_function,
    guard_exists_for_field,
    unguarded_arithmetic_sites,
    unguarded_masked_arithmetic,
)
from babylon.sentinels.masked_arithmetic.registry import (
    ARITHMETIC_WRAPPERS,
    DECLARED_FOGGED_CONSUMERS,
    MASKED_ARITHMETIC_EXEMPTIONS,
    DeclaredFoggedConsumer,
)

__all__ = [
    "ARITHMETIC_WRAPPERS",
    "DECLARED_FOGGED_CONSUMERS",
    "MASKED_ARITHMETIC_EXEMPTIONS",
    "DeclaredFoggedConsumer",
    "find_function",
    "guard_exists_for_field",
    "unguarded_arithmetic_sites",
    "unguarded_masked_arithmetic",
]
