#!/usr/bin/env python3
"""Build PER-40's observed national county foundation from pinned 2024 sources.

TIGER defines the 50-state/DC universe. ACS supplies resident persons, households,
and employment-status persons; QCEW supplies workplace jobs and establishments.
The artifact initializes no game entities, employers, labor pools, or money.
Bulk ACS files have sentinel literals, but no API annotation fields. Retain the
literals and their interpreted status; do not invent annotation observations.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
import struct
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / "tools/national_county_reference_2024_sources.json"
ARTIFACT_OUT = ROOT / "src/babylon/data/reference/economy/national_county_reference_2024.csv.gz"
METADATA_OUT = ARTIFACT_OUT.with_name("national_county_reference_2024.metadata.json")
STATE_COUNTS: Final = dict(
    zip(
        "01 02 04 05 06 08 09 10 11 12 13 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 44 45 46 47 48 49 50 51 53 54 55 56".split(),
        (
            67,
            30,
            15,
            75,
            58,
            64,
            9,
            3,
            1,
            67,
            159,
            5,
            44,
            102,
            92,
            99,
            105,
            120,
            64,
            16,
            24,
            14,
            83,
            87,
            82,
            115,
            56,
            93,
            17,
            10,
            21,
            33,
            62,
            100,
            53,
            88,
            77,
            36,
            67,
            5,
            46,
            66,
            95,
            254,
            29,
            14,
            133,
            39,
            55,
            72,
            23,
        ),
        strict=True,
    )
)
MAX_I64: Final = 2**63 - 1
INTEGER = re.compile(r"(?:0|[1-9][0-9]*)\Z", re.ASCII)
COUNTY_ID = re.compile(r"[0-9]{5}\Z", re.ASCII)
ACS_GEO_ID = re.compile(r"0500000US([0-9]{5})\Z", re.ASCII)
SENTINELS: Final = {
    "-666666666": "estimate_not_computable",
    "-999999999": "insufficient_sample_cases",
    "-888888888": "not_applicable_or_available",
    "-222222222": "moe_not_computable",
    "-333333333": "moe_open_ended_median",
    "-555555555": "controlled_estimate",
}


class ReferenceBuildError(ValueError):
    """A source or artifact boundary failed; no fallback is authorized."""


@dataclass(frozen=True)
class Cell:
    """An optional usable count and its literal source evidence."""

    value: int | None
    raw: str
    status: str

    def fields(self) -> tuple[str, str, str]:
        return ("" if self.value is None else str(self.value), self.raw, self.status)


@dataclass(frozen=True)
class County:
    county_geoid: str
    state_fips: str
    county_fips: str
    county_name: str
    land_square_metres: str
    water_square_metres: str
    internal_point_latitude: str
    internal_point_longitude: str


@dataclass(frozen=True)
class Series:
    name: str
    table: str
    line: str
    unit: str
    universe: str


ACS_SERIES: Final = (
    Series("population_persons", "B01003", "001", "persons", "Total population"),
    Series("households", "B11001", "001", "households", "Households"),
    Series("age_16_plus_persons", "B23025", "001", "persons", "Population 16 years and over"),
    Series("labor_force_persons", "B23025", "002", "persons", "Population 16 years and over"),
    Series(
        "civilian_labor_force_persons", "B23025", "003", "persons", "Population 16 years and over"
    ),
    Series("civilian_employed_persons", "B23025", "004", "persons", "Population 16 years and over"),
    Series(
        "civilian_unemployed_persons", "B23025", "005", "persons", "Population 16 years and over"
    ),
    Series("armed_forces_persons", "B23025", "006", "persons", "Population 16 years and over"),
    Series(
        "not_in_labor_force_persons", "B23025", "007", "persons", "Population 16 years and over"
    ),
)
QCEW_MEASURES: Final = {
    "qcew_establishments": {
        "source": "annual_avg_estabs",
        "unit": "establishments",
        "period": "2024 annual average",
    },
    "qcew_jobs": {"source": "annual_avg_emplvl", "unit": "jobs", "period": "2024 annual average"},
    "qcew_annual_payroll_usd": {
        "source": "total_annual_wages",
        "unit": "USD",
        "period": "2024 calendar-year total",
    },
    "qcew_mean_weekly_wage_usd": {
        "source": "annual_avg_wkly_wage",
        "unit": "USD per employee per week",
        "period": "2024 annual-average weekly rate",
    },
}
COUNTY_COLUMNS: Final = tuple(County.__dataclass_fields__)
COLUMNS: Final = (
    *COUNTY_COLUMNS,
    *(
        f"acs_{series.name}_{kind}{suffix}"
        for series in ACS_SERIES
        for kind in ("estimate", "moe")
        for suffix in ("", "_raw", "_status")
    ),
    "qcew_status",
    "qcew_disclosure_code",
    *(f"{name}{suffix}" for name in QCEW_MEASURES for suffix in ("", "_raw", "_status")),
)
METADATA: Final = {
    "contract": "NationalCountyReference2024V1",
    "issue": "PER-40",
    "evidence_class": "Observed",
    "classifications": {
        "source_values_and_sentinel_literals": "Observed",
        "interpreted_statuses_and_hashes": "Derived",
        "scope_schema_and_ordering": "Designed",
    },
    "acs_series": [asdict(series) for series in ACS_SERIES],
    "qcew_measures": QCEW_MEASURES,
    "semantics": {
        "scope": "TIGER2024 counties and county equivalents, 50 states and District of Columbia",
        "acs_period": "2020-2024 five-year period estimates; not a 2024 point-in-time census",
        "acs_annotation_fields": "unavailable_in_bulk_source",
        "acs_raw_fields": "literal bulk E/M tokens; no API annotation fields are inferred",
        "acs_moe": "90 percent margin of error; controlled-estimate sentinel retained with null numeric MOE, not silently replaced with zero",
        "acs_missing": "missing estimate stays null regardless of other observations; missing county source row is an error",
        "qcew_population": "workplace covered jobs, not distinct resident persons or a workforce",
        "qcew_establishments": "annual-average statistical establishments, not identified employers or production sites",
        "qcew_missing": "not_published means absent selected source row, not observed zero or proven suppression",
        "qcew_suppression": "N keeps establishments; jobs, payroll and wage have null usable values with raw source tokens retained",
        "numeric_conversion": "exact nonnegative signed-64-bit integers; no imputation, jobs-to-persons conversion, allocation or rounding",
        "geography_points": "TIGER internal points as published; not centroids or boundaries",
        "runtime_consumers": [],
    },
    "sentinel_statuses": SENTINELS,
    "annotation_documentation": "https://www.census.gov/data/developers/data-sets/acs-1year/notes-on-acs-estimate-and-annotation-values.html",
}


def integer(raw: str, identity: str) -> int:
    if not INTEGER.fullmatch(raw) or len(raw) > 19 or int(raw) > MAX_I64:
        raise ReferenceBuildError(f"{identity}: invalid nonnegative integer {raw!r}")
    return int(raw)


def parse_acs_cell(raw: str, *, margin: bool) -> Cell:
    if raw in ("", "null"):
        return Cell(None, raw, "missing")
    if raw in SENTINELS:
        if (not margin and raw in {"-222222222", "-333333333", "-555555555"}) or (
            margin and raw == "-666666666"
        ):
            raise ReferenceBuildError(f"acs_sentinel_role: {raw}")
        return Cell(None, raw, SENTINELS[raw])
    return Cell(integer(raw, "acs_value"), raw, "published")


def validate_counties(
    rows: Iterable[County], expected_counts: Mapping[str, int] = STATE_COUNTS
) -> tuple[County, ...]:
    counties: dict[str, County] = {}
    for row in rows:
        if (
            not COUNTY_ID.fullmatch(row.county_geoid)
            or row.county_geoid != row.state_fips + row.county_fips
        ):
            raise ReferenceBuildError(f"county_identity: {row.county_geoid}")
        if row.county_geoid in counties:
            raise ReferenceBuildError(f"duplicate_county: {row.county_geoid}")
        counties[row.county_geoid] = row
    counts = Counter(row.state_fips for row in counties.values())
    if counts != dict(expected_counts):
        raise ReferenceBuildError(f"county_coverage: {dict(sorted(counts.items()))}")
    return tuple(counties[key] for key in sorted(counties))


def read_counties(path: Path) -> tuple[County, ...]:
    """Read the pinned, bounded dBASE attribute file without loading polygons."""
    raw = path.read_bytes()
    if len(raw) < 33 or len(raw) > 2_000_000:
        raise ReferenceBuildError("tiger_dbf_size")
    count, header_size, row_size = struct.unpack_from("<IHH", raw, 4)
    if count > 4000 or header_size < 33 or header_size > len(raw) or raw[header_size - 1] != 13:
        raise ReferenceBuildError("tiger_dbf_header")
    if header_size + count * row_size > len(raw):
        raise ReferenceBuildError("tiger_dbf_truncated")
    fields: list[tuple[str, int]] = []
    for offset in range(32, header_size - 1, 32):
        descriptor = raw[offset : offset + 32]
        fields.append((descriptor[:11].split(b"\0")[0].decode("ascii"), descriptor[16]))
    if sum(size for _, size in fields) + 1 != row_size or len({name for name, _ in fields}) != len(
        fields
    ):
        raise ReferenceBuildError("tiger_dbf_fields")
    required = {
        "GEOID",
        "STATEFP",
        "COUNTYFP",
        "NAMELSAD",
        "ALAND",
        "AWATER",
        "INTPTLAT",
        "INTPTLON",
    }
    if not required.issubset({name for name, _ in fields}):
        raise ReferenceBuildError("tiger_dbf_schema")
    rows = []
    for index in range(count):
        record = raw[header_size + index * row_size : header_size + (index + 1) * row_size]
        if record[:1] != b" ":
            raise ReferenceBuildError("tiger_dbf_deleted_row")
        offset = 1
        values = {}
        for name, size in fields:
            values[name] = record[offset : offset + size].decode("utf-8").strip()
            offset += size
        if values["STATEFP"] not in STATE_COUNTS:
            continue
        integer(values["ALAND"], "tiger_land")
        integer(values["AWATER"], "tiger_water")
        rows.append(
            County(
                *(
                    values[key]
                    for key in (
                        "GEOID",
                        "STATEFP",
                        "COUNTYFP",
                        "NAMELSAD",
                        "ALAND",
                        "AWATER",
                        "INTPTLAT",
                        "INTPTLON",
                    )
                )
            )
        )
    return validate_counties(rows)


def read_acs_table(
    path: Path, table: str, county_ids: set[str]
) -> dict[str, dict[str, tuple[Cell, Cell]]]:
    series = [series for series in ACS_SERIES if series.table == table]
    if not series:
        raise ReferenceBuildError(f"acs_table: {table}")
    line_count = {"B01003": 1, "B11001": 9, "B23025": 7}[table]
    expected = [
        "GEO_ID",
        *(f"{table}_{kind}{line:03}" for line in range(1, line_count + 1) for kind in ("E", "M")),
    ]
    result = {}
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="|")
        if reader.fieldnames != expected:
            raise ReferenceBuildError(f"acs_schema: {table}")
        for row in reader:
            match = ACS_GEO_ID.fullmatch(row["GEO_ID"])
            if match is None or match[1][:2] not in STATE_COUNTS:
                continue
            geoid = match[1]
            if geoid not in county_ids:
                raise ReferenceBuildError(f"acs_unexpected_county: {table}/{geoid}")
            if geoid in result:
                raise ReferenceBuildError(f"duplicate_acs_county: {table}/{geoid}")
            if set(row) != set(expected) or any(value is None for value in row.values()):
                raise ReferenceBuildError(f"acs_row_shape: {table}/{geoid}")
            result[geoid] = {
                series.name: (
                    parse_acs_cell(row[f"{table}_E{series.line}"], margin=False),
                    parse_acs_cell(row[f"{table}_M{series.line}"], margin=True),
                )
                for series in series
            }
    if set(result) != county_ids:
        raise ReferenceBuildError(
            f"acs_coverage: {table}, missing {sorted(county_ids - set(result))}"
        )
    return result


@dataclass(frozen=True)
class QcewRow:
    status: str
    disclosure_code: str
    establishments: Cell
    jobs: Cell
    payroll: Cell
    weekly_wage: Cell


def parse_qcew_row(row: Mapping[str, str]) -> QcewRow:
    identity = tuple(
        row.get(key)
        for key in ("own_code", "industry_code", "agglvl_code", "size_code", "year", "qtr")
    )
    if identity != ("0", "10", "70", "0", "2024", "A"):
        raise ReferenceBuildError(f"qcew_identity: {row.get('area_fips')}")
    disclosure = row.get("disclosure_code")
    if disclosure not in {"", "N"}:
        raise ReferenceBuildError(f"qcew_disclosure: {disclosure!r}")
    cells = []
    for index, spec in enumerate(QCEW_MEASURES.values()):
        raw = row[spec["source"]]
        value = integer(raw, "qcew_value")
        suppressed = disclosure == "N" and index > 0
        if suppressed and value != 0:
            raise ReferenceBuildError("qcew_suppressed_nonzero")
        cells.append(
            Cell(None if suppressed else value, raw, "suppressed" if suppressed else "published")
        )
    return QcewRow("suppressed" if disclosure else "published", disclosure, *cells)


def read_qcew(path: Path, county_ids: set[str]) -> tuple[dict[str, QcewRow], list[str]]:
    selected: dict[str, QcewRow] = {}
    excluded = []
    with path.open(encoding="utf-8", newline="") as stream:
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
            *(spec["source"] for spec in QCEW_MEASURES.values()),
        }
        if not required.issubset(reader.fieldnames or []) or len(
            set(reader.fieldnames or [])
        ) != len(reader.fieldnames or []):
            raise ReferenceBuildError("qcew_schema")
        for row in reader:
            if row["agglvl_code"] != "70" or row["own_code"] != "0":
                continue
            geoid = row["area_fips"]
            if geoid not in county_ids:
                excluded.append(geoid)
                continue
            if geoid in selected:
                raise ReferenceBuildError(f"duplicate_qcew_county: {geoid}")
            if any(value is None for value in row.values()) or None in row:
                raise ReferenceBuildError(f"qcew_row_shape: {geoid}")
            selected[geoid] = parse_qcew_row(row)
    return selected, sorted(excluded)


def assemble_row(
    county: County, acs: Mapping[str, tuple[Cell, Cell]], qcew: QcewRow | None
) -> list[str]:
    result = list(asdict(county).values())
    for series in ACS_SERIES:
        for cell in acs[series.name]:
            result.extend(cell.fields())
    if qcew is None:
        result.extend(("not_published", ""))
        result.extend(field for _ in QCEW_MEASURES for field in ("", "", "not_published"))
    else:
        result.extend((qcew.status, qcew.disclosure_code))
        for cell in (qcew.establishments, qcew.jobs, qcew.payroll, qcew.weekly_wage):
            result.extend(cell.fields())
    return result


def check_acs_identities(cells: Mapping[str, tuple[Cell, Cell]], geoid: str) -> None:
    values = {name: pair[0].value for name, pair in cells.items()}
    for total, left, right in (
        ("age_16_plus_persons", "labor_force_persons", "not_in_labor_force_persons"),
        ("labor_force_persons", "civilian_labor_force_persons", "armed_forces_persons"),
        (
            "civilian_labor_force_persons",
            "civilian_employed_persons",
            "civilian_unemployed_persons",
        ),
    ):
        a, b, c = values[total], values[left], values[right]
        if a is not None and b is not None and c is not None and a != b + c:
            raise ReferenceBuildError(f"acs_partition: {geoid}/{total}")
    population, adults = values["population_persons"], values["age_16_plus_persons"]
    if population is not None and adults is not None and adults > population:
        raise ReferenceBuildError(f"acs_population_universe: {geoid}")


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ReferenceBuildError(f"manifest_duplicate_key: {key}")
        result[key] = value
    return result


def verify_sources(source_root: Path, manifest_path: Path) -> dict[str, Path]:
    manifest = json.loads(manifest_path.read_bytes(), object_pairs_hook=_unique_object)
    if manifest.get("contract") != "NationalCountyReference2024SourcesV1":
        raise ReferenceBuildError("source_manifest_contract")
    sources = {}
    for entry in manifest["sources"]:
        identity, relative = entry["id"], Path(entry["path"])
        if relative.is_absolute() or ".." in relative.parts or identity in sources:
            raise ReferenceBuildError("source_manifest_path_or_duplicate")
        source = source_root / relative
        if source.stat().st_size != entry["bytes"] or sha256(source) != entry["sha256"]:
            raise ReferenceBuildError(f"source_digest: {identity}")
        sources[identity] = source
    if set(sources) != {"tiger", "qcew", "B01003", "B11001", "B23025", "acs_table_shells"}:
        raise ReferenceBuildError("source_manifest_coverage")
    return sources


def read_acs_definitions(path: Path) -> dict[str, dict[str, str]]:
    """Bind selected estimates to the official table labels and universes."""
    wanted = {f"{series.table}_{series.line}": series for series in ACS_SERIES}
    definitions = {}
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="|")
        expected = ["Table ID", "Line", "Indent", "Unique ID", "Label", "Title", "Universe", "Type"]
        if reader.fieldnames != expected:
            raise ReferenceBuildError("acs_definition_schema")
        for row in reader:
            key = row["Unique ID"]
            if key not in wanted:
                continue
            if key in definitions:
                raise ReferenceBuildError(f"duplicate_acs_definition: {key}")
            if row["Universe"] != wanted[key].universe or row["Type"] != "int":
                raise ReferenceBuildError(f"acs_definition_universe: {key}")
            definitions[key] = {
                "label": row["Label"],
                "title": row["Title"],
                "universe": row["Universe"],
                "indent": row["Indent"],
            }
    if set(definitions) != set(wanted):
        raise ReferenceBuildError("acs_definition_coverage")
    return definitions


def build(
    *,
    source_root: Path,
    artifact_out: Path = ARTIFACT_OUT,
    metadata_out: Path = METADATA_OUT,
    source_manifest: Path = SOURCE_MANIFEST,
) -> dict[str, Any]:
    sources = verify_sources(source_root, source_manifest)
    definitions = read_acs_definitions(sources["acs_table_shells"])
    counties = read_counties(sources["tiger"])
    ids = {county.county_geoid for county in counties}
    acs: dict[str, dict[str, tuple[Cell, Cell]]] = {geoid: {} for geoid in ids}
    for table in ("B01003", "B11001", "B23025"):
        for geoid, cells in read_acs_table(sources[table], table, ids).items():
            acs[geoid].update(cells)
    qcew, excluded = read_qcew(sources["qcew"], ids)
    rows = []
    for county in counties:
        check_acs_identities(acs[county.county_geoid], county.county_geoid)
        rows.append(assemble_row(county, acs[county.county_geoid], qcew.get(county.county_geoid)))
    text = io.StringIO(newline="")
    writer = csv.writer(text, lineterminator="\n")
    writer.writerow(COLUMNS)
    writer.writerows(rows)
    payload = text.getvalue().encode("utf-8")
    compressed = io.BytesIO()
    with gzip.GzipFile(
        filename="", fileobj=compressed, mode="wb", compresslevel=9, mtime=0
    ) as stream:
        stream.write(payload)
    blob = compressed.getvalue()
    metadata = {
        **METADATA,
        "acs_source_definitions": definitions,
        "regeneration": "UV_PROJECT_ENVIRONMENT=.venv mise exec -- uv run --frozen python tools/make_national_county_reference.py --source-root /media/user/data/babylon-data",
        "source_manifest": {
            "path": str(source_manifest.relative_to(ROOT))
            if source_manifest.is_relative_to(ROOT)
            else source_manifest.name,
            "sha256": sha256(source_manifest),
        },
        "artifact": {
            "path": str(ARTIFACT_OUT.relative_to(ROOT)),
            "format": "csv.gz",
            "compression": "gzip-mtime-0",
            "columns": COLUMNS,
            "rows": len(rows),
            "bytes": len(blob),
            "uncompressed_bytes": len(payload),
            "sha256": hashlib.sha256(blob).hexdigest(),
            "uncompressed_sha256": hashlib.sha256(payload).hexdigest(),
        },
        "coverage": {
            "state_counties": STATE_COUNTS,
            "acs_counties_per_table": {table: len(ids) for table in ("B01003", "B11001", "B23025")},
            "controlled_population_moes": sum(
                acs[geoid]["population_persons"][1].status == "controlled_estimate" for geoid in ids
            ),
            "acs_cell_status_counts": dict(
                sorted(
                    Counter(
                        cell.status
                        for cells in acs.values()
                        for pair in cells.values()
                        for cell in pair
                    ).items()
                )
            ),
            "qcew_counties": len(qcew),
            "qcew_missing_counties": sorted(ids - qcew.keys()),
            "qcew_status_counts": dict(
                sorted(Counter(row.status for row in qcew.values()).items())
            ),
            "qcew_excluded_area_fips": excluded,
        },
    }
    artifact_out.parent.mkdir(parents=True, exist_ok=True)
    metadata_out.parent.mkdir(parents=True, exist_ok=True)
    artifact_out.write_bytes(blob)
    metadata_out.write_text(
        json.dumps(metadata, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--artifact-out", type=Path, default=ARTIFACT_OUT)
    parser.add_argument("--metadata-out", type=Path, default=METADATA_OUT)
    args = parser.parse_args()
    metadata = build(
        source_root=args.source_root, artifact_out=args.artifact_out, metadata_out=args.metadata_out
    )
    print(
        json.dumps({"artifact": metadata["artifact"], "coverage": metadata["coverage"]}, indent=2)
    )


if __name__ == "__main__":
    main()
