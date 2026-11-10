"""Synthetic admission and retention checks, without a Docker daemon or database."""

from pathlib import Path

import pytest
from tools.devtools import wayne_qualification_storage as storage


@pytest.mark.parametrize("mode", ["normal_play", "memory_capture"])
def test_three_media_profiles_require_the_exact_run_and_horizon(monkeypatch, mode) -> None:
    monkeypatch.setenv("BABYLON_NATIVE_MEASUREMENT_MODE", mode)
    for profile, focus, periods, leaf in (
        ("sql-01", "organizer_allocation_atomic", "", "sql-01"),
        ("smoke-01", "national_storage", "2", "smoke-01"),
        ("walk-01", "national_storage", "10", "walk-01"),
    ):
        lane = Path("/media/user/data/worktrees/per364-wayne-solidarity-loop")
        run = lane / "qualification-15" / leaf
        evidence = (run if profile == "sql-01" else run / mode) / "evidence"
        with pytest.raises(storage.StorageRefusal):
            storage.profile_run(
                profile, focus, periods, lane / "qualification-01" / leaf / "evidence"
            )
        with pytest.raises(storage.StorageRefusal):
            storage.profile_run(
                profile,
                focus,
                periods,
                (
                    lane / "qualification-10" / leaf
                    if profile == "sql-01"
                    else lane / "qualification-10" / leaf / mode
                )
                / "evidence",
            )
        retired = lane / "qualification-14" / leaf
        retired_evidence = (retired if profile == "sql-01" else retired / mode) / "evidence"
        with pytest.raises(storage.StorageRefusal):
            storage.profile_run(profile, focus, periods, retired_evidence)
        assert storage.profile_run(profile, focus, periods, evidence) == evidence.parent
        if profile != "sql-01":
            assert storage.native_path(evidence) == (profile, mode)
            with pytest.raises(storage.StorageRefusal):
                storage.native_path(retired_evidence)
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


def set_default_acl(path, group):
    import os
    import struct

    entries = [(1, 7), (4, group), (32, 0)]
    os.setxattr(
        path,
        "system.posix_acl_default",
        struct.pack("<I", 2)
        + b"".join(struct.pack("<HHI", tag, perm, 0xFFFFFFFF) for tag, perm in entries),
    )


@pytest.mark.parametrize("private_default", [False, True])
def test_sql_supervisor_mask_reaches_real_private_manifest_reader(tmp_path, private_default):
    import os
    import subprocess

    repo = Path(__file__).resolve().parents[3]
    evidence = tmp_path / "evidence"
    if private_default:
        set_default_acl(tmp_path, 0)
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


# Discriminating fields copied from the failed qualification-01 observation.
PID1_STATUS = "Name:\tpostgres\nPid:\t1\nUid:\t70\t70\t70\t70\nGid:\t70\t70\t70\t70"


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "process_uid",
        "process_gid",
        "account_uid",
        "account_gid",
        "malformed_account",
        "malformed_status",
        "duplicate_gid",
        "non_postgres",
        "directory_uid",
        "host_gid",
        "changed_creator_group",
        "mode",
        "inode",
        "mapping",
        "matching_directory_wrong_account",
    ],
)
def test_physical_observation_binds_process_account_and_private_directory(
    tmp_path, monkeypatch, fault
):
    from contextlib import nullcontext
    from unittest.mock import MagicMock

    run = tmp_path / "sql-01"
    directory = storage.PrivateEvidence(run / "evidence")
    directory.path.mkdir(parents=True, mode=0o700)
    image, cid, canary = "sha256:" + "a" * 64, "b" * 64, "c" * 32
    host = {"major": 253, "minor": 5, "inode": 104470194, "uid": 70, "gid": 1000, "mode": 0o700}
    creator_gid = 1000
    stat = "64773 104470194 70 1000 700"
    status = PID1_STATUS
    accounts = {"-u": b"70\n", "-g": b"70\n"}
    if fault in ("process_uid", "process_gid"):
        field = "Uid:" if fault == "process_uid" else "Gid:"
        status = status.replace(field + "\t70" * 4, field + "\t71" * 4)
    elif fault in ("account_uid", "account_gid", "malformed_account"):
        accounts["-u" if fault == "account_uid" else "-g"] = (
            b"70\n70\n" if fault == "malformed_account" else b"71\n"
        )
    elif fault == "matching_directory_wrong_account":
        creator_gid = 70
        host["gid"] = 70
        stat = stat.replace(" 1000 ", " 70 ")
        accounts["-g"] = b"71\n"
    elif fault == "malformed_status":
        status = status.replace("Uid:" + "\t70" * 4, "Uid:" + "\t70" * 3)
    elif fault == "duplicate_gid":
        status += "\nGid:\t70\t70\t70\t70"
    elif fault == "non_postgres":
        status = status.replace("postgres", "sh")
    elif fault == "directory_uid":
        host["uid"] = 71
        stat = stat.replace(" 70 ", " 71 ")
    elif fault == "mode":
        host["mode"] = 0o750
        stat = stat.replace(" 700", " 750")
    elif fault == "host_gid":
        host["gid"] = 70
    elif fault == "changed_creator_group":
        host["gid"] = 1001
        stat = stat.replace(" 1000 ", " 1001 ")
    elif fault == "inode":
        host["inode"] += 1

    monkeypatch.setattr(storage, "pinned_ancestry", lambda _run: nullcontext([]))
    monkeypatch.setattr(
        storage,
        "_media_creation",
        lambda *_: {
            "daemon": "local",
            "image": {"id": image},
            "creator": {"uid": 1000, "gid": creator_gid},
            "ancestry": [],
        },
    )
    monkeypatch.setattr(
        storage,
        "_one_docker",
        lambda *_: {
            "Name": "/selected",
            "State": {"Status": "running", "Running": True, "Pid": 1349614},
        },
    )
    mounts = {"mounts": [], "port_request": {}}
    monkeypatch.setattr(storage, "container_mounts", lambda *_: mounts)
    directory.publish_json(
        "media-container-created.json",
        {
            "container": cid,
            "canary": canary,
            "daemon": "local",
            "image": image,
            **mounts,
        },
    )
    monkeypatch.setattr(storage, "_assigned_port", lambda *_: 49157)
    monkeypatch.setattr(storage, "_host_identity", lambda _: host)
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda path: (
            "0 200000 65536" if fault == "mapping" and path.name == "gid_map" else "0 0 4294967295"
        ),
    )

    def output(args):
        assert args[:3] == ["docker", "exec", cid]
        return {
            ("cat", "/proc/1/status"): status,
            ("stat", "-c", "%d %i %u %g %a", storage.PGDATA): stat,
        }[tuple(args[3:])]

    def raw(args):
        assert args[:3] == ["docker", "exec", cid]
        return {
            ("id", "-u", "postgres"): accounts["-u"],
            ("id", "-g", "postgres"): accounts["-g"],
            ("cat", storage.PGDATA + "/PG_VERSION"): b"17\n",
            ("cat", storage.PGDATA + "/.babylon-postgres-lineage-v1"): (
                storage.LINEAGE + "\n"
            ).encode(),
        }[tuple(args[3:])]

    monkeypatch.setattr(storage, "exact_output", output)
    monkeypatch.setattr(storage, "_exec_bytes", raw)
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = (
        "test",
        "test",
        "template1",
        canary,
        storage.PGDATA,
        "170011",
        "501",
        "UTF8",
        "b",
        "C.UTF-8",
    )
    conn.execute.return_value.fetchall.return_value = [
        ("postgis", "3.5.7", "3.5.7"),
        ("vector", "0.8.5", "0.8.5"),
        ("h3", "4.5.0", None),
        ("h3_postgis", "4.5.0", None),
    ]
    monkeypatch.setattr(storage, "physical_session", lambda *_: nullcontext(conn))

    if fault:
        with pytest.raises(storage.StorageRefusal):
            storage.physical_observation(directory, tmp_path, cid, canary, image)
        return
    result = storage.physical_observation(directory, tmp_path, cid, canary, image)
    assert (result["server_uid"], result["server_gid"]) == (70, 70)
    assert result["host"] == result["container_root"] == host
    assert result["creator"] == {"uid": 1000, "gid": 1000}

    # The creator and current host observe translated host IDs, while stat inside
    # the container still observes its original directory group.
    creator_gid = 201000
    host["gid"] = 201000
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda path: "0 200000 65536" if path.name == "gid_map" else "0 0 4294967295",
    )
    translated = storage.physical_observation(directory, tmp_path, cid, canary, image)
    assert translated["creator"]["gid"] == translated["host"]["gid"] == 201000
    assert translated["container_root"]["gid"] == 1000
    assert translated["server_gid"] == 70


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
        "process_group",
        "ack_warning",
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
    run = tmp_path / "walk-01" / "normal_play"
    evidence = storage.PrivateEvidence(run / "evidence")
    evidence.path.mkdir(parents=True, mode=0o700)
    pg = {"inode": 32, "uid": 70, "gid": 1000}
    physical = {
        "container": cid,
        "image": {"id": image},
        "label": label,
        "host": pg,
        "pid": 303,
        "mounts": [],
        "port_request": {},
        "server_uid": 70,
        "server_gid": 70,
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
            assert kw == {"timeout": 180}
            assert args in (
                ["docker", "stop", "--time", "-1", cid],
                ["docker", "stop", "--timeout", "-1", cid],
            )
            if fault == "timeout":
                raise subprocess.TimeoutExpired(args, 90)
            stopped = True
            if "--time" in args or fault == "ack_warning":
                return f"Flag --time has been deprecated, use --timeout instead\n{cid}"
            return cid
        assert args[:5] == ["docker", "exec", "--user", "70:70", cid]
        if args[-1] == "/proc/1/status":
            return (
                PID1_STATUS.replace("Gid:" + "\t70" * 4, "Gid:" + "\t1000" * 4)
                if fault == "process_group"
                else PID1_STATUS
            )
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
        attempt = storage.strict_json_bytes(
            evidence.read_reference(evidence.reference("native-fenced-stop-attempt-v1.json"))
        )
        assert (attempt["uid"], attempt["gid"], attempt["host"]) == (70, 70, pg)
    else:
        with pytest.raises((storage.StorageRefusal, subprocess.TimeoutExpired)):
            storage.stop_checked(evidence, cid, fenced_image=image)
        assert not (evidence.path / "native-fenced-stop-v1.json").exists()
    stops = [args for args in records if "stop" in args]
    assert len(stops) == (
        0 if fault in ("image_signal", "container_signal", "pid", "process_group") else 1
    )
    assert not any("rm" in args or "kill" in args for args in records)


@pytest.mark.parametrize("warning_on_current_option", [False, True])
def test_sql_stop_uses_current_timeout_option_and_exact_acknowledgment(
    tmp_path, monkeypatch, warning_on_current_option
):
    from types import SimpleNamespace

    cid = "cb6d7be499d440fa5dbb5fd047f658bc3cea64abdcf70863c8ef0c60362c4048"
    directory = storage.PrivateEvidence(tmp_path)

    def ack(args, *, timeout):
        assert timeout == 75
        assert args[:2] == ["docker", "stop"] and args[3:] == ["60", cid]
        if args[2] == "--time" or warning_on_current_option:
            return f"Flag --time has been deprecated, use --timeout instead\n{cid}"
        assert args[2] == "--timeout"
        return cid

    monkeypatch.setattr(storage, "exact_output", ack)
    monkeypatch.setattr(
        storage,
        "_one_docker",
        lambda *_: {"State": {"Status": "exited", "ExitCode": 0, "OOMKilled": False}},
    )
    monkeypatch.setattr(
        storage.subprocess,
        "run",
        lambda *_a, **_kw: SimpleNamespace(stdout=b"database system is shut down", stderr=b""),
    )
    if warning_on_current_option:
        with pytest.raises(storage.StorageRefusal, match="full container ID"):
            storage.stop_checked(directory, cid)
        assert not (tmp_path / "clean-shutdown.log").exists()
    else:
        storage.stop_checked(directory, cid)
        assert directory.reference("clean-shutdown.log")


def test_sql_supervisor_refuses_inherited_manifest_acl_before_consuming_run(tmp_path):
    import os
    import subprocess
    import sys

    parent = tmp_path / "runs"
    parent.mkdir(mode=0o700)
    set_default_acl(parent, 5)
    # Demonstrate the actual shell mode, including inheritance through a private directory.
    subprocess.run(
        ["bash", "-c", 'umask 077; mkdir -m 700 "$1/child"; : > "$1/child/probe"', "sh", parent],
        check=True,
    )
    assert (parent / "child/probe").stat().st_mode & 0o777 == 0o640
    repo = Path(__file__).resolve().parents[3]
    init = tmp_path / "init"
    init.write_text(
        'mise() { [[ " $* " == *" reserve "* ]] || return 97; "$TMP_PY" -c "$TMP_RESERVE"; }\n'
    )
    mock_reserve = """
from contextlib import contextmanager
from pathlib import Path
import os
from tools.devtools import wayne_qualification_storage as s
parent = Path(os.environ["TMP_RUNS"])
s.RUN_PARENT = parent
root = Path.cwd()
s.MEDIA_CHECKOUT = root
s._daemon_endpoint = lambda: None
s._image = lambda _: None
s.exact_output = lambda args: ""
@contextmanager
def pins(path):
    fd = os.open(path, s.DIR_FLAGS)
    try: yield [s._directory_pin(fd, path)]
    finally: os.close(fd)
s.pinned_ancestry = pins
s.reserve_run("sql-01", "organizer_allocation_atomic", "", parent / "sql-01/evidence", root)
"""
    result = subprocess.run(
        ["bash", str(repo / "tools/run_rust_postgres.sh")],
        env={
            **{
                k: v
                for k, v in os.environ.items()
                if not (k.startswith("PG") or k.endswith("_DSN") or k == "CARGO_TARGET_DIR")
            },
            "BASH_ENV": str(init),
            "TMP_PY": sys.executable,
            "TMP_RUNS": str(parent),
            "TMP_RESERVE": mock_reserve,
            "BABYLON_POSTGRES_IMAGE_ID": "sha256:" + "a" * 64,
            "BABYLON_WAYNE_PROFILE": "sql-01",
            "BABYLON_STORAGE_REPORT_DIRECTORY": str(parent / "sql-01/evidence"),
            "BABYLON_POSTGRES_LIVE_FOCUS": "organizer_allocation_atomic",
        },
        capture_output=True,
    )
    assert result.returncode != 0 and b"inherited default ACL" in result.stderr, result.stderr
    assert not (parent / "sql-01").exists()


def test_governed_sql_archive_uses_a_fresh_private_build_destination(tmp_path, monkeypatch):
    import subprocess

    evidence = storage.PrivateEvidence(tmp_path)
    monkeypatch.setattr(storage, "_pinned_archive_tools", lambda: None, raising=False)

    def failed_build(args, **kwargs):
        assert args[1:3] == ["nextest", "archive"]
        assert "--lib" in args and "--locked" in args and "--cargo-message-format=json" in args
        archive = Path(args[args.index("--archive-file") + 1])
        assert archive.parent.parent == tmp_path
        assert archive.parent.stat().st_mode & 0o777 == 0o700
        assert not archive.exists()
        archive.write_bytes(b"incomplete")
        return subprocess.CompletedProcess(
            args, 1, b'{"reason":"build-finished","success":false}', b"failed"
        )

    monkeypatch.setattr(storage.subprocess, "run", failed_build)
    with pytest.raises(subprocess.CalledProcessError):
        storage._build_test(evidence, tmp_path)
    assert not (tmp_path / "ignored-tests.tar.zst").exists()
    assert (tmp_path / "ignored-build.stderr").read_bytes() == b"failed"
    assert not (tmp_path / "ignored-test").exists()


@pytest.mark.parametrize(
    "change",
    [
        "valid",
        "duplicate-compiler",
        "wrong-package",
        "missing-binary",
        "two-binaries",
        "archive-escape",
        "compiler-escape",
        "list-disagrees",
        "wrong-platform",
        "list-build-directory",
    ],
)
def test_sql_archive_matches_only_the_compiled_lib_under_its_normalized_target(tmp_path, change):
    import copy
    import json

    rust = tmp_path / "rust"
    crate = rust / "crates/babylon-persistence"
    build = tmp_path / "disposable/build"
    target = rust / "target"
    suffix = Path("debug/deps/babylon_persistence-0123456789abcdef")
    package = "path+" + crate.as_uri() + "#0.1.0"
    manifest = str(crate / "Cargo.toml")
    cargo = {
        "workspace_root": str(rust),
        "target_directory": str(target),
        "build_directory": str(build),
        "packages": [{"name": "babylon-persistence", "id": package, "manifest_path": manifest}],
        "workspace_members": [package],
    }
    artifact = {
        "reason": "compiler-artifact",
        "package_id": package,
        "manifest_path": manifest,
        "target": {
            "name": "babylon_persistence",
            "kind": ["lib"],
            "src_path": str(crate / "src/lib.rs"),
        },
        "profile": {"test": True},
        "executable": str(build / suffix),
        "filenames": [str(build / suffix)],
    }
    binary = {
        "binary-id": "babylon-persistence",
        "binary-name": "babylon_persistence",
        "kind": "lib",
        "package-id": package,
        "build-platform": "target",
        "binary-path": str(target / suffix),
    }
    binaries = {"babylon-persistence": binary}
    archive = {"rust-build-meta": {"target-directory": str(target)}, "rust-binaries": binaries}
    listed = copy.deepcopy(archive)
    listed["rust-build-meta"]["build-directory"] = str(target)
    if change == "list-build-directory":
        listed["rust-build-meta"]["build-directory"] = str(build)
    if change == "wrong-package":
        artifact["package_id"] = "different-crate"
    if change == "missing-binary":
        binaries.clear()
    if change == "two-binaries":
        binaries["second"] = binary
    if change == "archive-escape":
        binary["binary-path"] = str(target / ".." / suffix)
    if change == "compiler-escape":
        artifact["executable"] = str(build / ".." / suffix)
        artifact["filenames"] = [artifact["executable"]]
    if change == "list-disagrees":
        listed["rust-binaries"]["babylon-persistence"]["binary-path"] = str(build / suffix)
    if change == "wrong-platform":
        binary["build-platform"] = "host"
    compiler = (json.dumps(artifact) + "\n").encode() * (2 if change == "duplicate-compiler" else 1)
    if change == "valid":
        assert storage._sql_archive_member(tmp_path, compiler, cargo, archive, listed) == str(
            Path("target") / suffix
        )
        assert not build.exists()
    else:
        with pytest.raises(storage.StorageRefusal):
            storage._sql_archive_member(tmp_path, compiler, cargo, archive, listed)


@pytest.mark.parametrize(
    "change", ["valid", "symlink", "hardlink", "parent-link", "non-executable", "directory"]
)
def test_sql_archive_extraction_pins_unique_regular_member_below_private_parents(tmp_path, change):
    import os

    private = storage.PrivateEvidence(tmp_path)
    (tmp_path / "target").mkdir(mode=0o700)
    destination = tmp_path / "target/lib-test"
    original = tmp_path / "actual"
    original.write_bytes(b"extracted fixture bytes")
    original.chmod(0o755)
    if change == "symlink":
        destination.symlink_to(original)
    elif change == "hardlink":
        os.link(original, destination)
    elif change == "directory":
        destination.mkdir(mode=0o700)
    else:
        original.rename(destination)
    if change == "non-executable":
        destination.chmod(0o600)
    if change == "parent-link":
        (tmp_path / "target").rename(tmp_path / "elsewhere")
        (tmp_path / "target").symlink_to(tmp_path / "elsewhere", target_is_directory=True)
    if change == "valid":
        ref = private.extracted_member("target/lib-test", executable=True)
        assert private.read_reference(ref) == b"extracted fixture bytes"
        assert destination.stat().st_mode & 0o777 == 0o700
    else:
        with pytest.raises((storage.StorageRefusal, OSError)):
            private.extracted_member("target/lib-test", executable=True)


def test_sql_archive_publication_preserves_existing_evidence_and_rejects_aliases(tmp_path):
    import os

    directory = storage.PrivateEvidence(tmp_path)
    staging = storage.PrivateEvidence(tmp_path / "staging")
    staging.path.mkdir(mode=0o700)
    staged = staging.publish(storage.ARCHIVE_NAME, b"completed archive control")
    alias = staging.path / "alias"
    os.link(staging.path / staged.path, alias)
    with pytest.raises(storage.StorageRefusal, match="hard link"):
        storage._publish_test_archive(directory, staging)
    alias.unlink()
    existing = directory.publish(storage.ARCHIVE_NAME, b"earlier evidence")
    with pytest.raises(FileExistsError):
        storage._publish_test_archive(directory, staging)
    directory.verify(existing)
    staging.verify(staged)


@pytest.fixture
def native_release(tmp_path, monkeypatch):
    import hashlib
    import os
    from contextlib import contextmanager

    parent = tmp_path / "qualification-06"
    parent.mkdir(mode=0o700)
    root = tmp_path / "repo"
    binaries = root / "rust/target/debug"
    binaries.mkdir(parents=True)
    head = "a" * 40
    store = storage.PrivateEvidence(parent)
    capacity = store.publish_json(
        "smoke-01-capacity.json",
        {
            "tag": "wayne-disk-reservation-v1",
            "profile": "smoke-01",
            "source_head": head,
            "build_bytes": 1,
            "primary_bytes": 1,
            "evidence_bytes": 1,
            "restore_bytes": 1,
            "dump_bytes": 1,
            "archive_bytes": 1,
            "measured_basis": "synthetic capacity",
        },
    )
    host = {
        "tag": "wayne-host-process-context-v2",
        "mount_namespace": "mnt:[1]",
        "init_start_ticks": 1,
        "init_comm": "systemd",
        "boot_id": "00000000-0000-0000-0000-000000000002",
        "pid_namespace": "pid:[2]",
        "proc_mount_id": 3,
        "operator_uid": 1000,
    }
    host_ref = store.publish_json("host-process-context.json", host)
    monkeypatch.setenv("BABYLON_WAYNE_HOST_CONTEXT_SHA256", host_ref.sha256)
    packet = {
        "source_head": head,
        "capacity": capacity.model_dump(),
        "source_sha256": "d" * 64,
        "inputs_sha256": "e" * 64,
        "image_id": "sha256:" + "1" * 64,
        "host_context_sha256": host_ref.sha256,
    }
    monkeypatch.setattr(storage, "released_inventory", lambda _: ("d" * 64, "e" * 64))
    for slot, name in (
        ("runtime", "babylon-runtime"),
        ("client", "babylon-client"),
        ("material_audit", "babylon-material-audit"),
    ):
        data = name.encode()
        (binaries / name).write_bytes(data)
        packet[slot] = {
            "path": "normal-" + name,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }

    @contextmanager
    def pins(path):
        rows = []
        for selected in [
            parent,
            *(
                parent / Path(*path.relative_to(parent).parts[:n])
                for n in range(1, len(path.relative_to(parent).parts) + 1)
            ),
        ]:
            fd = os.open(selected, storage.DIR_FLAGS)
            try:
                rows.append(storage._directory_pin(fd, selected))
            finally:
                os.close(fd)
        yield rows

    monkeypatch.setattr(storage, "pinned_ancestry", pins)
    monkeypatch.setattr(storage, "MEDIA_CHECKOUT", root)
    monkeypatch.setattr(storage, "RUN_PARENT", parent)
    monkeypatch.setattr(storage, "actual_host_context", lambda: None)
    monkeypatch.setattr(storage, "selected_policy", lambda _: None)
    monkeypatch.setattr(storage, "_daemon_endpoint", lambda: None)
    monkeypatch.setattr(storage, "_daemon", lambda: {})
    monkeypatch.setattr(storage, "_image", lambda _: {})
    monkeypatch.setattr(storage, "exact_output", lambda args: head if "HEAD" in args else "")
    for key in tuple(os.environ):
        if key.startswith("PG") or key.endswith("_DSN") or key == "CARGO_TARGET_DIR":
            monkeypatch.delenv(key)
    monkeypatch.setenv("BABYLON_POSTGRES_IMAGE_ID", "sha256:" + "1" * 64)
    monkeypatch.delenv("BABYLON_WAYNE_NATIVE_EXPECTATION_REF", raising=False)
    monkeypatch.setenv("BABYLON_NATIVE_MEASUREMENT_MODE", "normal_play")
    return root, store, packet


@pytest.mark.parametrize(
    "change",
    [
        "head",
        "capacity",
        "missing",
        "malformed",
        "wrong-product",
        "inventory",
        "inputs",
        "image",
        "host",
    ],
)
def test_native_reserve_refuses_before_profile_creation(native_release, monkeypatch, change):
    root, store, packet = native_release
    if change == "head":
        packet["source_head"] = "b" * 40
    elif change in ("inventory", "inputs", "host", "image"):
        key = {
            "inventory": "source_sha256",
            "inputs": "inputs_sha256",
            "host": "host_context_sha256",
            "image": "image_id",
        }[change]
        packet[key] = "sha256:" + "f" * 64 if change == "image" else "f" * 64
    elif change == "capacity":
        (store.path / "smoke-01-capacity.json").write_bytes(
            (store.path / "smoke-01-capacity.json").read_bytes().replace(b"synthetic", b"refreshed")
        )
    elif change == "malformed":
        del packet["client"]
    elif change == "wrong-product":
        packet["runtime"] = packet["client"]
    if change != "missing":
        ref = store.publish_json("smoke-01-native-expectations.json", packet)
        monkeypatch.setenv("BABYLON_WAYNE_NATIVE_EXPECTATION_REF", ref.model_dump_json())
    run = store.path / "smoke-01" / "normal_play"
    with pytest.raises(storage.StorageRefusal, match="native"):
        storage.reserve_run("smoke-01", "national_storage", "2", run / "evidence", root)
    assert not run.exists()


@pytest.mark.parametrize("change", ["none", "size", "same-size", "new-reference"])
def test_native_pin_publishes_only_released_normal_copies(
    native_release, monkeypatch, change, capsys
):
    import sys

    root, store, packet = native_release
    ref = store.publish_json("smoke-01-native-expectations.json", packet)
    monkeypatch.setenv("BABYLON_WAYNE_NATIVE_EXPECTATION_REF", ref.model_dump_json())
    evidence = store.path / "smoke-01/normal_play/evidence"
    storage.reserve_run("smoke-01", "national_storage", "2", evidence, root)
    (evidence / "source-before.sha256").write_bytes(b"captured source")
    binary = root / "rust/target/debug/babylon-material-audit"
    if change == "new-reference":
        # Even a second internally consistent packet cannot replace the one selected at reserve.
        packet["source_head"] = "c" * 40
        (store.path / ref.path).unlink()
        second = store.publish_json(ref.path, packet)
        monkeypatch.setenv("BABYLON_WAYNE_NATIVE_EXPECTATION_REF", second.model_dump_json())
    elif change != "none":
        binary.write_bytes(b"x" * (binary.stat().st_size if change == "same-size" else 1))
    monkeypatch.setattr(storage, "source_unchanged", lambda *_: None)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "wayne",
            "pin-binaries",
            "--root",
            str(root),
            "--evidence",
            str(evidence),
            "--canary",
            "a" * 32,
            "--container",
            "b" * 64,
            "--profile",
            "smoke-01",
            "--focus",
            "national_storage",
            "--periods",
            "2",
        ],
    )
    previous = storage.os.umask(0o077)
    try:
        result = storage.main()
    finally:
        storage.os.umask(previous)
    roster = evidence / "normal-binaries.json"
    if change == "none":
        assert result == 0, capsys.readouterr().err
        assert storage.strict_json_bytes(roster.read_bytes()) == {
            entry["path"].removeprefix("normal-"): entry
            for entry in (packet["runtime"], packet["client"], packet["material_audit"])
        }
    else:
        reason = "initial reservation" if change == "new-reference" else "babylon-material-audit"
        assert result == 1 and reason in capsys.readouterr().err
        assert not roster.exists()
        assert not (evidence / "native-executables.sha256").exists()
