"""Unit tests for the live|archive source abstraction (spec-099, no DB)."""

from __future__ import annotations

from pathlib import Path

import pytest

from observatory.sources import (
    Source,
    archive_dir,
    archive_root,
    parse_source,
    translate_placeholders,
)

pytestmark = pytest.mark.unit

_SID = "edf07b2e-ac2f-4ed7-990e-cadd159ed7b2"


class TestParseSource:
    def test_default_is_live(self) -> None:
        assert parse_source(None) is Source.LIVE
        assert parse_source("") is Source.LIVE

    def test_explicit_values(self) -> None:
        assert parse_source("live") is Source.LIVE
        assert parse_source("archive") is Source.ARCHIVE

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="source"):
            parse_source("cloud")


class TestArchivePaths:
    def test_root_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("BABYLON_ARCHIVE_ROOT", raising=False)
        assert archive_root() == Path("/media/user/data/babylon-archives")

    def test_root_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BABYLON_ARCHIVE_ROOT", "/tmp/arch")
        assert archive_root() == Path("/tmp/arch")

    def test_session_dir(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BABYLON_ARCHIVE_ROOT", "/tmp/arch")
        assert archive_dir(_SID) == Path("/tmp/arch") / _SID


class TestPlaceholderTranslation:
    def test_qmark_to_pyformat(self) -> None:
        # Shared raw-table SQL is authored with '?'; Postgres needs '%s'.
        sql = "SELECT * FROM tick_commit WHERE session_id = ? AND tick BETWEEN ? AND ?"
        assert translate_placeholders(sql) == (
            "SELECT * FROM tick_commit WHERE session_id = %s AND tick BETWEEN %s AND %s"
        )
