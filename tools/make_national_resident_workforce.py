#!/usr/bin/env python3
"""Capture ACS resident worker classes without creating workplaces or payroll.

Observed B24080 leaves preserve their estimate/MOE tokens. Exact partitions and
B23025 employed controls are checked; source differences are never repaired.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from make_national_county_reference import (
    ACS_GEO_ID,
    MAX_I64,
    ROOT,
    STATE_COUNTS,
    Cell,
    ReferenceBuildError,
    ensure_output_paths,
    parse_acs_cell,
    provenance_path,
    sha256,
)

SOURCE_MANIFEST = ROOT / "tools/national_resident_workforce_2024_sources.json"
COUNTY_PATH = ROOT / "src/babylon/data/reference/economy/national_county_reference_2024.csv.gz"
ARTIFACT_OUT = COUNTY_PATH.with_name("national_resident_workforce_2024.csv.gz")
METADATA_OUT = ARTIFACT_OUT.with_name("national_resident_workforce_2024.metadata.json")
SOURCE_COLUMNS: Final = (
    "GEO_ID",
    *(f"B24080_{kind}{line:03}" for line in range(1, 22) for kind in ("E", "M")),
)
COLUMNS: Final = (
    "county_geoid",
    *(
        f"{column}_{suffix}"
        for column in SOURCE_COLUMNS[1:]
        for suffix in ("value", "raw", "status")
    ),
)
CLASS_NAMES: Final = (
    "private_company_employee",
    "incorporated_self_employed",
    "nonprofit_employee",
    "local_government_employee",
    "state_government_employee",
    "federal_government_employee",
    "unincorporated_self_employed",
    "unpaid_family_worker",
)
UNIVERSE: Final = "Civilian employed population 16 years and over"
PARTITIONS: Final = (
    (1, (2, 12)),
    (2, (3, 6, 7, 8, 9, 10, 11)),
    (3, (4, 5)),
    (12, (13, 16, 17, 18, 19, 20, 21)),
    (13, (14, 15)),
)


@dataclass(frozen=True)
class ResidentWorkerClasses:
    county_geoid: str
    cells: tuple[tuple[Cell, Cell], ...]

    def class_total(self, male_line: int) -> int | None:
        """Sum the two disjoint sex estimates, never their margins of error."""
        if not 4 <= male_line <= 11:
            raise ReferenceBuildError("class_leaf")
        return known_sum((self.cells[male_line - 1][0].value, self.cells[male_line + 9][0].value))


def known_sum(values: Iterable[int | None]) -> int | None:
    rows = tuple(values)
    if any(value is None for value in rows):
        return None
    total = sum(value for value in rows if value is not None)
    if total > MAX_I64:
        raise ReferenceBuildError("class_overflow")
    return total


def class_row(raw: Mapping[str, str], county: str, control: int | None) -> ResidentWorkerClasses:
    if set(raw) != set(SOURCE_COLUMNS) or any(value is None for value in raw.values()):
        raise ReferenceBuildError("source_schema")
    cells = tuple(
        (
            parse_acs_cell(raw[f"B24080_E{line:03}"], margin=False),
            parse_acs_cell(raw[f"B24080_M{line:03}"], margin=True),
        )
        for line in range(1, 22)
    )
    for total, members in PARTITIONS:
        target = cells[total - 1][0].value
        subtotal = known_sum(cells[line - 1][0].value for line in members)
        if target is not None and subtotal is not None and target != subtotal:
            raise ReferenceBuildError(f"class_partition: {county}/{total}")
    source_total = cells[0][0].value
    if source_total is not None and control is not None and source_total != control:
        raise ReferenceBuildError(f"resident_control: {county}/{source_total}/{control}")
    return ResidentWorkerClasses(county, cells)


def capture(
    rows: Iterable[Mapping[str, str]], controls: Mapping[str, int | None]
) -> tuple[ResidentWorkerClasses, ...]:
    selected = {}
    for raw in rows:
        match = ACS_GEO_ID.fullmatch(raw.get("GEO_ID", ""))
        if match is None or match[1][:2] not in STATE_COUNTS:
            continue
        county = match[1]
        if county not in controls:
            raise ReferenceBuildError(f"unexpected_county: {county}")
        if county in selected:
            raise ReferenceBuildError(f"duplicate_county: {county}")
        selected[county] = class_row(raw, county, controls[county])
    if set(selected) != set(controls):
        raise ReferenceBuildError("county_coverage")
    return tuple(selected[county] for county in sorted(selected))


def source_paths(source_root: Path, manifest: Mapping[str, Any]) -> dict[str, Path]:
    if manifest.get("contract") != "NationalResidentWorkforce2024SourcesV1":
        raise ReferenceBuildError("source_manifest")
    paths = {}
    for row in manifest["sources"]:
        relative = Path(row["path"])
        if relative.is_absolute() or ".." in relative.parts or row["id"] in paths:
            raise ReferenceBuildError("source_manifest_path")
        paths[row["id"]] = source_root / relative
    if set(paths) != {"B24080", "acs_table_shells"}:
        raise ReferenceBuildError("source_manifest_coverage")
    return paths


def definitions(path: Path) -> dict[str, dict[str, str]]:
    result = {}
    with path.open(newline="") as stream:
        for row in csv.DictReader(stream, delimiter="|"):
            if row["Table ID"] != "B24080":
                continue
            identity = row["Unique ID"]
            if identity in result or row["Universe"] != UNIVERSE or row["Type"] != "int":
                raise ReferenceBuildError("class_definition")
            result[identity] = {key: row[key] for key in ("Label", "Title", "Universe", "Indent")}
    if set(result) != {f"B24080_{line:03}" for line in range(1, 22)}:
        raise ReferenceBuildError("class_definition_coverage")
    return result


def county_controls() -> dict[str, int | None]:
    with gzip.open(COUNTY_PATH, "rt", newline="") as stream:
        rows = list(csv.DictReader(stream))
    controls = {
        row["county_geoid"]: parse_acs_cell(
            row["acs_civilian_employed_persons_estimate_raw"], margin=False
        ).value
        for row in rows
    }
    if len(rows) != len(controls) or len(controls) != 3144:
        raise ReferenceBuildError("county_roster")
    return controls


def encode(rows: tuple[ResidentWorkerClasses, ...]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(COLUMNS)
    for row in rows:
        writer.writerow(
            (
                row.county_geoid,
                *(part for pair in row.cells for cell in pair for part in cell.fields()),
            )
        )
    return buffer.getvalue().encode("ascii")


def metadata(rows: tuple[ResidentWorkerClasses, ...]) -> dict[str, Any]:
    statuses = Counter(
        f"{kind}:{cell.status}"
        for row in rows
        for pair in row.cells
        for kind, cell in zip(("estimate", "moe"), pair, strict=True)
    )
    totals = {}
    for line, name in enumerate(CLASS_NAMES, 4):
        values = tuple(row.class_total(line) for row in rows)
        totals[name] = {
            "known_persons": sum(value for value in values if value is not None),
            "complete_counties": sum(value is not None for value in values),
        }
    return {
        "counties": len(rows),
        "source_estimates": len(rows) * 21,
        "source_margins_of_error": len(rows) * 21,
        "statuses": dict(sorted(statuses.items())),
        "classes": totals,
    }


def build(
    source_root: Path,
    *,
    manifest_path: Path = SOURCE_MANIFEST,
    artifact_out: Path = ARTIFACT_OUT,
    metadata_out: Path = METADATA_OUT,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text())
    paths = source_paths(source_root, manifest)
    ensure_output_paths((artifact_out, metadata_out), (manifest_path, COUNTY_PATH, *paths.values()))
    if sha256(COUNTY_PATH) != manifest["county_reference_sha256"]:
        raise ReferenceBuildError("county_source_digest")
    for entry in manifest["sources"]:
        path = paths[entry["id"]]
        if path.stat().st_size != entry["bytes"] or sha256(path) != entry["sha256"]:
            raise ReferenceBuildError(f"source_digest: {entry['id']}")
    labels = definitions(paths["acs_table_shells"])
    with paths["B24080"].open(newline="") as stream:
        reader = csv.DictReader(stream, delimiter="|")
        if tuple(reader.fieldnames or ()) != SOURCE_COLUMNS:
            raise ReferenceBuildError("source_schema")
        rows = capture(reader, county_controls())
    encoded = encode(rows)
    artifact_out.parent.mkdir(parents=True, exist_ok=True)
    with (
        artifact_out.open("wb") as target,
        gzip.GzipFile(
            filename="", mode="wb", fileobj=target, mtime=0, compresslevel=9
        ) as compressed,
    ):
        compressed.write(encoded)
    result = {
        "contract": "NationalResidentWorkforce2024V1",
        "issue": "PER-40",
        "source_values_evidence_class": "Observed",
        "selection_and_subtotals_evidence_class": "Derived",
        "vintage": "ACS 2024 five-year (2020–2024)",
        "units": "resident persons",
        "universe": UNIVERSE,
        "artifact": {
            "path": provenance_path(artifact_out),
            "sha256": sha256(artifact_out),
            "bytes": artifact_out.stat().st_size,
            "decoded_bytes": len(encoded),
            "rows": len(rows),
        },
        "sources": {
            entry["id"]: {**entry, "actual_path": provenance_path(paths[entry["id"]])}
            for entry in manifest["sources"]
        },
        "source_manifest": {
            "path": provenance_path(manifest_path),
            "sha256": sha256(manifest_path),
        },
        "county_control": {
            "path": provenance_path(COUNTY_PATH),
            "sha256": sha256(COUNTY_PATH),
            "table": "B23025_004",
            "mismatches": 0,
        },
        "definitions": labels,
        "coverage": metadata(rows),
        "native_readers": ["babylon-persistence::national_resident_workforce"],
        "runtime_consumers": [],
        "semantics": {
            "partition": "Male leaves 004–011 and female leaves 014–021 are disjoint. Sex totals 002/012, private subtotals 003/013 and overall total 001 are controls only, never additional people.",
            "uncertainty": "Preserve each source estimate and 90-percent margin independently. Missing/sentinel cells remain absent; no summed or zero-filled margin of error is invented.",
            "control": "Check every available source partition and the exact county B23025 civilian-employed control. Contradictions refuse; no balancing or renormalization repairs observations.",
            "interpretation": "Class of worker is a source employment category, not a political class or observed workplace assignment. Incorporated self-employment is separate from private company employees. Neither establishes QCEW coverage.",
            "limits": "Creates no game people, households, firms, commuting, labor hours, incomes, cash or ownership claims. Any later allocation and omitted-function treatment need separate captured Designed policies.",
        },
        "regeneration": "mise exec -- uv run --frozen python tools/make_national_resident_workforce.py --source-root /media/user/data/babylon-data",
    }
    metadata_out.parent.mkdir(parents=True, exist_ok=True)
    metadata_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=SOURCE_MANIFEST)
    parser.add_argument("--artifact-out", type=Path, default=ARTIFACT_OUT)
    parser.add_argument("--metadata-out", type=Path, default=METADATA_OUT)
    args = parser.parse_args()
    result = build(
        args.source_root,
        manifest_path=args.manifest,
        artifact_out=args.artifact_out,
        metadata_out=args.metadata_out,
    )
    print(
        json.dumps({"artifact": result["artifact"], "coverage": result["coverage"]}, sort_keys=True)
    )


if __name__ == "__main__":
    main()
