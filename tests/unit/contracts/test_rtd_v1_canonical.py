"""Cross-language canonical byte and hash contracts for RTD V1."""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.contracts.relational_territory_dossier_v1 import (
    RTD_MAX_JSON_INPUT_BYTES,
    RtdValidationError,
    _CanonicalWriter,
    canonical_draft_bytes,
    parse_draft,
    parse_vector_corpus,
    projection_hash,
    seal_draft,
)
from babylon.contracts.rtd_v1_generated import RtdDossierDraftV1

ROOT = Path(__file__).resolve().parents[3]
VECTOR_PATH = ROOT / "contracts" / "relational_territory_dossier_v1_vectors.jsonl"


def test_shared_valid_vectors_pin_bytes_and_hashes() -> None:
    cases = parse_vector_corpus(VECTOR_PATH.read_bytes())
    valid = {case.case_id: case for case in cases if case.kind == "valid"}
    for case in valid.values():
        draft = parse_draft(case.draft)
        assert canonical_draft_bytes(draft).hex() == case.canonical_utf8_hex
        assert projection_hash(draft) == case.projection_hash
        assert seal_draft(draft).projection_hash == case.projection_hash
    assert valid["minimal-admin"].canonical_utf8_hex == valid["permuted-focus"].canonical_utf8_hex
    assert valid["minimal-admin"].projection_hash == valid["permuted-focus"].projection_hash
    assert valid["semantic-mutation"].projection_hash != valid["minimal-admin"].projection_hash


def test_shared_invalid_vectors_pin_all_stable_refusals() -> None:
    cases = parse_vector_corpus(VECTOR_PATH.read_bytes())
    invalid = [case for case in cases if case.kind == "invalid"]
    assert {case.error for case in invalid} == {
        "RTD_JSON",
        "RTD_JSON_DEPTH",
        "RTD_SCHEMA_VERSION",
        "RTD_UNKNOWN_FIELD",
        "RTD_ENUM",
        "RTD_IDENTITY",
        "RTD_DIGEST",
        "RTD_NON_NFC",
        "RTD_LIMIT_EXCEEDED",
        "RTD_DUPLICATE_KEY",
        "RTD_DANGLING_REF",
        "RTD_STATUS_VALUE",
        "RTD_NATIVE_GRAIN",
        "RTD_UNSUPPORTED_DOWNSCALE",
        "RTD_H3_BEFORE_PER21",
        "RTD_MSA_EVIDENCE",
        "RTD_CANADA_CONTROL",
        "RTD_FORBIDDEN_REDUCTION",
        "RTD_VECTOR_LIMIT",
        "RTD_CANONICAL_SIZE",
    }
    reader_only = {"RTD_JSON_DEPTH", "RTD_VECTOR_LIMIT", "RTD_CANONICAL_SIZE"}
    for case_index in range(256):
        if case_index == len(invalid):
            break
        case = invalid[case_index]
        if case.error in reader_only:
            continue
        with pytest.raises(RtdValidationError) as raised:
            parse_draft(case.draft)
        assert raised.value.code == case.error


@pytest.mark.parametrize(
    "payload",
    [
        b"{}\n" * 257,
        b'{"case_id":"' + (b"x" * 129) + b'","kind":"invalid","draft":{},"error":"RTD_JSON"}\n',
        b'{"case_id":"a","kind":"other","draft":{},"error":"RTD_JSON"}\n',
        b'{"case_id":"a","kind":"invalid","draft":{},"error":"RTD_JSON","extra":0}\n',
        b'{"case_id":"a","kind":"invalid","draft":{},"error":"RTD_JSON"} trailing\n',
    ],
)
def test_vector_reader_refuses_closed_envelope_violations(payload: bytes) -> None:
    with pytest.raises(RtdValidationError):
        parse_vector_corpus(payload)


def test_vector_reader_refuses_raw_line_and_depth_limits() -> None:
    with pytest.raises(RtdValidationError, match="RTD_VECTOR_LIMIT"):
        parse_vector_corpus(b"x" * 1_048_577)
    with pytest.raises(RtdValidationError, match="RTD_VECTOR_LIMIT"):
        parse_vector_corpus((b"x" * 262_145) + b"\n")
    nested = (
        b'{"case_id":"a","kind":"invalid","draft":'
        + (b'{"x":' * 32)
        + b"0"
        + (b"}" * 32)
        + b',"error":"RTD_JSON"}\n'
    )
    with pytest.raises(RtdValidationError, match="RTD_JSON_DEPTH"):
        parse_vector_corpus(nested)


def test_vector_reader_rejects_duplicate_case_id() -> None:
    line = b'{"case_id":"a","kind":"invalid","draft":{},"error":"RTD_JSON"}\n'
    with pytest.raises(RtdValidationError, match="RTD_DUPLICATE_KEY"):
        parse_vector_corpus(line + line)


def test_exact_canonical_size_plus_one_is_atomic() -> None:
    writer = _CanonicalWriter()
    writer._count = RTD_MAX_JSON_INPUT_BYTES
    with pytest.raises(RtdValidationError, match="RTD_CANONICAL_SIZE"):
        writer.write(b"x")
    assert writer.finish() == b""


def test_direct_draft_negative_zero_is_normalized_before_sealing() -> None:
    cases = parse_vector_corpus(VECTOR_PATH.read_bytes())
    case = None
    for case_index in range(256):
        if case_index == len(cases):
            break
        if cases[case_index].case_id == "negative-zero-normalizes":
            case = cases[case_index]
            break
    assert case is not None
    raw = RtdDossierDraftV1.model_validate(case.draft)
    assert raw.scale_memberships[0].weight_bits_or_null == "8000000000000000"
    sealed = seal_draft(raw)
    assert sealed.scale_memberships[0].weight_bits_or_null == "0000000000000000"
    assert sealed.projection_hash == case.projection_hash
