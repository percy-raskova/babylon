"""Independent behavioral checks for TickCommitClaimV1."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from tools.verify_tick_commit_claim_v1 import (
    ClaimContractRefusal,
    load_contract,
    load_vectors,
    main,
    verify_all,
)

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "contracts" / "tick_commit_claim_v1.yaml"
VECTORS = ROOT / "contracts" / "tick_commit_claim_v1_vectors.jsonl"


def test_shared_contract_verifies_independently() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)

    assert contract["meta"]["contract"] == "TickCommitClaimV1"
    assert verify_all(contract, vectors) == []


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("campaign_id", "20112233-4455-6677-8899-aabbccddeeff"),
        ("resolve_tick", 44),
        ("tick_content_hash_hex", "33" * 32),
    ],
)
def test_semantic_mutation_refuses_stale_canonical_bytes(
    field: str, replacement: str | int
) -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)
    mutated = copy.deepcopy(vectors)
    claim = next(row for row in mutated if row["id"] == "claim-base")
    claim["data"][field] = replacement

    errors = verify_all(contract, mutated)

    assert any("claim-base" in error for error in errors)


def test_compiled_schema_drift_refuses() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)
    contract["constants"]["canonical_bytes"] = 94

    with pytest.raises(ClaimContractRefusal, match="compiled_contract_drift"):
        verify_all(contract, vectors)


@pytest.mark.parametrize(
    "mutation",
    ["contract", "version", "claim_fields", "claim_key", "content_link"],
)
def test_compiled_layout_and_identity_drift_refuses(mutation: str) -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)
    if mutation == "contract":
        contract["meta"]["contract"] = "TickCommitClaimV2"
    elif mutation == "version":
        contract["meta"]["version"] = 2
    elif mutation == "claim_fields":
        contract["layouts"]["tick_commit_claim_v1"]["fields"].pop()
    elif mutation == "claim_key":
        contract["layouts"]["tick_commit_claim_v1"]["key"].reverse()
    else:
        contract["layouts"]["tick_content_link_v1"]["fields"][1] = "other_digest32"

    with pytest.raises(ClaimContractRefusal) as exc_info:
        verify_all(contract, vectors)

    assert exc_info.value.code == "compiled_contract_drift"


def test_missing_retry_outcome_refuses() -> None:
    contract = load_contract(SCHEMA)
    vectors = [row for row in load_vectors(VECTORS) if row["id"] != "retry-content-mismatch"]

    with pytest.raises(ClaimContractRefusal) as exc_info:
        verify_all(contract, vectors)

    assert exc_info.value.code == "retry_outcome_drift"


def test_duplicate_vector_id_refuses_before_indexing() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)
    duplicate = copy.deepcopy(next(row for row in vectors if row["id"] == "claim-content-mutated"))
    duplicate["id"] = "claim-base"
    vectors.append(duplicate)

    with pytest.raises(ClaimContractRefusal) as exc_info:
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
        retry["data"]["requested_id"] = "claim-missing"
        expected = "missing_vector_reference"

    with pytest.raises(ClaimContractRefusal) as exc_info:
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
        ["verify_tick_commit_claim_v1.py", "--schema", str(SCHEMA), "--vectors", str(vectors_path)],
    )

    assert main() == 1
    assert capsys.readouterr().out == "vector_row_shape: 1\n"


def test_vector_loader_refuses_row_and_line_overflow(tmp_path: Path) -> None:
    row = '{"id":"x","kind":"x","data":{}}'
    rows_path = tmp_path / "rows.jsonl"
    rows_path.write_text("\n".join([row] * 33), encoding="utf-8")
    with pytest.raises(ClaimContractRefusal, match="too_many_rows"):
        load_vectors(rows_path)

    line_path = tmp_path / "line.jsonl"
    line_path.write_text("x" * 4097, encoding="utf-8")
    with pytest.raises(ClaimContractRefusal, match="invalid_line_length"):
        load_vectors(line_path)


def test_every_refusal_vector_executes() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)
    refusal_ids = {row["id"] for row in vectors if row["kind"] == "refusal"}

    assert refusal_ids == {
        "refusal-campaign-text",
        "refusal-negative-tick",
        "refusal-tick-overflow",
        "refusal-digest-length",
    }
    assert verify_all(contract, vectors) == []
