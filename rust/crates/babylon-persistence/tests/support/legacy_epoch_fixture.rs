//! Shared bounded builder for the frozen Python `PostgreSQL` estate used by epoch tests.

use postgres::config::Host;
use postgres::{Config, NoTls};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

#[allow(
    dead_code,
    reason = "used by the external H3 parity test, not the lib-test copy"
)]
const LIVE_TASK_SECONDS: &str = "45s";
const LEGACY_SCHEMA_DDL: &[u8] = include_bytes!("../fixtures/legacy_schema_ddl_v1.bin");
const LEGACY_MIGRATIONS: &[u8] = include_bytes!("../fixtures/legacy_migrations_0010_0044_v1.bin");
const LEGACY_SCHEMA_CHUNKS: usize = 112;
const LEGACY_MIGRATION_CHUNKS: usize = 35;
const LEGACY_SCHEMA_DIGEST: &str =
    "0902471053ab7a22cdaf0340978712772990e87a63aaaa1636608894fa52590b";
const LEGACY_MIGRATION_DIGEST: &str =
    "4abe69ddc25569d5dff1941b4fbe2973df5cbd70a9bca4c92b9fe26f51dd45db";
const MAX_MANIFEST_BYTES: usize = 1_048_576;
#[allow(
    dead_code,
    reason = "used by the external legacy adopter live test, not the lib-test copy"
)]
const PARTIAL_DAMAGE_SCHEMA_CHUNKS: usize = 8;

pub(crate) fn build_frozen_python_estate(config: &Config) {
    let mut client = config.connect(NoTls).expect("frozen estate connection");
    client
        .query_one(
            "SELECT pg_catalog.pg_advisory_lock($1)",
            &[&0xBAB1_0537_i64],
        )
        .expect("frozen estate advisory lock");
    apply_manifest(
        &mut client,
        LEGACY_SCHEMA_DDL,
        LEGACY_SCHEMA_CHUNKS,
        LEGACY_SCHEMA_DIGEST,
        "POSTGRES_SCHEMA_DDL",
    );
    apply_manifest(
        &mut client,
        LEGACY_MIGRATIONS,
        LEGACY_MIGRATION_CHUNKS,
        LEGACY_MIGRATION_DIGEST,
        "migrations-0010-0044",
    );
    let released: bool = client
        .query_one(
            "SELECT pg_catalog.pg_advisory_unlock($1)",
            &[&0xBAB1_0537_i64],
        )
        .expect("frozen estate advisory unlock")
        .try_get(0)
        .expect("frozen estate unlock result");
    assert!(released, "frozen estate advisory lock must be released");
}

#[allow(
    dead_code,
    reason = "used by the external legacy adopter live test, not the lib-test copy"
)]
pub(crate) fn damage_frozen_python_estate_before_stamp(config: &Config) {
    let mut client = config.connect(NoTls).expect("damaged estate connection");
    let chunks = checked_manifest_chunks(
        LEGACY_SCHEMA_DDL,
        LEGACY_SCHEMA_CHUNKS,
        "POSTGRES_SCHEMA_DDL",
    );
    for (index, chunk) in chunks.iter().take(PARTIAL_DAMAGE_SCHEMA_CHUNKS).enumerate() {
        let sql = std::str::from_utf8(chunk)
            .unwrap_or_else(|_| panic!("POSTGRES_SCHEMA_DDL chunk {} must be UTF-8", index + 1));
        client.batch_execute(sql).unwrap_or_else(|error| {
            panic!(
                "POSTGRES_SCHEMA_DDL partial chunk {} must apply: {error}",
                index + 1
            )
        });
    }
    let stamp: Option<String> = client
        .query_one(
            "SELECT pg_catalog.to_regclass('public._babylon_schema_stamp')::pg_catalog.text",
            &[],
        )
        .expect("partial estate stamp probe")
        .try_get(0)
        .expect("partial estate stamp result");
    assert!(stamp.is_none(), "partial estate must remain unstamped");
}

fn apply_manifest(
    client: &mut postgres::Client,
    framed: &[u8],
    expected_chunks: usize,
    digest: &str,
    label: &str,
) {
    let chunks = checked_manifest_chunks(framed, expected_chunks, label);
    for (index, chunk) in chunks.iter().enumerate() {
        let sql = std::str::from_utf8(chunk)
            .unwrap_or_else(|_| panic!("{label} chunk {} must be UTF-8", index + 1));
        client
            .batch_execute(sql)
            .unwrap_or_else(|error| panic!("{label} chunk {} must apply: {error}", index + 1));
    }
    client
        .batch_execute(
            "CREATE TABLE IF NOT EXISTS public._babylon_schema_stamp (\
                 digest VARCHAR(64) PRIMARY KEY, \
                 applied_at TIMESTAMPTZ NOT NULL DEFAULT pg_catalog.now()\
             )",
        )
        .expect("legacy stamp table");
    client
        .execute(
            "INSERT INTO public._babylon_schema_stamp (digest) VALUES ($1) \
             ON CONFLICT (digest) DO UPDATE SET applied_at = pg_catalog.now()",
            &[&digest],
        )
        .expect("legacy manifest stamp");
}

fn checked_manifest_chunks<'a>(
    framed: &'a [u8],
    expected_chunks: usize,
    label: &str,
) -> Vec<&'a [u8]> {
    assert!(!framed.is_empty(), "{label} fixture must be nonempty");
    assert!(
        framed.len() <= MAX_MANIFEST_BYTES,
        "{label} fixture exceeds its byte bound"
    );
    assert_eq!(
        framed.last(),
        Some(&0),
        "{label} fixture must be NUL framed"
    );
    let chunks = framed[..framed.len() - 1]
        .split(|byte| *byte == 0)
        .take(expected_chunks + 1)
        .collect::<Vec<_>>();
    assert_eq!(chunks.len(), expected_chunks, "{label} chunk count");
    chunks
}

#[allow(
    dead_code,
    reason = "used by the external H3 parity test, not the lib-test copy"
)]
pub(crate) fn execute_h3_reader_parity_v1(config: &Config) {
    run_python_child(
        config,
        READER_PARITY_SCRIPT,
        "epoch-seven H3 reader parity executor",
    );
}

#[allow(
    dead_code,
    reason = "used by the external H3 parity test, not the lib-test copy"
)]
fn run_python_child(config: &Config, script: &str, description: &str) {
    let status = Command::new("timeout")
        .args([
            "--signal=TERM",
            "--kill-after=5s",
            LIVE_TASK_SECONDS,
            "uv",
            "run",
            "python",
            "-c",
            script,
        ])
        .current_dir(repository_root())
        .env("PER20_BUILD_DSN", config_dsn(config))
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .unwrap_or_else(|error| panic!("{description} must launch: {error}"));
    assert!(
        status.success(),
        "{description} must complete within its bound"
    );
}

#[allow(
    dead_code,
    reason = "used by the external H3 parity test, not the lib-test copy"
)]
fn config_dsn(config: &Config) -> String {
    let host = match config.get_hosts().first() {
        Some(Host::Tcp(host)) => host.as_str(),
        _ => panic!("frozen Python estate builder requires one TCP host"),
    };
    let port = config.get_ports().first().copied().unwrap_or(5432);
    let user = config.get_user().expect("test config user");
    let password = std::str::from_utf8(config.get_password().expect("test config password"))
        .expect("test password must be UTF-8");
    let dbname = config.get_dbname().expect("test config database");
    format!("host={host} port={port} dbname={dbname} user={user} password={password}")
}

#[allow(
    dead_code,
    reason = "used by the external H3 parity test, not the lib-test copy"
)]
fn repository_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../..")
        .canonicalize()
        .expect("repository root must resolve")
}

#[allow(
    dead_code,
    reason = "used by the external H3 parity test, not the lib-test copy"
)]
const READER_PARITY_SCRIPT: &str = r#"
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

import psycopg
import pyarrow as pa
import pyarrow.parquet as pq
from psycopg.rows import dict_row

from tools.execute_h3_reader_parity_v1 import execute_h3_reader_parity_v1
from tools.verify_h3_reader_cutover_v1 import (
    load_reader_cutover_contract,
    load_reader_parity_vectors,
)

SESSION_ID = UUID("27900000-0000-0000-0000-000000000001")
ARCHIVE_RELATIONS = (
    "dynamic_hex_state",
    "hex_spatial_map",
    "hex_state",
    "hex_terrain_state",
    "immutable_reference_lodes_od_matrix",
    "infrastructure_link_state",
)
EXPECTED_OPERATIONS = (
    "sparse_fill_forward",
    "value_aggregates",
    "runtime_trace",
    "session_partition_isolation",
    "r8_parent_reference_identity",
    "nullable_locations",
    "tagged_destinations",
    "stable_pagination",
    "archive_round_trip",
)


def export_epoch7_reader_fixture(dsn, archive_directory):
    tables = {}
    reference = {}
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        for relation in ARCHIVE_RELATIONS:
            count = connection.execute(
                f"SELECT count(*) AS rows FROM public.{relation} WHERE session_id = %s",
                (SESSION_ID,),
            ).fetchone()["rows"]
            if relation.startswith("immutable_reference_"):
                reference[relation] = count
            else:
                tables[relation] = {"rows": count}
        rows = connection.execute(
            "SELECT session_id::text AS session_id, tick, cell_id "
            "FROM public.dynamic_hex_state WHERE session_id = %s "
            "ORDER BY tick, cell_id",
            (SESSION_ID,),
        ).fetchall()
    pq.write_table(pa.Table.from_pylist([dict(row) for row in rows]), archive_directory / "dynamic_hex_state.parquet")
    manifest = {
        "schema_version": "epoch7-test-v1",
        "session_id": str(SESSION_ID),
        "tables": tables,
        "reference_tables_purge_only": reference,
    }
    (archive_directory / "archive_manifest.json").write_text(json.dumps(manifest))
    return manifest


def query_epoch7_reader_fixture(archive_directory):
    rows = pq.read_table(archive_directory / "dynamic_hex_state.parquet").to_pylist()
    return [
        {"session_id": row["session_id"], "tick": row["tick"], "cell_id": row["cell_id"]}
        for row in rows
        if row["tick"] == 0
    ]


class PostgreSQLReaderParityBackendV1:
    def __init__(self, dsn, archive_directory, manifest):
        self._dsn = dsn
        self._archive_directory = archive_directory
        self._manifest = manifest
        self.calls = []

    def _query(self, statement, parameters):
        with psycopg.connect(
            self._dsn,
            options="-c default_transaction_read_only=on",
            row_factory=dict_row,
        ) as connection:
            read_only = connection.execute("SHOW transaction_read_only").fetchone()
            if read_only is None or read_only["transaction_read_only"] != "on":
                raise AssertionError("reader parity connection must be read-only")
            return [dict(row) for row in connection.execute(statement, parameters).fetchall()]

    def execute_reader_case(self, operation, decoded_inputs):
        if operation in self.calls:
            raise AssertionError(f"reader parity operation repeated: {operation}")
        self.calls.append(operation)
        if operation == "sparse_fill_forward":
            session_id = decoded_inputs["session_id"]
            target_tick = decoded_inputs["target_tick"]
            asof_rows = self._query(
                """
                SELECT tick, cell_id, c, written_at_tick
                FROM public.v_hex_state_asof
                WHERE session_id = %s AND tick = %s
                ORDER BY written_at_tick, cell_id
                """,
                (session_id, target_tick),
            )
            composition_rows = self._query(
                """
                SELECT cell_id, view_name AS view
                FROM (
                    SELECT cell_id, 'v_hex_aid'::text AS view_name
                    FROM public.v_hex_aid WHERE game_id = %s AND tick = %s
                    UNION ALL
                    SELECT cell_id, 'v_hex_economic'::text AS view_name
                    FROM public.v_hex_economic WHERE game_id = %s AND tick = %s
                    UNION ALL
                    SELECT cell_id, 'v_hex_heat'::text AS view_name
                    FROM public.v_hex_heat WHERE game_id = %s AND tick = %s
                    UNION ALL
                    SELECT cell_id, 'v_hex_intel'::text AS view_name
                    FROM public.v_hex_intel WHERE game_id = %s AND tick = %s
                    UNION ALL
                    SELECT cell_id, 'v_hex_mobilize'::text AS view_name
                    FROM public.v_hex_mobilize WHERE game_id = %s AND tick = %s
                ) AS composition
                ORDER BY view_name COLLATE "C", cell_id
                """,
                (
                    session_id,
                    target_tick,
                    session_id,
                    target_tick,
                    session_id,
                    target_tick,
                    session_id,
                    target_tick,
                    session_id,
                    target_tick,
                ),
            )
            return {"asof_rows": asof_rows, "composition_rows": composition_rows}
        if operation == "value_aggregates":
            session_id = decoded_inputs["session_id"]
            target_tick = decoded_inputs["target_tick"]
            county_rows = self._query(
                """
                SELECT tick, county_fips, c_sum, hex_count
                FROM public.v_county_value_aggregate
                WHERE session_id = %s AND tick = %s
                ORDER BY county_fips COLLATE "C"
                """,
                (session_id, target_tick),
            )
            state_rows = self._query(
                """
                SELECT tick, state_fips, c_sum, hex_count
                FROM public.v_state_value_aggregate
                WHERE session_id = %s AND tick = %s
                ORDER BY state_fips COLLATE "C"
                """,
                (session_id, target_tick),
            )
            national_rows = self._query(
                """
                SELECT tick, national_id, c_sum, hex_count
                FROM public.v_national_value_aggregate
                WHERE session_id = %s AND tick = %s
                ORDER BY national_id COLLATE "C"
                """,
                (session_id, target_tick),
            )
            return {
                "county_rows": county_rows,
                "national_rows": national_rows,
                "state_rows": state_rows,
            }
        if operation == "runtime_trace":
            return {
                "trace_rows": self._query(
                    """
                    SELECT tick, entity_id, entity_kind, c, profit_rate
                    FROM public.view_runtime_trace_emission
                    WHERE session_id = %s AND tick = %s
                    ORDER BY entity_kind COLLATE "C", entity_id COLLATE "C"
                    """,
                    (decoded_inputs["session_id"], decoded_inputs["target_tick"]),
                )
            }
        if operation == "session_partition_isolation":
            return {
                "isolation_counts": self._query(
                    """
                    SELECT
                        (SELECT count(*) FROM public.dynamic_hex_state
                         WHERE session_id = %s) AS session_rows,
                        (SELECT count(*)
                         FROM public.dynamic_hex_state_p_27900000000000000000000000000001
                         WHERE session_id = %s) AS owned_partition_rows,
                        (SELECT count(*) FROM public.dynamic_hex_state
                         WHERE session_id = %s) AS other_session_rows,
                        NOT EXISTS (
                            SELECT 1 FROM public.dynamic_hex_state WHERE session_id = %s
                        ) AS foreign_rows_absent,
                        (SELECT count(*) FROM public.dynamic_hex_state_default
                         WHERE session_id = %s) AS default_partition_rows
                    """,
                    (
                        decoded_inputs["session_id"],
                        decoded_inputs["session_id"],
                        decoded_inputs["other_session_id"],
                        decoded_inputs["other_session_id"],
                        decoded_inputs["session_id"],
                    ),
                )
            }
        if operation == "r8_parent_reference_identity":
            return {
                "parent_rows": self._query(
                    """
                    SELECT cell_id, parent_cell_id
                    FROM public.hex_r8_reference
                    WHERE parent_cell_id = %s
                    ORDER BY cell_id
                    """,
                    (decoded_inputs["parent_cell_id"],),
                )
            }
        if operation == "nullable_locations":
            session_id = decoded_inputs["session_id"]
            organization_rows = self._query(
                """
                SELECT home_cell_id, org_id
                FROM public.org_snapshot
                WHERE game_id = %s
                ORDER BY org_id COLLATE "C"
                """,
                (session_id,),
            )
            event_rows = self._query(
                """
                SELECT cell_id, event_type
                FROM public.tick_event
                WHERE game_id = %s
                ORDER BY event_type COLLATE "C", event_id
                """,
                (session_id,),
            )
            return {"event_rows": event_rows, "organization_rows": organization_rows}
        if operation == "tagged_destinations":
            return {
                "commute_rows": self._query(
                    """
                    SELECT home_cell_id, s000_workers, workplace_cell_id,
                           CASE WHEN workplace_dest_kind = 'external'
                                THEN workplace_dest ELSE NULL END AS workplace_dest,
                           workplace_dest_kind
                    FROM public.immutable_reference_lodes_od_matrix
                    WHERE session_id = %s AND year = %s
                    ORDER BY home_cell_id,
                             CASE workplace_dest_kind WHEN 'hex' THEN 0 ELSE 1 END,
                             workplace_cell_id NULLS LAST,
                             workplace_dest COLLATE "C" NULLS FIRST
                    """,
                    (decoded_inputs["session_id"], decoded_inputs["year"]),
                )
            }
        if operation == "stable_pagination":
            session_id = decoded_inputs["session_id"]
            page_size = decoded_inputs["page_size"]
            page_one = self._query(
                """
                SELECT cell_id FROM public.hex_map
                WHERE game_id = %s
                ORDER BY cell_id
                LIMIT %s
                """,
                (session_id, page_size),
            )
            page_two = self._query(
                """
                SELECT cell_id FROM public.hex_map
                WHERE game_id = %s
                ORDER BY cell_id
                LIMIT %s OFFSET %s
                """,
                (session_id, page_size, page_size),
            )
            return {"page_one": page_one, "page_two": page_two}
        if operation == "archive_round_trip":
            if decoded_inputs["session_id"] != SESSION_ID:
                raise AssertionError("archive fixture session differs from the governed input")
            export_counts = [
                {
                    "relation": relation,
                    "rows": (
                        self._manifest["reference_tables_purge_only"][relation]
                        if relation.startswith("immutable_reference_")
                        else self._manifest["tables"][relation]["rows"]
                    ),
                }
                for relation in ARCHIVE_RELATIONS
            ]
            query_rows = query_epoch7_reader_fixture(self._archive_directory)
            return {"export_counts": export_counts, "query_rows": query_rows}
        raise AssertionError(f"unknown reader parity operation: {operation}")


repository_root = Path.cwd()
dsn = os.environ["PER20_BUILD_DSN"]
contract = load_reader_cutover_contract(repository_root / "contracts/h3_reader_cutover_v1.yaml")
vectors = load_reader_parity_vectors(
    repository_root / "contracts/h3_reader_cutover_v1_vectors.jsonl"
)
with TemporaryDirectory(prefix="babylon-per280-reader-parity-") as directory:
    archive_directory = Path(directory)
    manifest = export_epoch7_reader_fixture(dsn, archive_directory)
    backend = PostgreSQLReaderParityBackendV1(dsn, archive_directory, manifest)
    findings = execute_h3_reader_parity_v1(contract, vectors, repository_root, backend)
    if findings:
        raise AssertionError(f"reader parity findings: {findings!r}")
    if tuple(backend.calls) != EXPECTED_OPERATIONS:
        raise AssertionError(f"reader parity dispatch mismatch: {backend.calls!r}")
"#;
