"""Contradiction gap formulas for the Babylon simulation.

The Lawverian rewrite (Phase C) replaces the saturating, dollar-scale
tension accumulator with **scale-free** wealth-asymmetry gaps recomputed
fresh from current state every tick. The contradiction *is* the current
relation between two poles: :func:`calculate_wealth_asymmetry_gap` reports
how far the relation is from closure (0 = parity, 1 = one pole holds
everything) and :func:`calculate_wealth_asymmetry_balance` reports which
pole dominates. Because both divide by the pole sum, they are invariant
under a change of monetary numeraire (dollars vs. cents) by construction.

The older :func:`calculate_contradiction_intensity` — which fed a raw
dollar-scale divergence into a ``[0, 1]`` clamp and therefore pinned at
1.0 on any real wealth gap — is retained only for the deprecation window.
"""

from __future__ import annotations


def calculate_wealth_asymmetry_gap(
    wealth_a: float,
    wealth_b: float,
    epsilon: float = 1e-9,
) -> float:
    r"""Scale-free distance of a two-pole wealth relation from closure.

    The gap is the normalized absolute difference of the two poles'
    wealth, :math:`|W_b - W_a| / (W_a + W_b)`, clamped to ``[0, 1]``:
    ``0`` when the poles are at parity (the contradiction is resolved),
    approaching ``1`` as one pole holds all the wealth. Dividing by the
    pole sum makes it a pure number — multiplying both wealths by any
    ``k > 0`` (a change of monetary numeraire) leaves it unchanged.

    ``epsilon`` guards ONLY the degenerate all-zero case (both poles
    empty); it is deliberately NOT added into the ratio, so the measure
    stays *exactly* numeraire-invariant rather than invariant-up-to-epsilon
    (this is the difference that lets the property test hold to 1e-12).

    Args:
        wealth_a: Wealth of pole A (non-negative).
        wealth_b: Wealth of pole B (non-negative).
        epsilon: Zero-guard threshold on the pole sum; below it the gap is
            ``0.0`` (an empty relation has no measurable contradiction).

    Returns:
        The asymmetry gap in ``[0, 1]``; ``0.0`` when both poles are empty.

    Example:
        >>> calculate_wealth_asymmetry_gap(10.0, 30.0)
        0.5
        >>> calculate_wealth_asymmetry_gap(0.0, 0.0)
        0.0
        >>> round(calculate_wealth_asymmetry_gap(1.0, 3.0), 6) == round(
        ...     calculate_wealth_asymmetry_gap(1000.0, 3000.0), 6)
        True

    See Also:
        :func:`calculate_wealth_asymmetry_balance`: the signed counterpart.
    """
    total = wealth_a + wealth_b
    if total <= epsilon:
        return 0.0
    gap = abs(wealth_b - wealth_a) / total
    return min(1.0, max(0.0, gap))


def calculate_wealth_asymmetry_balance(
    wealth_a: float,
    wealth_b: float,
    epsilon: float = 1e-9,
) -> float:
    r"""Signed dominance of pole B over pole A, in ``[-1, 1]``.

    The signed counterpart of :func:`calculate_wealth_asymmetry_gap`:
    :math:`(W_b - W_a) / (W_a + W_b)`, clamped to ``[-1, 1]``. Positive
    means pole B (by convention the richer/target side) dominates;
    negative means pole A dominates; ``0`` is parity. Its magnitude equals
    the gap. Like the gap it is exactly numeraire-invariant.

    Args:
        wealth_a: Wealth of pole A (non-negative).
        wealth_b: Wealth of pole B (non-negative).
        epsilon: Zero-guard threshold on the pole sum; below it the balance
            is ``0.0``.

    Returns:
        The signed balance in ``[-1, 1]``; ``0.0`` when both poles are empty.

    Example:
        >>> calculate_wealth_asymmetry_balance(10.0, 30.0)
        0.5
        >>> calculate_wealth_asymmetry_balance(30.0, 10.0)
        -0.5

    See Also:
        :func:`calculate_wealth_asymmetry_gap`: the unsigned magnitude.
    """
    total = wealth_a + wealth_b
    if total <= epsilon:
        return 0.0
    balance = (wealth_b - wealth_a) / total
    return min(1.0, max(-1.0, balance))


def calculate_contradiction_intensity(
    divergence: float,
    centrality_a: float,
    centrality_b: float,
    sensitivity: float = 1.0,
) -> float:
    """Calculate the emergent intensity of a contradiction edge.

    .. deprecated:: spec-lawverian-C1
        Superseded by :func:`calculate_wealth_asymmetry_gap`. This function
        fed a raw dollar-scale ``divergence`` into a ``[0, 1]`` clamp, which
        saturated to ``1.0`` on any real wealth gap and carried no
        information (the four-inertness-bugs "Formula" defect). Retained for
        the deprecation window; no production caller remains after Phase C.

    Combines raw dialectical divergence (e.g. wealth gap, ideological distance)
    with the topological importance of the entities involved, scaling the
    divergence magnitude by their hypergraph centrality or degree.

    Formula:
        intensity = divergence * (1 + sqrt(Centrality_a * Centrality_b)) * sensitivity
        Bound to [0.0, 1.0]

    Args:
        divergence: Raw difference between node states (typically [0, 1]).
        centrality_a: Network/Hypergraph centrality of node A (typically [0, 1]).
        centrality_b: Network/Hypergraph centrality of node B (typically [0, 1]).
        sensitivity: System or definition-level scaling factor.

    Returns:
        Intensity scalar bounded [0.0, 1.0].

    Example:
        >>> calculate_contradiction_intensity(0.5, 0.8, 0.2, 1.0)
        0.7...
    """
    if divergence < 0.0:
        msg = "divergence must be non-negative"
        raise ValueError(msg)
    if centrality_a < 0.0 or centrality_b < 0.0:
        msg = "centralities must be non-negative"
        raise ValueError(msg)
    if sensitivity < 0.0:
        msg = "sensitivity must be non-negative"
        raise ValueError(msg)

    scale_factor = 1.0 + (centrality_a * centrality_b) ** 0.5
    raw_intensity = divergence * scale_factor * sensitivity

    return min(1.0, max(0.0, float(raw_intensity)))
