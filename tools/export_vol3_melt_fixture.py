#!/usr/bin/env python3
"""One-off export: national MELT inputs -> a committed, deterministic fixture.

Sibling of ``tools/export_vol3_fred_fixture.py`` (same D4 split, same rules):
this is the one-off, DB-reading half; ``tools/regression_test.py`` is the
hermetic, DB-free half that only ever reads the committed JSON produced here.
The two must never be merged back into one module.

Why a second fixture at all: ``create_financial_services`` supplies every Vol III
calculator EXCEPT ``melt_calculator``, and ``TickDynamicsSystem`` returns early on
``services.melt_calculator is None`` before Step 2 — so without this fixture the
whole annual economics pipeline is skipped under ``qa:regression`` and the gate is
blind to the economics estate.

``DefaultMELTCalculator`` consumes exactly two national annual scalars, so that is
all this exports: BEA GDP (current dollars) and QCEW national employment (persons),
read through the SAME adapters the live wiring uses
(``babylon.domain.economics.melt.adapters``) so the fixture is faithful by
construction rather than by a re-implemented query.

Honest absence (Constitution III.11): a year whose source returns ``None`` is
OMITTED, never written as a zero. The fixture-backed sources in
``tools/regression_test.py`` return ``None`` for a missing year, reproducing the
live adapters exactly. As of the current reference DB that means GDP 2010-2023
(``fact_bea_national_industry`` has no ``line_number=1`` row, so ``get_gdp`` takes
its county-sum fallback, which has no 2024) and employment 2010-2024.

Run once (and re-run only when the reference DB's BEA/QCEW tables are refreshed):

    uv run python tools/export_vol3_melt_fixture.py

Prerequisite: the worktree's data/ symlink farm must resolve
(``mise run data:doctor``) — this script opens the reference SQLite DB via
babylon.reference.database.get_normalized_session_factory().
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from babylon.domain.economics.melt.adapters import (
    SQLiteBEANationalGDPSource,
    SQLiteQCEWNationalEmploymentSource,
)
from babylon.domain.economics.melt.melt_calculator import MAX_YEAR, MIN_YEAR
from babylon.reference.database import get_normalized_session_factory

FIXTURE_PATH: Path = Path(__file__).parent.parent / "tests" / "fixtures" / "vol3_melt_national.json"


def main() -> int:
    """Query the reference DB and write the committed national MELT fixture.

    The year loop is bounded by ``DefaultMELTCalculator``'s own
    ``MIN_YEAR``/``MAX_YEAR`` constants (imported, not duplicated) so the
    fixture window can never drift from the calculator's guard.

    :returns: 0 on success, 1 if either source yielded zero years (loud
        failure per Constitution III.11 — never write a half-empty fixture).
    """
    session_factory = get_normalized_session_factory()
    bea = SQLiteBEANationalGDPSource(session_factory)
    qcew = SQLiteQCEWNationalEmploymentSource(session_factory)

    gdp: dict[str, float] = {}
    employment: dict[str, int] = {}
    for year in range(MIN_YEAR, MAX_YEAR + 1):
        gdp_value = bea.get_gdp(year)
        if gdp_value is not None:
            gdp[str(year)] = float(gdp_value)
        employment_value = qcew.get_national_employment(year)
        if employment_value is not None:
            employment[str(year)] = int(employment_value)

    if not gdp or not employment:
        print(
            "export_vol3_melt_fixture: reference DB yielded "
            f"{len(gdp)} GDP year(s) and {len(employment)} employment year(s) "
            f"over [{MIN_YEAR}, {MAX_YEAR}] — refusing to write a fixture that "
            "cannot resolve a single MELT",
            file=sys.stderr,
        )
        return 1

    payload = {
        "gdp": dict(sorted(gdp.items())),
        "employment": dict(sorted(employment.items())),
    }
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(
        f"export_vol3_melt_fixture: wrote {len(gdp)} GDP year(s) + "
        f"{len(employment)} employment year(s) to {FIXTURE_PATH}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
