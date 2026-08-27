"""Independent behavioral checks for TickCommitClaimV1."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
from tools.verify_tick_commit_claim_v1 import (
    ClaimContractRefusal,
    load_contract,
    load_vectors,
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
