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

    **Post-spec-067 contract** (commit 3b7568ec): the consumer SUMs all
    rows for a (county_id, time_id) pair — no filter on industry_id or
    ownership_id. Spec-067's data-layer migration ensures only canonical
    leaves (naics_level=6 × own_code ∈ {'1','2','3','5'}) are present, so
    SUM(everything) IS the BLS-publication total.

    The fixture inserts THREE rows whose SUM equals
    ``employment_industry_1`` so the test expectations stay readable.
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
    # Three canonical-leaf rows whose employment SUMs to
    # `employment_industry_1` (post-067 contract: SUM-of-leaves).
    half = employment_industry_1 // 2
    quarter = employment_industry_1 // 4
    eighth = employment_industry_1 - half - quarter  # ensures exact sum
    # (industry_id=2, ownership_id=2): 6-digit NAICS × Private — canonical leaf
    conn.execute(
        "INSERT INTO fact_qcew_annual VALUES (?, ?, ?, ?, ?, ?)",
        (1, 2, 2, 1, half, 0),
    )
    # (industry_id=3, ownership_id=2): different 6-digit NAICS × Private — leaf
    conn.execute(
        "INSERT INTO fact_qcew_annual VALUES (?, ?, ?, ?, ?, ?)",
        (1, 3, 2, 1, quarter, 0),
    )
    # (industry_id=2, ownership_id=3): same NAICS × Federal — leaf
    conn.execute(
        "INSERT INTO fact_qcew_annual VALUES (?, ?, ?, ?, ?, ?)",
        (1, 2, 3, 1, eighth, 0),
    )
    conn.commit()
    conn.close()
    return tmp


def test_returns_qcew_employment_as_annual_average() -> None:
    """T055 (amended post-spec-067): employment_proxy = SUM(employment) over
    all canonical-leaf rows for the (county, year).

    The QCEW `employment` column IS the BLS annual-average. No further
    division is applied (spec proposed /12 was discovered during
    implementation to be an incorrect re-division of an already-averaged
    value — see county_aggregation.py docstring).

    Given a fixture whose 3 canonical-leaf rows sum to 1,200,000 for
    Wayne County 2010, the hydrator output should be 1,200,000 as-is.

    **Pre-spec-067 history**: this test used to assert the consumer
    FILTERED by `industry_id=1 AND ownership_id=1` (the BLS rollup
    row). Spec-067 removed that filter at the data layer (commit
    c4e2671c migrates the live reference DB) AND at the consumer
    layer (commit 3b7568ec rewrites the query to SUM the leaves).
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
        f"expected raw annual avg 1,200,000 (SUM-of-leaves), got {result}"
    )
    assert result != pytest.approx(legacy_div_52, rel=1e-3), (
        f"result {result} still matches the legacy /52"
    )
    assert result != pytest.approx(spec_proposed_div_12, rel=1e-3), (
        f"result {result} matches the spec-proposed /12 (which was also wrong)"
    )


def test_qcew_employment_query_filters_industry_id_and_ownership() -> None:
    """T055 (amended post-spec-067) — renamed semantics: the consumer SUMs
    ALL canonical-leaf rows for a (county, year) without filtering.

    The fixture inserts 3 distinct canonical-leaf rows (different NAICS
    6-digit × different ownership) whose `employment` values sum to
    1,200,000. Post-067, all of them are valid leaves; the consumer
    aggregates them.

    **Pre-spec-067 history**: this test was named for the now-removed
    `WHERE industry_id = 1 AND ownership_id = 1` filter. The function
    name is retained for git-history continuity but the assertion
    body now validates the post-067 SUM-of-leaves contract.
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
        f"result {result} != sum of the 3 canonical-leaf rows (1,200,000); "
        f"the consumer may be erroneously filtering rows"
    )
