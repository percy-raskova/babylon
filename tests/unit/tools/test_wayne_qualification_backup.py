"""Synthetic bind visibility, archive integrity, and bounded retirement contracts."""

from __future__ import annotations

import hashlib
import io
import json
import struct
import subprocess
import tarfile
from functools import partial
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from psycopg.pq import TransactionStatus
from tools.devtools import wayne_qualification_backup as backup
from tools.devtools import wayne_qualification_storage as storage

SYSTEM = 504402
WAL = "pg_wal/000000010000000000000001"
SEGMENT = 1024 * 1024
RELATION = "base/551/2930"
LINEAGE = b"reviewed lineage\n"
DOCKER_ZERO = "0001-01-01T00:00:00Z"
SOURCE_STARTED = "2026-11-07T10:59:00.123456789Z"
SOURCE_FINISHED = "2026-11-07T11:00:04.000000999Z"
HELPER_STARTED = "2026-11-07T11:00:05.123456789Z"


def fixture() -> tuple[dict[str, bytes | None], backup.PhysicalWitness]:
    # Literal fixture emitted by the PG17.11 upstream C declarations and independent
    # x86 CRC32C instructions. Validator changes do not regenerate its checksums.
    control = bytes.fromhex(
        "52b2070000000000a40600008979100c010000000000000000f153650000000050001000000000005000100000000000010000000100000001000000010000000003000000000000014000000000000000000000000000000000000000000000000000000000000000f15365000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000080000000000000087d6324100200000000002000020000000001000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000048e4114b"
    ).ljust(8192, b"\0")
    wal = bytearray(SEGMENT)
    struct.pack_into("<HHIQ", wal, 0, 0xD116, 2, 1, SEGMENT)
    struct.pack_into("<QII", wal, 24, SYSTEM, SEGMENT, 8192)
    checkpoint = bytes.fromhex(
        "7200000000000000280010000000000000000000e2b59f0dff585000100000000000010000000100000001000000010000000003000000000000014000000000000000000000000000000000000000000000000000000000000000f153650000000000000000000000000000000000000000"
    )
    wal[80 : 80 + len(checkpoint)] = checkpoint
    relation = bytearray(PAGE_BYTES := 8192)
    struct.pack_into("<5H", relation, 10, 0, 24, PAGE_BYTES, PAGE_BYTES, PAGE_BYTES + 4)
    payloads = {
        "global": None,
        "base": None,
        "base/551": None,
        "pg_wal": None,
        "pg_tblspc": None,
        "PG_VERSION": b"17\n",
        ".babylon-postgres-lineage-v1": LINEAGE,
        "global/pg_control": bytes(control),
        WAL: bytes(wal),
        RELATION: bytes(relation),
    }
    before = {
        name: backup.Member(
            "dir" if content is None else "file",
            0o700 if content is None else 0o600,
            71,
            73,
            len(content)
            if content and name in ("PG_VERSION", ".babylon-postgres-lineage-v1")
            else None,
            hashlib.sha256(content).hexdigest()
            if content and name in ("PG_VERSION", ".babylon-postgres-lineage-v1")
            else None,
        )
        for name, content in payloads.items()
    }
    physical = {
        "daemon": {"id": "fixture-daemon"},
        "server_uid": 71,
        "server_gid": 73,
        "uid_map": "0 100000 65536",
        "gid_map": "0 200000 65536",
        "container_root": {"mode": 0o700, "uid": 71, "gid": 73},
        "host": {"mode": 0o700, "uid": 100071, "gid": 200073},
        "cluster": str(SYSTEM),
    }
    before[RELATION] = backup.Member("file", 0o600, 71, 73, 8192, None)
    physical["source_checkpoint"] = "0/100028"
    physical["pgss"] = {"preload": "pg_stat_statements", "save": "on", "version": "1.11"}
    physical["relation_sizes"] = {RELATION: 8192}
    physical["relation_page_occupancy"] = {RELATION: "01"}
    before["pg_stat_tmp/pgss_query_texts.stat"] = backup.Member("file", 0o600, 71, 73, 12, None)
    for name in ("pg_stat", "pg_stat_tmp"):
        payloads[name] = None
        before[name] = backup.Member("dir", 0o700, 71, 73, 0, None)
    payloads["pg_stat/pg_stat_statements.stat"] = struct.pack("<IIi", 0x20220408, 1700, 0) + bytes(
        16
    )
    witness = backup.PhysicalWitness(
        physical, before, {"babylon_state.tick_commit": RELATION}, 551, SEGMENT, 0xD116
    )
    return payloads, witness


def stopped_members(
    files: dict[str, bytes | None], witness: backup.PhysicalWitness
) -> dict[str, backup.Member]:
    result = {}
    for name, content in files.items():
        before = witness.members.get(name)
        uid, gid = (
            (before.uid, before.gid)
            if before
            else (witness.physical["server_uid"], witness.physical["server_gid"])
        )
        if name == ".":
            uid, gid = (
                witness.physical["container_root"]["uid"],
                witness.physical["container_root"]["gid"],
            )
        result[name] = backup.Member(
            "dir" if content is None else "file",
            0o700 if content is None else 0o600,
            storage._mapped(uid, witness.physical["uid_map"]),
            storage._mapped(gid, witness.physical["gid_map"]),
            len(content or b""),
            hashlib.sha256(content).hexdigest() if content is not None else None,
        )
    root = witness.physical["host"]
    result.setdefault(".", backup.Member("dir", root["mode"], root["uid"], root["gid"], 0, None))
    return result


def archive(
    path: Path,
    payloads: dict[str, bytes | None],
    *,
    uid: int = 71,
    gid: int = 73,
    extra: tarfile.TarInfo | None = None,
    owners: dict[str, tuple[int, int]] | None = None,
) -> None:
    with tarfile.open(path, "x:") as output:
        for name, content in {".": None, **payloads}.items():
            member = tarfile.TarInfo("./" + name)
            member.uid, member.gid = (owners or {}).get(name, (uid, gid))
            member.mode = 0o700 if content is None else 0o600
            member.type = tarfile.DIRTYPE if content is None else tarfile.REGTYPE
            member.size = len(content or b"")
            output.addfile(member, io.BytesIO(content or b""))
        if extra:
            output.addfile(extra)


@pytest.mark.parametrize(
    ("uid", "gid", "namespace"), [(71, 73, "container"), (100071, 200073, "host")]
)
def test_independent_members_prove_bind_and_numeric_translation(
    tmp_path: Path, uid: int, gid: int, namespace: str
) -> None:
    files, witness = fixture()
    stopped = stopped_members(files, witness)
    path = tmp_path / "copy.tar"
    archive(path, files, uid=uid, gid=gid)
    with path.open("rb") as stream:
        members, translation = backup.archive_manifest(stream, witness, stopped)
    assert translation == namespace
    assert members[RELATION].sha256 == hashlib.sha256(files[RELATION] or b"").hexdigest()
    assert members[RELATION].size == 8192


@pytest.mark.parametrize("host_namespace", [False, True])
@pytest.mark.parametrize("fault", [None, "running", "root", "new_member", "existing_member"])
def test_backup_distinguishes_server_root_and_existing_member_ownership(
    tmp_path: Path, host_namespace: bool, fault: str | None
) -> None:
    from dataclasses import replace

    files, witness = fixture()
    stopped = stopped_members(files, witness)
    witness.physical.update(server_uid=70, server_gid=70)
    witness.physical["container_root"].update(uid=70, gid=1000)
    witness.physical["host"].update(uid=100070, gid=201000)
    witness.members[backup.PGSS_RUNNING] = replace(
        witness.members[backup.PGSS_RUNNING], uid=70, gid=1000 if fault == "running" else 70
    )
    # Remaining pre-stop files carry their own individually witnessed identities.
    files["."] = None
    owners = {
        ".": (70, 70 if fault == "root" else 1000),
        backup.PGSS_STOPPED: (70, 1000 if fault == "new_member" else 70),
    }
    if fault == "existing_member":
        owners[RELATION] = (70, 70)
    uid_shift, gid_shift = (100000, 200000) if host_namespace else (0, 0)
    path = tmp_path / "copy.tar"
    stopped = stopped_members(files, witness)
    archive(
        path,
        files,
        uid=uid_shift + 71,
        gid=gid_shift + 73,
        owners={name: (uid_shift + uid, gid_shift + gid) for name, (uid, gid) in owners.items()},
    )
    with path.open("rb") as stream:
        if fault:
            with pytest.raises(backup.Refusal):
                backup.archive_manifest(stream, witness, stopped)
        else:
            members, mode = backup.archive_manifest(stream, witness, stopped)
            assert mode == ("host" if host_namespace else "container")
            assert members["."].gid == gid_shift + 1000
            assert members[backup.PGSS_STOPPED].gid == gid_shift + 70
            assert members[RELATION].gid == gid_shift + 73


@pytest.mark.parametrize(
    "fault",
    [
        "image_directory",
        "wrong_cluster",
        "unclean",
        "wrong_wal",
        "missing_checkpoint_wal",
        "stable_bytes",
        "wrong_owner",
        "relation_missing",
        "escaped",
        "link",
        "fifo",
        "duplicate",
        "truncated",
    ],
)
def test_copy_visibility_refuses_unsafe_or_unrelated_archive(tmp_path: Path, fault: str) -> None:
    files, witness = fixture()
    stopped = stopped_members(files, witness)
    extra = None
    if fault == "image_directory":
        files.clear()
    elif fault in ("wrong_cluster", "unclean"):
        control = bytearray(files["global/pg_control"] or b"")
        struct.pack_into(
            "<Q" if fault == "wrong_cluster" else "<I",
            control,
            0 if fault == "wrong_cluster" else 16,
            9,
        )
        files["global/pg_control"] = bytes(control)
    elif fault == "missing_checkpoint_wal":
        control = bytearray(files["global/pg_control"] or b"")
        struct.pack_into("<Q", control, 32, SEGMENT * 2 + 80)
        files["global/pg_control"] = bytes(control)
    elif fault == "wrong_wal":
        files[WAL] = bytes(SEGMENT)
    elif fault == "stable_bytes":
        files[".babylon-postgres-lineage-v1"] = b"other"
    elif fault == "relation_missing":
        del files[RELATION]
    elif fault in ("escaped", "link", "fifo", "duplicate"):
        extra = tarfile.TarInfo(
            {"escaped": "../x", "link": "badlink", "fifo": "pipe", "duplicate": "./PG_VERSION"}[
                fault
            ]
        )
        if fault == "link":
            extra.type, extra.linkname = tarfile.SYMTYPE, "/external"
        if fault == "fifo":
            extra.type = tarfile.FIFOTYPE
    path = tmp_path / "copy.tar"
    archive(path, files, uid=72 if fault == "wrong_owner" else 71, extra=extra)
    if fault == "truncated":
        with tarfile.open(path) as reader:
            last = reader.getmembers()[-1]
            end = last.offset_data + ((last.size + 511) // 512) * 512
        with path.open("r+b") as trunc:
            trunc.truncate(end + 512)
    with path.open("rb") as stream, pytest.raises(backup.Refusal):
        backup.archive_manifest(stream, witness, stopped)


def tick(tick_number: int, prior: bytes, after: bytes) -> tuple[int, str, str, str, str]:
    domain = b"babylon.material-tick-content.v3\0"
    parts = [b"f" * 32, b"h" * 32, b"g" * 32, b"G" * 32, prior, after, b"r" * 32]
    raw = domain + struct.pack(">IQ", 3, tick_number) + b"".join(parts)
    return tick_number, hashlib.sha256(raw).hexdigest(), "a" * 64, raw.hex(), "b" * 64


@pytest.mark.parametrize(
    "fault", ["absent", "gap", "partial", "foreign_marker", "unlinked_world", "foundation"]
)
def test_committed_material_checkpoint_and_world_chain_cannot_compare_equal_when_absent(
    fault: str,
) -> None:
    first = tick(1, b"A" * 32, b"B" * 32)
    second = tick(2, b"B" * 32, b"C" * 32)
    foundation = (b"f" * 32).hex()
    assert backup._markers([first, second], 2, foundation)[-1]["world_after"] == (b"C" * 32).hex()
    rows = [first, second]
    if fault == "absent":
        rows = []
    elif fault == "gap":
        rows = [second]
    elif fault == "partial":
        rows[1] = (*second[:4], "")
    elif fault == "foreign_marker":
        rows[1] = (2, first[1], *second[2:])
    elif fault == "unlinked_world":
        rows[1] = tick(2, b"Q" * 32, b"C" * 32)
    elif fault == "foundation":
        foundation = "0" * 64
    with pytest.raises(backup.Refusal):
        backup._markers(rows, 2, foundation)


def _read_physical_fixture(
    files: dict[str, bytes | None], args: list[str], *, timeout: int = 0
) -> bytes:
    before = {".": None, **files, backup.PGSS_RUNNING: b"stat"}
    del before[backup.PGSS_STOPPED]

    if "find" in args:
        if "-printf" in args:
            raise subprocess.CalledProcessError(1, args, b"", b"find: unrecognized: -printf\n")
        assert args[-4:] == ["find", ".", "-xdev", "-print0"]
        return b"\0".join(("." if path == "." else "./" + path).encode() for path in before) + b"\0"
    if "stat" in args:
        assert args[5:9] == ["stat", "-c", "%f %a %u %g %s %d", "--"]
        parts = []
        for raw in args[9:]:
            path = raw if raw == "." else raw.removeprefix("./")
            content = before[path]
            mode = 0o40700 if content is None else 0o100600
            parts.append(f"{mode:x} {mode & 0o7777:o} 71 73 {len(content or b'')} 1\n")
        return "".join(parts).encode()
    assert args[5:7] == ["cat", "--"]
    result = files[args[-1].removeprefix("./")]
    assert result is not None
    return result


def _physical_scan_fixture(
    monkeypatch: pytest.MonkeyPatch,
    source: MagicMock,
    files: dict[str, bytes | None],
    witness: backup.PhysicalWitness,
    owner: tuple[str, ...],
    events: list[str],
    counts: dict[str, backup.SessionTotal],
    fault: str,
    receipts: Path,
) -> dict[str, Any]:
    physical = {
        **{
            k: v
            for k, v in witness.physical.items()
            if k not in ("source_checkpoint", "pgss", "relation_sizes", "relation_page_occupancy")
        },
        "container_root": {**witness.physical["container_root"], "major": 0, "minor": 1},
        "lineage": LINEAGE.decode(),
        "pg_version": "17\n",
    }
    name = next(iter(witness.relations))
    monkeypatch.setattr(backup, "REQUIRED_ROWS", {name})
    wal = files[WAL]
    assert wal is not None

    def sql_response(stmt: str, args: object = None) -> MagicMock:
        cursor = MagicMock()
        if stmt == "CHECKPOINT":
            assert (
                "released sockets" not in events
                and (receipts / "pre-checkpoint-quiescence.json").is_file()
            )
            events.append("checkpoint-and-scan")
        elif "current_user::text" in stmt:
            cursor.fetchall.return_value = [
                ("test", "test", owner[7], owner[2], physical["cluster"], owner[9])
            ]
        elif "pg_control_checkpoint()" in stmt:
            cursor.fetchall.return_value = [("0/100028",)]
        elif "pg_tablespace" in stmt:
            cursor.fetchall.return_value = [("pg_default",), ("pg_global",)]
        elif "pg_walfile_name" in stmt:
            cursor.fetchall.return_value = [(551, physical["cluster"], SEGMENT, wal[:40])]
        elif "pg_control_version" in stmt:
            cursor.fetchall.return_value = [
                (
                    "170011",
                    1700,
                    202406281,
                    8192,
                    backup.RELSEG_BYTES,
                    "pg_stat_statements",
                    "on",
                    "1.11",
                )
            ]
        elif "WITH RECURSIVE" in stmt:
            cursor.fetchall.return_value = [(2930, name, "r", 0, None, None, RELATION, 8192)]
        elif "pg_read_binary_file" in stmt:
            assert args == (RELATION, 0, 8192)
            if fault == "finished-writer":
                counts["postgres"] = backup.SessionTotal(1, 51, None)
                events.append("writer-committed-and-exited")
            cursor.fetchone.return_value = (files[RELATION],)
        else:
            assert stmt == "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
        return cursor

    source.execute.side_effect = sql_response

    monkeypatch.setattr(storage, "_exec_bytes", partial(_read_physical_fixture, files))
    return physical


def _retirement_stop_fixture(
    target: backup.Evidence,
    cid: str,
    *,
    fenced_image: str,
    events: list[str],
    owner: tuple[str, ...],
    tmp_path: Path,
    physical: dict[str, Any],
    actual: list[backup.Backend],
    fault: str,
) -> None:
    assert "held sockets" in events and "released sockets" not in events
    assert fenced_image == owner[6] and (tmp_path / "backup/pre-stop-quiescence.json").is_file()
    events.append("stop")
    attempt = target.publish_json(
        "native-fenced-stop-attempt-v1.json",
        {
            "container": cid,
            "image": fenced_image,
            "stop_signal": "SIGINT",
            "since": "2026-11-07T11:00:01Z",
        },
    )
    pids = [b.pid for b in actual]
    if fault == "lost-before-stop":
        pids.pop()
    elif fault == "foreign-at-stop":
        pids[-1] = 501
    elif fault == "duplicate-at-stop":
        pids.append(pids[-1])
    stamp = "2026-11-07T11:00:00Z" if fault == "stale-stop" else "2026-11-07T11:00:02Z"
    server = (
        "2026-11-06 11:00:02.000" if fault == "stale-server-time" else "2026-11-07 11:00:02.000"
    )
    raw = target.publish(
        "clean-shutdown.log",
        "".join(
            f"{stamp} {server} UTC [{pid}] FATAL:  terminating connection due to administrator command\n"
            for pid in pids
        ).encode(),
    )
    if fault != "missing-fenced-stop":
        target.publish_json(
            "native-fenced-stop-v1.json",
            {
                "container": cid,
                "image": fenced_image,
                "host": physical["host"],
                "exit_code": 0,
                "oom_killed": False,
                "attempt": attempt.model_dump(),
                "log": raw.model_dump(),
                "fast": "2026-11-07T11:00:01Z",
                "clean": "2026-11-07T11:00:03Z",
                "finished": "2026-11-07T11:00:04Z",
            },
        )
    if fault == "changed-log":
        (target.path / "clean-shutdown.log").write_bytes(b"changed")


def _held_retirement_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    events: list[str],
    fault: str,
    saved: dict[str, Any],
    payloads: dict[str, bytes | None],
    witness: backup.PhysicalWitness,
) -> tuple[str, ...]:
    from contextlib import contextmanager

    admin, source, maintenance = MagicMock(), MagicMock(), MagicMock()
    for conn in (admin, source, maintenance):
        conn.autocommit = True
        conn.info.transaction_status = TransactionStatus.IDLE
    actual = [backup.Backend(n, str(n), 1, "test", "127.0.0.1", 39900 + n) for n in range(1, 51)]
    gate = MagicMock()
    gate.admin, gate.admin_backend = admin, actual[0]
    gate.client_logging = {str(b.pid): {"prefix": "%m [%p] ", "locale": "C"} for b in actual}
    gate.run.verification = "verify"
    gate.baseline = backup.ClusterStats("100", {})
    gate.expected = {
        "postgres": backup.SessionTotal(1, 50, None),
        "verify": backup.SessionTotal(22, 5, None),
    }
    counts = {"postgres": gate.expected["postgres"]}
    cid = "a" * 64
    owner = tuple({2: "b" * 32, 4: cid, 7: "national_src", 9: "551"}.get(i, "x") for i in range(21))
    physical = _physical_scan_fixture(
        monkeypatch, source, payloads, witness, owner, events, counts, fault, tmp_path / "backup"
    )
    monkeypatch.setattr(backup, "_cluster_stats", lambda _c: backup.ClusterStats("100", counts))
    original_one = backup._one

    def one(conn: Any, query: Any, args: tuple[object, ...] = ()) -> tuple[Any, ...]:
        if conn is admin:
            assert "pg_prepared_xacts" in query
            return int(fault == "prepared"), 0
        return original_one(conn, query, args)

    monkeypatch.setattr(backup, "_one", one)

    def activities() -> list[tuple[Any, ...]]:
        from dataclasses import astuple

        sessions = actual.copy()
        if fault == "active-writer":
            sessions[1] = backup.Backend(99, "200", 2, "national_writer", "127.0.0.1", 44444)
        return [
            (
                *astuple(backend),
                *(
                    ("active", False, True, False, "client backend")
                    if i == 0
                    else ("idle in transaction", False, True, False, "client backend")
                    if fault == "busy-owned" and i == 1
                    else ("idle", True, True, True, "client backend")
                ),
            )
            for i, backend in enumerate(sessions)
        ]

    admin.execute.return_value.fetchall.side_effect = activities

    def authenticate(selected: backup.Run, *, physical_connection: object = None) -> dict[str, Any]:
        if physical_connection is not None:
            assert physical_connection is maintenance and "released sockets" not in events
        events.append("auth")
        return physical

    monkeypatch.setattr(backup.Run, "authenticate", authenticate)

    @contextmanager
    def restored(_run: backup.Run, target: backup.Evidence, _state: dict[str, Any]) -> Any:
        events.append("held sockets")
        try:
            yield backup.HeldSource(
                gate,
                source,
                maintenance,
                tuple(actual[1:]),
                (target.publish("database.dump", b"dump"),),
            )
        finally:
            events.append("released sockets")

    monkeypatch.setattr(backup, "_restored_source", restored)
    monkeypatch.setattr(backup, "_inventory", lambda *_args, **_kw: {"postgres": 1})

    def snapshot(conn: object, _campaign: str, _period: int) -> dict[str, Any]:
        assert conn is source and "released sockets" not in events
        return (
            {**saved, "marker": "changed"}
            if fault == "changed-terminal" and "checkpoint-and-scan" in events
            else saved
        )

    monkeypatch.setattr(backup, "terminal_snapshot", snapshot)
    monkeypatch.setattr(
        storage,
        "stop_checked",
        partial(
            _retirement_stop_fixture,
            events=events,
            owner=owner,
            tmp_path=tmp_path,
            physical=physical,
            actual=actual,
            fault=fault,
        ),
    )
    return owner


@pytest.mark.parametrize(
    "fault",
    [
        "none",
        "unrelated_copy",
        "second_changed",
        "bulk_copy_failed",
        "missing_seal",
        "active-writer",
        "finished-writer",
        "busy-owned",
        "prepared",
        "changed-terminal",
        "missing-fenced-stop",
        "lost-before-stop",
        "foreign-at-stop",
        "duplicate-at-stop",
        "stale-stop",
        "stale-server-time",
        "changed-log",
        "restart-between-copies",
        "restart-after-copies",
        "restart-before-remove",
    ],
)
def test_retirement_needs_both_stopped_reads_and_reread_source_seals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:

    evidence = tmp_path / "evidence"
    evidence.mkdir(mode=0o700)
    (tmp_path / "backup").mkdir(mode=0o700)
    directory = backup.Evidence(evidence)
    saved = {"campaign": "campaign", "period": 2}
    directory.publish_json("completed-member.json", {"scope": "Designed custody input"})
    directory.publish_json("functional-terminal.json", saved)
    directory.publish("ownership", b"owner\n")
    payloads, witness = fixture()
    events: list[str] = []

    owner = _held_retirement_fixture(tmp_path, monkeypatch, events, fault, saved, payloads, witness)
    cid = owner[4]

    def stopped_source(*_args: Any) -> dict[str, Any]:
        events.append("stopped auth")
        changed = (
            fault == "restart-between-copies"
            and "pgdata.tar.partial" in events
            or fault == "restart-after-copies"
            and "pgdata-second.tar.partial" in events
            or fault == "restart-before-remove"
            and (tmp_path / "backup/recovery-seal.json").exists()
        )
        return {"incarnation": "different" if changed else "captured"}

    monkeypatch.setattr(backup, "_stopped", stopped_source)

    def inventory(
        _run: backup.Run,
        target: backup.Evidence,
        current: backup.PhysicalWitness,
        _ref: backup.Reference,
        _fenced_stop: backup.Reference,
    ) -> tuple[backup.Reference, dict[str, backup.Member]]:
        assert "stop" in events and "released sockets" in events
        return target.publish_json(
            "stopped-source-v1.json",
            {"scope": "separate reader fixture", "source": {"incarnation": "captured"}},
        ), stopped_members(payloads, current)

    monkeypatch.setattr(backup, "_stopped_inventory", inventory)
    monkeypatch.setattr(storage, "remove_stopped", lambda *_args: events.append("remove"))

    def copy(target: backup.Evidence, name: str, args: list[str]) -> backup.Reference:
        assert args == ["docker", "cp", "-a", cid + ":/var/lib/postgresql/data/.", "-"]
        assert "stop" in events and "released sockets" in events
        events.append(name)
        if fault == "bulk_copy_failed":
            raise backup.Refusal("simulated archive transport failure")
        files = dict(payloads)
        if fault == "unrelated_copy":
            files.clear()
        if fault == "second_changed" and name.startswith("pgdata-second"):
            files[RELATION] = b"changed relation in second copy"
        archive(target.path / name, files)
        (target.path / name).chmod(0o600)
        if fault == "missing_seal" and name.startswith("pgdata-second"):
            (target.path / "database.dump").write_bytes(b"changed")
        target.publish(name + ".stderr", b"")
        return target.reference(name)

    monkeypatch.setattr(backup, "_command", copy)
    if fault != "none":
        with pytest.raises(FileNotFoundError if fault == "missing-fenced-stop" else backup.Refusal):
            backup.backup_and_retire(tmp_path, evidence, owner, "campaign", 2)
        if fault in ("active-writer", "busy-owned", "prepared"):
            assert "checkpoint-and-scan" not in events
            assert (tmp_path / "backup/pre-checkpoint-quiescence.json").is_file()
        if fault in ("finished-writer", "changed-terminal"):
            assert "stop" not in events
            assert (tmp_path / "backup/post-physical-terminal.json").is_file()
        if fault == "finished-writer":
            assert (tmp_path / "backup/pre-stop-quiescence.json").is_file()
        if fault in (
            "lost-before-stop",
            "foreign-at-stop",
            "duplicate-at-stop",
            "stale-stop",
            "stale-server-time",
            "changed-log",
            "missing-fenced-stop",
        ):
            assert "stop" in events and "pgdata.tar.partial" not in events
        assert "remove" not in events
        assert (tmp_path / "backup/database.dump").exists()
    else:
        backup.backup_and_retire(tmp_path, evidence, owner, "campaign", 2)
        assert (
            events.index("stop")
            < events.index("pgdata.tar.partial")
            < events.index("pgdata-second.tar.partial")
        )
        assert events[-2:] == ["stopped auth", "remove"]
        assert (tmp_path / "backup/pgdata.tar").is_file()
        assert (tmp_path / "backup/pgdata-second.tar").is_file()


@pytest.mark.parametrize(
    "fault",
    [
        "none",
        "restore_failure",
        "wrong_restored",
        "wrong_probe",
        "foreign_session",
        "shared-grant",
        "shared-setting",
        "baseline-client",
    ],
)
def test_only_verified_restore_is_dropped_without_force(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:

    target = backup.Evidence(tmp_path)
    owner = ["x"] * 21
    owner[2], owner[4], owner[7], owner[8], owner[9] = (
        "1" * 32,
        "2" * 64,
        "national_original",
        "confined",
        "30",
    )
    run = backup.Run(tmp_path, tmp_path, tuple(owner), "campaign", 2)
    db = MagicMock()
    db.__enter__.return_value = db
    monkeypatch.setattr(backup, "_conn", lambda *_args: db)
    auth = MagicMock(return_value={})
    monkeypatch.setattr(backup.Run, "authenticate", auth)
    roster = {run.database: 30}
    state: dict[str, Any] = {
        "campaign": "campaign",
        "database": {"owner": "confined", "allows_connections": True, "connection_limit": -1},
        "markers": ["real P2"],
    }
    commands = []
    probes: list[str] = []
    seen = []
    baseline_read: list[bool] = []

    def inventory(
        conn: MagicMock,
        selected: backup.Run,
        verified_oid: int | None = None,
        admitted: object = None,
    ) -> dict[str, int]:
        if fault == "baseline-client" and baseline_read:
            raise backup.Refusal("already-counted client is still active before creation")
        if fault == "foreign_session" and probes == [run.database, run.verification]:
            raise backup.Refusal("unexpected client in task cluster")
        return roster

    def snapshot(conn: MagicMock, campaign: str, period: int) -> dict[str, Any]:
        seen.append(campaign)
        if len(seen) == 2:
            return {
                **state,
                "database": {**state["database"], "allows_connections": False},
                "markers": [] if fault == "wrong_restored" else state["markers"],
            }
        return state

    def probe(
        conn: MagicMock,
        selected: backup.Run,
        database: str,
        oid: int,
        verified_oid: int | None,
        gate: object = None,
    ) -> dict[str, str]:
        probes.append(database)
        return {
            "denied": "42501" if database == run.database or fault != "wrong_probe" else "allowed"
        }

    def command(
        directory: backup.Evidence, name: str, args: list[str], **kwargs: object
    ) -> backup.Reference:
        commands.append(args)
        if name == "restore.stdout" and fault == "restore_failure":
            raise backup.Refusal("synthetic restore failure")
        directory.publish(name + ".stderr", b"")
        return directory.publish(name, b"ok")

    monkeypatch.setattr(backup, "_inventory", inventory)
    monkeypatch.setattr(backup, "terminal_snapshot", snapshot)
    monkeypatch.setattr(backup, "_probes", probe)
    monkeypatch.setattr(backup, "_restrict_writer", lambda *_args: None)
    monkeypatch.setattr(backup, "_verify_create", lambda *_args: 31)
    monkeypatch.setattr(backup, "_db_privileges", lambda *_args: None)
    monkeypatch.setattr(backup, "_command", command)
    gate = MagicMock()
    gate.limit = -1
    baseline = backup.ClusterStats("startup", {run.database: backup.SessionTotal(30, 1, None)})
    gate.baseline = baseline
    gate.admin_backend = backup.Backend(5, "100", 5, "test", "127.0.0.1", 41500)

    def census(_c: object) -> backup.ClusterStats:
        baseline_read.append(True)
        return baseline

    monkeypatch.setattr(backup, "_cluster_stats", census)
    shared = {**state["database"], "allows_connections": False}
    if fault == "shared-grant":
        shared["acl"] = [["writer", "unexpected", "CONNECT", True]]
    elif fault == "shared-setting":
        shared["settings"] = [["unexpected", "search_path=public"]]
    monkeypatch.setattr(backup, "_catalog", lambda _c, _n: shared)
    source, maintenance = MagicMock(), MagicMock()
    gate.final_fence.return_value.__enter__.return_value = (source, maintenance, ())
    gate.sessions = []
    monkeypatch.setattr(backup, "RestoreAdmission", lambda *_args: gate)
    if fault == "foreign_session":
        gate.check_fence.side_effect = backup.Refusal("unaccounted session")
    if fault == "none":
        with backup._restored_source(run, target, state) as held:
            assert held.source is source and held.maintenance is maintenance
        auth.assert_called_with(physical_connection=maintenance)
    else:
        with pytest.raises(backup.Refusal), backup._restored_source(run, target, state):
            pytest.fail("invalid restore reached physical handoff")
    calls = [
        call.args[0] if isinstance(call.args[0], str) else call.args[0].as_string()
        for call in db.execute.call_args_list
    ]
    drops = [statement for statement in calls if statement.startswith("DROP DATABASE")]
    assert drops == ([f'DROP DATABASE "{run.verification}"'] if fault == "none" else [])
    restore_command = [
        "docker",
        "exec",
        "-i",
        run.container,
        "pg_restore",
        "--exit-on-error",
        "--single-transaction",
        "-U",
        "test",
        "--dbname=" + run.verification,
    ]
    assert (restore_command in commands) == (fault != "baseline-client")
    assert all(
        not {"--no-owner", "--no-privileges", "--create", "--force"} & set(argv)
        for argv in commands
    )
    assert (tmp_path / "cluster-globals.sql").read_bytes() == b"ok"


@pytest.mark.parametrize(
    "fault", ["none", "reader_allowed_raw", "masked_denial", "read_only", "missing_dossier"]
)
def test_restricted_roles_must_read_production_data_and_receive_exact_denials(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fault: str
) -> None:
    import psycopg

    owner = ["x"] * 21
    owner[2] = "f" * 32
    run = backup.Run(tmp_path, tmp_path, tuple(owner), "campaign", 2)
    selected = []

    def connect(
        selected_run: backup.Run, database: str, role: str, *, application: str
    ) -> MagicMock:
        login = MagicMock()
        login.__enter__.return_value = login
        login.info.backend_pid = 551
        kind = application.removeprefix("wayne_probe_")
        selected.append(role)

        def execute(query: str, args: tuple[object, ...] = ()) -> MagicMock:
            cursor = MagicMock()
            if "WHERE pid=pg_backend_pid()" in query:
                cursor.fetchall.return_value = [(551, "started", 30, role, "127.0.0.1", 52722)]
            elif "pg_has_role" in query:
                cursor.fetchall.return_value = [
                    (role, role, database, "on" if fault == "read_only" else "off", owner[2], True)
                ]
            elif "v_archive_revision_known_v2" in query:
                cursor.fetchall.return_value = (
                    []
                    if fault == "missing_dossier"
                    else [("county", "26163", 2, "ab" * 32, "cd" * 32)]
                )
            elif "v_observer_material_state_v1" in query:
                cursor.fetchall.return_value = [(2, "material", "marker")]
            else:
                assert "babylon_state.material_tick_v3" in query or "pg_read_binary_file" in query
                if fault == "masked_denial":
                    raise psycopg.errors.UndefinedTable()
                if fault != "reader_allowed_raw" or kind != "reader":
                    raise psycopg.errors.InsufficientPrivilege()
                cursor.fetchall.return_value = [("private",)]
            return cursor

        login.execute.side_effect = execute
        return login

    monkeypatch.setattr(backup, "_conn", connect)
    monkeypatch.setattr(backup, "_inventory", lambda *_args: {})
    if fault == "none":
        result = backup._probes(MagicMock(), run, "database", 30, 31)
        assert selected == [
            "national_reader_" + owner[2][:12],
            "national_observer_" + owner[2][:12],
        ]
        assert (
            result["reader"]["denied_sqlstates"]
            == result["observer"]["denied_sqlstates"]
            == ["42501", "42501"]
        )
    else:
        with pytest.raises(
            psycopg.errors.UndefinedTable if fault == "masked_denial" else backup.Refusal
        ):
            backup._probes(MagicMock(), run, "database", 30, 31)


def test_database_creation_uses_captured_writer_and_locale_and_pins_fresh_oid(
    tmp_path: Path,
) -> None:
    owner = ["x"] * 21
    owner[2], owner[8], owner[9] = "e" * 32, "confined", "30"
    run = backup.Run(tmp_path, tmp_path, tuple(owner), "campaign", 2)
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = [(31, "confined")]
    catalog = {
        "owner": "confined",
        "provider": "b",
        "encoding": "UTF8",
        "locale": "C.UTF-8",
        "collate": "C.UTF-8",
        "ctype": "C.UTF-8",
        "icu_rules": None,
        "connection_limit": -1,
    }
    assert backup._verify_create(conn, run, catalog) == 31
    query = conn.execute.call_args_list[0].args[0].as_string()
    assert f'CREATE DATABASE "{run.verification}" WITH TEMPLATE template0 OWNER "confined"' in query
    assert "ALLOW_CONNECTIONS false CONNECTION LIMIT 0" in query
    assert "BUILTIN_LOCALE 'C.UTF-8' LC_COLLATE 'C.UTF-8' LC_CTYPE 'C.UTF-8'" in query
    conn.execute.return_value.fetchall.return_value = [(30, "confined")]
    with pytest.raises(backup.Refusal):
        backup._verify_create(conn, run, catalog)
    with pytest.raises(backup.Refusal):
        backup._verify_create(conn, run, {**catalog, "owner": "test"})


def test_delegated_database_grants_and_role_settings_retain_the_original_authorities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    initial = {
        "owner": "writer",
        "acl_default": True,
        "acl": [["writer", None, "CONNECT", False]],
        "settings": [],
    }
    final = {
        "owner": "writer",
        "acl_default": False,
        "acl": [["delegate", "reader", "CONNECT", False], ["writer", "delegate", "CONNECT", True]],
        "settings": [[None, "timezone=UTC"], ["reader", "search_path=pg_catalog, public"]],
    }
    conn = MagicMock()
    monkeypatch.setattr(backup, "_catalog", MagicMock(side_effect=[initial, final]))
    backup._db_privileges(conn, "verification", final)
    calls = [
        c.args[0] if isinstance(c.args[0], str) else c.args[0].as_string()
        for c in conn.execute.call_args_list
    ]
    assert 'REVOKE ALL PRIVILEGES ON DATABASE "verification" FROM PUBLIC' in calls
    assert calls.index('SET LOCAL ROLE "writer"') < calls.index('SET LOCAL ROLE "delegate"')
    assert 'GRANT CONNECT ON DATABASE "verification" TO "delegate" WITH GRANT OPTION' in calls
    assert 'ALTER DATABASE "verification" SET "timezone" FROM CURRENT' in calls
    assert 'ALTER ROLE "reader" IN DATABASE "verification" SET "search_path" FROM CURRENT' in calls
    bad = {**final, "acl": [["outside", "reader", "CREATE", True]]}
    monkeypatch.setattr(backup, "_catalog", MagicMock(return_value=initial))
    with pytest.raises(backup.Refusal, match="grantor chain"):
        backup._db_privileges(conn, "verification", bad)


@pytest.mark.parametrize("identical", [True, False])
def test_numeric_namespace_requires_unique_translation_or_globally_identity_maps(
    tmp_path: Path, identical: bool
) -> None:
    files, witness = fixture()
    stopped = stopped_members(files, witness)
    mapping = "0 0 4294967295" if identical else "0 0 100\n100 20000 65536"
    witness.physical.update(uid_map=mapping, gid_map=mapping)
    witness.physical["host"].update(uid=71, gid=73)
    path = tmp_path / "copy.tar"
    stopped = stopped_members(files, witness)
    archive(path, files)
    with path.open("rb") as stream:
        if identical:
            assert (
                backup.archive_manifest(stream, witness, stopped)[1]
                == "identity-mapped-host-and-container"
            )
        else:
            with pytest.raises(backup.Refusal, match="ambiguous"):
                backup.archive_manifest(stream, witness, stopped)


@pytest.mark.parametrize(
    "fault",
    [
        "control-version",
        "catalog-version",
        "control-crc",
        "zero-record",
        "wal-record-crc",
        "foreign-checkpoint",
        "both-copies-truncated",
        "zero-padded-relation",
        "pgss-running-after-stop",
        "pgss-no-dump",
        "pgss-disabled",
        "unknown-stat-temp",
    ],
)
def test_independent_stopped_bind_witness_rejects_corruption(tmp_path: Path, fault: str) -> None:
    files, witness = fixture()
    stopped = stopped_members(files, witness)
    if fault in ("control-version", "catalog-version", "control-crc"):
        control = bytearray(files["global/pg_control"] or b"")
        control[{"control-version": 8, "catalog-version": 12, "control-crc": 288}[fault]] ^= 1
        files["global/pg_control"] = bytes(control)
    elif fault in ("zero-record", "wal-record-crc", "foreign-checkpoint"):
        wal = bytearray(files[WAL] or b"")
        if fault == "zero-record":
            wal[80:194] = bytes(114)
        else:
            wal[100 if fault == "wal-record-crc" else 129] ^= 1
        files[WAL] = bytes(wal)
    elif fault == "both-copies-truncated":
        files[RELATION] = b""
    elif fault == "zero-padded-relation":
        files[RELATION] = bytes(8192)
    elif fault == "pgss-running-after-stop":
        files["pg_stat_tmp/pgss_query_texts.stat"] = b"retained"
    elif fault == "pgss-no-dump":
        del files["pg_stat/pg_stat_statements.stat"]
    elif fault == "pgss-disabled":
        witness.physical["pgss"]["save"] = "off"
    else:
        files["pg_stat_tmp/unknown"] = b"unproved"
    for name in ("first.tar", "second.tar"):
        path = tmp_path / name
        archive(path, files)
        with path.open("rb") as stream, pytest.raises(backup.Refusal):
            backup.archive_manifest(stream, witness, stopped)


@pytest.mark.parametrize(
    "fault", ["none", "undrained", "missing", "wrong_dirty", "wrong_batch", "wrong_knowledge"]
)
def test_same_snapshot_requires_drained_terminal_archive_chain(fault: str) -> None:
    conn = MagicMock()
    markers = [{"tick": n, "hash": str(n) * 64} for n in (1, 2)]
    rows: list[list[Any]] = [
        [
            m["tick"],
            m["hash"],
            m["hash"],
            m["hash"],
            "b" * 64,
            "c" * 64,
            "c" * 64,
            "d" * 64,
            "d" * 64,
        ]
        for m in markers
    ]
    totals = (2, 2, 1) if fault == "undrained" else (None, 2, 0)
    if fault == "missing":
        rows.pop()
    elif fault == "wrong_dirty":
        rows[-1][1] = "7" * 64
    elif fault == "wrong_batch":
        rows[-1][4] = None
    elif fault == "wrong_knowledge":
        rows[-1][-1] = "8" * 64
    conn.execute.return_value.fetchall.side_effect = [[totals], rows]
    if fault == "none":
        result = backup._archive_terminal(conn, "campaign", markers)
        assert (
            result["pending"] == 0
            and result["watermark"] == 2
            and result["terminal_marker"] == markers[-1]["hash"]
        )
        assert len(result["receipts"]) == 2
    else:
        with pytest.raises(backup.Refusal):
            backup._archive_terminal(conn, "campaign", markers)


def test_interrupted_command_preserves_partial_streams_and_primary_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os
    import stat
    from contextlib import ExitStack

    outputs = backup.Evidence(tmp_path)
    calls = []
    real = os.fsync

    def sync(fd: int) -> None:
        name = os.readlink(f"/proc/self/fd/{fd}")
        calls.append((name, stat.S_ISDIR(os.fstat(fd).st_mode)))
        real(fd)
        if name.endswith(".stderr"):
            raise OSError("stderr fsync failure")

    monkeypatch.setattr(os, "fsync", sync)
    with (
        pytest.raises(backup.Refusal, match="primary monitor failure") as exc,
        ExitStack() as stack,
    ):
        out = stack.enter_context(backup._output(outputs, "restore.partial"))
        err = stack.enter_context(backup._output(outputs, "restore.partial.stderr"))
        out.write(b"interrupted stdout")
        err.write(b"interrupted stderr")
        raise backup.Refusal("primary monitor failure")
    assert (tmp_path / "restore.partial").read_bytes() == b"interrupted stdout"
    assert (tmp_path / "restore.partial.stderr").read_bytes() == b"interrupted stderr"
    assert {path for path, directory in calls if not directory} == {
        str(tmp_path / "restore.partial"),
        str(tmp_path / "restore.partial.stderr"),
    }
    assert sum(directory for _, directory in calls) >= 4
    assert any("stderr fsync failure" in note for note in exc.value.__notes__)


@pytest.mark.parametrize(
    "fault",
    [
        "none",
        "short_foreign",
        "unflushed",
        "reset",
        "restart",
        "wrong_incarnation",
        "unobserved",
        "extra_live",
        "foreign_transport",
        "startup_lock",
        "replication_slots",
        "finished-source",
        "finished-maintenance",
    ],
)
def test_restore_admission_requires_actual_incarnation_closed_gate_and_exact_cumulative_sessions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fault: str,
) -> None:
    owner = ["x"] * 21
    owner[2] = "1" * 32
    owner[8] = "writer"
    run = backup.Run(tmp_path, tmp_path, tuple(owner), "campaign", 2)
    admin = MagicMock()
    state: dict[str, Any] = {
        "open": False,
        "limit": 0,
        "sessions": 0,
        "epoch": None,
        "server": "100",
        "locks": 0,
        "senders": 0,
        "other": {30: 11, 5: 7},
        "grant": False,
    }

    def query(conn: Any, stmt: str, args: tuple[object, ...] = ()) -> tuple[Any, ...]:
        if "FROM pg_locks" in stmt:
            return (state["locks"],)
        if "pg_postmaster_start_time" in stmt:
            return state["server"], "on", "on", state["senders"]
        if "datallowconn" in stmt:
            return (313, "writer", state["open"], state["limit"])
        return (313, "writer")

    monkeypatch.setattr(backup, "_one", query)
    monkeypatch.setattr(backup, "_inventory", lambda *_args: {})
    actual = backup.Backend(120, "1000", 313, "test", None, -1)
    roster = [actual]
    monkeypatch.setattr(backup, "_clients", lambda _admin: roster)
    original = {
        run.database: backup.SessionTotal(30, 11, None),
        "postgres": backup.SessionTotal(5, 7, None),
    }
    prior = backup.ClusterStats("100", original)
    admin.execute.return_value.fetchall.side_effect = lambda: (
        [(name, total.oid, state["other"][total.oid], None) for name, total in original.items()]
        + [(run.verification, 313, state["sessions"], state["epoch"])]
    )
    monkeypatch.setattr(
        backup, "_own_backend", lambda *_args: backup.Backend(1, "1", 5, "test", "127.0.0.1", 1000)
    )
    gate = backup.RestoreAdmission(admin, run, 313, -1, prior)
    state["limit"] = -1
    if fault == "foreign_transport":
        roster[0] = backup.Backend(120, "1000", 313, "test", "127.0.0.1", 50111)
    elif fault == "extra_live":
        roster.append(backup.Backend(121, "1001", 313, "test", None, -1))
    if fault in ("foreign_transport", "extra_live"):
        with pytest.raises(backup.Refusal):
            gate.observe_restore()
        return
    if fault != "unobserved":
        gate.observe_restore()
    if fault == "wrong_incarnation":
        roster[0] = backup.Backend(120, "2000", 313, "test", None, -1)
        with pytest.raises(backup.Refusal):
            gate.observe_restore()
        return
    roster.clear()
    state["sessions"] = 2 if fault == "short_foreign" else 0 if fault == "unflushed" else 1
    if fault in ("finished-source", "finished-maintenance"):
        # A client changed shared authority and completed. No active PID remains.
        state["other"][30 if fault == "finished-source" else 5] += 1
        state["grant"] = True
    changes: dict[str, dict[str, object]] = {
        "reset": {"epoch": "new"},
        "restart": {"server": "101"},
        "startup_lock": {"locks": 1},
        "replication_slots": {"senders": 1},
    }
    state.update(changes.get(fault, {}))
    if fault == "none":
        gate.finish_restore()
        assert gate.sessions[0]["backend"]["started"] == "1000"
    else:
        with pytest.raises(backup.Refusal):
            gate.finish_restore()


@pytest.mark.parametrize("fault", ["none", "wrong-remnant", "wrong-timeline", "torn-record"])
def test_shutdown_checkpoint_can_span_a_segment_with_an_authenticated_continuation(
    tmp_path: Path, fault: str
) -> None:
    files, witness = fixture()
    stopped = stopped_members(files, witness)
    control = bytes.fromhex(
        "52b2070000000000a40600008979100c010000000000000000f1536500000000e0ff1f0000000000e0ff1f0000000000010000000100000001000000010000000003000000000000014000000000000000000000000000000000000000000000000000000000000000f15365000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000080000000000000087d632410020000000000200002000000000100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000003b7e7914"
    ).ljust(8192, b"\0")
    record = bytes.fromhex(
        "720000000000000028001000000000000000000004f2e4c2ff58e0ff1f0000000000010000000100000001000000010000000003000000000000014000000000000000000000000000000000000000000000000000000000000000f153650000000000000000000000000000000000000000"
    )
    files["global/pg_control"] = control
    prior = bytearray(files[WAL] or b"")
    struct.pack_into("<HHIQI", prior, SEGMENT - 8192, 0xD116, 0, 1, 2 * SEGMENT - 8192, 0)
    prior[-32:] = record[:32]
    files[WAL] = bytes(prior)
    following = bytearray(SEGMENT)
    struct.pack_into(
        "<HHIQI",
        following,
        0,
        0xD116,
        3,
        2 if fault == "wrong-timeline" else 1,
        2 * SEGMENT,
        len(record) - 32 + (fault == "wrong-remnant"),
    )
    struct.pack_into("<QII", following, 24, SYSTEM, SEGMENT, 8192)
    following[40 : 40 + len(record) - 32] = record[32:]
    if fault == "torn-record":
        following[80] ^= 1
    files["pg_wal/000000010000000000000002"] = bytes(following)
    path = tmp_path / "cross.tar"
    stopped = stopped_members(files, witness)
    archive(path, files)
    with path.open("rb") as stream:
        if fault == "none":
            assert backup.archive_manifest(stream, witness, stopped)[1] == "container"
        else:
            with pytest.raises(backup.Refusal):
                backup.archive_manifest(stream, witness, stopped)


def test_command_monitor_failure_syncs_both_streams_and_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os
    import subprocess
    from typing import BinaryIO

    seen = []
    real = os.fsync

    def fsync(fd: int) -> None:
        seen.append(os.readlink(f"/proc/self/fd/{fd}"))
        real(fd)

    def popen(args: list[str], *, stdin: object, stdout: BinaryIO, stderr: BinaryIO) -> MagicMock:
        stdout.write(b"partial native stdout")
        stderr.write(b"partial native stderr")
        proc = MagicMock()
        proc.__enter__.return_value = proc
        proc.poll.return_value = None
        return proc

    monkeypatch.setattr(os, "fsync", fsync)
    monkeypatch.setattr(subprocess, "Popen", popen)
    monitor = MagicMock()
    monitor.observe_restore.side_effect = backup.Refusal("unexpected backend")
    with pytest.raises(backup.Refusal, match="unexpected backend"):
        backup._command(backup.Evidence(tmp_path), "partial", ["synthetic"], monitor=monitor)
    for name in ("partial", "partial.stderr"):
        assert str(tmp_path / name) in seen and (tmp_path / name).read_bytes().startswith(
            b"partial native"
        )
    assert seen.count(str(tmp_path)) >= 4


@pytest.mark.parametrize("middle", ["populated", "new", "masked"])
def test_stopped_middle_block_requires_complete_source_occupancy(
    tmp_path: Path, middle: str
) -> None:
    files, witness = fixture()
    stopped = stopped_members(files, witness)
    page = files[RELATION]
    assert isinstance(page, bytes)
    src = page + (page if middle == "populated" else bytes(backup.PAGE)) + page
    if middle == "masked":
        src = src[: backup.PAGE + 40] + b"x" + src[backup.PAGE + 41 :]
    witness.members[RELATION] = backup.Member("file", 0o600, 71, 73, len(src), None)
    sizes = {RELATION: len(src)}
    witness.physical["relation_sizes"] = sizes
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = (src,)
    if middle == "masked":
        with pytest.raises(backup.Refusal):
            backup._source_pages(conn, sizes)
        return
    samples = backup._source_pages(conn, sizes)
    witness.physical["relation_page_occupancy"] = samples
    files[RELATION] = page + bytes(backup.PAGE) + page
    for filename in ["first.tar", "second.tar"]:
        target = tmp_path / filename
        stopped = stopped_members(files, witness)
        archive(target, files)
        with target.open("rb") as stream:
            if middle == "new":
                assert backup.archive_manifest(stream, witness, stopped)[1] == "container"
            else:
                with pytest.raises(backup.Refusal):
                    backup.archive_manifest(stream, witness, stopped)


@pytest.mark.parametrize(
    "fault",
    ["none", "toast-heap-truncated", "toast-index-truncated", "missing-toast", "missing-index"],
)
def test_toast_payload_and_index_require_their_measured_extents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    files, witness = fixture()
    stopped = stopped_members(files, witness)
    root_name = "babylon_state.tick_commit"
    monkeypatch.setattr(backup, "REQUIRED_ROWS", {root_name})
    toast = "base/551/4000"
    index = "base/551/4001"
    rows = [
        (2930, root_name, "r", 4000, None, None, RELATION, 8192),
        (4000, "pg_toast.pg_toast_2930", "t", 0, None, None, toast, 8192),
        (4001, "pg_toast.pg_toast_2930_index", "i", 0, 4000, True, index, 8192),
    ]
    if fault in ("missing-toast", "missing-index"):
        rows.pop(1 if fault == "missing-toast" else 2)
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = rows
    if fault in ("missing-toast", "missing-index"):
        with pytest.raises(backup.Refusal):
            backup._terminal_relations(conn, 551)
        return
    relations, sizes = backup._terminal_relations(conn, 551)
    assert set(relations.values()) == {RELATION, toast, index}
    witness.relations.update(relations)
    witness.physical["relation_sizes"] = sizes
    witness.physical["relation_page_occupancy"] = dict.fromkeys(sizes, "01")
    for name in (toast, index):
        files[name] = files[RELATION]
        witness.members[name] = witness.members[RELATION]
    if fault != "none":
        files[toast if fault == "toast-heap-truncated" else index] = b""
    for filename in ["first.tar", "second.tar"]:
        target = tmp_path / filename
        stopped = stopped_members(files, witness)
        archive(target, files)
        with target.open("rb") as stream:
            if fault == "none":
                assert backup.archive_manifest(stream, witness, stopped)[1] == "container"
            else:
                with pytest.raises(backup.Refusal):
                    backup.archive_manifest(stream, witness, stopped)


@pytest.mark.parametrize("fault", ["none", "wrong-prefix", "locale-not-set", "set-denied"])
def test_shutdown_logging_establishes_session_locale_before_reading_settings(fault: str) -> None:
    # The selected PG17 cluster reports the inherited default as an empty string.
    # Only a successful session SET supplies affirmative English-log evidence.
    locale = "de_DE" if fault == "locale-not-set" else ""
    conn = MagicMock()

    def execute(statement: str, args: tuple[object, ...] = ()) -> MagicMock:
        nonlocal locale
        cursor = MagicMock()
        if statement == "SET SESSION lc_messages = 'C'":
            if fault == "set-denied":
                raise backup.psycopg.errors.InsufficientPrivilege("permission denied")
            if fault != "locale-not-set":
                locale = "C"
        else:
            assert "current_setting('lc_messages')" in statement
            cursor.fetchall.return_value = [
                (
                    "%p" if fault == "wrong-prefix" else "%m [%p] ",
                    locale,
                    "default",
                    "stderr",
                    "off",
                    "warning",
                    "GMT",
                )
            ]
        return cursor

    conn.execute.side_effect = execute
    if fault == "set-denied":
        with pytest.raises(backup.psycopg.errors.InsufficientPrivilege):
            backup._stop_logging(conn)
    elif fault != "none":
        with pytest.raises(backup.Refusal):
            backup._stop_logging(conn)
    else:
        assert backup._stop_logging(conn) == {
            "prefix": "%m [%p] ",
            "locale": "C",
            "verbosity": "default",
            "destination": "stderr",
            "collector": "off",
            "minimum": "warning",
            "timezone": "GMT",
        }


def _change_held_fence(
    fault: str, live: list[backup.Backend], totals: dict[str, backup.SessionTotal]
) -> None:
    if fault == "lost-slot":
        live.pop()
    elif fault == "replaced-slot":
        live[-1] = backup.Backend(live[-1].pid, "foreign", 5, "test", "127.0.0.1", 50101)
    elif fault == "unobserved-reset":
        t = totals["babylon_test"]
        totals["babylon_test"] = backup.SessionTotal(t.oid, t.sessions, "new")
    elif fault == "helper-extra":
        t = totals["template1"]
        totals["template1"] = backup.SessionTotal(t.oid, t.sessions + 1, t.reset)
    elif fault == "changed-database":
        t = totals["template1"]
        totals["template1"] = backup.SessionTotal(200, t.sessions, t.reset)


def _fence_query(
    conn: Any,
    stmt: str,
    args: tuple[object, ...] = (),
    *,
    owner: list[str],
    admin: MagicMock,
    own_admin: backup.Backend,
    closed_limit: list[int],
    fault: str,
) -> tuple[Any, ...]:
    if "log_line_prefix" in stmt:
        return (
            "%p" if fault == "wrong-log-prefix" else "%m [%p] ",
            "de_DE" if fault == "wrong-messages" else "C",
            "default",
            "stderr",
            "off",
            "warning",
            "Etc/UTC",
        )
    if "max_connections" in stmt:
        return 48 if fault == "wrong-capacity" else 50, 0, "0"
    if "pg_postmaster_start_time" in stmt:
        return "start", "on", "on", 0
    if "pg_locks" in stmt:
        return (0,)
    if "datallowconn" in stmt:
        return 51, owner[8], False, closed_limit[0]
    if "idle_session_timeout" in stmt:
        return ("0",)
    if "babylon.disposable_runtime" in stmt:
        return owner[2], owner[20], "test", "test", "postgres"
    assert "pid=pg_backend_pid()" in stmt
    backend = own_admin if conn is admin else conn.actual
    return (
        backend.pid,
        backend.started,
        backend.oid,
        backend.role,
        backend.address,
        backend.port,
    )


@pytest.mark.parametrize(
    "fault",
    [
        "none",
        "foreign-source",
        "foreign-postgres",
        "unobserved-reset",
        "lost-slot",
        "replaced-slot",
        "can't-fill",
        "wrong-capacity",
        "wrong-log-prefix",
        "wrong-messages",
        "helper-extra",
        "changed-database",
    ],
)
def test_final_drop_requires_complete_live_slot_fence_and_cluster_counters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:

    owner = ["x"] * 21
    owner[2], owner[7], owner[8], owner[9], owner[20] = (
        "3" * 32,
        "national_src",
        "writer",
        "31",
        "123",
    )
    run = backup.Run(tmp_path, tmp_path, tuple(owner), "campaign", 2)
    names = {"template0": 4, "template1": 1, "postgres": 5, "babylon_test": 30, run.database: 31}
    totals = {name: backup.SessionTotal(oid, 4, None) for name, oid in names.items()}
    prior = backup.ClusterStats("start", totals.copy())
    totals[run.verification] = backup.SessionTotal(51, 0, None)
    live: list[backup.Backend] = []
    own_admin = backup.Backend(9, "2", 5, "test", "127.0.0.1", 50100)
    admin = MagicMock()
    admin.info.backend_pid = own_admin.pid
    closed_limit = [0]
    received: list[tuple[str, int]] = []
    released = []

    def execute(stmt: str, *args: object) -> MagicMock:
        cursor = MagicMock()
        if "LEFT JOIN pg_stat_database" in stmt:
            cursor.fetchall.return_value = [
                (name, t.oid, t.sessions, t.reset) for name, t in totals.items()
            ]
        elif "JOIN pg_roles" in stmt:
            cursor.fetchall.return_value = [
                (name, t.oid, owner[8] if name in (run.database, run.verification) else "test")
                for name, t in totals.items()
            ]
        return cursor

    def connect(_run: backup.Run, database: str) -> Any:
        if len(received) == 30 and fault == "can't-fill":
            raise backup.Refusal("could not acquire a required client slot")
        row = totals[database]
        pid = 1000 + len(received)
        actual = backup.Backend(pid, str(pid), row.oid, "test", "127.0.0.1", 50000 + pid)
        conn = MagicMock()
        conn.actual = actual
        conn.info.backend_pid = pid
        totals[database] = backup.SessionTotal(row.oid, row.sessions + 1, row.reset)
        received.append((database, pid))
        live.append(actual)

        def close() -> None:
            released.append(pid)
            if actual in live:
                live.remove(actual)

        conn.close.side_effect = close
        return conn

    monkeypatch.setattr(
        backup,
        "_one",
        partial(
            _fence_query,
            owner=owner,
            admin=admin,
            own_admin=own_admin,
            closed_limit=closed_limit,
            fault=fault,
        ),
    )
    admin.execute.side_effect = execute
    monkeypatch.setattr(backup, "_conn", connect)
    monkeypatch.setattr(backup, "_clients", lambda _admin: sorted(live, key=lambda b: b.pid))
    gate = backup.RestoreAdmission(admin, run, 51, -1, prior)
    closed_limit[0] = -1
    databases = {run.verification: {"grants": {"writer"}}}

    def decision() -> None:
        if fault in ("foreign-source", "foreign-postgres"):
            # A completed client mutated the verification database's shared ACL.
            # With no active foreign session, the final census must still refuse.
            db = run.database if fault == "foreign-source" else "postgres"
            t = totals[db]
            totals[db] = backup.SessionTotal(t.oid, t.sessions + 1, t.reset)
            databases[run.verification]["grants"].add("unexpected")
        with gate.final_fence() as (source, maintenance, held):
            assert (
                source.info.backend_pid == received[0][1]
                and maintenance.info.backend_pid == received[1][1]
                and [row[0] for row in received[:2]] == [run.database, "template1"]
            )
            assert len(live) == len(held) == 49
            _change_held_fence(fault, live, totals)
            gate.check_fence(held)
            del databases[run.verification]

    if fault == "none":
        decision()
    else:
        with pytest.raises(backup.Refusal):
            decision()
    assert (run.verification in databases) == (fault != "none")
    if fault in ("foreign-source", "foreign-postgres"):
        assert databases[run.verification]["grants"] == {"writer", "unexpected"}
    assert sorted(released) == sorted(pid for _, pid in received)


@pytest.mark.parametrize("fault", ["foreign-source", "missing-checkpoint"])
def test_checkpoint_flush_requires_the_authenticated_original_before_block_occupancy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    owner = ["x"] * 21
    owner[2], owner[7], owner[9] = "3" * 32, "national_src", "31"
    run = backup.Run(tmp_path, tmp_path, tuple(owner), "campaign", 2)
    conn = MagicMock()
    conn.__enter__.return_value = conn
    monkeypatch.setattr(backup, "_conn", lambda *_args: conn)
    results = [
        (
            "test",
            "test",
            run.database,
            "foreign" if fault == "foreign-source" else owner[2],
            "123",
            "31",
        ),
        (None,),
    ]
    monkeypatch.setattr(backup, "_one", lambda *_args: results.pop(0))
    with pytest.raises(backup.Refusal):
        backup._physical_witness(run, {"cluster": "123"}, conn)
    statements = [c.args[0] for c in conn.execute.call_args_list]
    assert statements == (
        []
        if fault == "foreign-source"
        else ["CHECKPOINT", "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"]
    )


@pytest.mark.parametrize("occupancy", [{}, {RELATION: ""}, {RELATION: "03"}, {RELATION: "xx"}])
def test_stopped_archive_refuses_missing_or_unmeasured_occupancy(
    tmp_path: Path,
    occupancy: dict[str, str],
) -> None:
    files, witness = fixture()
    stopped = stopped_members(files, witness)
    witness.physical["relation_page_occupancy"] = occupancy
    path = tmp_path / "copy.tar"
    archive(path, files)
    with path.open("rb") as stream, pytest.raises(backup.Refusal):
        backup.archive_manifest(stream, witness, stopped)


@pytest.mark.parametrize("database", [None, "verified"])
def test_shared_database_owner_acl_and_settings_bind_the_same_target(database: str | None) -> None:
    conn = MagicMock()
    results = [
        [("writer", "UTF8", "C", "C", "b", "C.UTF-8", None, -1, False, False)],
        [("writer", "reader", "CONNECT", False)],
        [(None, "timezone=UTC")],
    ]

    def execute(stmt: str, args: tuple[object, ...]) -> MagicMock:
        assert args == (database,) and stmt.count("%s") == len(args)
        cursor = MagicMock()
        cursor.fetchall.return_value = results.pop(0)
        return cursor

    conn.execute.side_effect = execute
    catalog = backup._catalog(conn, database)
    assert catalog["owner"] == "writer" and catalog["settings"] == [[None, "timezone=UTC"]]
    assert catalog["acl"] == [["writer", "reader", "CONNECT", False]] and not results


def test_physical_inventory_uses_busybox_advertised_interfaces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    files, witness = fixture()
    source = MagicMock()
    owner = tuple(
        {2: "b" * 32, 4: "a" * 64, 7: "national_src", 9: "551"}.get(i, "x") for i in range(21)
    )
    receipts = tmp_path / "backup"
    receipts.mkdir()
    (receipts / "pre-checkpoint-quiescence.json").write_bytes(b"{}")
    events: list[str] = []
    physical = _physical_scan_fixture(
        monkeypatch, source, files, witness, owner, events, {}, "none", receipts
    )
    run = backup.Run(tmp_path, tmp_path, owner, "campaign", 2)
    result = backup._physical_witness(run, physical, source)
    assert result.members[RELATION] == backup.Member("file", 0o600, 71, 73, 8192, None)
    assert result.members["PG_VERSION"].sha256 == hashlib.sha256(b"17\n").hexdigest()
    assert "source_checkpoint" not in physical
    assert result.physical["source_checkpoint"] == "0/100028"
    assert events == ["checkpoint-and-scan"]


def _inventory_run(tmp_path: Path) -> backup.Run:
    owner = tuple("a" * 64 if i == 4 else "x" for i in range(21))
    return backup.Run(tmp_path, tmp_path, owner, "campaign", 2)


def _inventory_authority() -> dict[str, Any]:
    return {
        "container_root": {"major": 253, "minor": 5, "mode": 0o700, "uid": 70, "gid": 1000},
        "pg_version": "17\n",
        "lineage": "reviewed lineage\n",
    }


@pytest.mark.parametrize(
    "record",
    [
        b"",
        b"8180 600 70 70 3 64773",  # Unterminated numeric record.
        b"8180 600 70 70 3 64773\n8180 600 70 70 3 64773\n",
        b"8180 600 70 70 3\n",
        b"8180\t600 70 70 3 64773\n",
        b"8180 700 70 70 3 64773\n",  # Octal/raw permission disagreement.
        b"8180 600 70 70 3 64774\n",  # Untraversed foreign mount/device.
        b"a180 600 70 70 3 64773\n",  # Link; stat must not dereference it.
        b"1180 600 70 70 3 64773\n",  # FIFO.
        b"c180 600 70 70 3 64773\n",  # Socket.
        b"2180 600 70 70 3 64773\n",  # Character device.
        b"10000 0 70 70 3 64773\n",  # Raw mode overflow.
        b"8180 600 -1 70 3 64773\n",
        b"8180 600 4294967296 70 3 64773\n",
        b"8180 600 70 4294967296 3 64773\n",
        b"8180 600 70 70 -1 64773\n",
        b"8180 600 70 70 9223372036854775808 64773\n",
        b"8180 600 70 70 3 18446744073709551616\n",
        b"8180 600 70 70 3 6e4\n",
        b"8180 600 70 70 3 64773\r\n",
        b"8180 600 70 70 3 64773\n./injected\n",
    ],
)
def test_container_inventory_refuses_partial_or_unsafe_numeric_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, record: bytes
) -> None:
    def acquire(args: list[str], *, timeout: int = 0) -> bytes:
        if args[5:] == ["find", ".", "-xdev", "-print0"]:
            return b".\0./ordinary\0"
        assert args[5:9] == ["stat", "-c", "%f %a %u %g %s %d", "--"]
        assert args[9:] == [".", "./ordinary"]
        return b"41c0 700 70 1000 4096 64773\n" + record

    monkeypatch.setattr(storage, "_exec_bytes", acquire)
    with pytest.raises(backup.Refusal):
        backup._container_members(_inventory_run(tmp_path), _inventory_authority())


@pytest.mark.parametrize(
    "names",
    [
        b"",
        b".\0./missing-nul",
        b"./missing-root\0",
        b".\0.\0",
        b".\0\0",
        b".\0./duplicate\0./duplicate\0",
        b".\0unprefixed\0",
        b".\0/absolute\0",
        b".\0././alias\0",
        b".\0./a/../escape\0",
        b".\0./a//alias\0",
        b".\0./a/\0",
        b".\0./.\0",
        b".\0./pg_tblspc/external\0",
        b".\0./invalid-utf8-\xff\0",
    ],
)
def test_container_inventory_refuses_ambiguous_or_incomplete_nul_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, names: bytes
) -> None:
    def acquire(args: list[str], *, timeout: int = 0) -> bytes:
        assert args[5:] == ["find", ".", "-xdev", "-print0"]
        return names

    monkeypatch.setattr(storage, "_exec_bytes", acquire)
    with pytest.raises(backup.Refusal):
        backup._container_members(_inventory_run(tmp_path), _inventory_authority())


@pytest.mark.parametrize("utility", ["find", "stat", "cat"])
def test_container_inventory_propagates_nonzero_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, utility: str
) -> None:
    def acquire(args: list[str], *, timeout: int = 0) -> bytes:
        if args[5] == utility:
            # Even apparently complete stdout cannot authorize success on a nonzero exit.
            raise subprocess.CalledProcessError(
                1, args, b"41c0 700 70 1000 4096 64773\n", b"failure"
            )
        if args[5] == "find":
            return b".\0./PG_VERSION\0"
        assert args[5] == "stat"
        return b"41c0 700 70 1000 4096 64773\n8180 600 70 70 3 64773\n"

    monkeypatch.setattr(storage, "_exec_bytes", acquire)
    with pytest.raises(subprocess.CalledProcessError):
        backup._container_members(_inventory_run(tmp_path), _inventory_authority())


@pytest.mark.parametrize(
    "fault",
    ["membership-added", "membership-removed", "root-type", "root-mode", "root-uid", "root-gid"],
)
def test_container_inventory_refuses_membership_or_bound_root_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    passes = 0

    def acquire(args: list[str], *, timeout: int = 0) -> bytes:
        nonlocal passes
        if args[5] == "find":
            passes += 1
            if passes == 2 and fault == "membership-added":
                return b".\0./ordinary\0./new\0"
            if passes == 2 and fault == "membership-removed":
                return b".\0"
            return b".\0./ordinary\0"
        assert args[5] == "stat"
        root = {
            "root-type": b"81c0 700 70 1000 4096 64773\n",
            "root-mode": b"41ed 755 70 1000 4096 64773\n",
            "root-uid": b"41c0 700 71 1000 4096 64773\n",
            "root-gid": b"41c0 700 70 70 4096 64773\n",
        }.get(fault, b"41c0 700 70 1000 4096 64773\n")
        return root + b"8180 600 70 70 3 64773\n"

    monkeypatch.setattr(storage, "_exec_bytes", acquire)
    with pytest.raises(backup.Refusal):
        backup._container_members(_inventory_run(tmp_path), _inventory_authority())


def test_container_inventory_keeps_nul_names_and_nonuniform_ids_across_bounded_batches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Long names force batching by encoded argv bytes even below a typical count limit.
    names = [".", "./line\nbreak", "./-leading", "./tab\tquote'$(literal)", "./é"] + [
        "./" + str(n) + "x" * 3900 for n in range(20)
    ]
    passes = 0
    batches: list[list[str]] = []

    def acquire(args: list[str], *, timeout: int = 0) -> bytes:
        nonlocal passes
        assert args[:5] == ["docker", "exec", "-w", storage.PGDATA, "a" * 64]
        if args[5:] == ["find", ".", "-xdev", "-print0"]:
            passes += 1
            ordered = names if passes == 1 else list(reversed(names))
            return b"\0".join(p.encode() for p in ordered) + b"\0"
        assert args[5:9] == ["stat", "-c", "%f %a %u %g %s %d", "--"]
        assert sum(len(arg.encode()) + 1 + 8 for arg in args) <= 32768
        batches.append(args[9:])
        return b"".join(
            b"41c0 700 70 1000 4096 64773\n" if p == "." else b"8180 600 70 70 3 64773\n"
            for p in args[9:]
        )

    monkeypatch.setattr(storage, "_exec_bytes", acquire)
    members = backup._container_members(_inventory_run(tmp_path), _inventory_authority())
    assert passes == 2 and len(batches) > 1
    assert [path for batch in batches for path in batch] == names
    assert "." not in members and len(members) == len(names) - 1
    for name in ("line\nbreak", "-leading", "tab\tquote'$(literal)", "é"):
        assert members[name] == backup.Member("file", 0o600, 70, 70, 3, None)


@pytest.mark.parametrize("fault", [None, "symlink", "fifo", "stable-length", "lineage", "version"])
def test_container_inventory_matches_real_portable_utilities_on_tiny_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    import os
    import stat

    root = tmp_path / "tiny"
    root.mkdir(mode=0o700)
    (root / "PG_VERSION").write_bytes(b"17\n")
    (root / ".babylon-postgres-lineage-v1").write_bytes(LINEAGE)
    (root / "nested").mkdir(mode=0o750)
    (root / "nested/-name\nwith\ttabs").write_bytes(b"payload")
    (root / "-leading").write_bytes(b"x")
    if fault == "symlink":
        (root / "link").symlink_to("PG_VERSION")
    elif fault == "fifo":
        os.mkfifo(root / "pipe")
    elif fault == "lineage":
        (root / ".babylon-postgres-lineage-v1").write_bytes(b"foreign\n")
    elif fault == "version":
        (root / "PG_VERSION").write_bytes(b"18\n")
    measured = root.stat()
    physical = {
        **_inventory_authority(),
        "container_root": {
            "major": os.major(measured.st_dev),
            "minor": os.minor(measured.st_dev),
            "uid": measured.st_uid,
            "gid": measured.st_gid,
            "mode": stat.S_IMODE(measured.st_mode),
        },
    }

    def acquire(args: list[str], *, timeout: int = 15) -> bytes:
        assert args[:5] == ["docker", "exec", "-w", storage.PGDATA, "a" * 64]
        assert args[5] in {"find", "stat", "cat"}
        # This subprocess only reads this test-owned tiny fixture, never host PGDATA.
        result = subprocess.run(
            args[5:], cwd=root, capture_output=True, check=True, timeout=timeout
        ).stdout
        if fault == "stable-length" and args[5] == "cat" and args[-1] == "./PG_VERSION":
            return result + b"changed"
        return result

    monkeypatch.setattr(storage, "_exec_bytes", acquire)
    if fault:
        with pytest.raises(backup.Refusal):
            backup._container_members(_inventory_run(tmp_path), physical)
    else:
        members = backup._container_members(_inventory_run(tmp_path), physical)
        assert set(members) == {
            "PG_VERSION",
            ".babylon-postgres-lineage-v1",
            "nested",
            "nested/-name\nwith\ttabs",
            "-leading",
        }
        for name, member in members.items():
            value = (root / name).lstat()
            assert (member.kind, member.mode, member.uid, member.gid, member.size) == (
                "dir" if stat.S_ISDIR(value.st_mode) else "file",
                stat.S_IMODE(value.st_mode),
                value.st_uid,
                value.st_gid,
                value.st_size,
            )
        assert members["PG_VERSION"].sha256 == hashlib.sha256(b"17\n").hexdigest()
        assert members[".babylon-postgres-lineage-v1"].sha256 == hashlib.sha256(LINEAGE).hexdigest()
        assert members["nested/-name\nwith\ttabs"].sha256 is None


def designed_custom_dump(database: str) -> bytes:
    """PG17 custom archive v1.16: one table and one readable COPY data block."""

    def integer(n: int) -> bytes:
        return bytes((int(n < 0),)) + abs(n).to_bytes(4, "little")

    def strings(*items: str | None) -> bytes:
        return b"".join(
            integer(-1) if s is None else integer(len(s)) + s.encode("ascii") for s in items
        )

    header = b"PGDMP" + bytes((1, 16, 0, 4, 8, 1, 0))
    date = b"".join(integer(n) for n in (0, 0, 0, 9, 10, 126, 0))
    table = (
        integer(1)
        + integer(0)
        + strings("1259", "16386", "tick_commit", "TABLE")
        + integer(2)
        + strings(
            "CREATE TABLE babylon_state.tick_commit(resolve_tick bigint);",
            "DROP TABLE babylon_state.tick_commit;",
            None,
            "babylon_state",
            None,
            "heap",
        )
        + integer(ord("r"))
        + strings("test", "false", None)
        + bytes((3,))
        + bytes(8)
    )
    data = (
        integer(2)
        + integer(1)
        + strings("0", "16386", "tick_commit", "TABLE DATA")
        + integer(3)
        + strings(
            None,
            None,
            "COPY babylon_state.tick_commit (resolve_tick) FROM stdin;\n",
            "babylon_state",
            None,
            None,
        )
        + integer(0)
        + strings("test", "false", "1", None)
        + bytes((1,))
        + bytes(8)
    )
    rows = b"2\n\\.\n\n\n"
    return (
        header
        + date
        + strings(database, "17.11", "17.11")
        + integer(2)
        + table
        + data
        + bytes((1,))
        + integer(2)
        + integer(len(rows))
        + rows
        + integer(0)
    )


def retained_pair_recovery(
    run, evidence, backup_store, physical, functional, *, reader_period: int = 2
):
    """Retain independent PG17 fixture tars, canonical restore/held-client and shutdown evidence."""
    from copy import deepcopy
    from dataclasses import asdict

    owner = run.owner
    database, verification = run.database, run.verification
    restored = {**functional, "database": {**functional["database"], "allows_connections": False}}
    marker = functional["markers"][-1]
    probes = {
        k: {
            "role": f"national_{k}_{owner[2][:12]}",
            "denied_sqlstates": ["42501", "42501"],
            "allowed": [2, marker["identity"], marker["hash"]]
            if k == "observer"
            else ["county", "26163", reader_period, "ab" * 32, "cd" * 32],
        }
        for k in ("reader", "observer")
    }
    files = []

    def record(name, value):
        ref = backup_store.publish_json(name, value)
        files.append(ref)
        return ref

    def raw(name, data):
        ref = backup_store.publish(name, data)
        files.append(ref)
        return ref

    record("original-terminal.json", functional)
    record("restored-terminal.json", restored)
    record("original-probes.json", probes)
    record("restored-probes.json", probes)
    initial = {database: 551, "postgres": 5, "template1": 1, "template0": 4, "babylon_test": 10}
    oid = initial[database] + 1
    record(
        "verification-identity.json",
        {"name": verification, "owner": owner[8], "oid": oid, "initial": initial},
    )
    for name, content in (
        ("database.dump", designed_custom_dump(database)),
        ("cluster-globals.sql", b"CREATE ROLE test;\n"),
        (
            "restore-list.txt",
            f""";
; Archive created at 2026-11-09 00:00:00 UTC
;     dbname: {database}
;     TOC Entries: 2
;     Compression: none
;     Dump Version: 1.16-0
;     Format: CUSTOM
;     Integer: 4 bytes
;     Offset: 8 bytes
;     Dumped from database version: 17.11
;     Dumped by pg_dump version: 17.11
;
;
; Selected TOC Entries:
;
1; 1259 16386 TABLE babylon_state tick_commit test
2; 0 16386 TABLE DATA babylon_state tick_commit test
""".encode(),
        ),
        ("restore.stdout", b""),
    ):
        raw(name, content)
        raw(name + ".stderr", b"")
    base = {
        "postmaster": "123000",
        "databases": {
            k: {"oid": v, "sessions": 0, "reset": None}
            for k, v in {**initial, verification: oid}.items()
        },
    }
    stats = deepcopy(base)

    def backend(pid, db, role):
        return backup.Backend(
            pid, str(pid), stats["databases"][db]["oid"], role, "127.0.0.1", 33000 + pid
        )

    admin = backend(1, "postgres", "test")
    held = [admin]
    sessions = []

    def session(purpose, db, limit, role):
        b = backend(2 + len(sessions), db, role)
        if purpose == "pg_restore":
            b = backup.Backend(b.pid, b.started, b.oid, b.role, None, -1)
        if purpose == "final-fence":
            held.append(b)
        stats["databases"][db]["sessions"] += 1
        sessions.append(
            {
                "purpose": purpose,
                "database": db,
                "open_limit": limit,
                "closed_limit": None if limit is None else -1,
                "expected_sessions": stats["databases"][db]["sessions"],
                "backend": asdict(b),
            }
        )

    for name in ("pg_restore", "restore-authority", "reader", "observer", "final-snapshot"):
        restricted = name in probes
        session(
            name,
            verification,
            1 if restricted else 0,
            probes[name]["role"] if restricted else "test",
        )
    for db in [database, "template1"] + ["postgres"] * (backup.NATIVE_CLIENT_SLOTS - 3):
        session("final-fence", db, None, "test")
    record(
        "verification-admission.json",
        {
            "restore_evidence": {r.path: r.model_dump() for r in files},
            "verification_oid": oid,
            "original_allow_connections": True,
            "verified_final_allow_connections": False,
            "source_connection_limit": -1,
            "creation_connection_limit": 0,
            "baseline": base,
            "maintenance_backend": asdict(admin),
            "sessions": sessions,
            "final_cluster_stats": stats,
            "final_shared_database": restored["database"],
            "held_client_slots": len(held),
        },
    )
    del stats["databases"][verification]
    for stem in ("pre-checkpoint", "pre-stop"):
        record(
            stem + "-quiescence.json",
            {
                "expected_stats": stats,
                "actual_stats": stats,
                "expected_clients": [asdict(b) for b in held],
                "clients": [
                    asdict(
                        backup.ClientActivity(
                            b,
                            "active" if b == admin else "idle",
                            b != admin,
                            True,
                            b != admin,
                            "client backend",
                        )
                    )
                    for b in held
                ],
                "observer_pid": admin.pid,
                "prepared_transactions": 0,
                "entering_backends": 0,
                "client_logging": {
                    str(b.pid): {
                        "prefix": "%m [%p] ",
                        "locale": "C",
                        "verbosity": "default",
                        "destination": "stderr",
                        "collector": "off",
                        "minimum": "warning",
                        "timezone": "UTC",
                    }
                    for b in held
                },
            },
        )
    record("pre-checkpoint-terminal.json", functional)
    record("post-physical-terminal.json", functional)
    payloads, witness = fixture()
    witness.physical.update(physical)
    struct_control = bytearray(payloads["global/pg_control"])
    struct.pack_into("<Q", struct_control, 0, int(physical["cluster"]))
    struct.pack_into("<I", struct_control, 288, backup._crc32c(bytes(struct_control[:288])))
    payloads["global/pg_control"] = bytes(struct_control)
    wal = bytearray(payloads[WAL])
    struct.pack_into("<Q", wal, 24, int(physical["cluster"]))
    payloads[WAL] = bytes(wal)
    source = MagicMock()
    with pytest.MonkeyPatch.context() as probes:
        admitted = _physical_scan_fixture(
            probes, source, payloads, witness, owner, [], {}, "none", backup_store.path
        )
        assert physical == admitted and "source_checkpoint" not in admitted
        witness = backup._physical_witness(run, admitted, source)
    assert witness.physical["source_checkpoint"] == "0/100028"
    wref = record("pre-stop-physical.json", asdict(witness))
    attempt = evidence.publish_json(
        "native-fenced-stop-attempt-v1.json",
        {
            "container": run.container,
            "image": owner[6],
            "container_pid": 1,
            "executable": "/usr/lib/postgresql/17/bin/postgres",
            "host_pid": physical["pid"],
            "host": physical["host"],
            "stop_signal": "SIGINT",
            "image_stop_signal": "SIGINT",
            "bind": {"mounts": physical["mounts"], "port_request": physical["port_request"]},
            "uid": physical["server_uid"],
            "gid": physical["server_gid"],
            "since": "2026-11-07T11:00:01+00:00",
        },
    )

    def log_line(seconds, pid, msg):
        return f"2026-11-07T11:00:0{seconds}Z 2026-11-07 11:00:0{seconds}.000 UTC [{pid}] {msg}\n"

    log = evidence.publish(
        "clean-shutdown.log",
        (
            log_line(1, 1, "LOG: received fast shutdown request")
            + "".join(
                log_line(2, b.pid, "FATAL:  terminating connection due to administrator command")
                for b in held
            )
            + log_line(3, 1, "LOG: database system is shut down")
        ).encode(),
    )
    stop = evidence.publish_json(
        "native-fenced-stop-v1.json",
        {
            "attempt": attempt.model_dump(),
            "log": log.model_dump(),
            "fast": "2026-11-07T11:00:01+00:00",
            "clean": "2026-11-07T11:00:03+00:00",
            "finished": "2026-11-07T11:00:04+00:00",
            "container": run.container,
            "image": owner[6],
            "host": physical["host"],
            "exit_code": 0,
            "oom_killed": False,
        },
    )
    *_, exits = backup._shutdown_evidence(evidence, backup_store, run, physical, tuple(held))
    files.append(exits)
    stopped = stopped_members(payloads, witness)
    cid, token = "c" * 64, "d" * 32
    confinement = backup._helper_expected(run, witness, cid, token)
    stopped_ref = record(
        "stopped-source-v1.json",
        {
            "version": 1,
            "pre_stop": wref.model_dump(),
            "fenced_stop": stop.model_dump(),
            "source": {
                "container": run.container,
                "image": run.owner[6],
                "daemon": physical["daemon"],
                "mounts": physical["mounts"],
                "host": physical["host"],
                "state": {
                    "Status": "exited",
                    "Running": False,
                    "ExitCode": 0,
                    "OOMKilled": False,
                    "Pid": 0,
                    "StartedAt": SOURCE_STARTED,
                    "FinishedAt": SOURCE_FINISHED,
                },
            },
            "helper_created": {
                "confinement": confinement,
                "status": "created",
                "pid": 0,
                "started": DOCKER_ZERO,
            },
            "helper_running": {
                "confinement": confinement,
                "status": "running",
                "pid": 12,
                "started": HELPER_STARTED,
            },
            "members": {k: asdict(v) for k, v in stopped.items()},
            "changes": backup._source_changes(witness, stopped),
        },
    )
    for name in ("pgdata.tar", "pgdata-second.tar"):
        archive(backup_store.path / name, payloads)
        (backup_store.path / name).chmod(0o600)
        ref = backup_store.reference(name)
        files.append(ref)
        raw(name + ".partial.stderr", b"")
        with backup_store.file(name) as stream:
            members, namespace = backup.archive_manifest(stream, witness, stopped)
        record(
            name + ".manifest.json",
            {
                "version": 2,
                "stopped_source": stopped_ref.model_dump(),
                "archive": ref.model_dump(),
                "root_and_source": wref.model_dump(),
                "numeric_id_space": namespace,
                "members": {k: asdict(v) for k, v in members.items()},
            },
        )
    record(
        "retained-storage.json",
        {
            "primary_file_bytes": sum(m.size or 0 for m in members.values() if m.kind == "file"),
            "backup_files_before_seal": [
                {
                    "path": r.path,
                    "bytes": r.bytes,
                    "allocated": (backup_store.path / r.path).stat().st_blocks * 512,
                }
                for r in files
            ],
            "available_media_bytes_at_measurement": 1024**3,
        },
    )
    backup_store.publish_json(
        "recovery-seal.json",
        {
            "version": 2,
            "completed_member": evidence.reference("completed-member.json").model_dump(),
            "owner": evidence.reference("ownership").model_dump(),
            "functional": evidence.reference("functional-terminal.json").model_dump(),
            "shutdown": log.model_dump(),
            "fenced_stop": stop.model_dump(),
            "stop_attempt": attempt.model_dump(),
            "retained": [r.model_dump() for r in files],
        },
    )


@pytest.fixture(scope="module")
def recovery_admission_bytes(tmp_path_factory: pytest.TempPathFactory) -> dict[str, bytes]:
    """Reuse one full native admission as input to each independently sealed recovery."""
    from tests.unit.tools.test_national_native_pair import member_bundle

    root = tmp_path_factory.mktemp("admitted-native-member")
    with pytest.MonkeyPatch.context() as paths:
        paths.setattr(storage, "RUN_PARENT", root)
        member_bundle(storage.PrivateEvidence(root), "normal_play")
        evidence = storage.PrivateEvidence(
            storage.member_run("smoke-01", "normal_play") / "evidence"
        )
    return {
        name: evidence.read_reference(evidence.reference(name))
        for name in (
            "ownership",
            "physical.json",
            "completed-member.json",
            "functional-terminal.json",
        )
    }


@pytest.mark.parametrize(
    ("table", "replacement", "reason"),
    [
        ("babylon_state.organizer_subject_v1", None, "campaign-table roster"),
        ("babylon_meta.watchlist", None, "campaign-table roster"),
        ("babylon_ref.county_identity", [], "campaign-table roster"),
        ("babylon_state.organizer_subject_v1", [], "organizer subject"),
        ("babylon_state.organizer_subject_v1", ["ab" * 32] * 6, "organizer subject"),
    ],
)
def test_resealed_campaign_table_roster(
    tmp_path: Path,
    recovery_admission_bytes: dict[str, bytes],
    table: str,
    replacement: list[str] | None,
    reason: str,
) -> None:
    evidence = storage.PrivateEvidence(tmp_path / "evidence")
    retained = storage.PrivateEvidence(tmp_path / "backup")
    for store in (evidence, retained):
        store.path.mkdir(mode=0o700)
    for name in ("ownership", "physical.json"):
        evidence.publish(name, recovery_admission_bytes[name])

    original = json.loads(recovery_admission_bytes["functional-terminal.json"])
    rows = original["campaign_rows_sha256"]
    assert any(r[0] == "r" and ".".join(r[1:3]) == table for r in original["object_authority"])
    if replacement is None:
        del rows[table]
    else:
        rows[table] = replacement
    changed = evidence.publish_json("functional-terminal.json", original)
    completed = json.loads(recovery_admission_bytes["completed-member.json"])
    entry = next(
        r for r in completed["evidence"] if r["path"] == "evidence/functional-terminal.json"
    )
    entry.update({"bytes": changed.bytes, "sha256": changed.sha256})
    evidence.publish_json("completed-member.json", completed)

    owner = tuple(recovery_admission_bytes["ownership"].decode().splitlines())
    run = backup.Run(storage.MEDIA_CHECKOUT, evidence.path, owner, original["campaign"], 2)
    physical = json.loads(recovery_admission_bytes["physical.json"])
    retained_pair_recovery(run, evidence, retained, physical, original)
    seal = json.loads(retained.read_reference(retained.reference("recovery-seal.json")))
    # All four independent backup files carry the same coordinated alteration.
    for name in ("original", "pre-checkpoint", "post-physical", "restored"):
        ref = retained.reference(f"{name}-terminal.json")
        assert json.loads(retained.read_reference(ref))["campaign_rows_sha256"] == rows
    with pytest.raises(backup.Refusal, match=reason):
        backup.verify_retained_backup(run, seal, original)


def altered_probes(data: bytes, name: str, fault: str) -> bytes:
    probes = json.loads(data)
    row = probes["reader"]["allowed"]
    if fault == "missing-revision":
        del row[2:]
    elif fault == "missing-row":
        del probes["reader"]["allowed"]
    elif fault == "malformed-row":
        probes["reader"]["allowed"] = None
    elif fault in ("late-period", "negative-period", "boolean-period"):
        row[2] = {"late-period": 3, "negative-period": -1, "boolean-period": True}[fault]
    elif fault in ("invalid-revision", "invalid-body"):
        row[3 if fault == "invalid-revision" else 4] = "g" * 64
    elif name == "restored-probes.json" and fault == "restored-null":
        probes = None
    elif name == "restored-probes.json" and fault == "restored-null-reader":
        probes["reader"] = None
    elif name == "restored-probes.json" and fault == "restored-period-float":
        assert type(row[2]) is int and row[2] == 2
        row[2] = 2.0
    elif name == "restored-probes.json" and fault == "restored-period-boolean":
        assert type(row[2]) is int and row[2] == 1
        row[2] = True
    else:
        return data
    return json.dumps(probes).encode()


@pytest.mark.parametrize(
    ("fault", "reason"),
    [
        ("header-only", "unreadable PostgreSQL custom archive"),
        ("data-truncated", "unreadable PostgreSQL custom archive"),
        ("different-listing", "actual PostgreSQL table of contents"),
        ("missing-revision", "Wayne reader revision"),
        ("missing-row", "Wayne reader revision"),
        ("malformed-row", "Wayne reader revision"),
        ("late-period", "Wayne reader revision"),
        ("negative-period", "Wayne reader revision"),
        ("boolean-period", "Wayne reader revision"),
        ("restored-null", "restricted probe evidence"),
        ("restored-null-reader", "restricted probe evidence"),
        ("restored-period-float", "Wayne reader revision"),
        ("restored-period-boolean", "Wayne reader revision"),
        ("invalid-revision", "Wayne reader revision"),
        ("invalid-body", "Wayne reader revision"),
    ],
)
def test_checksum_consistent_logical_recovery_refuses_incomplete_observations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
    reason: str,
    recovery_admission_bytes: dict[str, bytes],
) -> None:
    evidence, retained = (
        storage.PrivateEvidence(tmp_path / "evidence"),
        storage.PrivateEvidence(tmp_path / "backup"),
    )
    for store in (evidence, retained):
        store.path.mkdir(mode=0o700)
    for name, data in recovery_admission_bytes.items():
        evidence.publish(name, data)
    owner = tuple(recovery_admission_bytes["ownership"].decode().splitlines())
    original = json.loads(recovery_admission_bytes["functional-terminal.json"])
    physical = json.loads(recovery_admission_bytes["physical.json"])
    run = backup.Run(storage.MEDIA_CHECKOUT, evidence.path, owner, original["campaign"], 2)
    publish = storage.PrivateEvidence.publish

    def acquire(store: storage.PrivateEvidence, name: str, data: bytes) -> storage.Reference:
        if name == "database.dump" and fault == "header-only":
            data = data[:5]
        if name == "database.dump" and fault == "data-truncated":
            data = data[:-10]
        if name == "restore-list.txt" and fault == "different-listing":
            data = data.replace(b"tick_commit test", b"wrong_table test")
        if name in ("original-probes.json", "restored-probes.json"):
            data = altered_probes(data, name, fault)
        return publish(store, name, data)

    monkeypatch.setattr(storage.PrivateEvidence, "publish", acquire)
    retained_pair_recovery(
        run,
        evidence,
        retained,
        physical,
        original,
        reader_period=1 if fault == "restored-period-boolean" else 2,
    )
    seal = json.loads(retained.read_reference(retained.reference("recovery-seal.json")))
    with pytest.raises(backup.Refusal, match=reason):
        backup.verify_retained_backup(run, seal, original)


@pytest.mark.parametrize("bad", [None, "", "0/000000000", "0/100029", "0/100058"])
def test_shutdown_wal_requires_earlier_measured_source_checkpoint(
    tmp_path: Path, bad: object
) -> None:
    files, witness = fixture()
    stopped = stopped_members(files, witness)
    if bad is None:
        del witness.physical["source_checkpoint"]
    else:
        witness.physical["source_checkpoint"] = bad
    archive(tmp_path / "copy.tar", files)
    with (
        (tmp_path / "copy.tar").open("rb") as stream,
        pytest.raises(backup.Refusal, match="source checkpoint"),
    ):
        backup.archive_manifest(stream, witness, stopped)


def test_stopped_catalog_roster_is_independent_of_running_witness(tmp_path: Path) -> None:
    files, witness = fixture()
    stopped = stopped_members(files, witness)
    # Independent stopped input: catalog maintenance adds VM after the live census.
    files["global/1214_vm"] = bytes(8192)
    path = tmp_path / "stopped.tar"
    stopped = stopped_members(files, witness)
    archive(path, files)
    with path.open("rb") as stream:
        members, _ = backup.archive_manifest(stream, witness, stopped)
    assert members["global/1214_vm"].sha256 == hashlib.sha256(bytes(8192)).hexdigest()
    assert "global/1214_vm" not in witness.members


def local_stopped_source(tmp_path: Path) -> tuple[list[str], backup.PhysicalWitness]:
    import os
    from dataclasses import replace

    files, witness = fixture()
    root = tmp_path / "pgdata"
    root.mkdir(mode=0o700)
    for name, content in files.items():
        path = root / name
        if content is None:
            path.mkdir(mode=0o700, parents=True, exist_ok=True)
        else:
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            path.write_bytes(content)
            path.chmod(0o600)
    info = root.stat()
    witness.physical.update(
        server_uid=info.st_uid,
        server_gid=info.st_gid,
        uid_map="0 0 4294967295",
        gid_map="0 0 4294967295",
        host={
            "mode": 0o700,
            "uid": info.st_uid,
            "gid": info.st_gid,
            "major": os.major(info.st_dev),
            "minor": os.minor(info.st_dev),
            "inode": info.st_ino,
        },
    )
    witness.members.update(
        {name: replace(m, uid=info.st_uid, gid=info.st_gid) for name, m in witness.members.items()}
    )
    return ["env", "-C", str(root)], witness


@pytest.mark.parametrize(
    "fault",
    [
        "none",
        "symlink",
        "hardlink",
        "fifo",
        "hash-mutation",
        "late-mutation",
        "wrong-root",
        "cross-device",
    ],
)
def test_stopped_reader_hashes_actual_files_and_refuses_unsafe_or_mutating_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    import os

    command, witness = local_stopped_source(tmp_path)
    root = tmp_path / "pgdata"
    vm = root / "global/1214_vm"
    vm.write_bytes(bytes(8192))
    vm.chmod(0o600)
    if fault == "symlink":
        (root / "alias").symlink_to("global/1214_vm")
    elif fault == "hardlink":
        os.link(vm, root / "alias")
    elif fault == "fifo":
        os.mkfifo(root / "pipe")
    if fault == "wrong-root":
        witness.physical["host"]["inode"] += 1
    if fault == "cross-device":
        witness.physical["host"]["minor"] += 1
    execute = storage._exec_bytes
    reads = 0

    def observed(args: list[str], **kwargs: Any) -> bytes:
        nonlocal reads
        result = execute(args, **kwargs)
        if "sha256sum" in " ".join(args) and fault == "hash-mutation":
            vm.write_bytes(b"x" * 8192)
        if "find" in args:
            reads += 1
            if reads == 2 and fault == "late-mutation":
                vm.write_bytes(b"x" * 8192)
        return result

    monkeypatch.setattr(storage, "_exec_bytes", observed)
    if fault == "none":
        members = backup._read_stopped(command, witness)
        assert members["global/1214_vm"].sha256 == hashlib.sha256(vm.read_bytes()).hexdigest()
        assert all(m.sha256 is not None for m in members.values() if m.kind == "file")
    else:
        with pytest.raises(backup.Refusal):
            backup._read_stopped(command, witness)


@pytest.mark.parametrize("fault", ["extra", "missing", "vm-bytes", "heap-bytes"])
def test_stopped_oracle_refuses_same_length_damage_and_roster_changes(
    tmp_path: Path, fault: str
) -> None:
    files, witness = fixture()
    files["global/1214_vm"] = bytes(8192)
    files["global/1214"] = b"catalog" * 100
    stopped = stopped_members(files, witness)
    if fault == "extra":
        files["global/other_vm"] = bytes(8192)
    elif fault == "missing":
        del files["global/1214_vm"]
    else:
        name = "global/1214_vm" if fault == "vm-bytes" else "global/1214"
        value = files[name]
        assert value is not None
        files[name] = b"x" + value[1:]
    path = tmp_path / "damaged.tar"
    archive(path, files)
    with path.open("rb") as stream, pytest.raises(backup.Refusal, match="stopped source"):
        backup.archive_manifest(stream, witness, stopped)


def stopped_fence(
    directory: backup.Evidence, run: backup.Run, witness: backup.PhysicalWitness
) -> backup.Reference:
    return directory.publish_json(
        "native-fenced-stop-v1.json",
        {
            "container": run.container,
            "image": run.owner[6],
            "host": witness.physical["host"],
            "exit_code": 0,
            "oom_killed": False,
            "finished": "2026-11-07T11:00:04+00:00",
        },
    )


def helper_container(run: backup.Run, cid: str, token: str) -> dict[str, Any]:
    return {
        "Id": cid,
        "Image": run.owner[6],
        "Name": "/babylon-stopped-" + token,
        "Path": "/bin/sh",
        "Args": ["-ceu", "exec sleep 2147483647"],
        "RestartCount": 0,
        "Config": {
            "Labels": {"babylon.stopped-source": token},
            "User": "100071:200073",
            "Entrypoint": ["/bin/sh"],
            "Healthcheck": {"Test": ["NONE"]},
        },
        "HostConfig": {
            "NetworkMode": "none",
            "UsernsMode": "host",
            "PidMode": "",
            "IpcMode": "private",
            "ReadonlyRootfs": True,
            "Privileged": False,
            "CapAdd": None,
            "CapDrop": ["ALL"],
            "GroupAdd": None,
            "Devices": None,
            "SecurityOpt": ["no-new-privileges"],
            "RestartPolicy": {"Name": "no"},
        },
        "Mounts": [
            {
                "Type": "bind",
                "Source": str(run.evidence.parent / "pgdata"),
                "Destination": storage.PGDATA,
                "RW": False,
                "Propagation": "rprivate",
            }
        ],
        "State": {
            "Status": "created",
            "Running": False,
            "OOMKilled": False,
            "Pid": 0,
            "StartedAt": DOCKER_ZERO,
        },
    }


def damage_helper(record: dict[str, Any], fault: str) -> None:
    if fault == "image":
        record["Image"] = "wrong"
    if fault == "rw":
        record["Mounts"][0]["RW"] = True
    if fault == "network":
        record["HostConfig"]["NetworkMode"] = "host"
    if fault == "user":
        record["Config"]["User"] = "0:0"
    if fault == "groups":
        record["HostConfig"]["GroupAdd"] = ["0"]


@pytest.mark.parametrize(
    "fault",
    [
        "none",
        "image",
        "rw",
        "network",
        "user",
        "groups",
        "source",
        "helper-mutation",
        "create-error",
        "read-error",
    ],
)
def test_stopped_helper_refuses_before_use_and_cleans_exact_owned_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    import copy

    files, witness = fixture()
    witness.physical["mounts"] = []
    run = _inventory_run(tmp_path)
    directory = backup.Evidence(tmp_path)
    wref = directory.publish_json("pre-stop-physical.json", {})
    fence = stopped_fence(directory, run, witness)
    cid = "c" * 64
    record: dict[str, Any] = {}
    events: list[str] = []
    states = 0
    source = {
        "container": run.container,
        "image": run.owner[6],
        "daemon": witness.physical["daemon"],
        "mounts": [],
        "host": witness.physical["host"],
        "state": {
            "Status": "exited",
            "Running": False,
            "ExitCode": 0,
            "OOMKilled": False,
            "Pid": 0,
            "StartedAt": SOURCE_STARTED,
            "FinishedAt": SOURCE_FINISHED,
        },
    }

    def stopped(*_args: Any) -> dict[str, Any]:
        nonlocal states
        states += 1
        value = copy.deepcopy(source)
        if fault == "source" and states == 2:
            value["host"]["inode"] = 999
        return value

    def execute(args: list[str], **_kwargs: Any) -> bytes:
        if args[:2] == ["docker", "create"]:
            assert args[args.index("--pull") + 1] == "never"
            assert args[args.index("--entrypoint") + 1] == "/bin/sh"
            assert args[args.index("--user") + 1] == "100071:200073"
            assert args[args.index("--mount") + 1].endswith(
                ",destination=" + storage.PGDATA + ",readonly"
            )
            token = args[args.index("--label") + 1].split("=", 1)[1]
            record.update(helper_container(run, cid, token))
            Path(args[args.index("--cidfile") + 1]).write_text(cid)
            damage_helper(record, fault)
            if fault == "create-error":
                raise backup.Refusal("create interrupted")
            return (cid + "\n").encode()
        if args == ["docker", "start", cid]:
            events.append("start")
            record["State"].update(Status="running", Running=True, Pid=12, StartedAt=HELPER_STARTED)
            return (cid + "\n").encode()
        assert args == ["docker", "container", "rm", "--force", cid]
        events.append("removed")
        return (cid + "\n").encode()

    def read(*_args: Any) -> dict[str, backup.Member]:
        events.append("read")
        if fault == "read-error":
            raise backup.Refusal("read interrupted")
        if fault == "helper-mutation":
            record["State"]["StartedAt"] = "different"
        return stopped_members(files, witness)

    monkeypatch.setattr(storage, "_exec_bytes", execute)
    monkeypatch.setattr(storage, "_one_docker", lambda _kind, _target: copy.deepcopy(record))
    monkeypatch.setattr(backup, "_stopped", stopped)
    monkeypatch.setattr(backup, "_read_stopped", read)
    monkeypatch.setattr(backup, "_reader_mounts", lambda _command: None)
    if fault == "none":
        reference, members = backup._stopped_inventory(run, directory, witness, wref, fence)
        directory.verify(reference)
        packet = json.loads(directory.read_reference(reference))
        assert backup._retained_stopped(packet, run, witness, wref, fence) == members
    else:
        with pytest.raises(backup.Refusal):
            backup._stopped_inventory(run, directory, witness, wref, fence)
        assert not (tmp_path / "stopped-source-v1.json").exists()
    assert events[-1] == "removed"
    if fault in ("image", "rw", "network", "user", "groups", "create-error"):
        assert events == ["removed"]


@pytest.mark.parametrize("fault", ["none", "rw", "nested", "same-device-nested", "missing"])
def test_stopped_reader_mount_namespace_is_readonly_and_has_no_nested_mount(
    monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    row = b"31 23 0:1 / /var/lib/postgresql/data ro,relatime - ext4 /dev/data rw\n"
    if fault == "rw":
        row = row.replace(b"ro,relatime", b"rw,relatime")
    if fault in ("nested", "same-device-nested"):
        row += b"32 31 0:1 / /var/lib/postgresql/data/global ro - ext4 /dev/data rw\n"
    if fault == "missing":
        row = b""
    monkeypatch.setattr(storage, "_exec_bytes", lambda *_a, **_kw: row)
    if fault == "none":
        backup._reader_mounts(["confined"])
    else:
        with pytest.raises(backup.Refusal):
            backup._reader_mounts(["confined"])


@pytest.mark.parametrize(
    "fault",
    [
        "version",
        "missing",
        "unknown",
        "hash",
        "kind",
        "owner-boolean",
        "readonly-integer",
        "source",
        "pre-stop-ref",
        "created-null",
        "created-list",
        "created-object",
        "running-timestamp",
        "finished-incarnation",
    ],
)
def test_stopped_receipt_refuses_malformed_or_substituted_independent_proof(
    tmp_path: Path, fault: str
) -> None:
    from dataclasses import asdict

    files, witness = fixture()
    witness.physical["mounts"] = []
    run = _inventory_run(tmp_path)
    wref = backup.Reference(path="pre-stop-physical.json", bytes=2, sha256="a" * 64)
    fence = stopped_fence(backup.Evidence(tmp_path), run, witness)
    members = stopped_members(files, witness)
    confinement = backup._helper_expected(run, witness, "c" * 64, "d" * 32)
    packet = {
        "version": 1,
        "pre_stop": wref.model_dump(),
        "fenced_stop": fence.model_dump(),
        "source": {
            "container": run.container,
            "image": run.owner[6],
            "daemon": witness.physical["daemon"],
            "mounts": [],
            "host": witness.physical["host"],
            "state": {
                "Status": "exited",
                "Running": False,
                "ExitCode": 0,
                "OOMKilled": False,
                "Pid": 0,
                "StartedAt": SOURCE_STARTED,
                "FinishedAt": SOURCE_FINISHED,
            },
        },
        "helper_created": {
            "confinement": confinement,
            "status": "created",
            "pid": 0,
            "started": DOCKER_ZERO,
        },
        "helper_running": {
            "confinement": dict(confinement),
            "status": "running",
            "pid": 12,
            "started": HELPER_STARTED,
        },
        "members": {k: asdict(v) for k, v in members.items()},
        "changes": backup._source_changes(witness, members),
    }
    assert backup._retained_stopped(packet, run, witness, wref, fence) == members
    if fault == "version":
        packet["version"] = 2
    if fault == "missing":
        del packet["members"]
    if fault == "unknown":
        packet["extra"] = "unadmitted"
    if fault == "hash":
        packet["members"][RELATION]["sha256"] = "0" * 64
    if fault == "kind":
        packet["members"][RELATION]["kind"] = "symlink"
    if fault == "owner-boolean":
        packet["members"][RELATION]["uid"] = True
    if fault == "readonly-integer":
        packet["helper_created"]["confinement"]["readonly"] = 1
    if fault == "source":
        packet["source"]["container"] = "other"
    if fault == "pre-stop-ref":
        packet["pre_stop"]["sha256"] = "0" * 64
    if fault == "created-null":
        packet["helper_created"]["started"] = None
    if fault == "created-list":
        packet["helper_created"]["started"] = []
    if fault == "created-object":
        packet["helper_created"]["started"] = {}
    if fault == "running-timestamp":
        packet["helper_running"]["started"] = "not-a-timestamp"
    if fault == "finished-incarnation":
        packet["source"]["state"]["FinishedAt"] = "2026-11-07T11:00:05Z"

    with pytest.raises(backup.Refusal):
        backup._retained_stopped(packet, run, witness, wref, fence)


@pytest.mark.parametrize("fault", ["old-seal", "missing-proof", "tampered-proof"])
def test_recovery_admission_requires_new_seal_and_immutable_stopped_source(
    tmp_path: Path, recovery_admission_bytes: dict[str, bytes], fault: str
) -> None:
    evidence = storage.PrivateEvidence(tmp_path / "evidence")
    retained = storage.PrivateEvidence(tmp_path / "backup")
    for store in (evidence, retained):
        store.path.mkdir(mode=0o700)
    for name, content in recovery_admission_bytes.items():
        evidence.publish(name, content)
    owner = tuple(recovery_admission_bytes["ownership"].decode().splitlines())
    original = json.loads(recovery_admission_bytes["functional-terminal.json"])
    physical = json.loads(recovery_admission_bytes["physical.json"])
    run = backup.Run(storage.MEDIA_CHECKOUT, evidence.path, owner, original["campaign"], 2)
    retained_pair_recovery(run, evidence, retained, physical, original)
    seal = json.loads(retained.read_reference(retained.reference("recovery-seal.json")))
    if fault == "old-seal":
        del seal["version"]
    elif fault == "missing-proof":
        seal["retained"] = [r for r in seal["retained"] if r["path"] != "stopped-source-v1.json"]
    else:
        (retained.path / "stopped-source-v1.json").write_bytes(b"{}")
    with pytest.raises(backup.Refusal):
        backup.verify_retained_backup(run, seal, original)


@pytest.mark.parametrize(
    "finished,accepted",
    [
        ("2026-11-07T11:00:04.000000999Z", True),
        ("2026-11-07T11:00:04.000001000Z", False),
        ("2026-11-07T11:00:05.000000999Z", False),
        ("not-a-timestamp", False),
        ("2026-99-07T11:00:04Z", False),
    ],
)
def test_live_stopped_source_must_be_the_authenticated_fenced_incarnation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, finished: str, accepted: bool
) -> None:
    from contextlib import nullcontext

    _, witness = fixture()
    witness.physical["mounts"] = []
    evidence = tmp_path / "evidence"
    active = tmp_path / "active-lock"
    evidence.mkdir(mode=0o700)
    active.mkdir(mode=0o700)
    run = _inventory_run(evidence)
    owner = ("\n".join(run.owner) + "\n").encode()
    store = backup.Evidence(evidence)
    store.publish("ownership", owner)
    backup.Evidence(active).publish("active", owner)
    fence = store.publish_json(
        "native-fenced-stop-v1.json",
        {
            "container": run.container,
            "image": run.owner[6],
            "host": witness.physical["host"],
            "exit_code": 0,
            "oom_killed": False,
            "finished": "2026-11-07T11:00:04+00:00",
        },
    )
    record = {
        "State": {
            "Status": "exited",
            "Running": False,
            "ExitCode": 0,
            "OOMKilled": False,
            "Pid": 0,
            "StartedAt": "2026-11-07T10:59:00Z",
            "FinishedAt": finished,
        }
    }
    monkeypatch.setattr(storage, "_daemon_endpoint", lambda: None)
    monkeypatch.setattr(storage, "held_native_lock", lambda _root: active)
    monkeypatch.setattr(storage, "pinned_ancestry", lambda _path: nullcontext([]))
    monkeypatch.setattr(
        storage, "_media_creation", lambda *_args: {"daemon": witness.physical["daemon"]}
    )
    monkeypatch.setattr(storage, "_one_docker", lambda *_args: record)
    monkeypatch.setattr(storage, "container_mounts", lambda *_args: {"mounts": []})
    monkeypatch.setattr(storage, "_host_identity", lambda _path: witness.physical["host"])
    if accepted:
        assert backup._stopped(run, witness, fence)["state"]["FinishedAt"] == finished
    else:
        with pytest.raises(backup.Refusal, match="timestamp|incarnation"):
            backup._stopped(run, witness, fence)


def test_resealed_stopped_receipt_cannot_substitute_a_later_clean_incarnation(
    tmp_path: Path, recovery_admission_bytes: dict[str, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    evidence = storage.PrivateEvidence(tmp_path / "evidence")
    retained = storage.PrivateEvidence(tmp_path / "backup")
    for store in (evidence, retained):
        store.path.mkdir(mode=0o700)
    for name, content in recovery_admission_bytes.items():
        evidence.publish(name, content)
    owner = tuple(recovery_admission_bytes["ownership"].decode().splitlines())
    original = json.loads(recovery_admission_bytes["functional-terminal.json"])
    physical = json.loads(recovery_admission_bytes["physical.json"])
    run = backup.Run(storage.MEDIA_CHECKOUT, evidence.path, owner, original["campaign"], 2)
    publish = storage.PrivateEvidence.publish

    def substitute(store: storage.PrivateEvidence, name: str, data: bytes) -> storage.Reference:
        if name == "stopped-source-v1.json":
            packet = json.loads(data)
            packet["source"]["state"]["StartedAt"] = "2026-11-07T11:00:04.100000000Z"
            packet["source"]["state"]["FinishedAt"] = "2026-11-07T11:00:05.000000000Z"
            data = storage.canonical_json(packet)
        return publish(store, name, data)

    monkeypatch.setattr(storage.PrivateEvidence, "publish", substitute)
    retained_pair_recovery(run, evidence, retained, physical, original)
    seal = json.loads(retained.read_reference(retained.reference("recovery-seal.json")))
    # Every outer size/digest/manifest was authored over this internally consistent
    # later incarnation; only the independent canonical stop must reject it.
    with pytest.raises(backup.Refusal):
        backup.verify_retained_backup(run, seal, original)
