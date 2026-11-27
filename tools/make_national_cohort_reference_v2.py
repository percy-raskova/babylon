#!/usr/bin/env python3
"""Capture the twelve-trade county/function/ownership groups for native reading.

Version 2 of the cohort table: version 1's twelve columns over the version 2 jobs
basis, keeping only county leaf cells. Admission identifies positive observed
activity; it allocates no persons, firms, recipes, capacities or balances.
Suppression stays unknown. Version 1's builder and table are never edited.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any, Final

import make_national_cohort_reference as cohort
import make_national_qcew_function_basis as basis
import make_national_qcew_function_basis_v2 as v2
from make_national_county_reference import (
    ARTIFACT_OUT as COUNTY_PATH,
)
from make_national_county_reference import (
    METADATA_OUT as COUNTY_METADATA,
)
from make_national_county_reference import (
    ROOT,
    ReferenceBuildError,
    ensure_output_paths,
    provenance_path,
    sha256,
)

ARTIFACT_OUT: Final = (
    ROOT / "src/babylon/data/reference/economy/national_cohort_reference_v2_2024.csv.gz"
)
METADATA_OUT: Final = ARTIFACT_OUT.with_name("national_cohort_reference_v2_2024.metadata.json")
COUNTY_COUNT: Final = 3144


def county_observations(rows: Iterable[v2.SourceRow]) -> Iterator[dict[str, Any]]:
    """County leaf rows in version 1's field names; every other role is dropped."""
    for row in rows:
        if row.row_role != "county_leaf":
            continue
        yield {
            "county_geoid": row.area_fips,
            "ownership_code": row.ownership_code,
            "naics_code": row.naics_code,
            "agglvl_code": row.agglvl_code,
            "disclosure_code": row.disclosure_code,
            "annual_avg_establishments": row.annual_avg_establishments,
            "annual_avg_jobs": row.annual_avg_jobs,
            "annual_payroll_usd": row.annual_payroll_usd,
            "mean_weekly_wage_usd": row.mean_weekly_wage_usd,
        }


def capture_cohorts_v2(
    rows: Iterable[Mapping[str, Any]], counties: set[str], mapping: basis.FunctionMapping
) -> tuple[cohort.Cohort, ...]:
    grouped: dict[tuple[str, str, str], list[basis.Observation]] = defaultdict(list)
    seen = set()
    for raw in rows:
        row = cohort.observation(raw, counties, mapping)
        if row.key in seen:
            raise ReferenceBuildError("duplicate_source_member")
        seen.add(row.key)
        function = mapping.function_for(row.naics_code)
        grouped[(row.county_geoid, function or "", row.ownership_code)].append(row)
    result = []
    for (county, function, ownership), items in sorted(grouped.items()):
        members = tuple(sorted(items, key=lambda row: row.naics_code))
        establishments = cohort.subtotal(row.annual_avg_establishments for row in members)
        jobs = cohort.subtotal(row.annual_avg_jobs for row in members)
        payroll = cohort.subtotal(row.annual_payroll_usd for row in members)
        admitted = bool(function) and any(
            value.known_subtotal > 0 for value in (establishments, jobs, payroll)
        )
        result.append(
            cohort.Cohort(
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


def build(
    *, artifact_out: Path = ARTIFACT_OUT, metadata_out: Path = METADATA_OUT
) -> dict[str, Any]:
    inputs = (
        v2.ARTIFACT_OUT,
        v2.METADATA_OUT,
        v2.MAPPING_V2_PATH,
        COUNTY_PATH,
        COUNTY_METADATA,
    )
    ensure_output_paths((artifact_out, metadata_out), inputs)
    sources = {
        "leaf_basis": cohort.pinned_input(v2.ARTIFACT_OUT, v2.METADATA_OUT),
        "county_roster": cohort.pinned_input(COUNTY_PATH, COUNTY_METADATA),
        "function_mapping": {
            "path": provenance_path(v2.MAPPING_V2_PATH),
            "sha256": sha256(v2.MAPPING_V2_PATH),
        },
    }
    with gzip.open(COUNTY_PATH, "rt", newline="") as stream:
        counties = {row["county_geoid"] for row in csv.DictReader(stream)}
    if len(counties) != COUNTY_COUNT:
        raise ReferenceBuildError("source_schema_or_counties")
    mapping = v2.load_mapping_v2()
    cohorts = capture_cohorts_v2(county_observations(v2.read_basis_v2()), counties, mapping)
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(cohort.COLUMNS)
    writer.writerows(cohort.fields(row) for row in cohorts)
    encoded = buffer.getvalue().encode("ascii")
    artifact_out.parent.mkdir(parents=True, exist_ok=True)
    with (
        artifact_out.open("wb") as raw,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as compressed,
    ):
        compressed.write(encoded)
    metadata = {
        "contract": "NationalCohortReference2024V2",
        "issue": "PER-371",
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
        "regeneration": (
            "UV_PROJECT_ENVIRONMENT=.venv mise exec -- uv run --frozen python "
            "tools/make_national_cohort_reference_v2.py"
        ),
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
            "members": "Exact disjoint county leaf NAICS members of the twelve-trade cut, once each, sorted lexically; tuple naics~P/N~establishments~jobs~payroll~mean_weekly_wage separated by semicolons. Blank quantity is unknown, not zero. Parent, state and nation rows of the version 2 basis are never members.",
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
