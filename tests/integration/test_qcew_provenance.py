"""Spec-086 T030: provenance queryability + low-confidence flags (US3, SC-006).

RED phase until T031/T032 land the audit module + CLI wiring.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from tests.fixtures.qcew import (
    constraint_70_row,
    constraint_71_row,
    leaf_row,
    us_total_row,
    write_mini_singlefile,
)
from tests.fixtures.qcew.orm import create_qcew_engine, seed_qcew_dims

qcew_main = pytest.importorskip(
    "babylon_data.qcew.__main__", reason="babylon-data symlink not resolved (CI)"
)

pytestmark = [pytest.mark.integration, pytest.mark.ledger]

ROWS = [
    # Wayne: one disclosed leaf, one suppressed (imputed) leaf.
    constraint_70_row("26163", estabs=12, employment=1000, wages=50_000_000),
    constraint_71_row("26163", "5", estabs=12, employment=1000, wages=50_000_000),
    leaf_row("26163", "5", "336111", estabs=8, employment=700, wages=35_000_000),
    leaf_row("26163", "5", "336112", estabs=4, suppressed=True),
    # Macomb: county total itself suppressed → low-confidence + imputed rollup.
    constraint_70_row("26099", estabs=2, employment=0, wages=0, suppressed=True),
    constraint_71_row("26099", "5", estabs=2, employment=200, wages=8_000_000),
    leaf_row("26099", "5", "541511", estabs=2, employment=200, wages=8_000_000),
    us_total_row(estabs=14, employment=1200, wages=58_000_000),
]


@pytest.fixture()
def applied(tmp_path: Path) -> dict[str, Path]:
    db_path = tmp_path / "ref.sqlite"
    engine = create_qcew_engine(f"sqlite:///{db_path}")
    with Session(engine) as session:
        seed_qcew_dims(session)
        session.commit()
    engine.dispose()
    source = tmp_path / "src"
    source.mkdir()
    write_mini_singlefile(source, 2010, ROWS)
    reports = tmp_path / "reports"
    code = qcew_main.main(
        [
            "--apply",
            "--years",
            "2010",
            "--db",
            str(db_path),
            "--source-dir",
            str(source),
            "--report-dir",
            str(reports),
        ]
    )
    assert code == 0
    return {"db": db_path, "reports": reports}


class TestProvenance:
    def test_every_row_has_determinate_provenance(self, applied: dict[str, Path]) -> None:
        engine = create_qcew_engine(f"sqlite:///{applied['db']}")
        with Session(engine) as session:
            total, flagged = session.execute(
                text(
                    "SELECT COUNT(*), SUM(CASE WHEN is_imputed IN (0, 1) THEN 1 ELSE 0 END)"
                    " FROM fact_qcew_annual"
                )
            ).one()
        assert total == 3
        assert flagged == total  # SC-006: 100% coverage

    def test_imputed_implies_suppressed_and_null_derived(self, applied: dict[str, Path]) -> None:
        engine = create_qcew_engine(f"sqlite:///{applied['db']}")
        with Session(engine) as session:
            offenders = session.execute(
                text(
                    "SELECT COUNT(*) FROM fact_qcew_annual"
                    " WHERE is_imputed = 1 AND ("
                    "   disclosure_code IS NOT 'N'"
                    "   OR avg_weekly_wage_usd IS NOT NULL"
                    "   OR lq_employment IS NOT NULL)"
                )
            ).scalar_one()
        assert offenders == 0

    def test_low_confidence_county_in_report_and_rollup_flagged(
        self, applied: dict[str, Path]
    ) -> None:
        import json

        (json_file,) = sorted(applied["reports"].glob("qcew_impute_*.json"))
        document = json.loads(json_file.read_text(encoding="utf-8"))
        low_confidence = document["per_year"][0]["reconciliation"]["low_confidence_county_years"]
        assert {"county_fips": "26099", "reason": "county_total_suppressed"} in low_confidence

        engine = create_qcew_engine(f"sqlite:///{applied['db']}")
        with Session(engine) as session:
            imputed_rollup = session.execute(
                text(
                    "SELECT fr.is_imputed FROM fact_qcew_county_rollup fr"
                    " JOIN dim_county dc ON dc.county_id = fr.county_id"
                    " JOIN dim_ownership do ON do.ownership_id = fr.ownership_id"
                    " WHERE dc.fips = '26099' AND do.own_code = '0'"
                )
            ).scalar_one()
        assert imputed_rollup in (1, True)
