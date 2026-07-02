"""Adjoint cylinders: Lawvere's unity and identity of opposites.

An adjoint cylinder is an adjoint string :math:`i_! \\dashv i^* \\dashv i_*`
where both outer functors are fully faithful: two OPPOSITE ways of
embedding a base ``S`` into an ambient ``X``, unified by one projection.
The classic instance is Lawvere's cohesion fragment
discrete ⊣ points ⊣ codiscrete; Babylon's Phase-B instance is the
connectivity cylinder — atomized ⊣ individuals ⊣ total-unity over the
solidarity graph. (The word "cohesion" is deliberately avoided in this
package: it already means organizational cohesion elsewhere in Babylon.)

The two induced modalities are the skeleton comonad
:math:`\\Box = i_! \\circ i^*` (strip to the left pole) and the sheaf
monad :math:`\\bigcirc = i_* \\circ i^*` (complete to the right pole).
Because both embeddings section the same projection, the modal laws

.. math::

    \\Box\\Box = \\Box,\\quad \\bigcirc\\bigcirc = \\bigcirc,\\quad
    \\Box\\bigcirc = \\Box,\\quad \\bigcirc\\Box = \\bigcirc

hold exactly, and every ambient object sits in its own interval
:math:`\\Box x \\to x \\to \\bigcirc x`. The :meth:`balance` of ``x`` is
its measured position in that interval — for the connectivity instance,
0 is full atomization and 1 is the unity pole, so the position of the
social graph in its own adjoint interval IS the state of the struggle.

See Also:
    :class:`babylon.dialectics.core.level.LevelLattice`: orders many
    skeleton/sheaf pairs into levels with an Aufhebung operator.
"""

from __future__ import annotations

from collections.abc import Callable

__all__ = ["AdjointCylinder"]


def _default_eq(a: object, b: object) -> bool:
    """Structural equality fallback for the base carrier."""
    return bool(a == b)


class AdjointCylinder[S, X]:
    """Two opposite embeddings of a base carrier, unified by a projection.

    Args:
        embed_left: :math:`i_!` — the left-pole embedding ``S -> X``
            (e.g. the fully atomized graph on a node set).
        project: :math:`i^*` — the common projection ``X -> S``
            (e.g. the underlying node set).
        embed_right: :math:`i_*` — the right-pole embedding ``S -> X``
            (e.g. the complete graph on a node set).
        metric: A distance ``X × X -> float`` used to measure position
            inside the interval. Must satisfy ``metric(x, x) == 0`` and
            non-negativity; law tests enforce the consequences.
        eq_base: Equality on ``S`` used by :meth:`retracts`.

    Example:
        >>> cyl = AdjointCylinder(
        ...     embed_left=lambda s: (s, "left"),
        ...     project=lambda x: x[0],
        ...     embed_right=lambda s: (s, "right"),
        ...     metric=lambda a, b: float(a != b),
        ... )
        >>> cyl.retracts(42)
        True
    """

    def __init__(
        self,
        embed_left: Callable[[S], X],
        project: Callable[[X], S],
        embed_right: Callable[[S], X],
        metric: Callable[[X, X], float],
        eq_base: Callable[[S, S], bool] = _default_eq,
    ) -> None:
        self._embed_left = embed_left
        self._project = project
        self._embed_right = embed_right
        self._metric = metric
        self._eq_base = eq_base

    def skeleton(self, x: X) -> X:
        """The comonad :math:`\\Box x = i_!(i^*(x))` — strip to the left pole."""
        return self._embed_left(self._project(x))

    def sheaf(self, x: X) -> X:
        """The monad :math:`\\bigcirc x = i_*(i^*(x))` — complete to the right pole."""
        return self._embed_right(self._project(x))

    def span(self, x: X) -> float:
        """The width of ``x``'s interval: ``metric(□x, ○x)``.

        Returns:
            Zero exactly when the two poles coincide over ``x``'s base.
        """
        return self._metric(self.skeleton(x), self.sheaf(x))

    def balance(self, x: X) -> float:
        """Position of ``x`` inside its interval :math:`[\\Box x, \\bigcirc x]`.

        Returns:
            ``metric(□x, x) / span(x)`` clamped to [0, 1]; ``0.5`` when
            the interval is degenerate (span 0). For the connectivity
            instance: 0 = fully atomized, 1 = total unity.
        """
        width = self.span(x)
        if width == 0.0:
            return 0.5
        position = self._metric(self.skeleton(x), x) / width
        return min(1.0, max(0.0, position))

    def retracts(self, s: S) -> bool:
        """Full faithfulness check: both embeddings section the projection.

        Args:
            s: A base element.

        Returns:
            True iff ``project(embed_left(s)) == s == project(embed_right(s))``.
        """
        left_ok = self._eq_base(self._project(self._embed_left(s)), s)
        right_ok = self._eq_base(self._project(self._embed_right(s)), s)
        return left_ok and right_ok
