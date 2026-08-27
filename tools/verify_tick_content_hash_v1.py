#!/usr/bin/env python3
"""Independently verify the language-neutral PER-60 identity contract."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

import yaml

MAX_CHACHA_U64 = 256
MAX_VECTOR_ROWS = 256
MAX_SECTION_ROWS = 1_048_576
MAX_SCHEMA_BYTES = 262_144
U32_MASK = (1 << 32) - 1
U64_MASK = (1 << 64) - 1
COMPILED_BOUNDS = {
    "vector_rows": 256,
    "vector_line_bytes": 262_144,
    "symbol_bytes": 64,
    "qname_bytes": 128,
    "qname_segments": 4,
    "structural_type_bytes": 128,
    "intrinsic_identity_bytes": 96,
    "enum_type_bytes": 64,
    "enum_member_bytes": 64,
    "governance_utf8_bytes": 4_194_304,
    "stable_carrier_active_elements": 256,
    "stable_carrier_bytes": 131_072,
    "resolver_rows": 65_536,
    "resolver_edges": 65_536,
    "resolver_hyperedge_members": 65_536,
    "resolver_fact_units": 1_048_576,
    "resolver_manifest_bytes": 16_777_216,
    "stable_graph_elements": 65_536,
    "stable_graph_attribute_rows": 1_048_576,
    "stable_graph_hyperedge_members": 65_536,
    "stable_graph_fact_units": 1_048_576,
    "stable_graph_bytes": 67_108_864,
    "ordered_action_items": 4_096,
    "practice_intent_bytes": 16_384,
    "ordered_action_batch_bytes": 67_256_631,
    "prepared_rows": 65_536,
    "prepared_small_rows": 64,
    "identity_members": 1_048_576,
    "identity_aggregate_rows": 1_048_576,
    "identity_section_bytes": 67_108_864,
    "tick_rule_outcomes": 65_536,
    "tick_rows": 1_048_576,
}
COMPILED_SEMANTIC_TEXT = {
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


class ContractRefusal(ValueError):
    """A bounded contract input did not have its single canonical form."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code


def _verify_compiled_bounds(contract: dict[str, Any]) -> None:
    bounds = contract["bounds"]
    for name, compiled in COMPILED_BOUNDS.items():
        if bounds[name] != compiled:
            raise ContractRefusal("compiled_bound_drift", name)
    if bounds["replay_session_bytes"] != {"minimum": 1, "maximum": 256}:
        raise ContractRefusal("compiled_bound_drift", "replay_session_bytes")
    if bounds["rng_domain_bytes"] != {"minimum": 1, "maximum": 128}:
        raise ContractRefusal("compiled_bound_drift", "rng_domain_bytes")
    if bounds["rng_domain_segments"] != {"minimum": 2, "maximum": 4}:
        raise ContractRefusal("compiled_bound_drift", "rng_domain_segments")
    if set(contract["bound_refusals"]) != set(bounds):
        raise ContractRefusal("compiled_bound_drift", "bound_refusals")
    if contract["semantic_text"] != COMPILED_SEMANTIC_TEXT:
        raise ContractRefusal("compiled_semantic_text_drift", "semantic_text")
    if contract["production_decoder"] != "prohibited":
        raise ContractRefusal("compiled_decoder_drift", "production_decoder")


def load_contract(path: Path) -> dict[str, Any]:
    """Load one bounded YAML mapping."""
    with path.open("rb") as stream:
        raw = stream.read(MAX_SCHEMA_BYTES + 1)
    if len(raw) > MAX_SCHEMA_BYTES:
        raise ContractRefusal("schema_too_large", str(len(raw)))
    value = yaml.safe_load(raw)
    if not isinstance(value, dict):
        raise ContractRefusal("schema_shape", "top level must be a mapping")
    return value


def load_vectors(path: Path, *, maximum_rows: int, maximum_line_bytes: int) -> list[dict[str, Any]]:
    """Load bounded JSONL without accepting blank or non-object rows."""
    if maximum_rows < 1 or maximum_line_bytes < 2:
        raise ContractRefusal("invalid_loader_bound", "bounds must be positive")
    rows: list[dict[str, Any]] = []
    with path.open("rb") as stream:
        for index in range(maximum_rows + 1):
            line = stream.readline(maximum_line_bytes + 2)
            if not line:
                break
            if index == maximum_rows:
                raise ContractRefusal("too_many_rows", str(index + 1))
            content = line[:-1] if line.endswith(b"\n") else line
            if content.endswith(b"\r"):
                content = content[:-1]
            if not content or len(content) > maximum_line_bytes:
                raise ContractRefusal("invalid_line_length", str(index + 1))
            try:
                value = json.loads(content)
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
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
    if not isinstance(value, str):
        raise ContractRefusal("non_ascii", type(value).__name__)
    try:
        encoded = value.encode("ascii")
    except UnicodeEncodeError as error:
        raise ContractRefusal("non_ascii", value) from error
    if not encoded or any(byte < 0x21 or byte > 0x7E for byte in encoded):
        raise ContractRefusal("non_graphic_ascii", value)
    return encoded


def _symbol(value: str) -> bytes:
    encoded = _ascii(value)
    if len(encoded) > COMPILED_BOUNDS["symbol_bytes"]:
        raise ContractRefusal("invalid_symbol", value[:64])
    for index, byte in enumerate(encoded):
        lowercase = ord("a") <= byte <= ord("z")
        digit = ord("0") <= byte <= ord("9")
        valid = lowercase if index == 0 else lowercase or digit or byte == ord("-")
        if not valid:
            raise ContractRefusal("invalid_symbol", value[:64])
    return encoded


def _qname(value: str, *, minimum_segments: int = 1) -> bytes:
    if not isinstance(value, str):
        raise ContractRefusal("invalid_qname", type(value).__name__)
    try:
        encoded = value.encode("ascii")
    except UnicodeEncodeError as error:
        raise ContractRefusal("invalid_qname", value[:64]) from error
    if not encoded or len(encoded) > COMPILED_BOUNDS["qname_bytes"]:
        raise ContractRefusal("invalid_qname", str(value)[:64])
    segments = value.split("/")
    if not minimum_segments <= len(segments) <= COMPILED_BOUNDS["qname_segments"]:
        raise ContractRefusal("invalid_qname", value[:64])
    try:
        for segment in segments:
            _symbol(segment)
    except (UnicodeEncodeError, ContractRefusal) as error:
        raise ContractRefusal("invalid_qname", value[:64]) from error
    return encoded


def _structural_type(value: str) -> bytes:
    encoded = _ascii(value)
    if len(encoded) > COMPILED_BOUNDS["structural_type_bytes"]:
        raise ContractRefusal("invalid_structural_type", value[:64])
    return encoded


def _enum_type(value: str) -> bytes:
    encoded = _ascii(value)
    if len(encoded) > COMPILED_BOUNDS["enum_type_bytes"]:
        raise ContractRefusal("invalid_enum_type", value[:64])
    for index, byte in enumerate(encoded):
        uppercase = ord("A") <= byte <= ord("Z")
        lowercase = ord("a") <= byte <= ord("z")
        digit = ord("0") <= byte <= ord("9")
        valid = uppercase if index == 0 else uppercase or lowercase or digit
        if not valid:
            raise ContractRefusal("invalid_enum_type", value[:64])
    return encoded


def _enum_member(value: str) -> bytes:
    encoded = _ascii(value)
    if len(encoded) > COMPILED_BOUNDS["enum_member_bytes"]:
        raise ContractRefusal("invalid_enum_member", value[:64])
    for index, byte in enumerate(encoded):
        uppercase = ord("A") <= byte <= ord("Z")
        digit = ord("0") <= byte <= ord("9")
        valid = uppercase if index == 0 else uppercase or digit or byte == ord("_")
        if not valid:
            raise ContractRefusal("invalid_enum_member", value[:64])
    return encoded


def _intrinsic_identity(value: str) -> bytes:
    if not isinstance(value, str):
        raise ContractRefusal("invalid_intrinsic_identity", type(value).__name__)
    try:
        encoded = value.encode("ascii")
    except UnicodeEncodeError as error:
        raise ContractRefusal("invalid_intrinsic_identity", value[:64]) from error
    if (
        not encoded
        or len(encoded) > COMPILED_BOUNDS["intrinsic_identity_bytes"]
        or any(byte in b"|\r\n" for byte in encoded)
    ):
        raise ContractRefusal("invalid_intrinsic_identity", value[:64])
    return encoded


def _governance(value: str) -> bytes:
    if not isinstance(value, str):
        raise ContractRefusal("invalid_governance_string", type(value).__name__)
    encoded = value.encode("utf-8")
    if len(encoded) > COMPILED_BOUNDS["governance_utf8_bytes"]:
        raise ContractRefusal("governance_string_too_long", str(len(encoded)))
    return encoded


def _framed32(value: bytes, field: str) -> bytes:
    return _u32(len(value), field) + value


def _str16(value: str) -> bytes:
    encoded = _ascii(value)
    if len(encoded) > 256:
        raise ContractRefusal("string_too_long", value)
    return len(encoded).to_bytes(2, "big") + encoded


def _str32(value: str) -> bytes:
    encoded = _ascii(value)
    return _framed32(encoded, "str32 length")


def _governance_str32(value: str) -> bytes:
    return _framed32(_governance(value), "governance length")


def _hex_bytes(value: str, *, exact: int | None = None) -> bytes:
    if len(value) % 2 != 0 or any(character not in "0123456789abcdef" for character in value):
        raise ContractRefusal("invalid_hex", value[:64])
    decoded = bytes.fromhex(value)
    if exact is not None and len(decoded) != exact:
        raise ContractRefusal("invalid_hex_length", f"{len(decoded)} != {exact}")
    return decoded


def _bounded_int(value: Any, *, minimum: int, maximum: int, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum or value > maximum:
        raise ContractRefusal("integer_range", field)
    return value


def _u16(value: Any, field: str) -> bytes:
    return _bounded_int(value, minimum=0, maximum=(1 << 16) - 1, field=field).to_bytes(2, "big")


def _u32(value: Any, field: str) -> bytes:
    return _bounded_int(value, minimum=0, maximum=(1 << 32) - 1, field=field).to_bytes(4, "big")


def _u64(value: Any, field: str) -> bytes:
    return _bounded_int(value, minimum=0, maximum=U64_MASK, field=field).to_bytes(8, "big")


def _i64(value: Any, field: str) -> bytes:
    return _bounded_int(value, minimum=-(1 << 63), maximum=(1 << 63) - 1, field=field).to_bytes(
        8, "big", signed=True
    )


def _i128_text(value: Any, field: str) -> bytes:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise ContractRefusal("integer_shape", field) from error
    if str(parsed) != str(value) or parsed < -(1 << 127) or parsed > (1 << 127) - 1:
        raise ContractRefusal("integer_range", field)
    return parsed.to_bytes(16, "big", signed=True)


def _counted_rows(rows: Any, *, maximum: int, field: str) -> list[dict[str, Any]]:
    if not isinstance(rows, list) or len(rows) > maximum:
        raise ContractRefusal("row_limit", field)
    if any(not isinstance(row, dict) for row in rows):
        raise ContractRefusal("row_shape", field)
    return rows


def _bounded_bytes(value: bytes | bytearray, *, maximum: int, field: str) -> bytes:
    if len(value) > maximum:
        raise ContractRefusal("byte_limit", field)
    return bytes(value)


def _canonical_f64_bits(value: str) -> bytes:
    bits = int.from_bytes(_hex_bytes(value, exact=8), "big")
    exponent = (bits >> 52) & 0x7FF
    mantissa = bits & ((1 << 52) - 1)
    if exponent == 0x7FF:
        raise ContractRefusal("non_finite", value)
    if exponent == 0 and mantissa == 0:
        bits = 0
    return bits.to_bytes(8, "big")


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


def _rng_v2_preimage(data: dict[str, Any], rows_by_id: dict[str, dict[str, Any]]) -> bytes:
    try:
        domain = _qname(data["domain"], minimum_segments=2)
    except (UnicodeEncodeError, ContractRefusal) as error:
        raise ContractRefusal("invalid_rng_domain", str(data.get("domain"))[:64]) from error
    carrier_row = rows_by_id[data["carrier_id"]]
    if carrier_row.get("kind") != "stable_carrier_key":
        raise ContractRefusal("carrier_provenance", data["carrier_id"])
    carrier = _stable_carrier_key(carrier_row["data"], rows_by_id)
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
    _qname(data["scenario"])
    fields = [_str32(data["scenario"])]
    if kind == "node":
        tag = 1
        _symbol(data["local_name"])
        fields.append(_str32(data["local_name"]))
    elif kind == "edge":
        tag = 2
        _structural_type(data["edge_type"])
        _symbol(data["source_local_name"])
        _symbol(data["target_local_name"])
        fields.extend(
            _str32(data[name]) for name in ("edge_type", "source_local_name", "target_local_name")
        )
    elif kind == "hyperedge":
        tag = 3
        _symbol(data["local_name"])
        fields.append(_str32(data["local_name"]))
    else:
        raise ContractRefusal("stable_element_kind", str(kind))
    return b"babylon.stable-element\0" + (1).to_bytes(4, "big") + bytes([tag]) + b"".join(fields)


def _carrier_segment(data: dict[str, Any]) -> bytes:
    segments = data["segments"]
    if not isinstance(segments, list) or len(segments) not in (3, 5):
        raise ContractRefusal("carrier_segment_shape", "stable element")
    kind = segments[0]
    if (kind in {"node", "hyperedge"} and len(segments) != 3) or (
        kind == "edge" and len(segments) != 5
    ):
        raise ContractRefusal("carrier_segment_shape", str(kind))
    _qname(segments[1])
    if kind == "edge":
        _structural_type(segments[2])
        _symbol(segments[3])
        _symbol(segments[4])
    elif kind in {"node", "hyperedge"}:
        _symbol(segments[2])
    else:
        raise ContractRefusal("carrier_segment_kind", str(kind))
    parts = [_ascii(part) for part in segments]
    canonical = b"|".join(str(len(part)).encode("ascii") + b":" + part for part in parts)
    return canonical


def _stable_carrier_key(data: dict[str, Any], rows_by_id: dict[str, dict[str, Any]]) -> bytes:
    active_ids = data["active_segment_ids"]
    if (
        not isinstance(active_ids, list)
        or len(active_ids) > COMPILED_BOUNDS["stable_carrier_active_elements"]
    ):
        raise ContractRefusal("active_element_limit", "stable carrier")
    segment_ids = [data["subject_segment_id"], *active_ids]
    _validate_carrier_provenance(data, segment_ids, rows_by_id)
    segments: list[bytes] = []
    for row_id in segment_ids[: COMPILED_BOUNDS["stable_carrier_active_elements"] + 1]:
        linked = rows_by_id[row_id]
        if linked.get("kind") != "carrier_segment":
            raise ContractRefusal("carrier_provenance", str(row_id))
        segments.append(_carrier_segment(linked["data"]))
    slot = _bounded_int(
        data["draw_slot"], minimum=-(1 << 63), maximum=(1 << 63) - 1, field="draw slot"
    )
    segments.append(str(slot).encode("ascii"))
    canonical = b"|".join(
        str(len(segment)).encode("ascii") + b":" + segment for segment in segments
    )
    return _bounded_bytes(
        canonical,
        maximum=COMPILED_BOUNDS["stable_carrier_bytes"],
        field="stable carrier",
    )


def _validate_carrier_provenance(
    data: dict[str, Any],
    segment_ids: list[str],
    rows_by_id: dict[str, dict[str, Any]],
) -> None:
    resolver = rows_by_id.get(data.get("resolver_id"))
    stable_graph = rows_by_id.get(data.get("stable_graph_id"))
    if (
        resolver is None
        or resolver.get("kind") != "resolver_manifest"
        or stable_graph is None
        or stable_graph.get("kind") != "stable_graph"
    ):
        raise ContractRefusal("carrier_provenance", "missing sealed witnesses")
    resolver_data = resolver["data"]
    graph_data = stable_graph["data"]
    if resolver_data["scenario"] != graph_data["scenario"]:
        raise ContractRefusal("carrier_provenance", "scenario witness mismatch")
    resolver_nodes = {row["local_name"]: row["node_type"] for row in resolver_data["nodes"]}
    graph_nodes = {row["local_name"]: row["node_type"] for row in graph_data["nodes"]}
    resolver_hyperedges = {
        row["local_name"]: row["hyperedge_type"] for row in resolver_data["hyperedges"]
    }
    graph_hyperedges = {
        row["local_name"]: row["hyperedge_type"] for row in graph_data["hyperedges"]
    }
    if resolver_nodes != graph_nodes or resolver_hyperedges != graph_hyperedges:
        raise ContractRefusal("carrier_provenance", "resolver graph mismatch")
    graph_edges = {(row["edge_type"], row["source"], row["target"]) for row in graph_data["edges"]}
    for row_id in segment_ids[: COMPILED_BOUNDS["stable_carrier_active_elements"] + 1]:
        linked = rows_by_id.get(row_id)
        if linked is None or linked.get("kind") != "carrier_segment":
            raise ContractRefusal("carrier_provenance", str(row_id))
        segments = linked["data"]["segments"]
        if segments[1] != resolver_data["scenario"]:
            raise ContractRefusal("carrier_provenance", str(row_id))
        kind = segments[0]
        sealed = (
            (kind == "node" and segments[2] in resolver_nodes)
            or (kind == "hyperedge" and segments[2] in resolver_hyperedges)
            or (
                kind == "edge"
                and segments[3] in resolver_nodes
                and segments[4] in resolver_nodes
                and tuple(segments[2:5]) in graph_edges
            )
        )
        if not sealed:
            raise ContractRefusal("carrier_provenance", str(row_id))


def _resolver_manifest(data: dict[str, Any]) -> bytes:
    _qname(data["scenario"])
    nodes = _counted_rows(data["nodes"], maximum=65_536, field="resolver nodes")
    hyperedges = _counted_rows(data["hyperedges"], maximum=65_536, field="resolver hyperedges")
    if len(nodes) + len(hyperedges) > 65_536:
        raise ContractRefusal("row_limit", "resolver rows")
    sorted_nodes = sorted(nodes, key=lambda row: _ascii(row["local_name"]))
    sorted_hyperedges = sorted(hyperedges, key=lambda row: _ascii(row["local_name"]))
    output = bytearray(b"babylon.stable-element-resolver\0" + _u32(1, "resolver layout"))
    output.extend(b"\x01" + _str32(data["scenario"]))
    output.extend(b"\x02" + _u32(len(sorted_nodes), "resolver node count"))
    for row in sorted_nodes[:65_536]:
        _symbol(row["local_name"])
        _structural_type(row["node_type"])
        output.extend(_str32(row["local_name"]) + _str32(row["node_type"]))
    output.extend(b"\x03" + _u32(len(sorted_hyperedges), "resolver hyperedge count"))
    for row in sorted_hyperedges[:65_536]:
        _symbol(row["local_name"])
        _structural_type(row["hyperedge_type"])
        output.extend(_str32(row["local_name"]) + _str32(row["hyperedge_type"]))
    return _bounded_bytes(output, maximum=16_777_216, field="resolver manifest")


def _stable_graph(data: dict[str, Any]) -> bytes:
    _qname(data["scenario"])
    sections = [
        (2, "nodes", _stable_node_row, 65_536),
        (3, "node_f64", _stable_node_f64_row, 1_048_576),
        (4, "edges", _stable_edge_row, 65_536),
        (5, "hyperedges", _stable_hyperedge_row, 65_536),
        (6, "edge_f64", _stable_edge_f64_row, 1_048_576),
        (7, "node_currency", _stable_node_currency_row, 1_048_576),
        (8, "hyperedge_f64", _stable_hyperedge_f64_row, 1_048_576),
    ]
    output = bytearray(b"babylon.stable-graph\0" + _u32(1, "stable graph layout"))
    output.extend(b"\x01" + _str32(data["scenario"]))
    fact_units = 0
    for tag, name, builder, maximum in sections:
        rows = _counted_rows(data[name], maximum=maximum, field=name)
        fact_units += len(rows)
        if name == "hyperedges":
            fact_units += sum(len(row["members"]) for row in rows[:maximum])
        if fact_units > MAX_SECTION_ROWS:
            raise ContractRefusal("aggregate_row_limit", "stable graph")
        encoded = sorted((builder(row) for row in rows[:maximum]), key=lambda item: item[0])
        keys = [item[0] for item in encoded]
        if len(keys) != len(set(keys)):
            raise ContractRefusal("duplicate_fact", name)
        output.extend(bytes([tag]) + _u32(len(rows), f"{name} count"))
        for _, body in encoded[:maximum]:
            output.extend(body)
    return _bounded_bytes(output, maximum=67_108_864, field="stable graph")


def _stable_node_row(row: dict[str, Any]) -> tuple[tuple[bytes, ...], bytes]:
    key = (_symbol(row["local_name"]),)
    _structural_type(row["node_type"])
    return key, _str32(row["local_name"]) + _str32(row["node_type"])


def _stable_node_f64_row(row: dict[str, Any]) -> tuple[tuple[bytes, ...], bytes]:
    key = (_symbol(row["local_name"]), _qname(row["qname"]))
    return key, _str32(row["local_name"]) + _str32(row["qname"]) + _canonical_f64_bits(
        row["value_bits_hex"]
    )


def _stable_edge_row(row: dict[str, Any]) -> tuple[tuple[bytes, ...], bytes]:
    _structural_type(row["edge_type"])
    _symbol(row["source"])
    _symbol(row["target"])
    key = tuple(_ascii(row[name]) for name in ("edge_type", "source", "target"))
    body = b"".join(_str32(row[name]) for name in ("edge_type", "source", "target"))
    return key, body + _canonical_f64_bits(row["strength_bits_hex"])


def _stable_hyperedge_row(row: dict[str, Any]) -> tuple[tuple[bytes, ...], bytes]:
    raw_members = row["members"]
    if not isinstance(raw_members, list) or not raw_members or len(raw_members) > 65_536:
        raise ContractRefusal("hyperedge_members", row["local_name"])
    _symbol(row["local_name"])
    _structural_type(row["hyperedge_type"])
    members = sorted((_symbol(value), value) for value in raw_members[:65_536])
    if len(members) != len({item[0] for item in members}):
        raise ContractRefusal("hyperedge_members", row["local_name"])
    body = bytearray(_str32(row["local_name"]) + _str32(row["hyperedge_type"]))
    body.extend(_u32(len(members), "stable hyperedge member count"))
    for _, member in members[:65_536]:
        body.extend(_str32(member))
    return (_ascii(row["local_name"]),), bytes(body)


def _stable_edge_f64_row(row: dict[str, Any]) -> tuple[tuple[bytes, ...], bytes]:
    names = ("edge_type", "source", "target", "qname")
    _structural_type(row["edge_type"])
    _symbol(row["source"])
    _symbol(row["target"])
    _qname(row["qname"])
    key = tuple(_ascii(row[name]) for name in names)
    body = b"".join(_str32(row[name]) for name in names)
    return key, body + _canonical_f64_bits(row["value_bits_hex"])


def _stable_node_currency_row(row: dict[str, Any]) -> tuple[tuple[bytes, ...], bytes]:
    key = (_symbol(row["local_name"]), _qname(row["qname"]))
    body = _str32(row["local_name"]) + _str32(row["qname"])
    return key, body + _i128_text(row["micro_units"], "Currency micro-units")


def _stable_hyperedge_f64_row(row: dict[str, Any]) -> tuple[tuple[bytes, ...], bytes]:
    key = (_symbol(row["local_name"]), _qname(row["qname"]))
    body = _str32(row["local_name"]) + _str32(row["qname"])
    return key, body + _canonical_f64_bits(row["value_bits_hex"])


def _action_id(data: dict[str, Any]) -> bytes:
    intent_bytes = _hex_bytes(data["intent_bytes_hex"])
    if len(intent_bytes) > COMPILED_BOUNDS["practice_intent_bytes"]:
        raise ContractRefusal("intent_length", data.get("session", "action"))
    intent_digest = hashlib.sha256(intent_bytes).digest()
    if intent_digest.hex() != data["intent_digest_hex"]:
        raise ContractRefusal("intent_digest", data.get("session", "action"))
    return b"".join(
        (
            b"babylon.practice-action-id.v1\0",
            (1).to_bytes(2, "big"),
            _str16(data["session"]),
            (2).to_bytes(2, "big"),
            intent_digest,
        )
    )


def _ordered_action_batch(data: dict[str, Any]) -> bytes:
    items = _counted_rows(data["items"], maximum=4_096, field="ordered action items")
    output = bytearray(b"babylon.ordered-practice-action-batch.v1\0")
    output.extend(_u16(1, "ordered action schema") + _str16(data["session"]))
    output.extend(_u64(data["resolve_tick"], "ordered action resolve tick"))
    output.extend(_u16(len(items), "ordered action count"))
    action_ids: list[str] = []
    for index, item in enumerate(items[:4_096]):
        if item["ordinal"] != index:
            raise ContractRefusal("action_ordinal", str(index))
        intent_bytes = _hex_bytes(item["intent_bytes_hex"])
        if len(intent_bytes) > 16_384:
            raise ContractRefusal("intent_length", str(index))
        intent_digest = hashlib.sha256(intent_bytes).hexdigest()
        action_preimage = _action_id(
            {
                "session": data["session"],
                "intent_bytes_hex": item["intent_bytes_hex"],
                "intent_digest_hex": intent_digest,
            }
        )
        action_id = hashlib.sha256(action_preimage).digest()
        action_ids.append(action_id.hex())
        output.extend(_u16(index, "canonical action ordinal"))
        output.extend(action_id + _u16(len(intent_bytes), "ordered intent length") + intent_bytes)
    if data.get("action_ids_hex", action_ids) != action_ids:
        raise ContractRefusal("action_id", "ordered batch")
    return _bounded_bytes(output, maximum=67_256_631, field="ordered action batch")


def _bsl_type(data: dict[str, Any]) -> bytes:
    tags = {
        "probability": 1,
        "intensity": 2,
        "coefficient": 3,
        "currency": 4,
        "real": 5,
        "int": 6,
        "bool": 7,
        "enum": 8,
        "node_set": 9,
        "edge_set": 10,
    }
    kind = data["kind"]
    if kind not in tags:
        raise ContractRefusal("unknown_bsl_type", str(kind))
    output = bytearray([tags[kind]])
    if kind in {"enum", "node_set", "edge_set"}:
        if kind == "enum":
            _enum_type(data["name"])
        else:
            _enum_member(data["name"])
        output.extend(_str32(data["name"]))
    return bytes(output)


def _bsl_value(data: dict[str, Any]) -> bytes:
    kind = data["kind"]
    if kind == "int":
        return b"\x01" + _i64(data["value"], "ValueV1 int")
    if kind == "currency":
        return b"\x02" + _i128_text(data["micro_units"], "ValueV1 Currency")
    if kind == "real":
        return b"\x03" + _canonical_f64_bits(data["value_bits_hex"])
    if kind == "ratio":
        return (
            b"\x04"
            + _canonical_f64_bits(data["value_bits_hex"])
            + _ratio_option(data.get("floor_bits_hex"))
            + _ratio_option(data.get("cap_bits_hex"))
        )
    if kind == "bool":
        value = data["value"]
        if not isinstance(value, bool):
            raise ContractRefusal("noncanonical_boolean", str(value))
        return b"\x05" + bytes([int(value)])
    if kind == "enum":
        _enum_type(data["enum_type"])
        _enum_member(data["member"])
        return b"\x06" + _str32(data["enum_type"]) + _str32(data["member"])
    stable_kinds = {
        "node_ref": (7, "node"),
        "hyperedge_ref": (8, "hyperedge"),
        "edge_ref": (9, "edge"),
    }
    if kind in stable_kinds:
        tag, element_kind = stable_kinds[kind]
        element = dict(data["element"])
        element["element_kind"] = element_kind
        return bytes([tag]) + _stable_element(element)
    raise ContractRefusal("unknown_value", str(kind))


def _ratio_option(value: Any) -> bytes:
    if value is None:
        return b"\x00"
    return b"\x01" + _canonical_f64_bits(value)


def _effect(data: dict[str, Any]) -> bytes:
    kind = data["kind"]
    field_tags = {"node_field": 1, "edge_field": 2, "hyperedge_field": 3}
    if kind in field_tags:
        _qname(data["qname"])
        return bytes([field_tags[kind]]) + _str32(data["qname"])
    if kind == "event":
        _structural_type(data["event"])
        return b"\x04" + _str32(data["event"])
    if kind == "shape":
        shape_tags = {
            "add_node": 1,
            "remove_node": 2,
            "add_edge": 3,
            "remove_edge": 4,
            "add_hyperedge": 5,
            "remove_hyperedge": 6,
        }
        if data["verb"] not in shape_tags:
            raise ContractRefusal("unknown_shape", data["verb"])
        return b"\x05" + bytes([shape_tags[data["verb"]]])
    raise ContractRefusal("unknown_effect", str(kind))


def _closed_tag(value: str, choices: tuple[str, ...], field: str) -> bytes:
    try:
        return bytes([choices.index(value) + 1])
    except ValueError as error:
        raise ContractRefusal(f"unknown_{field}", value) from error


def _vocabulary(data: dict[str, Any]) -> bytes:
    if not data["present"]:
        return b"\x00"
    kinds = data["kinds"]
    output = bytearray(b"\x01")
    for tag, name in enumerate(("node_type", "edge_type", "hyperedge_type", "event_type"), 1):
        row = kinds[name]
        output.extend(bytes([tag, int(row["present"])]))
        if row["present"]:
            members = sorted(row["members"], key=_ascii)
            output.extend(_u32(len(members), "vocabulary member count"))
            for member in members[:MAX_SECTION_ROWS]:
                _enum_member(member)
                output.extend(_str32(member))
    return bytes(output)


def _prepared_environment(data: dict[str, Any], digests: dict[str, bytes]) -> bytes:
    _validate_prepared_counts(data)
    output = bytearray(b"babylon.prepared-environment\0" + _u32(1, "prepared layout"))
    output.extend(b"\x01" + _hex_bytes(data["rules_hash_hex"], exact=32))
    output.extend(b"\x02" + _u32(data["phase_schedule_layout"], "phase schedule layout"))
    output.extend(_hex_bytes(data["phase_schedule_digest_hex"], exact=32))
    rules = data["rule_order"]
    output.extend(b"\x03" + _u32(len(rules), "prepared rule count"))
    for rule in rules[:65_536]:
        _qname(rule)
        output.extend(_str32(rule))
    output.extend(b"\x04" + _prepared_fields(data))
    output.extend(b"\x05" + _prepared_intrinsics(data))
    output.extend(b"\x06" + _prepared_constants(data))
    output.extend(b"\x07" + _prepared_enums(data))
    output.extend(b"\x08" + _vocabulary(data["vocabulary"]))
    output.extend(b"\x09" + _u32(1, "resolver manifest layout"))
    output.extend(digests[data["resolver_manifest_id"]])
    output.extend(b"\x0a" + _u32(1, "register manifest layout"))
    output.extend(digests[data["register_manifest_id"]])
    return _bounded_bytes(output, maximum=67_108_864, field="prepared environment")


def _validate_prepared_counts(data: dict[str, Any]) -> None:
    rules = data["rule_order"]
    if not isinstance(rules, list) or len(rules) > 65_536:
        raise ContractRefusal("row_limit", "prepared rules")
    if any(not isinstance(rule, str) for rule in rules[:65_536]):
        raise ContractRefusal("row_shape", "prepared rules")
    fields = _counted_rows(data["fields"], maximum=65_536, field="prepared fields")
    exemptions = _counted_rows(data["exemptions"], maximum=64, field="prepared exemptions")
    intrinsics = _counted_rows(data["intrinsics"], maximum=64, field="prepared intrinsics")
    constants = _counted_rows(data["constants"], maximum=65_536, field="prepared constants")
    enum_types = _counted_rows(data["enum_types"], maximum=65_536, field="prepared enum types")
    total = sum(
        len(rows) for rows in (rules, fields, exemptions, intrinsics, constants, enum_types)
    )
    for declaration in enum_types[:65_536]:
        members = declaration["members"]
        if not isinstance(members, list) or len(members) > MAX_SECTION_ROWS:
            raise ContractRefusal("row_limit", "prepared enum members")
        total += len(members)
    vocabulary_data = data["vocabulary"]
    if vocabulary_data["present"]:
        total += 4
        for name in ("node_type", "edge_type", "hyperedge_type", "event_type"):
            members = vocabulary_data["kinds"][name]["members"]
            if len(members) > MAX_SECTION_ROWS:
                raise ContractRefusal("row_limit", "vocabulary members")
            total += len(members)
    if total > MAX_SECTION_ROWS:
        raise ContractRefusal("aggregate_row_limit", "prepared environment")


def _prepared_fields(data: dict[str, Any]) -> bytes:
    fields = sorted(data["fields"], key=lambda row: _ascii(row["qname"]))
    output = bytearray(_u32(len(fields), "field count"))
    field_kinds = {"intensive": 1, "extensive": 2, "not_applicable": 3}
    for row in fields[:65_536]:
        _qname(row["qname"])
        output.extend(_str32(row["qname"]) + _bsl_type(row["type"]))
        output.extend(bytes([field_kinds[row["field_kind"]]]))
    exemptions = sorted(
        data["exemptions"],
        key=lambda row: tuple(_ascii(row[name]) for name in ("field", "reason", "owner", "date")),
    )
    output.extend(_u32(len(exemptions), "exemption count"))
    for row in exemptions[:64]:
        _qname(row["field"])
        output.extend(_str32(row["field"]))
        for name in ("reason", "owner", "date"):
            output.extend(_governance_str32(row[name]))
    return bytes(output)


def _prepared_intrinsics(data: dict[str, Any]) -> bytes:
    rows = sorted(data["intrinsics"], key=lambda row: _ascii(row["name"]))
    output = bytearray(_u32(len(rows), "intrinsic count"))
    for row in rows[:64]:
        _symbol(row["name"])
        output.extend(_str32(row["name"]) + _u64(row["cost"], "intrinsic cost"))
    return bytes(output)


def _prepared_constants(data: dict[str, Any]) -> bytes:
    rows = sorted(data["constants"], key=lambda row: _ascii(row["qname"]))
    output = bytearray(_u32(len(rows), "constant count"))
    for row in rows[:65_536]:
        _qname(row["qname"])
        output.extend(_str32(row["qname"]) + _bsl_value(row["value"]))
    return bytes(output)


def _prepared_enums(data: dict[str, Any]) -> bytes:
    rows = sorted(data["enum_types"], key=lambda row: _ascii(row["name"]))
    output = bytearray(_u32(len(rows), "enum type count"))
    for row in rows[:65_536]:
        _enum_type(row["name"])
        output.extend(_str32(row["name"]) + _u32(len(row["members"]), "enum member count"))
        for member in row["members"][:MAX_SECTION_ROWS]:
            _enum_member(member)
            output.extend(_str32(member))
    return bytes(output)


def _register_manifest(data: dict[str, Any]) -> bytes:
    entries = data["entries"]
    output = bytearray(b"babylon.world-register-manifest\0" + _u32(1, "manifest layout"))
    output.extend(_u32(len(entries), "register manifest count"))
    for row in entries[:MAX_SECTION_ROWS]:
        output.extend(_str32(row["name"]) + _u32(row["layout"], "register layout"))
    return bytes(output)


def _register_set(data: dict[str, Any], digests: dict[str, bytes]) -> bytes:
    entries = data["entries"]
    output = bytearray(b"babylon.world-register-set\0" + _u32(1, "register set layout"))
    output.extend(b"\x01" + _u32(1, "manifest layout"))
    output.extend(digests[data["register_manifest_id"]])
    output.extend(b"\x02" + _u32(len(entries), "register set count"))
    for row in entries[:MAX_SECTION_ROWS]:
        payload = _i64(row["completed_tick"], "completed tick")
        if row["completed_tick"] < 0:
            raise ContractRefusal("negative_completed_tick", str(row["completed_tick"]))
        output.extend(_str32(row["name"]) + _u32(row["layout"], "register layout"))
        output.extend(_u32(len(payload), "register payload length") + payload)
    return bytes(output)


def _stable_world(data: dict[str, Any], digests: dict[str, bytes]) -> bytes:
    return b"".join(
        (
            b"babylon.stable-world\0",
            _u32(1, "stable world layout"),
            b"\x01",
            _u32(1, "stable graph layout"),
            digests[data["stable_graph_id"]],
            b"\x02",
            _u32(1, "register set layout"),
            digests[data["register_set_id"]],
        )
    )


def _tick_payload(data: dict[str, Any]) -> bytes:
    _validate_payload_counts(data)
    output = bytearray(b"babylon.tick-payload\0" + _u32(1, "tick payload layout"))
    outcomes = data["rule_outcomes"]
    output.extend(b"\x01" + _u32(len(outcomes), "rule outcome count"))
    for row in outcomes[:65_536]:
        _qname(row["rule"])
        output.extend(_str32(row["rule"]) + _u64(row["fired"], "fired count"))
    events = data["events"]
    output.extend(b"\x02" + _u32(len(events), "event count"))
    for row in events[:MAX_SECTION_ROWS]:
        _structural_type(row["event"])
        output.extend(_str32(row["event"]) + _u32(len(row["payload"]), "event payload count"))
        for item in row["payload"][:MAX_SECTION_ROWS]:
            _symbol(item["label"])
            output.extend(_str32(item["label"]) + _bsl_value(item["value"]))
    receipts = data["receipts"]
    output.extend(b"\x03" + _u32(len(receipts), "receipt count"))
    role_tags = {"mechanic": 1, "recognizer": 2, "external_event": 3, "intent": 4}
    evidence_tags = {"observed": 1, "derived": 2, "calibrated": 3, "designed": 4}
    for row in receipts[:MAX_SECTION_ROWS]:
        _qname(row["rule"])
        output.extend(_str32(row["rule"]))
        output.extend(bytes([role_tags[row["role"]], evidence_tags[row["evidence"]]]))
        output.extend(_u32(row["ordinal"], "receipt ordinal") + _effect(row["effect"]))
    output.extend(b"\x04" + _u16(data["accepted_action_outcome_count"], "action outcomes"))
    if data["accepted_action_outcome_count"] != 0:
        raise ContractRefusal("nonempty_action_outcomes", "Gate 3")
    return _bounded_bytes(output, maximum=67_108_864, field="tick payload")


def _validate_payload_counts(data: dict[str, Any]) -> None:
    outcomes = _counted_rows(data["rule_outcomes"], maximum=65_536, field="rule outcomes")
    events = _counted_rows(data["events"], maximum=MAX_SECTION_ROWS, field="events")
    receipts = _counted_rows(data["receipts"], maximum=MAX_SECTION_ROWS, field="receipts")
    total = len(outcomes) + len(events) + len(receipts)
    for event in events[:MAX_SECTION_ROWS]:
        payload = _counted_rows(
            event["payload"], maximum=MAX_SECTION_ROWS, field="event payload items"
        )
        total += len(payload)
    if total > MAX_SECTION_ROWS:
        raise ContractRefusal("aggregate_row_limit", "tick payload")


def _validate_outer_action_link(
    data: dict[str, Any], rows_by_id: dict[str, dict[str, Any]]
) -> None:
    action_id = data.get("actions_id")
    if not isinstance(action_id, str):
        raise ContractRefusal("runtime_actions_link", "missing action row")
    action_row = rows_by_id[action_id]
    if action_row.get("kind") != "ordered_action_batch":
        raise ContractRefusal("runtime_actions_link", action_id)
    action_data = action_row["data"]
    items = action_data.get("items")
    if not isinstance(items, list) or items:
        raise ContractRefusal("nonempty_runtime_actions", action_id)
    if action_data.get("session") != data.get("session"):
        raise ContractRefusal("action_session_mismatch", action_id)
    if action_data.get("resolve_tick") != data.get("resolve_tick"):
        raise ContractRefusal("action_tick_mismatch", action_id)


def _tick_content(
    data: dict[str, Any],
    digests: dict[str, bytes],
    rows_by_id: dict[str, dict[str, Any]],
) -> bytes:
    _validate_outer_action_link(data, rows_by_id)
    layouts = {
        "outer": 1,
        "session": 1,
        "seed": 1,
        "rng": 2,
        "content": 1,
        "reference": 1,
        "prepared": 1,
        "prior_world": 1,
        "actions": 1,
        "result_world": 1,
        "payload": 1,
        **data.get("layout_overrides", {}),
    }
    output = bytearray(b"babylon.tick-content\0" + _u32(layouts["outer"], "outer layout"))
    output.extend(b"\x01" + _u32(layouts["session"], "session layout") + _str16(data["session"]))
    output.extend(b"\x02" + _u64(data["resolve_tick"], "resolve tick"))
    output.extend(b"\x03" + _u32(layouts["seed"], "seed layout"))
    output.extend(_u32(layouts["rng"], "RNG layout") + _i64(data["seed"], "replay seed"))
    output.extend(b"\x04" + _u32(layouts["content"], "content layout"))
    output.extend(_hex_bytes(data["defines_digest_hex"], exact=32))
    output.extend(_hex_bytes(data["rules_digest_hex"], exact=32))
    names = ("reference", "prepared", "prior_world", "actions", "result_world", "payload")
    for tag, name in enumerate(names, start=5):
        output.extend(bytes([tag]) + _u32(layouts[name], f"{name} layout"))
        linked = data.get(f"{name}_id")
        digest = digests[linked] if linked else _hex_bytes(data[f"{name}_digest_hex"], exact=32)
        output.extend(digest)
    return bytes(output)


def _canonical_for(
    row: dict[str, Any],
    digests: dict[str, bytes],
    rows_by_id: dict[str, dict[str, Any]],
) -> bytes | None:
    kind = row["kind"]
    data = row["data"]
    builders = {
        "replay_session": lambda: _str16(data["session"]),
        "replay_seed": lambda: int(data["seed"]).to_bytes(8, "big", signed=True),
        "stable_element": lambda: _stable_element(data),
        "carrier_segment": lambda: _carrier_segment(data),
        "stable_carrier_key": lambda: _stable_carrier_key(data, rows_by_id),
        "action_id": lambda: _action_id(data),
        "resolver_manifest": lambda: _resolver_manifest(data),
        "stable_graph": lambda: _stable_graph(data),
        "ordered_action_batch": lambda: _ordered_action_batch(data),
        "prepared_environment": lambda: _prepared_environment(data, digests),
        "register_manifest": lambda: _register_manifest(data),
        "register_set": lambda: _register_set(data, digests),
        "stable_world": lambda: _stable_world(data, digests),
        "tick_payload": lambda: _tick_payload(data),
        "tick_content_hash": lambda: _tick_content(data, digests, rows_by_id),
    }
    if kind == "bsl_discriminant" and "governance_utf8" in data:
        return _governance_str32(data["governance_utf8"])
    if kind == "bsl_discriminant" and "vocabulary" in data:
        return _vocabulary(data["vocabulary"])
    if kind == "bsl_discriminant" and "bsl_type" in data:
        return _bsl_type(data["bsl_type"])
    if kind == "bsl_discriminant" and "bsl_value" in data:
        return _bsl_value(data["bsl_value"])
    if kind == "bsl_discriminant" and "effect" in data:
        return _effect(data["effect"])
    if kind == "bsl_discriminant" and "shape_verb" in data:
        return _closed_tag(
            data["shape_verb"],
            (
                "add_node",
                "remove_node",
                "add_edge",
                "remove_edge",
                "add_hyperedge",
                "remove_hyperedge",
            ),
            "shape",
        )
    if kind == "bsl_discriminant" and "field_kind" in data:
        return _closed_tag(
            data["field_kind"], ("intensive", "extensive", "not_applicable"), "field_kind"
        )
    if kind == "bsl_discriminant" and "rule_role" in data:
        return _closed_tag(
            data["rule_role"],
            ("mechanic", "recognizer", "external_event", "intent"),
            "rule_role",
        )
    if kind == "bsl_discriminant" and "evidence_class" in data:
        return _closed_tag(
            data["evidence_class"],
            ("observed", "derived", "calibrated", "designed"),
            "evidence_class",
        )
    builder = builders.get(kind)
    return None if builder is None else builder()


def _verify_rng(
    data: dict[str, Any], rows_by_id: dict[str, dict[str, Any]], *, version: int
) -> None:
    preimage = _rng_v1_preimage(data) if version == 1 else _rng_v2_preimage(data, rows_by_id)
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


def _bound_maximum(contract: dict[str, Any], name: str) -> int:
    maximum = contract["bounds"][name]
    return maximum["maximum"] if isinstance(maximum, dict) else maximum


def _recipe_count(recipe: dict[str, Any], name: str) -> int:
    value = recipe.get(name, 0)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ContractRefusal("bound_recipe_shape", name)
    return value


def _recipe_counts(recipe: dict[str, Any], name: str, maximum: int) -> list[int]:
    values = recipe.get(name)
    if not isinstance(values, list) or len(values) > maximum:
        raise ContractRefusal("bound_recipe_shape", name)
    counts = [_recipe_count({name: value}, name) for value in values]
    return counts


def _framed_length(length: int) -> int:
    return len(str(length)) + 1 + length


def _measure_text_bound_recipe(name: str, recipe: dict[str, Any]) -> int | None:
    if name == "vector_rows":
        return _recipe_count(recipe, "row_count")
    if name == "vector_line_bytes":
        return _recipe_count(recipe, "line_bytes")
    if name == "replay_session_bytes":
        return _recipe_count(recipe, "session_bytes")
    if name in {"rng_domain_bytes", "qname_bytes"}:
        segments = _recipe_counts(recipe, "segment_bytes", 5)
        return sum(segments) + max(len(segments) - 1, 0)
    if name in {"rng_domain_segments", "qname_segments"}:
        return len(_recipe_counts(recipe, "segment_bytes", 5))
    scalar_fields = {
        "symbol_bytes": "symbol_bytes",
        "structural_type_bytes": "type_bytes",
        "intrinsic_identity_bytes": "identity_bytes",
        "enum_type_bytes": "type_bytes",
        "enum_member_bytes": "member_bytes",
        "governance_utf8_bytes": "utf8_bytes",
    }
    if name in scalar_fields:
        return _recipe_count(recipe, scalar_fields[name])
    return None


def _measure_graph_bound_recipe(name: str, recipe: dict[str, Any]) -> int | None:
    scalar_fields = {
        "stable_carrier_active_elements": "active_segment_count",
        "resolver_edges": "edge_rows",
        "resolver_hyperedge_members": "maximum_members_per_hyperedge",
        "stable_graph_hyperedge_members": "maximum_members_per_hyperedge",
    }
    if name in scalar_fields:
        return _recipe_count(recipe, scalar_fields[name])
    if name == "stable_carrier_bytes":
        active_count = _recipe_count(recipe, "active_segment_count")
        active_length = _recipe_count(recipe, "active_segment_bytes")
        total = _framed_length(_recipe_count(recipe, "subject_segment_bytes"))
        total += active_count * (1 + _framed_length(active_length))
        return total + 1 + _framed_length(_recipe_count(recipe, "draw_slot_bytes"))
    if name == "resolver_rows":
        return _recipe_count(recipe, "node_rows") + _recipe_count(recipe, "hyperedge_rows")
    if name == "resolver_fact_units":
        return sum(
            _recipe_count(recipe, field)
            for field in (
                "node_rows",
                "edge_rows",
                "hyperedge_rows",
                "hyperedge_member_rows",
            )
        )
    if name == "resolver_manifest_bytes":
        return sum(
            _recipe_count(recipe, field)
            for field in (
                "domain_layout_bytes",
                "scenario_section_bytes",
                "node_section_bytes",
                "hyperedge_section_bytes",
            )
        )
    graph_elements = ("node_rows", "edge_rows", "hyperedge_rows")
    graph_attributes = (
        "node_f64_rows",
        "edge_f64_rows",
        "node_currency_rows",
        "hyperedge_f64_rows",
    )
    if name == "stable_graph_elements":
        return max((_recipe_count(recipe, field) for field in graph_elements), default=0)
    if name == "stable_graph_attribute_rows":
        return max((_recipe_count(recipe, field) for field in graph_attributes), default=0)
    if name == "stable_graph_fact_units":
        return sum(
            _recipe_count(recipe, field)
            for field in (*graph_elements, *graph_attributes, "hyperedge_member_rows")
        )
    if name == "stable_graph_bytes":
        return (
            _recipe_count(recipe, "domain_layout_bytes")
            + _recipe_count(recipe, "scenario_section_bytes")
            + sum(_recipe_counts(recipe, "section_bytes", 8))
        )
    return None


def _measure_runtime_bound_recipe(name: str, recipe: dict[str, Any]) -> int | None:
    scalar_fields = {
        "ordered_action_items": "item_count",
        "practice_intent_bytes": "intent_bytes",
        "tick_rule_outcomes": "rule_outcome_rows",
    }
    if name in scalar_fields:
        return _recipe_count(recipe, scalar_fields[name])
    if name == "ordered_action_batch_bytes":
        return (
            _recipe_count(recipe, "existing_batch_bytes")
            + 36
            + _recipe_count(recipe, "next_intent_bytes")
        )
    prepared_rows = ("field_rows", "constant_rows", "enum_type_rows")
    prepared_small = ("exemption_rows", "intrinsic_rows")
    if name == "prepared_rows":
        return max((_recipe_count(recipe, field) for field in prepared_rows), default=0)
    if name == "prepared_small_rows":
        return max((_recipe_count(recipe, field) for field in prepared_small), default=0)
    if name == "identity_members":
        return _recipe_count(recipe, "enum_member_rows")
    if name == "identity_aggregate_rows":
        return sum(
            _recipe_count(recipe, field)
            for field in (*prepared_rows, *prepared_small, "enum_member_rows")
        )
    if name == "identity_section_bytes":
        return sum(_recipe_counts(recipe, "section_bytes", 5))
    if name == "tick_rows":
        return max(
            (
                _recipe_count(recipe, field)
                for field in ("event_rows", "receipt_rows", "payload_rows")
            ),
            default=0,
        )
    return None


def _measure_bound_recipe(name: str, recipe: dict[str, Any]) -> int:
    measured = _measure_text_bound_recipe(name, recipe)
    if measured is not None:
        return measured
    measured = _measure_graph_bound_recipe(name, recipe)
    if measured is not None:
        return measured
    measured = _measure_runtime_bound_recipe(name, recipe)
    if measured is not None:
        return measured
    raise ContractRefusal("unknown_bound_recipe", name)


def _execute_text_bound_recipe(name: str, recipe: dict[str, Any], actual: int) -> bool:
    if name == "replay_session_bytes":
        _str16("a" * actual)
    elif name in {"rng_domain_bytes", "rng_domain_segments"}:
        segments = _recipe_counts(recipe, "segment_bytes", 5)
        if sum(segments) + len(segments) - 1 > 128:
            raise ContractRefusal("rng_domain_length", name)
        if not 2 <= len(segments) <= 4:
            raise ContractRefusal("rng_domain_segments", name)
        _qname("/".join("a" * length for length in segments), minimum_segments=2)
    elif name == "symbol_bytes":
        _symbol("a" * actual)
    elif name in {"qname_bytes", "qname_segments"}:
        segments = _recipe_counts(recipe, "segment_bytes", 5)
        _qname("/".join("a" * length for length in segments))
    elif name == "structural_type_bytes":
        _structural_type("A" * actual)
    elif name == "intrinsic_identity_bytes":
        _intrinsic_identity("a" * actual)
    elif name == "enum_type_bytes":
        _enum_type("A" + "a" * (actual - 1))
    elif name == "enum_member_bytes":
        _enum_member("A" * actual)
    elif name == "governance_utf8_bytes":
        _governance("a" * actual)
    else:
        return False
    return True


def _execute_graph_bound_recipe(name: str, recipe: dict[str, Any], maximum: int) -> bool:
    if name.startswith("resolver_") and name != "resolver_manifest_bytes":
        rows = _measure_bound_recipe("resolver_rows", recipe)
        edges = _measure_bound_recipe("resolver_edges", recipe)
        members = _measure_bound_recipe("resolver_hyperedge_members", recipe)
        facts = _measure_bound_recipe("resolver_fact_units", recipe)
        if rows > COMPILED_BOUNDS["resolver_rows"]:
            raise ContractRefusal("row_limit", name)
        if edges > COMPILED_BOUNDS["resolver_edges"]:
            raise ContractRefusal("edge_limit", name)
        if members > COMPILED_BOUNDS["resolver_hyperedge_members"]:
            raise ContractRefusal("hyperedge_members", name)
        if facts > COMPILED_BOUNDS["resolver_fact_units"]:
            raise ContractRefusal("aggregate_row_limit", name)
    elif name.startswith("stable_graph_"):
        elements = _measure_bound_recipe("stable_graph_elements", recipe)
        attributes = _measure_bound_recipe("stable_graph_attribute_rows", recipe)
        members = _measure_bound_recipe("stable_graph_hyperedge_members", recipe)
        facts = _measure_bound_recipe("stable_graph_fact_units", recipe)
        if elements > COMPILED_BOUNDS["stable_graph_elements"]:
            raise ContractRefusal("row_limit", name)
        if attributes > COMPILED_BOUNDS["stable_graph_attribute_rows"]:
            raise ContractRefusal("row_limit", name)
        if members > COMPILED_BOUNDS["stable_graph_hyperedge_members"]:
            raise ContractRefusal("hyperedge_members", name)
        if facts > COMPILED_BOUNDS["stable_graph_fact_units"]:
            raise ContractRefusal("aggregate_row_limit", name)
        if name == "stable_graph_bytes" and _measure_bound_recipe(name, recipe) > maximum:
            raise ContractRefusal("byte_limit", name)
    else:
        return False
    return True


def _execute_runtime_bound_recipe(name: str, recipe: dict[str, Any], maximum: int) -> bool:
    if name in {"ordered_action_items", "practice_intent_bytes"}:
        if _recipe_count(recipe, "item_count") > COMPILED_BOUNDS["ordered_action_items"]:
            raise ContractRefusal("row_limit", name)
        if _recipe_count(recipe, "intent_bytes") > COMPILED_BOUNDS["practice_intent_bytes"]:
            raise ContractRefusal("intent_length", name)
    elif name == "ordered_action_batch_bytes":
        if _recipe_count(recipe, "next_intent_bytes") > COMPILED_BOUNDS["practice_intent_bytes"]:
            raise ContractRefusal("intent_length", name)
        if _measure_bound_recipe(name, recipe) > maximum:
            raise ContractRefusal("byte_limit", name)
    elif name.startswith("prepared_") or name.startswith("identity_"):
        rows = _measure_bound_recipe("prepared_rows", recipe)
        small = _measure_bound_recipe("prepared_small_rows", recipe)
        members = _measure_bound_recipe("identity_members", recipe)
        aggregate = _measure_bound_recipe("identity_aggregate_rows", recipe)
        if (
            rows > COMPILED_BOUNDS["prepared_rows"]
            or small > COMPILED_BOUNDS["prepared_small_rows"]
        ):
            raise ContractRefusal("row_limit", name)
        if members > COMPILED_BOUNDS["identity_members"]:
            raise ContractRefusal("row_limit", name)
        if aggregate > COMPILED_BOUNDS["identity_aggregate_rows"]:
            raise ContractRefusal("aggregate_row_limit", name)
        if name == "identity_section_bytes" and _measure_bound_recipe(name, recipe) > maximum:
            raise ContractRefusal("byte_limit", name)
    elif name in {"tick_rule_outcomes", "tick_rows"}:
        outcomes = _measure_bound_recipe("tick_rule_outcomes", recipe)
        rows = _measure_bound_recipe("tick_rows", recipe)
        if outcomes > COMPILED_BOUNDS["tick_rule_outcomes"] or rows > COMPILED_BOUNDS["tick_rows"]:
            raise ContractRefusal("row_limit", name)
    else:
        return False
    return True


def _execute_bound_recipe(name: str, recipe: dict[str, Any]) -> None:
    actual = _measure_bound_recipe(name, recipe)
    maximum = {
        "replay_session_bytes": 256,
        "rng_domain_bytes": 128,
        "rng_domain_segments": 4,
    }.get(name, COMPILED_BOUNDS.get(name))
    if maximum is None:
        raise ContractRefusal("unknown_bound_recipe", name)
    if _execute_text_bound_recipe(name, recipe, actual):
        return
    if _execute_graph_bound_recipe(name, recipe, maximum):
        return
    if _execute_runtime_bound_recipe(name, recipe, maximum):
        return
    if actual <= maximum:
        return
    expected_codes = {
        "vector_rows": "too_many_rows",
        "vector_line_bytes": "invalid_line_length",
        "stable_carrier_active_elements": "active_element_limit",
        "stable_carrier_bytes": "byte_limit",
        "resolver_manifest_bytes": "byte_limit",
    }
    raise ContractRefusal(expected_codes[name], name)


def _verify_bound_case(contract: dict[str, Any], row: dict[str, Any]) -> None:
    data = row["data"]
    name = data["bound"]
    declaration = contract["bound_refusals"][name]
    expected_code = declaration["expected_code"]
    if data["expected_code"] != expected_code:
        raise ContractRefusal("wrong_refusal", data["expected_code"])
    accepted = data["accepted_recipe"]
    refused = data["refused_recipe"]
    if (
        accepted.get("operation") != declaration["operation"]
        or refused.get("operation") != declaration["operation"]
    ):
        raise ContractRefusal("bound_recipe_operation", name)
    maximum = _bound_maximum(contract, name)
    if (
        _measure_bound_recipe(name, accepted) != maximum
        or _measure_bound_recipe(name, refused) != maximum + 1
    ):
        raise ContractRefusal("bound_input_value", name)
    _execute_bound_recipe(name, accepted)
    try:
        _execute_bound_recipe(name, refused)
    except ContractRefusal as error:
        if error.code != expected_code:
            raise ContractRefusal("wrong_refusal", error.code) from error
        return
    raise ContractRefusal("missing_refusal", row["id"])


def _verify_refusal(
    contract: dict[str, Any],
    row: dict[str, Any],
    rows_by_id: dict[str, dict[str, Any]],
) -> None:
    data = row["data"]
    if data["operation"] == "session":
        try:
            _str16(data["value"])
        except ContractRefusal as error:
            if error.code != data["expected_code"]:
                raise ContractRefusal("wrong_refusal", error.code) from error
            return
        raise ContractRefusal("missing_refusal", row["id"])
    if data["operation"] == "bound_case":
        _verify_bound_case(contract, row)
        return
    if data["operation"] == "outer_action_link":
        outer = copy.deepcopy(rows_by_id[data["outer_id"]]["data"])
        outer["actions_id"] = data["actions_id"]
        try:
            _validate_outer_action_link(outer, rows_by_id)
        except ContractRefusal as error:
            if error.code != data["expected_code"]:
                raise ContractRefusal("wrong_refusal", error.code) from error
            return
        raise ContractRefusal("missing_refusal", row["id"])
    if data["operation"] == "stable_carrier_provenance":
        carrier = copy.deepcopy(rows_by_id[data["carrier_id"]]["data"])
        carrier["subject_segment_id"] = data["subject_segment_id"]
        try:
            _stable_carrier_key(carrier, rows_by_id)
        except ContractRefusal as error:
            if error.code != data["expected_code"]:
                raise ContractRefusal("wrong_refusal", error.code) from error
            return
        raise ContractRefusal("missing_refusal", row["id"])
    if data["operation"] == "governance_utf8":
        try:
            _governance(data["value"])
        except ContractRefusal as error:
            if error.code != data["expected_code"]:
                raise ContractRefusal("wrong_refusal", error.code) from error
            return
        raise ContractRefusal("missing_refusal", row["id"])
    if data["operation"] == "bounds":
        raise ContractRefusal("obsolete_refusal", row["id"])
    if data["operation"] == "bsl_value":
        try:
            _bsl_value(data["value"])
        except ContractRefusal as error:
            if error.code != data["expected_code"]:
                raise ContractRefusal("wrong_refusal", error.code) from error
            return
        raise ContractRefusal("missing_refusal", row["id"])
    if data["operation"] == "option_byte":
        if data["value"] not in (0, 1) and data["expected_code"] == "invalid_option":
            return
        raise ContractRefusal("missing_refusal", row["id"])
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


def _verify_mutation(
    row: dict[str, Any], rows_by_id: dict[str, dict[str, Any]], digests: dict[str, bytes]
) -> None:
    data = row["data"]
    base = copy.deepcopy(rows_by_id[data["base_id"]])
    before = _canonical_for(base, digests, rows_by_id)
    if before is None or hashlib.sha256(before).digest() != digests[data["base_id"]]:
        raise ContractRefusal("mutation_base", data["base_id"])
    target = base["data"]
    path = data["field"].split(".")
    for part in path[:-1]:
        target = target.setdefault(part, {})
    target[path[-1]] = data["replacement"]
    if derived_actions_id := data.get("derived_actions_id"):
        base["data"]["actions_id"] = derived_actions_id
    if path[-1].endswith("_digest_hex"):
        digest_name = path[-1].removesuffix("_digest_hex")
        base["data"].pop(f"{digest_name}_id", None)
    after = _canonical_for(base, digests, rows_by_id)
    if after is None or before == after:
        raise ContractRefusal("mutation_did_not_change_identity", row["id"])
    if hashlib.sha256(after).hexdigest() != data["after_digest_hex"]:
        raise ContractRefusal("mutation_digest", row["id"])


def _verify_row(
    contract: dict[str, Any],
    row: dict[str, Any],
    rows_by_id: dict[str, dict[str, Any]],
    digests: dict[str, bytes],
) -> bytes | None:
    if set(row) != {"id", "kind", "data"} or not isinstance(row["data"], dict):
        raise ContractRefusal("row_fields", str(row.get("id")))
    kind = row["kind"]
    data = row["data"]
    if kind == "rng_v1":
        _verify_rng(data, rows_by_id, version=1)
    elif kind == "rng_v2":
        _verify_rng(data, rows_by_id, version=2)
    elif kind == "bsl_discriminant":
        if "tables" in data and data["tables"] != contract["bsl_discriminants"]:
            raise ContractRefusal("bsl_discriminants", row["id"])
    elif kind == "mutation":
        _verify_mutation(row, rows_by_id, digests)
        return None
    elif kind == "refusal":
        _verify_refusal(contract, row, rows_by_id)
        return None
    canonical = _canonical_for(row, digests, rows_by_id)
    expected_hex = data.get("canonical_hex")
    if canonical is not None and canonical.hex() != expected_hex:
        raise ContractRefusal("canonical_bytes", row["id"])
    if canonical is not None:
        digest = hashlib.sha256(canonical).digest()
        if digest.hex() != data.get("digest_hex"):
            raise ContractRefusal("digest", row["id"])
        return digest
    return None


def verify_all(contract: dict[str, Any], vectors: list[dict[str, Any]]) -> list[str]:
    """Return every independent contract error in stable vector order."""
    errors: list[str] = []
    try:
        _verify_compiled_bounds(contract)
    except (ContractRefusal, KeyError, TypeError) as error:
        errors.append(f"contract bounds: {error}")
    required = set(contract["vector_families"]["required"])
    received = {row.get("kind") for row in vectors}
    if received != required:
        errors.append(
            f"vector families: missing={sorted(required - received)} extra={sorted(received - required)}"
        )
    row_ids = [row.get("id") for row in vectors]
    if len(row_ids) != len(set(row_ids)):
        errors.append("vector ids: duplicate")
    expected_bound_refusals = set(contract["bounds"])
    received_bound_refusals = {
        row.get("data", {}).get("bound")
        for row in vectors
        if row.get("kind") == "refusal" and row.get("data", {}).get("operation") == "bound_case"
    }
    if received_bound_refusals != expected_bound_refusals:
        errors.append(
            "bound refusal set: "
            f"missing={sorted(expected_bound_refusals - received_bound_refusals)} "
            f"extra={sorted(received_bound_refusals - expected_bound_refusals)}"
        )
    rows_by_id = {str(row["id"]): row for row in vectors if "id" in row}
    digests: dict[str, bytes] = {}
    for index in range(MAX_VECTOR_ROWS):
        if index >= len(vectors):
            break
        row = vectors[index]
        try:
            digest = _verify_row(contract, row, rows_by_id, digests)
            if digest is not None:
                digests[row["id"]] = digest
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
    try:
        _verify_compiled_bounds(contract)
    except (ContractRefusal, KeyError, TypeError) as error:
        print(f"contract bounds: {error}")
        return 1
    vectors = load_vectors(
        args.vectors,
        maximum_rows=COMPILED_BOUNDS["vector_rows"],
        maximum_line_bytes=COMPILED_BOUNDS["vector_line_bytes"],
    )
    errors = verify_all(contract, vectors)
    for error in errors[:256]:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
