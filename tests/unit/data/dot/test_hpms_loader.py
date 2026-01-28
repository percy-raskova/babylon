"""Unit tests for DOT HPMS loader."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from babylon.data.dot import DotHpmsLoader
from babylon.data.loader_base import LoaderConfig
from babylon.data.reference import schema as _schema  # noqa: F401
from babylon.data.reference.database import NormalizedBase
from babylon.data.reference.schema import DimCounty, DimState, FactHpmsRoadSegment


def _make_session() -> Session:
    from sqlalchemy import event

    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn: object, _connection_record: object) -> None:
        import sqlite3

        if isinstance(dbapi_conn, sqlite3.Connection):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    NormalizedBase.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    return session_factory()


def test_hpms_loader_ingests_basic_row(tmp_path: Path) -> None:
    session = _make_session()
    try:
        state = DimState(state_fips="01", state_name="Alabama", state_abbrev="AL")
        session.add(state)
        session.flush()
        county = DimCounty(
            fips="01081",
            state_id=state.state_id,
            county_fips="081",
            county_name="Lee County",
        )
        session.add(county)
        session.commit()

        csv_path = tmp_path / "hpms.csv"
        csv_path.write_text(
            "AADT,COUNTY_ID,StateID,ROUTE_ID,ROUTE_NUMBER,ROUTE_SIGNING,ROUTE_QUALIFIER,"
            "F_SYSTEM,FACILITY_TYPE,SPEED_LIMIT,THROUGH_LANES,LANE_WIDTH,SectionLength,"
            "NHS,NHFN,URBAN_ID,YEAR_RECORD,ShapeId,line\n"
            "5628,81,1,AL0000010000,431,1,3,3,2,55,2,12,0.006,1,0,4033,2024,349322813,"
            '"LINESTRING (0 0, 1 1)"\n',
            encoding="utf-8",
        )

        loader = DotHpmsLoader(LoaderConfig())
        stats = loader.load(session, reset=True, verbose=False, data_path=csv_path)

        assert stats.facts_loaded.get("hpms_road_segments") == 1
        row = session.execute(select(FactHpmsRoadSegment)).scalar_one()
        assert row.county_id == county.county_id
        assert row.aadt == 5628
        assert row.geometry_wkt == "LINESTRING (0 0, 1 1)"
    finally:
        session.close()
