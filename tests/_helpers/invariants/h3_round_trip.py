"""H3 roll-up / disaggregate round-trip helper — spec 060 US6(d) / FR-016.

Takes a child-resolution hex aggregate, rolls it up to one parent
resolution via ``h3.cell_to_parent``, then disaggregates back to the
child resolution per the chosen splitter rule. Returns both the
intermediate parent totals (for conservation assertion) and the
round-tripped per-child values (for per-cell recovery assertion).

When original siblings within a parent group have equal values, the
per-cell recovery is exact (within float epsilon). When siblings have
unequal values, the parent total is exactly preserved but per-cell
recovery washes out to the parent mean — that is the documented
limitation of uniform splitting and is asserted only at the parent
level.
"""

from __future__ import annotations

import h3

from babylon.config.h3_splitter import (
    DEFAULT_SPLITTER,
    H3SplitterRule,
    split_uniformly,
)


def rollup_then_disaggregate(
    hex_values: dict[str, float],
    parent_resolution: int,
    splitter: H3SplitterRule = DEFAULT_SPLITTER,
) -> tuple[dict[str, float], dict[str, float]]:
    """Roll up to ``parent_resolution``, then disaggregate back.

    Args:
        hex_values: ``{h3_index_at_R: value}`` at the child resolution.
        parent_resolution: ``R - 1`` (the rolled-up resolution).
        splitter: Disaggregation rule. Only ``UNIFORM`` is supported
            at landing time.

    Returns:
        Tuple ``(round_tripped, parent_totals)``:

        * ``round_tripped[h3_index_at_R]`` — per-child value after the
          full roll-up-and-down. Equals the original iff siblings were
          uniform; otherwise the parent's children all share the parent
          mean.
        * ``parent_totals[h3_index_at_R-1]`` — intermediate roll-up
          sums.

    Raises:
        ValueError: If ``splitter`` is not ``UNIFORM`` (other rules
            deferred to a future spec).
    """
    if splitter is not H3SplitterRule.UNIFORM:
        raise ValueError(f"Unsupported splitter rule {splitter!r}; only UNIFORM is supported")

    # Step 1: roll up children -> parents
    parent_totals: dict[str, float] = {}
    parent_children: dict[str, list[str]] = {}
    for child_idx, value in hex_values.items():
        parent_idx = h3.cell_to_parent(child_idx, parent_resolution)
        parent_totals[parent_idx] = parent_totals.get(parent_idx, 0.0) + value
        parent_children.setdefault(parent_idx, []).append(child_idx)

    # Step 2: disaggregate parent total back to the SAME children that
    # rolled up to it. This preserves the parent-total identity exactly
    # and uniformizes per-child values within each group.
    round_tripped: dict[str, float] = {}
    for parent_idx, total in parent_totals.items():
        children = parent_children[parent_idx]
        shares = split_uniformly(total, len(children))
        for child_idx, share in zip(children, shares, strict=True):
            round_tripped[child_idx] = share

    return round_tripped, parent_totals


__all__ = ["rollup_then_disaggregate"]
