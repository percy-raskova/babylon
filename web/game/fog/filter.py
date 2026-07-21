"""Legacy re-export shim over :mod:`babylon.projection.fog.filter`.

Relocated by Program 24 P1 WO-1 (the Hoist, part A); see
``web/game/fog/__init__.py`` for the shim rationale and
``babylon.projection.fog.filter`` for the real implementation.
"""

from __future__ import annotations

from babylon.projection.fog.filter import (
    ORG_INTERNAL_STATE_FIELDS,
    ORG_POLITICAL_FIELDS,
    POLITICAL_FIELDS,
    apply_fog,
    political_field_group,
)

__all__ = [
    "ORG_INTERNAL_STATE_FIELDS",
    "ORG_POLITICAL_FIELDS",
    "POLITICAL_FIELDS",
    "apply_fog",
    "political_field_group",
]
