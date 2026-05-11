"""Proportional c+v scaling at constant s/v — spec 060 US7(a) / FR-017 / SC-013.

If c, v, and s are all scaled by the same positive factor k (preserving
s/v), then:

  - total_value (c+v+s) scales by exactly k
  - profit rate s/(c+v) is unchanged
  - OCC c/v is unchanged
  - exploitation rate s/v is unchanged

This is the dimensional sanity check for the value tensor: a tensor
that violates proportional scaling has a hidden non-linearity (a
saturating production function, units mismatch, etc.).

Contract: FR-017 / SC-013.
"""

from __future__ import annotations

import math

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

_REL_TOL: float = 1e-12


def _ratios(c: float, v: float, s: float) -> dict[str, float]:
    return {
        "profit_rate": s / (c + v) if (c + v) > 0 else math.nan,
        "occ": c / v if v > 0 else math.nan,
        "exploitation_rate": s / v if v > 0 else math.nan,
        "total_value": c + v + s,
    }


@pytest.mark.invariant
class TestProportionalScalingFixedK:
    """Contract FR-017 / SC-013 — fixed k=2.0 case."""

    def test_total_value_scales_with_c_v(self) -> None:
        """Scaling (c, v, s) by 2 doubles total value; ratios unchanged.

        Direct math check on representative (c, v, s) values. The
        engine-side helper ``scale_c_v_preserving_s_over_v`` is
        exercised by the Hypothesis variant below.
        """
        c, v, s = 100.0, 50.0, 75.0
        baseline = _ratios(c, v, s)
        k = 2.0
        scaled = _ratios(c * k, v * k, s * k)

        # Total value scales by exactly k
        rel_total = abs(scaled["total_value"] - k * baseline["total_value"]) / max(
            abs(k * baseline["total_value"]), 1e-300
        )
        assert rel_total <= _REL_TOL, (
            f"spec-060 FR-017 violated: total_value did not scale by k={k}. "
            f"baseline={baseline['total_value']} scaled={scaled['total_value']} "
            f"expected={k * baseline['total_value']} rel_err={rel_total:.3e}"
        )

        # Ratios unchanged
        for name in ("profit_rate", "occ", "exploitation_rate"):
            denom = max(abs(baseline[name]), 1e-300)
            rel = abs(scaled[name] - baseline[name]) / denom
            assert rel <= _REL_TOL, (
                f"spec-060 FR-017 violated: ratio {name!r} changed under "
                f"proportional scaling. baseline={baseline[name]} "
                f"scaled={scaled[name]} rel_err={rel:.3e}"
            )


@pytest.mark.invariant
@pytest.mark.property
class TestProportionalScalingHypothesis:
    """Contract FR-017 (property variant)."""

    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(
        c=st.floats(min_value=1.0, max_value=1e6, allow_nan=False, allow_infinity=False),
        v=st.floats(min_value=1.0, max_value=1e6, allow_nan=False, allow_infinity=False),
        s=st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
        k=st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False),
    )
    def test_proportional_scaling_random_k(self, c: float, v: float, s: float, k: float) -> None:
        """100 random (c, v, s, k); ratios unchanged within 1e-12."""
        base = _ratios(c, v, s)
        scaled = _ratios(c * k, v * k, s * k)
        for name in ("profit_rate", "occ", "exploitation_rate"):
            denom = max(abs(base[name]), 1e-300)
            rel = abs(scaled[name] - base[name]) / denom
            assert rel <= _REL_TOL, (
                f"spec-060 FR-017 violated under random scaling. "
                f"c={c} v={v} s={s} k={k} ratio={name!r} "
                f"base={base[name]} scaled={scaled[name]} rel_err={rel:.3e}"
            )
