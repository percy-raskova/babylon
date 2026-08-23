"""Guard frozen Rust migration vectors against the Python legacy sources."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest

_EXPORTER_PATH = Path(__file__).resolve().parents[3] / "tools/export_legacy_postgres_contract.py"
_SPEC = importlib.util.spec_from_file_location("export_legacy_postgres_contract", _EXPORTER_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("export_legacy_postgres_contract.py failed import-spec resolution")
exporter = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(exporter)


def test_frozen_rust_legacy_postgres_fixtures_match_python_sources() -> None:
    """The committed vectors must exactly match the source DDL sequences."""
    root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [sys.executable, str(root / "tools/export_legacy_postgres_contract.py"), "--check"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_overfull_migration_directory_stops_at_its_sentinel_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Directory discovery must reject at its bounded sentinel entry."""

    def entries() -> Iterator[Path]:
        for index in range(exporter.MAX_MIGRATION_DIRECTORY_ENTRIES + 1):
            yield Path(f"{index:04d}_migration.sql")
        raise AssertionError("migration discovery consumed beyond its sentinel entry")

    def iterdir(_: Path) -> Iterator[Path]:
        return entries()

    monkeypatch.setattr(Path, "iterdir", iterdir)
    with pytest.raises(RuntimeError, match=r"migration directory: entries exceed"):
        exporter._numbered_migrations()


def test_oversized_migration_source_is_rejected_before_an_unbounded_read(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Migration source bytes must be capped before text decoding."""
    migration_dir = tmp_path / "babylon/persistence/migrations"
    migration_dir.mkdir(parents=True)
    (migration_dir / "0010_oversized.sql").write_bytes(b"x" * (exporter.MAX_BYTES + 1))
    monkeypatch.setattr(exporter, "SRC", tmp_path)

    def read_text(*_: object, **__: object) -> str:
        raise AssertionError("unbounded read_text() must not run")

    monkeypatch.setattr(Path, "read_text", read_text)
    with pytest.raises(ValueError, match=r"migrations-0010-0044: framed bytes exceed"):
        exporter._numbered_migrations()


def test_oversized_fixture_is_rejected_without_an_unbounded_read(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A stale oversized fixture must fail from metadata alone."""
    fixture = tmp_path / "fixture.bin"
    fixture.write_bytes(b"x")

    read_bytes_called = False

    def stat(_: Path, **__: object) -> SimpleNamespace:
        return SimpleNamespace(st_size=exporter.MAX_BYTES + 1)

    def read_bytes(*_: object, **__: object) -> bytes:
        nonlocal read_bytes_called
        read_bytes_called = True
        return b"expected"

    monkeypatch.setattr(Path, "stat", stat)
    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    assert not exporter._check(fixture, b"expected")
    assert not read_bytes_called


def test_numbered_migrations_preserve_unique_missing_and_duplicate_results(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Each required migration version has exactly one bounded source file."""
    migration_dir = tmp_path / "babylon/persistence/migrations"
    migration_dir.mkdir(parents=True)
    for version in range(10, 45):
        (migration_dir / f"{version:04d}_one.sql").write_text(str(version), encoding="utf-8")

    monkeypatch.setattr(exporter, "SRC", tmp_path)
    assert exporter._numbered_migrations() == [str(version) for version in range(10, 45)]

    (migration_dir / "0014_one.sql").unlink()
    with pytest.raises(RuntimeError, match=r"migration 0014: expected one file, found 0"):
        exporter._numbered_migrations()

    (migration_dir / "0014_one.sql").write_text("14", encoding="utf-8")
    (migration_dir / "0014_two.sql").write_text("duplicate", encoding="utf-8")
    with pytest.raises(RuntimeError, match=r"migration 0014: expected one file, found 2"):
        exporter._numbered_migrations()
