#!/usr/bin/env python3
"""Capture separate ACS household, household-person, income and earnings margins.

All source estimate/MOE tokens survive. Cross-table household microprofiles,
class, work, wealth and time allocations are deliberately absent.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
from collections import Counter
from collections.abc import Iterable, Mapping
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
from pydantic import BaseModel, ConfigDict

SOURCE_MANIFEST = ROOT / "tools/national_household_reference_2024_sources.json"
COUNTY_PATH = ROOT / "src/babylon/data/reference/economy/national_county_reference_2024.csv.gz"
ARTIFACT_OUT = COUNTY_PATH.with_name("national_household_reference_2024.csv.gz")
METADATA_OUT = ARTIFACT_OUT.with_name("national_household_reference_2024.metadata.json")
TABLES: Final = {"B11001": 9, "B11002": 12, "B19001": 17, "B19051": 3}
UNIVERSES: Final = {
    "B11001": "Households",
    "B11002": "Population in households",
    "B19001": "Households",
    "B19051": "Households",
}
PARTITIONS: Final = {
    "B11001": ((1, (2, 7)), (2, (3, 4)), (4, (5, 6)), (7, (8, 9))),
    "B11002": ((1, (2, 12)), (2, (3, 6, 9)), (3, (4, 5)), (6, (7, 8)), (9, (10, 11))),
    "B19001": ((1, tuple(range(2, 18))),),
    "B19051": ((1, (2, 3)),),
}
COLUMNS: Final = (
    "county_geoid",
    *(
        f"{table}_{kind}{line:03}_{suffix}"
        for table, count in TABLES.items()
        for line in range(1, count + 1)
        for kind in ("E", "M")
        for suffix in ("value", "raw", "status")
    ),
)


class CountyControl(BaseModel):
    model_config = ConfigDict(frozen=True)

    population: Cell
    households: tuple[Cell, Cell]


def known_sum(values: Iterable[int | None]) -> int | None:
    rows = tuple(values)
    if any(value is None for value in rows):
        return None
    total = sum(value for value in rows if value is not None)
    if total > MAX_I64:
        raise ReferenceBuildError("count_overflow")
    return total


def source_paths(source_root: Path, manifest: Mapping[str, Any]) -> dict[str, Path]:
    if manifest.get("contract") != "NationalHouseholdReference2024SourcesV1":
        raise ReferenceBuildError("source_manifest")
    paths = {}
    for row in manifest["sources"]:
        relative = Path(row["path"])
        if relative.is_absolute() or ".." in relative.parts or row["id"] in paths:
            raise ReferenceBuildError("source_manifest_path")
        paths[row["id"]] = source_root / relative
    if set(paths) != {*TABLES, "acs_table_shells"}:
        raise ReferenceBuildError("source_manifest_coverage")
    return paths


def definitions(path: Path) -> dict[str, dict[str, str]]:
    result = {}
    with path.open(newline="") as stream:
        for row in csv.DictReader(stream, delimiter="|"):
            table = row["Table ID"]
            if table not in TABLES:
                continue
            identity = row["Unique ID"]
            if identity in result or row["Universe"] != UNIVERSES[table] or row["Type"] != "int":
                raise ReferenceBuildError("table_definition")
            result[identity] = {key: row[key] for key in ("Label", "Title", "Universe", "Indent")}
    if set(result) != {
        f"{table}_{line:03}" for table, count in TABLES.items() for line in range(1, count + 1)
    }:
        raise ReferenceBuildError("table_definition_coverage")
    return result


def county_controls() -> dict[str, CountyControl]:
    with gzip.open(COUNTY_PATH, "rt", newline="") as stream:
        rows = list(csv.DictReader(stream))
    controls = {
        row["county_geoid"]: CountyControl(
            population=parse_acs_cell(row["acs_population_persons_estimate_raw"], margin=False),
            households=(
                parse_acs_cell(row["acs_households_estimate_raw"], margin=False),
                parse_acs_cell(row["acs_households_moe_raw"], margin=True),
            ),
        )
        for row in rows
    }
    if len(rows) != len(controls) or len(controls) != 3144:
        raise ReferenceBuildError("county_roster")
    return controls


def capture_table(
    path: Path, table: str, controls: Mapping[str, CountyControl]
) -> dict[str, tuple[tuple[Cell, Cell], ...]]:
    expected = (
        "GEO_ID",
        *(
            f"{table}_{kind}{line:03}"
            for line in range(1, TABLES[table] + 1)
            for kind in ("E", "M")
        ),
    )
    result = {}
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream, delimiter="|")
        if tuple(reader.fieldnames or ()) != expected:
            raise ReferenceBuildError(f"source_schema: {table}")
        for raw in reader:
            match = ACS_GEO_ID.fullmatch(raw.get("GEO_ID", ""))
            if match is None or match[1][:2] not in STATE_COUNTS:
                continue
            county = match[1]
            if county not in controls or county in result:
                raise ReferenceBuildError(f"unexpected_or_duplicate_county: {table}/{county}")
            if set(raw) != set(expected) or any(value is None for value in raw.values()):
                raise ReferenceBuildError(f"source_shape: {table}/{county}")
            cells = tuple(
                (
                    parse_acs_cell(raw[f"{table}_E{line:03}"], margin=False),
                    parse_acs_cell(raw[f"{table}_M{line:03}"], margin=True),
                )
                for line in range(1, TABLES[table] + 1)
            )
            for parent, members in PARTITIONS[table]:
                target = cells[parent - 1][0].value
                subtotal = known_sum(cells[line - 1][0].value for line in members)
                if target is not None and subtotal is not None and target != subtotal:
                    raise ReferenceBuildError(f"partition: {table}/{county}/{parent}")
            result[county] = cells
    if set(result) != set(controls):
        raise ReferenceBuildError(f"county_coverage: {table}")
    return result


def reconcile(
    tables: Mapping[str, Mapping[str, tuple[tuple[Cell, Cell], ...]]],
    controls: Mapping[str, CountyControl],
) -> dict[str, int | None]:
    residuals = {}
    for county, control in controls.items():
        household_cells = tables["B11001"][county][0]
        if household_cells != control.households:
            raise ReferenceBuildError(f"household_control: {county}")
        household_count = household_cells[0].value
        income_count = tables["B19001"][county][0][0].value
        if (
            household_count is not None
            and income_count is not None
            and household_count != income_count
        ):
            raise ReferenceBuildError(f"income_control: {county}")
        earnings_count = tables["B19051"][county][0][0].value
        if (
            household_count is not None
            and earnings_count is not None
            and household_count != earnings_count
        ):
            raise ReferenceBuildError(f"earnings_control: {county}")
        household_persons = tables["B11002"][county][0][0].value
        population = control.population.value
        residual = (
            None
            if household_persons is None or population is None
            else population - household_persons
        )
        if residual is not None and residual < 0:
            raise ReferenceBuildError(f"household_population_control: {county}")
        residuals[county] = residual
    return residuals


def encode(
    tables: Mapping[str, Mapping[str, tuple[tuple[Cell, Cell], ...]]], counties: Iterable[str]
) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(COLUMNS)
    for county in sorted(counties):
        writer.writerow(
            (
                county,
                *(
                    part
                    for table in TABLES
                    for pair in tables[table][county]
                    for cell in pair
                    for part in cell.fields()
                ),
            )
        )
    return buffer.getvalue().encode("ascii")


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
    controls = county_controls()
    tables = {table: capture_table(paths[table], table, controls) for table in TABLES}
    residuals = reconcile(tables, controls)
    encoded = encode(tables, controls)
    artifact_out.parent.mkdir(parents=True, exist_ok=True)
    with (
        artifact_out.open("wb") as target,
        gzip.GzipFile(
            filename="", mode="wb", fileobj=target, mtime=0, compresslevel=9
        ) as compressed,
    ):
        compressed.write(encoded)
    coverage = {}
    for table, counties in tables.items():
        statuses = Counter(
            f"{kind}:{cell.status}"
            for cells in counties.values()
            for pair in cells
            for kind, cell in zip(("estimate", "moe"), pair, strict=True)
        )
        coverage[table] = {
            "counties": len(counties),
            "estimate_moe_pairs": len(counties) * TABLES[table],
            "statuses": dict(sorted(statuses.items())),
            "total_estimate": known_sum(cells[0][0].value for cells in counties.values()),
            "line_estimate_totals": {
                f"{table}_{line:03}": known_sum(
                    cells[line - 1][0].value for cells in counties.values()
                )
                for line in range(1, TABLES[table] + 1)
            },
        }
    result = {
        "contract": "NationalHouseholdReference2024V1",
        "issue": "PER-40",
        "vintage": "ACS 2024 five-year (2020–2024)",
        "source_values_evidence_class": "Observed",
        "selection_and_residual_evidence_class": "Derived",
        "artifact": {
            "path": provenance_path(artifact_out),
            "sha256": sha256(artifact_out),
            "bytes": artifact_out.stat().st_size,
            "decoded_bytes": len(encoded),
            "rows": len(controls),
        },
        "source_manifest": {
            "path": provenance_path(manifest_path),
            "sha256": sha256(manifest_path),
        },
        "sources": {
            entry["id"]: {**entry, "actual_path": provenance_path(paths[entry["id"]])}
            for entry in manifest["sources"]
        },
        "county_control": {
            "path": provenance_path(COUNTY_PATH),
            "sha256": sha256(COUNTY_PATH),
            "population_table": "B01003_001",
            "households_table": "B11001_001",
            "roster": "TIGER2024 50 states and DC, 3144 county equivalents; CT9, AK30, HI5",
        },
        "definitions": labels,
        "coverage": coverage,
        "derived_group_quarters": {
            "formula": "B01003_001 minus B11002_001",
            "persons": known_sum(residuals.values()),
            "available_counties": sum(value is not None for value in residuals.values()),
            "margin_of_error": "Not derived; component uncertainty retained separately.",
        },
        "native_readers": ["babylon-persistence::national_households"],
        "runtime_consumers": [],
        "semantics": {
            "units": "B11001, B19001 and B19051 count households. B11002 counts persons in households. B19001 bins refer to annual household income in 2024 inflation-adjusted USD, not game cash, wages or wealth.",
            "partitions": "Each table's own nested parents are checked controls, not extra households/persons. B11001 disjoint type leaves are 003/005/006/008/009; B19001 leaves are 002–017. B19051 leaves 002/003 count households with/no earnings in the past12months. B11002 retains relatives/nonrelatives and family/nonfamily partitions in persons.",
            "uncertainty": "Every estimate and 90-percent MOE literal and sentinel is retained. Missing is not zero. A controlled-estimate MOE is unavailable, not zero uncertainty. No combined MOE is invented.",
            "annotations": "Raw estimate/MOE annotations are unavailable in these bulk sources, not blank or inferred.",
            "separate_margins": "Type counts, persons by type, income bins and historical with/no-earnings counts are separate marginal observations. They do not establish a joint microhousehold profile. Do not impose integer family-size feasibility across tables or silently rebalance their estimates.",
            "limits": "Historical B19051 earnings status is not current employment, wages or income amount. No class, ownership, employment, wages, wealth, domestic labor, time, political consent, game cohort or cash allocation is observed or initialized here. Later joint allocation requires an explicitly Designed policy.",
        },
        "regeneration": "mise exec -- uv run --frozen python tools/make_national_household_reference.py --source-root /media/user/data/babylon-data",
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
        json.dumps(
            {
                "artifact": result["artifact"],
                "coverage": result["coverage"],
                "derived_group_quarters": result["derived_group_quarters"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
