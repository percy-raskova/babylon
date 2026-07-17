"""One-shot execution of the ADR075 approved reference-DB amputations.

Owner ruling 1 (2026-07-16, ``ai/decisions/ADR075_data_constitution.yaml``
``rulings_resolved``) approved 16 of the 23 census AMPUTATE proposals. This
tool drops 15 of them — 14 dead tables plus ``view_labor_type``, which dies
with its A5 base table ``fact_census_occupation``. The two exceptions:

- A1 ``fact_qcew_annual__pre_086`` rides the dedicated spec-067 CLI
  (``tools/normalize_qcew_rollups.py --drop-backup``) so the staged-swap
  mechanism writes its own audit trail.
- A21 ``dim_education_level`` is DEFERRED: it is a primary-key FK parent of
  ``fact_census_education`` (disposition ``investigate``) — dropping the dim
  would orphan a living table. It falls when that table's fate is ruled.

Usage::

    poetry run python tools/amputate_reference_tables.py            # dry run
    poetry run python tools/amputate_reference_tables.py --execute
    poetry run python tools/amputate_reference_tables.py --execute --vacuum

Safety model (Constitution III.11, Loud Failure): every approved object must
exist before anything is dropped; any surviving view that still reads a
doomed table aborts the run; a per-object row-count report lands in
``reports/`` on execution. Dry run is the default and mutates nothing.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

#: The owner-approved drop list — name, kind. Views precede tables so a view
#: is never left dangling mid-run. Pinned byte-for-byte by
#: ``tests/unit/tools/test_amputate_reference_tables.py``.
APPROVED_DROPS: tuple[tuple[str, str], ...] = (
    ("view_labor_type", "view"),
    ("fact_atus_reproductive_labor", "table"),
    ("fact_bls_productivity", "table"),
    ("fact_census_commute", "table"),
    ("fact_census_gini", "table"),
    ("fact_census_occupation", "table"),
    ("fact_employment_industry_annual", "table"),
    ("fact_fred_industry_unemployment", "table"),
    ("fact_fred_state_unemployment", "table"),
    ("fact_hickel_drain", "table"),
    ("fact_qcew_metro_annual", "table"),
    ("fact_qcew_state_annual", "table"),
    ("dim_atus_activity_category", "table"),
    ("dim_commute_mode", "table"),
    ("dim_sector", "table"),
)

#: Default DB location; the env override mirrors
#: ``babylon.sentinels.coverage.db_probe._database_path`` (same contract,
#: kept standalone so this one-shot tool needs no package import).
_DEFAULT_DB = Path("data/sqlite/marxist-data-3NF.sqlite")
_ENV_OVERRIDE = "BABYLON_NORMALIZED_DB_PATH"


class AmputationError(Exception):
    """A pre-drop safety check failed; the database was not modified."""


def verify_all_present(conn: sqlite3.Connection) -> list[str]:
    """Return the approved objects missing from the database.

    :param conn: Open connection to the reference DB.
    :returns: Sorted names absent from ``sqlite_master`` (empty when all 15
        exist — the only state in which execution may proceed).
    """
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')").fetchall()
    present = {row[0] for row in rows}
    return sorted(name for name, _ in APPROVED_DROPS if name not in present)


def find_stray_readers(conn: sqlite3.Connection) -> list[str]:
    """Return surviving views whose SQL still references a doomed object.

    A surviving reader means the triage missed a consumer; dropping its base
    would leave a broken view behind, so execution must abort.

    :param conn: Open connection to the reference DB.
    :returns: Sorted names of non-doomed views referencing any doomed name.
    """
    doomed = {name for name, _ in APPROVED_DROPS}
    rows = conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type = 'view' AND sql IS NOT NULL"
    ).fetchall()
    strays = [
        name for name, sql in rows if name not in doomed and any(target in sql for target in doomed)
    ]
    return sorted(strays)


def _row_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Count rows for each approved table (views excluded)."""
    counts: dict[str, int] = {}
    for name, kind in APPROVED_DROPS:
        if kind != "table":
            continue
        cursor = conn.execute(f'SELECT COUNT(*) FROM "{name}"')  # noqa: S608 — fixed approved list
        counts[name] = int(cursor.fetchone()[0])
    return counts


def _write_report(report_dir: Path, counts: dict[str, int], integrity: str) -> Path:
    """Write the amputation audit report and return its path."""
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = report_dir / f"amputation_{stamp}.md"
    lines = [
        "# Reference-DB amputation report (ADR075 ruling 1)",
        "",
        f"Executed: {datetime.now().isoformat(timespec='seconds')}",
        f"Integrity (`PRAGMA quick_check`): {integrity}",
        "",
        "| object | kind | rows before drop |",
        "| --- | --- | --- |",
    ]
    for name, kind in APPROVED_DROPS:
        rows = f"rows_before={counts[name]}" if name in counts else "view"
        lines.append(f"| {name} | {kind} | {rows} |")
    path.write_text("\n".join(lines) + "\n")
    return path


def _execute_drops(conn: sqlite3.Connection) -> None:
    """Drop every approved object — views first, then tables."""
    for name, kind in APPROVED_DROPS:
        statement = f'DROP {"VIEW" if kind == "view" else "TABLE"} "{name}"'
        conn.execute(statement)
    conn.commit()


def main(argv: list[str] | None = None) -> int:
    """Run the amputation (dry run unless ``--execute``).

    :param argv: CLI arguments (defaults to ``sys.argv[1:]``).
    :returns: ``0`` on success.
    :raises AmputationError: When a safety check fails; nothing is dropped.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        type=Path,
        default=Path(os.environ.get(_ENV_OVERRIDE, str(_DEFAULT_DB))),
        help="Path to the reference DB (default honors BABYLON_NORMALIZED_DB_PATH).",
    )
    parser.add_argument("--report-dir", type=Path, default=Path("reports"))
    parser.add_argument("--execute", action="store_true", help="Actually drop (default: dry run).")
    parser.add_argument(
        "--vacuum", action="store_true", help="VACUUM after dropping (execute only)."
    )
    args = parser.parse_args(argv)

    if not args.db.exists():
        msg = f"database not found: {args.db}"
        raise AmputationError(msg)

    conn = sqlite3.connect(args.db)
    try:
        missing = verify_all_present(conn)
        if missing:
            msg = f"approved objects missing from DB (already dropped?): {missing}"
            raise AmputationError(msg)
        strays = find_stray_readers(conn)
        if strays:
            msg = f"surviving views still read doomed tables: {strays}"
            raise AmputationError(msg)
        counts = _row_counts(conn)
        for name, kind in APPROVED_DROPS:
            detail = f"rows={counts[name]}" if name in counts else "view"
            print(f"[amputate] {'DROP' if args.execute else 'would drop'} {kind} {name} ({detail})")
        if not args.execute:
            print("[amputate] dry run — nothing dropped (pass --execute to proceed)")
            return 0
        _execute_drops(conn)
        integrity = str(conn.execute("PRAGMA quick_check").fetchone()[0])
        if integrity != "ok":
            msg = f"post-drop quick_check failed: {integrity}"
            raise AmputationError(msg)
        report = _write_report(args.report_dir, counts, integrity)
        print(f"[amputate] dropped {len(APPROVED_DROPS)} objects; report at {report}")
        if args.vacuum:
            print("[amputate] VACUUM (this can take minutes on the full DB) ...")
            conn.execute("VACUUM")
            print("[amputate] VACUUM complete")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AmputationError as error:
        print(f"[amputate] ABORT: {error}", file=sys.stderr)
        sys.exit(2)
