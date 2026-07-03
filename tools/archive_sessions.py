"""Archive finished simulation sessions to local Parquet and purge Postgres.

Spec: 088-storage-partitioning-archival (S2b, FR-014) — the operator CLI
over :mod:`babylon.persistence.archival` (export → verify → purge) and the
completion of spec-037 T049 under the local-only ruling.

Usage::

    # Inventory: every session currently holding rows, with row counts
    python tools/archive_sessions.py list

    # Archive one session (export + verify + purge)
    python tools/archive_sessions.py archive --session <uuid>

    # Archive everything except the given sessions; keep rows (no purge)
    python tools/archive_sessions.py archive --all --keep <uuid> --no-purge

Archives land under ``$BABYLON_ARCHIVE_ROOT`` (default
``/media/user/data/babylon-archives``), one directory per session id.
Query later via ``babylon.persistence.archival.query_archived_session``.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from uuid import UUID

from babylon.persistence.archival import (
    export_session_to_parquet,
    purge_session,
)

DEFAULT_ARCHIVE_ROOT = "/media/user/data/babylon-archives"


def _archive_root() -> Path:
    return Path(os.environ.get("BABYLON_ARCHIVE_ROOT", DEFAULT_ARCHIVE_ROOT))


def _open_pool() -> object:
    """Open a pool from the same env DSNs the headless runner uses."""
    from psycopg_pool import ConnectionPool

    dsn = os.environ.get("BABYLON_PG_DSN") or os.environ.get("BABYLON_TEST_PG_DSN")
    if not dsn:
        print("ERROR: set BABYLON_PG_DSN or BABYLON_TEST_PG_DSN", file=sys.stderr)
        raise SystemExit(4)
    return ConnectionPool(dsn, min_size=1, max_size=2, open=True)


def discover_sessions(pool: object) -> list[UUID]:
    """Sessions holding rows: partition names + DEFAULT-partition strays."""
    sessions: set[UUID] = set()
    with pool.connection() as conn:  # type: ignore[attr-defined]
        rows = conn.execute(
            "SELECT relname FROM pg_class WHERE relname LIKE 'dynamic_hex_state_p_%'"
        ).fetchall()
        for (relname,) in rows:
            suffix = str(relname).rsplit("_p_", 1)[-1]
            if len(suffix) == 32:
                sessions.add(UUID(suffix))
        default_exists = conn.execute("SELECT to_regclass('dynamic_hex_state_default')").fetchone()
        if default_exists is not None and default_exists[0] is not None:
            strays = conn.execute(
                "SELECT DISTINCT session_id FROM dynamic_hex_state_default"
            ).fetchall()
            sessions.update(UUID(str(s)) for (s,) in strays)
    return sorted(sessions, key=str)


def _session_row_count(pool: object, session_id: UUID) -> int:
    with pool.connection() as conn:  # type: ignore[attr-defined]
        row = conn.execute(
            "SELECT count(*) FROM dynamic_hex_state WHERE session_id = %s",
            (str(session_id),),
        ).fetchone()
    return int(row[0]) if row is not None else 0


def _list_command(args: argparse.Namespace) -> int:
    del args
    pool = _open_pool()
    try:
        sessions = discover_sessions(pool)
        if not sessions:
            print("No sessions with rows in the database.")
            return 0
        print(f"{'session_id':<38} hex_rows")
        for session in sessions:
            print(f"{session!s:<38} {_session_row_count(pool, session)}")
    finally:
        pool.close()  # type: ignore[attr-defined]
    return 0


def _archive_one(pool: object, session_id: UUID, *, dest_root: Path, purge: bool) -> None:
    dest = dest_root / str(session_id)
    paths = export_session_to_parquet(pool, session_id, dest)
    print(f"  exported {len(paths) - 1} files → {dest}")
    if purge:
        deleted = purge_session(pool, session_id, manifest_path=dest / "archive_manifest.json")
        print(
            f"  purged: {deleted.pop('_partitions_dropped', 0)} partitions dropped, "
            f"leftovers {deleted or '{}'}"
        )


def _archive_command(args: argparse.Namespace) -> int:
    pool = _open_pool()
    try:
        if args.session is not None:
            targets = [args.session]
        else:
            keep = set(args.keep or [])
            targets = [s for s in discover_sessions(pool) if s not in keep]
        if not targets:
            print("Nothing to archive.")
            return 0
        dest_root = args.dest if args.dest is not None else _archive_root()
        for session in targets:
            print(f"session {session}:")
            _archive_one(pool, session, dest_root=dest_root, purge=not args.no_purge)
    finally:
        pool.close()  # type: ignore[attr-defined]
    return 0


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Archive simulation sessions to local Parquet (spec-088 S2b)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    lst = sub.add_parser("list", help="List sessions currently holding rows")
    lst.set_defaults(func=_list_command)

    arc = sub.add_parser("archive", help="Export (+purge) sessions to the archive root")
    group = arc.add_mutually_exclusive_group(required=True)
    group.add_argument("--session", type=UUID, help="Archive one session")
    group.add_argument("--all", action="store_true", help="Archive every discovered session")
    arc.add_argument("--keep", type=UUID, action="append", help="With --all: session to skip")
    arc.add_argument("--dest", type=Path, default=None, help="Override archive root")
    arc.add_argument("--no-purge", action="store_true", help="Export only; keep rows in Postgres")
    arc.set_defaults(func=_archive_command)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
