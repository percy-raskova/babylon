"""Tests for NPC action selection stub (Feature 032).

Verifies priority-based action selection and AP constraints.
"""

from __future__ import annotations

from babylon.config.defines import OODADefines
from babylon.models.enums import ActionType, OrgType
from babylon.ooda.npc_stub import select_npc_actions


class TestNPCPrioritySelection:
    """Priority queue selects actions by org type."""

    def test_state_apparatus_priorities(self) -> None:
        defines = OODADefines()
        actions = select_npc_actions(
            org_id="fbi",
            org_attrs={
                "org_type": OrgType.STATE_APPARATUS.value,
                "ooda_profile": {"action_points": 10},
            },
            target_id="community_1",
            defines=defines,
        )
        # Should select highest priority actions first
        assert len(actions) > 0
        assert actions[0].action_type == ActionType.SURVEIL

    def test_political_faction_priorities(self) -> None:
        defines = OODADefines()
        actions = select_npc_actions(
            org_id="rev_party",
            org_attrs={
                "org_type": OrgType.POLITICAL_FACTION.value,
                "ooda_profile": {"action_points": 10},
            },
            target_id="community_1",
            defines=defines,
        )
        assert len(actions) > 0
        assert actions[0].action_type == ActionType.EDUCATE

    def test_civil_society_priorities(self) -> None:
        defines = OODADefines()
        actions = select_npc_actions(
            org_id="church",
            org_attrs={
                "org_type": OrgType.CIVIL_SOCIETY.value,
                "ooda_profile": {"action_points": 10},
            },
            target_id="community_1",
            defines=defines,
        )
        assert len(actions) > 0
        assert actions[0].action_type == ActionType.PROVIDE_SERVICE

    def test_business_priorities(self) -> None:
        defines = OODADefines()
        actions = select_npc_actions(
            org_id="corp",
            org_attrs={
                "org_type": OrgType.BUSINESS.value,
                "ooda_profile": {"action_points": 5},
            },
            target_id="territory_1",
            defines=defines,
        )
        assert len(actions) > 0
        assert actions[0].action_type == ActionType.EMPLOY


class TestAPConstraints:
    """Action points limit action selection."""

    def test_ap_respected(self) -> None:
        """With only 1 AP, can only afford 1-cost actions."""
        defines = OODADefines()
        actions = select_npc_actions(
            org_id="rev_party",
            org_attrs={
                "org_type": OrgType.POLITICAL_FACTION.value,
                "ooda_profile": {"action_points": 1},
            },
            target_id="community_1",
            defines=defines,
        )
        total_cost = sum(a.action_point_cost for a in actions)
        assert total_cost <= 1

    def test_zero_ap_no_actions(self) -> None:
        defines = OODADefines()
        actions = select_npc_actions(
            org_id="rev_party",
            org_attrs={
                "org_type": OrgType.POLITICAL_FACTION.value,
                "ooda_profile": {"action_points": 0},
            },
            target_id="community_1",
            defines=defines,
        )
        assert len(actions) == 0

    def test_greedy_fill(self) -> None:
        """With enough AP, should select multiple actions."""
        defines = OODADefines()
        actions = select_npc_actions(
            org_id="rev_party",
            org_attrs={
                "org_type": OrgType.POLITICAL_FACTION.value,
                "ooda_profile": {"action_points": 10},
            },
            target_id="community_1",
            defines=defines,
        )
        assert len(actions) > 1

    def test_unknown_org_type_no_actions(self) -> None:
        defines = OODADefines()
        actions = select_npc_actions(
            org_id="unknown",
            org_attrs={
                "org_type": "unknown_type",
                "ooda_profile": {"action_points": 10},
            },
            target_id="community_1",
            defines=defines,
        )
        assert len(actions) == 0

    def test_default_ap_when_no_profile(self) -> None:
        """Should use default AP of 3 when no ooda_profile."""
        defines = OODADefines()
        actions = select_npc_actions(
            org_id="rev_party",
            org_attrs={"org_type": OrgType.POLITICAL_FACTION.value},
            target_id="community_1",
            defines=defines,
        )
        total_cost = sum(a.action_point_cost for a in actions)
        assert total_cost <= 3
