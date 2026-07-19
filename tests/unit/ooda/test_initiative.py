"""Tests for initiative scoring and action ordering (Feature 032).

Verifies the five-component composite formula with worked examples
from the initiative scoring contract.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import OODADefines
from babylon.models.enums import JurisdictionLevel
from babylon.ooda.initiative import (
    compute_community_embeddedness,
    compute_initiative_score,
    resolve_action_order,
    update_momentum,
)
from babylon.ooda.types import InitiativeScore
from babylon.topology.graph import BabylonGraph


class TestWorkedExamples:
    """Verify initiative score worked examples from contract."""

    def test_fbi_initiative_score(self) -> None:
        """FBI at game start: 5.508."""
        defines = OODADefines()
        score = compute_initiative_score(
            org_id="fbi",
            cycle_time=4.90,
            jurisdiction=JurisdictionLevel.NATIONAL,
            counter_intel_score=0.0,
            community_embeddedness=0.1,
            momentum=0.0,
            defines=defines,
        )
        assert score.score == pytest.approx(5.508, abs=0.01)
        assert score.speed_component == pytest.approx(0.408, abs=0.01)
        assert score.institutional_component == pytest.approx(5.0, abs=0.01)
        assert score.counterintel_component == pytest.approx(0.0, abs=0.01)
        assert score.embeddedness_component == pytest.approx(0.1, abs=0.01)
        assert score.momentum_component == pytest.approx(0.0, abs=0.01)

    def test_faction_initiative_score(self) -> None:
        """Faction at game start: 1.091."""
        defines = OODADefines()
        score = compute_initiative_score(
            org_id="rev_faction",
            cycle_time=5.12,
            jurisdiction=None,
            counter_intel_score=0.0,
            community_embeddedness=0.7,
            momentum=0.0,
            defines=defines,
        )
        assert score.score == pytest.approx(1.091, abs=0.01)

    def test_fbi_beats_faction_at_start(self) -> None:
        """FBI initiative >> faction at game start."""
        defines = OODADefines()
        fbi = compute_initiative_score(
            org_id="fbi",
            cycle_time=4.90,
            jurisdiction=JurisdictionLevel.NATIONAL,
            counter_intel_score=0.0,
            community_embeddedness=0.1,
            momentum=0.0,
            defines=defines,
        )
        faction = compute_initiative_score(
            org_id="rev_faction",
            cycle_time=5.12,
            jurisdiction=None,
            counter_intel_score=0.0,
            community_embeddedness=0.7,
            momentum=0.0,
            defines=defines,
        )
        assert fbi.score > faction.score


class TestResolveActionOrder:
    """Sort by descending score, ascending org_id tiebreak."""

    def test_descending_score_order(self) -> None:
        scores = [
            InitiativeScore(
                org_id="a",
                score=1.0,
                speed_component=1.0,
                institutional_component=0.0,
                counterintel_component=0.0,
                embeddedness_component=0.0,
                momentum_component=0.0,
            ),
            InitiativeScore(
                org_id="b",
                score=3.0,
                speed_component=3.0,
                institutional_component=0.0,
                counterintel_component=0.0,
                embeddedness_component=0.0,
                momentum_component=0.0,
            ),
            InitiativeScore(
                org_id="c",
                score=2.0,
                speed_component=2.0,
                institutional_component=0.0,
                counterintel_component=0.0,
                embeddedness_component=0.0,
                momentum_component=0.0,
            ),
        ]
        ordered = resolve_action_order(scores)
        assert [s.org_id for s in ordered] == ["b", "c", "a"]

    def test_tiebreak_by_org_id(self) -> None:
        scores = [
            InitiativeScore(
                org_id="z_org",
                score=5.0,
                speed_component=5.0,
                institutional_component=0.0,
                counterintel_component=0.0,
                embeddedness_component=0.0,
                momentum_component=0.0,
            ),
            InitiativeScore(
                org_id="a_org",
                score=5.0,
                speed_component=5.0,
                institutional_component=0.0,
                counterintel_component=0.0,
                embeddedness_component=0.0,
                momentum_component=0.0,
            ),
        ]
        ordered = resolve_action_order(scores)
        assert [s.org_id for s in ordered] == ["a_org", "z_org"]

    def test_empty_list(self) -> None:
        assert resolve_action_order([]) == []


class TestCommunityEmbeddedness:
    """Community embeddedness: org -> territory_ids -> TENANCY-linked
    social_class members -> each member's ``community_memberships`` share.

    Fixtures here are production-faithful: TENANCY is the real Occupant ->
    Territory edge (mirrors ``web/game/engine_bridge.py::
    _tenancy_members_by_territory``'s idiom), and NO node anywhere carries
    ``community_type`` -- that attribute is never produced (community is
    never a main-graph node, INV-010) and is exactly the phantom-attribute
    shape task #40 retired.
    """

    def test_no_territories_returns_zero(self) -> None:
        graph = BabylonGraph()
        graph.add_node("org_1", _node_type="organization")
        assert compute_community_embeddedness("org_1", graph) == 0.0

    def test_no_reachable_members_returns_zero(self) -> None:
        """org has territory_ids but no TENANCY-linked social_class members."""
        graph = BabylonGraph()
        graph.add_node("org_1", _node_type="organization", territory_ids=["terr_1"])
        graph.add_node("terr_1", _node_type="territory")
        assert compute_community_embeddedness("org_1", graph) == 0.0

    def test_no_memberships_anywhere_is_exactly_zero(self) -> None:
        """Production-faithful graph: real TENANCY-linked members, none of
        whom carry ``community_memberships`` -- must be exactly 0.0, not a
        default/fallback value."""
        graph = BabylonGraph()
        graph.add_node("org_1", _node_type="organization", territory_ids=["terr_1"])
        graph.add_node("terr_1", _node_type="territory")
        graph.add_node("member_1", _node_type="social_class")
        graph.add_node("member_2", _node_type="social_class")
        graph.add_edge("member_1", "terr_1", edge_type="tenancy")
        graph.add_edge("member_2", "terr_1", edge_type="tenancy")
        assert compute_community_embeddedness("org_1", graph) == 0.0

    def test_partial_membership_share(self) -> None:
        """2 of 4 TENANCY-linked members carry a non-empty
        ``community_memberships`` -> exactly 0.5."""
        graph = BabylonGraph()
        graph.add_node("org_1", _node_type="organization", territory_ids=["terr_1"])
        graph.add_node("terr_1", _node_type="territory")
        graph.add_node("member_1", _node_type="social_class", community_memberships=["religious"])
        graph.add_node("member_2", _node_type="social_class", community_memberships=["labor"])
        graph.add_node("member_3", _node_type="social_class")
        graph.add_node("member_4", _node_type="social_class")
        for member_id in ("member_1", "member_2", "member_3", "member_4"):
            graph.add_edge(member_id, "terr_1", edge_type="tenancy")
        assert compute_community_embeddedness("org_1", graph) == pytest.approx(0.5)

    def test_returns_bounded_value(self) -> None:
        graph = BabylonGraph()
        graph.add_node("org_1", _node_type="organization", territory_ids=["terr_1"])
        graph.add_node("terr_1", _node_type="territory")
        graph.add_node("member_1", _node_type="social_class", community_memberships=["new_afrikan"])
        graph.add_edge("member_1", "terr_1", edge_type="tenancy")
        result = compute_community_embeddedness("org_1", graph)
        assert 0.0 <= result <= 1.0


class TestUpdateMomentum:
    """Momentum decay and success bonus."""

    def test_decay_only(self) -> None:
        defines = OODADefines()
        new = update_momentum(1.0, action_succeeded=False, defines=defines)
        assert new == pytest.approx(0.8)

    def test_decay_plus_bonus(self) -> None:
        defines = OODADefines()
        new = update_momentum(1.0, action_succeeded=True, defines=defines)
        assert new == pytest.approx(1.0)  # 1.0 * 0.8 + 0.2

    def test_zero_momentum_success(self) -> None:
        defines = OODADefines()
        new = update_momentum(0.0, action_succeeded=True, defines=defines)
        assert new == pytest.approx(0.2)

    def test_exponential_decay(self) -> None:
        """Three ticks of decay without success."""
        defines = OODADefines()
        m = 1.0
        for _ in range(3):
            m = update_momentum(m, action_succeeded=False, defines=defines)
        assert m == pytest.approx(0.512, abs=0.001)
