"""Class-vision gate (EH Phase 2) — pure port of the bridge's inspector gate.

Desert WITHHOLDS the political fields (``None`` + a ``vision_masked``
marker list — falsification is Phase 3, gated on ruling 2); Mud shows them
quantized to the corpus's ±0.2 margin (+ ``vision_approx``); Water is
exact. ``vision=None`` (no computed vision) leaves the payload untouched —
persisted snapshots upstream always keep TRUE values (the DB is the
engine's ledger, not the player's view); this gate runs only at the
player-facing boundary.

Pure, non-mutating port (WO-41) of ``engine_bridge._apply_class_vision_gate``
so the TUI and the legacy inspector share one rule; the bridge delegates.
Composition with the spatial fog gate is defined in
:func:`babylon.projection.fog.precedence.apply_political_gates` — the
previously documented "two gates on one payload" hazard is resolved there,
not ad hoc at call sites.
"""

from __future__ import annotations

import math
from typing import Any

#: EH Phase 2's five gated class-political fields (the sixth surface,
#: ``consciousness``, is the ternary dict handled structurally below).
#: Material/public fields (wealth, population, wages) are never gated —
#: the corpus keeps public_info visible in every vision state.
VISION_GATED_CLASS_FIELDS: tuple[str, ...] = (
    "agitation",
    "class_consciousness",
    "national_identity",
    "organization",
    "p_revolution",
)

#: Corpus Mud rule: "±0.2 margin of error". A bucket of width W bounds
#: displayed error to W/2, so honoring a ±0.2 margin needs 0.4-wide buckets
#: — a 0.2 quantum would ship TWICE the precision the corpus allows.
#: Constitution III.7: masking must be a deterministic function of
#: committed state — quantization, not noise.
MUD_QUANTUM: float = 0.4


def mud_quantize(value: float) -> float:
    """One gated value onto the Mud grid: round-half-up, clamped to [0, 1].

    Explicit half-up (``floor(v/Q + 0.5)``), NOT banker's ``round()``:
    half-to-even makes grid boundaries flip direction by IEEE-754
    representation accident — an undocumented rule the player could never
    learn. The clamp keeps displayed values in the gated fields' [0, 1]
    domain.

    :param value: The true value.
    :returns: The quantized display value.
    """
    return min(1.0, max(0.0, math.floor(value / MUD_QUANTUM + 0.5) * MUD_QUANTUM))


def apply_class_vision(payload: dict[str, Any], vision: str | None) -> dict[str, Any]:
    """Gate a class payload by vision state — returns a NEW dict.

    :param payload: The class-inspector payload (not mutated).
    :param vision: ``"desert"`` / ``"mud"`` / ``"water"`` or ``None``.
    :returns: The gated copy. ``None`` vision returns an unmarked copy;
        desert masks only fields ACTUALLY holding a value (an already-None
        field is honest data-absence — claiming "the fog hid this" for it
        would conflate missing data with withheld data, III.11).
    """
    gated = dict(payload)
    if vision is None:
        return gated
    gated["class_vision"] = vision
    if vision == "water":
        return gated
    if vision == "desert":
        masked: list[str] = []
        for field in VISION_GATED_CLASS_FIELDS:
            if gated.get(field) is not None:
                gated[field] = None
                masked.append(field)
        if gated.get("consciousness") is not None:
            gated["consciousness"] = None
            masked.append("consciousness")
        gated["vision_masked"] = masked
        return gated
    # mud — deterministic quantization
    approx: list[str] = []
    for field in VISION_GATED_CLASS_FIELDS:
        value = gated.get(field)
        if isinstance(value, int | float):
            gated[field] = mud_quantize(float(value))
            approx.append(field)
    ternary = gated.get("consciousness")
    if isinstance(ternary, dict):
        gated["consciousness"] = {k: mud_quantize(float(v)) for k, v in ternary.items()}
        approx.append("consciousness")
    gated["vision_approx"] = approx
    return gated
