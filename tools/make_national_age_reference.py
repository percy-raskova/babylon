#!/usr/bin/env python3
"""Build four resident age bands from the 2020–2024 ACS five-year county estimates."""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from make_national_county_reference import (
    ACS_GEO_ID,
    ROOT,
    ReferenceBuildError,
    ensure_output_paths,
    integer,
    provenance_path,
    sha256,
)

COUNTY_PATH = ROOT / "src/babylon/data/reference/economy/national_county_reference_2024.csv.gz"
MANIFEST = ROOT / "tools/national_age_reference_2024_sources.json"
ARTIFACT = COUNTY_PATH.with_name("national_age_reference_2024.csv.gz")
METADATA = ARTIFACT.with_name("national_age_reference_2024.metadata.json")
COLUMNS: Final = ("county_geoid", "under_16", "age_16_17", "age_18_64", "age_65_plus")
type AgeBands = tuple[int, int, int, int]


def age_bands(county: str, cells: Mapping[int, int], controls: tuple[int, int]) -> AgeBands:
    population, age_16_plus = controls
    if cells[1] != population:
        raise ReferenceBuildError(f"population_control: {county}")
    if (
        cells[1] != cells[2] + cells[26]
        or cells[2] != sum(cells[i] for i in range(3, 26))
        or cells[26] != sum(cells[i] for i in range(27, 50))
    ):
        raise ReferenceBuildError(f"sex_partition: {county}")

    def both_sexes(first_male: int, last_male: int) -> int:
        return sum(cells[i] + cells[i + 24] for i in range(first_male, last_male + 1))

    age_18_64 = both_sexes(7, 19)
    age_65_plus = both_sexes(20, 25)
    age_16_17 = age_16_plus - age_18_64 - age_65_plus
    age_15 = both_sexes(6, 6) - age_16_17
    if min(age_15, age_16_17) < 0:
        raise ReferenceBuildError(f"age_15_17: {county}")
    under_16 = both_sexes(3, 5) + age_15
    if under_16 != population - age_16_plus:
        raise ReferenceBuildError(f"under_16_control: {county}")
    return under_16, age_16_17, age_18_64, age_65_plus


def validate_roster(actual: set[str], expected: set[str]) -> None:
    if actual != expected:
        raise ReferenceBuildError(
            f"county_coverage: missing {expected - actual}, extra {actual - expected}"
        )


def encode(table: Path) -> tuple[bytes, dict[str, int], int]:
    with gzip.open(COUNTY_PATH, "rt", newline="") as stream:
        controls = {
            row["county_geoid"]: (
                integer(row["acs_population_persons_estimate"], "population"),
                integer(row["acs_age_16_plus_persons_estimate"], "age_16_plus"),
            )
            for row in csv.DictReader(stream)
        }
    if len(controls) != 3144:
        raise ReferenceBuildError("county_control_coverage")
    resolved: dict[str, AgeBands] = {}
    dependencies: set[str] = set()
    age_15 = 0
    with table.open(newline="") as stream:
        reader = csv.DictReader(stream, delimiter="|")
        expected = ["GEO_ID", *(f"B01001_{k}{i:03}" for i in range(1, 50) for k in "EM")]
        if reader.fieldnames != expected:
            raise ReferenceBuildError("age_source_schema")
        for row in reader:
            match = ACS_GEO_ID.fullmatch(row["GEO_ID"])
            if match is None or None in row or None in row.values():
                raise ReferenceBuildError(f"age_source_shape: {row['GEO_ID']}")
            county = match[1]
            if county in dependencies or county in resolved:
                raise ReferenceBuildError(f"duplicate_age_county: {county}")
            if county.startswith("72"):
                dependencies.add(county)
                continue
            if county not in controls:
                raise ReferenceBuildError(f"unexpected_age_county: {county}")
            cells = {i: integer(row[f"B01001_E{i:03}"], county) for i in range(1, 50)}
            bands = age_bands(county, cells, controls[county])
            resolved[county] = bands
            age_15 += cells[6] + cells[30] - bands[1]
    validate_roster(set(resolved), set(controls))
    if len(dependencies) != 78:
        raise ReferenceBuildError("puerto_rico_coverage")
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(COLUMNS)
    for geoid, bands in sorted(resolved.items()):
        writer.writerow((geoid, *bands))
    totals = {
        key: sum(bands[i] for bands in resolved.values()) for i, key in enumerate(COLUMNS[1:])
    }
    return buffer.getvalue().encode("ascii"), totals, age_15


def build(source_root: Path, artifact_out: Path, metadata_out: Path) -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text())
    source = manifest["county_table"]
    table = source_root / source["path"]
    ensure_output_paths((artifact_out, metadata_out), (MANIFEST, COUNTY_PATH, table))
    if sha256(COUNTY_PATH) != manifest["county_reference_sha256"]:
        raise ReferenceBuildError("county_reference_digest")
    if table.stat().st_size != source["bytes"] or sha256(table) != source["sha256"]:
        raise ReferenceBuildError("age_source_digest")
    encoded, totals, age_15 = encode(table)
    artifact_out.parent.mkdir(parents=True, exist_ok=True)
    with (
        artifact_out.open("wb") as target,
        gzip.GzipFile(filename="", fileobj=target, mode="wb", mtime=0) as compressed,
    ):
        compressed.write(encoded)
    metadata = {
        "contract": "NationalAgeReference2024V1",
        "vintage": "ACS 2020–2024 five-year estimates",
        "universe": "Resident population, including group quarters, in the 50 states and DC",
        "evidence": "Derived from published ACS estimates. The reference contains county margins. Margins of error are retained in the sources. No household cross-tabulation or derived margin of error is asserted.",
        "artifact": {"path": provenance_path(artifact_out), "sha256": sha256(artifact_out)},
        "source_manifest": {"path": provenance_path(MANIFEST), "sha256": sha256(MANIFEST)},
        "county_control": {"path": provenance_path(COUNTY_PATH), "sha256": sha256(COUNTY_PATH)},
        "coverage": {
            "domestic_counties": 3144,
            "excluded_puerto_rico_municipios": 78,
            "missing_domestic_fips": 0,
        },
        "domestic_age_band_totals": totals,
        "domestic_resident_total": sum(totals.values()),
        "derived_age_15": age_15,
    }
    metadata_out.parent.mkdir(parents=True, exist_ok=True)
    metadata_out.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--artifact-out", default=ARTIFACT, type=Path)
    parser.add_argument("--metadata-out", default=METADATA, type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.source_root, args.artifact_out, args.metadata_out), indent=2))


if __name__ == "__main__":
    main()
