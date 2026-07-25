"""The faction read-model — ``project_faction``, Program 24 T3 U4.

Assembles a :class:`~babylon.projection.view_models.FactionView` dossier from
the post-tick graph's ``faction`` node (spec-070). Faction is the political
coalition a sovereign's ``ruling_faction_id`` names
(:mod:`babylon.projection.sovereign`) and the source of every INFLUENCES edge
contesting a territory; this module is what makes a sovereign page's
``ruling_faction_id`` resolvable to a real page, plus the forward direction —
every territory this faction influences, with its edge weight and channel.

Transport-neutral by construction, exactly like ``sovereign.py``: no Django,
no engine imports, no database connection — the caller hands in the graph
and world it already holds.

**One producer per field:**

.. list-table:: Field-producer rulings
   :header-rows: 1

   * - Field
     - Producer
   * - ``name``, ``ideology``, ``colonial_stance``, ``is_settler_formation``,
       ``extraction_modifier``, ``violence_modifier``, ``class_reduction``,
       ``metabolic_reduction``, ``color_hex``, ``founded_tick``,
       ``dissolved_tick``
     - The ``faction`` graph node's own attributes —
       ``BalkanizationFaction.model_dump()`` written by
       ``WorldState.to_graph()`` (spec-070 / spec-109 A6).
   * - ``territory_influence``
     - Derived: one entry per outgoing INFLUENCES edge from this faction,
       carrying the edge's ``influence_level``/``support_type`` and the
       target territory's ``county_fips`` (resolved the same way
       ``project_sovereign`` resolves a capital/claim) — the *reverse* of
       ``GraphProtocol.query_faction_influence_by_territory``, which walks
       INFLUENCES edges *into* one territory to find its influencing
       factions.

Absence discipline (Constitution III.11): a faction id with no matching
graph node projects every field as ``None`` — including
``territory_influence``, which is otherwise a *present* (possibly empty)
tuple the instant the faction node exists. An empty tuple ("influences
nothing right now") and ``None`` ("this faction doesn't exist in this run")
are deliberately distinct: the former is real data, the latter is honest
absence.

**Fixture-harvest finding (documented, not silently worked around):** no
``babylon.engine.scenarios`` builder ever constructs a
``BalkanizationFaction`` or populates ``WorldState.factions`` (confirmed by
grep: zero ``BalkanizationFaction(`` / ``factions=`` call sites under
``src/babylon/engine/``) — the only production writer of ``NodeType.FACTION``
graph nodes today is the legacy web bridge's
``web/game/engine_bridge.py::_seed_balkanization_layer`` (Bridge-layer only,
owner item 8). This is not a dead node type — ``NodeType.FACTION`` is real,
production-stamped graph vocabulary (``WorldState.to_graph()`` writes it,
``FactionInfluenceSystem`` reads it) — it is a scenario-coverage gap: every
real headless campaign bakes zero faction pages today, and that is correct
behavior, not a bug. Porting the seed into engine scenarios is a physics
change out of this unit's scope (belongs to the RED_OGV repair program); the
gap itself is recorded as a wiring-doctrine ledger row separately.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from babylon.models.enums.topology import EdgeType, NodeType
from babylon.projection.sovereign import _county_fips_of
from babylon.projection.vault.render_faction import faction_statblock_rows
from babylon.projection.view_models import FactionTerritoryInfluence, FactionView

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.models.graph import GraphNode
    from babylon.models.world_state import WorldState

__all__ = ["project_faction", "faction_statblocks"]


def _resolve_faction(graph: GraphProtocol, faction_id: str) -> GraphNode | None:
    """Look up the faction node by its stable id.

    :param graph: The post-tick graph.
    :param faction_id: The faction's node id (``FAC_*``, spec-070).
    :returns: The matching node, or ``None`` when no such node exists — the
        faction hasn't been instantiated in this run, or the caller passed
        an id nobody has minted.
    """
    node = graph.get_node(faction_id)
    if node is None or node.node_type != NodeType.FACTION.value:
        return None
    return node


def _territory_influence(
    graph: GraphProtocol, faction_id: str
) -> tuple[FactionTerritoryInfluence, ...]:
    """Every INFLUENCES edge this faction casts, resolved to territory + county.

    Mirrors ``project_sovereign._claimed_county_fips``'s generic-query
    pattern — walking ``graph.query_edges(edge_type=EdgeType.INFLUENCES)``
    rather than the dedicated ``query_faction_influence_by_territory``
    (which resolves the opposite direction: influences *at* one territory).

    :param graph: The post-tick graph.
    :param faction_id: The influencing faction's node id.
    :returns: Rows sorted by ``influence_level`` descending, ``territory_id``
        ascending on ties — matching
        ``GraphProtocol.query_faction_influence_by_territory``'s own
        ordering convention. Empty when the faction influences nothing.
    """
    rows: list[FactionTerritoryInfluence] = []
    for edge in graph.query_edges(edge_type=EdgeType.INFLUENCES):
        if edge.source_id != faction_id:
            continue
        rows.append(
            FactionTerritoryInfluence(
                territory_id=edge.target_id,
                county_fips=_county_fips_of(graph, edge.target_id),
                influence_level=edge.attributes.get("influence_level", 0.0),
                support_type=edge.attributes.get("support_type", "ideological"),
            )
        )
    rows.sort(key=lambda row: (-row.influence_level, row.territory_id))
    return tuple(rows)


def project_faction(
    faction_id: str,
    *,
    graph: GraphProtocol,
    world: WorldState,
    tick: int,
) -> FactionView:
    """Project one faction's post-tick state into a :class:`FactionView`.

    Read strictly *post-tick*, for the same reason ``project_sovereign`` is:
    systems mutate the shared graph in-place in strict order, so a mid-tick
    read would see a partially-applied world.

    :param faction_id: The faction's node id (e.g. ``"FAC_RESTORATIONIST"``).
    :param graph: The committed post-tick graph.
    :param world: Unused — every ``FactionView`` field is graph-node sourced
        (spec-070's ``BalkanizationFaction`` carries no world-entity
        aggregation). Accepted anyway for signature parity with the Lane P
        ``project_<kind>(id, *, graph, world, tick)`` recipe every sibling
        projector (``project_sovereign`` et al.) shares.
    :param tick: The committed tick this dossier is projected from —
        becomes the dossier's ``verified_tick`` staleness anchor.
    :returns: The frozen, validated faction dossier. Every unattributed or
        nonexistent quantity is ``None``.
    :raises pydantic.ValidationError: when a present source value violates
        its constrained type — a wrong value fails loud, only a *missing*
        one is absence.
    """
    del world  # unused: see docstring above.
    node = _resolve_faction(graph, faction_id)
    attrs: dict[str, Any] = dict(node.attributes) if node else {}

    return FactionView(
        faction_id=faction_id,
        verified_tick=tick,
        name=attrs.get("name"),
        ideology=attrs.get("ideology"),
        colonial_stance=attrs.get("colonial_stance"),
        is_settler_formation=attrs.get("is_settler_formation"),
        extraction_modifier=attrs.get("extraction_modifier"),
        violence_modifier=attrs.get("violence_modifier"),
        class_reduction=attrs.get("class_reduction"),
        metabolic_reduction=attrs.get("metabolic_reduction"),
        color_hex=attrs.get("color_hex"),
        founded_tick=attrs.get("founded_tick"),
        dissolved_tick=attrs.get("dissolved_tick"),
        territory_influence=_territory_influence(graph, faction_id) if node else None,
    )


def faction_statblocks(
    *,
    graph: GraphProtocol,
    world: WorldState,
    tick: int,
) -> Callable[[str], list[tuple[str, str]] | None]:
    """Build a live ``{statblock}`` provider for ``faction/<id>`` subjects.

    The per-kind statblock provider the shared-file-discipline design rule
    requires (``specs/24-archive/work-orders-p2-p4.md``): this module
    registers nothing in ``babylon.tui.app`` itself — the single serial
    WO-45 composes every Lane P kind's provider into the app's kind-dispatch
    ``StatblockProvider`` registry. Live, not baked (design canon S3): a
    page whose ``{statblock}`` fence carries no baked body defers to
    exactly this kind of provider, by subject id
    (``tui.directives.BabylonFence._directive_statblock``).

    Deliberately does not import :mod:`babylon.tui` — the projection layer
    must not depend on its own client — so the returned callable matches
    ``tui.directives.StatblockProvider``'s shape *structurally*
    (``Callable[[str], Sequence[tuple[str, str]] | None]``) rather than by
    importing that type alias.

    :param graph: The live post-tick graph the caller already holds.
    :param world: Unused; see :func:`project_faction`. Accepted for
        signature parity with the other Lane P statblock-provider factories.
    :param tick: The tick this provider's projections are verified as of.
    :returns: A provider callable: for a ``"faction/<id>"`` subject whose id
        names a real faction node, the flattened statblock rows of its live
        projection; ``None`` for any other subject or an unknown id (the
        honest-absence path the ``{statblock}`` directive itself renders).
    """

    def provider(subject: str) -> list[tuple[str, str]] | None:
        prefix = "faction/"
        if not subject.startswith(prefix):
            return None
        faction_id = subject[len(prefix) :]
        if _resolve_faction(graph, faction_id) is None:
            return None
        view = project_faction(faction_id, graph=graph, world=world, tick=tick)
        return list(faction_statblock_rows(view))

    return provider
