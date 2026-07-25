"""Behavioral contract for the deterministic CPU ActionPolicy (Task 9)."""

from babylon.game.actions.policy import select_actions


def test_selection_is_deterministic_and_budget_bounded():
    observed = {"repression": 0.4, "solidarity": 0.7}
    a = select_actions("organizer", budget=2, observed=observed)
    b = select_actions("organizer", budget=2, observed=observed)
    assert a == b  # deterministic
    assert len(a) <= 2  # budget-bounded
    assert all(isinstance(x, str) for x in a)


def test_zero_budget_selects_nothing():
    assert select_actions("organizer", budget=0, observed={}) == ()


def test_priority_table_orders_selection():
    # npc_stub's POLITICAL_FACTION priorities open with EDUCATE — the organizer's
    # first pick must follow the table, not alphabetical order ("aid" would win that).
    selected = select_actions("organizer", budget=1, observed={})
    assert selected == ("educate",)


def test_only_live_actions_are_selected():
    # state/corporation actions are all STUBs today — an honest empty selection,
    # never a fabricated macro-action.
    assert select_actions("corporation", budget=5, observed={}) == ()
