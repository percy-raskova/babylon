"""Repository contract for Babylon's versioned Codex Rust host bundle.

Version 12 is Babylon's deployment; NNSims has not adopted its bytes.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
HOST_ROOT = REPO_ROOT / ".codex" / "host"
ADR_KEY = "ADR290_host_policy_v12"
ADR_PATH = REPO_ROOT / "ai" / "decisions" / f"{ADR_KEY}.yaml"
ADR_INDEX_PATH = REPO_ROOT / "ai" / "decisions" / "index.yaml"
POLICY_V12_SHA256 = {
    "cargo": "d1b3dc2124ab6ff0e064034629a6fadde0299b8a820082a80c082b11e66b63a0",
    "cargo-config.py": "efd74452a2c521dfc9a38810e75f6605fadfa987af66f547f3bc89b5077380e0",
    "install.sh": "c6408ed8592248b9aa9c9f4b08a4e3474db5b1ef4d87a8246eb6ac8e411683de",
    "policy.sh": "5a251a80414a41758fbba69b416412205d0f52be86cec3898de115c71ad39019",
    "systemd/codex-rust-babylon.slice": "db18f20360e1b04cf2cd3c2e1a60e6f72df4d23141028c8b0be1e5b533c05da8",
    "systemd/codex-rust-nnsims.slice": "ab60acb7148fb1effd1cf8c4370744a536cd6cc7cbf09eef5bdb0e3083a7d51a",
    "systemd/codex-rust.slice": "54958cafc2b9073b8bdeceda78511a738e70fd78e555e0746741ec8ead4f1171",
    "tests/installer-contract.sh": "38ad421118281cc2f3ad223f5a66ff1e908ec513024fd6f59bbe45d73e6d0001",
    "tests/policy-contract.sh": "724cd467b00c01f5839e82372c7864557ed8b4ecad1a7ecfb0d297b554ab551f",
}

_WORKTREE_ENV_FIXTURE = """\
# Test-only support for policy v11's inherited NNS worktree assertions.
codex_fixture_git_root="$(
  /usr/bin/env \
    -u GIT_DIR \
    -u GIT_WORK_TREE \
    -u GIT_COMMON_DIR \
    -u GIT_INDEX_FILE \
    -u GIT_OBJECT_DIRECTORY \
    -u GIT_ALTERNATE_OBJECT_DIRECTORIES \
    -u GIT_NAMESPACE \
    -u GIT_CEILING_DIRECTORIES \
    -u GIT_DISCOVERY_ACROSS_FILESYSTEM \
    -u GIT_CONFIG \
    -u GIT_CONFIG_COUNT \
    -u GIT_CONFIG_PARAMETERS \
    /usr/bin/git -C "$PWD" rev-parse --show-toplevel 2>/dev/null || true
)"
if [ -z "$codex_fixture_git_root" ] || [ ! -d "$codex_fixture_git_root" ]; then
  echo "cannot resolve the NNSims worktree root" >&2
  return 1
fi
if [ -n "${CODEX_WORKTREE_PATH:-}" ] &&
  [ "$(readlink -f -- "$CODEX_WORKTREE_PATH")" != "$(readlink -f -- "$codex_fixture_git_root")" ]; then
  echo "CODEX_WORKTREE_PATH does not name the active Git worktree" >&2
  return 1
fi
codex_fixture_suffix="$(printf '%s' "$codex_fixture_git_root" | sha256sum | cut -c 1-12)"
export COMPOSE_PROJECT_NAME="nnsims_codex_${codex_fixture_suffix}"
export POSTGRES_HOST_PORT=0
unset codex_fixture_git_root codex_fixture_suffix
"""

_SCCACHE_STATS_FIXTURE = """\
#!/bin/sh
# Test-only support for policy v11's inherited NNS cache assertions.
set -eu
script_path="$(readlink -f -- "$0")"
fixture_root="$(dirname -- "$(dirname -- "$(dirname -- "$script_path")")")"
. "$fixture_root/.codex/host/policy.sh"
cache_root="$(codex_rust_cache_root)"
printf 'cache=%s\n' "$(codex_rust_cache_dir nnsims "$cache_root")"
printf 'socket=%s\n' "$(codex_rust_server_socket nnsims "$cache_root")"
printf 'slice=%s\n' "$CODEX_RUST_NNSIMS_SLICE"
"""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bundle_mismatches(root: Path, pins: dict[str, str]) -> list[str]:
    return [
        relative
        for relative, expected in pins.items()
        if not (path := root / relative).is_file() or _sha256(path) != expected
    ]


def _yaml_mapping(path: Path) -> dict[str, object]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _live_policy_version() -> str:
    policy = (HOST_ROOT / "policy.sh").read_text(encoding="utf-8")
    versions = re.findall(r"^CODEX_RUST_HOST_POLICY_VERSION=([0-9]+)$", policy, re.MULTILINE)
    assert len(versions) == 1
    return versions[0]


@pytest.mark.unit
def test_policy_v12_bundle_matches_reviewed_bytes() -> None:
    """A changed bundle must receive review and a new policy version."""
    actual_files = {
        path.relative_to(HOST_ROOT).as_posix() for path in HOST_ROOT.rglob("*") if path.is_file()
    }
    assert actual_files == set(POLICY_V12_SHA256)
    assert _bundle_mismatches(HOST_ROOT, POLICY_V12_SHA256) == []


@pytest.mark.unit
def test_accepted_decision_and_index_name_the_live_policy_version() -> None:
    """A policy bump must update the accepted authority, not only executable bytes."""
    version = _live_policy_version()
    decision = _yaml_mapping(ADR_PATH)[ADR_KEY]
    assert isinstance(decision, dict)
    index = _yaml_mapping(ADR_INDEX_PATH)
    decisions = index["decisions"]
    assert isinstance(decisions, dict)

    title = "Babylon deploys host policy v12 for its current Rust bootstrap"
    assert version == "12"
    assert decision["title"] == title
    assert decisions[ADR_KEY] == {
        "title": title,
        "status": "accepted",
        "date": "2026-10-28",
        "file": ADR_PATH.name,
    }
    toolchain = tomllib.loads((REPO_ROOT / "rust/rust-toolchain.toml").read_text())
    channel = toolchain["toolchain"]["channel"]
    policy = (HOST_ROOT / "policy.sh").read_text()
    assert f"printf '%s\\n' +{channel}" in policy


@pytest.mark.unit
@pytest.mark.parametrize("contract", ("policy-contract.sh", "installer-contract.sh"))
def test_host_shell_contracts_pass(contract: str, tmp_path: Path) -> None:
    """Run the bundle hermetically without installing its NNS-only helpers in Babylon."""
    fixture_codex = tmp_path / ".codex"
    fixture_host = fixture_codex / "host"
    shutil.copytree(HOST_ROOT, fixture_host)
    fixture_scripts = fixture_codex / "scripts"
    fixture_scripts.mkdir()
    support = {
        "worktree-env.sh": _WORKTREE_ENV_FIXTURE,
        "sccache-stats.sh": _SCCACHE_STATS_FIXTURE,
    }
    for name, source in support.items():
        support_path = fixture_scripts / name
        support_path.write_text(source, encoding="utf-8")
        support_path.chmod(0o755)

    completed = subprocess.run(
        [str(fixture_host / "tests" / contract)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


@pytest.mark.unit
def test_bundle_identity_checker_detects_drift(tmp_path: Path) -> None:
    """Negative control: the identity check must bite on changed bytes."""
    policy = tmp_path / "policy.sh"
    policy.write_bytes(b"version=7\n")
    pin = {"policy.sh": _sha256(policy)}
    assert _bundle_mismatches(tmp_path, pin) == []

    policy.write_bytes(b"version=7 # divergent bytes\n")
    assert _bundle_mismatches(tmp_path, pin) == ["policy.sh"]


@pytest.mark.unit
def test_python_tooling_leaves_the_immutable_host_bundle_alone() -> None:
    """Repository lint and auto-fixes must not reinterpret installed policy bytes."""
    with (REPO_ROOT / "pyproject.toml").open("rb") as stream:
        ruff_excludes = tomllib.load(stream)["tool"]["ruff"]["exclude"]
    assert ".codex/host/" in ruff_excludes

    source = (REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    for hook_id in ("ruff", "ruff-format"):
        marker = f"      - id: {hook_id}\n"
        assert marker in source
        hook = source.split(marker, maxsplit=1)[1].split("      - id:", maxsplit=1)[0]
        assert r"exclude: ^\.codex/host/" in hook


@pytest.mark.unit
def test_codex_environment_is_tracked_policy_not_ignored_local_state() -> None:
    """Fresh Babylon worktrees must receive the installer and its actions."""
    environment = REPO_ROOT / ".codex" / "environments" / "environment.toml"
    ignored = subprocess.run(
        ["git", "check-ignore", "--no-index", "--quiet", str(environment)],
        cwd=REPO_ROOT,
        check=False,
        timeout=30,
    )
    assert ignored.returncode == 1, ".codex returned to ignored local-only state"
    assert environment.is_file()

    source = environment.read_text(encoding="utf-8")
    for required in (
        ".codex/host/install.sh",
        ".codex/host/cargo-config.py",
        "CODEX_RUST_SCCACHE_BOOTSTRAP=1",
        "codex_rust_cache_dir babylon",
        "codex_rust_server_socket babylon",
        "rustup toolchain install 1.99.1",
        '"$CODEX_WORKTREE_PATH/rust/target"',
        "mise run check:worktree-contract",
        'export PATH="$codex_rust_dispatcher_bin:$codex_rust_cargo_home/bin:$PATH"',
    ):
        assert required in source, f"Codex environment lost {required}"
    dispatcher_path = 'export PATH="$codex_rust_dispatcher_bin:$codex_rust_cargo_home/bin:$PATH"'
    installer = (
        'CODEX_RUST_CACHE_ROOT="$codex_cache_root" "$CODEX_WORKTREE_PATH/.codex/host/install.sh"'
    )
    assert source.index(dispatcher_path) < source.index(installer)


@pytest.mark.unit
def test_repository_entrypoints_do_not_override_dispatcher_owned_resources() -> None:
    """Native Mise must not recreate the retired cross-repository cache."""
    entrypoints = {
        ".mise.toml": (REPO_ROOT / ".mise.toml").read_text(encoding="utf-8"),
    }
    prohibited_assignments = (
        r"^\s*RUSTC_WRAPPER\s*=",
        r"^\s*export\s+RUSTC_WRAPPER=",
        r"^\s*SCCACHE_DIR\s*=",
        r"^\s*export\s+SCCACHE_DIR=",
        r"^\s*SCCACHE_CACHE_SIZE\s*=",
        r"^\s*export\s+SCCACHE_CACHE_SIZE=",
    )
    for name, source in entrypoints.items():
        for assignment in prohibited_assignments:
            assert re.search(assignment, source, flags=re.MULTILINE) is None, (
                f"{name} overrides dispatcher-owned resources: {assignment}"
            )

    assert re.findall(
        r'^CARGO_BUILD_JOBS = "([0-9]+)"$', entrypoints[".mise.toml"], re.MULTILINE
    ) == ["4"]
    environment = (REPO_ROOT / ".codex/environments/environment.toml").read_text(encoding="utf-8")
    assert (
        'export PATH="$codex_rust_dispatcher_bin:$codex_rust_cargo_home/bin:$PATH"' in environment
    )
    assert 'export PATH="$HOME/.local/bin:' not in entrypoints[".mise.toml"]
    assert "nix develop" not in entrypoints[".mise.toml"]


@pytest.mark.integration
def test_native_mise_prefers_installed_managed_cargo() -> None:
    """Native Mise preserves the managed Cargo dispatcher and rustup tools."""
    cargo = shutil.which("cargo")
    if cargo is None:
        pytest.skip("Cargo is unavailable")
    cargo_path = Path(cargo).resolve()
    data_root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    policy_root = data_root / "codex-rust-host"
    if policy_root not in cargo_path.parents:
        pytest.skip("the managed Codex Cargo shim is not installed on this host")
    cargo_home = Path(os.environ.get("CARGO_HOME", Path.home() / ".cargo")).resolve()

    expected_target = REPO_ROOT / "rust" / "target"
    proof = subprocess.run(
        [
            "mise",
            "exec",
            "--",
            "sh",
            "-c",
            'test "$(readlink -f -- "$(command -v cargo)")" = "$EXPECTED_MANAGED_CARGO" && '
            'test "$(command -v rustc)" = "$EXPECTED_RUSTUP_BIN/rustc" && '
            'test "$(command -v cargo-clippy)" = "$EXPECTED_RUSTUP_BIN/cargo-clippy" && '
            'test "$(command -v rustfmt)" = "$EXPECTED_RUSTUP_BIN/rustfmt" && '
            "cd rust && "
            'test "$(rustc --version)" = "$(rustup run 1.99.1 rustc --version)" && '
            "CODEX_RUST_HOST_DRY_RUN=1 cargo metadata --locked --no-deps --format-version 1; "
            'inspection_status="$?"; test "$inspection_status" -eq 88',
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
        env={
            **os.environ,
            "EXPECTED_MANAGED_CARGO": str(cargo_path),
            "EXPECTED_RUSTUP_BIN": str(cargo_home / "bin"),
        },
    )
    assert proof.returncode == 0, proof.stdout + proof.stderr
    assert "repository=babylon" in proof.stdout
    assert f"target={expected_target}" in proof.stdout
    assert "jobs=4" in proof.stdout
