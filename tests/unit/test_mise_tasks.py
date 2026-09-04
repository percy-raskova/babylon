"""Unit tests for mise task discoverability (T034a, spec-064 SC-005)."""

from __future__ import annotations

import json
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
RUST_NEXTEST_CONFIG = REPOSITORY_ROOT / "rust" / ".config" / "nextest.toml"
SIMULATION_TASKS_TOML = REPOSITORY_ROOT / ".mise" / "tasks" / "simulation.toml"
ANALYSIS_TASKS_TOML = REPOSITORY_ROOT / ".mise" / "tasks" / "analysis.toml"
DEVTOOLS_TASKS_TOML = REPOSITORY_ROOT / ".mise" / "tasks" / "devtools.toml"

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


def _pre_commit_config() -> dict[str, object]:
    """Return the parsed repository pre-commit configuration."""
    config = yaml.safe_load(PRE_COMMIT_CONFIG.read_text())
    assert isinstance(config, dict)
    return config


def _tracked_paths() -> tuple[str, ...]:
    """Return the tracked path inventory used by hook-selector contracts."""
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
    )
    return tuple(path.decode() for path in completed.stdout.split(b"\0") if path)


@pytest.fixture(scope="module")
def mise_tasks() -> dict[str, dict[str, object]]:
    """Return Mise's resolved task graph, including split task files."""
    completed = subprocess.run(  # noqa: S603 -- repository-owned Mise config
        ["mise", "tasks", "--json"],  # noqa: S607 -- pinned project tool
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return {task["name"]: task for task in json.loads(completed.stdout)}


def _task_run(task: dict[str, object]) -> str:
    run = task["run"]
    assert isinstance(run, list)
    assert all(isinstance(command, str) for command in run)
    return "\n".join(run)


@pytest.mark.skipif(not MISE_TOML.exists(), reason=".mise.toml not present")
class TestMiseTaskDiscoverability:
    """Required mise tasks exist with non-empty descriptions."""

    def test_split_task_files_use_pinned_mise_compatible_includes(self) -> None:
        """This repository's declared Mise floor requires explicit task files."""
        config = tomllib.loads(MISE_TOML.read_text())

        assert config["min_version"] == "2025.11.7"
        assert config["task_config"]["includes"] == [
            ".mise/tasks/analysis.toml",
            ".mise/tasks/devtools.toml",
            ".mise/tasks/simulation.toml",
        ]

    def test_sim_e2e_michigan_declared_in_split_config(
        self, mise_tasks: dict[str, dict[str, object]]
    ) -> None:
        task = mise_tasks["sim:e2e-michigan"]
        assert Path(str(task["source"])).resolve() == SIMULATION_TASKS_TOML
        assert len(str(task["description"]).split()) >= 4
        assert "babylon-runtime run --ticks 520" in _task_run(task)

    def test_foreground_e2e_is_fresh_while_background_and_probe_share_stable_purpose(
        self, mise_tasks: dict[str, dict[str, object]]
    ) -> None:
        foreground = _task_run(mise_tasks["sim:e2e-michigan"])
        assert (
            "python3 tools/devtools/worktree_campaign.py --purpose michigan-e2e --fresh"
            in foreground
        )
        assert 'export BABYLON_CAMPAIGN_ID="$sim_campaign_id"' in foreground

        for name in ("sim:e2e-bg", "sim:status", "sim:probe"):
            run = _task_run(mise_tasks[name])
            assert "python3 tools/devtools/worktree_campaign.py --purpose michigan-e2e" in run
            assert "--fresh" not in run
            assert 'export BABYLON_CAMPAIGN_ID="$sim_campaign_id"' in run

        background = _task_run(mise_tasks["sim:e2e-bg"])
        status = _task_run(mise_tasks["sim:status"])
        assert "printf '%s\\n' \"$sim_campaign_id\" > .sim-pids/e2e.campaign-id" in background
        assert 'stored_campaign_id="$(cat .sim-pids/e2e.campaign-id)"' in status
        assert 'BABYLON_CAMPAIGN_ID="$stored_campaign_id" python3' in status
        assert 'elif [ "$background_is_live" = true ]; then' in status
        assert "background campaign identity is missing" in status

    def test_status_uses_recorded_campaign_after_background_process_exits(
        self,
        mise_tasks: dict[str, dict[str, object]],
        tmp_path: Path,
    ) -> None:
        campaign_id = "f487f780-9bc8-4a48-9fc4-da1d0f08943f"
        pid_dir = tmp_path / ".sim-pids"
        pid_dir.mkdir()
        (pid_dir / "e2e.campaign-id").write_text(f"{campaign_id}\n")

        capture_path = tmp_path / "runtime-campaign.txt"
        fake_bin = tmp_path / "bin"
        fake_bin.mkdir()
        fake_python = fake_bin / "python3"
        fake_python.write_text("#!/bin/sh\nprintf '%s\\n' \"${BABYLON_CAMPAIGN_ID-}\"\n")
        fake_python.chmod(0o755)
        fake_runtime = fake_bin / "babylon-runtime"
        fake_runtime.write_text(
            '#!/bin/sh\nprintf \'%s\\n\' "${BABYLON_CAMPAIGN_ID-}" > "$STATUS_CAPTURE"\n'
        )
        fake_runtime.chmod(0o755)

        environment = os.environ.copy()
        environment["PATH"] = f"{fake_bin}:{environment['PATH']}"
        environment["STATUS_CAPTURE"] = str(capture_path)
        completed = subprocess.run(  # noqa: S603 -- repository-owned task script
            ["bash", "-euo", "pipefail", "-c", _task_run(mise_tasks["sim:status"])],
            cwd=tmp_path,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )

        assert "(no daemonized run)" in completed.stdout
        assert capture_path.read_text() == f"{campaign_id}\n"

    def test_one_shot_pg_tasks_use_fresh_campaigns_unless_explicitly_configured(
        self, mise_tasks: dict[str, dict[str, object]]
    ) -> None:
        expected_purposes = {
            "qa:michigan-rollover-smoke": "qa-michigan-rollover-smoke",
            "test:int-pg": "test-int-pg",
        }
        for name, purpose in expected_purposes.items():
            run = _task_run(mise_tasks[name])
            assert (
                f"python3 tools/devtools/worktree_campaign.py --purpose {purpose} --fresh"
            ) in run
            assert "export BABYLON_CAMPAIGN_ID=" in run

    def test_sim_namespace_has_only_rust_authority_tasks(
        self, mise_tasks: dict[str, dict[str, object]]
    ) -> None:
        sim_tasks = {name: task for name, task in mise_tasks.items() if name.startswith("sim:")}
        assert set(sim_tasks) == {
            "sim:archive",
            "sim:dossier-demo",
            "sim:e2e-bg",
            "sim:e2e-michigan",
            "sim:probe",
            "sim:report",
            "sim:status",
            "sim:watch",
        }
        for task in sim_tasks.values():
            run = _task_run(task)
            assert "uv run" not in run
            assert "-m babylon" not in run
            assert "babylon.engine" not in run

    def test_frozen_python_and_analysis_tasks_are_renamed_without_aliases(
        self, mise_tasks: dict[str, dict[str, object]]
    ) -> None:
        retired = {
            "sim:run",
            "sim:sweep",
            "sim:monte-carlo",
            "sim:archived",
            "test:optimization",
        }
        assert not retired & mise_tasks.keys()
        assert not {name for name in mise_tasks if name.startswith("tune:")}
        expected_analysis = {
            "reference:python-smoke",
            "analysis:sweep",
            "analysis:sweep-custom",
            "analysis:landscape",
            "analysis:monte-carlo",
            "analysis:optuna",
            "analysis:dashboard",
            "analysis:campaign",
            "analysis:sensitivity",
            "analysis:morris",
            "analysis:sobol",
            "analysis:test",
        }
        assert expected_analysis <= mise_tasks.keys()
        for name in expected_analysis:
            assert Path(str(mise_tasks[name]["source"])).resolve() == ANALYSIS_TASKS_TOML
        assert "uv run python -m babylon" in _task_run(mise_tasks["reference:python-smoke"])
        assert "tools.devtools.sim_analysis sweep" in _task_run(mise_tasks["analysis:sweep"])
        assert "tools.devtools.sim_analysis monte-carlo" in _task_run(
            mise_tasks["analysis:monte-carlo"]
        )
        assert _task_run(mise_tasks["analysis:dashboard"]) == (
            'uv run optuna-dashboard "sqlite:///${usage_database}"'
        )
        assert 'help="Local SQLite database path" default="optuna.db"' in str(
            mise_tasks["analysis:dashboard"]["usage"]
        )
        campaign = mise_tasks["analysis:campaign"]
        assert 'default="weekly"' in str(campaign["usage"])
        assert _task_run(campaign) == (
            "uv run python -m tools.devtools.reference_analysis_campaign "
            '--profile "${usage_profile}"'
        )
        optuna_usage = mise_tasks["analysis:optuna"]["usage"]
        assert isinstance(optuna_usage, str)
        assert "maximum 384 at the fixed 5200-tick horizon" in optuna_usage
        for name in ("analysis:sensitivity", "analysis:morris", "analysis:sobol"):
            run = _task_run(mise_tasks[name])
            assert '--param-names "${usage_parameters}"' in run
            assert "--max-ticks ${usage_ticks}" in run
            assert 'default="economy.base_subsistence,' in str(mise_tasks[name]["usage"])
        combined = _task_run(mise_tasks["analysis:sensitivity"])
        assert "sensitivity --method both" in combined
        assert "--trajectories ${usage_trajectories}" in combined
        assert "--samples ${usage_samples}" in combined

    def test_sim_report_builds_only_runtime_and_uses_stdlib_reporter(
        self, mise_tasks: dict[str, dict[str, object]]
    ) -> None:
        task = mise_tasks["sim:report"]
        run = _task_run(task)
        assert 'arg "[ticks]" help="Number of Rust simulation ticks" default="60"' in str(
            task["usage"]
        )
        assert 'arg "[timeout_seconds]" help="Runtime wall-clock timeout" default="3000"' in str(
            task["usage"]
        )
        assert (
            'arg "[database_scope]" help="Database attribution scope: shared or exclusive" '
            'default="shared"'
        ) in str(task["usage"])
        assert (
            "CARGO_BUILD_JOBS=4 cargo build -p babylon-persistence --bin babylon-runtime --locked"
        ) in run
        assert "cargo build --workspace" not in run
        assert (
            "python3 tools/devtools/sim_report.py "
            "--runtime rust/target/debug/babylon-runtime "
            "--ticks ${usage_ticks} --timeout-seconds ${usage_timeout_seconds} "
            "--database-scope ${usage_database_scope} "
            "--output-root reports/sim-runs"
        ) in run
        assert "export BABYLON_RUNTIME_DSN=" in run
        assert "uv run" not in run

    def test_dev_doctor_uses_plain_python(self, mise_tasks: dict[str, dict[str, object]]) -> None:
        task = mise_tasks["dev:doctor"]
        assert Path(str(task["source"])).resolve() == DEVTOOLS_TASKS_TOML
        assert _task_run(task) == "python3 tools/devtools/doctor.py"


def test_docs_rebuild_serializes_clean_before_build(
    mise_tasks: dict[str, dict[str, object]],
) -> None:
    """Clean must finish before build rather than racing as sibling dependencies."""
    rebuild = mise_tasks["docs:rebuild"]
    assert rebuild["depends"] == ["docs:clean"]
    assert _task_run(rebuild) == "mise run docs:build"


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


def test_pre_commit_installs_every_governed_git_hook_by_default() -> None:
    """A plain install must not silently omit commit-message or push gates."""
    config = _pre_commit_config()
    tasks = _tasks()

    assert config["default_install_hook_types"] == [
        "pre-commit",
        "commit-msg",
        "pre-push",
    ]
    assert tasks["hooks"]["run"] == "uv run --frozen pre-commit install"
    assert "uv run --frozen pre-commit install" in str(tasks["setup"]["run"])


def test_pre_commit_file_selectors_resolve_to_tracked_paths() -> None:
    """A deleted estate must not leave hooks that can never execute."""
    config = _pre_commit_config()
    tracked_paths = _tracked_paths()
    unresolved: list[str] = []

    for repository in config["repos"]:
        for hook in repository["hooks"]:
            pattern = hook.get("files")
            if pattern is not None and not any(
                re.search(str(pattern), path) for path in tracked_paths
            ):
                unresolved.append(str(hook["id"]))

    assert unresolved == []


def test_pre_commit_uses_meta_guards_against_future_selector_drift() -> None:
    """Pre-commit's own cheap policy checks must guard the hook estate."""
    config = _pre_commit_config()
    meta = next(repository for repository in config["repos"] if repository["repo"] == "meta")

    assert [hook["id"] for hook in meta["hooks"]] == [
        "check-hooks-apply",
        "check-useless-excludes",
    ]


def test_retired_cockpit_hooks_are_absent() -> None:
    """The Bevy cutover must not leave an inert Node hook environment."""
    config = _pre_commit_config()
    hooks = [hook for repository in config["repos"] for hook in repository["hooks"]]

    assert {
        "prettier",
        "cockpit-typecheck",
        "cockpit-eslint",
        "cockpit-vitest",
    }.isdisjoint(str(hook["id"]) for hook in hooks)
    for hook in hooks:
        executable_policy = " ".join(
            str(hook.get(field, "")) for field in ("entry", "files", "exclude")
        )
        assert "src/frontend" not in executable_policy


def test_rust_pre_push_uses_exact_push_range_for_every_gate_definition() -> None:
    """The local hook must preserve deleted paths without fetching or building docs."""
    hook = _local_hook("rust-full-gate")
    entry = str(hook["entry"])

    assert entry == "python3 tools/run_pre_push_gate.py rust-full-gate"
    assert hook["pass_filenames"] is False
    assert hook["always_run"] is True
    assert "files" not in hook
    assert "git fetch" not in entry
    assert "mise run ci:rust" not in entry


def test_bsl_repo_sentinels_cover_their_non_rust_inputs() -> None:
    """Governance and retired-authority changes must run the Rust-owned sentinels."""
    hook = _local_hook("bsl-repo-sentinels")

    assert hook["entry"] == "python3 tools/run_pre_push_gate.py bsl-repo-sentinels"
    assert hook["pass_filenames"] is False
    assert hook["always_run"] is True
    assert "files" not in hook
    assert hook["stages"] == ["pre-push"]


def test_rust_gate_is_single_pass_with_explicit_repo_sentinel_exception() -> None:
    """The canonical gate has one non-doctest pass plus the preserved doctest proof."""
    script = str(_tasks()["rust:check-no-docs"]["run"])
    commands = [line for line in script.splitlines() if line.startswith("cargo ")]

    assert [line for line in commands if line.startswith("cargo clippy ")] == [
        "cargo clippy --workspace --all-targets --locked -- "
        "-D warnings -D clippy::cognitive_complexity"
    ]
    assert "python3 ../tools/rust_test_report.py run --profile ci --workspace" in script
    assert [line for line in commands if line.startswith("cargo test ")] == [
        "cargo test --workspace --doc --locked"
    ]
    assert [line for line in commands if line.startswith("cargo run ")] == [
        "cargo run -p bsl-lint --locked -- all"
    ]


def test_rust_reporter_tasks_and_nextest_profile_are_agent_first() -> None:
    """Rust reports must be complete on failure without flooding agent context."""
    tasks = _tasks()
    assert {
        "rust:test",
        "rust:test:q",
        "rust:test:failed",
        "rust:test:summary",
        "rust:test:inventory",
        "rust:test:install-tools",
        "rust:coverage",
    } <= set(tasks)

    config = tomllib.loads(RUST_NEXTEST_CONFIG.read_text())
    assert config["nextest-version"]["required"] == "0.9.143"
    profile = config["profile"]["ci"]
    assert profile["fail-fast"] is False
    assert profile["retries"] == 0
    assert profile["failure-output"] == "final"
    assert profile["success-output"] == "never"
    assert profile["status-level"] == "fail"
    assert profile["final-status-level"] == "slow"
    assert profile["slow-timeout"] == "60s"
    assert profile["junit"] == {
        "path": "junit.xml",
        "report-name": "babylon-rust",
        "store-success-output": False,
        "store-failure-output": True,
        "report-skipped": "ignored",
    }

    assert "--version 0.9.143 cargo-nextest" in str(tasks["rust:test:install-tools"]["run"])
    assert "--version 0.9.0 cargo-llvm-cov" in str(tasks["rust:test:install-tools"]["run"])
    install_script = str(tasks["rust:test:install-tools"]["run"])
    assert "rust/rust-toolchain.toml" in install_script
    assert 'rustup component add --toolchain "$CHANNEL" llvm-tools-preview' in install_script
    assert "rust_test_report.py summarize" in str(tasks["rust:test:summary"]["run"])
    assert "rust_test_report.py rerun-failed" in str(tasks["rust:test:failed"]["run"])


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
        "success() && steps.cargo-cache-size.outputs.within-bound == 'true' && "
        "steps.cargo-cache.outputs.cache-hit != 'true'"
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


# The play task's Archive sweep loop is executed by mise under a POSIX `sh`
# (dash on the dev host), where the glob negation class is `[!0-9]`; the
# bashism `[^0-9]` parses empty there and the loop broke after one sweep with
# pages still pending (PER-318 live-fire finding, 2026-09-04).
_PLAY_SWEEP_LOOP_BEGIN = "for sweep in 1 2 3 4 5 6 7 8; do"
_PLAY_SWEEP_LINE = (
    "Archive worker sweep complete; verified_tick=1; deferred=0; applied=0; "
    "already_consumed=0; paged={paged}."
)


def _play_run_script() -> str:
    """Return the play task's run script as one string."""
    run = _tasks()["play"]["run"]
    if isinstance(run, list):
        return "\n".join(str(command) for command in run)
    return str(run)


def _play_sweep_loop_block() -> str:
    """Extract the verbatim `for sweep ... done` block from the play task."""
    script = _play_run_script()
    begin = script.index(_PLAY_SWEEP_LOOP_BEGIN)
    block = []
    for line in script[begin:].splitlines():
        block.append(line)
        if line.strip() == "done":
            return "\n".join(block)
    raise AssertionError("play sweep loop has no closing `done`")


_STUB_RUNTIME = """\
#!/bin/sh
# Stub `babylon-runtime`: shift one scripted `--once` report per archive-worker
# call. A PATH stub is used because POSIX function names cannot contain "-".
[ "$1" = "archive-worker" ] || exit 0
sed -n '1p' "$PLAY_SWEEP_FIXTURE"
sed -n '2,$p' "$PLAY_SWEEP_FIXTURE" > "$PLAY_SWEEP_FIXTURE.shifted"
mv "$PLAY_SWEEP_FIXTURE.shifted" "$PLAY_SWEEP_FIXTURE"
"""


def _run_sweep_loop_under_posix_sh(outputs: list[str]) -> subprocess.CompletedProcess[str]:
    """Execute the real loop block under `/bin/sh` with a stubbed runtime.

    The stub shifts one scripted `--once` report line per archive-worker call,
    so the test exercises the task's actual parse and break logic instead of
    a hand-copied replica.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        fixture = Path(tmp) / "sweep_outputs.txt"
        fixture.write_text("".join(f"{line}\n" for line in outputs))
        stub_bin = Path(tmp) / "bin"
        stub_bin.mkdir()
        (stub_bin / "babylon-runtime").write_text(_STUB_RUNTIME)
        (stub_bin / "babylon-runtime").chmod(0o755)
        script = Path(tmp) / "sweep_loop.sh"
        script.write_text(_play_sweep_loop_block())
        env = {
            **os.environ,
            "PATH": f"{stub_bin}{os.pathsep}{os.environ.get('PATH', '')}",
            "PLAY_SWEEP_FIXTURE": str(fixture),
        }
        return subprocess.run(  # noqa: S603 -- generated script, pinned interpreter
            ["/bin/sh", str(script)],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )


def _sweep_lines(result: subprocess.CompletedProcess[str]) -> list[str]:
    return [line for line in result.stdout.splitlines() if "paged=" in line]


@pytest.mark.skipif(not MISE_TOML.exists(), reason=".mise.toml not present")
class TestPlaySweepLoopUnderPosixSh:
    """The play drain loop parses `paged=N.` under dash semantics, not bash."""

    def test_loop_uses_the_posix_negated_glob_class(self) -> None:
        """`[^0-9]` is a bashism; dash reads it as a literal class member."""
        assert "[!0-9]" in _play_sweep_loop_block()
        assert "[^0-9]" not in _play_run_script()

    def test_paged_parse_survives_the_trailing_period_under_posix_sh(self) -> None:
        """A mid-drain report (`paged=2.`) must not settle the loop early.

        Regression: under dash the bashism parsed empty, `${paged:-0}` became
        0, and the loop broke after the first sweep with pages still pending.
        """
        result = _run_sweep_loop_under_posix_sh(
            [_PLAY_SWEEP_LINE.format(paged=2), _PLAY_SWEEP_LINE.format(paged=0)]
        )
        assert result.returncode == 0, result.stderr
        lines = _sweep_lines(result)
        assert len(lines) == 2, f"loop must run both sweeps, got: {lines}"
        assert lines[0].endswith("paged=2.")

    def test_loop_breaks_immediately_on_a_settled_first_sweep(self) -> None:
        result = _run_sweep_loop_under_posix_sh([_PLAY_SWEEP_LINE.format(paged=0)])
        assert result.returncode == 0, result.stderr
        assert len(_sweep_lines(result)) == 1

    def test_loop_refuses_to_launch_when_the_drain_never_settles(self) -> None:
        result = _run_sweep_loop_under_posix_sh([_PLAY_SWEEP_LINE.format(paged=2)] * 8)
        assert result.returncode == 1
        assert "still paged" in result.stderr
