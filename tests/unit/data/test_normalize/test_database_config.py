from __future__ import annotations

import importlib
import os
from pathlib import Path

import babylon.data.normalize.database as database


def _reload_with_env(value: str | None) -> None:
    if value is None:
        os.environ.pop("BABYLON_NORMALIZED_DB_PATH", None)
    else:
        os.environ["BABYLON_NORMALIZED_DB_PATH"] = value
    importlib.reload(database)


def test_normalized_db_path_override_absolute(monkeypatch, tmp_path: Path) -> None:
    original = os.environ.get("BABYLON_NORMALIZED_DB_PATH")
    override_path = tmp_path / "custom.sqlite"

    try:
        monkeypatch.setenv("BABYLON_NORMALIZED_DB_PATH", str(override_path))
        db_module = importlib.reload(database)
        assert override_path == db_module.NORMALIZED_DB_PATH
    finally:
        _reload_with_env(original)


def test_normalized_db_path_override_relative(monkeypatch) -> None:
    original = os.environ.get("BABYLON_NORMALIZED_DB_PATH")
    relative_path = Path("data/sqlite/custom.sqlite")

    try:
        monkeypatch.setenv("BABYLON_NORMALIZED_DB_PATH", str(relative_path))
        db_module = importlib.reload(database)
        assert db_module._REPO_ROOT / relative_path == db_module.NORMALIZED_DB_PATH
    finally:
        _reload_with_env(original)
