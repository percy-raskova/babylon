"""Unit tests for Bug A — hex_hydrator Marx accounting (spec-066 US1).

Spec: 066-marx-coherence-fixes (T012-T014).

These tests verify the formula change ``s = max(0, GDP/52 - v)`` (NOT
``max(0, GDP/52 - v - c)``), the addition of ``industry_id = 1`` to the
QCEW SUM query, and the emission of a ``_CalibrationAlarm`` when the raw
residual is negative.

Uses an in-memory SQLite database with the minimal schema mirroring
``data/sqlite/marxist-data-3NF.sqlite``.
"""

from __future__ import annotations

import sqlite3

import pytest

from babylon.persistence.hex_hydrator import (
    _CalibrationAlarm,
    _fetch_per_county_data,
)

pytestmark = [pytest.mark.unit]


def _build_minimal_sqlite(
    *,
    fips: str = "26163",
    year: int = 2010,
    total_wages_industry_1: float = 50_000_000_000.0,  # $50B/yr Wayne Cty all-industries
    total_wages_industry_2: float = 30_000_000_000.0,  # $30B/yr Wayne Cty Manufacturing
    bea_gdp_millions: float = 200_000.0,  # $200B Wayne Cty GDP
) -> sqlite3.Connection:
    """In-memory SQLite with the four tables ``_fetch_per_county_data`` reads.

    Inserts TWO QCEW rows (industry_id=1 'All Industries' AND industry_id=2
    'Manufacturing') to verify the spec-066 industry_id=1 filter prevents
    the double-counting bug.
    """
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE dim_county (
            county_id INTEGER PRIMARY KEY,
            fips TEXT NOT NULL
        );
        CREATE TABLE dim_time (
            time_id INTEGER PRIMARY KEY,
            year INTEGER NOT NULL
        );
        CREATE TABLE fact_qcew_annual (
            county_id INTEGER NOT NULL,
            industry_id INTEGER NOT NULL,
            ownership_id INTEGER NOT NULL,
            time_id INTEGER NOT NULL,
            employment INTEGER,
            total_wages_usd NUMERIC(15, 2)
        );
        CREATE TABLE fact_bea_county_gdp (
            county_id INTEGER,
            time_id INTEGER,
            bea_industry_id INTEGER,
            gdp_millions REAL
        );
        CREATE TABLE fact_broadband_coverage (
            county_id INTEGER,
            pct_25_3 REAL,
            pct_100_20 REAL
        );
        CREATE TABLE fact_coercive_infrastructure (
            county_id INTEGER,
            facility_count INTEGER
        );
        """
    )
    conn.execute("INSERT INTO dim_county (county_id, fips) VALUES (?, ?)", (1, fips))
    conn.execute("INSERT INTO dim_time (time_id, year) VALUES (?, ?)", (1, year))
    # Two QCEW rows: industry 1 (All Industries) + industry 2 (Manufacturing).
    # Pre-spec-066, the SUM would double-count by adding both.
    # Spec-066: industry_id=1 + ownership_id=1 = BLS rollup row
    conn.execute(
        "INSERT INTO fact_qcew_annual VALUES (?, ?, ?, ?, ?, ?)",
        (1, 1, 1, 1, 1_200_000, total_wages_industry_1),
    )
    # Sibling industry_id=2 row (manufacturing): would over-count if
    # industry_id=1 filter were missing.
    conn.execute(
        "INSERT INTO fact_qcew_annual VALUES (?, ?, ?, ?, ?, ?)",
        (1, 2, 1, 1, 700_000, total_wages_industry_2),
    )
    # Sibling ownership_id=5 (Private) row at industry_id=1: would
    # over-count if ownership_id=1 filter were missing.
    conn.execute(
        "INSERT INTO fact_qcew_annual VALUES (?, ?, ?, ?, ?, ?)",
        (1, 1, 5, 1, 1_100_000, total_wages_industry_1 * 0.9),
    )
    conn.execute(
        "INSERT INTO fact_bea_county_gdp VALUES (?, ?, ?, ?)",
        (1, 1, 1, bea_gdp_millions),
    )
    conn.commit()
    return conn


def test_s_formula_uses_value_added_identity() -> None:
    """T012 / FR-001: hex_hydrator computes s = max(0, GDP/52 - v), NOT - v - c."""
    conn = _build_minimal_sqlite(
        total_wages_industry_1=50_000_000_000.0,
        bea_gdp_millions=200_000.0,
    )
    rows = _fetch_per_county_data(conn=conn, counties=frozenset({"26163"}), year=2010)
    row = rows["26163"]

    # Expected: v = $50B/52 ≈ $961.5M/wk; GDP/52 ≈ $3.846B/wk.
    expected_v = 50_000_000_000.0 / 52.0
    expected_gdp = 200_000_000_000.0 / 52.0
    # Spec-066 value-added identity: s = max(0, GDP/52 - v) ≈ $2.885B/wk.
    expected_s = max(0.0, expected_gdp - expected_v)
    # Old (buggy) formula: max(0, GDP/52 - v - c) where c = 0.5*GDP/52.
    # Would yield s = max(0, GDP/52 - v - 0.5*GDP/52) = max(0, 0.5*GDP/52 - v)
    # ≈ max(0, $1.923B - $961.5M) ≈ $961.5M/wk (different value).
    old_buggy_s = max(0.0, expected_gdp - expected_v - 0.5 * expected_gdp)

    assert row.v_per_week == pytest.approx(expected_v, rel=1e-9)
    assert row.s_per_week == pytest.approx(expected_s, rel=1e-9)
    assert row.s_per_week != pytest.approx(old_buggy_s, rel=1e-3), (
        f"s_per_week={row.s_per_week} matches the buggy formula; expected {expected_s}"
    )


def test_qcew_query_filters_industry_id_1() -> None:
    """T013 / FR-002: QCEW SUM only counts industry_id=1 rows.

    The fixture inserts two QCEW rows for the same county-year: industry_id=1
    ($50B All Industries) and industry_id=2 ($30B Manufacturing). Without
    the spec-066 filter, the SUM would be $80B (the bug). With the filter,
    SUM is $50B (the BLS publication granularity).
    """
    conn = _build_minimal_sqlite(
        total_wages_industry_1=50_000_000_000.0,
        total_wages_industry_2=30_000_000_000.0,
    )
    rows = _fetch_per_county_data(conn=conn, counties=frozenset({"26163"}), year=2010)
    row = rows["26163"]

    # If the filter were missing, v_per_week would be $80B/52 ≈ $1.538B/wk.
    # With the filter, v_per_week is $50B/52 ≈ $961.5M/wk.
    expected_v_filtered = 50_000_000_000.0 / 52.0
    naive_buggy_v = 80_000_000_000.0 / 52.0

    assert row.v_per_week == pytest.approx(expected_v_filtered, rel=1e-9)
    assert row.v_per_week != pytest.approx(naive_buggy_v, rel=1e-3), (
        f"v_per_week={row.v_per_week} matches the un-filtered SUM "
        f"(${naive_buggy_v:.0f}/wk); industry_id=1 filter is missing"
    )


def test_negative_residual_emits_alarm_audit_row() -> None:
    """T014 / FR-004: when GDP/52 < v, a _CalibrationAlarm is appended."""
    # Construct a commuter-wage boundary: tiny GDP, huge wages (work-county
    # reports wages, residence-county reports GDP).
    conn = _build_minimal_sqlite(
        total_wages_industry_1=100_000_000_000.0,  # $100B/yr wages reported here
        bea_gdp_millions=10_000.0,  # but only $10B GDP — residual is hugely negative
    )

    alarms: list[_CalibrationAlarm] = []
    rows = _fetch_per_county_data(
        conn=conn,
        counties=frozenset({"26163"}),
        year=2010,
        audit_alarms=alarms,
    )

    assert rows["26163"].s_per_week == 0.0, "s must be clamped to 0 when residual<0"
    assert len(alarms) == 1, f"expected exactly one alarm, got {len(alarms)}"
    alarm = alarms[0]
    assert alarm.invariant_name == "s_residual_negative"
    assert alarm.county_fips == "26163"
    assert alarm.year == 2010
    assert alarm.residual < 0
    assert alarm.gdp_per_week == pytest.approx(10_000_000_000.0 / 52.0, rel=1e-9)
    assert alarm.v_per_week == pytest.approx(100_000_000_000.0 / 52.0, rel=1e-9)
