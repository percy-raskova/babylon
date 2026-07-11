"""Galois connections: adjunctions between preorders.

The smallest fully executable form of Lawvere's thesis that "the main
pairs of opposing tendencies take the form of adjoint functors"
(Quantifiers and Sheaves, 1970). A Galois connection between preorders
:math:`(P, \\leq_P)` and :math:`(Q, \\leq_Q)` is a pair of monotone maps
``lower: P -> Q`` and ``upper: Q -> P`` satisfying the adjointness
biconditional

.. math::

    lower(p) \\leq_Q q \\iff p \\leq_P upper(q)

Every such connection induces a closure operator ``upper ∘ lower`` on
``P`` (the monad of the adjunction: inflationary, idempotent, monotone)
and an interior operator ``lower ∘ upper`` on ``Q`` (the comonad:
deflationary, idempotent, monotone). Lawvere's quantifiers arise this
way: the existential quantifier along a map is left adjoint to
substitution, :math:`\\exists_f \\dashv f^*`.

See Also:
    :class:`babylon.domain.dialectics.core.cylinder.AdjointCylinder`: the
    two-sided (unity-of-opposites) form used for oppositions.
"""

from __future__ import annotations

from collections.abc import Callable

__all__ = ["GaloisConnection"]


class GaloisConnection[P, Q]:
    """An adjunction ``lower ⊣ upper`` between two preorders.

    Args:
        lower: The left adjoint ``P -> Q``.
        upper: The right adjoint ``Q -> P``.
        leq_p: The preorder on ``P``.
        leq_q: The preorder on ``Q``.

    Example:
        >>> gc = GaloisConnection(
        ...     lower=lambda p: p * 3,
        ...     upper=lambda q: q // 3,
        ...     leq_p=lambda a, b: a <= b,
        ...     leq_q=lambda a, b: a <= b,
        ... )
        >>> gc.holds(4, 13)  # 12 <= 13  and  4 <= 4
        True
        >>> gc.closure(4)
        4
    """

    def __init__(
        self,
        lower: Callable[[P], Q],
        upper: Callable[[Q], P],
        leq_p: Callable[[P, P], bool],
        leq_q: Callable[[Q, Q], bool],
    ) -> None:
        self._lower = lower
        self._upper = upper
        self._leq_p = leq_p
        self._leq_q = leq_q

    def lower(self, p: P) -> Q:
        """Apply the left adjoint.

        Args:
            p: An element of the lower preorder.

        Returns:
            Its image in ``Q``.
        """
        return self._lower(p)

    def upper(self, q: Q) -> P:
        """Apply the right adjoint.

        Args:
            q: An element of the upper preorder.

        Returns:
            Its image in ``P``.
        """
        return self._upper(q)

    def holds(self, p: P, q: Q) -> bool:
        """Check the adjointness biconditional at a single pair.

        Args:
            p: An element of ``P``.
            q: An element of ``Q``.

        Returns:
            True iff ``lower(p) ≤ q`` and ``p ≤ upper(q)`` agree —
            law tests assert this for all generated pairs.
        """
        return self._leq_q(self._lower(p), q) == self._leq_p(p, self._upper(q))

    def closure(self, p: P) -> P:
        """The induced monad ``upper(lower(p))`` on ``P``.

        Returns:
            The closure of ``p`` — inflationary, idempotent, monotone.
        """
        return self._upper(self._lower(p))

    def interior(self, q: Q) -> Q:
        """The induced comonad ``lower(upper(q))`` on ``Q``.

        Returns:
            The interior of ``q`` — deflationary, idempotent, monotone.
        """
        return self._lower(self._upper(q))
