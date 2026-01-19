"""Unit tests for normalized schema drift checks."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import Integer, String, Text

import babylon.data.normalize.schema_check as schema_check
from babylon.data.exceptions import SchemaCheckError


def test_types_equivalent_treats_text_and_string_as_same() -> None:
    assert schema_check._types_equivalent(Text(), String()) is True
    assert schema_check._types_equivalent(String(), Text()) is True


def test_types_equivalent_detects_string_length_mismatch() -> None:
    assert schema_check._types_equivalent(String(10), String(20)) is False


def test_types_equivalent_detects_non_string_difference() -> None:
    assert schema_check._types_equivalent(Integer(), String()) is False


def test_schema_check_reports_missing_database(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.duckdb"
    original_path = schema_check.NORMALIZED_DB_PATH
    schema_check.NORMALIZED_DB_PATH = missing_path

    try:
        with pytest.raises(SchemaCheckError) as exc_info:
            schema_check.check_normalized_schema()
        assert "not found" in str(exc_info.value).lower()
        assert exc_info.value.hint
        assert exc_info.value.details.get("path") == str(missing_path)
    finally:
        schema_check.NORMALIZED_DB_PATH = original_path


def test_schema_check_wraps_duckdb_impl_error(tmp_path: Path) -> None:
    db_path = tmp_path / "db.duckdb"
    db_path.touch()
    original_path = schema_check.NORMALIZED_DB_PATH
    schema_check.NORMALIZED_DB_PATH = db_path

    def _raise(_engine: object | None = None) -> list[object]:
        raise KeyError("duckdb")

    original_collect = schema_check.collect_schema_diffs
    schema_check.collect_schema_diffs = _raise

    try:
        with pytest.raises(SchemaCheckError) as exc_info:
            schema_check.check_normalized_schema()
        assert "duckdb" in str(exc_info.value).lower()
        assert exc_info.value.hint
        assert exc_info.value.details.get("dialect") == "duckdb"
    finally:
        schema_check.collect_schema_diffs = original_collect
        schema_check.NORMALIZED_DB_PATH = original_path


def test_schema_check_reports_drift(tmp_path: Path) -> None:
    db_path = tmp_path / "db.duckdb"
    db_path.touch()
    original_path = schema_check.NORMALIZED_DB_PATH
    schema_check.NORMALIZED_DB_PATH = db_path

    original_collect = schema_check.collect_schema_diffs
    schema_check.collect_schema_diffs = lambda _engine=None: [["diff"]]

    try:
        with pytest.raises(SchemaCheckError) as exc_info:
            schema_check.check_normalized_schema()
        assert "schema drift" in str(exc_info.value).lower()
        assert exc_info.value.hint
        assert exc_info.value.details.get("diffs")
    finally:
        schema_check.collect_schema_diffs = original_collect
        schema_check.NORMALIZED_DB_PATH = original_path


def test_schema_check_returns_message_on_success(tmp_path: Path) -> None:
    db_path = tmp_path / "db.duckdb"
    db_path.touch()
    original_path = schema_check.NORMALIZED_DB_PATH
    schema_check.NORMALIZED_DB_PATH = db_path

    original_collect = schema_check.collect_schema_diffs
    schema_check.collect_schema_diffs = lambda _engine=None: []

    try:
        message = schema_check.check_normalized_schema()
        assert "matches" in message.lower()
    finally:
        schema_check.collect_schema_diffs = original_collect
        schema_check.NORMALIZED_DB_PATH = original_path
