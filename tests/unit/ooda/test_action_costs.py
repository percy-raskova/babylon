"""Tests for community-modified action costs (Feature 032).

Verifies embeddedness discount, outsider surcharge, contradiction pair
surcharge, and minimum cost floor.
"""

from __future__ import annotations

from typing import Any

import networkx as nx
import pytest

from babylon.config.defines import OODADefines
from babylon.models.enums import ActionType, CommunityType, EdgeType, OrgType
from babylon.ooda.action_costs import compute_action_cost
from babylon.ooda.types import ActionCostModifier


def _build_graph(
    org_id: str = "org_1",
    org_attrs: dict[str, Any] | None = None,
    community_id: str = "comm_1",
    community_attrs: dict[str, Any] | None = None,
    *,
    member_ids: list[str] | None = None,
    member_community_type: str = CommunityType.NEW_AFRIKAN.value,
) -> nx.DiGraph[str]:
    """Build a graph with an org, community, and optional membership edges."""
    graph: nx.DiGraph[str] = nx.DiGraph()

    default_org: dict[str, Any] = {
        "_node_type": "organization",
        "id": org_id,
        "org_type": OrgType.POLITICAL_FACTION.value,
    }
    if org_attrs:
        default_org.update(org_attrs)
    graph.add_node(org_id, **default_org)

    default_comm: dict[str, Any] = {
        "_node_type": "community",
        "id": community_id,
        "community_type": CommunityType.NEW_AFRIKAN.value,
    }
    if community_attrs:
        default_comm.update(community_attrs)
    graph.add_node(community_id, **default_comm)

    if member_ids:
        community_member_ids: list[str] = []
        for mid in member_ids:
            if mid not in graph:
                graph.add_node(
                    mid,
                    _node_type="person",
                    community_type=member_community_type,
                    community_id=community_id,
                )
            community_member_ids.append(mid)
            graph.add_edge(org_id, mid, edge_type=EdgeType.MEMBERSHIP.value)
        # Store member list on community node
        graph.nodes[community_id]["member_node_ids"] = community_member_ids

    return graph


class TestEmbeddedOrgDiscount:
    """Embedded organizations get cost discounts."""

    def test_full_overlap_max_discount(self) -> None:
        """Full membership overlap gives maximum discount."""
        defines = OODADefines()
        members = ["p1", "p2"]
        graph = _build_graph(member_ids=members)

        result = compute_action_cost(
            ActionType.EDUCATE,
            "org_1",
            "comm_1",
            graph,
            defines,
        )

        assert isinstance(result, ActionCostModifier)
        # Full overlap=1.0: modifier = max(0.5, 1.0 - 1.0*0.5) = 0.5
        assert result.modifier == pytest.approx(0.5)
        assert result.effective_cost >= 1

    def test_partial_overlap_proportional_discount(self) -> None:
        """Partial overlap gives proportional discount."""
        defines = OODADefines()
        # Org has 1 member, community has 2 members → overlap = 0.5
        graph = _build_graph(member_ids=["p1"])
        # Add a second community member not in the org
        graph.add_node(
            "p2",
            _node_type="person",
            community_id="comm_1",
        )
        graph.nodes["comm_1"]["member_node_ids"] = ["p1", "p2"]

        result = compute_action_cost(
            ActionType.EDUCATE,
            "org_1",
            "comm_1",
            graph,
            defines,
        )

        # overlap=0.5: modifier = max(0.5, 1.0 - 0.5*0.5) = max(0.5, 0.75) = 0.75
        assert result.modifier == pytest.approx(0.75)

    def test_minimum_cost_floor(self) -> None:
        """Effective cost never goes below 1."""
        defines = OODADefines()
        members = ["p1", "p2"]
        graph = _build_graph(member_ids=members)

        result = compute_action_cost(
            ActionType.EDUCATE,
            "org_1",
            "comm_1",
            graph,
            defines,
        )

        assert result.effective_cost >= 1


class TestOutsiderSurcharge:
    """Non-member organizations get cost surcharge."""

    def test_no_overlap_outsider_multiplier(self) -> None:
        """Zero overlap (no membership) gives outsider surcharge."""
        defines = OODADefines()
        graph = _build_graph()
        # Add community members not in the org
        graph.add_node("p1", _node_type="person", community_id="comm_1")
        graph.nodes["comm_1"]["member_node_ids"] = ["p1"]

        result = compute_action_cost(
            ActionType.EDUCATE,
            "org_1",
            "comm_1",
            graph,
            defines,
        )

        assert result.modifier == pytest.approx(defines.outsider_cost_multiplier)
        assert "No membership" in result.reason

    def test_outsider_increases_effective_cost(self) -> None:
        """Outsider surcharge increases effective AP cost."""
        defines = OODADefines()
        graph = _build_graph()
        graph.add_node("p1", _node_type="person", community_id="comm_1")
        graph.nodes["comm_1"]["member_node_ids"] = ["p1"]

        result = compute_action_cost(
            ActionType.ORGANIZE,
            "org_1",
            "comm_1",
            graph,
            defines,
        )

        base = defines.get_base_cost(ActionType.ORGANIZE.value)
        assert result.effective_cost >= base


class TestContradictionPairSurcharge:
    """Contradiction axis crossing incurs heavy surcharge."""

    def test_settler_targeting_new_afrikan(self) -> None:
        """SETTLER org members targeting NEW_AFRIKAN community = contradiction."""
        defines = OODADefines()
        graph = _build_graph(
            community_attrs={"community_type": CommunityType.NEW_AFRIKAN.value},
            member_ids=["p1"],
            member_community_type=CommunityType.SETTLER.value,
        )
        # Remove the member from the community member list (they're settler, not in new_afrikan)
        graph.nodes["comm_1"]["member_node_ids"] = []
        # Add actual community members
        graph.add_node("c1", _node_type="person", community_id="comm_1")
        graph.nodes["comm_1"]["member_node_ids"] = ["c1"]

        result = compute_action_cost(
            ActionType.EDUCATE,
            "org_1",
            "comm_1",
            graph,
            defines,
        )

        assert result.modifier == pytest.approx(defines.contradiction_cost_multiplier)
        assert "contradiction" in result.reason.lower()

    def test_patriarchal_targeting_women(self) -> None:
        """PATRIARCHAL org members targeting WOMEN community = contradiction."""
        defines = OODADefines()
        graph = _build_graph(
            community_attrs={"community_type": CommunityType.WOMEN.value},
            member_ids=["p1"],
            member_community_type=CommunityType.PATRIARCHAL.value,
        )
        graph.nodes["comm_1"]["member_node_ids"] = []
        graph.add_node("c1", _node_type="person", community_id="comm_1")
        graph.nodes["comm_1"]["member_node_ids"] = ["c1"]

        result = compute_action_cost(
            ActionType.EDUCATE,
            "org_1",
            "comm_1",
            graph,
            defines,
        )

        assert result.modifier == pytest.approx(defines.contradiction_cost_multiplier)

    def test_contradiction_surcharge_higher_than_outsider(self) -> None:
        """Contradiction surcharge is greater than outsider surcharge."""
        defines = OODADefines()
        assert defines.contradiction_cost_multiplier > defines.outsider_cost_multiplier

    def test_no_contradiction_same_community_type(self) -> None:
        """Org members from same community type as target = no contradiction."""
        defines = OODADefines()
        graph = _build_graph(
            community_attrs={"community_type": CommunityType.NEW_AFRIKAN.value},
            member_ids=["p1"],
            member_community_type=CommunityType.NEW_AFRIKAN.value,
        )

        result = compute_action_cost(
            ActionType.EDUCATE,
            "org_1",
            "comm_1",
            graph,
            defines,
        )

        # Same type members = embedded, not contradiction
        assert result.modifier < defines.contradiction_cost_multiplier


class TestCostComputation:
    """General cost computation behavior."""

    def test_effective_cost_rounds_up(self) -> None:
        """Effective cost uses ceil() rounding."""
        defines = OODADefines()
        # EDUCATE base cost = 1, with outsider multiplier 1.5 → ceil(1.5) = 2
        graph = _build_graph()
        graph.add_node("p1", _node_type="person", community_id="comm_1")
        graph.nodes["comm_1"]["member_node_ids"] = ["p1"]

        result = compute_action_cost(
            ActionType.EDUCATE,
            "org_1",
            "comm_1",
            graph,
            defines,
        )

        # base_cost=1, modifier=1.5 → ceil(1.5)=2
        assert result.effective_cost == 2

    def test_base_cost_matches_defines(self) -> None:
        """Base cost comes from defines.get_base_cost()."""
        defines = OODADefines()
        graph = _build_graph(member_ids=["p1"])

        result = compute_action_cost(
            ActionType.ORGANIZE,
            "org_1",
            "comm_1",
            graph,
            defines,
        )

        assert result.base_cost == defines.get_base_cost(ActionType.ORGANIZE.value)

    def test_empty_community_outsider(self) -> None:
        """Community with no members treats org as outsider."""
        defines = OODADefines()
        graph = _build_graph()
        # No members in community at all

        result = compute_action_cost(
            ActionType.EDUCATE,
            "org_1",
            "comm_1",
            graph,
            defines,
        )

        # No community members → outsider
        assert result.modifier == pytest.approx(defines.outsider_cost_multiplier)

    def test_reason_field_populated(self) -> None:
        """Result always has a reason string."""
        defines = OODADefines()
        graph = _build_graph(member_ids=["p1"])

        result = compute_action_cost(
            ActionType.EDUCATE,
            "org_1",
            "comm_1",
            graph,
            defines,
        )

        assert len(result.reason) > 0
