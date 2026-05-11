"""Productivity-shock value-price decoupling — spec 060 US5 / FR-007 / SC-005.

Doubling productivity in one sector (halving SNLT-per-unit) must:

  (a) Immediately halve the labor-value of that sector's output (T+1).
  (b) NOT immediately halve the money-price of that sector's output;
      price falls strictly less than half at T+1.
  (c) Over ticks T+1..T+5, the price asymptotically approaches the
      new value × τ (monotonically decreasing gap), demonstrating
      gradual equalization.

This is the testable content of the value/price distinction. A bug
that wires SNLT recompute and price recompute to the same tick boundary
collapses the gap and this test catches it.

Gated by ``skip_unless_active`` (transformation must be active). SKIPs
cleanly today.

Contract: FR-007 / SC-005.
"""

from __future__ import annotations

import pytest

from babylon.engine.scenarios.two_node import TwoNodeScenario
from tests._helpers.invariants.transformation_mode import skip_unless_active


@pytest.mark.invariant
class TestProductivityShockDecoupling:
    """Contract FR-007 / SC-005."""

    def test_value_drops_immediately_price_lags(self) -> None:
        """Halve SNLT at boundary T → value halves T+1, price lags T+1..T+5.

        SKIPs cleanly today (transformation engine in proportional
        mode). When active, the test:

        1. Builds baseline at tick T, records value_S_old, price_S_old.
        2. Halves SNLT in designated sector S → world'.
        3. Runs T+1; asserts ``|value_S_new - value_S_old/2| / |...| < 1e-9``
           AND ``price_S_new / price_S_old > 0.5 + 1e-3``.
        4. Runs T+2..T+5; asserts the price/(value × τ) deviation from
           1.0 is monotonically decreasing.
        """
        _state, _config, _defines = TwoNodeScenario().build()
        transformation = None
        skip_unless_active(transformation, spec_ref="spec-060 FR-007")

        # Body activates when the transformation engine matures.
        # The pattern below is the full assertion the test will run:
        #
        #   shocked = halve_snlt_in_sector(state, sector_id="S1")
        #   t1_baseline = step(state)
        #   t1_shocked = step(shocked)
        #
        #   value_old = compute_sector_value(t1_baseline, "S1")
        #   value_new = compute_sector_value(t1_shocked, "S1")
        #   price_old = compute_sector_price(t1_baseline, "S1")
        #   price_new = compute_sector_price(t1_shocked, "S1")
        #
        #   assert abs(value_new - value_old/2) / (value_old/2) <= 1e-9
        #   assert price_new / price_old > 0.5 + 1e-3
        #
        #   # T+2..T+5: gap closes
        #   gap_prev = abs(price_new - value_new * tau) / max(price_new, 1e-300)
        #   for _ in range(4):
        #       t_shocked = step(t_shocked)
        #       v = compute_sector_value(t_shocked, "S1")
        #       p = compute_sector_price(t_shocked, "S1")
        #       gap = abs(p - v * tau) / max(p, 1e-300)
        #       assert gap < gap_prev, "spec-060 FR-007: gap not monotone"
        #       gap_prev = gap
        pytest.fail("spec-060 FR-007 gate opened but body not yet wired")  # pragma: no cover
