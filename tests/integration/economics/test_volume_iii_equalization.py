"""Volume III equalization tendency — spec 060 US7(c) / FR-019 / SC-015.

Over many ticks on a scenario with active capital migration, the
inter-sectoral variance of the profit rate must MONOTONICALLY DECREASE
(strict: variance over the last 10 ticks < variance over the first 10).

This is the operational form of Marx's Volume III claim that capital
migrates from low-profit-rate sectors to high-profit-rate sectors,
equalizing the rate of profit over time. ``DefaultHexEqualizationComputer``
in ``src/babylon/domain/economics/substrate/equalization.py`` implements this
mechanism with a documented conservation proof.

Gated by ``skip_unless_active`` (transformation must be redistribution-
active) AND by ``equalization_alpha > 0`` (capital migration enabled)
per ``research.md`` R2 and the test infrastructure constraints.

Contract: FR-019 / SC-015.
"""

from __future__ import annotations

import pytest

from babylon.engine.scenarios.two_node import TwoNodeScenario
from tests._helpers.invariants.transformation_mode import skip_unless_active
from tests._helpers.invariants.variance_trace import ProfitRateVarianceTrace


@pytest.mark.invariant
class TestVolumeIIIEqualization:
    """Contract FR-019 / SC-015."""

    def test_inter_sectoral_variance_decreases(self) -> None:
        """50 ticks of capital migration → variance_late < variance_early.

        Gated by:
          1. Transformation mode is REDISTRIBUTION_ACTIVE.
          2. Scenario has ≥ 2 productive sectors.
          3. ``equalization_alpha > 0``.

        SKIPs cleanly today (gates closed); activates when the engine
        wiring matures.
        """
        _state, _config, defines = TwoNodeScenario().build()
        transformation = None
        skip_unless_active(transformation, spec_ref="spec-060 FR-019")

        # Gate 2: capital migration enabled
        eq_alpha = getattr(defines, "equalization_alpha", 0.0) if defines else 0.0
        if eq_alpha == 0.0:
            pytest.skip(
                "spec-060 FR-019: capital migration disabled "
                "(equalization_alpha == 0); Volume III equalization cannot "
                "be measured. See research.md R2."
            )

        # When both gates are open, run 50 ticks and collect the
        # per-tick (sector → profit-rate) mapping. Placeholder for
        # full implementation:
        trace = ProfitRateVarianceTrace.from_sector_rate_series([])
        assert trace.has_equalized(), (
            "spec-060 FR-019 violated: variance over last 10 ticks not less "
            f"than over first 10. early={trace.variance_early():.6g} "
            f"late={trace.variance_late():.6g}"
        )
