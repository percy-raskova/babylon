"""Transformation-mode probe — spec 060 T042 (remediation C3 / FR-008).

Unit test for the gate itself: verifies that ``skip_unless_active``
fires when transformation weight ≤ 0 and that ``probe_transformation_mode``
returns the correct mode based on weight sign.

This is the gate-behavior test that addresses the C3 coverage gap
identified in /speckit.analyze: the four transformation-gated
integration tests (FR-005-redist, FR-006, FR-007, FR-019) all *call*
``skip_unless_active`` but no test asserts the SKIP actually fires
correctly. This unit test does.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from tests._helpers.invariants.transformation_mode import (
    TransformationMode,
    probe_transformation_mode,
    skip_unless_active,
)


@dataclass
class _MockDialectic:
    """Minimal stand-in for ``TransformationDialectic`` carrying weight."""

    weight: float


@pytest.mark.invariant
class TestTransformationModeProbe:
    """Spec 060 FR-008 / FR-021 gate-behavior verification."""

    def test_probe_returns_redistribution_active_when_weight_positive(self) -> None:
        d = _MockDialectic(weight=0.5)
        assert probe_transformation_mode(d) == TransformationMode.REDISTRIBUTION_ACTIVE

    def test_probe_returns_proportional_when_weight_negative(self) -> None:
        d = _MockDialectic(weight=-0.5)
        assert probe_transformation_mode(d) == TransformationMode.PROPORTIONAL_PRICES

    def test_probe_returns_proportional_when_weight_zero(self) -> None:
        """Strict ``> 0`` boundary per ``contracts/transformation_mode_probe.md``."""
        d = _MockDialectic(weight=0.0)
        assert probe_transformation_mode(d) == TransformationMode.PROPORTIONAL_PRICES

    def test_probe_returns_proportional_on_none(self) -> None:
        assert probe_transformation_mode(None) == TransformationMode.PROPORTIONAL_PRICES

    def test_probe_returns_proportional_on_nan_weight(self) -> None:
        d = _MockDialectic(weight=float("nan"))
        assert probe_transformation_mode(d) == TransformationMode.PROPORTIONAL_PRICES

    def test_skip_unless_active_skips_when_proportional(self) -> None:
        """The gate fires: SKIP raised when in proportional-prices mode.

        Verifies the SKIP reason embeds 'spec-060' per FR-010 traceability.
        """
        d = _MockDialectic(weight=-0.5)
        with pytest.raises(pytest.skip.Exception) as exc_info:
            skip_unless_active(d, spec_ref="spec-060 FR-008-test")
        assert "spec-060" in str(exc_info.value)

    def test_skip_unless_active_does_not_skip_when_active(self) -> None:
        """No SKIP raised when transformation is active."""
        d = _MockDialectic(weight=0.5)
        # Should return without raising.
        skip_unless_active(d, spec_ref="spec-060 FR-008-test")
