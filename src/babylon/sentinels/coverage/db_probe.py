"""The catalog DB probe — reconciles ``data-catalog.yaml`` against the real DB.

The refdata-lane half of the Program 21 registry (the static half lives in
:mod:`babylon.sentinels.coverage.checks`). Opens the reference database
**read-only** and asserts the catalog↔DB bijection plus the emptiness law:

- every ``fact_/dim_/bridge_`` table and ``view_`` view in ``sqlite_master``
  has a catalog row (III.4 traceability — no undeclared data);
- every catalog row names an object the DB actually contains (no phantoms);
- no ``disposition: keep`` object is empty — a KEEP table with zero rows, or a
  KEEP view over an empty base table, is the ``view_surplus_value`` pathology:
  a consumer reading silence (Constitution III.11).

``fill``/``artifact``/``amputate``/``investigate`` rows are *declared debt* —
they are tracked by disposition and deliberately not gated on emptiness, so CI
stays green on known triage while any KEEP object going dark reds loudly.

**Subset awareness:** ci-data subsets carry base tables only (the generator
copies ``type='table'``), so when the probed DB contains *no* views at all the
view rows are reported as an advisory, not a violation.

This module opens sqlite3, so the CLI loads it lazily (like the partition
probe) and it runs only in the refdata lane — never the fast-gate.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

from babylon.sentinels.base import LabelledCheck, SentinelCheckError, run_sensor
from babylon.sentinels.coverage.catalog import CatalogTable, load_catalog_tables

#: Repo root (this file is ``<root>/src/babylon/sentinels/coverage/db_probe.py``).
_REPO_ROOT: Path = Path(__file__).resolve().parents[4]

#: Traceability scope: only these prefixes are governed by the catalog
#: (utility tables like ``ingest_checkpoint``/``staging_arcgis_feature`` are
#: outside it, exactly as the subset generator's find_unknown_tables excludes
#: them from policy review).
_GOVERNED_PREFIXES: tuple[str, ...] = ("fact_", "dim_", "bridge_", "view_")


def _database_path() -> Path:
    """Resolve the reference DB path (env override, then the canonical spot).

    :returns: The path ``BABYLON_NORMALIZED_DB_PATH`` names, or
        ``data/sqlite/marxist-data-3NF.sqlite`` under the repo root.
    """
    override = os.environ.get("BABYLON_NORMALIZED_DB_PATH")
    if override:
        return Path(override)
    return _REPO_ROOT / "data" / "sqlite" / "marxist-data-3NF.sqlite"


def _open_readonly(path: Path) -> sqlite3.Connection:
    """Open the reference DB genuinely read-only (``mode=ro`` URI).

    :param path: Database file.
    :returns: A read-only connection.
    :raises SentinelCheckError: If the file is missing or cannot be opened —
        the probe must never run against no DB and report clean.
    """
    if not path.is_file():
        raise SentinelCheckError(f"reference DB not found at {path} (probe cannot run)")
    try:
        return sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise SentinelCheckError(f"cannot open reference DB {path} read-only: {exc}") from exc


def _db_objects(conn: sqlite3.Connection) -> dict[str, str]:
    """Map every governed ``sqlite_master`` object name to its type.

    :param conn: Open reference-DB connection.
    :returns: ``{name: "table"|"view"}`` for governed-prefix objects.
    """
    rows = conn.execute(
        "SELECT name, type FROM sqlite_master WHERE type IN ('table','view') "
        "AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {name: kind for name, kind in rows if name.startswith(_GOVERNED_PREFIXES)}


def _is_empty(conn: sqlite3.Connection, table: str) -> bool:
    """O(1) emptiness probe (EXISTS, not COUNT — some tables hold 26M rows).

    The identifier cannot be a bound parameter; every ``table`` passed here is
    first verified against ``sqlite_master`` (see the callers), so the quoted
    interpolation cannot inject.
    """
    row = conn.execute(f'SELECT EXISTS(SELECT 1 FROM "{table}" LIMIT 1)').fetchone()  # noqa: S608
    return not bool(row[0])


def check_catalog_db_reconciliation(
    catalog: tuple[CatalogTable, ...] | None = None,
    db_path: Path | None = None,
) -> list[str]:
    """Assert the catalog↔DB bijection and the KEEP-objects-not-empty law.

    :param catalog: Rows to reconcile (defaults to the real catalog;
        injectable so tests can pin the ``view_surplus_value`` pathology as a
        regression contract with a synthetic row).
    :param db_path: Database to probe (defaults to the canonical/env path).
    :returns: Sorted violation strings (empty when catalog and DB agree and no
        KEEP object is dark). Subset-environment view absences are advisory
        and reported by :func:`check_subset_view_absence` instead.
    :raises SentinelCheckError: If the catalog or DB cannot be opened/parsed.
    """
    rows = load_catalog_tables() if catalog is None else catalog
    conn = _open_readonly(db_path if db_path is not None else _database_path())
    try:
        objects = _db_objects(conn)
        subset_env = not any(kind == "view" for kind in objects.values())
        declared = {row.name for row in rows}
        violations = [
            f"DB object {name!r} ({kind}) has no data-catalog.yaml row — undeclared "
            "data violates III.4 traceability"
            for name, kind in objects.items()
            if name not in declared
        ]
        for row in rows:
            if row.name not in objects:
                if row.kind == "view" and subset_env:
                    continue  # subset DBs carry no views — advisory tier's job
                violations.append(
                    f"catalog row {row.name!r} names an object the DB does not "
                    "contain (phantom declaration)"
                )
                continue
            violations.extend(_keep_emptiness_violations(conn, row, objects))
        return sorted(violations)
    finally:
        conn.close()


def _keep_emptiness_violations(
    conn: sqlite3.Connection, row: CatalogTable, objects: dict[str, str]
) -> list[str]:
    """Emptiness law for one KEEP row (empty list for other dispositions)."""
    if row.disposition != "keep":
        return []
    if row.kind == "table":
        if _is_empty(conn, row.name):
            return [
                f"KEEP table {row.name!r} is EMPTY — a declared-healthy object "
                "went dark (III.11 silent degradation)"
            ]
        return []
    return [
        f"KEEP view {row.name!r} reads {base!r} which is EMPTY — the view "
        "silently returns nothing (the view_surplus_value pathology, III.11)"
        for base in row.reads
        if base in objects and _is_empty(conn, base)
    ]


def check_subset_view_absence(
    catalog: tuple[CatalogTable, ...] | None = None,
    db_path: Path | None = None,
) -> list[str]:
    """Advisory: name the catalog views a view-less (subset) DB cannot check.

    :param catalog: Rows to inspect (defaults to the real catalog).
    :param db_path: Database to probe (defaults to the canonical/env path).
    :returns: One advisory string when the DB carries no views (naming the
        count of unchecked view rows); empty against a full DB.
    """
    rows = load_catalog_tables() if catalog is None else catalog
    conn = _open_readonly(db_path if db_path is not None else _database_path())
    try:
        has_views = bool(
            conn.execute("SELECT 1 FROM sqlite_master WHERE type='view' LIMIT 1").fetchone()
        )
    finally:
        conn.close()
    if has_views:
        return []
    view_count = sum(1 for row in rows if row.kind == "view")
    if not view_count:
        return []
    return [
        f"probed DB carries no views (ci-data subset environment) — "
        f"{view_count} catalog view rows unchecked here; the full-DB probe "
        "covers them locally"
    ]


#: Gating checks: a violation reds the refdata lane (exit 1).
_GATING_CHECKS: tuple[LabelledCheck, ...] = (
    ("catalog↔DB reconciliation / KEEP emptiness law", check_catalog_db_reconciliation),
)

#: Advisory: subset environments cannot check view rows (prints, never gates).
_ADVISORY_CHECKS: tuple[LabelledCheck, ...] = (
    ("view rows unchecked in subset DB", check_subset_view_absence),
)


def _summary(advisory_count: int) -> str:
    """Build the clean one-line summary printed when no gating violation occurred.

    :param advisory_count: Number of advisory findings printed above.
    :returns: The summary line naming the reconciled row count.
    """
    summary = (
        f"Data catalog (DB probe): clean — {len(load_catalog_tables())} catalog rows "
        "reconciled against the reference DB (no undeclared objects, no phantom "
        "rows, no dark KEEP objects)."
    )
    if advisory_count:
        summary += f" ({advisory_count} advisory findings above.)"
    return summary


def main(argv: list[str] | None = None) -> int:
    """Run the catalog DB probe and return the process exit code.

    :param argv: CLI args (``--check`` is accepted as the CI-mode alias; the
        behavior is always to gate).
    :returns: 0 clean, 1 gating violations, 2 infrastructure failure.
    """
    parser = argparse.ArgumentParser(
        description="Data catalog — DB reconciliation probe (III.4 / III.11 gate)."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI-mode alias; the tool always gates (exit 1 on violations).",
    )
    parser.parse_args(argv)
    return run_sensor("CATALOG", _GATING_CHECKS, _ADVISORY_CHECKS, _summary)


if __name__ == "__main__":
    sys.exit(main())
