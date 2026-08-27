#!/usr/bin/env python3
"""Independently verify the bounded CommittedTickEnvelopeV1 contract corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml

DOMAIN = b"babylon.committed-tick-envelope.v1\0"
CLAIM_DOMAIN = b"babylon.tick-commit-claim\0"
MAX_U64 = (1 << 64) - 1
MAX_SCHEMA_BYTES = 65_536
MAX_VECTOR_ROWS = 64
MAX_VECTOR_LINE_BYTES = 16_384
MAX_VECTOR_OBJECT_FIELDS = 64
MAX_VECTOR_FAMILY_ROWS = 64
MAX_AGGREGATE_ROWS = 1_048_576
MAX_FAMILY_BODY_BYTES = 67_108_864
FIXED_ENVELOPE_BYTES = 209
MAX_ENVELOPE_BYTES = 536_871_121
FAMILIES = (
    ("graph", 0x10),
    ("state", 0x11),
    ("event", 0x12),
    ("subsystem", 0x13),
    ("conservation", 0x14),
    ("boundary_flow", 0x15),
    ("checkpoint", 0x16),
    ("archive_dirty_receipt", 0x17),
)
REQUIRED_VECTOR_FAMILIES = {"envelope", "mutation", "retry", "refusal", "bound"}
REQUIRED_RETRY_OUTCOMES = {
    "idempotent",
    "key_mismatch",
    "content_identity_mismatch",
    "whole_payload_mismatch",
}
COMPILED_CONSTANTS = {
    "domain_ascii_nul": "babylon.committed-tick-envelope.v1",
    "layout_u32": 1,
    "claim_tag_u8": 1,
    "claim_bytes": 93,
    "family_count": 8,
    "row_length_field_bytes": 4,
    "fixed_envelope_bytes": FIXED_ENVELOPE_BYTES,
    "max_envelope_bytes": MAX_ENVELOPE_BYTES,
}
COMPILED_BOUNDS = {
    "schema_bytes": MAX_SCHEMA_BYTES,
    "vector_rows": MAX_VECTOR_ROWS,
    "vector_line_bytes": MAX_VECTOR_LINE_BYTES,
    "vector_object_fields": MAX_VECTOR_OBJECT_FIELDS,
    "vector_family_rows": MAX_VECTOR_FAMILY_ROWS,
    "aggregate_rows": MAX_AGGREGATE_ROWS,
    "family_body_bytes": MAX_FAMILY_BODY_BYTES,
}
COMPILED_LAYOUTS = {
    "claim_link_v1": {
        "owning_type": "babylon_persistence::tick_commit_claim::TickCommitClaimV1",
        "fields": ["claim_tag_u8_1", "claim_length_u32_93", "exact_claim_bytes93"],
    },
    "row_v1": {
        "fields": [
            "key_length_u32",
            "nonempty_exact_key_bytes",
            "payload_length_u32",
            "exact_payload_bytes",
        ],
        "order": "strict ascending exact key bytes within family",
        "duplicate_keys": "prohibited",
    },
    "family_section_v1": {
        "fields": [
            "family_tag_u8",
            "row_count_u32",
            "body_length_u32",
            "exact_ordered_rows",
        ],
        "empty_encoding": "tag plus zero row count plus zero body length",
    },
    "committed_tick_envelope_v1": {
        "fields": [
            "domain_ascii_nul",
            "layout_u32_1",
            "claim_link_v1",
            "graph_section",
            "state_section",
            "event_section",
            "subsystem_section",
            "conservation_section",
            "boundary_flow_section",
            "checkpoint_section",
            "archive_dirty_receipt_section",
        ],
        "key": ["campaign_id", "resolve_tick"],
    },
}
COMPILED_RETRY = {
    "different_key": "key_mismatch",
    "same_key_different_tick_content_hash": "content_identity_mismatch",
    "same_claim_same_exact_envelope_bytes": "idempotent",
    "same_claim_different_exact_envelope_bytes": "whole_payload_mismatch",
}


class EnvelopeContractRefusal(ValueError):
    """One typed independent-verifier refusal."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _bounded_file_bytes(path: Path, maximum: int, code: str) -> bytes:
    try:
        size = path.stat().st_size
    except OSError as error:
        raise EnvelopeContractRefusal("file_read", str(path)) from error
    if size > maximum:
        raise EnvelopeContractRefusal(code, str(size))
    try:
        return path.read_bytes()
    except OSError as error:
        raise EnvelopeContractRefusal("file_read", str(path)) from error


def load_contract(path: Path) -> dict[str, Any]:
    """Load one bounded YAML mapping."""
    raw = _bounded_file_bytes(path, MAX_SCHEMA_BYTES, "schema_too_large")
    try:
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError as error:
        raise EnvelopeContractRefusal("invalid_schema", str(path)) from error
    if not isinstance(loaded, dict):
        raise EnvelopeContractRefusal("invalid_schema", "root mapping")
    return loaded


def load_vectors(path: Path) -> list[dict[str, Any]]:
    """Load bounded JSONL rows without an unbounded whole-file read."""
    maximum = MAX_VECTOR_ROWS * (MAX_VECTOR_LINE_BYTES + 1)
    raw = _bounded_file_bytes(path, maximum, "vectors_too_large")
    lines = raw.splitlines()
    if len(lines) > MAX_VECTOR_ROWS:
        raise EnvelopeContractRefusal("too_many_rows", str(len(lines)))
    rows: list[dict[str, Any]] = []
    for index in range(MAX_VECTOR_ROWS):
        if index >= len(lines):
            break
        line = lines[index]
        if not line or len(line) > MAX_VECTOR_LINE_BYTES:
            raise EnvelopeContractRefusal("invalid_line_length", str(index + 1))
        try:
            row = json.loads(line, object_pairs_hook=_unique_json_object)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise EnvelopeContractRefusal("invalid_json", str(index + 1)) from error
        if not isinstance(row, dict):
            raise EnvelopeContractRefusal("vector_row_shape", str(index + 1))
        rows.append(row)
    return rows


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    if len(pairs) > MAX_VECTOR_OBJECT_FIELDS:
        raise EnvelopeContractRefusal("json_object_fields", str(len(pairs)))
    result: dict[str, Any] = {}
    for index in range(MAX_VECTOR_OBJECT_FIELDS):
        if index >= len(pairs):
            break
        key, value = pairs[index]
        if key in result:
            raise EnvelopeContractRefusal("duplicate_json_key", key)
        result[key] = value
    return result


def _verify_compiled_contract(contract: dict[str, Any]) -> None:
    if contract.get("meta") != {
        "contract": "CommittedTickEnvelopeV1",
        "version": 1,
        "issue": "PER-20",
        "byte_order": "big-endian",
        "digest": "SHA-256 diagnostic; exact bytes govern retry equality",
    }:
        raise EnvelopeContractRefusal("compiled_contract_drift", "meta")
    if contract.get("constants") != COMPILED_CONSTANTS:
        raise EnvelopeContractRefusal("compiled_contract_drift", "constants")
    if contract.get("bounds") != COMPILED_BOUNDS:
        raise EnvelopeContractRefusal("compiled_contract_drift", "bounds")
    if contract.get("layouts") != COMPILED_LAYOUTS:
        raise EnvelopeContractRefusal("compiled_contract_drift", "layouts")
    expected_families = [{"name": name, "tag_u8": tag} for name, tag in FAMILIES]
    if contract.get("row_families") != expected_families:
        raise EnvelopeContractRefusal("compiled_contract_drift", "row_families")
    retry = contract.get("retry_semantics", {}).get("requested_against_existing")
    if retry != COMPILED_RETRY:
        raise EnvelopeContractRefusal("compiled_contract_drift", "retry_semantics")
    if contract.get("production_decoder") != "prohibited":
        raise EnvelopeContractRefusal("compiled_contract_drift", "production_decoder")
    required = contract.get("vector_families", {}).get("required")
    if not isinstance(required, list) or set(required) != REQUIRED_VECTOR_FAMILIES:
        raise EnvelopeContractRefusal("compiled_contract_drift", "vector_families")


def _validated_rows(vectors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(vectors) > MAX_VECTOR_ROWS:
        raise EnvelopeContractRefusal("too_many_rows", str(len(vectors)))
    rows = vectors[:MAX_VECTOR_ROWS]
    seen_ids: set[str] = set()
    for index in range(MAX_VECTOR_ROWS):
        if index >= len(rows):
            break
        row = rows[index]
        row_id = row.get("id")
        if (
            set(row) != {"id", "kind", "data"}
            or not isinstance(row_id, str)
            or not row_id
            or not isinstance(row.get("kind"), str)
            or not isinstance(row.get("data"), dict)
        ):
            raise EnvelopeContractRefusal("vector_row_shape", str(index + 1))
        if row_id in seen_ids:
            raise EnvelopeContractRefusal("duplicate_vector_id", row_id)
        seen_ids.add(row_id)
    return rows


def _campaign_bytes(value: object) -> bytes:
    if not isinstance(value, str) or len(value.encode("utf-8")) != 36:
        raise EnvelopeContractRefusal("invalid_campaign_id", "length")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as error:
        raise EnvelopeContractRefusal("invalid_campaign_id", "syntax") from error
    if str(parsed) != value:
        raise EnvelopeContractRefusal("invalid_campaign_id", "canonical text")
    return parsed.bytes


def _u64_bytes(value: object) -> bytes:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > MAX_U64:
        raise EnvelopeContractRefusal("invalid_resolve_tick", str(value))
    return value.to_bytes(8, "big")


def _digest32(value: object) -> bytes:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value:
        raise EnvelopeContractRefusal("invalid_tick_content_hash", "text")
    try:
        digest = bytes.fromhex(value)
    except ValueError as error:
        raise EnvelopeContractRefusal("invalid_tick_content_hash", "hex") from error
    if len(digest) != 32:
        raise EnvelopeContractRefusal("invalid_tick_content_hash", "length")
    return digest


def _compose_claim(data: dict[str, Any]) -> bytes:
    claim = b"".join(
        (
            CLAIM_DOMAIN,
            (1).to_bytes(4, "big"),
            b"\x01",
            _campaign_bytes(data.get("campaign_id")),
            b"\x02",
            _u64_bytes(data.get("resolve_tick")),
            b"\x03",
            (1).to_bytes(4, "big"),
            _digest32(data.get("tick_content_hash_hex")),
        )
    )
    if len(claim) != 93:
        raise EnvelopeContractRefusal("claim_size", str(len(claim)))
    return claim


def _hex_bytes(value: object, field: str, allow_empty: bool) -> bytes:
    if (
        not isinstance(value, str)
        or value.lower() != value
        or len(value) % 2 != 0
        or len(value) > MAX_VECTOR_LINE_BYTES
        or (not allow_empty and not value)
    ):
        raise EnvelopeContractRefusal("invalid_row_hex", field)
    try:
        return bytes.fromhex(value)
    except ValueError as error:
        raise EnvelopeContractRefusal("invalid_row_hex", field) from error


def _compose_family(name: str, tag: int, rows: object) -> tuple[bytes, int]:
    if not isinstance(rows, list) or len(rows) > MAX_VECTOR_FAMILY_ROWS:
        raise EnvelopeContractRefusal("family_rows", name)
    body = bytearray()
    previous_key: bytes | None = None
    for index in range(MAX_VECTOR_FAMILY_ROWS):
        if index >= len(rows):
            break
        row = rows[index]
        if not isinstance(row, dict) or set(row) != {"key_hex", "payload_hex"}:
            raise EnvelopeContractRefusal("row_shape", f"{name}[{index}]")
        key = _hex_bytes(row.get("key_hex"), f"{name}[{index}].key", False)
        payload = _hex_bytes(row.get("payload_hex"), f"{name}[{index}].payload", True)
        if previous_key is not None and key == previous_key:
            raise EnvelopeContractRefusal("duplicate_row_key", f"{name}[{index}]")
        if previous_key is not None and key < previous_key:
            raise EnvelopeContractRefusal("row_order", f"{name}[{index}]")
        previous_key = key
        body.extend(len(key).to_bytes(4, "big"))
        body.extend(key)
        body.extend(len(payload).to_bytes(4, "big"))
        body.extend(payload)
        if len(body) > MAX_FAMILY_BODY_BYTES:
            raise EnvelopeContractRefusal("batch_bytes", name)
    section = bytearray((tag,))
    section.extend(len(rows).to_bytes(4, "big"))
    section.extend(len(body).to_bytes(4, "big"))
    section.extend(body)
    return bytes(section), len(rows)


def compose_envelope(data: dict[str, Any]) -> bytes:
    """Reconstruct exact envelope bytes from semantic vector inputs."""
    families = data.get("families")
    expected_order = tuple(name for name, _tag in FAMILIES)
    if not isinstance(families, dict) or set(families) != set(expected_order):
        raise EnvelopeContractRefusal("row_family_shape", "exact eight families")
    if tuple(families) != expected_order:
        raise EnvelopeContractRefusal("row_family_order", "exact eight families")
    claim = _compose_claim(data)
    output = bytearray(DOMAIN)
    output.extend((1).to_bytes(4, "big"))
    output.append(0x01)
    output.extend((93).to_bytes(4, "big"))
    output.extend(claim)
    total_rows = 0
    for index in range(len(FAMILIES)):
        name, tag = FAMILIES[index]
        section, row_count = _compose_family(name, tag, families[name])
        total_rows += row_count
        if total_rows > MAX_AGGREGATE_ROWS:
            raise EnvelopeContractRefusal("aggregate_rows", str(total_rows))
        output.extend(section)
    if len(output) > MAX_ENVELOPE_BYTES:
        raise EnvelopeContractRefusal("envelope_bytes", str(len(output)))
    return bytes(output)


def validate_bounds(row_counts: object, batch_body_bytes: object) -> int:
    """Validate the allocation-free cumulative production bounds."""
    if (
        not isinstance(row_counts, list)
        or not isinstance(batch_body_bytes, list)
        or len(row_counts) != len(FAMILIES)
        or len(batch_body_bytes) != len(FAMILIES)
    ):
        raise EnvelopeContractRefusal("bound_shape", "eight counts and sizes")
    total_rows = 0
    total_body = 0
    for index in range(len(FAMILIES)):
        rows = row_counts[index]
        body = batch_body_bytes[index]
        name, _tag = FAMILIES[index]
        if isinstance(rows, bool) or not isinstance(rows, int) or rows < 0:
            raise EnvelopeContractRefusal("bound_shape", f"{name}.rows")
        if isinstance(body, bool) or not isinstance(body, int) or body < 0:
            raise EnvelopeContractRefusal("bound_shape", f"{name}.body")
        if body > MAX_FAMILY_BODY_BYTES:
            raise EnvelopeContractRefusal("batch_bytes", name)
        if body < rows * 9 or (rows == 0 and body != 0):
            raise EnvelopeContractRefusal("batch_shape", name)
        total_rows += rows
        total_body += body
    if total_rows > MAX_AGGREGATE_ROWS:
        raise EnvelopeContractRefusal("aggregate_rows", str(total_rows))
    envelope_bytes = FIXED_ENVELOPE_BYTES + total_body
    if envelope_bytes > MAX_ENVELOPE_BYTES:
        raise EnvelopeContractRefusal("envelope_bytes", str(envelope_bytes))
    return envelope_bytes


def _reference(envelopes: dict[str, dict[str, Any]], value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, str) or value not in envelopes:
        raise EnvelopeContractRefusal("missing_vector_reference", field)
    return envelopes[value]


def _retry_result(requested: dict[str, Any], existing: dict[str, Any]) -> str:
    requested_bytes = compose_envelope(requested)
    existing_bytes = compose_envelope(existing)
    requested_key = (requested["campaign_id"], requested["resolve_tick"])
    existing_key = (existing["campaign_id"], existing["resolve_tick"])
    if requested_key != existing_key:
        return "key_mismatch"
    if requested["tick_content_hash_hex"] != existing["tick_content_hash_hex"]:
        return "content_identity_mismatch"
    if requested_bytes == existing_bytes:
        return "idempotent"
    return "whole_payload_mismatch"


def _verify_envelope(row: dict[str, Any]) -> str | None:
    data = row["data"]
    canonical = compose_envelope(data)
    if canonical.hex() != data.get("canonical_hex"):
        return f"{row['id']}: canonical bytes mismatch"
    if hashlib.sha256(canonical).hexdigest() != data.get("sha256_hex"):
        return f"{row['id']}: SHA-256 mismatch"
    return None


def _verify_refusal(row: dict[str, Any]) -> str | None:
    data = row["data"]
    if data.get("operation") != "compose_envelope":
        return f"{row['id']}: unknown refusal operation"
    try:
        compose_envelope(data)
    except EnvelopeContractRefusal as error:
        if error.code == data.get("expected_code"):
            return None
        return f"{row['id']}: expected {data.get('expected_code')}, got {error.code}"
    return f"{row['id']}: expected refusal"


def _verify_bound(row: dict[str, Any]) -> str | None:
    data = row["data"]
    try:
        actual = validate_bounds(data.get("row_counts"), data.get("batch_body_bytes"))
    except EnvelopeContractRefusal as error:
        if error.code == data.get("expected_code"):
            return None
        return f"{row['id']}: expected {data.get('expected_code')}, got {error.code}"
    if "expected_code" in data:
        return f"{row['id']}: expected refusal"
    if actual != data.get("expected_bytes"):
        return f"{row['id']}: expected {data.get('expected_bytes')}, got {actual}"
    return None


def _verify_retry_coverage(rows: list[dict[str, Any]]) -> None:
    received: set[str] = set()
    for index in range(MAX_VECTOR_ROWS):
        if index >= len(rows):
            break
        row = rows[index]
        if row["kind"] != "retry":
            continue
        expected = row["data"].get("expected")
        if not isinstance(expected, str):
            raise EnvelopeContractRefusal("retry_outcome_drift", row["id"])
        received.add(expected)
    if received != REQUIRED_RETRY_OUTCOMES:
        raise EnvelopeContractRefusal("retry_outcome_drift", repr(received))


def verify_all(contract: dict[str, Any], vectors: list[dict[str, Any]]) -> list[str]:
    """Verify all bounded rows and return exact row-scoped mismatches."""
    _verify_compiled_contract(contract)
    rows = _validated_rows(vectors)
    families = {row["kind"] for row in rows}
    if families != REQUIRED_VECTOR_FAMILIES:
        raise EnvelopeContractRefusal("vector_family_drift", repr(families))
    _verify_retry_coverage(rows)
    envelopes = {row["id"]: row["data"] for row in rows if row["kind"] == "envelope"}
    errors: list[str] = []
    for index in range(MAX_VECTOR_ROWS):
        if index >= len(rows):
            break
        row = rows[index]
        kind = row["kind"]
        error: str | None = None
        if kind == "envelope":
            error = _verify_envelope(row)
        elif kind == "mutation":
            base = _reference(envelopes, row["data"].get("base_id"), f"{row['id']}.base")
            mutated = _reference(envelopes, row["data"].get("mutated_id"), f"{row['id']}.mutated")
            if compose_envelope(base) == compose_envelope(mutated):
                error = f"{row['id']}: mutation did not move envelope"
        elif kind == "retry":
            requested = _reference(
                envelopes, row["data"].get("requested_id"), f"{row['id']}.requested"
            )
            existing = _reference(
                envelopes, row["data"].get("existing_id"), f"{row['id']}.existing"
            )
            actual = _retry_result(requested, existing)
            if actual != row["data"].get("expected"):
                error = f"{row['id']}: expected {row['data'].get('expected')}, got {actual}"
        elif kind == "refusal":
            error = _verify_refusal(row)
        elif kind == "bound":
            error = _verify_bound(row)
        if error is not None:
            errors.append(error)
    return errors


def main() -> int:
    """Verify repository contract paths or explicit alternatives."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("contracts/committed_tick_envelope_v1.yaml"),
    )
    parser.add_argument(
        "--vectors",
        type=Path,
        default=Path("contracts/committed_tick_envelope_v1_vectors.jsonl"),
    )
    arguments = parser.parse_args()
    try:
        errors = verify_all(load_contract(arguments.schema), load_vectors(arguments.vectors))
    except EnvelopeContractRefusal as error:
        print(error)
        return 1
    for index in range(MAX_VECTOR_ROWS):
        if index >= len(errors):
            break
        print(errors[index])
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
