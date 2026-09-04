#!/usr/bin/env python3
"""Independently verify the bounded BabylonMarkdownV1 profile contract corpus."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml
from markdown_it import MarkdownIt
from markdown_it.token import Token

PROFILE_ID = "babylon-markdown.v1"
CITATION_LINE_REGEX = (
    r"^- \*\*(?P<label>[^*]+)\*\*: (?P<value>.+) — (?P<source_id>[^;]+); (?P<locator>.+)$"
)
CHIP_SEPARATOR = " · "
GRANTED_LINK_FORM = "[{known_label}](subject:{kind}/{id})"
BARE_LINK_FORM = "[](subject:{kind}/{id})"
PENDING_LINK_FORM = "~~[{known_label}](subject:{kind}/{id})~~"
EXPORT_LINK_FORM = "[{known_label}](./{kind}/{id}.md)"
COUNTY_KIND = "county"
PLACE_KIND = "place"
COUNTY_ID_BYTES = 5
PLACE_ID_BYTES = 7
GFM_VERSION = "0.29"
MAX_MARKDOWN_BYTES = 1_048_576
MAX_CONTRACT_BYTES = 32_768
MAX_VECTOR_ROWS = 16
MAX_VECTOR_LINE_BYTES = 16_384
MAX_VECTOR_OBJECT_FIELDS = 64
SUBJECT_ID_WIDTHS = {COUNTY_KIND: COUNTY_ID_BYTES, PLACE_KIND: PLACE_ID_BYTES}
REQUIRED_VECTOR_KINDS = {"valid", "refusal", "identity"}
VALID_ROW_IDS = (
    "valid-archive-page-granted-links",
    "valid-archive-page-bare-link",
    "valid-assembled-profile-forms",
)
REFUSAL_ROW_IDS = (
    "refusal-crlf-ending",
    "refusal-raw-html",
    "refusal-disallowed-link-scheme",
    "refusal-malformed-subject-link",
    "refusal-stray-open-bracket",
    "refusal-strikethrough-without-link",
)
COMPILED_META = {
    "contract": "BabylonMarkdownV1",
    "version": 1,
    "issue": "PER-23",
    "profile": "GFM 0.29 plus the subject URI scheme and nothing else",
    "digest": "SHA-256 diagnostic; exact bytes govern retry equality",
}
COMPILED_CONSTANTS = {
    "profile_id": PROFILE_ID,
    "citation_line_regex": CITATION_LINE_REGEX,
    "chip_separator": CHIP_SEPARATOR,
    "granted_link_form": GRANTED_LINK_FORM,
    "bare_link_form": BARE_LINK_FORM,
    "pending_link_form": PENDING_LINK_FORM,
    "export_link_form": EXPORT_LINK_FORM,
    "county_kind": COUNTY_KIND,
    "place_kind": PLACE_KIND,
    "county_id_bytes": COUNTY_ID_BYTES,
    "place_id_bytes": PLACE_ID_BYTES,
    "gfm_version": GFM_VERSION,
}
COMPILED_BOUNDS = {
    "contract_bytes": MAX_CONTRACT_BYTES,
    "vector_rows": MAX_VECTOR_ROWS,
    "vector_line_bytes": MAX_VECTOR_LINE_BYTES,
    "vector_object_fields": MAX_VECTOR_OBJECT_FIELDS,
    "markdown_bytes": MAX_MARKDOWN_BYTES,
}
COMPILED_LAYOUTS = {
    "link_token_v1": {
        "granted": GRANTED_LINK_FORM,
        "bare": BARE_LINK_FORM,
        "pending_display_only": PENDING_LINK_FORM,
        "kind_allowlist": [COUNTY_KIND, PLACE_KIND],
        "id_width_bytes": {COUNTY_KIND: COUNTY_ID_BYTES, PLACE_KIND: PLACE_ID_BYTES},
        "id_charset": "ASCII digits",
    },
    "citation_line_v1": {
        "regex": CITATION_LINE_REGEX,
        "example": "- **Median wage:** 25.000000 — committed-tick-v1; campaign/2/oakland",
    },
    "git_export_v1": {
        "granted_rewrite": (
            "[{known_label}](subject:{kind}/{id}) -> [{known_label}](./{kind}/{id}.md)"
        ),
        "bare_rewrite": "[](subject:{kind}/{id}) -> unknown {kind} · {id}",
        "pending_rewrite": (
            "~~[{known_label}](subject:{kind}/{id})~~ -> ~~[{known_label}](./{kind}/{id}.md)~~"
        ),
    },
    "fog_chip_v1": {
        "form": "unknown {kind} · {id}",
        "label_bytes": 0,
        "separator": CHIP_SEPARATOR,
    },
}
CITATION_LINE = re.compile(CITATION_LINE_REGEX)
PARSER = MarkdownIt("gfm-like", {"linkify": False})


class BabylonMarkdownContractRefusal(ValueError):
    """One typed independent-verifier refusal."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


def _bounded_file_bytes(path: Path, maximum: int, code: str) -> bytes:
    try:
        size = path.stat().st_size
    except OSError as error:
        raise BabylonMarkdownContractRefusal("file_read", str(path)) from error
    if size > maximum:
        raise BabylonMarkdownContractRefusal(code, str(size))
    try:
        return path.read_bytes()
    except OSError as error:
        raise BabylonMarkdownContractRefusal("file_read", str(path)) from error


def load_contract(path: Path) -> dict[str, Any]:
    """Load one bounded YAML mapping."""
    raw = _bounded_file_bytes(path, MAX_CONTRACT_BYTES, "schema_too_large")
    try:
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError as error:
        raise BabylonMarkdownContractRefusal("invalid_schema", str(path)) from error
    if not isinstance(loaded, dict):
        raise BabylonMarkdownContractRefusal("invalid_schema", "root mapping")
    return loaded


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    if len(pairs) > MAX_VECTOR_OBJECT_FIELDS:
        raise BabylonMarkdownContractRefusal("json_object_fields", str(len(pairs)))
    result: dict[str, Any] = {}
    for index in range(MAX_VECTOR_OBJECT_FIELDS):
        if index >= len(pairs):
            break
        key, value = pairs[index]
        if key in result:
            raise BabylonMarkdownContractRefusal("duplicate_json_key", key)
        result[key] = value
    return result


def load_vectors(path: Path) -> list[dict[str, Any]]:
    """Load bounded JSONL rows without an unbounded whole-file read."""
    maximum = MAX_VECTOR_ROWS * (MAX_VECTOR_LINE_BYTES + 1)
    raw = _bounded_file_bytes(path, maximum, "vectors_too_large")
    lines = raw.splitlines()
    if len(lines) > MAX_VECTOR_ROWS:
        raise BabylonMarkdownContractRefusal("too_many_rows", str(len(lines)))
    rows: list[dict[str, Any]] = []
    for index in range(MAX_VECTOR_ROWS):
        if index >= len(lines):
            break
        line = lines[index]
        if not line or len(line) > MAX_VECTOR_LINE_BYTES:
            raise BabylonMarkdownContractRefusal("invalid_line_length", str(index + 1))
        try:
            row = json.loads(line, object_pairs_hook=_unique_json_object)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise BabylonMarkdownContractRefusal("invalid_json", str(index + 1)) from error
        if not isinstance(row, dict):
            raise BabylonMarkdownContractRefusal("vector_row_shape", str(index + 1))
        rows.append(row)
    return rows


def _verify_compiled_contract(contract: dict[str, Any]) -> None:
    if contract.get("meta") != COMPILED_META:
        raise BabylonMarkdownContractRefusal("compiled_contract_drift", "meta")
    if contract.get("constants") != COMPILED_CONSTANTS:
        raise BabylonMarkdownContractRefusal("compiled_contract_drift", "constants")
    if contract.get("bounds") != COMPILED_BOUNDS:
        raise BabylonMarkdownContractRefusal("compiled_contract_drift", "bounds")
    if contract.get("layouts") != COMPILED_LAYOUTS:
        raise BabylonMarkdownContractRefusal("compiled_contract_drift", "layouts")
    if contract.get("production_decoder") != "prohibited":
        raise BabylonMarkdownContractRefusal("compiled_contract_drift", "production_decoder")
    required = contract.get("vector_kinds", {}).get("required")
    if not isinstance(required, list) or set(required) != REQUIRED_VECTOR_KINDS:
        raise BabylonMarkdownContractRefusal("compiled_contract_drift", "vector_kinds")


def _validated_rows(vectors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(vectors) > MAX_VECTOR_ROWS:
        raise BabylonMarkdownContractRefusal("too_many_rows", str(len(vectors)))
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
            raise BabylonMarkdownContractRefusal("vector_row_shape", str(index + 1))
        if row_id in seen_ids:
            raise BabylonMarkdownContractRefusal("duplicate_vector_id", row_id)
        seen_ids.add(row_id)
    return rows


def _scan_link_tokens(text: str) -> list[tuple[str, str, str]] | str:
    """Scan byte-level link tokens; return (label, kind, id) or a refusal code."""
    tokens: list[tuple[str, str, str]] = []
    cursor = 0
    length = len(text)
    while cursor < length:
        if text[cursor] == "[":
            close = text.find("]", cursor + 1)
            if close < 0 or close + 1 >= length or text[close + 1] != "(":
                return "malformed_subject_link"
            end = text.find(")", close + 2)
            if end < 0:
                return "malformed_subject_link"
            label = text[cursor + 1 : close]
            if "[" in label or "]" in label:
                return "malformed_subject_link"
            destination = text[close + 2 : end]
            tokens.append((label, destination, "link"))
            cursor = end + 1
            continue
        if text.startswith("~~", cursor):
            link_start = cursor + 2
            if link_start >= length or text[link_start] != "[":
                return "strikethrough_without_link"
            close = text.find("]", link_start + 1)
            if close < 0 or close + 1 >= length or text[close + 1] != "(":
                return "strikethrough_without_link"
            end = text.find(")", close + 2)
            if end < 0 or not text.startswith("~~", end + 1):
                return "strikethrough_without_link"
            label = text[link_start + 1 : close]
            destination = text[close + 2 : end]
            tokens.append((label, destination, "pending"))
            cursor = end + 3
            continue
        cursor += 1
    return tokens


def _validate_destination(destination: str) -> str | None:
    """Return a refusal code or None when the destination is a pinned subject form."""
    rest = destination.removeprefix("subject:")
    if rest == destination:
        return "disallowed_link_scheme"
    kind, separator, subject_id = rest.partition("/")
    if not separator or kind not in SUBJECT_ID_WIDTHS:
        return "malformed_subject_link"
    width = SUBJECT_ID_WIDTHS[kind]
    if len(subject_id) != width or not subject_id.isascii() or not subject_id.isdigit():
        return "malformed_subject_link"
    return None


def _parser_link_tokens(text: str) -> list[str]:
    """Collect hrefs the GFM parser actually recognizes as link tokens."""

    def walk(tokens: list[Token]) -> list[str]:
        hrefs: list[str] = []
        for token in tokens:
            if token.type == "link_open":
                href = token.attrs.get("href")
                if isinstance(href, str):
                    hrefs.append(href)
            if token.children:
                hrefs.extend(walk(token.children))
        return hrefs

    return walk(PARSER.parse(text))


def validate_profile(markdown_bytes: bytes) -> str | None:
    """Return the first profile refusal code, or None when the bytes conform."""
    if len(markdown_bytes) > MAX_MARKDOWN_BYTES:
        return "too_large"
    try:
        text = markdown_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return "not_utf8"
    if "\r" in text:
        return "crlf_ending"
    if "<" in text:
        return "raw_html"
    scanned = _scan_link_tokens(text)
    if isinstance(scanned, str):
        return scanned
    parsed_hrefs = _parser_link_tokens(text)
    if len(parsed_hrefs) != len(scanned):
        return "link_tokens_not_gfm_visible"
    for (label, destination, _form), href in zip(scanned, parsed_hrefs, strict=True):
        refusal = _validate_destination(destination)
        if refusal is not None:
            return refusal
        if href != destination:
            return "link_tokens_not_gfm_visible"
        if not label and destination != href:
            return "malformed_subject_link"
    return None


def fog_chip(subject_kind: str, subject_id: str) -> str:
    """Synthesize the bare-link fog chip from public structure alone."""
    return f"unknown {subject_kind}{CHIP_SEPARATOR}{subject_id}"


def git_export_rewrite(markdown: str) -> str:
    """Derive the Git export bytes for already-validated Markdown text."""
    output: list[str] = []
    cursor = 0
    length = len(markdown)
    while cursor < length:
        if markdown[cursor] == "[":
            close = markdown.find("]", cursor)
            end = markdown.find(")", close)
            label = markdown[cursor + 1 : close]
            destination = markdown[close + 2 : end]
            rest = destination.removeprefix("subject:")
            kind, _, subject_id = rest.partition("/")
            if not label:
                output.append(fog_chip(kind, subject_id))
            else:
                output.append(f"[{label}](./{kind}/{subject_id}.md)")
            cursor = end + 1
            continue
        if markdown.startswith("~~", cursor):
            output.append("~~")
            link_start = cursor + 2
            close = markdown.find("]", link_start)
            end = markdown.find(")", close)
            label = markdown[link_start + 1 : close]
            destination = markdown[close + 2 : end]
            rest = destination.removeprefix("subject:")
            kind, _, subject_id = rest.partition("/")
            if not label:
                output.append(fog_chip(kind, subject_id))
            else:
                output.append(f"[{label}](./{kind}/{subject_id}.md)")
            output.append("~~")
            cursor = end + 3
            continue
        output.append(markdown[cursor])
        cursor += 1
    return "".join(output)


def _row_bytes(row: dict[str, Any], field: str) -> bytes:
    hex_text = row["data"].get(field)
    if not isinstance(hex_text, str):
        raise BabylonMarkdownContractRefusal("vector_row_shape", f"{row['id']}.{field}")
    try:
        return bytes.fromhex(hex_text)
    except ValueError as error:
        raise BabylonMarkdownContractRefusal("invalid_hex", row["id"]) from error


def _verify_valid(row: dict[str, Any]) -> str | None:
    markdown_bytes = _row_bytes(row, "markdown_hex")
    refusal = validate_profile(markdown_bytes)
    if refusal is not None:
        return f"{row['id']}: valid row refused: {refusal}"
    export = git_export_rewrite(markdown_bytes.decode("utf-8"))
    if export.encode("utf-8") != _row_bytes(row, "export_hex"):
        return f"{row['id']}: git export rewrite mismatch"
    if row["id"] == "valid-archive-page-bare-link":
        if "unknown place · 2668880" not in export:
            return f"{row['id']}: bare link export misses the fog chip"
        if "Riverview" in export:
            return f"{row['id']}: bare link export leaked label bytes"
    return None


def _verify_refusal(row: dict[str, Any]) -> str | None:
    expected = row["data"].get("expected_code")
    if not isinstance(expected, str):
        return f"{row['id']}: refusal row lacks an expected code"
    refusal = validate_profile(_row_bytes(row, "markdown_hex"))
    if refusal is None:
        return f"{row['id']}: refusal row validated"
    if refusal != expected:
        return f"{row['id']}: refusal code {refusal} != {expected}"
    return None


def _verify_identity(row: dict[str, Any]) -> str | None:
    data = row["data"]
    if data.get("profile_id") != PROFILE_ID:
        return f"{row['id']}: profile id drift"
    if data.get("citation_line_regex") != CITATION_LINE_REGEX:
        return f"{row['id']}: citation-line regex drift"
    if data.get("chip_separator") != CHIP_SEPARATOR:
        return f"{row['id']}: chip separator drift"
    if data.get("fog_chip_place_2674900") != fog_chip(PLACE_KIND, "2674900"):
        return f"{row['id']}: fog chip drift"
    citation = data.get("citation_line_example")
    if citation is not None and CITATION_LINE.match(citation) is None:
        return f"{row['id']}: citation-line example drifts"
    return None


def verify_all(contract: dict[str, Any], vectors: list[dict[str, Any]]) -> list[str]:
    """Verify all bounded rows and return exact row-scoped mismatches."""
    _verify_compiled_contract(contract)
    rows = _validated_rows(vectors)
    kinds = {row["kind"] for row in rows}
    if kinds != REQUIRED_VECTOR_KINDS:
        raise BabylonMarkdownContractRefusal("vector_kind_drift", repr(kinds))
    valid_ids = [row["id"] for row in rows if row["kind"] == "valid"]
    if valid_ids != list(VALID_ROW_IDS):
        raise BabylonMarkdownContractRefusal("vector_id_drift", repr(valid_ids))
    refusal_ids = [row["id"] for row in rows if row["kind"] == "refusal"]
    if refusal_ids != list(REFUSAL_ROW_IDS):
        raise BabylonMarkdownContractRefusal("vector_id_drift", repr(refusal_ids))
    errors: list[str] = []
    for row in rows:
        kind = row["kind"]
        error: str | None = None
        if kind == "valid":
            error = _verify_valid(row)
        elif kind == "refusal":
            error = _verify_refusal(row)
        elif kind == "identity":
            error = _verify_identity(row)
        if error is not None:
            errors.append(error)
    return errors


def main() -> int:
    """Verify repository contract paths or explicit alternatives."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("contracts/babylon_markdown_v1.yaml"),
    )
    parser.add_argument(
        "--vectors",
        type=Path,
        default=Path("contracts/babylon_markdown_v1_vectors.jsonl"),
    )
    arguments = parser.parse_args()
    try:
        errors = verify_all(load_contract(arguments.schema), load_vectors(arguments.vectors))
    except BabylonMarkdownContractRefusal as error:
        print(error)
        return 1
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
