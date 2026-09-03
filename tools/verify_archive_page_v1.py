#!/usr/bin/env python3
"""Independently verify the bounded ArchivePageV1 contract corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

FRONT_MATTER_CONTRACT_ID = "babylon.archive-page.v1"
TEMPLATE_PATH = "rust/crates/babylon-persistence/src/archive_page_v1.md.j2"
SCHEMA_PATH = "rust/crates/babylon-persistence/migrations/semantic_archive_v1.sql"
ATOM_SCHEMA_PATH = "rust/crates/babylon-persistence/migrations/archive_atom_v1.sql"
WORKER_DOMAIN_ASCII_NUL = "babylon.semantic-archive-worker.v1"
DIRTY_BATCH_DOMAIN_ASCII_NUL = "babylon.semantic-archive-dirty-batch.v1"
TEMPLATE_SHA256 = "f5561534e53924ac4f7970d9abfb19d032cf491e6d04dc2463d3b3bf25c4b539"
MAX_U64 = (1 << 64) - 1
MAX_I64 = (1 << 63) - 1
MAX_ID_BYTES = 128
MAX_TEXT_BYTES = 4_096
MAX_SIGNALS = 256
MAX_LINKS = 256
MAX_PAGES = 256
MAX_KNOWLEDGE_GRANTS = 65_535
MAX_PAGE_BYTES = 1_048_576
MAX_CONTRACT_BYTES = 131_072
MAX_VECTOR_ROWS = 32
MAX_VECTOR_LINE_BYTES = 16_384
MAX_VECTOR_OBJECT_FIELDS = 64
KIND_TAGS = {"county": 1, "place": 2}
ID_WIDTHS = {"county": 5, "place": 7}
REQUIRED_VECTOR_KINDS = {"render", "refusal", "batch", "identity"}
REQUIRED_BATCH_ROW_IDS = ("batch-empty", "batch-one-page")
COMPILED_META = {
    "contract": "ArchivePageV1",
    "version": 1,
    "issue": "PER-22",
    "byte_order": "big-endian",
    "digest": "SHA-256 diagnostic; exact bytes govern retry equality",
}
COMPILED_CONSTANTS = {
    "front_matter_contract_id": FRONT_MATTER_CONTRACT_ID,
    "archive_schema_contract_id": "babylon.semantic-archive-schema.v1",
    "template_path": TEMPLATE_PATH,
    "template_sha256": TEMPLATE_SHA256,
    "worker_domain_ascii_nul": WORKER_DOMAIN_ASCII_NUL,
    "atom_schema_path": ATOM_SCHEMA_PATH,
    "dirty_batch_domain_ascii_nul": DIRTY_BATCH_DOMAIN_ASCII_NUL,
    "knowledge_domain_ascii_nul": "babylon.semantic-archive-knowledge.v1",
    "county_kind_tag_u8": 1,
    "place_kind_tag_u8": 2,
    "max_id_bytes": MAX_ID_BYTES,
    "max_text_bytes": MAX_TEXT_BYTES,
    "max_signals_per_page": MAX_SIGNALS,
    "max_links_per_page": MAX_LINKS,
    "max_pages_per_batch": MAX_PAGES,
    "max_knowledge_grants": MAX_KNOWLEDGE_GRANTS,
    "max_page_bytes": MAX_PAGE_BYTES,
    "max_search_hits": 100,
}
COMPILED_BOUNDS = {
    "contract_bytes": MAX_CONTRACT_BYTES,
    "vector_rows": MAX_VECTOR_ROWS,
    "vector_line_bytes": MAX_VECTOR_LINE_BYTES,
    "vector_object_fields": MAX_VECTOR_OBJECT_FIELDS,
    "markdown_bytes": MAX_PAGE_BYTES,
    "signals_per_page": MAX_SIGNALS,
    "links_per_page": MAX_LINKS,
    "pages_per_batch": MAX_PAGES,
    "knowledge_grants_per_snapshot": MAX_KNOWLEDGE_GRANTS,
}
# Normative layouts mirrored from the compiled hashing and rendering
# implementation (rust/crates/babylon-persistence/src/archive.rs): the exact
# field order of hash_page_input, the dirty-batch digest composition, the
# worker contract concatenation, and the pinned template link forms.
COMPILED_LAYOUTS = {
    "hash_primitives_v1": {
        "length_prefix": "u64 big-endian exact byte count before every variable byte field"
    },
    "page_ref_v1": {
        "fields": ["kind_tag_u8", "length_prefixed_exact_id_ascii"],
        "county_tag_u8": 1,
        "place_tag_u8": 2,
        "county_id_bytes": 5,
        "place_id_bytes": 7,
    },
    "page_input_v1": {
        "fields": [
            "page_ref_v1",
            "length_prefixed_title",
            "verified_tick_u64",
            "tick_content_hash_exact_32_bytes",
            "length_prefixed_decision_question",
            "signal_count_u64",
            "per_signal_grant_key_label_value_citation",
            "link_count_u64",
            "per_link_page_ref_v1_and_length_prefixed_known_label",
        ],
        "order": "exact input order",
        "duplicate_signal_keys": "prohibited",
        "duplicate_link_targets": "prohibited",
    },
    "dirty_batch_v1": {
        "fields": [
            "dirty_batch_domain_ascii_nul",
            "resolve_tick_u64",
            "tick_content_hash_exact_32_bytes",
            "page_count_u64",
            "exact_ordered_page_input_v1_fields",
        ],
        "duplicate_subjects": "prohibited",
        "receipt_mismatch": "prohibited",
    },
    "worker_contract_v1": {
        "fields": [
            "worker_domain_ascii_nul",
            "exact_schema_sql_bytes",
            "exact_atom_schema_sql_bytes",
            "template_sha256_exact_32_bytes",
        ],
        "digest": "SHA-256 over the concatenation",
    },
    "page_markdown_v1": {
        "front_matter": [
            "schema_front_matter_contract_id",
            "subject_page_key",
            "verified_tick_decimal",
            "tick_content_hash_hex",
        ],
        "known_link_form": "[[{kind}/{id}|{known_label}]]",
        "redlink_form": "[[{kind}/{id}]]",
    },
    "search_text_v1": {
        "join": "single ASCII space",
        "parts": [
            "subject_page_key",
            "subject_title",
            "decision_question",
            "per_known_signal_label_then_value",
            "per_known_link_page_key_then_known_label",
        ],
    },
    "citations_v1": {
        "order": [
            "subject_grant_citation_first",
            "distinct_known_signal_citations_in_signal_order",
        ],
    },
}


class ArchivePageContractRefusal(ValueError):
    """One typed independent-verifier refusal."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _bounded_file_bytes(path: Path, maximum: int, code: str) -> bytes:
    try:
        size = path.stat().st_size
    except OSError as error:
        raise ArchivePageContractRefusal("file_read", str(path)) from error
    if size > maximum:
        raise ArchivePageContractRefusal(code, str(size))
    try:
        return path.read_bytes()
    except OSError as error:
        raise ArchivePageContractRefusal("file_read", str(path)) from error


def load_contract(path: Path) -> dict[str, Any]:
    """Load one bounded YAML mapping."""
    raw = _bounded_file_bytes(path, MAX_CONTRACT_BYTES, "schema_too_large")
    try:
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError as error:
        raise ArchivePageContractRefusal("invalid_schema", str(path)) from error
    if not isinstance(loaded, dict):
        raise ArchivePageContractRefusal("invalid_schema", "root mapping")
    return loaded


def load_vectors(path: Path) -> list[dict[str, Any]]:
    """Load bounded JSONL rows without an unbounded whole-file read."""
    maximum = MAX_VECTOR_ROWS * (MAX_VECTOR_LINE_BYTES + 1)
    raw = _bounded_file_bytes(path, maximum, "vectors_too_large")
    lines = raw.splitlines()
    if len(lines) > MAX_VECTOR_ROWS:
        raise ArchivePageContractRefusal("too_many_rows", str(len(lines)))
    rows: list[dict[str, Any]] = []
    for index in range(MAX_VECTOR_ROWS):
        if index >= len(lines):
            break
        line = lines[index]
        if not line or len(line) > MAX_VECTOR_LINE_BYTES:
            raise ArchivePageContractRefusal("invalid_line_length", str(index + 1))
        try:
            row = json.loads(line, object_pairs_hook=_unique_json_object)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ArchivePageContractRefusal("invalid_json", str(index + 1)) from error
        if not isinstance(row, dict):
            raise ArchivePageContractRefusal("vector_row_shape", str(index + 1))
        rows.append(row)
    return rows


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    if len(pairs) > MAX_VECTOR_OBJECT_FIELDS:
        raise ArchivePageContractRefusal("json_object_fields", str(len(pairs)))
    result: dict[str, Any] = {}
    for index in range(MAX_VECTOR_OBJECT_FIELDS):
        if index >= len(pairs):
            break
        key, value = pairs[index]
        if key in result:
            raise ArchivePageContractRefusal("duplicate_json_key", key)
        result[key] = value
    return result


def _verify_compiled_contract(contract: dict[str, Any]) -> None:
    if contract.get("meta") != COMPILED_META:
        raise ArchivePageContractRefusal("compiled_contract_drift", "meta")
    if contract.get("constants") != COMPILED_CONSTANTS:
        raise ArchivePageContractRefusal("compiled_contract_drift", "constants")
    if contract.get("bounds") != COMPILED_BOUNDS:
        raise ArchivePageContractRefusal("compiled_contract_drift", "bounds")
    if contract.get("layouts") != COMPILED_LAYOUTS:
        raise ArchivePageContractRefusal("compiled_contract_drift", "layouts")
    if contract.get("production_decoder") != "prohibited":
        raise ArchivePageContractRefusal("compiled_contract_drift", "production_decoder")
    required = contract.get("vector_kinds", {}).get("required")
    if not isinstance(required, list) or set(required) != REQUIRED_VECTOR_KINDS:
        raise ArchivePageContractRefusal("compiled_contract_drift", "vector_kinds")


def _validated_rows(vectors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(vectors) > MAX_VECTOR_ROWS:
        raise ArchivePageContractRefusal("too_many_rows", str(len(vectors)))
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
            raise ArchivePageContractRefusal("vector_row_shape", str(index + 1))
        if row_id in seen_ids:
            raise ArchivePageContractRefusal("duplicate_vector_id", row_id)
        seen_ids.add(row_id)
    return rows


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ArchivePageContractRefusal("invalid_text", field)
    encoded = value.encode("utf-8")
    if len(encoded) > MAX_TEXT_BYTES or b"\x00" in encoded:
        raise ArchivePageContractRefusal("invalid_text", field)
    return value


def _key(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > MAX_ID_BYTES:
        raise ArchivePageContractRefusal("invalid_key", field)
    first, rest = value[0], value[1:]
    if not (first.isascii() and (first.islower() or first.isdigit())):
        raise ArchivePageContractRefusal("invalid_key", field)
    if not all(
        char.isascii() and (char.islower() or char.isdigit() or char == "-") for char in rest
    ):
        raise ArchivePageContractRefusal("invalid_key", field)
    return value


def _page_ref(value: object, field: str) -> tuple[str, str]:
    if not isinstance(value, dict) or set(value) != {"kind", "id"}:
        raise ArchivePageContractRefusal("invalid_identity", field)
    kind = value.get("kind")
    identity = value.get("id")
    if kind not in KIND_TAGS or not isinstance(identity, str):
        raise ArchivePageContractRefusal("invalid_identity", field)
    if len(identity) != ID_WIDTHS[kind] or not identity.isascii() or not identity.isdigit():
        raise ArchivePageContractRefusal("invalid_identity", field)
    return kind, identity


def _page_key(ref: tuple[str, str]) -> str:
    return f"{ref[0]}/{ref[1]}"


_LOWER_HEX = frozenset("0123456789abcdef")


def _digest32(value: object, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in _LOWER_HEX for char in value)
    ):
        raise ArchivePageContractRefusal("invalid_digest", field)
    if len(bytes.fromhex(value)) != 32:
        raise ArchivePageContractRefusal("invalid_digest", field)
    return value


def _tick(value: object, field: str, *, allow_zero: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ArchivePageContractRefusal("invalid_tick", field)
    if value < 0 or (value == 0 and not allow_zero) or value > MAX_I64:
        raise ArchivePageContractRefusal("invalid_tick", field)
    return value


def _citation(value: object, field: str) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {"source_id", "locator"}:
        raise ArchivePageContractRefusal("invalid_citation", field)
    return {
        "source_id": _text(value.get("source_id"), f"{field}.source_id"),
        "locator": _text(value.get("locator"), f"{field}.locator"),
    }


def _signals(value: object, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > MAX_SIGNALS:
        raise ArchivePageContractRefusal("invalid_signals", field)
    signals: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, signal in enumerate(value):
        path = f"{field}[{index}]"
        if not isinstance(signal, dict) or set(signal) != {
            "grant_key",
            "label",
            "value",
            "citation",
        }:
            raise ArchivePageContractRefusal("invalid_signals", path)
        grant_key = _key(signal.get("grant_key"), f"{path}.grant_key")
        if grant_key in seen:
            raise ArchivePageContractRefusal("duplicate_signal_key", path)
        seen.add(grant_key)
        signals.append(
            {
                "grant_key": grant_key,
                "label": _text(signal.get("label"), f"{path}.label"),
                "value": _text(signal.get("value"), f"{path}.value"),
                "citation": _citation(signal.get("citation"), f"{path}.citation"),
            }
        )
    return signals


def _links(value: object, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > MAX_LINKS:
        raise ArchivePageContractRefusal("invalid_links", field)
    links: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for index, link in enumerate(value):
        path = f"{field}[{index}]"
        if not isinstance(link, dict) or set(link) != {"target", "known_label"}:
            raise ArchivePageContractRefusal("invalid_links", path)
        target = _page_ref(link.get("target"), f"{path}.target")
        if target in seen:
            raise ArchivePageContractRefusal("duplicate_link_target", path)
        seen.add(target)
        links.append(
            {"target": target, "known_label": _text(link.get("known_label"), f"{path}.known_label")}
        )
    return links


def _knowledge(value: object, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > MAX_KNOWLEDGE_GRANTS:
        raise ArchivePageContractRefusal("invalid_knowledge", field)
    grants: list[dict[str, Any]] = []
    seen: set[tuple[tuple[str, str], str]] = set()
    for index, grant in enumerate(value):
        path = f"{field}[{index}]"
        if not isinstance(grant, dict) or set(grant) != {
            "page_ref",
            "grant_key",
            "granted_tick",
            "citation",
        }:
            raise ArchivePageContractRefusal("invalid_knowledge", path)
        page_ref = _page_ref(grant.get("page_ref"), f"{path}.page_ref")
        grant_key = _key(grant.get("grant_key"), f"{path}.grant_key")
        identity = (page_ref, grant_key)
        if identity in seen:
            raise ArchivePageContractRefusal("duplicate_grant", path)
        seen.add(identity)
        grants.append(
            {
                "page_ref": page_ref,
                "grant_key": grant_key,
                "granted_tick": _tick(
                    grant.get("granted_tick"), f"{path}.granted_tick", allow_zero=True
                ),
                "citation": _citation(grant.get("citation"), f"{path}.citation"),
            }
        )
    return grants


def _page_input(data: Any, field: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ArchivePageContractRefusal("invalid_pages", field)
    subject = data.get("subject")
    if not isinstance(subject, dict) or set(subject) != {"kind", "id", "title"}:
        raise ArchivePageContractRefusal("invalid_identity", f"{field}.subject")
    page_ref = _page_ref({k: subject[k] for k in ("kind", "id")}, f"{field}.subject")
    return {
        "page_ref": page_ref,
        "title": _text(subject.get("title"), f"{field}.subject.title"),
        "verified_tick": _tick(data.get("verified_tick"), f"{field}.verified_tick"),
        "tick_content_hash_hex": _digest32(
            data.get("tick_content_hash_hex"), f"{field}.tick_content_hash_hex"
        ),
        "decision_question": _text(data.get("decision_question"), f"{field}.decision_question"),
        "signals": _signals(data.get("signals"), f"{field}.signals"),
        "links": _links(data.get("links"), f"{field}.links"),
    }


def _known_subject(grants: list[dict[str, Any]], page_ref: tuple[str, str]) -> bool:
    return any(
        grant["page_ref"] == page_ref and grant["grant_key"] == "subject" for grant in grants
    )


def _known_field(grants: list[dict[str, Any]], page_ref: tuple[str, str], grant_key: str) -> bool:
    return any(
        grant["page_ref"] == page_ref and grant["grant_key"] == grant_key for grant in grants
    )


def _derived_search_text(page: dict[str, Any], grants: list[dict[str, Any]]) -> str:
    parts = [
        _page_key(page["page_ref"]),
        page["title"],
        page["decision_question"],
    ]
    for signal in page["signals"]:
        if _known_field(grants, page["page_ref"], signal["grant_key"]):
            parts.append(signal["label"])
            parts.append(signal["value"])
    for link in page["links"]:
        if _known_subject(grants, link["target"]):
            parts.append(_page_key(link["target"]))
            parts.append(link["known_label"])
    return " ".join(parts)


def _derived_citations(page: dict[str, Any], grants: list[dict[str, Any]]) -> list[dict[str, str]]:
    citations: list[dict[str, str]] = []
    for grant in grants:
        if grant["page_ref"] == page["page_ref"] and grant["grant_key"] == "subject":
            citations.append(grant["citation"])
            break
    for signal in page["signals"]:
        citation = signal["citation"]
        if (
            _known_field(grants, page["page_ref"], signal["grant_key"])
            and citation not in citations
        ):
            citations.append(citation)
    return citations


def _expected_citations(value: object, field: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ArchivePageContractRefusal("invalid_citations", field)
    return [_citation(item, f"{field}[{index}]") for index, item in enumerate(value)]


def _hash_bytes(hasher: Any, text: str) -> None:
    encoded = text.encode("utf-8")
    hasher.update(len(encoded).to_bytes(8, "big"))
    hasher.update(encoded)


def _hash_page_ref(hasher: Any, ref: tuple[str, str]) -> None:
    hasher.update(bytes([KIND_TAGS[ref[0]]]))
    _hash_bytes(hasher, ref[1])


def compose_batch_sha256(data: dict[str, Any]) -> str:
    """Reconstruct the exact dirty-batch SHA-256 from semantic vector inputs."""
    resolve_tick = _tick(data.get("resolve_tick"), "resolve_tick")
    tick_hash = _digest32(data.get("tick_content_hash_hex"), "tick_content_hash_hex")
    pages_value = data.get("pages")
    if not isinstance(pages_value, list) or len(pages_value) > MAX_PAGES:
        raise ArchivePageContractRefusal("invalid_pages", "pages")
    pages = [_page_input(page, f"pages[{index}]") for index, page in enumerate(pages_value)]
    subjects = [page["page_ref"] for page in pages]
    if len(set(subjects)) != len(subjects):
        raise ArchivePageContractRefusal("duplicate_subject", "pages")
    for page in pages:
        if page["verified_tick"] != resolve_tick or page["tick_content_hash_hex"] != tick_hash:
            raise ArchivePageContractRefusal("receipt_mismatch", "pages")
    hasher = hashlib.sha256()
    hasher.update(DIRTY_BATCH_DOMAIN_ASCII_NUL.encode("ascii") + b"\x00")
    hasher.update(resolve_tick.to_bytes(8, "big"))
    hasher.update(bytes.fromhex(tick_hash))
    hasher.update(len(pages).to_bytes(8, "big"))
    for page in pages:
        _hash_page_ref(hasher, page["page_ref"])
        _hash_bytes(hasher, page["title"])
        hasher.update(page["verified_tick"].to_bytes(8, "big"))
        hasher.update(bytes.fromhex(page["tick_content_hash_hex"]))
        _hash_bytes(hasher, page["decision_question"])
        hasher.update(len(page["signals"]).to_bytes(8, "big"))
        for signal in page["signals"]:
            _hash_bytes(hasher, signal["grant_key"])
            _hash_bytes(hasher, signal["label"])
            _hash_bytes(hasher, signal["value"])
            _hash_bytes(hasher, signal["citation"]["source_id"])
            _hash_bytes(hasher, signal["citation"]["locator"])
        hasher.update(len(page["links"]).to_bytes(8, "big"))
        for link in page["links"]:
            _hash_page_ref(hasher, link["target"])
            _hash_bytes(hasher, link["known_label"])
    return hasher.hexdigest()


def _verify_render(row: dict[str, Any]) -> str | None:
    data = row["data"]
    page = _page_input(data, "data")
    grants = _knowledge(data.get("knowledge"), "data.knowledge")
    if not _known_subject(grants, page["page_ref"]):
        return f"{row['id']}: render vector lacks the subject grant"
    markdown_hex = data.get("markdown_hex")
    if (
        not isinstance(markdown_hex, str)
        or not markdown_hex
        or len(markdown_hex) % 2 != 0
        or len(markdown_hex) > MAX_PAGE_BYTES * 2
    ):
        return f"{row['id']}: invalid markdown hex"
    try:
        markdown_bytes = bytes.fromhex(markdown_hex)
    except ValueError:
        return f"{row['id']}: invalid markdown hex"
    if len(markdown_bytes) > MAX_PAGE_BYTES:
        return f"{row['id']}: markdown exceeds the page byte bound"
    if hashlib.sha256(markdown_bytes).hexdigest() != data.get("content_sha256_hex"):
        return f"{row['id']}: content SHA-256 mismatch"
    try:
        markdown = markdown_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return f"{row['id']}: markdown is not exact UTF-8"
    page_key = _page_key(page["page_ref"])
    front_matter = (
        f"schema: {FRONT_MATTER_CONTRACT_ID}",
        f"subject: {page_key}",
        f"verified_tick: {page['verified_tick']}",
        f"tick_content_hash: {page['tick_content_hash_hex']}",
        f"# {page['title']}",
    )
    for line in front_matter:
        if line not in markdown:
            return f"{row['id']}: markdown front-matter drift: {line}"
    if page["decision_question"] not in markdown:
        return f"{row['id']}: decision question drift"
    granted = 0
    for signal in page["signals"]:
        bullet = (
            f"- **{signal['label']}:** {signal['value']} — "
            f"{signal['citation']['source_id']}; {signal['citation']['locator']}"
        )
        if _known_field(grants, page["page_ref"], signal["grant_key"]):
            granted += 1
            if bullet not in markdown:
                return f"{row['id']}: known signal drift: {signal['grant_key']}"
        else:
            if f"**{signal['label']}:**" in markdown:
                return f"{row['id']}: ungranted signal rendered: {signal['grant_key']}"
            leaked_material = next(
                (
                    material_name
                    for material_name, material in (
                        ("value", signal["value"]),
                        ("locator", signal["citation"]["locator"]),
                    )
                    if material in markdown
                ),
                None,
            )
            if leaked_material is not None:
                return (
                    f"{row['id']}: ungranted signal {leaked_material} leaked: {signal['grant_key']}"
                )
    if ("## Signals" in markdown) != (granted > 0):
        return f"{row['id']}: signals section presence drift"
    if page["links"] and "## Related" not in markdown:
        return f"{row['id']}: related section missing"
    for link in page["links"]:
        target_key = _page_key(link["target"])
        if _known_subject(grants, link["target"]):
            if f"[[{target_key}|{link['known_label']}]]" not in markdown:
                return f"{row['id']}: known link drift: {target_key}"
        else:
            redlink_token = f"[[{target_key}]]"
            known_link_token = f"[[{target_key}|{link['known_label']}]]"
            if redlink_token not in markdown:
                return f"{row['id']}: redlink drift: {target_key}"
            if f"[[{target_key}|" in markdown or known_link_token in markdown:
                return f"{row['id']}: redlink leaked the known label: {target_key}"
    if _derived_search_text(page, grants) != data.get("search_text"):
        return f"{row['id']}: search_text derivation mismatch"
    if _derived_citations(page, grants) != _expected_citations(
        data.get("citations"), "data.citations"
    ):
        return f"{row['id']}: citation derivation mismatch"
    return None


def _verify_refusal(row: dict[str, Any]) -> str | None:
    data = row["data"]
    if data.get("operation") != "render":
        return f"{row['id']}: unknown refusal operation"
    if data.get("expected_code") != "unknown_subject":
        return f"{row['id']}: unknown refusal code"
    page = _page_input(data, "data")
    grants = _knowledge(data.get("knowledge"), "data.knowledge")
    if _known_subject(grants, page["page_ref"]):
        return f"{row['id']}: refusal is not forced; the subject grant is present"
    return None


def _verify_batch(row: dict[str, Any]) -> str | None:
    try:
        actual = compose_batch_sha256(row["data"])
    except ArchivePageContractRefusal as error:
        return f"{row['id']}: {error.code}"
    if actual != row["data"].get("sha256_hex"):
        return f"{row['id']}: batch SHA-256 mismatch"
    return None


def _verify_identity(row: dict[str, Any], root: Path) -> str | None:
    data = row["data"]
    if data.get("template_path") != TEMPLATE_PATH or data.get("schema_path") != SCHEMA_PATH:
        return f"{row['id']}: pinned source path drift"
    template_bytes = _bounded_file_bytes(root / TEMPLATE_PATH, MAX_PAGE_BYTES, "file_read")
    schema_bytes = _bounded_file_bytes(root / SCHEMA_PATH, MAX_CONTRACT_BYTES, "file_read")
    atom_schema_bytes = _bounded_file_bytes(
        root / ATOM_SCHEMA_PATH, MAX_CONTRACT_BYTES, "file_read"
    )
    template_sha256 = hashlib.sha256(template_bytes).hexdigest()
    if template_sha256 != TEMPLATE_SHA256:
        return f"{row['id']}: template SHA-256 drift from contract constant"
    if template_sha256 != data.get("template_sha256_hex"):
        return f"{row['id']}: template SHA-256 mismatch"
    worker = hashlib.sha256()
    worker.update(WORKER_DOMAIN_ASCII_NUL.encode("ascii") + b"\x00")
    worker.update(schema_bytes)
    worker.update(atom_schema_bytes)
    worker.update(bytes.fromhex(template_sha256))
    if worker.hexdigest() != data.get("worker_contract_sha256_hex"):
        return f"{row['id']}: worker contract SHA-256 mismatch"
    return None


def verify_all(contract: dict[str, Any], vectors: list[dict[str, Any]], root: Path) -> list[str]:
    """Verify all bounded rows and return exact row-scoped mismatches."""
    _verify_compiled_contract(contract)
    rows = _validated_rows(vectors)
    kinds = {row["kind"] for row in rows}
    if kinds != REQUIRED_VECTOR_KINDS:
        raise ArchivePageContractRefusal("vector_kind_drift", repr(kinds))
    batch_ids = {row["id"] for row in rows if row["kind"] == "batch"}
    if batch_ids != set(REQUIRED_BATCH_ROW_IDS):
        raise ArchivePageContractRefusal("vector_id_drift", repr(sorted(batch_ids)))
    errors: list[str] = []
    for row in rows:
        kind = row["kind"]
        error: str | None = None
        if kind == "render":
            error = _verify_render(row)
        elif kind == "refusal":
            error = _verify_refusal(row)
        elif kind == "batch":
            error = _verify_batch(row)
        elif kind == "identity":
            error = _verify_identity(row, root)
        if error is not None:
            errors.append(error)
    return errors


def main() -> int:
    """Verify repository contract paths or explicit alternatives."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("contracts/archive_page_v1.yaml"),
    )
    parser.add_argument(
        "--vectors",
        type=Path,
        default=Path("contracts/archive_page_v1_vectors.jsonl"),
    )
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        errors = verify_all(load_contract(arguments.schema), load_vectors(arguments.vectors), root)
    except ArchivePageContractRefusal as error:
        print(error)
        return 1
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
