"""Composition algebra for oppositions: the ⊗ (product) and ⊕ (sum) combinators.

Composition operates at the **binding** level. Each combinator takes two
:class:`~babylon.domain.dialectics.core.opposition.BoundOpposition` components and
returns a new binding whose measure is a pure function of the component
measures *re-run on the same inputs* — never of their post-step states. This
keeps composites ordinary bindings (their states are ordinary
:class:`~babylon.domain.dialectics.core.opposition.OppositionState` rows), makes
re-measure idempotent, and imposes zero ordering dependency on the registry.

Two combinators, with their ratified bound laws (see
``tests/property/dialectics/test_composition_laws.py``):

- :func:`product` — D1 ⊗ D2, "sharp only if BOTH are sharp":
  ``gap = gap1 * gap2``. **Law: gap(⊗) ≤ min(gap1, gap2).**
- :func:`sum_` — D1 ⊕ D2, "either develops":
  ``gap = gap1 + gap2 − gap1·gap2`` (probabilistic OR).
  **Law: gap(⊕) ≥ max(gap1, gap2).**

Both share one balance rule — the **gap-weighted mean** of the component
balances (0 when both gaps are 0) — so the composite dominance is dragged
toward whichever component is currently sharper. The returned spec carries
composition provenance (``composition`` + ``component_keys``) stamped from the
components, so a composite is always traceable to its parts.

See Also:
    :class:`babylon.domain.dialectics.core.opposition.OppositionRegistry`: steps
    composites exactly like atomic bindings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.domain.dialectics.core.opposition import BoundOpposition, GapReading

if TYPE_CHECKING:
    from babylon.domain.dialectics.core.opposition import OppositionSpec

__all__ = ["product", "sum_"]


def _gap_weighted_balance(r1: GapReading, r2: GapReading) -> float:
    """Mean of the two balances weighted by each component's gap.

    Returns 0.0 when both gaps are 0 (no measurable dominance either way).
    The result is a convex combination of two values in [-1, 1], hence itself
    in [-1, 1]; it is clamped only to absorb floating-point rounding.
    """
    total = r1.gap + r2.gap
    if total == 0.0:
        return 0.0
    balance = (r1.gap * r1.balance + r2.gap * r2.balance) / total
    return max(-1.0, min(1.0, balance))


def product[I](
    spec: OppositionSpec,
    d1: BoundOpposition[I],
    d2: BoundOpposition[I],
) -> BoundOpposition[I]:
    """Compose two oppositions conjunctively (D1 ⊗ D2).

    The composite is sharp only when both components are sharp:
    ``gap = gap1 * gap2``, with the gap-weighted-mean balance. The returned
    spec is stamped with ``composition="product"`` and ``component_keys``
    drawn from ``d1`` and ``d2``.

    Args:
        spec: Identity of the composite (its own key, poles, unity).
        d1: The first component binding.
        d2: The second component binding.

    Returns:
        A new :class:`BoundOpposition` whose measure re-runs both components.

    Example:
        >>> from babylon.domain.dialectics.core.opposition import (
        ...     BoundOpposition, GapReading, OppositionSpec)
        >>> def m(g, b):
        ...     return lambda _inp: GapReading(gap=g, balance=b)
        >>> a = BoundOpposition(OppositionSpec(key="a", pole_a="x", pole_b="y"), m(0.6, 0.2))
        >>> b = BoundOpposition(OppositionSpec(key="b", pole_a="x", pole_b="y"), m(0.5, -0.4))
        >>> spec = OppositionSpec(key="ab", pole_a="x", pole_b="y")
        >>> product(spec, a, b).measure(None).gap
        0.3
    """
    stamped = spec.model_copy(
        update={"composition": "product", "component_keys": (d1.spec.key, d2.spec.key)}
    )

    def measure(inputs: I) -> GapReading:
        r1 = d1.measure(inputs)
        r2 = d2.measure(inputs)
        return GapReading(gap=r1.gap * r2.gap, balance=_gap_weighted_balance(r1, r2))

    return BoundOpposition(spec=stamped, measure=measure)


def sum_[I](
    spec: OppositionSpec,
    d1: BoundOpposition[I],
    d2: BoundOpposition[I],
) -> BoundOpposition[I]:
    """Compose two oppositions disjunctively (D1 ⊕ D2).

    Either component developing sharpens the composite:
    ``gap = gap1 + gap2 − gap1·gap2`` (probabilistic OR, equivalently
    ``1 − (1 − gap1)(1 − gap2)``), with the gap-weighted-mean balance. The
    returned spec is stamped with ``composition="sum"`` and ``component_keys``.

    Args:
        spec: Identity of the composite (its own key, poles, unity).
        d1: The first component binding.
        d2: The second component binding.

    Returns:
        A new :class:`BoundOpposition` whose measure re-runs both components.

    Example:
        >>> from babylon.domain.dialectics.core.opposition import (
        ...     BoundOpposition, GapReading, OppositionSpec)
        >>> def m(g, b):
        ...     return lambda _inp: GapReading(gap=g, balance=b)
        >>> a = BoundOpposition(OppositionSpec(key="a", pole_a="x", pole_b="y"), m(0.6, 0.2))
        >>> b = BoundOpposition(OppositionSpec(key="b", pole_a="x", pole_b="y"), m(0.5, -0.4))
        >>> spec = OppositionSpec(key="ab", pole_a="x", pole_b="y")
        >>> round(sum_(spec, a, b).measure(None).gap, 2)
        0.8
    """
    stamped = spec.model_copy(
        update={"composition": "sum", "component_keys": (d1.spec.key, d2.spec.key)}
    )

    def measure(inputs: I) -> GapReading:
        r1 = d1.measure(inputs)
        r2 = d2.measure(inputs)
        # Stable factoring of g1 + g2 − g1·g2: multiplying two factors ≤ 1
        # never rounds up, so ``1 − (1−g1)(1−g2) ≥ max(g1, g2)`` holds exactly
        # in IEEE-754 (the naive difference can cancel a hair below max).
        gap = 1.0 - (1.0 - r1.gap) * (1.0 - r2.gap)
        return GapReading(gap=gap, balance=_gap_weighted_balance(r1, r2))

    return BoundOpposition(spec=stamped, measure=measure)
