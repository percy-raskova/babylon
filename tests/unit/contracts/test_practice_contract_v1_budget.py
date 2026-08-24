"""Checked ActionBudget conversion and detached transition contracts."""

from __future__ import annotations

import inspect
import math
import struct
from collections.abc import Callable

import pytest

from babylon.contracts.practice_contract_v1 import (
    PracticeContractViolation,
    compute_budget_delta,
    read_action_budget,
    write_action_budget,
)
from babylon.contracts.practice_contract_v1_generated import (
    PracticeBudgetTermsV1,
    PracticeContractError,
    PracticeIdV1,
    PracticeTargetDomainV1,
    SolidarityFootprintEdgeV1,
)

U32_MAX = (1 << 32) - 1
WORLD_HASH = b"\x5a" * 32


def _bits(value: float) -> int:
    return struct.unpack(">Q", struct.pack(">d", value))[0]


def _terms(
    *,
    ceiling: int = 4,
    credit_cap: int = 1,
    organize: int = 1,
    agitate: int = 2,
    mutual_aid: int = 3,
) -> PracticeBudgetTermsV1:
    return PracticeBudgetTermsV1(
        initial=1,
        weekly_credit_cap=credit_cap,
        storage_ceiling=ceiling,
        organize_cost=organize,
        agitate_cost=agitate,
        mutual_aid_cost=mutual_aid,
    )


def _edge(source: int, target: int, strength: float = 1.0) -> SolidarityFootprintEdgeV1:
    return SolidarityFootprintEdgeV1(
        source_org_node_id_u64=source,
        target_domain_u8=PracticeTargetDomainV1.SOCIAL_CLASS,
        target_class_node_id_u64=target,
        strength_f64_bits_u64=_bits(strength),
    )


def _assert_error(expected: PracticeContractError, operation: Callable[[], object]) -> None:
    with pytest.raises(PracticeContractViolation) as caught:
        operation()
    assert caught.value.error is expected
    assert caught.value.error.value == expected.value


@pytest.mark.parametrize("value", [0, 1, U32_MAX])
def test_action_budget_storage_round_trips_exact_u32_values(value: int) -> None:
    storage = write_action_budget(value)
    assert type(storage) is float
    assert read_action_budget(storage) == value


@pytest.mark.parametrize(
    ("storage", "error"),
    [
        (math.nan, PracticeContractError.PRACTICE_BUDGET_NONFINITE),
        (math.inf, PracticeContractError.PRACTICE_BUDGET_NONFINITE),
        (-math.inf, PracticeContractError.PRACTICE_BUDGET_NONFINITE),
        (-1.0, PracticeContractError.PRACTICE_BUDGET_NEGATIVE),
        (1.5, PracticeContractError.PRACTICE_BUDGET_FRACTIONAL),
        (float(U32_MAX) + 1.0, PracticeContractError.PRACTICE_BUDGET_RANGE),
        (-0.0, PracticeContractError.PRACTICE_BUDGET_ROUNDTRIP),
    ],
)
def test_action_budget_storage_refusals_have_exact_codes(
    storage: float, error: PracticeContractError
) -> None:
    _assert_error(error, lambda: read_action_budget(storage))


def test_transition_api_derives_cost_and_count_without_caller_overrides() -> None:
    assert tuple(inspect.signature(compute_budget_delta).parameters) == (
        "tick",
        "actor_node_id",
        "pre_action_world_hash",
        "budget_before",
        "practice",
        "footprint_edges",
        "terms",
    )


@pytest.mark.parametrize(
    ("practice", "cost"),
    [
        (None, 0),
        (PracticeIdV1.ORGANIZE, 1),
        (PracticeIdV1.AGITATE, 2),
        (PracticeIdV1.MUTUAL_AID, 3),
    ],
)
def test_transition_derives_each_governed_cost(practice: PracticeIdV1 | None, cost: int) -> None:
    delta = compute_budget_delta(
        11,
        7,
        WORLD_HASH,
        3,
        practice,
        (),
        _terms(ceiling=4),
    )
    assert delta.governed_cost == cost
    assert delta.budget_after == 3 - cost


def test_transition_records_snapshot_and_exact_derived_credit_fields() -> None:
    delta = compute_budget_delta(
        11,
        7,
        WORLD_HASH,
        2,
        PracticeIdV1.ORGANIZE,
        (_edge(7, 101), _edge(7, 102)),
        _terms(),
    )
    assert delta.model_dump() == {
        "schema_version": 1,
        "tick": 11,
        "actor_node_id": 7,
        "pre_action_world_hash": WORLD_HASH,
        "budget_before": 2,
        "governed_cost": 1,
        "footprint_count": 2,
        "raw_credit": 2,
        "credited_credit": 1,
        "ceiling_bound": False,
        "budget_after": 2,
    }


def test_transition_applies_ceiling_only_after_checked_addition() -> None:
    delta = compute_budget_delta(
        11,
        7,
        WORLD_HASH,
        3,
        None,
        (_edge(7, 101),),
        _terms(ceiling=3),
    )
    assert delta.raw_credit == 1
    assert delta.credited_credit == 1
    assert delta.ceiling_bound is True
    assert delta.budget_after == 3


def test_insufficient_budget_precedes_subtraction() -> None:
    _assert_error(
        PracticeContractError.PRACTICE_BUDGET_INSUFFICIENT,
        lambda: compute_budget_delta(
            11,
            7,
            WORLD_HASH,
            0,
            PracticeIdV1.ORGANIZE,
            (),
            _terms(),
        ),
    )


def test_checked_addition_overflow_precedes_storage_ceiling_clamp() -> None:
    _assert_error(
        PracticeContractError.PRACTICE_BUDGET_ARITHMETIC,
        lambda: compute_budget_delta(
            11,
            7,
            WORLD_HASH,
            U32_MAX,
            None,
            (_edge(7, 101),),
            _terms(ceiling=U32_MAX),
        ),
    )


@pytest.mark.parametrize(
    ("edges", "error"),
    [
        (
            tuple(_edge(7, target) for target in range(257)),
            PracticeContractError.PRACTICE_FOOTPRINT_LIMIT,
        ),
        (
            (_edge(7, 102), _edge(7, 101)),
            PracticeContractError.PRACTICE_FOOTPRINT_ORDER,
        ),
        (
            (_edge(7, 101), _edge(7, 101)),
            PracticeContractError.PRACTICE_FOOTPRINT_DUPLICATE,
        ),
        ((_edge(8, 101),), PracticeContractError.PRACTICE_FOOTPRINT_SOURCE),
        (
            (_edge(7, 101, math.nan),),
            PracticeContractError.PRACTICE_FOOTPRINT_STRENGTH_NONFINITE,
        ),
        (
            (_edge(7, 101, math.inf),),
            PracticeContractError.PRACTICE_FOOTPRINT_STRENGTH_NONFINITE,
        ),
        (
            (_edge(7, 101, 0.0),),
            PracticeContractError.PRACTICE_FOOTPRINT_STRENGTH_NONPOSITIVE,
        ),
        (
            (_edge(7, 101, -1.0),),
            PracticeContractError.PRACTICE_FOOTPRINT_STRENGTH_NONPOSITIVE,
        ),
    ],
)
def test_footprint_refusals_have_exact_codes(
    edges: tuple[SolidarityFootprintEdgeV1, ...], error: PracticeContractError
) -> None:
    _assert_error(
        error,
        lambda: compute_budget_delta(11, 7, WORLD_HASH, 3, None, edges, _terms()),
    )


def test_footprint_accepts_zero_and_exact_maximum_positive_edges() -> None:
    empty = compute_budget_delta(11, 7, WORLD_HASH, 0, None, (), _terms())
    maximum = compute_budget_delta(
        11,
        7,
        WORLD_HASH,
        0,
        None,
        tuple(_edge(7, target) for target in range(256)),
        _terms(),
    )
    assert empty.footprint_count == 0
    assert maximum.footprint_count == 256
    assert maximum.raw_credit == 256
