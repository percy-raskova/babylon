"""Pure non-live refusal metadata for every closed practice."""

from __future__ import annotations

import inspect
import operator

import pytest

from babylon.contracts.practice_contract_v1 import activation_blockers, unwired_reason
from babylon.contracts.practice_contract_v1_generated import (
    PracticeActivationBlockerV1,
    PracticeAuthorityKindV1,
    PracticeIdV1,
    PracticeRejectionCodeV1,
)

SHARED_BLOCKERS = (
    PracticeActivationBlockerV1.GATE3_COMMITTED_ENVELOPE,
    PracticeActivationBlockerV1.GATE5_PENDING_INPUT,
)
MUTUAL_AID_BLOCKERS = (
    *SHARED_BLOCKERS,
    PracticeActivationBlockerV1.PER30_ORDERS_INVENTORY,
    PracticeActivationBlockerV1.PER31_FREIGHT_REALIZATION,
)


@pytest.mark.parametrize("practice", tuple(PracticeIdV1))
def test_every_closed_practice_returns_the_unwired_reason(practice: PracticeIdV1) -> None:
    assert unwired_reason(practice) is PracticeRejectionCodeV1.PRACTICE_UNWIRED


def test_activation_blockers_are_exact_ordered_and_immutable() -> None:
    organize = activation_blockers(PracticeIdV1.ORGANIZE)
    agitate = activation_blockers(PracticeIdV1.AGITATE)
    mutual_aid = activation_blockers(PracticeIdV1.MUTUAL_AID)

    assert organize == SHARED_BLOCKERS
    assert agitate == SHARED_BLOCKERS
    assert mutual_aid == MUTUAL_AID_BLOCKERS
    assert organize is agitate
    assert organize is activation_blockers(PracticeIdV1.ORGANIZE)
    assert mutual_aid is activation_blockers(PracticeIdV1.MUTUAL_AID)
    with pytest.raises(TypeError):
        operator.setitem(organize, 0, PracticeActivationBlockerV1.PER30_ORDERS_INVENTORY)


def test_lookup_surface_accepts_only_one_closed_practice_value() -> None:
    for lookup in (unwired_reason, activation_blockers):
        assert tuple(inspect.signature(lookup).parameters) == ("practice",)
        with pytest.raises(TypeError, match="practice must be PracticeIdV1"):
            lookup(1)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="practice must be PracticeIdV1"):
            lookup(PracticeAuthorityKindV1.PLAYER_SEAT)  # type: ignore[arg-type]


def test_mutual_aid_blockers_do_not_invent_goods_or_universal_dependencies() -> None:
    names = " ".join(blocker.name for blocker in activation_blockers(PracticeIdV1.MUTUAL_AID))
    for forbidden in (
        "ACTION_BUDGET",
        "CAPACITY",
        "WEALTH",
        "RENT_POOL",
        "MONEY",
        "PER36",
        "PER44",
        "REPRESSION",
    ):
        assert forbidden not in names
