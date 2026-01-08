"""Unit tests for LODES crosswalk loader."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from babylon.data.loader_base import LoaderConfig
from babylon.data.lodes import LodesCrosswalkLoader
from babylon.data.normalize import schema as _schema  # noqa: F401
from babylon.data.normalize.database import NormalizedBase
from babylon.data.normalize.schema import BridgeLodesBlock, DimCounty, DimState


def _make_session() -> Session:
    engine = create_engine("duckdb:///:memory:")
    NormalizedBase.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    return session_factory()


def test_lodes_loader_creates_bridge_row(tmp_path: Path) -> None:
    session = _make_session()
    try:
        state = DimState(state_fips="01", state_name="Alabama", state_abbrev="AL")
        session.add(state)
        session.flush()
        county = DimCounty(
            fips="01001",
            state_id=state.state_id,
            county_fips="001",
            county_name="Autauga County",
        )
        session.add(county)
        session.commit()

        csv_path = tmp_path / "us_xwalk.csv"
        csv_path.write_text(
            "tabblk2020,st,cty,trct,bgrp,cbsa,zcta,blklatdd,blklondd\n"
            "010010201001000,01,001,020100,1,33860,36067,32.4706935,-86.4803993\n",
            encoding="utf-8",
        )

        loader = LodesCrosswalkLoader(LoaderConfig())
        stats = loader.load(session, reset=True, verbose=False, data_path=csv_path)

        assert stats.dimensions_loaded.get("lodes_blocks") == 1
        row = session.execute(select(BridgeLodesBlock)).scalar_one()
        assert row.block_geoid == "010010201001000"
        assert row.county_id == county.county_id
        assert row.cbsa_code == "33860"
    finally:
        session.close()
