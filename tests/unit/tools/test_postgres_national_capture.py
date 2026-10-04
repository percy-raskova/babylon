"""Invalid capture selections must refuse before owned-game preparation."""

import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]


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
        (REPOSITORY / "contracts/national_storage_qualification_v2.json").read_bytes()
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
def test_actual_national_measure_forwards_gate_and_preserves_refusal(
    tmp_path, mode, flag, evaluator_exit, capture_mode
):
    """Exercise the real publication path; synthetic files are not PG evidence."""
    policy = REPOSITORY / "contracts/national_storage_qualification_v2.json"
    (tmp_path / "policy.json").write_bytes(policy.read_bytes())
    (tmp_path / "storage-qualification-mode").write_text(mode + "\n")
    (tmp_path / "timing-qualification-mode").write_text("0\n")
    for name in (
        "schema-baseline.json",
        "opening-created.json",
        "native-timings.json",
        "tick-01.json",
        "tick-01-reopened.json",
        "tick-02.json",
        "tick-02-reopened.json",
    ):
        (tmp_path / name).write_text("{}\n")
    if capture_mode == "playable-aid":
        for name in (
            "national-capture-mode.json",
            "national-playable-qualification.json",
            "progress-000-starting.json",
            "reader-role",
            "observer-role",
        ):
            (tmp_path / name).write_text("{}\n")
        for tick in (1, 2):
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
            "BABYLON_NATIONAL_STORAGE_PERIODS": "2",
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
        assert actual.count("--qualify-playable") == 1
        assert actual[actual.index("--playable-report") + 1] == str(
            tmp_path / "national-playable-qualification.json"
        )
    else:
        assert "--qualify-playable" not in actual
        assert "--playable-report" not in actual
    assert ("--qualify-save" if flag == "--qualify" else "--qualify") not in actual
    assert "--qualify-smoke" in actual
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
    ready = tmp_path / "lock-ready"
    holder = subprocess.Popen(
        [
            "flock",
            "--close",
            str(control / "runner.lock"),
            "bash",
            "-c",
            'touch "$1"; read -r line',
            "held",
            str(ready),
        ],
        stdin=subprocess.PIPE,
    )
    try:
        import time

        deadline = time.monotonic() + 3
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert ready.exists()
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
