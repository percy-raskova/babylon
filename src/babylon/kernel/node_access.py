"""Shared graph-node payload accessors (spec-116 systems-dedup Phase 3).

Small, allocation-free readers over the loosely-typed ``dict[str, Any]`` node
payloads that Systems mutate in place. Lifted here to kill per-system copies;
each reader defaults defensively (a missing/malformed sub-payload yields the
neutral value) so callers need no guards. Kernel-layer: depends on nothing
above it (Program 14 layering).
"""

from __future__ import annotations

from typing import Any


def class_consciousness_from_node(
    node_data: dict[str, Any],
) -> float:  # pragma: no mutate — graph accessor
    """Read ``class_consciousness`` from a node's ``ideology`` sub-dict.

    The ``ideology`` payload is the ``IdeologicalProfile`` dict written by
    ConsciousnessSystem. A missing or non-dict ``ideology``, or a dict lacking
    the key, yields ``0.0``. Consolidates three identical
    ``_get_class_consciousness_from_node`` copies (SolidaritySystem,
    StruggleSystem, ImperialRentSystem).

    :param node_data: A graph node's attribute dict.
    :returns: ``class_consciousness`` in ``[0, 1]``, or ``0.0`` when absent.
    """
    ideology = node_data.get("ideology")  # pragma: no mutate

    if ideology is None:  # pragma: no mutate
        return 0.0  # pragma: no mutate

    if isinstance(ideology, dict):  # pragma: no mutate
        return float(ideology.get("class_consciousness", 0.0))  # pragma: no mutate

    return 0.0  # pragma: no mutate
