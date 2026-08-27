"""Independent checks for the language-neutral tick-content contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tools.verify_tick_content_hash_v1 import (
    ContractRefusal,
    chacha8_stream,
    load_contract,
    load_vectors,
    verify_all,
    verify_ordered_tags,
)

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "contracts" / "tick_content_hash_v1.yaml"
VECTORS = ROOT / "contracts" / "tick_content_hash_v1_vectors.jsonl"


def test_shared_contract_and_vectors_verify_independently() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS, maximum_rows=256, maximum_line_bytes=262_144)

    assert contract["meta"]["contract"] == "TickContentHashV1"
    assert verify_all(contract, vectors) == []


def test_chacha8_crosses_a_block_and_fresh_f64_matches_corpus() -> None:
    vectors = load_vectors(VECTORS, maximum_rows=256, maximum_line_bytes=262_144)
    row = next(row for row in vectors if row["kind"] == "rng_v2")
    key = bytes.fromhex(row["data"]["stream_seed_hex"])

    assert chacha8_stream(key, 9) == row["data"]["first_nine_u64"]
    assert chacha8_stream(key, 1, as_f64_bits=True) == [row["data"]["fresh_f64_bits"]]


@pytest.mark.parametrize(
    "mutator",
    [
        lambda value: b"\xff" + value[1:],
        lambda value: value[:-1],
        lambda value: value + b"\x00",
        lambda value: value[:4] + bytes([2, 1]) + value[6:],
    ],
    ids=["unknown", "truncated", "trailing", "out-of-order"],
)
def test_bounded_tag_parser_refuses_unknown_truncated_trailing_and_order(
    mutator: object,
) -> None:
    valid = bytes.fromhex("01000000010200000001")
    broken = mutator(valid)  # type: ignore[operator]

    with pytest.raises(ContractRefusal):
        verify_ordered_tags(broken, expected_tags=(1, 2), payload_bytes=4)


def test_vector_loader_refuses_unbounded_or_malformed_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "vectors.jsonl"
    path.write_text("\n".join(json.dumps({"row": index}) for index in range(3)))

    with pytest.raises(ContractRefusal):
        load_vectors(path, maximum_rows=2, maximum_line_bytes=128)

    path.write_text("{" + ("x" * 128))
    with pytest.raises(ContractRefusal):
        load_vectors(path, maximum_rows=2, maximum_line_bytes=64)
