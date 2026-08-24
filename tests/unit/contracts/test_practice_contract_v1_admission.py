"""Pure authority, quote, and batch validation contracts."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from babylon.contracts.practice_contract_v1 import (
    PracticeContractViolation,
    validate_authority_pair,
    validate_quote_context,
    validate_resolve_batch,
)
from babylon.contracts.practice_contract_v1_generated import (
    PolicyAuthorityPairV1,
    PracticeAuthorityContextV1,
    PracticeAuthorityKindV1,
    PracticeBudgetTermsV1,
    PracticeContractError,
    PracticeIdV1,
    PracticeInputAuthorityV1,
    PracticeIntentV1,
    PracticeQuoteContextV1,
    PracticeTargetDomainV1,
)


def _intent(actor: int = 7) -> PracticeIntentV1:
    return PracticeIntentV1(
        schema_version=1,
        submit_after_tick=10,
        resolve_tick=11,
        actor_org_id=actor,
        practice_id=PracticeIdV1.ORGANIZE,
        target_domain=PracticeTargetDomainV1.SOCIAL_CLASS,
        target_node_id=101,
        quoted_content_digest=b"\x22" * 32,
        quoted_action_budget_cost=1,
        parameters=(),
        evidence_digests=(),
    )


def _context() -> PracticeAuthorityContextV1:
    return PracticeAuthorityContextV1(
        player_org_id=7,
        player_gateway_content_digest=b"\x11" * 32,
        policy_authorities=(
            PolicyAuthorityPairV1(
                producer_content_digest=b"\x33" * 32,
                actor_org_id=8,
            ),
        ),
    )


def test_player_policy_quote_and_empty_batch_validate_without_side_effects() -> None:
    intent = _intent()
    player = PracticeInputAuthorityV1(
        schema_version=1,
        authority_kind=PracticeAuthorityKindV1.PLAYER_SEAT,
        actor_org_id=7,
        producer_content_digest=b"\x11" * 32,
    )
    validate_authority_pair(player, intent, _context())
    quote = PracticeQuoteContextV1(
        last_committed_tick=10,
        content_digest=b"\x22" * 32,
        budget_terms=PracticeBudgetTermsV1(
            initial=1,
            weekly_credit_cap=1,
            storage_ceiling=4,
            organize_cost=1,
            agitate_cost=1,
            mutual_aid_cost=1,
        ),
    )
    validate_quote_context(intent, quote)
    validate_resolve_batch((), 11)


def _authority(
    *,
    kind: PracticeAuthorityKindV1 = PracticeAuthorityKindV1.PLAYER_SEAT,
    actor: int = 7,
    digest: bytes = b"\x11" * 32,
) -> PracticeInputAuthorityV1:
    return PracticeInputAuthorityV1(
        schema_version=1,
        authority_kind=kind,
        actor_org_id=actor,
        producer_content_digest=digest,
    )


def _quote(
    *,
    tick: int = 10,
    digest: bytes = b"\x22" * 32,
    organize: int = 1,
    agitate: int = 2,
    mutual_aid: int = 3,
) -> PracticeQuoteContextV1:
    return PracticeQuoteContextV1(
        last_committed_tick=tick,
        content_digest=digest,
        budget_terms=PracticeBudgetTermsV1(
            initial=1,
            weekly_credit_cap=1,
            storage_ceiling=4,
            organize_cost=organize,
            agitate_cost=agitate,
            mutual_aid_cost=mutual_aid,
        ),
    )


def _assert_error(expected: PracticeContractError, operation: Callable[[], object]) -> None:
    with pytest.raises(PracticeContractViolation) as caught:
        operation()
    assert caught.value.error is expected


def test_player_authority_refuses_actor_and_content_mismatch() -> None:
    _assert_error(
        PracticeContractError.PRACTICE_ACTOR_MISMATCH,
        lambda: validate_authority_pair(_authority(actor=8), _intent(), _context()),
    )
    _assert_error(
        PracticeContractError.PRACTICE_AUTHORITY_CONTENT_MISMATCH,
        lambda: validate_authority_pair(_authority(digest=b"\x12" * 32), _intent(), _context()),
    )


def test_policy_authority_requires_sorted_unique_exact_registration() -> None:
    authority = _authority(
        kind=PracticeAuthorityKindV1.DETERMINISTIC_POLICY,
        actor=8,
        digest=b"\x33" * 32,
    )
    validate_authority_pair(authority, _intent(actor=8), _context())
    missing = _context().model_copy(update={"policy_authorities": ()})
    _assert_error(
        PracticeContractError.PRACTICE_AUTHORITY_UNREGISTERED,
        lambda: validate_authority_pair(authority, _intent(actor=8), missing),
    )
    pair = _context().policy_authorities[0]
    duplicate = _context().model_copy(update={"policy_authorities": (pair, pair)})
    _assert_error(
        PracticeContractError.PRACTICE_AUTHORITY_REGISTRY_DUPLICATE,
        lambda: validate_authority_pair(authority, _intent(actor=8), duplicate),
    )
    low = PolicyAuthorityPairV1(producer_content_digest=b"\x22" * 32, actor_org_id=8)
    unsorted = _context().model_copy(update={"policy_authorities": (pair, low)})
    _assert_error(
        PracticeContractError.PRACTICE_AUTHORITY_REGISTRY_ORDER,
        lambda: validate_authority_pair(authority, _intent(actor=8), unsorted),
    )
    too_many = _context().model_copy(
        update={"policy_authorities": tuple(pair for _index in range(4_097))}
    )
    _assert_error(
        PracticeContractError.PRACTICE_AUTHORITY_REGISTRY_LIMIT,
        lambda: validate_authority_pair(authority, _intent(actor=8), too_many),
    )


@pytest.mark.parametrize(
    ("practice", "cost"),
    ((PracticeIdV1.ORGANIZE, 1), (PracticeIdV1.AGITATE, 2), (PracticeIdV1.MUTUAL_AID, 3)),
)
def test_quote_cost_is_exhaustive_by_practice(practice: PracticeIdV1, cost: int) -> None:
    intent = _intent().model_copy(
        update={"practice_id": practice, "quoted_action_budget_cost": cost}
    )
    validate_quote_context(intent, _quote())
    wrong = intent.model_copy(update={"quoted_action_budget_cost": cost + 1})
    _assert_error(
        PracticeContractError.PRACTICE_QUOTE_COST_MISMATCH,
        lambda: validate_quote_context(wrong, _quote()),
    )


def test_quote_refuses_stale_tick_overflow_and_content() -> None:
    intent = _intent()
    _assert_error(
        PracticeContractError.PRACTICE_TICK_MISMATCH,
        lambda: validate_quote_context(intent, _quote(tick=9)),
    )
    overflow_intent = intent.model_copy(
        update={"submit_after_tick": (1 << 64) - 1, "resolve_tick": 0}
    )
    _assert_error(
        PracticeContractError.PRACTICE_TICK_OVERFLOW,
        lambda: validate_quote_context(overflow_intent, _quote(tick=(1 << 64) - 1)),
    )
    wrong_resolve = intent.model_copy(update={"resolve_tick": 12})
    _assert_error(
        PracticeContractError.PRACTICE_TICK_MISMATCH,
        lambda: validate_quote_context(wrong_resolve, _quote()),
    )
    _assert_error(
        PracticeContractError.PRACTICE_QUOTE_CONTENT_MISMATCH,
        lambda: validate_quote_context(intent, _quote(digest=b"\x23" * 32)),
    )


def test_batch_accepts_4096_and_refuses_limit_tick_and_duplicate_actor() -> None:
    intents = tuple(_intent(actor=index) for index in range(4_096))
    validate_resolve_batch(intents, 11)
    _assert_error(
        PracticeContractError.PRACTICE_BATCH_LIMIT,
        lambda: validate_resolve_batch(intents + (_intent(actor=4_096),), 11),
    )
    mismatched = (_intent(actor=1), _intent(actor=2).model_copy(update={"resolve_tick": 12}))
    _assert_error(
        PracticeContractError.PRACTICE_TICK_MISMATCH,
        lambda: validate_resolve_batch(mismatched, 11),
    )
    duplicate = intents[:-1] + (_intent(actor=0),)
    _assert_error(
        PracticeContractError.PRACTICE_DUPLICATE_ACTOR,
        lambda: validate_resolve_batch(duplicate, 11),
    )
