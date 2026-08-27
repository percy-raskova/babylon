#!/usr/bin/env python3
"""Independently verify the language-neutral TickCommitClaimV1 contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml

MAX_SCHEMA_BYTES = 32_768
MAX_VECTOR_ROWS = 32
MAX_VECTOR_LINE_BYTES = 4_096
MAX_U64 = (1 << 64) - 1
DOMAIN = b"babylon.tick-commit-claim\0"
COMPILED_CONSTANTS = {
    "domain_ascii_nul": "babylon.tick-commit-claim",
    "layout_u32": 1,
    "tick_content_layout_u32": 1,
    "tags": [1, 2, 3],
    "canonical_bytes": 93,
}
COMPILED_BOUNDS = {
    "schema_bytes": MAX_SCHEMA_BYTES,
    "vector_rows": MAX_VECTOR_ROWS,
    "vector_line_bytes": MAX_VECTOR_LINE_BYTES,
    "campaign_uuid_text_bytes": 36,
    "tick_content_digest_bytes": 32,
}
COMPILED_RETRY = {
    "different_key": "key_mismatch",
    "same_key_same_tick_content_hash": "idempotent",
    "same_key_different_tick_content_hash": "content_identity_mismatch",
}
REQUIRED_FAMILIES = {"claim", "mutation", "retry", "refusal"}


class ClaimContractRefusal(ValueError):
    """One bounded contract input lacked its single canonical form."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code


def load_contract(path: Path) -> dict[str, Any]:
    """Load one bounded YAML mapping."""
    with path.open("rb") as stream:
        raw = stream.read(MAX_SCHEMA_BYTES + 1)
    if len(raw) > MAX_SCHEMA_BYTES:
        raise ClaimContractRefusal("schema_too_large", str(len(raw)))
    value = yaml.safe_load(raw)
    if not isinstance(value, dict):
        raise ClaimContractRefusal("schema_shape", "top level must be a mapping")
    return value


def load_vectors(path: Path) -> list[dict[str, Any]]:
    """Load bounded JSONL rows with no unbounded line read."""
    rows: list[dict[str, Any]] = []
    with path.open("rb") as stream:
        for index in range(MAX_VECTOR_ROWS + 1):
            raw = stream.readline(MAX_VECTOR_LINE_BYTES + 2)
            if raw == b"":
                break
            if index == MAX_VECTOR_ROWS:
                raise ClaimContractRefusal("too_many_rows", str(index + 1))
            content = raw.removesuffix(b"\n").removesuffix(b"\r")
            if not content or len(content) > MAX_VECTOR_LINE_BYTES:
                raise ClaimContractRefusal("invalid_line_length", str(len(content)))
            try:
                value = json.loads(content)
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ClaimContractRefusal("invalid_json", str(index + 1)) from error
            if not isinstance(value, dict):
                raise ClaimContractRefusal("vector_shape", str(index + 1))
            rows.append(value)
    return rows


def _verify_compiled_contract(contract: dict[str, Any]) -> None:
    if contract.get("constants") != COMPILED_CONSTANTS:
        raise ClaimContractRefusal("compiled_contract_drift", "constants")
    if contract.get("bounds") != COMPILED_BOUNDS:
        raise ClaimContractRefusal("compiled_contract_drift", "bounds")
    retry = contract.get("retry_semantics", {}).get("requested_against_existing")
    if retry != COMPILED_RETRY:
        raise ClaimContractRefusal("compiled_contract_drift", "retry_semantics")
    if contract.get("production_decoder") != "prohibited":
        raise ClaimContractRefusal("compiled_contract_drift", "production_decoder")
    required = contract.get("vector_families", {}).get("required")
    if not isinstance(required, list) or set(required) != REQUIRED_FAMILIES:
        raise ClaimContractRefusal("compiled_contract_drift", "vector_families")


def _campaign_bytes(value: object) -> bytes:
    if not isinstance(value, str) or len(value.encode("utf-8")) != 36:
        raise ClaimContractRefusal("invalid_campaign_id", "length")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as error:
        raise ClaimContractRefusal("invalid_campaign_id", "syntax") from error
    if str(parsed) != value:
        raise ClaimContractRefusal("invalid_campaign_id", "canonical text")
    return parsed.bytes


def _resolve_tick_bytes(value: object) -> bytes:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ClaimContractRefusal("invalid_resolve_tick", "type")
    if value < 0 or value > MAX_U64:
        raise ClaimContractRefusal("invalid_resolve_tick", str(value))
    return value.to_bytes(8, "big")


def _tick_content_bytes(value: object) -> bytes:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value:
        raise ClaimContractRefusal("invalid_tick_content_hash", "text")
    try:
        digest = bytes.fromhex(value)
    except ValueError as error:
        raise ClaimContractRefusal("invalid_tick_content_hash", "hex") from error
    if len(digest) != 32:
        raise ClaimContractRefusal("invalid_tick_content_hash", "length")
    return digest


def compose_claim(data: dict[str, Any]) -> bytes:
    """Compose one claim from semantic values without trusting vector bytes."""
    campaign = _campaign_bytes(data.get("campaign_id"))
    tick = _resolve_tick_bytes(data.get("resolve_tick"))
    content = _tick_content_bytes(data.get("tick_content_hash_hex"))
    canonical = b"".join(
        (
            DOMAIN,
            (1).to_bytes(4, "big"),
            b"\x01",
            campaign,
            b"\x02",
            tick,
            b"\x03",
            (1).to_bytes(4, "big"),
            content,
        )
    )
    if len(canonical) != COMPILED_CONSTANTS["canonical_bytes"]:
        raise ClaimContractRefusal("canonical_size", str(len(canonical)))
    return canonical


def _retry_result(requested: dict[str, Any], existing: dict[str, Any]) -> str:
    requested_key = (requested["campaign_id"], requested["resolve_tick"])
    existing_key = (existing["campaign_id"], existing["resolve_tick"])
    if requested_key != existing_key:
        return "key_mismatch"
    if requested["tick_content_hash_hex"] == existing["tick_content_hash_hex"]:
        return "idempotent"
    return "content_identity_mismatch"


def _verify_claim(row: dict[str, Any]) -> str | None:
    data = row["data"]
    canonical = compose_claim(data)
    if canonical.hex() != data.get("canonical_hex"):
        return f"{row['id']}: canonical bytes mismatch"
    if hashlib.sha256(canonical).hexdigest() != data.get("sha256_hex"):
        return f"{row['id']}: SHA-256 mismatch"
    return None


def _verify_refusal(row: dict[str, Any]) -> str | None:
    data = row["data"]
    if data.get("operation") != "compose_claim":
        return f"{row['id']}: unknown refusal operation"
    try:
        compose_claim(data)
    except ClaimContractRefusal as error:
        if error.code == data.get("expected_code"):
            return None
        return f"{row['id']}: expected {data.get('expected_code')}, got {error.code}"
    return f"{row['id']}: expected refusal"


def verify_all(contract: dict[str, Any], vectors: list[dict[str, Any]]) -> list[str]:
    """Verify all bounded rows and return exact row-scoped mismatches."""
    _verify_compiled_contract(contract)
    families = {row.get("kind") for row in vectors[:MAX_VECTOR_ROWS]}
    if families != REQUIRED_FAMILIES:
        raise ClaimContractRefusal("vector_family_drift", repr(families))
    claims = {
        row["id"]: row["data"] for row in vectors[:MAX_VECTOR_ROWS] if row.get("kind") == "claim"
    }
    errors: list[str] = []
    for row in vectors[:MAX_VECTOR_ROWS]:
        kind = row.get("kind")
        error: str | None = None
        if kind == "claim":
            error = _verify_claim(row)
        elif kind == "mutation":
            data = row["data"]
            if compose_claim(claims[data["base_id"]]) == compose_claim(claims[data["mutated_id"]]):
                error = f"{row['id']}: mutation did not move claim"
        elif kind == "retry":
            data = row["data"]
            actual = _retry_result(claims[data["requested_id"]], claims[data["existing_id"]])
            if actual != data.get("expected"):
                error = f"{row['id']}: expected {data.get('expected')}, got {actual}"
        elif kind == "refusal":
            error = _verify_refusal(row)
        if error is not None:
            errors.append(error)
    return errors


def main() -> int:
    """Verify the repository contract paths or explicit alternatives."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", type=Path, default=Path("contracts/tick_commit_claim_v1.yaml"))
    parser.add_argument(
        "--vectors",
        type=Path,
        default=Path("contracts/tick_commit_claim_v1_vectors.jsonl"),
    )
    arguments = parser.parse_args()
    errors = verify_all(load_contract(arguments.schema), load_vectors(arguments.vectors))
    for error in errors[:MAX_VECTOR_ROWS]:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
