#!/usr/bin/env python3
"""Version 2 of the national QCEW function cut: twelve trades.

Consumer goods and leisure are cut out of version 1's ten trades. This module
validates the version 2 mapping and builds on version 1's helpers; it never
edits version 1's mapping, builder or tables.
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

import make_national_qcew_function_basis as basis
import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]
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

MAPPING_V2_PATH: Final = ROOT / "contracts/national_qcew_function_mapping_v2.json"
FUNCTION_IDS_V2: Final = (
    "food",
    "extraction",
    "energy_utilities",
    "manufacturing",
    "consumer_goods",
    "capital_goods",
    "construction_housing",
    "distribution_transport",
    "household_services",
    "leisure_hospitality",
    "business_services",
    "public_provisioning",
)
ARTIFACT_OUT: Final = (
    ROOT / "src/babylon/data/reference/economy/national_qcew_function_basis_v2_2024.parquet"
)
METADATA_OUT: Final = ARTIFACT_OUT.with_suffix(".metadata.json")
ROLES: Final = ("county_leaf", "county_parent", "nation_leaf", "state_leaf")
PARENT_CODES: Final = ("10", "11", "115", "31-33", "312", "334", "335", "336", "53")
COUNTY_LEVELS: Final = frozenset({71, 74, 75, 76})
STATE_LEVELS: Final = frozenset({54, 55, 56})
NATION_LEVELS: Final = frozenset({14, 15, 16})
ALL_LEVELS: Final = COUNTY_LEVELS | STATE_LEVELS | NATION_LEVELS
NATION_AREA: Final = "US000"
SCHEMA_V2: Final = pa.schema(
    [
        pa.field("row_role", pa.string(), nullable=False),
        pa.field("area_fips", pa.string(), nullable=False),
        pa.field("ownership_code", pa.string(), nullable=False),
        pa.field("naics_code", pa.string(), nullable=False),
        pa.field("agglvl_code", pa.uint8(), nullable=False),
        pa.field("disclosure_code", pa.string(), nullable=False),
        pa.field("annual_avg_establishments", pa.int64(), nullable=False),
        pa.field("annual_avg_jobs", pa.int64(), nullable=True),
        pa.field("annual_payroll_usd", pa.int64(), nullable=True),
        pa.field("mean_weekly_wage_usd", pa.int64(), nullable=True),
    ]
)
DICTIONARY_COLUMNS: Final = (
    "row_role",
    "area_fips",
    "ownership_code",
    "naics_code",
    "agglvl_code",
    "disclosure_code",
)


def validate_mapping_v2(document: dict[str, Any]) -> basis.FunctionMapping:
    """Repeat version 1's checks under the version 2 contract name and ids."""
    if (
        document.get("contract") != "NationalQcewFunctionMappingV2"
        or document.get("evidence_class") != "Designed"
        or document.get("source_vintage") != 2024
    ):
        raise ReferenceBuildError("function_mapping_identity")
    if set(document.get("ownership_codes", {})) != set(basis.OWNERSHIP_CODES):
        raise ReferenceBuildError("function_mapping_ownership")
    functions = document.get("functions", [])
    if [item.get("id") for item in functions] != list(FUNCTION_IDS_V2):
        raise ReferenceBuildError("function_mapping_functions")
    codes: dict[str, str] = {}
    for function in functions:
        if not function.get("qualification") or not function.get("naics_codes"):
            raise ReferenceBuildError("function_mapping_qualification")
        for code in function["naics_codes"]:
            basis.aggregation_level(code)
            if code in codes or code == "99":
                raise ReferenceBuildError(f"duplicate_naics: {code}")
            codes[code] = function["id"]
    if document.get("residual_naics_codes") != ["99"]:
        raise ReferenceBuildError("function_mapping_residual")
    selected = frozenset((*codes, "99"))
    for code in selected:
        for other in selected - {code}:
            if other.startswith(code) or (
                code in basis.SECTORS and basis.parent_sector(other) == code
            ):
                raise ReferenceBuildError(f"overlapping_naics: {code}/{other}")
    return basis.FunctionMapping(document, codes, selected)


def load_mapping_v2(path: Path = MAPPING_V2_PATH) -> basis.FunctionMapping:
    return validate_mapping_v2(json.loads(path.read_bytes(), object_pairs_hook=_unique_object))


@dataclass(frozen=True)
class SourceRow:
    row_role: str
    area_fips: str
    ownership_code: str
    naics_code: str
    agglvl_code: int
    disclosure_code: str
    annual_avg_establishments: int
    annual_avg_jobs: int | None
    annual_payroll_usd: int | None
    mean_weekly_wage_usd: int | None

    @property
    def key(self) -> tuple[str, str, str, str]:
        return self.row_role, self.area_fips, self.ownership_code, self.naics_code


def role_level(code: str, role: str) -> int:
    """The QCEW aggregation level the role expects for this code."""
    if role == "county_leaf":
        return int(basis.aggregation_level(code))
    if role == "county_parent":
        if code == "10":
            return 71
        if code not in PARENT_CODES:
            raise ReferenceBuildError(f"unsupported_naics: {code}")
        return 74 if code in {"11", "31-33", "53"} else 75
    if role == "state_leaf":
        return int(basis.aggregation_level(code)) - 20
    if role == "nation_leaf":
        return int(basis.aggregation_level(code)) - 60
    raise ReferenceBuildError(f"unsupported_role: {role}")


def parse_source_row(row: Mapping[str, str], role: str) -> SourceRow:
    if tuple(row.get(key) for key in ("year", "qtr", "size_code")) != ("2024", "A", "0"):
        raise ReferenceBuildError("period_identity")
    code = row["industry_code"]
    level = role_level(code, role)
    if row.get("agglvl_code") != str(level):
        raise ReferenceBuildError(f"aggregation_identity: {code}")
    if row["own_code"] not in basis.OWNERSHIP_CODES:
        raise ReferenceBuildError("ownership_identity")
    disclosure = row.get("disclosure_code")
    if disclosure not in {"", "N"}:
        raise ReferenceBuildError("source_disclosure")
    values = [integer(row[name], "source_value") for name in basis.SOURCE_METRICS]
    if disclosure == "N" and values[1:] != [0, 0, 0]:
        raise ReferenceBuildError("suppressed_nonzero")
    return SourceRow(
        role,
        row["area_fips"],
        row["own_code"],
        code,
        level,
        disclosure,
        values[0],
        *(None if disclosure else value for value in values[1:]),
    )


@dataclass(frozen=True)
class CaptureV2:
    rows: tuple[SourceRow, ...]
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


def _area_kind(area: str, county_ids: set[str]) -> str | None:
    if area in county_ids:
        return "county"
    if area == NATION_AREA:
        return "nation"
    if area[:2] in STATE_COUNTS and area.endswith("000"):
        return "state"
    return None


def capture_basis_v2(
    rows: Iterable[Mapping[str, str]], county_ids: set[str], mapping: basis.FunctionMapping
) -> CaptureV2:
    selected: dict[tuple[str, str, str, str], SourceRow] = {}
    county_jobs: dict[str, int] = {}
    unallocated_jobs: dict[str, int] = {}
    us_jobs: int | None = None
    outside_rows: Counter[str] = Counter()
    parent_codes = frozenset(PARENT_CODES)
    for row in rows:
        area, ownership, code = (row[name] for name in ("area_fips", "own_code", "industry_code"))
        level_text = row["agglvl_code"]
        if ownership == "0" and code == "10":
            if area == NATION_AREA and level_text == "10":
                if us_jobs is not None:
                    raise ReferenceBuildError("duplicate_us_total")
                us_jobs = _jobs_total(row)
            elif level_text == "70" and (
                area in county_ids or (area[:2] in STATE_COUNTS and area.endswith("999"))
            ):
                totals = county_jobs if area in county_ids else unallocated_jobs
                if area in totals:
                    raise ReferenceBuildError(f"duplicate_county_total: {area}")
                totals[area] = _jobs_total(row)
        if ownership not in basis.OWNERSHIP_CODES or not level_text.isdigit():
            continue
        level = int(level_text)
        if level not in ALL_LEVELS:
            continue
        kind = _area_kind(area, county_ids)
        leaf = code in mapping.source_codes
        if kind is None:
            if leaf or code in parent_codes:
                outside_rows[
                    "domestic_unallocated"
                    if area[:2] in STATE_COUNTS and area.endswith("999")
                    else "outside_50_states_dc"
                ] += 1
            continue
        if kind == "county":
            role = "county_leaf" if leaf else "county_parent" if code in parent_codes else None
        else:
            role = f"{kind}_leaf" if leaf else None
        if role is None:
            continue
        if level != role_level(code, role):
            raise ReferenceBuildError(f"aggregation_identity: {code}")
        parsed = parse_source_row(row, role)
        if parsed.key in selected:
            raise ReferenceBuildError(f"duplicate_source_cell: {parsed.key}")
        selected[parsed.key] = parsed
    ordered = tuple(selected[key] for key in sorted(selected))
    leaves = [item for item in ordered if item.row_role == "county_leaf"]
    by_function: dict[str, list[SourceRow]] = defaultdict(list)
    for item in leaves:
        by_function[mapping.function_for(item.naics_code) or "unclassified"].append(item)
    functions = {}
    for function in (*FUNCTION_IDS_V2, "unclassified"):
        members = by_function[function]
        present = {item.area_fips for item in members}
        disclosed = {item.area_fips for item in members if item.disclosure_code == ""}
        functions[function] = {
            "rows": len(members),
            "suppressed_rows": sum(item.disclosure_code == "N" for item in members),
            "counties": len(present),
            "counties_with_disclosed_rows": len(disclosed),
            "counties_without_selected_rows": sorted(county_ids - present),
            "counties_with_only_suppressed_rows": sorted(present - disclosed),
        }
    total_county_jobs = sum(county_jobs.values())
    total_unallocated_jobs = sum(unallocated_jobs.values())
    diagnostics: dict[str, Any] = {
        "rows": len(ordered),
        "rows_by_role": {role: sum(r.row_role == role for r in ordered) for role in ROLES},
        "withheld_rows_by_role": {
            role: sum(r.row_role == role and r.disclosure_code == "N" for r in ordered)
            for role in ROLES
        },
        "counties_with_leaf_rows": len({item.area_fips for item in leaves}),
        "counties_without_leaf_rows": sorted(county_ids - {item.area_fips for item in leaves}),
        "ownership_rows": dict(sorted(Counter(item.ownership_code for item in leaves).items())),
        "rounded_zero_establishment_rows": sum(
            item.annual_avg_establishments == 0 for item in leaves
        ),
        "published_zero_jobs_positive_payroll_rows": sum(
            item.annual_avg_jobs == 0 and (item.annual_payroll_usd or 0) > 0 for item in leaves
        ),
        "functions": functions,
        "outside_rows": dict(sorted(outside_rows.items())),
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
    return CaptureV2(ordered, diagnostics)


def read_basis_v2(path: Path = ARTIFACT_OUT) -> tuple[SourceRow, ...]:
    """Read the committed basis, checking its schema and its metadata digest."""
    if pq.read_schema(path) != SCHEMA_V2:
        raise ReferenceBuildError("basis_v2_schema")
    metadata = json.loads(path.with_suffix(".metadata.json").read_bytes())
    if metadata["artifact"]["sha256"] != sha256(path):
        raise ReferenceBuildError("basis_v2_digest")
    return tuple(SourceRow(**row) for row in pq.read_table(path).to_pylist())


def build(
    *,
    source_root: Path,
    artifact_out: Path = ARTIFACT_OUT,
    metadata_out: Path = METADATA_OUT,
) -> dict[str, Any]:
    sources = basis.selected_sources(source_root)
    ensure_output_paths(
        (artifact_out, metadata_out), (*sources.values(), SOURCE_MANIFEST, MAPPING_V2_PATH)
    )
    mapping = load_mapping_v2()
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
            *basis.SOURCE_METRICS,
        }
        if not required.issubset(reader.fieldnames or []):
            raise ReferenceBuildError("source_schema")
        result = capture_basis_v2(reader, counties, mapping)
    table = pa.Table.from_pylist([asdict(row) for row in result.rows], schema=SCHEMA_V2)
    buffer = io.BytesIO()
    pq.write_table(
        table,
        buffer,
        compression="zstd",
        compression_level=19,
        use_dictionary=list(DICTIONARY_COLUMNS),
        write_statistics=True,
        version="2.6",
        row_group_size=1_000_000,
    )
    blob = buffer.getvalue()
    metadata = {
        "contract": "NationalQcewFunctionBasis2024V2",
        "issue": "PER-371",
        "source_values_evidence_class": "Observed",
        "coverage_diagnostics_evidence_class": "Derived",
        "artifact": {
            "path": provenance_path(artifact_out),
            "format": "parquet",
            "rows": len(result.rows),
            "bytes": len(blob),
            "sha256": hashlib.sha256(blob).hexdigest(),
            "columns": table.column_names,
            "ordering": ["row_role", "area_fips", "ownership_code", "naics_code"],
            "writer": {
                "pyarrow": pa.__version__,
                "compression": "zstd",
                "compression_level": 19,
                "version": "2.6",
                "row_group_size": 1_000_000,
            },
        },
        "regeneration": (
            "UV_PROJECT_ENVIRONMENT=.venv mise exec -- uv run --frozen python "
            "tools/make_national_qcew_function_basis_v2.py "
            "--source-root /media/user/data/babylon-data"
        ),
        "source_manifest": {
            "path": provenance_path(SOURCE_MANIFEST),
            "sha256": sha256(SOURCE_MANIFEST),
            "selected_source_ids": ["tiger", "qcew"],
        },
        "function_mapping": {
            "path": provenance_path(MAPPING_V2_PATH),
            "sha256": sha256(MAPPING_V2_PATH),
            "evidence_class": "Designed",
        },
        "semantics": {
            "period": "2024 annual observations, NAICS source classifications as supplied",
            "roles": "county_leaf: mapped or residual code in a county; county_parent: a parent code in a county, kept so a withheld parent can be seen; state_leaf and nation_leaf: the same leaf codes at state and national rows",
            "levels": "county 71/74/75/76, state 54/55/56, nation 14/15/16; a taken code at another level of those sets is refused",
            "jobs": "covered workplace jobs; not distinct persons or resident workers",
            "establishments": "annual-average statistical establishments; published rounded zero stays present",
            "payroll": "calendar-year USD total, independent of rounded annual-average jobs",
            "weekly_wage": "annual-average USD per employee per week, not derived by division",
            "disclosure": "N preserves establishments and replaces the verified source-zero withheld placeholders with null usable values; blank means published",
            "absent_cell": "not_published; no synthetic zero row, no imputation",
            "ownership": "federal/state/local/private is independent of function, class and funding",
            "function_assignment": "Designed proxy from a disjoint NAICS cut; product end-use is not observed",
            "parent_rows": "county parent rows are placement controls, never additive output; annual-average rounding and withheld children prevent presumed exact reconciliation",
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
    print(json.dumps(metadata["coverage"]["rows_by_role"]))


if __name__ == "__main__":
    main()
