"""Local Parquet archival lifecycle for simulation sessions.

Spec: 088-storage-partitioning-archival (S2b, FR-010..FR-014), completing
spec-037 Phase 8 (T045/T047/T048) under the 2026-07-03 owner ruling:
archives are **local only** — Parquet (zstd) on disk, DuckDB for reads,
no cloud code paths (``upload_to_r2`` is retired, FR-013).

Lifecycle::

    paths = export_session_to_parquet(pool, session_id, archive_dir)
    purge_session(pool, session_id, manifest_path=archive_dir / "archive_manifest.json")
    rows = query_archived_session(archive_dir, "SELECT ... FROM dynamic_hex_state")

``purge_session`` refuses to delete anything unless the supplied manifest's
row counts match the live database (``ArchiveVerificationError``), then
drops the session's partitions (instant, zero dead tuples — see
:mod:`babylon.persistence.partitioning`) and deletes session rows from the
non-partitioned leftovers (``contradiction_field``, ``simulation_event``,
the per-session ``immutable_reference_*`` copies, DEFAULT-partition strays).

The reference copies are purged but not exported: they are reproducible
from the pinned SQLite (the run manifest records ``sqlite_sha256`` +
``defines_hash``), per the verifiable+replayable trackability ruling.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from babylon.persistence.partitioning import (
    PARTITIONED_TABLES,
    drop_session_partitions,
)

_LOG = logging.getLogger(__name__)

ARCHIVE_SCHEMA_VERSION = "1.0"

#: Session-keyed tables exported to Parquet (partitioned families plus the
#: non-partitioned session-keyed extras written by other subsystems).
EXPORT_TABLES: tuple[str, ...] = (
    *PARTITIONED_TABLES,
    "contradiction_field",
    "simulation_event",
)

_EXPORT_BATCH_ROWS = 50_000


class ArchiveVerificationError(RuntimeError):
    """Raised when an archive manifest does not match the live database."""


def _arrow_type(pg_type: str) -> Any:
    """Map a Postgres ``data_type`` to an explicit Arrow type.

    An explicit schema prevents per-batch type drift (e.g. an all-NULL TEXT
    column inferring ``null`` in one batch and ``string`` in another).
    """
    import pyarrow as pa  # type: ignore[import-untyped, import-not-found, unused-ignore]

    mapping: dict[str, Any] = {
        "uuid": pa.string(),
        "text": pa.string(),
        "character varying": pa.string(),
        "character": pa.string(),
        "integer": pa.int64(),
        "bigint": pa.int64(),
        "smallint": pa.int32(),
        "double precision": pa.float64(),
        "real": pa.float64(),
        "numeric": pa.float64(),
        "boolean": pa.bool_(),
        "timestamp with time zone": pa.timestamp("us", tz="UTC"),
        "timestamp without time zone": pa.timestamp("us"),
        "jsonb": pa.string(),
        "json": pa.string(),
    }
    return mapping.get(pg_type, pa.string())


def _table_schema(conn: Any, table: str) -> Any:
    """Build the explicit Arrow schema for ``table`` from the catalog."""
    import pyarrow as pa

    rows = conn.execute(
        """
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
        """,
        (table,),
    ).fetchall()
    return pa.schema([(str(name), _arrow_type(str(dtype))) for name, dtype in rows])


def _normalize_cell(value: Any) -> Any:
    """Coerce psycopg values Arrow cannot ingest directly."""
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict | list):
        return json.dumps(value, sort_keys=True)
    return value


def _export_table(conn: Any, table: str, session_id: UUID, out_path: Path, schema: Any) -> int:
    """Stream one table's session rows into a zstd Parquet file.

    Returns the number of rows written (0 ⇒ no file is created).
    """
    import pyarrow as pa
    import pyarrow.parquet as pq  # type: ignore[import-untyped, import-not-found, unused-ignore]

    columns = schema.names
    total = 0
    writer: Any = None
    try:
        # Server-side (named) cursors require an explicit transaction —
        # pooled connections may arrive in autocommit mode (e.g. after
        # the runner's _apply_migrations pass).
        with conn.transaction(), conn.cursor(name=f"archive_{table}") as cur:
            cur.itersize = _EXPORT_BATCH_ROWS
            cur.execute(
                f"SELECT {', '.join(columns)} FROM {table} WHERE session_id = %s",  # noqa: S608
                (str(session_id),),
            )
            while True:
                rows = cur.fetchmany(_EXPORT_BATCH_ROWS)
                if not rows:
                    break
                arrays = [
                    pa.array([_normalize_cell(r[i]) for r in rows], type=schema.types[i])
                    for i in range(len(columns))
                ]
                batch = pa.record_batch(arrays, schema=schema)
                if writer is None:
                    writer = pq.ParquetWriter(out_path, schema, compression="zstd")
                writer.write_batch(batch)
                total += len(rows)
    finally:
        if writer is not None:
            writer.close()
    return total


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _session_reference_tables(conn: Any) -> list[str]:
    """Discover the session-keyed ``immutable_reference_*`` copies."""
    rows = conn.execute(
        """
        SELECT DISTINCT table_name FROM information_schema.columns
        WHERE table_name LIKE 'immutable_reference_%'
          AND column_name = 'session_id'
        ORDER BY table_name
        """
    ).fetchall()
    return [str(r[0]) for r in rows]


def export_session_to_parquet(
    pool: Any,
    session_id: UUID,
    output_dir: str | Path,
) -> list[str]:
    """Export a session's rows to Parquet (zstd) plus a verification manifest.

    Args:
        pool: psycopg ConnectionPool instance.
        session_id: Session to export.
        output_dir: Directory to write ``<table>.parquet`` files and
            ``archive_manifest.json`` into (created if missing).

    Returns:
        Paths of every file written (Parquet files + manifest).

    Raises:
        ArchiveVerificationError: A written file's row count does not match
            what was exported (readback verification).
    """
    import pyarrow.parquet as pq

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    tables_meta: dict[str, dict[str, Any]] = {}
    reference_meta: dict[str, int] = {}
    paths: list[str] = []

    with pool.connection() as conn:
        for table in EXPORT_TABLES:
            exists = conn.execute("SELECT to_regclass(%s)", (table,)).fetchone()
            if exists is None or exists[0] is None:
                continue
            file_path = out / f"{table}.parquet"
            rows = _export_table(conn, table, session_id, file_path, _table_schema(conn, table))
            if rows == 0:
                tables_meta[table] = {"rows": 0, "file": None, "sha256": None}
                continue
            written = int(pq.read_metadata(file_path).num_rows)
            if written != rows:
                raise ArchiveVerificationError(
                    f"{table}: exported {rows} rows but Parquet holds {written}"
                )
            tables_meta[table] = {
                "rows": rows,
                "file": file_path.name,
                "sha256": _sha256_file(file_path),
            }
            paths.append(str(file_path))

        for table in _session_reference_tables(conn):
            row = conn.execute(
                f"SELECT count(*) FROM {table} WHERE session_id = %s",  # noqa: S608
                (str(session_id),),
            ).fetchone()
            reference_meta[table] = int(row[0]) if row is not None else 0

    manifest = {
        "schema_version": ARCHIVE_SCHEMA_VERSION,
        "session_id": str(session_id),
        "tables": tables_meta,
        # Purged-but-not-exported: reproducible from the pinned SQLite
        # (run manifest records sqlite_sha256 + defines_hash).
        "reference_tables_purge_only": reference_meta,
    }
    manifest_path = out / "archive_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    paths.append(str(manifest_path))
    _LOG.info(
        "Archived session %s: %d tables with rows → %s",
        session_id,
        sum(1 for m in tables_meta.values() if m["rows"]),
        out,
    )
    return paths


def _verify_manifest_against_live(conn: Any, session_id: UUID, manifest: dict[str, Any]) -> None:
    """Every manifest row count must equal the live count (purge gate)."""
    if manifest.get("session_id") != str(session_id):
        raise ArchiveVerificationError(
            f"manifest is for session {manifest.get('session_id')}, not {session_id}"
        )
    for table, meta in manifest.get("tables", {}).items():
        exists = conn.execute("SELECT to_regclass(%s)", (table,)).fetchone()
        if exists is None or exists[0] is None:
            continue
        row = conn.execute(
            f"SELECT count(*) FROM {table} WHERE session_id = %s",  # noqa: S608
            (str(session_id),),
        ).fetchone()
        live = int(row[0]) if row is not None else 0
        if live != int(meta["rows"]):
            raise ArchiveVerificationError(
                f"{table}: manifest has {meta['rows']} rows, live database has {live} "
                "— re-export before purging"
            )


def purge_session(
    pool: Any,
    session_id: UUID,
    *,
    manifest_path: str | Path,
) -> dict[str, int]:
    """Remove a session from Postgres after verifying its archive manifest.

    Args:
        pool: psycopg ConnectionPool instance.
        session_id: Session to purge.
        manifest_path: ``archive_manifest.json`` written by
            :func:`export_session_to_parquet`.

    Returns:
        Mapping of table → rows deleted by the leftover sweep (partition
        drops are reported under ``"_partitions_dropped"`` as a count).

    Raises:
        ArchiveVerificationError: Manifest missing or out of sync with the
            live database — nothing is deleted in that case.
    """
    path = Path(manifest_path)
    if not path.exists():
        raise ArchiveVerificationError(f"archive manifest not found at {path}")
    manifest = json.loads(path.read_text())

    with pool.connection() as conn:
        _verify_manifest_against_live(conn, session_id, manifest)

    dropped = drop_session_partitions(pool=pool, session_id=session_id)

    deleted: dict[str, int] = {"_partitions_dropped": len(dropped)}
    sweep = [
        *PARTITIONED_TABLES,  # DEFAULT-partition strays
        "contradiction_field",
        "simulation_event",
    ]
    with pool.connection() as conn:
        sweep.extend(_session_reference_tables(conn))
        for table in sweep:
            exists = conn.execute("SELECT to_regclass(%s)", (table,)).fetchone()
            if exists is None or exists[0] is None:
                continue
            cur = conn.execute(
                f"DELETE FROM {table} WHERE session_id = %s",  # noqa: S608
                (str(session_id),),
            )
            if cur.rowcount:
                deleted[table] = cur.rowcount
        # Best-effort: mark the game_session row archived where the
        # web-layer table exists (headless sessions have no row).
        game_session = conn.execute("SELECT to_regclass('game_session')").fetchone()
        if game_session is not None and game_session[0] is not None:
            try:
                conn.execute(
                    "UPDATE game_session SET status = 'archived' WHERE id = %s",
                    (str(session_id),),
                )
            except Exception as exc:  # noqa: BLE001 — schema variants differ; purge already succeeded
                _LOG.debug("game_session status update skipped: %s", exc)

    _LOG.info(
        "Purged session %s: %d partitions dropped, leftover rows deleted: %s",
        session_id,
        len(dropped),
        {k: v for k, v in deleted.items() if k != "_partitions_dropped"},
    )
    return deleted


def query_archived_session(
    parquet_path: str | Path,
    query: str,
) -> list[dict[str, Any]]:
    """Run SQL over an archived session directory via DuckDB.

    Args:
        parquet_path: Archive directory (each ``<table>.parquet`` becomes a
            DuckDB view named ``<table>``) or a single Parquet file (view
            named after the file stem).
        query: SQL to execute.

    Returns:
        Result rows as dictionaries keyed by column name.
    """
    import duckdb  # type: ignore[import-untyped, import-not-found, unused-ignore]

    path = Path(parquet_path)
    if not path.exists():
        raise FileNotFoundError(f"archive path does not exist: {path}")
    files = sorted(path.glob("*.parquet")) if path.is_dir() else [path]
    if not files:
        raise FileNotFoundError(f"no Parquet files found under {path}")

    con = duckdb.connect()
    try:
        for file in files:
            # DuckDB rejects prepared parameters in DDL; escape the path
            # literal (single quotes doubled) and the view identifier
            # (double quotes doubled) instead.
            path_literal = str(file).replace("'", "''")
            view_identifier = file.stem.replace('"', '""')
            con.execute(
                f"CREATE VIEW \"{view_identifier}\" AS SELECT * FROM read_parquet('{path_literal}')"  # noqa: S608 — local archive dir only; identifier + literal both escaped
            )
        result = con.execute(query)
        columns = [d[0] for d in result.description]
        return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]
    finally:
        con.close()


def upload_to_r2(
    parquet_paths: list[str],
    bucket: str,
    prefix: str = "",
) -> list[str]:
    """Retired: archives are local-only per the 2026-07-03 owner ruling.

    Spec-088 FR-013 drops spec-037's T046 R2 leg. Offsite copies, if ever
    wanted, are an ops concern (``rclone`` of the archive directory), not
    a code path.

    Raises:
        NotImplementedError: Always — local-only ruling.
    """
    raise NotImplementedError(
        "upload_to_r2 is retired: archives are local-only per the 2026-07-03 "
        f"owner ruling (spec-088 FR-013). bucket={bucket}, prefix={prefix}, "
        f"files={len(parquet_paths)}"
    )


__all__ = [
    "ARCHIVE_SCHEMA_VERSION",
    "EXPORT_TABLES",
    "ArchiveVerificationError",
    "export_session_to_parquet",
    "purge_session",
    "query_archived_session",
    "upload_to_r2",
]
