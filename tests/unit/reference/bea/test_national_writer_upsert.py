"""T019: UPSERT writer tests for fact_bea_national_industry (spec-068)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from babylon.reference.bea.ingest.national_writer import upsert_national_records
from babylon.reference.bea.models import BEAIndustryAnnualRecord
from babylon.reference.schema import (
    DimBEAIndustry,
    DimTime,
    FactBEANationalIndustry,
    NormalizedBase,
)


@pytest.fixture
def transient_session() -> Session:
    """Fresh in-memory SQLite with the spec-068 schema."""
    engine = create_engine("sqlite:///:memory:")
    NormalizedBase.metadata.create_all(
        engine,
        tables=[
            DimBEAIndustry.__table__,
            DimTime.__table__,
            FactBEANationalIndustry.__table__,
        ],
    )
    session = Session(engine)
    # Seed two industries + two years for the writer to look up via FKs.
    session.execute(
        text(
            "INSERT INTO dim_bea_industry (bea_industry_id, bea_code, industry_name, bea_level, line_number) "
            "VALUES (1, 'X11', 'Test Industry 1', 3, 1), "
            "       (2, 'X22', 'Test Industry 2', 3, 2)"
        )
    )
    session.execute(
        text(
            "INSERT INTO dim_time (time_id, year, is_annual) VALUES (100, 2010, 1), (101, 2011, 1)"
        )
    )
    session.commit()
    yield session
    session.close()


def _make_record(
    bea_id: int,
    year: int,
    go: str = "1000",
    ii: str = "400",
    va: str = "600",
    vintage: date | None = None,
) -> BEAIndustryAnnualRecord:
    return BEAIndustryAnnualRecord(
        bea_industry_id=bea_id,
        year=year,
        gross_output_millions=Decimal(go),
        intermediate_inputs_millions=Decimal(ii),
        value_added_millions=Decimal(va),
        vintage_published_date=vintage,
    )


@pytest.mark.unit
class TestUpsertWriter:
    """T019 acceptance criteria."""

    def test_first_write_inserts_all_records(self, transient_session: Session) -> None:
        records = [_make_record(1, 2010), _make_record(2, 2010), _make_record(1, 2011)]
        stats = upsert_national_records(transient_session, records)
        assert stats.rows_inserted == 3
        assert stats.rows_superseded == 0
        assert stats.rows_unchanged == 0

        count = transient_session.execute(
            select(FactBEANationalIndustry).where(
                FactBEANationalIndustry.bea_industry_id.is_not(None)
            )
        ).all()
        assert len(count) == 3

    def test_second_write_same_vintage_is_unchanged(self, transient_session: Session) -> None:
        v = date(2025, 1, 1)
        records = [_make_record(1, 2010, vintage=v), _make_record(2, 2010, vintage=v)]
        upsert_national_records(transient_session, records)
        stats2 = upsert_national_records(transient_session, records)
        assert stats2.rows_inserted == 0
        assert stats2.rows_superseded == 0
        assert stats2.rows_unchanged == 2

    def test_newer_vintage_supersedes_older(self, transient_session: Session) -> None:
        old = date(2021, 1, 1)
        new = date(2023, 6, 1)
        upsert_national_records(transient_session, [_make_record(1, 2010, vintage=old)])
        stats2 = upsert_national_records(
            transient_session, [_make_record(1, 2010, go="2000", ii="800", va="1200", vintage=new)]
        )
        assert stats2.rows_superseded == 1
        assert stats2.rows_unchanged == 0
        assert stats2.rows_inserted == 0
        assert len(stats2.supersessions) == 1
        assert stats2.supersessions[0].old_vintage == old
        assert stats2.supersessions[0].new_vintage == new

        # Row was actually updated:
        row = transient_session.execute(
            select(FactBEANationalIndustry).where(
                FactBEANationalIndustry.bea_industry_id == 1,
                FactBEANationalIndustry.time_id == 100,
            )
        ).scalar_one()
        assert row.gross_output_millions == Decimal("2000")

    def test_older_vintage_does_not_overwrite(self, transient_session: Session) -> None:
        new = date(2023, 6, 1)
        old = date(2021, 1, 1)
        upsert_national_records(
            transient_session,
            [_make_record(1, 2010, go="2000", ii="800", va="1200", vintage=new)],
        )
        stats2 = upsert_national_records(
            transient_session,
            [_make_record(1, 2010, go="1000", ii="400", va="600", vintage=old)],
        )
        # Older-vintage row must be SKIPPED.
        assert stats2.rows_unchanged == 1
        assert stats2.rows_superseded == 0
        row = transient_session.execute(
            select(FactBEANationalIndustry).where(
                FactBEANationalIndustry.bea_industry_id == 1,
                FactBEANationalIndustry.time_id == 100,
            )
        ).scalar_one()
        # Original (newer-vintage) values preserved.
        assert row.gross_output_millions == Decimal("2000")
