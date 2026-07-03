"""Unit tests for the Lawverian wealth-asymmetry gap formulas.

These replace the saturating :func:`calculate_contradiction_intensity`
(kept, deprecated) with scale-free gaps recomputed fresh each tick. The
central property — the reason the old saturation-at-1.0 bug is structurally
impossible now — is that the gap divides by the pole sum, so it is a pure
number bounded in ``[0, 1]`` that can *fall* as well as rise.
"""

from __future__ import annotations

import pytest

from babylon.formulas.contradiction import (
    calculate_wealth_asymmetry_balance,
    calculate_wealth_asymmetry_gap,
)

pytestmark = pytest.mark.math


class TestWealthAsymmetryGap:
    def test_parity_is_zero(self) -> None:
        assert calculate_wealth_asymmetry_gap(5.0, 5.0) == 0.0

    def test_known_ratio(self) -> None:
        # |30 - 10| / (10 + 30) = 20/40 = 0.5
        assert calculate_wealth_asymmetry_gap(10.0, 30.0) == pytest.approx(0.5)

    def test_symmetric_in_argument_order(self) -> None:
        assert calculate_wealth_asymmetry_gap(2.0, 9.0) == pytest.approx(
            calculate_wealth_asymmetry_gap(9.0, 2.0)
        )

    def test_bounded_in_unit_interval(self) -> None:
        # One pole holds (almost) everything → gap approaches but never exceeds 1.
        gap = calculate_wealth_asymmetry_gap(0.0, 1_000_000.0)
        assert 0.0 <= gap <= 1.0
        assert gap == pytest.approx(1.0)

    def test_both_zero_is_degenerate_zero_not_saturated(self) -> None:
        """The empty relation has NO contradiction — must not be 1.0."""
        assert calculate_wealth_asymmetry_gap(0.0, 0.0) == 0.0

    def test_dollar_scale_gap_does_not_saturate(self) -> None:
        """The original bug: a large dollar gap pinned intensity at 1.0.

        A worker at 0.8 and a bourgeois at 35.0 is a real, large wealth
        gap, yet the scale-free measure returns a moderate value, not 1.0.
        """
        gap = calculate_wealth_asymmetry_gap(0.8, 35.0)
        assert gap < 1.0
        assert gap == pytest.approx(34.2 / 35.8)

    def test_gap_can_fall_when_poles_converge(self) -> None:
        far = calculate_wealth_asymmetry_gap(1.0, 20.0)
        near = calculate_wealth_asymmetry_gap(10.0, 11.0)
        assert near < far

    def test_numeraire_invariance_exact(self) -> None:
        base = calculate_wealth_asymmetry_gap(1.3, 7.9)
        for k in (0.001, 100.0, 1e6):
            assert calculate_wealth_asymmetry_gap(1.3 * k, 7.9 * k) == pytest.approx(
                base, abs=1e-12
            )


class TestWealthAsymmetryBalance:
    def test_positive_when_pole_b_richer(self) -> None:
        assert calculate_wealth_asymmetry_balance(10.0, 30.0) == pytest.approx(0.5)

    def test_negative_when_pole_a_richer(self) -> None:
        assert calculate_wealth_asymmetry_balance(30.0, 10.0) == pytest.approx(-0.5)

    def test_parity_is_zero(self) -> None:
        assert calculate_wealth_asymmetry_balance(4.0, 4.0) == 0.0

    def test_both_zero_is_zero(self) -> None:
        assert calculate_wealth_asymmetry_balance(0.0, 0.0) == 0.0

    def test_magnitude_equals_gap(self) -> None:
        a, b = 2.0, 17.0
        assert abs(calculate_wealth_asymmetry_balance(a, b)) == pytest.approx(
            calculate_wealth_asymmetry_gap(a, b)
        )

    def test_bounded_in_signed_unit_interval(self) -> None:
        assert calculate_wealth_asymmetry_balance(0.0, 5.0) == pytest.approx(1.0)
        assert calculate_wealth_asymmetry_balance(5.0, 0.0) == pytest.approx(-1.0)

    def test_numeraire_invariance_exact(self) -> None:
        base = calculate_wealth_asymmetry_balance(3.1, 0.7)
        for k in (0.01, 250.0, 1e5):
            assert calculate_wealth_asymmetry_balance(3.1 * k, 0.7 * k) == pytest.approx(
                base, abs=1e-12
            )
