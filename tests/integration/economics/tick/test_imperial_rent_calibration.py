"""Year-resolved Hickel calibration test for SC-004.

Per spec.md SC-004 + research.md §R8.4: for at least one tick year with
both complete BEA + QCEW data and a row in babylon_hickel_final.csv, the
computed national-total imperial rent must be within an order of magnitude
of the annual_drain_usd_billions value for that year.

DEFERRED for Wayne County wiring: this test currently asserts the Hickel
CSV is loadable + the row exists. Full end-to-end OOM assertion lands
when Wayne County baseline is wired (follow-up task).
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

HICKEL_CSV = Path("/media/user/data/babylon-data/babylon_hickel_final.csv")


def _load_hickel_drain_by_year() -> dict[int, dict[str, float]]:
    if not HICKEL_CSV.exists():
        return {}
    result: dict[int, dict[str, float]] = {}
    with HICKEL_CSV.open() as fh:
        for row in csv.DictReader(fh):
            year = int(row["year"])
            scale_type = row["scale_type"].strip()
            result.setdefault(year, {})[scale_type] = float(row["annual_drain_usd_billions"])
    return result


@pytest.mark.integration
@pytest.mark.parametrize("year,scale_type", [(2015, "Intensive")])
def test_oom_against_hickel_csv(year: int, scale_type: str) -> None:
    """For year + scale_type: assert Hickel CSV row exists + value is positive.

    Full OOM ratio (computed_total / hickel_drain in [0.1, 10]) lands when
    Wayne County baseline is wired against real DefaultPeripheryLabor
    CoefficientsSource + DefaultFinalDemandSource + DefaultIndustryToCounty
    Allocator. The structural calibration gate is in place here.
    """
    drain_by_year = _load_hickel_drain_by_year()
    if not drain_by_year:
        pytest.skip(f"Hickel CSV not present at {HICKEL_CSV}")
    assert year in drain_by_year, f"Year {year} not in Hickel CSV"
    assert scale_type in drain_by_year[year], (
        f"scale_type={scale_type!r} not in Hickel CSV for year {year}; "
        f"available: {list(drain_by_year[year].keys())}"
    )

    hickel_drain = drain_by_year[year][scale_type]
    assert hickel_drain > 0
    if year == 2015 and scale_type == "Intensive":
        assert hickel_drain == pytest.approx(9750.0, rel=0.01)


@pytest.mark.integration
def test_hickel_csv_full_year_range() -> None:
    drain_by_year = _load_hickel_drain_by_year()
    if not drain_by_year:
        pytest.skip(f"Hickel CSV not present at {HICKEL_CSV}")
    assert min(drain_by_year.keys()) <= 1960
    assert max(drain_by_year.keys()) >= 2017
