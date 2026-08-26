"""Unit tests for mise task discoverability (T034a, spec-064 SC-005)."""

from __future__ import annotations

import os
import subprocess
import tomllib
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MISE_TOML = REPOSITORY_ROOT / ".mise.toml"


@pytest.mark.skipif(not MISE_TOML.exists(), reason=".mise.toml not present")
class TestMiseTaskDiscoverability:
    """Required mise tasks exist with non-empty descriptions."""

    def test_sim_e2e_michigan_declared(self) -> None:
        contents = MISE_TOML.read_text()
        assert '[tasks."sim:e2e-michigan"]' in contents

    def _e2e_block(self) -> str:
        contents = MISE_TOML.read_text()
        header = '[tasks."sim:e2e-michigan"]'
        block_start = contents.index(header) + len(header)
        # Block runs until the next "[tasks." heading.
        following = contents[block_start:]
        next_heading = following.find("\n[tasks.")
        return following[:next_heading] if next_heading != -1 else following

    def test_sim_e2e_michigan_has_description(self) -> None:
        block = self._e2e_block()
        match = [line for line in block.splitlines() if line.startswith("description = ")]
        assert match, "sim:e2e-michigan has no description"
        assert len(match[0].split()) >= 4

    def test_sim_e2e_michigan_invokes_runner_module(self) -> None:
        block = self._e2e_block()
        assert "babylon.engine.headless_runner" in block


def test_nix_task_forces_git_source_for_linked_worktree(tmp_path: Path) -> None:
    """The Nix task must not copy a linked worktree as an unfiltered path source."""
    task_script = tomllib.loads(MISE_TOML.read_text())["tasks"]["nix"]["run"]
    linked_worktree = tmp_path / "linked worktree"
    linked_worktree.mkdir()
    (linked_worktree / ".git").write_text("gitdir: /tmp/babylon-common/worktrees/test\n")

    capture_path = tmp_path / "nix-call.txt"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_nix = fake_bin / "nix"
    fake_nix.write_text(
        "#!/bin/sh\n"
        'printf \'%s\\n\' "${MISE_TRUSTED_CONFIG_PATHS-}" > "$NIX_TASK_CAPTURE"\n'
        'printf \'%s\\n\' "$@" >> "$NIX_TASK_CAPTURE"\n'
    )
    fake_nix.chmod(0o755)

    environment = os.environ.copy()
    environment["MISE_PROJECT_ROOT"] = str(linked_worktree)
    environment["NIX_TASK_CAPTURE"] = str(capture_path)
    environment["PATH"] = f"{fake_bin}{os.pathsep}{environment['PATH']}"
    subprocess.run(  # noqa: S603 -- repository-owned task script under contract
        ["bash", "-c", f'{task_script} "$@"', "nix-task-contract", "probe"],  # noqa: S607
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert capture_path.read_text().splitlines() == [
        str(linked_worktree),
        "develop",
        f"git+file://{linked_worktree}",
        "--command",
        "probe",
    ]
