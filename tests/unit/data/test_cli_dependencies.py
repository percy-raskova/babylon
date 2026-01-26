"""Unit tests for CLI loader dependency handling."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from babylon.data.cli import _check_loader_prereqs, _resolve_loader_order
from babylon.data.loader_base import LoaderConfig
from babylon.data.reference import schema as _schema  # noqa: F401
from babylon.data.reference.database import NormalizedBase


def _make_session():
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


def test_resolve_loader_order_sorts_dependencies() -> None:
    ordered = _resolve_loader_order(["qcew", "census"])
    assert ordered == ["census", "qcew"]


def test_check_loader_prereqs_reports_missing_census_dims() -> None:
    session = _make_session()
    try:
        errors = _check_loader_prereqs("qcew", session, LoaderConfig())
    finally:
        session.close()

    assert errors
    assert any("census" in error.lower() for error in errors)


def test_check_loader_prereqs_reports_missing_geography() -> None:
    session = _make_session()
    try:
        errors = _check_loader_prereqs("cfs", session, LoaderConfig())
    finally:
        session.close()

    assert errors
    assert any("geography" in error.lower() for error in errors)
