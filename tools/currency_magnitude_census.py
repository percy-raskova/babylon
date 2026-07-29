"""Census of the largest |Currency| values across shipped artifacts.

Program 27 spec §6.1: proves the i64-micro-unit overflow claim and pins the
i128 headroom. Scans (a) every JSON baseline, (b) every dense CSV golden,
(c) the reference DB's numeric columns. Emits max values with provenance.

The reference DB (``data/sqlite/marxist-data-3NF.sqlite``) is a gitignored
build product (ADR098) — absent in fresh clones/worktrees until
``mise run data:build-db`` runs. The sqlite leg is skipped (not a hard
failure) when the file is missing, so this script and its pinned test stay
runnable everywhere; the census report this feeds should be generated in an
environment where the reference DB is present so the sqlite leg is included.
"""

import csv
import json
import math
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BASELINES = REPO / "tests" / "baselines"
REFERENCE_DB = REPO / "data" / "sqlite" / "marxist-data-3NF.sqlite"


def _walk_json(node: object, path: str, out: list[tuple[float, str]]) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            _walk_json(v, f"{path}.{k}", out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _walk_json(v, f"{path}[{i}]", out)
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        # Non-finite leaves (e.g. a dependency_ratio's divide-by-zero
        # Infinity) are data artifacts, not currency magnitudes — exclude
        # them so they can't dominate the top-50 in place of real values.
        value = float(node)
        if math.isfinite(value):
            out.append((abs(value), path))


def _census_sqlite(hits: list[tuple[float, str]]) -> None:
    """Scan the reference DB's numeric columns for max |value|, if present."""
    if not REFERENCE_DB.exists():
        return
    con = sqlite3.connect(f"file:{REFERENCE_DB}?mode=ro", uri=True)
    try:
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        for t in tables:
            cols = [
                r[1]
                for r in con.execute(f"PRAGMA table_info('{t}')")
                if r[2].upper() in ("REAL", "INTEGER", "NUMERIC", "FLOAT")
            ]
            for c in cols:
                row = con.execute(f'SELECT MAX(ABS("{c}")) FROM "{t}"').fetchone()
                if row and row[0] is not None:
                    hits.append((float(row[0]), f"sqlite:{t}.{c}"))
    finally:
        con.close()


def census() -> list[tuple[float, str]]:
    hits: list[tuple[float, str]] = []
    for p in sorted(BASELINES.glob("*.json")):
        try:
            data = json.loads(p.read_text())
        except json.JSONDecodeError:
            # Un-hydrated git-lfs pointer (this worktree/clone hasn't pulled
            # LFS content) — skip rather than crash; note it so a run
            # against a fully-hydrated checkout is understood as authoritative.
            print(f"# skipped (not valid JSON, likely an LFS pointer): {p.name}", file=sys.stderr)
            continue
        _walk_json(data, p.name, hits)
    for p in sorted((BASELINES / "dense").glob("*.csv")):
        with p.open() as f:
            for row_n, row in enumerate(csv.reader(f)):
                for cell in row:
                    try:
                        hits.append((abs(float(cell)), f"{p.name}:{row_n}"))
                    except ValueError:
                        continue
    _census_sqlite(hits)
    return sorted(hits, reverse=True)[:50]


if __name__ == "__main__":
    for value, source in census():
        print(f"{value:.6g}\t{source}")
