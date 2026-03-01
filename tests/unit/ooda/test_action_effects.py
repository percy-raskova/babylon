"""Tests for action resolution and consciousness effects (Feature 032).

Verifies consciousness delta computation, action dispatch, and
specialized resolvers for AGITATE, REPRESS/SURVEIL, ASSIMILATE,
and PROVIDE_SERVICE actions.
"""

from __future__ import annotations

from typing import Any

import networkx as nx
import pytest

from babylon.config.defines import OODADefines, OrganizationDefines
from babylon.models.enums import (
    ActionType,
    ConsciousnessTendency,
    EdgeType,
    EventType,
    OrgType,
)
from babylon.ooda.action_effects import (
    compute_consciousness_delta,
    resolve_action,
)
from babylon.ooda.types import Action


def _make_graph_with_org_and_community(
    org_attrs: dict[str, Any],
    community_attrs: dict[str, Any],
    org_id: str = "org_1",
    community_id: str = "comm_1",
    *,
    add_membership: bool = False,
    member_ids: list[str] | None = None,
) -> nx.DiGraph[str]:
    """Build a minimal graph with one org and one community node."""
    graph: nx.DiGraph[str] = nx.DiGraph()
    graph.add_node(org_id, **org_attrs)
    graph.add_node(community_id, **community_attrs)

    if add_membership and member_ids:
        for member_id in member_ids:
            if member_id not in graph:
                graph.add_node(
                    member_id,
                    _node_type="person",
                    community_id=community_id,
                )
            graph.add_edge(
                org_id,
                member_id,
                edge_type=EdgeType.MEMBERSHIP.value,
            )

    return graph


def _default_org_attrs(
    org_id: str = "org_1",
    tendency: str = "revolutionary",
    org_type: str = OrgType.POLITICAL_FACTION.value,
    **overrides: Any,
) -> dict[str, Any]:
    """Default org attributes dict."""
    attrs: dict[str, Any] = {
        "_node_type": "organization",
        "id": org_id,
        "org_type": org_type,
        "cohesion": 0.7,
        "cadre_level": 0.5,
        "consciousness_tendency": tendency,
        "budget": 100.0,
        "heat": 0.0,
    }
    attrs.update(overrides)
    return attrs


def _default_community_attrs(
    community_id: str = "comm_1",
    **overrides: Any,
) -> dict[str, Any]:
    """Default community attributes dict."""
    attrs: dict[str, Any] = {
        "_node_type": "community",
        "id": community_id,
        "collective_identity": 0.3,
        "ideological_contestation": 0.2,
    }
    attrs.update(overrides)
    return attrs


class TestComputeConsciousnessDelta:
    """Consciousness delta computation from action effects."""

    def test_revolutionary_educate_positive_ci(self) -> None:
        """REVOLUTIONARY tendency EDUCATE produces positive CI delta."""
        defines = OODADefines()
        org_defines = OrganizationDefines()
        org_attrs = _default_org_attrs(tendency="revolutionary")
        community_attrs = _default_community_attrs()

        members = ["p1", "p2"]
        graph = _make_graph_with_org_and_community(
            org_attrs,
            community_attrs,
            add_membership=True,
            member_ids=members,
        )
        # Add community member references
        community_attrs_with_members = {**community_attrs, "member_node_ids": members}
        graph.nodes["comm_1"].update(community_attrs_with_members)

        delta = compute_consciousness_delta(
            org_attrs,
            "comm_1",
            ActionType.EDUCATE,
            graph,
            defines,
            org_defines,
        )

        assert delta is not None
        assert delta.collective_identity_delta > 0.0
        assert delta.tendency_pressure == ConsciousnessTendency.REVOLUTIONARY

    def test_liberal_educate_negative_or_zero_ci(self) -> None:
        """LIBERAL tendency EDUCATE produces zero or negative CI delta."""
        defines = OODADefines()
        org_defines = OrganizationDefines()
        org_attrs = _default_org_attrs(tendency="liberal")
        community_attrs = _default_community_attrs()

        members = ["p1", "p2"]
        graph = _make_graph_with_org_and_community(
            org_attrs,
            community_attrs,
            add_membership=True,
            member_ids=members,
        )
        graph.nodes["comm_1"].update({"member_node_ids": members})

        delta = compute_consciousness_delta(
            org_attrs,
            "comm_1",
            ActionType.EDUCATE,
            graph,
            defines,
            org_defines,
        )

        assert delta is not None
        # Liberal tendency_modifier is -0.05, so delta should be negative
        assert delta.collective_identity_delta <= 0.0
        assert delta.tendency_pressure == ConsciousnessTendency.LIBERAL

    def test_zero_cadre_returns_zero_delta(self) -> None:
        """Zero cadre_level short-circuits to zero delta."""
        defines = OODADefines()
        org_defines = OrganizationDefines()
        org_attrs = _default_org_attrs(cadre_level=0.0)
        community_attrs = _default_community_attrs()
        graph = _make_graph_with_org_and_community(org_attrs, community_attrs)

        delta = compute_consciousness_delta(
            org_attrs,
            "comm_1",
            ActionType.EDUCATE,
            graph,
            defines,
            org_defines,
        )

        assert delta is not None
        assert delta.collective_identity_delta == 0.0
        assert delta.tendency_magnitude == 0.0

    def test_zero_cohesion_returns_zero_delta(self) -> None:
        """Zero cohesion short-circuits to zero delta."""
        defines = OODADefines()
        org_defines = OrganizationDefines()
        org_attrs = _default_org_attrs(cohesion=0.0)
        community_attrs = _default_community_attrs()
        graph = _make_graph_with_org_and_community(org_attrs, community_attrs)

        delta = compute_consciousness_delta(
            org_attrs,
            "comm_1",
            ActionType.EDUCATE,
            graph,
            defines,
            org_defines,
        )

        assert delta is not None
        assert delta.collective_identity_delta == 0.0

    def test_zero_overlap_near_zero_effect(self) -> None:
        """No membership overlap produces near-zero effect (0.01 floor)."""
        defines = OODADefines()
        org_defines = OrganizationDefines()
        org_attrs = _default_org_attrs()
        community_attrs = _default_community_attrs()

        # No membership edges => overlap = 0, but floor is 0.01
        graph = _make_graph_with_org_and_community(org_attrs, community_attrs)

        delta = compute_consciousness_delta(
            org_attrs,
            "comm_1",
            ActionType.EDUCATE,
            graph,
            defines,
            org_defines,
        )

        # With no org members, overlap is 0.0 → effective_credibility = base * 0.01
        # But actually _compute_membership_overlap returns 0 with no members
        # base_credibility * max(0.0, 0.01) = base * 0.01
        assert delta is not None
        # Very small but nonzero due to 0.01 floor
        assert abs(delta.collective_identity_delta) < 0.01

    def test_full_overlap_full_effect(self) -> None:
        """Full membership overlap gives full credibility effect."""
        defines = OODADefines()
        org_defines = OrganizationDefines()
        org_attrs = _default_org_attrs()
        community_attrs = _default_community_attrs()

        members = ["p1", "p2"]
        graph = _make_graph_with_org_and_community(
            org_attrs,
            community_attrs,
            add_membership=True,
            member_ids=members,
        )
        graph.nodes["comm_1"].update({"member_node_ids": members})

        delta = compute_consciousness_delta(
            org_attrs,
            "comm_1",
            ActionType.EDUCATE,
            graph,
            defines,
            org_defines,
        )

        # Full overlap = 1.0, so effective_credibility = base_credibility
        assert delta is not None
        assert abs(delta.collective_identity_delta) > 0.01

    def test_max_delta_clamped(self) -> None:
        """Delta is clamped to max_ci_delta_per_tick."""
        defines = OODADefines()
        org_defines = OrganizationDefines()
        # Very high values to push raw delta above clamp
        org_attrs = _default_org_attrs(
            cadre_level=1.0,
            cohesion=1.0,
            tendency="revolutionary",
        )
        community_attrs = _default_community_attrs()

        members = ["p1", "p2"]
        graph = _make_graph_with_org_and_community(
            org_attrs,
            community_attrs,
            add_membership=True,
            member_ids=members,
        )
        graph.nodes["comm_1"].update({"member_node_ids": members})

        delta = compute_consciousness_delta(
            org_attrs,
            "comm_1",
            ActionType.EDUCATE,
            graph,
            defines,
            org_defines,
        )

        assert delta is not None
        assert abs(delta.collective_identity_delta) <= defines.max_ci_delta_per_tick

    def test_educate_contestation_bonus(self) -> None:
        """EDUCATE gets bonus when contestation > threshold."""
        defines = OODADefines()
        org_defines = OrganizationDefines()
        org_attrs = _default_org_attrs()

        # Low contestation (below threshold)
        community_low = _default_community_attrs(ideological_contestation=0.1)
        members = ["p1", "p2"]
        graph_low = _make_graph_with_org_and_community(
            org_attrs,
            community_low,
            add_membership=True,
            member_ids=members,
        )
        graph_low.nodes["comm_1"].update({"member_node_ids": members})

        delta_low = compute_consciousness_delta(
            org_attrs,
            "comm_1",
            ActionType.EDUCATE,
            graph_low,
            defines,
            org_defines,
        )

        # High contestation (above threshold = 0.3)
        community_high = _default_community_attrs(ideological_contestation=0.5)
        graph_high = _make_graph_with_org_and_community(
            org_attrs,
            community_high,
            add_membership=True,
            member_ids=members,
        )
        graph_high.nodes["comm_1"].update({"member_node_ids": members})

        delta_high = compute_consciousness_delta(
            org_attrs,
            "comm_1",
            ActionType.EDUCATE,
            graph_high,
            defines,
            org_defines,
        )

        assert delta_low is not None
        assert delta_high is not None
        # High-contestation EDUCATE should be larger
        assert abs(delta_high.collective_identity_delta) > abs(delta_low.collective_identity_delta)

    def test_agitate_returns_none_for_ci(self) -> None:
        """AGITATE has action_base = 0.0, so compute_consciousness_delta returns None."""
        defines = OODADefines()
        org_defines = OrganizationDefines()
        org_attrs = _default_org_attrs()
        community_attrs = _default_community_attrs()
        graph = _make_graph_with_org_and_community(org_attrs, community_attrs)

        delta = compute_consciousness_delta(
            org_attrs,
            "comm_1",
            ActionType.AGITATE,
            graph,
            defines,
            org_defines,
        )

        assert delta is None


class TestResolveAction:
    """Action dispatch via resolve_action()."""

    def test_agitate_returns_contestation_delta(self) -> None:
        """AGITATE resolver returns contestation_delta in direct_effects."""
        defines = OODADefines()
        org_defines = OrganizationDefines()
        org_attrs = _default_org_attrs()
        community_attrs = _default_community_attrs()
        graph = _make_graph_with_org_and_community(org_attrs, community_attrs)

        action = Action(
            org_id="org_1",
            action_type=ActionType.AGITATE,
            target_id="comm_1",
        )

        result = resolve_action(action, org_attrs, graph, defines, org_defines)

        assert result.success is True
        assert result.consciousness_delta is None
        assert result.direct_effects is not None
        assert result.direct_effects["contestation_delta"] == pytest.approx(
            defines.agitation_contestation_delta
        )
        assert EventType.ORGANIZATIONAL_ACTION.value in result.events_generated

    def test_repress_backfire_positive_ci(self) -> None:
        """REPRESS backfire raises target CI toward REVOLUTIONARY."""
        defines = OODADefines()
        org_defines = OrganizationDefines()
        org_attrs = _default_org_attrs(
            org_type=OrgType.STATE_APPARATUS.value,
            consciousness_tendency="liberal",
        )
        community_attrs = _default_community_attrs()
        graph = _make_graph_with_org_and_community(org_attrs, community_attrs)

        action = Action(
            org_id="org_1",
            action_type=ActionType.REPRESS,
            target_id="comm_1",
        )

        result = resolve_action(action, org_attrs, graph, defines, org_defines)

        assert result.success is True
        assert result.consciousness_delta is not None
        assert result.consciousness_delta.collective_identity_delta > 0.0
        assert result.consciousness_delta.tendency_pressure == ConsciousnessTendency.REVOLUTIONARY
        assert result.direct_effects is not None
        assert result.direct_effects.get("backfire") is True
        assert EventType.STATE_REPRESSION.value in result.events_generated

    def test_surveil_backfire_positive_ci(self) -> None:
        """SURVEIL backfire raises target CI toward REVOLUTIONARY."""
        defines = OODADefines()
        org_defines = OrganizationDefines()
        org_attrs = _default_org_attrs(
            org_type=OrgType.STATE_APPARATUS.value,
            consciousness_tendency="liberal",
        )
        community_attrs = _default_community_attrs()
        graph = _make_graph_with_org_and_community(org_attrs, community_attrs)

        action = Action(
            org_id="org_1",
            action_type=ActionType.SURVEIL,
            target_id="comm_1",
        )

        result = resolve_action(action, org_attrs, graph, defines, org_defines)

        assert result.success is True
        assert result.consciousness_delta is not None
        assert result.consciousness_delta.collective_identity_delta > 0.0
        assert result.consciousness_delta.tendency_pressure == ConsciousnessTendency.REVOLUTIONARY
        assert EventType.STATE_SURVEILLANCE.value in result.events_generated

    def test_surveil_smaller_backfire_than_repress(self) -> None:
        """SURVEIL has smaller backfire delta than REPRESS."""
        # Raise the clamp so both raw values aren't clamped to the same limit
        defines = OODADefines(max_ci_delta_per_tick=1.0)
        org_defines = OrganizationDefines()
        org_attrs = _default_org_attrs(
            org_type=OrgType.STATE_APPARATUS.value,
            consciousness_tendency="liberal",
        )
        community_attrs = _default_community_attrs()

        # REPRESS
        graph_r = _make_graph_with_org_and_community(org_attrs, community_attrs)
        action_r = Action(
            org_id="org_1",
            action_type=ActionType.REPRESS,
            target_id="comm_1",
        )
        result_r = resolve_action(action_r, org_attrs, graph_r, defines, org_defines)

        # SURVEIL
        graph_s = _make_graph_with_org_and_community(org_attrs, community_attrs)
        action_s = Action(
            org_id="org_1",
            action_type=ActionType.SURVEIL,
            target_id="comm_1",
        )
        result_s = resolve_action(action_s, org_attrs, graph_s, defines, org_defines)

        assert result_r.consciousness_delta is not None
        assert result_s.consciousness_delta is not None
        assert (
            result_r.consciousness_delta.collective_identity_delta
            > result_s.consciousness_delta.collective_identity_delta
        )

    def test_assimilate_negative_ci_liberal_tendency(self) -> None:
        """ASSIMILATE produces negative CI and LIBERAL tendency pressure."""
        defines = OODADefines()
        org_defines = OrganizationDefines()
        org_attrs = _default_org_attrs(
            org_type=OrgType.STATE_APPARATUS.value,
            consciousness_tendency="liberal",
        )
        community_attrs = _default_community_attrs()
        graph = _make_graph_with_org_and_community(org_attrs, community_attrs)

        action = Action(
            org_id="org_1",
            action_type=ActionType.ASSIMILATE,
            target_id="comm_1",
        )

        result = resolve_action(action, org_attrs, graph, defines, org_defines)

        assert result.success is True
        assert result.consciousness_delta is not None
        assert result.consciousness_delta.collective_identity_delta < 0.0
        assert result.consciousness_delta.tendency_pressure == ConsciousnessTendency.LIBERAL

    def test_assimilate_ci_clamped(self) -> None:
        """ASSIMILATE CI delta doesn't exceed max_ci_delta_per_tick."""
        defines = OODADefines()
        org_defines = OrganizationDefines()
        org_attrs = _default_org_attrs(
            org_type=OrgType.STATE_APPARATUS.value,
            consciousness_tendency="liberal",
        )
        community_attrs = _default_community_attrs()
        graph = _make_graph_with_org_and_community(org_attrs, community_attrs)

        action = Action(
            org_id="org_1",
            action_type=ActionType.ASSIMILATE,
            target_id="comm_1",
        )

        result = resolve_action(action, org_attrs, graph, defines, org_defines)

        assert result.consciousness_delta is not None
        assert (
            abs(result.consciousness_delta.collective_identity_delta)
            <= defines.max_ci_delta_per_tick
        )

    def test_provide_service_revolutionary_positive(self) -> None:
        """REVOLUTIONARY PROVIDE_SERVICE increases CI."""
        defines = OODADefines()
        org_defines = OrganizationDefines()
        org_attrs = _default_org_attrs(tendency="revolutionary")
        community_attrs = _default_community_attrs()

        members = ["p1", "p2"]
        graph = _make_graph_with_org_and_community(
            org_attrs,
            community_attrs,
            add_membership=True,
            member_ids=members,
        )
        graph.nodes["comm_1"].update({"member_node_ids": members})

        action = Action(
            org_id="org_1",
            action_type=ActionType.PROVIDE_SERVICE,
            target_id="comm_1",
        )

        result = resolve_action(action, org_attrs, graph, defines, org_defines)

        assert result.success is True
        assert result.consciousness_delta is not None
        assert result.consciousness_delta.collective_identity_delta > 0.0

    def test_provide_service_liberal_negative(self) -> None:
        """LIBERAL PROVIDE_SERVICE decreases CI (negative delta)."""
        defines = OODADefines()
        org_defines = OrganizationDefines()
        org_attrs = _default_org_attrs(tendency="liberal")
        community_attrs = _default_community_attrs()

        members = ["p1", "p2"]
        graph = _make_graph_with_org_and_community(
            org_attrs,
            community_attrs,
            add_membership=True,
            member_ids=members,
        )
        graph.nodes["comm_1"].update({"member_node_ids": members})

        action = Action(
            org_id="org_1",
            action_type=ActionType.PROVIDE_SERVICE,
            target_id="comm_1",
        )

        result = resolve_action(action, org_attrs, graph, defines, org_defines)

        assert result.success is True
        assert result.consciousness_delta is not None
        assert result.consciousness_delta.collective_identity_delta < 0.0

    def test_provide_service_fascist_no_effect(self) -> None:
        """FASCIST PROVIDE_SERVICE returns zero CI delta (returns None from action base)."""
        defines = OODADefines()
        org_defines = OrganizationDefines()
        org_attrs = _default_org_attrs(tendency="fascist")
        community_attrs = _default_community_attrs()
        graph = _make_graph_with_org_and_community(org_attrs, community_attrs)

        action = Action(
            org_id="org_1",
            action_type=ActionType.PROVIDE_SERVICE,
            target_id="comm_1",
        )

        result = resolve_action(action, org_attrs, graph, defines, org_defines)

        assert result.success is True
        # FASCIST tendency returns action_base 0.0, so no CI effect
        assert result.consciousness_delta is None

    def test_educate_dispatch_returns_action_result(self) -> None:
        """EDUCATE goes through generic consciousness path."""
        defines = OODADefines()
        org_defines = OrganizationDefines()
        org_attrs = _default_org_attrs()
        community_attrs = _default_community_attrs()

        members = ["p1", "p2"]
        graph = _make_graph_with_org_and_community(
            org_attrs,
            community_attrs,
            add_membership=True,
            member_ids=members,
        )
        graph.nodes["comm_1"].update({"member_node_ids": members})

        action = Action(
            org_id="org_1",
            action_type=ActionType.EDUCATE,
            target_id="comm_1",
        )

        result = resolve_action(action, org_attrs, graph, defines, org_defines)

        assert result.success is True
        assert result.consciousness_delta is not None
        assert EventType.ORGANIZATIONAL_ACTION.value in result.events_generated

    def test_recruit_generic_dispatch(self) -> None:
        """RECRUIT goes through generic consciousness path."""
        defines = OODADefines()
        org_defines = OrganizationDefines()
        org_attrs = _default_org_attrs()
        community_attrs = _default_community_attrs()

        members = ["p1", "p2"]
        graph = _make_graph_with_org_and_community(
            org_attrs,
            community_attrs,
            add_membership=True,
            member_ids=members,
        )
        graph.nodes["comm_1"].update({"member_node_ids": members})

        action = Action(
            org_id="org_1",
            action_type=ActionType.RECRUIT,
            target_id="comm_1",
        )

        result = resolve_action(action, org_attrs, graph, defines, org_defines)

        assert result.success is True
        assert result.consciousness_delta is not None


class TestCredibilityByOrgType:
    """Credibility derivation from org attributes for different org types."""

    def test_civil_society_uses_legitimacy(self) -> None:
        """CivilSocietyOrg credibility comes from legitimacy attribute."""
        defines = OODADefines()
        org_defines = OrganizationDefines()
        org_attrs = _default_org_attrs(
            org_type=OrgType.CIVIL_SOCIETY.value,
            legitimacy=0.9,
        )
        community_attrs = _default_community_attrs()

        members = ["p1"]
        graph = _make_graph_with_org_and_community(
            org_attrs,
            community_attrs,
            add_membership=True,
            member_ids=members,
        )
        graph.nodes["comm_1"].update({"member_node_ids": members})

        delta = compute_consciousness_delta(
            org_attrs,
            "comm_1",
            ActionType.EDUCATE,
            graph,
            defines,
            org_defines,
        )

        assert delta is not None
        # With 0.9 legitimacy, effect should be significant
        assert abs(delta.collective_identity_delta) > 0.0

    def test_business_uses_employment_share(self) -> None:
        """Business credibility = employment_count / community_workforce."""
        defines = OODADefines()
        org_defines = OrganizationDefines()
        org_attrs = _default_org_attrs(
            org_type=OrgType.BUSINESS.value,
            employment_count=50,
            community_workforce=100,
        )
        community_attrs = _default_community_attrs()

        members = ["p1"]
        graph = _make_graph_with_org_and_community(
            org_attrs,
            community_attrs,
            add_membership=True,
            member_ids=members,
        )
        graph.nodes["comm_1"].update({"member_node_ids": members})

        delta = compute_consciousness_delta(
            org_attrs,
            "comm_1",
            ActionType.EDUCATE,
            graph,
            defines,
            org_defines,
        )

        assert delta is not None
        assert abs(delta.collective_identity_delta) > 0.0

    def test_business_zero_workforce_zero_credibility(self) -> None:
        """Business with zero workforce has zero credibility."""
        defines = OODADefines()
        org_defines = OrganizationDefines()
        org_attrs = _default_org_attrs(
            org_type=OrgType.BUSINESS.value,
            employment_count=50,
            community_workforce=0,
        )
        community_attrs = _default_community_attrs()
        graph = _make_graph_with_org_and_community(org_attrs, community_attrs)

        delta = compute_consciousness_delta(
            org_attrs,
            "comm_1",
            ActionType.EDUCATE,
            graph,
            defines,
            org_defines,
        )

        # Zero workforce → credibility = 0.0
        # But action_base != 0 so we still get a ConsciousnessDelta (just zero values)
        # Actually with credibility=0, effective_credibility = 0*0.01 = 0
        # base_delta = modifier * cadre * cohesion * 0 = 0
        # scaled = 0 * action_base = 0
        assert delta is not None
        assert delta.collective_identity_delta == 0.0

    def test_state_apparatus_sovereign_credibility(self) -> None:
        """StateApparatus SOVEREIGN uses credibility_sovereign (0.8)."""
        defines = OODADefines()
        org_defines = OrganizationDefines()
        org_attrs = _default_org_attrs(
            org_type=OrgType.STATE_APPARATUS.value,
            legal_standing="sovereign",
        )
        community_attrs = _default_community_attrs()

        members = ["p1"]
        graph = _make_graph_with_org_and_community(
            org_attrs,
            community_attrs,
            add_membership=True,
            member_ids=members,
        )
        graph.nodes["comm_1"].update({"member_node_ids": members})

        delta = compute_consciousness_delta(
            org_attrs,
            "comm_1",
            ActionType.EDUCATE,
            graph,
            defines,
            org_defines,
        )

        assert delta is not None
        assert abs(delta.collective_identity_delta) > 0.0
