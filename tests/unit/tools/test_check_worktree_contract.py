"""Diagnostic contract for the worktree environment checker."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from check_worktree_contract import (  # type: ignore[import-not-found]  # noqa: E402
    check_lock_unmodified,
)


def _run_git(arguments: list[str], *, cwd: Path) -> None:
    subprocess.run(["git", *arguments], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.mark.unit
def test_dirty_lock_guidance_scopes_frozen_commands_and_unsets_lock_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A dirty lock tells users which commands may use frozen mode."""
    _run_git(["init", "-b", "main"], cwd=tmp_path)
    _run_git(["config", "user.email", "test@example.invalid"], cwd=tmp_path)
    _run_git(["config", "user.name", "Test User"], cwd=tmp_path)
    lock_path = tmp_path / "uv.lock"
    lock_path.write_text("version = 1\n")
    _run_git(["add", "uv.lock"], cwd=tmp_path)
    _run_git(["commit", "-m", "initial lock"], cwd=tmp_path)
    lock_path.write_text("version = 2\n")
    monkeypatch.chdir(tmp_path)

    message = check_lock_unmodified()

    assert message is not None
    assert (
        "use `UV_FROZEN=1` only for `uv sync` or `uv run`; "
        "`uv lock --check` must run with `UV_FROZEN` unset"
    ) in message
