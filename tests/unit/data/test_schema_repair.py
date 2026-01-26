"""Unit tests for schema repair helpers."""

from __future__ import annotations

from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, inspect

from babylon.data.reference import schema_check


def _create_sqlite_engine():
    """Create SQLite engine with FK enforcement."""
    from sqlalchemy import event

    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn: object, _connection_record: object) -> None:
        import sqlite3

        if isinstance(dbapi_conn, sqlite3.Connection):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def test_apply_schema_repairs_adds_table() -> None:
    engine = _create_sqlite_engine()
    metadata = MetaData()
    table = Table("test_add_table", metadata, Column("id", Integer))

    report = schema_check.apply_schema_repairs(
        engine=engine,
        diffs=[("add_table", table)],
        recheck=False,
    )

    inspector = inspect(engine)
    assert "test_add_table" in inspector.get_table_names()
    assert report.applied


def test_apply_schema_repairs_adds_table_with_autoincrement() -> None:
    """Test adding table with autoincrement primary key (SQLite-compatible)."""
    engine = _create_sqlite_engine()
    metadata = MetaData()
    table = Table(
        "test_autoinc_table",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("label", String()),
    )

    report = schema_check.apply_schema_repairs(
        engine=engine,
        diffs=[("add_table", table)],
        recheck=False,
    )

    inspector = inspect(engine)
    assert "test_autoinc_table" in inspector.get_table_names()
    assert report.applied


def test_apply_schema_repairs_adds_column() -> None:
    engine = _create_sqlite_engine()
    metadata = MetaData()
    _table = Table("test_add_column", metadata, Column("id", Integer))
    metadata.create_all(engine)

    new_column = Column("new_col", String())

    report = schema_check.apply_schema_repairs(
        engine=engine,
        diffs=[("add_column", "test_add_column", new_column)],
        recheck=False,
    )

    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("test_add_column")}
    assert "new_col" in columns
    assert report.applied


def test_apply_schema_repairs_leaves_blocking_diffs() -> None:
    engine = _create_sqlite_engine()
    metadata = MetaData()
    Table("test_blocking", metadata, Column("id", Integer))
    metadata.create_all(engine)

    report = schema_check.apply_schema_repairs(
        engine=engine,
        diffs=[("remove_column", "test_blocking", Column("id", Integer))],
        recheck=False,
    )

    assert report.applied == []
    assert report.remaining_diffs
