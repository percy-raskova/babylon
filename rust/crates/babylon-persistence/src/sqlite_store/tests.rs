//! Contract tests for the nine-table `STRICT` campaign schema and its codecs.
//!
//! Each test pins one published boundary: the exact table set, the connection
//! pragmas, the SQL length and registry refusals, the decoded payload limits,
//! the canonical numeric encodings, and the single-writer campaign lock.

use std::fs;
use std::path::PathBuf;
use std::time::SystemTime;
use std::time::UNIX_EPOCH;

use babylon_kernel::content_digest;
use rusqlite::params;
use rusqlite::Connection;
use uuid::Uuid;

use crate::identity::CampaignId;

use super::chunks;
use super::chunks::ChunkSection;
use super::chunks::ContentEntryKind;
use super::chunks::DetailFamily;
use super::chunks::JournalKind;
use super::chunks::JournalRecordInput;
use super::chunks::JournalSubject;
use super::chunks::SubjectKind;
use super::codec;
use super::codec::PayloadBudget;
use super::codec::PayloadCodec;
use super::codec::StoredPayload;
use super::codec::MAX_CHOICE_ENDPOINT;
use super::codec::MAX_PERMANENT_JOURNAL_BYTES;
use super::codec::MAX_SERVICE_STATE_BYTES;
use super::codec::MAX_STATE_CHUNK_BYTES;
use super::codec::MONEY_BYTES;
use super::lock;
use super::lock::CampaignLock;
use super::lock::LOCK_RECORD_BYTES;
use super::schema;
use super::schema::SnapshotRole;
use super::schema::BUSY_TIMEOUT;
use super::schema::SCHEMA_VERSION;
use super::SaveError;

const NINE_TABLES: [&str; 9] = [
    "content_entry",
    "knowledge_grant",
    "permanent_journal",
    "recent_detail",
    "save_manifest",
    "service_state",
    "snapshot",
    "snapshot_chunk",
    "state_chunk",
];

struct TempRoot(PathBuf);

impl TempRoot {
    fn new() -> Self {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("the test clock is after the epoch")
            .as_nanos();
        let path = std::env::temp_dir().join(format!(
            "babylon-sqlite-store-{}-{nanos}",
            std::process::id()
        ));
        fs::create_dir_all(&path).expect("the temporary campaign root is creatable");
        Self(path)
    }

    fn path(&self, name: &str) -> PathBuf {
        self.0.join(name)
    }
}

impl Drop for TempRoot {
    fn drop(&mut self) {
        let result = fs::remove_dir_all(&self.0);
        assert!(
            result.is_ok(),
            "the temporary campaign root must be removable"
        );
    }
}

fn configured_database(root: &TempRoot) -> Connection {
    let connection =
        Connection::open(root.path("campaign.sqlite3")).expect("the campaign database file opens");
    schema::configure_connection(&connection)
        .expect("the durable pragmas apply to a fresh connection");
    schema::install_schema(&connection).expect("the nine-table STRICT schema installs");
    connection
}

fn count(connection: &Connection, table: &str) -> i64 {
    connection
        .query_row(&format!("SELECT COUNT(*) FROM {table}"), [], |row| {
            row.get(0)
        })
        .expect("the counted table exists")
}

fn insert_snapshot(connection: &Connection, snapshot_id: i64, role: i64, period: i64) {
    connection
        .execute(
            "INSERT INTO snapshot (
                snapshot_id, role, period, world_hash, state_hash, manifest_bytes,
                committed_journal_seq, committed_journal_hash, knowledge_seq, knowledge_hash
            ) VALUES (
                ?1, ?2, ?3, zeroblob(32), zeroblob(32), x'00', 0, zeroblob(32), 0, zeroblob(32)
            )",
            params![snapshot_id, role, period],
        )
        .expect("the snapshot row satisfies the durable schema");
}

fn manifest_sql(
    campaign: usize,
    build: usize,
    content: usize,
    journal: usize,
    knowledge: usize,
) -> String {
    format!(
        "INSERT INTO save_manifest (
            id, schema_version, campaign_id, build_hash, content_hash, current_snapshot_id,
            journal_tail_seq, journal_tail_hash, knowledge_tail_seq, knowledge_tail_hash
        ) VALUES (
            1, 1, zeroblob({campaign}), zeroblob({build}), zeroblob({content}), 1,
            0, zeroblob({journal}), 0, zeroblob({knowledge})
        )"
    )
}

fn insert_journal(
    connection: &Connection,
    journal_seq: i64,
    kind: i64,
    period: i64,
    nonce: Option<&[u8]>,
    record_key: Option<&[u8]>,
) {
    connection
        .execute(
            "INSERT INTO permanent_journal (
                journal_seq, kind, period, nonce, record_key, codec, raw_len,
                raw_hash, payload, previous_hash, entry_hash
            ) VALUES (
                ?1, ?2, ?3, ?4, ?5, 1, 0, zeroblob(32), x'', zeroblob(32), zeroblob(32)
            )",
            params![journal_seq, kind, period, nonce, record_key],
        )
        .expect("the journal row satisfies the durable schema");
}

#[test]
fn schema_installs_exactly_nine_strict_tables() {
    let root = TempRoot::new();
    let connection = configured_database(&root);
    schema::verify_installed_schema(&connection).expect("the installed schema is self-consistent");

    let mut statement = connection
        .prepare(
            "SELECT name, strict FROM pragma_table_list
             WHERE schema = 'main' AND type = 'table' AND name NOT LIKE 'sqlite_%'
             ORDER BY name",
        )
        .expect("the table list is queryable");
    let tables: Vec<(String, i64)> = statement
        .query_map([], |row| Ok((row.get(0)?, row.get(1)?)))
        .expect("the table list rows decode")
        .collect::<Result<_, _>>()
        .expect("every table row is readable");

    let names: Vec<&str> = tables.iter().map(|(name, _)| name.as_str()).collect();
    assert_eq!(
        names, NINE_TABLES,
        "the schema publishes exactly nine tables"
    );
    for (name, strict) in &tables {
        assert_eq!(*strict, 1, "table {name} must be declared STRICT");
    }

    let version: i64 = connection
        .query_row("PRAGMA user_version", [], |row| row.get(0))
        .expect("the schema version is readable");
    assert_eq!(version, i64::from(SCHEMA_VERSION));
}

#[test]
fn required_indexes_are_installed() {
    let root = TempRoot::new();
    let connection = configured_database(&root);

    let mut statement = connection
        .prepare(
            "SELECT name FROM sqlite_master
             WHERE type = 'index' AND name NOT LIKE 'sqlite_autoindex_%' ORDER BY name",
        )
        .expect("the index list is queryable");
    let indexes: Vec<String> = statement
        .query_map([], |row| row.get(0))
        .expect("the index names decode")
        .collect::<Result<_, _>>()
        .expect("every index name is readable");

    assert_eq!(
        indexes,
        schema::EXPECTED_INDEXES,
        "the required index set is exact"
    );
}

#[test]
fn connection_pragmas_match_the_durable_contract() {
    let root = TempRoot::new();
    let connection = configured_database(&root);

    let journal_mode: String = connection
        .query_row("PRAGMA journal_mode", [], |row| row.get(0))
        .expect("the journal mode is readable");
    assert_eq!(journal_mode, "wal", "the campaign store runs in WAL mode");

    let synchronous: i64 = connection
        .query_row("PRAGMA synchronous", [], |row| row.get(0))
        .expect("the synchronous level is readable");
    assert_eq!(synchronous, 2, "synchronous must be FULL");

    let foreign_keys: i64 = connection
        .query_row("PRAGMA foreign_keys", [], |row| row.get(0))
        .expect("the foreign-key switch is readable");
    assert_eq!(foreign_keys, 1, "foreign keys must be enforced");

    let auto_vacuum: i64 = connection
        .query_row("PRAGMA auto_vacuum", [], |row| row.get(0))
        .expect("the auto-vacuum mode is readable");
    assert_eq!(auto_vacuum, 2, "auto_vacuum must be INCREMENTAL");

    let busy_timeout: i64 = connection
        .query_row("PRAGMA busy_timeout", [], |row| row.get(0))
        .expect("the busy timeout is readable");
    assert_eq!(
        busy_timeout,
        i64::try_from(BUSY_TIMEOUT.as_millis()).expect("the timeout fits an integer"),
        "the writer serializes on the five-second busy timeout"
    );
}

#[test]
fn sql_length_checks_refuse_wrong_width_hashes_ids_and_nonces() {
    let root = TempRoot::new();
    let connection = configured_database(&root);
    insert_snapshot(&connection, 1, 1, 0);

    for (label, widths) in [
        ("campaign_id", (15, 32, 32, 32, 32)),
        ("build_hash", (16, 31, 32, 32, 32)),
        ("content_hash", (16, 32, 33, 32, 32)),
        ("journal_tail_hash", (16, 32, 32, 31, 32)),
        ("knowledge_tail_hash", (16, 32, 32, 32, 31)),
    ] {
        let (campaign, build, content, journal, knowledge) = widths;
        assert!(
            connection
                .execute(
                    &manifest_sql(campaign, build, content, journal, knowledge),
                    []
                )
                .is_err(),
            "a wrong-width {label} must be refused at the SQLite boundary"
        );
    }
    connection
        .execute(&manifest_sql(16, 32, 32, 32, 32), [])
        .expect("the correctly sized manifest row is accepted");

    let wrong_actor = "INSERT INTO permanent_journal (
        journal_seq, kind, period, actor_id, codec, raw_len, raw_hash, payload,
        previous_hash, entry_hash
    ) VALUES (1, 4, 1, zeroblob(9), 1, 0, zeroblob(32), x'', zeroblob(32), zeroblob(32))";
    assert!(
        connection.execute(wrong_actor, []).is_err(),
        "a wrong-width actor_id must be refused"
    );

    let wrong_nonce = "INSERT INTO permanent_journal (
        journal_seq, kind, period, nonce, codec, raw_len, raw_hash, payload,
        previous_hash, entry_hash
    ) VALUES (1, 1, 1, zeroblob(15), 1, 0, zeroblob(32), x'', zeroblob(32), zeroblob(32))";
    assert!(
        connection.execute(wrong_nonce, []).is_err(),
        "a wrong-width command nonce must be refused"
    );

    insert_journal(&connection, 2, 4, 1, None, None);
    let wrong_player = "INSERT INTO knowledge_grant (
        knowledge_seq, player_id, subject_kind, subject_id, grant_key, acquired_period,
        source_journal_seq, payload, previous_hash, entry_hash
    ) VALUES (1, zeroblob(7), 1, x'01', 1, 1, 2, x'', zeroblob(32), zeroblob(32))";
    assert!(
        connection.execute(wrong_player, []).is_err(),
        "a wrong-width player_id must be refused"
    );

    let wrong_chunk_hash = "INSERT INTO state_chunk (
        section, ordinal, codec, raw_len, raw_hash, payload
    ) VALUES (1, 0, 1, 0, zeroblob(31), x'')";
    assert!(
        connection.execute(wrong_chunk_hash, []).is_err(),
        "a wrong-width chunk hash must be refused"
    );

    let strict_type = "INSERT INTO recent_detail (
        period, family, ordinal, codec, raw_len, raw_hash, payload
    ) VALUES (1.5, 1, 0, 1, 0, zeroblob(32), x'')";
    assert!(
        connection.execute(strict_type, []).is_err(),
        "a STRICT table must refuse a REAL value in an INTEGER column"
    );
}

#[test]
fn closed_registry_columns_refuse_unknown_values() {
    let root = TempRoot::new();
    let connection = configured_database(&root);

    let insert_detail = "INSERT INTO recent_detail (
        period, family, ordinal, codec, raw_len, raw_hash, payload
    ) VALUES (1, ?1, 0, ?2, 0, zeroblob(32), x'')";
    for family in [0_i64, 38] {
        assert!(
            connection
                .execute(insert_detail, params![family, 1])
                .is_err(),
            "detail family {family} is outside the closed registry"
        );
    }
    for codec in [0_i64, 3] {
        assert!(
            connection
                .execute(insert_detail, params![1, codec])
                .is_err(),
            "payload codec {codec} is outside the closed registry"
        );
    }

    let insert_chunk = "INSERT INTO state_chunk (
        section, ordinal, codec, raw_len, raw_hash, payload
    ) VALUES (?1, 0, 1, 0, zeroblob(32), x'')";
    for section in [0_i64, 10] {
        assert!(
            connection.execute(insert_chunk, params![section]).is_err(),
            "chunk section {section} is outside the closed registry"
        );
    }

    let insert_snapshot_role = "INSERT INTO snapshot (
        snapshot_id, role, period, world_hash, state_hash, manifest_bytes,
        committed_journal_seq, committed_journal_hash, knowledge_seq, knowledge_hash
    ) VALUES (?1, ?2, 1, zeroblob(32), zeroblob(32), x'00', 0, zeroblob(32), 0, zeroblob(32))";
    for role in [0_i64, 4] {
        assert!(
            connection
                .execute(insert_snapshot_role, params![role, role])
                .is_err(),
            "snapshot role {role} is outside the closed registry"
        );
    }

    let insert_journal_kind = "INSERT INTO permanent_journal (
        journal_seq, kind, period, codec, raw_len, raw_hash, payload, previous_hash, entry_hash
    ) VALUES (1, ?1, 1, 1, 0, zeroblob(32), x'', zeroblob(32), zeroblob(32))";
    for kind in [0_i64, 7] {
        assert!(
            connection
                .execute(insert_journal_kind, params![kind])
                .is_err(),
            "journal kind {kind} is outside the closed registry"
        );
    }

    let insert_content_kind = "INSERT INTO content_entry (
        kind, entry_key, ordinal, codec, raw_len, raw_hash, payload
    ) VALUES (?1, x'6b', 0, 1, 0, zeroblob(32), x'')";
    for kind in [0_i64, 5] {
        assert!(
            connection
                .execute(insert_content_kind, params![kind])
                .is_err(),
            "content kind {kind} is outside the closed registry"
        );
    }

    let insert_journal_subject = "INSERT INTO permanent_journal (
        journal_seq, kind, period, subject_kind, subject_id, codec, raw_len, raw_hash,
        payload, previous_hash, entry_hash
    ) VALUES (1, 4, 1, ?1, x'01', 1, 0, zeroblob(32), x'', zeroblob(32), zeroblob(32))";
    for kind in [0_i64, 11] {
        assert!(
            connection
                .execute(insert_journal_subject, params![kind])
                .is_err(),
            "journal subject kind {kind} is outside the closed registry"
        );
    }
}

#[test]
fn snapshot_roles_limit_one_opening_one_current_and_unique_history() {
    let root = TempRoot::new();
    let connection = configured_database(&root);

    insert_snapshot(&connection, 1, 1, 0);
    assert!(
        connection
            .execute(
                "INSERT INTO snapshot (
                    snapshot_id, role, period, world_hash, state_hash, manifest_bytes,
                    committed_journal_seq, committed_journal_hash, knowledge_seq, knowledge_hash
                ) VALUES (2, 1, 0, zeroblob(32), zeroblob(32), x'00', 0, zeroblob(32), 0, zeroblob(32))",
                [],
            )
            .is_err(),
        "only one opening snapshot is admitted"
    );
    assert!(
        connection
            .execute(
                "INSERT INTO snapshot (
                    snapshot_id, role, period, world_hash, state_hash, manifest_bytes,
                    committed_journal_seq, committed_journal_hash, knowledge_seq, knowledge_hash
                ) VALUES (2, 1, 5, zeroblob(32), zeroblob(32), x'00', 0, zeroblob(32), 0, zeroblob(32))",
                [],
            )
            .is_err(),
        "the opening snapshot is period zero"
    );

    insert_snapshot(&connection, 2, 2, 12);
    assert!(
        connection
            .execute(
                "INSERT INTO snapshot (
                    snapshot_id, role, period, world_hash, state_hash, manifest_bytes,
                    committed_journal_seq, committed_journal_hash, knowledge_seq, knowledge_hash
                ) VALUES (3, 2, 13, zeroblob(32), zeroblob(32), x'00', 0, zeroblob(32), 0, zeroblob(32))",
                [],
            )
            .is_err(),
        "only one current snapshot is admitted"
    );

    insert_snapshot(&connection, 3, 3, 13);
    assert!(
        connection
            .execute(
                "INSERT INTO snapshot (
                    snapshot_id, role, period, world_hash, state_hash, manifest_bytes,
                    committed_journal_seq, committed_journal_hash, knowledge_seq, knowledge_hash
                ) VALUES (4, 3, 13, zeroblob(32), zeroblob(32), x'00', 0, zeroblob(32), 0, zeroblob(32))",
                [],
            )
            .is_err(),
        "a historical period has one checkpoint"
    );
    insert_snapshot(&connection, 4, 3, 26);

    let histories: i64 = connection
        .query_row(
            "SELECT COUNT(*) FROM snapshot WHERE role = ?1",
            params![SnapshotRole::Historical.code()],
            |row| row.get(0),
        )
        .expect("the historical roster is queryable");
    assert_eq!(histories, 2, "two distinct historical periods are retained");
}

#[test]
fn journal_identity_indexes_refuse_duplicate_nonces_periods_and_record_keys() {
    let root = TempRoot::new();
    let connection = configured_database(&root);

    insert_journal(&connection, 1, 1, 1, Some(&[0x11; 16]), None);
    assert!(
        connection
            .execute(
                "INSERT INTO permanent_journal (
                    journal_seq, kind, period, nonce, codec, raw_len, raw_hash, payload,
                    previous_hash, entry_hash
                ) VALUES (2, 2, 2, x'11111111111111111111111111111111', 1, 0, zeroblob(32),
                    x'', zeroblob(32), zeroblob(32))",
                [],
            )
            .is_err(),
        "a command nonce is unique across the campaign"
    );
    assert!(
        connection
            .execute(
                "INSERT INTO permanent_journal (
                    journal_seq, kind, period, nonce, codec, raw_len, raw_hash, payload,
                    previous_hash, entry_hash
                ) VALUES (2, 1, 1, x'22222222222222222222222222222222', 1, 0, zeroblob(32),
                    x'', zeroblob(32), zeroblob(32))",
                [],
            )
            .is_err(),
        "one accepted command targets each period"
    );

    insert_journal(&connection, 2, 6, 1, None, Some(b"dossier-key"));
    assert!(
        connection
            .execute(
                "INSERT INTO permanent_journal (
                    journal_seq, kind, period, record_key, codec, raw_len, raw_hash, payload,
                    previous_hash, entry_hash
                ) VALUES (3, 6, 2, x'646f73736965722d6b6579', 1, 0, zeroblob(32),
                    x'', zeroblob(32), zeroblob(32))",
                [],
            )
            .is_err(),
        "a record key is unique within its journal kind"
    );
    insert_journal(&connection, 3, 4, 2, None, Some(b"dossier-key"));
    insert_journal(&connection, 4, 5, 2, None, None);
    insert_journal(&connection, 5, 5, 3, None, None);

    let unresolved: i64 = connection
        .query_row(
            "SELECT COUNT(*) FROM permanent_journal WHERE kind = 1 AND resolved_period IS NULL",
            [],
            |row| row.get(0),
        )
        .expect("the unresolved command index is queryable");
    assert_eq!(unresolved, 1, "the accepted command remains unresolved");
}

#[test]
fn oversized_state_chunk_is_refused_before_insertion() {
    let root = TempRoot::new();
    let connection = configured_database(&root);

    let oversized = vec![0x5a_u8; MAX_STATE_CHUNK_BYTES + 1];
    let refused =
        chunks::write_state_chunk(&connection, ChunkSection::WorldRegisters, 0, &oversized);
    assert!(
        matches!(
            refused,
            Err(SaveError::PayloadTooLarge {
                table: "state_chunk",
                limit: MAX_STATE_CHUNK_BYTES,
                ..
            })
        ),
        "a chunk above four MiB must fail preflight: {refused:?}"
    );
    assert_eq!(
        count(&connection, "state_chunk"),
        0,
        "a refused chunk leaves no partial row"
    );

    let boundary = vec![0x5a_u8; MAX_STATE_CHUNK_BYTES];
    let chunk_id =
        chunks::write_state_chunk(&connection, ChunkSection::WorldRegisters, 0, &boundary)
            .expect("a four MiB chunk is admitted");
    assert!(chunk_id > 0, "the stored chunk carries a positive id");
    assert_eq!(
        chunks::read_state_chunk(&connection, chunk_id).expect("the stored chunk decodes"),
        boundary,
        "the stored chunk round-trips its exact decoded bytes"
    );
}

#[test]
fn oversized_content_entry_and_recent_detail_are_refused_before_insertion() {
    let root = TempRoot::new();
    let connection = configured_database(&root);
    let oversized = vec![0x6b_u8; MAX_STATE_CHUNK_BYTES + 1];

    assert!(
        chunks::write_content_entry(
            &connection,
            ContentEntryKind::CapturedSource,
            b"rules.bsl",
            0,
            &oversized,
        )
        .is_err(),
        "content chunks share the four MiB cap"
    );
    assert!(
        chunks::write_recent_detail(&connection, 1, DetailFamily::Production, 0, &oversized,)
            .is_err(),
        "recent detail shares the four MiB cap"
    );
    assert_eq!(count(&connection, "content_entry"), 0);
    assert_eq!(count(&connection, "recent_detail"), 0);

    chunks::write_content_entry(
        &connection,
        ContentEntryKind::CapturedSource,
        b"rules.bsl",
        0,
        b"literal rules",
    )
    .expect("a bounded content entry is admitted");
    chunks::write_recent_detail(&connection, 1, DetailFamily::Production, 0, b"receipt")
        .expect("a bounded detail row is admitted");
    assert_eq!(count(&connection, "content_entry"), 1);
    assert_eq!(count(&connection, "recent_detail"), 1);
}

#[test]
fn oversized_journal_record_is_refused_before_insertion() {
    let root = TempRoot::new();
    let connection = configured_database(&root);

    let oversized = vec![0x7c_u8; MAX_PERMANENT_JOURNAL_BYTES + 1];
    let refused = chunks::write_journal_record(
        &connection,
        &JournalRecordInput {
            journal_seq: 1,
            kind: JournalKind::PeriodSummary,
            period: 1,
            actor_id: None,
            subject: None,
            nonce: None,
            record_key: None,
            payload: &oversized,
            previous_hash: [0; 32],
            entry_hash: [0; 32],
        },
    );
    assert!(
        matches!(
            refused,
            Err(SaveError::PayloadTooLarge {
                table: "permanent_journal",
                limit: MAX_PERMANENT_JOURNAL_BYTES,
                ..
            })
        ),
        "a journal record above sixteen MiB must fail preflight: {refused:?}"
    );
    assert_eq!(
        count(&connection, "permanent_journal"),
        0,
        "a refused journal record leaves no partial row"
    );

    let boundary = vec![0x7c_u8; MAX_PERMANENT_JOURNAL_BYTES];
    chunks::write_journal_record(
        &connection,
        &JournalRecordInput {
            journal_seq: 1,
            kind: JournalKind::PeriodSummary,
            period: 1,
            actor_id: None,
            subject: None,
            nonce: None,
            record_key: None,
            payload: &boundary,
            previous_hash: [0; 32],
            entry_hash: [0; 32],
        },
    )
    .expect("a sixteen MiB journal record is admitted");
    assert_eq!(count(&connection, "permanent_journal"), 1);
}

#[test]
fn oversized_service_state_is_refused_before_insertion() {
    let root = TempRoot::new();
    let connection = configured_database(&root);

    let oversized = vec![0x8d_u8; MAX_SERVICE_STATE_BYTES + 1];
    let refused = chunks::write_service_state(&connection, 0, &oversized);
    assert!(
        matches!(
            refused,
            Err(SaveError::PayloadTooLarge {
                table: "service_state",
                limit: MAX_SERVICE_STATE_BYTES,
                ..
            })
        ),
        "a service record above one MiB must fail preflight: {refused:?}"
    );
    assert_eq!(count(&connection, "service_state"), 0);

    let boundary = vec![0x8d_u8; MAX_SERVICE_STATE_BYTES];
    chunks::write_service_state(&connection, 0, &boundary)
        .expect("a one MiB service record is admitted");
    chunks::write_service_state(&connection, 1, b"navigation cursor")
        .expect("the service record advances");
    assert_eq!(
        count(&connection, "service_state"),
        1,
        "the service record is one mutable singleton"
    );
    let sequence: i64 = connection
        .query_row(
            "SELECT service_seq FROM service_state WHERE id = 1",
            [],
            |row| row.get(0),
        )
        .expect("the service sequence is readable");
    assert_eq!(sequence, 1);
}

#[test]
fn journal_subject_pairing_is_refused_at_the_sqlite_boundary() {
    let root = TempRoot::new();
    let connection = configured_database(&root);
    let paired = chunks::write_journal_record(
        &connection,
        &JournalRecordInput {
            journal_seq: 1,
            kind: JournalKind::PlayerReceipt,
            period: 3,
            actor_id: Some([7; 8]),
            subject: Some(JournalSubject {
                kind: SubjectKind::County,
                id: b"26163",
            }),
            nonce: None,
            record_key: None,
            payload: b"wage receipt",
            previous_hash: [1; 32],
            entry_hash: [2; 32],
        },
    );
    paired.expect("a paired subject record is admitted");

    assert!(
        connection
            .execute(
                "INSERT INTO permanent_journal (
                    journal_seq, kind, period, subject_kind, codec, raw_len, raw_hash, payload,
                    previous_hash, entry_hash
                ) VALUES (2, 4, 3, 2, 1, 0, zeroblob(32), x'', zeroblob(32), zeroblob(32))",
                [],
            )
            .is_err(),
        "a subject kind without an identity is refused"
    );
}

#[test]
fn money_codec_is_exact_sixteen_byte_big_endian_twos_complement() {
    for value in [0_i128, 1, -1, i128::MIN, i128::MAX] {
        let encoded = codec::encode_money_i128(value);
        assert_eq!(
            encoded,
            value.to_be_bytes(),
            "money {value} uses canonical big-endian bytes"
        );
        assert_eq!(encoded.len(), MONEY_BYTES);
        assert_eq!(codec::decode_money_i128(encoded), value);
    }
}

#[test]
fn choice_endpoints_allow_two_to_the_sixty_fourth_and_refuse_beyond() {
    let boundary = codec::encode_choice_endpoint_u128(MAX_CHOICE_ENDPOINT)
        .expect("the governed upper bound is encodable");
    assert_eq!(
        codec::decode_choice_endpoint_u128(boundary).expect("the boundary decodes"),
        MAX_CHOICE_ENDPOINT
    );

    let refused = codec::encode_choice_endpoint_u128(MAX_CHOICE_ENDPOINT + 1);
    assert!(
        matches!(
            refused,
            Err(SaveError::ChoiceEndpointOutOfRange {
                endpoint
            }) if endpoint == MAX_CHOICE_ENDPOINT + 1
        ),
        "an endpoint above 2^64 is refused: {refused:?}"
    );

    let corrupt = (MAX_CHOICE_ENDPOINT + 1).to_be_bytes();
    assert!(
        matches!(
            codec::decode_choice_endpoint_u128(corrupt),
            Err(SaveError::ChoiceEndpointOutOfRange { .. })
        ),
        "a stored endpoint above 2^64 is refused on decode"
    );
}

#[test]
fn payload_codecs_round_trip_every_budget_and_refuse_tampering() {
    let raw = b"canonical decoded payload bytes".repeat(64);
    for budget in [
        PayloadBudget::ContentEntry,
        PayloadBudget::StateChunk,
        PayloadBudget::RecentDetail,
        PayloadBudget::PermanentJournal,
        PayloadBudget::ServiceState,
    ] {
        let encoded = codec::encode_payload(budget, &raw).expect("the payload fits its budget");
        assert_eq!(encoded.codec, budget.codec());
        assert_eq!(
            encoded.raw_len,
            u32::try_from(raw.len()).expect("the payload length fits u32")
        );
        assert_eq!(encoded.raw_hash, content_digest::sha256_of(&raw));

        let stored = StoredPayload {
            codec: encoded.codec,
            raw_len: encoded.raw_len,
            raw_hash: encoded.raw_hash,
            payload: &encoded.payload,
        };
        assert_eq!(
            codec::decode_payload(budget, &stored).expect("the stored payload decodes"),
            raw
        );

        let other = match encoded.codec {
            PayloadCodec::Literal => PayloadCodec::ZstdFrame,
            PayloadCodec::ZstdFrame => PayloadCodec::Literal,
        };
        assert!(
            matches!(
                codec::decode_payload(
                    budget,
                    &StoredPayload {
                        codec: other,
                        ..stored
                    }
                ),
                Err(SaveError::CodecMismatch { .. })
            ),
            "a codec outside the budget's fixed selection is refused"
        );

        assert!(
            matches!(
                codec::decode_payload(
                    budget,
                    &StoredPayload {
                        raw_len: stored.raw_len + 1,
                        ..stored
                    }
                ),
                Err(SaveError::CorruptPayload { .. })
            ),
            "a forged decoded length is refused"
        );

        assert!(
            matches!(
                codec::decode_payload(
                    budget,
                    &StoredPayload {
                        raw_hash: [0; 32],
                        ..stored
                    }
                ),
                Err(SaveError::CorruptPayload { .. })
            ),
            "a forged decoded hash is refused"
        );
    }

    assert_eq!(
        PayloadBudget::ServiceState.codec(),
        PayloadCodec::Literal,
        "the mutable service singleton stays literal"
    );
    assert_eq!(
        PayloadBudget::StateChunk.codec(),
        PayloadCodec::ZstdFrame,
        "immutable bulk chunks use one zstd frame"
    );
}

#[test]
fn payload_budget_preflight_refuses_oversized_decoded_bytes() {
    let root = TempRoot::new();
    let _connection = configured_database(&root);

    for (budget, limit) in [
        (PayloadBudget::StateChunk, MAX_STATE_CHUNK_BYTES),
        (PayloadBudget::PermanentJournal, MAX_PERMANENT_JOURNAL_BYTES),
        (PayloadBudget::ServiceState, MAX_SERVICE_STATE_BYTES),
    ] {
        let raw = vec![0_u8; limit + 1];
        assert!(
            matches!(
                codec::encode_payload(budget, &raw),
                Err(SaveError::PayloadTooLarge { limit: refused, .. }) if refused == limit
            ),
            "{} refuses decoded bytes above {limit}",
            budget.table()
        );
    }
}

#[test]
fn detail_family_registry_covers_thirty_six_receipts_and_one_event_stream() {
    assert_eq!(
        DetailFamily::ALL.len(),
        37,
        "the registry has 36 receipt families plus one event chunk family"
    );
    for (index, family) in DetailFamily::ALL.iter().enumerate() {
        assert_eq!(
            family.code(),
            i64::try_from(index).expect("the registry index fits i64") + 1,
            "registry codes are dense and start at one"
        );
    }
    assert_eq!(DetailFamily::Collections.code(), 36);
    assert_eq!(DetailFamily::EventChunk.code(), 37);
}

#[test]
fn second_writer_on_the_same_campaign_refuses_with_owner_identity() {
    let root = TempRoot::new();
    let database = root.path("campaign.sqlite3");
    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x354));

    let first = CampaignLock::acquire(&database, campaign).expect("the first owner takes the lock");
    assert!(
        lock::lock_path(&database).exists(),
        "the owner publishes a lock record beside the campaign file"
    );
    let record = fs::read(lock::lock_path(&database)).expect("the owner record is readable");
    assert_eq!(
        record.len(),
        LOCK_RECORD_BYTES,
        "the owner record has its published width"
    );
    assert_eq!(
        &record[..4],
        &std::process::id().to_be_bytes(),
        "the owner record carries the owning process id"
    );
    assert_eq!(
        &record[4..],
        campaign.canonical_bytes(),
        "the owner record carries the campaign identity"
    );

    let refused = CampaignLock::acquire(&database, campaign);
    match refused {
        Err(SaveError::CampaignLocked {
            owner_pid,
            campaign_id,
        }) => {
            assert_eq!(owner_pid, std::process::id());
            assert_eq!(campaign_id, campaign);
        }
        other => panic!("a second writer must refuse with the owner identity: {other:?}"),
    }

    drop(first);
    assert!(
        !lock::lock_path(&database).exists(),
        "the task-scoped lock record is removed on release"
    );
    let reacquired =
        CampaignLock::acquire(&database, campaign).expect("the released campaign reopens");
    drop(reacquired);
}

#[test]
fn malformed_lock_record_is_reported_not_silently_replaced() {
    let root = TempRoot::new();
    let database = root.path("campaign.sqlite3");
    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x355));
    fs::write(lock::lock_path(&database), b"short").expect("the malformed lock record is writable");

    let refused = CampaignLock::acquire(&database, campaign);
    assert!(
        matches!(refused, Err(SaveError::LockRecordInvalid { .. })),
        "a malformed lock record is reported: {refused:?}"
    );

    fs::remove_file(lock::lock_path(&database)).expect("the malformed lock record is removable");
    CampaignLock::acquire(&database, campaign).expect("the campaign locks after cleanup");
}

#[test]
fn no_column_stores_real_values() {
    let root = TempRoot::new();
    let connection = configured_database(&root);

    for table in NINE_TABLES {
        let mut statement = connection
            .prepare(&format!("PRAGMA table_info({table})"))
            .expect("the column list is queryable");
        let columns: Vec<(String, String)> = statement
            .query_map([], |row| Ok((row.get(1)?, row.get(2)?)))
            .expect("the column rows decode")
            .collect::<Result<_, _>>()
            .expect("every column row is readable");
        assert!(!columns.is_empty(), "table {table} publishes its columns");
        for (name, declared) in columns {
            assert_ne!(
                declared.to_uppercase(),
                "REAL",
                "{table}.{name} cannot store a binary64 value"
            );
            assert!(
                declared.eq_ignore_ascii_case("INTEGER") || declared.eq_ignore_ascii_case("BLOB"),
                "{table}.{name} uses a durable integer or blob type, not {declared}"
            );
        }
    }
}

#[test]
fn sql_decoded_length_checks_refuse_oversized_claims() {
    let root = TempRoot::new();
    let connection = configured_database(&root);

    for (table, sql) in [
        (
            "content_entry",
            "INSERT INTO content_entry (kind, entry_key, ordinal, codec, raw_len, raw_hash, payload)
             VALUES (1, x'6b', 0, 1, 4194305, zeroblob(32), x'')",
        ),
        (
            "state_chunk",
            "INSERT INTO state_chunk (section, ordinal, codec, raw_len, raw_hash, payload)
             VALUES (1, 0, 1, 4194305, zeroblob(32), x'')",
        ),
        (
            "recent_detail",
            "INSERT INTO recent_detail (period, family, ordinal, codec, raw_len, raw_hash, payload)
             VALUES (1, 1, 0, 1, 4194305, zeroblob(32), x'')",
        ),
        (
            "permanent_journal",
            "INSERT INTO permanent_journal (
                journal_seq, kind, period, codec, raw_len, raw_hash, payload,
                previous_hash, entry_hash
             ) VALUES (1, 5, 1, 1, 16777217, zeroblob(32), x'', zeroblob(32), zeroblob(32))",
        ),
        (
            "service_state",
            "INSERT INTO service_state (id, service_seq, codec, raw_len, raw_hash, payload)
             VALUES (1, 0, 1, 1048577, zeroblob(32), x'')",
        ),
    ] {
        assert!(
            connection.execute(sql, []).is_err(),
            "{table} must refuse a decoded length above its published cap"
        );
    }
}

#[test]
fn read_state_chunk_refuses_tampered_stored_bytes() {
    let root = TempRoot::new();
    let connection = configured_database(&root);
    let chunk_id =
        chunks::write_state_chunk(&connection, ChunkSection::StableGraph, 0, b"stable graph")
            .expect("the chunk is admitted");

    connection
        .execute(
            "UPDATE state_chunk SET payload = x'00' WHERE chunk_id = ?1",
            params![chunk_id],
        )
        .expect("the stored payload is writable for the tamper probe");
    assert!(
        matches!(
            chunks::read_state_chunk(&connection, chunk_id),
            Err(SaveError::CorruptPayload { .. })
        ),
        "a tampered stored payload is refused on decode"
    );

    chunks::write_state_chunk(&connection, ChunkSection::StableGraph, 0, b"stable graph")
        .expect("the next chunk is admitted");
    connection
        .execute(
            "UPDATE state_chunk SET raw_hash = zeroblob(32) WHERE chunk_id = ?1",
            params![chunk_id],
        )
        .expect("the stored hash is writable for the tamper probe");
    assert!(
        matches!(
            chunks::read_state_chunk(&connection, chunk_id),
            Err(SaveError::CorruptPayload { .. })
        ),
        "a tampered stored hash is refused on decode"
    );

    assert!(
        connection
            .execute(
                "UPDATE state_chunk SET codec = 9 WHERE chunk_id = ?1",
                params![chunk_id],
            )
            .is_err(),
        "the SQL registry refuses a codec outside the closed set"
    );
    assert!(
        matches!(
            PayloadCodec::from_code(9),
            Err(SaveError::UnsupportedCodec { codec: 9 })
        ),
        "the reader refuses a codec outside the closed set"
    );
}

#[test]
fn empty_content_entry_key_is_refused_before_insertion() {
    let root = TempRoot::new();
    let connection = configured_database(&root);

    assert!(
        matches!(
            chunks::write_content_entry(
                &connection,
                ContentEntryKind::CapturedSource,
                b"",
                0,
                b"rules",
            ),
            Err(SaveError::InvalidField {
                field: "entry_key",
                ..
            })
        ),
        "an empty content key is refused"
    );
    assert_eq!(count(&connection, "content_entry"), 0);
}

#[test]
fn closed_registry_codes_are_dense_and_single_valued() {
    assert_eq!(
        [
            SnapshotRole::Opening.code(),
            SnapshotRole::Current.code(),
            SnapshotRole::Historical.code(),
        ],
        [1, 2, 3]
    );
    assert_eq!(
        [
            ChunkSection::StableGraph.code(),
            ChunkSection::WorldRegisters.code(),
            ChunkSection::ResolverManifest.code(),
            ChunkSection::PreparedEnvironment.code(),
            ChunkSection::ReplaySessionIdentity.code(),
            ChunkSection::RngSeed.code(),
            ChunkSection::ContentDigest.code(),
            ChunkSection::ReferenceDigest.code(),
            ChunkSection::SemanticState.code(),
        ],
        [1, 2, 3, 4, 5, 6, 7, 8, 9]
    );
    assert_eq!(
        [
            ContentEntryKind::CapturedSource.code(),
            ContentEntryKind::CompiledDefinitions.code(),
            ContentEntryKind::Provenance.code(),
            ContentEntryKind::OpeningMetadata.code(),
        ],
        [1, 2, 3, 4]
    );
    assert_eq!(
        [
            JournalKind::AcceptedCommand.code(),
            JournalKind::ResolvedBatch.code(),
            JournalKind::GovernedChoice.code(),
            JournalKind::PlayerReceipt.code(),
            JournalKind::PeriodSummary.code(),
            JournalKind::Dossier.code(),
        ],
        [1, 2, 3, 4, 5, 6]
    );
    assert_eq!(
        [
            SubjectKind::Player.code(),
            SubjectKind::County.code(),
            SubjectKind::Place.code(),
            SubjectKind::Workplace.code(),
            SubjectKind::Organization.code(),
            SubjectKind::Product.code(),
            SubjectKind::Agreement.code(),
            SubjectKind::Shipment.code(),
            SubjectKind::Commitment.code(),
            SubjectKind::Observation.code(),
        ],
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    );
    assert_eq!(
        [PayloadCodec::Literal.code(), PayloadCodec::ZstdFrame.code()],
        [1, 2]
    );
}

#[test]
fn installed_schema_refuses_reinstallation_and_a_dropped_index() {
    let root = TempRoot::new();
    let connection = configured_database(&root);

    assert!(
        matches!(
            schema::install_schema(&connection),
            Err(SaveError::SchemaMismatch {
                reason: "the schema is already installed"
            })
        ),
        "the installer never overwrites an installed campaign schema"
    );

    connection
        .execute_batch("DROP INDEX snapshot_single_opening")
        .expect("the index is droppable for the corruption probe");
    assert!(
        matches!(
            schema::verify_installed_schema(&connection),
            Err(SaveError::SchemaMismatch {
                reason: "the required index set is not exact"
            })
        ),
        "open verification refuses a missing required index"
    );
}
