"""Unit tests for Bug A — hex_hydrator Marx accounting (spec-066 US1).

Spec: 066-marx-coherence-fixes (T012-T014) + spec-068 T056 (BEA share wiring).

These tests verify the formula change ``s = max(0, GDP/52 - v)`` (NOT
``max(0, GDP/52 - v - c)``), the addition of ``industry_id = 1`` to the
QCEW SUM query, and the emission of a ``_CalibrationAlarm`` when the raw
residual is negative.

T056 tests verify that ``_fetch_per_county_data`` uses the
``BEAShareLookupService`` per-county share when provided, falling back
to the 0.5 constant when ``None`` (FR-010 backward-compat).

Uses an in-memory SQLite database with the minimal schema mirroring
``data/sqlite/marxist-data-3NF.sqlite``.
"""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

import pytest

from babylon.persistence.hex_hydrator import (
    _CalibrationAlarm,
    _fetch_per_county_data,
)
from babylon.reference.bea.lookup_results import CountyShareLookupResult

pytestmark = [pytest.mark.unit]


def _build_minimal_sqlite(
    *,
    fips: str = "26163",
    year: int = 2010,
    total_wages_industry_1: float = 50_000_000_000.0,  # $50B/yr canonical-leaves total
    total_wages_industry_2: float = 30_000_000_000.0,  # retained for sig compat; unused post-067
    bea_gdp_millions: float = 200_000.0,  # $200B Wayne Cty GDP
) -> sqlite3.Connection:
    """In-memory SQLite with the four tables ``_fetch_per_county_data`` reads.

    Post-spec-067: inserts ONE QCEW row representing the SUM of canonical
    leaves for the (county, year). Spec-066's multi-row fixture verified
    the now-removed filter; post-067 the consumer has no filter so the
    test invariants are simpler.
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
    # **Post-spec-067 contract** (commit 3b7568ec): hex_hydrator SUMs all
    # rows for a (county, year) without filtering. Spec-067's data-layer
    # migration guarantees only canonical leaves (naics_level=6 × own_code
    # ∈ {'1','2','3','5'}) exist in fact_qcew_annual, so SUM-of-everything
    # is the BLS-publication aggregate.
    #
    # The fixture inserts ONE row whose total_wages_usd equals
    # `total_wages_industry_1` — the tests' v_per_week expectations
    # then trivially match `total_wages_industry_1 / 52`. Multi-row
    # SUM coverage is in test_employment_proxy_units.py.
    conn.execute(
        "INSERT INTO fact_qcew_annual VALUES (?, ?, ?, ?, ?, ?)",
        (1, 2, 2, 1, 1_200_000, total_wages_industry_1),
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
    """T013 / FR-002 (amended post-spec-067): QCEW SUM aggregates over the
    canonical leaves for a (county, year).

    Post-067 the consumer has no `WHERE industry_id = 1` filter — the
    data-layer migration deleted all non-canonical (rollup) rows, so
    the fixture's single row IS the canonical leaves total.

    The test name is retained for git-history continuity; the assertion
    body is now the SUM-of-leaves contract.
    """
    conn = _build_minimal_sqlite(
        total_wages_industry_1=50_000_000_000.0,
    )
    rows = _fetch_per_county_data(conn=conn, counties=frozenset({"26163"}), year=2010)
    row = rows["26163"]

    # Single fixture row → SUM equals total_wages_industry_1 = $50B/yr.
    # v_per_week = $50B / 52 weeks ≈ $961.5M/wk.
    expected_v = 50_000_000_000.0 / 52.0
    assert row.v_per_week == pytest.approx(expected_v, rel=1e-9), (
        f"v_per_week={row.v_per_week} ≠ canonical-leaves SUM / 52 = {expected_v:.0f}"
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


# ─── T056: BEAShareLookupService wiring (spec-068) ─────────────────────


def _build_two_county_sqlite() -> sqlite3.Connection:
    """In-memory SQLite with two counties for BEA-share-wiring tests.

    County 26163 (Wayne): GDP=$200B, wages=$50B/yr.
    County 26099 (Oakland): GDP=$100B, wages=$30B/yr.
    """
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE dim_county (county_id INTEGER PRIMARY KEY, fips TEXT NOT NULL);
        CREATE TABLE dim_time (time_id INTEGER PRIMARY KEY, year INTEGER NOT NULL);
        CREATE TABLE fact_qcew_annual (
            county_id INTEGER, industry_id INTEGER, ownership_id INTEGER,
            time_id INTEGER, employment INTEGER, total_wages_usd NUMERIC(15, 2)
        );
        CREATE TABLE fact_bea_county_gdp (
            county_id INTEGER, time_id INTEGER, bea_industry_id INTEGER, gdp_millions REAL
        );
        CREATE TABLE fact_broadband_coverage (county_id INTEGER, pct_25_3 REAL, pct_100_20 REAL);
        CREATE TABLE fact_coercive_infrastructure (county_id INTEGER, facility_count INTEGER);
        """
    )
    conn.execute("INSERT INTO dim_county VALUES (1, '26163'), (2, '26099')")
    conn.execute("INSERT INTO dim_time VALUES (1, 2010)")
    conn.execute(
        "INSERT INTO fact_qcew_annual VALUES (1, 2, 2, 1, 1200000, 50000000000.0), "
        "(2, 2, 2, 1, 500000, 30000000000.0)"
    )
    conn.execute("INSERT INTO fact_bea_county_gdp VALUES (1, 1, 1, 200000.0), (2, 1, 1, 100000.0)")
    conn.commit()
    return conn


def _make_mock_service(share_by_fips: dict[str, float]) -> MagicMock:
    """Build a mock BEAShareLookupService returning per-county shares."""

    def _lookup(county_fips: str, year: int) -> CountyShareLookupResult:
        share = share_by_fips[county_fips]
        return CountyShareLookupResult(
            intermediate_inputs_share=share,
            value_added_share=1.0 - share,
            fallback_employment_fraction=0.0,
            per_industry_breakdown={},
        )

    mock = MagicMock()
    mock.lookup_county_share.side_effect = _lookup
    return mock


def test_bea_share_service_overrides_constant_fraction() -> None:
    """T056: When a BEAShareLookupService is provided, ``c_per_week`` uses the
    per-county share from the service instead of the 0.5 constant.

    RED against pre-T056 code: ``_fetch_per_county_data`` does not accept
    ``bea_share_service`` → ``TypeError``.
    """
    conn = _build_two_county_sqlite()
    svc = _make_mock_service({"26163": 0.3, "26099": 0.7})

    rows = _fetch_per_county_data(
        conn=conn,
        counties=frozenset({"26163", "26099"}),
        year=2010,
        bea_share_service=svc,
    )

    # Wayne: GDP=$200B, share=0.3 → c = 200e9 * 0.3 / 52
    expected_c_wayne = 200_000_000_000.0 * 0.3 / 52.0
    # Oakland: GDP=$100B, share=0.7 → c = 100e9 * 0.7 / 52
    expected_c_oakland = 100_000_000_000.0 * 0.7 / 52.0

    assert rows["26163"].c_per_week == pytest.approx(expected_c_wayne, rel=1e-9)
    assert rows["26099"].c_per_week == pytest.approx(expected_c_oakland, rel=1e-9)

    # The constant 0.5 would give Wayne c = 200e9*0.5/52 ≈ $1.923B/wk.
    # With share=0.3, c ≈ $1.154B/wk — strictly different.
    constant_c_wayne = 200_000_000_000.0 * 0.5 / 52.0
    assert rows["26163"].c_per_week != pytest.approx(constant_c_wayne, rel=1e-3)

    # Service called once per county with correct args.
    assert svc.lookup_county_share.call_count == 2
    svc.lookup_county_share.assert_any_call(county_fips="26163", year=2010)
    svc.lookup_county_share.assert_any_call(county_fips="26099", year=2010)


def test_bea_share_service_none_uses_constant_fraction() -> None:
    """T056: When ``bea_share_service`` is ``None``, the 0.5 constant is used
    (FR-010 backward-compat — preserves the spec-066/067 baseline)."""
    conn = _build_two_county_sqlite()

    rows = _fetch_per_county_data(
        conn=conn,
        counties=frozenset({"26163", "26099"}),
        year=2010,
        bea_share_service=None,
    )

    # Both counties use 0.5 → c = GDP * 0.5 / 52
    expected_c_wayne = 200_000_000_000.0 * 0.5 / 52.0
    expected_c_oakland = 100_000_000_000.0 * 0.5 / 52.0
    assert rows["26163"].c_per_week == pytest.approx(expected_c_wayne, rel=1e-9)
    assert rows["26099"].c_per_week == pytest.approx(expected_c_oakland, rel=1e-9)


def test_bea_share_service_different_shares_produce_different_cv() -> None:
    """T056/SC-005: When two counties have different BEA shares, their c/v
    ratios differ — the precondition for ``stddev(c/v) > 0`` across counties.

    RED against pre-T056 code: every county gets 0.5 → identical c/v.
    """
    conn = _build_two_county_sqlite()
    svc = _make_mock_service({"26163": 0.3, "26099": 0.7})

    rows = _fetch_per_county_data(
        conn=conn,
        counties=frozenset({"26163", "26099"}),
        year=2010,
        bea_share_service=svc,
    )

    cv_wayne = rows["26163"].c_per_week / rows["26163"].v_per_week
    cv_oakland = rows["26099"].c_per_week / rows["26099"].v_per_week
    assert cv_wayne != pytest.approx(cv_oakland, rel=1e-3), (
        f"c/v must differ when BEA shares differ: wayne={cv_wayne:.4f}, oakland={cv_oakland:.4f}"
    )
