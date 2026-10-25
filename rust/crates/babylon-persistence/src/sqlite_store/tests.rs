//! Contract tests for the nine-table `STRICT` campaign schema and its codecs.
//!
//! Each test pins one published boundary: the exact table set, the connection
//! pragmas, the SQL length and registry refusals, the decoded payload limits,
//! the canonical numeric encodings, and the single-writer campaign lock.

use std::fs;
use std::path::Path;
use std::path::PathBuf;
use std::sync::atomic::AtomicBool;
use std::time::SystemTime;
use std::time::UNIX_EPOCH;

use babylon_kernel::content_digest;
use rusqlite::params;
use rusqlite::Connection;
use rusqlite::OpenFlags;
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
use super::export;
use super::lock;
use super::lock::CampaignLock;
use super::lock::LOCK_RECORD_BYTES;
use super::owner::AcceptanceKind;
use super::owner::AdmittedContent;
use super::owner::AdmittedContentEntry;
use super::owner::AdmittedOpening;
use super::owner::BuildIdentity;
use super::owner::CampaignHandle;
use super::owner::CommandError;
use super::owner::CommitKind;
use super::owner::CommittedPeriod;
use super::owner::CurrentRoot;
use super::owner::FaultPoint;
use super::owner::PlayerCommand;
use super::owner::PreparedDetailRow;
use super::owner::PreparedJournalRecord;
use super::owner::PreparedKnowledgeGrant;
use super::owner::PreparedPeriod;
use super::owner::PreparedSubject;
use super::owner::SqliteCampaignStore;
use super::owner::StateChunk;
use super::replay::RecentDetailRow;
use super::replay::ReplayError;
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
        let encoded =
            codec::encode_chunk_payload(budget, &raw).expect("the payload fits its budget");
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
            codec::decode_chunk_payload(budget, &stored).expect("the stored payload decodes"),
            raw
        );

        let other = match encoded.codec {
            PayloadCodec::Literal => PayloadCodec::ZstdFrame,
            PayloadCodec::ZstdFrame => PayloadCodec::Literal,
        };
        assert!(
            matches!(
                codec::decode_chunk_payload(
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
                codec::decode_chunk_payload(
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
                codec::decode_chunk_payload(
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
                codec::encode_chunk_payload(budget, &raw),
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

// ---------------------------------------------------------------------------
// Task 6 (`P3b`): campaign lifecycle, lock recovery and `SqliteCampaignStore`.
// ---------------------------------------------------------------------------

const NONCE_ONE: [u8; 16] = [0x11; 16];
const NONCE_TWO: [u8; 16] = [0x22; 16];
const CAMPAIGN_UUID: u128 = 0x354;
const BUILD_HASH: [u8; 32] = [0x5b; 32];

fn campaign_id() -> CampaignId {
    CampaignId::from_uuid(Uuid::from_u128(CAMPAIGN_UUID))
}

fn other_campaign_id() -> CampaignId {
    CampaignId::from_uuid(Uuid::from_u128(0x999))
}

fn build_identity() -> BuildIdentity {
    BuildIdentity::from_hash(BUILD_HASH)
}

fn frame(domain: &[u8], period: u64, body: &[u8]) -> Vec<u8> {
    let mut bytes = Vec::with_capacity(domain.len() + 8 + body.len());
    bytes.extend_from_slice(domain);
    bytes.extend_from_slice(&period.to_be_bytes());
    bytes.extend_from_slice(body);
    bytes
}

fn world_identity(period: u64) -> [u8; 32] {
    content_digest::sha256_of(format!("world-identity-{period}").as_bytes())
}

fn register(period: u64) -> Vec<u8> {
    frame(
        b"babylon.test.material-state.v1\0",
        period,
        format!("register-{period}").as_bytes(),
    )
}

fn graph(period: u64) -> Vec<u8> {
    frame(
        b"babylon.test.graph.v1\0",
        period,
        format!("graph-{period}").as_bytes(),
    )
}

fn chunk(section: ChunkSection, ordinal: u32, bytes: Vec<u8>) -> StateChunk {
    StateChunk {
        section,
        ordinal,
        bytes,
    }
}

fn admitted_content() -> AdmittedContent {
    AdmittedContent {
        campaign_id: campaign_id(),
        build: build_identity(),
        entries: vec![
            AdmittedContentEntry {
                kind: ContentEntryKind::CapturedSource,
                key: b"rules.bsl".to_vec(),
                ordinal: 0,
                bytes: b"captured source rules".to_vec(),
            },
            AdmittedContentEntry {
                kind: ContentEntryKind::CompiledDefinitions,
                key: b"defines".to_vec(),
                ordinal: 0,
                bytes: b"compiled definitions".to_vec(),
            },
        ],
    }
}

fn admitted_opening() -> AdmittedOpening {
    let register_zero = register(0);
    AdmittedOpening {
        world_hash: world_identity(0),
        state_hash: content_digest::sha256_of(&register_zero),
        chunks: vec![
            chunk(ChunkSection::WorldRegisters, 0, register_zero),
            chunk(ChunkSection::StableGraph, 0, graph(0)),
        ],
    }
}

fn journal(
    kind: JournalKind,
    subject: Option<(SubjectKind, &[u8])>,
    payload: &[u8],
) -> PreparedJournalRecord {
    PreparedJournalRecord {
        kind,
        subject: subject.map(|(kind, id)| PreparedSubject {
            kind,
            id: id.to_vec(),
        }),
        record_key: None,
        payload: payload.to_vec(),
        resolves_prior_subject: false,
    }
}

fn resolving_journal(
    kind: JournalKind,
    subject: (SubjectKind, &[u8]),
    payload: &[u8],
) -> PreparedJournalRecord {
    PreparedJournalRecord {
        kind,
        subject: Some(PreparedSubject {
            kind: subject.0,
            id: subject.1.to_vec(),
        }),
        record_key: None,
        payload: payload.to_vec(),
        resolves_prior_subject: true,
    }
}

fn knowledge(
    player: u64,
    kind: SubjectKind,
    id: &[u8],
    grant_key: i64,
    payload: &[u8],
) -> PreparedKnowledgeGrant {
    PreparedKnowledgeGrant {
        player_id: player.to_be_bytes(),
        subject: PreparedSubject {
            kind,
            id: id.to_vec(),
        },
        grant_key,
        payload: payload.to_vec(),
    }
}

fn prepared(
    period: u64,
    expected_world: [u8; 32],
    chunks: Vec<StateChunk>,
    journal: Vec<PreparedJournalRecord>,
    knowledge: Vec<PreparedKnowledgeGrant>,
) -> PreparedPeriod {
    let state_hash = chunks
        .first()
        .map_or([0_u8; 32], |chunk| content_digest::sha256_of(&chunk.bytes));
    PreparedPeriod {
        period,
        expected_world_hash: expected_world,
        world_hash: world_identity(period),
        state_hash,
        chunks,
        journal,
        knowledge,
        detail: Vec::new(),
    }
}

fn state_chunk_ids(root: &CurrentRoot, section: ChunkSection) -> Vec<i64> {
    root.chunks
        .iter()
        .filter(|chunk| chunk.section == section)
        .map(|chunk| chunk.chunk_id)
        .collect()
}

fn write_lock_record(database: &Path, pid: u32, campaign: CampaignId) {
    let mut record = [0_u8; LOCK_RECORD_BYTES];
    record[..4].copy_from_slice(&pid.to_be_bytes());
    record[4..].copy_from_slice(campaign.canonical_bytes());
    fs::write(lock::lock_path(database), record).expect("the lock record is writable");
}

fn raw_connection(database: &Path) -> Connection {
    Connection::open(database).expect("the campaign database opens raw")
}

/// Return every resolution column of one subject's journal records in order.
fn subject_resolution_rows(
    database: &Path,
    kind: SubjectKind,
    id: &[u8],
) -> Vec<(u64, Option<u64>, Option<u64>)> {
    let connection = raw_connection(database);
    let mut statement = connection
        .prepare(
            "SELECT journal_seq, resolved_period, resolution_seq FROM permanent_journal
             WHERE subject_kind = ?1 AND subject_id = ?2 ORDER BY journal_seq",
        )
        .expect("the subject journal list queries");
    let rows = statement
        .query_map(params![kind.code(), id], |row| {
            Ok((
                row.get::<_, i64>(0)?,
                row.get::<_, Option<i64>>(1)?,
                row.get::<_, Option<i64>>(2)?,
            ))
        })
        .expect("the subject journal rows read");
    rows.map(|row| {
        let (seq, resolved_period, resolution_seq) = row.expect("the subject row is readable");
        (
            u64::try_from(seq).expect("a journal sequence is non-negative"),
            resolved_period.map(|value| u64::try_from(value).expect("a period is non-negative")),
            resolution_seq.map(|value| u64::try_from(value).expect("a sequence is non-negative")),
        )
    })
    .collect()
}

/// How far an interrupted `create_inner` got before its crash.
#[derive(Clone, Copy)]
enum PartialCreation {
    /// The crash landed before the schema installed, leaving an empty file.
    EmptyFile,
    /// The crash landed after the schema and before the manifest commit.
    SchemaOnly,
}

/// Reproduce the files an interrupted `create_inner` leaves behind.
fn interrupted_creation(database: &Path, partial: PartialCreation) {
    match partial {
        PartialCreation::SchemaOnly => {
            let connection = Connection::open(database).expect("the partial database file opens");
            schema::configure_connection(&connection).expect("the partial database is configured");
            schema::install_schema(&connection).expect("the partial schema installs");
            // A crash before `create_inner`'s manifest commit leaves the schema
            // and no committed root, which is exactly this state.
        }
        PartialCreation::EmptyFile => {
            fs::write(database, b"").expect("the empty partial database file is writable");
        }
    }
    write_lock_record(database, u32::MAX, campaign_id());
}

#[test]
#[allow(
    clippy::too_many_lines,
    clippy::cognitive_complexity,
    reason = "one conformance scenario asserts the whole two-period trajectory"
)]
fn two_period_identities_survive_cold_reopen_and_export() {
    let root = TempRoot::new();
    let database = root.path("campaign.sqlite3");
    let opening = admitted_opening();
    let opening_world = opening.world_hash;
    let mut handle = SqliteCampaignStore::create(&database, admitted_content(), opening)
        .expect("the campaign is created once");
    assert_eq!(
        handle.current().period,
        0,
        "a new campaign opens at period 0"
    );
    assert_eq!(handle.campaign_id(), &campaign_id());

    let accepted = handle
        .accept_command(
            PlayerCommand {
                period: 1,
                actor_id: [42; 8],
                payload: b"organizer-command-before-period-1".to_vec(),
            },
            NONCE_ONE,
        )
        .expect("the organizer command is durable before the advance");
    assert_eq!(accepted.kind, AcceptanceKind::Inserted);

    let graph_one = graph(1);
    let first_candidate = prepared(
        1,
        opening_world,
        vec![
            chunk(ChunkSection::WorldRegisters, 0, register(1)),
            chunk(ChunkSection::StableGraph, 0, graph_one.clone()),
        ],
        vec![
            journal(
                JournalKind::PlayerReceipt,
                Some((SubjectKind::County, b"26163")),
                b"county-wage-receipt",
            ),
            journal(
                JournalKind::GovernedChoice,
                Some((SubjectKind::Observation, b"choice-1")),
                b"choice-receipt-payload",
            ),
        ],
        vec![knowledge(
            42,
            SubjectKind::County,
            b"michigan-wayne",
            1,
            b"earned-county-fact",
        )],
    );
    let first = handle
        .commit(first_candidate.clone())
        .expect("period one commits with the accepted command");
    assert_eq!(first.kind, CommitKind::Inserted);
    assert_eq!(
        first.world_hash, first_candidate.world_hash,
        "the store preserves the caller's canonical world identity"
    );
    assert_eq!(
        first.state_hash, first_candidate.state_hash,
        "the store preserves the caller's canonical state identity"
    );
    let period_one_graph = state_chunk_ids(handle.current(), ChunkSection::StableGraph);

    let conflicting = prepared(
        1,
        opening_world,
        vec![
            chunk(ChunkSection::WorldRegisters, 0, register(1)),
            chunk(ChunkSection::StableGraph, 0, graph_one.clone()),
        ],
        vec![journal(
            JournalKind::GovernedChoice,
            Some((SubjectKind::Observation, b"choice-1")),
            b"different-choice-payload",
        )],
        vec![knowledge(
            42,
            SubjectKind::County,
            b"michigan-wayne",
            1,
            b"earned-county-fact",
        )],
    );
    match handle.commit(conflicting) {
        Err(SaveError::ConflictingPeriodCommit { period }) => assert_eq!(period, 1),
        other => panic!("period one must keep one immutable commitment: {other:?}"),
    }
    assert_eq!(
        handle
            .read_granted_subject(
                42_u64.to_be_bytes(),
                SubjectKind::County,
                b"michigan-wayne",
                1
            )
            .expect("period one knowledge is disclosed at period one"),
        b"earned-county-fact",
        "the earned fact is readable at its acquisition period"
    );

    let second_candidate = prepared(
        2,
        first.world_hash,
        vec![
            chunk(ChunkSection::WorldRegisters, 0, register(2)),
            chunk(ChunkSection::StableGraph, 0, graph_one),
        ],
        vec![journal(
            JournalKind::PlayerReceipt,
            None,
            b"period-two-summary",
        )],
        Vec::new(),
    );
    let second = handle
        .commit(second_candidate.clone())
        .expect("period two commits");
    assert_eq!(second.kind, CommitKind::Inserted);
    assert_eq!(
        second.chunks_reused, 1,
        "the unchanged StableGraph chunk shares its integer identity"
    );
    assert_eq!(
        second.chunks_inserted, 1,
        "the changed WorldRegisters chunk is inserted"
    );
    assert!(
        second.journal_tail_seq > first.journal_tail_seq,
        "period two extends the permanent journal"
    );
    assert_eq!(
        state_chunk_ids(handle.current(), ChunkSection::StableGraph),
        period_one_graph,
        "unchanged (section, ordinal) chunks share the preceding chunk_id"
    );
    let replayed_second = handle
        .commit(second_candidate)
        .expect("an identical period two replay is idempotent");
    assert_eq!(replayed_second.kind, CommitKind::Existing);
    assert_eq!(
        replayed_second.journal_tail_hash, second.journal_tail_hash,
        "replay must not append a second period commit"
    );
    drop(handle);

    let mut reopened =
        SqliteCampaignStore::open(&database, build_identity()).expect("the campaign cold reopens");
    assert_eq!(reopened.current().period, 2);
    assert_eq!(reopened.current().world_hash, second.world_hash);
    assert_eq!(reopened.current().state_hash, second.state_hash);
    assert_eq!(reopened.current().journal_tail_seq, second.journal_tail_seq);
    assert_eq!(
        reopened.current().journal_tail_hash,
        second.journal_tail_hash
    );
    assert_eq!(
        reopened.opened_chunk_reads(),
        u64::try_from(reopened.current().chunks.len()).expect("the chunk count fits"),
        "opening reads exactly the chunks the current snapshot reaches"
    );
    let cold_one = reopened
        .commit(prepared(
            1,
            opening_world,
            vec![
                chunk(ChunkSection::WorldRegisters, 0, register(1)),
                chunk(ChunkSection::StableGraph, 0, graph(1)),
            ],
            vec![
                journal(
                    JournalKind::PlayerReceipt,
                    Some((SubjectKind::County, b"26163")),
                    b"county-wage-receipt",
                ),
                journal(
                    JournalKind::GovernedChoice,
                    Some((SubjectKind::Observation, b"choice-1")),
                    b"choice-receipt-payload",
                ),
            ],
            vec![knowledge(
                42,
                SubjectKind::County,
                b"michigan-wayne",
                1,
                b"earned-county-fact",
            )],
        ))
        .expect("the period one identity survives a cold reopen");
    assert_eq!(cold_one.kind, CommitKind::Existing);
    assert_eq!(cold_one.world_hash, first.world_hash);
    assert_eq!(cold_one.journal_tail_hash, first.journal_tail_hash);

    let exported = root.path("exported.sqlite3");
    let report = reopened
        .export_save(&exported)
        .expect("the committed boundary exports online");
    assert!(report.integrity_verified);
    assert!(report.destination_bytes > 0);
    assert!(report.page_count > 0);
    assert_eq!(report.current_period, 2);
    assert_eq!(report.journal_tail_hash, second.journal_tail_hash);

    let exported_handle = SqliteCampaignStore::open(&exported, build_identity())
        .expect("the published export opens independently");
    assert_eq!(exported_handle.current().period, 2);
    assert_eq!(
        exported_handle.current().journal_tail_hash,
        second.journal_tail_hash,
        "the export preserves the journal tail identity"
    );
    assert_eq!(
        exported_handle
            .read_granted_subject(
                42_u64.to_be_bytes(),
                SubjectKind::County,
                b"michigan-wayne",
                2
            )
            .expect("the export preserves earned authority"),
        b"earned-county-fact"
    );
}

#[test]
#[allow(
    clippy::too_many_lines,
    reason = "one conformance scenario asserts every acceptance refusal"
)]
fn command_nonce_idempotency_and_single_commitment_refusal() {
    let root = TempRoot::new();
    let database = root.path("campaign.sqlite3");
    let mut handle = SqliteCampaignStore::create(&database, admitted_content(), admitted_opening())
        .expect("the campaign is created once");

    let first = handle
        .accept_command(
            PlayerCommand {
                period: 1,
                actor_id: [7; 8],
                payload: b"equal-command-bytes".to_vec(),
            },
            NONCE_ONE,
        )
        .expect("the first commitment is accepted");
    assert_eq!(first.kind, AcceptanceKind::Inserted);
    let replay = handle
        .accept_command(
            PlayerCommand {
                period: 1,
                actor_id: [7; 8],
                payload: b"equal-command-bytes".to_vec(),
            },
            NONCE_ONE,
        )
        .expect("the equal retry returns the original acceptance");
    assert_eq!(replay.kind, AcceptanceKind::Existing);
    assert_eq!(replay.acceptance_seq, first.acceptance_seq);
    assert_eq!(replay.payload_hash, first.payload_hash);

    assert!(
        matches!(
            handle.accept_command(
                PlayerCommand {
                    period: 1,
                    actor_id: [7; 8],
                    payload: b"different-command-bytes".to_vec(),
                },
                NONCE_ONE,
            ),
            Err(CommandError::ConflictingNonce)
        ),
        "one nonce cannot authenticate different bytes"
    );
    assert!(
        matches!(
            handle.accept_command(
                PlayerCommand {
                    period: 1,
                    actor_id: [7; 8],
                    payload: b"equal-command-bytes".to_vec(),
                },
                NONCE_TWO,
            ),
            Err(CommandError::PeriodCommitmentAlreadyAccepted { period: 1 })
        ),
        "a second distinct commitment for the period refuses even with another nonce"
    );

    let opening_world = handle.current().world_hash;
    handle
        .commit(prepared(
            1,
            opening_world,
            vec![chunk(ChunkSection::WorldRegisters, 0, register(1))],
            Vec::new(),
            Vec::new(),
        ))
        .expect("period one commits with the accepted command");
    let retried = handle
        .accept_command(
            PlayerCommand {
                period: 1,
                actor_id: [7; 8],
                payload: b"equal-command-bytes".to_vec(),
            },
            NONCE_ONE,
        )
        .expect("the original acknowledgement replays after the advance");
    assert_eq!(retried.kind, AcceptanceKind::Existing);
    assert_eq!(retried.acceptance_seq, first.acceptance_seq);

    handle.inject_fault(FaultPoint::AfterAcceptBeforeAck);
    let lost = handle
        .accept_command(
            PlayerCommand {
                period: 2,
                actor_id: [7; 8],
                payload: b"period-two-command".to_vec(),
            },
            NONCE_TWO,
        )
        .expect_err("the injected fault loses the acceptance acknowledgement");
    assert!(
        matches!(lost, CommandError::Store(SaveError::InjectedFault)),
        "the acceptance seam reports its injected fault"
    );
    let reconciled = handle
        .accept_command(
            PlayerCommand {
                period: 2,
                actor_id: [7; 8],
                payload: b"period-two-command".to_vec(),
            },
            NONCE_TWO,
        )
        .expect("the durable acceptance reconciles after the lost acknowledgement");
    assert_eq!(reconciled.kind, AcceptanceKind::Existing);
    assert_eq!(reconciled.period, 2);
}

#[test]
#[allow(
    clippy::too_many_lines,
    reason = "one conformance scenario asserts every disclosure refusal"
)]
fn scoped_read_refuses_undisclosed_or_future_acquired_fact() {
    let root = TempRoot::new();
    let database = root.path("campaign.sqlite3");
    let mut handle = SqliteCampaignStore::create(&database, admitted_content(), admitted_opening())
        .expect("the campaign is created once");
    handle
        .commit(prepared(
            1,
            world_identity(0),
            vec![chunk(ChunkSection::WorldRegisters, 0, register(1))],
            Vec::new(),
            Vec::new(),
        ))
        .expect("period one commits without the future fact");
    assert!(
        matches!(
            handle.read_granted_subject(
                9_u64.to_be_bytes(),
                SubjectKind::County,
                b"michigan-wayne",
                1
            ),
            Err(SaveError::UndisclosedSubject)
        ),
        "period one does not disclose a fact acquired later"
    );

    let observed = frame(
        b"babylon.test.observation.v1\0",
        1,
        b"observed-in-period-one",
    );
    handle
        .commit(prepared(
            2,
            world_identity(1),
            vec![chunk(ChunkSection::WorldRegisters, 0, register(2))],
            vec![journal(
                JournalKind::GovernedChoice,
                Some((SubjectKind::Observation, b"choice-2")),
                b"choice-receipt-period-two",
            )],
            vec![knowledge(
                9,
                SubjectKind::County,
                b"michigan-wayne",
                1,
                &observed,
            )],
        ))
        .expect("period two commits the earned fact");
    assert!(
        matches!(
            handle.read_granted_subject(
                9_u64.to_be_bytes(),
                SubjectKind::County,
                b"michigan-wayne",
                1
            ),
            Err(SaveError::UndisclosedSubject)
        ),
        "an observation period inside the payload does not disclose a period-two acquisition"
    );
    assert_eq!(
        handle
            .read_granted_subject(
                9_u64.to_be_bytes(),
                SubjectKind::County,
                b"michigan-wayne",
                2
            )
            .expect("the acquisition period discloses the fact"),
        observed
    );
    assert!(matches!(
        handle.read_granted_subject(
            9_u64.to_be_bytes(),
            SubjectKind::County,
            b"michigan-wayne",
            3
        ),
        Err(SaveError::FuturePeriod {
            current: 2,
            requested: 3
        })
    ));
    assert!(matches!(
        handle.read_granted_subject(
            9_u64.to_be_bytes(),
            SubjectKind::Place,
            b"michigan-wayne",
            2
        ),
        Err(SaveError::UndisclosedSubject)
    ));
    assert!(matches!(
        handle.read_granted_subject(
            10_u64.to_be_bytes(),
            SubjectKind::County,
            b"michigan-wayne",
            2
        ),
        Err(SaveError::UndisclosedSubject)
    ));
}

#[test]
#[allow(
    clippy::too_many_lines,
    reason = "one conformance scenario asserts every crash point"
)]
fn crash_points_preserve_atomic_state_and_single_execution() {
    let root = TempRoot::new();
    let database = root.path("campaign.sqlite3");
    let mut handle = SqliteCampaignStore::create(&database, admitted_content(), admitted_opening())
        .expect("the campaign is created once");
    handle
        .accept_command(
            PlayerCommand {
                period: 1,
                actor_id: [7; 8],
                payload: b"command-before-the-crash".to_vec(),
            },
            NONCE_ONE,
        )
        .expect("the command is durable before the crash");
    handle.inject_fault(FaultPoint::BeforeCommit);
    let before = handle
        .commit(prepared(
            1,
            world_identity(0),
            vec![chunk(ChunkSection::WorldRegisters, 0, register(1))],
            Vec::new(),
            Vec::new(),
        ))
        .expect_err("the injected fault aborts before the commit transaction");
    assert!(matches!(before, SaveError::InjectedFault));
    drop(handle);

    let mut reopened =
        SqliteCampaignStore::open(&database, build_identity()).expect("the witness cold reopens");
    let after_crash = reopened
        .commit(prepared(
            1,
            world_identity(0),
            vec![chunk(ChunkSection::WorldRegisters, 0, register(1))],
            Vec::new(),
            Vec::new(),
        ))
        .expect("a crash before commit leaves the accepted command reconstructible");
    assert_eq!(after_crash.kind, CommitKind::Inserted);
    let single = reopened
        .commit(prepared(
            1,
            world_identity(0),
            vec![chunk(ChunkSection::WorldRegisters, 0, register(1))],
            Vec::new(),
            Vec::new(),
        ))
        .expect("the post-crash retry is idempotent");
    assert_eq!(single.kind, CommitKind::Existing);
    assert_eq!(single.journal_tail_hash, after_crash.journal_tail_hash);
    assert_eq!(single.journal_tail_seq, after_crash.journal_tail_seq);
    drop(reopened);

    let mut lost_ack =
        SqliteCampaignStore::open(&database, build_identity()).expect("the campaign reopens again");
    lost_ack.inject_fault(FaultPoint::AfterCommitBeforeAck);
    let lost = lost_ack
        .commit(prepared(
            2,
            world_identity(1),
            vec![chunk(ChunkSection::WorldRegisters, 0, register(2))],
            Vec::new(),
            Vec::new(),
        ))
        .expect_err("the injected fault loses the acknowledgement");
    assert!(matches!(lost, SaveError::InjectedFault));
    drop(lost_ack);

    let mut reconciled =
        SqliteCampaignStore::open(&database, build_identity()).expect("the campaign reconciles");
    assert_eq!(
        reconciled.current().period,
        2,
        "the committed period survived the lost acknowledgement"
    );
    let reconciled_receipt = reconciled
        .commit(prepared(
            2,
            world_identity(1),
            vec![chunk(ChunkSection::WorldRegisters, 0, register(2))],
            Vec::new(),
            Vec::new(),
        ))
        .expect("the committed period reconciles exactly");
    assert_eq!(reconciled_receipt.kind, CommitKind::Existing);
    let reconciled_again = reconciled
        .commit(prepared(
            2,
            world_identity(1),
            vec![chunk(ChunkSection::WorldRegisters, 0, register(2))],
            Vec::new(),
            Vec::new(),
        ))
        .expect("the reconciled period stays idempotent");
    assert_eq!(
        reconciled_again.journal_tail_seq, reconciled_receipt.journal_tail_seq,
        "reconciliation never performs the period twice"
    );

    let destination = root.path("interrupted.sqlite3");
    reconciled.inject_fault(FaultPoint::DuringExport);
    let interrupted = reconciled
        .export_save(&destination)
        .expect_err("the injected fault aborts the export before publication");
    assert!(matches!(interrupted, SaveError::InjectedFault));
    assert!(
        !destination.exists(),
        "an interrupted export publishes no partial destination"
    );
    let published = reconciled
        .export_save(&destination)
        .expect("the source remains exportable after an interrupted export");
    assert!(published.integrity_verified);
}

#[test]
#[allow(
    clippy::too_many_lines,
    reason = "one conformance scenario asserts rollback and retry together"
)]
fn during_commit_fault_rolls_back_atomically() {
    let root = TempRoot::new();
    let database = root.path("campaign.sqlite3");
    let mut handle = SqliteCampaignStore::create(&database, admitted_content(), admitted_opening())
        .expect("the campaign is created once");
    let accepted = handle
        .accept_command(
            PlayerCommand {
                period: 1,
                actor_id: [7; 8],
                payload: b"command-inside-the-period-transaction".to_vec(),
            },
            NONCE_ONE,
        )
        .expect("the accepted command is durable before the period");
    handle.inject_fault(FaultPoint::DuringCommit);
    let interrupted = handle
        .commit(prepared(
            1,
            world_identity(0),
            vec![chunk(ChunkSection::WorldRegisters, 0, register(1))],
            vec![journal(
                JournalKind::GovernedChoice,
                Some((SubjectKind::Observation, b"choice-1")),
                b"choice-receipt-payload",
            )],
            vec![knowledge(
                42,
                SubjectKind::County,
                b"michigan-wayne",
                1,
                b"earned-county-fact",
            )],
        ))
        .expect_err("the injected fault aborts inside the write transaction");
    assert!(matches!(interrupted, SaveError::InjectedFault));
    assert_eq!(
        handle.current().period,
        0,
        "the aborted transaction leaves the committed present at the opening period"
    );
    assert!(matches!(
        handle.read_granted_subject(
            42_u64.to_be_bytes(),
            SubjectKind::County,
            b"michigan-wayne",
            1
        ),
        Err(SaveError::FuturePeriod {
            current: 0,
            requested: 1
        })
    ));
    drop(handle);

    let raw = raw_connection(&database);
    let committed_period: i64 = raw
        .query_row(
            "SELECT period FROM snapshot
             WHERE snapshot_id = (SELECT current_snapshot_id FROM save_manifest WHERE id = 1)",
            [],
            |row| row.get(0),
        )
        .expect("the current snapshot is readable");
    assert_eq!(
        committed_period, 0,
        "the aborted transaction leaves the manifest at the opening period"
    );
    assert_eq!(
        count(&raw, "snapshot"),
        1,
        "the aborted transaction publishes no partial snapshot"
    );
    assert_eq!(
        count(&raw, "permanent_journal"),
        1,
        "only the accepted command record survives the rollback"
    );
    assert_eq!(
        count(&raw, "knowledge_grant"),
        0,
        "the aborted transaction publishes no partial knowledge grant"
    );
    drop(raw);

    let mut retried =
        SqliteCampaignStore::open(&database, build_identity()).expect("the campaign cold reopens");
    let committed = retried
        .commit(prepared(
            1,
            world_identity(0),
            vec![chunk(ChunkSection::WorldRegisters, 0, register(1))],
            vec![journal(
                JournalKind::GovernedChoice,
                Some((SubjectKind::Observation, b"choice-1")),
                b"choice-receipt-payload",
            )],
            vec![knowledge(
                42,
                SubjectKind::County,
                b"michigan-wayne",
                1,
                b"earned-county-fact",
            )],
        ))
        .expect("the retry commits the whole period after a clean rollback");
    assert_eq!(committed.kind, CommitKind::Inserted);
    assert_eq!(
        committed.journal_tail_seq,
        accepted.acceptance_seq + 3,
        "the retry appends the command consumption, the evidence record and the period summary"
    );
    assert_eq!(
        retried
            .read_granted_subject(
                42_u64.to_be_bytes(),
                SubjectKind::County,
                b"michigan-wayne",
                1
            )
            .expect("the retried period discloses its earned fact"),
        b"earned-county-fact"
    );
}

#[test]
#[allow(
    clippy::too_many_lines,
    clippy::cognitive_complexity,
    reason = "one refusal scenario covers each admitted malformed input"
)]
fn refuses_truncated_payload_wrong_schema_and_inconsistent_candidates() {
    let root = TempRoot::new();
    let truncated_database = root.path("truncated.sqlite3");
    let mut handle =
        SqliteCampaignStore::create(&truncated_database, admitted_content(), admitted_opening())
            .expect("the campaign is created once");
    handle
        .commit(prepared(
            1,
            world_identity(0),
            vec![chunk(ChunkSection::WorldRegisters, 0, register(1))],
            vec![journal(
                JournalKind::GovernedChoice,
                Some((SubjectKind::Observation, b"choice-1")),
                b"choice-receipt-payload",
            )],
            vec![knowledge(
                7,
                SubjectKind::County,
                b"michigan-wayne",
                1,
                b"stored-fact-payload",
            )],
        ))
        .expect("period one commits the earned fact");
    drop(handle);

    let raw = raw_connection(&truncated_database);
    raw.execute(
        "UPDATE knowledge_grant SET payload = substr(payload, 1, length(payload) - 1)",
        [],
    )
    .expect("the test truncates the stored knowledge payload");
    drop(raw);
    let reopened = SqliteCampaignStore::open(&truncated_database, build_identity())
        .expect("the campaign reopens");
    assert!(
        matches!(
            reopened.read_granted_subject(
                7_u64.to_be_bytes(),
                SubjectKind::County,
                b"michigan-wayne",
                1
            ),
            Err(SaveError::CorruptPayload {
                table: "knowledge_grant",
                ..
            })
        ),
        "the stored entry hash detects truncation"
    );

    let version_database = root.path("version.sqlite3");
    let version_store =
        SqliteCampaignStore::create(&version_database, admitted_content(), admitted_opening())
            .expect("the version campaign is created");
    drop(version_store);
    let raw = raw_connection(&version_database);
    raw.pragma_update(None, "user_version", 99)
        .expect("the test writes a wrong schema version");
    drop(raw);
    match SqliteCampaignStore::open(&version_database, build_identity()) {
        Err(SaveError::SchemaVersion { expected, actual }) => {
            assert_eq!(expected, SCHEMA_VERSION);
            assert_eq!(actual, 99);
        }
        other => panic!("a wrong schema version must refuse: {other:?}"),
    }

    let input_database = root.path("input.sqlite3");
    let mut input =
        SqliteCampaignStore::create(&input_database, admitted_content(), admitted_opening())
            .expect("the input campaign is created");
    let base_chunks = vec![chunk(ChunkSection::WorldRegisters, 0, register(1))];
    assert!(matches!(
        input.commit(prepared(
            1,
            world_identity(0),
            Vec::new(),
            Vec::new(),
            Vec::new()
        )),
        Err(SaveError::InvalidField {
            field: "chunks",
            ..
        })
    ));
    let oversized = vec![0_u8; MAX_STATE_CHUNK_BYTES + 1];
    assert!(matches!(
        input.commit(prepared(
            1,
            world_identity(0),
            vec![chunk(ChunkSection::WorldRegisters, 0, oversized)],
            Vec::new(),
            Vec::new(),
        )),
        Err(SaveError::PayloadTooLarge {
            table: "state_chunk",
            ..
        })
    ));
    assert!(matches!(
        input.commit(prepared(
            1,
            world_identity(0),
            vec![
                chunk(ChunkSection::WorldRegisters, 0, register(1)),
                chunk(ChunkSection::WorldRegisters, 0, register(1)),
            ],
            Vec::new(),
            Vec::new(),
        )),
        Err(SaveError::DuplicateChunkPosition {
            section: 2,
            ordinal: 0
        })
    ));
    assert!(matches!(
        input.commit(prepared(
            1,
            world_identity(0),
            base_chunks.clone(),
            Vec::new(),
            vec![knowledge(
                7,
                SubjectKind::County,
                b"michigan-wayne",
                1,
                b"stored-fact-payload",
            )],
        )),
        Err(SaveError::KnowledgeSourceMissing)
    ));
    assert!(matches!(
        input.commit(prepared(
            1,
            world_identity(0),
            base_chunks.clone(),
            vec![journal(JournalKind::PlayerReceipt, None, b"first-receipt",)],
            vec![
                knowledge(
                    7,
                    SubjectKind::County,
                    b"michigan-wayne",
                    1,
                    b"first-fact-payload",
                ),
                knowledge(
                    7,
                    SubjectKind::County,
                    b"michigan-wayne",
                    1,
                    b"second-fact-payload",
                ),
            ],
        )),
        Err(SaveError::DuplicateKnowledgeGrant)
    ));
    assert!(matches!(
        input.commit(prepared(
            1,
            world_identity(0),
            base_chunks.clone(),
            vec![journal(
                JournalKind::AcceptedCommand,
                None,
                b"forged-command-record",
            )],
            Vec::new(),
        )),
        Err(SaveError::ReservedJournalKind { code: 1 })
    ));
    assert!(matches!(
        input.commit(prepared(
            1,
            world_identity(0),
            base_chunks.clone(),
            vec![resolving_journal(
                JournalKind::PlayerReceipt,
                (SubjectKind::Shipment, b"never-shipped"),
                b"orphan-resolution",
            )],
            Vec::new(),
        )),
        Err(SaveError::UnresolvedSubjectMissing)
    ));
    assert!(matches!(
        input.commit(prepared(
            1,
            content_digest::sha256_of(b"a different root"),
            base_chunks.clone(),
            Vec::new(),
            Vec::new(),
        )),
        Err(SaveError::StaleRoot { .. })
    ));
    assert!(matches!(
        input.commit(prepared(
            3,
            world_identity(0),
            base_chunks,
            Vec::new(),
            Vec::new(),
        )),
        Err(SaveError::WrongPeriod {
            expected: 1,
            actual: 3
        })
    ));
    drop(input);
    assert!(matches!(
        SqliteCampaignStore::create(&input_database, admitted_content(), admitted_opening()),
        Err(SaveError::CampaignExists { .. })
    ));
    assert!(matches!(
        SqliteCampaignStore::open(&input_database, BuildIdentity::from_hash([0_u8; 32])),
        Err(SaveError::BuildMismatch { .. })
    ));
}

#[test]
fn open_refuses_a_tampered_current_chunk() {
    let root = TempRoot::new();
    let database = root.path("campaign.sqlite3");
    let mut handle = SqliteCampaignStore::create(&database, admitted_content(), admitted_opening())
        .expect("the campaign is created once");
    handle
        .commit(prepared(
            1,
            world_identity(0),
            vec![chunk(ChunkSection::WorldRegisters, 0, register(1))],
            Vec::new(),
            Vec::new(),
        ))
        .expect("period one commits");
    drop(handle);

    let raw = raw_connection(&database);
    raw.execute(
        "UPDATE state_chunk SET payload = x'00'
         WHERE chunk_id = (
             SELECT chunk_id FROM snapshot_chunk
             JOIN snapshot USING (snapshot_id)
             WHERE snapshot.role = 2 LIMIT 1
         )",
        [],
    )
    .expect("the test tampers with the current chunk");
    drop(raw);
    assert!(
        matches!(
            SqliteCampaignStore::open(&database, build_identity()),
            Err(SaveError::CorruptPayload { .. })
        ),
        "opening authenticates every current chunk"
    );
}

#[test]
fn stale_lock_with_a_dead_owner_is_recovered_after_identity_check() {
    let root = TempRoot::new();
    let database = root.path("campaign.sqlite3");
    let handle = SqliteCampaignStore::create(&database, admitted_content(), admitted_opening())
        .expect("the campaign is created once");
    drop(handle);

    write_lock_record(&database, u32::MAX, campaign_id());
    let reopened = SqliteCampaignStore::open(&database, build_identity())
        .expect("a dead owner's record is recovered");
    let record = fs::read(lock::lock_path(&database)).expect("the recovered record is readable");
    assert_eq!(
        &record[..4],
        &std::process::id().to_be_bytes(),
        "recovery republishes this process as the owner"
    );
    drop(reopened);
}

#[test]
fn stale_lock_for_another_campaign_is_not_recovered() {
    let root = TempRoot::new();
    let database = root.path("campaign.sqlite3");
    let handle = SqliteCampaignStore::create(&database, admitted_content(), admitted_opening())
        .expect("the campaign is created once");
    drop(handle);

    write_lock_record(&database, u32::MAX, other_campaign_id());
    match SqliteCampaignStore::open(&database, build_identity()) {
        Err(SaveError::LockRecordMismatch { recorded, manifest }) => {
            assert_eq!(recorded, other_campaign_id());
            assert_eq!(manifest, campaign_id());
        }
        other => panic!("a mismatched stale owner must refuse: {other:?}"),
    }
    assert!(
        lock::lock_path(&database).exists(),
        "a mismatched record is not deleted"
    );
}

#[test]
fn live_lock_refuses_recovery() {
    let root = TempRoot::new();
    let database = root.path("campaign.sqlite3");
    let handle = SqliteCampaignStore::create(&database, admitted_content(), admitted_opening())
        .expect("the campaign is created once");
    drop(handle);

    write_lock_record(&database, std::process::id(), campaign_id());
    assert!(
        matches!(
            SqliteCampaignStore::open(&database, build_identity()),
            Err(SaveError::CampaignLocked { owner_pid, .. }) if owner_pid == std::process::id()
        ),
        "a live owner always refuses"
    );
}

#[test]
fn stale_lock_without_a_database_is_recovered_by_create() {
    let root = TempRoot::new();
    let database = root.path("campaign.sqlite3");
    write_lock_record(&database, u32::MAX, campaign_id());
    let handle = SqliteCampaignStore::create(&database, admitted_content(), admitted_opening())
        .expect("a create crash before the database leaves a recoverable record");
    drop(handle);
    assert!(
        SqliteCampaignStore::open(&database, build_identity()).is_ok(),
        "the created campaign reopens"
    );
}

#[test]
fn recovery_claim_held_by_a_live_owner_refuses() {
    let root = TempRoot::new();
    let database = root.path("campaign.sqlite3");
    let handle = SqliteCampaignStore::create(&database, admitted_content(), admitted_opening())
        .expect("the campaign is created once");
    drop(handle);

    write_lock_record(&database, u32::MAX, campaign_id());
    let mut claim = lock::lock_path(&database).into_os_string();
    claim.push(".recover");
    fs::write(PathBuf::from(claim), std::process::id().to_be_bytes())
        .expect("the recovery claim is writable");
    assert!(
        matches!(
            SqliteCampaignStore::open(&database, build_identity()),
            Err(SaveError::LockRecoveryBusy { .. })
        ),
        "a live recovery claim serializes takeover"
    );
}

#[test]
fn create_reclaims_an_interrupted_creation_instead_of_dead_ending_the_path() {
    let root = TempRoot::new();

    // A crash after the schema installed but before the manifest committed.
    let schema_database = root.path("schema-only.sqlite3");
    interrupted_creation(&schema_database, PartialCreation::SchemaOnly);
    assert!(
        matches!(
            SqliteCampaignStore::open(&schema_database, build_identity()),
            Err(SaveError::CorruptManifest { .. })
        ),
        "an interrupted creation has no committed root to open"
    );
    let handle =
        SqliteCampaignStore::create(&schema_database, admitted_content(), admitted_opening())
            .expect("a dead owner's interrupted creation is reclaimed by create");
    let raw = raw_connection(&schema_database);
    assert_eq!(
        count(&raw, "save_manifest"),
        1,
        "the reclaimed path commits exactly one manifest root"
    );
    assert_eq!(
        count(&raw, "content_entry"),
        2,
        "the reclaimed path holds exactly the newly admitted content"
    );
    assert_eq!(
        count(&raw, "permanent_journal"),
        0,
        "no journal record survives an interrupted creation"
    );
    drop(raw);
    drop(handle);
    let reopened = SqliteCampaignStore::open(&schema_database, build_identity())
        .expect("the reclaimed campaign cold reopens");
    assert_eq!(reopened.current().period, 0);
    drop(reopened);

    // A crash before the schema installed leaves an empty file behind.
    let empty_database = root.path("empty.sqlite3");
    interrupted_creation(&empty_database, PartialCreation::EmptyFile);
    let reclaimed =
        SqliteCampaignStore::create(&empty_database, admitted_content(), admitted_opening())
            .expect("an empty partial creation is reclaimed by create");
    drop(reclaimed);
    assert!(
        SqliteCampaignStore::open(&empty_database, build_identity()).is_ok(),
        "the reclaimed campaign opens"
    );
}

#[test]
fn prior_subject_resolution_is_persisted_and_survives_cold_reopen() {
    let root = TempRoot::new();
    let database = root.path("campaign.sqlite3");
    let mut handle = SqliteCampaignStore::create(&database, admitted_content(), admitted_opening())
        .expect("the campaign is created once");
    let first = handle
        .commit(prepared(
            1,
            world_identity(0),
            vec![chunk(ChunkSection::WorldRegisters, 0, register(1))],
            vec![journal(
                JournalKind::PlayerReceipt,
                Some((SubjectKind::Shipment, b"freight-wayne-1")),
                b"freight-notice",
            )],
            Vec::new(),
        ))
        .expect("period one journals the unresolved freight subject");
    let second = handle
        .commit(prepared(
            2,
            first.world_hash,
            vec![chunk(ChunkSection::WorldRegisters, 0, register(2))],
            vec![resolving_journal(
                JournalKind::PlayerReceipt,
                (SubjectKind::Shipment, b"freight-wayne-1"),
                b"freight-delivered",
            )],
            Vec::new(),
        ))
        .expect("the period-two record resolves the prior freight subject");
    assert_eq!(
        second.journal_tail_seq,
        first.journal_tail_seq + 2,
        "period two appends the resolving freight record and its period summary"
    );
    let resolution_seq = second.journal_tail_seq - 1;
    let assert_freight = |rows: &[(u64, Option<u64>, Option<u64>)]| {
        assert_eq!(rows.len(), 2, "the freight subject owns two records");
        assert_eq!(
            rows[0].0,
            first.journal_tail_seq - 1,
            "the freight record precedes its period's terminal summary"
        );
        assert_eq!(
            rows[0].1,
            Some(2),
            "the earlier freight record resolved in period two"
        );
        assert_eq!(
            rows[0].2,
            Some(resolution_seq),
            "the earlier freight record names the period-two resolution"
        );
        assert_eq!(rows[1].0, resolution_seq);
        assert_eq!(rows[1].1, None, "the resolving record stays unresolved");
        assert_eq!(rows[1].2, None);
    };
    assert_freight(&subject_resolution_rows(
        &database,
        SubjectKind::Shipment,
        b"freight-wayne-1",
    ));
    drop(handle);

    let reopened =
        SqliteCampaignStore::open(&database, build_identity()).expect("the campaign cold reopens");
    assert_eq!(reopened.current().period, 2);
    assert_freight(&subject_resolution_rows(
        &database,
        SubjectKind::Shipment,
        b"freight-wayne-1",
    ));
}

#[test]
fn publication_refuses_a_destination_that_appears_after_the_check() {
    let root = TempRoot::new();
    let temporary = root.path("verified.tmp");
    fs::write(&temporary, b"verified backup").expect("the verified temporary file is writable");
    let destination = root.path("published.sqlite3");
    fs::write(&destination, b"someone else's save").expect("the late destination is writable");

    assert!(
        matches!(
            export::publish(&temporary, &destination),
            Err(SaveError::ExportDestinationExists)
        ),
        "publication refuses a destination that appeared after the reservation"
    );
    assert_eq!(
        fs::read(&destination).expect("the destination is readable"),
        b"someone else's save",
        "a refused publication never overwrites the destination"
    );
    assert!(
        temporary.exists(),
        "the refused publication keeps its temporary file for the caller"
    );
}

#[test]
fn export_refuses_a_broken_snapshot_chunk_link() {
    let root = TempRoot::new();
    let database = root.path("campaign.sqlite3");
    let mut handle = SqliteCampaignStore::create(&database, admitted_content(), admitted_opening())
        .expect("the campaign is created once");
    handle
        .commit(prepared(
            1,
            world_identity(0),
            vec![chunk(ChunkSection::WorldRegisters, 0, register(1))],
            Vec::new(),
            Vec::new(),
        ))
        .expect("period one commits");

    // Break the committed link behind the already-open handle, so only the export
    // verifier can catch it.
    let raw = raw_connection(&database);
    raw.execute(
        "DELETE FROM snapshot_chunk WHERE snapshot_id = (
             SELECT current_snapshot_id FROM save_manifest WHERE id = 1
         )",
        [],
    )
    .expect("the test breaks the committed chunk link");
    drop(raw);

    let destination = root.path("refused.sqlite3");
    match handle.export_save(&destination) {
        Err(SaveError::CorruptManifest { reason }) => assert_eq!(
            reason, "the snapshot manifest declares chunks it does not reach",
            "the verifier re-runs the restart-root load"
        ),
        other => panic!("an export with a broken chunk link must refuse: {other:?}"),
    }
    assert!(!destination.exists(), "a refused export publishes nothing");
    let leftovers: Vec<String> = fs::read_dir(&root.0)
        .expect("the campaign root is readable")
        .map(|entry| {
            entry
                .expect("the directory entry reads")
                .file_name()
                .to_string_lossy()
                .into_owned()
        })
        .filter(|name| name.contains(".export-"))
        .collect();
    assert!(
        leftovers.is_empty(),
        "a refused export removes its temporary file: {leftovers:?}"
    );
}

//
// Task 8 (`P4b`): 13-period retention, two rolling checkpoints, chunk GC,
// isolated replay and recovery. The tests cross the roster boundaries named in
// the plan (12/13/14, 25/26/27, 39/40) and inject independent corruption into
// the current chunk, a cold detail row, an acquired fact and a command
// resolution.
//

/// Deterministic poorly compressible bytes for the retention fixture.
fn incompressible_bytes(seed: u64, len: usize) -> Vec<u8> {
    let mut state = seed.wrapping_mul(0x9e37_79b9_7f4a_7c15) | 1;
    let mut bytes = Vec::with_capacity(len);
    for _ in 0..len {
        state ^= state << 13;
        state ^= state >> 7;
        state ^= state << 17;
        bytes.push(state.to_le_bytes()[0]);
    }
    bytes
}

/// One committed period kept for replay comparison.
fn long_candidate(
    period: u64,
    expected_world: [u8; 32],
    journal: Vec<PreparedJournalRecord>,
    knowledge: Vec<PreparedKnowledgeGrant>,
) -> PreparedPeriod {
    // Each period's register owns whole pages of poorly compressible bytes, so
    // retiring a checkpoint frees pages rather than only slack in a shared page.
    let mut register_period = register(period);
    register_period.extend_from_slice(&incompressible_bytes(period, 65_536));
    PreparedPeriod {
        period,
        expected_world_hash: expected_world,
        world_hash: world_identity(period),
        state_hash: content_digest::sha256_of(&register_period),
        chunks: vec![
            chunk(ChunkSection::WorldRegisters, 0, register_period),
            chunk(ChunkSection::StableGraph, 0, graph(0)),
        ],
        journal,
        knowledge,
        detail: vec![PreparedDetailRow {
            family: DetailFamily::Prices,
            ordinal: 0,
            payload: format!("prices-{period}").into_bytes(),
        }],
    }
}

/// A campaign driven period by period with one choice receipt per period.
struct RetentionRun {
    handle: CampaignHandle,
    receipts: Vec<CommittedPeriod>,
}

impl RetentionRun {
    fn start(database: &Path) -> Self {
        let handle = SqliteCampaignStore::create(database, admitted_content(), admitted_opening())
            .expect("the retention campaign is created once");
        Self {
            handle,
            receipts: Vec::new(),
        }
    }

    fn advance_to(&mut self, last_period: u64) {
        while self.handle.current().period < last_period {
            let period = self.handle.current().period + 1;
            let mut records = vec![journal(
                JournalKind::GovernedChoice,
                Some((
                    SubjectKind::Observation,
                    format!("choice-{period}").as_bytes(),
                )),
                format!("choice-receipt-{period}").as_bytes(),
            )];
            if period == 2 {
                let mut receipt = journal(
                    JournalKind::PlayerReceipt,
                    Some((SubjectKind::County, b"26163")),
                    b"county-wage-receipt",
                );
                receipt.record_key = Some(b"receipt-2".to_vec());
                records.push(receipt);
            }
            let knowledge = if period == 9 {
                vec![knowledge(
                    42,
                    SubjectKind::County,
                    b"michigan-wayne",
                    1,
                    b"observed-in-period-4-acquired-in-9",
                )]
            } else {
                Vec::new()
            };
            let candidate =
                long_candidate(period, self.handle.current().world_hash, records, knowledge);
            let committed = self
                .handle
                .commit(candidate)
                .expect("every retention period commits");
            self.receipts.push(committed);
        }
    }
}

/// Read `(role, period)` for every retained snapshot in natural order.
fn snapshot_roster(database: &Path) -> Vec<(i64, i64)> {
    let connection = read_connection(database);
    let mut statement = connection
        .prepare("SELECT role, period FROM snapshot ORDER BY role, period")
        .expect("the snapshot roster queries");
    let rows = statement
        .query_map([], |row| Ok((row.get(0)?, row.get(1)?)))
        .expect("the snapshot roster reads");
    rows.map(|row| row.expect("a snapshot row is readable"))
        .collect()
}

/// Read the chunk identity set one snapshot reaches.
fn snapshot_chunks(database: &Path, period: i64, role: i64) -> Vec<i64> {
    let connection = read_connection(database);
    let mut statement = connection
        .prepare(
            "SELECT chunk_id FROM snapshot_chunk
             WHERE snapshot_id = (SELECT snapshot_id FROM snapshot WHERE period = ?1 AND role = ?2)
             ORDER BY chunk_id",
        )
        .expect("the snapshot chunk list queries");
    let rows = statement
        .query_map(params![period, role], |row| row.get::<_, i64>(0))
        .expect("the snapshot chunk list reads");
    rows.map(|row| row.expect("a chunk link is readable"))
        .collect()
}

fn scalar(connection: &Connection, sql: &str) -> i64 {
    connection
        .query_row(sql, [], |row| row.get(0))
        .expect("the scalar query reads one row")
}

fn read_connection(database: &Path) -> Connection {
    Connection::open_with_flags(
        database,
        OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_NO_MUTEX,
    )
    .expect("the campaign database opens read-only")
}

/// Flip one byte of every row a `WHERE` clause selects in a payload column.
fn flip_payload_bytes(database: &Path, table: &str, where_clause: &str) {
    let connection = raw_connection(database);
    connection
        .execute(
            &format!(
                "UPDATE {table} SET payload = CAST(
                     substr(payload, 1, 1) || x'FF' || substr(payload, 3) AS BLOB
                 ) WHERE {where_clause}"
            ),
            [],
        )
        .expect("the test flips one payload byte");
}

#[test]
#[allow(
    clippy::too_many_lines,
    clippy::cognitive_complexity,
    reason = "one conformance scenario asserts every roster boundary, the window and the accounting"
)]
fn retention_rotation_keeps_the_exact_roster_and_recent_window() {
    let root = TempRoot::new();
    let database = root.path("campaign.sqlite3");
    let mut run = RetentionRun::start(&database);

    run.advance_to(12);
    assert_eq!(
        snapshot_roster(&database),
        vec![(1, 0), (2, 12)],
        "period 12 retains opening and current and no checkpoint"
    );

    run.advance_to(13);
    assert_eq!(
        snapshot_roster(&database),
        vec![(1, 0), (2, 13), (3, 13)],
        "period 13 adds one checkpoint beside the current root"
    );
    assert_eq!(
        snapshot_chunks(&database, 13, 2),
        snapshot_chunks(&database, 13, 3),
        "the current root and its checkpoint share integer chunk identities"
    );

    run.advance_to(14);
    assert_eq!(
        snapshot_roster(&database),
        vec![(1, 0), (2, 14), (3, 13)],
        "period 14 replaces the current root and keeps checkpoint 13"
    );

    run.advance_to(25);
    assert_eq!(
        snapshot_roster(&database),
        vec![(1, 0), (2, 25), (3, 13)],
        "periods 15 to 25 never accumulate checkpoints"
    );

    run.advance_to(26);
    assert_eq!(
        snapshot_roster(&database),
        vec![(1, 0), (2, 26), (3, 13), (3, 26)],
        "period 26 retains the two completed checkpoints"
    );

    run.advance_to(27);
    assert_eq!(
        snapshot_roster(&database),
        vec![(1, 0), (2, 27), (3, 13), (3, 26)],
        "period 27 keeps both checkpoints behind the new current root"
    );

    run.advance_to(39);
    assert_eq!(
        snapshot_roster(&database),
        vec![(1, 0), (2, 39), (3, 26), (3, 39)],
        "period 39 retires checkpoint 13 and keeps 26 and 39"
    );

    run.advance_to(40);
    assert_eq!(
        snapshot_roster(&database),
        vec![(1, 0), (2, 40), (3, 26), (3, 39)],
        "period 40 moves the current root without adding a checkpoint"
    );

    let retirement = run.receipts[38].retention;
    assert_eq!(
        (retirement.period, retirement.snapshots_retained),
        (39, 4),
        "the period-39 checkpoint rotation retains opening, current and two checkpoints"
    );
    assert!(
        retirement.gross_bytes_added > 65_536 && retirement.bytes_made_unreachable > 0,
        "period 39 counts its inserted register bytes apart from the bytes it made unreachable"
    );
    assert!(
        retirement.chunks_reclaimed > 0 && retirement.main_file_bytes > 0,
        "period 39 reclaims the retired checkpoint's exclusive chunks and reports the file"
    );
    assert!(
        retirement.reclaimed_bytes > 0,
        "the bounded incremental vacuum actually returns the retired checkpoint's pages"
    );
    let newest = run.receipts[39].retention;
    assert_eq!(
        (newest.period, newest.detail_rows_reclaimed),
        (40, 1),
        "period 40 evicts exactly the detail row that left the thirteen-period window"
    );
    let connection = read_connection(&database);
    assert_eq!(
        scalar(
            &connection,
            "SELECT COUNT(*) FROM state_chunk
             WHERE chunk_id NOT IN (SELECT chunk_id FROM snapshot_chunk)"
        ),
        0,
        "rotation reclaims every chunk no retained snapshot reaches"
    );
    assert_eq!(
        scalar(
            &connection,
            "SELECT COUNT(*) FROM snapshot_chunk
             WHERE snapshot_id = (SELECT snapshot_id FROM snapshot WHERE role = 1)"
        ),
        2,
        "the opening keeps its exact chunk links through rotation"
    );
    assert_eq!(
        scalar(
            &connection,
            "SELECT COUNT(*) FROM recent_detail
             WHERE period < (SELECT MAX(period) FROM recent_detail) - 12"
        ),
        0,
        "recent detail keeps only the latest thirteen completed periods"
    );
    assert_eq!(
        (
            scalar(&connection, "SELECT MIN(period) FROM recent_detail"),
            scalar(&connection, "SELECT MAX(period) FROM recent_detail"),
            scalar(
                &connection,
                "SELECT COUNT(DISTINCT period) FROM recent_detail"
            ),
        ),
        (28, 40, 13),
        "period 40 exposes detail for exactly [28, 40]"
    );
    assert_eq!(
        scalar(
            &connection,
            "SELECT COUNT(*) FROM snapshot WHERE period = 2"
        ),
        0,
        "the period-two root is rotated out"
    );
    assert!(
        scalar(
            &connection,
            "SELECT COUNT(*) FROM permanent_journal WHERE period = 2"
        ) >= 2,
        "the permanent journal keeps period-two evidence after rotation"
    );
    drop(connection);

    let sequence = run
        .handle
        .journal_sequence_for_record(JournalKind::PlayerReceipt, b"receipt-2")
        .expect("the permanent receipt index reads")
        .expect("the period-two receipt stays resolvable across rotation");
    assert!(sequence > 0);
    assert_eq!(
        run.handle
            .read_recent_detail(40, DetailFamily::Prices)
            .expect("the newest detail row is readable"),
        vec![RecentDetailRow {
            period: 40,
            family: DetailFamily::Prices,
            ordinal: 0,
            payload: b"prices-40".to_vec(),
        }],
    );
    assert!(
        matches!(
            run.handle.read_recent_detail(27, DetailFamily::Prices),
            Err(SaveError::InvalidField {
                table: "recent_detail",
                ..
            })
        ),
        "period 27 fell out of the thirteen-period window and is refused explicitly"
    );
    assert_eq!(
        run.handle.current().period,
        40,
        "rotation publishes the newest current root"
    );
    drop(run);

    let reopened = SqliteCampaignStore::open(&database, build_identity())
        .expect("the rotated campaign cold reopens");
    assert_eq!(reopened.current().period, 40);
}

#[test]
#[allow(
    clippy::too_many_lines,
    clippy::cognitive_complexity,
    reason = "one conformance scenario asserts both replay spans, deltas and isolation together"
)]
fn replay_reconstructs_opening_and_checkpoint_span_with_matching_identities() {
    let root = TempRoot::new();
    let database = root.path("campaign.sqlite3");
    let mut run = RetentionRun::start(&database);
    run.advance_to(40);
    let source_before = fs::read(&database).expect("the campaign file is readable");
    let journal_before = {
        let connection = read_connection(&database);
        scalar(&connection, "SELECT COUNT(*) FROM permanent_journal")
    };
    let cancel = AtomicBool::new(false);

    let from_opening = run
        .handle
        .replay_to_period(5, &cancel)
        .expect("period five reconstructs from the opening");
    assert_eq!(from_opening.target_period, 5);
    assert_eq!(from_opening.source_checkpoint_period, 0);
    assert_eq!(from_opening.world_hash, run.receipts[4].world_hash);
    assert_eq!(from_opening.state_hash, run.receipts[4].state_hash);
    assert_eq!(from_opening.periods_verified, 5);
    assert_eq!(from_opening.choice_receipts.len(), 5);
    assert_eq!(
        from_opening
            .choice_receipts
            .iter()
            .map(|receipt| receipt.period)
            .collect::<Vec<_>>(),
        vec![1, 2, 3, 4, 5],
        "every intervening governed choice is reconstructed in order"
    );

    let from_checkpoint = run
        .handle
        .replay_to_period(28, &cancel)
        .expect("period twenty-eight reconstructs from checkpoint 26");
    assert_eq!(from_checkpoint.source_checkpoint_period, 26);
    assert_eq!(from_checkpoint.world_hash, run.receipts[27].world_hash);
    assert_eq!(from_checkpoint.state_hash, run.receipts[27].state_hash);
    assert_eq!(from_checkpoint.periods_verified, 2);
    assert_eq!(
        from_checkpoint
            .choice_receipts
            .iter()
            .map(|receipt| receipt.period)
            .collect::<Vec<_>>(),
        vec![27, 28]
    );

    let checkpoint_itself = run
        .handle
        .replay_to_period(26, &cancel)
        .expect("a checkpoint period reconstructs from itself");
    assert_eq!(checkpoint_itself.source_checkpoint_period, 26);
    assert_eq!(checkpoint_itself.world_hash, run.receipts[25].world_hash);
    assert_eq!(checkpoint_itself.periods_verified, 0);

    assert!(
        run.handle
            .replay_to_period(4, &cancel)
            .expect("period four reconstructs")
            .knowledge_grants
            .is_empty(),
        "a fact acquired in period nine is invisible in a period-four view"
    );
    let at_nine = run
        .handle
        .replay_to_period(9, &cancel)
        .expect("period nine reconstructs");
    assert_eq!(at_nine.knowledge_grants.len(), 1);
    assert_eq!(at_nine.knowledge_grants[0].acquired_period, 9);
    assert_eq!(at_nine.knowledge_grants[0].subject_id, b"michigan-wayne");

    assert_eq!(
        fs::read(&database).expect("the campaign file is readable"),
        source_before,
        "replay never mutates the source save bytes"
    );
    {
        let connection = read_connection(&database);
        assert_eq!(
            scalar(&connection, "SELECT COUNT(*) FROM permanent_journal"),
            journal_before,
            "replay publishes no journal record"
        );
    }
    assert_eq!(
        run.handle.current().period,
        40,
        "replay leaves the live current period untouched"
    );

    let cancelled = AtomicBool::new(true);
    assert!(matches!(
        run.handle.replay_to_period(10, &cancelled),
        Err(ReplayError::Cancelled)
    ));
    assert!(matches!(
        run.handle.replay_to_period(41, &cancel),
        Err(ReplayError::FuturePeriod {
            current: 40,
            requested: 41
        })
    ));
}

#[test]
fn open_refuses_a_bit_flip_in_the_current_chunk() {
    let root = TempRoot::new();
    let database = root.path("campaign.sqlite3");
    let mut run = RetentionRun::start(&database);
    run.advance_to(14);
    drop(run.handle);
    flip_payload_bytes(
        &database,
        "state_chunk",
        "chunk_id = (SELECT chunk_id FROM snapshot_chunk
             WHERE snapshot_id = (SELECT current_snapshot_id FROM save_manifest WHERE id = 1)
             LIMIT 1)",
    );
    assert!(
        SqliteCampaignStore::open(&database, build_identity()).is_err(),
        "a damaged current root refuses before mutation"
    );
}

#[test]
fn a_cold_detail_bit_flip_is_diagnosed_on_access_not_at_open() {
    let root = TempRoot::new();
    let database = root.path("campaign.sqlite3");
    let mut run = RetentionRun::start(&database);
    run.advance_to(14);
    drop(run.handle);
    flip_payload_bytes(&database, "recent_detail", "period = 5");
    let reopened = SqliteCampaignStore::open(&database, build_identity())
        .expect("cold detail damage does not block an otherwise valid open");
    assert!(
        matches!(
            reopened.read_recent_detail(5, DetailFamily::Prices),
            Err(SaveError::CorruptPayload {
                table: "recent_detail",
                ..
            })
        ),
        "reading the damaged detail range diagnoses it explicitly"
    );
    assert_eq!(
        reopened
            .read_recent_detail(14, DetailFamily::Prices)
            .expect("an intact cold row still reads")
            .len(),
        1
    );
}

#[test]
fn an_acquired_fact_bit_flip_refuses_its_read_and_its_replay() {
    let root = TempRoot::new();
    let database = root.path("campaign.sqlite3");
    let mut run = RetentionRun::start(&database);
    run.advance_to(14);
    drop(run.handle);
    flip_payload_bytes(&database, "knowledge_grant", "knowledge_seq = 1");
    let reopened = SqliteCampaignStore::open(&database, build_identity())
        .expect("the campaign still opens around a damaged grant payload");
    assert!(matches!(
        reopened.read_granted_subject(
            42_u64.to_be_bytes(),
            SubjectKind::County,
            b"michigan-wayne",
            14
        ),
        Err(SaveError::CorruptPayload {
            table: "knowledge_grant",
            ..
        })
    ));
    assert!(matches!(
        reopened.replay_to_period(10, &AtomicBool::new(false)),
        Err(ReplayError::Save(SaveError::CorruptPayload {
            table: "knowledge_grant",
            ..
        }))
    ));
}

#[test]
fn a_command_resolution_bit_flip_refuses_the_open() {
    let root = TempRoot::new();
    let database = root.path("campaign.sqlite3");
    let mut handle = SqliteCampaignStore::create(&database, admitted_content(), admitted_opening())
        .expect("the campaign is created once");
    handle
        .accept_command(
            PlayerCommand {
                period: 1,
                actor_id: [9; 8],
                payload: b"organizer-command".to_vec(),
            },
            NONCE_ONE,
        )
        .expect("the command is durably accepted");
    handle
        .commit(prepared(
            1,
            world_identity(0),
            vec![chunk(ChunkSection::WorldRegisters, 0, register(1))],
            Vec::new(),
            Vec::new(),
        ))
        .expect("period one commits");
    drop(handle);

    let raw = raw_connection(&database);
    raw.execute(
        "UPDATE permanent_journal SET period = 7 WHERE kind = ?1",
        params![JournalKind::ResolvedBatch.code()],
    )
    .expect("the test flips the resolution period");
    drop(raw);
    assert!(matches!(
        SqliteCampaignStore::open(&database, build_identity()),
        Err(SaveError::CorruptManifest { .. })
    ));
}

#[test]
fn recover_to_new_save_drops_cold_damage_and_preserves_the_evidence() {
    let root = TempRoot::new();
    let database = root.path("campaign.sqlite3");
    let mut run = RetentionRun::start(&database);
    run.advance_to(40);
    let recovered_world = run.receipts[39].world_hash;
    drop(run.handle);
    flip_payload_bytes(&database, "recent_detail", "period = 35");
    let source_before = fs::read(&database).expect("the damaged source is readable");
    let destination = root.path("recovered.sqlite3");
    let recovery =
        SqliteCampaignStore::recover_to_new_save(&database, &destination, build_identity())
            .expect("cold damage recovers into a clean independent file");
    assert!(recovery.integrity_verified);
    assert_eq!(recovery.recovered_period, 40);
    assert_eq!(recovery.world_hash, recovered_world);
    assert!(recovery.cold_rows_dropped >= 1);
    assert_eq!(
        fs::read(&database).expect("the damaged source is readable"),
        source_before,
        "recovery never overwrites the sole original"
    );
    let reopened = SqliteCampaignStore::open(&destination, build_identity())
        .expect("the recovered destination is a complete campaign");
    assert_eq!(reopened.current().period, 40);
    assert_eq!(
        reopened
            .read_recent_detail(35, DetailFamily::Prices)
            .expect("the dropped cold row reads as absent"),
        Vec::new()
    );
    assert_eq!(
        reopened
            .read_recent_detail(40, DetailFamily::Prices)
            .expect("intact cold detail survives recovery")
            .len(),
        1
    );
    assert!(
        matches!(
            SqliteCampaignStore::recover_to_new_save(&database, &destination, build_identity()),
            Err(SaveError::ExportDestinationExists)
        ),
        "recovery never overwrites an existing destination"
    );
}

#[test]
fn recover_to_new_save_refuses_a_damaged_current_root() {
    let root = TempRoot::new();
    let database = root.path("campaign.sqlite3");
    let mut run = RetentionRun::start(&database);
    run.advance_to(14);
    drop(run.handle);
    flip_payload_bytes(
        &database,
        "state_chunk",
        "chunk_id = (SELECT chunk_id FROM snapshot_chunk
             WHERE snapshot_id = (SELECT current_snapshot_id FROM save_manifest WHERE id = 1)
             LIMIT 1)",
    );
    let destination = root.path("unrecoverable.sqlite3");
    assert!(
        SqliteCampaignStore::recover_to_new_save(&database, &destination, build_identity())
            .is_err(),
        "a damaged current root cannot be recovered into a fabricated save"
    );
    assert!(
        !destination.exists(),
        "a refused recovery publishes no destination"
    );
}
