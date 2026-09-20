#!/usr/bin/env python3
"""Capture source-qualified world population without duplicating included areas.

This is demographic context, not productive capacity, household formation or
labor supply. The 2024 WPP values are explicitly medium-variant projections.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterator
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from make_international_counterpart_reference import load_membership
from make_national_county_reference import (
    ROOT,
    ReferenceBuildError,
    ensure_output_paths,
    provenance_path,
    sha256,
)

ARTIFACT_OUT = ROOT / "src/babylon/data/reference/economy/world_population_reference_2024.csv.gz"
METADATA_OUT = ARTIFACT_OUT.with_name("world_population_reference_2024.metadata.json")
SOURCE_MANIFEST = ROOT / "tools/world_population_2024_sources.json"
POLICY_PATH = ROOT / "contracts/world_population_scope_v1.json"
MEMBERSHIP_PATH = ROOT / "contracts/international_counterpart_membership_v1.json"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def persons(raw: str) -> int:
    """Round reported thousands to integral persons without binary floating point."""
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise ReferenceBuildError("population_token") from exc
    if raw.strip() != raw or not value.is_finite() or not 0 <= value <= 20_000_000:
        raise ReferenceBuildError("population_token")
    return int((value * 1000).quantize(Decimal(1), rounding=ROUND_HALF_EVEN))


def sheet_rows(archive: zipfile.ZipFile, sheet: str) -> Iterator[dict[str, str]]:
    """Stream source cells while retaining exact XML numeric tokens."""
    strings_xml = archive.read("xl/sharedStrings.xml")
    root = ET.fromstring(strings_xml)  # noqa: S314 -- pinned, size-bounded source
    strings = ["".join(row.itertext()) for row in root]
    with archive.open(f"xl/worksheets/{sheet}.xml") as stream:
        for _, row in ET.iterparse(stream, events=("end",)):  # noqa: S314 -- pinned, size-bounded source
            if row.tag != NS + "row":
                continue
            cells = {"row": row.attrib["r"]}
            for cell in row:
                value = cell.find(NS + "v")
                if value is not None and value.text is not None:
                    token = strings[int(value.text)] if cell.get("t") == "s" else value.text
                    cells[re.sub(r"[0-9]", "", cell.attrib["r"])] = token
            yield cells
            row.clear()


def read_population(path: Path) -> tuple[dict[str, dict[str, str]], str, list[str]]:
    """Select Country/Area leaves and keep the world control separate."""
    source: dict[str, dict[str, str]] = {}
    world = ""
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if (
            len({entry.filename for entry in entries}) != len(entries)
            or sum(entry.file_size for entry in entries) > 160 * 1024 * 1024
        ):
            raise ReferenceBuildError("population_workbook_bound")
        notes = [row["A"] for row in sheet_rows(archive, "sheet3") if "A" in row]
        for row in sheet_rows(archive, "sheet2"):
            if row.get("K") != "2024":
                continue
            if row.get("B") != "Medium":
                raise ReferenceBuildError("population_variant")
            if row.get("I") == "World":
                if world:
                    raise ReferenceBuildError("duplicate_population_world")
                world = row["M"]
            if row.get("I") != "Country/Area":
                continue
            identity = f"m49:{int(row['E']):03d}"
            if identity in source:
                raise ReferenceBuildError("duplicate_population_identity")
            persons(row["M"])
            source[identity] = row
    if len(source) != 237 or not world:
        raise ReferenceBuildError("population_source_coverage")
    return source, world, notes


def capture(source: dict[str, dict[str, str]], policy: dict[str, Any]) -> list[dict[str, str]]:
    """Apply separately declared scope allocation without rewriting source values."""
    membership = load_membership(MEMBERSHIP_PATH)
    members = {m.identity_id: m for m in membership}
    if not set(source) <= members.keys():
        raise ReferenceBuildError("unmapped_population_identity")
    amounts = {key: persons(row["M"]) for key, row in source.items()}
    altered: set[str] = set()
    for transfer in policy["apportionments"]:
        parent, child, quantity = transfer["parent"], transfer["child"], transfer["persons"]
        if (
            type(quantity) is not int
            or quantity <= 0
            or parent not in source
            or child in amounts
            or child not in members
        ):
            raise ReferenceBuildError("population_apportionment")
        if amounts[parent] < quantity:
            raise ReferenceBuildError("population_apportionment")
        amounts[parent] -= quantity
        amounts[child] = quantity
        altered.update((parent, child))
    if sum(amounts.values()) != sum(persons(row["M"]) for row in source.values()):
        raise ReferenceBuildError("population_conservation")
    included = policy["included_in_parent"]
    for child, parent in included.items():
        if child in amounts or parent not in amounts or child not in members:
            raise ReferenceBuildError("population_parent_scope")
        if members[child].counterpart_id != members[parent].counterpart_id:
            raise ReferenceBuildError("cross_market_parent_scope")
    rows = []
    for member in membership:
        key = member.identity_id
        raw = source.get(key, {})
        if key.startswith("census:"):
            status, parent = "trade_only", "m49:275"
        elif key in included:
            status, parent = "included_in_parent", included[key]
        elif key in altered:
            status, parent = "designed_scope_apportionment", key
        elif key in amounts:
            status, parent = "source_projection", key
        else:
            status, parent = "not_published", ""
        rows.append(
            {
                "identity_id": key,
                "counterpart_id": member.counterpart_id,
                "disposition": member.disposition,
                "status": status,
                "accounted_in_identity": parent,
                "population_persons": str(amounts[key]) if key in amounts else "",
                "population_evidence": "Designed"
                if key in altered
                else "Derived"
                if key in amounts
                else "",
                "source_kind": "medium_projection" if raw else "",
                "source_date": "2024-07-01" if raw else "",
                "source_sheet": "Medium variant" if raw else "",
                "source_row": raw.get("row", ""),
                "source_area_name": raw.get("C", ""),
                "source_notes": raw.get("D", ""),
                "source_population_thousands_raw": raw.get("M", ""),
            }
        )
    return sorted(rows, key=lambda row: row["identity_id"])


def scope_totals(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    groups = sorted({r["counterpart_id"] or r["disposition"] for r in rows})
    output = []
    for group in groups:
        selected = [r for r in rows if (r["counterpart_id"] or r["disposition"]) == group]
        output.append(
            {
                "scope": group,
                "known_population_persons": sum(
                    int(r["population_persons"] or 0) for r in selected
                ),
                "not_published_identities": [
                    r["identity_id"] for r in selected if r["status"] == "not_published"
                ],
                "included_in_parent_identities": [
                    r["identity_id"] for r in selected if r["status"] == "included_in_parent"
                ],
            }
        )
    return output


def build(
    *, source_root: Path, artifact_out: Path = ARTIFACT_OUT, metadata_out: Path = METADATA_OUT
) -> dict[str, Any]:
    manifest = json.loads(SOURCE_MANIFEST.read_text())
    paths = {}
    for spec in manifest["sources"]:
        path = source_root / spec["path"]
        if (
            not path.is_file()
            or path.stat().st_size != spec["bytes"]
            or sha256(path) != spec["sha256"]
        ):
            raise ReferenceBuildError("population_source_digest")
        paths[spec["id"]] = path
    ensure_output_paths(
        (artifact_out, metadata_out),
        (*paths.values(), SOURCE_MANIFEST, POLICY_PATH, MEMBERSHIP_PATH),
    )
    policy = json.loads(POLICY_PATH.read_text())
    if policy["contract"] != "WorldPopulationScopeV1" or policy["evidence_class"] != "Designed":
        raise ReferenceBuildError("population_scope_policy")
    source, world, notes = read_population(paths["un_wpp"])
    rows = capture(source, policy)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    artifact_out.parent.mkdir(parents=True, exist_ok=True)
    with (
        artifact_out.open("wb") as raw,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed,
    ):
        compressed.write(stream.getvalue().encode())
    known = sum(int(row["population_persons"] or 0) for row in rows)
    metadata = {
        "contract": "WorldPopulationReference2024V1",
        "issue": "PER-31",
        "source_kind": "UN WPP2024 medium-fertility projection",
        "source_date": "2024-07-01",
        "source_unit": "thousands of persons",
        "rounding": "Derived integral persons: Decimal(raw)*1000, round-half-even; source XML tails confer no extra precision.",
        "source_notes": notes,
        "country_area_source_rows": len(source),
        "world_source_thousands_raw": world,
        "known_area_population_persons": known,
        "rounding_residual_persons": known - persons(world),
        "domestic_runtime_source": "ACS 2024 five-year county capture",
        "runtime_consumers": [],
        "scope_totals": scope_totals(rows),
        "semantics": policy["semantics"],
        "artifact": {
            "path": provenance_path(artifact_out),
            "rows": len(rows),
            "bytes": artifact_out.stat().st_size,
            "sha256": sha256(artifact_out),
        },
        "source_manifest": {
            "path": str(SOURCE_MANIFEST.relative_to(ROOT)),
            "sha256": sha256(SOURCE_MANIFEST),
        },
        "scope_policy": {"path": str(POLICY_PATH.relative_to(ROOT)), "sha256": sha256(POLICY_PATH)},
        "membership": {
            "path": str(MEMBERSHIP_PATH.relative_to(ROOT)),
            "sha256": sha256(MEMBERSHIP_PATH),
        },
    }
    metadata_out.parent.mkdir(parents=True, exist_ok=True)
    metadata_out.write_text(
        json.dumps(metadata, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path("/media/user/data/babylon-data"))
    parser.add_argument("--artifact-out", type=Path, default=ARTIFACT_OUT)
    parser.add_argument("--metadata-out", type=Path, default=METADATA_OUT)
    args = parser.parse_args()
    print(
        json.dumps(
            build(
                source_root=args.source_root,
                artifact_out=args.artifact_out,
                metadata_out=args.metadata_out,
            )["artifact"],
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
