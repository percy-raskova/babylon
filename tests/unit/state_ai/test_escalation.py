"""Unit tests for escalation scoring and faction objective functions (Feature 039, T029).

Tests the escalation ladder rank lookup, heat-to-escalation scoring,
faction-specific objective functions, and the weighted score_action combiner.

These are RED-phase tests: they will fail until the escalation and decision
modules are implemented (T030, T033, T034).

See Also:
    ``specs/039-state-apparatus-ai/contracts/state-ai-decision.md``: D-01, D-03, D-04.
    ``src/babylon/ooda/state_ai/escalation.py``: Escalation rank and heat scoring.
    ``src/babylon/ooda/state_ai/decision.py``: Faction objectives and score_action.
"""

from __future__ import annotations

import pytest
from tests.constants import TestConstants
from tests.unit.state_ai.conftest import make_faction_balance, make_state_action

from babylon.config.defines import GameDefines, StateApparatusAIDefines
from babylon.models.enums import StateActionType, StateFaction
from babylon.ooda.state_ai.decision import (
    finance_capital_objective,
    score_action,
    security_state_objective,
    settler_populist_objective,
)
from babylon.ooda.state_ai.escalation import (
    compute_heat_escalation_score,
    get_escalation_rank,
)

TC = TestConstants


# =============================================================================
# Helpers
# =============================================================================


def _defines() -> StateApparatusAIDefines:
    """Load default state AI defines."""
    return GameDefines().state_ai


def _ladder_max_rank() -> int:
    """Return the highest valid rank in the escalation ladder (0-indexed)."""
    return len(_defines().escalation_ladder) - 1


# =============================================================================
# TestGetEscalationRank
# =============================================================================


class TestGetEscalationRank:
    """T029: Escalation ladder rank lookup for sub-verbs."""

    def test_propagandize_is_lowest_rank(self) -> None:
        """PROPAGANDIZE sits at the bottom of the escalation ladder (rank 0)."""
        defines = _defines()
        rank = get_escalation_rank(StateActionType.PROPAGANDIZE, defines)
        assert rank == 0, f"PROPAGANDIZE should be rank 0 (lowest), got {rank}"

    def test_scorched_earth_is_highest_rank(self) -> None:
        """SCORCHED_EARTH sits at the top of the escalation ladder."""
        defines = _defines()
        rank = get_escalation_rank(StateActionType.SCORCHED_EARTH, defines)
        expected = _ladder_max_rank()
        assert rank == expected, f"SCORCHED_EARTH should be rank {expected} (highest), got {rank}"

    def test_raid_higher_than_bribe(self) -> None:
        """RAID is more escalatory than BRIBE (higher rank)."""
        defines = _defines()
        raid_rank = get_escalation_rank(StateActionType.RAID, defines)
        bribe_rank = get_escalation_rank(StateActionType.BRIBE, defines)
        assert raid_rank > bribe_rank, (
            f"RAID rank ({raid_rank}) should exceed BRIBE rank ({bribe_rank})"
        )

    def test_unknown_verb_returns_negative(self) -> None:
        """A top-level verb (e.g. REPRESS) is not a sub-verb on the ladder.

        get_escalation_rank should return -1 for items not in the ladder.
        """
        defines = _defines()
        rank = get_escalation_rank(StateActionType.REPRESS, defines)
        assert rank == -1, f"Top-level verb REPRESS should return -1, got {rank}"

    def test_ladder_order_matches_defines(self) -> None:
        """Ranks are monotonically increasing through the configured ladder.

        Walking the escalation_ladder list, each successive sub-verb must
        have a rank exactly 1 higher than the previous.
        """
        defines = _defines()
        previous_rank = -1
        max_iterations = len(defines.escalation_ladder)
        for idx in range(max_iterations):
            sub_verb_str = defines.escalation_ladder[idx]
            sub_verb = StateActionType(sub_verb_str)
            rank = get_escalation_rank(sub_verb, defines)
            assert rank == idx, (
                f"Ladder position {idx} ({sub_verb_str}) has rank {rank}, expected {idx}"
            )
            assert rank > previous_rank, (
                f"Rank at position {idx} ({rank}) should exceed previous rank ({previous_rank})"
            )
            previous_rank = rank


# =============================================================================
# TestComputeHeatEscalationScore
# =============================================================================


class TestComputeHeatEscalationScore:
    """T029: Heat-to-escalation scoring — higher heat prefers higher ranks."""

    def test_high_heat_prefers_high_rank(self) -> None:
        """At heat=0.9, a high-rank verb scores better than a low-rank verb."""
        max_rank = _ladder_max_rank()
        high_rank = max_rank
        low_rank = 0

        high_score = compute_heat_escalation_score(
            heat=0.9,
            escalation_rank=high_rank,
            max_rank=max_rank,
        )
        low_score = compute_heat_escalation_score(
            heat=0.9,
            escalation_rank=low_rank,
            max_rank=max_rank,
        )
        assert high_score > low_score, (
            f"At heat=0.9, rank {high_rank} score ({high_score}) should "
            f"exceed rank {low_rank} score ({low_score})"
        )

    def test_low_heat_prefers_low_rank(self) -> None:
        """At heat=0.1, a low-rank verb scores better than a high-rank verb."""
        max_rank = _ladder_max_rank()
        high_rank = max_rank
        low_rank = 0

        low_rank_score = compute_heat_escalation_score(
            heat=0.1,
            escalation_rank=low_rank,
            max_rank=max_rank,
        )
        high_rank_score = compute_heat_escalation_score(
            heat=0.1,
            escalation_rank=high_rank,
            max_rank=max_rank,
        )
        assert low_rank_score > high_rank_score, (
            f"At heat=0.1, rank {low_rank} score ({low_rank_score}) should "
            f"exceed rank {high_rank} score ({high_rank_score})"
        )

    def test_zero_heat_zero_rank_baseline(self) -> None:
        """At heat=0.0 and rank=0, score should be positive (baseline)."""
        max_rank = _ladder_max_rank()
        score = compute_heat_escalation_score(
            heat=0.0,
            escalation_rank=0,
            max_rank=max_rank,
        )
        assert score > 0.0, f"Baseline score at heat=0.0, rank=0 should be positive, got {score}"

    def test_score_is_bounded(self) -> None:
        """All scores should remain within a reasonable bounded range."""
        max_rank = _ladder_max_rank()
        scores: list[float] = []
        # Sweep all combinations of heat and rank
        heat_values = [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
        rank_values = list(range(max_rank + 1))
        max_iterations = len(heat_values) * len(rank_values)
        iteration = 0
        for heat in heat_values:
            for rank in rank_values:
                if iteration >= max_iterations:
                    break
                score = compute_heat_escalation_score(
                    heat=heat,
                    escalation_rank=rank,
                    max_rank=max_rank,
                )
                scores.append(score)
                iteration += 1

        # All scores should be non-negative and bounded above by some
        # reasonable maximum (e.g., 10.0 — exact bound is implementation detail)
        for score in scores:
            assert score >= 0.0, f"Score should be non-negative, got {score}"
        max_score = max(scores)
        assert max_score <= 10.0, f"Maximum score ({max_score}) should be bounded by 10.0"


# =============================================================================
# TestFinanceCapitalObjective
# =============================================================================


class TestFinanceCapitalObjective:
    """T029: Finance-Capital faction objective function.

    Finance-Capital prefers CO_OPT, DEVELOP, ADMINISTER.
    Dislikes REPRESS (destabilizes extraction conditions).
    """

    def test_co_opt_scores_higher_than_repress(self) -> None:
        """At low heat, CO_OPT.BRIBE should outscore REPRESS.RAID.

        Finance-Capital prefers co-optation over repression because
        repression destabilizes the investment environment.
        """
        co_opt_action = make_state_action(
            verb=StateActionType.CO_OPT,
            sub_verb=StateActionType.BRIBE,
            budget_cost=5.0,
            thread_cost=0,
            legitimacy_cost=-0.01,
            faction_alignment=StateFaction.FINANCE_CAPITAL,
        )
        repress_action = make_state_action(
            verb=StateActionType.REPRESS,
            sub_verb=StateActionType.RAID,
            budget_cost=10.0,
            thread_cost=1,
            legitimacy_cost=-0.05,
            faction_alignment=StateFaction.SECURITY_STATE,
        )
        low_heat = 0.2
        co_opt_score = finance_capital_objective(co_opt_action, low_heat)
        repress_score = finance_capital_objective(repress_action, low_heat)
        assert co_opt_score > repress_score, (
            f"FC: CO_OPT.BRIBE ({co_opt_score}) should outscore "
            f"REPRESS.RAID ({repress_score}) at low heat"
        )

    def test_develop_scores_well(self) -> None:
        """DEVELOP.INVEST should get a positive score from Finance-Capital.

        Investment improves extraction efficiency — aligned with FC interests.
        """
        invest_action = make_state_action(
            verb=StateActionType.DEVELOP,
            sub_verb=StateActionType.INVEST,
            budget_cost=8.0,
            thread_cost=0,
            legitimacy_cost=0.01,
            faction_alignment=StateFaction.FINANCE_CAPITAL,
        )
        score = finance_capital_objective(invest_action, heat=0.3)
        assert score > 0.0, f"FC: DEVELOP.INVEST should have positive score, got {score}"

    def test_withdraw_scores_poorly(self) -> None:
        """WITHDRAW.SCORCHED_EARTH should score poorly for Finance-Capital.

        Scorched earth destroys the material base needed for extraction.
        """
        scorched_action = make_state_action(
            verb=StateActionType.WITHDRAW,
            sub_verb=StateActionType.SCORCHED_EARTH,
            budget_cost=15.0,
            thread_cost=0,
            legitimacy_cost=-0.1,
            faction_alignment=StateFaction.SETTLER_POPULIST,
        )
        # Compare against a positive-scoring action to show SCORCHED_EARTH
        # scores poorly (negative or at least much lower)
        invest_action = make_state_action(
            verb=StateActionType.DEVELOP,
            sub_verb=StateActionType.INVEST,
            budget_cost=8.0,
            thread_cost=0,
            legitimacy_cost=0.01,
            faction_alignment=StateFaction.FINANCE_CAPITAL,
        )
        scorched_score = finance_capital_objective(scorched_action, heat=0.5)
        invest_score = finance_capital_objective(invest_action, heat=0.5)
        assert scorched_score < invest_score, (
            f"FC: SCORCHED_EARTH ({scorched_score}) should score lower than INVEST ({invest_score})"
        )


# =============================================================================
# TestSecurityStateObjective
# =============================================================================


class TestSecurityStateObjective:
    """T029: Security-State faction objective function.

    Security-State prefers REPRESS, RESEARCH.
    Higher heat increases REPRESS scores (institutional incentive to
    maintain threat perception).
    """

    def test_repress_scores_higher_at_high_heat(self) -> None:
        """At heat=0.8, REPRESS.RAID should score well for Security-State."""
        raid_action = make_state_action(
            verb=StateActionType.REPRESS,
            sub_verb=StateActionType.RAID,
            budget_cost=10.0,
            thread_cost=1,
            legitimacy_cost=-0.05,
            faction_alignment=StateFaction.SECURITY_STATE,
        )
        high_heat_score = security_state_objective(raid_action, heat=0.8)
        # At high heat, SS should score REPRESS positively
        assert high_heat_score > 0.0, (
            f"SS: REPRESS.RAID at heat=0.8 should be positive, got {high_heat_score}"
        )

    def test_repress_scores_lower_at_low_heat(self) -> None:
        """At heat=0.1, REPRESS.RAID should score lower than at heat=0.8.

        Without active threat, the security state has less justification
        for aggressive action.
        """
        raid_action = make_state_action(
            verb=StateActionType.REPRESS,
            sub_verb=StateActionType.RAID,
            budget_cost=10.0,
            thread_cost=1,
            legitimacy_cost=-0.05,
            faction_alignment=StateFaction.SECURITY_STATE,
        )
        low_heat_score = security_state_objective(raid_action, heat=0.1)
        high_heat_score = security_state_objective(raid_action, heat=0.8)
        assert high_heat_score > low_heat_score, (
            f"SS: RAID at heat=0.8 ({high_heat_score}) should outscore "
            f"RAID at heat=0.1 ({low_heat_score})"
        )

    def test_surveil_scores_well(self) -> None:
        """REPRESS.SURVEIL should always score decently for Security-State.

        Surveillance is core to the apparatus's self-justification and
        resource acquisition, regardless of heat level.
        """
        surveil_action = make_state_action(
            verb=StateActionType.REPRESS,
            sub_verb=StateActionType.SURVEIL,
            budget_cost=3.0,
            thread_cost=1,
            legitimacy_cost=-0.005,
            faction_alignment=StateFaction.SECURITY_STATE,
        )
        # Should score positively at both low and moderate heat
        low_score = security_state_objective(surveil_action, heat=0.2)
        mid_score = security_state_objective(surveil_action, heat=0.5)
        assert low_score > 0.0, f"SS: SURVEIL at heat=0.2 should be positive, got {low_score}"
        assert mid_score > 0.0, f"SS: SURVEIL at heat=0.5 should be positive, got {mid_score}"


# =============================================================================
# TestSettlerPopulistObjective
# =============================================================================


class TestSettlerPopulistObjective:
    """T029: Settler-Populist faction objective function.

    Settler-Populist prefers DEVELOP.DISPLACE, CO_OPT.DIVIDE.
    Dislikes WITHDRAW (abandons settler interests).
    """

    def test_displace_scores_high(self) -> None:
        """DEVELOP.DISPLACE is core to settler-populist interests.

        Displacement secures territory for the settler nation and
        reinforces the material base of imperial rent distribution.
        """
        displace_action = make_state_action(
            verb=StateActionType.DEVELOP,
            sub_verb=StateActionType.DISPLACE,
            budget_cost=10.0,
            thread_cost=0,
            legitimacy_cost=-0.03,
            faction_alignment=StateFaction.SETTLER_POPULIST,
        )
        score = settler_populist_objective(displace_action, heat=0.4)
        assert score > 0.0, f"SP: DISPLACE should have positive score, got {score}"

    def test_divide_scores_well(self) -> None:
        """CO_OPT.DIVIDE prevents cross-line solidarity — key SP interest.

        Divide-and-conquer prevents multiracial class solidarity
        that would threaten the imperial rent distribution.
        """
        divide_action = make_state_action(
            verb=StateActionType.CO_OPT,
            sub_verb=StateActionType.DIVIDE,
            budget_cost=5.0,
            thread_cost=0,
            legitimacy_cost=-0.01,
            faction_alignment=StateFaction.SETTLER_POPULIST,
        )
        score = settler_populist_objective(divide_action, heat=0.3)
        assert score > 0.0, f"SP: DIVIDE should have positive score, got {score}"

    def test_withdraw_scores_lowest(self) -> None:
        """WITHDRAW actions score poorly for Settler-Populist.

        Withdrawal represents abandonment of settler territorial claims.
        Even strategic withdrawal is unacceptable to the settler base.
        """
        withdraw_action = make_state_action(
            verb=StateActionType.WITHDRAW,
            sub_verb=StateActionType.STRATEGIC_WITHDRAWAL,
            budget_cost=2.0,
            thread_cost=0,
            legitimacy_cost=-0.02,
            faction_alignment=StateFaction.FINANCE_CAPITAL,
        )
        displace_action = make_state_action(
            verb=StateActionType.DEVELOP,
            sub_verb=StateActionType.DISPLACE,
            budget_cost=10.0,
            thread_cost=0,
            legitimacy_cost=-0.03,
            faction_alignment=StateFaction.SETTLER_POPULIST,
        )
        withdraw_score = settler_populist_objective(withdraw_action, heat=0.4)
        displace_score = settler_populist_objective(displace_action, heat=0.4)
        assert withdraw_score < displace_score, (
            f"SP: WITHDRAW ({withdraw_score}) should score lower than DISPLACE ({displace_score})"
        )


# =============================================================================
# TestScoreAction
# =============================================================================


class TestScoreAction:
    """T029: Weighted faction objective scoring via score_action.

    score_action computes: fc_weight * fc_obj + ss_weight * ss_obj + sp_weight * sp_obj
    """

    def test_weighted_sum_matches_manual_calculation(self) -> None:
        """score_action result equals manual weighted sum of faction objectives."""
        balance = make_faction_balance(
            finance_capital=0.45,
            security_state=0.30,
            settler_populist=0.25,
        )
        action = make_state_action(
            verb=StateActionType.REPRESS,
            sub_verb=StateActionType.RAID,
            budget_cost=10.0,
            thread_cost=1,
            legitimacy_cost=-0.05,
            faction_alignment=StateFaction.SECURITY_STATE,
        )
        heat = 0.5

        # Compute individual faction scores
        fc_score = finance_capital_objective(action, heat)
        ss_score = security_state_objective(action, heat)
        sp_score = settler_populist_objective(action, heat)

        # Manual weighted sum
        expected = (
            balance.finance_capital * fc_score
            + balance.security_state * ss_score
            + balance.settler_populist * sp_score
        )

        actual = score_action(action, balance, heat)
        assert actual == pytest.approx(expected, abs=1e-9), (
            f"score_action ({actual}) should equal weighted sum ({expected}): "
            f"FC={fc_score}*{balance.finance_capital} + "
            f"SS={ss_score}*{balance.security_state} + "
            f"SP={sp_score}*{balance.settler_populist}"
        )

    def test_ss_dominant_prefers_repress(self) -> None:
        """With Security-State dominant (SS=0.6), REPRESS.RAID outscores CO_OPT.BRIBE.

        This is the core behavioral contract: factional balance determines
        action preference (D-01 contract).
        """
        ss_dominant = make_faction_balance(
            finance_capital=0.15,
            security_state=0.60,
            settler_populist=0.25,
        )
        raid_action = make_state_action(
            verb=StateActionType.REPRESS,
            sub_verb=StateActionType.RAID,
            budget_cost=10.0,
            thread_cost=1,
            legitimacy_cost=-0.05,
            faction_alignment=StateFaction.SECURITY_STATE,
        )
        bribe_action = make_state_action(
            verb=StateActionType.CO_OPT,
            sub_verb=StateActionType.BRIBE,
            budget_cost=5.0,
            thread_cost=0,
            legitimacy_cost=-0.01,
            faction_alignment=StateFaction.FINANCE_CAPITAL,
        )
        heat = 0.6  # Moderate-high heat reinforces SS preference

        raid_score = score_action(raid_action, ss_dominant, heat)
        bribe_score = score_action(bribe_action, ss_dominant, heat)
        assert raid_score > bribe_score, (
            f"SS-dominant: RAID ({raid_score}) should outscore BRIBE ({bribe_score}) at heat={heat}"
        )

    def test_fc_dominant_prefers_co_opt(self) -> None:
        """With Finance-Capital dominant (FC=0.6), CO_OPT.BRIBE outscores REPRESS.RAID.

        The inverse of the SS-dominant test. FC faction prefers stabilizing
        co-optation over destabilizing repression.
        """
        fc_dominant = make_faction_balance(
            finance_capital=0.60,
            security_state=0.15,
            settler_populist=0.25,
        )
        raid_action = make_state_action(
            verb=StateActionType.REPRESS,
            sub_verb=StateActionType.RAID,
            budget_cost=10.0,
            thread_cost=1,
            legitimacy_cost=-0.05,
            faction_alignment=StateFaction.SECURITY_STATE,
        )
        bribe_action = make_state_action(
            verb=StateActionType.CO_OPT,
            sub_verb=StateActionType.BRIBE,
            budget_cost=5.0,
            thread_cost=0,
            legitimacy_cost=-0.01,
            faction_alignment=StateFaction.FINANCE_CAPITAL,
        )
        heat = 0.3  # Low-moderate heat favors FC's preference for stability

        bribe_score = score_action(bribe_action, fc_dominant, heat)
        raid_score = score_action(raid_action, fc_dominant, heat)
        assert bribe_score > raid_score, (
            f"FC-dominant: BRIBE ({bribe_score}) should outscore RAID ({raid_score}) at heat={heat}"
        )
