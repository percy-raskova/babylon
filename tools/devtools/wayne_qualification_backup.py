"""Restore and compare the terminal Wayne campaign before preserving its bound PGDATA."""

from __future__ import annotations

import hashlib
import os
import re
import struct
import subprocess
import tarfile
import time
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, BinaryIO
from uuid import UUID

import psycopg
from psycopg import sql
from psycopg.abc import QueryNoTemplate
from tools.devtools import wayne_qualification_storage as storage
from tools.devtools.national_storage_qualification import strict_json_bytes

Refusal = storage.StorageRefusal
Connection = psycopg.Connection[Any]
Evidence = storage.PrivateEvidence
Reference = storage.Reference
WAL_NAME = re.compile(r"pg_wal/([A-F0-9]{8})([A-F0-9]{8})([A-F0-9]{8})\Z")
STABLE_BYTES = {
    "PG_VERSION",
    ".babylon-postgres-lineage-v1",
    "postgresql.conf",
    "postgresql.auto.conf",
    "pg_hba.conf",
    "pg_ident.conf",
}
REQUIRED_ROWS = {
    "babylon_state.campaign",
    "babylon_state.campaign_foundation",
    "babylon_state.material_campaign_foundation_v3",
    "babylon_state.tick_commit",
    "babylon_state.material_tick_v3",
    "babylon_state.checkpoint_manifest",
    "babylon_state.checkpoint_section_v1",
    "babylon_state.organizer_command_v1",
    "babylon_state.organizer_receipt_v1",
    "babylon_state.organizer_observation_v1",
    "babylon_meta.archive_tick_knowledge_v3",
    "babylon_meta.archive_page_revision_v2",
    "babylon_meta.archive_knowledge_grant_v1",
    "babylon_state.archive_dirty_receipt_v1",
}


def _one(
    conn: Connection, query: QueryNoTemplate, args: tuple[object, ...] = ()
) -> tuple[Any, ...]:
    rows = conn.execute(query, args).fetchall()
    if len(rows) != 1:
        raise Refusal("expected one authoritative SQL row")
    return tuple(rows[0])


def _catalog(conn: Connection) -> dict[str, Any]:
    owner, encoding, collate, ctype, provider, locale, rules, connlimit, default_acl, allows = _one(
        conn,
        """
        SELECT pg_get_userbyid(datdba),pg_encoding_to_char(encoding),datcollate,datctype,
               datlocprovider::text,datlocale,daticurules,datconnlimit,datacl IS NULL,datallowconn
        FROM pg_catalog.pg_database WHERE datname=current_database()
    """,
    )
    acl = conn.execute("""
        SELECT pg_get_userbyid(a.grantor),CASE WHEN a.grantee=0 THEN NULL ELSE pg_get_userbyid(a.grantee) END,
               a.privilege_type,a.is_grantable
        FROM pg_catalog.pg_database d CROSS JOIN LATERAL aclexplode(COALESCE(d.datacl,acldefault('d',d.datdba))) a
        WHERE datname=current_database() ORDER BY 1,2 NULLS FIRST,3,4
    """).fetchall()
    settings = conn.execute("""
        SELECT CASE WHEN s.setrole=0 THEN NULL ELSE pg_get_userbyid(s.setrole) END,setting
        FROM pg_catalog.pg_db_role_setting s CROSS JOIN LATERAL unnest(s.setconfig) setting
        WHERE s.setdatabase=(SELECT oid FROM pg_database WHERE datname=current_database())
        ORDER BY 1 NULLS FIRST,2
    """).fetchall()
    return {
        "owner": owner,
        "encoding": encoding,
        "collate": collate,
        "ctype": ctype,
        "provider": provider,
        "locale": locale,
        "icu_rules": rules,
        "connection_limit": connlimit,
        "acl_default": default_acl,
        "allows_connections": allows,
        "acl": [list(row) for row in acl],
        "settings": [list(row) for row in settings],
    }


def _object_authority(conn: Connection) -> list[list[Any]]:
    # regprocedure textual forms can depend on search_path. Qualify all argument types consistently.
    return [
        list(row)
        for row in conn.execute("""
        WITH namespaces AS (
            SELECT oid,nspname,nspowner,nspacl FROM pg_catalog.pg_namespace
            WHERE nspname !~ '^pg_' AND nspname<>'information_schema'
        ), objects AS (
            SELECT 'schema' kind,nspname::text ns,''::text ident,nspowner owner,
                   COALESCE(nspacl,acldefault('n',nspowner)) acl FROM namespaces
            UNION ALL SELECT c.relkind::text,n.nspname::text,c.relname::text,c.relowner,
                   COALESCE(c.relacl,acldefault(CASE WHEN c.relkind='S' THEN 's' ELSE 'r' END::"char",c.relowner))
            FROM pg_catalog.pg_class c JOIN namespaces n ON n.oid=c.relnamespace
            WHERE c.relkind IN ('r','p','v','m','f','S')
            UNION ALL SELECT 'routine',n.nspname,p.proname||'('||oidvectortypes(p.proargtypes)||')',p.proowner,
                   COALESCE(p.proacl,acldefault('f',p.proowner))
            FROM pg_catalog.pg_proc p JOIN namespaces n ON n.oid=p.pronamespace
            UNION ALL SELECT 'column',n.nspname,c.relname||'.'||a.attname,c.relowner,a.attacl
            FROM pg_catalog.pg_attribute a JOIN pg_catalog.pg_class c ON c.oid=a.attrelid
            JOIN namespaces n ON n.oid=c.relnamespace
            WHERE a.attnum>0 AND NOT a.attisdropped AND a.attacl IS NOT NULL
            UNION ALL SELECT 'default-'||d.defaclobjtype::text,COALESCE(n.nspname::text,''),
                             pg_get_userbyid(d.defaclrole),d.defaclrole,d.defaclacl
            FROM pg_catalog.pg_default_acl d LEFT JOIN namespaces n ON d.defaclnamespace=n.oid
            WHERE d.defaclnamespace=0 OR n.oid IS NOT NULL
        )
        SELECT kind,ns,ident,pg_get_userbyid(owner),pg_get_userbyid(a.grantor),
               CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(a.grantee) END,
               a.privilege_type,a.is_grantable
        FROM objects LEFT JOIN LATERAL aclexplode(acl) a ON true
        ORDER BY 1,ns COLLATE "C",ident COLLATE "C",4,5,6,7,8
    """).fetchall()
    ]


def _campaign_rows(conn: Connection, campaign: str) -> dict[str, list[str]]:
    columns = conn.execute("""
        SELECT n.nspname,c.relname,a.attname,a.atttypid='pg_catalog.bytea'::regtype
        FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
        JOIN pg_catalog.pg_attribute a ON a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped
        WHERE c.relkind IN ('r','p') AND NOT c.relispartition
          AND n.nspname IN ('babylon_meta','babylon_state','babylon_ref')
          AND EXISTS(SELECT FROM pg_attribute id WHERE id.attrelid=c.oid
                     AND id.attname='campaign_id' AND NOT id.attisdropped)
        ORDER BY n.nspname COLLATE "C",c.relname COLLATE "C",a.attnum
    """).fetchall()
    by_table: dict[tuple[str, str], list[sql.Composable]] = {}
    for namespace, table, name, binary in columns:
        column = sql.Identifier(name)
        # Hash bytea before converting the row to JSON. National register packages
        # can exceed PostgreSQL's varlena limit when converted to textual hex.
        value = sql.SQL("encode(sha256({}),'hex')").format(column) if binary else column
        by_table.setdefault((namespace, table), []).append(
            sql.SQL("{},{}").format(sql.Literal(name), value)
        )
    result = {}
    for (namespace, table), values in by_table.items():
        query = sql.SQL("""
            SELECT encode(sha256(convert_to(jsonb_build_object({})::text,'UTF8')),'hex') COLLATE "C" AS digest
            FROM {} WHERE campaign_id=%s::uuid ORDER BY 1
        """).format(sql.SQL(",").join(values), sql.Identifier(namespace, table))
        result[f"{namespace}.{table}"] = [
            row[0] for row in conn.execute(query, (campaign,)).fetchall()
        ]
    if not REQUIRED_ROWS <= {name for name, rows in result.items() if rows}:
        raise Refusal(
            "terminal campaign is missing required checkpoint, organizer or Archive witnesses"
        )
    return result


def _markers(rows: list[tuple[Any, ...]], period: int, foundation: str) -> list[dict[str, Any]]:
    # IdentifiedMaterialTick::decode in babylon-tick/material_replay.rs.
    domain = b"babylon.material-tick-content.v3\0"
    if [row[0] for row in rows] != list(range(1, period + 1)):
        raise Refusal("durable markers and checkpoints are not contiguous through terminal")
    entries = []
    previous = None
    for tick, digest, envelope, encoded, checkpoint in rows:
        if not all(
            isinstance(v, str) and re.fullmatch(r"[a-f0-9]{64}", v)
            for v in (digest, envelope, checkpoint)
        ):
            raise Refusal("commit marker, envelope or checkpoint digest is incomplete")
        raw = bytes.fromhex(encoded or "")
        header = domain + struct.pack(">IQ", 3, tick)
        if (
            not raw.startswith(header)
            or len(raw) != len(header) + 224
            or hashlib.sha256(raw).hexdigest() != digest
        ):
            raise Refusal("commit marker does not match its canonical material identity")
        digests = [raw[i : i + 32].hex() for i in range(len(header), len(raw), 32)]
        if digests[0] != foundation or (previous is not None and digests[4] != previous):
            raise Refusal(
                "material foundation or prior nominal world differs from the committed chain"
            )
        entries.append(
            {
                "tick": tick,
                "hash": digest,
                "envelope": envelope,
                "identity": encoded,
                "checkpoint": checkpoint,
                "world_before": digests[4],
                "world_after": digests[5],
                "receipt": digests[6],
            }
        )
        previous = digests[5]
    return entries


def _archive_terminal(
    conn: Connection, campaign: str, markers: list[dict[str, Any]]
) -> dict[str, Any]:
    # archive_worker.rs ARCHIVE_SWEEP_WATERMARK_SQL, including marker-backed
    # outer consumption semantics. All reads share terminal_snapshot's transaction.
    first, highest, pending = _one(
        conn,
        """
        SELECT min(d.resolve_tick) FILTER(WHERE c.campaign_id IS NULL),coalesce(max(d.resolve_tick),0),
               count(*) FILTER(WHERE c.campaign_id IS NULL)
        FROM babylon_state.archive_dirty_receipt_v1 d
        JOIN babylon_state.tick_commit m USING(campaign_id,resolve_tick)
        LEFT JOIN babylon_meta.archive_receipt_consumption_v1 c USING(campaign_id,resolve_tick)
        WHERE d.campaign_id=%s::uuid
    """,
        (campaign,),
    )
    watermark = highest if first is None else first - 1
    if pending or first is not None or watermark != markers[-1]["tick"]:
        raise Refusal("Archive is not drained through the terminal marker")
    rows = conn.execute(
        """
        SELECT resolve_tick,encode(d.tick_content_hash,'hex'),encode(c.tick_content_hash,'hex'),
               encode(k.tick_content_hash,'hex'),encode(c.batch_sha256,'hex'),
               encode(c.worker_contract_sha256,'hex'),encode(k.worker_contract_sha256,'hex'),
               encode(c.knowledge_sha256,'hex'),encode(k.knowledge_sha256,'hex')
        FROM babylon_state.archive_dirty_receipt_v1 d
        FULL JOIN babylon_meta.archive_receipt_consumption_v1 c USING(campaign_id,resolve_tick)
        FULL JOIN babylon_meta.archive_tick_knowledge_v3 k USING(campaign_id,resolve_tick)
        WHERE campaign_id=%s::uuid ORDER BY resolve_tick
    """,
        (campaign,),
    ).fetchall()
    if len(rows) != len(markers):
        raise Refusal("Archive proof is missing a committed period")
    receipts = []
    for marker, row in zip(markers, rows, strict=True):
        tick, dirty, consumed, knowledge_marker, batch, worker, known_worker, knowledge, known = row
        if (
            tick != marker["tick"]
            or not dirty == consumed == knowledge_marker == marker["hash"]
            or worker != known_worker
            or knowledge != known
            or not all(re.fullmatch("[a-f0-9]{64}", v or "") for v in (batch, worker, knowledge))
        ):
            raise Refusal(
                "Archive dirty, consumption or knowledge identity differs from its committed marker"
            )
        receipts.append(
            {
                "tick": tick,
                "marker": dirty,
                "batch": batch,
                "worker": worker,
                "knowledge": knowledge,
            }
        )
    return {
        "terminal_marker": markers[-1]["hash"],
        "watermark": watermark,
        "pending": pending,
        "receipts": receipts,
    }


def terminal_snapshot(connection: Connection, campaign: str, period: int) -> dict[str, Any]:
    if str(UUID(campaign)) != campaign or type(period) is not int or period <= 0:
        raise Refusal("terminal campaign or period is malformed")
    if connection.info.transaction_status != psycopg.pq.TransactionStatus.IDLE:
        raise Refusal(
            "terminal snapshot requires an idle connection for an independent repeatable read"
        )
    with connection.transaction():
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        connection.execute("SET LOCAL search_path=pg_catalog")
        connection.execute("SET LOCAL timezone='UTC'")
        identity = connection.execute("""
            SELECT campaign_id::text,preset_id,encode(content_sha256,'hex'),encode(foundation_sha256,'hex'),
                   encode(graph_foundation_sha256,'hex'),encode(defines_hash,'hex'),encode(rules_hash,'hex'),
                   encode(ref_digest,'hex'),encode(sha256(content_bundle_bytes),'hex')
            FROM public.v_observer_material_foundation_v1
        """).fetchall()
        if (
            len(identity) != 1
            or identity[0][:2] != (campaign, "national-world")
            or any(not re.fullmatch(r"[a-f0-9]{64}", value or "") for value in identity[0][2:])
        ):
            raise Refusal(
                "source, parameter bundle or foundations differ from one national campaign"
            )
        markers = connection.execute(
            """
            SELECT t.resolve_tick,encode(t.tick_content_hash,'hex'),encode(t.envelope_digest,'hex'),
                   encode(m.identity_bytes,'hex'),encode(c.manifest_sha256,'hex')
            FROM babylon_state.tick_commit t FULL JOIN babylon_state.material_tick_v3 m USING(campaign_id,resolve_tick)
            FULL JOIN babylon_state.checkpoint_manifest c USING(campaign_id,resolve_tick)
            WHERE campaign_id=%s::uuid ORDER BY resolve_tick
        """,
            (campaign,),
        ).fetchall()
        chain = _markers(markers, period, identity[0][3])
        return {
            "campaign": campaign,
            "period": period,
            "identity": list(identity[0]),
            "markers": chain,
            "archive_terminal": _archive_terminal(connection, campaign, chain),
            "campaign_rows_sha256": _campaign_rows(connection, campaign),
            "database": _catalog(connection),
            "object_authority": _object_authority(connection),
        }


@dataclass(frozen=True)
class Member:
    kind: str
    mode: int
    uid: int
    gid: int
    size: int | None
    sha256: str | None


@dataclass(frozen=True)
class PhysicalWitness:
    physical: dict[str, Any]
    members: dict[str, Member]
    relations: dict[str, str]
    database_oid: int
    segment_bytes: int
    wal_magic: int


def _member_name(raw: str) -> str:
    if raw in ("", "/"):
        raise Refusal("archive member has an empty or absolute path")
    value = raw.removeprefix("./")
    if not value or value == ".":
        return "."
    if any(part in ("", ".", "..") for part in value.split("/")) or "\x00" in value:
        raise Refusal("archive member has an escaping or ambiguous path")
    return value


# PostgreSQL REL_17_11 pg_control.h and xlogrecord.h, little-endian linux/amd64.
# C layout witness: sizeof(CheckPoint)=88, offsetof(ControlFileData,crc)=288.
PGSS_RUNNING = "pg_stat_tmp/pgss_query_texts.stat"
PGSS_STOPPED = "pg_stat/pg_stat_statements.stat"
PAGE = 8192
RELSEG_BYTES = PAGE * 131072


def _crc32c(data: bytes) -> int:
    value = 0xFFFFFFFF
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ (0x82F63B78 if value & 1 else 0)
    return value ^ 0xFFFFFFFF


def _checkpoint(
    stream: BinaryIO, control: bytes, wal: dict[str, int], witness: PhysicalWitness
) -> None:
    cluster = int(witness.physical["cluster"])
    if (
        len(control) != PAGE
        or struct.unpack_from("<QIII", control) != (cluster, 1700, 202406281, 1)
        or struct.unpack_from("<I", control, 288)[0] != _crc32c(control[:288])
        or struct.unpack_from("<IIII", control, 216) != (PAGE, 131072, PAGE, witness.segment_bytes)
    ):
        raise Refusal("clean control format, catalog, cluster, block geometry or CRC differs")
    lsn, redo, timeline = struct.unpack_from("<QQI", control, 32)
    if not timeline or not lsn or lsn != redo or lsn % 8:
        raise Refusal("shutdown checkpoint lacks an aligned redo location and timeline")
    cursor = lsn
    record = bytearray()
    while len(record) < 114:
        log, position = divmod(cursor, 2**32)
        segment, within_segment = divmod(position, witness.segment_bytes)
        page_offset, in_page = divmod(within_segment, PAGE)
        name = f"pg_wal/{timeline:08X}{log:08X}{segment:08X}"
        if name not in wal:
            raise Refusal("checkpoint segment is absent or lacks its source-bound long header")
        page_start = wal[name] + page_offset * PAGE
        stream.seek(page_start)
        page = stream.read(40)
        magic, flags, tli, address, remaining = struct.unpack_from("<HHIQI", page)
        header_size = 40 if page_offset == 0 else 24
        if (
            magic != 0xD116
            or tli != timeline
            or address != cursor - in_page
            or flags & ~7
            or bool(flags & 2) != (page_offset == 0)
        ):
            raise Refusal("shutdown checkpoint WAL page identity differs")
        if record:
            if in_page or not flags & 1 or remaining != 114 - len(record):
                raise Refusal("shutdown checkpoint continuation length or location differs")
            in_page = header_size
            cursor += header_size
        elif in_page < header_size or (flags & 1 and in_page < header_size + remaining):
            raise Refusal("shutdown checkpoint starts inside a WAL header or preceding record")
        take = min(114 - len(record), PAGE - in_page)
        stream.seek(page_start + in_page)
        data = stream.read(take)
        if len(data) != take:
            raise Refusal("checkpoint WAL record is truncated")
        record.extend(data)
        cursor += take
    length, xid, previous, flags, rmid = struct.unpack_from("<IIQBB", record)
    if (
        length != 114
        or xid
        or not 0 < previous < lsn
        or flags
        or rmid
        or record[18:20] != bytes(2)
        or record[24:26] != b"\xff\x58"
        or record[26:] != control[40:128]
        or struct.unpack_from("<I", record, 20)[0] != _crc32c(bytes(record[24:] + record[:20]))
    ):
        raise Refusal("WAL record is not the matching CRC-verified shutdown checkpoint")


def _extent_files(sizes: dict[str, int]) -> dict[str, int]:
    extents = {}
    for path, size in sizes.items():
        if size < 0 or size % PAGE:
            raise Refusal("relation extent is not block aligned")
        for pos in range(0, max(size, 1), RELSEG_BYTES):
            name = path if pos == 0 else f"{path}.{pos // RELSEG_BYTES}"
            extents[name] = min(size - pos, RELSEG_BYTES)
    return extents


def _initialized(header: bytes | memoryview) -> bool:
    if len(header) != 24:
        raise Refusal("relation block header is truncated")
    if header == bytes(24):
        return False
    flags, lower, upper, special, version = struct.unpack_from("<5H", header, 10)
    if (
        flags & ~7
        or not 24 <= lower <= upper <= special <= PAGE
        or special % 8
        or version != PAGE + 4
    ):
        raise Refusal("terminal relation block has an invalid PG17 page header")
    return True


def _source_pages(conn: Connection, sizes: dict[str, int]) -> dict[str, dict[str, bool]]:
    samples = [
        (name, offset)
        for name, length in _extent_files(sizes).items()
        if length
        for offset in sorted({0, length - PAGE})
    ]
    result: dict[str, dict[str, bool]] = {}
    rows = conn.execute(
        """
        SELECT path,off,pg_read_binary_file(path,off,24)
        FROM unnest(%s::text[],%s::bigint[]) AS e(path,off) ORDER BY path,off
    """,
        ([name for name, _ in samples], [off for _, off in samples]),
    ).fetchall()
    if {(r[0], r[1]) for r in rows} != set(samples) or len(rows) != len(samples):
        raise Refusal("source boundary block inventory differs from the SQL main-fork sizes")
    for path, offset, header in rows:
        result.setdefault(path, {})[str(offset)] = _initialized(bytes(header))
    return result


def _verify_blocks(chunk: bytes, start: int, samples: dict[str, bool]) -> None:
    if len(chunk) % PAGE:
        raise Refusal("incomplete terminal relation block")
    view = memoryview(chunk)
    for i in range(0, len(chunk), PAGE):
        initialized = _initialized(view[i : i + 24])
        # Mutable pages may be rewritten. An independently observed populated
        # boundary cannot turn into an unproved hole at clean shutdown.
        if not initialized and (samples.get(str(start + i)) or view[i : i + PAGE] != bytes(PAGE)):
            raise Refusal("terminal block is missing or its zero header masks nonzero contents")


def _extents(witness: PhysicalWitness, members: dict[str, Member]) -> None:
    sizes = witness.physical["relation_sizes"]
    if set(sizes) != set(witness.relations.values()):
        raise Refusal("missing independent table or index extent")
    for path, length in sizes.items():
        if length < 0 or length % PAGE:
            raise Refusal("SQL main-fork size is not block aligned")
        # PostgreSQL may leave an empty trailing segment at an exact segment boundary.
        full, remainder = divmod(length, RELSEG_BYTES)
        for index in range(full + 1):
            name = path if not index else f"{path}.{index}"
            size = RELSEG_BYTES if index < full else remainder
            if not size and index and name not in witness.members and name not in members:
                continue
            before, after = witness.members.get(name), members.get(name)
            if (
                before is None
                or after is None
                or before.kind != "file"
                or after.kind != "file"
                or before.size != size
                or after.size != size
            ):
                raise Refusal(
                    "terminal relation no longer covers its independently measured blocks"
                )
    # Any additional segment of a selected main fork needs independent proof.
    for name in set(witness.members) | set(members):
        base, dot, suffix = name.rpartition(".")
        if (
            dot
            and base in sizes
            and suffix.isdecimal()
            and (
                not suffix.isascii()
                or suffix != str(int(suffix))
                or not 1 <= int(suffix) <= sizes[base] // RELSEG_BYTES
            )
        ):
            raise Refusal("terminal relation has an unaccounted segment")


def _pgss_source(witness: PhysicalWitness) -> None:
    config = witness.physical["pgss"]
    before = witness.members.get(PGSS_RUNNING)
    root = witness.physical["container_root"]
    if (
        config != {"preload": "pg_stat_statements", "save": "on", "version": "1.11"}
        or before is None
        or (before.kind, before.mode, before.uid, before.gid)
        != ("file", 0o600, root["uid"], root["gid"])
        or PGSS_STOPPED in witness.members
    ):
        raise Refusal(
            "pg_stat_statements persistence configuration or directional file transition differs"
        )


def _shutdown_change(path: str, *, added: bool) -> bool:
    if path in (PGSS_STOPPED, "pg_stat/pgstat.stat"):
        return added
    if path in (PGSS_RUNNING, "postmaster.pid"):
        return not added
    return (
        WAL_NAME.fullmatch(path) is not None
        or re.fullmatch(r"pg_wal/archive_status/[A-F0-9]{24}\.(ready|done)", path) is not None
    )


def _valid_wal(path: str, header: bytes, size: int, witness: PhysicalWitness) -> bool:
    match = WAL_NAME.fullmatch(path)
    if match is None or len(header) < 40 or size != witness.segment_bytes:
        return False
    timeline, log, segment = (int(part, 16) for part in match.groups())
    magic, flags, page_timeline, address = struct.unpack_from("<HHIQ", header)
    system, segment_bytes, block = struct.unpack_from("<QII", header, 24)
    return (
        magic == witness.wal_magic
        and flags & 2 != 0
        and timeline == page_timeline
        and segment < 2**32 // size
        and address == (log << 32) + segment * size
        and system == int(witness.physical["cluster"])
        and segment_bytes == size
        and block == 8192
    )


def archive_manifest(stream: BinaryIO, witness: PhysicalWitness) -> tuple[dict[str, Member], str]:
    result: dict[str, Member] = {}
    extent_files = _extent_files(witness.physical["relation_sizes"])
    samples = witness.physical["relation_page_samples"]
    for path, length in extent_files.items():
        if length and set(samples.get(path, {})) != {str(x) for x in (0, length - PAGE)}:
            raise Refusal("independent boundary block samples are absent")
    wal: dict[str, int] = {}
    control = b""
    with tarfile.open(fileobj=stream, mode="r:") as archive:
        for item in archive:
            path = _member_name(item.name)
            if (
                path in result
                or item.sparse is not None
                or item.type not in {tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE}
                or item.linkname
                or min(item.uid, item.gid, item.size) < 0
                or item.mode & ~0o7777
            ):
                raise Refusal("duplicate, link, sparse, special or malformed PGDATA member")
            digest = None
            if item.isdir():
                if item.size:
                    raise Refusal("directory archive entry carries file bytes")
            else:
                source = archive.extractfile(item)
                if source is None:
                    raise Refusal("ordinary archive member lacks its payload")
                with source:
                    header = source.read(
                        PAGE if path == "global/pg_control" or path in extent_files else 64
                    )
                    if path in extent_files:
                        _verify_blocks(header, 0, samples.get(path, {}))
                    hasher = hashlib.sha256(header)
                    size = len(header)
                    while data := source.read(1024 * 1024):
                        if path in extent_files:
                            _verify_blocks(data, size, samples.get(path, {}))
                        hasher.update(data)
                        size += len(data)
                    if size != item.size:
                        raise Refusal("archive file length differs from its actual payload")
                    digest = hasher.hexdigest()
                if path == "global/pg_control" and size == PAGE:
                    control = header
                if path == PGSS_STOPPED and (
                    size < 28 or struct.unpack_from("<II", header) != (0x20220408, 1700)
                ):
                    raise Refusal("pg_stat_statements shutdown file header differs")
                if _valid_wal(path, header, size, witness):
                    wal[path] = item.offset_data
            result[path] = Member(
                "dir" if item.isdir() else "file", item.mode, item.uid, item.gid, item.size, digest
            )
        stream.seek(archive.offset)
        tail = 0
        while pad := stream.read(1024 * 1024):
            if pad.strip(b"\0"):
                raise Refusal("archive contains data beyond its first end marker")
            tail += len(pad)
        if tail < 1024 or tail % 512:
            raise Refusal("PGDATA archive is truncated at its end markers")
    required = {
        "PG_VERSION",
        ".babylon-postgres-lineage-v1",
        "global/pg_control",
        "pg_wal",
        "pg_tblspc",
        *witness.relations.values(),
    }
    if not witness.relations or not required <= result.keys():
        raise Refusal(
            "archive lacks the admitted cluster, clean control, WAL or terminal relations"
        )
    _checkpoint(stream, control, wal, witness)
    _extents(witness, result)
    _pgss_source(witness)
    if PGSS_RUNNING in result or PGSS_STOPPED not in result:
        raise Refusal("pg_stat_statements shutdown transition is incomplete")
    if any(path.startswith("pg_tblspc/") for path in result):
        raise Refusal("physical archive contains an external tablespace")
    modes = {"host", "container"}
    root = witness.physical["container_root"]
    for path in set(witness.members) | set(result):
        actual = result.get(path)
        expected = witness.members.get(path)
        if path == ".":
            expected = Member("dir", root["mode"], root["uid"], root["gid"], None, None)
        if actual is None or expected is None:
            if not _shutdown_change(path, added=expected is None):
                raise Refusal("archive and independent stable member inventory differ: " + path)
            if actual is None:
                continue
            expected = Member("file", 0o600, root["uid"], root["gid"], None, None)
        if (
            actual.kind != expected.kind
            or actual.mode != expected.mode
            or expected.sha256 is not None
            and actual.size != expected.size
            or expected.sha256 is not None
            and actual.sha256 != expected.sha256
        ):
            raise Refusal("archive metadata or stable bytes differ from running source: " + path)
        inside = (expected.uid, expected.gid)
        host = (
            storage._mapped(expected.uid, witness.physical["uid_map"]),
            storage._mapped(expected.gid, witness.physical["gid_map"]),
        )
        if (actual.uid, actual.gid) != inside:
            modes.discard("container")
        if (actual.uid, actual.gid) != host:
            modes.discard("host")
    if not modes:
        raise Refusal("archive numeric UID/GID namespace cannot be reconciled with the bind")
    if len(modes) == 1:
        return result, next(iter(modes))
    for mapping in ("uid_map", "gid_map"):
        if any(row.split()[0] != row.split()[1] for row in witness.physical[mapping].splitlines()):
            raise Refusal("archive UID/GID namespace is ambiguous outside the observed identities")
    return result, "identity-mapped-host-and-container"


@dataclass(frozen=True)
class Run:
    root: Path
    evidence: Path
    owner: tuple[str, ...]
    campaign: str
    period: int

    @property
    def database(self) -> str:
        return self.owner[7]

    @property
    def verification(self) -> str:
        return "per364_verify_" + self.owner[2][:12]

    @property
    def container(self) -> str:
        return self.owner[4]

    @property
    def port(self) -> int:
        return int(self.owner[19])

    def authenticate(self) -> dict[str, Any]:
        if (
            len(self.owner) != 21
            or self.owner[0] != "national-storage-runner-media-v2"
            or self.owner[1] != str(self.root)
            or self.owner[10] != str(self.evidence)
            or self.evidence != storage.RUN_PARENT / self.owner[11] / "evidence"
            or self.owner[11] not in ("smoke-01", "walk-01")
            or self.period != int(storage.PROFILES[self.owner[11]][1])
            or not re.fullmatch(r"[a-f0-9]{32}", self.owner[2])
            or self.database != "national_" + self.owner[2][:12]
            or self.owner[8] != "national_writer_" + self.owner[2][:12]
        ):
            raise Refusal("backup requires the exact terminal media-native owner")
        storage.reauthenticate_native_owner(self.root, self.evidence, self.owner)
        physical = storage._current_physical(
            Evidence(self.evidence), self.root, self.container, self.owner[2], self.owner[6]
        )
        if type(physical.get("max_wal_senders")) is not int or physical["max_wal_senders"] != 0:
            raise Refusal("native physical receipt does not exclude uncounted replication sessions")
        return physical


@dataclass(frozen=True)
class Backend:
    pid: int
    started: str
    oid: int
    role: str
    address: str | None
    port: int


def _clients(conn: Connection) -> list[Backend]:
    return [
        Backend(*row)
        for row in conn.execute("""
        SELECT pid,(extract(epoch FROM backend_start)*1000000)::bigint::text,datid,usename,host(client_addr),client_port
        FROM pg_stat_activity WHERE pid<>pg_backend_pid() AND (backend_type='client backend'
             OR backend_type='walsender') ORDER BY pid
    """).fetchall()
    ]


def _own_backend(conn: Connection, oid: int, role: str) -> Backend:
    values = _one(
        conn,
        """
        SELECT pid,(extract(epoch FROM backend_start)*1000000)::bigint::text,datid,usename,host(client_addr),client_port
        FROM pg_stat_activity WHERE pid=pg_backend_pid() AND usename=session_user
    """,
    )
    own = Backend(*values)
    if (
        own.pid != conn.info.backend_pid
        or own.oid != oid
        or own.role != role
        or not own.address
        or own.port <= 0
    ):
        raise Refusal("SQL login does not match its own authenticated TCP backend")
    return own


class RestoreAdmission:
    """One admitted backend per closed verification-database window."""

    def __init__(self, admin: Connection, run: Run, oid: int, original_limit: int) -> None:
        self.admin = admin
        self.run = run
        self.oid = oid
        self.limit = original_limit
        self.restore_backend: Backend | None = None
        self.sessions: list[dict[str, Any]] = []
        self._guard(False, 0)
        self._barrier()
        count, self.reset, self.postmaster = self._stats()
        if count or original_limit == 0:
            raise Refusal(
                "new verification database has a prior session or source forbids connections"
            )

    def _guard(self, opened: bool, limit: int) -> None:
        actual = _one(
            self.admin,
            """
            SELECT oid,pg_get_userbyid(datdba),datallowconn,datconnlimit
            FROM pg_database WHERE datname=%s
        """,
            (self.run.verification,),
        )
        if actual != (self.oid, self.run.owner[8], opened, limit):
            raise Refusal("verification OID, owner or checked admission guard changed")

    def _latch(self, opened: bool, limit: int) -> None:
        if _one(
            self.admin,
            "SELECT oid,pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s",
            (self.run.verification,),
        ) != (self.oid, self.run.owner[8]):
            raise Refusal("verification database identity changed before admission transition")
        self.admin.execute(
            sql.SQL("ALTER DATABASE {} ALLOW_CONNECTIONS {} CONNECTION LIMIT {}").format(
                sql.Identifier(self.run.verification), sql.Literal(opened), sql.Literal(limit)
            )
        )
        self._guard(opened, limit)

    def _barrier(self) -> None:
        # REL_17_11 postinit.c holds this shared-object lock from before
        # CheckMyDatabase until after its backend status becomes visible.
        if _one(
            self.admin,
            """SELECT count(*) FROM pg_locks WHERE locktype='object'
            AND classid='pg_catalog.pg_database'::regclass AND objid=%s::oid
            AND mode='RowExclusiveLock'""",
            (self.oid,),
        ) != (0,):
            raise Refusal("a verification backend is still entering the database")

    def _stats(self) -> tuple[int, str | None, str]:
        n, reset, started, counts, activities, senders = _one(
            self.admin,
            """
            SELECT sessions,(extract(epoch FROM stats_reset)*1000000)::bigint::text,(extract(epoch FROM pg_postmaster_start_time())*1000000)::bigint::text,
                   current_setting('track_counts'),current_setting('track_activities'),current_setting('max_wal_senders')::int
            FROM pg_stat_database WHERE datid=%s
        """,
            (self.oid,),
        )
        if (
            type(n) is not int
            or n < 0
            or not started
            or (counts, activities, senders) != ("on", "on", 0)
        ):
            raise Refusal("server does not supply usable session statistics")
        return n, reset, started

    def reconcile(self, closing: Backend | None = None) -> None:
        self._guard(False, self.limit)
        self._barrier()
        # A socket close does not wait for server teardown. Wait only for the
        # exact backend whose own close we initiated, never an unknown client.
        deadline = time.monotonic() + 5
        while clients := _clients(self.admin):
            if closing is None or clients != [closing] or time.monotonic() >= deadline:
                raise Refusal(
                    "unexpected or non-exiting client behind the closed verification gate"
                )
            time.sleep(0.025)
        _inventory(self.admin, self.run, self.oid)
        # Flush occurs in before_shmem_exit; activity removal is on_shmem_exit.
        # Fresh autocommit statements read the count AFTER the zero-backend barrier.
        if self._stats() != (len(self.sessions), self.reset, self.postmaster):
            raise Refusal("verification session total, reset epoch or postmaster differs")

    def _record(self, purpose: str, backend: Backend, opened_limit: int) -> None:
        if any(row["backend"] == asdict(backend) for row in self.sessions):
            raise Refusal("verification backend incarnation reused for another admitted connection")
        self.sessions.append(
            {
                "purpose": purpose,
                "backend": asdict(backend),
                "open_limit": opened_limit,
                "closed_limit": self.limit,
                "expected_sessions": len(self.sessions) + 1,
            }
        )
        self.reconcile(backend)

    @contextmanager
    def window(self, limit: int) -> Iterator[None]:
        self._latch(True, limit)
        try:
            yield
        finally:
            self._latch(False, self.limit)

    def observe_restore(self) -> None:
        clients = _clients(self.admin)
        if not clients:
            return
        if len(clients) != 1:
            raise Refusal("additional client during single-connection pg_restore")
        client = clients[0]
        if (
            client.oid != self.oid
            or client.role != "test"
            or client.address is not None
            or client.port != -1
            or client.pid <= 0
            or not client.started
            or self.restore_backend not in (None, client)
        ):
            raise Refusal("single local restore backend incarnation or transport changed")
        self.restore_backend = client

    def finish_restore(self) -> None:
        if self.restore_backend is None:
            raise Refusal("single-connection pg_restore exited without an observed backend")
        self._record("pg_restore", self.restore_backend, 0)

    @contextmanager
    def session(self, role: str, purpose: str) -> Iterator[Connection]:
        # Allow only one ordinary slot for a real restricted login. Close new
        # admission before that login performs work. The final comparison runs
        # after both restricted logins closed and their exact totals reconciled.
        limit = 0 if role == "test" else 1
        with ExitStack() as sessions:
            with self.window(limit):
                conn = sessions.enter_context(_conn(self.run, self.run.verification, role))
                own = _own_backend(conn, self.oid, role)
            self._barrier()
            _inventory(self.admin, self.run, self.oid, own)
            yield conn
        self._record(purpose, own, limit)


def _inventory(
    conn: Connection,
    run: Run,
    verified_oid: int | None = None,
    admitted: Backend | None = None,
) -> dict[str, int]:
    rows = conn.execute("""
        SELECT d.datname::text,d.oid,r.rolname::text FROM pg_database d JOIN pg_roles r ON r.oid=d.datdba
    """).fetchall()
    expected = {"babylon_test", "postgres", "template0", "template1", run.database}
    if verified_oid is not None:
        expected.add(run.verification)
    identities = {name: (oid, owner) for name, oid, owner in rows}
    if (
        identities.keys() != expected
        or identities.get(run.database) != (int(run.owner[9]), run.owner[8])
        or verified_oid is not None
        and identities.get(run.verification) != (verified_oid, run.owner[8])
    ):
        raise Refusal("unexpected task-cluster database roster, owner or verification OID")
    endpoint = _one(
        conn,
        """
        SELECT current_setting('babylon.disposable_runtime',true),(pg_control_system()).system_identifier::text,
               session_user::text,current_user::text,current_database()
    """,
    )
    if endpoint != (run.owner[2], run.owner[20], "test", "test", "postgres"):
        raise Refusal("backup administrator identity or cluster differs from the captured owner")
    if _clients(conn) != ([] if admitted is None else [admitted]):
        raise Refusal("unexpected client on the task cluster during recovery")
    return {name: oid for name, (oid, _) in identities.items()}


def _conn(
    run: Run, database: str, role: str = "test", *, application: str = "wayne_backup_admin"
) -> Connection:
    return psycopg.connect(
        host="127.0.0.1",
        port=run.port,
        dbname=database,
        user=role,
        password="test" if role == "test" else run.owner[2],
        application_name=application,
        sslmode="disable",
        connect_timeout=5,
        autocommit=True,
    )


@contextmanager
def _output(directory: Evidence, name: str) -> Iterator[BinaryIO]:
    directory_fd = os.open(directory.path, storage.DIR_FLAGS)
    try:
        storage._private_dir(directory_fd)
        target = storage._new_stream(directory, name)
        primary: BaseException | None = None
        try:
            os.fsync(directory_fd)
            yield target
        except BaseException as exc:
            primary = exc
            raise
        finally:
            failures = []
            for operation in (
                target.flush,
                lambda: os.fsync(target.fileno()),
                target.close,
                lambda: os.fsync(directory_fd),
            ):
                try:
                    operation()
                except OSError as exc:
                    failures.append(exc)
            if failures:
                if primary is None:
                    raise failures[0]
                for failure in failures:
                    primary.add_note(f"retaining {name}: {failure}")
    finally:
        os.close(directory_fd)


def _command(
    directory: Evidence,
    name: str,
    args: list[str],
    *,
    source: Reference | None = None,
    monitor: RestoreAdmission | None = None,
) -> Reference:
    with ExitStack() as files:
        if source is not None:
            directory.verify(source)
        input_file = (
            files.enter_context(directory.file(source.path)) if source else subprocess.DEVNULL
        )
        output = files.enter_context(_output(directory, name))
        errors = files.enter_context(_output(directory, name + ".stderr"))
        with subprocess.Popen(args, stdin=input_file, stdout=output, stderr=errors) as child:
            while child.poll() is None:
                if monitor is not None:
                    monitor.observe_restore()
                try:
                    child.wait(timeout=0.5 if monitor else None)
                except subprocess.TimeoutExpired:
                    continue
            code = child.returncode
    if code != 0:
        raise Refusal("backup command failed; retained private stdout and stderr: " + name)
    result = directory.reference(name)
    directory.verify(result)
    return result


def _restrict_writer(conn: Connection, run: Run) -> None:
    rows = conn.execute(
        """
        SELECT rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls,
               EXISTS(SELECT FROM pg_auth_members WHERE member=r.oid)
        FROM pg_roles r WHERE rolname=%s
    """,
        (run.owner[8],),
    ).fetchall()
    if rows != [(True, False, False, False, False, False, False)]:
        raise Refusal("source database owner is not the confined national writer")


def _verify_create(admin: Connection, run: Run, catalog: dict[str, Any]) -> int:
    if (
        catalog["owner"] != run.owner[8]
        or catalog["provider"] != "b"
        or catalog["locale"] != "C.UTF-8"
        or catalog["encoding"] != "UTF8"
        or catalog["icu_rules"] is not None
    ):
        raise Refusal("national owner or selected PostgreSQL built-in locale differs")
    admin.execute(
        sql.SQL("""
        CREATE DATABASE {} WITH TEMPLATE template0 OWNER {} ENCODING {} LOCALE_PROVIDER builtin
        BUILTIN_LOCALE {} LC_COLLATE {} LC_CTYPE {} ALLOW_CONNECTIONS false CONNECTION LIMIT 0
    """).format(
            sql.Identifier(run.verification),
            sql.Identifier(catalog["owner"]),
            *(sql.Literal(catalog[k]) for k in ("encoding", "locale", "collate", "ctype")),
        )
    )
    oid, owner = _one(
        admin,
        """
        SELECT oid,pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s
    """,
        (run.verification,),
    )
    if owner != run.owner[8] or oid == int(run.owner[9]):
        raise Refusal("fresh verification database owner or identity differs")
    return int(oid)


def _db_privileges(conn: Connection, name: str, catalog: dict[str, Any]) -> None:
    current = _catalog(conn)
    database = sql.Identifier(name)
    if current["acl"] != catalog["acl"] or current["acl_default"] != catalog["acl_default"]:
        # A fresh template0 DB starts with just the owner's and PUBLIC's default
        # entries. Recreate all grants, including grantor chains, from that point.
        if any(entry[0] != catalog["owner"] for entry in current["acl"]):
            raise Refusal("fresh verification database has an unexpected delegated grantor")
        for role in {entry[1] for entry in current["acl"]}:
            target = sql.Identifier(role) if role else sql.SQL("PUBLIC")
            conn.execute(
                sql.SQL("REVOKE ALL PRIVILEGES ON DATABASE {} FROM {}").format(database, target)
            )
        ready = {(catalog["owner"], p) for p in ("CONNECT", "CREATE", "TEMPORARY")}
        pending = list(catalog["acl"])
        while pending:
            eligible = [entry for entry in pending if (entry[0], entry[2]) in ready]
            if not eligible:
                raise Refusal("database ACL grantor chain cannot be reproduced")
            for grantor, grantee, privilege, grantable in eligible:
                with conn.transaction():
                    conn.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(grantor)))
                    stmt = sql.SQL("GRANT {} ON DATABASE {} TO {} {}").format(
                        sql.SQL(privilege),
                        database,
                        sql.Identifier(grantee) if grantee else sql.SQL("PUBLIC"),
                        sql.SQL("WITH GRANT OPTION") if grantable else sql.SQL(""),
                    )
                    conn.execute(stmt)
                if grantable:
                    ready.add((grantee, privilege))
                pending.remove([grantor, grantee, privilege, grantable])
    if current["settings"]:
        raise Refusal("template0 verification DB unexpectedly inherited per-database settings")
    for role, setting in catalog["settings"]:
        key, separator, value = setting.partition("=")
        if not separator or not re.fullmatch(
            r"[a-z_A-Z][a-zA-Z_0-9]*(?:\.[a-zA-Z_][a-zA-Z_0-9]*)*", key
        ):
            raise Refusal("database setting name cannot be reproduced")
        prefix = (
            sql.SQL("ALTER ROLE {} IN DATABASE {}").format(sql.Identifier(role), database)
            if role
            else sql.SQL("ALTER DATABASE {}").format(database)
        )
        with conn.transaction():
            conn.execute("SELECT pg_catalog.set_config(%s,%s,true)", (key, value))
            conn.execute(
                sql.SQL("{} SET {} FROM CURRENT").format(prefix, sql.Identifier(*key.split(".")))
            )
    if _catalog(conn) != catalog:
        raise Refusal("restored database owner, locale, settings or privileges differ")


def _probes(
    admin: Connection,
    run: Run,
    database: str,
    oid: int,
    verification_oid: int | None,
    gate: RestoreAdmission | None = None,
) -> dict[str, Any]:
    results = {}
    for kind in ("reader", "observer"):
        role = "national_" + kind + "_" + run.owner[2][:12]
        application = "wayne_probe_" + kind
        session = (
            gate.session(role, kind)
            if gate
            else _conn(run, database, role, application=application)
        )
        with session as conn:
            if not gate:
                _inventory(admin, run, verification_oid, _own_backend(conn, oid, role))
            identity = _one(
                conn,
                """
                SELECT session_user::text,current_user::text,current_database(),current_setting('transaction_read_only'),
                       current_setting('babylon.disposable_runtime',true),pg_has_role(current_user,%s,'MEMBER')
            """,
                ("babylon_" + kind,),
            )
            if identity != (role, role, database, "off", run.owner[2], True):
                raise Refusal(
                    "restricted probe did not authenticate its real writable-session login"
                )
            if kind == "reader":
                allowed = _one(
                    conn,
                    """
                    SELECT subject_kind,subject_id,effective_tick,encode(revision_sha256,'hex'),
                           encode(sha256(body_bytes),'hex') FROM public.v_archive_revision_known_v2
                    WHERE campaign_id=%s::uuid AND effective_tick<=%s AND subject_kind='county' AND subject_id='26163'
                    ORDER BY effective_tick DESC LIMIT 1
                """,
                    (run.campaign, run.period),
                )
            else:
                allowed = _one(
                    conn,
                    """
                    SELECT resolve_tick,encode(identity_bytes,'hex'),encode(tick_content_hash,'hex')
                    FROM public.v_observer_material_state_v1 WHERE campaign_id=%s::uuid AND resolve_tick=%s
                """,
                    (run.campaign, run.period),
                )
            if not all(allowed):
                raise Refusal("restricted production read returned no terminal data")
            denied = []
            for forbidden in (
                "SELECT identity_bytes FROM babylon_state.material_tick_v3 LIMIT 1",
                "SELECT pg_catalog.pg_read_binary_file('PG_VERSION',0,1)",
            ):
                try:
                    conn.execute(forbidden).fetchall()
                except psycopg.errors.InsufficientPrivilege as exc:
                    if exc.sqlstate != "42501":
                        raise
                    denied.append(exc.sqlstate)
                else:
                    raise Refusal("raw or administrative operation unexpectedly succeeded")
            results[kind] = {"role": role, "allowed": list(allowed), "denied_sqlstates": denied}
    return results


def _logical(run: Run, backup: Evidence, functional: dict[str, Any]) -> list[Reference]:
    docker = ["docker", "exec", run.container]
    with _conn(run, "postgres") as admin:
        initial = _inventory(admin, run)
        _restrict_writer(admin, run)
        with _conn(run, run.database) as conn:
            original = terminal_snapshot(conn, run.campaign, run.period)
        refs = [backup.publish_json("original-terminal.json", original)]
        if original != functional:
            raise Refusal("original campaign differs from the installed functional snapshot")
        probes = _probes(admin, run, run.database, initial[run.database], None)
        refs.append(backup.publish_json("original-probes.json", probes))
        _inventory(admin, run)
    # pg_dump/pg_dumpall connect to the exact owned container via its local
    # socket. The cluster globals are retained privately and never executed.
    dump = _command(
        backup,
        "database.dump",
        [*docker, "pg_dump", "-U", "test", "--format=custom", "--dbname=" + run.database],
    )
    globals_dump = _command(
        backup, "cluster-globals.sql", [*docker, "pg_dumpall", "-U", "test", "--globals-only"]
    )
    listing = _command(
        backup,
        "restore-list.txt",
        ["docker", "exec", "-i", run.container, "pg_restore", "--list"],
        source=dump,
    )
    if not all(ref.bytes for ref in (dump, globals_dump, listing)):
        raise Refusal("custom dump, globals or restore listing is empty")
    refs.extend((dump, globals_dump, listing))
    refs.extend(backup.reference(ref.path + ".stderr") for ref in (dump, globals_dump, listing))
    run.authenticate()
    with _conn(run, "postgres") as admin:
        if _inventory(admin, run) != initial:
            raise Refusal("cluster changed during logical dump")
        _restrict_writer(admin, run)
        oid = _verify_create(admin, run, original["database"])
        refs.append(
            backup.publish_json(
                "verification-identity.json",
                {"name": run.verification, "oid": oid, "owner": run.owner[8], "initial": initial},
            )
        )
        if original["database"]["allows_connections"] is not True:
            raise Refusal("original database is not open for its verified logins")
        # The actual closed DB guard is the sole intentional authority difference.
        expected_closed = {
            **original,
            "database": {**original["database"], "allows_connections": False},
        }
        gate = RestoreAdmission(admin, run, oid, original["database"]["connection_limit"])
        with gate.window(0):
            refs.append(
                _command(
                    backup,
                    "restore.stdout",
                    [
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
                    ],
                    source=dump,
                    monitor=gate,
                )
            )
        gate.finish_restore()
        refs.append(backup.reference("restore.stdout.stderr"))
        with gate.session("test", "restore-authority") as conn:
            _db_privileges(conn, run.verification, expected_closed["database"])
        restored_probes = _probes(admin, run, run.verification, oid, oid, gate)
        refs.append(backup.publish_json("restored-probes.json", restored_probes))
        with gate.session("test", "final-snapshot") as conn:
            restored = terminal_snapshot(conn, run.campaign, run.period)
        refs.append(backup.publish_json("restored-terminal.json", restored))
        if restored != expected_closed or restored_probes != probes or original != functional:
            raise Refusal("restored state or restricted operations differ; retain both databases")
        refs.append(
            backup.publish_json(
                "verification-admission.json",
                {
                    "verification_oid": oid,
                    "original_allow_connections": True,
                    "verified_final_allow_connections": False,
                    "source_connection_limit": gate.limit,
                    "creation_connection_limit": 0,
                    "stats_reset": gate.reset,
                    "postmaster_stamp": gate.postmaster,
                    "sessions": gate.sessions,
                },
            )
        )
        for ref in refs:
            backup.verify(ref)
        run.authenticate()
        with _conn(run, run.database) as source_conn:
            final_original = terminal_snapshot(source_conn, run.campaign, run.period)
        if final_original != functional:
            raise Refusal(
                "original terminal state changed during restore; retain verification database"
            )
        gate.reconcile()
        admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(run.verification)))
        if _inventory(admin, run) != initial:
            raise Refusal("normal cluster inventory differs after verification DB removal")
    return refs


def _physical_witness(run: Run, physical: dict[str, Any]) -> PhysicalWitness:
    with _conn(run, run.database) as conn, conn.transaction():
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        spaces = conn.execute("SELECT spcname FROM pg_tablespace ORDER BY spcname").fetchall()
        if spaces != [("pg_default",), ("pg_global",)]:
            raise Refusal("external tablespaces cannot be included in this PGDATA archive")
        oid, cluster, size, wal_head = _one(
            conn,
            """
            SELECT d.oid,(pg_control_system()).system_identifier::text,
                   pg_size_bytes(current_setting('wal_segment_size')),
                   pg_read_binary_file('pg_wal/'||pg_walfile_name(pg_current_wal_lsn()),0,40)
            FROM pg_database d WHERE d.datname=current_database()
        """,
        )
        if (
            str(oid) != run.owner[9]
            or cluster != physical["cluster"]
            or size < 1024**2
            or size > 1024**3
            or size & (size - 1)
            or len(wal_head) != 40
            or struct.unpack_from("<H", wal_head)[0] != 0xD116
            or struct.unpack_from("<QII", wal_head, 24) != (int(cluster), size, 8192)
        ):
            raise Refusal("source database, cluster or WAL header differs from physical authority")
        major, control_version, catalog, block, segment, preload, save, extension = _one(
            conn,
            """
            SELECT current_setting('server_version_num'),(pg_control_system()).pg_control_version,
                   (pg_control_system()).catalog_version_no, current_setting('block_size')::int,
                   pg_size_bytes(current_setting('segment_size')), current_setting('shared_preload_libraries'),
                   current_setting('pg_stat_statements.save'), (SELECT extversion FROM pg_extension
                   WHERE extname='pg_stat_statements')
        """,
        )
        if (major, control_version, catalog, block, segment, preload, save, extension) != (
            "170011",
            1700,
            202406281,
            PAGE,
            RELSEG_BYTES,
            "pg_stat_statements",
            "on",
            "1.11",
        ):
            raise Refusal(
                "source PostgreSQL ABI, relation geometry or statistics extension differs"
            )
        physical = {**physical, "pgss": {"preload": preload, "save": save, "version": extension}}
        selected = conn.execute("""
            WITH terminal AS (
                SELECT c.oid FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE c.relkind IN ('r','m') AND n.nspname IN ('babylon_state','babylon_meta')
            ), files AS (
                SELECT oid FROM terminal UNION SELECT indexrelid FROM pg_index JOIN terminal ON indrelid=oid
            ) SELECT n.nspname||'.'||c.relname,pg_relation_filepath(c.oid),pg_relation_size(c.oid,'main')
            FROM files JOIN pg_class c USING(oid) JOIN pg_namespace n ON n.oid=c.relnamespace ORDER BY 1
        """).fetchall()
        relations = {name: path for name, path, _ in selected}
        physical["relation_sizes"] = {path: int(length) for _, path, length in selected}
        if (
            len(relations) != len(selected)
            or not REQUIRED_ROWS <= relations.keys()
            or any(
                not re.fullmatch(rf"base/{oid}/[1-9][0-9]*", path or "")
                for path in relations.values()
            )
        ):
            raise Refusal(
                "terminal table and index relation paths are incomplete or outside the database"
            )
        physical["relation_page_samples"] = _source_pages(conn, physical["relation_sizes"])
    cmd = ["docker", "exec", "-w", storage.PGDATA, run.container]
    # GNU find does not follow symlinks here. Its NUL-separated names are data.
    raw = storage._exec_bytes(
        [*cmd, "find", "-P", ".", "-xdev", "-printf", r"%P\0%y\0%m\0%U\0%G\0%s\0%D\0"], timeout=120
    )
    fields = raw.split(b"\0")
    if fields.pop() or len(fields) % 7:
        raise Refusal("container member inventory is truncated")
    members: dict[str, Member] = {}
    root = physical["container_root"]
    for i in range(0, len(fields), 7):
        raw_path, kind, mode, uid, gid, length, device = fields[i : i + 7]
        path = _member_name(raw_path.decode() or ".")
        if (
            kind not in (b"f", b"d")
            or path in members
            or int(device) != os.makedev(root["major"], root["minor"])
            or path.startswith("pg_tblspc/")
        ):
            raise Refusal("PGDATA contains a nested mount, link, special file or duplicate name")
        sha = None
        if path in STABLE_BYTES or path.endswith("/PG_VERSION"):
            actual = storage._exec_bytes([*cmd, "cat", "--", "./" + path])
            if len(actual) != int(length):
                raise Refusal("stable source file changed during physical attestation")
            if (
                path == "PG_VERSION"
                and actual != physical["pg_version"].encode()
                or path == ".babylon-postgres-lineage-v1"
                and actual != physical["lineage"].encode()
            ):
                raise Refusal("running PGDATA differs from independent admitted lineage/version")
            sha = hashlib.sha256(actual).hexdigest()
        members[path] = Member(
            "dir" if kind == b"d" else "file", int(mode, 8), int(uid), int(gid), int(length), sha
        )
    seen_root = members.pop(".", None)
    if seen_root is None or (seen_root.kind, seen_root.mode, seen_root.uid, seen_root.gid) != (
        "dir",
        root["mode"],
        root["uid"],
        root["gid"],
    ):
        raise Refusal("container traversal root differs from the independently bound PGDATA")
    if not {
        "PG_VERSION",
        ".babylon-postgres-lineage-v1",
        "global/pg_control",
        "pg_wal",
        "pg_tblspc",
        *relations.values(),
    } <= members.keys() or not any(WAL_NAME.fullmatch(p) for p in members):
        raise Refusal("running physical witness is missing required relations, control or WAL")
    witness = PhysicalWitness(physical, members, relations, oid, size, 0xD116)
    _extents(witness, members)
    _pgss_source(witness)
    return witness


def _stopped(run: Run, witness: PhysicalWitness) -> None:
    directory = Evidence(run.evidence)
    storage._daemon_endpoint()
    active = Evidence(storage.held_native_lock(run.root))
    owner_bytes = ("\n".join(run.owner) + "\n").encode()
    if (
        active.read_reference(active.reference("active")) != owner_bytes
        or directory.read_reference(directory.reference("ownership")) != owner_bytes
    ):
        raise Refusal("stopped recovery no longer holds its matching active and frozen owner")
    with storage.pinned_ancestry(run.evidence.parent) as pins:
        created = storage._media_creation(directory, pins)
        record = storage._one_docker("container", run.container)
        mounts = storage.container_mounts(
            record, run.root, run.evidence.parent, run.owner[2], run.container, run.owner[6]
        )
        if (
            created["daemon"] != witness.physical["daemon"]
            or mounts["mounts"] != witness.physical["mounts"]
            or storage._host_identity(run.evidence.parent / "pgdata") != witness.physical["host"]
            or record["State"]["Status"] != "exited"
            or record["State"]["Running"] is not False
            or record["State"]["ExitCode"] != 0
            or record["State"]["OOMKilled"] is not False
        ):
            raise Refusal("stopped container, clean shutdown or retained bind identity differs")


def _seal_archive(directory: Evidence, ref: Reference, final: str) -> Reference:
    directory.verify(ref)
    fd = os.open(directory.path, storage.DIR_FLAGS)
    try:
        os.link(ref.path, final, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
        os.fsync(fd)
    finally:
        os.close(fd)
    sealed = Reference(path=final, bytes=ref.bytes, sha256=ref.sha256)
    directory.verify(sealed)
    return sealed


def _offline(
    run: Run, backup: Evidence, witness: PhysicalWitness, witness_ref: Reference
) -> list[Reference]:
    names = ("pgdata.tar", "pgdata-second.tar")
    first: dict[str, Member] | None = None
    namespace = ""
    partials = []
    refs = []
    for name in names:
        _stopped(run, witness)
        partial = _command(
            backup,
            name + ".partial",
            ["docker", "cp", "-a", run.container + ":" + storage.PGDATA + "/.", "-"],
        )
        with backup.file(partial.path) as stream:
            members, current = archive_manifest(stream, witness)
        if first is not None and (first != members or current != namespace):
            raise Refusal(
                "second independent stopped archive differs from the first complete manifest"
            )
        first, namespace = members, current
        refs.append(backup.reference(partial.path + ".stderr"))
        manifest = {
            "archive": Reference(
                path=name, bytes=partial.bytes, sha256=partial.sha256
            ).model_dump(),
            "root_and_source": witness_ref.model_dump(),
            "numeric_id_space": current,
            "members": {key: asdict(member) for key, member in members.items()},
        }
        refs.append(backup.publish_json(name + ".manifest.json", manifest))
        partials.append(partial)
    for partial, name in zip(partials, names, strict=True):
        refs.append(_seal_archive(backup, partial, name))
    # Both verified final names now retain the exact archived inodes.
    fd = os.open(backup.path, storage.DIR_FLAGS)
    try:
        for partial, name in zip(partials, names, strict=True):
            if not os.path.samestat(
                os.stat(partial.path, dir_fd=fd, follow_symlinks=False),
                os.stat(name, dir_fd=fd, follow_symlinks=False),
            ):
                raise Refusal("published archive and its original temporary inode differ")
            os.unlink(partial.path, dir_fd=fd)
        os.fsync(fd)
    finally:
        os.close(fd)
    if first is None:
        raise Refusal("offline archive accounting requires both verified passes")
    # Count files once by inode. The bind itself is deliberately unreadable to
    # the operator after init; the authenticated tar supplies its file lengths.
    files = []
    seen = set()
    for child in sorted(backup.path.iterdir()):
        with backup.file(child.name) as stream:
            info = os.fstat(stream.fileno())
            if (info.st_dev, info.st_ino) not in seen:
                files.append(
                    {"path": child.name, "bytes": info.st_size, "allocated": info.st_blocks * 512}
                )
                seen.add((info.st_dev, info.st_ino))
    filesystem = os.statvfs(backup.path)
    refs.append(
        backup.publish_json(
            "retained-storage.json",
            {
                "primary_file_bytes": sum(m.size or 0 for m in first.values() if m.kind == "file"),
                "backup_files_before_seal": files,
                "available_media_bytes_at_measurement": filesystem.f_bavail * filesystem.f_frsize,
            },
        )
    )
    return refs


def backup_and_retire(
    root: Path, evidence: Path, owner: tuple[str, ...], campaign: str, period: int
) -> None:
    run = Run(root, evidence, owner, campaign, period)
    run.authenticate()
    directory = Evidence(evidence)
    backup = Evidence(evidence.parent / "backup")
    functional_ref = directory.reference("functional-terminal.json")
    functional = strict_json_bytes(directory.read_reference(functional_ref, maximum=512 * 1024**2))
    if not isinstance(functional, dict) or (
        functional.get("campaign"),
        functional.get("period"),
    ) != (campaign, period):
        raise Refusal("functional terminal receipt belongs to another campaign or period")
    logical = _logical(run, backup, functional)
    physical = run.authenticate()
    witness = _physical_witness(run, physical)
    witness_ref = backup.publish_json("pre-stop-physical.json", asdict(witness))
    for item in [*logical, witness_ref]:
        backup.verify(item)
    directory.verify(functional_ref)
    run.authenticate()
    with _conn(run, "postgres") as admin:
        _inventory(admin, run)
    storage.stop_checked(directory, run.container)
    shutdown = directory.reference("clean-shutdown.log")
    archives = _offline(run, backup, witness, witness_ref)
    retained = [*logical, witness_ref, *archives]
    seal = backup.publish_json(
        "recovery-seal.json",
        {
            "owner": directory.reference("ownership").model_dump(),
            "functional": functional_ref.model_dump(),
            "shutdown": shutdown.model_dump(),
            "retained": [ref.model_dump() for ref in retained],
        },
    )
    for item in [*retained, seal]:
        backup.verify(item)
    directory.verify(functional_ref)
    directory.verify(shutdown)
    _stopped(run, witness)
    storage.remove_stopped(directory, root, run.container, owner[2], owner[6])
