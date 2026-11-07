"""Synthetic bind visibility, archive integrity, and bounded retirement contracts."""

from __future__ import annotations

import hashlib
import io
import struct
import tarfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from tools.devtools import wayne_qualification_backup as backup
from tools.devtools import wayne_qualification_storage as storage

SYSTEM = 504402
WAL = "pg_wal/000000010000000000000001"
SEGMENT = 1024 * 1024
RELATION = "base/551/2930"
LINEAGE = b"reviewed lineage\n"


def fixture() -> tuple[dict[str, bytes | None], backup.PhysicalWitness]:
    control = bytearray(8192)
    struct.pack_into("<Q", control, 0, SYSTEM)
    struct.pack_into("<I", control, 16, 1)
    struct.pack_into("<Q", control, 32, SEGMENT + 80)
    struct.pack_into("<I", control, 48, 1)
    wal = bytearray(SEGMENT)
    struct.pack_into("<HHIQ", wal, 0, 0xD116, 2, 1, SEGMENT)
    struct.pack_into("<QII", wal, 24, SYSTEM, SEGMENT, 8192)
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
        RELATION: b"shutdown pages",
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
        "uid_map": "0 100000 65536",
        "gid_map": "0 200000 65536",
        "container_root": {"mode": 0o700, "uid": 71, "gid": 73},
        "host": {"mode": 0o700, "uid": 100071, "gid": 200073},
        "cluster": str(SYSTEM),
    }
    witness = backup.PhysicalWitness(
        physical, before, {"babylon_state.tick_commit": RELATION}, 551, SEGMENT, 0xD116
    )
    return payloads, witness


def archive(
    path: Path,
    payloads: dict[str, bytes | None],
    *,
    uid: int = 71,
    gid: int = 73,
    extra: tarfile.TarInfo | None = None,
) -> None:
    with tarfile.open(path, "x:") as output:
        for name, content in payloads.items():
            member = tarfile.TarInfo("./" + name)
            member.uid, member.gid = uid, gid
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
    path = tmp_path / "copy.tar"
    archive(path, files, uid=uid, gid=gid)
    with path.open("rb") as stream:
        members, translation = backup.archive_manifest(stream, witness)
    assert translation == namespace
    assert members[RELATION].sha256 == hashlib.sha256(b"shutdown pages").hexdigest()
    assert members[RELATION].size == 14


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
        backup.archive_manifest(stream, witness)


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


@pytest.mark.parametrize(
    "fault", ["none", "unrelated_copy", "second_changed", "bulk_copy_failed", "missing_seal"]
)
def test_retirement_needs_both_stopped_reads_and_reread_source_seals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    from contextlib import nullcontext

    evidence = tmp_path / "evidence"
    evidence.mkdir(mode=0o700)
    (tmp_path / "backup").mkdir(mode=0o700)
    directory = backup.Evidence(evidence)
    saved = {"campaign": "campaign", "period": 2}
    directory.publish_json("functional-terminal.json", saved)
    directory.publish("ownership", b"owner\n")
    payloads, witness = fixture()
    events = []

    def authenticate(selected: backup.Run) -> dict[str, Any]:
        events.append("auth")
        return {}

    monkeypatch.setattr(backup.Run, "authenticate", authenticate)
    monkeypatch.setattr(backup, "_physical_witness", lambda *_args: witness)
    monkeypatch.setattr(backup, "_conn", lambda *_args: nullcontext(None))
    monkeypatch.setattr(backup, "_inventory", lambda *_args: events.append("empty cluster"))
    monkeypatch.setattr(
        backup, "_logical", lambda _run, target, _state: [target.publish("database.dump", b"dump")]
    )

    def stop(target: backup.Evidence, cid: str) -> None:
        events.append("stop")
        target.publish("clean-shutdown.log", b"database system is shut down")

    monkeypatch.setattr(storage, "stop_checked", stop)
    monkeypatch.setattr(backup, "_stopped", lambda *_args: events.append("stopped auth"))
    monkeypatch.setattr(storage, "remove_stopped", lambda *_args: events.append("remove"))
    cid = "a" * 64
    owner = tuple("x" if i != 4 else cid for i in range(21))

    def copy(target: backup.Evidence, name: str, args: list[str]) -> backup.Reference:
        assert args == ["docker", "cp", "-a", cid + ":/var/lib/postgresql/data/.", "-"]
        assert "stop" in events
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
        with pytest.raises(backup.Refusal):
            backup.backup_and_retire(tmp_path, evidence, owner, "campaign", 2)
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
    "fault", ["none", "restore_failure", "wrong_restored", "wrong_probe", "foreign_session"]
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
    monkeypatch.setattr(backup.Run, "authenticate", lambda _self: {})
    roster = {run.database: 30}
    state = {"campaign": "campaign", "database": {"owner": "confined"}, "markers": ["real P2"]}
    commands = []
    probes: list[str] = []
    seen = []

    def inventory(
        conn: MagicMock,
        selected: backup.Run,
        verified_oid: int | None = None,
        admitted: object = None,
    ) -> dict[str, int]:
        if fault == "foreign_session" and probes == [run.database, run.verification]:
            raise backup.Refusal("unexpected client in task cluster")
        return roster

    def snapshot(conn: MagicMock, campaign: str, period: int) -> dict[str, Any]:
        seen.append(campaign)
        return state if fault != "wrong_restored" or len(seen) == 1 else {**state, "markers": []}

    def probe(
        conn: MagicMock, selected: backup.Run, database: str, oid: int, verified_oid: int | None
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
    if fault == "none":
        backup._logical(run, target, state)
    else:
        with pytest.raises(backup.Refusal):
            backup._logical(run, target, state)
    calls = [call.args[0].as_string() for call in db.execute.call_args_list]
    drops = [statement for statement in calls if statement.startswith("DROP DATABASE")]
    assert drops == ([f'DROP DATABASE "{run.verification}"'] if fault == "none" else [])
    assert [
        "docker",
        "exec",
        "-i",
        "-e",
        "PGAPPNAME=wayne_backup_restore",
        run.container,
        "pg_restore",
        "--exit-on-error",
        "-U",
        "test",
        "--dbname=" + run.verification,
    ] in commands
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
        kind = application.removeprefix("wayne_probe_")
        selected.append(role)

        def execute(query: str, args: tuple[object, ...] = ()) -> MagicMock:
            cursor = MagicMock()
            if "pg_has_role" in query:
                cursor.fetchall.return_value = [
                    (role, role, database, "on" if fault == "read_only" else "off", owner[2], True)
                ]
            elif "v_archive_revision_known_v2" in query:
                cursor.fetchall.return_value = (
                    [] if fault == "missing_dossier" else [("county", "26163", 2, "hash", "body")]
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
    mapping = "0 0 4294967295" if identical else "0 0 100\n100 20000 65536"
    witness.physical.update(uid_map=mapping, gid_map=mapping)
    witness.physical["host"].update(uid=71, gid=73)
    path = tmp_path / "copy.tar"
    archive(path, files)
    with path.open("rb") as stream:
        if identical:
            assert (
                backup.archive_manifest(stream, witness)[1] == "identity-mapped-host-and-container"
            )
        else:
            with pytest.raises(backup.Refusal, match="ambiguous"):
                backup.archive_manifest(stream, witness)
