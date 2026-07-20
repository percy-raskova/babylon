"""Behavioral contract for the baseline-ceremony gate (§6.5 provenance & ceremony).

Owner ruling 2026-07-20: the ceremony doctrine's home is CLAUDE.md + CI teeth,
not a constitutional amendment. The gate (``tools/check_baseline_ceremony.py``)
mechanizes Constitution III.7's "regenerate the baselines *and say so*": any
commit that touches ``tests/baselines/**`` must machine-checkably declare its
ceremony via a ``Baselines: blessed(<ceremony-slug>)`` trailer.

Two enforcement modes, both covered here against synthetic git repos:

a. ``--commit-msg-file`` — the local commit-msg hook (staged paths vs message);
b. ``--range A..B``      — the CI leg (every non-merge commit in a PR range).

The synthetic-violation tests are the mutation proof that each mode detects
its violation class (Constitution III.11 — Loud Failure).
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

from check_baseline_ceremony import (  # type: ignore[import-not-found]  # noqa: E402
    check_commit_msg,
    check_range,
    main,
    message_declares_ceremony,
    touches_baselines,
)

pytestmark = pytest.mark.unit


def _git(repo: Path, *args: str) -> str:
    """Run git in ``repo``, failing the test loudly on nonzero exit."""
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "gate-test@example.invalid")
    _git(repo, "config", "user.name", "Gate Test")
    (repo / "README.md").write_text("seed\n")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "chore: seed")
    return repo


def _commit_file(repo: Path, rel_path: str, content: str, message: str) -> str:
    target = repo / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    _git(repo, "add", rel_path)
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


BLESSED = "test(baselines): ceremony\n\nBaselines: blessed(unit-proof-ceremony)"


class TestTrailerGrammar:
    """The declaration is a strict trailer line, not a vibe."""

    def test_valid_trailer_accepted(self) -> None:
        assert message_declares_ceremony(BLESSED)

    def test_missing_trailer_rejected(self) -> None:
        assert not message_declares_ceremony("test(baselines): regen\n\nno declaration")

    def test_empty_slug_rejected(self) -> None:
        assert not message_declares_ceremony("msg\n\nBaselines: blessed()")

    def test_uppercase_slug_rejected(self) -> None:
        assert not message_declares_ceremony("msg\n\nBaselines: blessed(LOUD)")

    def test_untouched_is_not_a_blessing(self) -> None:
        assert not message_declares_ceremony("msg\n\nBaselines: untouched")

    def test_mid_line_mention_rejected(self) -> None:
        assert not message_declares_ceremony("msg\n\nsee Baselines: blessed(x) above")

    def test_comment_line_rejected(self) -> None:
        # git strips '#' comment lines at cleanup; the gate must not accept a
        # declaration that only exists inside one.
        assert not message_declares_ceremony("msg\n\n# Baselines: blessed(sneaky)")


class TestPathScope:
    def test_baseline_path_in_scope(self) -> None:
        assert touches_baselines(["tests/baselines/glut.json"])

    def test_dense_subdir_in_scope(self) -> None:
        assert touches_baselines(["tests/baselines/dense/glut/C001_wealth.csv"])

    def test_non_baseline_paths_out_of_scope(self) -> None:
        assert not touches_baselines(["src/babylon/engine/simulation_engine.py"])

    def test_lookalike_prefix_out_of_scope(self) -> None:
        assert not touches_baselines(["tests/baselines_archive/old.json"])


class TestCommitMsgMode:
    """Local hook: staged baseline paths demand a declared message."""

    def test_staged_baseline_without_trailer_is_violation(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path)
        (repo / "tests/baselines").mkdir(parents=True)
        (repo / "tests/baselines/glut.json").write_text("{}\n")
        _git(repo, "add", "tests/baselines/glut.json")
        msg = tmp_path / "msg.txt"
        msg.write_text("test(baselines): regen without declaration\n")
        violations = check_commit_msg(msg, repo)
        assert violations, "undeclared staged baseline change must be flagged"

    def test_staged_baseline_with_trailer_is_clean(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path)
        (repo / "tests/baselines").mkdir(parents=True)
        (repo / "tests/baselines/glut.json").write_text("{}\n")
        _git(repo, "add", "tests/baselines/glut.json")
        msg = tmp_path / "msg.txt"
        msg.write_text(BLESSED + "\n")
        assert check_commit_msg(msg, repo) == []

    def test_non_baseline_staging_needs_no_trailer(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path)
        (repo / "notes.md").write_text("plain\n")
        _git(repo, "add", "notes.md")
        msg = tmp_path / "msg.txt"
        msg.write_text("docs: plain change\n")
        assert check_commit_msg(msg, repo) == []


class TestRangeMode:
    """CI leg: every non-merge commit in the range is inspected."""

    def test_undeclared_commit_flagged_by_sha(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path)
        base = _git(repo, "rev-parse", "HEAD")
        sha = _commit_file(
            repo, "tests/baselines/glut.json", "{}\n", "test(baselines): silent drift"
        )
        violations = check_range(f"{base}..HEAD", repo)
        assert len(violations) == 1
        assert sha[:12] in violations[0] or sha in violations[0]

    def test_declared_commit_is_clean(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path)
        base = _git(repo, "rev-parse", "HEAD")
        _commit_file(repo, "tests/baselines/glut.json", "{}\n", BLESSED)
        assert check_range(f"{base}..HEAD", repo) == []

    def test_non_baseline_commits_ignored(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path)
        base = _git(repo, "rev-parse", "HEAD")
        _commit_file(repo, "src/module.py", "x = 1\n", "feat: unrelated")
        assert check_range(f"{base}..HEAD", repo) == []

    def test_merge_commits_skipped(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path)
        base = _git(repo, "rev-parse", "HEAD")
        _git(repo, "switch", "-c", "side")
        _commit_file(repo, "tests/baselines/glut.json", "{}\n", BLESSED)
        _git(repo, "switch", "main")
        _commit_file(repo, "other.md", "y\n", "docs: mainline drift")
        _git(repo, "merge", "--no-ff", "-m", "merge side into main", "side")
        # The merge commit itself carries no trailer; only its non-merge
        # parents are inspected, and the side commit is blessed.
        assert check_range(f"{base}..HEAD", repo) == []

    def test_multiple_undeclared_commits_all_reported(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path)
        base = _git(repo, "rev-parse", "HEAD")
        _commit_file(repo, "tests/baselines/a.json", "{}\n", "test(baselines): one")
        _commit_file(repo, "tests/baselines/b.json", "{}\n", "test(baselines): two")
        assert len(check_range(f"{base}..HEAD", repo)) == 2


class TestMainCli:
    def test_range_mode_exit_codes(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path)
        base = _git(repo, "rev-parse", "HEAD")
        _commit_file(repo, "tests/baselines/glut.json", "{}\n", "test(baselines): silent")
        assert main(["--range", f"{base}..HEAD", "--repo", str(repo)]) == 1
        _git(repo, "commit", "--amend", "-m", BLESSED)
        assert main(["--range", f"{base}..HEAD", "--repo", str(repo)]) == 0

    def test_commit_msg_mode_exit_codes(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path)
        (repo / "tests/baselines").mkdir(parents=True)
        (repo / "tests/baselines/glut.json").write_text("{}\n")
        _git(repo, "add", "tests/baselines/glut.json")
        msg = tmp_path / "msg.txt"
        msg.write_text("test(baselines): silent\n")
        assert main(["--commit-msg-file", str(msg), "--repo", str(repo)]) == 1
        msg.write_text(BLESSED + "\n")
        assert main(["--commit-msg-file", str(msg), "--repo", str(repo)]) == 0

    def test_no_mode_is_usage_error(self) -> None:
        assert main([]) == 2

    def test_bad_range_is_git_error(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path)
        assert main(["--range", "nonexistent..HEAD", "--repo", str(repo)]) == 2
