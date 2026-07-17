"""Spec-086 T037: live-DB reconciliation gates (SC-001…SC-005, FR-010).

Runs ONLY against a spec-086-applied canonical reference database:
skips at collection when the live DB is absent, and at fixture time when
``fact_qcew_annual`` lacks ``is_imputed`` (pre-apply) — the pattern of
``test_post_067_consumer_queries.py``.

Asserts through the REAL consumer path (``fetch_employment_proxy_for_
county_at_tick``) plus rollup-table joins, so FR-010 ("consumers need no
changes") is what is actually tested.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DB_PATH = _REPO_ROOT / "data" / "sqlite" / "marxist-data-3NF.sqlite"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.ledger,
    pytest.mark.empirical,
    pytest.mark.requires_reference_db,
]

if not _DB_PATH.exists():  # pragma: no cover - environment guard
    pytest.skip("live reference DB absent", allow_module_level=True)

#: BLS-published Wayne County MI 2010 Total Covered (verified agglvl-70).
WAYNE_2010_PUBLISHED = 657_150


@pytest.fixture(scope="module")
def live() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{_DB_PATH}?mode=ro", uri=True)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(fact_qcew_annual)")}
    if "is_imputed" not in columns:
        pytest.skip("live DB not yet spec-086 applied (fact_qcew_annual lacks is_imputed)")
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "fact_qcew_county_rollup" not in tables:
        pytest.skip("live DB not yet spec-086 applied (rollup table absent)")
    yield conn
    conn.close()


class TestWayne2010:
    def test_sc003_via_real_consumer_path(self, live: sqlite3.Connection) -> None:
        from babylon.persistence.county_aggregation import (
            fetch_employment_proxy_for_county_at_tick,
        )

        proxy = fetch_employment_proxy_for_county_at_tick(
            _DB_PATH, "26163", tick=0, start_year=2010
        )
        delta_pct = abs(proxy - WAYNE_2010_PUBLISHED) / WAYNE_2010_PUBLISHED * 100.0
        assert delta_pct <= 2.0, f"Wayne 2010 proxy {proxy} vs {WAYNE_2010_PUBLISHED}"


def _within_band_share(live: sqlite3.Connection, metric: str) -> tuple[int, int]:
    rows = live.execute(
        f"""
        SELECT COUNT(*),
               SUM(CASE WHEN fr.{metric} > 0
                         AND ABS(leaf.total - fr.{metric}) * 100.0 / fr.{metric} <= 2.0
                        THEN 1
                        WHEN fr.{metric} = 0 AND leaf.total = 0 THEN 1
                        ELSE 0 END)
        FROM fact_qcew_county_rollup fr
        JOIN dim_ownership do ON do.ownership_id = fr.ownership_id AND do.own_code = '0'
        JOIN (
            SELECT county_id, time_id, SUM({metric}) AS total
            FROM fact_qcew_annual GROUP BY county_id, time_id
        ) leaf ON leaf.county_id = fr.county_id AND leaf.time_id = fr.time_id
        """  # noqa: S608 - metric is a code-controlled literal
    ).fetchone()
    return int(rows[0]), int(rows[1])


class TestBands:
    def test_sc001_employment_99pct_within_2pct(self, live: sqlite3.Connection) -> None:
        total, within = _within_band_share(live, "employment")
        assert total > 40_000  # ~3,220 counties × 15 years
        assert within / total * 100.0 >= 99.0, f"{within}/{total}"

    def test_sc002_wages_99pct_within_2pct(self, live: sqlite3.Connection) -> None:
        total, within = _within_band_share(live, "total_wages_usd")
        assert within / total * 100.0 >= 99.0, f"{within}/{total}"

    def test_sc004_ownership_95pct_within_2pct(self, live: sqlite3.Connection) -> None:
        rows = live.execute(
            """
            SELECT COUNT(*),
                   SUM(CASE WHEN fr.employment > 0
                             AND ABS(leaf.total - fr.employment) * 100.0 / fr.employment <= 2.0
                            THEN 1
                            WHEN fr.employment = 0 AND COALESCE(leaf.total, 0) = 0 THEN 1
                            ELSE 0 END)
            FROM fact_qcew_county_rollup fr
            JOIN dim_ownership do ON do.ownership_id = fr.ownership_id AND do.own_code != '0'
            LEFT JOIN (
                SELECT county_id, time_id, ownership_id, SUM(employment) AS total
                FROM fact_qcew_annual GROUP BY county_id, time_id, ownership_id
            ) leaf ON leaf.county_id = fr.county_id AND leaf.time_id = fr.time_id
                  AND leaf.ownership_id = fr.ownership_id
            """
        ).fetchone()
        total, within = int(rows[0]), int(rows[1])
        assert within / total * 100.0 >= 95.0, f"{within}/{total}"


class TestProvenanceAtScale:
    def test_sc006_full_coverage_and_semantics(self, live: sqlite3.Connection) -> None:
        total, determinate = live.execute(
            "SELECT COUNT(*), SUM(CASE WHEN is_imputed IN (0,1) THEN 1 ELSE 0 END)"
            " FROM fact_qcew_annual"
        ).fetchone()
        assert total > 10_000_000
        assert determinate == total
        offenders = live.execute(
            "SELECT COUNT(*) FROM fact_qcew_annual"
            " WHERE is_imputed = 1 AND disclosure_code IS NOT 'N'"
        ).fetchone()[0]
        assert offenders == 0
