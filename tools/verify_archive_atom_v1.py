#!/usr/bin/env python3
"""Independently verify the bounded ArchiveAtomV1 contract corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import uuid
from pathlib import Path
from typing import Any

import yaml

SOURCE_PATH = "rust/crates/babylon-persistence/src/archive.rs"
SCHEMA_PATH = "rust/crates/babylon-persistence/migrations/archive_atom_v1.sql"
ATOM_DOMAIN_ASCII_NUL = "babylon.semantic-archive-atom.v1"
ATOM_SCHEMA_CONTRACT_ID = "babylon.archive-atom-schema.v1"
MAX_I64 = (1 << 63) - 1
MAX_CONTRACT_BYTES = 131_072
MAX_VECTOR_ROWS = 32
MAX_VECTOR_LINE_BYTES = 16_384
MAX_VECTOR_OBJECT_FIELDS = 64
MAX_ID_BYTES = 128
MAX_TEXT_BYTES = 4_096
KIND_TAGS = {"county": 1, "place": 2, "concept": 3}
EVIDENCE_TAGS = {"Observed": 1, "Derived": 2, "Calibrated": 3, "Designed": 4}
VALUE_TAGS = {"text": 1, "f64": 2, "u64": 3, "bool": 4}
CONCEPT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,127}$")
KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,127}$")
REQUIRED_VECTOR_KINDS = {"identity", "encoding", "refusal", "visibility"}
REQUIRED_ROW_IDS = {
    "identity": {"identity-domain-and-layouts"},
    "encoding": {
        "encoding-county-subject-text-observed",
        "encoding-place-f64-derived",
        "encoding-concept-u64-designed",
        "encoding-concept-bool-designed",
        "encoding-f64-neg-zero-canonical",
    },
    "refusal": {"refuse-f64-pos-inf", "refuse-f64-neg-inf", "refuse-f64-nan"},
    "visibility": {
        "visibility-granted-in-horizon",
        "visibility-granted-tick-after-valid",
        "visibility-no-grant-row",
        "visibility-past-horizon",
    },
}
NONFINITE_BITS_HEX = {"7ff0000000000000", "fff0000000000000", "7ff8000000000000"}
COMPILED_META = {
    "contract": "ArchiveAtomV1",
    "version": 1,
    "issue": "PER-23",
    "digest": "SHA-256 diagnostic; exact bytes govern retry equality",
}
COMPILED_CONSTANTS = {
    "source_path": SOURCE_PATH,
    "schema_path": SCHEMA_PATH,
    "atom_domain_ascii_nul": ATOM_DOMAIN_ASCII_NUL,
    "atom_schema_contract_id": ATOM_SCHEMA_CONTRACT_ID,
    "county_kind_tag_u8": 1,
    "place_kind_tag_u8": 2,
    "concept_kind_tag_u8": 3,
    "observed_tag_u8": 1,
    "derived_tag_u8": 2,
    "calibrated_tag_u8": 3,
    "designed_tag_u8": 4,
    "text_tag_u8": 1,
    "f64_tag_u8": 2,
    "u64_tag_u8": 3,
    "bool_tag_u8": 4,
    "max_id_bytes": MAX_ID_BYTES,
    "max_text_bytes": MAX_TEXT_BYTES,
    "evidence_classes": ["Observed", "Derived", "Calibrated", "Designed"],
    "value_kinds": ["text", "f64", "u64", "bool"],
}
COMPILED_BOUNDS = {
    "contract_bytes": MAX_CONTRACT_BYTES,
    "vector_rows": MAX_VECTOR_ROWS,
    "vector_line_bytes": MAX_VECTOR_LINE_BYTES,
    "vector_object_fields": MAX_VECTOR_OBJECT_FIELDS,
    "atom_subject_id_bytes": MAX_ID_BYTES,
    "signal_key_bytes": MAX_ID_BYTES,
    "grant_key_bytes": MAX_ID_BYTES,
    "citation_source_id_bytes": MAX_TEXT_BYTES,
    "citation_locator_bytes": MAX_TEXT_BYTES,
}
COMPILED_LAYOUTS = {
    "canonical_encoding_v1": {
        "digest": "SHA-256 over the concatenation, in this exact order",
        "fields": [
            "domain_ascii_nul_plus_one_trailing_nul_byte",
            "campaign_id_exact_16_uuid_bytes_network_order",
            "subject_kind_tag_u8",
            "length_prefixed_subject_id_utf8_u64_big_endian",
            "length_prefixed_signal_key_utf8_u64_big_endian",
            "length_prefixed_grant_key_utf8_u64_big_endian",
            "evidence_class_tag_u8",
            "value_kind_tag_u8",
            "value_payload_v1",
            "length_prefixed_citation_source_id_utf8_u64_big_endian",
            "length_prefixed_citation_locator_utf8_u64_big_endian",
            "valid_tick_u64_big_endian",
        ],
    },
    "value_payload_v1": {
        "text": "length_prefixed_utf8_u64_big_endian",
        "f64": "canonical_binary64_bits_u64_big_endian_neg_zero_normalizes_to_pos_zero",
        "u64": "u64_big_endian",
        "bool": "one_byte_zero_or_one",
    },
    "length_prefix": "u64 big-endian exact byte count before every variable byte field",
}


class ArchiveAtomContractRefusal(ValueError):
    """One typed independent-verifier refusal."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _bounded_file_bytes(path: Path, maximum: int, code: str) -> bytes:
    try:
        size = path.stat().st_size
    except OSError as error:
        raise ArchiveAtomContractRefusal("file_read", str(path)) from error
    if size > maximum:
        raise ArchiveAtomContractRefusal(code, str(size))
    try:
        return path.read_bytes()
    except OSError as error:
        raise ArchiveAtomContractRefusal("file_read", str(path)) from error


def load_contract(path: Path) -> dict[str, Any]:
    """Load one bounded YAML mapping."""
    raw = _bounded_file_bytes(path, MAX_CONTRACT_BYTES, "schema_too_large")
    try:
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError as error:
        raise ArchiveAtomContractRefusal("schema_invalid", str(error)) from error
    if not isinstance(loaded, dict):
        raise ArchiveAtomContractRefusal("schema_shape", type(loaded).__name__)
    return loaded


def load_vectors(path: Path) -> list[dict[str, Any]]:
    """Load bounded JSONL vector rows."""
    raw = _bounded_file_bytes(path, MAX_VECTOR_ROWS * MAX_VECTOR_LINE_BYTES, "vectors_too_large")
    rows: list[dict[str, Any]] = []
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        if len(line.encode("utf-8")) > MAX_VECTOR_LINE_BYTES:
            raise ArchiveAtomContractRefusal("vector_line_too_large", str(len(line)))
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ArchiveAtomContractRefusal("vector_invalid", str(error)) from error
        if not isinstance(row, dict) or len(row) > MAX_VECTOR_OBJECT_FIELDS:
            raise ArchiveAtomContractRefusal("vector_shape", repr(row)[:200])
        rows.append(row)
    if len(rows) > MAX_VECTOR_ROWS:
        raise ArchiveAtomContractRefusal("vector_rows", str(len(rows)))
    return rows


def _prefix(hasher: hashlib._Hash, text: str) -> None:
    encoded = text.encode("utf-8")
    hasher.update(struct.pack(">Q", len(encoded)))
    hasher.update(encoded)


def _check_bounded_text(value: Any, maximum: int, code: str) -> str:
    if not isinstance(value, str):
        raise ArchiveAtomContractRefusal(code, type(value).__name__)
    if not 1 <= len(value.encode("utf-8")) <= maximum or "\x00" in value:
        raise ArchiveAtomContractRefusal(code, value[:64])
    return value


def _check_key(value: Any, code: str) -> str:
    if not isinstance(value, str) or not KEY_RE.fullmatch(value):
        raise ArchiveAtomContractRefusal(code, repr(value)[:64])
    return value


def _subject_id(kind: str, value: Any) -> str:
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > MAX_ID_BYTES:
        raise ArchiveAtomContractRefusal("subject_id", repr(value)[:64])
    if kind in ("county", "place"):
        expected = 5 if kind == "county" else 7
        if len(value) != expected or not value.isascii() or not value.isdigit():
            raise ArchiveAtomContractRefusal("subject_id", value)
    elif kind == "concept":
        if not CONCEPT_ID_RE.fullmatch(value):
            raise ArchiveAtomContractRefusal("subject_id", value)
    else:
        raise ArchiveAtomContractRefusal("subject_kind", kind)
    return value


def atom_id_from_fields(data: dict[str, Any]) -> tuple[bytes, str]:
    """Recompute the canonical atom identity from one vector input."""
    try:
        campaign = uuid.UUID(data["campaign_id_uuid"])
    except (KeyError, ValueError, TypeError, AttributeError) as error:
        raise ArchiveAtomContractRefusal("campaign_id", repr(error)) from error
    kind = data["subject_kind"]
    subject_id = _subject_id(kind, data["subject_id"])
    signal_key = _check_key(data["signal_key"], "signal_key")
    grant_key = _check_key(data["grant_key"], "grant_key")
    evidence = data["evidence_class"]
    if evidence not in EVIDENCE_TAGS:
        raise ArchiveAtomContractRefusal("evidence_class", repr(evidence))
    citation = data["citation"]
    source_id = _check_bounded_text(citation["source_id"], MAX_TEXT_BYTES, "citation_source")
    locator = _check_bounded_text(citation["locator"], MAX_TEXT_BYTES, "citation_locator")
    valid_tick = data["valid_tick"]
    if not isinstance(valid_tick, int) or isinstance(valid_tick, bool):
        raise ArchiveAtomContractRefusal("valid_tick", repr(valid_tick))
    if not 0 <= valid_tick <= MAX_I64:
        raise ArchiveAtomContractRefusal("valid_tick", str(valid_tick))
    value = data["value"]
    value_kind = value["kind"]
    if value_kind not in VALUE_TAGS:
        raise ArchiveAtomContractRefusal("value_kind", repr(value_kind))
    hasher = hashlib.sha256()
    hasher.update(ATOM_DOMAIN_ASCII_NUL.encode("ascii") + b"\x00")
    hasher.update(campaign.bytes)
    hasher.update(bytes([KIND_TAGS[kind]]))
    _prefix(hasher, subject_id)
    _prefix(hasher, signal_key)
    _prefix(hasher, grant_key)
    hasher.update(bytes([EVIDENCE_TAGS[evidence]]))
    hasher.update(bytes([VALUE_TAGS[value_kind]]))
    if value_kind == "text":
        text = _check_bounded_text(value["text"], MAX_TEXT_BYTES, "value_text")
        _prefix(hasher, text)
    elif value_kind == "f64":
        try:
            bits = int(value["bits_hex"], 16)
        except (KeyError, ValueError, TypeError) as error:
            raise ArchiveAtomContractRefusal("value_f64", repr(error)) from error
        if not 0 <= bits <= 0xFFFF_FFFF_FFFF_FFFF:
            raise ArchiveAtomContractRefusal("value_f64", str(bits))
        number = struct.unpack(">d", struct.pack(">Q", bits))[0]
        if not math.isfinite(number):
            raise ArchiveAtomContractRefusal("value_f64_nonfinite", value["bits_hex"])
        canonical = 0.0 if number == 0.0 else number
        hasher.update(struct.pack(">Q", struct.unpack(">Q", struct.pack(">d", canonical))[0]))
    elif value_kind == "u64":
        number = value["number"]
        if not isinstance(number, int) or isinstance(number, bool) or not 0 <= number < 1 << 64:
            raise ArchiveAtomContractRefusal("value_u64", repr(number))
        hasher.update(struct.pack(">Q", number))
    else:
        flag = value["flag"]
        if not isinstance(flag, bool):
            raise ArchiveAtomContractRefusal("value_bool", repr(flag))
        hasher.update(b"\x01" if flag else b"\x00")
    _prefix(hasher, source_id)
    _prefix(hasher, locator)
    hasher.update(struct.pack(">Q", valid_tick))
    return hasher.digest(), value_kind


def _verify_identity(row: dict[str, Any], root: Path) -> str | None:
    data = row["data"]
    if data.get("source_path") != SOURCE_PATH or data.get("schema_path") != SCHEMA_PATH:
        return f"{row['id']}: pinned source path drift"
    if data.get("atom_domain_ascii_nul") != ATOM_DOMAIN_ASCII_NUL:
        return f"{row['id']}: atom domain drift"
    if data.get("atom_schema_contract_id") != ATOM_SCHEMA_CONTRACT_ID:
        return f"{row['id']}: atom schema contract id drift"
    if data.get("kind_tags") != KIND_TAGS:
        return f"{row['id']}: kind tag drift"
    if data.get("evidence_tags") != EVIDENCE_TAGS:
        return f"{row['id']}: evidence tag drift"
    if data.get("value_tags") != VALUE_TAGS:
        return f"{row['id']}: value tag drift"
    schema = _bounded_file_bytes(root / SCHEMA_PATH, MAX_CONTRACT_BYTES, "file_read")
    text = schema.decode("utf-8")
    for needle in (
        ATOM_SCHEMA_CONTRACT_ID,
        "value_f64 = value_f64",
        "abs(value_f64) <> 'Infinity'::float8",
        "v_archive_atom_visible",
    ):
        if needle not in text:
            return f"{row['id']}: schema byte drift missing {needle!r}"
    return None


def _verify_encoding(row: dict[str, Any]) -> str | None:
    try:
        atom_id, _ = atom_id_from_fields(row["data"])
    except (ArchiveAtomContractRefusal, KeyError) as error:
        return f"{row['id']}: {getattr(error, 'code', 'shape')}"
    if atom_id.hex() != row["data"].get("atom_id_hex"):
        return f"{row['id']}: atom_id mismatch"
    return None


def _verify_refusal(row: dict[str, Any]) -> str | None:
    data = row["data"]
    if data.get("operation") != "mint":
        return f"{row['id']}: unknown refusal operation"
    if data.get("expected_code") != "non_finite_value":
        return f"{row['id']}: unknown refusal code"
    bits = data.get("value", {}).get("bits_hex")
    if bits not in NONFINITE_BITS_HEX:
        return f"{row['id']}: refusal vector bits drift"
    try:
        atom_id_from_fields(data)
    except ArchiveAtomContractRefusal as error:
        if error.code == "value_f64_nonfinite":
            return None
        return f"{row['id']}: {error.code}"
    return f"{row['id']}: refusal is not forced; encoding succeeded"


def _verify_visibility(row: dict[str, Any]) -> str | None:
    data = row["data"]
    try:
        atom_id_from_fields(data["atom"])
    except (ArchiveAtomContractRefusal, KeyError) as error:
        return f"{row['id']}: {getattr(error, 'code', 'shape')}"
    valid_tick = data["atom"]["valid_tick"]
    granted_tick = data.get("granted_tick")
    horizon_tick = data.get("horizon_tick")
    if not isinstance(horizon_tick, int) or isinstance(horizon_tick, bool):
        return f"{row['id']}: horizon tick malformed"
    if granted_tick is not None and (
        not isinstance(granted_tick, int) or isinstance(granted_tick, bool)
    ):
        return f"{row['id']}: granted tick malformed"
    actual = granted_tick is not None and granted_tick <= valid_tick <= horizon_tick
    if actual != data.get("expected_visible"):
        return f"{row['id']}: visibility predicate mismatch"
    return None


def _verify_compiled_contract(contract: dict[str, Any]) -> None:
    if contract.get("meta") != COMPILED_META:
        raise ArchiveAtomContractRefusal("compiled_meta_drift", repr(contract.get("meta")))
    if contract.get("production_decoder") != "prohibited":
        raise ArchiveAtomContractRefusal("decoder_gate", repr(contract.get("production_decoder")))
    if contract.get("constants") != COMPILED_CONSTANTS:
        raise ArchiveAtomContractRefusal(
            "compiled_constants_drift", repr(contract.get("constants"))
        )
    if contract.get("bounds") != COMPILED_BOUNDS:
        raise ArchiveAtomContractRefusal("compiled_bounds_drift", repr(contract.get("bounds")))
    if contract.get("layouts") != COMPILED_LAYOUTS:
        raise ArchiveAtomContractRefusal("compiled_layouts_drift", repr(contract.get("layouts")))


def verify_all(contract: dict[str, Any], vectors: list[dict[str, Any]], root: Path) -> list[str]:
    """Verify all bounded rows and return exact row-scoped mismatches."""
    _verify_compiled_contract(contract)
    kinds = {row.get("kind") for row in vectors}
    if kinds != REQUIRED_VECTOR_KINDS:
        raise ArchiveAtomContractRefusal("vector_kind_drift", repr(kinds))
    by_kind: dict[str, set[str]] = {}
    for row in vectors:
        by_kind.setdefault(row["kind"], set()).add(row["id"])
    for kind, required in REQUIRED_ROW_IDS.items():
        if by_kind.get(kind) != required:
            raise ArchiveAtomContractRefusal(
                "vector_id_drift", f"{kind}: {sorted(by_kind.get(kind, set()))}"
            )
    errors: list[str] = []
    for row in vectors:
        kind = row["kind"]
        error: str | None = None
        if kind == "identity":
            error = _verify_identity(row, root)
        elif kind == "encoding":
            error = _verify_encoding(row)
        elif kind == "refusal":
            error = _verify_refusal(row)
        elif kind == "visibility":
            error = _verify_visibility(row)
        if error:
            errors.append(error)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", type=Path, default=Path("contracts/archive_atom_v1.yaml"))
    parser.add_argument(
        "--vectors", type=Path, default=Path("contracts/archive_atom_v1_vectors.jsonl")
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    try:
        contract = load_contract(args.schema)
        vectors = load_vectors(args.vectors)
        errors = verify_all(contract, vectors, args.root)
    except ArchiveAtomContractRefusal as error:
        print(f"{error.code}: {error.detail}")
        return 1
    for error in errors:
        print(error)
    if errors:
        return 1
    print(f"archive_atom_v1: {len(vectors)} vector rows verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
