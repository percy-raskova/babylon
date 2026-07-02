"""Spec-086 T022: staged-swap lifecycle mechanics (US2, research D9).

RED phase until T024 lands swap/rollback/drop-backup in
``babylon_data.qcew.writer``: canonical → ``__pre_086`` backup, staging →
canonical, the three canonical indexes recreated, the stale
``_cache_national_wages_bea`` dropped, legacy file-checkpoints purged.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

qcew_writer = pytest.importorskip(
    "babylon_data.qcew.writer",
    reason="babylon-data symlink not resolved (CI)",
)

pytestmark = [pytest.mark.integration, pytest.mark.ledger, pytest.mark.red_phase]

_CANONICAL_INDEXES = {"idx_qcew_county_time", "idx_qcew_industry_time", "idx_qcew_ownership"}


def _table_names(session: Session) -> set[str]:
    rows = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).all()
    return {row[0] for row in rows}


def _index_names(session: Session, table: str) -> set[str]:
    rows = session.execute(
        text(f"SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='{table}'")
    ).all()
    return {row[0] for row in rows if not row[0].startswith("sqlite_autoindex")}


def _stage_one_row(session: Session) -> None:
    qcew_writer.ensure_staging_tables(session)
    session.execute(
        text(
            f"INSERT INTO {qcew_writer.STAGING_LEAF_TABLE}"
            " (county_id, industry_id, ownership_id, time_id,"
            "  establishments, employment, total_wages_usd, is_imputed)"
            " VALUES (1, 6, 5, 1, 3, 777, 12345.0, 1)"
        )
    )
    session.execute(
        text(
            f"INSERT INTO {qcew_writer.STAGING_ROLLUP_TABLE}"
            " (county_id, time_id, ownership_id, establishments, employment,"
            "  total_wages_usd, is_imputed)"
            " VALUES (1, 1, 1, 3, 777, 12345.0, 0)"
        )
    )


class TestSwap:
    def test_swap_promotes_staging_and_keeps_backup(self, qcew_orm_session: Session) -> None:
        qcew_orm_session.execute(
            text(
                "INSERT INTO fact_qcew_annual"
                " (county_id, industry_id, ownership_id, time_id,"
                "  establishments, employment, total_wages_usd, is_imputed)"
                " VALUES (1, 6, 5, 1, 9, 111, 999.0, 0)"
            )
        )
        _stage_one_row(qcew_orm_session)
        qcew_orm_session.execute(text("CREATE TABLE _cache_national_wages_bea (x INT)"))

        qcew_writer.swap_staging(qcew_orm_session)

        tables = _table_names(qcew_orm_session)
        assert "fact_qcew_annual__pre_086" in tables
        assert "fact_qcew_county_rollup__pre_086" in tables
        assert qcew_writer.STAGING_LEAF_TABLE not in tables
        assert "_cache_national_wages_bea" not in tables

        promoted = qcew_orm_session.execute(
            text("SELECT employment FROM fact_qcew_annual")
        ).scalar_one()
        assert promoted == 777
        backed_up = qcew_orm_session.execute(
            text("SELECT employment FROM fact_qcew_annual__pre_086")
        ).scalar_one()
        assert backed_up == 111

    def test_swap_recreates_canonical_indexes(self, qcew_orm_session: Session) -> None:
        _stage_one_row(qcew_orm_session)
        qcew_writer.swap_staging(qcew_orm_session)
        assert _index_names(qcew_orm_session, "fact_qcew_annual") >= _CANONICAL_INDEXES


class TestRollbackAndDrop:
    def test_rollback_restores_pre_086_tables(self, qcew_orm_session: Session) -> None:
        qcew_orm_session.execute(
            text(
                "INSERT INTO fact_qcew_annual"
                " (county_id, industry_id, ownership_id, time_id,"
                "  establishments, employment, total_wages_usd, is_imputed)"
                " VALUES (1, 6, 5, 1, 9, 111, 999.0, 0)"
            )
        )
        _stage_one_row(qcew_orm_session)
        qcew_writer.swap_staging(qcew_orm_session)

        qcew_writer.rollback_from_backup(qcew_orm_session)

        restored = qcew_orm_session.execute(
            text("SELECT employment FROM fact_qcew_annual")
        ).scalar_one()
        assert restored == 111
        assert "fact_qcew_annual__pre_086" not in _table_names(qcew_orm_session)

    def test_drop_backup_removes_pre_086_tables(self, qcew_orm_session: Session) -> None:
        _stage_one_row(qcew_orm_session)
        qcew_writer.swap_staging(qcew_orm_session)
        qcew_writer.drop_backup(qcew_orm_session)
        tables = _table_names(qcew_orm_session)
        assert "fact_qcew_annual__pre_086" not in tables
        assert "fact_qcew_county_rollup__pre_086" not in tables

    def test_rollback_without_backup_is_a_hard_error(self, qcew_orm_session: Session) -> None:
        with pytest.raises(qcew_writer.SwapStateError):
            qcew_writer.rollback_from_backup(qcew_orm_session)
