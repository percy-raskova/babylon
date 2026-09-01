"""Contracts for deletion-aware pre-push gate selection."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from tools import run_pre_push_gate

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _git(repository: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def test_changed_paths_preserve_a_deleted_rust_input(tmp_path: Path) -> None:
    """The exact push range must retain paths that no longer exist at HEAD."""
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.name", "Pre-push Contract")
    _git(tmp_path, "config", "user.email", "pre-push@example.invalid")
    rust_file = tmp_path / "rust" / "deleted.rs"
    rust_file.parent.mkdir()
    rust_file.write_text("pub fn removed() {}\n")
    _git(tmp_path, "add", "rust/deleted.rs")
    _git(tmp_path, "commit", "-m", "test: add Rust input")
    old = _git(tmp_path, "rev-parse", "HEAD")

    rust_file.unlink()
    _git(tmp_path, "add", "rust/deleted.rs")
    _git(tmp_path, "commit", "-m", "test: delete Rust input")
    new = _git(tmp_path, "rev-parse", "HEAD")

    assert run_pre_push_gate.changed_paths(tmp_path, old, new) == frozenset({"rust/deleted.rs"})
    assert run_pre_push_gate.gate_applies(
        run_pre_push_gate.Gate.RUST_FULL,
        {"rust/deleted.rs"},
    )


def test_bsl_sentinel_selection_covers_every_retired_authority_path() -> None:
    """The local selector must match the Rust lint's complete closed list."""
    authority_source = (
        REPOSITORY_ROOT / "rust/crates/bsl-lint/src/rust_contract_authority.rs"
    ).read_text()
    retired_array = re.search(
        r"const RETIRED_PATHS: \[&str; \d+\] = \[(?P<body>.*?)\];",
        authority_source,
        flags=re.DOTALL,
    )
    assert retired_array is not None
    rust_paths = frozenset(re.findall(r'"([^"]+)"', retired_array.group("body")))

    assert rust_paths == run_pre_push_gate.BSL_RETIRED_AUTHORITY_PATHS
    for path in rust_paths:
        assert run_pre_push_gate.gate_applies(
            run_pre_push_gate.Gate.BSL_REPO_SENTINELS,
            {path},
        )


def test_classifier_changes_run_both_owned_gates() -> None:
    """The selector cannot change without exercising the gates it controls."""
    path = "tools/run_pre_push_gate.py"

    assert run_pre_push_gate.gate_applies(run_pre_push_gate.Gate.RUST_FULL, {path})
    assert run_pre_push_gate.gate_applies(
        run_pre_push_gate.Gate.BSL_REPO_SENTINELS,
        {path},
    )


def test_rust_reporter_changes_run_the_full_rust_gate() -> None:
    """The selected runner cannot change without exercising its owned gate."""
    assert run_pre_push_gate.gate_applies(
        run_pre_push_gate.Gate.RUST_FULL,
        {"tools/rust_test_report.py"},
    )
