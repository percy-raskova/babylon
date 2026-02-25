"""Unit tests for CommunitySystem (Feature 022).

TDD RED phase: Tests written before implementation of hypergraph builder
and CommunitySystem. Tests cover build, query, and overlap operations.
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.models.entities.community import (
    CommunityMembership,
    CommunityState,
)
from babylon.models.enums import CommunityType, LegalStatus, MembershipRole


@pytest.mark.unit
class TestBuildCommunityHypergraph:
    """Tests for build_community_hypergraph()."""

    def test_builds_hypergraph_from_memberships(self) -> None:
        """Hypergraph contains one hyperedge per non-empty community."""
        from babylon.engine.systems.community import build_community_hypergraph

        memberships = [
            CommunityMembership(
                agent_id="A1",
                community_type=CommunityType.NEW_AFRIKAN,
                role=MembershipRole.ACTIVE,
                strength=0.7,  # type: ignore[arg-type]
            ),
            CommunityMembership(
                agent_id="A2",
                community_type=CommunityType.NEW_AFRIKAN,
                role=MembershipRole.PARTICIPANT,
            ),
            CommunityMembership(
                agent_id="A2",
                community_type=CommunityType.TRANS,
                role=MembershipRole.CORE_ORGANIZER,
                strength=1.0,  # type: ignore[arg-type]
            ),
            CommunityMembership(
                agent_id="A3",
                community_type=CommunityType.TRANS,
                role=MembershipRole.PERIPHERAL,
                strength=0.2,  # type: ignore[arg-type]
            ),
        ]
        community_states = {
            CommunityType.NEW_AFRIKAN: CommunityState(community_type=CommunityType.NEW_AFRIKAN),
            CommunityType.TRANS: CommunityState(community_type=CommunityType.TRANS),
        }

        H = build_community_hypergraph(memberships, community_states)

        # Two communities with members → two hyperedges
        assert H.num_edges == 2
        # Three unique agents → three nodes
        assert H.num_nodes == 3

    def test_empty_community_excluded(self) -> None:
        """Communities with no members are not added as hyperedges."""
        from babylon.engine.systems.community import build_community_hypergraph

        memberships = [
            CommunityMembership(
                agent_id="A1",
                community_type=CommunityType.NEW_AFRIKAN,
            ),
        ]
        community_states = {
            CommunityType.NEW_AFRIKAN: CommunityState(community_type=CommunityType.NEW_AFRIKAN),
            CommunityType.DISABLED: CommunityState(community_type=CommunityType.DISABLED),
        }

        H = build_community_hypergraph(memberships, community_states)

        # Only NEW_AFRIKAN has members
        assert H.num_edges == 1

    def test_multi_membership_agent(self) -> None:
        """Agent belonging to multiple communities appears in all hyperedges."""
        from babylon.engine.systems.community import build_community_hypergraph

        memberships = [
            CommunityMembership(agent_id="A1", community_type=CommunityType.NEW_AFRIKAN),
            CommunityMembership(agent_id="A1", community_type=CommunityType.TRANS),
            CommunityMembership(agent_id="A1", community_type=CommunityType.DISABLED),
        ]
        community_states = {
            CommunityType.NEW_AFRIKAN: CommunityState(community_type=CommunityType.NEW_AFRIKAN),
            CommunityType.TRANS: CommunityState(community_type=CommunityType.TRANS),
            CommunityType.DISABLED: CommunityState(community_type=CommunityType.DISABLED),
        }

        H = build_community_hypergraph(memberships, community_states)

        # Agent A1 belongs to all 3
        agent_communities = H.nodes.memberships("A1")
        assert len(agent_communities) == 3


@pytest.mark.unit
class TestSharedCommunities:
    """Tests for shared_communities()."""

    def test_shared_communities_intersection(self) -> None:
        """Returns correct intersection of community memberships."""
        from babylon.engine.systems.community import (
            build_community_hypergraph,
            shared_communities,
        )

        memberships = [
            CommunityMembership(agent_id="A1", community_type=CommunityType.NEW_AFRIKAN),
            CommunityMembership(agent_id="A1", community_type=CommunityType.TRANS),
            CommunityMembership(agent_id="A2", community_type=CommunityType.TRANS),
            CommunityMembership(agent_id="A2", community_type=CommunityType.DISABLED),
        ]
        community_states = {
            CommunityType.NEW_AFRIKAN: CommunityState(community_type=CommunityType.NEW_AFRIKAN),
            CommunityType.TRANS: CommunityState(community_type=CommunityType.TRANS),
            CommunityType.DISABLED: CommunityState(community_type=CommunityType.DISABLED),
        }

        H = build_community_hypergraph(memberships, community_states)
        shared = shared_communities(H, "A1", "A2")

        # Only TRANS is shared
        assert len(shared) == 1
        assert CommunityType.TRANS.value in shared

    def test_no_shared_communities(self) -> None:
        """Returns empty set when agents share no communities."""
        from babylon.engine.systems.community import (
            build_community_hypergraph,
            shared_communities,
        )

        memberships = [
            CommunityMembership(agent_id="A1", community_type=CommunityType.NEW_AFRIKAN),
            CommunityMembership(agent_id="A2", community_type=CommunityType.DISABLED),
        ]
        community_states = {
            CommunityType.NEW_AFRIKAN: CommunityState(community_type=CommunityType.NEW_AFRIKAN),
            CommunityType.DISABLED: CommunityState(community_type=CommunityType.DISABLED),
        }

        H = build_community_hypergraph(memberships, community_states)
        shared = shared_communities(H, "A1", "A2")

        assert len(shared) == 0


@pytest.mark.unit
class TestCommunityOverlapMatrix:
    """Tests for community_overlap_matrix()."""

    def test_diagonal_equals_community_count(self) -> None:
        """Diagonal entry equals number of communities the agent belongs to."""
        from babylon.engine.systems.community import (
            build_community_hypergraph,
            community_overlap_matrix,
        )

        memberships = [
            CommunityMembership(agent_id="A1", community_type=CommunityType.NEW_AFRIKAN),
            CommunityMembership(agent_id="A1", community_type=CommunityType.TRANS),
            CommunityMembership(agent_id="A1", community_type=CommunityType.DISABLED),
            CommunityMembership(agent_id="A2", community_type=CommunityType.TRANS),
        ]
        community_states = {
            CommunityType.NEW_AFRIKAN: CommunityState(community_type=CommunityType.NEW_AFRIKAN),
            CommunityType.TRANS: CommunityState(community_type=CommunityType.TRANS),
            CommunityType.DISABLED: CommunityState(community_type=CommunityType.DISABLED),
        }

        H = build_community_hypergraph(memberships, community_states)
        overlap, node_index = community_overlap_matrix(H)

        # A1 belongs to 3 communities
        a1_idx = node_index["A1"]
        assert overlap[a1_idx, a1_idx] == 3

        # A2 belongs to 1 community
        a2_idx = node_index["A2"]
        assert overlap[a2_idx, a2_idx] == 1

    def test_off_diagonal_equals_shared_count(self) -> None:
        """Off-diagonal entry equals number of shared communities."""
        from babylon.engine.systems.community import (
            build_community_hypergraph,
            community_overlap_matrix,
        )

        memberships = [
            CommunityMembership(agent_id="A1", community_type=CommunityType.NEW_AFRIKAN),
            CommunityMembership(agent_id="A1", community_type=CommunityType.TRANS),
            CommunityMembership(agent_id="A2", community_type=CommunityType.TRANS),
            CommunityMembership(agent_id="A2", community_type=CommunityType.NEW_AFRIKAN),
        ]
        community_states = {
            CommunityType.NEW_AFRIKAN: CommunityState(community_type=CommunityType.NEW_AFRIKAN),
            CommunityType.TRANS: CommunityState(community_type=CommunityType.TRANS),
        }

        H = build_community_hypergraph(memberships, community_states)
        overlap, node_index = community_overlap_matrix(H)

        a1_idx = node_index["A1"]
        a2_idx = node_index["A2"]
        # Both share NEW_AFRIKAN and TRANS → 2
        assert overlap[a1_idx, a2_idx] == 2
        assert overlap[a2_idx, a1_idx] == 2


@pytest.mark.unit
class TestCommunitySystemStep:
    """Tests for CommunitySystem.step() — solidarity amplification and decay."""

    def _make_graph_with_solidarity_edge(self) -> Any:
        """Create a minimal graph with a SOLIDARITY edge between two agents."""
        import networkx as nx

        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "A1",
            _node_type="social_class",
            active=True,
            wealth=20.0,
            community_memberships=[],
            community_cost_modifier=1.0,
            threat_score=0.0,
        )
        graph.add_node(
            "A2",
            _node_type="social_class",
            active=True,
            wealth=15.0,
            community_memberships=[],
            community_cost_modifier=1.0,
            threat_score=0.0,
        )
        graph.add_edge(
            "A1",
            "A2",
            _edge_type="solidarity",
            solidarity_strength=0.5,
        )
        return graph

    def test_system_has_name(self) -> None:
        """CommunitySystem has the correct name attribute."""
        from babylon.engine.systems.community import CommunitySystem

        system = CommunitySystem()
        assert system.name == "community"

    def test_step_amplifies_solidarity_strength(self) -> None:
        """Shared community memberships amplify solidarity_strength on edges."""
        from babylon.engine.systems.community import CommunitySystem

        graph = self._make_graph_with_solidarity_edge()

        # Give both agents shared community memberships
        memberships_a1 = [
            CommunityMembership(
                agent_id="A1",
                community_type=CommunityType.NEW_AFRIKAN,
                role=MembershipRole.ACTIVE,
                strength=0.7,  # type: ignore[arg-type]
            ),
        ]
        memberships_a2 = [
            CommunityMembership(
                agent_id="A2",
                community_type=CommunityType.NEW_AFRIKAN,
                role=MembershipRole.PARTICIPANT,
            ),
        ]
        graph.nodes["A1"]["community_memberships"] = [m.model_dump() for m in memberships_a1]
        graph.nodes["A2"]["community_memberships"] = [m.model_dump() for m in memberships_a2]

        community_states = {
            CommunityType.NEW_AFRIKAN: CommunityState(
                community_type=CommunityType.NEW_AFRIKAN,
                infrastructure=0.8,  # type: ignore[arg-type]
                cohesion=0.6,  # type: ignore[arg-type]
            ),
        }

        from babylon.engine.services import ServiceContainer

        services = ServiceContainer.create(
            community_hypergraph={"community_states": community_states},
        )

        context: dict[str, object] = {"tick": 1}

        system = CommunitySystem()
        system.step(graph, services, context)

        # Solidarity strength should be amplified above 0.5
        edge_data = graph.edges["A1", "A2"]
        assert edge_data["solidarity_strength"] > 0.5

    def test_step_computes_threat_scores(self) -> None:
        """CommunitySystem writes threat_score to agent nodes."""
        from babylon.engine.systems.community import CommunitySystem

        graph = self._make_graph_with_solidarity_edge()

        memberships_a1 = [
            CommunityMembership(
                agent_id="A1",
                community_type=CommunityType.NEW_AFRIKAN,
                role=MembershipRole.CORE_ORGANIZER,
                strength=1.0,  # type: ignore[arg-type]
                visibility=0.8,  # type: ignore[arg-type]
            ),
        ]
        graph.nodes["A1"]["community_memberships"] = [m.model_dump() for m in memberships_a1]
        graph.nodes["A2"]["community_memberships"] = []

        community_states = {
            CommunityType.NEW_AFRIKAN: CommunityState(
                community_type=CommunityType.NEW_AFRIKAN,
                heat=0.4,  # type: ignore[arg-type]
                legal_status=LegalStatus.DESIGNATED_EXTREMIST,
            ),
        }

        from babylon.engine.services import ServiceContainer

        services = ServiceContainer.create(
            community_hypergraph={"community_states": community_states},
        )

        context: dict[str, object] = {"tick": 1}

        system = CommunitySystem()
        system.step(graph, services, context)

        # A1 should have non-zero threat score
        assert graph.nodes["A1"]["threat_score"] > 0.0
        # A2 has no memberships → zero threat
        assert graph.nodes["A2"]["threat_score"] == 0.0


@pytest.mark.unit
class TestRepressionActions:
    """Tests for community-level repression action functions."""

    def test_legal_status_escalate_one_step(self) -> None:
        """Escalation advances legal status by one step."""
        from babylon.engine.systems.community import legal_status_escalate

        cs = CommunityState(
            community_type=CommunityType.NEW_AFRIKAN,
            legal_status=LegalStatus.LEGAL,
        )
        escalated = legal_status_escalate(cs)
        assert escalated.legal_status == LegalStatus.SURVEILLED

    def test_legal_status_escalate_from_top_stays(self) -> None:
        """Escalation at CRIMINALIZED stays at CRIMINALIZED."""
        from babylon.engine.systems.community import legal_status_escalate

        cs = CommunityState(
            community_type=CommunityType.NEW_AFRIKAN,
            legal_status=LegalStatus.CRIMINALIZED,
        )
        escalated = legal_status_escalate(cs)
        assert escalated.legal_status == LegalStatus.CRIMINALIZED

    def test_designate_increases_heat_and_legal_status(self) -> None:
        """Designate action raises heat and escalates legal status."""
        from babylon.engine.systems.community import designate_community

        cs = CommunityState(
            community_type=CommunityType.NEW_AFRIKAN,
            heat=0.2,  # type: ignore[arg-type]
            legal_status=LegalStatus.LEGAL,
        )
        result = designate_community(cs)
        assert result.legal_status == LegalStatus.SURVEILLED
        assert float(result.heat) > 0.2

    def test_infiltrate_reduces_cohesion(self) -> None:
        """Infiltrate action reduces community cohesion."""
        from babylon.engine.systems.community import infiltrate_community

        cs = CommunityState(
            community_type=CommunityType.TRANS,
            cohesion=0.7,  # type: ignore[arg-type]
        )
        result = infiltrate_community(cs)
        assert float(result.cohesion) < 0.7

    def test_disrupt_infrastructure_reduces_infrastructure(self) -> None:
        """Disrupt action reduces community infrastructure."""
        from babylon.engine.systems.community import disrupt_infrastructure

        cs = CommunityState(
            community_type=CommunityType.DISABLED,
            infrastructure=0.8,  # type: ignore[arg-type]
        )
        result = disrupt_infrastructure(cs)
        assert float(result.infrastructure) < 0.8
