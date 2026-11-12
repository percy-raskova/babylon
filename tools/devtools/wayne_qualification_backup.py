"""Restore and compare the terminal Wayne campaign before preserving its bound PGDATA."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import struct
import subprocess
import tarfile
import tempfile
import time
from collections.abc import Iterator
from contextlib import ExitStack, closing, contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, BinaryIO, Literal
from uuid import UUID, uuid4

import psycopg
from psycopg import sql
from psycopg.abc import QueryNoTemplate
from pydantic import Field, StrictBool, StrictInt, StrictStr, ValidationError
from tools.devtools import wayne_qualification_storage as storage
from tools.devtools.national_native_evidence import OriginalDecision
from tools.devtools.national_storage_qualification import (
    FrozenRecord,
    Nonnegative,
    Positive,
    Sha256,
    strict_json_bytes,
)

Refusal = storage.StorageRefusal
Connection = psycopg.Connection[Any]
Evidence = storage.PrivateEvidence
Reference = storage.Reference
NATIVE_CLIENT_SLOTS = 50  # docker/postgres/postgresql.ci.conf
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


def _catalog(conn: Connection, database: str | None = None) -> dict[str, Any]:
    owner, encoding, collate, ctype, provider, locale, rules, connlimit, default_acl, allows = _one(
        conn,
        """
        SELECT pg_get_userbyid(datdba),pg_encoding_to_char(encoding),datcollate,datctype,
               datlocprovider::text,datlocale,daticurules,datconnlimit,datacl IS NULL,datallowconn
        FROM pg_catalog.pg_database WHERE datname=coalesce(%s::text,current_database())
    """,
        (database,),
    )
    acl = conn.execute(
        """
        SELECT pg_get_userbyid(a.grantor),CASE WHEN a.grantee=0 THEN NULL ELSE pg_get_userbyid(a.grantee) END,
               a.privilege_type,a.is_grantable
        FROM pg_catalog.pg_database d CROSS JOIN LATERAL aclexplode(COALESCE(d.datacl,acldefault('d',d.datdba))) a
        WHERE datname=coalesce(%s::text,current_database()) ORDER BY 1,2 NULLS FIRST,3,4
    """,
        (database,),
    ).fetchall()
    settings = conn.execute(
        """
        SELECT CASE WHEN s.setrole=0 THEN NULL ELSE pg_get_userbyid(s.setrole) END,setting
        FROM pg_catalog.pg_db_role_setting s CROSS JOIN LATERAL unnest(s.setconfig) setting
        WHERE s.setdatabase=(SELECT oid FROM pg_database WHERE datname=coalesce(%s::text,current_database()))
        ORDER BY 1 NULLS FIRST,2
    """,
        (database,),
    ).fetchall()
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
    if len(rows) != period or any(row[0] != tick for tick, row in enumerate(rows, 1)):
        raise Refusal("durable markers and checkpoints are not contiguous through terminal")
    entries = []
    previous = None
    for tick, digest, envelope, encoded, checkpoint in rows:
        if not all(
            isinstance(v, str) and re.fullmatch(r"[a-f0-9]{64}", v)
            for v in (digest, envelope, checkpoint)
        ):
            raise Refusal("commit marker, envelope or checkpoint digest is incomplete")
        if (
            not isinstance(encoded, str)
            or not re.fullmatch("[a-f0-9]+", encoded)
            or len(encoded) != 2 * (len(domain) + 12 + 224)
        ):
            raise Refusal("commit marker does not match its canonical material identity")
        raw = bytes.fromhex(encoded)
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


class TerminalMarker(FrozenRecord):
    tick: Positive
    hash: Sha256
    envelope: Sha256
    identity: StrictStr
    checkpoint: Sha256
    world_before: Sha256
    world_after: Sha256
    receipt: Sha256


class ArchiveConsumption(FrozenRecord):
    tick: Positive
    marker: Sha256
    batch: Sha256
    worker: Sha256
    knowledge: Sha256


class DrainedArchive(FrozenRecord):
    terminal_marker: Sha256
    watermark: Nonnegative
    pending: Nonnegative
    receipts: tuple[ArchiveConsumption, ...]


class TerminalDatabase(FrozenRecord):
    owner: StrictStr
    encoding: Literal["UTF8"]
    collate: StrictStr
    ctype: StrictStr
    provider: Literal["b"]
    locale: Literal["C.UTF-8"]
    icu_rules: None
    connection_limit: StrictInt
    acl_default: StrictBool
    allows_connections: StrictBool
    acl: tuple[tuple[StrictStr, StrictStr | None, StrictStr, StrictBool], ...]
    settings: tuple[tuple[StrictStr | None, StrictStr], ...]


AuthorityRow = tuple[
    StrictStr,
    StrictStr,
    StrictStr,
    StrictStr,
    StrictStr | None,
    StrictStr | None,
    StrictStr | None,
    StrictBool | None,
]


class FunctionalTerminal(FrozenRecord):
    campaign: StrictStr
    period: Positive
    identity: tuple[
        StrictStr, Literal["national-world"], Sha256, Sha256, Sha256, Sha256, Sha256, Sha256, Sha256
    ]
    markers: Annotated[tuple[TerminalMarker, ...], Field(min_length=1)]
    archive_terminal: DrainedArchive
    organizer_decisions: tuple[OriginalDecision, ...]
    campaign_rows_sha256: dict[StrictStr, tuple[Sha256, ...]]
    database: TerminalDatabase
    object_authority: tuple[AuthorityRow, ...]


def _validate_wayne_campaign_rows(tables: dict[str, tuple[str, ...]], period: int) -> None:
    # Rust's current-schema census includes every installed base relation. The
    # current DDL scopes all state and meta relations to campaign_id except the
    # schema singleton. Reference relations have no campaign_id.
    census = (
        Path(__file__).resolve().parents[2]
        / "rust/crates/babylon-persistence/src/fixtures/current_schema_census.txt"
    )
    expected = {
        f"{schema}.{table}"
        for schema, table in re.findall(
            r"^relation\|(babylon_state|babylon_meta)\|([^|\n]+)\|",
            census.read_text(),
            re.MULTILINE,
        )
    }
    if tables.keys() != expected - {"babylon_meta.current_schema"}:
        raise Refusal("functional terminal differs from the complete campaign-table roster")
    if not REQUIRED_ROWS <= {name for name, rows in tables.items() if rows} or any(
        tuple(sorted(rows)) != rows for rows in tables.values()
    ):
        raise Refusal("terminal lacks required ordered campaign-table row hashes")
    # organizer_archive::subject_definitions creates four base subjects. The
    # named national opening adds one local and one remote aid-partner subject.
    subjects = tables["babylon_state.organizer_subject_v1"]
    if len(subjects) != 6 or len(set(subjects)) != 6:
        raise Refusal("native Wayne terminal requires its six distinct organizer subject rows")
    per_period = (
        "babylon_state.tick_commit",
        "babylon_state.material_tick_v3",
        "babylon_state.checkpoint_manifest",
        "babylon_state.archive_dirty_receipt_v1",
        "babylon_meta.archive_receipt_consumption_v1",
        "babylon_meta.archive_tick_knowledge_v3",
    )
    if any(len(tables[name]) != period for name in per_period):
        raise Refusal("terminal campaign row counts differ from the drained marker chain")


def validate_terminal(raw: object, campaign: str, period: int) -> FunctionalTerminal:
    """Replay the repeatable-read terminal contract without a database connection."""
    try:
        terminal = FunctionalTerminal.model_validate(raw)
    except ValidationError as error:
        raise Refusal("functional terminal has incomplete or malformed SQL evidence") from error
    if (terminal.campaign, terminal.identity[0], terminal.period) != (campaign, campaign, period):
        raise Refusal("functional terminal campaign or period differs")
    chain = _markers(
        [(m.tick, m.hash, m.envelope, m.identity, m.checkpoint) for m in terminal.markers],
        period,
        terminal.identity[3],
    )
    if chain != [m.model_dump() for m in terminal.markers]:
        raise Refusal("terminal world or receipt differs from its canonical material identity")
    archive = terminal.archive_terminal
    if (archive.terminal_marker, archive.pending, archive.watermark) != (
        terminal.markers[-1].hash,
        0,
        period,
    ) or [(r.tick, r.marker) for r in archive.receipts] != [
        (m.tick, m.hash) for m in terminal.markers
    ]:
        raise Refusal("Archive is not drained through each terminal marker")
    tables = terminal.campaign_rows_sha256
    _validate_wayne_campaign_rows(tables, period)
    authority = terminal.object_authority
    if not {"babylon_meta", "babylon_ref", "babylon_state", "public"} <= {
        ns for kind, ns, ident, *_ in authority if kind == "schema" and not ident
    } or not tables.keys() <= {
        f"{ns}.{ident}" for kind, ns, ident, *_ in authority if kind in ("r", "p")
    }:
        raise Refusal("terminal object authority lacks campaign tables or schemas")
    grants = {
        (ident, grantee)
        for kind, ns, ident, _, _, grantee, privilege, grantable in authority
        if kind == "v" and ns == "public" and privilege == "SELECT" and grantable is False
    }
    if (
        not {
            ("v_observer_material_foundation_v1", "babylon_observer"),
            ("v_observer_material_state_v1", "babylon_observer"),
            ("v_archive_revision_known_v2", "babylon_reader"),
        }
        <= grants
    ):
        raise Refusal("terminal object authority lacks its foundation and restricted probe grants")
    return terminal


def terminal_snapshot(connection: Connection, campaign: str, period: int) -> dict[str, Any]:
    from tools.devtools.national_native_pair import terminal_decisions

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
        packet = {
            "campaign": campaign,
            "period": period,
            "identity": list(identity[0]),
            "markers": chain,
            "archive_terminal": _archive_terminal(connection, campaign, chain),
            "organizer_decisions": terminal_decisions(connection, campaign),
            "campaign_rows_sha256": _campaign_rows(connection, campaign),
            "database": _catalog(connection),
            "object_authority": _object_authority(connection),
        }
        validate_terminal(packet, campaign, period)
        return packet


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


def _source_checkpoint_lsn(value: object) -> int:
    match = (
        re.fullmatch(r"([0-9A-F]{1,8})/([0-9A-F]{1,8})", value) if isinstance(value, str) else None
    )
    if not match:
        raise Refusal("source checkpoint has no measured WAL location")
    lsn = int(match[1], 16) << 32 | int(match[2], 16)
    if not lsn or lsn % 8:
        raise Refusal("source checkpoint WAL location is zero or unaligned")
    return lsn


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
    if _source_checkpoint_lsn(witness.physical.get("source_checkpoint")) >= lsn:
        raise Refusal("measured source checkpoint must precede the archived shutdown checkpoint")
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


def _terminal_relations(
    conn: Connection, database_oid: int
) -> tuple[dict[str, str], dict[str, int]]:
    rows = conn.execute("""
        WITH RECURSIVE heaps(oid, toast) AS (
            SELECT c.oid,c.reltoastrelid FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE c.relkind IN ('r','m') AND n.nspname IN ('babylon_state','babylon_meta')
            UNION
            SELECT t.oid,t.reltoastrelid FROM heaps h JOIN pg_class t ON t.oid=h.toast
        ), files AS (
            SELECT oid FROM heaps UNION SELECT i.indexrelid FROM heaps h JOIN pg_index i ON i.indrelid=h.oid
        )
        SELECT c.oid,n.nspname||'.'||c.relname,c.relkind::text,c.reltoastrelid,i.indrelid,
               i.indisunique AND i.indisvalid AND i.indisready AND i.indislive,
               pg_relation_filepath(c.oid),pg_relation_size(c.oid,'main')
        FROM files f JOIN pg_class c ON c.oid=f.oid JOIN pg_namespace n ON n.oid=c.relnamespace
        LEFT JOIN pg_index i ON i.indexrelid=c.oid ORDER BY c.oid
    """).fetchall()
    relations = {name: path for _, name, _, _, _, _, path, _ in rows}
    sizes = {path: length for _, _, _, _, _, _, path, length in rows}
    declared = {toast for _, _, _, toast, _, _, _, _ in rows if toast}
    toast_heaps = {oid for oid, _, kind, _, _, _, _, _ in rows if kind == "t"}
    indexed = {parent for _, _, kind, _, parent, valid, _, _ in rows if kind == "i" and valid}
    if (
        len(relations) != len(rows)
        or len(sizes) != len(rows)
        or not REQUIRED_ROWS <= relations.keys()
        or declared != toast_heaps
        or not toast_heaps <= indexed
        or any(not re.fullmatch(rf"base/{database_oid}/[1-9][0-9]*", path or "") for path in sizes)
    ):
        raise Refusal("terminal heap, TOAST or index storage identity is incomplete")
    return relations, sizes


def _source_pages(conn: Connection, sizes: dict[str, int]) -> dict[str, str]:
    occupancy = {}
    for path, length in _extent_files(sizes).items():
        bits = bytearray((length // PAGE + 7) // 8)
        for pos in range(0, length, 1024 * 1024):
            count = min(1024 * 1024, length - pos)
            row = conn.execute(
                "SELECT pg_read_binary_file(%s,%s,%s)", (path, pos, count)
            ).fetchone()
            if row is None or len(row[0]) != count:
                raise Refusal("source extent changed while reading block occupancy")
            view = memoryview(row[0])
            for i in range(0, count, PAGE):
                block = (pos + i) // PAGE
                if _initialized(view[i : i + 24]):
                    bits[block // 8] |= 1 << (block % 8)
                elif view[i : i + PAGE] != bytes(PAGE):
                    raise Refusal("zero source header masks nonzero block contents")
        occupancy[path] = bits.hex()
    return occupancy


def _verify_blocks(chunk: bytes, start: int, occupancy: bytes) -> None:
    if len(chunk) % PAGE:
        raise Refusal("incomplete terminal relation block")
    view = memoryview(chunk)
    for i in range(0, len(chunk), PAGE):
        block = (start + i) // PAGE
        if not _initialized(view[i : i + 24]) and (
            occupancy[block // 8] & (1 << (block % 8)) or view[i : i + PAGE] != bytes(PAGE)
        ):
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
    if (
        config != {"preload": "pg_stat_statements", "save": "on", "version": "1.11"}
        or before is None
        or (before.kind, before.mode, before.uid, before.gid)
        != ("file", 0o600, witness.physical["server_uid"], witness.physical["server_gid"])
        or PGSS_STOPPED in witness.members
    ):
        raise Refusal(
            "pg_stat_statements persistence configuration or directional file transition differs"
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


def archive_manifest(
    stream: BinaryIO, witness: PhysicalWitness, stopped: dict[str, Member]
) -> tuple[dict[str, Member], str]:
    result: dict[str, Member] = {}
    extent_files = _extent_files(witness.physical["relation_sizes"])
    encoded = witness.physical["relation_page_occupancy"]
    if set(encoded) != set(extent_files):
        raise Refusal("independent block occupancy extent roster differs")
    occupancy = {}
    for path, length in extent_files.items():
        blocks = length // PAGE
        value = encoded[path]
        if (
            not isinstance(value, str)
            or not re.fullmatch("[0-9a-f]*", value)
            or len(value) != 2 * ((blocks + 7) // 8)
        ):
            raise Refusal("independent block occupancy has the wrong size or encoding")
        occupancy[path] = bytes.fromhex(value)
        if blocks % 8 and occupancy[path][-1] >> (blocks % 8):
            raise Refusal("independent block occupancy has nonzero padding")
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
            if path in extent_files and (item.isdir() or item.size != extent_files[path]):
                raise Refusal(
                    "stopped terminal heap or index extent differs from the measured source"
                )
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
                        _verify_blocks(header, 0, occupancy[path])
                    hasher = hashlib.sha256(header)
                    size = len(header)
                    while data := source.read(1024 * 1024):
                        if path in extent_files:
                            _verify_blocks(data, size, occupancy[path])
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
    _stopped_contract(witness, stopped)
    if set(result) != set(stopped):
        raise Refusal("archive and independent stopped source roster differ")
    modes = {"host", "container"}
    for path, expected in stopped.items():
        actual = result[path]
        if (
            actual.kind != expected.kind
            or actual.mode != expected.mode
            or actual.size != expected.size
            or actual.sha256 != expected.sha256
        ):
            raise Refusal("archive metadata or bytes differ from stopped source: " + path)
        host = (expected.uid, expected.gid)
        inside = (
            _unmapped(expected.uid, witness.physical["uid_map"]),
            _unmapped(expected.gid, witness.physical["gid_map"]),
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

    def authenticate(self, *, physical_connection: Connection | None = None) -> dict[str, Any]:
        if (
            len(self.owner) != 21
            or self.owner[0] != "national-storage-runner-media-v2"
            or self.owner[1] != str(self.root)
            or self.owner[10] != str(self.evidence)
            or storage.native_path(self.evidence)[0] != self.owner[11]
            or self.owner[11] not in ("smoke-01", "walk-01")
            or self.period != int(storage.PROFILES[self.owner[11]][1])
            or not re.fullmatch(r"[a-f0-9]{32}", self.owner[2])
            or self.database != "national_" + self.owner[2][:12]
            or self.owner[8] != "national_writer_" + self.owner[2][:12]
        ):
            raise Refusal("backup requires the exact terminal media-native owner")
        storage.reauthenticate_native_owner(
            self.root, self.evidence, self.owner, physical_connection=physical_connection
        )
        physical = storage._current_physical(
            Evidence(self.evidence),
            self.root,
            self.container,
            self.owner[2],
            self.owner[6],
            physical_connection=physical_connection,
        )
        if (
            type(physical.get("max_wal_senders")) is not int
            or physical["max_wal_senders"] != 0
            or type(physical.get("max_connections")) is not int
            or physical["max_connections"] != NATIVE_CLIENT_SLOTS
        ):
            raise Refusal(
                "native physical receipt differs from the selected 50 client slots and zero WAL senders"
            )
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


@dataclass(frozen=True)
class SessionTotal:
    oid: int
    sessions: int
    reset: str | None


@dataclass(frozen=True)
class ClusterStats:
    postmaster: str
    databases: dict[str, SessionTotal]


def _cluster_stats(admin: Connection) -> ClusterStats:
    started, counts, activities, senders = _one(
        admin,
        """
        SELECT (extract(epoch FROM pg_postmaster_start_time())*1000000)::bigint::text,
               current_setting('track_counts'),current_setting('track_activities'),current_setting('max_wal_senders')::int
    """,
    )
    if not started or (counts, activities, senders) != ("on", "on", 0):
        raise Refusal("cluster does not supply complete ordinary-client session statistics")
    rows = admin.execute("""
        SELECT d.datname::text,d.oid,s.sessions,(extract(epoch FROM s.stats_reset)*1000000)::bigint::text
        FROM pg_database d LEFT JOIN pg_stat_database s ON s.datid=d.oid ORDER BY d.oid
    """).fetchall()
    databases = {name: SessionTotal(oid, count, reset) for name, oid, count, reset in rows}
    if len(databases) != len(rows) or any(
        type(t.sessions) is not int or t.sessions < 0 for t in databases.values()
    ):
        raise Refusal("cluster database session counter is absent or ambiguous")
    return ClusterStats(started, databases)


def _stop_logging(conn: Connection) -> dict[str, str]:
    # These admitted privileged fence sessions must emit parseable shutdown logs.
    # An empty inherited locale does not establish their message language.
    conn.execute("SET SESSION lc_messages = 'C'")
    prefix, locale, verbosity, destination, collector, minimum, zone = _one(
        conn,
        """
        SELECT current_setting('log_line_prefix'),current_setting('lc_messages'),
               current_setting('log_error_verbosity'),current_setting('log_destination'),current_setting('logging_collector'),
               current_setting('log_min_messages'),current_setting('log_timezone')
    """,
    )
    result = {
        "prefix": prefix,
        "locale": locale,
        "verbosity": verbosity,
        "destination": destination,
        "collector": collector,
        "minimum": minimum,
        "timezone": zone,
    }
    _verify_stop_logging(**result)
    return result


def _verify_stop_logging(
    *,
    prefix: str,
    locale: str,
    verbosity: str,
    destination: str,
    collector: str,
    minimum: str,
    timezone: str,
) -> None:
    if (
        prefix != "%m [%p] "
        or locale != "C"
        or (
            verbosity not in ("default", "terse")
            or destination != "stderr"
            or collector != "off"
            or minimum
            not in (
                "debug5",
                "debug4",
                "debug3",
                "debug2",
                "debug1",
                "info",
                "notice",
                "warning",
                "error",
                "log",
                "fatal",
            )
            or timezone not in ("UTC", "Etc/UTC", "GMT", "Etc/GMT")
        )
    ):
        raise Refusal(
            "selected backend lacks a supported timestamped English PID-prefixed stderr log"
        )


class RestoreAdmission:
    """One admitted backend per closed verification-database window."""

    def __init__(
        self, admin: Connection, run: Run, oid: int, original_limit: int, prior: ClusterStats
    ) -> None:
        self.admin = admin
        self.run = run
        self.oid = oid
        self.limit = original_limit
        self.restore_backend: Backend | None = None
        self.sessions: list[dict[str, Any]] = []
        self._guard(False, 0)
        self._barrier()
        current = _cluster_stats(admin)
        new = current.databases.get(run.verification)
        if new is None or new.oid != oid or new.sessions or original_limit == 0:
            raise Refusal(
                "new verification database has wrong identity, prior sessions or a forbidden limit"
            )
        self.baseline = ClusterStats(prior.postmaster, {**prior.databases, run.verification: new})
        if current != self.baseline or run.verification in prior.databases:
            raise Refusal(
                "cluster sessions, database identity or reset epoch changed during creation"
            )
        self.expected = self.baseline.databases.copy()
        self.admin_backend = _own_backend(admin, prior.databases["postgres"].oid, "test")

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
            AND classid='pg_catalog.pg_database'::regclass
            AND mode='RowExclusiveLock'""",
        ) != (0,):
            raise Refusal("a verification backend is still entering the database")

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
        self.check_totals()

    def check_totals(self) -> None:
        if _cluster_stats(self.admin) != ClusterStats(self.baseline.postmaster, self.expected):
            raise Refusal(
                "cluster session totals, database identities, reset epochs or postmaster differ"
            )

    def _admit(
        self, purpose: str, backend: Backend, database: str, opened_limit: int | None
    ) -> None:
        if any(row["backend"] == asdict(backend) for row in self.sessions):
            raise Refusal("verification backend incarnation reused for another admitted connection")
        previous = self.expected[database]
        if backend.oid != previous.oid:
            raise Refusal("admitted backend differs from its database identity")
        self.expected[database] = SessionTotal(previous.oid, previous.sessions + 1, previous.reset)
        self.sessions.append(
            {
                "purpose": purpose,
                "database": database,
                "backend": asdict(backend),
                "open_limit": opened_limit,
                "closed_limit": self.limit if opened_limit is not None else None,
                "expected_sessions": previous.sessions + 1,
            }
        )

    def _record(self, purpose: str, backend: Backend, opened_limit: int) -> None:
        self._admit(purpose, backend, self.run.verification, opened_limit)
        self.reconcile(backend)

    @contextmanager
    def final_fence(self) -> Iterator[tuple[Connection, Connection, tuple[Backend, ...]]]:
        # REL_17_11 proc.c allocates exactly max_connections regular PGPROCs.
        # Superusers share this list; WAL senders have a separate, empty list.
        self.reconcile()
        if _one(
            self.admin,
            """SELECT current_setting('max_connections')::int,
                current_setting('max_wal_senders')::int,current_setting('idle_session_timeout')""",
        ) != (NATIVE_CLIENT_SLOTS, 0, "0"):
            raise Refusal(
                "final fence requires the selected 50 ordinary slots and zero WAL senders"
            )
        self.client_logging = {str(self.admin_backend.pid): _stop_logging(self.admin)}
        held: list[Backend] = []
        sockets = []
        with ExitStack() as stack:
            databases = [self.run.database, "template1"] + ["postgres"] * (NATIVE_CLIENT_SLOTS - 3)
            for db in databases:
                conn = stack.enter_context(closing(_conn(self.run, db)))
                own = _own_backend(conn, self.expected[db].oid, "test")
                if _one(conn, "SELECT current_setting('idle_session_timeout')") != ("0",):
                    raise Refusal("a final fence session can time out while held")
                self.client_logging[str(own.pid)] = _stop_logging(conn)
                conn.execute("SELECT pg_stat_force_next_flush()")
                self._admit("final-fence", own, db, None)
                held.append(own)
                sockets.append(conn)
            admitted = tuple(held)
            self.check_fence(admitted)
            yield sockets[0], sockets[1], admitted

    def check_fence(self, admitted: tuple[Backend, ...]) -> None:
        if (
            len({backend.pid for backend in (self.admin_backend, *admitted)}) != NATIVE_CLIENT_SLOTS
            or len(admitted) != NATIVE_CLIENT_SLOTS - 1
        ):
            raise Refusal("final fence lacks all 50 distinct authenticated ordinary clients")
        if (
            _own_backend(self.admin, self.baseline.databases["postgres"].oid, "test")
            != self.admin_backend
        ):
            raise Refusal("final maintenance backend incarnation changed")
        self._guard(False, self.limit)
        self._barrier()
        _inventory(self.admin, self.run, self.oid, admitted)
        self.check_totals()

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
    admitted: Backend | tuple[Backend, ...] | None = None,
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
    expected_clients = (
        admitted if isinstance(admitted, tuple) else (() if admitted is None else (admitted,))
    )
    if _clients(conn) != sorted(expected_clients, key=lambda backend: backend.pid):
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


def _require_wayne_reader_revision(row: object, period: int) -> None:
    if (
        not isinstance(row, (list, tuple))
        or len(row) != 5
        or tuple(row[:2]) != ("county", "26163")
        or type(row[2]) is not int
        or not 0 < row[2] <= period
        or any(
            not isinstance(value, str) or not re.fullmatch("[0-9a-f]{64}", value)
            for value in row[3:]
        )
    ):
        raise Refusal(
            "restricted Wayne reader revision lacks its subject, bounded period or SHA-256 digests"
        )


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
                _require_wayne_reader_revision(allowed, run.period)
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


@dataclass(frozen=True)
class ClientActivity:
    backend: Backend
    state: str
    no_transaction: bool
    no_xid: bool
    no_xmin: bool
    backend_type: str


@dataclass(frozen=True)
class HeldSource:
    gate: RestoreAdmission
    source: Connection
    maintenance: Connection
    admitted: tuple[Backend, ...]
    logical: tuple[Reference, ...]

    def quiescence(self, backup: Evidence, stage: str) -> Reference:
        admin, run = self.gate.admin, self.gate.run
        expected = {
            name: total for name, total in self.gate.expected.items() if name != run.verification
        }
        expected_clients = sorted((self.gate.admin_backend, *self.admitted), key=lambda b: b.pid)
        stats = _cluster_stats(admin)
        rows = admin.execute("""
            SELECT pid,(extract(epoch FROM backend_start)*1000000)::bigint::text,datid,usename,host(client_addr),client_port,
                   state,xact_start IS NULL,backend_xid IS NULL,backend_xmin IS NULL,backend_type
            FROM pg_stat_activity WHERE datid IS NOT NULL OR backend_type IN ('client backend','walsender') ORDER BY pid
        """).fetchall()
        activity = [ClientActivity(Backend(*row[:6]), *row[6:]) for row in rows]
        prepared, entering = _one(
            admin,
            """
            SELECT (SELECT count(*) FROM pg_prepared_xacts),
                   (SELECT count(*) FROM pg_locks WHERE locktype='object' AND classid='pg_catalog.pg_database'::regclass
                    AND mode='RowExclusiveLock')
        """,
        )
        record = backup.publish_json(
            stage + "-quiescence.json",
            {
                "expected_stats": asdict(ClusterStats(self.gate.baseline.postmaster, expected)),
                "actual_stats": asdict(stats),
                "expected_clients": [asdict(b) for b in expected_clients],
                "clients": [asdict(client) for client in activity],
                "observer_pid": self.gate.admin_backend.pid,
                "prepared_transactions": prepared,
                "entering_backends": entering,
                "client_logging": self.gate.client_logging,
            },
        )
        backup.verify(record)
        if (
            len(expected_clients) != NATIVE_CLIENT_SLOTS
            or len({b.pid for b in expected_clients}) != NATIVE_CLIENT_SLOTS
            or [client.backend for client in activity] != expected_clients
            or stats != ClusterStats(self.gate.baseline.postmaster, expected)
            or set(self.gate.client_logging) != {str(b.pid) for b in expected_clients}
            or prepared != 0
            or entering != 0
        ):
            raise Refusal(
                "physical observation lost its complete, continuously owned cluster census"
            )
        for client in activity:
            # This autocommit observer is executing this census. Every other
            # admitted socket must be idle outside a transaction, with no work.
            if client.backend == self.gate.admin_backend:
                if (
                    client.state != "active"
                    or not client.no_xid
                    or client.backend_type != "client backend"
                ):
                    raise Refusal("physical census administrator has an unexpected transaction")
            elif (
                client.state != "idle"
                or client.backend_type != "client backend"
                or not (client.no_transaction and client.no_xid and client.no_xmin)
            ):
                raise Refusal("a held maintenance client is not idle before physical observation")
        if _inventory(admin, run, admitted=self.admitted) != {
            name: t.oid for name, t in expected.items()
        }:
            raise Refusal("normal database inventory changed during physical observation")
        for conn in (admin, self.source, self.maintenance):
            if (
                not conn.autocommit
                or conn.info.transaction_status != psycopg.pq.TransactionStatus.IDLE
            ):
                raise Refusal("maintenance transaction is incomplete at the physical boundary")
        return record


@contextmanager
def _restored_source(
    run: Run, backup: Evidence, functional: dict[str, Any]
) -> Iterator[HeldSource]:
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
        [
            "docker",
            "exec",
            "-i",
            "-e",
            "LC_ALL=C",
            "-e",
            "TZ=UTC",
            run.container,
            "pg_restore",
            "--list",
        ],
        source=dump,
    )
    if not all(ref.bytes for ref in (dump, globals_dump, listing)):
        raise Refusal("custom dump, globals or restore listing is empty")
    refs.extend((dump, globals_dump, listing))
    refs.extend(backup.reference(ref.path + ".stderr") for ref in (dump, globals_dump, listing))
    run.authenticate()
    with closing(_conn(run, "postgres")) as admin:
        if _inventory(admin, run) != initial:
            raise Refusal("cluster changed during logical dump")
        _restrict_writer(admin, run)
        admin.execute("SELECT pg_stat_force_next_flush()")
        prior = _cluster_stats(admin)
        # Read cumulative counts first, then prove that no already-counted
        # backend survived the baseline into verification database creation.
        if {name: total.oid for name, total in prior.databases.items()} != initial or _inventory(
            admin, run
        ) != initial:
            raise Refusal("pre-creation session baseline or database roster changed")
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
        gate = RestoreAdmission(admin, run, oid, original["database"]["connection_limit"], prior)
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
        with gate.final_fence() as (source_conn, maintenance_conn, admitted):
            run.authenticate(physical_connection=maintenance_conn)
            if terminal_snapshot(source_conn, run.campaign, run.period) != functional:
                raise Refusal(
                    "original terminal state changed during restore; retain verification database"
                )
            shared = _catalog(admin, run.verification)
            if shared != expected_closed["database"]:
                raise Refusal("closed verification database authority changed before removal")
            gate.check_fence(admitted)
            refs.append(
                backup.publish_json(
                    "verification-admission.json",
                    {
                        "restore_evidence": {r.path: r.model_dump() for r in refs},
                        "verification_oid": oid,
                        "original_allow_connections": True,
                        "verified_final_allow_connections": False,
                        "source_connection_limit": gate.limit,
                        "creation_connection_limit": 0,
                        "baseline": asdict(gate.baseline),
                        "maintenance_backend": asdict(gate.admin_backend),
                        "sessions": gate.sessions,
                        "final_cluster_stats": asdict(_cluster_stats(admin)),
                        "final_shared_database": shared,
                        "held_client_slots": len(admitted) + 1,
                    },
                )
            )
            for ref in refs:
                backup.verify(ref)
            gate.check_fence(admitted)
            admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(run.verification)))
            if _inventory(admin, run, admitted=admitted) != initial:
                raise Refusal("normal cluster inventory differs after verification DB removal")
            yield HeldSource(gate, source_conn, maintenance_conn, admitted, tuple(refs))


def _container_paths(command: list[str]) -> dict[str, str]:
    # GNU and BusyBox both default to physical traversal; neither follows links here.
    raw = storage._exec_bytes([*command, "find", ".", "-xdev", "-print0"], timeout=120)
    if not raw.endswith(b"\0"):
        raise Refusal("container member inventory is truncated")
    names: dict[str, str] = {}
    for encoded in raw[:-1].split(b"\0"):
        try:
            original = encoded.decode("utf-8")
        except UnicodeDecodeError as error:
            raise Refusal("container member name is not UTF-8") from error
        if original != "." and not original.startswith("./"):
            raise Refusal("container member name is not relative to the exact traversal root")
        path = _member_name(original)
        if (
            original != ("." if path == "." else "./" + path)
            or os.fsencode(original) != encoded
            or path in names
            or path.startswith("pg_tblspc/")
        ):
            raise Refusal("PGDATA contains an ambiguous, duplicate or external tablespace name")
        names[path] = original
    if "." not in names:
        raise Refusal("container member inventory is missing its traversal root")
    return names


def _container_members(run: Run, physical: dict[str, Any]) -> dict[str, Member]:
    """Read container metadata and stable bytes without SQL or filesystem mutation."""
    command = ["docker", "exec", "-w", storage.PGDATA, run.container]
    names = _container_paths(command)
    root = physical["container_root"]
    device = os.makedev(root["major"], root["minor"])
    # No filenames enter the line-oriented format. Each exact find operand remains
    # one argv value, including embedded newlines, whitespace and leading dashes.
    stat_command = [*command, "stat", "-c", "%f %a %u %g %s %d", "--"]
    # Bound encoded strings, terminating NULs and 64-bit argv pointers well below
    # Linux's minimum argument budget, including each individual operand.
    limit = 32768
    fixed = sum(len(os.fsencode(arg)) + 1 + 8 for arg in stat_command)
    batches: list[list[str]] = []
    batch: list[str] = []
    used = fixed
    for original in names.values():
        length = len(os.fsencode(original)) + 1 + 8
        if fixed + length > limit:
            raise Refusal("container member name exceeds the bounded metadata argument budget")
        if used + length > limit:
            batches.append(batch)
            batch, used = [], fixed
        batch.append(original)
        used += length
    batches.append(batch)
    members: dict[str, Member] = {}
    for batch in batches:
        raw = storage._exec_bytes([*stat_command, *batch], timeout=120)
        rows = raw.split(b"\n")
        if rows.pop() or len(rows) != len(batch):
            raise Refusal("container numeric metadata is truncated or has extra records")
        for original, row in zip(batch, rows, strict=True):
            match = re.fullmatch(
                rb"([0-9a-fA-F]{1,4}) ([0-7]{1,4}) ([0-9]{1,10}) ([0-9]{1,10}) ([0-9]{1,19}) ([0-9]{1,20})",
                row,
            )
            if match is None:
                raise Refusal("container numeric metadata is malformed or out of range")
            raw_mode = int(match[1], 16)
            mode = int(match[2], 8)
            uid, gid, size, actual_device = (int(match[i]) for i in range(3, 7))
            kind = stat.S_IFMT(raw_mode)
            if (
                kind not in (stat.S_IFDIR, stat.S_IFREG)
                or stat.S_IMODE(raw_mode) != mode
                or max(uid, gid) > 2**32 - 1
                or size > 2**63 - 1
                or actual_device > 2**64 - 1
                or actual_device != device
            ):
                raise Refusal(
                    "PGDATA contains a nested mount, link, special file or invalid metadata"
                )
            path = "." if original == "." else original[2:]
            members[path] = Member(
                "dir" if kind == stat.S_IFDIR else "file", mode, uid, gid, size, None
            )
    seen_root = members.pop(".")
    if (seen_root.kind, seen_root.mode, seen_root.uid, seen_root.gid) != (
        "dir",
        root["mode"],
        root["uid"],
        root["gid"],
    ):
        raise Refusal("container traversal root differs from the independently bound PGDATA")
    for path, member in members.items():
        if path in STABLE_BYTES or path.endswith("/PG_VERSION"):
            actual = storage._exec_bytes([*command, "cat", "--", names[path]])
            if len(actual) != member.size:
                raise Refusal("stable source file changed during physical attestation")
            if (
                path == "PG_VERSION"
                and actual != physical["pg_version"].encode()
                or path == ".babylon-postgres-lineage-v1"
                and actual != physical["lineage"].encode()
            ):
                raise Refusal("running PGDATA differs from independent admitted lineage/version")
            members[path] = Member(
                member.kind,
                member.mode,
                member.uid,
                member.gid,
                member.size,
                hashlib.sha256(actual).hexdigest(),
            )
    if _container_paths(command) != names:
        raise Refusal("container member inventory changed during physical attestation")
    return members


def _physical_witness(run: Run, physical: dict[str, Any], conn: Connection) -> PhysicalWitness:
    if _one(
        conn,
        """SELECT session_user::text,current_user::text,current_database()::text,
            current_setting('babylon.disposable_runtime',true),(pg_control_system()).system_identifier::text,
            (SELECT oid::text FROM pg_database WHERE datname=current_database())""",
    ) != ("test", "test", run.database, run.owner[2], physical["cluster"], run.owner[9]):
        raise Refusal("source checkpoint requires the exact authenticated terminal database")
    conn.execute("CHECKPOINT")
    with conn.transaction():
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        (checkpoint,) = _one(conn, "SELECT (pg_control_checkpoint()).checkpoint_lsn::text")
        _source_checkpoint_lsn(checkpoint)
        physical = {**physical, "source_checkpoint": checkpoint}
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
        relations, sizes = _terminal_relations(conn, oid)
        physical["relation_sizes"] = sizes
        physical["relation_page_occupancy"] = _source_pages(conn, sizes)
    members = _container_members(run, physical)
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


def _unmapped(value: int, mapping: str) -> int:
    matches = [
        inside + value - host
        for inside, host, length in (map(int, row.split()) for row in mapping.splitlines())
        if host <= value < host + length
    ]
    if len(matches) != 1:
        raise Refusal("stopped source owner has no unique captured container ID")
    return matches[0]


def _stopped_contract(witness: PhysicalWitness, members: dict[str, Member]) -> None:
    root = witness.physical["host"]
    expected_root = Member("dir", root["mode"], root["uid"], root["gid"], 0, None)
    if members.get(".") != expected_root:
        raise Refusal("stopped source root differs from the admitted bind")
    for path, member in members.items():
        if path != _member_name(path) or path.startswith("pg_tblspc/"):
            raise Refusal("stopped source contains a noncanonical or external member")
        if member.kind == "file":
            if member.size is None or member.sha256 is None:
                raise Refusal("stopped ordinary file lacks its independent length or SHA256")
        elif member.kind != "dir" or member.size != 0 or member.sha256 is not None:
            raise Refusal("stopped member kind or directory payload differs")
    for path, before in witness.members.items():
        after = members.get(path)
        # Stable version, lineage and configuration remain independent running authority.
        if before.sha256 is not None and (
            after is None
            or (after.kind, after.mode, after.size, after.sha256)
            != (before.kind, before.mode, before.size, before.sha256)
            or (after.uid, after.gid)
            != (
                storage._mapped(before.uid, witness.physical["uid_map"]),
                storage._mapped(before.gid, witness.physical["gid_map"]),
            )
        ):
            raise Refusal("stopped stable bytes differ from the independent running source")


DOCKER_CREATED_AT = "0001-01-01T00:00:00Z"


def _docker_timestamp(value: object, label: str) -> datetime:
    match = (
        re.fullmatch(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?Z", value)
        if isinstance(value, str)
        else None
    )
    if match is None:
        raise Refusal(label + " Docker timestamp is malformed")
    # Docker retains nanoseconds; the authenticated Python datetime fence stores
    # microseconds. Deliberately truncate both to that common precision.
    fraction = (match[2] or "").ljust(6, "0")[:6]
    try:
        return datetime.fromisoformat(match[1] + "." + fraction + "+00:00")
    except ValueError as error:
        raise Refusal(label + " Docker timestamp is malformed") from error


def _helper_timestamp(value: object, status: str) -> None:
    if status == "created":
        if value != DOCKER_CREATED_AT:
            raise Refusal("created helper timestamp differs from the Docker zero value")
    elif value == DOCKER_CREATED_AT:
        raise Refusal("running helper still has the Docker zero timestamp")
    else:
        _docker_timestamp(value, "running helper")


def _fenced_finished(run: Run, witness: PhysicalWitness, reference: Reference) -> datetime:
    evidence = Evidence(run.evidence)
    if reference != evidence.reference("native-fenced-stop-v1.json"):
        raise Refusal("stopped source substituted its canonical fenced-stop reference")
    record = strict_json_bytes(evidence.read_reference(reference))
    if (
        not isinstance(record, dict)
        or record.get("container") != run.container
        or record.get("image") != run.owner[6]
        or storage.canonical_json(record.get("host"))
        != storage.canonical_json(witness.physical["host"])
        or type(record.get("exit_code")) is not int
        or record["exit_code"] != 0
        or record.get("oom_killed") is not False
    ):
        raise Refusal("stopped source fenced-stop authority differs from its container or bind")
    value = record.get("finished")
    if (
        not isinstance(value, str)
        or re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)", value)
        is None
    ):
        raise Refusal("authenticated fenced-stop finished timestamp is malformed")
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise Refusal("authenticated fenced-stop finished timestamp is malformed") from error


def _bind_stopped_state(state: dict[str, Any], finished: datetime) -> None:
    started_at = _docker_timestamp(state["StartedAt"], "stopped source StartedAt")
    finished_at = _docker_timestamp(state["FinishedAt"], "stopped source FinishedAt")
    if (
        state["StartedAt"] == DOCKER_CREATED_AT
        or not started_at < finished_at
        or finished_at != finished
    ):
        raise Refusal("stopped source incarnation differs from the authenticated fenced stop")


HELPER_SCRIPT = "exec sleep 2147483647"


def _helper_expected(run: Run, witness: PhysicalWitness, cid: str, token: str) -> dict[str, Any]:
    physical = witness.physical
    return {
        "id": cid,
        "image": run.owner[6],
        "name": "/babylon-stopped-" + token,
        "label": token,
        "user": f"{storage._mapped(physical['server_uid'], physical['uid_map'])}:"
        f"{storage._mapped(physical['server_gid'], physical['gid_map'])}",
        "path": "/bin/sh",
        "args": ["-ceu", HELPER_SCRIPT],
        "entrypoint": ["/bin/sh"],
        "healthcheck": ["NONE"],
        "network": "none",
        "userns": "host",
        "pid_mode": "",
        "ipc_mode": "private",
        "readonly": True,
        "privileged": False,
        "cap_add": [],
        "cap_drop": ["ALL"],
        "groups": [],
        "devices": [],
        "security": ["no-new-privileges"],
        "restart": "no",
        "restarts": 0,
        "mounts": [
            {
                "Type": "bind",
                "Source": str(run.evidence.parent / "pgdata"),
                "Destination": storage.PGDATA,
                "RW": False,
                "Propagation": "rprivate",
            }
        ],
    }


def _inspect_helper(run: Run, witness: PhysicalWitness, cid: str, token: str) -> dict[str, Any]:
    raw = storage._one_docker("container", cid)
    config, host = raw["Config"], raw["HostConfig"]
    proof = {
        "id": raw["Id"],
        "image": raw["Image"],
        "name": raw["Name"],
        "label": config["Labels"].get("babylon.stopped-source"),
        "user": config["User"],
        "path": raw["Path"],
        "args": raw["Args"],
        "entrypoint": config["Entrypoint"],
        "healthcheck": config["Healthcheck"]["Test"],
        "network": host["NetworkMode"],
        "userns": host["UsernsMode"],
        "pid_mode": host["PidMode"],
        "ipc_mode": host["IpcMode"],
        "readonly": host["ReadonlyRootfs"],
        "privileged": host["Privileged"],
        "cap_add": host["CapAdd"] or [],
        "cap_drop": host["CapDrop"],
        "groups": host["GroupAdd"] or [],
        "devices": host["Devices"] or [],
        "security": host["SecurityOpt"],
        "restart": host["RestartPolicy"]["Name"],
        "restarts": raw["RestartCount"],
        "mounts": [
            {k: m[k] for k in ("Type", "Source", "Destination", "RW", "Propagation")}
            for m in raw["Mounts"]
        ],
    }
    if (
        storage.canonical_json(proof)
        != storage.canonical_json(_helper_expected(run, witness, cid, token))
        or proof["readonly"] is not True
        or proof["privileged"] is not False
        or any(m["RW"] is not False for m in proof["mounts"])
        or type(proof["restarts"]) is not int
    ):
        raise Refusal("stopped helper image, identity or complete confinement differs")
    state = raw["State"]
    if (
        state["Status"] not in ("created", "running")
        or state["OOMKilled"] is not False
        or state["Running"] is not (state["Status"] == "running")
        or type(state["Pid"]) is not int
        or (state["Pid"] > 0) != (state["Status"] == "running")
    ):
        raise Refusal("stopped helper process state differs")
    _helper_timestamp(state["StartedAt"], state["Status"])
    return {
        "confinement": proof,
        "status": state["Status"],
        "pid": state["Pid"],
        "started": state["StartedAt"],
    }


def _reader_batches(names: list[str], command: list[str]) -> Iterator[list[str]]:
    used = sum(len(os.fsencode(arg)) + 9 for arg in command)
    fixed = used
    batch: list[str] = []
    for name in names:
        length = len(os.fsencode(name)) + 9
        if fixed + length > 32768:
            raise Refusal("stopped source name exceeds bounded reader argument budget")
        if used + length > 32768:
            yield batch
            batch, used = [], fixed
        batch.append(name)
        used += length
    if batch:
        yield batch


def _read_stopped(command: list[str], witness: PhysicalWitness) -> dict[str, Member]:
    names = _container_paths(command)
    root = witness.physical["host"]
    device = os.makedev(root["major"], root["minor"])
    members: dict[str, Member] = {}
    inodes: set[int] = set()
    # Bound each argv batch. Capture only metadata and SHA256, while the helper
    # streams payloads. Validate all metadata before asking it to hash any file.
    metadata = [*command, "stat", "-c", "%f|%a|%u|%g|%s|%d|%i|%h|%y|%z", "--"]
    observations: list[tuple[list[str], bytes]] = []
    for batch in _reader_batches(list(names.values()), metadata):
        before = storage._exec_bytes([*metadata, *batch], timeout=120)
        observations.append((batch, before))
        rows = before.splitlines(keepends=True)
        if len(rows) != len(batch):
            raise Refusal("stopped source metadata is truncated or has extra rows")
        regular: list[str] = []
        for original, row in zip(batch, rows, strict=True):
            match = re.fullmatch(
                rb"([0-9a-fA-F]{1,4})\|([0-7]{1,4})\|([0-9]{1,10})\|([0-9]{1,10})\|"
                rb"([0-9]{1,19})\|([0-9]{1,20})\|([0-9]{1,20})\|([0-9]{1,20})\|([^|\n]+)\|([^|\n]+)\n",
                row,
            )
            if match is None:
                raise Refusal("stopped source numeric metadata is malformed")
            raw_mode, mode = int(match[1], 16), int(match[2], 8)
            uid, gid, size, dev, inode, links = (int(match[i]) for i in range(3, 9))
            kind = stat.S_IFMT(raw_mode)
            if (
                kind not in (stat.S_IFDIR, stat.S_IFREG)
                or stat.S_IMODE(raw_mode) != mode
                or dev != device
                or max(uid, gid) > 2**32 - 1
                or size > 2**63 - 1
                or inode in inodes
                or kind == stat.S_IFREG
                and links != 1
            ):
                raise Refusal(
                    "stopped source has a cross-mount, alias, link, special or invalid member"
                )
            if original == "." and inode != root["inode"]:
                raise Refusal("stopped helper traversal root differs from the admitted bind inode")
            inodes.add(inode)
            path = "." if original == "." else original[2:]
            members[path] = Member(
                "dir" if kind == stat.S_IFDIR else "file",
                mode,
                uid,
                gid,
                0 if kind == stat.S_IFDIR else size,
                None,
            )
            if kind == stat.S_IFREG:
                regular.append(original)
        hashing = [
            *command,
            "/bin/sh",
            "-ceu",
            'for file do sha256sum < "$file"; done',
            "stopped-sha256",
        ]
        for files in _reader_batches(regular, hashing):
            hashes = storage._exec_bytes([*hashing, *files], timeout=120).splitlines()
            if len(hashes) != len(files):
                raise Refusal("stopped source SHA256 output is truncated or has extra rows")
            for original, raw in zip(files, hashes, strict=True):
                found = re.fullmatch(rb"([0-9a-f]{64})  -", raw)
                if found is None:
                    raise Refusal("stopped source SHA256 output is malformed")
                path = original[2:]
                m = members[path]
                members[path] = Member(
                    m.kind, m.mode, m.uid, m.gid, m.size, found[1].decode("ascii")
                )
        if storage._exec_bytes([*metadata, *batch], timeout=120) != before:
            raise Refusal("stopped source member mutated during hashing")
    if _container_paths(command) != names:
        raise Refusal("stopped source roster mutated during inventory")
    for batch, before in observations:
        if storage._exec_bytes([*metadata, *batch], timeout=120) != before:
            raise Refusal("stopped source mutated before inventory completion")
    _stopped_contract(witness, members)
    return members


def _source_changes(witness: PhysicalWitness, members: dict[str, Member]) -> dict[str, Any]:
    return {
        path: {
            "running": asdict(witness.members[path]) if path in witness.members else None,
            "stopped": asdict(members[path]) if path in members else None,
        }
        for path in sorted(set(witness.members) | set(members))
        if witness.members.get(path) != members.get(path)
    }


class StoppedFile(FrozenRecord):
    kind: Literal["dir", "file"]
    mode: Annotated[StrictInt, Field(ge=0, le=0o7777)]
    uid: Annotated[StrictInt, Field(ge=0, le=2**32 - 1)]
    gid: Annotated[StrictInt, Field(ge=0, le=2**32 - 1)]
    size: Nonnegative
    sha256: Sha256 | None


class StoppedSource(FrozenRecord):
    version: Literal[1]
    pre_stop: Reference
    fenced_stop: Reference
    source: dict[str, Any]
    helper_created: dict[str, Any]
    helper_running: dict[str, Any]
    members: dict[str, StoppedFile]
    changes: dict[str, Any]


def _retained_stopped(
    raw: object, run: Run, witness: PhysicalWitness, witness_ref: Reference, fenced_stop: Reference
) -> dict[str, Member]:
    try:
        packet = StoppedSource.model_validate(raw)
        created, running = packet.helper_created, packet.helper_running
        proof = created["confinement"]
        cid, token = proof["id"], proof["label"]
        expected = _helper_expected(run, witness, cid, token)
        source = packet.source
        state = source["state"]
        _helper_timestamp(created["started"], created["status"])
        _helper_timestamp(running["started"], running["status"])
        _bind_stopped_state(state, _fenced_finished(run, witness, fenced_stop))
        members = {k: Member(**v.model_dump()) for k, v in packet.members.items()}
        if (
            type(packet.version) is not int
            or packet.pre_stop != witness_ref
            or packet.fenced_stop != fenced_stop
            or re.fullmatch("[0-9a-f]{64}", cid) is None
            or re.fullmatch("[0-9a-f]{32}", token) is None
            or storage.canonical_json(proof) != storage.canonical_json(expected)
            or storage.canonical_json(running["confinement"]) != storage.canonical_json(expected)
            or set(created) != {"confinement", "status", "pid", "started"}
            or set(running) != set(created)
            or created["status"] != "created"
            or type(created["pid"]) is not int
            or created["pid"] != 0
            or running["status"] != "running"
            or type(running["pid"]) is not int
            or running["pid"] <= 0
            or not isinstance(running["started"], str)
            or not running["started"]
            or storage.canonical_json(source)
            != storage.canonical_json(
                {
                    "container": run.container,
                    "image": run.owner[6],
                    "daemon": witness.physical["daemon"],
                    "mounts": witness.physical["mounts"],
                    "host": witness.physical["host"],
                    "state": state,
                }
            )
            or set(state)
            != {"Status", "Running", "ExitCode", "OOMKilled", "Pid", "StartedAt", "FinishedAt"}
            or state["Status"] != "exited"
            or state["Running"] is not False
            or state["OOMKilled"] is not False
            or type(state["ExitCode"]) is not int
            or state["ExitCode"] != 0
            or type(state["Pid"]) is not int
            or state["Pid"] != 0
            or not all(isinstance(state[k], str) and state[k] for k in ("StartedAt", "FinishedAt"))
            or storage.canonical_json(packet.changes)
            != storage.canonical_json(_source_changes(witness, members))
        ):
            raise Refusal(
                "stopped source receipt differs from its independent source or confinement"
            )
        _stopped_contract(witness, members)
        return members
    except Refusal:
        raise
    except (ValidationError, KeyError, TypeError, ValueError) as error:
        raise Refusal("stopped source receipt is malformed or unsupported") from error


def _reader_mounts(command: list[str]) -> None:
    rows = storage._exec_bytes([*command, "cat", "/proc/self/mountinfo"]).splitlines()
    bound = []
    for row in rows:
        fields = row.split()
        if len(fields) < 10 or b"-" not in fields:
            raise Refusal("stopped helper mount namespace observation is malformed")
        destination = fields[4]
        if destination == storage.PGDATA.encode() or destination.startswith(
            storage.PGDATA.encode() + b"/"
        ):
            bound.append((destination, fields[5].split(b",")))
    if len(bound) != 1 or bound[0][0] != storage.PGDATA.encode() or b"ro" not in bound[0][1]:
        raise Refusal("stopped helper has a nested mount or non-readonly PGDATA")


def _stopped_inventory(
    run: Run,
    backup: Evidence,
    witness: PhysicalWitness,
    witness_ref: Reference,
    fenced_stop: Reference,
) -> tuple[Reference, dict[str, Member]]:
    before = _stopped(run, witness, fenced_stop)
    token = uuid4().hex
    cid = ""
    failure: BaseException | None = None
    with tempfile.TemporaryDirectory(prefix="babylon-stopped-") as temporary:
        cidfile = Path(temporary) / "cid"
        expected = _helper_expected(run, witness, cid, token)
        command = [
            "docker",
            "create",
            "--no-healthcheck",
            "--pull",
            "never",
            "--name",
            expected["name"][1:],
            "--label",
            "babylon.stopped-source=" + token,
            "--cidfile",
            str(cidfile),
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--user",
            expected["user"],
            "--userns",
            "host",
            "--ipc",
            "private",
            "--mount",
            f"type=bind,source={run.evidence.parent / 'pgdata'},destination={storage.PGDATA},readonly",
            "--entrypoint",
            "/bin/sh",
            run.owner[6],
            "-ceu",
            HELPER_SCRIPT,
        ]
        try:
            raw = storage._exec_bytes(command)
            cid = cidfile.read_text(encoding="ascii").strip()
            if re.fullmatch("[0-9a-f]{64}", cid) is None or raw.strip() != cid.encode():
                raise Refusal("stopped helper creation CID differs")
            created = _inspect_helper(run, witness, cid, token)
            if created["status"] != "created":
                raise Refusal("stopped helper was already started")
            storage._exec_bytes(["docker", "start", cid])
            running = _inspect_helper(run, witness, cid, token)
            if running["status"] != "running":
                raise Refusal("stopped helper did not start")
            if _stopped(run, witness, fenced_stop) != before:
                raise Refusal("stopped original source changed before inventory")
            reader = ["docker", "exec", "-w", storage.PGDATA, cid]
            _reader_mounts(reader)
            members = _read_stopped(reader, witness)
            _reader_mounts(reader)
            if _inspect_helper(run, witness, cid, token) != running:
                raise Refusal("stopped helper mutated during inventory")
            if _stopped(run, witness, fenced_stop) != before:
                raise Refusal("stopped original source mutated during inventory")
            packet = {
                "version": 1,
                "pre_stop": witness_ref.model_dump(),
                "fenced_stop": fenced_stop.model_dump(),
                "source": before,
                "helper_created": created,
                "helper_running": running,
                "members": {k: asdict(v) for k, v in members.items()},
                "changes": _source_changes(witness, members),
            }
            _retained_stopped(packet, run, witness, witness_ref, fenced_stop)
        except BaseException as error:
            failure = error
            raise
        finally:
            try:
                if not cid and cidfile.is_file():
                    cid = cidfile.read_text(encoding="ascii").strip()
                if not cid:
                    candidates = storage._exec_bytes(
                        [
                            "docker",
                            "ps",
                            "-aq",
                            "--no-trunc",
                            "--filter",
                            "name=^" + expected["name"] + "$",
                            "--filter",
                            "label=babylon.stopped-source=" + token,
                        ]
                    ).splitlines()
                    if candidates:
                        if len(candidates) != 1:
                            raise Refusal("stopped helper cleanup identity is not unique")
                        cid = candidates[0].decode("ascii")
                if cid:
                    if re.fullmatch("[0-9a-f]{64}", cid) is None:
                        raise Refusal("stopped helper cleanup CID is malformed")
                    # Authenticate the exact created identity even on a confinement
                    # refusal; never remove the original or a name-selected container.
                    cleanup_record = storage._one_docker("container", cid)
                    if (
                        cleanup_record["Id"] != cid
                        or cleanup_record["Config"]["Labels"].get("babylon.stopped-source") != token
                        or cleanup_record["Name"] != expected["name"]
                    ):
                        raise Refusal("stopped helper cleanup identity differs")
                    removed = storage._exec_bytes(["docker", "container", "rm", "--force", cid])
                    if removed.strip() != cid.encode():
                        raise Refusal("stopped helper removal receipt differs")
            except BaseException as cleanup:
                if failure is not None:
                    raise BaseExceptionGroup(
                        "stopped inventory and exact helper cleanup failed", [failure, cleanup]
                    ) from None
                raise
    return backup.publish_json("stopped-source-v1.json", packet), members


def _stopped(run: Run, witness: PhysicalWitness, fenced_stop: Reference) -> dict[str, Any]:
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
        if record["State"]["Pid"] != 0:
            raise Refusal("stopped source still has a process")
        _bind_stopped_state(record["State"], _fenced_finished(run, witness, fenced_stop))
        return {
            "container": run.container,
            "image": run.owner[6],
            "daemon": created["daemon"],
            "mounts": mounts["mounts"],
            "host": witness.physical["host"],
            "state": {
                k: record["State"][k]
                for k in (
                    "Status",
                    "Running",
                    "ExitCode",
                    "OOMKilled",
                    "Pid",
                    "StartedAt",
                    "FinishedAt",
                )
            },
        }


def _require_stopped_incarnation(
    run: Run, witness: PhysicalWitness, fenced_stop: Reference, captured: dict[str, Any]
) -> None:
    if storage.canonical_json(_stopped(run, witness, fenced_stop)) != storage.canonical_json(
        captured
    ):
        raise Refusal("stopped source incarnation changed after its independent inventory")


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
    run: Run,
    backup: Evidence,
    witness: PhysicalWitness,
    witness_ref: Reference,
    fenced_stop: Reference,
) -> list[Reference]:
    stopped_ref, stopped = _stopped_inventory(run, backup, witness, witness_ref, fenced_stop)
    captured = _retained_record(backup, stopped_ref.path)["source"]
    names = ("pgdata.tar", "pgdata-second.tar")
    first: dict[str, Member] | None = None
    namespace = ""
    partials = []
    refs = [stopped_ref]
    for name in names:
        _require_stopped_incarnation(run, witness, fenced_stop, captured)
        partial = _command(
            backup,
            name + ".partial",
            ["docker", "cp", "-a", run.container + ":" + storage.PGDATA + "/.", "-"],
        )
        _require_stopped_incarnation(run, witness, fenced_stop, captured)
        with backup.file(partial.path) as stream:
            members, current = archive_manifest(stream, witness, stopped)
        _require_stopped_incarnation(run, witness, fenced_stop, captured)
        if first is not None and (first != members or current != namespace):
            raise Refusal(
                "second independent stopped archive differs from the first complete manifest"
            )
        first, namespace = members, current
        refs.append(backup.reference(partial.path + ".stderr"))
        manifest = {
            "version": 2,
            "stopped_source": stopped_ref.model_dump(),
            "archive": Reference(
                path=name, bytes=partial.bytes, sha256=partial.sha256
            ).model_dump(),
            "root_and_source": witness_ref.model_dump(),
            "numeric_id_space": current,
            "members": {key: asdict(member) for key, member in members.items()},
        }
        refs.append(backup.publish_json(name + ".manifest.json", manifest))
        partials.append(partial)
    _require_stopped_incarnation(run, witness, fenced_stop, captured)
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


def _shutdown_evidence(
    directory: Evidence,
    backup: Evidence,
    run: Run,
    physical: dict[str, Any],
    clients: tuple[Backend, ...],
    *,
    replay: bool = False,
) -> tuple[Reference, Reference, Reference, Reference]:
    attempt = directory.reference("native-fenced-stop-attempt-v1.json")
    success = directory.reference("native-fenced-stop-v1.json")
    log = directory.reference("clean-shutdown.log")
    record = strict_json_bytes(directory.read_reference(success))
    if (
        not isinstance(record, dict)
        or record.get("attempt") != attempt.model_dump()
        or record.get("log") != log.model_dump()
        or record.get("container") != run.container
        or record.get("image") != run.owner[6]
        or record.get("host") != physical["host"]
        or type(record.get("exit_code")) is not int
        or record["exit_code"] != 0
        or record.get("oom_killed") is not False
    ):
        raise Refusal(
            "fenced stop success differs from the selected container, bind or retained stop evidence"
        )
    start_record = strict_json_bytes(directory.read_reference(attempt))
    if not isinstance(start_record, dict) or (
        start_record.get("container"),
        start_record.get("image"),
    ) != (run.container, run.owner[6]):
        raise Refusal("fenced stop attempt does not identify the source image and container")
    try:
        since = datetime.fromisoformat(start_record["since"])
        fast, clean, finished = (
            datetime.fromisoformat(record[k]) for k in ("fast", "clean", "finished")
        )
    except (KeyError, TypeError, ValueError) as error:
        raise Refusal("fenced shutdown timestamp is malformed") from error
    if (
        any(stamp.tzinfo is None for stamp in (since, fast, clean, finished))
        or not since <= fast <= clean <= finished
    ):
        raise Refusal("fenced shutdown timestamps do not delimit one stop attempt")
    earliest_server_ms = since.replace(microsecond=since.microsecond // 1000 * 1000)
    exits = []
    for line in directory.read_reference(log).decode().splitlines():
        if "terminating connection due to administrator command" not in line:
            continue
        match = re.fullmatch(
            r"(\S+) (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) (?:UTC|GMT) \[([1-9]\d*)\] FATAL:\s+terminating connection due to administrator command",
            line,
        )
        if not match:
            raise Refusal("ordinary-client shutdown log differs from the observed prefix or locale")
        exits.append(
            (
                int(match[3]),
                datetime.fromisoformat(match[1]),
                datetime.fromisoformat(match[2]).replace(tzinfo=UTC),
            )
        )
    packet = {
        "stop": success.model_dump(),
        "expected": [asdict(b) for b in clients],
        "exits": [
            {"pid": pid, "docker_stamp": stamp.isoformat(), "server_stamp": server.isoformat()}
            for pid, stamp, server in exits
        ],
    }
    if replay:
        corroboration = backup.reference("fenced-client-exits.json")
        if strict_json_bytes(backup.read_reference(corroboration)) != packet:
            raise Refusal("retained held-client exits differ from the actual shutdown log")
        if (
            start_record.get("host_pid") != physical["pid"]
            or start_record.get("container_pid") != 1
            or start_record.get("stop_signal") != "SIGINT"
            or start_record.get("image_stop_signal") != "SIGINT"
            or start_record.get("host") != physical["host"]
            or start_record.get("bind")
            != {"mounts": physical["mounts"], "port_request": physical["port_request"]}
            or (start_record.get("uid"), start_record.get("gid"))
            != (physical["server_uid"], physical["server_gid"])
            or not Path(start_record["executable"]).is_absolute()
            or Path(start_record["executable"]).name != "postgres"
            or [
                e[0]
                for e in storage.shutdown_events(directory.read_reference(log), since, finished)
            ]
            != [fast, clean]
        ):
            raise Refusal(
                "retained fenced-stop attempt differs from the held physical source or ordered PID 1 shutdown"
            )
    else:
        corroboration = backup.publish_json("fenced-client-exits.json", packet)
    if (
        any(
            stamp.tzinfo is None
            or not fast <= stamp <= clean
            or not earliest_server_ms <= server <= finished
            for _, stamp, server in exits
        )
        or sorted(pid for pid, _, _ in exits) != sorted(b.pid for b in clients)
        or len(clients) != NATIVE_CLIENT_SLOTS
    ):
        raise Refusal(
            "fresh fast shutdown did not account for every held ordinary client exactly once"
        )
    return attempt, success, log, corroboration


RESTORE_FILES = frozenset(
    {
        "original-terminal.json",
        "original-probes.json",
        "verification-identity.json",
        "restored-probes.json",
        "restored-terminal.json",
        "database.dump",
        "cluster-globals.sql",
        "restore-list.txt",
        "restore.stdout",
        "database.dump.stderr",
        "cluster-globals.sql.stderr",
        "restore-list.txt.stderr",
        "restore.stdout.stderr",
    }
)
RECOVERY_FILES = RESTORE_FILES | {
    "verification-admission.json",
    "pre-checkpoint-terminal.json",
    "post-physical-terminal.json",
    "pre-checkpoint-quiescence.json",
    "pre-stop-quiescence.json",
    "pre-stop-physical.json",
    "stopped-source-v1.json",
    "fenced-client-exits.json",
    "pgdata.tar",
    "pgdata-second.tar",
    "pgdata.tar.manifest.json",
    "pgdata-second.tar.manifest.json",
    "pgdata.tar.partial.stderr",
    "pgdata-second.tar.partial.stderr",
    "retained-storage.json",
}


def _retained_record(directory: Evidence, name: str) -> Any:
    return strict_json_bytes(directory.read_reference(directory.reference(name), 512 * 1024**2))


def _verify_logical_dump(backup: Evidence, refs: dict[str, Reference], database: str) -> None:
    """Read the PG17 custom archive using a host PG17+ client in offline modes only."""
    client = shutil.which("pg_restore")
    if not client:
        raise Refusal("offline logical recovery requires PostgreSQL 17+ pg_restore on PATH")
    environment = {**os.environ, "LC_ALL": "C", "TZ": "UTC"}
    listing = backup.read_reference(refs["restore-list.txt"])
    try:
        version = subprocess.run(
            [client, "--version"], capture_output=True, check=True, timeout=10, env=environment
        ).stdout
        match = re.fullmatch(rb"pg_restore \(PostgreSQL\) ([0-9]+)\.[^\n]+\n?", version)
        if not match or int(match[1]) < 17:
            raise Refusal("offline logical recovery requires PostgreSQL 17+ pg_restore on PATH")
        with backup.file(refs["database.dump"].path) as dump, tempfile.TemporaryFile() as actual:
            subprocess.run(
                [client, "--format=custom", "--list"],
                stdin=dump,
                stdout=actual,
                stderr=subprocess.DEVNULL,
                env=environment,
                check=True,
                timeout=900,
            )
            actual.seek(0)
            if actual.read(len(listing) + 1) != listing:
                raise Refusal(
                    "retained restore listing differs from the actual PostgreSQL table of contents"
                )
            if (
                not {
                    f";     dbname: {database}".encode(),
                    b";     Format: CUSTOM",
                    b";     Dump Version: 1.16-0",
                }
                <= set(listing.splitlines())
                or not refs["cluster-globals.sql"].bytes
            ):
                raise Refusal(
                    "logical dump metadata or globals differ from the admitted PG17 database"
                )
            # Listing reads only the TOC. Rendering SQL consumes the original data blocks.
            dump.seek(0)
            subprocess.run(
                [client, "--format=custom", "--file=" + os.devnull],
                stdin=dump,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=environment,
                check=True,
                timeout=900,
            )
    except subprocess.TimeoutExpired as exc:
        raise Refusal("offline pg_restore exceeded its archive-read watchdog") from exc
    except (subprocess.CalledProcessError, OSError) as exc:
        raise Refusal("unreadable PostgreSQL custom archive or failed offline pg_restore") from exc


def _restore_clients(
    run: Run, backup: Evidence, refs: dict[str, Reference], original: dict[str, Any]
) -> tuple[Backend, ...]:
    identity = _retained_record(backup, "verification-identity.json")
    admission = _retained_record(backup, "verification-admission.json")
    closed = {**original["database"], "allows_connections": False}
    roster = identity["initial"]
    oid = identity["oid"]
    if (
        identity["name"] != run.verification
        or identity["owner"] != run.owner[8]
        or roster.get(run.database) != int(run.owner[9])
        or oid in roster.values()
        or run.verification in roster
        or admission["verification_oid"] != oid
        or admission["source_connection_limit"] != original["database"]["connection_limit"]
        or admission["creation_connection_limit"] != 0
        or original["database"]["owner"] != run.owner[8]
        or original["database"]["allows_connections"] is not True
        or admission["original_allow_connections"] is not True
        or admission["verified_final_allow_connections"] is not False
        or admission["final_shared_database"] != closed
        or admission["held_client_slots"] != NATIVE_CLIENT_SLOTS
        or admission["restore_evidence"]
        != {name: refs[name].model_dump() for name in RESTORE_FILES}
    ):
        raise Refusal("verification database, restore inputs, privileges or held slots differ")
    _verify_logical_dump(backup, refs, run.database)
    probes = _retained_record(backup, "original-probes.json")
    restored_probes = _retained_record(backup, "restored-probes.json")
    for observed in (probes, restored_probes):
        if (
            not isinstance(observed, dict)
            or set(observed) != {"reader", "observer"}
            or not all(isinstance(probe, dict) for probe in observed.values())
        ):
            raise Refusal("restricted probe evidence must include the reader and observer")
        _require_wayne_reader_revision(observed["reader"].get("allowed"), run.period)
    if probes != restored_probes:
        raise Refusal("restored restricted reader/observer evidence differs")
    for kind, probe in probes.items():
        if probe["role"] != "national_" + kind + "_" + run.owner[2][:12] or probe[
            "denied_sqlstates"
        ] != ["42501", "42501"]:
            raise Refusal("restored access did not retain actual confined roles and denied probes")
    marker = original["markers"][-1]
    if probes["observer"].get("allowed") != [run.period, marker["identity"], marker["hash"]]:
        raise Refusal("restored probe differs from the terminal marker or required Wayne grant")
    baseline = admission["baseline"]
    totals = {k: dict(v) for k, v in baseline["databases"].items()}
    if {k: t["oid"] for k, t in totals.items()} != {**roster, run.verification: oid} or totals[
        run.verification
    ]["sessions"] != 0:
        raise Refusal("verification census differs from the initial cluster")
    admin = Backend(**admission["maintenance_backend"])
    if admin.oid != roster["postgres"] or admin.role != "test":
        raise Refusal("verification observer does not name the admitted maintenance login")
    expected: list[tuple[str, str, int | None]] = [
        (purpose, run.verification, 1 if purpose in ("reader", "observer") else 0)
        for purpose in ("pg_restore", "restore-authority", "reader", "observer", "final-snapshot")
    ]
    expected.extend(
        ("final-fence", db, None)
        for db in [run.database, "template1"] + ["postgres"] * (NATIVE_CLIENT_SLOTS - 3)
    )
    held = [admin]
    seen = {admin}
    for (purpose, db, limit), row in zip(expected, admission["sessions"], strict=True):
        backend = Backend(**row["backend"])
        role = (
            "national_" + purpose + "_" + run.owner[2][:12]
            if purpose in ("reader", "observer")
            else "test"
        )
        totals[db]["sessions"] += 1
        if (
            (
                row["purpose"],
                row["database"],
                row["open_limit"],
                row["closed_limit"],
                row["expected_sessions"],
            )
            != (
                purpose,
                db,
                limit,
                None if limit is None else admission["source_connection_limit"],
                totals[db]["sessions"],
            )
            or backend.oid != totals[db]["oid"]
            or backend.role != role
            or backend in seen
            or type(backend.pid) is not int
            or backend.pid <= 0
            or not backend.started
            or (purpose == "pg_restore" and (backend.address is not None or backend.port != -1))
            or (purpose != "pg_restore" and (not backend.address or backend.port <= 0))
        ):
            raise Refusal("restore session identity, ordering or cumulative census differs")
        seen.add(backend)
        if purpose == "final-fence":
            held.append(backend)
    stats = {"postmaster": baseline["postmaster"], "databases": totals}
    if (
        admission["final_cluster_stats"] != stats
        or len({b.pid for b in held}) != NATIVE_CLIENT_SLOTS
    ):
        raise Refusal("verification lacks the complete distinct held cluster census")
    del totals[run.verification]
    ordered = [asdict(b) for b in sorted(held, key=lambda b: b.pid)]
    for name in ("pre-checkpoint-quiescence.json", "pre-stop-quiescence.json"):
        census = _retained_record(backup, name)
        if (
            census["actual_stats"] != stats
            or census["expected_stats"] != stats
            or census["expected_clients"] != ordered
            or census["observer_pid"] != admin.pid
            or census["prepared_transactions"]
            or census["entering_backends"]
            or set(census["client_logging"]) != {str(b.pid) for b in held}
            or [r["backend"] for r in census["clients"]] != ordered
        ):
            raise Refusal("held slots differ between physical observation and stop")
        for settings in census["client_logging"].values():
            _verify_stop_logging(**settings)
        for client in census["clients"]:
            observer = client["backend"]["pid"] == admin.pid
            if (
                client["backend_type"] != "client backend"
                or client["no_xid"] is not True
                or client["state"] != ("active" if observer else "idle")
                or not observer
                and (client["no_transaction"] is not True or client["no_xmin"] is not True)
            ):
                raise Refusal("retained held client was not quiescent for its admitted role")
    return tuple(held)


def verify_retained_backup(run: Run, record: dict[str, Any], original: dict[str, Any]) -> None:
    """Replay the retained restore, fenced shutdown and both offline archive witnesses."""
    evidence, backup = Evidence(run.evidence), Evidence(run.evidence.parent / "backup")
    if record.get("version") != 2 or type(record["version"]) is not int:
        raise Refusal("unsupported recovery seal version")
    references = [Reference.model_validate(row) for row in record["retained"]]
    refs = {ref.path: ref for ref in references}
    if set(refs) != RECOVERY_FILES or len(refs) != len(references):
        raise Refusal("recovery seal differs from the complete restore and physical archive roster")
    for ref in references:
        backup.verify(ref)
    source = validate_terminal(original, run.campaign, run.period)
    for name in (
        "original-terminal.json",
        "pre-checkpoint-terminal.json",
        "post-physical-terminal.json",
        "restored-terminal.json",
    ):
        retained = validate_terminal(_retained_record(backup, name), run.campaign, run.period)
        expected = source
        if name == "restored-terminal.json":
            expected = source.model_copy(
                update={
                    "database": source.database.model_copy(update={"allows_connections": False})
                }
            )
        if retained != expected:
            raise Refusal("restored or physical checkpoint state differs from the original")
    held = _restore_clients(run, backup, refs, original)
    physical = _retained_record(evidence, "physical.json")
    raw = _retained_record(backup, "pre-stop-physical.json")
    witness = PhysicalWitness(
        **{**raw, "members": {k: Member(**v) for k, v in raw["members"].items()}}
    )
    if (
        {
            k: v
            for k, v in witness.physical.items()
            if k not in ("source_checkpoint", "relation_sizes", "relation_page_occupancy", "pgss")
        }
        != physical
        or witness.database_oid != int(run.owner[9])
        or not witness.relations
        or witness.wal_magic != 0xD116
        or physical["max_connections"] != NATIVE_CLIENT_SLOTS
        or physical["max_wal_senders"] != 0
    ):
        raise Refusal("pre-stop physical witness differs from the admitted source")
    for key, ref in zip(
        ("stop_attempt", "fenced_stop", "shutdown", "held_exits"),
        _shutdown_evidence(evidence, backup, run, physical, held, replay=True),
        strict=True,
    ):
        if (
            refs["fenced-client-exits.json"].model_dump() if key == "held_exits" else record[key]
        ) != ref.model_dump():
            raise Refusal("seal substituted its canonical stop evidence")
    stopped = _retained_stopped(
        _retained_record(backup, "stopped-source-v1.json"),
        run,
        witness,
        refs["pre-stop-physical.json"],
        evidence.reference("native-fenced-stop-v1.json"),
    )
    prior = None
    for name in ("pgdata.tar", "pgdata-second.tar"):
        with backup.file(name) as stream:
            members, namespace = archive_manifest(stream, witness, stopped)
        manifest = _retained_record(backup, name + ".manifest.json")
        if (
            manifest
            != {
                "version": 2,
                "stopped_source": refs["stopped-source-v1.json"].model_dump(),
                "archive": refs[name].model_dump(),
                "root_and_source": refs["pre-stop-physical.json"].model_dump(),
                "numeric_id_space": namespace,
                "members": {k: asdict(v) for k, v in members.items()},
            }
            or prior is not None
            and prior != (members, namespace)
        ):
            raise Refusal(
                "independent offline archive differs from its source or retained manifest"
            )
        prior = (members, namespace)
    inventory = _retained_record(backup, "retained-storage.json")
    rows = inventory["backup_files_before_seal"]
    if (
        len(rows) != len(refs) - 1
        or {r["path"]: r["bytes"] for r in rows}
        != {k: v.bytes for k, v in refs.items() if k != "retained-storage.json"}
        or inventory["primary_file_bytes"]
        != sum(m.size or 0 for m in members.values() if m.kind == "file")
    ):
        raise Refusal("retained byte inventory differs from the independently archived members")


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
    with _restored_source(run, backup, functional) as held:
        logical = list(held.logical)
        physical = run.authenticate(physical_connection=held.maintenance)
        before = terminal_snapshot(held.source, campaign, period)
        logical.append(backup.publish_json("pre-checkpoint-terminal.json", before))
        if before != functional:
            raise Refusal("original terminal changed before its source checkpoint")
        logical.append(held.quiescence(backup, "pre-checkpoint"))
        witness = _physical_witness(run, physical, held.source)
        witness_ref = backup.publish_json("pre-stop-physical.json", asdict(witness))
        after = terminal_snapshot(held.source, campaign, period)
        logical.append(backup.publish_json("post-physical-terminal.json", after))
        if after != functional:
            raise Refusal("source terminal changed during physical witness acquisition")
        if run.authenticate(physical_connection=held.maintenance) != physical:
            raise Refusal("physical source identity changed during witness acquisition")
        for item in [*logical, witness_ref]:
            backup.verify(item)
        directory.verify(functional_ref)
        logical.append(held.quiescence(backup, "pre-stop"))
        storage.stop_checked(directory, run.container, fenced_image=owner[6])
        attempt, fenced_stop, shutdown, exits = _shutdown_evidence(
            directory, backup, run, physical, (held.gate.admin_backend, *held.admitted)
        )
        logical.append(exits)
    archives = _offline(run, backup, witness, witness_ref, fenced_stop)
    retained = [*logical, witness_ref, *archives]
    seal = backup.publish_json(
        "recovery-seal.json",
        {
            "version": 2,
            "completed_member": directory.reference("completed-member.json").model_dump(),
            "owner": directory.reference("ownership").model_dump(),
            "functional": functional_ref.model_dump(),
            "shutdown": shutdown.model_dump(),
            "fenced_stop": fenced_stop.model_dump(),
            "stop_attempt": attempt.model_dump(),
            "retained": [ref.model_dump() for ref in retained],
        },
    )
    for item in [*retained, seal]:
        backup.verify(item)
    directory.verify(functional_ref)
    directory.verify(shutdown)
    directory.verify(fenced_stop)
    directory.verify(attempt)
    captured = _retained_record(backup, "stopped-source-v1.json")["source"]
    _require_stopped_incarnation(run, witness, fenced_stop, captured)
    storage.remove_stopped(directory, root, run.container, owner[2], owner[6])
