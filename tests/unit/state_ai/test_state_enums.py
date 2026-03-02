"""Unit tests for State Apparatus AI enums (Feature 039, T004-T005, T007-T009).

Tests enum membership, VERB_CHILDREN integrity, and StateAction hierarchy
validation.
"""

from __future__ import annotations

import pytest

from babylon.models.entities.state_apparatus_ai import (
    ALL_SUB_VERBS,
    TOP_LEVEL_VERBS,
    VERB_CHILDREN,
    StateAction,
    get_parent_verb,
)
from babylon.models.enums import (
    EdgeType,
    EventType,
    StateActionType,
    StateFaction,
    SurveillanceMethod,
    ThreadPhase,
)


class TestStateFaction:
    """T004: StateFaction enum membership."""

    def test_has_three_members(self) -> None:
        assert len(StateFaction) == 3

    def test_finance_capital(self) -> None:
        assert StateFaction.FINANCE_CAPITAL.value == "finance_capital"

    def test_security_state(self) -> None:
        assert StateFaction.SECURITY_STATE.value == "security_state"

    def test_settler_populist(self) -> None:
        assert StateFaction.SETTLER_POPULIST.value == "settler_populist"

    def test_is_str_enum(self) -> None:
        assert isinstance(StateFaction.FINANCE_CAPITAL, str)


class TestStateActionType:
    """T005: StateActionType enum — 6 top-level + sub-verbs."""

    def test_six_top_level_verbs(self) -> None:
        expected = {"ADMINISTER", "DEVELOP", "RESEARCH", "CO_OPT", "REPRESS", "WITHDRAW"}
        actual = {v.name for v in TOP_LEVEL_VERBS}
        assert actual == expected

    def test_administer_sub_verbs(self) -> None:
        expected = {
            StateActionType.FUND,
            StateActionType.STAFF,
            StateActionType.LEGISLATE,
            StateActionType.AUDIT,
            StateActionType.REVOKE,
        }
        assert VERB_CHILDREN[StateActionType.ADMINISTER] == expected

    def test_develop_sub_verbs(self) -> None:
        expected = {
            StateActionType.INVEST,
            StateActionType.REZONE,
            StateActionType.DISPLACE,
            StateActionType.NEGLECT,
        }
        assert VERB_CHILDREN[StateActionType.DEVELOP] == expected

    def test_research_sub_verbs(self) -> None:
        expected = {
            StateActionType.PURSUE_TECH,
            StateActionType.DEPLOY_TECH,
        }
        assert VERB_CHILDREN[StateActionType.RESEARCH] == expected

    def test_co_opt_sub_verbs(self) -> None:
        expected = {
            StateActionType.BRIBE,
            StateActionType.PROPAGANDIZE,
            StateActionType.INCORPORATE,
            StateActionType.DIVIDE,
        }
        assert VERB_CHILDREN[StateActionType.CO_OPT] == expected

    def test_repress_sub_verbs(self) -> None:
        expected = {
            StateActionType.SURVEIL,
            StateActionType.INFILTRATE,
            StateActionType.RAID,
            StateActionType.PROSECUTE,
            StateActionType.LIQUIDATE,
        }
        assert VERB_CHILDREN[StateActionType.REPRESS] == expected

    def test_withdraw_sub_verbs(self) -> None:
        expected = {
            StateActionType.STRATEGIC_WITHDRAWAL,
            StateActionType.TACTICAL_RETREAT,
            StateActionType.SCORCHED_EARTH,
        }
        assert VERB_CHILDREN[StateActionType.WITHDRAW] == expected

    def test_all_sub_verbs_covered(self) -> None:
        """Every non-top-level enum member appears in exactly one parent."""
        all_children = frozenset().union(*VERB_CHILDREN.values())
        non_top = {v for v in StateActionType if v not in TOP_LEVEL_VERBS}
        assert non_top == all_children

    def test_no_overlap_between_verb_groups(self) -> None:
        """No sub-verb appears under multiple parents."""
        seen: set[StateActionType] = set()
        for children in VERB_CHILDREN.values():
            overlap = seen & children
            assert not overlap, f"Overlapping sub-verbs: {overlap}"
            seen |= children

    def test_top_level_not_in_sub_verbs(self) -> None:
        assert frozenset() == TOP_LEVEL_VERBS & ALL_SUB_VERBS

    def test_surveil_namespaced(self) -> None:
        """SURVEIL value is namespaced to avoid ActionType.SURVEIL conflict."""
        assert StateActionType.SURVEIL.value == "surveil_state"

    def test_infiltrate_namespaced(self) -> None:
        """INFILTRATE value is namespaced to avoid ActionType.INFILTRATE conflict."""
        assert StateActionType.INFILTRATE.value == "infiltrate_state"


class TestThreadPhase:
    """T007: ThreadPhase enum membership."""

    def test_has_four_phases(self) -> None:
        assert len(ThreadPhase) == 4

    def test_phase_values(self) -> None:
        expected = {"dormant", "monitoring", "active_investigation", "disruption"}
        actual = {p.value for p in ThreadPhase}
        assert actual == expected


class TestSurveillanceMethod:
    """T007: SurveillanceMethod enum membership."""

    def test_has_five_methods(self) -> None:
        assert len(SurveillanceMethod) == 5

    def test_method_values(self) -> None:
        expected = {"signals", "financial", "social_media", "informant", "physical"}
        actual = {m.value for m in SurveillanceMethod}
        assert actual == expected


class TestEdgeTypeAdditions:
    """T013: EdgeType additions for Feature 039."""

    def test_targets_edge(self) -> None:
        assert EdgeType.TARGETS.value == "targets"

    def test_owned_by_edge(self) -> None:
        assert EdgeType.OWNED_BY.value == "owned_by"

    def test_jurisdiction_edge(self) -> None:
        assert EdgeType.JURISDICTION.value == "jurisdiction"


class TestEventTypeAdditions:
    """T012: EventType additions for Feature 039."""

    def test_state_action_executed(self) -> None:
        assert EventType.STATE_ACTION_EXECUTED.value == "state_action_executed"

    def test_fascist_convergence(self) -> None:
        assert EventType.FASCIST_CONVERGENCE.value == "fascist_convergence"

    def test_faction_shift(self) -> None:
        assert EventType.FACTION_SHIFT.value == "faction_shift"

    def test_thread_escalation(self) -> None:
        assert EventType.THREAD_ESCALATION.value == "thread_escalation"

    def test_legal_framework_enacted(self) -> None:
        assert EventType.LEGAL_FRAMEWORK_ENACTED.value == "legal_framework_enacted"

    def test_legal_framework_revoked(self) -> None:
        assert EventType.LEGAL_FRAMEWORK_REVOKED.value == "legal_framework_revoked"


class TestGetParentVerb:
    """T014: get_parent_verb helper."""

    def test_raid_parent_is_repress(self) -> None:
        assert get_parent_verb(StateActionType.RAID) == StateActionType.REPRESS

    def test_bribe_parent_is_co_opt(self) -> None:
        assert get_parent_verb(StateActionType.BRIBE) == StateActionType.CO_OPT

    def test_fund_parent_is_administer(self) -> None:
        assert get_parent_verb(StateActionType.FUND) == StateActionType.ADMINISTER

    def test_top_level_returns_none(self) -> None:
        assert get_parent_verb(StateActionType.REPRESS) is None

    def test_invest_parent_is_develop(self) -> None:
        assert get_parent_verb(StateActionType.INVEST) == StateActionType.DEVELOP


class TestStateActionVerbHierarchy:
    """T009: StateAction model validator for verb-sub_verb consistency."""

    def test_valid_repress_surveil(self) -> None:
        action = StateAction(
            verb=StateActionType.REPRESS,
            sub_verb=StateActionType.SURVEIL,
            budget_cost=5.0,
            thread_cost=1,
            legitimacy_cost=-0.01,
            faction_alignment=StateFaction.SECURITY_STATE,
        )
        assert action.verb == StateActionType.REPRESS

    def test_invalid_repress_bribe_rejected(self) -> None:
        """BRIBE is a CO_OPT sub-verb, not a REPRESS sub-verb."""
        with pytest.raises(ValueError, match="not a valid sub-verb"):
            StateAction(
                verb=StateActionType.REPRESS,
                sub_verb=StateActionType.BRIBE,
                budget_cost=5.0,
                thread_cost=0,
                legitimacy_cost=0.0,
                faction_alignment=StateFaction.FINANCE_CAPITAL,
            )

    def test_invalid_sub_verb_as_verb_rejected(self) -> None:
        """Sub-verbs cannot be used as verb field."""
        with pytest.raises(ValueError, match="must be a top-level verb"):
            StateAction(
                verb=StateActionType.RAID,
                sub_verb=StateActionType.SURVEIL,
                budget_cost=5.0,
                thread_cost=0,
                legitimacy_cost=0.0,
                faction_alignment=StateFaction.SECURITY_STATE,
            )

    def test_all_verb_children_pairs_valid(self) -> None:
        """Every valid parent-child pair constructs without error."""
        for parent, children in VERB_CHILDREN.items():
            for child in children:
                action = StateAction(
                    verb=parent,
                    sub_verb=child,
                    budget_cost=0.0,
                    thread_cost=0,
                    legitimacy_cost=0.0,
                    faction_alignment=StateFaction.FINANCE_CAPITAL,
                )
                assert action.verb == parent
                assert action.sub_verb == child
