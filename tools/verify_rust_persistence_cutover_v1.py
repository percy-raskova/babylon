#!/usr/bin/env python3
"""Independent repository verifier for the PER-281 one-way Rust cutover."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import re
import shlex
import struct
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import h3
import yaml

MAX_CONTRACT_BYTES = 65_536
MAX_VECTOR_BYTES = 262_144
MAX_VECTOR_ROWS = 256

_PYTHON_WRITE_SQL = re.compile(
    r"\b(?:INSERT\s+INTO|UPDATE\s+[A-Za-z_]|DELETE\s+FROM|CREATE\s+TABLE|"
    r"CREATE\s+SCHEMA|CREATE\s+VIEW|ALTER\s+TABLE|DROP\s+TABLE|TRUNCATE\s+|COPY\s+[^;]+\s+FROM)",
    re.IGNORECASE,
)
_PYTHON_DYNAMIC_WRITE = re.compile(
    r"(?:sql\.SQL\s*\(|executemany\s*\(|copy_from\s*\(|_apply_migrations|migration.*execute)",
    re.IGNORECASE | re.DOTALL,
)
_POSTGRES_CAPABILITY = re.compile(
    r"(?:psycopg|postgres|PostgresRuntime|BABYLON_DSN|connection_pool)", re.IGNORECASE
)
_RETAINED_SQL_PERIPHERY = {"src/babylon/persistence/pgvector_store.py"}

EXPECTED_FOUNDATION_FIELDS = [
    "stable_graph",
    "world_registers",
    "resolver_manifest",
    "prepared_environment",
    "replay_session_identity",
    "rng_seed",
    "content_digest",
    "reference_digest",
    "content_bundle",
]
EXPECTED_SEMANTIC_FAMILIES = [
    "graph",
    "state",
    "event",
    "checkpoint",
    "archive_dirty_receipt",
]
EXPECTED_SEMANTIC_FAMILY_TAGS = [16, 17, 18, 22, 23]
EXPECTED_PROHIBITED_RELATIONS = [
    "babylon_state.tick_graph_row",
    "babylon_state.tick_state_row",
    "babylon_state.tick_event_row",
    "babylon_state.tick_subsystem_row",
    "babylon_state.tick_conservation_row",
    "babylon_state.tick_boundary_flow_row",
    "babylon_state.tick_checkpoint_row",
    "babylon_state.tick_archive_dirty_receipt_row",
]
EXPECTED_READER_BOUNDARY = {
    "contract": "contracts/h3_reader_cutover_v1.yaml",
    "sha256": "2a842bc91dad91024b0079ff2df071079867cfe828ff3f2d868fc74e5b8d40fc",
    "edges": 0,
    "source_files": 0,
    "runtime_consumer_edges": 0,
    "bootstrap_predecessors": 0,
    "views": 0,
    "epoch7_edges": 13,
    "epoch7_source_files": 5,
    "epoch7_views": 10,
}
EXPECTED_BOUNDS = {
    "contract_bytes": MAX_CONTRACT_BYTES,
    "vector_bytes": MAX_VECTOR_BYTES,
    "vector_rows": 128,
    "vector_line_bytes": 65_536,
    "identifier_bytes": 256,
    "utf8_bytes": 65_535,
    "family_rows": 1_048_576,
    "aggregate_rows": 1_048_576,
}
EXPECTED_VECTOR_METADATA = {
    "path": "contracts/rust_persistence_cutover_v1_vectors.jsonl",
    "sha256": "eb7e50f887e39a30d48e085b2d9b001bb3abd823089d7bd6df7c7a066e68ff94",
    "rows": 56,
    "required_kinds": [
        "valid_scalar",
        "valid_row",
        "valid_foundation",
        "valid_checkpoint",
        "valid_empty_family",
        "valid_authority_ledger",
        "refusal",
    ],
    "row_executor": "verify_rust_persistence_cutover_vector_row_v1",
    "row_execution_independent_of_corpus_digest": True,
    "required_refusal_operations": [
        "encode_scalar",
        "encode_row",
        "compose_family",
        "decode_row",
        "prepare_committed_tick",
        "select_restart_root",
        "resolve_foundation",
    ],
    "required_refusal_codes": [
        "nonfinite_f64",
        "invalid_h3_cell_id",
        "unknown_closed_tag",
        "runtime_graph_handle",
        "noncanonical_field_order",
        "duplicate_row_key",
        "unknown_producer_tag",
        "synthetic_tick_zero",
        "resolve_tick_sql_range",
        "missing_empty_proof",
        "foreign_empty_proof",
        "incomplete_full_checkpoint",
        "delta_checkpoint_not_restart_root",
        "missing_foundation_artifact",
        "foundation_artifact_digest_mismatch",
        "field_byte_bound",
        "opaque_semantic_payload",
    ],
    "valid_row_count": 14,
    "valid_authority_ledger_count": 2,
    "required_valid_authority_ledger_states": ["prepared", "rust_active"],
    "composite_valid_row_layout": "exact_key_bytes_then_exact_payload_bytes",
    "required_valid_row_codecs": [
        "stable_graph_node_v1",
        "stable_graph_node_f64_v1",
        "stable_graph_edge_v1",
        "stable_graph_hyperedge_v1",
        "stable_graph_edge_f64_v1",
        "stable_graph_node_currency_v1",
        "stable_graph_hyperedge_f64_v1",
        "world_register_v1",
        "territory_state_v1",
        "dynamic_hex_state_v1",
        "organization_state_v1",
        "successful_event_v1",
        "checkpoint_v1",
        "archive_dirty_receipt_v1",
    ],
}
EXPECTED_AUTHORITY_LEDGER_WIRE = {
    "domain_utf8": "babylon.persistence-authority-ledger-row.v1\0",
    "layout_u32": 1,
    "closed_state_tags": {"prepared": 1, "rust_active": 2},
    "fields": [
        "ordinal_u16_be",
        "state_tag_u8",
        "schema_epoch_u16_be",
        "contract_sha256",
        "reader_contract_sha256",
        "predecessor_optional_digest32",
    ],
    "optional_digest32": {"none_tag_u8": 0, "some_tag_u8": 1},
    "row_sha256": "sha256_exact_canonical_bytes",
    "predecessor_law": ("rust_active predecessor_sha256 equals the exact prepared-row SHA-256"),
    "vector_ids": ["authority-ledger-prepared", "authority-ledger-rust-active"],
}
EXPECTED_STABLE_BSL_REFERENCES = {
    "bsl-stable-node": {
        "tag": "stable_node_key",
        "scenario": "demo/cross-allocation",
        "local_name": "workers",
    },
    "bsl-stable-hyperedge": {
        "tag": "stable_hyperedge_key",
        "scenario": "demo/cross-allocation",
        "local_name": "coalition-one",
    },
    "bsl-stable-edge": {
        "tag": "stable_edge_key",
        "scenario": "demo/cross-allocation",
        "edge_type": "OWNS",
        "source_local_name": "capital",
        "target_local_name": "workers",
    },
}
EXPECTED_SECTION_SHA256 = {
    "meta": "194fba79efc6f2fe0e2e17a9baf6acf13372b2c221f7aff2d9e650d31030f8c6",
    "bounds": "7ca4e16686d5f4d01a2b3aaac65948cb051a12800f3334fe063338b066792835",
    "authority": "fc0b24b29dad9e7732f3cc1a0afb7323de07b0bdd40da796a6560845d2f0a380",
    "schema_epochs": "fe4748e79868675cf4a0252e518da3e17c81f4d02b1b78c81b7c943fdd901a31",
    "foundation": "3f1b07af04df6ef6483c0a96774e8fbf52abd3188e7aadb484715950f782a2c1",
    "semantic_rows": "7107bad64d527c7d4cdbaecdb7a1b72cb8db9b09abc44b20f04d49a5c0b44cbd",
    "storage": "e16be924d06d4d8c0aad2a4f40b85f9ddb44e6f85254bbd0196f8ca040b78611",
    "reader_boundary": "e7df049ff4501f9da0f63a3e0adcd8b6af123950986cae476bdd3e4360832440",
    "data_disposition": "4916c0d2df1931f1478572fc70a4d088700b40137592652a4fd46f04511b158e",
    "python_authority": "ef5508bdc8d2bb00a6ef24516aa00aa3a347e59378527ebd5e43d75ff4d80d36",
    "vectors": "b3c1354b86093e89f8ef24e1139a1487f0573e1a95d59a92d0f56779a149e234",
    "proofs": "1a8ea6c6ccffdd089c6826cffde62148d105f07646187f897582d91e0af494d1",
    "non_goals": "8970b365f3ada9007519e3774238dacdebd1cf18ba415d597e97e9f93685291e",
}
EXPECTED_PROOFS = [
    "source-level single constructor and single production root census",
    "Python DDL and DML absence or typed refusal",
    "fresh Rust-only bootstrap",
    "adopted estate migration with exact counts and ordered hashes",
    "rollback before activation",
    "crash after activation COMMIT before caller acknowledgement",
    "failed or unresolved commit leaves the caller sink and runtime completed-tick state unchanged",
    "exact authority reacquisition after durable activation",
    "first real tick committed at tick 1 with no synthetic tick-zero marker",
    "restart from foundation or full checkpoint and contiguous verified replay",
    "next tick committed exactly once",
    "Michigan production-path proof on PostgreSQL 17",
    "repository, catalog, hooks, exact-head CI, and independent review",
]


class RustPersistenceCutoverRefusal(ValueError):
    """A malformed or self-contradictory cutover contract."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class _UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that refuses duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeyLoader, node: yaml.nodes.MappingNode, deep: bool = False
) -> dict[object, object]:
    loader.flatten_mapping(node)
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as error:
            raise RustPersistenceCutoverRefusal(
                "invalid_contract", "YAML mapping keys must be hashable"
            ) from error
        if duplicate:
            raise RustPersistenceCutoverRefusal(
                "duplicate_contract_key", f"duplicate YAML key {key!r}"
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


@dataclass(frozen=True, order=True)
class CutoverFinding:
    """One stable repository fact that still violates the cutover contract."""

    code: str
    path: str
    detail: str


def _mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise RustPersistenceCutoverRefusal("invalid_contract", f"{field} must be a mapping")
    return value


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise RustPersistenceCutoverRefusal("invalid_contract", f"{field} must be nonempty text")
    return value


def _integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RustPersistenceCutoverRefusal("invalid_contract", f"{field} must be an integer")
    return value


def _rows(value: object, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise RustPersistenceCutoverRefusal("invalid_contract", f"{field} must be a list")
    return [_mapping(row, f"{field}[{index}]") for index, row in enumerate(value)]


def _list(value: object, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise RustPersistenceCutoverRefusal("invalid_contract", f"{field} must be a list")
    return value


def _expect_exact(value: object, expected: object, field: str, code: str) -> None:
    if value != expected:
        raise RustPersistenceCutoverRefusal(code, f"{field} must equal {expected!r}")


def _section_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _field_codec(value: object, field: str) -> str:
    encoded = _string(value, field)
    if ":" not in encoded:
        raise RustPersistenceCutoverRefusal("invalid_semantic_rows", f"{field} must be name:codec")
    name, codec = encoded.split(":", 1)
    _string(name, f"{field}.name")
    return _string(codec, f"{field}.codec")


def _str32(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return len(encoded).to_bytes(4, "big") + encoded


def _decimal_integer(value: object, field: str) -> int:
    if not isinstance(value, str) or re.fullmatch(r"-?(?:0|[1-9][0-9]*)", value) is None:
        raise RustPersistenceCutoverRefusal(
            "invalid_vectors", f"{field} must be one canonical decimal integer string"
        )
    return int(value)


def _integer_bytes(value: object, width: int, signed: bool, field: str) -> bytes:
    integer = _decimal_integer(value, field)
    try:
        return integer.to_bytes(width, "big", signed=signed)
    except OverflowError as error:
        raise RustPersistenceCutoverRefusal(
            "invalid_vectors", f"{field} is outside its {width * 8}-bit domain"
        ) from error


def _finite_float(value: object, field: str) -> float:
    if not isinstance(value, str):
        raise RustPersistenceCutoverRefusal(
            "invalid_vectors", f"{field} must be one canonical decimal float string"
        )
    if value == "negative_zero":
        number = -0.0
    else:
        try:
            number = float(value)
        except ValueError as error:
            raise RustPersistenceCutoverRefusal(
                "invalid_vectors", f"{field} is not a decimal float"
            ) from error
    if not math.isfinite(number):
        raise RustPersistenceCutoverRefusal("invalid_vectors", f"{field} must be finite")
    return number


def _canonical_f64_bytes(value: object, field: str) -> bytes:
    number = _finite_float(value, field)
    if number == 0.0:
        number = 0.0
    return struct.pack(">d", number)


def _canonical_positive_ratio(value: object, field: str) -> float:
    number = _finite_float(value, field)
    if number <= 0.0:
        raise RustPersistenceCutoverRefusal("invalid_vectors", f"{field} must be strictly positive")
    scaled = number * 1_000_000.0
    if not math.isfinite(scaled):
        raise RustPersistenceCutoverRefusal(
            "invalid_vectors", f"{field} is outside the ratio grid domain"
        )
    quantized = math.floor(scaled + 0.5) / 1_000_000.0
    if struct.pack(">d", quantized) != struct.pack(">d", number):
        raise RustPersistenceCutoverRefusal(
            "invalid_vectors", f"{field} is not on the canonical 1e-6 ratio grid"
        )
    return number


def _bounded_utf8_bytes(value: object, field: str) -> bytes:
    if not isinstance(value, str):
        raise RustPersistenceCutoverRefusal("invalid_vectors", f"{field} must be UTF-8 text")
    encoded = value.encode("utf-8")
    if b"\0" in encoded or len(encoded) > 65_535:
        raise RustPersistenceCutoverRefusal(
            "invalid_vectors", f"{field} violates the bounded UTF-8 domain"
        )
    return len(encoded).to_bytes(4, "big") + encoded


def _expect_input_keys(value: dict[str, Any], expected: set[str], field: str) -> None:
    if set(value) != expected:
        raise RustPersistenceCutoverRefusal(
            "invalid_vectors", f"{field} keys must equal {sorted(expected)!r}"
        )


def _validate_lower_symbol(value: object, field: str) -> str:
    text = _string(value, field)
    if len(text.encode("utf-8")) > 64 or re.fullmatch(r"[a-z][a-z0-9-]{0,63}", text) is None:
        raise RustPersistenceCutoverRefusal("invalid_vectors", f"{field} is not a lower-symbol")
    return text


def _validate_scenario_qname(value: object, field: str) -> str:
    scenario = _string(value, field)
    encoded = scenario.encode("utf-8")
    segments = scenario.split("/")
    if len(encoded) > 128 or not 1 <= len(segments) <= 4:
        raise RustPersistenceCutoverRefusal(
            "invalid_vectors", f"{field} violates the scenario qname bounds"
        )
    for index, segment in enumerate(segments):
        _validate_lower_symbol(segment, f"{field}[{index}]")
    return scenario


def _validate_ascii_graphic(value: object, field: str) -> str:
    text = _string(value, field)
    try:
        encoded = text.encode("ascii")
    except UnicodeEncodeError as error:
        raise RustPersistenceCutoverRefusal(
            "invalid_vectors", f"{field} must be ASCII graphic text"
        ) from error
    if not 1 <= len(encoded) <= 128 or not all(0x21 <= byte <= 0x7E for byte in encoded):
        raise RustPersistenceCutoverRefusal(
            "invalid_vectors", f"{field} must be 1..128 ASCII graphic bytes"
        )
    return text


def _stable_element_key_bytes(value: object, field: str) -> bytes:
    key = _mapping(value, field)
    stable = bytearray(b"babylon.stable-element\0")
    stable.extend((1).to_bytes(4, "big"))
    kind = _string(key.get("tag"), f"{field}.tag")
    scenario = _validate_scenario_qname(key.get("scenario"), f"{field}.scenario")
    if kind == "stable_node_key":
        _expect_input_keys(key, {"tag", "scenario", "local_name"}, field)
        stable.append(0x01)
        stable.extend(_str32(scenario))
        stable.extend(_str32(_validate_lower_symbol(key.get("local_name"), f"{field}.local_name")))
    elif kind == "stable_edge_key":
        _expect_input_keys(
            key,
            {
                "tag",
                "scenario",
                "edge_type",
                "source_local_name",
                "target_local_name",
            },
            field,
        )
        stable.append(0x02)
        stable.extend(_str32(scenario))
        stable.extend(_str32(_validate_ascii_graphic(key.get("edge_type"), f"{field}.edge_type")))
        stable.extend(
            _str32(
                _validate_lower_symbol(key.get("source_local_name"), f"{field}.source_local_name")
            )
        )
        stable.extend(
            _str32(
                _validate_lower_symbol(key.get("target_local_name"), f"{field}.target_local_name")
            )
        )
    elif kind == "stable_hyperedge_key":
        _expect_input_keys(key, {"tag", "scenario", "local_name"}, field)
        stable.append(0x03)
        stable.extend(_str32(scenario))
        stable.extend(_str32(_validate_lower_symbol(key.get("local_name"), f"{field}.local_name")))
    else:
        raise RustPersistenceCutoverRefusal(
            "invalid_vectors", f"{field} has unknown stable-element key tag {kind!r}"
        )
    return bytes(stable)


def _stable_bsl_reference_bytes(tag: int, value: dict[str, Any]) -> bytes:
    return bytes((tag,)) + _stable_element_key_bytes(value, "stable BSL reference")


def _ordered_named_bsl_fields_bytes(
    value: object, field: str, stable_tags: dict[str, Any]
) -> bytes:
    rows = _list(value, field)
    if len(rows) > 1_048_576:
        raise RustPersistenceCutoverRefusal(
            "invalid_vectors", f"{field} exceeds the ordered-field item bound"
        )
    encoded = bytearray(len(rows).to_bytes(4, "big"))
    previous_name: bytes | None = None
    for index, value_row in enumerate(rows):
        row = _mapping(value_row, f"{field}[{index}]")
        _expect_input_keys(row, {"name", "value"}, f"{field}[{index}]")
        name = _string(row.get("name"), f"{field}[{index}].name")
        name_bytes = name.encode("utf-8")
        if previous_name is not None and previous_name >= name_bytes:
            raise RustPersistenceCutoverRefusal(
                "invalid_vectors", f"{field} names must be strictly ascending UTF-8 bytes"
            )
        previous_name = name_bytes
        encoded.extend(_bounded_utf8_bytes(name, f"{field}[{index}].name"))
        encoded.extend(
            _stable_bsl_scalar_bytes(row.get("value"), f"{field}[{index}].value", stable_tags)
        )
    return bytes(encoded)


def _ordered_stable_element_keys_bytes(value: object, field: str) -> bytes:
    rows = _list(value, field)
    if len(rows) > 1_048_576:
        raise RustPersistenceCutoverRefusal(
            "invalid_vectors", f"{field} exceeds the stable-key item bound"
        )
    encoded = bytearray(len(rows).to_bytes(4, "big"))
    previous: bytes | None = None
    for index, value_row in enumerate(rows):
        key = _stable_element_key_bytes(value_row, f"{field}[{index}]")
        if previous is not None and previous >= key:
            raise RustPersistenceCutoverRefusal(
                "invalid_vectors",
                f"{field} keys must be strictly ascending canonical bytes",
            )
        previous = key
        encoded.extend(len(key).to_bytes(4, "big"))
        encoded.extend(key)
    return bytes(encoded)


def _stable_bsl_scalar_bytes(value: object, field: str, stable_tags: dict[str, Any]) -> bytes:
    stable = _mapping(value, field)
    tag = _string(stable.get("tag"), f"{field}.tag")
    outer_tag = _integer(stable_tags.get(tag), f"stable_bsl_value_v1.closed_tags.{tag}")
    if not 1 <= outer_tag <= 255:
        raise RustPersistenceCutoverRefusal(
            "invalid_vectors", f"{field}.tag is outside the closed u8 vocabulary"
        )
    if tag == "int_i64":
        _expect_input_keys(stable, {"tag", "value"}, field)
        return bytes((outer_tag,)) + _integer_bytes(stable.get("value"), 8, True, f"{field}.value")
    if tag == "currency_i128":
        _expect_input_keys(stable, {"tag", "micro_units"}, field)
        return bytes((outer_tag,)) + _integer_bytes(
            stable.get("micro_units"), 16, True, f"{field}.micro_units"
        )
    if tag == "real_f64_bits":
        _expect_input_keys(stable, {"tag", "value"}, field)
        return bytes((outer_tag,)) + _canonical_f64_bytes(stable.get("value"), f"{field}.value")
    if tag == "ratio_f64_bits_with_optional_bounds":
        _expect_input_keys(stable, {"tag", "value", "floor", "cap"}, field)
        ratio = _canonical_positive_ratio(stable.get("value"), f"{field}.value")
        floor_value = stable.get("floor")
        cap_value = stable.get("cap")
        floor = (
            None
            if floor_value is None
            else _canonical_positive_ratio(floor_value, f"{field}.floor")
        )
        cap = None if cap_value is None else _canonical_positive_ratio(cap_value, f"{field}.cap")
        if floor is not None and cap is not None and floor >= cap:
            raise RustPersistenceCutoverRefusal(
                "invalid_vectors", f"{field} ratio floor must be below cap"
            )
        if floor is not None and ratio <= floor:
            raise RustPersistenceCutoverRefusal(
                "invalid_vectors", f"{field} ratio must be above floor"
            )
        if cap is not None and ratio > cap:
            raise RustPersistenceCutoverRefusal(
                "invalid_vectors", f"{field} ratio must not exceed cap"
            )
        encoded = bytearray((outer_tag,))
        encoded.extend(_canonical_f64_bytes(stable.get("value"), f"{field}.value"))
        for name, bound in (("floor", floor_value), ("cap", cap_value)):
            encoded.append(0 if bound is None else 1)
            if bound is not None:
                encoded.extend(_canonical_f64_bytes(bound, f"{field}.{name}"))
        return bytes(encoded)
    if tag == "bool":
        _expect_input_keys(stable, {"tag", "value"}, field)
        boolean = stable.get("value")
        if not isinstance(boolean, bool):
            raise RustPersistenceCutoverRefusal("invalid_vectors", f"{field}.value must be boolean")
        return bytes((outer_tag, int(boolean)))
    if tag == "enum_type_and_member":
        _expect_input_keys(stable, {"tag", "enum_type", "member"}, field)
        enum_type = _string(stable.get("enum_type"), f"{field}.enum_type")
        member = _string(stable.get("member"), f"{field}.member")
        if re.fullmatch(r"[A-Z][A-Za-z0-9]{0,63}", enum_type) is None:
            raise RustPersistenceCutoverRefusal(
                "invalid_vectors", f"{field}.enum_type violates the enum type grammar"
            )
        if re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", member) is None:
            raise RustPersistenceCutoverRefusal(
                "invalid_vectors", f"{field}.member violates the enum member grammar"
            )
        return (
            bytes((outer_tag,))
            + _bounded_utf8_bytes(enum_type, f"{field}.enum_type")
            + _bounded_utf8_bytes(member, f"{field}.member")
        )
    if tag in {"stable_node_key", "stable_hyperedge_key", "stable_edge_key"}:
        return _stable_bsl_reference_bytes(outer_tag, stable)
    raise RustPersistenceCutoverRefusal(
        "invalid_vectors", f"{field} has unknown stable BSL tag {tag!r}"
    )


def _valid_scalar_bytes(
    codec: object, value: object, field: str, stable_tags: dict[str, Any]
) -> bytes:
    codec_id = _string(codec, f"{field}.codec")
    if codec_id == "bool_u8":
        if not isinstance(value, bool):
            raise RustPersistenceCutoverRefusal("invalid_vectors", f"{field}.input must be boolean")
        return bytes((int(value),))
    if codec_id == "u64_be":
        return _integer_bytes(value, 8, False, f"{field}.input")
    if codec_id == "i64_be":
        return _integer_bytes(value, 8, True, f"{field}.input")
    if codec_id == "i128_be":
        return _integer_bytes(value, 16, True, f"{field}.input")
    if codec_id == "f64_be_canonical":
        return _canonical_f64_bytes(value, f"{field}.input")
    if codec_id == "h3_cell_id_i64_be":
        integer = _decimal_integer(value, f"{field}.input")
        try:
            cell = h3.int_to_str(integer)
            valid = h3.is_valid_cell(cell)
            roundtrip = h3.str_to_int(cell)
        except (h3.H3BaseException, OverflowError, ValueError) as error:
            raise RustPersistenceCutoverRefusal(
                "invalid_vectors", f"{field}.input is not an H3 cell"
            ) from error
        if integer <= 0 or not valid or roundtrip != integer:
            raise RustPersistenceCutoverRefusal(
                "invalid_vectors", f"{field}.input is not a roundtripping H3 cell"
            )
        return _integer_bytes(value, 8, True, f"{field}.input")
    if codec_id == "optional_bounded_utf8":
        return b"\0" if value is None else b"\x01" + _bounded_utf8_bytes(value, f"{field}.input")
    if codec_id == "stable_bsl_value_v1":
        return _stable_bsl_scalar_bytes(value, f"{field}.input", stable_tags)
    raise RustPersistenceCutoverRefusal(
        "invalid_vectors", f"{field} has unknown valid scalar codec {codec_id!r}"
    )


def _material_valid_row_bytes(
    row: dict[str, Any], stable_tags: dict[str, Any]
) -> tuple[bytes, bytes] | None:
    codec = _string(row.get("codec"), "material valid-row codec")
    tags = {
        "territory_state_v1": 0x02,
        "dynamic_hex_state_v1": 0x03,
        "organization_state_v1": 0x08,
    }
    row_tag = tags.get(codec)
    if row_tag is None:
        return None
    data = _mapping(row.get("data"), f"{row.get('id')}.data")
    key = bytearray(b"babylon.committed-tick-row-key.v1\0")
    payload = bytearray(b"babylon.committed-tick-row-payload.v1\0")
    for target in (key, payload):
        target.extend((1).to_bytes(4, "big"))
        target.extend((0x11, 0x10, row_tag))

    if codec == "territory_state_v1":
        _expect_input_keys(data, {"territory_id", "ordered_fields"}, f"{row['id']}.data")
        key.extend(_stable_element_key_bytes(data.get("territory_id"), f"{row['id']}.territory_id"))
        payload.extend(
            _ordered_named_bsl_fields_bytes(
                data.get("ordered_fields"), f"{row['id']}.ordered_fields", stable_tags
            )
        )
    elif codec == "dynamic_hex_state_v1":
        lane_names = [
            "c",
            "v",
            "s",
            "k",
            "biocapacity_stock",
            "energy_stock",
            "raw_material_stock",
            "internet_access_pct",
            "surveillance_coupling",
        ]
        _expect_input_keys(data, {"cell_id", *lane_names}, f"{row['id']}.data")
        key.extend(
            _valid_scalar_bytes(
                "h3_cell_id_i64_be", data.get("cell_id"), f"{row['id']}.cell_id", stable_tags
            )
        )
        for lane in lane_names:
            payload.extend(_canonical_f64_bytes(data.get(lane), f"{row['id']}.{lane}"))
    else:
        _expect_input_keys(
            data,
            {
                "organization_id",
                "organization_kind",
                "ordered_territory_ids",
                "ordered_fields",
            },
            f"{row['id']}.data",
        )
        key.extend(
            _stable_element_key_bytes(data.get("organization_id"), f"{row['id']}.organization_id")
        )
        organization_kind = _mapping(
            data.get("organization_kind"), f"{row['id']}.organization_kind"
        )
        if (
            organization_kind.get("tag") != "enum_type_and_member"
            or organization_kind.get("enum_type") != "OrgKind"
        ):
            raise RustPersistenceCutoverRefusal(
                "invalid_vectors",
                f"{row['id']}.organization_kind must be an exact OrgKind stable enum value",
            )
        payload.extend(
            _stable_bsl_scalar_bytes(
                organization_kind, f"{row['id']}.organization_kind", stable_tags
            )
        )
        payload.extend(
            _ordered_stable_element_keys_bytes(
                data.get("ordered_territory_ids"),
                f"{row['id']}.ordered_territory_ids",
            )
        )
        payload.extend(
            _ordered_named_bsl_fields_bytes(
                data.get("ordered_fields"), f"{row['id']}.ordered_fields", stable_tags
            )
        )
    return bytes(key), bytes(payload)


def _verify_material_valid_rows(
    rows: list[dict[str, Any]],
    relative: str,
    findings: set[CutoverFinding],
    stable_tags: dict[str, Any],
) -> None:
    for row in rows:
        if row.get("kind") != "valid_row" or row.get("codec") not in {
            "territory_state_v1",
            "dynamic_hex_state_v1",
            "organization_state_v1",
        }:
            continue
        row_id = str(row.get("id"))
        try:
            recomputed = _material_valid_row_bytes(row, stable_tags)
            if recomputed is None:
                raise ValueError("material row was not independently reconstructed")
            key, payload = recomputed
            composite = key + payload
            expected = {
                "key": _string(row.get("expected_key_hex"), f"{row_id}.expected_key_hex"),
                "payload": _string(
                    row.get("expected_payload_hex"), f"{row_id}.expected_payload_hex"
                ),
                "composite": _string(row.get("expected_hex"), f"{row_id}.expected_hex"),
                "sha256": _string(row.get("expected_sha256"), f"{row_id}.expected_sha256"),
            }
            actual = {
                "key": key.hex(),
                "payload": payload.hex(),
                "composite": composite.hex(),
                "sha256": hashlib.sha256(composite).hexdigest(),
            }
            if actual != expected:
                raise ValueError("declared bytes do not match the typed material source data")
        except (
            RustPersistenceCutoverRefusal,
            UnicodeError,
            OverflowError,
            ValueError,
            struct.error,
        ) as error:
            findings.add(
                CutoverFinding("cutover_valid_row_identity", relative, f"{row_id}: {error}")
            )


def _verify_valid_scalars(
    rows: list[dict[str, Any]],
    relative: str,
    findings: set[CutoverFinding],
    stable_tags: dict[str, Any],
) -> None:
    for row in rows:
        if row.get("kind") != "valid_scalar":
            continue
        row_id = str(row.get("id"))
        try:
            expected_hex = _string(row.get("expected_hex"), f"{row_id}.expected_hex")
            recomputed = _valid_scalar_bytes(
                row.get("codec"), row.get("input"), row_id, stable_tags
            ).hex()
            if expected_hex != recomputed:
                raise RustPersistenceCutoverRefusal(
                    "invalid_vectors",
                    f"expected_hex {expected_hex!r} does not match reconstructed {recomputed!r}",
                )
        except (
            RustPersistenceCutoverRefusal,
            UnicodeError,
            OverflowError,
            ValueError,
            struct.error,
        ) as error:
            findings.add(
                CutoverFinding("cutover_valid_scalar_identity", relative, f"{row_id}: {error}")
            )


def _verify_stable_bsl_references(
    rows: list[dict[str, Any]],
    relative: str,
    findings: set[CutoverFinding],
    stable_tags: dict[str, Any],
) -> None:
    by_id = {row.get("id"): row for row in rows}
    for row_id, expected_input in EXPECTED_STABLE_BSL_REFERENCES.items():
        row = by_id.get(row_id)
        try:
            if row is None:
                raise RustPersistenceCutoverRefusal("invalid_vectors", "required row is absent")
            actual_input = _mapping(row.get("input"), f"{row_id}.input")
            if actual_input != expected_input:
                raise RustPersistenceCutoverRefusal(
                    "invalid_vectors",
                    f"input must equal the governed cross-allocation key {expected_input!r}",
                )
            expected_hex = _string(row.get("expected_hex"), f"{row_id}.expected_hex")
            kind = _string(actual_input.get("tag"), f"{row_id}.input.tag")
            tag = _integer(stable_tags.get(kind), f"stable_bsl_value_v1.closed_tags.{kind}")
            recomputed = _stable_bsl_reference_bytes(tag, actual_input).hex()
            if expected_hex != recomputed:
                raise RustPersistenceCutoverRefusal(
                    "invalid_vectors", "expected_hex is not the full stable-element key layout"
                )
        except (
            RustPersistenceCutoverRefusal,
            UnicodeError,
            OverflowError,
            ValueError,
            struct.error,
        ) as error:
            findings.add(
                CutoverFinding("cutover_stable_bsl_identity", relative, f"{row_id}: {error}")
            )


def load_cutover_contract(path: Path) -> dict[str, Any]:
    """Load one bounded YAML mapping and refuse trailing documents."""

    size = path.stat().st_size
    if size > MAX_CONTRACT_BYTES:
        raise RustPersistenceCutoverRefusal(
            "contract_too_large", f"{path} is {size} bytes; maximum is {MAX_CONTRACT_BYTES}"
        )
    documents = list(yaml.load_all(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader))
    if len(documents) != 1:
        raise RustPersistenceCutoverRefusal(
            "invalid_contract", f"{path} must contain exactly one YAML document"
        )
    contract = _mapping(documents[0], "contract")
    validate_cutover_contract(contract)
    return contract


def validate_cutover_contract(contract: dict[str, Any]) -> None:
    """Refuse contract drift that would create a second authority or fake tick zero."""

    _expect_exact(
        set(contract),
        {
            "meta",
            "bounds",
            "authority",
            "schema_epochs",
            "foundation",
            "semantic_rows",
            "storage",
            "reader_boundary",
            "data_disposition",
            "python_authority",
            "vectors",
            "proofs",
            "non_goals",
        },
        "contract keys",
        "invalid_contract_shape",
    )

    meta = _mapping(contract.get("meta"), "meta")
    expected_meta = {
        "contract": "RustPersistenceCutoverV1",
        "version": 1,
        "issue": "PER-281",
        "parent": "PER-21",
        "stopped_with": "PER-280",
    }
    if meta != expected_meta:
        raise RustPersistenceCutoverRefusal("invalid_meta", repr(meta))

    bounds = _mapping(contract.get("bounds"), "bounds")
    _expect_exact(bounds, EXPECTED_BOUNDS, "bounds", "invalid_bounds")

    authority = _mapping(contract.get("authority"), "authority")
    expected_authority = {
        "purpose": (
            "One-way replacement of Python game-managed PostgreSQL authority with one Rust runtime"
        ),
        "canonical_crate": "babylon-persistence",
        "composition_module": "rust/crates/babylon-persistence/src/runtime.rs",
        "composition_binary": "rust/crates/babylon-persistence/src/bin/babylon-runtime.rs",
        "composition_type": "DurableReplayRuntimeV1",
        "prepared_tick_type": "PreparedCommittedTickV1",
        "identified_tick_input": "babylon_tick::replay_session::IdentifiedTickReportV1",
        "prepared_tick_constructor": "prepare_committed_tick_v1",
        "activation_function": "activate_rust_persistence_v1",
        "absorbed_binary": "rust/crates/babylon-persistence/src/bin/babylon-schema-epoch.rs",
        "constructibility": {
            "activation": (
                "activate_rust_persistence_v1(&postgres::Config) -> "
                "Result<ActivationReportV1, RustPersistenceActivationErrorV1>"
            ),
            "content_bundle": (
                "FoundationContentBundleV1::try_new(&str, Option<&str>, &str, &[u8], "
                "&[u8]) -> Result<FoundationContentBundleV1, "
                "RustPersistenceRuntimeErrorV1>"
            ),
            "foundation_capture": (
                "CampaignFoundationV1::capture(&ReplayTickSession<HypergraphStore>, "
                "FoundationContentBundleV1) -> Result<CampaignFoundationV1, "
                "RustPersistenceRuntimeErrorV1>"
            ),
            "foundation_hydration": (
                "hydrate_campaign_foundation_v1(&postgres::Config, CampaignId) -> "
                "Result<CampaignFoundationV1, RustPersistenceRuntimeErrorV1>"
            ),
            "runtime_create": (
                "DurableReplayRuntimeV1<HypergraphStore>::create(&postgres::Config, "
                "CampaignId, ReplayTickSession<HypergraphStore>, "
                "FoundationContentBundleV1) -> Result<Self, "
                "RustPersistenceRuntimeErrorV1>"
            ),
            "runtime_open": (
                "DurableReplayRuntimeV1<HypergraphStore>::open(&postgres::Config, "
                "CampaignId) -> Result<Self, RustPersistenceRuntimeErrorV1>"
            ),
            "runtime_advance": (
                "DurableReplayRuntimeV1<HypergraphStore>::advance_and_commit(&mut self, "
                "&mut CollectingSink, &OrderedPracticeActionBatchV1) -> "
                "Result<CommittedTickReceiptV1, RustPersistenceRuntimeErrorV1>"
            ),
            "adjudication_sink": "private_runtime_owned_buffer",
            "caller_sink_law": (
                "The mutable caller sink is a post-acknowledgement destination only; it "
                "remains byte-identical on refusal, rollback, or unresolved commit ambiguity."
            ),
            "external_commit_from_report": "prohibited",
        },
        "prohibited_owners": ["babylon-tick", "babylon-client"],
        "prohibited_adjudication_calls": ["prepare_rules", "run_prepared_replay_tick"],
        "invariants": [
            "Tick adjudication remains database-free.",
            (
                "A completed tick is observable only after COMMIT acknowledgement or exact "
                "ambiguity reconciliation."
            ),
            (
                "A failed post-adjudication commit permits only identical retry or runtime "
                "reconstruction."
            ),
            (
                "Python game-managed DDL and writes refuse before Rust authority becomes "
                "constructible."
            ),
            (
                "No compatibility view, adapter, fallback, dual writer, dual storage, or "
                "runnable midpoint exists."
            ),
        ],
    }
    _expect_exact(authority, expected_authority, "authority", "invalid_root")

    epochs = _mapping(contract.get("schema_epochs"), "schema_epochs")
    _expect_exact(
        {
            field: epochs.get(field)
            for field in [
                "reader_epoch",
                "additive_preparation_epoch",
                "destructive_activation_epoch",
            ]
        },
        {"reader_epoch": 7, "additive_preparation_epoch": 8, "destructive_activation_epoch": 9},
        "schema_epochs",
        "invalid_schema_epochs",
    )
    if epochs.get("activation_ledger_row_commits_last") is not True:
        raise RustPersistenceCutoverRefusal(
            "invalid_schema_epochs", "activation ledger must commit last"
        )
    if epochs.get("recovery_after_activation") != "forward_only":
        raise RustPersistenceCutoverRefusal(
            "invalid_schema_epochs", "activation recovery must be forward-only"
        )
    ledger = _mapping(epochs.get("activation_ledger"), "schema_epochs.activation_ledger")
    _expect_exact(
        set(ledger),
        {
            "relation",
            "row_type",
            "state_type",
            "primary_key",
            "wire",
            "columns",
            "state_machine",
            "allowed_transitions",
            "prohibited_transitions",
            "row_last_law",
            "reacquisition_law",
        },
        "schema_epochs.activation_ledger keys",
        "invalid_schema_epochs",
    )
    _expect_exact(
        ledger.get("wire"),
        EXPECTED_AUTHORITY_LEDGER_WIRE,
        "schema_epochs.activation_ledger.wire",
        "invalid_schema_epochs",
    )
    _expect_exact(
        ledger.get("relation"),
        "babylon_meta.persistence_authority_ledger",
        "schema_epochs.activation_ledger.relation",
        "invalid_schema_epochs",
    )
    _expect_exact(
        (ledger.get("row_type"), ledger.get("state_type"), ledger.get("primary_key")),
        ("PersistenceAuthorityLedgerRowV1", "PersistenceAuthorityStateV1", ["ordinal"]),
        "schema_epochs.activation_ledger types and key",
        "invalid_schema_epochs",
    )
    _expect_exact(
        ledger.get("state_machine"),
        [
            {
                "ordinal": 1,
                "state_tag": 1,
                "state": "prepared",
                "schema_epoch": 8,
                "predecessor": "none",
            },
            {
                "ordinal": 2,
                "state_tag": 2,
                "state": "rust_active",
                "schema_epoch": 9,
                "predecessor": "exact_prepared_row_sha256",
            },
        ],
        "schema_epochs.activation_ledger.state_machine",
        "invalid_schema_epochs",
    )
    _expect_exact(
        ledger.get("row_last_law"),
        "The rust_active ledger row is the final DML statement before activation COMMIT.",
        "schema_epochs.activation_ledger.row_last_law",
        "invalid_schema_epochs",
    )
    _expect_exact(
        ledger.get("reacquisition_law"),
        (
            "A durable rust_active row permits only the Rust composition root to construct "
            "write authority."
        ),
        "schema_epochs.activation_ledger.reacquisition_law",
        "invalid_schema_epochs",
    )
    _expect_exact(
        ledger.get("allowed_transitions"),
        ["absent_to_prepared", "prepared_to_rust_active"],
        "schema_epochs.activation_ledger.allowed_transitions",
        "invalid_schema_epochs",
    )
    _expect_exact(
        ledger.get("prohibited_transitions"),
        ["skip_prepared", "update", "delete", "rollback", "python_active_after_rust_active"],
        "schema_epochs.activation_ledger.prohibited_transitions",
        "invalid_schema_epochs",
    )

    foundation = _mapping(contract.get("foundation"), "foundation")
    if foundation.get("tick_commit_starts_at") != 1:
        raise RustPersistenceCutoverRefusal(
            "synthetic_tick_zero", "tick_commit must begin at the first executed tick"
        )
    if foundation.get("tick_zero_marker") != "prohibited":
        raise RustPersistenceCutoverRefusal(
            "synthetic_tick_zero", "a no-op tick-zero TickContentHash is not governed"
        )
    _expect_exact(
        (
            foundation.get("tick_commit_maximum"),
            foundation.get("tick_number_type"),
            foundation.get("out_of_postgresql_bigint_range"),
        ),
        (9_223_372_036_854_775_807, "CommittedResolveTickV1", "refused"),
        "foundation tick bounds",
        "invalid_foundation",
    )
    _expect_exact(
        foundation.get("relation"),
        "babylon_state.campaign_foundation",
        "foundation.relation",
        "invalid_foundation",
    )
    _expect_exact(
        [
            row.get("name")
            for row in _rows(foundation.get("exact_fields"), "foundation.exact_fields")
        ],
        EXPECTED_FOUNDATION_FIELDS,
        "foundation.exact_fields names",
        "invalid_foundation",
    )
    _expect_exact(
        foundation.get("first_tick_checkpoint"),
        "required_full",
        "foundation.first_tick_checkpoint",
        "invalid_foundation",
    )
    bundle = _mapping(foundation.get("content_bundle"), "foundation.content_bundle")
    _expect_exact(
        bundle.get("type"),
        "FoundationContentBundleV1",
        "foundation.content_bundle.type",
        "invalid_foundation",
    )
    artifact = _mapping(
        bundle.get("artifact_resolution"), "foundation.content_bundle.artifact_resolution"
    )
    _expect_exact(
        artifact.get("prohibited"),
        ["ambient_path", "network_fetch", "latest_version", "digest_fallback"],
        "foundation.content_bundle.artifact_resolution.prohibited",
        "invalid_foundation",
    )
    checkpoint = _mapping(
        foundation.get("checkpoint_completeness"), "foundation.checkpoint_completeness"
    )
    _expect_exact(
        checkpoint.get("required_full_sections"),
        [
            "stable_graph",
            "world_registers",
            "resolver_manifest",
            "prepared_environment",
            "replay_session_identity",
            "rng_seed",
            "content_digest",
            "reference_digest",
            "semantic_state",
        ],
        "foundation.checkpoint_completeness.required_full_sections",
        "invalid_foundation",
    )
    if checkpoint.get("delta_is_restore_root") is not False:
        raise RustPersistenceCutoverRefusal(
            "invalid_foundation", "a delta checkpoint cannot be a restore root"
        )
    if not _list(foundation.get("restart"), "foundation.restart"):
        raise RustPersistenceCutoverRefusal(
            "invalid_foundation", "foundation.restart must be nonempty"
        )

    semantic_rows = _mapping(contract.get("semantic_rows"), "semantic_rows")
    _expect_exact(
        set(semantic_rows),
        {
            "row_wire",
            "family_order",
            "scalar_codecs",
            "row_codecs",
            "producer_inventory",
            "emptiness_law",
            "laws",
        },
        "semantic_rows keys",
        "invalid_semantic_rows",
    )
    family_rows = _rows(semantic_rows.get("family_order"), "semantic_rows.family_order")
    _expect_exact(
        family_rows,
        [
            {"family": family, "tag_u8": tag}
            for family, tag in zip(
                EXPECTED_SEMANTIC_FAMILIES,
                EXPECTED_SEMANTIC_FAMILY_TAGS,
                strict=True,
            )
        ],
        "semantic_rows.family_order",
        "invalid_semantic_rows",
    )
    _expect_exact(
        [row.get("family") for row in family_rows],
        EXPECTED_SEMANTIC_FAMILIES,
        "semantic_rows family names",
        "invalid_semantic_rows",
    )
    for field in [
        "row_wire",
        "scalar_codecs",
        "row_codecs",
        "producer_inventory",
        "emptiness_law",
    ]:
        value = semantic_rows.get(field)
        if not value:
            raise RustPersistenceCutoverRefusal(
                "invalid_semantic_rows", f"semantic_rows.{field} must be nonempty"
            )
    scalar_codecs = _mapping(semantic_rows["scalar_codecs"], "semantic_rows.scalar_codecs")
    scalar_ids = set(scalar_codecs)
    _expect_exact(
        scalar_codecs.get("i64_be"),
        {
            "bytes": 8,
            "minimum": -9_223_372_036_854_775_808,
            "maximum": 9_223_372_036_854_775_807,
            "encoding": "twos_complement",
        },
        "semantic_rows.scalar_codecs.i64_be",
        "invalid_semantic_rows",
    )
    _expect_exact(
        scalar_codecs.get("h3_cell_id_i64_be"),
        {
            "bytes": 8,
            "minimum": 1,
            "maximum": 9_223_372_036_854_775_807,
            "validation": "babylon_kernel::H3CellId::try_from(u64)",
            "invalid_mode_or_resolution": "refused",
        },
        "semantic_rows.scalar_codecs.h3_cell_id_i64_be",
        "invalid_semantic_rows",
    )
    _expect_exact(
        scalar_codecs.get("stable_element_key_v1"),
        {
            "domain_ascii_nul": "babylon.stable-element",
            "layout_u32": 1,
            "closed_kinds": {
                "stable_node_key": {
                    "key_kind_u8": 1,
                    "fields": ["scenario_qname", "local_name_lower_symbol"],
                },
                "stable_edge_key": {
                    "key_kind_u8": 2,
                    "fields": [
                        "scenario_qname",
                        "edge_type_ascii_graphic",
                        "source_local_name_lower_symbol",
                        "target_local_name_lower_symbol",
                    ],
                },
                "stable_hyperedge_key": {
                    "key_kind_u8": 3,
                    "fields": ["scenario_qname", "local_name_lower_symbol"],
                },
            },
            "canonical_bytes": "exact_StableElementKeyV1_canonical_bytes",
            "runtime_graph_handles": "prohibited",
        },
        "semantic_rows.scalar_codecs.stable_element_key_v1",
        "invalid_semantic_rows",
    )
    _expect_exact(
        scalar_codecs.get("ordered_stable_element_keys_v1"),
        {
            "layout": ["count_u32_be", "exact_ordered_items"],
            "item_layout": [
                "item_length_u32_be",
                "stable_element_key_v1_canonical_bytes",
            ],
            "order": "strictly_ascending_stable_element_key_v1_canonical_bytes",
            "duplicate_key": "refused",
            "maximum_items": 1_048_576,
        },
        "semantic_rows.scalar_codecs.ordered_stable_element_keys_v1",
        "invalid_semantic_rows",
    )
    _expect_exact(
        scalar_codecs.get("stable_bsl_value_v1"),
        {
            "closed_tags": {
                "int_i64": 1,
                "currency_i128": 2,
                "real_f64_bits": 3,
                "ratio_f64_bits_with_optional_bounds": 4,
                "bool": 5,
                "enum_type_and_member": 6,
                "stable_node_key": 7,
                "stable_hyperedge_key": 8,
                "stable_edge_key": 9,
            },
            "graph_reference_payload": "full StableElementKeyV1 canonical layout",
            "graph_reference_layout": [
                "domain_ascii_nul",
                "layout_u32",
                "key_kind_u8",
                "scenario_qname",
                "exact_key_fields",
            ],
            "outer_variant_key_kind": "must_match_inner_key_kind",
            "runtime_graph_handles": "prohibited",
            "unknown_tag": "refused",
        },
        "semantic_rows.scalar_codecs.stable_bsl_value_v1",
        "invalid_semantic_rows",
    )
    for row in _rows(ledger.get("columns"), "schema_epochs.activation_ledger.columns"):
        if row.get("codec") not in scalar_ids:
            raise RustPersistenceCutoverRefusal(
                "dangling_codec", f"activation ledger codec {row.get('codec')!r} is undefined"
            )
    for row in _rows(bundle.get("fields"), "foundation.content_bundle.fields"):
        if row.get("codec") not in scalar_ids:
            raise RustPersistenceCutoverRefusal(
                "dangling_codec", f"content bundle codec {row.get('codec')!r} is undefined"
            )
    for row in _rows(foundation.get("exact_fields"), "foundation.exact_fields"):
        if row.get("codec") not in scalar_ids:
            raise RustPersistenceCutoverRefusal(
                "dangling_codec", f"foundation codec {row.get('codec')!r} is undefined"
            )

    row_codecs = _rows(semantic_rows["row_codecs"], "semantic_rows.row_codecs")
    row_codec_ids = [_string(row.get("id"), "row_codec.id") for row in row_codecs]
    if len(row_codec_ids) != len(set(row_codec_ids)):
        raise RustPersistenceCutoverRefusal("invalid_semantic_rows", "row codec ids must be unique")
    typed_relations: list[str] = []
    codec_family: dict[str, str] = {}
    codec_tags: set[tuple[str, int]] = set()
    for row in row_codecs:
        codec_id = _string(row.get("id"), "row_codec.id")
        required_row_codec_fields = {
            "id",
            "tag_u8",
            "family",
            "typed_relation",
            "key_fields",
            "payload_fields",
        }
        allowed_row_codec_fields = set(required_row_codec_fields)
        if codec_id == "archive_dirty_receipt_v1":
            allowed_row_codec_fields.add("typed_primary_key")
        _expect_exact(
            set(row),
            allowed_row_codec_fields,
            "row_codec keys",
            "invalid_semantic_rows",
        )
        family = _string(row.get("family"), "row_codec.family")
        if family not in EXPECTED_SEMANTIC_FAMILIES:
            raise RustPersistenceCutoverRefusal(
                "invalid_semantic_rows", f"row codec {codec_id} has unknown family {family!r}"
            )
        tag = _integer(row.get("tag_u8"), "row_codec.tag_u8")
        if not 0 < tag <= 255 or (family, tag) in codec_tags:
            raise RustPersistenceCutoverRefusal(
                "invalid_semantic_rows", f"row codec {codec_id} tag is not unique in {family}"
            )
        codec_tags.add((family, tag))
        codec_family[codec_id] = family
        typed_relations.append(_string(row.get("typed_relation"), "row_codec.typed_relation"))
        for field_list in ["key_fields", "payload_fields"]:
            fields = _list(row.get(field_list), f"row_codec.{field_list}")
            if not fields and not (
                codec_id == "archive_dirty_receipt_v1" and field_list == "key_fields"
            ):
                raise RustPersistenceCutoverRefusal(
                    "invalid_semantic_rows", f"row codec {codec_id} {field_list} must be nonempty"
                )
            field_names: list[str] = []
            for index, value in enumerate(fields):
                field_value = _string(value, f"row_codec.{field_list}[{index}]")
                field_names.append(field_value.split(":", 1)[0])
                codec = _field_codec(value, f"row_codec.{field_list}[{index}]")
                if codec not in scalar_ids:
                    raise RustPersistenceCutoverRefusal(
                        "dangling_codec", f"row codec {row.get('id')} references {codec!r}"
                    )
            if len(field_names) != len(set(field_names)):
                raise RustPersistenceCutoverRefusal(
                    "invalid_semantic_rows", f"row codec {codec_id} repeats a {field_list} name"
                )
            if field_list == "key_fields" and {"campaign_id", "resolve_tick"} & set(field_names):
                raise RustPersistenceCutoverRefusal(
                    "invalid_semantic_rows",
                    f"row codec {codec_id} duplicates storage identity in its semantic key",
                )
        if codec_id == "archive_dirty_receipt_v1":
            _expect_exact(
                row.get("typed_primary_key"),
                ["campaign_id", "resolve_tick"],
                "archive dirty receipt typed primary key",
                "invalid_semantic_rows",
            )
    if len(typed_relations) != len(set(typed_relations)):
        raise RustPersistenceCutoverRefusal(
            "invalid_semantic_rows", "typed semantic relations must be unique"
        )

    producers = _rows(semantic_rows["producer_inventory"], "semantic_rows.producer_inventory")
    producer_ids = [_string(row.get("id"), "producer.id") for row in producers]
    if len(producer_ids) != len(set(producer_ids)):
        raise RustPersistenceCutoverRefusal("invalid_semantic_rows", "producer ids must be unique")
    producer_families = [_string(row.get("family"), "producer.family") for row in producers]
    _expect_exact(
        producer_families,
        EXPECTED_SEMANTIC_FAMILIES,
        "semantic_rows producer families",
        "invalid_semantic_rows",
    )
    row_codec_id_set = set(row_codec_ids)
    producer_tags: set[int] = set()
    referenced_row_codecs: list[str] = []
    emptiness_proofs: list[str] = []
    source_accessors: list[str] = []
    for producer in producers:
        producer_id = _string(producer.get("id"), "producer.id")
        required_producer_fields = {
            "id",
            "tag_u8",
            "family",
            "source_type",
            "source_accessor",
            "row_codecs",
        }
        if producer_id not in {
            "material_state_rows_v1",
            "checkpoint_rows_v1",
            "campaign_work_receipt_v1",
        }:
            required_producer_fields.add("emptiness_proof_type")
        allowed_producer_fields = required_producer_fields | {
            "closed_variants",
            "value_codec",
            "emptiness_proof_type",
        }
        if producer_id == "campaign_work_receipt_v1":
            allowed_producer_fields |= {"source_identity", "cardinality", "emptiness_proof"}
        if producer_id == "checkpoint_rows_v1":
            allowed_producer_fields.add("cardinality")
        if (
            not required_producer_fields <= set(producer)
            or not set(producer) <= allowed_producer_fields
        ):
            raise RustPersistenceCutoverRefusal(
                "invalid_semantic_rows", f"producer {producer.get('id')!r} has an open shape"
            )
        if producer_id == "material_state_rows_v1" and "emptiness_proof_type" in producer:
            raise RustPersistenceCutoverRefusal(
                "invalid_semantic_rows",
                "material state is inherently nonempty and must not claim an aggregate empty proof",
            )
        if producer_id == "checkpoint_rows_v1":
            _expect_exact(
                {
                    "closed_variants": producer.get("closed_variants"),
                    "cardinality": producer.get("cardinality"),
                },
                {"closed_variants": ["full"], "cardinality": "exactly_nine"},
                "checkpoint producer",
                "invalid_semantic_rows",
            )
        if producer_id == "campaign_work_receipt_v1":
            _expect_exact(
                {
                    "source_identity": producer.get("source_identity"),
                    "cardinality": producer.get("cardinality"),
                    "emptiness_proof": producer.get("emptiness_proof"),
                },
                {
                    "source_identity": "IdentifiedTickReportV1.tick_content_hash",
                    "cardinality": "exactly_one",
                    "emptiness_proof": "prohibited",
                },
                "campaign work receipt producer",
                "invalid_semantic_rows",
            )
        producer_tag = _integer(producer.get("tag_u8"), "producer.tag_u8")
        if not 0 < producer_tag <= 255 or producer_tag in producer_tags:
            raise RustPersistenceCutoverRefusal(
                "invalid_semantic_rows", f"producer {producer_id} tag must be unique"
            )
        producer_tags.add(producer_tag)
        producer_family = _string(producer.get("family"), "producer.family")
        _string(producer.get("source_type"), "producer.source_type")
        source_accessors.append(
            _string(producer.get("source_accessor"), "producer.source_accessor")
        )
        if "emptiness_proof_type" in producer:
            emptiness_proofs.append(
                _string(producer.get("emptiness_proof_type"), "producer.emptiness_proof_type")
            )
        for codec in _list(producer.get("row_codecs"), "producer.row_codecs"):
            if codec not in row_codec_id_set:
                raise RustPersistenceCutoverRefusal(
                    "dangling_row_codec",
                    f"producer {producer.get('id')} references {codec!r}",
                )
            if codec_family[codec] != producer_family:
                raise RustPersistenceCutoverRefusal(
                    "dangling_row_codec",
                    f"producer {producer_id} crosses {producer_family} to {codec_family[codec]}",
                )
            referenced_row_codecs.append(codec)
        value_codec = producer.get("value_codec")
        if value_codec is not None and value_codec not in scalar_ids:
            raise RustPersistenceCutoverRefusal(
                "dangling_codec", f"producer value codec {value_codec!r} is undefined"
            )
    if referenced_row_codecs != row_codec_ids:
        raise RustPersistenceCutoverRefusal(
            "dangling_row_codec",
            "producer inventory must reference every row codec exactly once in contract order",
        )
    if len(source_accessors) != len(set(source_accessors)) or len(emptiness_proofs) != len(
        set(emptiness_proofs)
    ):
        raise RustPersistenceCutoverRefusal(
            "invalid_semantic_rows", "source accessors and empty proof types must be unique"
        )
    if not _list(semantic_rows.get("laws"), "semantic_rows.laws"):
        raise RustPersistenceCutoverRefusal(
            "invalid_semantic_rows", "semantic_rows.laws must be nonempty"
        )

    storage = _mapping(contract.get("storage"), "storage")
    _expect_exact(
        set(storage),
        {
            "canonical_schemas",
            "marker",
            "visibility_law",
            "public_marker_disposition",
            "prohibited_final_relations",
            "prohibited_final_columns",
            "prohibited_semantic_sql_types",
            "physical_scalar_columns",
            "bsl_value_columns_v1",
            "parent_relation_law",
            "normalized_child_relations",
            "normalized_child_laws",
            "metadata_disposition",
            "laws",
        },
        "storage keys",
        "invalid_storage",
    )
    _expect_exact(
        storage.get("canonical_schemas"),
        ["babylon_ref", "babylon_state", "babylon_meta"],
        "storage.canonical_schemas",
        "invalid_storage",
    )
    _expect_exact(
        storage.get("marker"),
        "babylon_state.tick_commit",
        "storage.marker",
        "invalid_storage",
    )
    _expect_exact(
        storage.get("visibility_law"),
        "marker_last",
        "storage.visibility_law",
        "invalid_storage",
    )
    _expect_exact(
        storage.get("prohibited_final_relations"),
        EXPECTED_PROHIBITED_RELATIONS,
        "storage.prohibited_final_relations",
        "invalid_storage",
    )
    _expect_exact(
        storage.get("prohibited_final_columns"),
        ["row_key", "row_payload"],
        "storage.prohibited_final_columns",
        "invalid_storage",
    )
    _expect_exact(
        storage.get("prohibited_semantic_sql_types"),
        ["JSON", "JSONB"],
        "storage.prohibited_semantic_sql_types",
        "invalid_storage",
    )
    physical_scalar_columns = _mapping(
        storage.get("physical_scalar_columns"), "storage.physical_scalar_columns"
    )
    _expect_exact(
        list(physical_scalar_columns),
        [
            "bool_u8",
            "u16_be",
            "u32_be",
            "u64_be",
            "i64_be",
            "nonnegative_i64_be",
            "i128_be",
            "uuid16",
            "digest32",
            "h3_cell_id_i64_be",
            "f64_be_canonical",
            "bounded_utf8",
            "bounded_bytes",
            "optional_bounded_utf8",
            "optional_h3_cell_id_i64_be",
            "optional_digest32",
            "closed_enum_u8",
            "stable_element_key_v1",
        ],
        "storage.physical_scalar_columns",
        "invalid_storage",
    )
    if not all(
        _mapping(value, f"physical scalar {key}") for key, value in physical_scalar_columns.items()
    ):
        raise RustPersistenceCutoverRefusal(
            "invalid_storage", "physical scalar mappings must be nonempty"
        )
    _expect_exact(
        physical_scalar_columns.get("h3_cell_id_i64_be", {}).get("rust_validation"),
        "babylon_kernel::H3CellId::try_from(i64)",
        "storage.physical_scalar_columns.h3_cell_id_i64_be.rust_validation",
        "invalid_storage",
    )
    _expect_exact(
        physical_scalar_columns.get("optional_h3_cell_id_i64_be", {}).get("rust_validation"),
        "babylon_kernel::H3CellId::try_from(i64)",
        "storage.physical_scalar_columns.optional_h3_cell_id_i64_be.rust_validation",
        "invalid_storage",
    )
    _expect_exact(
        physical_scalar_columns.get("stable_element_key_v1"),
        {
            "postgresql": "BYTEA",
            "nullable": False,
            "rust_type": "StableElementKeyV1",
            "encoding": "exact_canonical_bytes",
            "validation": "checked_before_insert",
        },
        "storage.physical_scalar_columns.stable_element_key_v1",
        "invalid_storage",
    )
    bsl_columns = _mapping(storage.get("bsl_value_columns_v1"), "storage.bsl_value_columns_v1")
    _expect_exact(
        set(bsl_columns),
        {"columns", "exact_variant_check", "law"},
        "storage.bsl_value_columns_v1 keys",
        "invalid_storage",
    )
    if not _rows(bsl_columns.get("columns"), "storage.bsl_value_columns_v1.columns"):
        raise RustPersistenceCutoverRefusal(
            "invalid_storage", "stable BSL value columns must be explicit"
        )
    variant_check = bsl_columns.get("exact_variant_check")
    if not isinstance(variant_check, dict):
        raise RustPersistenceCutoverRefusal(
            "invalid_storage", "storage.bsl_value_columns_v1 exact variants must be a mapping"
        )
    _expect_exact(
        set(variant_check),
        set(range(1, 10)),
        "storage.bsl_value_columns_v1 exact variants",
        "invalid_storage",
    )
    _string(bsl_columns.get("law"), "storage.bsl_value_columns_v1.law")
    parent_law = _mapping(storage.get("parent_relation_law"), "storage.parent_relation_law")
    _expect_exact(
        set(parent_law),
        {
            "mandatory_prefix_columns",
            "scalar_expansion",
            "bsl_expansion",
            "primary_key",
            "ordered_field_storage",
        },
        "storage.parent_relation_law keys",
        "invalid_storage",
    )
    _expect_exact(
        parent_law.get("ordered_field_storage"),
        "prohibited_in_parent",
        "storage.parent_relation_law.ordered_field_storage",
        "invalid_storage",
    )
    child_rows = _rows(
        storage.get("normalized_child_relations"), "storage.normalized_child_relations"
    )
    if not child_rows:
        raise RustPersistenceCutoverRefusal(
            "invalid_storage", "normalized ordered fields require named child relations"
        )
    child_relations: list[str] = []
    codec_by_relation = {
        _string(row.get("typed_relation"), "typed relation"): row for row in row_codecs
    }
    for row in child_rows:
        _expect_exact(
            set(row),
            {"relation", "parent", "parent_key", "columns", "primary_key", "unique", "foreign_key"},
            "normalized child relation keys",
            "invalid_storage",
        )
        child_relations.append(_string(row.get("relation"), "normalized child relation"))
        if row.get("parent") not in typed_relations:
            raise RustPersistenceCutoverRefusal(
                "invalid_storage", f"normalized child {row.get('relation')} has no typed parent"
            )
        parent_codec = codec_by_relation[_string(row.get("parent"), "normalized child parent")]
        parent_key_fields = [
            _string(value, "row key field").split(":", 1)[0]
            for value in _list(parent_codec.get("key_fields"), "row key fields")
        ]
        expected_parent_key = ["campaign_id", "resolve_tick", *parent_key_fields]
        _expect_exact(
            row.get("parent_key"),
            expected_parent_key,
            "normalized child parent_key",
            "invalid_storage",
        )
        if not _list(row.get("columns"), "normalized child columns"):
            raise RustPersistenceCutoverRefusal(
                "invalid_storage", "normalized child columns must be nonempty"
            )
        _expect_exact(
            row.get("foreign_key"),
            "exact_parent_key_cascade",
            "normalized child foreign_key",
            "invalid_storage",
        )
        _expect_exact(
            row.get("primary_key"),
            [*expected_parent_key, "position"],
            "normalized child primary_key",
            "invalid_storage",
        )
    if len(child_relations) != len(set(child_relations)):
        raise RustPersistenceCutoverRefusal(
            "invalid_storage", "normalized child relations must be unique"
        )
    organization_territory = next(
        (
            row
            for row in child_rows
            if row.get("relation") == "babylon_state.organization_territory_v1"
        ),
        None,
    )
    _expect_exact(
        organization_territory,
        {
            "relation": "babylon_state.organization_territory_v1",
            "parent": "babylon_state.organization_state_v1",
            "parent_key": ["campaign_id", "resolve_tick", "organization_id"],
            "columns": [
                "position_INTEGER_CHECK_gte_0",
                "territory_id_BYTEA_NOT_NULL_STABLE_ELEMENT_KEY_V1",
            ],
            "primary_key": ["campaign_id", "resolve_tick", "organization_id", "position"],
            "unique": ["campaign_id", "resolve_tick", "organization_id", "territory_id"],
            "foreign_key": "exact_parent_key_cascade",
        },
        "storage organization territory normalized child",
        "invalid_storage",
    )
    ordered_codecs = {
        "ordered_bounded_utf8_v1",
        "ordered_named_bsl_fields_v1",
        "ordered_named_f64_fields_v1",
        "ordered_stable_element_keys_v1",
    }
    ordered_parent_relations = [
        _string(row.get("typed_relation"), "row codec typed_relation")
        for row in row_codecs
        for value in _list(row.get("payload_fields"), "row codec payload fields")
        if _field_codec(value, "row codec payload field") in ordered_codecs
    ]
    child_parent_relations = [
        _string(row.get("parent"), "normalized child parent") for row in child_rows
    ]
    if sorted(ordered_parent_relations) != sorted(child_parent_relations):
        raise RustPersistenceCutoverRefusal(
            "invalid_storage",
            "every specialized ordered field needs exactly one normalized child relation",
        )
    child_laws = _list(storage.get("normalized_child_laws"), "storage.normalized_child_laws")
    if not child_laws:
        raise RustPersistenceCutoverRefusal(
            "invalid_storage", "normalized child laws must be nonempty"
        )
    if (
        "Organization territory positions preserve strictly ascending exact "
        "StableElementKeyV1 canonical bytes from the source-owned PRESENCE topology."
        not in child_laws
    ):
        raise RustPersistenceCutoverRefusal(
            "invalid_storage", "organization territory child ordering law is absent"
        )
    if not _list(storage.get("laws"), "storage.laws"):
        raise RustPersistenceCutoverRefusal("invalid_storage", "storage.laws must be nonempty")
    public_marker = _mapping(
        storage.get("public_marker_disposition"), "storage.public_marker_disposition"
    )
    _expect_exact(
        set(public_marker),
        {
            "source",
            "source_partition",
            "action",
            "destination",
            "hash_law",
            "checkpoint_law",
            "count_law",
            "retirement",
        },
        "storage.public_marker_disposition keys",
        "invalid_storage",
    )
    _expect_exact(
        (
            public_marker.get("source"),
            public_marker.get("destination"),
            public_marker.get("action"),
        ),
        (
            "public.tick_commit",
            "babylon_state.tick_commit",
            "migrate_verify_drop_in_activation_epoch",
        ),
        "storage.public_marker_disposition",
        "invalid_storage",
    )
    _expect_exact(
        public_marker.get("source_partition"),
        "public.tick_commit_default",
        "storage.public_marker_disposition.source_partition",
        "invalid_storage",
    )
    for field in ["hash_law", "checkpoint_law", "count_law", "retirement"]:
        _string(public_marker.get(field), f"storage.public_marker_disposition.{field}")
    metadata = _mapping(storage.get("metadata_disposition"), "storage.metadata_disposition")
    _expect_exact(
        set(metadata),
        {
            "owner",
            "material_state_dependency",
            "tick_hash_membership",
            "relations",
            "python_writes_after_activation",
        },
        "storage.metadata_disposition keys",
        "invalid_storage",
    )
    _expect_exact(
        (
            metadata.get("owner"),
            metadata.get("material_state_dependency"),
            metadata.get("tick_hash_membership"),
            metadata.get("python_writes_after_activation"),
        ),
        ("babylon_persistence::meta", "prohibited", "excluded", "prohibited"),
        "storage.metadata_disposition authority",
        "invalid_storage",
    )
    metadata_rows = _rows(metadata.get("relations"), "metadata relations")
    _expect_exact(
        [row.get("relation") for row in metadata_rows],
        [
            "babylon_meta.campaign",
            "babylon_meta.watchlist",
            "babylon_meta.jumplist",
            "babylon_meta.breadcrumb",
        ],
        "storage.metadata_disposition.relations",
        "invalid_storage",
    )
    for row in metadata_rows:
        _expect_exact(
            set(row),
            {"relation", "action", "rust_type", "key", "law"},
            "metadata relation keys",
            "invalid_storage",
        )
        _expect_exact(
            row.get("action"),
            "retain_typed_in_place",
            "metadata relation action",
            "invalid_storage",
        )
        _string(row.get("rust_type"), "metadata relation rust_type")
        if not _list(row.get("key"), "metadata relation key"):
            raise RustPersistenceCutoverRefusal(
                "invalid_storage", "metadata relation keys must be nonempty"
            )
        _string(row.get("law"), "metadata relation law")

    boundary = _mapping(contract.get("reader_boundary"), "reader_boundary")
    _expect_exact(
        set(boundary),
        {
            "contract",
            "sha256",
            "edges",
            "source_files",
            "runtime_consumer_edges",
            "bootstrap_predecessors",
            "views",
            "epoch7_edges",
            "epoch7_source_files",
            "epoch7_views",
            "projection_relations",
            "view_projections",
            "requirement",
        },
        "reader_boundary keys",
        "stale_reader_census",
    )
    for field, expected in EXPECTED_READER_BOUNDARY.items():
        _expect_exact(
            boundary.get(field), expected, f"reader_boundary.{field}", "stale_reader_census"
        )
    projection_rows = _rows(
        boundary.get("projection_relations"), "reader_boundary.projection_relations"
    )
    projection_legacy = [
        _string(row.get("legacy_relation"), "legacy_relation") for row in projection_rows
    ]
    if len(projection_legacy) != len(set(projection_legacy)):
        raise RustPersistenceCutoverRefusal(
            "stale_reader_census", "legacy projection relations must be unique"
        )
    producer_to_relations = {
        _string(producer.get("id"), "producer id"): {
            _string(codec.get("typed_relation"), "typed relation")
            for codec in row_codecs
            if codec_family[_string(codec.get("id"), "row codec id")]
            == _string(producer.get("family"), "producer family")
        }
        for producer in producers
    }
    declared_typed_relations = set(typed_relations)
    for row in projection_rows:
        _expect_exact(
            set(row) - {"disposition"},
            {"legacy_relation", "typed_relation", "producer", "reader_edges"},
            "projection relation keys",
            "stale_reader_census",
        )
        typed_relation = _string(row.get("typed_relation"), "projection typed_relation")
        producer_id = _string(row.get("producer"), "projection producer")
        if (
            producer_id in producer_to_relations
            and typed_relation not in producer_to_relations[producer_id]
        ):
            raise RustPersistenceCutoverRefusal(
                "stale_reader_census",
                f"projection {row.get('legacy_relation')} is not emitted by {producer_id}",
            )
        if producer_id == "sql_projection" and typed_relation != row.get("legacy_relation"):
            raise RustPersistenceCutoverRefusal(
                "stale_reader_census", "SQL projection identity must remain exact"
            )
        if producer_id == "none" and not (
            typed_relation == "none"
            and row.get("disposition")
            in {
                "drop_after_view_parity",
                "preserve_until_zero_row_census_then_drop_without_typed_replacement",
            }
        ):
            raise RustPersistenceCutoverRefusal(
                "stale_reader_census", "an unproduced predecessor requires exact retirement"
            )
    if (
        sum(_integer(row.get("reader_edges"), "projection reader_edges") for row in projection_rows)
        != EXPECTED_READER_BOUNDARY["edges"]
    ):
        raise RustPersistenceCutoverRefusal(
            "stale_reader_census",
            "projection reader edges must sum to the exact reader boundary",
        )
    view_rows = _rows(boundary.get("view_projections"), "reader_boundary.view_projections")
    if view_rows:
        raise RustPersistenceCutoverRefusal(
            "stale_reader_census",
            "terminal Rust authority must not retain Python game-state view projections",
        )
    allowed_view_sources = (
        declared_typed_relations
        | {_string(storage.get("marker"), "storage.marker")}
        | {
            _string(row.get("typed_relation"), "projection typed_relation")
            for row in projection_rows
            if row.get("typed_relation") != "none"
        }
    )
    view_names: list[str] = []
    for row in view_rows:
        _expect_exact(set(row), {"name", "sources"}, "view projection keys", "stale_reader_census")
        view_names.append(_string(row.get("name"), "view projection name"))
        sources = {
            _string(value, "view projection source")
            for value in _list(row.get("sources"), "view projection sources")
        }
        if not sources or not sources <= allowed_view_sources:
            raise RustPersistenceCutoverRefusal(
                "stale_reader_census", f"view {row.get('name')} has an undefined source"
            )
    if len(view_names) != len(set(view_names)):
        raise RustPersistenceCutoverRefusal(
            "stale_reader_census", "view projection names must be unique"
        )
    _string(boundary.get("requirement"), "reader_boundary.requirement")

    disposition = _mapping(contract.get("data_disposition"), "data_disposition")
    _expect_exact(
        set(disposition),
        {
            "whole_table_drop_after_parity",
            "replace_then_drop_after_ordered_count_and_hash_parity",
            "preserve_until_zero_row_census_then_drop_without_typed_replacement",
            "identity_columns_only_until_lossless_destination_exists",
            "lodes_destination",
            "prohibited_without_proof",
            "python_written_relation_disposition",
        },
        "data_disposition keys",
        "lossy_table_disposition",
    )
    if disposition.get("whole_table_drop_after_parity") != ["public.hex_latest"]:
        raise RustPersistenceCutoverRefusal(
            "lossy_table_disposition", "only public.hex_latest is pre-proved as a whole cache"
        )
    for field in [
        "replace_then_drop_after_ordered_count_and_hash_parity",
        "preserve_until_zero_row_census_then_drop_without_typed_replacement",
        "identity_columns_only_until_lossless_destination_exists",
        "prohibited_without_proof",
    ]:
        if not _list(disposition.get(field), f"data_disposition.{field}"):
            raise RustPersistenceCutoverRefusal(
                "lossy_table_disposition", f"data_disposition.{field} must be nonempty"
            )
    if (
        "public.tick_commit"
        not in disposition["replace_then_drop_after_ordered_count_and_hash_parity"]
    ):
        raise RustPersistenceCutoverRefusal(
            "lossy_table_disposition", "public.tick_commit must retire after exact parity"
        )
    deferred_untyped = set(
        _list(
            disposition["preserve_until_zero_row_census_then_drop_without_typed_replacement"],
            "data_disposition.preserve_until_zero_row_census_then_drop_without_typed_replacement",
        )
    )
    _expect_exact(
        deferred_untyped,
        {
            "public.hex_activity",
            "public.hex_state",
            "public.hex_terrain_state",
            "public.infrastructure_link_state",
        },
        "zero-census untyped relation disposition",
        "lossy_table_disposition",
    )
    lodes = _mapping(disposition.get("lodes_destination"), "data_disposition.lodes_destination")
    _expect_exact(
        lodes.get("variants"),
        ["hex_cell_id", "canada", "rest_of_usa"],
        "data_disposition.lodes_destination.variants",
        "invalid_lodes_destination",
    )
    _string(lodes.get("sql_law"), "data_disposition.lodes_destination.sql_law")
    written = _mapping(
        disposition.get("python_written_relation_disposition"),
        "data_disposition.python_written_relation_disposition",
    )
    _expect_exact(
        set(written),
        {
            "typed_tick_replacement",
            "foundation_or_reference_replacement",
            "rust_metadata_replacement",
            "non_goal_unreachable_drop",
            "cache_drop_after_view_parity",
            "sole_marker_migration_and_drop",
            "law",
        },
        "data_disposition.python_written_relation_disposition keys",
        "lossy_table_disposition",
    )
    disposition_relations: list[str] = []
    for field in [
        "typed_tick_replacement",
        "foundation_or_reference_replacement",
        "rust_metadata_replacement",
        "non_goal_unreachable_drop",
        "cache_drop_after_view_parity",
        "sole_marker_migration_and_drop",
    ]:
        values = [
            _string(value, f"python_written_relation_disposition.{field} item")
            for value in _list(written.get(field), f"python_written_relation_disposition.{field}")
        ]
        if not values:
            raise RustPersistenceCutoverRefusal(
                "lossy_table_disposition", f"{field} must be nonempty"
            )
        disposition_relations.extend(values)
    if len(disposition_relations) != len(set(disposition_relations)):
        raise RustPersistenceCutoverRefusal(
            "lossy_table_disposition", "every Python-written relation needs one disposition"
        )
    _string(written.get("law"), "python_written_relation_disposition.law")
    _expect_exact(
        written.get("rust_metadata_replacement"),
        [row.get("relation") for row in metadata_rows],
        "python_written_relation_disposition.rust_metadata_replacement",
        "lossy_table_disposition",
    )
    _expect_exact(
        written.get("cache_drop_after_view_parity"),
        disposition.get("whole_table_drop_after_parity"),
        "python_written_relation_disposition.cache_drop_after_view_parity",
        "lossy_table_disposition",
    )
    _expect_exact(
        written.get("sole_marker_migration_and_drop"),
        [public_marker.get("source"), public_marker.get("source_partition")],
        "python_written_relation_disposition.sole_marker_migration_and_drop",
        "lossy_table_disposition",
    )

    python = _mapping(contract.get("python_authority"), "python_authority")
    _expect_exact(
        set(python),
        {
            "must_delete",
            "must_replace_entrypoints_without_python_adapter",
            "census",
            "retain_as_non_authoritative_periphery",
            "tranche_law",
        },
        "python_authority keys",
        "invalid_python_authority",
    )
    python_rows = _rows(python.get("must_delete"), "python_authority.must_delete")
    refuse_rows = _rows(
        python.get("must_replace_entrypoints_without_python_adapter"),
        "python_authority.must_replace_entrypoints_without_python_adapter",
    )
    if not python_rows or not refuse_rows:
        raise RustPersistenceCutoverRefusal(
            "invalid_python_authority", "deletion and refusal inventories must be nonempty"
        )
    for row in python_rows:
        _expect_exact(set(row), {"path", "symbols"}, "must_delete row", "invalid_python_authority")
        _string(row.get("path"), "must_delete.path")
        if not _list(row.get("symbols"), "must_delete.symbols"):
            raise RustPersistenceCutoverRefusal(
                "invalid_python_authority", "must_delete.symbols must be nonempty"
            )
    for row in refuse_rows:
        allowed_keys = {"path", "entrypoint", "required_rust_command", "prohibited_fragments"}
        if (
            not {"path", "entrypoint", "required_rust_command"} <= set(row)
            or not set(row) <= allowed_keys
        ):
            raise RustPersistenceCutoverRefusal(
                "invalid_python_authority", "replacement entrypoint rows must be closed"
            )
        _string(row.get("path"), "must_replace_entrypoints_without_python_adapter.path")
        _string(row.get("entrypoint"), "must_replace_entrypoints_without_python_adapter.entrypoint")
        _string(row.get("required_rust_command"), "required_rust_command")
        if "prohibited_fragments" in row and not _list(
            row.get("prohibited_fragments"), "prohibited_fragments"
        ):
            raise RustPersistenceCutoverRefusal(
                "invalid_python_authority", "prohibited_fragments cannot be empty"
            )
    census = _mapping(python.get("census"), "python_authority.census")
    _expect_exact(
        set(census),
        {
            "inventory_entries",
            "inventory_sha256",
            "digest_preimage",
            "symbol_rename_does_not_satisfy_retirement",
            "scan_roots",
            "forbidden_capabilities",
            "required_evidence",
        },
        "python_authority.census keys",
        "invalid_python_authority",
    )
    if census.get("symbol_rename_does_not_satisfy_retirement") is not True:
        raise RustPersistenceCutoverRefusal(
            "invalid_python_authority", "Python authority census must be exact and rename-safe"
        )
    _expect_exact(
        census.get("scan_roots"),
        ["src/babylon", "tools", ".mise.toml"],
        "python_authority.census.scan_roots",
        "invalid_python_authority",
    )
    _expect_exact(
        census.get("forbidden_capabilities"),
        [
            "game_writer_connection",
            "governed_relation_ddl",
            "governed_relation_dml",
            "copy_from",
            "dynamic_sql",
            "migration_execution",
            "game_mutation_protocol",
            "game_writer_credential",
        ],
        "python_authority.census.forbidden_capabilities",
        "invalid_python_authority",
    )
    _expect_exact(
        census.get("digest_preimage"),
        "globally sorted UTF-8 union of path::symbol plus LF and path::entrypoint plus LF",
        "python_authority.census.digest_preimage",
        "invalid_python_authority",
    )
    delete_inventory = sorted(
        f"{_string(row['path'], 'must_delete.path')}::{_string(symbol, 'must_delete.symbol')}"
        for row in python_rows
        for symbol in _list(row["symbols"], "must_delete.symbols")
    )
    entrypoint_inventory = sorted(
        f"{_string(row['path'], 'replacement.path')}::{_string(row['entrypoint'], 'replacement.entrypoint')}"
        for row in refuse_rows
    )
    inventory_preimage = "".join(
        f"{entry}\n" for entry in sorted([*delete_inventory, *entrypoint_inventory])
    ).encode("utf-8")
    _expect_exact(
        census.get("inventory_entries"),
        124,
        "python_authority.census.inventory_entries",
        "invalid_python_authority",
    )
    _expect_exact(
        len(delete_inventory) + len(entrypoint_inventory),
        124,
        "computed Python authority inventory entries",
        "invalid_python_authority",
    )
    _expect_exact(
        census.get("inventory_sha256"),
        hashlib.sha256(inventory_preimage).hexdigest(),
        "python_authority.census.inventory_sha256",
        "invalid_python_authority",
    )
    _expect_exact(
        census.get("inventory_sha256"),
        "7393c6709c47ac4dff2dc7b8bde3be48a1ea8341c110e448dc48b5cc4d6fec65",
        "python_authority.census.inventory_sha256",
        "invalid_python_authority",
    )
    _expect_exact(
        census.get("required_evidence"),
        (
            "Exact inventory plus an independent AST call graph, SQL-literal, dynamic-SQL, "
            "migration, and connection-constructor scan."
        ),
        "python_authority.census.required_evidence",
        "invalid_python_authority",
    )
    if not _list(
        python.get("retain_as_non_authoritative_periphery"),
        "python_authority.retain_as_non_authoritative_periphery",
    ):
        raise RustPersistenceCutoverRefusal(
            "invalid_python_authority", "retained periphery must be explicit"
        )
    _string(python.get("tranche_law"), "python_authority.tranche_law")

    vectors = _mapping(contract.get("vectors"), "vectors")
    _expect_exact(vectors, EXPECTED_VECTOR_METADATA, "vectors", "invalid_vectors")

    _expect_exact(contract.get("proofs"), EXPECTED_PROOFS, "proofs", "invalid_proofs")
    _expect_exact(
        contract.get("non_goals"),
        [
            "Bevy persistence integration",
            "player-action execution",
            "new BSL primitive or material-mechanic rule",
            "fabricated subsystem, conservation, boundary-flow, or Archive rows",
        ],
        "non_goals",
        "invalid_non_goals",
    )
    for section, expected_digest in EXPECTED_SECTION_SHA256.items():
        actual_digest = _section_digest(contract[section])
        if actual_digest != expected_digest:
            raise RustPersistenceCutoverRefusal(
                "section_digest",
                f"{section} expected {expected_digest}; got {actual_digest}",
            )


def _text(root: Path, relative: str) -> str:
    path = root / relative
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _python_symbol_survives(source: str, symbol: str) -> bool:
    leaf = symbol.rsplit(".", 1)[-1]
    return (
        symbol in source
        or f"def {leaf}(" in source
        or f"async def {leaf}(" in source
        or f"class {leaf}" in source
        or leaf in source
    )


def _call_name(call: ast.Call) -> str:
    """Return a stable dotted name for one syntactic call target."""

    parts: list[str] = []
    node: ast.expr = call.func
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _string_expression(node: ast.AST, bindings: dict[str, str]) -> str:
    """Recover the static text of a SQL-bearing expression when possible."""

    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return bindings.get(node.id, "")
    if isinstance(node, ast.JoinedStr):
        return "".join(
            part.value if isinstance(part, ast.Constant) and isinstance(part.value, str) else "{}"
            for part in node.values
        )
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _string_expression(node.left, bindings) + _string_expression(node.right, bindings)
    if isinstance(node, ast.Call) and node.args:
        return _string_expression(node.args[0], bindings)
    return ""


def _executable_string_bindings(tree: ast.AST) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                text = _string_expression(node.value, bindings)
                if text:
                    bindings[target.id] = text
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.value is not None:
                text = _string_expression(node.value, bindings)
                if text:
                    bindings[node.target.id] = text
    return bindings


def _contains_game_dsn(node: ast.AST, aliases: set[str]) -> bool:
    return any(
        (isinstance(child, ast.Name) and child.id in {"BABYLON_DSN", "GAME_DSN"} | aliases)
        or (
            isinstance(child, ast.Constant)
            and isinstance(child.value, str)
            and child.value in {"BABYLON_DSN", "GAME_DSN"}
        )
        for child in ast.walk(node)
    )


def _references_game_dsn(call: ast.Call, aliases: set[str]) -> bool:
    return any(
        _contains_game_dsn(argument, aliases)
        for argument in [*call.args, *(keyword.value for keyword in call.keywords)]
    )


def _sql_targets_governed_relation(sql: str, governed_relations: set[str]) -> bool:
    lowered = sql.lower()
    if re.search(r"\bbabylon_(?:ref|state|meta)\s*\.", lowered):
        return True
    return any(
        re.search(rf"(?<![a-z0-9_]){re.escape(relation.lower())}(?![a-z0-9_])", lowered)
        or re.search(
            rf"(?<![a-z0-9_]){re.escape(relation.rsplit('.', 1)[-1].lower())}(?![a-z0-9_])",
            lowered,
        )
        for relation in governed_relations
    )


@dataclass
class _PythonCapability:
    path: str
    function: str
    calls: set[str]
    game_connection: bool = False
    governed_write: bool = False
    dynamic_write: bool = False
    migration_execution: bool = False


def _scope_aliases(scope: ast.AST) -> set[str]:
    aliases: set[str] = set()
    changed = True
    while changed:
        changed = False
        for node in ast.walk(scope):
            value: ast.AST | None = None
            targets: list[ast.expr] = []
            if isinstance(node, ast.Assign):
                value = node.value
                targets = node.targets
            elif isinstance(node, ast.AnnAssign):
                value = node.value
                targets = [node.target]
            if value is None or not _contains_game_dsn(value, aliases):
                continue
            for target in targets:
                if isinstance(target, ast.Name) and target.id not in aliases:
                    aliases.add(target.id)
                    changed = True
    return aliases


def _scope_capability(
    path: str,
    function: str,
    scope: ast.AST,
    bindings: dict[str, str],
    governed_relations: set[str],
) -> _PythonCapability:
    aliases = _scope_aliases(scope)
    calls = [node for node in ast.walk(scope) if isinstance(node, ast.Call)]
    capability = _PythonCapability(
        path=path,
        function=function,
        calls={_call_name(call).rsplit(".", 1)[-1] for call in calls},
    )
    for call in calls:
        call_name = _call_name(call)
        leaf = call_name.rsplit(".", 1)[-1]
        if call_name in {"PostgresRuntime", "open_runtime"} or call_name.endswith(
            ".PostgresRuntime"
        ):
            capability.game_connection = True
        if call_name in {
            "psycopg.connect",
            "psycopg.Connection.connect",
            "ConnectionPool",
            "AsyncConnectionPool",
        } and _references_game_dsn(call, aliases):
            capability.game_connection = True
        if leaf in {"_apply_migrations", "apply_migrations", "run_migrations"}:
            capability.migration_execution = True
        if (
            leaf
            not in {
                "execute",
                "SQL",
                "Identifier",
                "copy_from",
                "copy",
                "executemany",
            }
            or not call.args
        ):
            continue
        sql = _string_expression(call.args[0], bindings)
        is_write = bool(_PYTHON_WRITE_SQL.search(sql) or _PYTHON_DYNAMIC_WRITE.search(sql))
        if is_write and _sql_targets_governed_relation(sql, governed_relations):
            capability.governed_write = True
        if leaf in {"SQL", "Identifier"} or (is_write and "{}" in sql):
            capability.dynamic_write = True
    return capability


def _source_capabilities(
    path: str, source: str, governed_relations: set[str]
) -> list[_PythonCapability]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    bindings = _executable_string_bindings(tree)
    capabilities = [
        _scope_capability(path, node.name, node, bindings, governed_relations)
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    module_scope = ast.Module(
        body=[
            node
            for node in tree.body
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        ],
        type_ignores=[],
    )
    capabilities.append(
        _scope_capability(path, "<module>", module_scope, bindings, governed_relations)
    )
    return capabilities


def _python_capability_paths(sources: dict[str, str], governed_relations: set[str]) -> set[str]:
    """Close connection/write capabilities over a conservative cross-file call graph."""

    capabilities = [
        capability
        for path, source in sources.items()
        for capability in _source_capabilities(path, source, governed_relations)
    ]
    by_function: dict[str, list[_PythonCapability]] = {}
    for capability in capabilities:
        by_function.setdefault(capability.function, []).append(capability)
    unique_functions = {
        function: rows[0] for function, rows in by_function.items() if len(rows) == 1
    }

    changed = True
    while changed:
        changed = False
        for capability in capabilities:
            callees = [
                unique_functions[call] for call in capability.calls if call in unique_functions
            ]
            for field in [
                "game_connection",
                "governed_write",
                "dynamic_write",
                "migration_execution",
            ]:
                if not getattr(capability, field) and any(
                    getattr(callee, field) for callee in callees
                ):
                    setattr(capability, field, True)
                    changed = True

    return {
        capability.path
        for capability in capabilities
        if capability.game_connection
        or capability.governed_write
        or capability.migration_execution
        or (capability.dynamic_write and capability.game_connection)
    }


def _has_python_game_write_capability(
    source: str, governed_relations: set[str] | None = None
) -> bool:
    """Detect one-file constructible writer capability for focused callers."""

    return bool(_python_capability_paths({"<source>": source}, governed_relations or set()))


def _entrypoint_source(relative: str, source: str, entrypoint: str) -> str:
    """Select exactly one governed Mise task or Python entrypoint body."""

    if relative == ".mise.toml":
        quoted = re.escape(f'[tasks."{entrypoint}"]')
        bare = re.escape(f"[tasks.{entrypoint}]")
        match = re.search(rf"(?m)^(?:{quoted}|{bare})\s*$", source)
        if match is None:
            return ""
        following = re.search(r"(?m)^\[", source[match.end() :])
        end = match.end() + following.start() if following is not None else len(source)
        return source[match.start() : end]

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ""
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and node.name == entrypoint
    ]
    if len(matches) != 1:
        return ""
    return ast.get_source_segment(source, matches[0]) or ""


def _tokens_in_order(tokens: list[str], required: str) -> bool:
    required_tokens = shlex.split(required)
    flattened: list[str] = []
    for token in tokens:
        pieces = shlex.split(token) if any(character.isspace() for character in token) else [token]
        flattened.extend(pieces)
    return any(
        flattened[index : index + len(required_tokens)] == required_tokens
        for index in range(len(flattened) - len(required_tokens) + 1)
    )


def _shell_executable_tokens(source: str) -> list[str]:
    tokens: list[str] = []
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("[tasks."):
            continue
        try:
            tokens.extend(shlex.split(line, comments=True, posix=True))
        except ValueError:
            uncommented = line.split("#", 1)[0]
            tokens.extend(re.findall(r"[A-Za-z0-9_./:+-]+", uncommented))
    return tokens


def _mise_run_values(governed_source: str) -> list[str]:
    try:
        parsed = tomllib.loads(governed_source)
    except tomllib.TOMLDecodeError:
        return []
    tasks = parsed.get("tasks")
    if not isinstance(tasks, dict) or len(tasks) != 1:
        return []
    task = next(iter(tasks.values()))
    if not isinstance(task, dict):
        return []
    run = task.get("run")
    if isinstance(run, str):
        return [run]
    if isinstance(run, list) and all(isinstance(value, str) for value in run):
        return run
    return []


def _command_expression_tokens(node: ast.AST, bindings: dict[str, str]) -> list[str]:
    if isinstance(node, (ast.List, ast.Tuple)):
        return [
            token
            for element in node.elts
            for token in _command_expression_tokens(element, bindings)
        ]
    text = _string_expression(node, bindings)
    return shlex.split(text) if text else []


def _python_executable_command_tokens(source: str) -> list[list[str]]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    bindings = _executable_string_bindings(tree)
    commands: list[list[str]] = []
    for call in [node for node in ast.walk(tree) if isinstance(node, ast.Call)]:
        call_name = _call_name(call)
        leaf = call_name.rsplit(".", 1)[-1]
        if leaf not in {
            "run",
            "Popen",
            "call",
            "check_call",
            "check_output",
            "system",
            "execv",
            "execvp",
            "spawnv",
            "spawnvp",
        }:
            continue
        if not call.args:
            continue
        commands.append(_command_expression_tokens(call.args[0], bindings))
    return commands


def _entrypoint_executes_required_command(
    relative: str, governed_source: str, required: str
) -> bool:
    if relative == ".mise.toml":
        return any(
            _tokens_in_order(_shell_executable_tokens(run), required)
            for run in _mise_run_values(governed_source)
        )
    return any(
        _tokens_in_order(command, required)
        for command in _python_executable_command_tokens(governed_source)
    )


def _verify_authority_ledger_vectors(
    contract: dict[str, Any],
    parsed_rows: list[dict[str, Any]],
    relative: str,
    findings: set[CutoverFinding],
) -> None:
    """Reconstruct the closed prepared-to-active authority chain independently."""

    ledger = _mapping(
        _mapping(contract["schema_epochs"], "schema_epochs")["activation_ledger"],
        "schema_epochs.activation_ledger",
    )
    wire = _mapping(ledger["wire"], "schema_epochs.activation_ledger.wire")
    vectors = _mapping(contract["vectors"], "vectors")
    ledger_rows = [row for row in parsed_rows if row.get("kind") == "valid_authority_ledger"]
    expected_count = _integer(
        vectors["valid_authority_ledger_count"], "vectors.valid_authority_ledger_count"
    )
    expected_states = [
        _string(value, "vectors.required_valid_authority_ledger_states item")
        for value in _list(
            vectors["required_valid_authority_ledger_states"],
            "vectors.required_valid_authority_ledger_states",
        )
    ]
    expected_ids = [
        _string(value, "activation_ledger.wire.vector_ids item")
        for value in _list(wire["vector_ids"], "activation_ledger.wire.vector_ids")
    ]
    observed_ids = [_string(row.get("id"), "authority ledger vector id") for row in ledger_rows]
    observed_states = [
        _string(_mapping(row.get("data"), "authority ledger data").get("state"), "state")
        for row in ledger_rows
    ]
    if (
        len(ledger_rows) != expected_count
        or observed_ids != expected_ids
        or observed_states != expected_states
    ):
        findings.add(
            CutoverFinding(
                "cutover_authority_ledger_identity",
                relative,
                "authority ledger vectors must be the exact ordered prepared-to-active pair",
            )
        )
        return

    try:
        domain = _string(wire["domain_utf8"], "activation ledger domain").encode("utf-8")
        layout = _integer(wire["layout_u32"], "activation ledger layout").to_bytes(4, "big")
        state_tags = _mapping(wire["closed_state_tags"], "activation ledger state tags")
        optional = _mapping(wire["optional_digest32"], "activation ledger optional digest")
        none_tag = _integer(optional["none_tag_u8"], "activation ledger none tag").to_bytes(
            1, "big"
        )
        some_tag = _integer(optional["some_tag_u8"], "activation ledger some tag").to_bytes(
            1, "big"
        )
        state_machine = _rows(ledger["state_machine"], "activation ledger state machine")
        prepared_sha256 = ""
        common_contract_sha256 = ""
        common_reader_sha256 = ""
        for index, (row, expected_state) in enumerate(zip(ledger_rows, state_machine, strict=True)):
            data = _mapping(row["data"], "authority ledger data")
            if set(data) != {
                "ordinal",
                "state",
                "state_tag",
                "schema_epoch",
                "contract_sha256",
                "reader_contract_sha256",
                "predecessor_sha256",
            }:
                raise ValueError("authority ledger data has an open or incomplete shape")
            ordinal = _integer(data["ordinal"], "authority ledger ordinal")
            state = _string(data["state"], "authority ledger state")
            state_tag = _integer(data["state_tag"], "authority ledger state tag")
            schema_epoch = _integer(data["schema_epoch"], "authority ledger schema epoch")
            if (
                ordinal != _integer(expected_state["ordinal"], "expected ledger ordinal")
                or state != _string(expected_state["state"], "expected ledger state")
                or state_tag != _integer(expected_state["state_tag"], "expected ledger state tag")
                or schema_epoch
                != _integer(expected_state["schema_epoch"], "expected ledger schema epoch")
                or state_tags.get(state) != state_tag
            ):
                raise ValueError("authority ledger state identity differs from the closed machine")

            contract_sha256 = _string(data["contract_sha256"], "contract_sha256")
            reader_sha256 = _string(data["reader_contract_sha256"], "reader_contract_sha256")
            contract_digest = bytes.fromhex(contract_sha256)
            reader_digest = bytes.fromhex(reader_sha256)
            if len(contract_digest) != 32 or len(reader_digest) != 32:
                raise ValueError("authority ledger contract digests must be exactly 32 bytes")
            predecessor = data["predecessor_sha256"]
            if predecessor is None:
                predecessor_bytes = none_tag
            else:
                predecessor_text = _string(predecessor, "predecessor_sha256")
                predecessor_digest = bytes.fromhex(predecessor_text)
                if len(predecessor_digest) != 32:
                    raise ValueError("authority ledger predecessor must be exactly 32 bytes")
                predecessor_bytes = some_tag + predecessor_digest

            encoded = b"".join(
                [
                    domain,
                    layout,
                    ordinal.to_bytes(2, "big"),
                    state_tag.to_bytes(1, "big"),
                    schema_epoch.to_bytes(2, "big"),
                    contract_digest,
                    reader_digest,
                    predecessor_bytes,
                ]
            )
            encoded_sha256 = hashlib.sha256(encoded).hexdigest()
            if (
                _string(row["expected_hex"], "authority ledger expected_hex") != encoded.hex()
                or _string(row["expected_sha256"], "authority ledger expected_sha256")
                != encoded_sha256
            ):
                raise ValueError(
                    "authority ledger expected bytes or digest differ from reconstruction"
                )
            if index == 0:
                if predecessor is not None:
                    raise ValueError("prepared authority row must have no predecessor")
                prepared_sha256 = encoded_sha256
                common_contract_sha256 = contract_sha256
                common_reader_sha256 = reader_sha256
            elif (
                predecessor != prepared_sha256
                or contract_sha256 != common_contract_sha256
                or reader_sha256 != common_reader_sha256
            ):
                raise ValueError(
                    "rust_active authority row must bind the exact prepared row and contracts"
                )
    except (KeyError, OverflowError, RustPersistenceCutoverRefusal, ValueError) as error:
        findings.add(CutoverFinding("cutover_authority_ledger_identity", relative, str(error)))


def _verify_vectors(contract: dict[str, Any], root: Path, findings: set[CutoverFinding]) -> None:
    bounds = _mapping(contract["bounds"], "bounds")
    vectors = _mapping(contract["vectors"], "vectors")
    relative = _string(vectors["path"], "vectors.path")
    path = root / relative
    if not path.is_file():
        findings.add(
            CutoverFinding("missing_cutover_vectors", relative, "language-neutral vectors absent")
        )
        return

    payload = path.read_bytes()
    max_bytes = _integer(bounds["vector_bytes"], "bounds.vector_bytes")
    if len(payload) > max_bytes:
        findings.add(
            CutoverFinding(
                "cutover_vectors_too_large",
                relative,
                f"{len(payload)} bytes exceeds {max_bytes}",
            )
        )
        return
    actual_digest = hashlib.sha256(payload).hexdigest()
    expected_digest = _string(vectors["sha256"], "vectors.sha256")
    if actual_digest != expected_digest:
        findings.add(
            CutoverFinding(
                "cutover_vector_digest",
                relative,
                f"expected {expected_digest}; got {actual_digest}",
            )
        )
        return

    lines = payload.splitlines()
    max_rows = _integer(bounds["vector_rows"], "bounds.vector_rows")
    expected_rows = _integer(vectors["rows"], "vectors.rows")
    if not lines or len(lines) > max_rows or len(lines) != expected_rows:
        findings.add(
            CutoverFinding(
                "cutover_vector_count",
                relative,
                f"expected {expected_rows} rows within bound {max_rows}; got {len(lines)}",
            )
        )
        return

    parsed_rows: list[dict[str, Any]] = []
    try:
        for index, line in enumerate(lines):
            if len(line) > _integer(bounds["vector_line_bytes"], "bounds.vector_line_bytes"):
                raise RustPersistenceCutoverRefusal(
                    "invalid_vectors", f"vectors row {index} exceeds the line bound"
                )
            row = _mapping(json.loads(line), f"vectors row {index}")
            parsed_rows.append(row)
    except (UnicodeDecodeError, json.JSONDecodeError, RustPersistenceCutoverRefusal) as error:
        findings.add(CutoverFinding("invalid_cutover_vectors", relative, str(error)))
        return
    expected_kinds = [
        _string(value, "vectors.required_kinds item")
        for value in _list(vectors["required_kinds"], "vectors.required_kinds")
    ]
    kinds = [_string(row.get("kind"), "vector kind") for row in parsed_rows]
    if sorted(set(kinds)) != sorted(expected_kinds):
        findings.add(
            CutoverFinding(
                "cutover_vector_kinds",
                relative,
                f"expected {sorted(expected_kinds)!r}; got {sorted(set(kinds))!r}",
            )
        )
        return
    kind_counts = {kind: kinds.count(kind) for kind in expected_kinds}
    if kind_counts != {
        "valid_scalar": 18,
        "valid_row": 14,
        "valid_foundation": 1,
        "valid_checkpoint": 1,
        "valid_empty_family": 1,
        "valid_authority_ledger": 2,
        "refusal": 19,
    }:
        findings.add(
            CutoverFinding(
                "cutover_vector_kind_counts",
                relative,
                f"exact vector kind counts changed: {kind_counts!r}",
            )
        )
        return
    exact_shapes = {
        "valid_scalar": {"id", "kind", "codec", "input", "expected_hex"},
        "valid_row": {
            "id",
            "kind",
            "codec",
            "data",
            "expected_key_hex",
            "expected_payload_hex",
            "expected_hex",
            "expected_sha256",
        },
        "valid_foundation": {
            "id",
            "kind",
            "data",
            "expected_content_bundle_hex",
            "expected_hex",
            "expected_sha256",
        },
        "valid_checkpoint": {"id", "kind", "data", "expected_hex", "expected_sha256"},
        "valid_empty_family": {
            "id",
            "kind",
            "data",
            "expected_hex",
            "expected_sha256",
        },
        "valid_authority_ledger": {
            "id",
            "kind",
            "data",
            "expected_hex",
            "expected_sha256",
        },
    }
    refusal_shapes = [
        {"id", "kind", "operation", "input", "expected_code"},
        {"id", "kind", "operation", "codec", "input", "expected_code"},
        {"id", "kind", "operation", "producer", "input", "expected_code"},
    ]
    for row in parsed_rows:
        kind = _string(row.get("kind"), "vector kind")
        valid_shape = (
            set(row) in refusal_shapes if kind == "refusal" else set(row) == exact_shapes[kind]
        )
        if not valid_shape:
            findings.add(
                CutoverFinding(
                    "cutover_vector_shape",
                    relative,
                    f"{row.get('id')!r} has an open or incomplete {kind!r} shape",
                )
            )
            return
    refusal_rows = [row for row in parsed_rows if row.get("kind") == "refusal"]
    observed_operations = {
        _string(row.get("operation"), "refusal operation") for row in refusal_rows
    }
    expected_operations = {
        _string(value, "required refusal operation")
        for value in _list(
            vectors["required_refusal_operations"], "vectors.required_refusal_operations"
        )
    }
    observed_codes = {
        _string(row.get("expected_code"), "refusal expected_code") for row in refusal_rows
    }
    expected_codes = {
        _string(value, "required refusal code")
        for value in _list(vectors["required_refusal_codes"], "vectors.required_refusal_codes")
    }
    if observed_operations != expected_operations or observed_codes != expected_codes:
        findings.add(
            CutoverFinding(
                "cutover_vector_refusal_vocabulary",
                relative,
                "refusal operation and typed error-code vocabularies must be exact",
            )
        )
        return
    ids = [_string(row.get("id"), "vector id") for row in parsed_rows]
    if len(ids) != len(set(ids)):
        findings.add(CutoverFinding("invalid_cutover_vectors", relative, "ids must be unique"))
        return
    _verify_authority_ledger_vectors(contract, parsed_rows, relative, findings)
    semantic = _mapping(contract["semantic_rows"], "semantic_rows")
    scalar_codecs = _mapping(semantic["scalar_codecs"], "semantic_rows.scalar_codecs")
    stable_bsl = _mapping(
        scalar_codecs["stable_bsl_value_v1"],
        "semantic_rows.scalar_codecs.stable_bsl_value_v1",
    )
    stable_tags = _mapping(
        stable_bsl["closed_tags"],
        "semantic_rows.scalar_codecs.stable_bsl_value_v1.closed_tags",
    )
    _verify_valid_scalars(parsed_rows, relative, findings, stable_tags)
    _verify_stable_bsl_references(parsed_rows, relative, findings, stable_tags)
    _verify_material_valid_rows(parsed_rows, relative, findings, stable_tags)
    scalar_ids = set(scalar_codecs)
    row_codec_ids = {
        _string(row.get("id"), "row codec id")
        for row in _rows(semantic["row_codecs"], "semantic_rows.row_codecs")
    }
    required_row_codecs = [
        _string(value, "vectors.required_valid_row_codecs item")
        for value in _list(
            vectors["required_valid_row_codecs"], "vectors.required_valid_row_codecs"
        )
    ]
    if required_row_codecs != [
        _string(row.get("id"), "row codec id")
        for row in _rows(semantic["row_codecs"], "semantic_rows.row_codecs")
    ]:
        findings.add(
            CutoverFinding(
                "cutover_vector_row_coverage",
                relative,
                "required valid-row codecs must equal the contract row-codec order",
            )
        )
        return
    valid_row_codecs = [
        _string(row.get("codec"), "valid-row codec")
        for row in parsed_rows
        if row.get("kind") == "valid_row"
    ]
    if valid_row_codecs != required_row_codecs or len(valid_row_codecs) != _integer(
        vectors["valid_row_count"], "vectors.valid_row_count"
    ):
        findings.add(
            CutoverFinding(
                "cutover_vector_row_coverage",
                relative,
                "every row codec requires exactly one ordered valid-row vector",
            )
        )
        return
    producer_ids = {
        _string(row.get("id"), "producer id")
        for row in _rows(semantic["producer_inventory"], "semantic_rows.producer_inventory")
    }
    for row in parsed_rows:
        kind = _string(row.get("kind"), "vector kind")
        codec = row.get("codec")
        if codec is not None and codec not in scalar_ids | row_codec_ids:
            findings.add(
                CutoverFinding(
                    "cutover_vector_codec",
                    relative,
                    f"{row['id']} references undefined codec {codec!r}",
                )
            )
        if kind == "valid_row":
            try:
                key_hex = _string(row.get("expected_key_hex"), "expected_key_hex")
                payload_hex = _string(row.get("expected_payload_hex"), "expected_payload_hex")
                composite_hex = _string(row.get("expected_hex"), "expected_hex")
                expected_sha256 = _string(row.get("expected_sha256"), "expected_sha256")
                if composite_hex != key_hex + payload_hex:
                    raise ValueError("composite bytes are not key bytes followed by payload bytes")
                composite = bytes.fromhex(composite_hex)
                if hashlib.sha256(composite).hexdigest() != expected_sha256:
                    raise ValueError("composite SHA-256 does not match exact bytes")
            except (RustPersistenceCutoverRefusal, ValueError) as error:
                findings.add(
                    CutoverFinding("invalid_cutover_vector_row", relative, f"{row['id']}: {error}")
                )
        producer = row.get("producer")
        if producer is not None and producer not in producer_ids:
            findings.add(
                CutoverFinding(
                    "cutover_vector_producer",
                    relative,
                    f"{row['id']} references undefined producer {producer!r}",
                )
            )
    if not any(
        row.get("id") == "refuse-resolve-tick-postgresql-bigint-overflow"
        and row.get("kind") == "refusal"
        and row.get("operation") == "prepare_committed_tick"
        and row.get("input") == {"resolve_tick": "9223372036854775808"}
        and row.get("expected_code") == "resolve_tick_sql_range"
        for row in parsed_rows
    ):
        findings.add(
            CutoverFinding(
                "cutover_vector_tick_bound",
                relative,
                "PostgreSQL BIGINT overflow refusal vector is absent or weakened",
            )
        )


def _governed_relations(contract: dict[str, Any]) -> set[str]:
    """Derive the complete relation vocabulary independently scanned for writes."""

    relations: set[str] = set()
    foundation = _mapping(contract["foundation"], "foundation")
    relations.add(_string(foundation["relation"], "foundation.relation"))
    artifact = _mapping(foundation["content_bundle"], "foundation.content_bundle")[
        "artifact_resolution"
    ]
    relations.add(
        _string(_mapping(artifact, "artifact_resolution")["relation"], "artifact relation")
    )

    storage = _mapping(contract["storage"], "storage")
    relations.add(_string(storage["marker"], "storage.marker"))
    marker = _mapping(storage["public_marker_disposition"], "public_marker_disposition")
    relations.update(
        {
            _string(marker["source"], "marker source"),
            _string(marker["destination"], "marker destination"),
        }
    )
    for row in _rows(storage["metadata_disposition"]["relations"], "metadata relations"):
        relations.add(_string(row["relation"], "metadata relation"))
    for row in _rows(storage["normalized_child_relations"], "normalized child relations"):
        relations.add(_string(row["relation"], "normalized child relation"))

    semantic = _mapping(contract["semantic_rows"], "semantic_rows")
    for row in _rows(semantic["row_codecs"], "row_codecs"):
        relations.add(_string(row["typed_relation"], "row codec typed_relation"))

    boundary = _mapping(contract["reader_boundary"], "reader_boundary")
    for row in _rows(boundary["projection_relations"], "projection_relations"):
        relations.add(_string(row["legacy_relation"], "legacy_relation"))
        typed = _string(row["typed_relation"], "typed_relation")
        if typed != "none":
            relations.add(typed)
    for row in _rows(boundary["view_projections"], "view_projections"):
        relations.add(_string(row["name"], "view name"))
        relations.update(
            _string(value, "view source") for value in _list(row["sources"], "sources")
        )

    disposition = _mapping(contract["data_disposition"], "data_disposition")
    for field in [
        "whole_table_drop_after_parity",
        "replace_then_drop_after_ordered_count_and_hash_parity",
        "preserve_until_zero_row_census_then_drop_without_typed_replacement",
        "identity_columns_only_until_lossless_destination_exists",
    ]:
        relations.update(_string(value, field) for value in _list(disposition[field], field))
    written = _mapping(
        disposition["python_written_relation_disposition"],
        "python_written_relation_disposition",
    )
    for field, values in written.items():
        if field != "law":
            relations.update(_string(value, field) for value in _list(values, field))
    return relations


def verify_cutover_contract(contract: dict[str, Any], root: Path) -> list[CutoverFinding]:
    """Return the exact sorted repository violations for one validated contract."""

    validate_cutover_contract(contract)
    findings: set[CutoverFinding] = set()
    authority = _mapping(contract["authority"], "authority")
    governed_relations = _governed_relations(contract)
    _verify_vectors(contract, root, findings)

    for field, code in [
        ("composition_module", "missing_runtime_module"),
        ("composition_binary", "missing_runtime_binary"),
    ]:
        relative = _string(authority[field], f"authority.{field}")
        if not (root / relative).is_file():
            findings.add(CutoverFinding(code, relative, "required production root is absent"))

    absorbed = _string(authority["absorbed_binary"], "authority.absorbed_binary")
    if (root / absorbed).exists():
        findings.add(
            CutoverFinding(
                "second_migrator_command", absorbed, "must be absorbed by babylon-runtime"
            )
        )

    tick_writer_relative = "rust/crates/babylon-persistence/src/committed_tick_writer.rs"
    if "marker.resolve_tick = 0" in _text(root, tick_writer_relative):
        findings.add(
            CutoverFinding(
                "synthetic_tick_zero_source",
                tick_writer_relative,
                "foundation hydration must not depend on a tick-zero commit marker",
            )
        )
    old_tick_zero_law = "rust/crates/babylon-persistence/tests/committed_tick_writer_v1_contract.rs"
    if "opaque_checkpoint_hydration_uses_only_the_tick_zero_foundation" in _text(
        root, old_tick_zero_law
    ):
        findings.add(
            CutoverFinding(
                "synthetic_tick_zero_source",
                old_tick_zero_law,
                "the old executable tick-zero requirement must be inverted",
            )
        )

    for package in authority["prohibited_owners"]:
        manifest = f"rust/crates/{package}/Cargo.toml"
        if "babylon-persistence" in _text(root, manifest):
            findings.add(
                CutoverFinding(
                    "wrong_dependency_direction",
                    manifest,
                    "tick adjudication and Bevy must not own persistence",
                )
            )

    boundary = _mapping(contract["reader_boundary"], "reader_boundary")
    reader_relative = _string(boundary["contract"], "reader_boundary.contract")
    reader_path = root / reader_relative
    if not reader_path.is_file():
        findings.add(
            CutoverFinding("missing_reader_contract", reader_relative, "stopped train is split")
        )
    elif hashlib.sha256(reader_path.read_bytes()).hexdigest() != boundary["sha256"]:
        findings.add(
            CutoverFinding("reader_contract_digest", reader_relative, "digest does not match")
        )
    else:
        try:
            reader_documents = list(
                yaml.load_all(reader_path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
            )
            if len(reader_documents) != 1:
                raise RustPersistenceCutoverRefusal(
                    "invalid_reader_contract", "reader contract must contain one document"
                )
            reader_contract = _mapping(reader_documents[0], "reader contract")
            reader_views = {
                _string(row.get("canonical_relation"), "reader current view")
                for row in _rows(reader_contract.get("current_views"), "reader current_views")
            }
            boundary_views = {
                _string(row.get("name"), "boundary view")
                for row in _rows(boundary.get("view_projections"), "boundary view_projections")
            }
            if (
                len(reader_views)
                != _integer(boundary.get("epoch7_views"), "reader_boundary.epoch7_views")
                or not boundary_views <= reader_views
            ):
                findings.add(
                    CutoverFinding(
                        "reader_view_crosswalk",
                        reader_relative,
                        "typed future projections must be a subset of the exact current-view authority",
                    )
                )
        except (UnicodeError, yaml.YAMLError, RustPersistenceCutoverRefusal) as error:
            findings.add(CutoverFinding("invalid_reader_contract", reader_relative, str(error)))

    storage_relative = "rust/crates/babylon-persistence/src/committed_tick_storage.rs"
    storage_source = _text(root, storage_relative)
    storage = _mapping(contract["storage"], "storage")
    for relation in storage["prohibited_final_relations"]:
        if relation in storage_source:
            findings.add(CutoverFinding("opaque_storage_survivor", storage_relative, str(relation)))

    python = _mapping(contract["python_authority"], "python_authority")
    python_sources: dict[str, str] = {}
    for scan_root in ["src/babylon", "tools"]:
        base = root / scan_root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            python_sources[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8")
    capability_paths = _python_capability_paths(python_sources, governed_relations)
    inventoried_paths: set[str] = set()
    for row in _rows(python["must_delete"], "python_authority.must_delete"):
        relative = _string(row["path"], "must_delete.path")
        inventoried_paths.add(relative)
        source = _text(root, relative)
        for value in _list(row["symbols"], "must_delete.symbols"):
            symbol = _string(value, "must_delete.symbol")
            if _python_symbol_survives(source, symbol):
                findings.add(CutoverFinding("python_authority_survivor", relative, symbol))
        if relative in capability_paths:
            findings.add(
                CutoverFinding(
                    "python_write_capability_survivor",
                    relative,
                    "game-managed PostgreSQL write capability remains constructible",
                )
            )

    for row in _rows(
        python["must_replace_entrypoints_without_python_adapter"],
        "python_authority.must_replace_entrypoints_without_python_adapter",
    ):
        relative = _string(row["path"], "must_replace_entrypoints_without_python_adapter.path")
        inventoried_paths.add(relative)
        source = _text(root, relative)
        entrypoint = _string(
            row["entrypoint"], "must_replace_entrypoints_without_python_adapter.entrypoint"
        )
        governed_source = _entrypoint_source(relative, source, entrypoint)
        if not governed_source:
            findings.add(CutoverFinding("missing_replacement_entrypoint", relative, entrypoint))
            continue
        required = _string(row["required_rust_command"], "required_rust_command")
        if not _entrypoint_executes_required_command(relative, governed_source, required):
            findings.add(
                CutoverFinding("missing_rust_entrypoint", relative, f"{entrypoint}: {required}")
            )
        if "prohibited_fragments" in row:
            for value in _list(row["prohibited_fragments"], "prohibited_fragments"):
                fragment = _string(value, "prohibited_fragment")
                if fragment in governed_source:
                    findings.add(
                        CutoverFinding(
                            "python_sql_authority_survivor",
                            relative,
                            f"{entrypoint}: {fragment}",
                        )
                    )

    for relative in sorted(capability_paths):
        if relative in inventoried_paths or relative in _RETAINED_SQL_PERIPHERY:
            continue
        findings.add(
            CutoverFinding(
                "uncensused_python_write_authority",
                relative,
                "write capability is outside the exact retirement inventory",
            )
        )

    return sorted(findings)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--contract", default="contracts/rust_persistence_cutover_v1.yaml", type=Path
    )
    parser.add_argument("--root", default=Path.cwd(), type=Path)
    args = parser.parse_args()
    try:
        contract = load_cutover_contract(args.contract)
        findings = verify_cutover_contract(contract, args.root.resolve())
    except (OSError, UnicodeError, yaml.YAMLError, RustPersistenceCutoverRefusal) as error:
        print(f"Rust persistence cutover REFUSED: {error}")
        return 2
    if findings:
        for finding in findings:
            print(f"{finding.code}: {finding.path}: {finding.detail}")
        return 1
    print("Rust persistence cutover contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
