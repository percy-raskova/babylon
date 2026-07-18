"""Tick execution partitions (spec-116 systems-dedup Phase 4, ADR081).

The engine runs its Systems in strict materialist-causality order, grouped into
three partitions (Spec 056 FR-002). Each System declares which partition it
belongs to via ``partition: ClassVar[TickPartition]`` and its ordinal via
``position: ClassVar[float]``; ``simulation_engine`` derives both the ordered
``_DEFAULT_SYSTEMS`` list and the partition frozensets from those declarations,
so a System's ordering metadata lives on the System (single source of truth)
rather than being restated in a hand-ordered list plus three hand-maintained
sets. Kernel-layer: depends on nothing above it (Program 14 layering).
"""

from __future__ import annotations

from enum import StrEnum


class TickPartition(StrEnum):
    """The three tick phases, in materialist-causality order.

    Values:
        MATERIAL_BASE: Biological/spatial/economic base (positions 1–13).
        ACTION: Organizations observe + act — the OODA phase (position 14).
        CONSEQUENCE: Superstructural consequences of the acted-on base
            (positions 14.5–22).
    """

    MATERIAL_BASE = "material_base"
    ACTION = "action"
    CONSEQUENCE = "consequence"
