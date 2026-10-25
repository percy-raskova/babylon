//! Exact nine-table `STRICT` schema and per-connection durable pragmas.
//!
//! The schema is the published physical contract from Chapter 06 of the
//! architecture reset: nine tables, explicit length and registry checks,
//! enforced foreign keys, WAL journaling, `synchronous=FULL`, incremental
//! auto-vacuum and the required partial and unique indexes. Opaque payloads are
//! never queried with JSON extraction; indexed columns select a bounded set.

use std::time::Duration;

use rusqlite::Connection;

use crate::sqlite_runtime_pin;
use crate::sqlite_store::SaveError;

/// Schema format version pinned in `PRAGMA user_version`.
pub const SCHEMA_VERSION: u32 = 1;

/// Writer serialization timeout required by the durable commit contract.
pub const BUSY_TIMEOUT: Duration = Duration::from_secs(5);

/// Exact nine table names owned by the campaign database.
pub const EXPECTED_TABLES: [&str; 9] = [
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

/// Exact required index names owned by the campaign database.
pub const EXPECTED_INDEXES: [&str; 12] = [
    "journal_accepted_command_period",
    "journal_command_nonce",
    "journal_period",
    "journal_record_key",
    "journal_subject",
    "journal_unresolved_command",
    "knowledge_acquisition",
    "knowledge_lookup",
    "snapshot_chunk_reachability",
    "snapshot_historical_period",
    "snapshot_single_current",
    "snapshot_single_opening",
];

/// Closed snapshot role registry.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum SnapshotRole {
    /// The immutable opening at period zero.
    Opening = 1,
    /// The single restart root replaced by every successful commit.
    Current = 2,
    /// One retained thirteen-period checkpoint.
    Historical = 3,
}

impl SnapshotRole {
    /// Return the exact versioned integer stored in `snapshot.role`.
    #[must_use]
    pub const fn code(self) -> i64 {
        self as i64
    }
}

/// Complete DDL for the nine published tables and their required indexes.
///
/// `role`, `kind`, `section`, `family` and `codec` values are closed registries
/// compiled into the reader. Length checks describe `BLOB` width, never a
/// `BLOB(N)` affinity assumption. No `REAL` column stores money, counts,
/// tickets or canonical binary64 bits.
const SCHEMA_DDL: &str = "
CREATE TABLE save_manifest (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    schema_version INTEGER NOT NULL CHECK (schema_version >= 1),
    campaign_id BLOB NOT NULL CHECK (length(campaign_id) = 16),
    build_hash BLOB NOT NULL CHECK (length(build_hash) = 32),
    content_hash BLOB NOT NULL CHECK (length(content_hash) = 32),
    current_snapshot_id INTEGER NOT NULL REFERENCES snapshot(snapshot_id),
    journal_tail_seq INTEGER NOT NULL CHECK (journal_tail_seq >= 0),
    journal_tail_hash BLOB NOT NULL CHECK (length(journal_tail_hash) = 32),
    knowledge_tail_seq INTEGER NOT NULL CHECK (knowledge_tail_seq >= 0),
    knowledge_tail_hash BLOB NOT NULL CHECK (length(knowledge_tail_hash) = 32)
) STRICT;

CREATE TABLE content_entry (
    kind INTEGER NOT NULL CHECK (kind BETWEEN 1 AND 4),
    entry_key BLOB NOT NULL CHECK (length(entry_key) > 0),
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    codec INTEGER NOT NULL CHECK (codec IN (1, 2)),
    raw_len INTEGER NOT NULL CHECK (raw_len BETWEEN 0 AND 4194304),
    raw_hash BLOB NOT NULL CHECK (length(raw_hash) = 32),
    payload BLOB NOT NULL,
    PRIMARY KEY (kind, entry_key, ordinal)
) STRICT;

CREATE TABLE state_chunk (
    chunk_id INTEGER PRIMARY KEY,
    section INTEGER NOT NULL CHECK (section BETWEEN 1 AND 9),
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    codec INTEGER NOT NULL CHECK (codec IN (1, 2)),
    raw_len INTEGER NOT NULL CHECK (raw_len BETWEEN 0 AND 4194304),
    raw_hash BLOB NOT NULL CHECK (length(raw_hash) = 32),
    payload BLOB NOT NULL
) STRICT;

CREATE TABLE snapshot (
    snapshot_id INTEGER PRIMARY KEY,
    role INTEGER NOT NULL CHECK (role IN (1, 2, 3)),
    period INTEGER NOT NULL CHECK (period >= 0),
    world_hash BLOB NOT NULL CHECK (length(world_hash) = 32),
    state_hash BLOB NOT NULL CHECK (length(state_hash) = 32),
    manifest_bytes BLOB NOT NULL,
    committed_journal_seq INTEGER NOT NULL CHECK (committed_journal_seq >= 0),
    committed_journal_hash BLOB NOT NULL CHECK (length(committed_journal_hash) = 32),
    knowledge_seq INTEGER NOT NULL CHECK (knowledge_seq >= 0),
    knowledge_hash BLOB NOT NULL CHECK (length(knowledge_hash) = 32),
    CHECK (role <> 1 OR period = 0)
) STRICT;

CREATE TABLE snapshot_chunk (
    snapshot_id INTEGER NOT NULL REFERENCES snapshot(snapshot_id),
    section INTEGER NOT NULL CHECK (section BETWEEN 1 AND 9),
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    chunk_id INTEGER NOT NULL REFERENCES state_chunk(chunk_id),
    PRIMARY KEY (snapshot_id, section, ordinal)
) STRICT;

CREATE TABLE permanent_journal (
    journal_seq INTEGER PRIMARY KEY CHECK (journal_seq > 0),
    kind INTEGER NOT NULL CHECK (kind BETWEEN 1 AND 6),
    period INTEGER NOT NULL CHECK (period >= 0),
    actor_id BLOB CHECK (actor_id IS NULL OR length(actor_id) = 8),
    subject_kind INTEGER CHECK (subject_kind BETWEEN 1 AND 10),
    subject_id BLOB,
    nonce BLOB CHECK (nonce IS NULL OR length(nonce) = 16),
    record_key BLOB,
    codec INTEGER NOT NULL CHECK (codec IN (1, 2)),
    raw_len INTEGER NOT NULL CHECK (raw_len BETWEEN 0 AND 16777216),
    raw_hash BLOB NOT NULL CHECK (length(raw_hash) = 32),
    payload BLOB NOT NULL,
    previous_hash BLOB NOT NULL CHECK (length(previous_hash) = 32),
    entry_hash BLOB NOT NULL CHECK (length(entry_hash) = 32),
    resolved_period INTEGER CHECK (resolved_period IS NULL OR resolved_period >= 0),
    resolution_seq INTEGER CHECK (
        resolution_seq IS NULL
        OR (resolution_seq > 0 AND resolution_seq <> journal_seq)
    ) REFERENCES permanent_journal(journal_seq),
    CHECK ((subject_kind IS NULL) = (subject_id IS NULL)),
    CHECK (subject_id IS NULL OR length(subject_id) > 0),
    CHECK ((resolved_period IS NULL) = (resolution_seq IS NULL))
) STRICT;

CREATE TABLE knowledge_grant (
    knowledge_seq INTEGER PRIMARY KEY CHECK (knowledge_seq > 0),
    player_id BLOB NOT NULL CHECK (length(player_id) = 8),
    subject_kind INTEGER NOT NULL CHECK (subject_kind BETWEEN 1 AND 10),
    subject_id BLOB NOT NULL CHECK (length(subject_id) > 0),
    grant_key INTEGER NOT NULL,
    acquired_period INTEGER NOT NULL CHECK (acquired_period >= 0),
    source_journal_seq INTEGER NOT NULL REFERENCES permanent_journal(journal_seq),
    payload BLOB NOT NULL,
    previous_hash BLOB NOT NULL CHECK (length(previous_hash) = 32),
    entry_hash BLOB NOT NULL CHECK (length(entry_hash) = 32)
) STRICT;

CREATE TABLE service_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    service_seq INTEGER NOT NULL CHECK (service_seq >= 0),
    codec INTEGER NOT NULL CHECK (codec IN (1, 2)),
    raw_len INTEGER NOT NULL CHECK (raw_len BETWEEN 0 AND 1048576),
    raw_hash BLOB NOT NULL CHECK (length(raw_hash) = 32),
    payload BLOB NOT NULL
) STRICT;

CREATE TABLE recent_detail (
    period INTEGER NOT NULL CHECK (period >= 1),
    family INTEGER NOT NULL CHECK (family BETWEEN 1 AND 37),
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    codec INTEGER NOT NULL CHECK (codec IN (1, 2)),
    raw_len INTEGER NOT NULL CHECK (raw_len BETWEEN 0 AND 4194304),
    raw_hash BLOB NOT NULL CHECK (length(raw_hash) = 32),
    payload BLOB NOT NULL,
    PRIMARY KEY (period, family, ordinal)
) STRICT;

CREATE UNIQUE INDEX snapshot_single_opening ON snapshot(role) WHERE role = 1;
CREATE UNIQUE INDEX snapshot_single_current ON snapshot(role) WHERE role = 2;
CREATE UNIQUE INDEX snapshot_historical_period ON snapshot(period) WHERE role = 3;
CREATE INDEX snapshot_chunk_reachability ON snapshot_chunk(chunk_id);

CREATE INDEX journal_period ON permanent_journal(period, journal_seq);
CREATE INDEX journal_subject
    ON permanent_journal(subject_kind, subject_id, period, journal_seq);
CREATE UNIQUE INDEX journal_command_nonce
    ON permanent_journal(nonce) WHERE nonce IS NOT NULL;
CREATE UNIQUE INDEX journal_record_key
    ON permanent_journal(kind, record_key) WHERE record_key IS NOT NULL;
CREATE UNIQUE INDEX journal_accepted_command_period
    ON permanent_journal(period) WHERE kind = 1;
CREATE INDEX journal_unresolved_command
    ON permanent_journal(period) WHERE kind = 1 AND resolved_period IS NULL;

CREATE INDEX knowledge_lookup
    ON knowledge_grant(
        player_id, subject_kind, subject_id, grant_key, acquired_period, knowledge_seq
    );
CREATE UNIQUE INDEX knowledge_acquisition
    ON knowledge_grant(player_id, subject_kind, subject_id, grant_key, source_journal_seq);
";

/// Apply the pinned runtime identity and the durable per-connection pragmas.
///
/// `auto_vacuum=INCREMENTAL` must be set before the schema creates any table, so
/// a fresh campaign file is configured first and installed second.
///
/// # Errors
///
/// Refuses a mismatched linked `SQLite` runtime, a write-ahead log that cannot
/// be enabled, a busy timeout that cannot be set, or a `SQLite` failure.
pub fn configure_connection(connection: &Connection) -> Result<(), SaveError> {
    sqlite_runtime_pin::verify_sqlite_runtime()?;
    // `auto_vacuum` only takes effect on an empty database, so it is set before
    // the write-ahead log touches the file header.
    connection.pragma_update(None, "auto_vacuum", 2)?;
    let journal_mode: String =
        connection.query_row("PRAGMA journal_mode = WAL", [], |row| row.get(0))?;
    if !journal_mode.eq_ignore_ascii_case("wal") {
        return Err(SaveError::WalUnavailable);
    }
    connection.pragma_update(None, "synchronous", 2)?;
    connection.pragma_update(None, "foreign_keys", "ON")?;
    connection.busy_timeout(BUSY_TIMEOUT)?;
    Ok(())
}

/// Install the nine-table schema into an empty configured database.
///
/// # Errors
///
/// Refuses an already versioned database, an unversioned database that already
/// owns tables, an auto-vacuum mode that will not reclaim incrementally, or a
/// `SQLite` failure. A failed installation rolls back without a partial schema.
pub fn install_schema(connection: &Connection) -> Result<(), SaveError> {
    let version = user_version(connection)?;
    if version == i64::from(SCHEMA_VERSION) {
        return Err(SaveError::SchemaMismatch {
            reason: "the schema is already installed",
        });
    }
    if version != 0 {
        return Err(SaveError::SchemaVersion {
            expected: SCHEMA_VERSION,
            actual: u32::try_from(version).unwrap_or(u32::MAX),
        });
    }
    let tables: i64 = connection.query_row(
        "SELECT COUNT(*) FROM sqlite_master
         WHERE type = 'table' AND name NOT LIKE 'sqlite_%'",
        [],
        |row| row.get(0),
    )?;
    if tables != 0 {
        return Err(SaveError::SchemaMismatch {
            reason: "unversioned tables already exist",
        });
    }
    let auto_vacuum: i64 = connection.query_row("PRAGMA auto_vacuum", [], |row| row.get(0))?;
    if auto_vacuum != 2 {
        return Err(SaveError::PragmaMismatch {
            pragma: "auto_vacuum",
            expected: "INCREMENTAL",
            actual: auto_vacuum.to_string(),
        });
    }

    let transaction = connection.unchecked_transaction()?;
    transaction.execute_batch(SCHEMA_DDL)?;
    transaction.pragma_update(None, "user_version", SCHEMA_VERSION)?;
    transaction.commit()?;
    Ok(())
}

/// Verify that one open database carries the exact versioned nine-table schema.
///
/// # Errors
///
/// Refuses an unsupported schema version, a missing or extra user table, a
/// table that is not `STRICT`, or a `SQLite` failure.
pub fn verify_installed_schema(connection: &Connection) -> Result<(), SaveError> {
    let version = user_version(connection)?;
    if version != i64::from(SCHEMA_VERSION) {
        return Err(SaveError::SchemaVersion {
            expected: SCHEMA_VERSION,
            actual: u32::try_from(version).unwrap_or(u32::MAX),
        });
    }

    let mut statement = connection.prepare(
        "SELECT name, strict FROM pragma_table_list
         WHERE schema = 'main' AND type = 'table' AND name NOT LIKE 'sqlite_%'
         ORDER BY name",
    )?;
    let mut rows = statement.query([])?;
    let mut names: Vec<String> = Vec::new();
    while let Some(row) = rows.next()? {
        let name: String = row.get(0)?;
        let strict: i64 = row.get(1)?;
        if strict != 1 {
            return Err(SaveError::SchemaMismatch {
                reason: "a published table is not STRICT",
            });
        }
        names.push(name);
    }
    let installed: Vec<&str> = names.iter().map(String::as_str).collect();
    if installed != EXPECTED_TABLES {
        return Err(SaveError::SchemaMismatch {
            reason: "the published table set is not exact",
        });
    }

    let mut statement = connection.prepare(
        "SELECT name FROM sqlite_master
         WHERE type = 'index' AND name NOT LIKE 'sqlite_autoindex_%' ORDER BY name",
    )?;
    let mut rows = statement.query([])?;
    let mut indexes: Vec<String> = Vec::new();
    while let Some(row) = rows.next()? {
        indexes.push(row.get(0)?);
    }
    let installed: Vec<&str> = indexes.iter().map(String::as_str).collect();
    if installed != EXPECTED_INDEXES {
        return Err(SaveError::SchemaMismatch {
            reason: "the required index set is not exact",
        });
    }
    Ok(())
}

fn user_version(connection: &Connection) -> Result<i64, SaveError> {
    connection
        .query_row("PRAGMA user_version", [], |row| row.get(0))
        .map_err(SaveError::from)
}
