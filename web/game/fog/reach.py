"""Legacy re-export shim over :mod:`babylon.projection.fog.reach`.

Relocated by Program 24 P1 WO-1 (the Hoist, part A); see
``web/game/fog/__init__.py`` for the shim rationale and
``babylon.projection.fog.reach`` for the real implementation.
"""

from __future__ import annotations

from babylon.projection.fog.reach import organizing_reach

__all__ = ["organizing_reach"]
