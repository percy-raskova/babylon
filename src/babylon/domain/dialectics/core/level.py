"""Levels and Aufhebung: quality from quantity, executably.

Lawvere formalizes Hegel's levels as essential subtoposes ordered by
inclusion, each carrying a skeleton/sheaf pair of modalities. The
**Aufhebung** (sublation) of a level ``i`` is the LEAST higher level
``j`` at which the lower opposition is resolved-and-preserved:

.. math::

    \\bigcirc_j(\\Box_i(x)) = \\Box_i(x)

— every ``i``-skeleton is already a ``j``-sheaf. This module implements
the finite, executable fragment: a totally ordered chain of levels with
per-level skeleton/sheaf operators and a probe-based Aufhebung search.
In Babylon the chains are the spatial hierarchy
(hex ≺ county ≺ state ≺ nation) and the social hierarchy
(individual ≺ community ≺ class ≺ bloc); a rupture is a level
transition fired when the resolution condition is met (Phase E).

See Also:
    :class:`babylon.domain.dialectics.core.cylinder.AdjointCylinder`: supplies
    skeleton/sheaf pairs for a single opposition.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["Level", "LevelLattice", "LevelOperators"]


class Level(BaseModel):
    """A named rung in a level chain.

    Example:
        >>> Level(index=1, name="county").name
        'county'
    """

    index: int = Field(..., ge=0, description="Position in the chain; higher = coarser")
    name: str = Field(..., min_length=1, description="Human-readable level name")

    model_config = ConfigDict(frozen=True, extra="forbid")


@dataclass(frozen=True)
class LevelOperators[X]:
    """The skeleton/sheaf modality pair carried by one level."""

    skeleton: Callable[[X], X]
    sheaf: Callable[[X], X]


class LevelLattice[X]:
    """A totally ordered chain of levels with an Aufhebung operator.

    Args:
        levels: The chain, with strictly increasing ``index`` values.
        operators: A skeleton/sheaf pair for every level index.
        eq: Equality on the ambient carrier, used by the resolution test.

    Raises:
        ValueError: If the chain is empty, indices are not strictly
            increasing, or any level lacks operators.
    """

    def __init__(
        self,
        levels: Sequence[Level],
        operators: Mapping[int, LevelOperators[X]],
        eq: Callable[[X, X], bool],
    ) -> None:
        if not levels:
            raise ValueError("LevelLattice requires at least one level")
        indices = [level.index for level in levels]
        if any(a >= b for a, b in zip(indices, indices[1:], strict=False)):
            raise ValueError(f"level indices must be strictly increasing, got {indices}")
        missing = [i for i in indices if i not in operators]
        if missing:
            raise ValueError(f"missing operator pair for level indices {missing}")
        self._levels: tuple[Level, ...] = tuple(levels)
        self._operators: dict[int, LevelOperators[X]] = dict(operators)
        self._eq = eq

    @property
    def levels(self) -> tuple[Level, ...]:
        """The chain, lowest first."""
        return self._levels

    def _require(self, index: int) -> LevelOperators[X]:
        ops = self._operators.get(index)
        if ops is None:
            raise ValueError(f"unknown level index {index}")
        return ops

    def is_resolved_at(self, x: X, lower: int, higher: int) -> bool:
        """Lawvere's resolution condition for one probe.

        Args:
            x: The probe object.
            lower: Index of the level whose opposition is tested.
            higher: Index of the candidate resolving level.

        Returns:
            True iff ``sheaf_higher(skeleton_lower(x)) == skeleton_lower(x)``
            — the lower skeleton is already closed at the higher level.

        Raises:
            ValueError: If either index is unknown or ``lower >= higher``.
        """
        if lower >= higher:
            raise ValueError(f"lower index {lower} must be below higher index {higher}")
        low_ops = self._require(lower)
        high_ops = self._require(higher)
        fixed = low_ops.skeleton(x)
        return self._eq(high_ops.sheaf(fixed), fixed)

    def aufhebung_of(self, lower: int, probes: Sequence[X]) -> Level | None:
        """The least level above ``lower`` resolving it on every probe.

        Args:
            lower: Index of the level being sublated.
            probes: Non-empty sample of ambient objects to test against.

        Returns:
            The least resolving :class:`Level`, or None if no higher
            level resolves all probes (the opposition is antagonistic
            relative to this chain).

        Raises:
            ValueError: If ``lower`` is unknown or ``probes`` is empty.
        """
        self._require(lower)
        if not probes:
            raise ValueError("aufhebung_of requires at least one probe")
        for level in self._levels:
            if level.index <= lower:
                continue
            if all(self.is_resolved_at(p, lower, level.index) for p in probes):
                return level
        return None
