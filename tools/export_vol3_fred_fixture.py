#!/usr/bin/env python3
"""One-off export: Volume III FRED series -> a committed, deterministic fixture.

D4 (docs/superpowers/specs/2026-07-18-vol3-money-scissors-design.md): gives
tools/regression_test.py's qa:regression gate real Vol III money data WITHOUT
touching the reference DB / babylon-data drive (standing owner ruling — CI/
tests never touch the drive). This script is the one-off, DB-reading half of
that split; tools/regression_test.py is the hermetic, DB-free half that only
ever reads the committed JSON this script produces — the two must never be
merged back into one module.

Run once (and re-run only when the reference DB's fred_series/fred_national
tables are refreshed):

    poetry run python tools/export_vol3_fred_fixture.py

Prerequisite: the worktree's data/ symlink farm must resolve
(``mise run data:doctor``) — this script opens the reference SQLite DB via
babylon.reference.database.get_normalized_session_factory().
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from babylon.domain.economics.factory import load_fred_series_from_db
from babylon.reference.database import get_normalized_session_factory

FIXTURE_PATH: Path = Path(__file__).parent.parent / "tests" / "fixtures" / "vol3_fred_series.json"


def main() -> int:
    """Query the reference DB and write the committed Vol III FRED fixture.

    :returns: 0 on success, 1 if the reference DB returned zero FRED rows
        (loud failure per Constitution III.11 — never write an empty fixture).
    """
    session_factory = get_normalized_session_factory()
    series = load_fred_series_from_db(session_factory)
    if not series:
        print(
            "export_vol3_fred_fixture: reference DB returned zero Vol III FRED rows",
            file=sys.stderr,
        )
        return 1

    payload = {
        series_id: {str(year): value for year, value in sorted(years.items())}
        for series_id, years in sorted(series.items())
    }
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"export_vol3_fred_fixture: wrote {len(payload)} series to {FIXTURE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
