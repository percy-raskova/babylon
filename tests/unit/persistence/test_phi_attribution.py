"""Unit tests for spec-101 Φ attribution + bilateral-trade sourcing.

The reference DB provides the Hickel drain only as a national aggregate, so
spec-101 attributes it across engine nodes by bilateral-trade share via the
injective ``_NODE_TO_BLOC`` crosswalk (D3). These tests pin the pure attribution
math and the SQLite trade reader without touching Postgres.
"""

from __future__ import annotations

import csv
import gzip
import sqlite3
from pathlib import Path

import pytest

from babylon.persistence.postgres_initialization import (
    _NODE_TO_BLOC,
    PhiAttributionUnavailableError,
    _attribute_phi_and_trade,
    _preflight_hickel_intensive_coverage,
    _read_bloc_trade,
    _read_faf_bloc_tons,
)

pytestmark = [pytest.mark.unit]


def test_crosswalk_is_injective() -> None:
    # No bloc double-counted: distinct bloc id per mapped node.
    bloc_ids = list(_NODE_TO_BLOC.values())
    assert len(bloc_ids) == len(set(bloc_ids))
    # Program 26 U3: india / latin_america are now grounded (Census FT900,
    # dim_country ids 149 / 6) — the ADR055 Φ=0 coverage hole is closed.
    assert _NODE_TO_BLOC["india"] == 149
    assert _NODE_TO_BLOC["latin_america"] == 6


def test_all_eight_international_nodes_mapped() -> None:
    """Every canonical INTERNATIONAL_NODE has a grounded bloc — the
    Program 26 U3 closure means all 8, not 6, nodes are attributable."""
    from babylon.persistence.postgres_initialization import INTERNATIONAL_NODES

    assert set(_NODE_TO_BLOC) == set(INTERNATIONAL_NODES)


def test_shares_sum_to_national_phi() -> None:
    national_phi = 8.625e12  # 2010 "Intensive" aggregate, USD
    # one trade value per mapped bloc id (all 8 nodes, Program 26 U3)
    bloc_trade = {1: 100.0, 6: 40.0, 7: 200.0, 8: 50.0, 9: 25.0, 10: 300.0, 12: 325.0, 149: 60.0}
    out = _attribute_phi_and_trade(national_phi=national_phi, bloc_trade=bloc_trade)
    assert set(out) == set(_NODE_TO_BLOC)  # all 8 mapped nodes present
    total_phi = sum(phi for phi, _ in out.values())
    assert total_phi == pytest.approx(national_phi, rel=1e-12)  # national conservation


def test_india_and_latin_america_receive_positive_phi_when_trade_positive() -> None:
    """Regression pin: Program 26 U3 closes the ADR055 Φ=0 coverage hole —
    india/latin_america must now receive a positive Φ share (not silently
    stay at 0.0) whenever their bloc's recorded trade is positive."""
    national_phi = 1.0e12
    bloc_trade = {149: 100.0, 6: 50.0}  # only india + latin_america present
    out = _attribute_phi_and_trade(national_phi=national_phi, bloc_trade=bloc_trade)
    assert set(out) == {"india", "latin_america"}
    india_phi, india_btv = out["india"]
    latam_phi, latam_btv = out["latin_america"]
    assert india_phi > 0.0
    assert latam_phi > 0.0
    assert india_phi == pytest.approx(national_phi * (100.0 / 150.0))
    assert latam_phi == pytest.approx(national_phi * (50.0 / 150.0))
    assert india_btv == pytest.approx(100.0 * 1e6)
    assert latam_btv == pytest.approx(50.0 * 1e6)
    # Conservation still holds exactly with only these two mapped nodes present.
    assert india_phi + latam_phi == pytest.approx(national_phi, rel=1e-12)


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


# ---------------------------------------------------------------------------
# Program 26 U3 — FAF freight-tons bootstrap stamping (fake artifact rows).
# ---------------------------------------------------------------------------


def _write_fake_faf_artifact(path: Path, rows: list[tuple[str, int, float]]) -> None:
    with gzip.open(path, mode="wt", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["node_id", "year", "tons"])
        for node_id, year, tons in rows:
            writer.writerow([node_id, year, tons])


def test_read_faf_bloc_tons_covered_year(tmp_path: Path) -> None:
    artifact = tmp_path / "faf.csv.gz"
    _write_fake_faf_artifact(
        artifact,
        [
            ("canada", 2018, 613124.6),
            ("canada", 2019, 623131.4),
            ("eu", 2018, 301882.0),
        ],
    )
    out = _read_faf_bloc_tons(year=2018, artifact_path=artifact)
    assert out == {"canada": pytest.approx(613124.6), "eu": pytest.approx(301882.0)}


def test_read_faf_bloc_tons_outside_coverage_window_logs_and_returns_empty(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Spec-101 ADR055 no-fabrication precedent: a start_year outside the
    artifact's 2018-2024 coverage must NOT fabricate tons — one loud log
    line naming the coverage window, empty dict (every node falls back to
    0.0 at the call site)."""
    artifact = tmp_path / "faf.csv.gz"
    _write_fake_faf_artifact(artifact, [("canada", 2018, 613124.6)])
    with caplog.at_level("WARNING"):
        out = _read_faf_bloc_tons(year=2010, artifact_path=artifact)
    assert out == {}
    assert any("2018" in r.message and "2024" in r.message for r in caplog.records)


def test_read_faf_bloc_tons_missing_artifact_file_returns_empty(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    missing = tmp_path / "does-not-exist.csv.gz"
    with caplog.at_level("WARNING"):
        out = _read_faf_bloc_tons(year=2020, artifact_path=missing)
    assert out == {}
    assert len(caplog.records) == 1


def test_read_faf_bloc_tons_real_checked_in_artifact_canada_2018() -> None:
    """Bootstrap-stamping proof against the REAL checked-in artifact
    (default ``artifact_path``): the exact FAF-computed pinned value for
    canada/2018 comes back, matching what ``_bootstrap_external_nodes``
    would stamp onto ``ExternalNode.bilateral_trade_tons``."""
    out = _read_faf_bloc_tons(year=2018)
    assert out["canada"] == pytest.approx(613124.597691, rel=1e-9)
    assert "india" not in out
    assert "russia_csi" not in out
