"""Track 1 / Task 2 (2026-07-18): the organizing-reach primitive.

``organizing_reach`` answers one question — which node ids sit within the
player org's PRESENCE ∪ SOLIDARITY neighborhood — and nothing else. Task 4's
``apply_fog`` (not written here) will use it as the *spatial* visibility axis:
political fields on nodes outside the returned set get masked at the
serialization boundary, never inside the engine.

**Reuse, not reinvention.** All hop-traversal is delegated to
``BabylonGraph.get_neighborhood`` (``src/babylon/topology/graph.py:706-739``),
which is already unit-tested; this module only supplies the PRESENCE ∪
SOLIDARITY edge-type filter and the ``player_org_id is None`` sentinel.

**Why plain edge-type strings, not the ``EdgeType`` enum.** This package sits
under ``web/game/fog/`` and is NOT on the allowlist in
``tests/unit/web/test_import_boundary.py`` that lets only
``engine_bridge.py`` (+ a short allowlist) import ``babylon.models`` /
``babylon.config`` / ``babylon.engine`` / ``babylon.ooda`` /
``babylon.persistence`` from ``web/``. ``EdgeType.PRESENCE.value ==
"presence"`` and ``EdgeType.SOLIDARITY.value == "solidarity"``
(``babylon.models.enums.topology.EdgeType``) are stored as plain strings on
every edge regardless (``BabylonGraph.add_edge`` folds ``edge_type=`` into
``_edge_type``), so comparing against the literal values is exact, not an
approximation — the same idiom ``engine_bridge._tenancy_members_by_territory``
already uses for TENANCY. The ``graph`` parameter is typed against
``babylon.kernel.graph_protocol.GraphProtocol`` instead of the concrete
``BabylonGraph``: ``babylon.kernel`` is the substrate-agnostic protocol layer
and is likewise outside the restricted prefix list, so this stays a
zero-engine-coupling module by construction, not just by convention.

**Empirical finding (verified against the shipped Wayne County scenario,
``babylon.engine.scenarios.create_wayne_county_scenario``):** PRESENCE edges
are real and populated (``Organization.territory_ids`` — Feature 031 /
``world_state.py:698-704``); SOLIDARITY edges are also real
(``SolidaritySystem``) but in every shipped scenario they connect
``social_class`` node to ``social_class`` node (periphery worker → core
worker), never an organization or a territory. Since ``organizing_reach``
roots its BFS at ``player_org_id`` — an organization — and no PRESENCE/
SOLIDARITY edge bridges territory → class or org → class, the SOLIDARITY
half of the union is, TODAY, structurally unreachable from this primitive in
every shipped scenario: it always resolves to "PRESENCE-reachable
territories plus any sibling organizations sharing them". This matches the
plan's own guidance that class↔territory visibility is a TENANCY-based
concern for Task 4 to resolve separately (via
``engine_bridge._tenancy_members_by_territory``), not something this
primitive should special-case. The union is still implemented exactly as
specified — a scenario that ever wires an org-to-org or org-to-class
SOLIDARITY edge lights it up for free — but a caller must not assume
``organizing_reach`` currently surfaces any ``social_class`` node.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from babylon.kernel import GraphProtocol

#: EdgeType.PRESENCE.value / EdgeType.SOLIDARITY.value, as plain strings —
#: see the module docstring for why the enum itself is not imported here.
_REACH_EDGE_TYPES: frozenset[str] = frozenset({"presence", "solidarity"})


def organizing_reach(
    graph: GraphProtocol, player_org_id: str | None, radius: int
) -> frozenset[str]:
    """Node ids within organizing reach — the PRESENCE ∪ SOLIDARITY neighborhood.

    Args:
        graph: The hydrated session graph (any ``GraphProtocol`` implementer;
            in practice ``babylon.topology.graph.BabylonGraph``).
        player_org_id: The session's canonical player-org id (see
            ``engine_bridge._resolve_player_org_id`` — the single source of
            truth Task 1 established). ``None`` is a legitimate sentinel for
            sessions with no player org set (synthetic scenarios, headless
            sweeps — ``world_state.py:461-471``): it returns an empty reach,
            not an error.
        radius: Maximum hop distance, 1 = immediate neighbors only. Callers
            supply this from ``GameDefines.epistemic_horizon.organizing_reach_radius``
            — never hardcoded here.

    Returns:
        A ``frozenset`` of node ids — deterministic and order-independent
        (repeated calls on the same graph/args always compare equal), and
        hashable so callers may cache on it.

    Raises:
        KeyError: If ``player_org_id`` is not ``None`` but names no node in
            ``graph`` (propagated from ``get_neighborhood`` — a genuinely
            invalid id is a bug, not a fog case, and must fail loud rather
            than silently resolve to an empty reach).
    """
    if player_org_id is None:
        return frozenset()

    neighborhood = graph.get_neighborhood(
        player_org_id,
        radius=radius,
        edge_types=set(_REACH_EDGE_TYPES),
        direction="both",
    )
    return frozenset(node.id for node in neighborhood.nodes())


__all__ = ["organizing_reach"]
