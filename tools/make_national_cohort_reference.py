#!/usr/bin/env python3
"""Capture disjoint county/function/ownership source groups for native reading.

Admission identifies positive observed activity; it allocates no persons, firms,
physical recipes, capacities or monetary balances. Suppression stays unknown.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import make_national_qcew_function_basis as basis
import pyarrow.parquet as pq  # type: ignore[import-untyped]
from make_national_county_reference import (
    ARTIFACT_OUT as COUNTY_PATH,
)
from make_national_county_reference import (
    MAX_I64,
    ROOT,
    ReferenceBuildError,
    ensure_output_paths,
    provenance_path,
    sha256,
)
from make_national_county_reference import (
    METADATA_OUT as COUNTY_METADATA,
)

ARTIFACT_OUT = ROOT / "src/babylon/data/reference/economy/national_cohort_reference_2024.csv.gz"
METADATA_OUT = ARTIFACT_OUT.with_name("national_cohort_reference_2024.metadata.json")
COLUMNS: Final = (
    "county_geoid",
    "function_id",
    "ownership_code",
    "admitted",
    "member_count",
    "establishments_known",
    "establishments_published_members",
    "jobs_known",
    "jobs_published_members",
    "payroll_known",
    "payroll_published_members",
    "members",
)


@dataclass(frozen=True)
class Subtotal:
    known_subtotal: int
    published_members: int
    member_count: int

    @property
    def complete_total(self) -> int | None:
        return self.known_subtotal if self.published_members == self.member_count else None


@dataclass(frozen=True)
class Cohort:
    county_geoid: str
    function_id: str | None
    ownership_code: str
    admitted: bool
    establishments: Subtotal
    jobs: Subtotal
    payroll: Subtotal
    members: tuple[basis.Observation, ...]


def source_integer(value: object) -> int:
    if type(value) is not int or value < 0 or value > MAX_I64:
        raise ReferenceBuildError("source_integer")
    return value


def subtotal(values: Iterable[int | None]) -> Subtotal:
    rows = tuple(values)
    known = tuple(source_integer(value) for value in rows if value is not None)
    total = source_integer(sum(known))
    return Subtotal(total, len(known), len(rows))


def observation(
    row: Mapping[str, Any], counties: set[str], mapping: basis.FunctionMapping
) -> basis.Observation:
    if set(row) != set(basis.SCHEMA.names):
        raise ReferenceBuildError("source_row_schema")
    if row["county_geoid"] not in counties:
        raise ReferenceBuildError("source_county")
    code, ownership, disclosure = row["naics_code"], row["ownership_code"], row["disclosure_code"]
    if code not in mapping.source_codes or row["agglvl_code"] != basis.aggregation_level(code):
        raise ReferenceBuildError("source_naics")
    if ownership not in basis.OWNERSHIP_CODES or disclosure not in {"", "N"}:
        raise ReferenceBuildError("source_ownership_disclosure")
    source_integer(row["annual_avg_establishments"])
    for key in basis.METRICS[1:]:
        if disclosure == "N":
            if row[key] is not None:
                raise ReferenceBuildError("source_suppression")
        else:
            source_integer(row[key])
    return basis.Observation(**row)


def capture(rows: Iterable[Mapping[str, Any]], counties: set[str]) -> tuple[Cohort, ...]:
    mapping = basis.load_mapping()
    grouped: dict[tuple[str, str, str], list[basis.Observation]] = defaultdict(list)
    seen = set()
    for raw in rows:
        row = observation(raw, counties, mapping)
        if row.key in seen:
            raise ReferenceBuildError("duplicate_source_member")
        seen.add(row.key)
        function = mapping.function_for(row.naics_code)
        grouped[(row.county_geoid, function or "", row.ownership_code)].append(row)
    result = []
    for (county, function, ownership), items in sorted(grouped.items()):
        members = tuple(sorted(items, key=lambda row: row.naics_code))
        establishments = subtotal(row.annual_avg_establishments for row in members)
        jobs = subtotal(row.annual_avg_jobs for row in members)
        payroll = subtotal(row.annual_payroll_usd for row in members)
        admitted = bool(function) and any(
            value.known_subtotal > 0 for value in (establishments, jobs, payroll)
        )
        result.append(
            Cohort(
                county,
                function or None,
                ownership,
                admitted,
                establishments,
                jobs,
                payroll,
                members,
            )
        )
    return tuple(result)


def member_text(row: basis.Observation) -> str:
    return "~".join(
        (
            row.naics_code,
            "N" if row.disclosure_code else "P",
            str(row.annual_avg_establishments),
            *(
                "" if value is None else str(value)
                for value in (row.annual_avg_jobs, row.annual_payroll_usd, row.mean_weekly_wage_usd)
            ),
        )
    )


def fields(row: Cohort) -> tuple[str, ...]:
    return (
        row.county_geoid,
        row.function_id or "",
        row.ownership_code,
        str(int(row.admitted)),
        str(len(row.members)),
        *(
            str(value)
            for cell in (row.establishments, row.jobs, row.payroll)
            for value in (cell.known_subtotal, cell.published_members)
        ),
        ";".join(member_text(member) for member in row.members),
    )


def pinned_input(path: Path, metadata_path: Path) -> dict[str, Any]:
    metadata = json.loads(metadata_path.read_text())
    if sha256(path) != metadata["artifact"]["sha256"]:
        raise ReferenceBuildError(f"source_digest: {path}")
    return {
        "path": provenance_path(path),
        "sha256": sha256(path),
        "metadata_sha256": sha256(metadata_path),
    }


def build(
    *, artifact_out: Path = ARTIFACT_OUT, metadata_out: Path = METADATA_OUT
) -> dict[str, Any]:
    inputs = (
        basis.ARTIFACT_OUT,
        basis.METADATA_OUT,
        basis.MAPPING_PATH,
        COUNTY_PATH,
        COUNTY_METADATA,
    )
    ensure_output_paths((artifact_out, metadata_out), inputs)
    sources = {
        "leaf_basis": pinned_input(basis.ARTIFACT_OUT, basis.METADATA_OUT),
        "county_roster": pinned_input(COUNTY_PATH, COUNTY_METADATA),
        "function_mapping": {
            "path": provenance_path(basis.MAPPING_PATH),
            "sha256": sha256(basis.MAPPING_PATH),
        },
    }
    with gzip.open(COUNTY_PATH, "rt", newline="") as stream:
        counties = {row["county_geoid"] for row in csv.DictReader(stream)}
    table = pq.read_table(basis.ARTIFACT_OUT)
    if not table.schema.equals(basis.SCHEMA) or len(counties) != 3144:
        raise ReferenceBuildError("source_schema_or_counties")
    cohorts = capture(table.to_pylist(), counties)
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(COLUMNS)
    writer.writerows(fields(row) for row in cohorts)
    encoded = buffer.getvalue().encode("ascii")
    artifact_out.parent.mkdir(parents=True, exist_ok=True)
    with (
        artifact_out.open("wb") as raw,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as compressed,
    ):
        compressed.write(encoded)
    metadata = {
        "contract": "NationalCohortReference2024V1",
        "issue": "PER-40",
        "year": 2024,
        "source_values_evidence_class": "Observed",
        "aggregation_evidence_class": "Derived",
        "membership_and_admission_evidence_class": "Designed",
        "artifact": {
            "path": provenance_path(artifact_out),
            "sha256": sha256(artifact_out),
            "bytes": artifact_out.stat().st_size,
            "decoded_bytes": len(encoded),
            "rows": len(cohorts),
        },
        "sources": sources,
        "coverage": {
            "source_members": sum(len(row.members) for row in cohorts),
            "mapped_groups": sum(row.function_id is not None for row in cohorts),
            "admitted_groups": sum(row.admitted for row in cohorts),
            "unclassified_groups": sum(row.function_id is None for row in cohorts),
            "counties_with_observations": len({row.county_geoid for row in cohorts}),
            "counties_without_observations": sorted(
                counties - {row.county_geoid for row in cohorts}
            ),
            "known_totals": {
                name: sum(getattr(row, name).known_subtotal for row in cohorts)
                for name in ("establishments", "jobs", "payroll")
            },
        },
        "native_readers": ["babylon-persistence::national_cohorts"],
        "runtime_consumers": [],
        "semantics": {
            "admission": "A mapped group with any positive known establishments, workplace jobs or annual payroll is eligible for a later compiler; admission creates no worksite or person. Every other group remains source context.",
            "completeness": "Each measure independently retains its checked known subtotal and published member count. Complete total exists only when all source members publish that measure; unknown members are never observed zeros.",
            "suppression": "N preserves published establishments while jobs, payroll and mean weekly wage remain unknown. P means published source row; absent county/group remains absent.",
            "members": "Exact disjoint source NAICS members once each, sorted lexically; tuple naics~P/N~establishments~jobs~payroll~mean_weekly_wage separated by semicolons. Blank quantity is unknown, not zero. Source basis preserves source aggregation-level identity.",
            "wages": "Published mean weekly wage is retained only per source member; means are never added or averaged into cohort wages.",
            "context": "Code 99 has no function and is never admitted. All 3,144 counties remain in the independent county roster; Kalawao's residents do not imply an observed workplace.",
            "limits": "No jobs-to-persons conversion, household allocation, physical recipe, operating capacity, opening stock, current wage payment or game-state hydration follows from this capture.",
        },
    }
    metadata_out.parent.mkdir(parents=True, exist_ok=True)
    metadata_out.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-out", type=Path, default=ARTIFACT_OUT)
    parser.add_argument("--metadata-out", type=Path, default=METADATA_OUT)
    args = parser.parse_args()
    metadata = build(artifact_out=args.artifact_out, metadata_out=args.metadata_out)
    print(
        json.dumps(
            {"artifact": metadata["artifact"], "coverage": metadata["coverage"]}, sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
