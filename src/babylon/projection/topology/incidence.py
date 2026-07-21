"""Incidence/adjacency matrix ordering provider over the WO-24 community
projection shape (WO-32, Lane T).

Design canon S9 ("incidence/adjacency matrices — making I.21's
centrality/singleton/cutset targeting modes legible") and Constitution I.21
(the Sparrow three-targeting-modes framework: **centrality** — hubs and
critical nodes; **singletons** — isolated targets; **cutsets** — bridges and
bottlenecks). This module makes those three shapes *visible* — it computes
no centrality score, detects no cutset, and defines no targeting mechanic
(that is out of this WO's scope, per its own "READ-ONLY, no targeting
mechanics" ruling); it only orders and lays out the raw incidence/adjacency
data so a human (or a later Sparrow implementation) can see hubs, isolates,
and bridges by eye.

Transport-neutral by construction, mirroring :mod:`babylon.projection.community`
and :mod:`babylon.projection.topology.choropleth`: no Textual, no database
connection. Input is a sequence of already-projected
:class:`~babylon.projection.view_models.CommunityView` dossiers (WO-24's
shape) — this module never re-derives roster/membership itself.

**Deterministic ordering (III.13), explicit, not incidental:**

.. list-table:: Ordering rules
   :header-rows: 1

   * - Axis
     - Rule
   * - Nodes (rows, both matrices)
     - The sorted union of every attributed view's ``roster`` — lexicographic
       string sort, the same convention :func:`~babylon.projection.community.
       project_community` itself uses for one roster.
   * - Hyperedges (columns, incidence only)
     - The attributed views' ``community_id`` values, sorted lexicographically
       (:class:`~babylon.models.enums.CommunityType` is a ``StrEnum`` and
       compares as its string value directly). There is no formation-tick to
       sort by here (unlike PAOH, WO-30) — ``CommunityView.formation_tick``
       is always ``None`` today (no hyperedge lifecycle exists;
       ``community.py``'s own docstring records this fact) — so an
       alphabetic column order is the honest, explicit choice, not a
       placeholder for a richer one.

**Honest absence, not a fabricated matrix:** a :class:`~babylon.projection.
view_models.CommunityView` with ``roster is None`` (no producer attributed —
today, that is *every* community, since ``CommunitySystem.step`` is a
structural no-op; see ``community.py``'s "No producer exists today" note) is
excluded entirely from both matrices — it contributes no row candidates and
no hyperedge column. A run with zero attributed communities projects an
honestly empty :class:`IncidenceMatrix`/:class:`AdjacencyMatrix`
(``nodes == ()``), never a fabricated all-absent grid.

**One producer per field:**

.. list-table:: Field-producer rulings
   :header-rows: 1

   * - Field
     - Producer
   * - ``IncidenceMatrix.cells[r][c]``
     - ``True`` iff ``nodes[r]`` appears in the ``c``-th (sorted) attributed
       view's ``roster`` — direct membership, no derived weighting.
   * - ``AdjacencyMatrix.cells[i][j]``
     - ``True`` iff ``i != j`` and ``nodes[i]``/``nodes[j]`` co-occur in at
       least one attributed community's ``roster`` (co-membership adjacency).
       The diagonal (``i == j``) is always ``False`` — self-adjacency is not
       a meaningful quantity here, not a computed "0 shared communities."

**Same-shape producers, two call sites (deliberate, not accidental
duplication):** :func:`incidence_ordering`/:func:`adjacency_ordering` derive
:class:`IncidenceMatrix`/:class:`AdjacencyMatrix` from live
:class:`~babylon.projection.view_models.CommunityView` data (this module's
own job — the "ordering provider" WO-32 names). ``babylon.tui.directives``
parses the *identical* two model shapes directly out of a baked ``{matrix}``
fence body (mirroring how ``parse_maproom_body`` builds
:class:`~babylon.projection.topology.choropleth.ChoroplethCell` instances
straight from text) — a baked page never re-runs this module's projection
logic, it carries its own numbers (III.13: a materialized view renders from
its own bytes). Sharing one Pydantic contract between the two producers,
rather than inventing a second ad hoc shape for the fence-body path, is what
keeps that duplication honest.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, model_validator

from babylon.models.enums import CommunityType

if TYPE_CHECKING:
    from babylon.projection.view_models import CommunityView

__all__ = [
    "IncidenceMatrix",
    "AdjacencyMatrix",
    "incidence_ordering",
    "adjacency_ordering",
]


class IncidenceMatrix(BaseModel):
    """A node x hyperedge incidence grid, in explicit deterministic order.

    :param nodes: Row labels (``SocialClass`` ids), sorted lexicographically.
    :param hyperedges: Column labels, sorted lexicographically. Empty exactly
        when :attr:`nodes` is empty (honest absence — no attributed
        community data at all), never populated with a phantom all-``False``
        column.
    :param cells: Row-major membership grid — ``cells[r][c]`` is ``True`` iff
        ``nodes[r]`` belongs to ``hyperedges[c]``. ``len(cells) ==
        len(nodes)`` and every row's length equals ``len(hyperedges)``,
        enforced below rather than left to caller discipline.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    nodes: tuple[str, ...]
    hyperedges: tuple[CommunityType, ...]
    cells: tuple[tuple[bool, ...], ...]

    @model_validator(mode="after")
    def _validate_shape(self) -> IncidenceMatrix:
        """Require the grid's declared shape to actually hold.

        :raises ValueError: if ``cells`` has a different row count than
            :attr:`nodes`, or any row's length differs from
            ``len(hyperedges)`` — a malformed grid is a bug, never a
            silently-truncated or padded one.
        :returns: The validated model (unchanged).
        """
        if len(self.cells) != len(self.nodes):
            msg = f"{len(self.cells)} row(s) for {len(self.nodes)} node(s)"
            raise ValueError(msg)
        for row in self.cells:
            if len(row) != len(self.hyperedges):
                msg = f"row of length {len(row)} for {len(self.hyperedges)} hyperedge(s)"
                raise ValueError(msg)
        return self


class AdjacencyMatrix(BaseModel):
    """A node x node co-membership adjacency grid, in explicit deterministic order.

    :param nodes: Row/column labels, sorted lexicographically — the same
        node set and order :class:`IncidenceMatrix` would produce from the
        same input.
    :param cells: Row-major, symmetric adjacency grid — ``cells[i][j]`` is
        ``True`` iff ``i != j`` and the two nodes share at least one
        attributed community. The diagonal is always ``False``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    nodes: tuple[str, ...]
    cells: tuple[tuple[bool, ...], ...]

    @model_validator(mode="after")
    def _validate_shape(self) -> AdjacencyMatrix:
        """Require a square grid, symmetric, with a clear diagonal.

        :raises ValueError: if ``cells`` is not ``len(nodes)`` square, or any
            diagonal cell is ``True``, or the grid is not symmetric — any of
            these is a malformed adjacency grid, never silently accepted.
        :returns: The validated model (unchanged).
        """
        n = len(self.nodes)
        if len(self.cells) != n:
            msg = f"{len(self.cells)} row(s) for {n} node(s)"
            raise ValueError(msg)
        for row_index, row in enumerate(self.cells):
            if len(row) != n:
                msg = f"row of length {len(row)} for {n} node(s)"
                raise ValueError(msg)
            if row[row_index]:
                msg = f"diagonal cell [{row_index}][{row_index}] must be False"
                raise ValueError(msg)
        for i in range(n):
            for j in range(n):
                if self.cells[i][j] != self.cells[j][i]:
                    msg = f"adjacency is not symmetric at ({i}, {j})"
                    raise ValueError(msg)
        return self


def _attributed(community_views: Sequence[CommunityView]) -> list[CommunityView]:
    """Keep only views with a real (non-``None``) roster, sorted by ``community_id``.

    :param community_views: The candidate dossiers.
    :raises ValueError: if two views name the same ``community_id`` — a
        caller error (ambiguous which is "the" incidence data for that
        hyperedge), never silently resolved by picking one.
    :returns: The attributed subset, sorted lexicographically by
        ``community_id``.
    """
    attributed = [view for view in community_views if view.roster]
    ids = [view.community_id for view in attributed]
    if len(set(ids)) != len(ids):
        msg = f"duplicate community_id in input: {sorted(cid for cid in ids if ids.count(cid) > 1)}"
        raise ValueError(msg)
    return sorted(attributed, key=lambda view: view.community_id)


def incidence_ordering(community_views: Sequence[CommunityView]) -> IncidenceMatrix:
    """Derive the deterministic node x hyperedge incidence matrix.

    :param community_views: Projected community dossiers (WO-24's
        :func:`~babylon.projection.community.project_community` output),
        any order — this function does its own sorting.
    :raises ValueError: propagated from :class:`IncidenceMatrix`'s
        validators, or from a duplicate ``community_id`` in the input.
    :returns: The incidence matrix — honestly empty (``nodes == ()``) when no
        view carries an attributed roster.
    """
    attributed = _attributed(community_views)
    hyperedges = tuple(view.community_id for view in attributed)
    nodes = tuple(sorted({member for view in attributed for member in view.roster or ()}))
    cells = tuple(tuple(node in (view.roster or ()) for view in attributed) for node in nodes)
    return IncidenceMatrix(nodes=nodes, hyperedges=hyperedges, cells=cells)


def adjacency_ordering(community_views: Sequence[CommunityView]) -> AdjacencyMatrix:
    """Derive the deterministic node x node co-membership adjacency matrix.

    Reuses :func:`incidence_ordering` for the node order and per-hyperedge
    membership, then folds each hyperedge's members into a pairwise
    co-adjacency (two nodes are adjacent iff they share at least one
    attributed community) — never a re-derivation of roster data from
    scratch, so the two matrices' node order is guaranteed identical for the
    same input.

    :param community_views: Projected community dossiers, any order.
    :raises ValueError: propagated from :func:`incidence_ordering` or
        :class:`AdjacencyMatrix`'s validators.
    :returns: The adjacency matrix — honestly empty (``nodes == ()``) when no
        view carries an attributed roster.
    """
    incidence = incidence_ordering(community_views)
    n = len(incidence.nodes)
    adjacent = [[False] * n for _ in range(n)]
    for column in range(len(incidence.hyperedges)):
        members = [row for row in range(n) if incidence.cells[row][column]]
        for i in members:
            for j in members:
                if i != j:
                    adjacent[i][j] = True
    cells = tuple(tuple(row) for row in adjacent)
    return AdjacencyMatrix(nodes=incidence.nodes, cells=cells)
