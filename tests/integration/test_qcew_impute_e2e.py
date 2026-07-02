"""Spec-086 T013: fixture-scale end-to-end pipeline (US1).

RED phase until T014–T018 land ``babylon_data.qcew.{singlefile,hierarchy,
imputation,writer,validation}``.

Composes the real seams: mini singlefile → classify → trees → impute →
write into an in-memory ORM database → reconcile. Asserts the US1
acceptance shape: summed leaves reconcile EXACTLY to the published county
Total Covered; provenance flags and NULL-avg/lq semantics hold; the
constraint rollup table is populated.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from tests.fixtures.qcew import (
    constraint_70_row,
    constraint_71_row,
    leaf_row,
    naics_constraint_row,
    us_total_row,
    write_mini_singlefile,
)

singlefile = pytest.importorskip(
    "babylon_data.qcew.singlefile", reason="babylon-data symlink not resolved (CI)"
)
hierarchy = pytest.importorskip(
    "babylon_data.qcew.hierarchy", reason="babylon-data symlink not resolved (CI)"
)
imputation = pytest.importorskip(
    "babylon_data.qcew.imputation", reason="babylon-data symlink not resolved (CI)"
)
qcew_writer = pytest.importorskip(
    "babylon_data.qcew.writer", reason="babylon-data symlink not resolved (CI)"
)
validation = pytest.importorskip(
    "babylon_data.qcew.validation", reason="babylon-data symlink not resolved (CI)"
)

pytestmark = [pytest.mark.integration, pytest.mark.ledger]

KNOWN_FIPS = {"26163", "26099", "46102", "46113", "09110"}


@pytest.fixture()
def qcew_orm_session():  # type: ignore[no-untyped-def]
    from sqlalchemy.orm import Session

    from tests.fixtures.qcew.orm import create_qcew_engine, seed_qcew_dims

    with Session(create_qcew_engine()) as session:
        seed_qcew_dims(session)
        yield session


def _wayne_macomb_rows() -> list[str]:
    """Two-county 2010 fixture: Wayne heavily suppressed, Macomb fully disclosed."""
    return [
        # Wayne (26163): total 1000/50M; own 5 = 900/45M, own 3 = 100/5M.
        constraint_70_row("26163", estabs=12, employment=1000, wages=50_000_000),
        constraint_71_row("26163", "5", estabs=9, employment=900, wages=45_000_000),
        constraint_71_row("26163", "3", estabs=3, employment=100, wages=5_000_000),
        naics_constraint_row("26163", "5", "31-33", estabs=9, employment=900, wages=45_000_000),
        leaf_row("26163", "5", "336111", estabs=5, employment=600, wages=30_000_000),
        leaf_row("26163", "5", "336112", estabs=4, suppressed=True),  # → 300 / 15M
        leaf_row("26163", "3", "541511", estabs=3, suppressed=True),  # → 100 / 5M
        # Macomb (26099): fully disclosed single leaf.
        constraint_70_row("26099", estabs=2, employment=200, wages=8_000_000),
        constraint_71_row("26099", "5", estabs=2, employment=200, wages=8_000_000),
        leaf_row("26099", "5", "541511", estabs=2, employment=200, wages=8_000_000),
        us_total_row(estabs=14, employment=1200, wages=58_000_000),
    ]


@pytest.fixture()
def loaded_session(qcew_orm_session, tmp_path: Path):  # type: ignore[no-untyped-def]
    path = write_mini_singlefile(tmp_path, 2010, _wayne_macomb_rows())
    year_data = singlefile.read_singlefile(path, year=2010, known_county_fips=KNOWN_FIPS)
    trees = hierarchy.trees_from_year_data(year_data)
    results = {fips: imputation.impute_county(tree) for fips, tree in trees.items()}
    dim_maps = qcew_writer.build_dim_maps(qcew_orm_session)
    qcew_writer.write_year(
        qcew_orm_session, year=2010, trees=trees, results=results, dim_maps=dim_maps
    )
    qcew_orm_session.commit()
    return qcew_orm_session


class TestReconciliation:
    def test_leaf_sums_reconcile_exactly_to_published_totals(self, loaded_session) -> None:  # type: ignore[no-untyped-def]
        rows = loaded_session.execute(
            text(
                "SELECT dc.fips, SUM(fq.employment), SUM(fq.total_wages_usd)"
                " FROM fact_qcew_annual fq"
                " JOIN dim_county dc ON dc.county_id = fq.county_id"
                " GROUP BY dc.fips ORDER BY dc.fips"
            )
        ).all()
        assert [(r[0], int(r[1]), int(r[2])) for r in rows] == [
            ("26099", 200, 8_000_000),
            ("26163", 1000, 50_000_000),
        ]

    def test_validation_module_reports_exact_reconciliation(self, loaded_session) -> None:  # type: ignore[no-untyped-def]
        dim_maps = qcew_writer.build_dim_maps(loaded_session)
        report = validation.reconcile_year(loaded_session, year=2010, dim_maps=dim_maps)
        by_fips = {entry.fips: entry for entry in report}
        assert by_fips["26163"].employment_residual_pct == 0.0
        assert by_fips["26163"].wages_residual_pct == 0.0
        assert by_fips["26163"].within_band is True
        assert by_fips["26099"].within_band is True


class TestProvenance:
    def test_imputed_rows_flagged_with_null_derived_fields(self, loaded_session) -> None:  # type: ignore[no-untyped-def]
        rows = loaded_session.execute(
            text(
                "SELECT di.naics_code, fq.is_imputed, fq.employment, fq.disclosure_code,"
                "       fq.avg_weekly_wage_usd, fq.lq_employment"
                " FROM fact_qcew_annual fq"
                " JOIN dim_industry di ON di.industry_id = fq.industry_id"
                " JOIN dim_county dc ON dc.county_id = fq.county_id"
                " WHERE dc.fips = '26163' ORDER BY di.naics_code, fq.ownership_id"
            )
        ).all()
        by_key = {(r[0]): r for r in rows if r[0] != "541511"}
        observed = by_key["336111"]
        assert observed[1] in (0, False)
        assert observed[2] == 600
        imputed = by_key["336112"]
        assert imputed[1] in (1, True)
        assert imputed[2] == 300
        assert imputed[3] == "N"
        assert imputed[4] is None and imputed[5] is None

    def test_own3_suppressed_leaf_recovered_exactly(self, loaded_session) -> None:  # type: ignore[no-untyped-def]
        row = loaded_session.execute(
            text(
                "SELECT fq.employment, fq.total_wages_usd, fq.is_imputed"
                " FROM fact_qcew_annual fq"
                " JOIN dim_industry di ON di.industry_id = fq.industry_id"
                " JOIN dim_ownership do ON do.ownership_id = fq.ownership_id"
                " JOIN dim_county dc ON dc.county_id = fq.county_id"
                " WHERE dc.fips = '26163' AND di.naics_code = '541511' AND do.own_code = '3'"
            )
        ).one()
        assert (int(row[0]), int(row[1])) == (100, 5_000_000)
        assert row[2] in (1, True)


class TestRollupTable:
    def test_published_constraints_persisted(self, loaded_session) -> None:  # type: ignore[no-untyped-def]
        rows = loaded_session.execute(
            text(
                "SELECT dc.fips, do.own_code, fr.employment, fr.is_imputed"
                " FROM fact_qcew_county_rollup fr"
                " JOIN dim_county dc ON dc.county_id = fr.county_id"
                " JOIN dim_ownership do ON do.ownership_id = fr.ownership_id"
                " ORDER BY dc.fips, do.own_code"
            )
        ).all()
        as_tuples = [(r[0], r[1], int(r[2]), bool(r[3])) for r in rows]
        assert ("26163", "0", 1000, False) in as_tuples
        assert ("26163", "5", 900, False) in as_tuples
        assert ("26163", "3", 100, False) in as_tuples
        assert ("26099", "0", 200, False) in as_tuples

    def test_true_zero_disclosed_cell_not_flagged(self, loaded_session) -> None:  # type: ignore[no-untyped-def]
        count = loaded_session.execute(
            text("SELECT COUNT(*) FROM fact_qcew_annual WHERE is_imputed = 1")
        ).scalar_one()
        assert count == 2  # exactly the two suppressed Wayne leaves
