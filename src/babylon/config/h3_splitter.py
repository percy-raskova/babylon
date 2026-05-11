"""Canonical H3 disaggregation rules — spec 060 FR-011 exception.

The codebase uses uniform splitting as a de facto convention across
multiple modules (``infrastructure/r8_mesh.py``,
``economics/substrate/spatial.py``, ``economics/substrate/circulation.py``)
without a single named rule. This module codifies that convention so
spec-060 FR-016 (H3 round-trip conservation) has a single source of
truth to test against.

Future rules (area-weighted, population-weighted, employment-weighted)
can be added as additional ``H3SplitterRule`` members; each must
preserve the conservation invariant ``sum(split(v, n)) == v``.

See:
    specs/060-value-form-invariants/research.md (R1)
    specs/060-value-form-invariants/data-model.md (H3SplitterRule)
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class H3SplitterRule(StrEnum):
    """Canonical H3 disaggregation rules."""

    UNIFORM = "uniform"
    # Future: AREA_WEIGHTED, POPULATION_WEIGHTED, EMPLOYMENT_WEIGHTED


DEFAULT_SPLITTER: Final[H3SplitterRule] = H3SplitterRule.UNIFORM


def split_uniformly(parent_value: float, n_children: int) -> list[float]:
    """Split a parent quantity equally among ``n_children`` children.

    Conserves total exactly for the reduction (``sum(result) ==
    parent_value`` within float epsilon) by emitting equal shares.

    Args:
        parent_value: The quantity to split.
        n_children: The number of children (positive integer).
            For an H3 cell at resolution R, the typical value is 7 (one
            finer resolution).

    Returns:
        A list of ``n_children`` floats each equal to
        ``parent_value / n_children``.

    Raises:
        ValueError: If ``n_children < 1``.
    """
    if n_children < 1:
        raise ValueError(f"n_children must be >= 1, got {n_children}")
    share = parent_value / n_children
    return [share] * n_children


__all__ = ["H3SplitterRule", "DEFAULT_SPLITTER", "split_uniformly"]
