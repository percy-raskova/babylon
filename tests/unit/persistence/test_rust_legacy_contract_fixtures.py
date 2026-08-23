"""Guard frozen Rust migration vectors against the Python legacy sources."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

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


def test_numbered_migration_discovery_reads_at_most_two_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Duplicate migration detection must stop before a third candidate."""

    def candidates() -> Iterator[Path]:
        yield Path("0010_first.sql")
        yield Path("0010_second.sql")
        raise AssertionError("migration discovery consumed a third candidate")

    def glob(_: Path, pattern: str) -> Iterator[Path]:
        assert pattern == "0010_*.sql"
        return candidates()

    monkeypatch.setattr(Path, "glob", glob)
    with pytest.raises(RuntimeError, match=r"migration 0010: expected one file, found 2"):
        exporter._numbered_migrations()
