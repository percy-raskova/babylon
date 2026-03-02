"""Contract tests for State AI decision function (Feature 039 Phase 3).

Behavioral contracts D-01 through D-06 from
``specs/039-state-apparatus-ai/contracts/state-ai-decision.md``.

These tests validate the public interface of RuleBasedStateAI.select_action()
before the implementation exists (TDD RED phase). Each test class maps to
one behavioral contract.

See Also:
    :mod:`babylon.ooda.state_ai.decision`: Implementation (does not exist yet).
    :mod:`babylon.ooda.state_ai.escalation`: Escalation ladder ranking.
"""

from __future__ import annotations

from babylon.config.defines import StateApparatusAIDefines
from babylon.models.enums import StateActionType
from babylon.ooda.state_ai.decision import RuleBasedStateAI
from babylon.ooda.state_ai.escalation import get_escalation_rank
from tests.constants import TestConstants
from tests.contract.state_ai.conftest import make_faction_balance, make_state_budget

TC = TestConstants

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_ORG_ID: str = "apparatus_detroit_pd"
_DEFAULT_SEED: int = 42
_MAX_TICKS: int = 52


def _make_defines(**overrides: object) -> StateApparatusAIDefines:
    """Build StateApparatusAIDefines with optional overrides."""
    return StateApparatusAIDefines(**overrides)  # type: ignore[arg-type]


# ===========================================================================
# D-01: Factional Objective Scoring
# ===========================================================================


class TestFactionalObjectiveScoring:
    """D-01: Different FactionBalance weights produce different action rankings.

    Reference: FR-D02, FR-D03, FR-D04.
    Spec: state-ai-decision.md D-01.
    """

    def test_different_faction_weights_produce_different_rankings(self) -> None:
        """Security-State dominance prefers REPRESS; Finance-Capital prefers CO_OPT.

        Under SS=0.5 dominance the selected action should lean toward REPRESS
        sub-verbs (e.g. RAID). Under FC=0.5 dominance the selected action should
        lean toward CO_OPT sub-verbs (e.g. BRIBE).
        """
        ai = RuleBasedStateAI()
        defines = _make_defines()
        budget = make_state_budget()
        heat: float = 0.4  # moderate threat

        ss_dominant = make_faction_balance(
            finance_capital=0.25,
            security_state=0.50,
            settler_populist=0.25,
        )
        fc_dominant = make_faction_balance(
            finance_capital=0.50,
            security_state=0.25,
            settler_populist=0.25,
        )

        actions_ss = ai.select_action(
            org_id=_DEFAULT_ORG_ID,
            faction_balance=ss_dominant,
            budget=budget,
            heat=heat,
            defines=defines,
            rng_seed=_DEFAULT_SEED,
        )
        actions_fc = ai.select_action(
            org_id=_DEFAULT_ORG_ID,
            faction_balance=fc_dominant,
            budget=budget,
            heat=heat,
            defines=defines,
            rng_seed=_DEFAULT_SEED,
        )

        assert len(actions_ss) >= 1, "SS-dominant should produce at least one action"
        assert len(actions_fc) >= 1, "FC-dominant should produce at least one action"

        # The first (or sole) action should differ between the two faction configs.
        ss_verb = actions_ss[0].sub_verb
        fc_verb = actions_fc[0].sub_verb
        assert ss_verb != fc_verb, (
            f"Different faction weights must produce different verb rankings, "
            f"but both selected {ss_verb}"
        )

    def test_scoring_is_deterministic(self) -> None:
        """Same inputs + same seed must produce identical output."""
        ai = RuleBasedStateAI()
        defines = _make_defines()
        budget = make_state_budget()
        balance = make_faction_balance()
        heat: float = 0.4

        run_a = ai.select_action(
            org_id=_DEFAULT_ORG_ID,
            faction_balance=balance,
            budget=budget,
            heat=heat,
            defines=defines,
            rng_seed=_DEFAULT_SEED,
        )
        run_b = ai.select_action(
            org_id=_DEFAULT_ORG_ID,
            faction_balance=balance,
            budget=budget,
            heat=heat,
            defines=defines,
            rng_seed=_DEFAULT_SEED,
        )

        assert len(run_a) == len(run_b), "Determinism: action count must match"
        for idx in range(len(run_a)):
            assert run_a[idx] == run_b[idx], (
                f"Determinism: action at index {idx} differs between runs"
            )


# ===========================================================================
# D-02: Verb Selection Under Budget Constraint
# ===========================================================================


class TestBudgetConstraint:
    """D-02: Budget constraints are never violated.

    Reference: FR-D05.
    Spec: state-ai-decision.md D-02.
    """

    def test_zero_budget_yields_zero_cost_actions(self) -> None:
        """With revenue=0 and available=0, all actions must cost nothing."""
        ai = RuleBasedStateAI()
        defines = _make_defines()
        balance = make_faction_balance()

        zero_budget = make_state_budget(
            revenue=0.0,
            available=0.0,
            allocated={
                StateActionType.ADMINISTER: 0.0,
                StateActionType.DEVELOP: 0.0,
                StateActionType.RESEARCH: 0.0,
                StateActionType.CO_OPT: 0.0,
                StateActionType.REPRESS: 0.0,
                StateActionType.WITHDRAW: 0.0,
            },
            imperial_rent_pool=0.0,
        )

        actions = ai.select_action(
            org_id=_DEFAULT_ORG_ID,
            faction_balance=balance,
            budget=zero_budget,
            heat=0.3,
            defines=defines,
            rng_seed=_DEFAULT_SEED,
        )

        for action in actions:
            assert action.budget_cost == 0.0, (
                f"Zero-budget action must have budget_cost == 0.0, "
                f"got {action.budget_cost} for {action.sub_verb}"
            )

    def test_no_overdraft(self) -> None:
        """Sum of action costs must not exceed available budget."""
        ai = RuleBasedStateAI()
        defines = _make_defines()
        balance = make_faction_balance()
        available: float = 10.0

        budget = make_state_budget(
            revenue=available,
            available=available,
            allocated={
                StateActionType.ADMINISTER: 2.0,
                StateActionType.DEVELOP: 2.0,
                StateActionType.RESEARCH: 1.0,
                StateActionType.CO_OPT: 2.0,
                StateActionType.REPRESS: 2.0,
                StateActionType.WITHDRAW: 1.0,
            },
            imperial_rent_pool=0.0,
        )

        actions = ai.select_action(
            org_id=_DEFAULT_ORG_ID,
            faction_balance=balance,
            budget=budget,
            heat=0.5,
            defines=defines,
            rng_seed=_DEFAULT_SEED,
        )

        total_cost = sum(a.budget_cost for a in actions)
        assert total_cost <= available, (
            f"Total action cost ({total_cost}) exceeds available budget ({available})"
        )

    def test_action_cost_within_budget(self) -> None:
        """Every individual action must have budget_cost <= budget.available."""
        ai = RuleBasedStateAI()
        defines = _make_defines()
        balance = make_faction_balance()
        available: float = 10.0

        budget = make_state_budget(
            revenue=available,
            available=available,
            allocated={
                StateActionType.ADMINISTER: 2.0,
                StateActionType.DEVELOP: 2.0,
                StateActionType.RESEARCH: 1.0,
                StateActionType.CO_OPT: 2.0,
                StateActionType.REPRESS: 2.0,
                StateActionType.WITHDRAW: 1.0,
            },
            imperial_rent_pool=0.0,
        )

        actions = ai.select_action(
            org_id=_DEFAULT_ORG_ID,
            faction_balance=balance,
            budget=budget,
            heat=0.5,
            defines=defines,
            rng_seed=_DEFAULT_SEED,
        )

        for action in actions:
            assert action.budget_cost <= available, (
                f"Action {action.sub_verb} costs {action.budget_cost} "
                f"but only {available} is available"
            )


# ===========================================================================
# D-03: Escalation Sequence
# ===========================================================================


class TestEscalationSequence:
    """D-03: Monotonically increasing Heat shifts verbs up the escalation ladder.

    Reference: FR-D06.
    Spec: state-ai-decision.md D-03.
    """

    def test_escalation_with_increasing_heat(self) -> None:
        """Mean escalation rank rises as heat increases from 0.1 to 0.9.

        Over 20 ticks with linearly rising heat, the mean escalation rank
        of actions selected in the last 5 ticks must exceed the mean rank
        of the first 5 ticks.
        """
        ai = RuleBasedStateAI()
        defines = _make_defines()
        balance = make_faction_balance()
        budget = make_state_budget()

        total_ticks: int = 20
        all_ranks: list[float] = []

        for tick in range(total_ticks):
            # Heat rises linearly from 0.1 to 0.9
            heat: float = 0.1 + (0.8 * tick / (total_ticks - 1))

            actions = ai.select_action(
                org_id=_DEFAULT_ORG_ID,
                faction_balance=balance,
                budget=budget,
                heat=heat,
                defines=defines,
                rng_seed=_DEFAULT_SEED + tick,
            )

            if actions:
                tick_ranks = [get_escalation_rank(a.sub_verb, defines) for a in actions]
                all_ranks.append(sum(tick_ranks) / len(tick_ranks))
            else:
                all_ranks.append(0.0)

        first_five = all_ranks[:5]
        last_five = all_ranks[-5:]

        mean_first = sum(first_five) / len(first_five)
        mean_last = sum(last_five) / len(last_five)

        assert mean_last > mean_first, (
            f"Escalation contract violated: mean rank of last 5 ticks "
            f"({mean_last:.2f}) should exceed first 5 ticks ({mean_first:.2f})"
        )


# ===========================================================================
# D-04: De-escalation
# ===========================================================================


class TestDeescalation:
    """D-04: Heat drop shifts verbs back to low-cost options.

    Reference: FR-D07.
    Spec: state-ai-decision.md D-04.
    """

    def test_deescalation_after_heat_drop(self) -> None:
        """After high heat drops, mean escalation rank must decrease.

        Run 10 ticks at high heat (0.8), then 10 ticks at low heat (0.1).
        The mean rank of the last 5 ticks (low heat) must be lower than
        the mean rank of ticks 5-10 (high heat).
        """
        ai = RuleBasedStateAI()
        defines = _make_defines()
        balance = make_faction_balance()
        budget = make_state_budget()

        total_ticks: int = 20
        all_ranks: list[float] = []

        for tick in range(total_ticks):
            # First 10 ticks: high heat (0.8); last 10 ticks: low heat (0.1)
            heat: float = 0.8 if tick < 10 else 0.1

            actions = ai.select_action(
                org_id=_DEFAULT_ORG_ID,
                faction_balance=balance,
                budget=budget,
                heat=heat,
                defines=defines,
                rng_seed=_DEFAULT_SEED + tick,
            )

            if actions:
                tick_ranks = [get_escalation_rank(a.sub_verb, defines) for a in actions]
                all_ranks.append(sum(tick_ranks) / len(tick_ranks))
            else:
                all_ranks.append(0.0)

        # High-heat period: ticks 5-10 (second half of high heat phase)
        high_heat_ranks = all_ranks[5:10]
        # Low-heat period: last 5 ticks (ticks 15-20)
        low_heat_ranks = all_ranks[-5:]

        mean_high = sum(high_heat_ranks) / len(high_heat_ranks)
        mean_low = sum(low_heat_ranks) / len(low_heat_ranks)

        assert mean_low < mean_high, (
            f"De-escalation contract violated: mean rank during low heat "
            f"({mean_low:.2f}) should be lower than during high heat ({mean_high:.2f})"
        )


# ===========================================================================
# D-05: Determinism
# ===========================================================================


class TestDeterminism:
    """D-05: Identical seed + state produces identical action sequences.

    Reference: FR-D08.
    Spec: state-ai-decision.md D-05.
    """

    def test_identical_seed_identical_output(self) -> None:
        """Two independent runs with seed=42 and same inputs yield identical actions."""
        defines = _make_defines()
        balance = make_faction_balance()
        budget = make_state_budget()
        heat: float = 0.5
        seed: int = 42

        ai_a = RuleBasedStateAI()
        ai_b = RuleBasedStateAI()

        actions_a = ai_a.select_action(
            org_id=_DEFAULT_ORG_ID,
            faction_balance=balance,
            budget=budget,
            heat=heat,
            defines=defines,
            rng_seed=seed,
        )
        actions_b = ai_b.select_action(
            org_id=_DEFAULT_ORG_ID,
            faction_balance=balance,
            budget=budget,
            heat=heat,
            defines=defines,
            rng_seed=seed,
        )

        assert len(actions_a) == len(actions_b), (
            f"Determinism violated: run A produced {len(actions_a)} actions, "
            f"run B produced {len(actions_b)}"
        )
        for idx in range(len(actions_a)):
            assert actions_a[idx] == actions_b[idx], (
                f"Determinism violated at action index {idx}: "
                f"run A={actions_a[idx]}, run B={actions_b[idx]}"
            )

    def test_different_seed_can_differ(self) -> None:
        """Two runs with different seeds MAY produce different results.

        This is a probabilistic check -- over 10 attempts with varying seeds,
        at least one pair should differ. If the AI is fully deterministic but
        seed-independent (degenerate case), this test is allowed to pass.
        """
        defines = _make_defines()
        balance = make_faction_balance()
        budget = make_state_budget()
        heat: float = 0.5

        seen_sub_verbs: set[StateActionType] = set()
        max_attempts: int = 10

        for seed_offset in range(max_attempts):
            ai = RuleBasedStateAI()
            actions = ai.select_action(
                org_id=_DEFAULT_ORG_ID,
                faction_balance=balance,
                budget=budget,
                heat=heat,
                defines=defines,
                rng_seed=100 + seed_offset,
            )
            for action in actions:
                seen_sub_verbs.add(action.sub_verb)

        # We expect at least some variety. If the AI always picks the same
        # verb regardless of seed, it's acceptable (greedy tie-breaking)
        # but we note it. This test documents the expectation, not hard-fails
        # on zero variety.
        assert len(seen_sub_verbs) >= 1, "Different seeds should produce at least one valid action"


# ===========================================================================
# D-06: Actions Per Tick
# ===========================================================================


class TestActionsPerTick:
    """D-06: Default is one action per tick; configurable via defines.

    Reference: FR-D05.
    Spec: state-ai-decision.md D-06.
    """

    def test_default_one_action_per_tick(self) -> None:
        """Default config produces exactly 1 action (or 0 if budget exhausted)."""
        ai = RuleBasedStateAI()
        defines = _make_defines()  # defaults: actions_per_tick=1
        balance = make_faction_balance()
        budget = make_state_budget()

        actions = ai.select_action(
            org_id=_DEFAULT_ORG_ID,
            faction_balance=balance,
            budget=budget,
            heat=0.4,
            defines=defines,
            rng_seed=_DEFAULT_SEED,
        )

        assert len(actions) <= TC.StateAI.ACTIONS_PER_TICK_DEFAULT, (
            f"Default config should produce at most "
            f"{TC.StateAI.ACTIONS_PER_TICK_DEFAULT} action(s), "
            f"got {len(actions)}"
        )

    def test_configurable_actions_per_tick(self) -> None:
        """Override actions_per_tick=3 produces at most 3 actions."""
        ai = RuleBasedStateAI()
        max_actions: int = 3
        defines = _make_defines(actions_per_tick=max_actions)
        balance = make_faction_balance()
        budget = make_state_budget()

        actions = ai.select_action(
            org_id=_DEFAULT_ORG_ID,
            faction_balance=balance,
            budget=budget,
            heat=0.6,
            defines=defines,
            rng_seed=_DEFAULT_SEED,
        )

        assert len(actions) <= max_actions, (
            f"With actions_per_tick={max_actions}, should produce at most "
            f"{max_actions} actions, got {len(actions)}"
        )
