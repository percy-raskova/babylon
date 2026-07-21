"""Legacy re-export shim over :mod:`babylon.projection.fog.ledger`.

Relocated by Program 24 P1 WO-1 (the Hoist, part A); see
``web/game/fog/__init__.py`` for the shim rationale and
``babylon.projection.fog.ledger`` for the real implementation.
"""

from __future__ import annotations

from babylon.projection.fog.ledger import (
    IntelEntry,
    IntelLedger,
    IntelReading,
    VisibilityTier,
    ledger_from_events,
    read_intel,
)

__all__ = [
    "IntelEntry",
    "IntelLedger",
    "IntelReading",
    "VisibilityTier",
    "ledger_from_events",
    "read_intel",
]
