"""Spec-100 T003: additive ORM schema for the county-exposure loader.

Asserts the spec-100 additions to :mod:`babylon.reference.schema`:

- ``FactCountyExposureByExternal`` — PK ``(time_id, external_country_id,
  county_id)``, ``weight`` Float NOT NULL. The materialized
  ``county_exposure_by_external`` map consumed by
  :mod:`babylon.engine.systems.phi_distribution`.
- ``FactBilateralTradeAnnual`` — PK ``(time_id, country_id)``, USD-millions
  import/export/total columns.

House pattern: in-memory SQLite engine, ``create_all`` over an explicit table
subset (see ``tests/unit/reference/qcew/test_schema_086.py``).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from babylon.reference.database import NormalizedBase
from babylon.reference.schema import (
    FactBilateralTradeAnnual,
    FactCountyExposureByExternal,
)

pytestmark = [pytest.mark.unit, pytest.mark.ledger]

_TABLE_SUBSET = [
    "dim_state",
    "dim_county",
    "dim_country",
    "dim_time",
    "fact_county_exposure_by_external",
    "fact_bilateral_trade_annual",
]


@pytest.fixture()
def engine_100() -> Engine:
    """In-memory engine with the spec-100 table subset (dims + both facts)."""
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
            "INSERT INTO dim_country (country_id, cty_code, country_name, is_region)"
            " VALUES (1, '16', 'Asia', 1)"
        )
    )
    session.execute(text("INSERT INTO dim_time (time_id, year, is_annual) VALUES (28, 2024, 1)"))


class TestFactCountyExposureByExternal:
    """FR-005/FR-006: the exposure map persisted at year × bloc × county."""

    def test_table_name_and_primary_key(self) -> None:
        assert FactCountyExposureByExternal.__tablename__ == "fact_county_exposure_by_external"
        table = NormalizedBase.metadata.tables["fact_county_exposure_by_external"]
        pk_columns = set(table.primary_key.columns.keys())
        assert pk_columns == {"time_id", "external_country_id", "county_id"}

    def test_weight_column_not_nullable(self) -> None:
        column = FactCountyExposureByExternal.__table__.columns["weight"]
        assert column.nullable is False

    def test_round_trip_weight_row(self, engine_100: Engine) -> None:
        with Session(engine_100) as session:
            _seed_dims(session)
            session.add(
                FactCountyExposureByExternal(
                    time_id=28,
                    external_country_id=1,
                    county_id=1,
                    weight=0.375,
                )
            )
            session.commit()
            row = session.execute(select(FactCountyExposureByExternal)).scalar_one()
            assert row.weight == pytest.approx(0.375)
            assert row.external_country_id == 1

    def test_physical_pk_enforced(self, engine_100: Engine) -> None:
        inspector = inspect(engine_100)
        pk = inspector.get_pk_constraint("fact_county_exposure_by_external")
        assert set(pk["constrained_columns"]) == {
            "time_id",
            "external_country_id",
            "county_id",
        }


class TestFactBilateralTradeAnnual:
    """FR-009: bloc-year USD trade totals persisted at year × country."""

    def test_table_name_and_primary_key(self) -> None:
        assert FactBilateralTradeAnnual.__tablename__ == "fact_bilateral_trade_annual"
        table = NormalizedBase.metadata.tables["fact_bilateral_trade_annual"]
        assert set(table.primary_key.columns.keys()) == {"time_id", "country_id"}

    def test_columns_match_data_model(self) -> None:
        table = NormalizedBase.metadata.tables["fact_bilateral_trade_annual"]
        assert {
            "time_id",
            "country_id",
            "imports_usd_millions",
            "exports_usd_millions",
            "total_trade_usd_millions",
        } <= set(table.columns.keys())

    def test_round_trip_trade_row(self, engine_100: Engine) -> None:
        with Session(engine_100) as session:
            _seed_dims(session)
            session.add(
                FactBilateralTradeAnnual(
                    time_id=28,
                    country_id=1,
                    imports_usd_millions=Decimal("123456.78"),
                    exports_usd_millions=Decimal("87654.32"),
                    total_trade_usd_millions=Decimal("211111.10"),
                )
            )
            session.commit()
            row = session.execute(select(FactBilateralTradeAnnual)).scalar_one()
            assert row.imports_usd_millions == Decimal("123456.78")
            assert row.total_trade_usd_millions == Decimal("211111.10")
