#!/usr/bin/env python3
"""Independently verify the language-neutral PER-60 identity contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

import yaml

MAX_CHACHA_U64 = 256
U32_MASK = (1 << 32) - 1
U64_MASK = (1 << 64) - 1


class ContractRefusal(ValueError):
    """A bounded contract input did not have its single canonical form."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code


def load_contract(path: Path) -> dict[str, Any]:
    """Load one bounded YAML mapping."""
    raw = path.read_bytes()
    if len(raw) > 262_144:
        raise ContractRefusal("schema_too_large", str(len(raw)))
    value = yaml.safe_load(raw)
    if not isinstance(value, dict):
        raise ContractRefusal("schema_shape", "top level must be a mapping")
    return value


def load_vectors(path: Path, *, maximum_rows: int, maximum_line_bytes: int) -> list[dict[str, Any]]:
    """Load bounded JSONL without accepting blank or non-object rows."""
    if maximum_rows < 1 or maximum_line_bytes < 2:
        raise ContractRefusal("invalid_loader_bound", "bounds must be positive")
    raw = path.read_bytes()
    maximum_file_bytes = maximum_rows * maximum_line_bytes
    if len(raw) > maximum_file_bytes:
        raise ContractRefusal("vector_file_too_large", str(len(raw)))
    lines = raw.splitlines()
    if len(lines) > maximum_rows:
        raise ContractRefusal("too_many_rows", str(len(lines)))
    rows: list[dict[str, Any]] = []
    for index in range(maximum_rows):
        if index >= len(lines):
            break
        line = lines[index]
        if not line or len(line) > maximum_line_bytes:
            raise ContractRefusal("invalid_line_length", str(index + 1))
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise ContractRefusal("invalid_json", str(index + 1)) from error
        if not isinstance(value, dict):
            raise ContractRefusal("row_shape", str(index + 1))
        rows.append(value)
    return rows


def _rotl32(value: int, count: int) -> int:
    return ((value << count) & U32_MASK) | (value >> (32 - count))


def _quarter_round(words: list[int], a: int, b: int, c: int, d: int) -> None:
    words[a] = (words[a] + words[b]) & U32_MASK
    words[d] = _rotl32(words[d] ^ words[a], 16)
    words[c] = (words[c] + words[d]) & U32_MASK
    words[b] = _rotl32(words[b] ^ words[c], 12)
    words[a] = (words[a] + words[b]) & U32_MASK
    words[d] = _rotl32(words[d] ^ words[a], 8)
    words[c] = (words[c] + words[d]) & U32_MASK
    words[b] = _rotl32(words[b] ^ words[c], 7)


def _chacha8_block(key: bytes, counter: int) -> bytes:
    if len(key) != 32 or counter < 0 or counter > U64_MASK:
        raise ContractRefusal("invalid_chacha_input", "key or counter")
    constants = (0x61707865, 0x3320646E, 0x79622D32, 0x6B206574)
    key_words = struct.unpack("<8I", key)
    initial = [*constants, *key_words, counter & U32_MASK, counter >> 32, 0, 0]
    words = initial.copy()
    for _round in range(4):
        _quarter_round(words, 0, 4, 8, 12)
        _quarter_round(words, 1, 5, 9, 13)
        _quarter_round(words, 2, 6, 10, 14)
        _quarter_round(words, 3, 7, 11, 15)
        _quarter_round(words, 0, 5, 10, 15)
        _quarter_round(words, 1, 6, 11, 12)
        _quarter_round(words, 2, 7, 8, 13)
        _quarter_round(words, 3, 4, 9, 14)
    output = tuple((words[index] + initial[index]) & U32_MASK for index in range(16))
    return struct.pack("<16I", *output)


def chacha8_stream(key: bytes, count: int, *, as_f64_bits: bool = False) -> list[int]:
    """Return at most 256 ChaCha8 u64 values or their exact f64 bit mapping."""
    if count < 0 or count > MAX_CHACHA_U64:
        raise ContractRefusal("chacha_count", str(count))
    output: list[int] = []
    block_count = (count + 7) // 8
    for block_index in range(32):
        if block_index >= block_count:
            break
        block = _chacha8_block(key, block_index)
        for word_index in range(8):
            if len(output) >= count:
                break
            value = int.from_bytes(block[word_index * 8 : word_index * 8 + 8], "little")
            if as_f64_bits:
                mapped = (value >> 11) * (2.0**-53)
                value = int.from_bytes(struct.pack(">d", mapped), "big")
            output.append(value)
    return output


def verify_ordered_tags(
    value: bytes, *, expected_tags: tuple[int, ...], payload_bytes: int
) -> None:
    """Verify one fixed-payload, exactly ordered, no-trailing tag sequence."""
    if payload_bytes < 0:
        raise ContractRefusal("invalid_payload_bound", str(payload_bytes))
    offset = 0
    for expected in expected_tags:
        if offset >= len(value):
            raise ContractRefusal("truncated", str(offset))
        actual = value[offset]
        if actual not in expected_tags:
            raise ContractRefusal("unknown_tag", str(actual))
        if actual != expected:
            raise ContractRefusal("tag_order", f"{actual} != {expected}")
        offset += 1 + payload_bytes
        if offset > len(value):
            raise ContractRefusal("truncated", str(offset))
    if offset != len(value):
        raise ContractRefusal("trailing_bytes", str(len(value) - offset))


def _ascii(value: str) -> bytes:
    try:
        encoded = value.encode("ascii")
    except UnicodeEncodeError as error:
        raise ContractRefusal("non_ascii", value) from error
    if not encoded or any(byte < 0x21 or byte > 0x7E for byte in encoded):
        raise ContractRefusal("non_graphic_ascii", value)
    return encoded


def _str16(value: str) -> bytes:
    encoded = _ascii(value)
    if len(encoded) > 256:
        raise ContractRefusal("string_too_long", value)
    return len(encoded).to_bytes(2, "big") + encoded


def _str32(value: str) -> bytes:
    encoded = _ascii(value)
    return len(encoded).to_bytes(4, "big") + encoded


def _rng_v1_preimage(data: dict[str, Any]) -> bytes:
    session = _ascii(data["session"])
    domain = _ascii(data["domain"])
    carrier = _ascii(data["carrier"])
    return b"".join(
        (
            session,
            int(data["tick"]).to_bytes(8, "little"),
            int(data["salt"]).to_bytes(8, "little"),
            len(domain).to_bytes(8, "little"),
            domain,
            len(carrier).to_bytes(8, "little"),
            carrier,
        )
    )


def _rng_v2_preimage(data: dict[str, Any]) -> bytes:
    domain = _ascii(data["domain"])
    carrier = _ascii(data["carrier"])
    return b"".join(
        (
            b"babylon.rng-stream\0",
            (2).to_bytes(4, "big"),
            b"\x01",
            int(data["seed"]).to_bytes(8, "big", signed=True),
            b"\x02",
            _str16(data["session"]),
            b"\x03",
            int(data["tick"]).to_bytes(8, "big"),
            b"\x04",
            len(domain).to_bytes(4, "big"),
            domain,
            b"\x05",
            len(carrier).to_bytes(4, "big"),
            carrier,
        )
    )


def _stable_element(data: dict[str, Any]) -> bytes:
    kind = data["element_kind"]
    fields = [_str32(data["scenario"])]
    if kind == "node":
        tag = 1
        fields.append(_str32(data["local_name"]))
    elif kind == "edge":
        tag = 2
        fields.extend(
            _str32(data[name]) for name in ("edge_type", "source_local_name", "target_local_name")
        )
    elif kind == "hyperedge":
        tag = 3
        fields.append(_str32(data["local_name"]))
    else:
        raise ContractRefusal("stable_element_kind", str(kind))
    return b"babylon.stable-element\0" + (1).to_bytes(4, "big") + bytes([tag]) + b"".join(fields)


def _carrier_segment(data: dict[str, Any]) -> bytes:
    parts = [_ascii(part) for part in data["segments"]]
    return b"|".join(str(len(part)).encode("ascii") + b":" + part for part in parts)


def _action_id(data: dict[str, Any]) -> bytes:
    return b"".join(
        (
            b"babylon.practice-action-id.v1\0",
            (1).to_bytes(2, "big"),
            _str16(data["session"]),
            (2).to_bytes(2, "big"),
            bytes.fromhex(data["intent_digest_hex"]),
        )
    )


def _empty_action_batch(data: dict[str, Any]) -> bytes:
    return b"".join(
        (
            b"babylon.ordered-practice-action-batch.v1\0",
            (1).to_bytes(2, "big"),
            _str16(data["session"]),
            int(data["resolve_tick"]).to_bytes(8, "big"),
            (0).to_bytes(2, "big"),
        )
    )


def _tick_content(data: dict[str, Any]) -> bytes:
    output = bytearray(b"babylon.tick-content\0" + (1).to_bytes(4, "big"))
    output.extend(b"\x01" + (1).to_bytes(4, "big") + _str16(data["session"]))
    output.extend(b"\x02" + int(data["resolve_tick"]).to_bytes(8, "big"))
    output.extend(b"\x03" + (1).to_bytes(4, "big") + (2).to_bytes(4, "big"))
    output.extend(int(data["seed"]).to_bytes(8, "big", signed=True))
    output.extend(b"\x04" + (1).to_bytes(4, "big"))
    output.extend(bytes.fromhex(data["defines_digest_hex"]))
    output.extend(bytes.fromhex(data["rules_digest_hex"]))
    for tag, name in enumerate(
        ("reference", "prepared", "prior_world", "actions", "result_world", "payload"),
        start=5,
    ):
        output.extend(bytes([tag]) + (1).to_bytes(4, "big"))
        output.extend(bytes.fromhex(data[f"{name}_digest_hex"]))
    return bytes(output)


def _canonical_for(row: dict[str, Any]) -> bytes | None:
    kind = row["kind"]
    data = row["data"]
    builders = {
        "replay_session": lambda: _str16(data["session"]),
        "replay_seed": lambda: int(data["seed"]).to_bytes(8, "big", signed=True),
        "stable_element": lambda: _stable_element(data),
        "carrier_segment": lambda: _carrier_segment(data),
        "action_id": lambda: _action_id(data),
        "ordered_action_batch": lambda: _empty_action_batch(data),
        "tick_content_hash": lambda: _tick_content(data),
    }
    builder = builders.get(kind)
    return None if builder is None else builder()


def _verify_rng(data: dict[str, Any], *, version: int) -> None:
    preimage = _rng_v1_preimage(data) if version == 1 else _rng_v2_preimage(data)
    if preimage.hex() != data["preimage_hex"]:
        raise ContractRefusal("rng_preimage", f"V{version}")
    key = hashlib.sha256(preimage).digest()
    if key.hex() != data["stream_seed_hex"]:
        raise ContractRefusal("rng_key", f"V{version}")
    expected = data["first_four_u64"] if version == 1 else data["first_nine_u64"]
    if chacha8_stream(key, len(expected)) != expected:
        raise ContractRefusal("rng_stream", f"V{version}")
    if version == 2 and chacha8_stream(key, 1, as_f64_bits=True) != [data["fresh_f64_bits"]]:
        raise ContractRefusal("rng_f64", "V2")


def _verify_domain_row(contract: dict[str, Any], row: dict[str, Any]) -> None:
    kind = row["kind"]
    layout_names = {
        "resolver_manifest": "resolver_manifest_v1",
        "stable_graph": "stable_graph_v1",
        "prepared_environment": "prepared_environment_v1",
        "register_manifest": "world_register_manifest_v1",
        "register_set": "world_register_set_v1",
        "stable_world": "stable_world_v1",
        "tick_payload": "tick_payload_v1",
    }
    layout = contract["layouts"][layout_names[kind]]
    expected = layout["domain_ascii_nul"].encode("ascii") + b"\0"
    canonical = bytes.fromhex(row["data"]["canonical_hex"])
    if not canonical.startswith(expected + (1).to_bytes(4, "big")):
        raise ContractRefusal("domain_or_layout", kind)


def _verify_refusal(row: dict[str, Any]) -> None:
    data = row["data"]
    try:
        verify_ordered_tags(
            bytes.fromhex(data["canonical_hex"]),
            expected_tags=tuple(data["expected_tags"]),
            payload_bytes=data["payload_bytes"],
        )
    except ContractRefusal as error:
        if error.code != data["expected_code"]:
            raise ContractRefusal("wrong_refusal", error.code) from error
        return
    raise ContractRefusal("missing_refusal", row["id"])


def _verify_row(contract: dict[str, Any], row: dict[str, Any]) -> None:
    if set(row) != {"id", "kind", "data"} or not isinstance(row["data"], dict):
        raise ContractRefusal("row_fields", str(row.get("id")))
    kind = row["kind"]
    data = row["data"]
    if kind == "rng_v1":
        _verify_rng(data, version=1)
    elif kind == "rng_v2":
        _verify_rng(data, version=2)
    elif kind == "bsl_discriminant":
        if data["tables"] != contract["bsl_discriminants"]:
            raise ContractRefusal("bsl_discriminants", row["id"])
    elif kind == "mutation":
        before = bytes.fromhex(data["before_hex"])
        after = bytes.fromhex(data["after_hex"])
        if before == after or hashlib.sha256(before).digest() == hashlib.sha256(after).digest():
            raise ContractRefusal("mutation_did_not_change_identity", row["id"])
    elif kind == "refusal":
        _verify_refusal(row)
    elif kind in {
        "resolver_manifest",
        "stable_graph",
        "prepared_environment",
        "register_manifest",
        "register_set",
        "stable_world",
        "tick_payload",
    }:
        _verify_domain_row(contract, row)
    canonical = _canonical_for(row)
    expected_hex = data.get("canonical_hex")
    if canonical is not None and canonical.hex() != expected_hex:
        raise ContractRefusal("canonical_bytes", row["id"])
    if expected_hex is not None and "digest_hex" in data:
        digest = hashlib.sha256(bytes.fromhex(expected_hex)).hexdigest()
        if digest != data["digest_hex"]:
            raise ContractRefusal("digest", row["id"])


def verify_all(contract: dict[str, Any], vectors: list[dict[str, Any]]) -> list[str]:
    """Return every independent contract error in stable vector order."""
    errors: list[str] = []
    required = set(contract["vector_families"]["required"])
    received = {row.get("kind") for row in vectors}
    if received != required:
        errors.append(
            f"vector families: missing={sorted(required - received)} extra={sorted(received - required)}"
        )
    for index in range(256):
        if index >= len(vectors):
            break
        row = vectors[index]
        try:
            _verify_row(contract, row)
        except (ContractRefusal, KeyError, TypeError, ValueError) as error:
            errors.append(f"{row.get('id', index)}: {error}")
    return errors


def main() -> int:
    """Verify the repository-owned contract and print stable diagnostics."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--vectors", type=Path, required=True)
    args = parser.parse_args()
    contract = load_contract(args.schema)
    bounds = contract["bounds"]
    vectors = load_vectors(
        args.vectors,
        maximum_rows=bounds["vector_rows"],
        maximum_line_bytes=bounds["vector_line_bytes"],
    )
    errors = verify_all(contract, vectors)
    for error in errors[:256]:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
