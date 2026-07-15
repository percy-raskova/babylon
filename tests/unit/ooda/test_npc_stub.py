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


class TestStateAIDispatchGate:
    """Feature 039: ``faction_balance`` gates RuleBasedStateAI dispatch.

    Sibling to ``TestNPCPrioritySelection.test_state_apparatus_priorities``
    (no ``faction_balance`` -> legacy priority queue, asserted there) —
    this class asserts the OTHER branch: ``faction_balance`` present ->
    RuleBasedStateAI. Until wayne_county seeded this attribute
    (``babylon.engine.scenarios._legacy_wayne._create_state_apparatus_org``),
    no scenario ever set it, so this branch had never once executed.
    """

    def test_faction_balance_present_dispatches_to_state_ai(self) -> None:
        defines = OODADefines()
        actions = select_npc_actions(
            org_id="detroit_pd",
            org_attrs={
                "org_type": OrgType.STATE_APPARATUS.value,
                "heat": 0.3,
                "faction_balance": {
                    "finance_capital": 0.2,
                    "security_state": 0.6,
                    "settler_populist": 0.2,
                    "stability": 0.5,
                    "legitimacy": 0.5,
                },
                "rng_seed": 0,
            },
            target_id="community_1",
            defines=defines,
        )
        # Only RuleBasedStateAI's legacy-compat wrapper sets budget_cost;
        # the static priority queue never touches that field (stays at the
        # Action model default of 0.0).
        assert len(actions) == 1
        assert actions[0].budget_cost > 0.0

    def test_faction_balance_absent_falls_through_to_legacy(self) -> None:
        """Control: identical org_type, no faction_balance -> legacy path."""
        defines = OODADefines()
        actions = select_npc_actions(
            org_id="detroit_pd",
            org_attrs={
                "org_type": OrgType.STATE_APPARATUS.value,
                "heat": 0.3,
                "ooda_profile": {"action_points": 10},
            },
            target_id="community_1",
            defines=defines,
        )
        assert len(actions) > 0
        assert all(a.budget_cost == 0.0 for a in actions)

    def test_invalid_faction_balance_falls_through_to_legacy(self) -> None:
        """A malformed faction_balance (wrong type) logs a warning and falls
        through rather than crashing — asserted directly since it's the
        third branch of ``_try_state_ai_dispatch``'s isinstance check."""
        defines = OODADefines()
        actions = select_npc_actions(
            org_id="detroit_pd",
            org_attrs={
                "org_type": OrgType.STATE_APPARATUS.value,
                "heat": 0.3,
                "faction_balance": "not-a-faction-balance",
                "ooda_profile": {"action_points": 10},
            },
            target_id="community_1",
            defines=defines,
        )
        assert len(actions) > 0
        assert all(a.budget_cost == 0.0 for a in actions)
