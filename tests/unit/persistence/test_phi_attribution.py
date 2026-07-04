"""Unit tests for spec-101 Φ attribution + bilateral-trade sourcing.

The reference DB provides the Hickel drain only as a national aggregate, so
spec-101 attributes it across engine nodes by bilateral-trade share via the
injective ``_NODE_TO_BLOC`` crosswalk (D3). These tests pin the pure attribution
math and the SQLite trade reader without touching Postgres.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from babylon.persistence.postgres_initialization import (
    _NODE_TO_BLOC,
    PhiAttributionUnavailableError,
    _attribute_phi_and_trade,
    _preflight_hickel_intensive_coverage,
    _read_bloc_trade,
)

pytestmark = [pytest.mark.unit]


def test_crosswalk_is_injective() -> None:
    # No bloc double-counted: distinct bloc id per mapped node.
    bloc_ids = list(_NODE_TO_BLOC.values())
    assert len(bloc_ids) == len(set(bloc_ids))
    # india / latin_america deliberately absent (no distinct grounded bloc, D3).
    assert "india" not in _NODE_TO_BLOC
    assert "latin_america" not in _NODE_TO_BLOC


def test_shares_sum_to_national_phi() -> None:
    national_phi = 8.625e12  # 2010 "Intensive" aggregate, USD
    # one trade value per mapped bloc id
    bloc_trade = {1: 100.0, 7: 200.0, 8: 50.0, 9: 25.0, 10: 300.0, 12: 325.0}
    out = _attribute_phi_and_trade(national_phi=national_phi, bloc_trade=bloc_trade)
    assert set(out) == set(_NODE_TO_BLOC)  # all 6 mapped nodes present
    total_phi = sum(phi for phi, _ in out.values())
    assert total_phi == pytest.approx(national_phi, rel=1e-12)  # national conservation


def test_bilateral_value_is_usd_from_millions() -> None:
    out = _attribute_phi_and_trade(national_phi=1.0, bloc_trade={12: 1183.5})  # only Asia present
    phi, btv = out["china"]
    assert btv == pytest.approx(1183.5 * 1e6)
    assert phi == pytest.approx(1.0)  # china is the sole mapped node with trade → share 1.0


def test_unmapped_and_missing_blocs_absent() -> None:
    # Only EU bloc present → only 'eu' attributed; others fall through to (0,0) at call site.
    out = _attribute_phi_and_trade(national_phi=1.0, bloc_trade={1: 500.0})
    assert set(out) == {"eu"}
    assert out["eu"][0] == pytest.approx(1.0)


def test_no_trade_raises_loud() -> None:
    """Spec-101 fix #1: a zero-trade denominator must fail loud, not silently

    zero the national Φ across every bloc. Mirrors the sibling
    ``county_exposure.py`` hard-fail (III.8: no silent conservation break).
    """
    with pytest.raises(PhiAttributionUnavailableError):
        _attribute_phi_and_trade(national_phi=9.9e12, bloc_trade={})
    # bloc present but zero trade contributes nothing to the denominator either.
    with pytest.raises(PhiAttributionUnavailableError):
        _attribute_phi_and_trade(national_phi=9.9e12, bloc_trade={1: 0.0})


def test_zero_phi_still_populates_trade_value() -> None:
    out = _attribute_phi_and_trade(national_phi=0.0, bloc_trade={1: 500.0})
    phi, btv = out["eu"]
    assert phi == 0.0
    assert btv == pytest.approx(500.0 * 1e6)


def test_read_bloc_trade_from_sqlite(tmp_path: Path) -> None:
    path = tmp_path / "ref.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE dim_time (time_id INTEGER PRIMARY KEY, year INTEGER, is_annual INTEGER);
        CREATE TABLE fact_bilateral_trade_annual (
            time_id INTEGER, country_id INTEGER,
            imports_usd_millions REAL, exports_usd_millions REAL, total_trade_usd_millions REAL
        );
        """
    )
    conn.execute("INSERT INTO dim_time VALUES (14, 2010, 1)")
    conn.execute("INSERT INTO dim_time VALUES (99, 2010, 0)")  # non-annual, must be ignored
    conn.execute("INSERT INTO fact_bilateral_trade_annual VALUES (14, 1, 200, 358, 558.9)")
    conn.execute("INSERT INTO fact_bilateral_trade_annual VALUES (14, 12, 600, 583, 1183.5)")
    conn.execute("INSERT INTO fact_bilateral_trade_annual VALUES (99, 1, 1, 1, 9999)")  # ignored
    conn.commit()
    conn.close()

    trade = _read_bloc_trade(path, 2010)
    assert trade == {1: pytest.approx(558.9), 12: pytest.approx(1183.5)}
    assert _read_bloc_trade(path, 1999) == {}  # no annual time_id


def _make_hickel_sqlite(tmp_path: Path, *, years: list[int]) -> Path:
    path = tmp_path / "hickel.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE dim_time (time_id INTEGER PRIMARY KEY, year INTEGER, is_annual INTEGER);
        CREATE TABLE fact_hickel_erdi_annual (
            id INTEGER PRIMARY KEY, time_id INTEGER, scale_type TEXT,
            erdi REAL, annual_drain_usd_billions REAL
        );
        """
    )
    for i, year in enumerate(years):
        conn.execute("INSERT INTO dim_time VALUES (?, ?, 1)", (i, year))
        conn.execute(
            "INSERT INTO fact_hickel_erdi_annual (time_id, scale_type, erdi, "
            "annual_drain_usd_billions) VALUES (?, 'Intensive', 1.0, 100.0)",
            (i,),
        )
    conn.commit()
    conn.close()
    return path


def test_hickel_coverage_preflight_raises_outside_window(tmp_path: Path) -> None:
    """Spec-101 review fix #2: start_year=2020 is outside the verified

    1980-2017 'Intensive' coverage — must fail loud, not let
    ``_fetch_national_phi`` read back its silent 0.0 fallback.
    """
    path = _make_hickel_sqlite(tmp_path, years=[1980, 2017])
    with pytest.raises(PhiAttributionUnavailableError):
        _preflight_hickel_intensive_coverage(sqlite_path=path, start_year=2020)


def test_hickel_coverage_preflight_passes_inside_window(tmp_path: Path) -> None:
    path = _make_hickel_sqlite(tmp_path, years=[1980, 2010, 2017])
    _preflight_hickel_intensive_coverage(sqlite_path=path, start_year=2010)  # no raise


def test_hickel_coverage_preflight_raises_when_no_intensive_rows(tmp_path: Path) -> None:
    path = _make_hickel_sqlite(tmp_path, years=[])
    with pytest.raises(PhiAttributionUnavailableError):
        _preflight_hickel_intensive_coverage(sqlite_path=path, start_year=2010)
