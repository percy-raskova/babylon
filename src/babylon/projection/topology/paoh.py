"""The PAOH ordering provider — community/hyperedge projection to a
deterministic node/edge ordering (WO-30, Lane T).

Design canon S9 (``ai/_inbox/tui/20260719archiveinterfacedesign.md``):
"PAOH (nodes as rows, hyperedges as columns ordered by formation tick,
membership dots joined by vertical segments — needs an *ordering*, not a
layout, hence deterministic and snapshot-testable)". The keel already ships
the rendering half of that contract — ``babylon.tui.directives.parse_paoh_body``
(fence-body text -> nodes/edges) and ``render_paoh`` (nodes/edges -> matrix
markup) — this module supplies the other half: **deriving** that ordering
from real projection data (:class:`~babylon.projection.view_models.CommunityView`,
WO-24) instead of a hand-typed fence body.

Transport-neutral by construction, matching every other module in this
package: no Textual, no persistence, no engine import — pure functions over
already-projected :class:`CommunityView` dossiers.

**``formation_tick`` reality check (read before extending this module):**
:attr:`CommunityView.formation_tick` has **no producer today** — neither
``CommunityState`` nor ``CommunityMembership`` carries a timestamp field, so
every dossier a live game produces carries ``formation_tick=None`` (see the
field's own docstring in ``view_models.py`` and
``babylon.projection.community``'s module docstring for the full accounting).
This module carries that absence through honestly rather than fabricating a
tick: an edge with no ``formation_tick`` sorts after every ticked edge
(:func:`paoh_ordering`) and is omitted from a rendered ``{paoh}`` fence body
(:func:`format_paoh_fence_body`) — the fence grammar's per-line label is a
mandatory integer tick, so there is no honest "unknown tick" slot to render
it into (mirrors ``ea_choropleth_cells``' "no producer, return absence"
discipline in the sibling ``choropleth`` module, applied at edge granularity
instead of at the whole-view granularity).
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.enums import CommunityType
from babylon.projection.view_models import CommunityView

__all__ = ["PaohEdge", "format_paoh_fence_body", "paoh_ordering"]


class PaohEdge(BaseModel):
    """One community projected as a PAOH hyperedge column.

    :param community_id: The :class:`~babylon.models.enums.CommunityType`
        this hyperedge represents.
    :param formation_tick: The tick this hyperedge formed, or ``None`` when
        unavailable — :attr:`CommunityView.formation_tick` is always
        ``None`` today (no producer; see the module docstring). Carried as
        ``Optional`` rather than defaulted to a fabricated tick.
    :param members: The community's roster at projection time, as a
        frozenset — matches the edge-member shape
        :func:`babylon.tui.directives.parse_paoh_body` already parses.
        ``min_length=1``: a hyperedge with zero members is not a hyperedge
        (:func:`paoh_ordering` never constructs one from an unattributed
        or empty roster).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    community_id: CommunityType
    formation_tick: int | None = None
    members: frozenset[str] = Field(min_length=1)


def paoh_ordering(
    community_views: Sequence[CommunityView],
) -> tuple[tuple[str, ...], tuple[PaohEdge, ...]]:
    """Derive a deterministic PAOH node/edge ordering from community dossiers.

    Every attributed dossier (:attr:`CommunityView.roster` not ``None``/empty)
    becomes one :class:`PaohEdge` column; an unattributed dossier contributes
    no node and no edge (III.11 — absence is not a zero-member hyperedge).

    :param community_views: One dossier per community to plot. Order does
        not matter — both returned sequences are independently sorted, so
        feeding this function the same dossiers in a different order
        produces byte-identical output (mirrors
        ``choropleth.county_choropleth_cells``' "sorted regardless of input
        order" discipline).
    :returns: ``(nodes_in_order, edges_sorted_by_formation_tick)``.
        ``nodes_in_order`` is the union of every attributed roster, sorted
        lexicographically by member id — an explicit, content-derived row
        order (III.13), not the accidental order communities were passed in.
        ``edges_sorted_by_formation_tick`` is ascending by
        :attr:`PaohEdge.formation_tick`, ``None`` sorted last (every
        real dossier today — see the module docstring); ties (including
        every ``None`` against every other ``None``) break on
        :attr:`PaohEdge.community_id`, the taxonomy's own stable string
        value, so the ordering is total and reproducible even when no
        dossier has a formation tick at all.
    """
    node_set: set[str] = set()
    edges: list[PaohEdge] = []
    for view in community_views:
        if not view.roster:
            continue
        node_set.update(view.roster)
        edges.append(
            PaohEdge(
                community_id=view.community_id,
                formation_tick=view.formation_tick,
                members=frozenset(view.roster),
            )
        )

    nodes_in_order = tuple(sorted(node_set))
    edges_sorted_by_formation_tick = tuple(
        sorted(
            edges,
            key=lambda edge: (
                edge.formation_tick is None,
                edge.formation_tick if edge.formation_tick is not None else 0,
                edge.community_id,
            ),
        )
    )
    return nodes_in_order, edges_sorted_by_formation_tick


def format_paoh_fence_body(nodes: Sequence[str], edges: Sequence[PaohEdge]) -> str:
    """Render a :func:`paoh_ordering` result as ``{paoh}`` fence-body text.

    The output is exactly the line-oriented grammar
    :func:`babylon.tui.directives.parse_paoh_body` parses (``nodes: ...``
    then one ``<tick>: <members>`` line per ticked edge) — this is the
    "wire the ordering into a real page fixture" seam the WO names: a
    caller embeds this text inside a ` ```{paoh}` ... ``` ` fence and the
    existing, already-tested keel directive renders it unchanged.

    :param nodes: Row labels in display order — normally ``paoh_ordering``'s
        first return value.
    :param edges: Columns in display order — normally ``paoh_ordering``'s
        second return value. Edges whose :attr:`PaohEdge.formation_tick` is
        ``None`` are honestly **omitted**, never assigned a fabricated tick:
        the fence grammar's column label is a mandatory integer, and there
        is no producer for that integer today (see the module docstring).
        Order among the surviving edges is preserved from ``edges`` as
        passed — pass ``paoh_ordering``'s already-tick-sorted output to keep
        that guarantee.
    :returns: The fence-body text. A member frozenset is serialized sorted,
        so the same edge always renders the same member list regardless of
        the frozenset's internal iteration order.
    """
    lines = [f"nodes: {', '.join(nodes)}"]
    lines += [
        f"{edge.formation_tick}: {', '.join(sorted(edge.members))}"
        for edge in edges
        if edge.formation_tick is not None
    ]
    return "\n".join(lines)
