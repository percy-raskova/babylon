#!/usr/bin/env python3
"""Extract one pinned, observed Wayne repair-industry row; no commodity expansion."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

SOURCE_FILE = "2024.annual 26163 Wayne County, Michigan.csv"
SOURCE_SHA256 = "1382b5821ac95ca6f344e50f76b6846f76f841b0bc32ebf69ee8fbadc545481a"
OUTPUT = (
    Path(__file__).resolve().parents[1]
    / "src/babylon/data/reference/economy/wayne_maintenance_industry_2024.json"
)


def extract(source: Path) -> bytes:
    """Refuse source drift, ambiguity and suppression before transcribing exact units."""
    if source.name != SOURCE_FILE or source.stat().st_size > 1_048_576:
        raise ValueError("expected the bounded pinned Wayne annual source")
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("Wayne annual source SHA-256 differs from its admitted pin")
    selectors = {
        "area_fips": "26163",
        "own_code": "5",
        "industry_code": "811310",
        "agglvl_code": "78",
        "size_code": "0",
        "year": "2024",
        "qtr": "A",
    }
    rows = [
        row
        for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        if all(row[key] == value for key, value in selectors.items())
    ]
    if len(rows) != 1 or rows[0]["disclosure_code"]:
        raise ValueError("the selected repair observation is absent, ambiguous or suppressed")
    selected = rows[0]
    row: dict[str, object] = {
        key: selected[key]
        for key in (
            "area_fips",
            "area_title",
            "industry_code",
            "industry_title",
            "own_code",
            "agglvl_code",
            "disclosure_code",
        )
    }
    for key in (
        "annual_avg_estabs_count",
        "annual_avg_emplvl",
        "total_annual_wages",
        "annual_avg_wkly_wage",
    ):
        row[key] = int(selected[key])
    if row["annual_avg_estabs_count"] != 122:
        raise ValueError("the pinned repair establishment count differs")
    row.update(source_file=SOURCE_FILE, source_sha256=SOURCE_SHA256)
    artifact = {
        "schema": "MichiganMaintenanceIndustryV1",
        "evidence_class": "Observed",
        "vintage": 2024,
        "source_url": "https://data.bls.gov/cew/data/files/2024/csv/2024_annual_by_area.zip",
        "selection": selectors,
        "row": row,
    }
    return (json.dumps(artifact, sort_keys=True, indent=2) + "\n").encode()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if args.output.resolve() == args.source.resolve():
        raise ValueError("output cannot replace the pinned input source")
    data = extract(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    print(f"{args.output}: {len(data)} bytes; sha256={hashlib.sha256(data).hexdigest()}")


if __name__ == "__main__":
    main()
