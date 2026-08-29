"""Contracts for the PER-287 clean-bootstrap Rust epoch handoff."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BOOTSTRAP_CALLERS = (
    ".github/workflows/ci.yml",
    ".github/workflows/main.yml",
    ".github/workflows/nightly-michigan-smoke.yml",
    ".github/workflows/weekly-pg-integration.yml",
    ".github/workflows/weekly-sim-artifacts.yml",
)


def _mise_task(name: str) -> str:
    text = (ROOT / ".mise.toml").read_text(encoding="utf-8")
    return text.split(f'[tasks."{name}"]', maxsplit=1)[1].split("\n[tasks.", maxsplit=1)[0]


def test_db_bootstrap_advances_the_exact_rust_epoch_after_legacy_ddl() -> None:
    task = _mise_task("db:bootstrap")

    legacy = task.index("ensure_ddl_applied")
    migrations = task.index("_apply_migrations(pool)")
    rust_epoch = task.index("babylon-schema-epoch")
    assert legacy < migrations < rust_epoch
    assert "BABYLON_SCHEMA_EPOCH_DSN" in task
    assert "host=127.0.0.1" in task
    assert "host=localhost" not in task
    assert (
        "CARGO_BUILD_JOBS=4 cargo run -p babylon-persistence --bin babylon-schema-epoch --locked"
    ) in task


def test_repository_cargo_concurrency_matches_the_host_contract() -> None:
    mise = (ROOT / ".mise.toml").read_text(encoding="utf-8")

    assert 'CARGO_BUILD_JOBS = "4"' in mise
    assert 'CARGO_BUILD_JOBS = "8"' not in mise


def test_schema_epoch_cli_has_one_environment_only_connection_boundary() -> None:
    source = (ROOT / "rust/crates/babylon-persistence/src/bin/babylon-schema-epoch.rs").read_text(
        encoding="utf-8"
    )

    assert 'const DSN_ENV: &str = "BABYLON_SCHEMA_EPOCH_DSN";' in source
    assert "migrate_schema_epoch(&config)" in source
    assert "std::env::args" not in source


def test_every_checked_in_bootstrap_caller_provisions_pinned_rust() -> None:
    action = (ROOT / ".github/actions/bootstrap-persistence/action.yml").read_text(encoding="utf-8")
    assert "rust/rust-toolchain.toml" in action
    assert 'rustup toolchain install "$CHANNEL" --profile minimal --no-self-update' in action

    for relative in BOOTSTRAP_CALLERS:
        workflow = (ROOT / relative).read_text(encoding="utf-8")
        assert "mise run db:bootstrap" in workflow
        assert "uses: ./.github/actions/bootstrap-persistence" in workflow


def test_disposable_pg_runner_proves_bootstrap_and_michigan_smoke() -> None:
    runner = (ROOT / "tools/run_rust_legacy_adopter_pg.sh").read_text(encoding="utf-8")

    assert "clean_bootstrap" in runner
    assert "mise run db:bootstrap" in runner
    assert "mise run qa:michigan-rollover-smoke" in runner
    assert '"6|bigint"' in runner
