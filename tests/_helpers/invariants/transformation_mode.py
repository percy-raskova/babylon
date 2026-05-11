"""Transformation-mode probe — spec 060 FR-021 single source of truth.

Per ``src/babylon/engine/dialectics/transformation.py:54-55``:

    weight < 0 → values dominate prices (low equalization)
    weight > 0 → prices of production fully equalized

The probe classifies modes based on this weight. Tests gated on
redistribution-active mode (FR-005-redistribution-arm, FR-006, FR-007,
FR-019) call ``skip_unless_active(...)`` so the gate is enforced in one
place.

Contract: ``specs/060-value-form-invariants/contracts/transformation_mode_probe.md``.

NOTE on engine integration
--------------------------
The ``WorldState`` model does not currently carry a ``dialectics``
field; ``TransformationDialectic`` is stored separately in the engine's
dialectic registry. The probe accepts the dialectic directly (or
``None`` → PROPORTIONAL_PRICES) so it is callable from tests that
either (a) hold a dialectic reference, or (b) operate on a stock
``WorldState`` and expect the proportional-prices default.
"""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Any

import pytest


class TransformationMode(StrEnum):
    """Mode of the transformation engine."""

    PROPORTIONAL_PRICES = "proportional"
    REDISTRIBUTION_ACTIVE = "redistribution"


def probe_transformation_mode(transformation_dialectic: Any | None) -> TransformationMode:
    """Probe a transformation dialectic's weight to determine mode.

    Per the strict ``> 0`` boundary: at ``weight == 0`` the dialectic is
    exactly at the value/price boundary; the probe prefers
    ``PROPORTIONAL_PRICES`` (SKIP) rather than RUN with degenerate
    behavior.

    Args:
        transformation_dialectic: Either an instance with a numeric
            ``weight`` attribute, or ``None``. ``None`` and ``nan``
            weights both map to ``PROPORTIONAL_PRICES``.

    Returns:
        ``REDISTRIBUTION_ACTIVE`` iff ``weight`` exists and is finite
        and strictly positive; otherwise ``PROPORTIONAL_PRICES``.
    """
    if transformation_dialectic is None:
        return TransformationMode.PROPORTIONAL_PRICES
    weight = getattr(transformation_dialectic, "weight", None)
    if weight is None:
        return TransformationMode.PROPORTIONAL_PRICES
    try:
        w = float(weight)
    except (TypeError, ValueError):
        return TransformationMode.PROPORTIONAL_PRICES
    if not math.isfinite(w):
        return TransformationMode.PROPORTIONAL_PRICES
    return (
        TransformationMode.REDISTRIBUTION_ACTIVE
        if w > 0.0
        else TransformationMode.PROPORTIONAL_PRICES
    )


def skip_unless_active(
    transformation_dialectic: Any | None,
    spec_ref: str = "spec-060",
) -> None:
    """pytest-style skip if not in ``REDISTRIBUTION_ACTIVE`` mode.

    Args:
        transformation_dialectic: As accepted by
            ``probe_transformation_mode``.
        spec_ref: Embedded in the skip reason for traceability (FR-010).
    """
    if (
        probe_transformation_mode(transformation_dialectic)
        != TransformationMode.REDISTRIBUTION_ACTIVE
    ):
        pytest.skip(
            f"Transformation engine in proportional-prices mode (weight <= 0). "
            f"Test gated by {spec_ref} FR-008."
        )


__all__ = [
    "TransformationMode",
    "probe_transformation_mode",
    "skip_unless_active",
]
