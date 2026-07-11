"""Behavioral contract for the repo-hygiene gate (Program 14, Phase 0.5).

The gate (``tools/check_repo_hygiene.py``) enforces three invariants, loudly
(Constitution III.11):

a. every *tracked* top-level entry is on the fixed allowlist;
b. no tracked file matches the ignore rules (``.gitkeep`` convention exempt);
c. no tracked blob at HEAD exceeds 1 MiB unless it is an LFS pointer
   (pointers are ~130 bytes, so blob size alone distinguishes them) or a
   named exemption.

The synthetic-input tests are the red-phase/mutation proof that each check
actually detects its violation class; the integration test pins the repo's
own cleanliness from Phase 0 onward.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Mirror the import path used by tools/*.py and its existing unit tests
# (see tests/unit/tools/test_dense_goldens.py).
TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from check_repo_hygiene import (  # type: ignore[import-not-found]  # noqa: E402
    check_large_non_lfs_blobs,
    check_top_level_allowlist,
    check_tracked_but_ignored,
    main,
)


@pytest.mark.unit
class TestSyntheticViolations:
    """Each check must catch a planted violation (detection proof)."""

    def test_allowlist_violation_detected(self) -> None:
        tracked = ["src/babylon/__init__.py", "evil-dir/payload.py", "README.md"]
        violations = check_top_level_allowlist(tracked)
        assert violations == ["evil-dir"]

    def test_allowlist_rejects_unknown_top_level_file(self) -> None:
        tracked = ["stray-notes.txt", "src/babylon/__init__.py"]
        violations = check_top_level_allowlist(tracked)
        assert violations == ["stray-notes.txt"]

    def test_allowlist_clean_input_passes(self) -> None:
        tracked = ["src/a.py", "tests/b.py", "README.md", "pyproject.toml"]
        assert check_top_level_allowlist(tracked) == []

    def test_tracked_but_ignored_detected(self) -> None:
        ignored_tracked = ["reports/sim-runs/trace.csv"]
        violations = check_tracked_but_ignored(ignored_tracked)
        assert violations == ["reports/sim-runs/trace.csv"]

    def test_gitkeep_convention_exempt(self) -> None:
        ignored_tracked = ["results/.gitkeep", "logs/.gitkeep"]
        assert check_tracked_but_ignored(ignored_tracked) == []

    def test_large_blob_detected(self) -> None:
        # git ls-tree -r -l line shape: mode SP type SP oid SP size TAB path
        lines = [
            "100644 blob abc123                2097152\ttests/fat_fixture.json",
        ]
        violations = check_large_non_lfs_blobs(lines)
        assert violations == ["tests/fat_fixture.json (2097152 bytes)"]

    def test_lfs_pointer_passes(self) -> None:
        lines = [
            "100644 blob def456                    133\tsources/Capital-Volume-I.pdf",
        ]
        assert check_large_non_lfs_blobs(lines) == []

    def test_symlink_entries_are_skipped(self) -> None:
        # symlinks are mode 120000 with the target path as tiny blob content
        lines = ["120000 blob 0ddba11                    33\tdata/sqlite"]
        assert check_large_non_lfs_blobs(lines) == []


@pytest.mark.unit
class TestRepoIsClean:
    """The real repository satisfies the gate from Program 14 Phase 0 onward."""

    def test_gate_passes_on_this_repo(self) -> None:
        assert main() == 0
