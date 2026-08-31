"""Independent behavioral checks for CommittedTickEnvelopeV1."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from tools.verify_committed_tick_envelope_v1 import (
    EnvelopeContractRefusal,
    load_contract,
    load_vectors,
    main,
    verify_all,
)

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "contracts" / "committed_tick_envelope_v1.yaml"
VECTORS = ROOT / "contracts" / "committed_tick_envelope_v1_vectors.jsonl"


def test_shared_contract_verifies_independently() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)

    assert contract["meta"]["contract"] == "CommittedTickEnvelopeV1"
    assert verify_all(contract, vectors) == []


@pytest.mark.parametrize(
    "family",
    [
        "graph",
        "state",
        "event",
        "checkpoint",
        "archive_dirty_receipt",
    ],
)
def test_each_row_family_mutation_refuses_stale_whole_payload_bytes(family: str) -> None:
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    envelope = next(row for row in vectors if row["id"] == "envelope-all-families")
    selected = envelope["data"]["families"][family]
    if family == "archive_dirty_receipt":
        selected["payload_hex"] = "ff"
    else:
        selected[0]["payload_hex"] = "ff"

    errors = verify_all(contract, vectors)

    assert any("envelope-all-families" in error for error in errors)


def test_compiled_family_order_drift_refuses() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)
    contract["row_families"][0]["name"] = "other"

    with pytest.raises(EnvelopeContractRefusal) as exc_info:
        verify_all(contract, vectors)

    assert exc_info.value.code == "compiled_contract_drift"


@pytest.mark.parametrize("malformation", ["missing", "out_of_order"])
def test_family_mapping_refuses_missing_or_out_of_order_input(malformation: str) -> None:
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    envelope = next(row for row in vectors if row["id"] == "envelope-all-families")
    expected = "row_family_shape"
    if malformation == "missing":
        envelope["data"]["families"].pop("event")
    else:
        families = envelope["data"]["families"]
        envelope["data"]["families"] = {
            "state": families["state"],
            "graph": families["graph"],
            **{name: rows for name, rows in families.items() if name not in {"graph", "state"}},
        }
        expected = "row_family_order"

    with pytest.raises(EnvelopeContractRefusal) as exc_info:
        verify_all(contract, vectors)

    assert exc_info.value.code == expected


def test_retry_vectors_cover_all_closed_outcomes() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)
    outcomes = {row["data"]["expected"] for row in vectors if row["kind"] == "retry"}

    assert outcomes == {
        "idempotent",
        "key_mismatch",
        "content_identity_mismatch",
        "whole_payload_mismatch",
    }
    assert verify_all(contract, vectors) == []


def test_missing_retry_outcome_refuses() -> None:
    contract = load_contract(SCHEMA)
    vectors = [row for row in load_vectors(VECTORS) if row["id"] != "retry-whole-payload-mismatch"]

    with pytest.raises(EnvelopeContractRefusal) as exc_info:
        verify_all(contract, vectors)

    assert exc_info.value.code == "retry_outcome_drift"


def test_non_text_retry_outcome_uses_typed_refusal() -> None:
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    retry = next(row for row in vectors if row["id"] == "retry-idempotent")
    retry["data"]["expected"] = []

    with pytest.raises(EnvelopeContractRefusal) as exc_info:
        verify_all(contract, vectors)

    assert exc_info.value.code == "retry_outcome_drift"


def test_duplicate_vector_id_refuses_before_indexing() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)
    duplicate = copy.deepcopy(vectors[1])
    duplicate["id"] = vectors[0]["id"]
    vectors.append(duplicate)

    with pytest.raises(EnvelopeContractRefusal) as exc_info:
        verify_all(contract, vectors)

    assert exc_info.value.code == "duplicate_vector_id"


@pytest.mark.parametrize("malformation", ["missing_id", "missing_data", "missing_reference"])
def test_malformed_vector_rows_use_typed_refusals(malformation: str) -> None:
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    expected = "vector_row_shape"
    if malformation == "missing_id":
        vectors[0].pop("id")
    elif malformation == "missing_data":
        vectors[0].pop("data")
    else:
        retry = next(row for row in vectors if row["id"] == "retry-idempotent")
        retry["data"]["requested_id"] = "envelope-missing"
        expected = "missing_vector_reference"

    with pytest.raises(EnvelopeContractRefusal) as exc_info:
        verify_all(contract, vectors)

    assert exc_info.value.code == expected


def test_cli_prints_typed_refusal_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    vectors = copy.deepcopy(load_vectors(VECTORS))
    vectors[0].pop("id")
    vectors_path = tmp_path / "malformed.jsonl"
    vectors_path.write_text(
        "\n".join(json.dumps(row, separators=(",", ":")) for row in vectors),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "verify_committed_tick_envelope_v1.py",
            "--schema",
            str(SCHEMA),
            "--vectors",
            str(vectors_path),
        ],
    )

    assert main() == 1
    assert capsys.readouterr().out == "vector_row_shape: 1\n"


def test_vector_loader_refuses_row_and_line_overflow(tmp_path: Path) -> None:
    row = '{"id":"x","kind":"x","data":{}}'
    rows_path = tmp_path / "rows.jsonl"
    rows_path.write_text("\n".join([row] * 65), encoding="utf-8")
    with pytest.raises(EnvelopeContractRefusal, match="too_many_rows"):
        load_vectors(rows_path)

    line_path = tmp_path / "line.jsonl"
    line_path.write_text("x" * 16_385, encoding="utf-8")
    with pytest.raises(EnvelopeContractRefusal, match="invalid_line_length"):
        load_vectors(line_path)


def test_vector_loader_refuses_duplicate_json_keys(tmp_path: Path) -> None:
    vectors_path = tmp_path / "duplicate-key.jsonl"
    vectors_path.write_text(
        '{"id":"a","id":"b","kind":"x","data":{}}',
        encoding="utf-8",
    )

    with pytest.raises(EnvelopeContractRefusal) as exc_info:
        load_vectors(vectors_path)

    assert exc_info.value.code == "duplicate_json_key"


def test_every_refusal_and_bound_vector_executes() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)

    assert {row["id"] for row in vectors if row["kind"] == "refusal"} == {
        "refusal-empty-key",
        "refusal-duplicate-key",
        "refusal-row-order",
        "refusal-missing-archive-dirty-receipt",
        "refusal-duplicate-archive-dirty-receipt",
    }
    assert {row["id"] for row in vectors if row["kind"] == "bound"} == {
        "bound-envelope-byte-maximum",
        "bound-family-byte-maximum-plus-one",
        "bound-aggregate-row-maximum",
        "bound-aggregate-row-maximum-plus-one",
        "bound-impossible-row-body",
    }
    assert verify_all(contract, vectors) == []


def test_live_envelope_is_five_sparse_families_with_one_mandatory_archive_receipt() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)

    assert [(row["name"], row["tag_u8"]) for row in contract["row_families"]] == [
        ("graph", 0x10),
        ("state", 0x11),
        ("event", 0x12),
        ("checkpoint", 0x16),
        ("archive_dirty_receipt", 0x17),
    ]
    assert contract["constants"]["family_count"] == 5
    assert contract["constants"]["fixed_envelope_bytes"] == 182
    assert contract["constants"]["max_envelope_bytes"] == 335_544_502
    assert len(vectors) == 28
    assert {
        kind: sum(row["kind"] == kind for row in vectors)
        for kind in {row["kind"] for row in vectors}
    } == {"envelope": 9, "mutation": 5, "retry": 4, "refusal": 5, "bound": 5}
    for row in vectors:
        if row["kind"] != "envelope":
            continue
        archive = row["data"]["families"]["archive_dirty_receipt"]
        assert set(archive) == {"key_hex", "payload_hex"}
