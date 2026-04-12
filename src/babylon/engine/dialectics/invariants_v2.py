"""Universal and per-type invariant checking for the v2 engine.

The engine enforces three universal invariants on every Dialectic at
every tick:

1. ``weight ∈ [-1, 1]``
2. Type stability across motion (a CommodityDialectic remains one)
3. ``step()`` returns a Dialectic of the declared type

Per-type invariants are defined by each Dialectic subclass via the
``invariants()`` method.

See Also:
    :meth:`babylon.engine.dialectics.base.Dialectic.invariants`
"""

from __future__ import annotations

from typing import Any

from babylon.engine.dialectics.base import Dialectic
from babylon.engine.dialectics.world import World


def check_universal_invariants(d: Dialectic[Any, Any]) -> list[str]:
    """Check universal invariants on a single dialectic.

    Universal invariants:
        - weight ∈ [-1.0, 1.0]
        - type_tag is a non-empty string

    These are defensive checks — Pydantic should already enforce weight
    bounds, but we double-check at runtime as a safety net.

    Args:
        d: Any Dialectic instance.

    Returns:
        List of violation descriptions. Empty = valid.
    """
    violations: list[str] = []
    if d.weight < -1.0 or d.weight > 1.0:
        violations.append(f"{d.type_tag} {d.id}: weight {d.weight} out of [-1, 1]")
    if not d.type_tag:
        violations.append(f"Dialectic {d.id}: empty type_tag")
    return violations


def check_all_invariants(world: World) -> list[str]:
    """Check all invariants across every dialectic in the world.

    Runs universal invariants + per-type invariants on every dialectic.

    Args:
        world: The current World state.

    Returns:
        Aggregated list of all invariant violations. Empty = valid world.
    """
    violations: list[str] = []
    for d in world.dialectics.values():
        violations.extend(check_universal_invariants(d))
        violations.extend(d.invariants())
    return violations
