#!/usr/bin/env python3
"""Capture one disjoint observed QCEW cut for separately Designed game functions.

Own codes 1/2/3/5 remain separate. Missing cells stay absent, N rows retain public
establishment counts, and legitimate rounded-zero observations stay present.
Parent sectors are diagnostics only: never add them to the selected evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final

import pyarrow as pa
import pyarrow.parquet as pq
from make_national_county_reference import (
    ROOT,
    SOURCE_MANIFEST,
    STATE_COUNTS,
    ReferenceBuildError,
    _unique_object,
    ensure_output_paths,
    integer,
    provenance_path,
    read_counties,
    sha256,
)

MAPPING_PATH = ROOT / "contracts/national_qcew_function_mapping_v1.json"
ARTIFACT_OUT = ROOT / "src/babylon/data/reference/economy/national_qcew_function_basis_2024.parquet"
METADATA_OUT = ARTIFACT_OUT.with_suffix(".metadata.json")
OWNERSHIP_CODES: Final = ("1", "2", "3", "5")
FUNCTION_IDS: Final = (
    "food",
    "extraction",
    "energy_utilities",
    "manufacturing",
    "capital_goods",
    "construction_housing",
    "distribution_transport",
    "household_services",
    "business_services",
    "public_provisioning",
)
SECTORS: Final = (
    "11",
    "21",
    "22",
    "23",
    "31-33",
    "42",
    "44-45",
    "48-49",
    "51",
    "52",
    "53",
    "54",
    "55",
    "56",
    "61",
    "62",
    "71",
    "72",
    "81",
    "92",
    "99",
)
METRICS: Final = (
    "annual_avg_establishments",
    "annual_avg_jobs",
    "annual_payroll_usd",
    "mean_weekly_wage_usd",
)
SOURCE_METRICS: Final = (
    "annual_avg_estabs",
    "annual_avg_emplvl",
    "total_annual_wages",
    "annual_avg_wkly_wage",
)
SCHEMA: Final = pa.schema(
    [
        pa.field("county_geoid", pa.string(), nullable=False),
        pa.field("ownership_code", pa.string(), nullable=False),
        pa.field("naics_code", pa.string(), nullable=False),
        pa.field("agglvl_code", pa.uint8(), nullable=False),
        pa.field("disclosure_code", pa.string(), nullable=False),
        pa.field("annual_avg_establishments", pa.int64(), nullable=False),
        *(pa.field(name, pa.int64(), nullable=True) for name in METRICS[1:]),
    ]
)


@dataclass(frozen=True)
class FunctionMapping:
    document: dict[str, Any]
    code_to_function: dict[str, str]
    source_codes: frozenset[str]

    def function_for(self, code: str) -> str | None:
        if code not in self.source_codes:
            raise ReferenceBuildError(f"unsupported_naics: {code}")
        return self.code_to_function.get(code)


def aggregation_level(code: str) -> int:
    if code in SECTORS:
        return 74
    if code.isascii() and code.isdigit() and len(code) in {3, 4}:
        return 72 + len(code)
    raise ReferenceBuildError(f"unsupported_naics: {code}")


def parent_sector(code: str) -> str:
    if code in SECTORS:
        return code
    prefix = code[:2]
    if prefix in {"31", "32", "33"}:
        return "31-33"
    if prefix in {"44", "45"}:
        return "44-45"
    if prefix in {"48", "49"}:
        return "48-49"
    if prefix not in SECTORS:
        raise ReferenceBuildError(f"unsupported_naics_parent: {code}")
    return prefix


def validate_mapping(document: dict[str, Any]) -> FunctionMapping:
    if (
        document.get("contract") != "NationalQcewFunctionMappingV1"
        or document.get("evidence_class") != "Designed"
        or document.get("source_vintage") != 2024
    ):
        raise ReferenceBuildError("function_mapping_identity")
    if set(document.get("ownership_codes", {})) != set(OWNERSHIP_CODES):
        raise ReferenceBuildError("function_mapping_ownership")
    functions = document.get("functions", [])
    if [item.get("id") for item in functions] != list(FUNCTION_IDS):
        raise ReferenceBuildError("function_mapping_functions")
    codes = {}
    for function in functions:
        if not function.get("qualification") or not function.get("naics_codes"):
            raise ReferenceBuildError("function_mapping_qualification")
        for code in function["naics_codes"]:
            aggregation_level(code)
            if code in codes or code == "99":
                raise ReferenceBuildError(f"duplicate_naics: {code}")
            codes[code] = function["id"]
    if document.get("residual_naics_codes") != ["99"]:
        raise ReferenceBuildError("function_mapping_residual")
    selected = frozenset((*codes, "99"))
    for code in selected:
        for other in selected - {code}:
            if other.startswith(code) or (code in SECTORS and parent_sector(other) == code):
                raise ReferenceBuildError(f"overlapping_naics: {code}/{other}")
    return FunctionMapping(document, codes, selected)


def load_mapping(path: Path = MAPPING_PATH) -> FunctionMapping:
    return validate_mapping(json.loads(path.read_bytes(), object_pairs_hook=_unique_object))


@dataclass(frozen=True)
class Observation:
    county_geoid: str
    ownership_code: str
    naics_code: str
    agglvl_code: int
    disclosure_code: str
    annual_avg_establishments: int
    annual_avg_jobs: int | None
    annual_payroll_usd: int | None
    mean_weekly_wage_usd: int | None

    @property
    def key(self) -> tuple[str, str, str]:
        return self.county_geoid, self.ownership_code, self.naics_code


def parse_observation(row: Mapping[str, str]) -> Observation:
    if tuple(row.get(key) for key in ("year", "qtr", "size_code")) != ("2024", "A", "0"):
        raise ReferenceBuildError("period_identity")
    code = row["industry_code"]
    level = aggregation_level(code)
    if row.get("agglvl_code") != str(level):
        raise ReferenceBuildError(f"aggregation_identity: {code}")
    if row["own_code"] not in OWNERSHIP_CODES:
        raise ReferenceBuildError("ownership_identity")
    disclosure = row.get("disclosure_code")
    if disclosure not in {"", "N"}:
        raise ReferenceBuildError("source_disclosure")
    values = [integer(row[name], "source_value") for name in SOURCE_METRICS]
    if disclosure == "N" and values[1:] != [0, 0, 0]:
        raise ReferenceBuildError("suppressed_nonzero")
    return Observation(
        row["area_fips"],
        row["own_code"],
        code,
        level,
        disclosure,
        values[0],
        *(None if disclosure else value for value in values[1:]),
    )


@dataclass(frozen=True)
class Capture:
    observations: tuple[Observation, ...]
    diagnostics: dict[str, Any]


def _jobs_total(row: Mapping[str, str]) -> int:
    if tuple(row.get(key) for key in ("year", "qtr", "size_code", "disclosure_code")) != (
        "2024",
        "A",
        "0",
        "",
    ):
        raise ReferenceBuildError("jobs_total_identity")
    return integer(row["annual_avg_emplvl"], "jobs_total_value")


def capture(
    rows: Iterable[dict[str, str]], county_ids: set[str], mapping: FunctionMapping
) -> Capture:
    selected: dict[tuple[str, str, str], Observation] = {}
    parents: dict[tuple[str, str, str], Observation] = {}
    county_jobs: dict[str, int] = {}
    unallocated_jobs: dict[str, int] = {}
    us_jobs: int | None = None
    outside_rows = Counter()
    for row in rows:
        geoid, ownership, code = (row[name] for name in ("area_fips", "own_code", "industry_code"))
        level = row["agglvl_code"]
        if ownership == "0" and code == "10":
            if geoid == "US000" and level == "10":
                if us_jobs is not None:
                    raise ReferenceBuildError("duplicate_us_total")
                us_jobs = _jobs_total(row)
            elif level == "70" and (
                geoid in county_ids or (geoid[:2] in STATE_COUNTS and geoid.endswith("999"))
            ):
                totals = county_jobs if geoid in county_ids else unallocated_jobs
                if geoid in totals:
                    raise ReferenceBuildError(f"duplicate_county_total: {geoid}")
                totals[geoid] = _jobs_total(row)
        if level not in {"74", "75", "76"} or ownership not in OWNERSHIP_CODES:
            continue
        if code not in mapping.source_codes and level != "74":
            continue
        if geoid not in county_ids:
            outside_rows[
                "domestic_unallocated"
                if geoid[:2] in STATE_COUNTS and geoid.endswith("999")
                else "outside_50_states_dc"
            ] += 1
            continue
        observation = parse_observation(row)
        if level == "74":
            if observation.key in parents:
                raise ReferenceBuildError(f"duplicate_source_cell: {observation.key}")
            parents[observation.key] = observation
        if code in mapping.source_codes:
            if observation.key in selected:
                raise ReferenceBuildError(f"duplicate_source_cell: {observation.key}")
            selected[observation.key] = observation
    observations = tuple(selected[key] for key in sorted(selected))
    by_function: dict[str, list[Observation]] = defaultdict(list)
    by_parent: dict[tuple[str, str, str], list[Observation]] = defaultdict(list)
    for row in observations:
        by_function[mapping.function_for(row.naics_code) or "unclassified"].append(row)
        by_parent[(row.county_geoid, row.ownership_code, parent_sector(row.naics_code))].append(row)
    functions = {}
    for function in (*FUNCTION_IDS, "unclassified"):
        members = by_function[function]
        present = {row.county_geoid for row in members}
        disclosed = {row.county_geoid for row in members if row.disclosure_code == ""}
        functions[function] = {
            "rows": len(members),
            "suppressed_rows": sum(row.disclosure_code == "N" for row in members),
            "counties": len(present),
            "counties_with_disclosed_rows": len(disclosed),
            "counties_without_selected_rows": sorted(county_ids - present),
            "counties_with_only_suppressed_rows": sorted(present - disclosed),
        }
    parent_groups: dict[str, Counter[str]] = defaultdict(Counter)
    for key, parent in sorted(parents.items()):
        children = by_parent[key]
        group = parent_groups[f"{parent.ownership_code}/{parent.naics_code}"]
        group["parent_rows"] += 1
        group["parents_without_selected_rows"] += not children
        group["parents_with_suppressed_selected_rows"] += any(
            row.disclosure_code == "N" for row in children
        )
        group["establishment_sum_difference"] += (
            sum(row.annual_avg_establishments for row in children)
            - parent.annual_avg_establishments
        )
        if (
            parent.annual_avg_jobs is not None
            and children
            and all(row.annual_avg_jobs is not None for row in children)
        ):
            group["comparable_published_job_rows"] += 1
            difference = sum(row.annual_avg_jobs or 0 for row in children) - parent.annual_avg_jobs
            group["published_job_sum_difference"] += difference
            group["published_job_groups_with_difference"] += difference != 0
    total_county_jobs, total_unallocated_jobs = (
        sum(county_jobs.values()),
        sum(unallocated_jobs.values()),
    )
    diagnostics = {
        "rows": len(observations),
        "counties_with_rows": len({row.county_geoid for row in observations}),
        "counties_without_selected_rows": sorted(
            county_ids - {row.county_geoid for row in observations}
        ),
        "ownership_rows": dict(sorted(Counter(row.ownership_code for row in observations).items())),
        "suppressed_rows": sum(row.disclosure_code == "N" for row in observations),
        "rounded_zero_establishment_rows": sum(
            row.annual_avg_establishments == 0 for row in observations
        ),
        "published_zero_jobs_positive_payroll_rows": sum(
            row.annual_avg_jobs == 0 and (row.annual_payroll_usd or 0) > 0 for row in observations
        ),
        "functions": functions,
        "parent_sector_rows": len(parents),
        "parent_sector_diagnostics": {
            key: dict(sorted(value.items())) for key, value in sorted(parent_groups.items())
        },
        "selected_groups_without_parent_rows": len(by_parent.keys() - parents.keys()),
        "outside_county_rows": dict(sorted(outside_rows.items())),
        "national_jobs": {
            "us_jobs": us_jobs,
            "county_jobs": total_county_jobs,
            "domestic_unallocated_jobs": total_unallocated_jobs,
            "domestic_unallocated_areas": sorted(unallocated_jobs),
            "reconciliation_residual_jobs": None
            if us_jobs is None
            else us_jobs - total_county_jobs - total_unallocated_jobs,
        },
    }
    return Capture(observations, diagnostics)


def selected_sources(source_root: Path) -> dict[str, Path]:
    manifest = json.loads(SOURCE_MANIFEST.read_bytes(), object_pairs_hook=_unique_object)
    if manifest.get("contract") != "NationalCountyReference2024SourcesV1":
        raise ReferenceBuildError("source_manifest_contract")
    selected = {}
    for entry in manifest["sources"]:
        if entry["id"] not in {"tiger", "qcew"}:
            continue
        relative = Path(entry["path"])
        if relative.is_absolute() or ".." in relative.parts or entry["id"] in selected:
            raise ReferenceBuildError("source_manifest_identity")
        path = source_root / relative
        if path.stat().st_size != entry["bytes"] or sha256(path) != entry["sha256"]:
            raise ReferenceBuildError(f"source_digest: {entry['id']}")
        selected[entry["id"]] = path
    if set(selected) != {"tiger", "qcew"}:
        raise ReferenceBuildError("source_manifest_coverage")
    return selected


def build(
    *,
    source_root: Path,
    artifact_out: Path = ARTIFACT_OUT,
    metadata_out: Path = METADATA_OUT,
    mapping_path: Path = MAPPING_PATH,
) -> dict[str, Any]:
    sources = selected_sources(source_root)
    ensure_output_paths(
        (artifact_out, metadata_out), (*sources.values(), SOURCE_MANIFEST, mapping_path)
    )
    mapping = load_mapping(mapping_path)
    counties = {row.county_geoid for row in read_counties(sources["tiger"])}
    with sources["qcew"].open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {
            "area_fips",
            "own_code",
            "industry_code",
            "agglvl_code",
            "size_code",
            "year",
            "qtr",
            "disclosure_code",
            *SOURCE_METRICS,
        }
        if not required.issubset(reader.fieldnames or []):
            raise ReferenceBuildError("source_schema")
        result = capture(reader, counties, mapping)
    table = pa.Table.from_pylist([asdict(row) for row in result.observations], schema=SCHEMA)
    buffer = io.BytesIO()
    pq.write_table(
        table,
        buffer,
        compression="zstd",
        compression_level=19,
        use_dictionary=[
            "county_geoid",
            "ownership_code",
            "naics_code",
            "agglvl_code",
            "disclosure_code",
        ],
        write_statistics=True,
        version="2.6",
        row_group_size=1_000_000,
    )
    blob = buffer.getvalue()
    metadata = {
        "contract": "NationalQcewFunctionBasis2024V1",
        "issue": "PER-40",
        "source_values_evidence_class": "Observed",
        "coverage_diagnostics_evidence_class": "Derived",
        "artifact": {
            "path": provenance_path(artifact_out),
            "format": "parquet",
            "rows": len(result.observations),
            "bytes": len(blob),
            "sha256": hashlib.sha256(blob).hexdigest(),
            "columns": table.column_names,
            "ordering": ["county_geoid", "ownership_code", "naics_code"],
            "writer": {
                "pyarrow": pa.__version__,
                "compression": "zstd",
                "compression_level": 19,
                "version": "2.6",
                "row_group_size": 1_000_000,
            },
        },
        "source_manifest": {
            "path": provenance_path(SOURCE_MANIFEST),
            "sha256": sha256(SOURCE_MANIFEST),
            "selected_source_ids": ["tiger", "qcew"],
        },
        "function_mapping": {
            "path": provenance_path(mapping_path),
            "sha256": sha256(mapping_path),
            "evidence_class": "Designed",
        },
        "semantics": {
            "period": "2024 annual observations, NAICS source classifications as supplied",
            "jobs": "covered workplace jobs; not distinct persons or resident workers",
            "establishments": "annual-average statistical establishments; published rounded zero stays present",
            "payroll": "calendar-year USD total, independent of rounded annual-average jobs",
            "weekly_wage": "annual-average USD per employee per week, not derived by division",
            "disclosure": "N preserves establishments and replaces the three verified source-zero withheld placeholders with null usable values; blank means published",
            "absent_cell": "not_published; no synthetic zero row, no imputation",
            "ownership": "federal/state/local/private is independent of function, class and funding",
            "function_assignment": "Designed proxy from a disjoint NAICS cut; product end-use and executable recipes are not observed",
            "parent_diagnostics": "source parent sector rows are comparison controls, never additive output; annual-average rounding and suppressed/absent children prevent presumed exact reconciliation",
            "outside_county_jobs": "domestic xx999 jobs remain unallocated and distinct from territorial exclusions; no county fallback",
            "runtime_consumers": [],
        },
        "coverage": result.diagnostics,
    }
    artifact_out.parent.mkdir(parents=True, exist_ok=True)
    metadata_out.parent.mkdir(parents=True, exist_ok=True)
    artifact_out.write_bytes(blob)
    metadata_out.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--artifact-out", type=Path, default=ARTIFACT_OUT)
    parser.add_argument("--metadata-out", type=Path, default=METADATA_OUT)
    args = parser.parse_args()
    metadata = build(
        source_root=args.source_root, artifact_out=args.artifact_out, metadata_out=args.metadata_out
    )
    print(json.dumps(metadata["artifact"], indent=2))


if __name__ == "__main__":
    main()
