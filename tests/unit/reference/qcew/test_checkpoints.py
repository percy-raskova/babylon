"""Spec-086 T020: per-year checkpoint semantics (US2, FR-012).

RED phase until T024 extends ``babylon_data.qcew.writer`` with the staging
lifecycle. Corrected ``ingest_checkpoint`` usage (data-model.md §3):
``(source='qcew', year=<real>, state_fips='US', table_id='annual_v086',
race_code='T')`` — no more year=0 / path-hash abuse; the swap purges ONLY
the legacy ``table_id='file'`` rows.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

qcew_writer = pytest.importorskip(
    "babylon_data.qcew.writer",
    reason="babylon-data symlink not resolved (CI)",
)

pytestmark = [pytest.mark.unit, pytest.mark.ledger]


def _insert_legacy_checkpoint(session: Session) -> None:
    session.execute(
        text(
            "INSERT INTO ingest_checkpoint"
            " (source_code, year, state_fips, table_id, race_code, row_count)"
            " VALUES ('qcew', 0, '9326447d07859049', 'file', 'T', 2861234)"
        )
    )


def _insert_other_source_checkpoint(session: Session) -> None:
    session.execute(
        text(
            "INSERT INTO ingest_checkpoint"
            " (source_code, year, state_fips, table_id, race_code, row_count)"
            " VALUES ('census', 2010, '26', 'B01001', 'T', 12345)"
        )
    )


class TestCheckpointRecords:
    def test_record_and_exists(self, qcew_orm_session: Session) -> None:
        assert qcew_writer.year_checkpoint_exists(qcew_orm_session, 2010) is False
        qcew_writer.record_year_checkpoint(qcew_orm_session, 2010, row_count=42)
        assert qcew_writer.year_checkpoint_exists(qcew_orm_session, 2010) is True
        row = qcew_orm_session.execute(
            text(
                "SELECT source_code, year, state_fips, table_id, race_code, row_count"
                " FROM ingest_checkpoint WHERE source_code='qcew' AND table_id='annual_v086'"
            )
        ).one()
        assert tuple(row) == ("qcew", 2010, "US", "annual_v086", "T", 42)

    def test_record_is_upsert(self, qcew_orm_session: Session) -> None:
        qcew_writer.record_year_checkpoint(qcew_orm_session, 2010, row_count=1)
        qcew_writer.record_year_checkpoint(qcew_orm_session, 2010, row_count=99)
        count, row_count = qcew_orm_session.execute(
            text(
                "SELECT COUNT(*), MAX(row_count) FROM ingest_checkpoint"
                " WHERE source_code='qcew' AND table_id='annual_v086' AND year=2010"
            )
        ).one()
        assert (count, row_count) == (1, 99)


class TestResume:
    def test_pending_years_skips_checkpointed_and_populated(
        self, qcew_orm_session: Session
    ) -> None:
        qcew_writer.ensure_staging_tables(qcew_orm_session)
        # 2010 checkpointed AND populated in staging → skipped; 2015 not.
        qcew_orm_session.execute(
            text(
                f"INSERT INTO {qcew_writer.STAGING_LEAF_TABLE}"
                " (county_id, industry_id, ownership_id, time_id,"
                "  establishments, employment, total_wages_usd, is_imputed)"
                " VALUES (1, 6, 5, 1, 1, 10, 100.0, 0)"
            )
        )
        qcew_writer.record_year_checkpoint(qcew_orm_session, 2010, row_count=1)
        assert qcew_writer.pending_years(qcew_orm_session, [2010, 2015]) == [2015]

    def test_checkpoint_without_rows_is_not_skipped(self, qcew_orm_session: Session) -> None:
        qcew_writer.ensure_staging_tables(qcew_orm_session)
        qcew_writer.record_year_checkpoint(qcew_orm_session, 2010, row_count=0)
        assert qcew_writer.pending_years(qcew_orm_session, [2010, 2015]) == [2010, 2015]


class TestRestartAndPurge:
    def test_clear_staging_drops_tables_and_v086_checkpoints_only(
        self, qcew_orm_session: Session
    ) -> None:
        qcew_writer.ensure_staging_tables(qcew_orm_session)
        qcew_writer.record_year_checkpoint(qcew_orm_session, 2010, row_count=5)
        _insert_legacy_checkpoint(qcew_orm_session)
        _insert_other_source_checkpoint(qcew_orm_session)

        qcew_writer.clear_staging(qcew_orm_session)

        remaining = qcew_orm_session.execute(
            text("SELECT source_code, table_id FROM ingest_checkpoint ORDER BY source_code")
        ).all()
        assert [tuple(row) for row in remaining] == [("census", "B01001"), ("qcew", "file")]
        staging_exists = qcew_orm_session.execute(
            text(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                f" AND name='{qcew_writer.STAGING_LEAF_TABLE}'"
            )
        ).scalar_one()
        assert staging_exists == 0

    def test_purge_legacy_checkpoints_targets_only_old_loader_rows(
        self, qcew_orm_session: Session
    ) -> None:
        qcew_writer.record_year_checkpoint(qcew_orm_session, 2010, row_count=5)
        _insert_legacy_checkpoint(qcew_orm_session)
        _insert_other_source_checkpoint(qcew_orm_session)

        purged = qcew_writer.purge_legacy_checkpoints(qcew_orm_session)

        assert purged == 1
        remaining = qcew_orm_session.execute(
            text("SELECT source_code, table_id FROM ingest_checkpoint ORDER BY source_code")
        ).all()
        assert [tuple(row) for row in remaining] == [
            ("census", "B01001"),
            ("qcew", "annual_v086"),
        ]
