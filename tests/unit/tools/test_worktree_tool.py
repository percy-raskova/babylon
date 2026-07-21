"""Behavioral contract for the ``wt:new``/``wt:done`` primitives (git-doctrine item 2).

``tools/worktree_tool.py`` implements two subcommands:

* ``new NAME`` — validates ``NAME`` against a strict slug grammar, then
  creates ``.claude/worktrees/NAME`` on a fresh ``wt/NAME`` branch off the
  invoking checkout's current branch.
* ``done NAME`` — refuses to retire the worktree unless it is clean and its
  branch is fully merged into the current branch (``--force`` bypasses
  both checks), then removes the worktree and deletes the branch.

Two test tiers:

1. **Slug validation table** — pure unit tests over :func:`is_valid_slug`.
2. **Integration-ish subprocess tests** — a scratch git repo built fresh
   under ``tmp_path`` (never the real repo) exercises ``new``/``done`` end
   to end via ``subprocess``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

# Mirror the import path used by tools/*.py and its existing unit tests
# (see tests/unit/tools/test_repo_hygiene.py).
TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from worktree_tool import SLUG_MAX_LEN, is_valid_slug  # type: ignore[import-not-found]  # noqa: E402

TOOL_PATH = TOOLS_DIR / "worktree_tool.py"


@pytest.mark.unit
class TestSlugValidation:
    """Table-driven proof of the strict worktree-slug grammar."""

    @pytest.mark.parametrize(
        "name",
        [
            "wo-9",
            "feature-x",
            "a",
            "abc123",
            "already-hyphenated-slug",
            "9",
            "a" * SLUG_MAX_LEN,
        ],
    )
    def test_valid_slugs_accepted(self, name: str) -> None:
        assert is_valid_slug(name) is True

    @pytest.mark.parametrize(
        "name",
        [
            "",
            "Feature-X",  # uppercase
            "feature_x",  # underscore
            "feature/x",  # slash
            "-feature",  # leading hyphen
            "feature-",  # trailing hyphen
            "feature--x",  # double hyphen
            "feat ure",  # whitespace
            "a" * (SLUG_MAX_LEN + 1),  # too long
            "féature",  # non-ascii
        ],
    )
    def test_invalid_slugs_rejected(self, name: str) -> None:
        assert is_valid_slug(name) is False


def _run_git(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    )
    return result


def _run_tool(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL_PATH), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def scratch_repo(tmp_path: Path) -> Path:
    """Build a throwaway git repo (never the real one) with one commit."""
    repo = tmp_path / "scratch-repo"
    repo.mkdir()
    _run_git(["init", "-b", "main"], cwd=repo)
    _run_git(["config", "user.email", "test@example.invalid"], cwd=repo)
    _run_git(["config", "user.name", "Test User"], cwd=repo)
    (repo / "README.md").write_text("scratch\n")
    _run_git(["add", "README.md"], cwd=repo)
    _run_git(["commit", "-m", "initial commit"], cwd=repo)
    return repo


@pytest.mark.unit
class TestNewSubcommand:
    """``new NAME`` end-to-end against a scratch repo."""

    def test_new_rejects_invalid_slug(self, scratch_repo: Path) -> None:
        result = _run_tool(["new", "Bad_Name"], cwd=scratch_repo)
        assert result.returncode == 1
        assert "invalid worktree name" in result.stderr

    def test_new_creates_worktree_on_wt_branch(self, scratch_repo: Path) -> None:
        result = _run_tool(["new", "my-feature"], cwd=scratch_repo)
        assert result.returncode == 0, result.stderr

        worktree_path = scratch_repo / ".claude" / "worktrees" / "my-feature"
        assert worktree_path.is_dir()

        branch = _run_git(
            ["rev-parse", "--abbrev-ref", "HEAD"], cwd=worktree_path
        ).stdout.strip()
        assert branch == "wt/my-feature"

        # Usage recipe surfaced.
        assert "PYTHONPATH" in result.stdout
        assert "pytest" in result.stdout
        assert "lint-imports" in result.stdout

    def test_new_refuses_existing_worktree_path(self, scratch_repo: Path) -> None:
        first = _run_tool(["new", "dup-slug"], cwd=scratch_repo)
        assert first.returncode == 0, first.stderr

        second = _run_tool(["new", "dup-slug"], cwd=scratch_repo)
        assert second.returncode == 1
        assert "already exists" in second.stderr


@pytest.mark.unit
class TestDoneSubcommand:
    """``done NAME`` end-to-end against a scratch repo."""

    def test_done_refuses_nonexistent_worktree(self, scratch_repo: Path) -> None:
        result = _run_tool(["done", "never-existed"], cwd=scratch_repo)
        assert result.returncode == 1
        assert "no such worktree" in result.stderr

    def test_done_refuses_unmerged_branch(self, scratch_repo: Path) -> None:
        created = _run_tool(["new", "unmerged-feature"], cwd=scratch_repo)
        assert created.returncode == 0, created.stderr

        worktree_path = scratch_repo / ".claude" / "worktrees" / "unmerged-feature"
        # Commit something on the worktree branch so it diverges from main.
        (worktree_path / "new-file.txt").write_text("data\n")
        _run_git(["add", "new-file.txt"], cwd=worktree_path)
        _run_git(["commit", "-m", "unmerged work"], cwd=worktree_path)

        result = _run_tool(["done", "unmerged-feature"], cwd=scratch_repo)
        assert result.returncode == 1
        assert "not fully merged" in result.stderr
        # Worktree must still be there — refusal did not remove it.
        assert worktree_path.is_dir()

    def test_done_refuses_dirty_worktree(self, scratch_repo: Path) -> None:
        created = _run_tool(["new", "dirty-feature"], cwd=scratch_repo)
        assert created.returncode == 0, created.stderr

        worktree_path = scratch_repo / ".claude" / "worktrees" / "dirty-feature"
        (worktree_path / "untracked.txt").write_text("oops\n")

        result = _run_tool(["done", "dirty-feature"], cwd=scratch_repo)
        assert result.returncode == 1
        assert "not clean" in result.stderr
        assert worktree_path.is_dir()

    def test_done_removes_clean_merged_worktree(self, scratch_repo: Path) -> None:
        created = _run_tool(["new", "clean-feature"], cwd=scratch_repo)
        assert created.returncode == 0, created.stderr
        worktree_path = scratch_repo / ".claude" / "worktrees" / "clean-feature"
        assert worktree_path.is_dir()

        # Branch has no new commits beyond main => trivially merged, clean.
        result = _run_tool(["done", "clean-feature"], cwd=scratch_repo)
        assert result.returncode == 0, result.stderr
        assert not worktree_path.exists()

        branches = _run_git(["branch", "--list", "wt/clean-feature"], cwd=scratch_repo)
        assert branches.stdout.strip() == ""

    def test_done_force_removes_dirty_unmerged_worktree(self, scratch_repo: Path) -> None:
        created = _run_tool(["new", "force-feature"], cwd=scratch_repo)
        assert created.returncode == 0, created.stderr
        worktree_path = scratch_repo / ".claude" / "worktrees" / "force-feature"

        (worktree_path / "new-file.txt").write_text("data\n")
        _run_git(["add", "new-file.txt"], cwd=worktree_path)
        _run_git(["commit", "-m", "unmerged work"], cwd=worktree_path)
        (worktree_path / "scratch.txt").write_text("dirty\n")

        result = _run_tool(["done", "force-feature", "--force"], cwd=scratch_repo)
        assert result.returncode == 0, result.stderr
        assert not worktree_path.exists()
