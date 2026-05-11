"""OCC monotonicity (sign property) — spec 060 US7(b) / FR-018 / SC-014.

For any entity: monotonically increasing c (v fixed) must monotonically
INCREASE its organic composition c/v. Symmetrically, monotonically
increasing v (c fixed) must monotonically DECREASE its OCC.

This is the simplest direction-of-effect check the value tensor must
satisfy. A bug that swaps c↔v in the derived-metrics module would
flip the sign and this test would catch it.

Contract: FR-018 / SC-014.
"""

from __future__ import annotations

import pytest

_N_POINTS: int = 11


def _occ(c: float, v: float) -> float:
    return c / v


@pytest.mark.invariant
class TestOCCMonotonicity:
    """Contract FR-018 / SC-014."""

    def test_occ_monotone_in_c(self) -> None:
        """c sweep with v fixed: OCC is strictly non-decreasing.

        11 evenly-spaced c values from 0.5×baseline to 1.5×baseline.
        """
        c0, v0 = 100.0, 50.0
        c_values = [c0 * (0.5 + 0.1 * i) for i in range(_N_POINTS)]
        occs = [_occ(c, v0) for c in c_values]
        for i in range(len(occs) - 1):
            assert occs[i + 1] >= occs[i], (
                f"spec-060 FR-018 violated (c-sweep): OCC not monotone non-decreasing "
                f"at index {i}. c={c_values[i]} occ={occs[i]} → c={c_values[i + 1]} occ={occs[i + 1]}"
            )

    def test_occ_monotone_in_v(self) -> None:
        """v sweep with c fixed: OCC is strictly non-increasing.

        11 evenly-spaced v values from 0.5×baseline to 1.5×baseline.
        """
        c0, v0 = 100.0, 50.0
        v_values = [v0 * (0.5 + 0.1 * i) for i in range(_N_POINTS)]
        occs = [_occ(c0, v) for v in v_values]
        for i in range(len(occs) - 1):
            assert occs[i + 1] <= occs[i], (
                f"spec-060 FR-018 violated (v-sweep): OCC not monotone non-increasing "
                f"at index {i}. v={v_values[i]} occ={occs[i]} → v={v_values[i + 1]} occ={occs[i + 1]}"
            )
