"""Gate composition — the fog + class-vision precedence rule (WO-41).

The keel inherited a documented correctness hazard (``filter.py``'s own
header): the spatial fog gate (:func:`~babylon.projection.fog.filter.apply_fog`)
and the class-vision gate
(:func:`~babylon.projection.fog.class_vision.apply_class_vision`) both gate
political fields, and running both on one payload was flagged as
unresolved. This module RESOLVES it by pinning the composition:

**Vision first, fog second.** Both gates are restriction maps (each output
field is the input field, quantized, or withheld — never something new),
so their sequential composition is itself a restriction map: the composite
can never reveal MORE than either gate alone would. Order matters only for
the marker keys, and vision-then-fog lets the spatial gate's per-call
verdict (reach wins outright) still bound the final shape. Deterministic
by construction — both gates quantize on fixed grids, no noise
(Constitution III.7).

A field the vision gate withheld stays withheld: fog only ever further
restricts a ``None``. A field both gates quantize is quantized twice —
strictly-not-more-precise, deterministic, and idempotent on shared grid
points; the honest reading is "the coarser of two blurs".
"""

from __future__ import annotations

from typing import Any

from babylon.projection.fog.class_vision import apply_class_vision
from babylon.projection.fog.filter import POLITICAL_FIELDS, apply_fog
from babylon.projection.fog.ledger import IntelLedger


def apply_political_gates(
    payload: dict[str, Any],
    *,
    node_type: str,
    node_id: str,
    vision: str | None,
    reach: frozenset[str],
    ledger: IntelLedger,
    tick: int,
    staleness_ticks: int,
    unknown_ticks: int,
    political_fields: tuple[str, ...] = POLITICAL_FIELDS,
) -> dict[str, Any]:
    """Run BOTH political gates on one payload, in the pinned order.

    :param payload: The read-model payload (never mutated).
    :param node_type: The subject's node type.
    :param node_id: The subject's node id.
    :param vision: The class-vision state (``desert``/``mud``/``water``)
        or ``None`` when no vision is computed (vision gate is a no-op).
    :param reach: The org's organizing-reach node ids.
    :param ledger: The session's intel ledger.
    :param tick: The current tick.
    :param staleness_ticks: Intel exact-tier age bound.
    :param unknown_ticks: Intel approximate-tier age bound.
    :param political_fields: The gated field vocabulary.
    :returns: A NEW gated dict — vision applied first, fog second.
    """
    return apply_fog(
        apply_class_vision(payload, vision),
        node_type,
        node_id,
        reach,
        ledger,
        tick,
        staleness_ticks=staleness_ticks,
        unknown_ticks=unknown_ticks,
        political_fields=political_fields,
    )
