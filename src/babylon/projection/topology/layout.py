"""Closed-form deterministic layout for the ``paoh`` topology kind (M4 §1, Task 30).

Design canon S9 stands: the ordering modules (:mod:`~babylon.projection.
topology.paoh`, :mod:`~babylon.projection.topology.levi`, :mod:`~babylon.
projection.topology.incidence`) stay ORDERING providers — none of them
computes a screen position, only a deterministic node/edge/cell sequence.
This module is the one place an ordering becomes an on-screen coordinate,
and it does so with **pure trigonometry over a sorted id list** — never an
iterative/spring solver: float-iteration convergence is a determinism
hazard for zero benefit at these node counts (the M4 topology contract,
``docs/superpowers/specs/2026-07-27-m4-topology-contracts.md`` §1, RULES
this explicitly). rustworkx's own layout functions
(``shell_layout``/``spring_layout``) stay unused for now — closed-form beats
seeded-iterative on the determinism budget; revisit only if a future graph
outgrows the shell (a recorded non-goal, not an oversight).

Only :func:`bipartite_shell_layout` lives here today — the ``paoh`` kind's
own layout. ``egotree``/``incidence``/``adjacency`` are text-grid renderers
with no spatial layout at all (contract §1: "``egotree``/``incidence``/
``adjacency`` carry NO layout — their renderers are text-grid, not
spatial"), so this module defines no layout function for them.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

__all__ = ["bipartite_shell_layout"]

_MEMBER_RADIUS = 1.0
"""The outer ring's fixed radius — hyperedge MEMBER ids (contract §1: "member
nodes on an outer circle (unit radius ...)")."""

_COMMUNITY_RADIUS = 0.45
"""The inner ring's fixed radius — hyperedge COMMUNITY ids (contract §1:
"community nodes on an inner circle (radius 0.45 ...)")."""


def _ring_positions(ids: Iterable[str], *, radius: float) -> dict[str, tuple[float, float]]:
    """One ring's worth of evenly-spaced points on a circle of ``radius``.

    :param ids: the ring's node ids, in any order and with any duplication —
        de-duplicated and sorted lexicographically internally (contract §1:
        "angle = index/len · 2π over the lexicographic order"), so the same
        id SET always produces the same ring regardless of how the caller
        happened to order or repeat it (byte-stable given the same payload).
    :param radius: the ring's fixed radius.
    :returns: ``{id: (x, y)}``. The empty dict for an empty ring — no
        division-by-zero, no fabricated single point.
    """
    ordered = sorted(set(ids))
    count = len(ordered)
    if count == 0:
        return {}
    return {
        node_id: (
            radius * math.cos(2 * math.pi * index / count),
            radius * math.sin(2 * math.pi * index / count),
        )
        for index, node_id in enumerate(ordered)
    }


def bipartite_shell_layout(
    member_ids: Iterable[str], community_ids: Iterable[str]
) -> dict[str, tuple[float, float]]:
    """The ``paoh`` envelope's closed-form bipartite-shell layout (contract §1).

    Member ids sit on an outer unit-radius circle; community ids sit on an
    inner radius-``0.45`` circle; both rings are independently evenly spaced
    over their own sorted order (see :func:`_ring_positions`) — pure
    trigonometry, no iterative/spring solving (see the module docstring).

    :param member_ids: the hyperedge member ids — normally
        :func:`~babylon.projection.topology.paoh.paoh_ordering`'s
        ``nodes_in_order``, any order accepted.
    :param community_ids: the hyperedge community ids — normally the sorted
        ``community_id`` values off :func:`~babylon.projection.topology.
        paoh.paoh_ordering`'s edges, any order accepted.
    :raises ValueError: the same id appears in both ``member_ids`` and
        ``community_ids`` — the Levi graph's two node classes are disjoint by
        construction (:mod:`~babylon.projection.topology.levi`'s own module
        docstring); a collision means a caller mixed the two rings, never a
        silently-overwritten position.
    :returns: ``{id: (x, y)}`` merging both rings — every member AND every
        community id present, matching the ``paoh`` envelope's own "both node
        and community ids present" contract (§1).
    """
    members = _ring_positions(member_ids, radius=_MEMBER_RADIUS)
    communities = _ring_positions(community_ids, radius=_COMMUNITY_RADIUS)
    overlap = members.keys() & communities.keys()
    if overlap:
        msg = f"bipartite_shell_layout: id(s) present in both rings: {sorted(overlap)}"
        raise ValueError(msg)
    return {**members, **communities}
