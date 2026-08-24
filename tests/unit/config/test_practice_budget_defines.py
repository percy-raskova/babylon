"""Designed practice-budget defines and generated parity contract."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from pydantic import ValidationError

import babylon.config.defines as defines_package
from babylon.config.defines import GameDefines
from babylon.config.defines.organizations import PracticeBudgetDefines
from babylon.contracts import practice_contract_v1 as practice_contract

U32_MAX = (1 << 32) - 1


def _assert_invalid(factory: Callable[[], object]) -> None:
    with pytest.raises(ValidationError):
        factory()


def test_default_practice_budget_terms_match_contract_adapter_exactly() -> None:
    defines = GameDefines()
    terms = practice_contract.PracticeBudgetTermsV1.from_defines(defines)
    assert terms.model_dump() == {
        "initial": defines.practice_budget.action_budget_initial,
        "weekly_credit_cap": defines.practice_budget.action_budget_weekly_credit_cap,
        "storage_ceiling": defines.practice_budget.action_budget_storage_ceiling,
        "organize_cost": defines.practice_budget.organize_action_budget_cost,
        "agitate_cost": defines.practice_budget.agitate_action_budget_cost,
        "mutual_aid_cost": defines.practice_budget.mutual_aid_action_budget_cost,
    }
    assert terms.model_dump() == {
        "initial": 1,
        "weekly_credit_cap": 1,
        "storage_ceiling": 4,
        "organize_cost": 1,
        "agitate_cost": 1,
        "mutual_aid_cost": 1,
    }


def test_practice_budget_default_invariants_are_explicit() -> None:
    budget = GameDefines().practice_budget
    assert budget.action_budget_initial >= min(
        budget.organize_action_budget_cost,
        budget.agitate_action_budget_cost,
    )
    assert budget.action_budget_storage_ceiling >= budget.action_budget_initial
    for cost in (
        budget.organize_action_budget_cost,
        budget.agitate_action_budget_cost,
        budget.mutual_aid_action_budget_cost,
    ):
        assert 1 <= cost <= U32_MAX
    for term in (
        budget.action_budget_initial,
        budget.action_budget_weekly_credit_cap,
        budget.action_budget_storage_ceiling,
    ):
        assert 0 <= term <= U32_MAX


@pytest.mark.parametrize(
    "factory",
    [
        pytest.param(
            lambda: PracticeBudgetDefines(action_budget_initial=-1), id="negative-initial"
        ),
        pytest.param(
            lambda: PracticeBudgetDefines(action_budget_weekly_credit_cap=-1),
            id="negative-credit",
        ),
        pytest.param(
            lambda: PracticeBudgetDefines(action_budget_storage_ceiling=U32_MAX + 1),
            id="ceiling-over-u32",
        ),
        pytest.param(
            lambda: PracticeBudgetDefines(organize_action_budget_cost=0),
            id="zero-organize",
        ),
        pytest.param(
            lambda: PracticeBudgetDefines(agitate_action_budget_cost=U32_MAX + 1),
            id="agitate-over-u32",
        ),
        pytest.param(
            lambda: PracticeBudgetDefines(mutual_aid_action_budget_cost=0),
            id="zero-mutual-aid",
        ),
        pytest.param(
            lambda: PracticeBudgetDefines(
                action_budget_initial=2,
                action_budget_storage_ceiling=1,
            ),
            id="initial-over-ceiling",
        ),
        pytest.param(
            lambda: PracticeBudgetDefines(
                action_budget_initial=0,
                organize_action_budget_cost=1,
                agitate_action_budget_cost=1,
            ),
            id="initial-below-wired-costs",
        ),
    ],
)
def test_invalid_practice_budget_defines_are_refused(
    factory: Callable[[], object],
) -> None:
    _assert_invalid(factory)


def test_private_practice_budget_category_does_not_widen_public_package() -> None:
    assert "PracticeBudgetDefines" not in defines_package.__all__
    assert not hasattr(defines_package, "PracticeBudgetDefines")
