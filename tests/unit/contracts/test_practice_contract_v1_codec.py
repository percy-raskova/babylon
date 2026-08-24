"""Cross-language behavioral contract for practice wire codecs."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from babylon.contracts.practice_contract_v1 import (
    PracticeContractViolation,
    PracticeVectorCaseV1,
    PracticeVectorCorpusError,
    budget_delta_digest,
    decode_budget_delta,
    decode_input_authority,
    decode_intent,
    decode_rejection,
    encode_budget_delta,
    encode_input_authority,
    encode_intent,
    encode_intent_parameters,
    encode_rejection,
    input_authority_digest,
    intent_digest,
    parameter_bytes_digest,
    parse_vector_corpus,
    rejection_for,
    submission_rejection_alias,
    target_selection_policy_digest,
)
from babylon.contracts.practice_contract_v1_generated import (
    OrganizationBudgetDeltaV1,
    PracticeAuthorityKindV1,
    PracticeContractError,
    PracticeIdV1,
    PracticeInputAuthorityV1,
    PracticeIntentV1,
    PracticeParameterV1,
    PracticeRejectionCodeV1,
    PracticeSubmissionRejectionV1,
    PracticeTargetDomainV1,
)

ROOT = Path(__file__).parents[3]
VECTOR_PATH = ROOT / "contracts" / "practice_contract_v1_vectors.jsonl"
ZERO_DIGEST = b"\x00" * 32


def _authority() -> PracticeInputAuthorityV1:
    return PracticeInputAuthorityV1(
        schema_version=1,
        authority_kind=PracticeAuthorityKindV1.PLAYER_SEAT,
        actor_org_id=7,
        producer_content_digest=b"\x11" * 32,
    )


def _intent(practice: PracticeIdV1 = PracticeIdV1.ORGANIZE) -> PracticeIntentV1:
    return PracticeIntentV1(
        schema_version=1,
        submit_after_tick=10,
        resolve_tick=11,
        actor_org_id=7,
        practice_id=practice,
        target_domain=PracticeTargetDomainV1.SOCIAL_CLASS,
        target_node_id=101,
        quoted_content_digest=b"\x22" * 32,
        quoted_action_budget_cost=1,
        parameters=(),
        evidence_digests=(),
    )


def _budget_delta() -> OrganizationBudgetDeltaV1:
    return OrganizationBudgetDeltaV1(
        schema_version=1,
        tick=11,
        actor_node_id=7,
        pre_action_world_hash=b"\x33" * 32,
        budget_before=1,
        governed_cost=1,
        footprint_count=2,
        raw_credit=2,
        credited_credit=1,
        ceiling_bound=False,
        budget_after=1,
    )


def _rejection(reason: PracticeRejectionCodeV1) -> PracticeSubmissionRejectionV1:
    return PracticeSubmissionRejectionV1(
        schema_version=1,
        submitted_bytes_digest=b"\x44" * 32,
        reason_code=reason,
        last_committed_tick=10,
        content_digest=b"\x22" * 32,
    )


def test_shared_corpus_is_bounded_and_consumable() -> None:
    cases = parse_vector_corpus(VECTOR_PATH.read_bytes())
    assert len(cases) > 0
    assert len({case.case_id for case in cases}) == len(cases)


def _cases_by_kind(kind: str) -> tuple[PracticeVectorCaseV1, ...]:
    return tuple(
        case for case in parse_vector_corpus(VECTOR_PATH.read_bytes()) if case.kind == kind
    )


def test_shared_valid_vectors_pin_bytes_round_trips_and_digests() -> None:
    for case in _cases_by_kind("authority"):
        data = case.data
        authority_value = PracticeInputAuthorityV1(
            schema_version=1,
            authority_kind=PracticeAuthorityKindV1(data["authority_kind"]),
            actor_org_id=data["actor_org_id"],
            producer_content_digest=bytes.fromhex(data["producer_content_digest_hex"]),
        )
        canonical = bytes.fromhex(data["canonical_hex"])
        assert encode_input_authority(authority_value) == canonical
        assert decode_input_authority(canonical) == authority_value
        assert input_authority_digest(authority_value).hex() == data["digest_hex"]
    for case in _cases_by_kind("intent"):
        data = case.data
        intent_value = PracticeIntentV1(
            schema_version=1,
            submit_after_tick=10,
            resolve_tick=11,
            actor_org_id=data["actor_org_id"],
            practice_id=PracticeIdV1(data["practice_id"]),
            target_domain=PracticeTargetDomainV1.SOCIAL_CLASS,
            target_node_id=data["target_node_id"],
            quoted_content_digest=bytes.fromhex(data["quoted_content_digest_hex"]),
            quoted_action_budget_cost=data["quoted_action_budget_cost"],
            parameters=(),
            evidence_digests=tuple(
                bytes.fromhex(digest) for digest in data["evidence_digests_hex"]
            ),
        )
        canonical = bytes.fromhex(data["canonical_hex"])
        assert encode_intent(intent_value) == canonical
        assert decode_intent(canonical) == intent_value
        assert intent_digest(intent_value).hex() == data["digest_hex"]
        assert encode_intent_parameters(intent_value).hex() == data["parameter_hex"]
        assert parameter_bytes_digest(intent_value).hex() == data["parameter_digest_hex"]
        assert (
            target_selection_policy_digest(
                intent_value.target_domain, intent_value.target_node_id
            ).hex()
            == data["target_digest_hex"]
        )
        target_preimage = (
            b"babylon.fixed-target-selection.v1"
            + b"\x00"
            + bytes((intent_value.target_domain.value,))
            + intent_value.target_node_id.to_bytes(8, "big")
        )
        assert target_preimage.hex() == data["target_preimage_hex"]
        assert sha256(target_preimage).hexdigest() == data["target_digest_hex"]


def test_budget_and_all_rejection_vectors_pin_exact_bytes() -> None:
    budget_case = _cases_by_kind("budget_delta")[0]
    delta = _budget_delta()
    canonical = bytes.fromhex(budget_case.data["canonical_hex"])
    assert encode_budget_delta(delta) == canonical
    assert decode_budget_delta(canonical) == delta
    assert budget_delta_digest(delta).hex() == budget_case.data["digest_hex"]
    rejection_cases = _cases_by_kind("rejection")
    assert [case.data["reason_code"] for case in rejection_cases] == list(range(1, 12))
    for case in rejection_cases:
        value = _rejection(PracticeRejectionCodeV1(case.data["reason_code"]))
        canonical = bytes.fromhex(case.data["canonical_hex"])
        assert encode_rejection(value) == canonical
        assert decode_rejection(canonical) == value


def test_invalid_wire_vectors_return_the_exact_governed_error() -> None:
    decoders = {
        "authority": decode_input_authority,
        "intent": decode_intent,
        "budget_delta": decode_budget_delta,
        "rejection": decode_rejection,
    }
    for case in _cases_by_kind("invalid_wire"):
        with pytest.raises(PracticeContractViolation) as caught:
            decoders[case.data["codec"]](bytes.fromhex(case.data["payload_hex"]))
        assert caught.value.error is PracticeContractError(case.data["error"])


def test_intent_truncation_oversize_and_atomic_encoder_refusals() -> None:
    canonical = encode_intent(_intent())
    manifest = _cases_by_kind("manifest")[0]
    for offset in manifest.data["intent_truncation_offsets"]:
        if offset == len(canonical):
            continue
        with pytest.raises(PracticeContractViolation) as caught:
            decode_intent(canonical[:offset])
        assert caught.value.error is PracticeContractError.PRACTICE_TRUNCATED
    with pytest.raises(PracticeContractViolation) as caught:
        decode_intent(canonical + bytes(16_385 - len(canonical)))
    assert caught.value.error is PracticeContractError.PRACTICE_LENGTH
    first_parameter = PracticeParameterV1(
        key_u8=1, value_kind_u8=1, value_length_u16=0, value_bytes=b""
    )
    bad_intent = _intent().model_copy(update={"parameters": (first_parameter,)})
    with pytest.raises(PracticeContractViolation) as caught:
        encode_intent(bad_intent)
    assert caught.value.error is PracticeContractError.PRACTICE_PARAMETER
    bad_intent = _intent().model_copy(update={"evidence_digests": (b"\x02" * 32, b"\x01" * 32)})
    with pytest.raises(PracticeContractViolation) as caught:
        intent_digest(bad_intent)
    assert caught.value.error is PracticeContractError.PRACTICE_EVIDENCE_ORDER


def test_encoder_precedence_pins_parameter_and_evidence_plus_one_witnesses() -> None:
    parameter_256 = PracticeParameterV1(
        key_u8=1, value_kind_u8=1, value_length_u16=256, value_bytes=bytes(256)
    )
    bad_intent = _intent().model_copy(update={"parameters": (parameter_256,)})
    with pytest.raises(PracticeContractViolation) as caught:
        encode_intent_parameters(bad_intent)
    assert caught.value.error is PracticeContractError.PRACTICE_PARAMETER
    parameter_257 = PracticeParameterV1(
        key_u8=1, value_kind_u8=1, value_length_u16=257, value_bytes=bytes(257)
    )
    bad_intent = _intent().model_copy(update={"parameters": (parameter_257,)})
    with pytest.raises(PracticeContractViolation) as caught:
        encode_intent_parameters(bad_intent)
    assert caught.value.error is PracticeContractError.PRACTICE_PARAMETER_LENGTH
    bad_intent = _intent().model_copy(update={"parameters": (parameter_256,) * 17})
    with pytest.raises(PracticeContractViolation) as caught:
        encode_intent_parameters(bad_intent)
    assert caught.value.error is PracticeContractError.PRACTICE_PARAMETER_LIMIT
    bad_intent = _intent().model_copy(update={"evidence_digests": (bytes(32),) * 65})
    with pytest.raises(PracticeContractViolation) as caught:
        encode_intent(bad_intent)
    assert caught.value.error is PracticeContractError.PRACTICE_EVIDENCE_LIMIT
    bad_intent = _intent().model_copy(update={"evidence_digests": (b"\x01" * 32, b"\x01" * 32)})
    with pytest.raises(PracticeContractViolation) as caught:
        intent_digest(bad_intent)
    assert caught.value.error is PracticeContractError.PRACTICE_EVIDENCE_DUPLICATE


def test_parameter_refusal_waits_for_every_structural_frame() -> None:
    valid = PracticeParameterV1(key_u8=1, value_kind_u8=1, value_length_u16=0, value_bytes=b"")
    malformed = PracticeParameterV1(key_u8=2, value_kind_u8=1, value_length_u16=2, value_bytes=b"x")
    value = _intent().model_copy(update={"parameters": (valid, malformed)})
    with pytest.raises(PracticeContractViolation) as caught:
        encode_intent_parameters(value)
    assert caught.value.error is PracticeContractError.PRACTICE_PARAMETER_LENGTH

    canonical = encode_intent(_intent())
    parameter_offset = len(canonical) - 4
    prefix = canonical[:parameter_offset]
    valid_frame = b"\x01\x01\x00\x00"
    malformed_frame = b"\x02\x01\x01\x01" + bytes(257)
    with pytest.raises(PracticeContractViolation) as caught:
        decode_intent(prefix + b"\x00\x02" + valid_frame + malformed_frame + b"\x00\x00")
    assert caught.value.error is PracticeContractError.PRACTICE_PARAMETER_LENGTH

    truncated_later = prefix + b"\x00\x02" + valid_frame + b"\x02\x01\x00\x02x"
    with pytest.raises(PracticeContractViolation) as caught:
        decode_intent(truncated_later)
    assert caught.value.error is PracticeContractError.PRACTICE_TRUNCATED

    valid_later = prefix + b"\x00\x02" + valid_frame + b"\x02\x01\x00\x00\x00\x00"
    with pytest.raises(PracticeContractViolation) as caught:
        decode_intent(valid_later)
    assert caught.value.error is PracticeContractError.PRACTICE_PARAMETER


def _vector_line(case_id: str = "case", kind: str = "manifest") -> bytes:
    return (
        json.dumps({"case_id": case_id, "kind": kind, "data": {}}, separators=(",", ":")).encode()
        + b"\n"
    )


def test_vector_reader_refuses_every_fixed_bound_and_closed_shape() -> None:
    unique_lines = b"".join(_vector_line(f"case-{index}") for index in range(513))
    witnesses = (
        b"x" * 2_097_153,
        unique_lines,
        b" " * 65_536 + b"\n",
        _vector_line("x" * 129),
        b'{"case_id":"case","kind":"manifest","data":' + b"[" * 33 + b"]" * 33 + b"}\n",
        _vector_line() * 2,
        _vector_line(kind="unknown"),
        b'{"case_id":"case","kind":"manifest","data":{},"extra":0}\n',
        b'{"case_id":"case","kind":"manifest","data":{}} {}\n',
        b'{"case_id":"case","case_id":"other","kind":"manifest","data":{}}\n',
    )
    for payload in witnesses:
        with pytest.raises(PracticeVectorCorpusError):
            parse_vector_corpus(payload)


def test_local_type_and_shape_errors_never_gain_wire_identity() -> None:
    with pytest.raises(TypeError):
        PracticeContractViolation(1)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        submission_rejection_alias(16)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        submission_rejection_alias(PracticeRejectionCodeV1.PRACTICE_UNWIRED)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        target_selection_policy_digest(1, 101)  # type: ignore[arg-type]
    for target in (True, -1, 1 << 64):
        with pytest.raises((TypeError, ValueError)):
            target_selection_policy_digest(PracticeTargetDomainV1.SOCIAL_CLASS, target)
    base = _rejection(PracticeRejectionCodeV1.PRACTICE_UNWIRED).model_dump()
    shape_witnesses = (
        {key: value for key, value in base.items() if key != "content_digest"},
        {**base, "extra": 0},
        {**base, "content_digest": None},
    )
    for witness in shape_witnesses:
        with pytest.raises(ValidationError):
            PracticeSubmissionRejectionV1.model_validate(witness)


def test_typed_fixtures_reject_every_digest_width_before_codec_use() -> None:
    witnesses: list[tuple[type[object], dict[str, object], str]] = [
        (
            PracticeInputAuthorityV1,
            _authority().model_dump(),
            "producer_content_digest",
        ),
        (PracticeIntentV1, _intent().model_dump(), "quoted_content_digest"),
        (
            OrganizationBudgetDeltaV1,
            _budget_delta().model_dump(),
            "pre_action_world_hash",
        ),
        (
            PracticeSubmissionRejectionV1,
            _rejection(PracticeRejectionCodeV1.PRACTICE_UNWIRED).model_dump(),
            "submitted_bytes_digest",
        ),
        (
            PracticeSubmissionRejectionV1,
            _rejection(PracticeRejectionCodeV1.PRACTICE_UNWIRED).model_dump(),
            "content_digest",
        ),
    ]
    for model_type, base, field in witnesses:
        for width in (31, 33):
            with pytest.raises(ValidationError):
                model_type.model_validate({**base, field: bytes(width)})  # type: ignore[attr-defined]
    for width in (31, 33):
        with pytest.raises(ValidationError):
            PracticeIntentV1.model_validate(
                {**_intent().model_dump(), "evidence_digests": (bytes(width),)}
            )


def test_typed_fixtures_reject_unsigned_width_plus_one_witnesses() -> None:
    constructors = (
        lambda value: PracticeParameterV1(
            key_u8=value, value_kind_u8=0, value_length_u16=0, value_bytes=b""
        ),
        lambda value: PracticeInputAuthorityV1(
            schema_version=value,
            authority_kind=PracticeAuthorityKindV1.PLAYER_SEAT,
            actor_org_id=7,
            producer_content_digest=b"\x11" * 32,
        ),
        lambda value: PracticeIntentV1(
            **{**_intent().model_dump(), "quoted_action_budget_cost": value}
        ),
        lambda value: PracticeInputAuthorityV1(
            schema_version=1,
            authority_kind=PracticeAuthorityKindV1.PLAYER_SEAT,
            actor_org_id=value,
            producer_content_digest=b"\x11" * 32,
        ),
    )
    for constructor, upper in zip(constructors, (1 << 8, 1 << 16, 1 << 32, 1 << 64), strict=True):
        for witness in (-1, upper):
            with pytest.raises(ValidationError):
                constructor(witness)


def test_alias_table_is_total_over_the_closed_contract_error_enum() -> None:
    expected = {
        16: PracticeRejectionCodeV1.PRACTICE_TICK_MISMATCH,
        17: PracticeRejectionCodeV1.PRACTICE_TICK_MISMATCH,
        21: PracticeRejectionCodeV1.PRACTICE_AUTHORITY_UNREGISTERED,
        22: PracticeRejectionCodeV1.PRACTICE_ACTOR_MISMATCH,
        23: PracticeRejectionCodeV1.PRACTICE_AUTHORITY_UNREGISTERED,
        24: PracticeRejectionCodeV1.PRACTICE_STALE_CONTENT,
        25: PracticeRejectionCodeV1.PRACTICE_COST_MISMATCH,
        26: PracticeRejectionCodeV1.PRACTICE_BATCH_LIMIT,
        27: PracticeRejectionCodeV1.PRACTICE_DUPLICATE_ACTOR,
        33: PracticeRejectionCodeV1.PRACTICE_BUDGET_INSUFFICIENT,
    }
    for error in PracticeContractError:
        assert submission_rejection_alias(error) is expected.get(error.value)


def test_alias_table_is_mechanically_pinned_to_the_yaml_authority() -> None:
    schema = yaml.safe_load((ROOT / "contracts" / "practice_contract_v1.yaml").read_bytes())
    expected = {
        PracticeContractError(code): PracticeRejectionCodeV1[name]
        for code, name in schema["submission_rejection_aliases"].items()
    }
    assert {
        error: alias
        for error in PracticeContractError
        if (alias := submission_rejection_alias(error)) is not None
    } == expected


def test_fixed_records_round_trip_without_defaulting() -> None:
    authority = _authority()
    intent = _intent()
    delta = _budget_delta()
    rejection = _rejection(PracticeRejectionCodeV1.PRACTICE_UNWIRED)
    assert decode_input_authority(encode_input_authority(authority)) == authority
    assert decode_intent(encode_intent(intent)) == intent
    assert decode_budget_delta(encode_budget_delta(delta)) == delta
    assert decode_rejection(encode_rejection(rejection)) == rejection


def test_digest_and_metadata_interfaces_are_typed() -> None:
    authority = _authority()
    intent = _intent()
    delta = _budget_delta()
    assert len(input_authority_digest(authority)) == 32
    assert encode_intent_parameters(intent) == b"\x00\x00"
    assert len(intent_digest(intent)) == 32
    assert len(parameter_bytes_digest(intent)) == 32
    assert len(target_selection_policy_digest(PracticeTargetDomainV1.SOCIAL_CLASS, 101)) == 32
    assert len(budget_delta_digest(delta)) == 32
    assert submission_rejection_alias(PracticeContractError.PRACTICE_TICK_OVERFLOW) is (
        PracticeRejectionCodeV1.PRACTICE_TICK_MISMATCH
    )
    assert submission_rejection_alias(PracticeContractError.PRACTICE_DOMAIN) is None


def test_rejection_factory_requires_complete_context() -> None:
    rejection = rejection_for(
        submitted_bytes_digest=b"\x44" * 32,
        reason_code=PracticeRejectionCodeV1.PRACTICE_STALE_CONTENT,
        last_committed_tick=10,
        content_digest=b"\x22" * 32,
    )
    assert rejection == _rejection(PracticeRejectionCodeV1.PRACTICE_STALE_CONTENT)


def test_governed_violation_exposes_only_the_exact_error() -> None:
    payload = bytearray(encode_input_authority(_authority()))
    payload[0] ^= 1
    try:
        decode_input_authority(bytes(payload))
    except PracticeContractViolation as violation:
        assert violation.error is PracticeContractError.PRACTICE_DOMAIN
    else:
        raise AssertionError("bad domain accepted")


def test_governed_violation_error_identity_is_immutable() -> None:
    violation = PracticeContractViolation(PracticeContractError.PRACTICE_DOMAIN)
    with pytest.raises(AttributeError):
        violation.error = PracticeContractError.PRACTICE_LENGTH  # type: ignore[misc]
    with pytest.raises(AttributeError):
        violation._error = PracticeContractError.PRACTICE_LENGTH  # type: ignore[misc]


def test_vector_reader_rejects_unknown_kind_specific_data_field() -> None:
    payload = json.dumps(
        {
            "case_id": "case",
            "kind": "manifest",
            "data": {
                "parameter_limit_valid_witness": None,
                "intent_truncation_offsets": [],
                "unknown": 0,
            },
        },
        separators=(",", ":"),
    ).encode()
    with pytest.raises(PracticeVectorCorpusError):
        parse_vector_corpus(payload)
