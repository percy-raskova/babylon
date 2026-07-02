"""Spec-086 shared ORM helpers: in-memory reference-DB subset + dim seeds.

Plain functions (no pytest dependency) so both the unit conftest
(``tests/unit/reference/qcew/conftest.py``) and integration modules can
build identical fixture databases without conftest plugin gymnastics.
"""

from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from babylon.reference.database import NormalizedBase

QCEW_TABLES = [
    "dim_state",
    "dim_county",
    "dim_industry",
    "dim_ownership",
    "dim_time",
    "ingest_checkpoint",
    "fact_qcew_annual",
    "fact_qcew_county_rollup",
]

#: (state_fips, state_name, abbrev)
STATES = [("26", "Michigan", "MI"), ("46", "South Dakota", "SD"), ("09", "Connecticut", "CT")]

#: (fips, state_fips, name) — covers Wayne/Macomb (canonical scope), the
#: Shannon→Oglala Lakota identity pair, and a CT planning region (2024 codes).
COUNTIES = [
    ("26163", "26", "Wayne County"),
    ("26099", "26", "Macomb County"),
    ("46102", "46", "Oglala Lakota County"),
    ("46113", "46", "Shannon County"),
    ("09110", "09", "Capitol Planning Region"),
]

#: (naics_code, level) — a range-sector chain (31-33 → 336111/336112/336120,
#: incl. subsector 337) plus a plain-sector chain (54 → 541511/541512).
INDUSTRIES = [
    ("10", 0),
    ("31-33", 2),
    ("336", 3),
    ("3361", 4),
    ("33611", 5),
    ("336111", 6),
    ("336112", 6),
    ("33612", 5),
    ("336120", 6),
    ("337", 3),
    ("3371", 4),
    ("33711", 5),
    ("337110", 6),
    ("54", 2),
    ("541", 3),
    ("5415", 4),
    ("54151", 5),
    ("541511", 6),
    ("541512", 6),
]

#: (own_code, title, is_government, is_private)
OWNERSHIPS = [
    ("0", "Total Covered", 0, 0),
    ("1", "Federal Government", 1, 0),
    ("2", "State Government", 1, 0),
    ("3", "Local Government", 1, 0),
    ("5", "Private", 0, 1),
]

YEARS = [2010, 2015, 2024]


def create_qcew_engine(url: str = "sqlite:///:memory:") -> Engine:
    """Engine with the spec-086 table subset created from the ORM.

    Pass a file URL (``sqlite:///path``) when the database must survive a
    second connection (CLI end-to-end tests).
    """
    engine = create_engine(url)
    tables = [NormalizedBase.metadata.tables[name] for name in QCEW_TABLES]
    NormalizedBase.metadata.create_all(engine, tables=tables)
    return engine


def seed_qcew_dims(session: Session) -> None:
    """Seed the dimension rows every spec-086 fixture scenario relies on."""
    for i, (fips, name, abbrev) in enumerate(STATES, start=1):
        session.execute(
            text(
                "INSERT INTO dim_state (state_id, state_fips, state_name, state_abbrev)"
                f" VALUES ({i}, '{fips}', '{name}', '{abbrev}')"
            )
        )
    state_ids = {fips: i for i, (fips, _, _) in enumerate(STATES, start=1)}
    for i, (fips, state_fips, name) in enumerate(COUNTIES, start=1):
        session.execute(
            text(
                "INSERT INTO dim_county (county_id, fips, state_id, county_fips, county_name)"
                f" VALUES ({i}, '{fips}', {state_ids[state_fips]}, '{fips[2:]}', '{name}')"
            )
        )
    for i, (code, level) in enumerate(INDUSTRIES, start=1):
        session.execute(
            text(
                "INSERT INTO dim_industry (industry_id, naics_code, industry_title,"
                " naics_level, has_productivity_data, has_fred_data, has_qcew_data)"
                f" VALUES ({i}, '{code}', 'Industry {code}', {level}, 0, 0, 1)"
            )
        )
    for i, (own, title, gov, priv) in enumerate(OWNERSHIPS, start=1):
        session.execute(
            text(
                "INSERT INTO dim_ownership (ownership_id, own_code, own_title,"
                f" is_government, is_private) VALUES ({i}, '{own}', '{title}', {gov}, {priv})"
            )
        )
    for i, year in enumerate(YEARS, start=1):
        session.execute(
            text(f"INSERT INTO dim_time (time_id, year, is_annual) VALUES ({i}, {year}, 1)")
        )
    session.commit()
