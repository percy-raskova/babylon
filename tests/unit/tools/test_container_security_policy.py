"""Static contracts for the Babylon PostgreSQL container boundary."""

from __future__ import annotations

import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOCKERFILE_PATH = ROOT / "docker" / "postgres" / "Dockerfile"
ENTRYPOINT_PATCH_PATH = ROOT / "docker" / "postgres" / "patch-entrypoint.awk"
COMPOSE_PATH = ROOT / "docker-compose.yml"
GOTCHAS_PATH = ROOT / "docs" / "agents" / "gotchas.md"
MISE_PATH = ROOT / ".mise.toml"
TRIVYIGNORE_PATH = ROOT / ".trivyignore"
LEGACY_ADOPTER_LIVE_PATH = (
    ROOT / "rust" / "crates" / "babylon-persistence" / "tests" / "legacy_adopter_postgres.rs"
)
LEGACY_ADOPTER_RUNNER_PATH = ROOT / "tools" / "run_rust_legacy_adopter_pg.sh"

POSTGIS_ALPINE = (
    "postgis/postgis:17-3.5-alpine@"
    "sha256:08f4b1e1f4a571008c60272ceb9e0d1f9f8f643792d006b74a35b1bec44c2218"
)
LINEAGE = (
    "babylon-postgres-lineage-v1|postgres=17|locale-provider=builtin|"
    "locale=C.UTF-8|encoding=UTF8|postgis=3.5.7|h3=4.5.0|"
    "h3_postgis=4.5.0|vector=0.8.5"
)
NEW_DEFAULT_VOLUME = "babylon-pg-alpine-c-utf8-v1"

UPSTREAM_ENTRYPOINT_SHAPE = "\n".join(
    (
        "_main() {",
        '\tif [ "$1" = \'postgres\' ] && ! _pg_want_help "$@"; then',
        "\t\tdocker_setup_env",
        "\t\t# setup data directories and permissions (when run as root)",
        "\t\tdocker_create_db_directories",
        "\t\tif [ \"$(id -u)\" = '0' ]; then",
        "\t\t\t# then restart script as postgres user",
        '\t\t\texec gosu postgres "$BASH_SOURCE" "$@"',
        "\t\tfi",
        '\t\tif [ -z "$DATABASE_ALREADY_EXISTS" ]; then',
        "\t\t\tdocker_verify_minimum_env",
        "\t\t\tdocker_error_old_databases",
        "\t\t\tls /docker-entrypoint-initdb.d/ > /dev/null",
        "\t\t\tdocker_init_database_dir",
        '\t\t\tpg_setup_hba_conf "$@"',
        '\t\t\texport PGPASSWORD="${PGPASSWORD:-$POSTGRES_PASSWORD}"',
        '\t\t\tdocker_temp_server_start "$@"',
        "\t\t\tdocker_setup_db",
        "\t\t\tdocker_process_init_files /docker-entrypoint-initdb.d/*",
        "\t\t\tdocker_temp_server_stop",
        "\t\t\tunset PGPASSWORD",
        "\t\tfi",
        '\t\tunset "${!POSTGRES_@}"',
        "\tfi",
        '\texec "$@"',
        "}",
        "",
    )
)


def _dockerfile() -> str:
    return DOCKERFILE_PATH.read_text(encoding="utf-8")


def _patch_entrypoint(source: str = UPSTREAM_ENTRYPOINT_SHAPE) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["awk", "-f", str(ENTRYPOINT_PATCH_PATH)],
        input=source,
        check=False,
        capture_output=True,
        text=True,
    )


def _write_patched_entrypoint(tmp_path: Path) -> Path:
    result = _patch_entrypoint()
    assert result.returncode == 0, result.stderr
    entrypoint = tmp_path / "docker-entrypoint.sh"
    entrypoint.write_text(result.stdout, encoding="utf-8")
    entrypoint.chmod(0o755)
    return entrypoint


def test_postgres_extensions_share_one_pinned_alpine_lineage() -> None:
    dockerfile = _dockerfile()
    from_lines = [line for line in dockerfile.splitlines() if line.startswith("FROM ")]

    assert from_lines == [
        f"FROM {POSTGIS_ALPINE} AS extension-builder",
        f"FROM {POSTGIS_ALPINE}",
    ]
    for forbidden in ("bullseye", "gcc:", "apt-archive", ".deb", "dpkg"):
        assert forbidden not in dockerfile


def test_postgres_extensions_use_checksum_pinned_official_sources() -> None:
    dockerfile = _dockerfile()
    expected_inputs = {
        "https://github.com/postgis/h3-pg/archive/refs/tags/v4.5.0.tar.gz": (
            "sha256:c54c119e1d9a578d5cbcce22f6c66dab2b5a45219fc2b260619807f7f061e53a"
        ),
        "https://github.com/uber/h3/archive/refs/tags/v4.5.0.tar.gz": (
            "sha256:0da8a392a6ff77e76b60e6a331a49497d0935b6b7b6899da7a3e2786139b0441"
        ),
        "https://github.com/pgvector/pgvector/archive/refs/tags/v0.8.5.tar.gz": (
            "sha256:6f88a5cbdde31666f4b6c1a6b75c51dcbeffe58f9a7d2b26e502d5a6e5e14d44"
        ),
    }

    for source, checksum in expected_inputs.items():
        assert f"ADD --checksum={checksum}" in dockerfile
        assert source in dockerfile
    assert dockerfile.count("ADD --checksum=sha256:") == len(expected_inputs)


def test_final_image_copies_only_staged_extension_artifacts() -> None:
    copy_lines = [line for line in _dockerfile().splitlines() if line.startswith("COPY --from=")]

    assert copy_lines == [
        "COPY --from=extension-builder \\",
        "COPY --from=extension-builder \\",
    ]
    dockerfile = _dockerfile()
    assert (
        "/tmp/extension-install/usr/local/lib/postgresql/ /usr/local/lib/postgresql/"
    ) in dockerfile
    assert (
        "/tmp/extension-install/usr/local/share/postgresql/extension/ "
        "/usr/local/share/postgresql/extension/"
    ) in dockerfile


def test_entrypoint_switches_directly_to_su_exec_after_root_bootstrap() -> None:
    dockerfile = _dockerfile()

    assert "apk add --no-cache su-exec=0.3-r0" in dockerfile
    assert (
        "--mount=type=bind,source=patch-entrypoint.awk,"
        "target=/tmp/patch-entrypoint.awk,readonly" in dockerfile
    )
    assert 'awk -f /tmp/patch-entrypoint.awk "$entrypoint" > "$patched_entrypoint"' in dockerfile
    assert 'expected_gosu=\'exec gosu postgres "$BASH_SOURCE" "$@"\'' in dockerfile
    assert 'expected_su_exec=\'exec su-exec postgres "$BASH_SOURCE" "$@"\'' in dockerfile
    assert "sed -i" not in dockerfile
    assert "! grep -Fq 'gosu' \"$entrypoint\"" in dockerfile
    assert "rm /usr/local/bin/gosu" in dockerfile
    assert "test ! -e /usr/local/bin/gosu" in dockerfile
    assert "ENTRYPOINT" not in dockerfile
    assert not any(line.startswith("USER ") for line in dockerfile.splitlines())


def test_entrypoint_rejects_unmarked_pgdata_before_any_directory_mutation() -> None:
    result = _patch_entrypoint()

    assert result.returncode == 0, result.stderr
    patched = result.stdout
    setup = patched.index("\t\tdocker_setup_env")
    marker_check = patched.index(
        f'\t\tlocal babylon_lineage="{LINEAGE}"',
        setup,
    )
    create_directories = patched.index("\t\tdocker_create_db_directories")
    assert setup < marker_check < create_directories
    for required in (
        'local babylon_lineage_marker="$PGDATA/.babylon-postgres-lineage-v1"',
        'if [ -e "$PGDATA" ] && [ ! -d "$PGDATA" ]; then',
        'elif [ -e "$babylon_lineage_marker" ]; then',
        '[ "$(stat -c %a "$babylon_lineage_marker")" = "444" ]',
        '[ "$(cat "$PGDATA/PG_VERSION")" = "17" ]',
        'find "$PGDATA" -mindepth 1 -maxdepth 1 -print -quit',
        'if [ "$babylon_lineage_state" = "refuse" ]; then',
        "No PGDATA ownership, mode, or content mutation was attempted.",
        "exit 1",
    ):
        assert required in patched


def test_entrypoint_forces_builtin_locale_and_marks_only_completed_init() -> None:
    result = _patch_entrypoint()

    assert result.returncode == 0, result.stderr
    patched = result.stdout
    init_branch = patched.index('\t\tif [ -z "$DATABASE_ALREADY_EXISTS" ]; then')
    init_args = patched.index(
        "--locale-provider=builtin --builtin-locale=C.UTF-8 --encoding=UTF8",
        init_branch,
    )
    init_files = patched.index(
        "\t\t\tdocker_process_init_files /docker-entrypoint-initdb.d/*",
        init_args,
    )
    temp_stop = patched.index("\t\t\tdocker_temp_server_stop", init_files)
    unset_password = patched.index("\t\t\tunset PGPASSWORD", temp_stop)
    marker_temp = patched.index(
        '\t\t\tlocal babylon_lineage_tmp="${babylon_lineage_marker}.tmp.$$"',
        unset_password,
    )
    marker_write = patched.index(
        'printf "%s\\n" "$babylon_lineage" > "$babylon_lineage_tmp"',
        marker_temp,
    )
    marker_chmod = patched.index('chmod 0444 "$babylon_lineage_tmp"', marker_write)
    marker_move = patched.index(
        'mv "$babylon_lineage_tmp" "$babylon_lineage_marker"',
        marker_chmod,
    )
    assert init_branch < init_args < init_files < temp_stop < unset_password
    assert unset_password < marker_temp < marker_write < marker_chmod < marker_move


def test_entrypoint_patch_fails_closed_when_upstream_shape_drifts() -> None:
    missing_anchor = UPSTREAM_ENTRYPOINT_SHAPE.replace(
        "\t\tdocker_create_db_directories\n",
        "",
        1,
    )
    duplicate_anchor = UPSTREAM_ENTRYPOINT_SHAPE.replace(
        "\t\tdocker_setup_env\n",
        "\t\tdocker_setup_env\n\t\tdocker_setup_env\n",
        1,
    )

    for source in (missing_anchor, duplicate_anchor):
        result = _patch_entrypoint(source)
        assert result.returncode == 42
        assert "refusing unexpected upstream entrypoint shape" in result.stderr


def test_unmarked_pgdata_rejection_preserves_content_mode_and_skips_mutator(
    tmp_path: Path,
) -> None:
    entrypoint = _write_patched_entrypoint(tmp_path)
    pgdata = tmp_path / "legacy-pgdata"
    pgdata.mkdir(mode=0o751)
    version = pgdata / "PG_VERSION"
    sentinel = pgdata / "sentinel.bin"
    version.write_bytes(b"17\n")
    sentinel.write_bytes(b"legacy-bytes\x00must-not-change")
    sentinel.chmod(0o640)
    mutator_receipt = tmp_path / "mutator-called"
    before = (
        stat.S_IMODE(pgdata.stat().st_mode),
        stat.S_IMODE(version.stat().st_mode),
        stat.S_IMODE(sentinel.stat().st_mode),
        version.read_bytes(),
        sentinel.read_bytes(),
    )

    result = subprocess.run(
        [
            "bash",
            "-c",
            """
source "$1"
_pg_want_help() { return 1; }
docker_setup_env() { DATABASE_ALREADY_EXISTS=true; }
docker_create_db_directories() { printf 'called\n' > "$2"; }
export PGDATA="$3" PG_MAJOR=17
_main postgres
""",
            "per272-lineage-test",
            str(entrypoint),
            str(mutator_receipt),
            str(pgdata),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    after = (
        stat.S_IMODE(pgdata.stat().st_mode),
        stat.S_IMODE(version.stat().st_mode),
        stat.S_IMODE(sentinel.stat().st_mode),
        version.read_bytes(),
        sentinel.read_bytes(),
    )
    assert result.returncode == 1
    assert "refusing unrecognized PostgreSQL data directory" in result.stderr
    assert "No PGDATA ownership, mode, or content mutation was attempted." in result.stderr
    assert not mutator_receipt.exists()
    assert after == before


def test_fresh_init_appends_fixed_locale_args_and_writes_exact_marker_last(
    tmp_path: Path,
) -> None:
    entrypoint = _write_patched_entrypoint(tmp_path)
    pgdata = tmp_path / "fresh-pgdata"
    pgdata.mkdir(mode=0o700)
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_postgres = fake_bin / "postgres"
    fake_postgres.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    fake_postgres.chmod(0o755)
    events = tmp_path / "events"
    init_args = tmp_path / "init-args"

    result = subprocess.run(
        [
            "bash",
            "-c",
            """
source "$1"
_pg_want_help() { return 1; }
docker_setup_env() {
    DATABASE_ALREADY_EXISTS=
    POSTGRES_INITDB_ARGS="--data-checksums"
    POSTGRES_PASSWORD=test
    POSTGRES_USER=test
    POSTGRES_DB=test
    POSTGRES_HOST_AUTH_METHOD=
}
docker_create_db_directories() { printf 'create-directories\n' >> "$EVENTS"; }
docker_verify_minimum_env() { printf 'verify-env\n' >> "$EVENTS"; }
docker_error_old_databases() { printf 'verify-layout\n' >> "$EVENTS"; }
ls() { :; }
docker_init_database_dir() {
    printf '%s\n' "$POSTGRES_INITDB_ARGS" > "$INIT_ARGS"
    printf 'init-database\n' >> "$EVENTS"
}
pg_setup_hba_conf() { printf 'hba\n' >> "$EVENTS"; }
docker_temp_server_start() { printf 'temp-start\n' >> "$EVENTS"; }
docker_setup_db() { printf 'setup-db\n' >> "$EVENTS"; }
docker_process_init_files() { printf 'init-files\n' >> "$EVENTS"; }
docker_temp_server_stop() { printf 'temp-stop\n' >> "$EVENTS"; }
export PGDATA="$2" PG_MAJOR=17 EVENTS="$3" INIT_ARGS="$4"
export PATH="$5:$PATH"
_main postgres
""",
            "per272-lineage-test",
            str(entrypoint),
            str(pgdata),
            str(events),
            str(init_args),
            str(fake_bin),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    marker = pgdata / ".babylon-postgres-lineage-v1"
    assert result.returncode == 0, result.stderr
    assert init_args.read_text(encoding="utf-8") == (
        "--data-checksums --locale-provider=builtin --builtin-locale=C.UTF-8 --encoding=UTF8\n"
    )
    assert events.read_text(encoding="utf-8").splitlines() == [
        "create-directories",
        "verify-env",
        "verify-layout",
        "init-database",
        "hba",
        "temp-start",
        "setup-db",
        "init-files",
        "temp-stop",
    ]
    assert marker.read_bytes() == f"{LINEAGE}\n".encode()
    assert stat.S_IMODE(marker.stat().st_mode) == 0o444
    assert list(pgdata.glob(".babylon-postgres-lineage-v1.tmp.*")) == []


def test_compose_rotates_the_default_volume_without_touching_the_legacy_name() -> None:
    compose = COMPOSE_PATH.read_text(encoding="utf-8")

    assert f"${{BABYLON_PG_DATA:-{NEW_DEFAULT_VOLUME}}}:/var/lib/postgresql/data" in compose
    assert f"  {NEW_DEFAULT_VOLUME}:" in compose
    assert "${BABYLON_PG_DATA:-babylon-pg-data}" not in compose
    assert "\n  babylon-pg-data:\n" not in compose


def test_local_start_tasks_always_build_the_declared_postgres_image() -> None:
    mise = MISE_PATH.read_text(encoding="utf-8")

    for task_name in ("db:up", "db:start"):
        task_start = mise.index(f'[tasks."{task_name}"]')
        task_end = mise.index("\n[tasks.", task_start + 1)
        task = mise[task_start:task_end]
        assert 'run = "docker compose up --build -d --wait babylon-pg"' in task


def test_compose_healthcheck_proves_the_exact_runtime_and_cluster_lineage() -> None:
    compose = COMPOSE_PATH.read_text(encoding="utf-8")

    for required in (
        "$${PGDATA}/.babylon-postgres-lineage-v1",
        LINEAGE,
        "server_version_num') = '170011'",
        "pg_encoding_to_char(database_row.encoding) = 'UTF8'",
        "database_row.datlocprovider = 'b'",
        "database_row.datlocale = 'C.UTF-8'",
        "extension_row.extversion = '3.5.7'",
        "extension_row.extversion = '0.8.5'",
        "available.default_version = '4.5.0'",
        "available.name = 'h3'",
        "available.name = 'h3_postgis'",
    ):
        assert required in compose
    assert "pg_isready -U test -d babylon_test" in compose


def test_operational_contract_is_fresh_init_or_offline_logical_restore_only() -> None:
    dockerfile = _dockerfile()
    gotchas = GOTCHAS_PATH.read_text(encoding="utf-8")
    mise = MISE_PATH.read_text(encoding="utf-8")

    assert NEW_DEFAULT_VOLUME in gotchas
    assert "babylon-pg-data" in gotchas
    assert "offline logical dump/restore" in gotchas
    assert "never attach" in gotchas
    assert NEW_DEFAULT_VOLUME in mise
    for forbidden in (
        "REINDEX DATABASE",
        "REFRESH COLLATION VERSION",
        "ALTER EXTENSION",
        "postgis_extensions_upgrade",
    ):
        assert forbidden not in dockerfile


def test_lineage_marker_is_a_recoverability_fence_not_security_attestation() -> None:
    dockerfile = _dockerfile()
    gotchas = GOTCHAS_PATH.read_text(encoding="utf-8")
    normalized_dockerfile = " ".join(dockerfile.split())
    normalized_gotchas = " ".join(gotchas.split())

    assert "accidental/recoverability lineage fence" in normalized_gotchas
    assert "not an adversarial attestation" in normalized_gotchas
    assert "fail-before-chown" in normalized_gotchas
    assert "No wrapper or fallback" in normalized_gotchas
    assert "recoverability fence" in normalized_dockerfile
    assert "security attestation" in normalized_dockerfile


def test_build_contract_is_pinned_and_verified_but_not_byte_reproducible() -> None:
    dockerfile = _dockerfile()
    normalized = " ".join(line.removeprefix("#").strip() for line in dockerfile.splitlines())

    for claim in (
        "digest-pinned base",
        "checksum-pinned source archives",
        "exact final-stage runtime package revisions",
        "behavioral version checks",
        "does not claim byte-identical image rebuilds",
        "Builder-only APK packages are repository-resolved",
    ):
        assert claim in normalized
    assert "apk add --no-cache --virtual .extension-build-deps" in dockerfile
    assert "$DOCKER_PG_LLVM_DEPS" in dockerfile


def test_final_image_pins_available_high_severity_security_fixes() -> None:
    dockerfile = _dockerfile()

    for package in (
        "giflib=5.2.2-r2",
        "libcrypto3=3.5.8-r0",
        "libssl3=3.5.8-r0",
    ):
        assert package in dockerfile


def test_trivy_policy_retains_only_the_root_bootstrap_shape_exception() -> None:
    active_entries = [
        line.strip()
        for line in TRIVYIGNORE_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    assert active_entries == ["DS-0002"]


def test_current_census_export_is_one_explicit_bounded_v2_path() -> None:
    live = LEGACY_ADOPTER_LIVE_PATH.read_text(encoding="utf-8")
    runner = LEGACY_ADOPTER_RUNNER_PATH.read_text(encoding="utf-8")

    assert 'const CURRENT_CENSUS_V2_FOCUS: &str = "runtime_census_v2";' in live
    assert (
        "const CURRENT_CENSUS_V2_EXPORT_DIR_ENV: &str = "
        '"BABYLON_CURRENT_CENSUS_V2_EXPORT_DIR";' in live
    )
    assert "MAX_CURRENT_CENSUS_V2_DRIFT_ROWS" in live
    assert "MAX_CURRENT_CENSUS_V2_REPORT_BYTES" in live
    assert ".create_new(true)" in live
    assert "legacy_adopter_census_v2.txt" in live
    assert "fresh_schema_epoch_census_v2.txt" in live
    assert "fresh_schema_epoch_census_with_intel_v2.txt" in live
    assert "current_census_v2_drift_report.txt" in live
    assert "BABYLON_LEGACY_ADOPTER_CENSUS_EXPORT" not in live

    assert "runtime_census_v2" in runner
    assert "BABYLON_CURRENT_CENSUS_V2_EXPORT_DIR" in runner
    assert "current-census-v2 output directory must be absolute" in runner
    assert "current-census-v2 export directory is accepted only" in runner


def test_current_census_export_uses_independent_pairs_and_blocks_unexplained_drift() -> None:
    live = LEGACY_ADOPTER_LIVE_PATH.read_text(encoding="utf-8")
    exporter_start = live.index("fn export_current_census_v2(")
    exporter_end = live.index("\nfn verify_pinned_postgres_runtime", exporter_start)
    exporter = live[exporter_start:exporter_end]

    for receipt in (
        "assert_eq!(fresh_without_intel_first, fresh_without_intel_second)",
        "assert_eq!(legacy_first, legacy_second)",
        "assert_eq!(fresh_with_intel_first, fresh_with_intel_second)",
        "hardened_authority_snapshot(first_config)",
        "hardened_authority_snapshot(second_config)",
        "validated_current_stamp_definitions(&legacy_first)",
        "validated_current_stamp_definitions(&legacy_second)",
        "current_census_v2_runtime_provenance(first_config)",
        "current_census_v2_runtime_provenance(second_config)",
        "current_census_sql_sha256()",
        'snapshot.authority_schemas.join(",")',
        "parse_legacy_census_fixture(fixture_text)",
        "blocked_pending_exact_payload_comparison",
        "conservation_audit_log",
        "census_payloads_for_drift",
        "JOIN ROWS FROM",
        "MAX_CURRENT_CENSUS_V2_INLINE_PAYLOAD_BYTES",
        "'mode', 'inline'",
        "'mode', 'structural'",
        "'payload_bytes'",
        "'payload_sha256'",
        "'collections'",
    ):
        assert receipt in exporter
    assert "JOIN pg_catalog.unnest(" not in exporter
    assert exporter.count("ScratchDatabase::empty(") == 2
    assert exporter.count("legacy_epoch_fixture::build_frozen_python_estate(") == 2
    assert exporter.index("let fresh_payloads =") < exporter.index(
        "legacy_epoch_fixture::build_frozen_python_estate("
    )
    assert "run_python_repair(" not in exporter
    assert "std::fs::write" not in exporter
    assert "LEGACY_CENSUS_FIXTURE.find" not in exporter

    writer_start = exporter.index("fn current_census_v2_fixture_bytes(")
    writer_end = exporter.index("\nfn current_census_drift(", writer_start)
    writer = exporter[writer_start:writer_end]
    assert "validated_current_stamp_definitions(snapshot)" in writer
    assert "LEGACY_STAMP_CATALOG.iter().take(LEGACY_STAMP_CATALOG.len())" not in writer
