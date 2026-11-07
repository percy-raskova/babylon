"""Synthetic admission and retention checks, without a Docker daemon or database."""

from pathlib import Path

import pytest
from tools.devtools import wayne_qualification_storage as storage


def test_three_media_profiles_require_the_exact_run_and_horizon() -> None:
    for profile, focus, periods, leaf in (
        ("sql-01", "organizer_allocation_atomic", "", "sql-01"),
        ("smoke-01", "national_storage", "2", "smoke-01"),
        ("walk-01", "national_storage", "10", "walk-01"),
    ):
        evidence = storage.RUN_PARENT / leaf / "evidence"
        assert storage.profile_run(profile, focus, periods, evidence) == evidence.parent
        with pytest.raises(storage.StorageRefusal):
            storage.profile_run(profile, focus, periods, evidence / "..")
        with pytest.raises(storage.StorageRefusal):
            storage.profile_run(profile, focus, "9", evidence)


def test_test_result_binds_the_ignored_case_and_exact_pass_count() -> None:
    result = (
        f"\nrunning 1 test\ntest {storage.TEST_NAME} ... ok\n\n"
        "test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 47 filtered out; "
        "finished in 2.53s\n"
    ).encode()
    storage.verify_transcript(result, 0)
    for changed in [
        result.replace(b"1 passed", b"0 passed"),
        result.replace(b"0 ignored", b"1 ignored"),
        result.replace(b"... ok", b"... ignored"),
        result.replace(storage.TEST_NAME.encode(), b"some_other_test"),
        result + result,
    ]:
        with pytest.raises(storage.StorageRefusal):
            storage.verify_transcript(changed, 0)
    with pytest.raises(storage.StorageRefusal):
        storage.verify_transcript(result, 1)


def test_evidence_reference_refuses_replacement_escape_and_unsealed_bytes(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    root = storage.PrivateEvidence(tmp_path)
    reference = root.publish("stage.json", b'{"actual": 3}\n')
    assert root.read_reference(reference) == b'{"actual": 3}\n'
    with pytest.raises(FileExistsError):
        root.publish("stage.json", b"replacement")
    (tmp_path / "linked.json").symlink_to(tmp_path / "stage.json")
    for path in ["../stage.json", "linked.json", "/stage.json", "a/../stage.json"]:
        with pytest.raises((storage.StorageRefusal, OSError)):
            root.read_reference(reference.model_copy(update={"path": path}))
    (tmp_path / "stage.json").write_bytes(b'{"actual": 4}\n')
    with pytest.raises(storage.StorageRefusal):
        root.read_reference(reference)


@pytest.mark.parametrize("profile", ["sql-01", "smoke-01", "walk-01"])
def test_new_container_wal_senders_profile_is_scoped_to_native_create(
    tmp_path, monkeypatch, profile
):
    from contextlib import nullcontext

    run = tmp_path / profile
    (run / "pgdata").mkdir(parents=True)
    recorded = []
    monkeypatch.setattr(storage, "pinned_ancestry", lambda _path: nullcontext([]))
    monkeypatch.setattr(
        storage,
        "_media_creation",
        lambda *_args: {"profile": profile, "creator": storage._host_identity(run / "pgdata")},
    )

    class StopAfterCreate(Exception):
        pass

    def capture(command, **_kwargs):
        recorded.extend(command)
        raise StopAfterCreate

    monkeypatch.setattr(storage, "exact_output", capture)
    with pytest.raises(StopAfterCreate):
        storage.create_and_start(
            storage.PrivateEvidence(run / "evidence"), tmp_path, "a" * 32, "sha256:" + "b" * 64
        )
    assert recorded[:2] == ["docker", "create"]
    assert ("max_wal_senders=0" in recorded) == (profile != "sql-01")
    if profile != "sql-01":
        assert recorded[-2:] == ["-c", "max_wal_senders=0"]


@pytest.mark.parametrize("actual", [None, ("1",), ("00",), (False,), ("0",)])
def test_physical_native_wal_sender_setting_requires_actual_exact_zero(actual):
    if actual == ("0",):
        assert storage.native_wal_senders(actual) == 0
    else:
        with pytest.raises(storage.StorageRefusal, match="WAL senders"):
            storage.native_wal_senders(actual)


def test_sql_supervisor_mask_reaches_real_private_manifest_reader(tmp_path):
    import os
    import subprocess

    repo = Path(__file__).resolve().parents[3]
    evidence = tmp_path / "evidence"
    evidence.mkdir(mode=0o700)
    (tmp_path / "item").write_bytes(b"fixture")
    # BASH_ENV intercepts the first media call inside the ordinary supervisor.
    # Exercise actual shell manifest publication using tiny file rosters only.
    hook = tmp_path / "shell-init"
    hook.write_text(
        """umask 022
mise() {
  [[ " $* " == *" reserve "* ]] || return 91
  REPO_ROOT_COPY="$TMP_CAPTURE_REPO"
  ( unset -f mise; bash -c '
    unset BASH_ENV
    source "$1"
    REPO_ROOT="$2"; CANARY=abc
    national_source_paths(){ printf "item\\0"; }
    national_input_paths(){ printf "item\\0"; }
    national_source_manifest(){ (cd "$REPO_ROOT" && sha256sum item); }
    national_reproducibility
  ' capture "$REPO_ROOT/tools/postgres_national_lifecycle.sh" "$REPO_ROOT_COPY" )
  return 71
}
""".replace("unset -f mise; bash", "unset -f mise; BASH_ENV= bash")
    )
    result = subprocess.run(
        ["bash", str(repo / "tools/run_rust_postgres.sh")],
        env={
            **os.environ,
            "BASH_ENV": str(hook),
            "BABYLON_WAYNE_PROFILE": "sql-01",
            "BABYLON_POSTGRES_LIVE_FOCUS": "organizer_allocation_atomic",
            "BABYLON_STORAGE_REPORT_DIRECTORY": str(evidence),
            "TMP_CAPTURE_REPO": str(tmp_path),
        },
        capture_output=True,
    )
    assert result.returncode == 71, result.stderr
    directory = storage.PrivateEvidence(evidence)
    for name in ("source-before.sha256", "inputs.sha256"):
        assert directory.reference(name).bytes > 0


def test_released_head_refuses_clean_drift_before_create(tmp_path, monkeypatch):
    directory = storage.PrivateEvidence(tmp_path)
    tmp_path.chmod(0o700)
    directory.publish_json(
        "media-creation.json",
        {"source_head": "1" * 40, "profile": "sql-01", "capacity": {"source_head": "1" * 40}},
    )
    monkeypatch.setattr(
        storage, "exact_output", lambda command: "2" * 40 if "HEAD" in command else ""
    )
    with pytest.raises(storage.StorageRefusal, match="released"):
        storage.released_head(directory, tmp_path)


def test_selected_policy_refuses_coherent_alternate_ceiling(tmp_path):
    policy = (
        Path(__file__).resolve().parents[3] / "contracts/national_storage_qualification_v6.json"
    )
    changed = tmp_path / "policy.json"
    changed.write_bytes(
        policy.read_bytes().replace(
            b'"maximum_cold_open_seconds": 180', b'"maximum_cold_open_seconds": 999'
        )
    )
    with pytest.raises(ValueError, match="released v6"):
        storage.selected_policy(changed)
    storage.selected_policy(policy)


def test_duplicate_owning_gid_cannot_erase_effective_write_search(tmp_path, monkeypatch):
    from types import SimpleNamespace

    info = tmp_path.stat()
    monkeypatch.setattr(Path, "read_text", lambda *_: "passwd: files\ngroup: files\n")
    outside = SimpleNamespace(pw_uid=7777, pw_gid=info.st_gid, pw_name="outside")
    monkeypatch.setattr(storage.pwd, "getpwall", lambda: [outside])
    monkeypatch.setattr(storage.grp, "getgrgid", lambda _gid: SimpleNamespace(gr_mem=["outside"]))
    monkeypatch.setattr(storage.os, "getgrouplist", lambda *_: [info.st_gid])
    acl = [(4, 3, 0), (8, 0, info.st_gid), (16, 7, 0), (32, 0, 0)]
    with pytest.raises(storage.StorageRefusal, match="group"):
        storage._can_replace(info, acl, info.st_uid)


def test_proc_mask_over_numeric_row_refuses_full_host_view():
    lines = "99 1 0:9 / /proc rw - proc proc rw\n101 99 0:9 /6 /proc/180/comm rw - proc proc rw\n"
    with pytest.raises(storage.StorageRefusal, match="submount"):
        storage.host_proc_mount(lines)


def test_peer_bind_even_on_same_device_refuses_ancestry():
    media = storage.DirectoryPin(
        path="/media",
        major=1,
        minor=1,
        inode=7,
        uid=1,
        gid=1,
        mode=448,
        mount_id=3,
        access_acl=[],
        default_acl=[],
    )
    child = media.model_copy(update={"path": "/media/child", "mount_id": 7})
    with pytest.raises(storage.StorageRefusal, match="mount"):
        storage.check_media_mount(media, [media, child])


def test_physical_repeat_reuses_only_admitted_template1_connection(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(
        storage, "_connect", lambda *_a, **_kw: pytest.fail("opened an unaccounted connection")
    )
    conn = SimpleNamespace(
        info=SimpleNamespace(host="127.0.0.1", port=49157, dbname="template1", user="test")
    )
    with storage.physical_session(49157, conn) as actual:
        assert actual is conn
    conn.info.port = 49158
    with (
        pytest.raises(storage.StorageRefusal, match="maintenance"),
        storage.physical_session(49157, conn),
    ):
        pytest.fail("wrong endpoint used")


def test_known_human_refuses_before_reserving_new_run(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setattr(storage, "MEDIA_CHECKOUT", root)
    monkeypatch.setattr(storage, "RUN_PARENT", tmp_path / "new-runs")
    monkeypatch.setattr(storage, "profile_run", lambda *_args: storage.RUN_PARENT / "smoke-01")
    monkeypatch.setattr(storage, "selected_policy", lambda _path: None)

    def human():
        raise storage.StorageRefusal("active Babylon process")

    monkeypatch.setattr(storage, "actual_host_context", human)
    monkeypatch.setattr(
        storage, "_daemon_endpoint", lambda: pytest.fail("human present: daemon reached")
    )
    for name in tuple(storage.os.environ):
        if name.startswith("PG") or name.endswith("_DSN") or name == "CARGO_TARGET_DIR":
            monkeypatch.delenv(name)
    with pytest.raises(storage.StorageRefusal, match="active Babylon"):
        storage.reserve_run(
            "smoke-01", "national_storage", "2", storage.RUN_PARENT / "smoke-01/evidence", root
        )
    assert not storage.RUN_PARENT.exists()


def test_same_names_different_native_oids_refuse_owner_reauthentication(tmp_path, monkeypatch):
    directory = storage.PrivateEvidence(tmp_path)
    directory.publish_json("native-role-oids.json", {"national_reader_abc": 12})
    monkeypatch.setattr(storage, "_current_physical", lambda *_a, **_kw: {"port": 49157})
    monkeypatch.setattr(storage, "native_roles", lambda *_a, **_kw: {"national_reader_abc": 13})
    with pytest.raises(storage.StorageRefusal, match="role OID changed"):
        storage.owner_lines(directory, tmp_path, "abc", "id", "img", "42")


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "image_signal",
        "container_signal",
        "pid",
        "oldlog",
        "wrong_order",
        "late",
        "timeout",
        "bind",
    ],
)
def test_held_slot_stop_requires_exact_fast_configuration_and_current_clean_stop(
    tmp_path, monkeypatch, fault
):
    import subprocess
    from contextlib import nullcontext
    from datetime import UTC, datetime, timedelta
    from types import SimpleNamespace

    cid, label, image = "a" * 64, "c" * 32, "sha256:" + "b" * 64
    run = tmp_path / "walk-01"
    evidence = storage.PrivateEvidence(run / "evidence")
    evidence.path.mkdir(parents=True, mode=0o700)
    pg = {"inode": 32}
    physical = {
        "container": cid,
        "image": {"id": image},
        "label": label,
        "host": pg,
        "pid": 303,
        "mounts": [],
        "port_request": {},
        "server_uid": 23,
        "server_gid": 24,
    }
    evidence.publish_json("physical.json", physical)
    monkeypatch.setattr(storage, "pinned_ancestry", lambda _path: nullcontext([]))
    monkeypatch.setattr(storage, "_media_creation", lambda *_args: {"image": {"id": image}})
    monkeypatch.setattr(
        storage, "container_mounts", lambda *_args: {"mounts": [], "port_request": {}}
    )
    monkeypatch.setattr(
        storage,
        "_host_identity",
        lambda _path: {"inode": 33} if stopped and fault == "bind" else pg,
    )
    monkeypatch.setattr(storage, "RUN_PARENT", tmp_path)
    stopped = False
    records = []

    def inspect(kind, ident):
        if kind == "image":
            return {
                "Id": image,
                "Config": {"StopSignal": "SIGTERM" if fault == "image_signal" else "SIGINT"},
            }
        return {
            "Id": cid,
            "Image": image,
            "Config": {"StopSignal": "SIGTERM" if fault == "container_signal" else "SIGINT"},
            "State": {
                "Status": "exited" if stopped else "running",
                "Running": not stopped,
                "Pid": 0 if stopped else 303,
                "ExitCode": 0,
                "OOMKilled": False,
                "FinishedAt": datetime.now(UTC).isoformat(),
            },
        }

    monkeypatch.setattr(storage, "_one_docker", inspect)

    def command(args, **kw):
        nonlocal stopped
        records.append(args)
        if "stop" in args:
            assert args == ["docker", "stop", "--time", "-1", cid]
            if fault == "timeout":
                raise subprocess.TimeoutExpired(args, 90)
            stopped = True
            return cid
        if args[-1] == "/proc/1/status":
            return "Name:\tpostgres\nPid:\t1\nUid:\t23 23 23 23\nGid:\t24 24 24 24"
        if args[-1] == "/proc/1/exe":
            return "/sbin/sleep" if fault == "pid" else "/usr/local/bin/postgres"
        if args[-1] == "postgres":
            return "/usr/local/bin/postgres"
        pytest.fail(str(args))

    monkeypatch.setattr(storage, "exact_output", command)

    def logs(args, **kw):
        assert args[:3] == ["docker", "logs", "--timestamps"] and "--since" in args
        stamp = datetime.fromisoformat(args[args.index("--since") + 1])
        if fault == "oldlog":
            stamp -= timedelta(seconds=1)
        if fault == "late":
            stamp += timedelta(seconds=90)
        lines = ["received fast shutdown request", "database system is shut down"]
        if fault == "wrong_order":
            lines.reverse()
        return SimpleNamespace(
            stdout=b"",
            stderr="".join(f"{stamp.isoformat()} [1] LOG:  {line}\n" for line in lines).encode(),
        )

    monkeypatch.setattr(storage.subprocess, "run", logs)
    if fault is None:
        storage.stop_checked(evidence, cid, fenced_image=image)
        assert evidence.reference("native-fenced-stop-v1.json")
    else:
        with pytest.raises((storage.StorageRefusal, subprocess.TimeoutExpired)):
            storage.stop_checked(evidence, cid, fenced_image=image)
        assert not (evidence.path / "native-fenced-stop-v1.json").exists()
    stops = [args for args in records if "stop" in args]
    assert len(stops) == (0 if fault in ("image_signal", "container_signal", "pid") else 1)
    assert not any("rm" in args or "kill" in args for args in records)
