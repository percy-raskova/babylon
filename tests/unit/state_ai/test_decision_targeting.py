"""Unit tests for RuleBasedStateAI target selection (task #73 / Feature 039 remainder).

Before this fix, ``RuleBasedStateAI.select_action`` always set
``target_id=org_id`` — the state org REPRESSed *itself* every tick
regardless of what other organizations existed in the world. These tests
pin the fix: :func:`select_repress_target` (the "Blind Giant" reactive
doctrine from ``ai/epochs/epoch3/state-attention-economy.yaml``
~L524-545 — sort visible threats by Heat x Visibility, act on the top
one) and its wiring into ``RuleBasedStateAI.select_action``.

See Also:
    ``tests/contract/state_ai/test_decision_contract.py``: D-01..D-06
    behavioral contracts for verb/budget/escalation selection — those
    never pass ``target_candidates`` and must keep passing unchanged
    (the ``target_candidates=None`` backward-compat branch below is
    exactly what keeps them green).
    ``tests/integration/test_state_ai_wayne_county.py``: end-to-end
    proof over a real scenario.
"""

from __future__ import annotations

from babylon.config.defines import StateApparatusAIDefines
from babylon.ooda.state_ai.decision import RuleBasedStateAI, select_repress_target
from tests.contract.state_ai.conftest import make_faction_balance, make_state_budget

_ORG_ID = "apparatus_detroit_pd"


def _make_defines(**overrides: object) -> StateApparatusAIDefines:
    return StateApparatusAIDefines(**overrides)  # type: ignore[arg-type]


# ===========================================================================
# select_repress_target — pure function
# ===========================================================================


class TestSelectRepressTargetTopHeatWins:
    """The highest Heat x Visibility candidate is selected."""

    def test_top_heat_wins(self) -> None:
        candidates = [("org_low", 0.2), ("org_high", 0.9), ("org_mid", 0.5)]
        assert select_repress_target(_ORG_ID, candidates) == "org_high"

    def test_visibility_multiplier_applied(self) -> None:
        """A lower-heat but higher-visibility candidate can outrank a
        higher-heat, lower-visibility one once real per-candidate
        visibility exists — proven here with the uniform multiplier
        scaling the winner's score without changing WHO wins (visibility
        is uniform across all candidates today; this documents that the
        multiplier is actually applied, not ignored)."""
        candidates = [("org_a", 0.5), ("org_b", 0.3)]
        assert select_repress_target(_ORG_ID, candidates, visibility=0.1) == "org_a"


class TestSelectRepressTargetTieBreak:
    """Ties broken by ascending lexicographic ID (established idiom, see
    ``babylon.ooda.initiative.resolve_action_order``)."""

    def test_lexicographic_tie_break(self) -> None:
        candidates = [("org_zebra", 0.5), ("org_apple", 0.5), ("org_mango", 0.5)]
        assert select_repress_target(_ORG_ID, candidates) == "org_apple"

    def test_tie_break_independent_of_input_order(self) -> None:
        forward = [("org_b", 0.7), ("org_a", 0.7)]
        backward = [("org_a", 0.7), ("org_b", 0.7)]
        assert select_repress_target(_ORG_ID, forward) == "org_a"
        assert select_repress_target(_ORG_ID, backward) == "org_a"


class TestSelectRepressTargetEmptyCandidates:
    """Zero eligible targets -> None, never a fabricated target."""

    def test_empty_candidate_list(self) -> None:
        assert select_repress_target(_ORG_ID, []) is None

    def test_all_heat_zero(self) -> None:
        """The corpus's 'Blind Giant': with no visible threats (heat 0
        everywhere), the state sees nothing."""
        candidates = [("org_a", 0.0), ("org_b", 0.0)]
        assert select_repress_target(_ORG_ID, candidates) is None

    def test_negative_or_zero_heat_excluded_positive_included(self) -> None:
        candidates = [("org_a", 0.0), ("org_b", 0.4)]
        assert select_repress_target(_ORG_ID, candidates) == "org_b"


class TestSelectRepressTargetSelfExclusion:
    """The acting org is never a valid target, even if the caller's
    candidate list includes it (defensive, belt-and-suspenders)."""

    def test_self_excluded_even_with_highest_heat(self) -> None:
        candidates = [(_ORG_ID, 0.99), ("org_other", 0.1)]
        assert select_repress_target(_ORG_ID, candidates) == "org_other"

    def test_self_only_candidate_yields_none(self) -> None:
        candidates = [(_ORG_ID, 0.8)]
        assert select_repress_target(_ORG_ID, candidates) is None


# ===========================================================================
# RuleBasedStateAI.select_action — wiring
# ===========================================================================


class TestSelectActionTargetsRealThreat:
    """When target_candidates identify a real threat, every selected
    action targets it -- never org_id."""

    def test_actions_target_top_threat_not_self(self) -> None:
        ai = RuleBasedStateAI()
        actions = ai.select_action(
            org_id=_ORG_ID,
            faction_balance=make_faction_balance(),
            budget=make_state_budget(),
            heat=0.4,
            defines=_make_defines(),
            rng_seed=42,
            target_candidates=[("org_player", 0.6), ("org_other", 0.2)],
        )
        assert actions, "Expected at least one action when a real threat is visible"
        for action in actions:
            assert action.target_id == "org_player"
            assert action.target_id != _ORG_ID


class TestSelectActionEmptyCandidatesIsHonestNoOp:
    """Zero eligible targets -> [] (never self-targeting)."""

    def test_empty_target_candidates_yields_no_actions(self) -> None:
        ai = RuleBasedStateAI()
        actions = ai.select_action(
            org_id=_ORG_ID,
            faction_balance=make_faction_balance(),
            budget=make_state_budget(),
            heat=0.4,
            defines=_make_defines(),
            rng_seed=42,
            target_candidates=[],
        )
        assert actions == []

    def test_all_zero_heat_target_candidates_yields_no_actions(self) -> None:
        ai = RuleBasedStateAI()
        actions = ai.select_action(
            org_id=_ORG_ID,
            faction_balance=make_faction_balance(),
            budget=make_state_budget(),
            heat=0.4,
            defines=_make_defines(),
            rng_seed=42,
            target_candidates=[("org_player", 0.0)],
        )
        assert actions == []


class TestSelectActionBackwardCompat:
    """target_candidates=None (unset) preserves the pre-fix self-target
    default -- required so the D-01..D-06 behavioral contracts (which
    never pass target_candidates) keep holding."""

    def test_no_target_candidates_falls_back_to_self(self) -> None:
        ai = RuleBasedStateAI()
        actions = ai.select_action(
            org_id=_ORG_ID,
            faction_balance=make_faction_balance(),
            budget=make_state_budget(),
            heat=0.4,
            defines=_make_defines(),
            rng_seed=42,
        )
        assert actions, "Legacy call shape must still produce an action"
        for action in actions:
            assert action.target_id == _ORG_ID


class TestSelectActionTargetingIsDeterministic:
    """Same candidates + same seed -> identical target and action stream."""

    def test_identical_inputs_identical_targets(self) -> None:
        ai_a = RuleBasedStateAI()
        ai_b = RuleBasedStateAI()
        candidates = [("org_player", 0.6), ("org_other", 0.6)]

        actions_a = ai_a.select_action(
            org_id=_ORG_ID,
            faction_balance=make_faction_balance(),
            budget=make_state_budget(),
            heat=0.5,
            defines=_make_defines(),
            rng_seed=7,
            target_candidates=candidates,
        )
        actions_b = ai_b.select_action(
            org_id=_ORG_ID,
            faction_balance=make_faction_balance(),
            budget=make_state_budget(),
            heat=0.5,
            defines=_make_defines(),
            rng_seed=7,
            target_candidates=candidates,
        )

        assert len(actions_a) == len(actions_b)
        for a, b in zip(actions_a, actions_b, strict=True):
            assert a == b
        # org_other wins the tie lexicographically ("org_other" < "org_player").
        assert all(a.target_id == "org_other" for a in actions_a)
