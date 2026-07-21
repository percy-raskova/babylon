"""Legacy re-export shim over :mod:`babylon.projection.fog`.

Program 24 P1 WO-1 (the Hoist, part A) relocated this package's real
implementation to ``babylon.projection.fog`` — it was already
transport-neutral (zero ``django``/``babylon.engine`` coupling), so the move
is a pure relocation with no behavior change. This module exists only so
that ``web/`` code (``engine_bridge.py`` and any callers importing
``game.fog``/``game.fog.reach``/``game.fog.ledger``/``game.fog.filter``)
keeps working unchanged until the P4 cutover retires ``web/`` entirely. New
code should import :mod:`babylon.projection.fog` directly.

See the canonical package docstring at
``src/babylon/projection/fog/__init__.py`` for the fog-of-war design
(organizing reach, the intel ledger, ``apply_fog``).
"""

from __future__ import annotations

from babylon.projection.fog.filter import (
    ORG_INTERNAL_STATE_FIELDS,
    ORG_POLITICAL_FIELDS,
    POLITICAL_FIELDS,
    apply_fog,
    political_field_group,
)
from babylon.projection.fog.ledger import (
    IntelEntry,
    IntelLedger,
    IntelReading,
    VisibilityTier,
    ledger_from_events,
    read_intel,
)
from babylon.projection.fog.reach import organizing_reach

__all__ = [
    "IntelEntry",
    "IntelLedger",
    "IntelReading",
    "ORG_INTERNAL_STATE_FIELDS",
    "ORG_POLITICAL_FIELDS",
    "POLITICAL_FIELDS",
    "VisibilityTier",
    "apply_fog",
    "ledger_from_events",
    "organizing_reach",
    "political_field_group",
    "read_intel",
]
