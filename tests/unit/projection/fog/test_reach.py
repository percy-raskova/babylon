"""Track 1 / Task 2 (2026-07-18) + fix/null-play-coupling correction: the
organizing-reach primitive.

``organizing_reach`` wraps ``BabylonGraph.get_neighborhood``/``query_edges`` —
it must NOT reimplement BFS (that machinery is already tested at
``tests/unit/topology/``). These tests exercise the wrapper's own contract:
the composed PRESENCE -> TENANCY -> SOLIDARITY traversal, the radius bound
(which now governs only the SOLIDARITY hop depth), determinism, and the
``player_org_id is None`` sentinel (world_state.py:461-471 — a legitimate
"no player org" state for synthetic scenarios/headless sweeps, not an error).

**Why the fixture changed.** The original implementation was a single
``get_neighborhood(player_org_id, edge_types={"presence", "solidarity"})``
union call. That is provably wrong: SOLIDARITY edges connect ``social_class``
to ``social_class`` only in every shipped scenario (see
``TestSolidarityNeverTouchesAnOrganization`` below) — never an organization —
so a BFS rooted at an org can never reach the SOLIDARITY half of that union
except by an artificial org-to-class SOLIDARITY edge that does not exist in
shipped data. The corrected primitive composes three explicit, differently-
typed hops (PRESENCE, then TENANCY, then SOLIDARITY) instead. The fixture
below now includes a TENANCY edge so the composed chain has something to
walk in a minimal synthetic graph, matching the real topology's shape.
"""

from __future__ import annotations

import pytest

from babylon.models.enums import NodeType
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit


def _graph() -> BabylonGraph:
    """Player org ORG1 (presence in T1 only) + rival ORG2 (presence in T2,
    structurally unreachable from ORG1 by any hop this primitive takes) +
    a tenant class C1 in T1, allied to C2 by one SOLIDARITY hop and to C3
    by a second.

    Topology (all edges undirected in effect via direction="both"):

        ORG1 --presence--> T1 <--tenancy-- C1 --solidarity--> C2 --solidarity--> C3
        ORG2 --presence--> T2   (unrelated; no path from ORG1 reaches it)
    """
    g = BabylonGraph()
    g.add_node("ORG1", NodeType.ORGANIZATION, name="Player Org")
    g.add_node("ORG2", NodeType.ORGANIZATION, name="Rival Org")
    g.add_node("T1", NodeType.TERRITORY, name="Home Territory")
    g.add_node("T2", NodeType.TERRITORY, name="Far Territory")
    g.add_node("C1", NodeType.SOCIAL_CLASS, name="Class 1 (tenant of T1)")
    g.add_node("C2", NodeType.SOCIAL_CLASS, name="Class 2 (ally of C1)")
    g.add_node("C3", NodeType.SOCIAL_CLASS, name="Class 3 (ally of C2)")
    g.add_edge("ORG1", "T1", "presence")
    g.add_edge("ORG2", "T2", "presence")
    g.add_edge("C1", "T1", "tenancy")
    g.add_edge("C1", "C2", "solidarity", solidarity_strength=0.6)
    g.add_edge("C2", "C3", "solidarity", solidarity_strength=0.3)
    return g


class TestOrganizingReach:
    """Contract of ``organizing_reach(graph, player_org_id, radius)``."""

    def test_includes_presence_linked_territory(self) -> None:
        from babylon.projection.fog.reach import organizing_reach

        reach = organizing_reach(_graph(), "ORG1", radius=1)

        assert "T1" in reach

    def test_includes_tenancy_linked_class(self) -> None:
        """The TENANCY hop (territory -> social_class) is structural and
        always taken exactly once, regardless of ``radius``."""
        from babylon.projection.fog.reach import organizing_reach

        reach = organizing_reach(_graph(), "ORG1", radius=1)

        assert "C1" in reach

    def test_includes_first_degree_solidarity_ally(self) -> None:
        """``radius=1`` takes one SOLIDARITY hop from the tenant class."""
        from babylon.projection.fog.reach import organizing_reach

        reach = organizing_reach(_graph(), "ORG1", radius=1)

        assert "C2" in reach
        assert "C3" not in reach

    def test_radius_extends_solidarity_hops_only(self) -> None:
        """``radius=2`` reaches the second-degree SOLIDARITY ally. This is
        the ONLY hop radius controls — PRESENCE and TENANCY are always
        exactly one hop regardless of ``radius``."""
        from babylon.projection.fog.reach import organizing_reach

        reach = organizing_reach(_graph(), "ORG1", radius=2)

        assert "C3" in reach

    def test_excludes_unrelated_org_and_territory(self) -> None:
        """ORG2/T2 share no PRESENCE/TENANCY/SOLIDARITY path with ORG1, at
        any radius."""
        from babylon.projection.fog.reach import organizing_reach

        reach = organizing_reach(_graph(), "ORG1", radius=5)

        assert "ORG2" not in reach
        assert "T2" not in reach

    def test_deterministic_across_repeated_calls(self) -> None:
        from babylon.projection.fog.reach import organizing_reach

        g = _graph()

        first = organizing_reach(g, "ORG1", radius=2)
        second = organizing_reach(g, "ORG1", radius=2)

        assert first == second

    def test_returns_frozenset(self) -> None:
        from babylon.projection.fog.reach import organizing_reach

        reach = organizing_reach(_graph(), "ORG1", radius=1)

        assert isinstance(reach, frozenset)

    def test_empty_for_none_player_org_id(self) -> None:
        """``player_org_id=None`` is a legitimate sentinel (no player org
        set — synthetic scenarios, headless sweeps), never a crash."""
        from babylon.projection.fog.reach import organizing_reach

        reach = organizing_reach(_graph(), None, radius=5)

        assert reach == frozenset()

    def test_includes_player_org_itself(self) -> None:
        from babylon.projection.fog.reach import organizing_reach

        reach = organizing_reach(_graph(), "ORG1", radius=1)

        assert "ORG1" in reach


class TestOrganizingReachAgainstRealWayneCountyScenario:
    """THE test that matters: against the REAL shipped
    ``create_wayne_county_scenario()`` graph (not a synthetic fixture),
    reach must include a ``social_class`` reached via the TENANCY hop AND
    an allied class reached via the SOLIDARITY hop. The old
    presence-union-solidarity implementation could never pass this — the
    SOLIDARITY half of its union was unreachable from an org root by
    construction.
    """

    def test_reach_includes_tenancy_and_solidarity_hops(self) -> None:
        from babylon.engine.scenarios import create_wayne_county_scenario
        from babylon.projection.fog.reach import organizing_reach

        state, _config, defines = create_wayne_county_scenario()
        graph = state.to_graph()
        assert state.player_org_id is not None

        radius = defines.epistemic_horizon.organizing_reach_radius
        reach = organizing_reach(graph, state.player_org_id, radius=radius)

        # C001 (Detroit Proletariat) holds TENANCY over the player org's two
        # starting territories in the shipped scenario data.
        assert "C001" in reach, (
            f"expected the TENANCY-reached tenant class in the reach set; got {sorted(reach)}"
        )
        # C004 (Dearborn Workers) is C001's sole SOLIDARITY ally in the
        # shipped scenario ("Potential cross-community worker solidarity").
        assert "C004" in reach, (
            "expected the SOLIDARITY-reached allied class in the reach set "
            "-- if this fails, the organizing front is EMPTY in the shipped "
            f"scenario and needs an owner seeding decision; got {sorted(reach)}"
        )


class TestOrganizingReachAgainstRealUSScenario:
    """Blocker B1 (owner-ruled, 2026-07-18): the canonical ``us_nationwide``
    campaign (``create_us_scenario``) seeded ZERO organizations before this
    fix -- ``player_org_id`` was ``None`` and reach was structurally empty
    for the ONE game mode the spec's D3 declares IS the game. Same contract
    as :class:`TestOrganizingReachAgainstRealWayneCountyScenario`, against
    the nationwide scenario's seeded national Cadre Council org instead.
    """

    def test_reach_includes_tenancy_and_solidarity_hops(self) -> None:
        from babylon.engine.scenarios import create_us_scenario
        from babylon.projection.fog.reach import organizing_reach

        state, _config, defines = create_us_scenario()
        graph = state.to_graph()
        assert state.player_org_id is not None

        radius = defines.epistemic_horizon.organizing_reach_radius
        reach = organizing_reach(graph, state.player_org_id, radius=radius)

        # C001 (Periphery Worker) holds TENANCY over the player org's
        # starting territories -- the org is seeded among the mass base the
        # imperial circuit's periphery-worker tenancy zone already covers.
        assert "C001" in reach, (
            f"expected the TENANCY-reached tenant class in the reach set; got {sorted(reach)}"
        )
        # C004 (Labor Aristocracy) is C001's SOLIDARITY partner in the
        # shared imperial-circuit relationship set ``create_us_scenario``
        # reuses (edge exists regardless of solidarity_strength).
        assert "C004" in reach, (
            "expected the SOLIDARITY-reached allied class in the reach set "
            "-- if this fails, the organizing front is EMPTY in the shipped "
            f"scenario and needs an owner seeding decision; got {sorted(reach)}"
        )


class TestSolidarityNeverTouchesAnOrganization:
    """Pins the structural fact that makes the composed-hop design
    necessary: SOLIDARITY edges in the shipped scenarios connect
    ``social_class`` to ``social_class`` ONLY, never an organization. If a
    later scenario adds an org-level SOLIDARITY edge, THIS test must fail
    loudly so ``organizing_reach``'s design gets revisited deliberately
    rather than silently drifting.
    """

    def test_wayne_county_solidarity_edges_are_class_to_class(self) -> None:
        from babylon.engine.scenarios import create_wayne_county_scenario

        state, _config, _defines = create_wayne_county_scenario()
        graph = state.to_graph()

        solidarity_edges = list(graph.query_edges(edge_type="solidarity"))
        assert solidarity_edges, "expected at least one SOLIDARITY edge to check"
        for edge in solidarity_edges:
            source_type = graph.get_node(edge.source_id).node_type  # type: ignore[union-attr]
            target_type = graph.get_node(edge.target_id).node_type  # type: ignore[union-attr]
            assert source_type == "social_class", (
                f"SOLIDARITY source {edge.source_id!r} is {source_type!r}, "
                "not social_class -- org-level SOLIDARITY now exists, "
                "revisit organizing_reach's composed-hop design"
            )
            assert target_type == "social_class", (
                f"SOLIDARITY target {edge.target_id!r} is {target_type!r}, "
                "not social_class -- org-level SOLIDARITY now exists, "
                "revisit organizing_reach's composed-hop design"
            )

    def test_imperial_circuit_solidarity_edges_are_class_to_class(self) -> None:
        from babylon.engine.scenarios import create_imperial_circuit_scenario

        state, _config, _defines = create_imperial_circuit_scenario(solidarity_strength=0.4)
        graph = state.to_graph()

        solidarity_edges = list(graph.query_edges(edge_type="solidarity"))
        assert solidarity_edges, "expected at least one SOLIDARITY edge to check"
        for edge in solidarity_edges:
            source_type = graph.get_node(edge.source_id).node_type  # type: ignore[union-attr]
            target_type = graph.get_node(edge.target_id).node_type  # type: ignore[union-attr]
            assert source_type == "social_class"
            assert target_type == "social_class"
