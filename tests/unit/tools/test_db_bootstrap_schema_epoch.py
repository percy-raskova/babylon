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
LIBPQ_TARGET_ENV = (
    "PGHOST",
    "PGHOSTADDR",
    "PGPORT",
    "PGDATABASE",
    "PGOPTIONS",
    "PGSERVICE",
    "PGSERVICEFILE",
    "PGSYSCONFDIR",
)
LOCAL_BOOTSTRAP_DSN = "host=127.0.0.1 port=5433 dbname=babylon_test user=test password=test"


def _mise_task(name: str) -> str:
    text = (ROOT / ".mise.toml").read_text(encoding="utf-8")
    for header in (f'[tasks."{name}"]', f"[tasks.{name}]"):
        if header in text:
            return text.split(header, maxsplit=1)[1].split("\n[tasks.", maxsplit=1)[0]
    raise AssertionError(f"missing Mise task: {name}")


def test_db_bootstrap_preflights_target_and_owner_then_advances_after_legacy_ddl() -> None:
    task = _mise_task("db:bootstrap")

    preflight = task.index("--locked -- --preflight")
    legacy = task.index("executed = ensure_ddl_applied(conn, POSTGRES_SCHEMA_DDL)")
    migrations = task.index("_apply_migrations(pool)")
    rust_epoch = task.rindex("babylon-schema-epoch")
    assert preflight < legacy < migrations < rust_epoch
    assert task.count("babylon-schema-epoch") == 2
    assert "BABYLON_SCHEMA_EPOCH_DSN" in task
    assert "host=127.0.0.1" in task
    assert "host=localhost" not in task
    assert (
        "CARGO_BUILD_JOBS=4 cargo run -p babylon-persistence --bin babylon-schema-epoch --locked"
    ) in task


def test_db_bootstrap_clears_inherited_libpq_targets_before_any_database_access() -> None:
    task = _mise_task("db:bootstrap")

    unset_lines = [line.strip() for line in task.splitlines() if line.strip().startswith("unset ")]
    assert unset_lines == [f"unset {' '.join(LIBPQ_TARGET_ENV)}"]
    sanitization = task.index(unset_lines[0])
    preflight = task.index("--locked -- --preflight")
    python = task.index('uv run python -c "')
    legacy = task.index("executed = ensure_ddl_applied(conn, POSTGRES_SCHEMA_DDL)")
    assert sanitization < preflight < python < legacy


def test_repository_cargo_concurrency_matches_the_host_contract() -> None:
    mise = (ROOT / ".mise.toml").read_text(encoding="utf-8")

    assert 'CARGO_BUILD_JOBS = "4"' in mise
    assert 'CARGO_BUILD_JOBS = "8"' not in mise


def test_sccache_uses_the_repository_local_policy_cache() -> None:
    mise = (ROOT / ".mise.toml").read_text(encoding="utf-8")
    flake = (ROOT / "flake.nix").read_text(encoding="utf-8")
    policy = (ROOT / ".codex/host/policy.sh").read_text(encoding="utf-8")

    assert "SCCACHE_DIR" not in mise
    assert "SCCACHE_DIR" not in flake
    assert "codex_rust_dispatcher_bin" in flake
    assert "codex-rust-host/v11/cargo" in flake
    assert "CODEX_RUST_SCCACHE_POLICY_KEY=0.17.0-p2" in policy
    assert "printf '%s/sccache/%s/%s\\n'" in policy
    assert "/media/user/data/sccache" not in mise
    assert "/media/user/data/sccache" not in flake


def test_default_nix_shell_conditions_the_linux_only_bevy_closure() -> None:
    flake = (ROOT / "flake.nix").read_text(encoding="utf-8")

    assert flake.count("devShells.default = pkgs.mkShell") == 1
    assert "linuxBevyPackages = lib.optionals pkgs.stdenv.isLinux" in flake
    assert "linuxBevyLibraryPackages" not in flake
    assert "]) ++ linuxBevyPackages ++ rustToolchainPackages ++ [" in flake
    assert "] ++ linuxBevyPackages)}" in flake
    for package in ("alsa-lib", "udev", "wayland", "libxkbcommon"):
        assert flake.count(package) == 1


def test_local_bootstrap_callers_run_rust_in_the_pinned_nix_shell() -> None:
    setup = _mise_task("setup")
    assert "PostgreSQL 17" in setup
    assert "Postgres 16" not in setup

    for task_name in ("setup", "clean:testdb", "test:int-pg"):
        task_lines = {line.strip() for line in _mise_task(task_name).splitlines()}
        assert (
            f'BABYLON_SCHEMA_EPOCH_DSN="{LOCAL_BOOTSTRAP_DSN}" '
            "mise run nix -- mise run db:bootstrap"
        ) in task_lines
        assert "mise run db:bootstrap" not in task_lines

    direct_bootstrap = _mise_task("db:bootstrap")
    assert (
        f'export BABYLON_SCHEMA_EPOCH_DSN="${{BABYLON_SCHEMA_EPOCH_DSN:-{LOCAL_BOOTSTRAP_DSN}}}"'
    ) in direct_bootstrap

    for relative in ("README.md", "SETUP_GUIDE.md"):
        guide = (ROOT / relative).read_text(encoding="utf-8")
        assert "`mise run setup` requires [Nix]" in guide


def test_schema_epoch_cli_has_one_exact_connecting_schema_preflight_mode() -> None:
    source = (ROOT / "rust/crates/babylon-persistence/src/bin/babylon-schema-epoch.rs").read_text(
        encoding="utf-8"
    )

    assert 'const DSN_ENV: &str = "BABYLON_SCHEMA_EPOCH_DSN";' in source
    assert 'const PREFLIGHT_MODE: &str = "--preflight";' in source
    assert "std::env::args_os()" in source
    assert "Mode::Preflight => preflight_schema_epoch(&config)" in source
    assert "migrate_schema_epoch(&config)" in source
    assert "unexpected arguments; expected no arguments or" in source
    assert "--validate-target-only" not in source
    assert "ValidateTargetOnly" not in source
    assert "validate_target_only" not in source


def test_every_checked_in_bootstrap_caller_provisions_pinned_rust() -> None:
    action = (ROOT / ".github/actions/bootstrap-persistence/action.yml").read_text(encoding="utf-8")
    assert "rust/rust-toolchain.toml" in action
    assert 'rustup toolchain install "$CHANNEL" --profile minimal --no-self-update' in action

    for relative in BOOTSTRAP_CALLERS:
        workflow = (ROOT / relative).read_text(encoding="utf-8")
        assert "mise run db:bootstrap" in workflow
        assert "uses: ./.github/actions/bootstrap-persistence" in workflow


def test_pr_pg_lane_fetches_reference_data_before_the_michigan_proof() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    pg_lane = workflow.split("\n  pg-integration:", maxsplit=1)[1].split(
        "\n  security:", maxsplit=1
    )[0]

    reference_data = pg_lane.index("uses: ./.github/actions/fetch-reference-db")
    pr_focus = pg_lane.index("BABYLON_LEGACY_ADOPTER_LIVE_FOCUS: pr")
    assert reference_data < pr_focus


def test_nightly_michigan_job_covers_bootstrap_smoke_and_hosted_setup_cleanup() -> None:
    workflow = (ROOT / ".github/workflows/nightly-michigan-smoke.yml").read_text(encoding="utf-8")
    job = workflow.split("\n  michigan-smoke:", maxsplit=1)[1]
    timeout_minutes = int(
        next(
            line.split(":", maxsplit=1)[1].strip()
            for line in job.splitlines()
            if line.strip().startswith("timeout-minutes:")
        )
    )

    bootstrap_envelope_seconds = 600 + 30
    michigan_envelope_seconds = 1800 + 30
    hosted_setup_and_cleanup_headroom_seconds = 15 * 60
    assert timeout_minutes == 69
    assert timeout_minutes * 60 >= (
        bootstrap_envelope_seconds
        + michigan_envelope_seconds
        + hosted_setup_and_cleanup_headroom_seconds
    )


def test_disposable_pg_runner_proves_bootstrap_and_michigan_smoke() -> None:
    runner = (ROOT / "tools/run_rust_legacy_adopter_pg.sh").read_text(encoding="utf-8")

    assert "clean_bootstrap" in runner
    assert 'if [ "$LIVE_FOCUS" = "clean_bootstrap" ] || [ "$LIVE_FOCUS" = "pr" ]; then' in runner
    options_refusal = runner.index('HOSTILE_OPTIONS_DSN="${BOOTSTRAP_DSN}?options=')
    before_snapshot = runner.index('before_options_refusal="$(timeout', options_refusal)
    refused_bootstrap = runner.index(
        'BABYLON_SCHEMA_EPOCH_DSN="$HOSTILE_OPTIONS_DSN"', before_snapshot
    )
    after_snapshot = runner.index('after_options_refusal="$(timeout', refused_bootstrap)
    assert "mise run db:bootstrap" in runner
    normal_bootstrap = runner.index('BABYLON_SCHEMA_EPOCH_DSN="$BOOTSTRAP_DSN"', after_snapshot)
    assert options_refusal < before_snapshot < refused_bootstrap < after_snapshot < normal_bootstrap
    assert "options-bearing DSN unexpectedly passed schema preflight" in runner
    assert "options-bearing DSN changed the fresh database before refusal" in runner
    bootstrap_prefix = runner[
        normal_bootstrap : runner.index("mise run db:bootstrap", normal_bootstrap)
    ]
    for assignment in (
        'PGHOST="host.invalid"',
        'PGHOSTADDR="203.0.113.1"',
        'PGPORT="1"',
        'PGDATABASE="redirected"',
        "PGOPTIONS='-c search_path=redirected,public'",
        'PGSERVICE="redirected"',
        'PGSERVICEFILE="/nonexistent/babylon-pg-service.conf"',
        'PGSYSCONFDIR="/nonexistent/babylon-pg-service.d"',
    ):
        assert assignment in bootstrap_prefix
    assert "mise run qa:michigan-rollover-smoke" in runner
    assert '"6|bigint"' in runner
    smoke = runner.split("mise run qa:michigan-rollover-smoke", maxsplit=1)[0].rsplit(
        "timeout --signal=TERM --kill-after=30s 1800s", maxsplit=1
    )[1]
    assert 'BABYLON_DSN="$BOOTSTRAP_DSN"' in smoke
    assert "BABYLON_PG_DSN=" not in smoke
    assert "BABYLON_TEST_PG_DSN=" not in smoke
