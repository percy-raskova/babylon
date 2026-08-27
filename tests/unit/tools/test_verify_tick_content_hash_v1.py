"""Independent checks for the language-neutral tick-content contract."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest
import yaml
from tools.verify_tick_content_hash_v1 import (
    ContractRefusal,
    _stable_graph,
    chacha8_stream,
    load_contract,
    load_vectors,
    main,
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


@pytest.mark.parametrize(
    "kind",
    [
        "replay_session",
        "replay_seed",
        "stable_element",
        "carrier_segment",
        "resolver_manifest",
        "stable_graph",
        "action_id",
        "ordered_action_batch",
        "prepared_environment",
        "register_manifest",
        "register_set",
        "stable_world",
        "tick_payload",
        "tick_content_hash",
    ],
)
@pytest.mark.parametrize("corruption", ["body", "truncated", "trailing"])
def test_every_nested_body_is_reconstructed_from_semantic_inputs(
    kind: str, corruption: str
) -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS, maximum_rows=256, maximum_line_bytes=262_144)
    row = next(row for row in vectors if row["kind"] == kind)
    canonical = bytearray.fromhex(row["data"]["canonical_hex"])
    if corruption == "body":
        canonical[-1] ^= 1
    elif corruption == "truncated":
        canonical.pop()
    else:
        canonical.append(0)
    row["data"]["canonical_hex"] = canonical.hex()
    row["data"]["digest_hex"] = hashlib.sha256(canonical).hexdigest()

    errors = verify_all(contract, vectors)

    assert any(row["id"] in error for error in errors)


def test_shared_contract_declares_complete_nested_layouts_and_float_rule() -> None:
    contract = load_contract(SCHEMA)
    layouts = contract["layouts"]

    assert contract["authority"]["invariants"][-2:] == [
        "Finite floating-point zero canonicalizes to positive zero before encoding.",
        "NaN and infinity are refused before canonical encoding.",
    ]
    for name in [
        "resolver_manifest_v1",
        "stable_graph_v1",
        "prepared_environment_v1",
        "world_register_manifest_v1",
        "world_register_set_v1",
        "stable_world_v1",
        "tick_payload_v1",
    ]:
        assert layouts[name]["sections"]


def test_corpus_covers_promised_extremes_and_structural_classes() -> None:
    vectors = load_vectors(VECTORS, maximum_rows=256, maximum_line_bytes=262_144)
    ids = {row["id"] for row in vectors}

    assert {
        "replay-session-minimum",
        "replay-session-maximum",
        "replay-seed-minimum",
        "replay-seed-negative-one",
        "replay-seed-zero",
        "replay-seed-one",
        "replay-seed-maximum",
        "stable-edge-key",
        "stable-hyperedge-key",
        "cross-allocation-stable-graph",
        "nonempty-ordered-action-batch",
        "vocabulary-absent",
        "vocabulary-present-empty",
        "bound-vector-rows-maximum-plus-one-refusal",
        "outer-nonempty-action-link-refusal",
        "outer-wrong-session-action-link-refusal",
        "outer-wrong-tick-action-link-refusal",
    } <= ids
    assert {
        f"bsl-type-{name.replace('_', '-')}"
        for name in (
            "probability",
            "intensity",
            "coefficient",
            "currency",
            "real",
            "int",
            "bool",
            "enum",
            "node_set",
            "edge_set",
        )
    } <= ids
    assert {
        f"bsl-value-{name.replace('_', '-')}"
        for name in (
            "int",
            "currency",
            "real",
            "ratio",
            "bool",
            "enum",
            "node_ref",
            "hyperedge_ref",
            "edge_ref",
        )
    } <= ids
    assert {
        f"shape-verb-{name}"
        for name in (
            "add-node",
            "remove-node",
            "add-edge",
            "remove-edge",
            "add-hyperedge",
            "remove-hyperedge",
        )
    } <= ids


def test_bound_refusal_rows_cover_every_declared_bound() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS, maximum_rows=256, maximum_line_bytes=262_144)
    refusal_rows = [
        row
        for row in vectors
        if row["kind"] == "refusal" and row["data"]["operation"] == "bound_case"
    ]

    assert {row["data"]["bound"] for row in refusal_rows} == set(contract["bounds"])
    assert all("accepted_input" in row["data"] for row in refusal_rows)
    assert all("refused_input" in row["data"] for row in refusal_rows)
    assert all("expected_code" in row["data"] for row in refusal_rows)
    removed = refusal_rows[-1]
    vectors.remove(removed)

    errors = verify_all(contract, vectors)

    assert any("bound refusal set" in error for error in errors)


def test_rng_v2_requires_a_graph_owned_stable_carrier_key() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS, maximum_rows=256, maximum_line_bytes=262_144)
    row = next(row for row in vectors if row["kind"] == "rng_v2")
    row["data"]["carrier_id"] = "stable-node-carrier-segment"

    errors = verify_all(contract, vectors)

    assert any(row["id"] in error for error in errors)


@pytest.mark.parametrize(
    ("action_id", "expected_code"),
    [
        ("nonempty-ordered-action-batch", "nonempty_runtime_actions"),
        ("empty-ordered-action-batch-wrong-session", "action_session_mismatch"),
        ("empty-ordered-action-batch-wrong-tick", "action_tick_mismatch"),
    ],
)
def test_outer_refuses_nonempty_or_mismatched_action_links(
    action_id: str, expected_code: str
) -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS, maximum_rows=256, maximum_line_bytes=262_144)
    row = next(row for row in vectors if row["kind"] == "tick_content_hash")
    row["data"]["actions_id"] = action_id

    errors = verify_all(contract, vectors)

    assert any(row["id"] in error and expected_code in error for error in errors)


def test_schema_declares_semantic_text_carrier_provenance_and_no_decoder() -> None:
    contract = load_contract(SCHEMA)

    assert contract["semantic_text"] == {
        "symbol": {"encoding": "ASCII", "minimum_bytes": 1, "maximum_bytes": 64},
        "qname": {
            "encoding": "ASCII",
            "minimum_bytes": 1,
            "maximum_bytes": 128,
            "maximum_segments": 4,
        },
        "structural_type": {
            "encoding": "graphic ASCII",
            "minimum_bytes": 1,
            "maximum_bytes": 128,
        },
        "intrinsic_identity": {
            "encoding": "ASCII",
            "minimum_bytes": 1,
            "maximum_bytes": 96,
        },
        "enum_type": {"encoding": "ASCII", "minimum_bytes": 1, "maximum_bytes": 64},
        "enum_member": {"encoding": "ASCII", "minimum_bytes": 1, "maximum_bytes": 64},
        "governance": {"encoding": "UTF-8", "maximum_bytes": 4_194_304},
    }
    carrier = contract["layouts"]["stable_carrier_key_v2"]
    assert carrier["provenance"] == "sealed graph resolver only"
    assert contract["production_decoder"] == "prohibited"


def test_governance_utf8_and_final_stable_carrier_are_reconstructed() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS, maximum_rows=256, maximum_line_bytes=262_144)
    ids = {row["id"] for row in vectors}

    assert {"governance-utf8", "stable-carrier-key-v2"} <= ids
    assert verify_all(contract, vectors) == []


def test_action_intent_limit_is_enforced_against_self_consistent_bytes() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS, maximum_rows=256, maximum_line_bytes=262_144)
    row = next(row for row in vectors if row["kind"] == "action_id")
    intent = b"x" * 16_385
    intent_digest = hashlib.sha256(intent).digest()
    session = row["data"]["session"].encode("ascii")
    canonical = b"".join(
        (
            b"babylon.practice-action-id.v1\0",
            (1).to_bytes(2, "big"),
            len(session).to_bytes(2, "big"),
            session,
            (2).to_bytes(2, "big"),
            intent_digest,
        )
    )
    row["data"]["intent_bytes_hex"] = intent.hex()
    row["data"]["intent_digest_hex"] = intent_digest.hex()
    row["data"]["canonical_hex"] = canonical.hex()
    row["data"]["digest_hex"] = hashlib.sha256(canonical).hexdigest()

    errors = verify_all(contract, vectors)

    assert any(row["id"] in error for error in errors)


def test_stable_graph_member_limit_precedes_member_semantics() -> None:
    data = {
        "scenario": "bounded",
        "nodes": [],
        "node_f64": [],
        "edges": [],
        "hyperedges": [
            {
                "local_name": "too-large",
                "hyperedge_type": "GROUP",
                "members": [None] * 65_537,
            }
        ],
        "edge_f64": [],
        "node_currency": [],
        "hyperedge_f64": [],
    }

    with pytest.raises(ContractRefusal, match="hyperedge_members"):
        _stable_graph(data)


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


def test_vector_loader_refuses_unbounded_or_malformed_jsonl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "vectors.jsonl"
    path.write_text("\n".join(json.dumps({"row": index}) for index in range(3)))

    with pytest.raises(ContractRefusal):
        load_vectors(path, maximum_rows=2, maximum_line_bytes=128)

    path.write_text("{" + ("x" * 128))
    with pytest.raises(ContractRefusal):
        load_vectors(path, maximum_rows=2, maximum_line_bytes=64)

    monkeypatch.setattr(Path, "read_bytes", lambda _path: pytest.fail("unbounded read"))
    with pytest.raises(ContractRefusal):
        load_vectors(path, maximum_rows=2, maximum_line_bytes=64)

    schema = tmp_path / "contract.yaml"
    schema.write_bytes(b"x" * 262_145)
    with pytest.raises(ContractRefusal, match="schema_too_large"):
        load_contract(schema)


def test_schema_cannot_widen_vector_loader_bounds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contract = load_contract(SCHEMA)
    contract["bounds"]["vector_rows"] = 257
    schema = tmp_path / "contract.yaml"
    schema.write_text(yaml.safe_dump(contract))
    vectors = tmp_path / "vectors.jsonl"
    vectors.write_text("{}\n")
    monkeypatch.setattr(
        sys,
        "argv",
        ["verify", "--schema", str(schema), "--vectors", str(vectors)],
    )
    monkeypatch.setattr(
        "tools.verify_tick_content_hash_v1.load_vectors",
        lambda *_args, **_kwargs: pytest.fail("schema widened vector loader"),
    )

    assert main() == 1
