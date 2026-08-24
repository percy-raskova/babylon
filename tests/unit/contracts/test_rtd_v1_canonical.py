"""Cross-language canonical byte and hash contracts for RTD V1."""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.contracts.relational_territory_dossier_v1 import (
    RTD_MAX_JSON_INPUT_BYTES,
    RtdValidationError,
    canonical_draft_bytes,
    parse_draft,
    parse_vector_corpus,
    projection_hash,
    seal_draft,
)
from babylon.contracts.rtd_v1_generated import RtdDossierDraftV1

ROOT = Path(__file__).resolve().parents[3]
VECTOR_PATH = ROOT / "contracts" / "relational_territory_dossier_v1_vectors.jsonl"
SIZE_WITNESS_UNIFORM_ROWS = 10_485
SIZE_WITNESS_UNIFORM_ROW_BYTES = 6_399
SIZE_WITNESS_FINAL_ROW_BYTES = 3_781
SIZE_WITNESS_EMPTY_DRAFT_BYTES = 1_083
SIZE_WITNESS_FINAL_NULS = 501
SIZE_WITNESS_FINAL_XS = 520


def _invalid_vector_line(case_id: str, ending: bytes = b"\n") -> bytes:
    return (
        b'{"case_id":"'
        + case_id.encode("ascii")
        + b'","kind":"invalid","draft":{},"error":"RTD_JSON"}'
        + ending
    )


def _provenance_row(row_index: int, locator: str) -> dict[str, object]:
    return {
        "provenance_id": {
            "domain": "provenance",
            "authority": "size",
            "local_id": f"{row_index:05x}",
        },
        "artifact_digest": "55" * 32,
        "locator": locator,
        "vintage": "v",
        "evidence_class": "Derived",
        "transformation_digest_or_null": None,
    }


def _canonical_size_witness(*, one_extra_x: bool) -> RtdDossierDraftV1:
    cases = parse_vector_corpus(VECTOR_PATH.read_bytes())
    payload = None
    for case_index in range(256):
        if case_index == len(cases):
            break
        if cases[case_index].case_id == "minimal-admin":
            payload = dict(cases[case_index].draft)
            break
    assert payload is not None
    provenance: list[dict[str, object]] = []
    uniform_locator = "\x00" * 1_024
    for row_index in range(SIZE_WITNESS_UNIFORM_ROWS):
        provenance.append(_provenance_row(row_index, uniform_locator))
    final_locator = ("\x00" * SIZE_WITNESS_FINAL_NULS) + (
        "x" * (SIZE_WITNESS_FINAL_XS + int(one_extra_x))
    )
    provenance.append(
        _provenance_row(
            SIZE_WITNESS_UNIFORM_ROWS,
            final_locator,
        )
    )
    payload["provenance"] = provenance
    return parse_draft(payload)


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


def test_vector_reader_is_lf_oriented_with_crlf_and_cr_only_parity() -> None:
    lf = _invalid_vector_line("a") + _invalid_vector_line("b")
    crlf = _invalid_vector_line("a", b"\r\n") + _invalid_vector_line("b", b"\r\n")
    assert parse_vector_corpus(crlf) == parse_vector_corpus(lf)
    assert len(parse_vector_corpus(_invalid_vector_line("a", b"\r"))) == 1
    cr_only = _invalid_vector_line("a", b"\r") + _invalid_vector_line("b", b"\r")
    with pytest.raises(RtdValidationError, match="RTD_JSON"):
        parse_vector_corpus(cr_only)


def test_vector_reader_refuses_257_valid_lines_before_returning_cases() -> None:
    payload = bytearray()
    for line_index in range(257):
        payload.extend(_invalid_vector_line(f"case-{line_index}"))
    with pytest.raises(RtdValidationError, match="RTD_VECTOR_LIMIT"):
        parse_vector_corpus(bytes(payload))


def test_vector_reader_rejects_duplicate_case_id() -> None:
    line = b'{"case_id":"a","kind":"invalid","draft":{},"error":"RTD_JSON"}\n'
    with pytest.raises(RtdValidationError, match="RTD_DUPLICATE_KEY"):
        parse_vector_corpus(line + line)


def test_exact_canonical_size_is_accepted() -> None:
    expected_size = (
        SIZE_WITNESS_EMPTY_DRAFT_BYTES
        + (SIZE_WITNESS_UNIFORM_ROWS * SIZE_WITNESS_UNIFORM_ROW_BYTES)
        + SIZE_WITNESS_FINAL_ROW_BYTES
        + SIZE_WITNESS_UNIFORM_ROWS
    )
    assert expected_size == RTD_MAX_JSON_INPUT_BYTES
    draft = _canonical_size_witness(one_extra_x=False)
    assert len(canonical_draft_bytes(draft)) == RTD_MAX_JSON_INPUT_BYTES


def test_public_canonical_apis_refuse_limit_plus_one_without_result() -> None:
    expected_size = (
        SIZE_WITNESS_EMPTY_DRAFT_BYTES
        + (SIZE_WITNESS_UNIFORM_ROWS * SIZE_WITNESS_UNIFORM_ROW_BYTES)
        + SIZE_WITNESS_FINAL_ROW_BYTES
        + SIZE_WITNESS_UNIFORM_ROWS
        + 1
    )
    assert expected_size == RTD_MAX_JSON_INPUT_BYTES + 1
    draft = _canonical_size_witness(one_extra_x=True)
    for operation in (canonical_draft_bytes, projection_hash, seal_draft):
        with pytest.raises(RtdValidationError) as raised:
            operation(draft)
        assert raised.value.code == "RTD_CANONICAL_SIZE"


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
