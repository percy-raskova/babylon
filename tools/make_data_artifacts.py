"""Per-table hashed data artifacts — the ADR076 generator (rulings R1-R5).

Converts artifact-disposition reference tables into deterministic,
hash-pinned files and maintains their successor registry,
``data-artifacts.yaml`` (the lineage home once the DB copy is dropped —
the catalog DB-probe reds phantom rows, so catalog->manifest is an atomic
handoff, ADR076 decision 4).

Two artifact tiers (decision 1): in-repo CSV under
``src/babylon/data/reference/`` for tiny tables (plain-text diffs, riding the
.gitattributes LFS exemption), release-shipped parquet under
``dist/data-artifacts/`` for large ones (uploaded to the ci-data release
channel, sha256-pinned here).

Determinism discipline (decision 3): rows sorted by the table's primary key,
an EXPLICIT arrow schema mapped from the sqlite declared types (never
inferred from values), a single row group per parquet file, pinned
codec+level, pyarrow pinned by poetry.lock. Byte-stability is proven by the
double-generation test in ``tests/unit/reference/test_data_artifacts.py``,
never asserted.

Usage::

    poetry run python tools/make_data_artifacts.py            # generate + rewrite manifest
    poetry run python tools/make_data_artifacts.py --check    # verify hashes vs manifest
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

_DEFAULT_DB = Path("data/sqlite/marxist-data-3NF.sqlite")
_ENV_OVERRIDE = "BABYLON_NORMALIZED_DB_PATH"
MANIFEST_PATH = Path("data-artifacts.yaml")
PARQUET_HOME = Path("dist/data-artifacts")
CSV_HOME = Path("src/babylon/data/reference")

#: Pinned parquet write parameters — changing either is a DECLARED
#: regeneration event (rerun the generator, update manifest hashes, say so).
PARQUET_COMPRESSION = "zstd"
PARQUET_COMPRESSION_LEVEL = 9

#: Fixed chunking is the determinism pin: 4Mi rows exceeds every curated
#: table so their existing single-group bytes are unchanged. Full-DB tables
#: (LODES-family facts may run to tens of millions of rows) stream in
#: batches of this size instead of one ``fetchall()``, to avoid OOM.
ROW_GROUP_SIZE = 4_194_304


class ArtifactError(Exception):
    """A generation or verification step failed loudly."""


@dataclass(frozen=True)
class ArtifactSpec:
    """One table's conversion policy (the ADR076 execution map)."""

    name: str
    format: Literal["csv", "parquet"]
    source_table: str
    home: str  # repo-relative output path
    material_relation: str
    mode: Literal["generate", "register"] = "generate"


#: R1-R5 (ADR076 decision 5). ``register`` adopts a pre-existing canonical
#: artifact without regenerating it (R2: the ricci CSV was always canonical).
ARTIFACTS: tuple[ArtifactSpec, ...] = (
    ArtifactSpec(
        name="bridge_county_bea_ea",
        format="csv",
        source_table="bridge_county_bea_ea",
        home="src/babylon/data/reference/bridge_county_bea_ea.csv",
        material_relation=(
            "county -> BEA Economic Area membership map — the regional-market "
            "aggregation geography for cross-border metropolitan gravity."
        ),
    ),
    ArtifactSpec(
        name="dim_bea_economic_area",
        format="csv",
        source_table="dim_bea_economic_area",
        home="src/babylon/data/reference/dim_bea_economic_area.csv",
        material_relation=(
            "the 8 BEA Economic Areas (cross-border metro market regions) the "
            "bridge maps counties onto."
        ),
    ),
    ArtifactSpec(
        name="babylon_ricci_final",
        format="csv",
        source_table="fact_ricci_unequal_exchange",
        home="src/babylon/data/reference/babylon_ricci_final.csv",
        material_relation=(
            "Ricci unequal-exchange transfer series (1995-2007, region x "
            "flow-direction x transfer-type) — periphery->core value-drain "
            "calibration. The CSV was ALWAYS canonical; the DB mirror it "
            "replaces was re-derived from it (R2 demote-only)."
        ),
        mode="register",
    ),
    ArtifactSpec(
        name="fact_energy_annual",
        format="parquet",
        source_table="fact_energy_annual",
        home="dist/data-artifacts/fact_energy_annual.parquet",
        material_relation=(
            "EIA MER annual energy series values 1949-2023 (series x year) — "
            "national energy-metabolism history."
        ),
    ),
    ArtifactSpec(
        name="dim_energy_series",
        format="parquet",
        source_table="dim_energy_series",
        home="dist/data-artifacts/dim_energy_series.parquet",
        material_relation="EIA MER series definitions for fact_energy_annual.",
    ),
    ArtifactSpec(
        name="dim_energy_table",
        format="parquet",
        source_table="dim_energy_table",
        home="dist/data-artifacts/dim_energy_table.parquet",
        material_relation=(
            "EIA MER table taxonomy (with marxian_interpretation labels) for the energy series."
        ),
    ),
    ArtifactSpec(
        name="bridge_lodes_block",
        format="parquet",
        source_table="bridge_lodes_block",
        home="dist/data-artifacts/bridge_lodes_block.parquet",
        material_relation=(
            "census-block -> county/tract/CBSA/ZCTA crosswalk with block "
            "centroids (1,150,562 blocks) — the future hex-level commuter "
            "disaggregation geography."
        ),
    ),
    ArtifactSpec(
        name="staging_arcgis_feature",
        format="parquet",
        source_table="staging_arcgis_feature",
        home="dist/data-artifacts/staging_arcgis_feature.parquet",
        material_relation=(
            "facility-grain ArcGIS provenance rows (5,974 features: source, "
            "object id, county, type, capacity) behind fact_coercive_"
            "infrastructure — kept as raw-provenance artifact."
        ),
    ),
)

#: sqlite declared-type prefix -> arrow type. NUMERIC maps to float64
#: deliberately: sqlite stores these columns as REAL — there is no decimal
#: precision in the source to preserve (documented, not inferred). DATE and
#: DATETIME map to string() for the same reason: this codebase never opens
#: sqlite3 with detect_types=PARSE_DECLTYPES, so both arrive as plain ISO
#: strings (verified against the full reference DB, 2026-07-19) — mapping
#: to a date/timestamp arrow type would be an inferred parse, not a
#: preserved representation.
_DECLTYPE_TO_ARROW: tuple[tuple[str, pa.DataType], ...] = (
    ("INTEGER", pa.int64()),
    ("BIGINT", pa.int64()),
    ("VARCHAR", pa.string()),
    ("TEXT", pa.string()),
    ("DATETIME", pa.string()),
    ("DATE", pa.string()),
    ("NUMERIC", pa.float64()),
    ("FLOAT", pa.float64()),
    ("REAL", pa.float64()),
    ("BOOLEAN", pa.bool_()),
)


def _arrow_type(decltype: str) -> pa.DataType:
    """Map a sqlite declared type to its pinned arrow type — loud otherwise."""
    upper = decltype.upper()
    for prefix, arrow_type in _DECLTYPE_TO_ARROW:
        if upper.startswith(prefix):
            return arrow_type
    msg = f"no pinned arrow mapping for declared type {decltype!r}"
    raise ArtifactError(msg)


def _column_info(conn: sqlite3.Connection, table: str) -> list[tuple[Any, ...]]:
    """Raw ``PRAGMA table_info`` rows for ``table`` — loud if it's absent.

    Typed ``Any`` (not ``object``) to match ``Cursor.fetchall()``'s own stub
    return type — sqlite3 row values are runtime-dynamic regardless of a
    column's declared type, so ``object`` would be a false precision that
    breaks every downstream ``row[i]`` use (str comparisons, sort keys).
    """
    info = conn.execute(f"PRAGMA table_info({table})").fetchall()
    if not info:
        msg = f"source table missing from DB: {table}"
        raise ArtifactError(msg)
    return info


def _table_layout(conn: sqlite3.Connection, table: str) -> tuple[list[str], list[str], pa.Schema]:
    """Return (columns, primary-key columns, explicit arrow schema)."""
    info = _column_info(conn, table)
    columns = [row[1] for row in info]
    pk = [row[1] for row in sorted((r for r in info if r[5]), key=lambda r: r[5])]
    if not pk:
        msg = f"{table} has no primary key — cannot sort deterministically"
        raise ArtifactError(msg)
    schema = pa.schema([(row[1], _arrow_type(row[2])) for row in info])
    return columns, pk, schema


def _table_layout_or_all_columns(
    conn: sqlite3.Connection, table: str
) -> tuple[list[str], list[str], pa.Schema]:
    """``_table_layout``, but a PK-less table sorts by every column instead
    of hard-erroring — identical rows are interchangeable, so this stays
    byte-deterministic without a declared primary key. Used by
    ``export_table_parquet`` for the full-DB sweep, which encounters
    staging/dimension tables the curated generate path never touches."""
    info = _column_info(conn, table)
    columns = [row[1] for row in info]
    pk = [row[1] for row in sorted((r for r in info if r[5]), key=lambda r: r[5])]
    schema = pa.schema([(row[1], _arrow_type(row[2])) for row in info])
    if not pk:
        print(f"{table}: no PK — sorting by all columns")
        pk = columns
    return columns, pk, schema


def _fetch_sorted(
    conn: sqlite3.Connection, table: str, columns: list[str], pk: list[str]
) -> list[tuple[object, ...]]:
    order = ", ".join(f'"{c}"' for c in pk)
    cols = ", ".join(f'"{c}"' for c in columns)
    return conn.execute(f'SELECT {cols} FROM "{table}" ORDER BY {order}').fetchall()  # noqa: S608 — fixed spec list


def _write_csv(path: Path, columns: list[str], rows: list[tuple[object, ...]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(rows)


def _column_array(values: list[object], field: pa.Field) -> pa.Array:
    """Build one arrow column from raw sqlite row values for ``field``.

    Boolean-declared columns arrive from sqlite3 as plain ints (0/1) — sqlite
    has no native boolean storage class and the stdlib driver doesn't coerce
    — so ``pa.array(ints, type=pa.bool_())`` refuses outright (ArrowInvalid).
    Every other pinned type maps as-is; this is a no-op for the curated
    tables (none declare a BOOLEAN column), verified byte-identical.
    """
    if pa.types.is_boolean(field.type):
        # bool(v) collapses any non-0/1 int (e.g. 2) to True — the future
        # round-trip verifier (plan Task 7) must canonicalize BOOLEAN columns
        # the same way rather than comparing raw storage values.
        values = [None if v is None else bool(v) for v in values]
    return pa.array(values, type=field.type)


def governed_db_tables(conn: sqlite3.Connection) -> list[str]:
    """Every table this DB governs — the full sweep surface for the Phase-0
    measurement CLI. Excludes sqlite's own internal bookkeeping tables
    (``sqlite_sequence`` et al.)."""
    rows = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    ).fetchall()
    return [row[0] for row in rows]


def export_table_parquet(conn: sqlite3.Connection, table: str, dest: Path) -> tuple[int, int]:
    """Write ``table`` to ``dest`` as parquet with the pinned codec/row-group
    settings — the ONLY parquet-writing path (both the curated generate
    mode below and ``tools/measure_reference_export.py``'s full-DB sweep
    call this). Returns ``(rows, bytes)``.

    Streams via ``cursor.fetchmany(ROW_GROUP_SIZE)`` batches rather than one
    ``fetchall()`` — full-DB tables (LODES-family facts may run to tens of
    millions of rows) risk an OOM under full materialization. Each batch
    becomes exactly one row group (``ROW_GROUP_SIZE`` exceeds every curated
    table, so their existing single-row-group bytes are unchanged).
    """
    columns, pk, schema = _table_layout_or_all_columns(conn, table)
    order = ", ".join(f'"{c}"' for c in pk)
    cols = ", ".join(f'"{c}"' for c in columns)
    cursor = conn.execute(f'SELECT {cols} FROM "{table}" ORDER BY {order}')  # noqa: S608 — fixed spec list

    dest.parent.mkdir(parents=True, exist_ok=True)
    total_rows = 0
    wrote_any_group = False
    with pq.ParquetWriter(
        dest,
        schema,
        compression=PARQUET_COMPRESSION,
        compression_level=PARQUET_COMPRESSION_LEVEL,
        write_statistics=True,
    ) as writer:
        while True:
            batch = cursor.fetchmany(ROW_GROUP_SIZE)
            if not batch:
                break
            arrays = [
                _column_array([row[i] for row in batch], field) for i, field in enumerate(schema)
            ]
            chunk = pa.Table.from_arrays(arrays, schema=schema)
            writer.write_table(chunk, row_group_size=len(batch))
            total_rows += len(batch)
            wrote_any_group = True
        if not wrote_any_group:
            # An empty table still needs a valid (0-row) parquet file —
            # row_group_size=1 is a floor, not a claim of one actual row.
            empty = pa.Table.from_arrays(
                [_column_array([], field) for field in schema], schema=schema
            )
            writer.write_table(empty, row_group_size=1)
    return total_rows, dest.stat().st_size


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _csv_data_rows(path: Path) -> int:
    with path.open(encoding="utf-8") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def _wrap(text: str, indent: str, width: int = 96) -> list[str]:
    """Greedy word-wrap for the hand-written manifest YAML."""
    lines: list[str] = []
    current = indent
    for word in text.split():
        if len(current) + len(word) + 1 > width and current.strip():
            lines.append(current)
            current = indent
        current = f"{current}{word} " if current.strip() else f"{indent}{word} "
    if current.strip():
        lines.append(current.rstrip())
    return lines


def _write_manifest(entries: list[dict[str, object]]) -> None:
    lines = [
        "# data-artifacts.yaml — successor registry for artifact-ized reference tables",
        "# (ADR076). One entry per artifact: the lineage that used to live in the",
        "# dropped table's data-catalog.yaml row. REGENERATED by",
        "# tools/make_data_artifacts.py — do not edit entries by hand.",
        "---",
        'version: "1.0.0"',
        "artifacts:",
    ]
    for entry in entries:
        lines.append(f"  - name: {entry['name']}")
        lines.append(f"    format: {entry['format']}")
        lines.append(f"    source_table: {entry['source_table']}")
        lines.append("    generator: tools/make_data_artifacts.py")
        lines.append(f"    mode: {entry['mode']}")
        lines.append(f"    rows: {entry['rows']}")
        lines.append(f"    sha256: {entry['sha256']}")
        lines.append(f"    home: {entry['home']}")
        lines.append("    material_relation: >-")
        lines.extend(_wrap(str(entry["material_relation"]), "      "))
    MANIFEST_PATH.write_text("\n".join(lines) + "\n")


def generate(db_path: Path) -> list[dict[str, object]]:
    """Generate every artifact and return the manifest entries."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    entries: list[dict[str, object]] = []
    try:
        for spec in ARTIFACTS:
            out = Path(spec.home)
            if spec.mode == "register":
                if not out.exists():
                    msg = f"register-mode artifact missing: {out}"
                    raise ArtifactError(msg)
                rows = _csv_data_rows(out)
            elif spec.format == "csv":
                columns, pk, _schema = _table_layout(conn, spec.source_table)
                data = _fetch_sorted(conn, spec.source_table, columns, pk)
                _write_csv(out, columns, data)
                rows = len(data)
            else:
                rows, _size = export_table_parquet(conn, spec.source_table, out)
            entries.append(
                {
                    "name": spec.name,
                    "format": spec.format,
                    "source_table": spec.source_table,
                    "mode": spec.mode,
                    "rows": rows,
                    "sha256": _sha256(out),
                    "home": spec.home,
                    "material_relation": spec.material_relation,
                }
            )
            print(f"[artifacts] {spec.name}: {rows} rows -> {out}")
    finally:
        conn.close()
    return entries


def check() -> int:
    """Verify on-disk artifacts against the manifest (in-repo tier always;
    dist-tier only when present locally)."""
    import yaml

    if not MANIFEST_PATH.exists():
        msg = f"manifest missing: {MANIFEST_PATH}"
        raise ArtifactError(msg)
    manifest = yaml.safe_load(MANIFEST_PATH.read_text())
    failures: list[str] = []
    for entry in manifest["artifacts"]:
        path = Path(entry["home"])
        if not path.exists():
            if str(path).startswith("dist/"):
                print(f"[artifacts] {entry['name']}: dist-tier absent locally — skipped")
                continue
            failures.append(f"{entry['name']}: missing file {path}")
            continue
        actual = _sha256(path)
        if actual != entry["sha256"]:
            failures.append(
                f"{entry['name']}: sha256 mismatch (manifest {entry['sha256'][:12]}…, "
                f"actual {actual[:12]}…)"
            )
    for failure in failures:
        print(f"[artifacts] FAIL {failure}", file=sys.stderr)
    print(f"[artifacts] check: {len(manifest['artifacts'])} entries, {len(failures)} failures")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    """Generate artifacts + rewrite the manifest, or verify with ``--check``."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        type=Path,
        default=Path(os.environ.get(_ENV_OVERRIDE, str(_DEFAULT_DB))),
    )
    parser.add_argument("--check", action="store_true", help="verify hashes vs manifest")
    args = parser.parse_args(argv)

    if args.check:
        return check()
    if not args.db.exists():
        msg = f"database not found: {args.db}"
        raise ArtifactError(msg)
    entries = generate(args.db)
    _write_manifest(entries)
    print(f"[artifacts] manifest rewritten: {MANIFEST_PATH} ({len(entries)} entries)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ArtifactError as error:
        print(f"[artifacts] ABORT: {error}", file=sys.stderr)
        sys.exit(2)
