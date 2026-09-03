#!/usr/bin/env python3
"""Independently verify the bounded GlossaryConceptsV1 contract corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

FIXTURE_PATH = "contracts/fixtures/glossary_concepts_v1.jsonl"
MAX_CONTRACT_BYTES = 32_768
MAX_FIXTURE_BYTES = 65_536
MAX_CONCEPT_ROWS = 64
MAX_CONCEPT_ID_BYTES = 128
MAX_DISPLAY_LABEL_BYTES = 256
MAX_DEFINITION_BYTES = 4_096
MAX_CITATION_SOURCE_ID_BYTES = 128
MAX_CITATION_LOCATOR_BYTES = 4_096
EVIDENCE_CLASSES = ["Observed", "Derived", "Calibrated", "Designed"]
CONCEPT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,127}$")
COMPILED_META = {
    "contract": "GlossaryConceptsV1",
    "version": 1,
    "issue": "PER-23",
    "digest": "SHA-256 diagnostic; exact bytes govern retry equality",
}
COMPILED_CONSTANTS = {
    "fixture_path": FIXTURE_PATH,
    "fixture_sha256": "f47e289dc4e7a11c595f0e42643e352e255775c77dde3a7ed35a91de8d84d85a",
    "semantic_domain_ascii_nul": "babylon.glossary-concepts.v1",
    "semantic_sha256": "d296f02168c66199168f732388abfeaf06d03932f784885884b82382b9454ebe",
    "required_concept_ids": [
        "census-identity",
        "class-composition",
        "containment",
        "employment",
        "existence",
        "identity",
        "median-wage",
        "phi-hour",
    ],
    "grant_keys": ["subject", "identity"],
    "grant_tick": 0,
    "concept_id_regex": r"^[a-z0-9][a-z0-9-]{0,127}$",
    "citation_source_id": "glossary-concepts-v1",
    "citation_locator_prefix": "contracts/fixtures/glossary_concepts_v1.jsonl#concept_id=",
}
COMPILED_BOUNDS = {
    "contract_bytes": MAX_CONTRACT_BYTES,
    "fixture_bytes": MAX_FIXTURE_BYTES,
    "concept_rows": MAX_CONCEPT_ROWS,
    "concept_id_bytes": MAX_CONCEPT_ID_BYTES,
    "display_label_bytes": MAX_DISPLAY_LABEL_BYTES,
    "definition_bytes": MAX_DEFINITION_BYTES,
    "citation_source_id_bytes": MAX_CITATION_SOURCE_ID_BYTES,
    "citation_locator_bytes": MAX_CITATION_LOCATOR_BYTES,
}
COMPILED_LAYOUTS = {
    "concept_row_v1": {
        "fields": [
            "concept_id",
            "term",
            "display_label",
            "definition",
            "evidence_class",
            "citation_source_id",
            "citation_locator",
        ],
        "order": "sorted by concept_id",
    },
    "semantic_encoding_v1": {
        "domain": "semantic_domain_ascii_nul plus one trailing NUL byte",
        "row_prefix": "u64 big-endian concept row count",
        "per_concept": [
            "length_prefixed_concept_id_utf8",
            "length_prefixed_display_label_utf8",
            "length_prefixed_definition_utf8",
        ],
        "digest": "SHA-256 over the concatenation",
    },
}


class GlossaryConceptsRefusal(ValueError):
    """One typed independent-verifier refusal."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _bounded_file_bytes(path: Path, maximum: int, code: str) -> bytes:
    try:
        size = path.stat().st_size
    except OSError as error:
        raise GlossaryConceptsRefusal("file_read", str(path)) from error
    if size > maximum:
        raise GlossaryConceptsRefusal(code, str(size))
    try:
        return path.read_bytes()
    except OSError as error:
        raise GlossaryConceptsRefusal("file_read", str(path)) from error


def load_contract(path: Path) -> dict[str, Any]:
    """Load one bounded YAML mapping."""
    raw = _bounded_file_bytes(path, MAX_CONTRACT_BYTES, "schema_too_large")
    try:
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError as error:
        raise GlossaryConceptsRefusal("invalid_schema", str(path)) from error
    if not isinstance(loaded, dict):
        raise GlossaryConceptsRefusal("invalid_schema", "root mapping")
    return loaded


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GlossaryConceptsRefusal("duplicate_json_key", key)
        result[key] = value
    return result


def _bounded_text(value: Any, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise GlossaryConceptsRefusal("concept_row_shape", field)
    encoded = value.encode("utf-8")
    if not encoded or len(encoded) > maximum or b"\x00" in encoded:
        raise GlossaryConceptsRefusal("concept_text_bounds", field)
    return value


def load_concepts(path: Path) -> list[dict[str, Any]]:
    """Load the bounded concept rows without an unbounded whole-file read."""
    raw = _bounded_file_bytes(path, MAX_FIXTURE_BYTES, "fixture_too_large")
    lines = raw.splitlines()
    if not lines or len(lines) > MAX_CONCEPT_ROWS:
        raise GlossaryConceptsRefusal("concept_row_count", str(len(lines)))
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        if not line:
            raise GlossaryConceptsRefusal("concept_row_shape", str(index + 1))
        try:
            row = json.loads(line, object_pairs_hook=_unique_json_object)
        except (json.JSONDecodeError, UnicodeDecodeError, GlossaryConceptsRefusal) as error:
            if isinstance(error, GlossaryConceptsRefusal):
                raise GlossaryConceptsRefusal(error.code, f"{index + 1}: {error.detail}") from error
            raise GlossaryConceptsRefusal("invalid_json", str(index + 1)) from error
        if not isinstance(row, dict) or set(row) != {
            "concept_id",
            "term",
            "display_label",
            "definition",
            "evidence_class",
            "citation",
        }:
            raise GlossaryConceptsRefusal("concept_row_shape", str(index + 1))
        citation = row["citation"]
        if not isinstance(citation, dict) or set(citation) != {"source_id", "locator"}:
            raise GlossaryConceptsRefusal("concept_row_shape", f"{index + 1}: citation")
        concept_id = _bounded_text(row["concept_id"], "concept_id", MAX_CONCEPT_ID_BYTES)
        if not CONCEPT_ID_PATTERN.fullmatch(concept_id):
            raise GlossaryConceptsRefusal("concept_id_shape", concept_id)
        rows.append(
            {
                "concept_id": concept_id,
                "term": _bounded_text(row["term"], "term", MAX_DISPLAY_LABEL_BYTES),
                "display_label": _bounded_text(
                    row["display_label"], "display_label", MAX_DISPLAY_LABEL_BYTES
                ),
                "definition": _bounded_text(row["definition"], "definition", MAX_DEFINITION_BYTES),
                "evidence_class": row["evidence_class"],
                "citation_source_id": _bounded_text(
                    citation["source_id"], "citation.source_id", MAX_CITATION_SOURCE_ID_BYTES
                ),
                "citation_locator": _bounded_text(
                    citation["locator"], "citation.locator", MAX_CITATION_LOCATOR_BYTES
                ),
            }
        )
    return rows


def compute_semantic_sha256(concepts: list[dict[str, Any]]) -> str:
    """Recompute the canonical per-concept semantic digest."""
    hasher = hashlib.sha256()
    hasher.update(COMPILED_CONSTANTS["semantic_domain_ascii_nul"].encode("ascii") + b"\x00")
    hasher.update(len(concepts).to_bytes(8, "big"))
    for row in concepts:
        for field in ("concept_id", "display_label", "definition"):
            encoded = row[field].encode("utf-8")
            hasher.update(len(encoded).to_bytes(8, "big"))
            hasher.update(encoded)
    return hasher.hexdigest()


def _verify_compiled_contract(contract: dict[str, Any]) -> None:
    if contract.get("meta") != COMPILED_META:
        raise GlossaryConceptsRefusal("compiled_contract_drift", "meta")
    if contract.get("constants") != COMPILED_CONSTANTS:
        raise GlossaryConceptsRefusal("compiled_contract_drift", "constants")
    if contract.get("bounds") != COMPILED_BOUNDS:
        raise GlossaryConceptsRefusal("compiled_contract_drift", "bounds")
    if contract.get("layouts") != COMPILED_LAYOUTS:
        raise GlossaryConceptsRefusal("compiled_contract_drift", "layouts")
    if contract.get("production_decoder") != "prohibited":
        raise GlossaryConceptsRefusal("compiled_contract_drift", "production_decoder")
    required = contract.get("vector_kinds", {}).get("required")
    if required != []:
        raise GlossaryConceptsRefusal("compiled_contract_drift", "vector_kinds")


def verify_all(contract: dict[str, Any], concepts: list[dict[str, Any]], root: Path) -> list[str]:
    """Verify all bounded rows and return exact row-scoped mismatches."""
    _verify_compiled_contract(contract)
    constants = contract["constants"]
    errors: list[str] = []
    fixture_bytes = _bounded_file_bytes(root / FIXTURE_PATH, MAX_FIXTURE_BYTES, "fixture_too_large")
    if hashlib.sha256(fixture_bytes).hexdigest() != constants["fixture_sha256"]:
        raise GlossaryConceptsRefusal("fixture_digest", FIXTURE_PATH)
    ids = [row["concept_id"] for row in concepts]
    if ids != sorted(ids) or len(set(ids)) != len(ids):
        errors.append("fixture order: concepts must be sorted by concept_id without duplicates")
    if set(ids) != set(constants["required_concept_ids"]):
        unexpected = sorted(set(ids) - set(constants["required_concept_ids"]))
        missing = sorted(set(constants["required_concept_ids"]) - set(ids))
        errors.append(f"fixture set: unexpected={unexpected} missing={missing}")
    locator_prefix = constants["citation_locator_prefix"]
    for row in concepts:
        concept_id = row["concept_id"]
        if not CONCEPT_ID_PATTERN.fullmatch(concept_id):
            errors.append(f"{concept_id}: concept id shape drift")
        if row["evidence_class"] not in EVIDENCE_CLASSES:
            errors.append(f"{concept_id}: evidence_class outside the constitutional compact")
        if row["citation_source_id"] != constants["citation_source_id"]:
            errors.append(f"{concept_id}: citation source identity drift")
        if row["citation_locator"] != f"{locator_prefix}{concept_id}":
            errors.append(f"{concept_id}: citation locator drift")
        if row["term"] != row["display_label"]:
            errors.append(f"{concept_id}: term must equal the canonical display label")
    if compute_semantic_sha256(concepts) != constants["semantic_sha256"]:
        errors.append("semantic digest: recomputed digest diverges from the contract constant")
    return errors


def main() -> int:
    """Verify repository contract paths or explicit alternatives."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("contracts/glossary_concepts_v1.yaml"),
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path(FIXTURE_PATH),
    )
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        errors = verify_all(load_contract(arguments.schema), load_concepts(arguments.fixture), root)
    except GlossaryConceptsRefusal as error:
        print(error)
        return 1
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
