#!/usr/bin/env python3
"""Independently verify the bounded PER-319 QCEW county economics contract."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
import struct
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path, PurePosixPath
from typing import Any, Final

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode

EXPECTED_META: Final = {
    "contract": "QcewCountyEconomicsV1",
    "version": 1,
    "issue": "PER-319",
    "parent": "PER-10",
}
EXPECTED_CLASSIFICATIONS: Final = {
    "source_filenames_bytes_and_vintage": "Observed",
    "artifact_bytes_rows_columns_and_values": "Observed",
    "semantic_digests": "Derived",
    "canonical_formats_ordering_and_column_names": "Designed",
    "bounds_refusals_absences_and_lineage": "Designed",
}
EXPECTED_SOURCE_MANIFEST: Final = "tools/qcew_county_economics_v1_source_manifest.json"
COLUMNS: Final = (
    "county_geoid",
    "annual_avg_estabs_count",
    "annual_avg_emplvl",
    "total_annual_wages",
    "annual_avg_wkly_wage",
)
EXPECTED_ABSENCES: Final = {
    "disclosure_flag_rows",
    "suppressed_rows",
    "industry_detail",
    "ownership_splits",
    "derived_or_rounded_values",
    "postgresql_schema",
    "runtime_importer",
    "cutover_authority",
}
EXPECTED_BOUNDS: Final = {
    "contract_bytes": 65_536,
    "source_manifest_bytes": 131_072,
    "source_file_bytes": 4_194_304,
    "artifact_bytes": 1_048_576,
    "artifact_uncompressed_bytes": 33_554_432,
    "artifact_rows": 2_048,
    "csv_field_bytes": 4_194_304,
}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
ASCII_DIGITS = re.compile(r"^[0-9]+$")
GEOID = re.compile(r"^26[0-1][0-9]{2}$")


class QcewCountyEconomicsRefusal(ValueError):
    """One typed refusal from the independent PER-319 verifier."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


class _UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeyLoader, node: MappingNode, deep: bool = False
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


def _safe_load_unique(raw: bytes) -> Any:
    loader = _UniqueKeyLoader(raw)
    try:
        return loader.get_single_data()
    finally:
        loader.dispose()


def _bounded_bytes(path: Path, maximum: int, code: str) -> bytes:
    try:
        size = path.stat().st_size
    except OSError as error:
        raise QcewCountyEconomicsRefusal("file_read", str(path)) from error
    if size > maximum:
        raise QcewCountyEconomicsRefusal(code, str(size))
    try:
        return path.read_bytes()
    except OSError as error:
        raise QcewCountyEconomicsRefusal("file_read", str(path)) from error


def load_contract(path: Path) -> dict[str, Any]:
    """Load one bounded YAML contract mapping with duplicate-key refusal."""
    raw = _bounded_bytes(path, EXPECTED_BOUNDS["contract_bytes"], "contract_size")
    try:
        document = _safe_load_unique(raw)
    except yaml.YAMLError as error:
        raise QcewCountyEconomicsRefusal("invalid_contract", str(path)) from error
    if not isinstance(document, dict):
        raise QcewCountyEconomicsRefusal("invalid_contract", "root mapping")
    return document


def _require_sha256(value: object, detail: str) -> str:
    if not isinstance(value, str) or SHA256.fullmatch(value) is None:
        raise QcewCountyEconomicsRefusal("contract_sha256", detail)
    return value


def verify_contract(contract: dict[str, Any]) -> None:
    """Verify the closed contract shape and declared authority boundary."""
    if set(contract) != {
        "meta",
        "classifications",
        "bounds",
        "source",
        "artifact",
        "declared_absences",
        "lineage",
    }:
        raise QcewCountyEconomicsRefusal("contract_shape", "root")
    if (
        contract.get("meta") != EXPECTED_META
        or contract.get("classifications") != EXPECTED_CLASSIFICATIONS
        or contract.get("bounds") != EXPECTED_BOUNDS
    ):
        raise QcewCountyEconomicsRefusal("contract_shape", "meta_classifications_or_bounds")
    source = contract.get("source")
    if not isinstance(source, dict) or set(source) != {
        "manifest",
        "manifest_sha256",
        "vintage",
        "state_fips",
        "area_glob",
        "agglvl_code",
        "own_code",
        "files",
    }:
        raise QcewCountyEconomicsRefusal("contract_shape", "source")
    if (
        source.get("manifest") != EXPECTED_SOURCE_MANIFEST
        or source.get("vintage") != 2024
        or source.get("state_fips") != "26"
        or source.get("area_glob") != "2024.annual 26* County, Michigan.csv"
        or source.get("agglvl_code") != 70
        or source.get("own_code") != "0"
        or source.get("files") != 83
    ):
        raise QcewCountyEconomicsRefusal("contract_shape", "source authority")
    _require_sha256(source.get("manifest_sha256"), "source_manifest")

    artifact = contract.get("artifact")
    if not isinstance(artifact, dict) or set(artifact) != {
        "name",
        "path",
        "format",
        "compression",
        "rows",
        "columns",
        "ordering",
        "sha256",
        "semantic_sha256",
    }:
        raise QcewCountyEconomicsRefusal("contract_shape", "artifact")
    if (
        artifact.get("name") != "qcew_county_economics_mi_2024"
        or artifact.get("path")
        != "src/babylon/data/reference/economy/qcew_county_economics_mi_2024.csv.gz"
        or artifact.get("format") != "csv.gz"
        or artifact.get("compression") != "gzip-mtime-0"
        or artifact.get("columns") != list(COLUMNS)
        or artifact.get("ordering") != "county_geoid-ascending"
        or isinstance(artifact.get("rows"), bool)
        or not isinstance(artifact.get("rows"), int)
        or not 0 < artifact["rows"] <= EXPECTED_BOUNDS["artifact_rows"]
    ):
        raise QcewCountyEconomicsRefusal("contract_shape", "artifact")
    _require_sha256(artifact.get("sha256"), "artifact.sha256")
    _require_sha256(artifact.get("semantic_sha256"), "artifact.semantic_sha256")

    absences = contract.get("declared_absences")
    if (
        not isinstance(absences, list)
        or set(absences) != EXPECTED_ABSENCES
        or len(absences) != len(EXPECTED_ABSENCES)
    ):
        raise QcewCountyEconomicsRefusal("contract_shape", "declared_absences")
    lineage = contract.get("lineage")
    if not isinstance(lineage, dict) or lineage != {
        "issue": "PER-319",
        "parent": "PER-10",
        "rulings": ["ADR250-R3", "ADR250-R5", "ADR250-R6", "ADR250-R7"],
        "archive_tier": "cursory",
        "database_dependency_owner": "PER-10",
    }:
        raise QcewCountyEconomicsRefusal("contract_shape", "lineage")


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise QcewCountyEconomicsRefusal("source_manifest_duplicate_key", key)
        result[key] = value
    return result


def verify_source_manifest(contract: dict[str, Any], path: Path) -> None:
    """Verify that the acquisition manifest carries the exact contract pin."""
    raw = _bounded_bytes(path, EXPECTED_BOUNDS["source_manifest_bytes"], "source_manifest_size")
    actual_sha256 = hashlib.sha256(raw).hexdigest()
    if actual_sha256 != contract["source"]["manifest_sha256"]:
        raise QcewCountyEconomicsRefusal("source_manifest_sha256", actual_sha256)
    try:
        document = json.loads(raw, object_pairs_hook=_unique_json_object)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise QcewCountyEconomicsRefusal("source_manifest_json", str(path)) from error
    if not isinstance(document, dict) or document != {
        "contract": "QcewCountyEconomicsV1",
        "version": 1,
        "entries": document.get("entries") if isinstance(document, dict) else None,
    }:
        raise QcewCountyEconomicsRefusal("source_manifest_shape", "root")
    entries = document.get("entries")
    if not isinstance(entries, list) or len(entries) != 83:
        raise QcewCountyEconomicsRefusal("source_manifest_shape", "entries")
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"file", "sha256"}:
            raise QcewCountyEconomicsRefusal("source_manifest_entry", repr(entry))
        if SHA256.fullmatch(str(entry.get("sha256", ""))) is None:
            raise QcewCountyEconomicsRefusal("source_manifest_sha256", repr(entry))


def _artifact_path(root: Path, raw: object) -> Path:
    if not isinstance(raw, str):
        raise QcewCountyEconomicsRefusal("artifact_path", repr(raw))
    pure = PurePosixPath(raw)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise QcewCountyEconomicsRefusal("artifact_path", raw)
    return root.joinpath(*pure.parts)


def _semantic_sha256(
    domain: bytes, columns: Sequence[str], rows: Iterable[Sequence[object]]
) -> str:
    digest = hashlib.sha256(domain + b"\0")
    digest.update(json.dumps(list(columns), separators=(",", ":")).encode("ascii") + b"\n")
    for row in rows:
        digest.update(
            json.dumps(list(row), ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode(
                "ascii"
            )
            + b"\n"
        )
    return digest.hexdigest()


def _read_gzip_rows(path: Path, spec: dict[str, Any]) -> list[list[str]]:
    raw = _bounded_bytes(path, EXPECTED_BOUNDS["artifact_bytes"], "artifact_size")
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != spec["sha256"]:
        raise QcewCountyEconomicsRefusal("artifact_sha256", str(path))
    if len(raw) < 10 or raw[:2] != b"\x1f\x8b" or struct.unpack("<I", raw[4:8])[0] != 0:
        raise QcewCountyEconomicsRefusal("artifact_gzip_header", str(path))
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(raw), mode="rb") as compressed:
            decoded = compressed.read(EXPECTED_BOUNDS["artifact_uncompressed_bytes"] + 1)
    except (OSError, EOFError) as error:
        raise QcewCountyEconomicsRefusal("artifact_gzip", str(path)) from error
    if len(decoded) > EXPECTED_BOUNDS["artifact_uncompressed_bytes"]:
        raise QcewCountyEconomicsRefusal("artifact_uncompressed_size", str(path))
    try:
        text = decoded.decode("utf-8")
    except UnicodeDecodeError as error:
        raise QcewCountyEconomicsRefusal("artifact_utf8", str(path)) from error
    csv.field_size_limit(EXPECTED_BOUNDS["csv_field_bytes"])
    try:
        reader = csv.reader(io.StringIO(text, newline=""))
        header = next(reader)
        rows = list(reader)
    except (csv.Error, StopIteration) as error:
        raise QcewCountyEconomicsRefusal("artifact_csv", str(path)) from error
    if header != list(COLUMNS):
        raise QcewCountyEconomicsRefusal("artifact_columns", str(path))
    if len(rows) != spec["rows"] or len(rows) > EXPECTED_BOUNDS["artifact_rows"]:
        raise QcewCountyEconomicsRefusal("artifact_rows", str(path))
    if any(len(row) != len(COLUMNS) for row in rows):
        raise QcewCountyEconomicsRefusal("artifact_row_shape", str(path))
    if any("\x00" in value or "\n" in value or "\r" in value for row in rows for value in row):
        raise QcewCountyEconomicsRefusal("artifact_field", str(path))
    return rows


def _verify_rows(rows: list[list[str]]) -> None:
    keys = [row[0] for row in rows]
    if keys != sorted(keys) or len(keys) != len(set(keys)):
        raise QcewCountyEconomicsRefusal("artifact_order", repr(keys[:3]))
    for row in rows:
        geoid, *values = row
        if GEOID.fullmatch(geoid) is None:
            raise QcewCountyEconomicsRefusal("artifact_geoid", geoid)
        if any(ASCII_DIGITS.fullmatch(value) is None for value in values):
            raise QcewCountyEconomicsRefusal("artifact_value", geoid)


def verify_artifacts(contract: dict[str, Any], root: Path) -> list[list[str]]:
    """Regenerate from the staged CSVs, byte-check, and semantic-check the artifact."""
    import make_qcew_county_economics_artifacts as builder

    spec = contract["artifact"]
    artifact_path = _artifact_path(root, spec["path"])
    rows = _read_gzip_rows(artifact_path, spec)
    _verify_rows(rows)
    semantic = _semantic_sha256(b"babylon.qcew-county-economics.v1", COLUMNS, rows)
    if semantic != spec["semantic_sha256"]:
        raise QcewCountyEconomicsRefusal("artifact_semantic_sha256", semantic)
    regenerated = builder.build(out_path=root / ".verify-qcew-tmp.csv.gz")
    try:
        if regenerated.sha256 != spec["sha256"]:
            raise QcewCountyEconomicsRefusal(
                "artifact_regeneration", f"expected {spec['sha256']}, got {regenerated.sha256}"
            )
        if regenerated.semantic_sha256 != spec["semantic_sha256"]:
            raise QcewCountyEconomicsRefusal(
                "artifact_regeneration_semantic", regenerated.semantic_sha256
            )
    finally:
        (root / ".verify-qcew-tmp.csv.gz").unlink(missing_ok=True)
    return rows


def verify_artifact_manifest(contract: dict[str, Any], path: Path) -> None:
    """Tripwire the hand-maintained second-order registry entry."""
    raw = _bounded_bytes(path, 262_144, "artifact_manifest_size")
    try:
        document = _safe_load_unique(raw)
    except yaml.YAMLError as error:
        raise QcewCountyEconomicsRefusal("artifact_manifest_yaml", str(path)) from error
    if not isinstance(document, dict) or not isinstance(document.get("artifacts"), list):
        raise QcewCountyEconomicsRefusal("artifact_manifest_shape", str(path))
    by_name: dict[str, Any] = {}
    for entry in document["artifacts"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            raise QcewCountyEconomicsRefusal("artifact_manifest_entry", repr(entry))
        if entry["name"] in by_name:
            raise QcewCountyEconomicsRefusal("artifact_manifest_duplicate", entry["name"])
        by_name[entry["name"]] = entry
    spec = contract["artifact"]
    entry = by_name.get(spec["name"])
    if not isinstance(entry, dict) or entry != {
        "name": spec["name"],
        "format": spec["format"],
        "source_table": None,
        "generator": "tools/make_qcew_county_economics_artifacts.py",
        "mode": "register",
        "rows": spec["rows"],
        "sha256": spec["sha256"],
        "home": spec["path"],
        "material_relation": entry.get("material_relation") if isinstance(entry, dict) else None,
    }:
        raise QcewCountyEconomicsRefusal("artifact_manifest_pin", spec["name"])
    material_relation = entry["material_relation"]
    if not isinstance(material_relation, str) or "PER-319" not in material_relation:
        raise QcewCountyEconomicsRefusal("artifact_manifest_relation", spec["name"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("contracts/qcew_county_economics_v1.yaml"),
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    contract = load_contract(args.contract)
    verify_contract(contract)
    verify_source_manifest(contract, args.repo_root / EXPECTED_SOURCE_MANIFEST)
    rows = verify_artifacts(contract, args.repo_root)
    verify_artifact_manifest(contract, args.repo_root / "data-artifacts.yaml")
    print(f"QcewCountyEconomicsV1 verified: {len(rows)} county rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
