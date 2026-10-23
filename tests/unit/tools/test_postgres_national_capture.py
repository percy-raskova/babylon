"""Invalid capture selections must refuse before owned-game preparation."""

import hashlib
import json
import os
import select
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]


def _supervisor_probe(tmp_path, *, packet=None, arguments=(), oid="42", live=True):
    canary = "12" * 16
    database = "national_" + canary[:12]
    inventory = f"babylon_test,{database},postgres,template0,template1"
    environment = {
        "PATH": os.defpath,
        "REPO_ROOT": str(tmp_path),
        "NATIONAL_RECORD": str(tmp_path / "active"),
        "CANARY": canary,
        "CONTAINER": "owned-probe",
        "CONTAINER_ID": "a1" * 32,
        "VOLUME": "owned-probe-volume",
        "IMAGE_ID": "sha256:" + "b2" * 32,
        "NATIONAL_DATABASE": database,
        "NATIONAL_WRITER": "national_writer_" + canary[:12],
        "NATIONAL_DATABASE_OID": oid,
        "BABYLON_STORAGE_REPORT_DIRECTORY": str(tmp_path),
        "PROBE_INVENTORY": inventory,
        "PROBE_PACKET": packet if packet is not None else f"{canary}|{inventory}|{oid}|0",
        "PROBE_CALLS": str(tmp_path / "calls"),
        "PROBE_QUERIES": str(tmp_path / "queries"),
    }
    script = r"""
source "$1"
shift
national_record
docker() {
  [ "$1" = inspect ] || return 98
  printf '%s\n' "$CONTAINER_ID|$IMAGE_ID|$CANARY|$VOLUME"
}
national_sql() {
  printf 'call\n' >> "$PROBE_CALLS"
  printf '%s\n' "$1" >> "$PROBE_QUERIES"
  if [[ "$1" = *current_setting* && "$1" = *string_agg* ]]; then
    printf '%s\n' "$PROBE_PACKET"
  elif [[ "$1" = "SELECT current_setting"* ]]; then
    printf '%s\n' "$CANARY"
  elif [[ "$1" = "SELECT string_agg"* ]]; then
    printf '%s\n' "$PROBE_INVENTORY"
  elif [[ "$1" = "SELECT oid"* ]]; then
    printf '%s\n' "$NATIONAL_DATABASE_OID"
  else
    printf '0\n'
  fi
}
"""
    script += 'national_verify_live "$@"' if live else 'national_verify_identity "$@"'
    return subprocess.run(
        [
            "bash",
            "-c",
            script,
            "supervisor-probe",
            str(REPOSITORY / "tools/postgres_national_lifecycle.sh"),
            *arguments,
        ],
        env=environment,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )


def test_live_supervisor_uses_one_fresh_complete_sql_observation(tmp_path):
    result = _supervisor_probe(tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "", "live admission must keep private identities private"
    assert (tmp_path / "calls").read_text().splitlines() == ["call"]
    query = (tmp_path / "queries").read_text()
    for authority in (
        "babylon.disposable_runtime",
        "pg_catalog.pg_database",
        "datdba",
        'COLLATE "C"',
        "bad_roles",
        "pg_catalog.pg_auth_members",
        "rolbypassrls",
        "bad_clients",
        "pid<>pg_backend_pid()",
    ):
        assert authority in query


@pytest.mark.parametrize(
    "fault",
    [
        "canary",
        "inventory",
        "owner",
        "clients_or_roles",
        "null",
        "empty",
        "extra_column",
        "extra_row",
    ],
)
def test_live_supervisor_refuses_incomplete_or_changed_sql_observation(tmp_path, fault):
    canary = "12" * 16
    inventory = f"babylon_test,national_{canary[:12]},postgres,template0,template1"
    fields = [canary, inventory, "42", "0"]
    if fault in {"canary", "inventory", "owner", "clients_or_roles", "null"}:
        column = {"canary": 0, "inventory": 1, "owner": 2, "clients_or_roles": 3, "null": 0}[fault]
        fields[column] = "" if fault == "null" else "changed"
    packet = "|".join(fields)
    if fault == "empty":
        packet = ""
    elif fault == "extra_column":
        packet += "|0"
    elif fault == "extra_row":
        packet += "\n" + packet
    result = _supervisor_probe(tmp_path, packet=packet)
    assert result.returncode != 0
    assert result.stdout == ""
    assert (tmp_path / "calls").read_text().splitlines() == ["call"]


@pytest.mark.parametrize("oid", ["", "42"])
def test_terminal_supervisor_preserves_private_identity_without_live_role_checks(tmp_path, oid):
    result = _supervisor_probe(tmp_path, oid=oid, live=False)
    assert result.returncode == 0, result.stderr
    canary = "12" * 16
    expected = (
        f"{'a1' * 32}|sha256:{'b2' * 32}|{canary}|owned-probe-volume\n"
        f"babylon_test,national_{canary[:12]},postgres,template0,template1\n"
    )
    assert result.stdout == expected
    assert (tmp_path / "calls").read_text().splitlines() == ["call"]
    assert "bad_clients" not in (tmp_path / "queries").read_text()


@pytest.mark.parametrize("arguments", [("unknown",), ("--live", "extra")])
def test_supervisor_refuses_unknown_or_extra_arguments_before_observation(tmp_path, arguments):
    result = _supervisor_probe(tmp_path, arguments=arguments, live=False)
    assert result.returncode != 0
    assert not (tmp_path / "calls").exists()


@pytest.mark.parametrize("oid", ["", "0", "042", "malformed"])
def test_live_supervisor_refuses_unadmitted_owner_identity_before_observation(tmp_path, oid):
    result = _supervisor_probe(tmp_path, oid=oid)
    assert result.returncode != 0
    assert result.stdout == ""
    assert not (tmp_path / "calls").exists()


@pytest.mark.parametrize("changed", [False, True])
def test_frozen_source_revalidation_never_replaces_original_capture(tmp_path, changed):
    """Real verification function over a bounded Designed source/input scope."""
    source = tmp_path / "source"
    source.write_text("captured source\n")
    frozen = tmp_path / "source-before.sha256"
    before = f"{hashlib.sha256(source.read_bytes()).hexdigest()}  {source}\n".encode()
    frozen.write_bytes(before)
    (tmp_path / "inputs.sha256").write_bytes(before)
    for name in ("source-archive", "input-archive"):
        archive = tmp_path / f"{name}.tar.gz"
        archive.write_bytes(b"Designed immutable capsule control")
        (tmp_path / f"{name}.sha256").write_text(
            f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive}\n"
        )
    if changed:
        source.write_text("source changed after original capture\n")
    result = subprocess.run(
        [
            "bash",
            "-c",
            'source "$1"; national_source_manifest() { sha256sum "$REPO_ROOT/source"; }; national_verify_source_capture',
            "verify-frozen-source",
            str(REPOSITORY / "tools/postgres_national_lifecycle.sh"),
        ],
        env={
            "PATH": os.defpath,
            "REPO_ROOT": str(tmp_path),
            "BABYLON_STORAGE_REPORT_DIRECTORY": str(tmp_path),
        },
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert (result.returncode == 0) == (not changed)
    assert frozen.read_bytes() == before
    assert not (tmp_path / "source-captured.sha256").exists()


@pytest.mark.parametrize("mode", ["", "national", "playable-aids", "raw-economic/extra"])
def test_unknown_capture_mode_refuses_before_preparing_game(tmp_path: Path, mode: str):
    tools = tmp_path / "tools"
    tools.mkdir()
    for name in ("run_rust_postgres.sh", "postgres_national_lifecycle.sh"):
        (tools / name).write_bytes((REPOSITORY / "tools" / name).read_bytes())
    evidence = tmp_path / "uncreated-evidence"
    environment = {
        "PATH": os.defpath,
        "BABYLON_POSTGRES_LIVE_FOCUS": "national_storage",
        "BABYLON_NATIONAL_CAPTURE_MODE": mode,
        "BABYLON_STORAGE_REPORT_DIRECTORY": str(evidence),
    }
    result = subprocess.run(
        ["bash", str(tools / "run_rust_postgres.sh")],
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 2
    assert "unsupported national capture mode" in result.stderr
    assert not evidence.exists()
    assert not (tmp_path / "reports/test-results/national-storage-runner").exists()


@pytest.mark.parametrize("requested,expected", [(None, "3"), ("1", "1"), ("325", "325")])
def test_default_period_count_uses_captured_routine_policy(tmp_path, requested, expected):
    data = json.loads(
        (REPOSITORY / "contracts/national_storage_qualification_v6.json").read_bytes()
    )
    data["routine_smoke_periods"] = 3
    (tmp_path / "policy.json").write_text(json.dumps(data))
    # Keep the actual shell admission path; only replace the toolchain launcher.
    launcher = tmp_path / "mise"
    launcher.write_text(
        '#!/bin/sh\nshift 5\n[ "$1" = python ] || exit 99\nshift\nexec '
        + shlex.quote(sys.executable)
        + ' "$@"\n'
    )
    launcher.chmod(0o700)
    environment = {
        "PATH": f"{tmp_path}:{os.defpath}",
        "BABYLON_STORAGE_REPORT_DIRECTORY": str(tmp_path),
    }
    if requested is not None:
        environment["BABYLON_NATIONAL_STORAGE_PERIODS"] = requested
    result = subprocess.run(
        [
            "bash",
            "-c",
            'source "$1"; national_period_count',
            "national-periods",
            str(REPOSITORY / "tools/postgres_national_lifecycle.sh"),
        ],
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected


@pytest.mark.parametrize(
    "mode,flag", [("report-only", ""), ("storage", "--qualify"), ("save", "--qualify-save")]
)
def test_explicit_storage_qualification_selects_current_evaluator_gate(mode, flag):
    result = subprocess.run(
        [
            "bash",
            "-c",
            'source "$1"; die() { echo "$*" >&2; exit 2; }; national_storage_qualification_selection; national_storage_qualification_flags "$NATIONAL_STORAGE_QUALIFICATION"',
            "qualification",
            str(REPOSITORY / "tools/postgres_national_lifecycle.sh"),
        ],
        env={"PATH": os.defpath, "BABYLON_NATIONAL_STORAGE_QUALIFICATION": mode},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == flag


@pytest.mark.parametrize("mode", ["", "1", "qualify", "storage/save"])
def test_unknown_storage_qualification_refuses_before_owned_game(tmp_path, mode):
    tools = tmp_path / "tools"
    tools.mkdir()
    for name in ("run_rust_postgres.sh", "postgres_national_lifecycle.sh"):
        (tools / name).write_bytes((REPOSITORY / "tools" / name).read_bytes())
    result = subprocess.run(
        ["bash", str(tools / "run_rust_postgres.sh")],
        env={
            "PATH": os.defpath,
            "BABYLON_POSTGRES_LIVE_FOCUS": "national_storage",
            "BABYLON_NATIONAL_STORAGE_QUALIFICATION": mode,
        },
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 2
    assert "unsupported national storage qualification" in result.stderr
    assert not (tmp_path / "reports").exists()


@pytest.mark.parametrize("mode,flag", [("storage", "--qualify"), ("save", "--qualify-save")])
@pytest.mark.parametrize("evaluator_exit", [0, 7])
@pytest.mark.parametrize("capture_mode", ["raw-economic", "playable-aid"])
@pytest.mark.parametrize("periods", [2, 3])
def test_actual_national_measure_forwards_gate_and_preserves_refusal(
    tmp_path, mode, flag, evaluator_exit, capture_mode, periods
):
    """Exercise the real publication path; synthetic files are not PG evidence."""
    policy = REPOSITORY / "contracts/national_storage_qualification_v6.json"
    (tmp_path / "policy.json").write_bytes(policy.read_bytes())
    (tmp_path / "storage-qualification-mode").write_text(mode + "\n")
    (tmp_path / "timing-qualification-mode").write_text("0\n")
    for name in (
        "schema-baseline.json",
        "opening-created.json",
        "native-timings.json",
    ):
        (tmp_path / name).write_text("{}\n")
    for tick in range(1, periods + 1):
        (tmp_path / f"tick-{tick:02}.json").write_text("{}\n")
        (tmp_path / f"tick-{tick:02}-reopened.json").write_text("{}\n")
    if capture_mode == "playable-aid":
        for name in (
            "national-capture-mode.json",
            "national-playable-qualification.json",
            "progress-000-starting.json",
            "reader-role",
            "observer-role",
        ):
            (tmp_path / name).write_text("{}\n")
        for tick in range(1, periods + 1):
            for boundary in ("committed", "archive", "accounting", "production", "reopened"):
                (tmp_path / f"progress-{tick:03}-{boundary}.json").write_text("{}\n")
    evaluator = tmp_path / "national_storage_qualification.py"
    evaluator.write_text(
        "import json,os,sys\n"
        "from pathlib import Path\n"
        "Path(os.environ['ARGUMENT_RECORD']).write_text(json.dumps(sys.argv[1:]))\n"
        "print(json.dumps({'status':'qualified'}))\n"
        "raise SystemExit(int(os.environ['EVALUATOR_EXIT']))\n"
    )
    launcher = tmp_path / "mise"
    launcher.write_text(
        '#!/bin/sh\nshift 5\n[ "$1" = python ] || exit 99\nshift\nexec '
        + shlex.quote(sys.executable)
        + ' "$@"\n'
    )
    launcher.chmod(0o700)
    # Preserve the actual operator/evidence hash checks instead of stubbing them.
    frozen = (
        "policy.json",
        "storage-qualification-mode",
        "timing-qualification-mode",
        evaluator.name,
    )
    (tmp_path / "operator.sha256").write_text(
        "".join(
            f"{hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()}  {name}\n"
            for name in frozen
        )
    )
    arguments = tmp_path / "evaluator-arguments.json"
    result = subprocess.run(
        [
            "bash",
            "-c",
            'source "$1"; national_storage_qualification_selection; '
            "NATIONAL_QUALIFY_TIMING=0; national_measure",
            "measure-wiring",
            str(REPOSITORY / "tools/postgres_national_lifecycle.sh"),
        ],
        env={
            "PATH": f"{tmp_path}:{os.defpath}",
            "BABYLON_STORAGE_REPORT_DIRECTORY": str(tmp_path),
            "BABYLON_NATIONAL_CAPTURE_MODE": capture_mode,
            "BABYLON_NATIONAL_STORAGE_QUALIFICATION": mode,
            "BABYLON_NATIONAL_STORAGE_PERIODS": str(periods),
            "ARGUMENT_RECORD": str(arguments),
            "EVALUATOR_EXIT": str(evaluator_exit),
        },
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    actual = json.loads(arguments.read_bytes())
    assert actual.count(flag) == 1
    if capture_mode == "playable-aid":
        assert actual.count("--qualify-playable") == int(periods > 2)
        assert actual[actual.index("--playable-report") + 1] == str(
            tmp_path / "national-playable-qualification.json"
        )
    else:
        assert "--qualify-playable" not in actual
        assert "--playable-report" not in actual
    assert ("--qualify-save" if flag == "--qualify" else "--qualify") not in actual
    assert ("--qualify-smoke" in actual) == (periods == 2)
    assert "--qualify-timing" not in actual
    assert actual[actual.index("--policy") + 1] == str(tmp_path / "policy.json")
    published = tmp_path / "qualification.json"
    sealed = tmp_path / "evaluated-evidence.sha256"
    if evaluator_exit:
        assert result.returncode != 0
        assert not published.exists()
        assert not sealed.exists()
        assert (tmp_path / "qualification.json.partial").exists()
        assert (tmp_path / "evaluated-evidence.sha256.partial").exists()
    else:
        assert result.returncode == 0, result.stderr
        assert json.loads(published.read_bytes())["status"] == "qualified"
        assert sealed.exists()
        assert not (tmp_path / "qualification.json.partial").exists()


def national_linked_checkouts(tmp_path):
    repository = tmp_path / "repository"
    linked = tmp_path / "linked"
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "-c",
            "user.name=Proof",
            "-c",
            "user.email=proof@example.invalid",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "proof",
        ],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repository), "worktree", "add", "-q", "-b", "linked", str(linked)],
        check=True,
    )
    return repository, linked


def national_guard(checkout, command="national_existing_game_guard"):
    return subprocess.run(
        [
            "bash",
            "-c",
            'source "$1"; REPO_ROOT="$2"; die() { printf "%s\\n" "$*" >&2; exit 2; }; ' + command,
            "lease-proof",
            str(REPOSITORY / "tools/postgres_national_lifecycle.sh"),
            str(checkout),
        ],
        env={"PATH": os.defpath},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def test_linked_worktrees_share_national_control_directory(tmp_path):
    repository, linked = national_linked_checkouts(tmp_path)
    outputs = [
        national_guard(path, "national_control_directory").stdout.strip()
        for path in (repository, linked)
    ]
    assert outputs == [str(repository / ".git/babylon-national-storage")] * 2
    assert not Path(outputs[0]).exists()


def test_foreign_legacy_game_refuses_without_creation_or_secret_leak(tmp_path):
    repository, linked = national_linked_checkouts(tmp_path)
    record = linked / "reports/test-results/national-storage-runner/active"
    record.parent.mkdir(parents=True)
    secret = b"legacy-canary-credential-private\n"
    record.write_bytes(secret)
    result = national_guard(repository)
    assert result.returncode == 2
    assert "retained national" in result.stderr
    assert secret.decode().strip() not in result.stdout + result.stderr
    assert record.read_bytes() == secret
    assert not (repository / ".git/babylon-national-storage").exists()
    assert not (repository / "reports").exists()


def test_retained_global_game_refuses_without_reading_or_replacing_record(tmp_path):
    repository, linked = national_linked_checkouts(tmp_path)
    record = repository / ".git/babylon-national-storage/active"
    record.parent.mkdir()
    secret = b"global-canary-credential-private\n"
    record.write_bytes(secret)
    result = national_guard(linked)
    assert result.returncode == 2
    assert "retained national" in result.stderr
    assert secret.decode().strip() not in result.stdout + result.stderr
    assert record.read_bytes() == secret
    assert list(record.parent.iterdir()) == [record]
    assert not (linked / "reports").exists()


def test_real_global_flock_conflicts_across_linked_worktrees(tmp_path):
    repository, linked = national_linked_checkouts(tmp_path)
    control = repository / ".git/babylon-national-storage"
    control.mkdir()
    holder = subprocess.Popen(
        [
            "flock",
            "--close",
            str(control / "runner.lock"),
            "bash",
            "-c",
            'printf "locked\\n"; read -r line',
            "held",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    try:
        assert holder.stdout is not None
        readable, _, _ = select.select([holder.stdout], [], [], 3)
        assert readable, "actual lock-holder readiness within the three-second bound"
        assert holder.stdout.readline() == b"locked\n"
        result = national_guard(linked, "national_lock_entry")
        assert result.returncode == 75
        assert not (linked / "reports").exists()
        assert not (control / "active").exists()
    finally:
        holder.communicate(b"release\n", timeout=5)


def test_failure_summary_is_atomic_secret_safe_and_preserves_existing_proof(tmp_path):
    secret = "private-credential-should-never-appear"
    (tmp_path / "ownership").write_text(secret)
    (tmp_path / "native-timings.json").write_text("{}\n")
    progress = tmp_path / "progress-002-archive.json"
    progress.write_text("{}\n")
    proof = tmp_path / "qualification.json"
    proof.write_text('{"status":"earlier-proof"}\n')
    command = 'BABYLON_STORAGE_REPORT_DIRECTORY="$REPO_ROOT"; national_failure_summary 143'
    first = national_guard(tmp_path, command)
    assert first.returncode == 0, first.stderr
    summary = tmp_path / "failure-summary.json"
    captured = summary.read_bytes()
    result = json.loads(captured)
    assert result["status"] == "failure-retained"
    assert result["exit_code"] == 143
    assert result["latest_progress"] == progress.name
    assert secret not in captured.decode() + first.stdout + first.stderr
    assert proof.read_text() == '{"status":"earlier-proof"}\n'
    second = national_guard(tmp_path, command.replace("143", "2"))
    assert second.returncode == 0
    assert summary.read_bytes() == captured
    assert not list(tmp_path.glob(".failure-summary-*"))


def test_real_flock_supervisor_proves_common_inode_and_closes_child_descriptor(tmp_path):
    repository, linked = national_linked_checkouts(tmp_path)
    tools = linked / "tools"
    tools.mkdir()
    runner = tools / "run_rust_postgres.sh"
    runner.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        f"REPO_ROOT={shlex.quote(str(linked))}\n"
        f"source {shlex.quote(str(REPOSITORY / 'tools/postgres_national_lifecycle.sh'))}\n"
        'die() { printf "%s\\n" "$*" >&2; exit 2; }\n'
        'national_lock_entry "$@"\n'
        'identity="$(stat -Lc "%d:%i" "$(national_control_directory)/runner.lock")"\n'
        "for descriptor in /proc/$$/fd/*; do\n"
        '  [ "$(stat -Lc "%d:%i" "$descriptor" 2>/dev/null || true)" != "$identity" ] || exit 99\n'
        'done\nprintf "verified\\n"\n'
    )
    result = subprocess.run(
        ["bash", str(runner)],
        env={"PATH": os.defpath},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "verified" in result.stdout
    assert (repository / ".git/babylon-national-storage/runner.lock").exists()
    assert not (linked / "reports").exists()


def test_playable_game_startup_admits_separate_confined_reader_credential(tmp_path):
    """Exercise shell role/credential wiring with a fake connection, never PostgreSQL."""
    launcher = tmp_path / "mise"
    launcher.write_text(
        f"#!{sys.executable}\n"
        "import json,os,sys,types\n"
        "from pathlib import Path\n"
        "from urllib.parse import urlparse\n"
        "class Connection:\n"
        " def __enter__(self): return self\n"
        " def __exit__(self,*args): return False\n"
        " def execute(self,query): return self\n"
        " def fetchone(self): return (False,)*5\n"
        "def connect(dsn,**kwargs):\n"
        " assert kwargs == {'connect_timeout':10,'options':'-c event_triggers=off'}\n"
        " record=Path(os.environ['CREDENTIAL_RECORD'])\n"
        " rows=json.loads(record.read_text()) if record.exists() else []\n"
        " rows.append(urlparse(dsn).username); record.write_text(json.dumps(rows))\n"
        " return Connection()\n"
        "sys.modules['psycopg']=types.SimpleNamespace(connect=connect,Error=Exception)\n"
        "exec(sys.stdin.read())\n"
    )
    launcher.chmod(0o700)
    sql = tmp_path / "sql-record"
    credentials = tmp_path / "credential-record"
    canary = "1234567890abcdef1234567890abcdef"
    result = subprocess.run(
        [
            "bash",
            "-c",
            'source "$1"; die() { printf "%s\\n" "$*" >&2; exit 2; }; '
            'national_record() { :; }; national_sql() { case "$1" in "SELECT oid "*) printf "42\\n";; '
            '*) printf "%s\\n" "$1" >> "$SQL_RECORD";; esac; }; national_create_game',
            "credential-proof",
            str(REPOSITORY / "tools/postgres_national_lifecycle.sh"),
        ],
        env={
            "PATH": f"{tmp_path}:{os.defpath}",
            "CANARY": canary,
            "PORT": "9999",
            "NATIONAL_DATABASE": "national_proof",
            "NATIONAL_WRITER": "national_writer_proof",
            "BABYLON_NATIONAL_CAPTURE_MODE": "playable-aid",
            "SQL_RECORD": str(sql),
            "CREDENTIAL_RECORD": str(credentials),
            "BABYLON_STORAGE_REPORT_DIRECTORY": str(tmp_path),
        },
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    reader = "national_reader_1234567890ab"
    observer = "national_observer_1234567890ab"
    assert json.loads(credentials.read_bytes()) == ["national_writer_proof", observer, reader]
    commands = sql.read_text()
    assert f"GRANT SET ON PARAMETER event_triggers TO {reader};" in commands
    assert "IN ROLE babylon_reader;" in commands
    assert "NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS" in commands
    assert (tmp_path / "reader-role").read_text() == reader + "\n"
    assert canary not in result.stdout + result.stderr


@pytest.mark.parametrize("choice", ["", "keep", "retain", "retain-for-native/extra"])
def test_native_retention_disposition_refuses_unknown_choice(tmp_path, choice):
    result = subprocess.run(
        [
            "bash",
            "-c",
            'source "$1"; die() { exit 2; }; national_success_selection',
            "selection",
            str(REPOSITORY / "tools/postgres_national_lifecycle.sh"),
        ],
        env={
            "PATH": os.defpath,
            "BABYLON_NATIONAL_SUCCESS_DISPOSITION": choice,
            "BABYLON_POSTGRES_LIVE_FOCUS": "national_storage",
            "BABYLON_NATIONAL_CAPTURE_MODE": "playable-aid",
        },
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == 2


@pytest.mark.parametrize(
    "focus,mode", [("reader", "playable-aid"), ("national_storage", "raw-economic")]
)
def test_native_retention_requires_owned_playable_national_scope(focus, mode):
    result = subprocess.run(
        [
            "bash",
            "-c",
            'source "$1"; die() { exit 2; }; national_success_selection',
            "selection",
            str(REPOSITORY / "tools/postgres_national_lifecycle.sh"),
        ],
        env={
            "PATH": os.defpath,
            "BABYLON_NATIONAL_SUCCESS_DISPOSITION": "retain-for-native",
            "BABYLON_POSTGRES_LIVE_FOCUS": focus,
            "BABYLON_NATIONAL_CAPTURE_MODE": mode,
        },
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == 2


@pytest.mark.parametrize("passed", [True, False])
def test_native_success_retention_keeps_lease_and_never_freezes_database(tmp_path, passed):
    (tmp_path / "active").write_text("private lease preimage")
    (tmp_path / "campaign").write_text("00000000-0000-0000-0000-000000000001\n")
    (tmp_path / "qualification.json").write_text(
        json.dumps({"status": "incomplete", "required_ticks": 52})
    )
    (tmp_path / "policy.json").write_text(
        json.dumps({"qualification_ticks": 52, "routine_smoke_periods": 2})
    )
    (tmp_path / "native-timings.json").write_text(json.dumps({"run": {"periods": 2}}))
    (tmp_path / "evaluated-evidence.sha256").write_text("public evidence manifest")
    (tmp_path / "tick-02-reopened.json").write_text(
        json.dumps({"acknowledged_markers": {"material": {"tick": 2, "hash": "terminal"}}})
    )
    launcher = tmp_path / "mise"
    launcher.write_text(
        '#!/bin/sh\nshift 5\n[ "$1" = python ] || exit 99\nshift\nexec '
        + shlex.quote(sys.executable)
        + ' "$@"\n'
    )
    launcher.chmod(0o700)
    script = (
        'source "$1"; NATIONAL_RECORD="$2/active"; NATIONAL_DATABASE_OID=42; '
        "national_verify_success() { return " + ("0" if passed else "1") + "; }; "
        'national_sql() { printf "unexpected SQL" >&2; return 99; }; '
        "national_retain_success"
    )
    result = subprocess.run(
        [
            "bash",
            "-c",
            script,
            "retention",
            str(REPOSITORY / "tools/postgres_national_lifecycle.sh"),
            str(tmp_path),
        ],
        env={"PATH": f"{tmp_path}:{os.defpath}", "BABYLON_STORAGE_REPORT_DIRECTORY": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert (result.returncode == 0) is passed
    assert (tmp_path / "active").read_text() == "private lease preimage"
    assert "unexpected SQL" not in result.stderr
    if passed:
        receipt = json.loads((tmp_path / "native-handoff.json").read_text())
        assert receipt["scope"] == "routine-smoke"
        assert receipt["status"] == "success-retained-for-native"
        assert receipt["qualification_status"] == "incomplete"
        assert "private lease preimage" not in json.dumps(receipt)
    else:
        assert not (tmp_path / "native-handoff.json").exists()


def test_native_handoff_requires_explicit_canonical_existing_campaign(tmp_path):
    result = subprocess.run(
        ["bash", str(REPOSITORY / "tools/run_rust_postgres.sh"), "--national-native-open", "new"],
        env={"PATH": os.defpath},
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == 2
    assert "existing campaign" in result.stderr


@pytest.mark.parametrize(
    "fault", [None, "campaign", "evidence", "missing-digest", "unexpected-digest"]
)
def test_native_handoff_receipt_refuses_changed_or_incomplete_evidence(tmp_path, fault):
    campaign = "00000000-0000-0000-0000-000000000001"
    files = {
        "qualification.json": {"status": "incomplete"},
        "native-timings.json": {"run": {"periods": 2}},
        "policy.json": {"qualification_ticks": 52},
        "tick-02-reopened.json": {"acknowledged_markers": {"material": 2}},
    }
    for name, value in files.items():
        (tmp_path / name).write_text(json.dumps(value))
    (tmp_path / "campaign").write_text(campaign + "\n")
    (tmp_path / "evaluated-evidence.sha256").write_text("bounded manifest")
    digests = {
        name: hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()
        for name in [*files, "campaign", "evaluated-evidence.sha256"]
    }
    receipt = {
        "version": 1,
        "status": "success-retained-for-native",
        "periods": 2,
        "campaign": campaign,
        "evidence_sha256": digests,
    }
    if fault == "campaign":
        receipt["campaign"] = "00000000-0000-0000-0000-000000000002"
    elif fault == "evidence":
        (tmp_path / "qualification.json").write_text('{"status":"qualified"}')
    elif fault == "missing-digest":
        del digests["campaign"]
    elif fault == "unexpected-digest":
        digests["outside"] = "0" * 64
    (tmp_path / "native-handoff.json").write_text(json.dumps(receipt))
    source = (REPOSITORY / "tools/postgres_national_lifecycle.sh").read_text()
    # Execute the actual refusal code, with no shell, service, or native worker.
    program = source.split("<<'PY_VERIFY'\n", 1)[1].split("\nPY_VERIFY", 1)[0]
    result = subprocess.run(
        [sys.executable, "-", str(tmp_path), campaign],
        input=program,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert (result.returncode == 0) is (fault is None)


@pytest.mark.parametrize("fault", [None, "missing", "digest", "scope"])
def test_native_handoff_binary_admission_refuses_before_process_pair(tmp_path, fault):
    tools = tmp_path / "tools"
    binaries = tmp_path / "rust/target/debug"
    tools.mkdir()
    binaries.mkdir(parents=True)
    (tools / "run_observer_session.py").write_text(
        "from pathlib import Path\n"
        "DEFAULT_DEFINES = Path('defines')\n"
        "def ReaderCredentials(*args): return args\n"
        "def OpenCampaignTarget(value): return value\n"
        "def child_environments(environment, credentials): return {}, {}\n"
        "def run_pair(*args, **kwargs):\n"
        "    (args[2] / 'pair-called').write_text('existing-only')\n"
        "    return 0\n"
    )
    names = [binaries / "babylon-runtime", binaries / "babylon-client"]
    for name in names:
        name.write_bytes(b"owned executable preimage")
    manifest = tmp_path / "native-executables.sha256"
    rows = [(hashlib.sha256(name.read_bytes()).hexdigest(), str(name)) for name in names]
    if fault == "digest":
        names[0].write_bytes(b"changed executable")
    elif fault == "scope":
        rows.pop()
    if fault != "missing":
        manifest.write_text("".join(f"{digest}  {name}\n" for digest, name in rows))
    source = (REPOSITORY / "tools/postgres_national_lifecycle.sh").read_text()
    program = source.split("<<'PY_OPEN'\n", 1)[1].split("\nPY_OPEN", 1)[0]
    result = subprocess.run(
        [sys.executable, "-", str(tmp_path), "00000000-0000-0000-0000-000000000001"],
        input=program,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
        env={
            "PATH": os.defpath,
            "BABYLON_STORAGE_REPORT_DIRECTORY": str(tmp_path),
            "BABYLON_OBSERVER_DSN": "private-observer",
            "BABYLON_READER_DSN": "private-reader",
        },
    )
    assert (result.returncode == 0) is (fault is None)
    assert (tmp_path / "pair-called").exists() is (fault is None)
    assert "private-observer" not in result.stdout + result.stderr
    assert "private-reader" not in result.stdout + result.stderr
