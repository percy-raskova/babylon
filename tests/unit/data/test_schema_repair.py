"""Unit tests for schema repair helpers."""

from __future__ import annotations

from sqlalchemy import Column, Integer, MetaData, Sequence, String, Table, create_engine, inspect

from babylon.data.normalize import schema_check


def test_apply_schema_repairs_adds_table() -> None:
    engine = create_engine("duckdb:///:memory:")
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


def test_apply_schema_repairs_adds_table_with_sequence() -> None:
    engine = create_engine("duckdb:///:memory:")
    metadata = MetaData()
    seq = Sequence("test_sequence_id_seq", metadata=metadata)
    table = Table(
        "test_seq_table",
        metadata,
        Column("id", Integer, server_default=seq.next_value(), primary_key=True),
        Column("label", String()),
    )

    report = schema_check.apply_schema_repairs(
        engine=engine,
        diffs=[("add_table", table)],
        recheck=False,
    )

    inspector = inspect(engine)
    assert "test_seq_table" in inspector.get_table_names()
    assert report.applied


def test_apply_schema_repairs_adds_column() -> None:
    engine = create_engine("duckdb:///:memory:")
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
    engine = create_engine("duckdb:///:memory:")
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
