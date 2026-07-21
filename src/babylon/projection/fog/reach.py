"""Track 1 / Task 2 (2026-07-18) + fix/null-play-coupling correction: the
organizing-reach primitive.

``organizing_reach`` answers one question — which node ids sit within the
player org's *organizing reach* — and nothing else. Task 4's ``apply_fog``
(not written here) will use it as the *spatial* visibility axis: political
fields on nodes outside the returned set get masked at the serialization
boundary, never inside the engine.

**The defect this module now corrects.** The original implementation
(commit ``aa98dbbd``) did a single
``get_neighborhood(player_org_id, edge_types={"presence", "solidarity"},
direction="both")`` call — a UNION of two edge types rooted at the org. That
is provably wrong: SOLIDARITY edges in this codebase connect ``social_class``
<-> ``social_class`` ONLY (verified in both shipped scenarios —
``_legacy_wayne.py:427-429`` and ``_legacy.py:431-440``; also pinned by
``tests/unit/web/fog/test_reach.py::TestSolidarityNeverTouchesAnOrganization``,
which fails loudly if that ever changes). SOLIDARITY never touches an
organization, so a BFS rooted at an org can never reach the SOLIDARITY half
of that union — the function silently resolved to presence-only reach while
being named "organizing reach."

**The correction: a composed, alternating traversal, not a union.** Reach is
three explicit hops, each over a DIFFERENT edge type — one ``get_neighborhood``
call with a multi-type edge set cannot express this, because SOLIDARITY is
only reachable *after* crossing PRESENCE then TENANCY, not directly from the
org::

    org --PRESENCE--> territory --TENANCY--> class --SOLIDARITY--> class

1. **PRESENCE**, org -> territory ids (``Organization.territory_ids`` is
   materialized as PRESENCE edges, ``world_state.py:698-704``).
2. **TENANCY**, those territories -> the ``social_class`` ids tenant there
   (the engine's Occupant -> Territory edge, directed class -> territory;
   see ``EdgeType.TENANCY``'s docstring and every shipped scenario's
   relationship-building code). Walked directly via
   ``GraphProtocol.query_edges(edge_type="tenancy")`` rather than importing
   ``engine_bridge._tenancy_members_by_territory`` (:1290-1322), which does
   the same grouping — importing it would create ``fog -> engine_bridge``,
   and Task 4 already imports ``engine_bridge -> fog``, so that edge would be
   a cycle. Traversing the protocol directly also means ``apply_fog`` calls
   this function with the graph alone; it does not need to separately
   compute and thread a tenancy map through every call site.
3. **SOLIDARITY**, those classes -> their allied classes — the organizing
   FRONT (Task 6 draws these as literal lines). This is the ONLY hop
   ``radius`` controls (see ``organizing_reach``'s docstring below); PRESENCE
   and TENANCY are structural and always exactly one hop, because an org has
   exactly one operational-footprint hop to its territories and a territory
   has exactly one tenancy hop to its occupant class — there is no
   "further" to walk along either edge type that means anything for this
   primitive.

**Empirical finding (verified against the shipped Wayne County scenario,
``babylon.engine.scenarios.create_wayne_county_scenario``):** the composed
traversal is NOT empty. The player org's two starting territories are held
in TENANCY by C001 (Detroit Proletariat), which has exactly one SOLIDARITY
ally, C004 (Dearborn Workers) — "Potential cross-community worker
solidarity". So the organizing front is real, if thin (one ally, one edge),
in the one shipped scenario that has both an org and TENANCY data.

**Why plain edge-type/node-type strings, not enums.** This package lives at
``babylon.projection.fog`` (relocated from ``web/game/fog/`` by Program 24
P1 WO-1) and sits outside the restricted prefix list in
``tests/unit/web/test_import_boundary.py`` that lets only
``engine_bridge.py`` (+ a short allowlist) import ``babylon.models`` /
``babylon.config`` / ``babylon.engine`` / ``babylon.ooda`` /
``babylon.persistence`` from ``web/``. ``EdgeType.PRESENCE.value ==
"presence"``, ``EdgeType.TENANCY.value == "tenancy"``,
``EdgeType.SOLIDARITY.value == "solidarity"``, and ``NodeType.TERRITORY.value
== "territory"`` (``babylon.models.enums``) are stored as plain strings on
every node/edge regardless (``BabylonGraph.add_node``/``add_edge`` fold
``node_type=``/``edge_type=`` into ``_node_type``/``_edge_type``), so
comparing against the literal values is exact, not an approximation — the
same idiom ``engine_bridge._tenancy_members_by_territory`` already uses. The
``graph`` parameter is typed against
``babylon.kernel.graph_protocol.GraphProtocol`` instead of the concrete
``BabylonGraph``: ``babylon.kernel`` is the substrate-agnostic protocol layer
and is likewise outside the restricted prefix list, so this stays a
zero-engine-coupling module by construction, not just by convention.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from babylon.kernel import GraphProtocol

#: EdgeType.PRESENCE.value, as a plain string — see the module docstring for
#: why the enum itself is not imported here.
_PRESENCE_EDGE_TYPE: str = "presence"

#: EdgeType.TENANCY.value, as a plain string.
_TENANCY_EDGE_TYPE: str = "tenancy"

#: EdgeType.SOLIDARITY.value, as a plain string.
_SOLIDARITY_EDGE_TYPE: str = "solidarity"

#: NodeType.TERRITORY.value, as a plain string.
_TERRITORY_NODE_TYPE: str = "territory"


def organizing_reach(
    graph: GraphProtocol, player_org_id: str | None, radius: int
) -> frozenset[str]:
    """Node ids within organizing reach — the composed PRESENCE -> TENANCY ->
    SOLIDARITY traversal rooted at the player org.

    Args:
        graph: The hydrated session graph (any ``GraphProtocol`` implementer;
            in practice ``babylon.topology.graph.BabylonGraph``).
        player_org_id: The session's canonical player-org id (see
            ``engine_bridge._resolve_player_org_id`` — the single source of
            truth Task 1 established). ``None`` is a legitimate sentinel for
            sessions with no player org set (synthetic scenarios, headless
            sweeps — ``world_state.py:461-471``): it returns an empty reach,
            not an error.
        radius: Maximum SOLIDARITY-hop distance from the organized classes —
            i.e. how deep the organizing FRONT extends, 1 = only direct
            allies of the classes the org already has TENANCY-mediated
            presence among. **This controls ONLY the third (SOLIDARITY) hop.**
            The PRESENCE hop (org -> territory) and the TENANCY hop
            (territory -> class) are each ALWAYS exactly one hop, regardless
            of ``radius`` — they are structural facts about the topology
            (an org's operational footprint, a territory's occupant), not a
            search depth to tune. Callers supply this from
            ``GameDefines.epistemic_horizon.organizing_reach_radius`` — never
            hardcoded here.

    Returns:
        A ``frozenset`` of node ids — the player org itself, every territory
        reached by the PRESENCE hop, every social class reached by the
        TENANCY hop, and every class reached by up to ``radius`` SOLIDARITY
        hops from there. Deterministic and order-independent (repeated calls
        on the same graph/args always compare equal), and hashable so
        callers may cache on it.

    Raises:
        KeyError: If ``player_org_id`` is not ``None`` but names no node in
            ``graph`` (propagated from ``get_neighborhood`` — a genuinely
            invalid id is a bug, not a fog case, and must fail loud rather
            than silently resolve to an empty reach).
    """
    if player_org_id is None:
        return frozenset()

    reached: set[str] = {player_org_id}

    # Hop 1 (structural, always exactly one hop): PRESENCE, org -> territory.
    presence_neighborhood = graph.get_neighborhood(
        player_org_id,
        radius=1,
        edge_types={_PRESENCE_EDGE_TYPE},
        direction="both",
    )
    territory_ids = {
        node.id for node in presence_neighborhood.nodes() if node.node_type == _TERRITORY_NODE_TYPE
    }
    reached |= territory_ids

    # Hop 2 (structural, always exactly one hop): TENANCY, territory ->
    # social_class. TENANCY is directed class -> territory, so we match on
    # target_id rather than calling get_neighborhood again.
    organized_class_ids = {
        edge.source_id
        for edge in graph.query_edges(edge_type=_TENANCY_EDGE_TYPE)
        if edge.target_id in territory_ids
    }
    reached |= organized_class_ids

    # Hop 3 (the only hop `radius` controls): SOLIDARITY, class -> allied
    # class(es) — the organizing front, `radius` hops deep.
    for class_id in organized_class_ids:
        solidarity_neighborhood = graph.get_neighborhood(
            class_id,
            radius=radius,
            edge_types={_SOLIDARITY_EDGE_TYPE},
            direction="both",
        )
        reached |= {node.id for node in solidarity_neighborhood.nodes()}

    return frozenset(reached)


__all__ = ["organizing_reach"]
