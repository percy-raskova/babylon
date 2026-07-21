"""Legacy re-export shim over :mod:`babylon.projection.veil`.

Relocated by Program 24 P2 WO-41 (veil-tier hoist); see
``babylon.projection.veil`` for the real implementation and its full
rationale (monotonic gating, §5d field->tier registry, I-15 calibration).
The legacy bridge and serializers keep importing from here so the doctrine
veil stays single-sourced through the P4 cutover.
"""

from __future__ import annotations

from babylon.projection.veil import (
    TIER1_VALUE_RELATION_FIELDS,
    TIER2_SCISSORS_FIELDS,
    VeilStatus,
    compute_veil_status,
    compute_veil_tier,
    gate_value_axis_fields,
)

__all__ = [
    "TIER1_VALUE_RELATION_FIELDS",
    "TIER2_SCISSORS_FIELDS",
    "VeilStatus",
    "compute_veil_status",
    "compute_veil_tier",
    "gate_value_axis_fields",
]
