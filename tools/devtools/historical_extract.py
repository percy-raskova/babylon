"""Pin small retrospective observations; the reference database is always read-only.

Run as ``python -m tools.devtools.historical_extract --database PATH --sources PATH``.
The Parquets retain source partitions and flags. Experiment inputs contain only
starting observations; target observations never enter the engine input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]
import yaml

COHORTS = ("26099/332", "26125/311", "26161/311", "26163/331", "26163/3363")
FREIGHT_SERIES = "detroit_canada_truck_import_hs72"
PYARROW_VERSION = "25.0.0"
DEFAULT_FIXTURES = Path(__file__).resolve().parents[2] / "tests/fixtures/historical/michigan"
EMPLOYMENT_SQL = """SELECT c.fips AS county_fips, i.naics_code, o.own_code,
 t.year, t.quarter, s.source_code, f.employment_begin, f.employment_end,
 f.employment_stable, f.hires_all, f.hires_new, f.separations,
 f.turnover_stable, f.firm_job_gains, f.firm_job_losses, f.firm_job_change,
 f.avg_monthly_earnings_stable_usd, f.payroll_usd,
 f.status_employment_begin, f.status_employment_end, f.status_employment_stable,
 f.status_hires_all, f.status_hires_new, f.status_separations,
 f.status_turnover_stable, f.status_firm_job_gains, f.status_firm_job_losses,
 f.status_firm_job_change, f.status_avg_monthly_earnings_stable, f.status_payroll
FROM fact_qwi_county_flow AS f
JOIN dim_county AS c USING (county_id)
JOIN dim_industry AS i USING (industry_id)
JOIN dim_ownership AS o USING (ownership_id)
JOIN dim_time AS t USING (time_id)
JOIN dim_data_source AS s USING (source_id)
WHERE o.own_code = '5' AND t.year BETWEEN 2009 AND 2019
 AND ((c.fips = '26163' AND i.naics_code IN ('331', '3363'))
 OR (c.fips = '26099' AND i.naics_code = '332')
 OR (c.fips IN ('26161', '26125') AND i.naics_code = '311'))
ORDER BY c.fips, i.naics_code, t.year, t.quarter"""
FREIGHT_SQL = """SELECT f.port_code, h.hs2_code, f.mode_code, f.trade_type,
 f.domestic_foreign, f.container_code, f.country, t.year, t.month,
 s.source_code, f.value_usd, f.shipwt_kg, f.freight_charges_usd
FROM fact_transborder_port_commodity AS f
JOIN dim_hs2_commodity AS h USING (hs2_id)
JOIN dim_time AS t USING (time_id)
JOIN dim_data_source AS s USING (source_id)
WHERE f.port_code = '3801' AND h.hs2_code = '72' AND f.country = '1220'
 AND f.mode_code = 5 AND f.trade_type = 2 AND t.year BETWEEN 2019 AND 2024
ORDER BY t.year, t.month, f.domestic_foreign, f.container_code"""


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def digest_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def snapshot_digest(manifest: dict[str, Any]) -> str:
    return hashlib.sha256(
        canonical_bytes({k: v for k, v in manifest.items() if k != "snapshot_sha256"})
    ).hexdigest()


def validate_rows(employment: list[dict[str, Any]], freight: list[dict[str, Any]]) -> None:
    expected_employment = {
        (s, y, q) for s in COHORTS for y in range(2009, 2020) for q in range(1, 5)
    }
    keys = [(f"{r['county_fips']}/{r['naics_code']}", r["year"], r["quarter"]) for r in employment]
    if len(keys) != 220 or set(keys) != expected_employment:
        raise ValueError(
            "employment coverage or duplicate rows differ from 220 pinned quarterly observations"
        )
    if any(r["own_code"] != "5" or r["source_code"] != "LEHD_QWI" for r in employment):
        raise ValueError("employment requires private-ownership QWI observations")
    for series in COHORTS:
        counties = [s.split("/")[1] for s in COHORTS if s.split("/")[0] == series.split("/")[0]]
        if any(a != b and b.startswith(a) for a in counties for b in counties):
            raise ValueError("overlapping employment industry aggregation")
    freight_keys = [
        (r["year"], r["month"], r["domestic_foreign"], r["container_code"]) for r in freight
    ]
    if len(freight_keys) != 82 or len(set(freight_keys)) != 82:
        raise ValueError("freight source partitions must contain 82 unique rows")
    if {(r["year"], r["month"]) for r in freight} != {
        (y, m) for y in range(2019, 2025) for m in range(1, 13)
    }:
        raise ValueError("freight requires all 72 months")
    for row in freight:
        if (
            row["port_code"],
            row["hs2_code"],
            row["country"],
            row["mode_code"],
            row["trade_type"],
            row["source_code"],
        ) != ("3801", "72", "1220", 5, 2, "BTS_TRANSBORDER"):
            raise ValueError("freight boundary must be Detroit Canadian truck imports of HS72")
        if row["shipwt_kg"] is None or row["shipwt_kg"] < 0:
            raise ValueError("freight import weights must be observed nonnegative kilograms")


def starting_specs(
    employment: list[dict[str, Any]], freight: list[dict[str, Any]], snapshots: dict[str, str]
) -> dict[str, dict[str, Any]]:
    series = []
    for row in employment:
        if row["year"] == 2010 and row["quarter"] == 1:
            if row["status_employment_begin"] != 1 or row["employment_begin"] is None:
                raise ValueError(
                    "initial employment requires an observed unsuppressed beginning-job count"
                )
            series.append(
                {
                    "series_id": f"{row['county_fips']}/{row['naics_code']}",
                    "jobs": row["employment_begin"],
                }
            )
    if len(series) != 5:
        raise ValueError("initial employment requires exactly five cohorts")
    base: dict[str, Any] = {
        "schema": "SimulationExperimentV1",
        "seed": 319,
        "interventions": [],
    }
    return {
        "employment": {
            **base,
            "profile": "historical_employment",
            "source_snapshot_sha256": snapshots["employment"],
            "epoch": "2010-01-01",
            "horizon": 131,
            "starting_snapshot": {"kind": "employment", "date": "2010-01-01", "series": series},
        },
        "freight": {
            **base,
            "profile": "historical_freight",
            "source_snapshot_sha256": snapshots["freight"],
            "epoch": "2019-02-01",
            "horizon": 78,
            "starting_snapshot": {
                "kind": "freight",
                "date": "2019-01-01",
                "series_id": FREIGHT_SERIES,
                "arrived_kg": sum(
                    r["shipwt_kg"] for r in freight if r["year"] == 2019 and r["month"] == 1
                ),
            },
        },
    }


def initialization_snapshot_digest(
    employment: list[dict[str, Any]], freight: list[dict[str, Any]]
) -> dict[str, str]:
    """Bind each engine profile only to its own initial observations and definitions.

    Whole source-file and target-fixture hashes belong to evaluator lineage.
    Another profile's initialization is also excluded: January 2019 freight is
    a future observation for the employment experiment starting in 2010.
    """
    specs = starting_specs(employment, freight, {"employment": "", "freight": ""})
    identities = {
        "employment": {
            "product": "LEHD_QWI",
            "release": "R2026Q3",
            "definition": "2010Q1 beginning employment; ownership 5; status 1; five disjoint county/NAICS cohorts",
            "query": EMPLOYMENT_SQL.replace(
                "t.year BETWEEN 2009 AND 2019", "t.year = 2010 AND t.quarter = 1"
            ),
            "cohorts": COHORTS,
            "snapshot": specs["employment"]["starting_snapshot"],
        },
        "freight": {
            "product": "BTS_TRANSBORDER",
            "release": "January2019TransBorderRawData; retrieved 2026-09-05",
            "definition": "2019-01 sum shipwt_kg across container/domestic_foreign partitions; port3801; country1220; mode5; trade2; HS72",
            "query": FREIGHT_SQL.replace(
                "t.year BETWEEN 2019 AND 2024", "t.year = 2019 AND t.month = 1"
            ),
            "snapshot": specs["freight"]["starting_snapshot"],
        },
    }
    return {
        name: hashlib.sha256(
            canonical_bytes(
                {
                    "schema": "babylon.historical-initialization.v1",
                    "profile": specs[name]["profile"],
                    **identity,
                }
            )
        ).hexdigest()
        for name, identity in identities.items()
    }


def _source_manifest(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text())
    return {
        "manifest_filename": f"{path.parent.name}/{path.name}",
        "manifest_sha256": digest_file(path),
        "retrieved_at": value["retrieved_at"],
        "source_page": value["source_page"],
        "files": sorted(value["files"], key=lambda row: row["filename"]),
    }


def _table(rows: list[dict[str, Any]]) -> Any:
    strings = {
        "county_fips",
        "naics_code",
        "own_code",
        "source_code",
        "port_code",
        "hs2_code",
        "domestic_foreign",
        "container_code",
        "country",
    }
    schema = pa.schema(
        [
            (
                name,
                pa.string()
                if name in strings
                else pa.float64()
                if name == "turnover_stable"
                else pa.int64(),
            )
            for name in rows[0]
        ]
    )
    return pa.Table.from_pylist(rows, schema=schema)


def _wal_contains_pages(database: Path) -> bool:
    try:
        return database.with_name(database.name + "-wal").stat().st_size > 0
    except FileNotFoundError:
        return False


def _database_fingerprint(database: Path, before: os.stat_result) -> dict[str, Any]:
    """Fingerprint the database inside the same read transaction as both queries."""
    if _wal_contains_pages(database):
        raise ValueError(
            "SQLite source has a nonempty WAL; checkpoint the source before reproducible extraction"
        )
    digest = digest_file(database)
    after = database.stat()

    def identity(value: os.stat_result) -> tuple[int, int, int, int]:
        return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)

    if identity(before) != identity(after) or _wal_contains_pages(database):
        raise ValueError("SQLite source changed during extraction or hashing")
    return {"sqlite_source_sha256": digest, "sqlite_source_bytes": after.st_size}


def extract(database: Path, sources: Path, destination: Path) -> dict[str, Any]:
    if pa.__version__ != PYARROW_VERSION:
        raise ValueError(f"reproducible extracts require pyarrow {PYARROW_VERSION}")
    database = database.resolve(strict=True)
    before = database.stat()
    if _wal_contains_pages(database):
        raise ValueError(
            "SQLite source has a nonempty WAL; checkpoint the source before reproducible extraction"
        )
    connection = sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        employment = [dict(row) for row in connection.execute(EMPLOYMENT_SQL)]
        freight = [dict(row) for row in connection.execute(FREIGHT_SQL)]
        fingerprint = _database_fingerprint(database, before)
    finally:
        connection.close()
    validate_rows(employment, freight)
    destination.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "schema": "babylon.historical-observations.v1",
        "pyarrow_version": PYARROW_VERSION,
        "sqlite_source": database.name,
        **fingerprint,
        "database_access": "read-only transaction",
        "source_manifests": [
            _source_manifest(sources / "lehd_qwi/MANIFEST.yaml"),
            _source_manifest(sources / "bts_transborder/MANIFEST.yaml"),
        ],
        "datasets": {},
    }
    details = [
        (
            "employment",
            employment,
            EMPLOYMENT_SQL,
            "jobs (not unique people)",
            "QWI R2026Q3, retrieved 2026-09-05",
        ),
        (
            "freight",
            freight,
            FREIGHT_SQL,
            "kilograms",
            "BTS 2019-2024 monthly releases, retrieved 2026-09-05",
        ),
    ]
    for name, rows, query, units, vintage in details:
        path = destination / f"{name}.parquet"
        table = _table(rows)
        pq.write_table(
            table,
            path,
            compression="zstd",
            version="2.6",
            use_dictionary=False,
            write_statistics=True,
            data_page_version="2.0",
        )
        manifest["datasets"][name] = {
            "filename": path.name,
            "sha256": digest_file(path),
            "row_count": len(rows),
            "schema": str(table.schema),
            "query": query,
            "units": units,
            "vintage": vintage,
            "evidence_class": "Observed",
            "quality": "QWI companion status flags retained; only status 1 is scored"
            if name == "employment"
            else "source domestic_foreign and container_code partitions retained; land exports excluded; monthly sums formed only by evaluator",
        }
    manifest["initialization_snapshot_sha256"] = initialization_snapshot_digest(employment, freight)
    manifest["snapshot_sha256"] = snapshot_digest(manifest)
    (destination / "manifest.json").write_bytes(canonical_bytes(manifest))
    for name, spec in starting_specs(
        employment, freight, manifest["initialization_snapshot_sha256"]
    ).items():
        (destination / f"{name}_experiment.json").write_bytes(canonical_bytes(spec))
    return manifest


def load_fixtures(
    directory: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    manifest = json.loads((directory / "manifest.json").read_text())
    if snapshot_digest(manifest) != manifest["snapshot_sha256"]:
        raise ValueError("historical manifest identity mismatch")
    tables = []
    for name in ("employment", "freight"):
        dataset = manifest["datasets"][name]
        path = directory / dataset["filename"]
        if digest_file(path) != dataset["sha256"]:
            raise ValueError(f"{name} Parquet checksum mismatch")
        table = pq.read_table(path)
        if table.num_rows != dataset["row_count"] or str(table.schema) != dataset["schema"]:
            raise ValueError(f"{name} Parquet schema or row count mismatch")
        tables.append(table.to_pylist())
    validate_rows(tables[0], tables[1])
    if (
        initialization_snapshot_digest(tables[0], tables[1])
        != manifest["initialization_snapshot_sha256"]
    ):
        raise ValueError("initialization-only snapshot identity mismatch")
    return manifest, tables[0], tables[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_FIXTURES)
    args = parser.parse_args()
    result = extract(args.database, args.sources, args.output)
    print(
        json.dumps(
            {
                "snapshot_sha256": result["snapshot_sha256"],
                "rows": {k: v["row_count"] for k, v in result["datasets"].items()},
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
