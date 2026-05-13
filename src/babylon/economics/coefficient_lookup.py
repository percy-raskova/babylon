"""Coefficient lookup policy re-export for economics callsites.

The actual model lives at :mod:`babylon.config.defines.cross_scale` to avoid
a circular import with :mod:`babylon.config.defines.economy_basic`. This
module re-exports it so callsites that conceptually treat the policy as an
economics primitive read naturally.

Spec 062 — FR-011 / FR-012 / FR-013.
"""

from __future__ import annotations

from babylon.config.defines.cross_scale import (
    CoefficientLookupPolicy,
    LookupPolicy,
)

__all__ = ["LookupPolicy", "CoefficientLookupPolicy"]
