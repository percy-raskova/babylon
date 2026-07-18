"""Track 1 / Task 2 (2026-07-18): the organizing-reach primitive.

``organizing_reach`` wraps ``BabylonGraph.get_neighborhood`` — it must NOT
reimplement BFS (that machinery is already tested at
``tests/unit/topology/``). These tests exercise the wrapper's own contract:
the PRESENCE ∪ SOLIDARITY edge-type filter, the radius bound, determinism,
and the ``player_org_id is None`` sentinel (world_state.py:461-471 — a
legitimate "no player org" state for synthetic scenarios/headless sweeps,
not an error).

Graphs are built directly with ``BabylonGraph`` (same idiom as
``tests/unit/web/test_player_org_identity.py``) rather than a full
``WorldState``/scenario round-trip, so each test pins an exact, minimal
topology instead of depending on scenario-data shape.
"""

from __future__ import annotations

import pytest

from babylon.models.enums import NodeType
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit


def _graph() -> BabylonGraph:
    """Player org ORG1 (presence in T1 only) + rival ORG2 (presence in T2,
    two hops from ORG1) + two social classes linked by SOLIDARITY.

    Topology (all edges undirected in effect via direction="both"):

        ORG1 --presence--> T1
        T1   <--presence-- ORG2 --presence--> T2
        C1   --solidarity--> C2   (unconnected to ORG1/ORG2 by default)
    """
    g = BabylonGraph()
    g.add_node("ORG1", NodeType.ORGANIZATION, name="Player Org")
    g.add_node("ORG2", NodeType.ORGANIZATION, name="Rival Org")
    g.add_node("T1", NodeType.TERRITORY, name="Home Territory")
    g.add_node("T2", NodeType.TERRITORY, name="Far Territory")
    g.add_node("C1", NodeType.SOCIAL_CLASS, name="Class 1")
    g.add_node("C2", NodeType.SOCIAL_CLASS, name="Class 2")
    g.add_edge("ORG1", "T1", "presence")
    g.add_edge("ORG2", "T1", "presence")
    g.add_edge("ORG2", "T2", "presence")
    g.add_edge("C1", "C2", "solidarity", solidarity_strength=0.6)
    return g


class TestOrganizingReach:
    """Contract of ``organizing_reach(graph, player_org_id, radius)``."""

    def test_includes_presence_linked_territory(self) -> None:
        from game.fog.reach import organizing_reach

        reach = organizing_reach(_graph(), "ORG1", radius=1)

        assert "T1" in reach

    def test_includes_solidarity_linked_node(self) -> None:
        """A SOLIDARITY edge from the player org reaches its solidarity
        partner — the union half of PRESENCE ∪ SOLIDARITY. (In the shipped
        Wayne County scenario SOLIDARITY only ever links social_class to
        social_class, never an organization, so this wires the edge
        directly onto the org to exercise the primitive's actual contract;
        see the module report for the scenario-topology finding.)
        """
        from game.fog.reach import organizing_reach

        g = _graph()
        g.add_edge("ORG1", "C1", "solidarity", solidarity_strength=0.4)

        reach = organizing_reach(g, "ORG1", radius=1)

        assert "C1" in reach

    def test_excludes_nodes_beyond_radius(self) -> None:
        """T2 is two PRESENCE-hops from ORG1 (ORG1->T1->ORG2->T2 is three
        hops; even the closer ORG2 is 2 hops) — radius=1 must not reach it."""
        from game.fog.reach import organizing_reach

        reach = organizing_reach(_graph(), "ORG1", radius=1)

        assert "T2" not in reach
        assert "ORG2" not in reach

    def test_radius_two_reaches_sibling_org_via_shared_territory(self) -> None:
        """Sanity check that radius genuinely extends the search: ORG2
        shares T1 with ORG1, so it is reachable at radius=2 but T2 (one hop
        further) still is not."""
        from game.fog.reach import organizing_reach

        reach = organizing_reach(_graph(), "ORG1", radius=2)

        assert "ORG2" in reach
        assert "T2" not in reach

    def test_deterministic_across_repeated_calls(self) -> None:
        from game.fog.reach import organizing_reach

        g = _graph()

        first = organizing_reach(g, "ORG1", radius=2)
        second = organizing_reach(g, "ORG1", radius=2)

        assert first == second

    def test_returns_frozenset(self) -> None:
        from game.fog.reach import organizing_reach

        reach = organizing_reach(_graph(), "ORG1", radius=1)

        assert isinstance(reach, frozenset)

    def test_empty_for_none_player_org_id(self) -> None:
        """``player_org_id=None`` is a legitimate sentinel (no player org
        set — synthetic scenarios, headless sweeps), never a crash."""
        from game.fog.reach import organizing_reach

        reach = organizing_reach(_graph(), None, radius=5)

        assert reach == frozenset()
