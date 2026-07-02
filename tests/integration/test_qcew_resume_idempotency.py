"""Spec-086 T021: resume + idempotency + determinism e2e (US2, FR-007/008/012).

RED phase until T024 lands the staging lifecycle in
``babylon_data.qcew.writer``.
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
    write_mini_singlefile,
)
from tests.fixtures.qcew.orm import create_qcew_engine, seed_qcew_dims

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

pytestmark = [pytest.mark.integration, pytest.mark.ledger, pytest.mark.red_phase]

KNOWN_FIPS = {"26163", "26099", "46102", "46113", "09110"}


def _year_rows(year: int, employment: int) -> list[str]:
    wages = employment * 50_000
    disclosed = employment - employment // 4
    return [
        constraint_70_row("26163", year=year, estabs=6, employment=employment, wages=wages),
        constraint_71_row("26163", "5", year=year, estabs=6, employment=employment, wages=wages),
        leaf_row(
            "26163",
            "5",
            "336111",
            year=year,
            estabs=4,
            employment=disclosed,
            wages=disclosed * 50_000,
        ),
        leaf_row("26163", "5", "336112", year=year, estabs=2, suppressed=True),
    ]


def _load_year_into_staging(session: Session, source_dir: Path, year: int) -> int:
    data = singlefile.read_singlefile(
        source_dir / f"{year}.annual.singlefile.csv", year=year, known_county_fips=KNOWN_FIPS
    )
    trees = hierarchy.trees_from_year_data(data)
    results = {fips: imputation.impute_county(tree) for fips, tree in trees.items()}
    dim_maps = qcew_writer.build_dim_maps(session)
    return qcew_writer.load_year_into_staging(
        session, year=year, trees=trees, results=results, dim_maps=dim_maps
    )


@pytest.fixture()
def source_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "qcew-src"
    directory.mkdir()
    write_mini_singlefile(directory, 2010, _year_rows(2010, 1000))
    write_mini_singlefile(directory, 2015, _year_rows(2015, 1200))
    return directory


@pytest.fixture()
def session(tmp_path: Path):  # type: ignore[no-untyped-def]
    engine = create_qcew_engine(f"sqlite:///{tmp_path / 'ref.sqlite'}")
    with Session(engine) as sess:
        seed_qcew_dims(sess)
        yield sess


class TestResume:
    def test_interrupted_run_resumes_at_first_unloaded_year(
        self, session: Session, source_dir: Path
    ) -> None:
        qcew_writer.ensure_staging_tables(session)
        _load_year_into_staging(session, source_dir, 2010)  # "interrupt" after year 1
        assert qcew_writer.pending_years(session, [2010, 2015]) == [2015]
        _load_year_into_staging(session, source_dir, 2015)
        assert qcew_writer.pending_years(session, [2010, 2015]) == []
        counts = session.execute(
            text(
                f"SELECT t.year, COUNT(*) FROM {qcew_writer.STAGING_LEAF_TABLE} s"
                " JOIN dim_time t ON t.time_id = s.time_id GROUP BY t.year ORDER BY t.year"
            )
        ).all()
        assert [tuple(row) for row in counts] == [(2010, 2), (2015, 2)]

    def test_reloading_a_year_replaces_rather_than_duplicates(
        self, session: Session, source_dir: Path
    ) -> None:
        qcew_writer.ensure_staging_tables(session)
        _load_year_into_staging(session, source_dir, 2010)
        _load_year_into_staging(session, source_dir, 2010)  # FR-007 idempotent re-run
        count = session.execute(
            text(f"SELECT COUNT(*) FROM {qcew_writer.STAGING_LEAF_TABLE}")
        ).scalar_one()
        assert count == 2


class TestDeterminism:
    def test_two_full_runs_reproduce_identical_logical_hashes(
        self, tmp_path: Path, source_dir: Path
    ) -> None:
        hashes = []
        for run in ("a", "b"):
            engine = create_qcew_engine(f"sqlite:///{tmp_path / f'ref-{run}.sqlite'}")
            with Session(engine) as sess:
                seed_qcew_dims(sess)
                qcew_writer.ensure_staging_tables(sess)
                for year in (2010, 2015):
                    _load_year_into_staging(sess, source_dir, year)
                qcew_writer.swap_staging(sess)
                sess.commit()
                hashes.append(
                    (
                        qcew_writer.logical_table_hash(sess, "fact_qcew_annual"),
                        qcew_writer.logical_table_hash(sess, "fact_qcew_county_rollup"),
                    )
                )
        assert hashes[0] == hashes[1]

    def test_composite_pk_rejects_duplicate_leaf(self, session: Session) -> None:
        qcew_writer.ensure_staging_tables(session)
        insert = (
            f"INSERT INTO {qcew_writer.STAGING_LEAF_TABLE}"
            " (county_id, industry_id, ownership_id, time_id,"
            "  establishments, employment, total_wages_usd, is_imputed)"
            " VALUES (1, 6, 5, 1, 1, 10, 100.0, 0)"
        )
        session.execute(text(insert))
        with pytest.raises(Exception, match="UNIQUE|PRIMARY"):
            session.execute(text(insert))
        session.rollback()
