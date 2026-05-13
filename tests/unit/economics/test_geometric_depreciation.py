"""Tests for spec 062 geometric weekly depreciation/equalization helpers.

Covers FR-014, FR-015, FR-029a invariants.
"""

from __future__ import annotations

import math

import pytest

from babylon.economics.geometric_depreciation import alpha_weekly, delta_weekly


@pytest.mark.cross_scale
@pytest.mark.math
class TestDeltaWeekly:
    """delta_weekly: annual rate -> per-tick equivalent."""

    def test_inverse_identity_at_07(self) -> None:
        """(1 - delta_weekly(0.07))^52 == 1 - 0.07 within 1e-12."""
        d_annual = 0.07
        d_weekly = delta_weekly(d_annual)
        assert math.isclose(
            (1.0 - d_weekly) ** 52,
            1.0 - d_annual,
            abs_tol=1e-12,
        )

    def test_known_value_at_07(self) -> None:
        """FR-015 invariant: delta_weekly(0.07) ~ 0.001397."""
        assert math.isclose(delta_weekly(0.07), 0.001397, abs_tol=1e-5)

    def test_zero_rate_returns_zero(self) -> None:
        assert delta_weekly(0.0) == 0.0

    def test_rejects_negative(self) -> None:
        with pytest.raises(ValueError):
            delta_weekly(-0.01)

    def test_rejects_unit_or_above(self) -> None:
        with pytest.raises(ValueError):
            delta_weekly(1.0)
        with pytest.raises(ValueError):
            delta_weekly(1.5)


@pytest.mark.cross_scale
@pytest.mark.math
class TestAlphaWeekly:
    """alpha_weekly: identical functional form to delta_weekly."""

    def test_inverse_identity_at_01(self) -> None:
        a_annual = 0.01
        a_weekly = alpha_weekly(a_annual)
        assert math.isclose(
            (1.0 - a_weekly) ** 52,
            1.0 - a_annual,
            abs_tol=1e-12,
        )

    def test_fr_029a_invariant_holds_at_default(self) -> None:
        """alpha_weekly(0.01) must be strictly less than 1/52."""
        assert alpha_weekly(0.01) < 1.0 / 52.0

    def test_rejects_negative(self) -> None:
        with pytest.raises(ValueError):
            alpha_weekly(-0.01)
