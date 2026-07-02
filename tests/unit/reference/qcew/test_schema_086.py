"""Spec-086 T006/T007: ORM schema delta for the imputing QCEW loader.

Asserts the spec-086 additions to :mod:`babylon.reference.schema`:

- ``FactQcewAnnual.is_imputed`` — row-level provenance flag (research D4,
  data-model.md §1): Boolean, NOT NULL, server default 0.
- ``FactQcewCountyRollup`` — BLS-published county/ownership reconciliation
  constraints (research D5, data-model.md §2): PK
  ``(county_id, time_id, ownership_id)``.

House pattern: in-memory SQLite engine, ``create_all`` over an explicit
table subset (see ``tests/unit/reference/bea/test_national_writer_upsert.py``).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from babylon.reference.database import NormalizedBase
from babylon.reference.schema import FactQcewAnnual, FactQcewCountyRollup

pytestmark = [pytest.mark.unit, pytest.mark.ledger]

_TABLE_SUBSET = [
    "dim_state",
    "dim_county",
    "dim_industry",
    "dim_ownership",
    "dim_time",
    "fact_qcew_annual",
    "fact_qcew_county_rollup",
]


@pytest.fixture()
def engine_086() -> Engine:
    """In-memory engine with the QCEW table subset (dims + both facts)."""
    engine = create_engine("sqlite:///:memory:")
    tables = [NormalizedBase.metadata.tables[name] for name in _TABLE_SUBSET]
    NormalizedBase.metadata.create_all(engine, tables=tables)
    return engine


def _seed_dims(session: Session) -> None:
    session.execute(
        text(
            "INSERT INTO dim_state (state_id, state_fips, state_name, state_abbrev)"
            " VALUES (1, '26', 'Michigan', 'MI')"
        )
    )
    session.execute(
        text(
            "INSERT INTO dim_county (county_id, fips, state_id, county_fips, county_name)"
            " VALUES (1, '26163', 1, '163', 'Wayne County')"
        )
    )
    session.execute(
        text(
            "INSERT INTO dim_industry (industry_id, naics_code, industry_title, naics_level,"
            " has_productivity_data, has_fred_data, has_qcew_data)"
            " VALUES (1, '541511', 'Custom Computer Programming', 6, 0, 0, 1)"
        )
    )
    session.execute(
        text(
            "INSERT INTO dim_ownership (ownership_id, own_code, own_title,"
            " is_government, is_private)"
            " VALUES (1, '0', 'Total Covered', 0, 0), (2, '5', 'Private', 0, 1)"
        )
    )
    session.execute(text("INSERT INTO dim_time (time_id, year, is_annual) VALUES (14, 2010, 1)"))


class TestFactQcewAnnualIsImputed:
    """FR-005: every stored magnitude carries an observed/imputed marker."""

    def test_is_imputed_column_declared(self) -> None:
        column = FactQcewAnnual.__table__.columns["is_imputed"]
        assert column.nullable is False
        assert column.server_default is not None

    def test_is_imputed_defaults_to_false_on_insert(self, engine_086: Engine) -> None:
        with Session(engine_086) as session:
            _seed_dims(session)
            session.execute(
                text(
                    "INSERT INTO fact_qcew_annual"
                    " (county_id, industry_id, ownership_id, time_id,"
                    "  establishments, employment, total_wages_usd)"
                    " VALUES (1, 1, 2, 14, 7, 120, 4800000.00)"
                )
            )
            session.commit()
            row = session.execute(select(FactQcewAnnual)).scalar_one()
            assert row.is_imputed is False

    def test_is_imputed_true_round_trips(self, engine_086: Engine) -> None:
        with Session(engine_086) as session:
            _seed_dims(session)
            session.add(
                FactQcewAnnual(
                    county_id=1,
                    industry_id=1,
                    ownership_id=2,
                    time_id=14,
                    establishments=7,
                    employment=95,
                    total_wages_usd=Decimal("3100000.00"),
                    disclosure_code="N",
                    is_imputed=True,
                )
            )
            session.commit()
            row = session.execute(select(FactQcewAnnual)).scalar_one()
            assert row.is_imputed is True
            assert row.disclosure_code == "N"


class TestFactQcewCountyRollup:
    """Research D5: published constraints persisted at county × year × ownership."""

    def test_table_name_and_primary_key(self) -> None:
        assert FactQcewCountyRollup.__tablename__ == "fact_qcew_county_rollup"
        table = NormalizedBase.metadata.tables["fact_qcew_county_rollup"]
        pk_columns = set(table.primary_key.columns.keys())
        assert pk_columns == {"county_id", "time_id", "ownership_id"}

    def test_columns_match_data_model(self) -> None:
        table = NormalizedBase.metadata.tables["fact_qcew_county_rollup"]
        assert {
            "county_id",
            "time_id",
            "ownership_id",
            "establishments",
            "employment",
            "total_wages_usd",
            "disclosure_code",
            "is_imputed",
        } <= set(table.columns.keys())

    def test_round_trip_total_covered_row(self, engine_086: Engine) -> None:
        with Session(engine_086) as session:
            _seed_dims(session)
            session.add(
                FactQcewCountyRollup(
                    county_id=1,
                    time_id=14,
                    ownership_id=1,
                    establishments=31404,
                    employment=657150,
                    total_wages_usd=Decimal("33223962701.00"),
                )
            )
            session.commit()
            row = session.execute(select(FactQcewCountyRollup)).scalar_one()
            assert row.employment == 657150
            assert row.is_imputed is False

    def test_physical_pk_enforced(self, engine_086: Engine) -> None:
        inspector = inspect(engine_086)
        pk = inspector.get_pk_constraint("fact_qcew_county_rollup")
        assert set(pk["constrained_columns"]) == {"county_id", "time_id", "ownership_id"}
