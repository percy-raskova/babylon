"""Unit tests for Bug B — employment_proxy unit fix /52 → /12 (spec-066 US4).

Spec: 066-marx-coherence-fixes (T055).

BLS QCEW reports monthly average employment (a stock, not a flow).
Dividing by 52 weeks treats stock as flow and undercounts by ~4.3x.
The correct division is by 12 months for annual average.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from babylon.persistence.county_aggregation import fetch_employment_proxy_for_county_at_tick

pytestmark = [pytest.mark.unit]


def _build_minimal_sqlite(*, fips: str, year: int, employment_industry_1: int) -> Path:
    """Create a tiny on-disk SQLite snapshot for the function to read.

    fetch_employment_proxy_for_county_at_tick opens its own sqlite3.connect
    on a Path, so we can't pass an in-memory connection.
    """
    tmp = Path(tempfile.mkdtemp()) / "test_emp.sqlite"
    conn = sqlite3.connect(tmp)
    conn.executescript(
        """
        CREATE TABLE dim_county (county_id INTEGER PRIMARY KEY, fips TEXT);
        CREATE TABLE dim_time (time_id INTEGER PRIMARY KEY, year INTEGER);
        CREATE TABLE fact_qcew_annual (
            county_id INTEGER, industry_id INTEGER, ownership_id INTEGER,
            time_id INTEGER, employment INTEGER, total_wages_usd NUMERIC
        );
        """
    )
    conn.execute("INSERT INTO dim_county VALUES (?, ?)", (1, fips))
    conn.execute("INSERT INTO dim_time VALUES (?, ?)", (1, year))
    # Spec-066: industry_id=1 + ownership_id=1 row is the BLS rollup
    conn.execute(
        "INSERT INTO fact_qcew_annual VALUES (?, ?, ?, ?, ?, ?)",
        (1, 1, 1, 1, employment_industry_1, 0),
    )
    # Sibling NAICS (industry_id=2) that must NOT be summed.
    conn.execute(
        "INSERT INTO fact_qcew_annual VALUES (?, ?, ?, ?, ?, ?)",
        (1, 2, 1, 1, 700_000, 0),
    )
    # Sibling ownership_id=5 at industry_id=1 that must NOT be summed.
    conn.execute(
        "INSERT INTO fact_qcew_annual VALUES (?, ?, ?, ?, ?, ?)",
        (1, 1, 5, 1, 900_000, 0),
    )
    conn.commit()
    conn.close()
    return tmp


def test_returns_qcew_employment_as_annual_average() -> None:
    """T055: employment_proxy = SUM(employment WHERE industry_id=1 AND ownership_id=1).

    The QCEW `employment` column IS the BLS annual-average. No further
    division is applied (spec proposed /12 was discovered during
    implementation to be an incorrect re-division of an already-averaged
    value — see county_aggregation.py docstring).

    Given a mocked QCEW employment of 1,200,000 (industry=1, ownership=1)
    for Wayne County, the hydrator output should be 1,200,000 as-is.
    """
    with patch(
        "babylon.persistence.county_aggregation._tick_to_year",
        return_value=2010,
    ):
        sqlite_path = _build_minimal_sqlite(
            fips="26163",
            year=2010,
            employment_industry_1=1_200_000,
        )
        result = fetch_employment_proxy_for_county_at_tick(
            sqlite_path=sqlite_path,
            county_fips="26163",
            tick=0,
            start_year=2010,
        )

    legacy_div_52 = 1_200_000 / 52.0
    spec_proposed_div_12 = 1_200_000 / 12.0
    assert result == pytest.approx(1_200_000.0, rel=1e-9), (
        f"expected raw annual avg 1,200,000, got {result}"
    )
    assert result != pytest.approx(legacy_div_52, rel=1e-3), (
        f"result {result} still matches the legacy /52"
    )
    assert result != pytest.approx(spec_proposed_div_12, rel=1e-3), (
        f"result {result} matches the spec-proposed /12 (which was also wrong)"
    )


def test_qcew_employment_query_filters_industry_id_and_ownership() -> None:
    """T055 (companion): the SUM filters to industry_id=1 AND ownership_id=1.

    The fixture inserts industry_id=1 with ownership_id=1 (the BLS rollup)
    PLUS industry_id=2 with ownership_id=5 (which would over-count if
    either filter were missing).
    """
    with patch(
        "babylon.persistence.county_aggregation._tick_to_year",
        return_value=2010,
    ):
        sqlite_path = _build_minimal_sqlite(
            fips="26163",
            year=2010,
            employment_industry_1=1_200_000,
        )
        result = fetch_employment_proxy_for_county_at_tick(
            sqlite_path=sqlite_path,
            county_fips="26163",
            tick=0,
            start_year=2010,
        )

    assert result == pytest.approx(1_200_000.0, rel=1e-9), (
        f"result {result} differs from the industry=1+ownership=1 row"
    )
    naive_without_filter = (1_200_000 + 700_000) * 1.0  # would include industry_id=2 row
    assert result != pytest.approx(naive_without_filter, rel=1e-3), (
        f"result {result} matches the un-filtered SUM"
    )
