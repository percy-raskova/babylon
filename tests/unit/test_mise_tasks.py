"""Unit tests for mise task discoverability (T034a, spec-064 SC-005)."""

from __future__ import annotations

import os
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MISE_TOML = REPOSITORY_ROOT / ".mise.toml"
PRE_COMMIT_CONFIG = REPOSITORY_ROOT / ".pre-commit-config.yaml"
CI_WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"

HOSTED_STATIC_TASKS = [
    "check:hygiene",
    "check:dynamic-linking-fence",
    "check:sentinels-static",
    "check:surface",
    "lint:check",
    "format:check",
    "lint:imports",
    "typecheck",
    "check:lock",
]


def _tasks() -> dict[str, dict[str, object]]:
    """Return the repository's parsed Mise task table."""
    return tomllib.loads(MISE_TOML.read_text())["tasks"]


def _dependency_closure(task_name: str) -> set[str]:
    """Return every task reachable from ``task_name`` through ``depends``."""
    tasks = _tasks()
    pending = [task_name]
    closure: set[str] = set()
    while pending:
        current = pending.pop()
        if current in closure:
            continue
        closure.add(current)
        pending.extend(str(name) for name in tasks[current].get("depends", []))
    return closure


def _local_hook(hook_id: str) -> dict[str, object]:
    """Return one repository-local pre-commit hook by ID."""
    config = yaml.safe_load(PRE_COMMIT_CONFIG.read_text())
    return next(
        hook
        for repository in config["repos"]
        if repository["repo"] == "local"
        for hook in repository["hooks"]
        if hook["id"] == hook_id
    )


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

    def test_sim_e2e_michigan_invokes_rust_runtime(self) -> None:
        block = self._e2e_block()
        assert "babylon-runtime run --ticks 520" in block
        assert "babylon.engine.headless_runner" not in block


@pytest.mark.skipif(not MISE_TOML.exists(), reason=".mise.toml not present")
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


def test_check_is_non_mutating_and_keeps_dynamic_probes_explicit() -> None:
    """The canonical check must never rewrite source or require local data."""
    tasks = _tasks()

    assert tasks["check"]["depends"] == [
        "check:static",
        "check:governance-mass",
        "check:adr-catalog",
        "test:unit",
    ]
    assert {"lint", "format", "data:doctor", "check:catalog"}.isdisjoint(
        _dependency_closure("check")
    )
    assert tasks["check:full-local"]["depends"] == [
        "check",
        "data:doctor",
        "check:catalog",
    ]


def test_hosted_fast_gate_and_local_static_gate_share_tasks() -> None:
    """Local and hosted static validation must execute the same Mise leaves."""
    workflow = yaml.safe_load(CI_WORKFLOW.read_text())
    commands = [
        step["run"].removeprefix("mise run ")
        for step in workflow["jobs"]["fast-gate"]["steps"]
        if isinstance(step.get("run"), str) and step["run"].startswith("mise run ")
    ]

    assert _tasks()["check:static"]["depends"] == HOSTED_STATIC_TASKS
    assert commands == HOSTED_STATIC_TASKS


def test_fixing_is_explicit_and_sequential() -> None:
    """Mutation belongs to an explicit task, never a verification aggregate."""
    tasks = _tasks()

    assert tasks["check:quick"]["depends"] == ["lint:check", "format:check", "typecheck"]
    assert tasks["lint"]["run"] == "uv run ruff check . --fix"
    assert tasks["format"]["run"] == "uv run ruff format ."
    assert str(tasks["fix"]["run"]).splitlines() == [
        "set -e",
        "mise run lint",
        "mise run format",
    ]


def test_rust_pre_push_uses_no_docs_gate_for_every_gate_definition() -> None:
    """The local hook must obey the no-documentation rule and see task changes."""
    entry = str(_local_hook("rust-full-gate")["entry"])

    assert "mise run rust:check-no-docs" in entry
    assert "mise run ci:rust" not in entry
    assert (
        'git diff --name-only "${base}..HEAD" -- rust/ .mise.toml .pre-commit-config.yaml' in entry
    )
    assert "git status --porcelain -- rust/ .mise.toml .pre-commit-config.yaml" in entry
