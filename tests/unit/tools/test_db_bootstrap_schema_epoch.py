"""Contracts for the PER-287 clean-bootstrap Rust epoch handoff."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BOOTSTRAP_CALLERS = (
    ".github/workflows/ci.yml",
    ".github/workflows/main.yml",
    ".github/workflows/nightly-michigan-smoke.yml",
    ".github/workflows/weekly-pg-integration.yml",
)
DIRECT_BOOTSTRAP_CALLERS = (
    ".github/workflows/main.yml",
    ".github/workflows/nightly-michigan-smoke.yml",
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


def test_db_bootstrap_has_one_rust_owned_activation_root() -> None:
    task = _mise_task("db:bootstrap")

    build = task.index("cargo build -p babylon-persistence --bin babylon-runtime --locked")
    activation = task.index("babylon-runtime bootstrap")
    assert build < activation
    assert task.count("babylon-runtime bootstrap") == 1
    assert "BABYLON_RUNTIME_DSN" in task
    assert "host=127.0.0.1" in task
    assert "host=localhost" not in task
    for retired_root in (
        "BABYLON_SCHEMA_EPOCH_DSN",
        "babylon-schema-epoch",
        "POSTGRES_SCHEMA_DDL",
        "ensure_ddl_applied",
        "_apply_migrations",
        "uv run python",
    ):
        assert retired_root not in task


def test_db_bootstrap_clears_inherited_libpq_targets_before_any_database_access() -> None:
    task = _mise_task("db:bootstrap")

    unset_lines = [line.strip() for line in task.splitlines() if line.strip().startswith("unset ")]
    assert unset_lines == [f"unset {' '.join(LIBPQ_TARGET_ENV)}"]
    sanitization = task.index(unset_lines[0])
    build = task.index("cargo build -p babylon-persistence --bin babylon-runtime --locked")
    activation = task.index("babylon-runtime bootstrap")
    assert sanitization < build < activation


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


def test_local_bootstrap_callers_expose_the_single_rust_authority_root() -> None:
    setup = _mise_task("setup")
    assert "PostgreSQL 17" in setup
    assert "Postgres 16" not in setup

    for task_name in ("setup", "clean:testdb"):
        task = _mise_task(task_name)
        assert "cargo build -p babylon-persistence --bin babylon-runtime --locked" in task
        assert f'BABYLON_RUNTIME_DSN="{LOCAL_BOOTSTRAP_DSN}" babylon-runtime bootstrap' in task
        assert "mise run db:bootstrap" not in task

    integration = _mise_task("test:int-pg")
    assert f'export BABYLON_RUNTIME_DSN="{LOCAL_BOOTSTRAP_DSN}"' in integration
    assert "babylon-runtime bootstrap" in integration
    assert "babylon-runtime michigan-smoke" in integration
    assert "uv run pytest" not in integration

    michigan_smoke = _mise_task("qa:michigan-rollover-smoke")
    assert 'export PATH="$PWD/rust/target/debug:$PATH"' in michigan_smoke
    assert "babylon-runtime michigan-smoke" in michigan_smoke

    direct_bootstrap = _mise_task("db:bootstrap")
    assert (
        f'export BABYLON_RUNTIME_DSN="${{BABYLON_RUNTIME_DSN:-{LOCAL_BOOTSTRAP_DSN}}}"'
    ) in direct_bootstrap

    for relative in ("README.md", "SETUP_GUIDE.md"):
        guide = (ROOT / relative).read_text(encoding="utf-8")
        assert "`mise run setup` requires [Nix]" in guide


def test_runtime_cli_has_one_exact_connecting_schema_preflight_mode() -> None:
    source = (ROOT / "rust/crates/babylon-persistence/src/bin/babylon-runtime.rs").read_text(
        encoding="utf-8"
    )

    assert 'const DSN_ENV: &str = "BABYLON_RUNTIME_DSN";' in source
    assert "std::env::args_os().skip(1)" in source
    assert "Command::Preflight =>" in source
    assert "preflight_schema_epoch(config)" in source
    assert "Command::Activate | Command::Bootstrap =>" in source
    assert "activate_rust_persistence_v1(config)" in source
    assert "babylon-schema-epoch" not in source
    assert "BABYLON_SCHEMA_EPOCH_DSN" not in source


def test_runtime_cli_owns_one_restart_safe_activation_sequence() -> None:
    persistence = ROOT / "rust/crates/babylon-persistence"
    cli = (persistence / "src/bin/babylon-runtime.rs").read_text(encoding="utf-8")
    lib = (persistence / "src/lib.rs").read_text(encoding="utf-8")
    bootstrap = (persistence / "src/bootstrap.rs").read_text(encoding="utf-8")
    runtime = (persistence / "src/runtime.rs").read_text(encoding="utf-8")
    cohort = (persistence / "src/h3_reference_cohort.rs").read_text(encoding="utf-8")

    assert "activate_rust_persistence_v1(config)" in cli
    activation = runtime.split("pub fn activate_rust_persistence_v1", maxsplit=1)[1]
    assert "bootstrap_h3_reader_epoch_v1(config)" in activation
    assert "batch_execute(MIGRATION_0008_SQL)" in activation
    assert "batch_execute(MIGRATION_0009_SQL)" in activation
    assert (
        activation.index("bootstrap_h3_reader_epoch_v1(config)")
        < activation.index("batch_execute(MIGRATION_0008_SQL)")
        < activation.index("batch_execute(MIGRATION_0009_SQL)")
    )

    for call in (
        "representative_h3_reference_cohort_v1()",
        "michigan_dynamic_hex_foundation_v1()",
        "migrate_schema_epoch_to_h3_handoff(config)",
        "install_michigan_h3_reference_bundle_v1(config, cohort, foundation)",
        "backfill_legacy_h3_shadow_keys(config)",
        "migrate_schema_epoch(config)",
    ):
        assert call in bootstrap
    source_validation = bootstrap.index("representative_h3_reference_cohort_v1()")
    foundation_validation = bootstrap.index("michigan_dynamic_hex_foundation_v1()")
    handoff = bootstrap.index("migrate_schema_epoch_to_h3_handoff(config)")
    install = bootstrap.index("install_michigan_h3_reference_bundle_v1(config, cohort, foundation)")
    backfill = bootstrap.index("backfill_legacy_h3_shadow_keys(config)")
    terminal = bootstrap.rindex("migrate_schema_epoch(config)")
    assert source_validation < foundation_validation < handoff < install < backfill < terminal
    assert "install_representative_h3_cohort" not in bootstrap
    assert "pub fn bootstrap_h3_reader_epoch_v1" in bootstrap
    assert "mod bootstrap;" in lib
    assert "pub mod bootstrap;" not in lib
    assert "bootstrap_h3_reader_epoch_v1" in lib

    source_fixture = persistence / "src/fixtures/h3_reference_source_v1.bin"
    retired_test_fixture = persistence / "tests/fixtures/h3_reference_source_v1.bin"
    assert source_fixture.is_file()
    assert not retired_test_fixture.exists()
    assert 'include_bytes!("fixtures/h3_reference_source_v1.bin")' in cohort

    include_sites = []
    for path in persistence.rglob("*.rs"):
        text = path.read_text(encoding="utf-8")
        if 'include_bytes!("fixtures/h3_reference_source_v1.bin")' in text:
            include_sites.append(path.relative_to(persistence).as_posix())
    assert include_sites == ["src/h3_reference_cohort.rs"]


def test_every_checked_in_bootstrap_caller_provisions_pinned_rust() -> None:
    action = (ROOT / ".github/actions/bootstrap-persistence/action.yml").read_text(encoding="utf-8")
    assert "rust/rust-toolchain.toml" in action
    assert 'rustup toolchain install "$CHANNEL" --profile minimal --no-self-update' in action

    for relative in BOOTSTRAP_CALLERS:
        workflow = (ROOT / relative).read_text(encoding="utf-8")
        assert "uses: ./.github/actions/bootstrap-persistence" in workflow

    for relative in DIRECT_BOOTSTRAP_CALLERS:
        workflow = (ROOT / relative).read_text(encoding="utf-8")
        assert "mise run db:bootstrap" in workflow

    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    weekly = (ROOT / ".github/workflows/weekly-pg-integration.yml").read_text(encoding="utf-8")
    assert "tools/run_rust_legacy_adopter_pg.sh" in ci
    assert "tools/run_rust_legacy_adopter_pg.sh" in weekly
    assert "mise run test:rust-legacy-adopter-pg" not in weekly


def test_pr_pg_lane_runs_the_rust_live_matrix_without_python_reference_data() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    pg_lane = workflow.split("\n  pg-integration:", maxsplit=1)[1].split(
        "\n  security:", maxsplit=1
    )[0]

    bootstrap = pg_lane.index("uses: ./.github/actions/bootstrap-persistence")
    pr_focus = pg_lane.index("BABYLON_LEGACY_ADOPTER_LIVE_FOCUS: pr")
    runner = pg_lane.index("tools/run_rust_legacy_adopter_pg.sh")
    assert bootstrap < pr_focus < runner
    assert "fetch-reference-db" not in pg_lane
    assert "bootstrap-python" not in pg_lane
    assert "uv run pytest" not in pg_lane


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
    refused_bootstrap = runner.index('BABYLON_RUNTIME_DSN="$HOSTILE_OPTIONS_DSN"', before_snapshot)
    after_snapshot = runner.index('after_options_refusal="$(timeout', refused_bootstrap)
    assert "mise run db:bootstrap" in runner
    normal_bootstrap = runner.index('BABYLON_RUNTIME_DSN="$BOOTSTRAP_DSN"', after_snapshot)
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
    assert '"1:1:8,2:2:9|true|true"' in runner
    assert "babylon_meta.persistence_authority_ledger" in runner
    assert "pg_catalog.to_regclass('public.hex_spatial_map') IS NULL" in runner
    assert "pg_catalog.to_regclass('babylon_state.campaign_foundation') IS NOT NULL" in runner
    smoke = runner.split("mise run qa:michigan-rollover-smoke", maxsplit=1)[0].rsplit(
        "timeout --signal=TERM --kill-after=30s 1800s", maxsplit=1
    )[1]
    assert 'BABYLON_RUNTIME_DSN="$BOOTSTRAP_DSN"' in smoke
    assert "BABYLON_PG_DSN=" not in smoke
    assert "BABYLON_TEST_PG_DSN=" not in smoke
