"""H3 resolution round-trip conservation — spec 060 US6(d) / FR-016 / SC-012.

Roll a per-hex aggregate up one resolution, then disaggregate back to
the original resolution using the engine's declared splitter
(``H3SplitterRule.UNIFORM`` per spec-060 FR-011 exception / R1). Assert:
(a) parent totals exactly equal Σ children at the intermediate
resolution, (b) per-child round-trip recovery holds within 1e-9 when
original siblings were uniform.

This test exercises a different property from spec-053 INV-002 sheaf-
gluing in ``tests/property/invariants/test_h3_hierarchical.py``: that
test asserts the static per-parent invariant; THIS test asserts the
*round-trip* identity through the disaggregator helper.

Contract: FR-016 / SC-012.
"""

from __future__ import annotations

import h3
import pytest

from babylon.config.h3_splitter import H3SplitterRule
from tests._helpers.invariants.h3_round_trip import rollup_then_disaggregate

# Tolerances per Contract FR-016 / SC-012
_PARENT_CONSERVATION_TOL: float = 1e-15  # exact within float epsilon
_PER_CHILD_RECOVERY_TOL: float = 1e-9


def _seven_children_under_parent(parent_res: int, child_res: int) -> list[str]:
    """Pick a real H3 parent cell and its 7 children at child_res."""
    # Use a known H3 location (downtown Detroit area, just for a real index).
    # We just need any valid parent at parent_res.
    detroit_lat, detroit_lng = 42.3314, -83.0458
    parent = h3.latlng_to_cell(detroit_lat, detroit_lng, parent_res)
    children = list(h3.cell_to_children(parent, child_res))
    assert len(children) == 7, (
        f"H3 child count should be 7 at one finer resolution, got {len(children)}"
    )
    return children


@pytest.mark.invariant
class TestH3RoundTripConservation:
    """Contract FR-016 / SC-012."""

    def test_rollup_disaggregate_conserves_parent_total_exactly(self) -> None:
        """Parent totals exactly equal Σ children (1e-15 float-epsilon).

        Uses heterogeneous original sibling values to verify the parent
        total is preserved even when per-child round-trip is not exact.
        """
        children = _seven_children_under_parent(parent_res=7, child_res=8)
        original = {c: float(i + 1) for i, c in enumerate(children)}
        parent_total_expected = sum(original.values())  # 1 + 2 + ... + 7 = 28

        _round_tripped, parent_totals = rollup_then_disaggregate(
            original, parent_resolution=7, splitter=H3SplitterRule.UNIFORM
        )
        assert len(parent_totals) == 1, "expected single parent for 7 sibling children"
        parent_total = next(iter(parent_totals.values()))

        rel = abs(parent_total - parent_total_expected) / max(abs(parent_total_expected), 1e-300)
        assert rel <= _PARENT_CONSERVATION_TOL, (
            f"spec-060 FR-016 violated: parent total drifted under roll-up. "
            f"expected={parent_total_expected:.15g} got={parent_total:.15g} "
            f"relative_error={rel:.3e}"
        )

    def test_uniform_siblings_recover_per_child(self) -> None:
        """When original siblings are uniform, per-child round-trip is exact.

        Per the helper's documented limitation: per-cell recovery is
        guaranteed only when original siblings were uniform; the
        general case preserves the parent total but uniformizes within
        each group. This test verifies the documented exact-recovery
        case.
        """
        children = _seven_children_under_parent(parent_res=7, child_res=8)
        uniform_value = 3.14159
        original = dict.fromkeys(children, uniform_value)

        round_tripped, _parent_totals = rollup_then_disaggregate(
            original, parent_resolution=7, splitter=H3SplitterRule.UNIFORM
        )

        worst_delta: float = 0.0
        worst_cell: str | None = None
        for cell, orig_val in original.items():
            rt_val = round_tripped[cell]
            denom = max(abs(orig_val), 1e-300)
            rel = abs(orig_val - rt_val) / denom
            if rel > worst_delta:
                worst_delta = rel
                worst_cell = cell

        assert worst_delta <= _PER_CHILD_RECOVERY_TOL, (
            f"spec-060 FR-016 violated: per-child recovery diverged for uniform "
            f"siblings. worst cell={worst_cell!r} original={uniform_value} "
            f"round-tripped={round_tripped.get(worst_cell)} "
            f"relative_error={worst_delta:.3e}"
        )
