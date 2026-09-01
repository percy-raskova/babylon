"""Unit tests for mise task discoverability (T034a, spec-064 SC-005)."""

from __future__ import annotations

import os
import re
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

PEDANTIC_RUST_PACKAGES = [
    "babylon-kernel",
    "babylon-persistence",
    "babylon-bsl",
    "babylon-graph",
    "babylon-ls",
    "babylon-client",
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


def test_check_freezes_every_uv_verification_leaf() -> None:
    """Verification must report lock drift before any uv command can repair it."""
    tasks = _tasks()
    unfrozen_tasks = [
        task_name
        for task_name in sorted(_dependency_closure("check"))
        if re.search(r"\buv run(?! --frozen\b)", str(tasks[task_name].get("run", "")))
    ]

    assert unfrozen_tasks == []
    assert tasks["check:lock"]["run"] == "env -u UV_FROZEN uv lock --check"


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


def test_rust_gate_is_single_pass_with_explicit_repo_sentinel_exception() -> None:
    """The canonical gate must not rerun package tests or Clippy passes."""
    script = str(_tasks()["rust:check-no-docs"]["run"])
    commands = [line for line in script.splitlines() if line.startswith("cargo ")]

    assert [line for line in commands if line.startswith("cargo clippy ")] == [
        "cargo clippy --workspace --all-targets --locked -- "
        "-D warnings -D clippy::cognitive_complexity"
    ]
    assert [line for line in commands if line.startswith("cargo test ")] == [
        "cargo test --workspace --locked"
    ]
    assert [line for line in commands if line.startswith("cargo run ")] == [
        "cargo run -p bsl-lint --locked -- all"
    ]


def test_single_clippy_pass_preserves_the_existing_pedantic_package_boundary() -> None:
    """Manifest lint policy must preserve every formerly scoped pedantic pass."""
    workspace = tomllib.loads((REPOSITORY_ROOT / "rust" / "Cargo.toml").read_text())

    assert workspace["workspace"]["lints"]["clippy"]["pedantic"] == {
        "level": "warn",
        "priority": -1,
    }
    opted_in = []
    for manifest_path in sorted((REPOSITORY_ROOT / "rust" / "crates").glob("*/Cargo.toml")):
        manifest = tomllib.loads(manifest_path.read_text())
        if manifest.get("lints") == {"workspace": True}:
            opted_in.append(manifest["package"]["name"])

    assert opted_in == sorted(PEDANTIC_RUST_PACKAGES)


def test_rust_cache_is_source_keyed_bounded_and_published_only_by_dev() -> None:
    """PRs may restore the cache, while only successful dev pushes may save it."""
    workflow = yaml.safe_load(CI_WORKFLOW.read_text())
    steps = workflow["jobs"]["rust-gate"]["steps"]
    restore = next(step for step in steps if step.get("name") == "Restore cargo cache")
    measure = next(step for step in steps if step.get("name") == "Measure cargo cache payload")
    save = next(step for step in steps if step.get("name") == "Publish trusted cargo cache")

    assert restore["id"] == "cargo-cache"
    assert restore["uses"].startswith("actions/cache/restore@")
    assert (
        "hashFiles('rust/**/*.rs', 'rust/**/Cargo.toml', '.mise.toml', "
        "'.github/workflows/ci.yml')" in restore["with"]["key"]
    )
    assert restore["with"]["restore-keys"].splitlines() == [
        "cargo-gate-${{ runner.os }}-v4-${{ "
        "hashFiles('rust/Cargo.lock', 'rust/rust-toolchain.toml') }}-"
    ]
    cache_paths = restore["with"]["path"].splitlines()
    assert cache_paths == save["with"]["path"].splitlines()
    assert "rust/target" not in cache_paths
    assert "rust/target/debug/incremental" not in cache_paths
    assert "rust/target/debug/deps/*.rlib" in cache_paths
    assert "rust/target/debug/deps/*.rmeta" in cache_paths
    assert "rust/target/debug/deps/*.so" in cache_paths
    assert "rust/target/doc" in cache_paths
    assert measure["id"] == "cargo-cache-size"
    assert "max_bytes=$((8 * 1024 * 1024 * 1024))" in measure["run"]
    assert "rust/target/debug/deps" in measure["run"]
    assert 'find "${find_roots[@]}" -maxdepth 1 -type f' in measure["run"]
    assert "cargo-cache exact_restore=" in measure["run"]
    assert "cargo-cache matched_key=" in measure["run"]
    assert "cargo-cache payload_bytes=" in measure["run"]
    assert "cargo-cache publication_bound_bytes=" in measure["run"]
    assert "cargo-cache within_publication_bound=" in measure["run"]
    assert save["uses"].startswith("actions/cache/save@")
    assert save["if"] == (
        "github.event_name == 'push' && github.ref == 'refs/heads/dev' && "
        "success() && steps.cargo-cache-size.outputs.within-bound == 'true'"
    )
    assert save["with"]["key"] == "${{ steps.cargo-cache.outputs.cache-primary-key }}"


def test_rustdoc_remains_hosted_and_blocking_after_single_pass_refactor() -> None:
    """The local no-doc gate stays separate from the hosted Rustdoc contract."""
    tasks = _tasks()
    ci_script = str(tasks["ci:rust"]["run"])
    workflow = yaml.safe_load(CI_WORKFLOW.read_text())
    rust_job = workflow["jobs"]["rust-gate"]
    hosted_step = next(
        step
        for step in rust_job["steps"]
        if step.get("name") == "Rust full gate (canonical ci:rust task)"
    )

    assert "mise run rust:check-no-docs" in ci_script
    assert "RUSTDOCFLAGS='-D warnings' cargo doc --workspace --no-deps --locked" in ci_script
    assert hosted_step["run"] == "mise run ci:rust"
    assert "continue-on-error" not in hosted_step
    assert "continue-on-error" not in rust_job
