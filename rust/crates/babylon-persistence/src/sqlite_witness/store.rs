//! Bounded `SQLite` witness storage for two canonical periods.
//!
//! The witness stores opaque canonical frames and caller-supplied canonical
//! identities. It never interprets material or practice semantics.

use std::cell::Cell;
use std::ffi::OsString;
use std::fmt::Formatter;
use std::fmt::Result as FmtResult;
use std::fs;
use std::io::ErrorKind;
use std::path::Path;
use std::path::PathBuf;
use std::time::Duration;
use std::time::Instant;
use std::time::SystemTime;

use rusqlite::backup::Backup;
use rusqlite::params;
use rusqlite::Connection;
use rusqlite::OpenFlags;
use rusqlite::TransactionBehavior;

use babylon_kernel::content_digest;

use crate::sqlite_runtime_pin;
use crate::sqlite_runtime_pin::SqlitePinError;

/// Exact witness schema version stored in `PRAGMA user_version` and the manifest.
pub const WITNESS_SCHEMA_VERSION: u32 = 1;
/// Width of an accepted-command nonce.
pub const WITNESS_NONCE_BYTES: usize = 16;
/// Ceiling for captured opening content, matching the state chunk allowance.
pub const MAX_WITNESS_OPENING_BYTES: usize = 4 * 1024 * 1024;
/// Ceiling for one complete canonical material register frame.
pub const MAX_WITNESS_REGISTER_BYTES: usize = 4 * 1024 * 1024;
/// Ceiling for one complete canonical receipt frame.
pub const MAX_WITNESS_RECEIPT_BYTES: usize = 16 * 1024 * 1024;
/// Ceiling for one permanent journal payload.
pub const MAX_WITNESS_JOURNAL_PAYLOAD_BYTES: usize = 16 * 1024 * 1024;
/// Ceiling for one scoped knowledge payload.
pub const MAX_WITNESS_SCOPED_PAYLOAD_BYTES: usize = 1024 * 1024;

const LEDGER_DOMAIN: &[u8] = b"babylon.sqlite-witness.ledger.v1\0";
const JOURNAL_DOMAIN: &[u8] = b"babylon.sqlite-witness.journal.v1\0";
const KNOWLEDGE_DOMAIN: &[u8] = b"babylon.sqlite-witness.knowledge.v1\0";
const CANDIDATE_DOMAIN: &[u8] = b"babylon.sqlite-witness.candidate.v1\0";
const MAX_SUBJECT_BYTES: usize = 64;
const FOUNDATION_KEY: &[u8] = b"foundation";
const OPENING_PERIOD: u64 = 0;

const SCHEMA: &str = "
CREATE TABLE save_manifest (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    schema_version INTEGER NOT NULL,
    foundation_hash BLOB NOT NULL CHECK (length(foundation_hash) = 32),
    opening_register_hash BLOB NOT NULL CHECK (length(opening_register_hash) = 32),
    current_period INTEGER NOT NULL CHECK (current_period >= 0),
    current_world_hash BLOB CHECK (
        current_world_hash IS NULL OR length(current_world_hash) = 32
    ),
    journal_tail_seq INTEGER NOT NULL CHECK (journal_tail_seq >= 0),
    journal_tail_hash BLOB NOT NULL CHECK (length(journal_tail_hash) = 32),
    knowledge_tail_seq INTEGER NOT NULL CHECK (knowledge_tail_seq >= 0),
    knowledge_tail_hash BLOB NOT NULL CHECK (length(knowledge_tail_hash) = 32)
) STRICT;

CREATE TABLE content_entry (
    kind INTEGER NOT NULL,
    entry_key BLOB NOT NULL,
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    raw_len INTEGER NOT NULL CHECK (raw_len >= 0),
    raw_hash BLOB NOT NULL CHECK (length(raw_hash) = 32),
    payload BLOB NOT NULL,
    PRIMARY KEY (kind, entry_key, ordinal)
) STRICT;

CREATE TABLE snapshot (
    period INTEGER PRIMARY KEY CHECK (period >= 0),
    world_hash BLOB NOT NULL CHECK (length(world_hash) = 32),
    state_hash BLOB NOT NULL CHECK (length(state_hash) = 32),
    candidate_hash BLOB NOT NULL CHECK (length(candidate_hash) = 32),
    register BLOB NOT NULL,
    register_hash BLOB NOT NULL CHECK (length(register_hash) = 32),
    receipts BLOB NOT NULL,
    receipts_hash BLOB NOT NULL CHECK (length(receipts_hash) = 32),
    journal_tail_seq INTEGER NOT NULL CHECK (journal_tail_seq >= 0),
    journal_tail_hash BLOB NOT NULL CHECK (length(journal_tail_hash) = 32),
    knowledge_tail_seq INTEGER NOT NULL CHECK (knowledge_tail_seq >= 0),
    knowledge_tail_hash BLOB NOT NULL CHECK (length(knowledge_tail_hash) = 32)
) STRICT;

CREATE TABLE permanent_journal (
    seq INTEGER PRIMARY KEY CHECK (seq > 0),
    kind INTEGER NOT NULL,
    period INTEGER NOT NULL CHECK (period >= 0),
    nonce BLOB CHECK (nonce IS NULL OR length(nonce) = 16),
    subject_kind BLOB,
    subject_id BLOB,
    payload BLOB NOT NULL,
    raw_len INTEGER NOT NULL CHECK (raw_len >= 0),
    raw_hash BLOB NOT NULL CHECK (length(raw_hash) = 32),
    previous_hash BLOB NOT NULL CHECK (length(previous_hash) = 32),
    entry_hash BLOB NOT NULL CHECK (length(entry_hash) = 32),
    resolved_period INTEGER CHECK (resolved_period IS NULL OR resolved_period >= 0),
    resolution_seq INTEGER CHECK (resolution_seq IS NULL OR resolution_seq > 0),
    CHECK ((subject_kind IS NULL) = (subject_id IS NULL)),
    CHECK ((resolved_period IS NULL) = (resolution_seq IS NULL))
) STRICT;

CREATE TABLE accepted_command (
    period INTEGER PRIMARY KEY CHECK (period > 0),
    nonce BLOB NOT NULL UNIQUE CHECK (length(nonce) = 16),
    payload BLOB NOT NULL,
    raw_len INTEGER NOT NULL CHECK (raw_len >= 0),
    raw_hash BLOB NOT NULL CHECK (length(raw_hash) = 32),
    accepted_seq INTEGER NOT NULL UNIQUE REFERENCES permanent_journal(seq)
) STRICT;

CREATE TABLE knowledge_grant (
    seq INTEGER PRIMARY KEY CHECK (seq > 0),
    player_id BLOB NOT NULL CHECK (length(player_id) = 8),
    subject_kind BLOB NOT NULL,
    subject_id BLOB NOT NULL,
    acquired_period INTEGER NOT NULL CHECK (acquired_period > 0),
    observed_period INTEGER NOT NULL CHECK (observed_period >= 0),
    payload BLOB NOT NULL,
    raw_len INTEGER NOT NULL CHECK (raw_len >= 0),
    raw_hash BLOB NOT NULL CHECK (length(raw_hash) = 32),
    source_journal_seq INTEGER NOT NULL REFERENCES permanent_journal(seq),
    previous_hash BLOB NOT NULL CHECK (length(previous_hash) = 32),
    entry_hash BLOB NOT NULL CHECK (length(entry_hash) = 32),
    UNIQUE (player_id, subject_kind, subject_id, acquired_period)
) STRICT;

CREATE UNIQUE INDEX journal_command_nonce
    ON permanent_journal(nonce) WHERE nonce IS NOT NULL AND kind = 1;
CREATE INDEX journal_period ON permanent_journal(period, seq);
CREATE INDEX journal_subject
    ON permanent_journal(subject_kind, subject_id, period, seq);
CREATE INDEX journal_unresolved
    ON permanent_journal(period) WHERE resolved_period IS NULL;
CREATE INDEX knowledge_lookup
    ON knowledge_grant(player_id, subject_kind, acquired_period, seq);

INSERT INTO save_manifest (
    id, schema_version, foundation_hash, opening_register_hash,
    current_period, current_world_hash, journal_tail_seq, journal_tail_hash,
    knowledge_tail_seq, knowledge_tail_hash
) VALUES (
    1, 1, zeroblob(32), zeroblob(32), 0, NULL, 0, zeroblob(32), 0, zeroblob(32)
);

PRAGMA user_version = 1;
";

/// Closed journal kinds admitted by the witness.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum WitnessJournalKind {
    /// An organizer command accepted before the period advanced.
    OrganizerCommandAccepted = 1,
    /// The same organizer command consumed once by its period commit.
    OrganizerCommandConsumed = 2,
    /// A shipment or obligation that remains unresolved across a boundary.
    FreightUnresolved = 3,
    /// The period commit that resolves one earlier unresolved subject.
    FreightResolved = 4,
    /// A governed choice receipt committed with this period.
    ChoiceReceipt = 5,
}

impl WitnessJournalKind {
    const fn code(self) -> i64 {
        self as i64
    }
}

/// One immutable journal record supplied with a period commit.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct WitnessJournalEntry<'a> {
    /// Closed record kind.
    pub kind: WitnessJournalKind,
    /// Optional subject registry tag.
    pub subject_kind: Option<&'a [u8]>,
    /// Optional subject identity bytes.
    pub subject_id: Option<&'a [u8]>,
    /// Opaque canonical payload bytes.
    pub payload: &'a [u8],
}

/// One fact or authority reference earned by a period commit.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct WitnessKnowledgeGrant<'a> {
    /// Player who earned the authority.
    pub player_id: u64,
    /// Subject registry tag.
    pub subject_kind: &'a [u8],
    /// Subject identity bytes.
    pub subject_id: &'a [u8],
    /// Period the granting observation was taken, which never substitutes for
    /// the acquisition period when authority is checked.
    pub observed_period: u64,
    /// Opaque canonical payload bytes.
    pub payload: &'a [u8],
}

/// One complete canonical period candidate offered to the witness.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct WitnessPeriodCommit<'a> {
    /// Period this candidate completes.
    pub period: u64,
    /// Canonical world identity the caller recorded for the period.
    pub world_hash: [u8; 32],
    /// Canonical material state identity the caller recorded for the period.
    pub state_hash: [u8; 32],
    /// Complete canonical material register frame.
    pub register: &'a [u8],
    /// Complete canonical receipt frame.
    pub receipts: &'a [u8],
    /// Ordered permanent journal records.
    pub journal: &'a [WitnessJournalEntry<'a>],
    /// Facts or authorities earned in this period.
    pub knowledge: &'a [WitnessKnowledgeGrant<'a>],
}

/// Whether an acceptance inserted a new commitment or replayed an existing one.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum WitnessAcceptanceKind {
    /// The nonce and period were free, so the commitment was inserted.
    Inserted,
    /// The exact nonce and bytes were already durable.
    Existing,
}

/// Durable acknowledgement of one accepted organizer command.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct WitnessAcceptance {
    /// Period the command applies to.
    pub period: u64,
    /// Command nonce.
    pub nonce: [u8; WITNESS_NONCE_BYTES],
    /// Digest of the accepted canonical payload.
    pub payload_hash: [u8; 32],
    /// Journal sequence of the immutable acceptance record.
    pub acceptance_seq: u64,
    /// Whether the acknowledgement inserted or replayed.
    pub kind: WitnessAcceptanceKind,
}

/// Whether a commit inserted a new period or replayed an identical one.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum WitnessCommitKind {
    /// The period was inserted.
    Inserted,
    /// The same canonical candidate was already committed.
    Existing,
}

/// Durable acknowledgement of one committed period.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct WitnessCommitReceipt {
    /// Committed period.
    pub period: u64,
    /// Canonical world identity recorded for the period.
    pub world_hash: [u8; 32],
    /// Canonical material state identity recorded for the period.
    pub state_hash: [u8; 32],
    /// Journal tail after this commit.
    pub journal_tail_seq: u64,
    /// Hash of the journal tail entry.
    pub journal_tail_hash: [u8; 32],
    /// Knowledge tail after this commit.
    pub knowledge_tail_seq: u64,
    /// Hash of the knowledge tail entry.
    pub knowledge_tail_hash: [u8; 32],
    /// Time spent inside the commit transaction.
    pub commit_ns: u64,
    /// Whether the commit inserted or replayed.
    pub kind: WitnessCommitKind,
}

/// Verified result of one online export.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct WitnessExportReport {
    /// Bytes in the published destination file.
    pub destination_bytes: u64,
    /// Pages in the published destination database.
    pub page_count: u64,
    /// Whether the destination passed `PRAGMA integrity_check`.
    pub integrity_verified: bool,
    /// Wall time spent exporting and verifying.
    pub elapsed_ns: u64,
}

/// Separately measured witness storage and timing metrics.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct WitnessStorageFootprint {
    /// Main database file bytes.
    pub main_db_bytes: u64,
    /// Write-ahead log file bytes.
    pub wal_bytes: u64,
    /// Bytes held by index b-trees.
    pub index_bytes: u64,
    /// Bytes of the most recent published export.
    pub export_bytes: u64,
    /// Wall time from open start to a ready store.
    pub cold_reopen_ns: u64,
    /// Time spent inside the most recent commit transaction.
    pub commit_ns: u64,
    /// Resident set size when the host exposes it.
    pub rss_bytes: Option<u64>,
}

/// Why the witness refused an operation.
#[derive(Debug)]
pub enum WitnessError {
    /// The linked `SQLite` runtime is not the pinned build.
    RuntimePin(SqlitePinError),
    /// `SQLite` refused a statement.
    Sqlite(rusqlite::Error),
    /// Host file I/O failed.
    Io(std::io::Error),
    /// The open database has an unsupported witness schema version.
    SchemaVersion {
        /// Version this witness requires.
        expected: u32,
        /// Version found in the database.
        actual: u32,
    },
    /// The database carries an unexpected table set.
    SchemaMismatch,
    /// The write-ahead log could not be enabled.
    WalUnavailable,
    /// An opening was already captured and cannot be replaced.
    OpeningAlreadyCaptured,
    /// A period commit requires a captured opening first.
    OpeningRequired,
    /// A required payload was empty or short.
    TruncatedPayload {
        /// Field that failed admission.
        field: &'static str,
    },
    /// A payload exceeded its bounded allowance.
    PayloadTooLarge {
        /// Field that failed admission.
        field: &'static str,
        /// Bounded allowance in bytes.
        limit: usize,
        /// Supplied length in bytes.
        actual: usize,
    },
    /// A journal subject tag or identity was empty, oversized or unpaired.
    InvalidSubject {
        /// Field that failed admission.
        field: &'static str,
    },
    /// A period commit tried to forge a witness-owned journal kind.
    ReservedJournalKind {
        /// Rejected integer code.
        code: i64,
    },
    /// The offered period is not the next or an already committed period.
    WrongPeriod {
        /// Period the witness requires.
        expected: u64,
        /// Period offered.
        actual: u64,
    },
    /// An already committed period was offered different canonical bytes.
    ConflictingPeriodCommit {
        /// Period that already has a different commitment.
        period: u64,
    },
    /// A period already has one immutable accepted commitment.
    PeriodCommitmentAlreadyAccepted {
        /// Period that already has an accepted commitment.
        period: u64,
    },
    /// A nonce was reused with different bytes or for a different period.
    ConflictingNonce,
    /// No earned grant discloses the requested subject at that period.
    UndisclosedSubject,
    /// The scoped read requested a period beyond the committed present.
    FuturePeriod {
        /// Highest committed period.
        current: u64,
        /// Requested period.
        requested: u64,
    },
    /// A resolution named no unresolved freight subject.
    UnresolvedFreightMissing,
    /// Earned knowledge had no period journal record to cite.
    KnowledgeSourceMissing,
    /// Two grants for the same identity and acquisition period were supplied.
    DuplicateKnowledgeGrant,
    /// Stored bytes no longer match their recorded length or hash.
    IntegrityMismatch {
        /// Column or field that failed verification.
        field: &'static str,
    },
    /// A sequence or period did not fit the checked `SQLite` integer range.
    Arithmetic,
    /// The export destination already exists and is never overwritten.
    ExportDestinationExists,
    /// The exported database failed integrity or identity verification.
    ExportIdentityMismatch,
    /// A deterministic test seam aborted the operation.
    InjectedFault,
}

impl std::fmt::Display for WitnessError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> FmtResult {
        match self {
            Self::RuntimePin(error) => write!(formatter, "SQLite runtime pin refused: {error}"),
            Self::Sqlite(error) => {
                write!(formatter, "SQLite refused the witness statement: {error}")
            }
            Self::Io(error) => write!(formatter, "witness host I/O refused: {error}"),
            Self::SchemaVersion { expected, actual } => write!(
                formatter,
                "witness schema version {actual} does not match required {expected}"
            ),
            Self::SchemaMismatch => write!(formatter, "witness schema is missing or foreign"),
            Self::WalUnavailable => write!(formatter, "write-ahead logging is unavailable"),
            Self::OpeningAlreadyCaptured => {
                write!(formatter, "the witness opening is already captured")
            }
            Self::OpeningRequired => write!(formatter, "the witness opening is not captured"),
            Self::TruncatedPayload { field } => {
                write!(formatter, "witness {field} payload is empty or truncated")
            }
            Self::PayloadTooLarge {
                field,
                limit,
                actual,
            } => write!(
                formatter,
                "witness {field} payload of {actual} bytes exceeds the {limit}-byte allowance"
            ),
            Self::InvalidSubject { field } => {
                write!(formatter, "witness {field} subject is invalid")
            }
            Self::ReservedJournalKind { code } => {
                write!(formatter, "witness journal kind {code} is witness-owned")
            }
            Self::WrongPeriod { expected, actual } => {
                write!(
                    formatter,
                    "witness expected period {expected}, received {actual}"
                )
            }
            Self::ConflictingPeriodCommit { period } => write!(
                formatter,
                "witness period {period} already has a different canonical commitment"
            ),
            Self::PeriodCommitmentAlreadyAccepted { period } => write!(
                formatter,
                "witness period {period} already has an accepted commitment"
            ),
            Self::ConflictingNonce => {
                write!(formatter, "witness nonce was reused with different bytes")
            }
            Self::UndisclosedSubject => write!(
                formatter,
                "witness has no earned grant for that subject and period"
            ),
            Self::FuturePeriod { current, requested } => write!(
                formatter,
                "witness requested period {requested} beyond committed period {current}"
            ),
            Self::UnresolvedFreightMissing => write!(
                formatter,
                "witness resolution named no unresolved freight subject"
            ),
            Self::KnowledgeSourceMissing => {
                write!(formatter, "witness knowledge needs a period journal record")
            }
            Self::DuplicateKnowledgeGrant => {
                write!(
                    formatter,
                    "witness knowledge identity repeats in one period"
                )
            }
            Self::IntegrityMismatch { field } => {
                write!(
                    formatter,
                    "witness {field} failed length or hash verification"
                )
            }
            Self::Arithmetic => write!(formatter, "witness sequence exceeded its checked range"),
            Self::ExportDestinationExists => {
                write!(formatter, "witness export destination already exists")
            }
            Self::ExportIdentityMismatch => {
                write!(
                    formatter,
                    "witness export failed integrity or identity verification"
                )
            }
            Self::InjectedFault => write!(formatter, "witness test seam aborted the operation"),
        }
    }
}

impl std::error::Error for WitnessError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::RuntimePin(error) => Some(error),
            Self::Sqlite(error) => Some(error),
            Self::Io(error) => Some(error),
            _ => None,
        }
    }
}

impl From<rusqlite::Error> for WitnessError {
    fn from(error: rusqlite::Error) -> Self {
        Self::Sqlite(error)
    }
}

impl From<SqlitePinError> for WitnessError {
    fn from(error: SqlitePinError) -> Self {
        Self::RuntimePin(error)
    }
}

impl From<std::io::Error> for WitnessError {
    fn from(error: std::io::Error) -> Self {
        Self::Io(error)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) enum FaultPoint {
    BeforeCommit,
    AfterAcceptBeforeAck,
    AfterCommitBeforeAck,
    DuringExport,
}

#[derive(Clone, Copy)]
struct Manifest {
    schema_version: u64,
    foundation_hash: [u8; 32],
    current_period: u64,
    journal_tail_seq: u64,
    journal_tail_hash: [u8; 32],
    knowledge_tail_seq: u64,
    knowledge_tail_hash: [u8; 32],
}

#[derive(Clone, Copy)]
struct SnapshotHeader {
    world_hash: [u8; 32],
    state_hash: [u8; 32],
    candidate_hash: [u8; 32],
    journal_tail_seq: u64,
    journal_tail_hash: [u8; 32],
    knowledge_tail_seq: u64,
    knowledge_tail_hash: [u8; 32],
}

/// A temporary single-writer `SQLite` witness for two canonical periods.
pub struct SqliteWitnessStore {
    connection: Connection,
    path: PathBuf,
    current_period: u64,
    journal_tail_seq: u64,
    journal_tail_hash: [u8; 32],
    knowledge_tail_seq: u64,
    knowledge_tail_hash: [u8; 32],
    cold_reopen_ns: u64,
    commit_ns: Cell<u64>,
    export_bytes: Cell<u64>,
    fault: Cell<Option<FaultPoint>>,
}

impl std::fmt::Debug for SqliteWitnessStore {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> FmtResult {
        formatter
            .debug_struct("SqliteWitnessStore")
            .field("path", &self.path)
            .field("current_period", &self.current_period)
            .field("journal_tail_seq", &self.journal_tail_seq)
            .field("knowledge_tail_seq", &self.knowledge_tail_seq)
            .finish_non_exhaustive()
    }
}

impl SqliteWitnessStore {
    /// Open or create one isolated witness database at an exact path.
    ///
    /// # Errors
    ///
    /// Refuses a mismatched `SQLite` runtime, an unsupported schema version, a
    /// foreign table set, or a host I/O or `SQLite` failure.
    pub fn open_at(path: &Path) -> Result<Self, WitnessError> {
        let started = Instant::now();
        sqlite_runtime_pin::verify_sqlite_runtime()?;
        let connection = Connection::open(path)?;
        let journal_mode: String =
            connection.query_row("PRAGMA journal_mode = WAL", [], |row| row.get(0))?;
        if journal_mode != "wal" {
            return Err(WitnessError::WalUnavailable);
        }
        connection.pragma_update(None, "synchronous", "FULL")?;
        connection.pragma_update(None, "foreign_keys", "ON")?;
        connection.busy_timeout(Duration::from_secs(5))?;

        let version: i64 = connection.query_row("PRAGMA user_version", [], |row| row.get(0))?;
        let tables: i64 = connection.query_row(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'",
            [],
            |row| row.get(0),
        )?;
        if version == 0 {
            if tables != 0 {
                return Err(WitnessError::SchemaMismatch);
            }
            connection.execute_batch(SCHEMA)?;
        } else if version != i64::from(WITNESS_SCHEMA_VERSION) {
            return Err(WitnessError::SchemaVersion {
                expected: WITNESS_SCHEMA_VERSION,
                actual: u32::try_from(version).unwrap_or(u32::MAX),
            });
        }

        let manifest = read_manifest(&connection)?;
        if manifest.schema_version != u64::from(WITNESS_SCHEMA_VERSION) {
            return Err(WitnessError::SchemaVersion {
                expected: WITNESS_SCHEMA_VERSION,
                actual: u32::try_from(manifest.schema_version).unwrap_or(u32::MAX),
            });
        }
        let cold_reopen_ns = elapsed_ns(started);
        Ok(Self {
            connection,
            path: path.to_path_buf(),
            current_period: manifest.current_period,
            journal_tail_seq: manifest.journal_tail_seq,
            journal_tail_hash: manifest.journal_tail_hash,
            knowledge_tail_seq: manifest.knowledge_tail_seq,
            knowledge_tail_hash: manifest.knowledge_tail_hash,
            cold_reopen_ns,
            commit_ns: Cell::new(0),
            export_bytes: Cell::new(0),
            fault: Cell::new(None),
        })
    }

    /// Capture the opening content and initial register exactly once.
    ///
    /// # Errors
    ///
    /// Refuses a second capture, empty or oversized frames, or a storage fault.
    pub fn capture_opening(
        &mut self,
        foundation: &[u8],
        initial_register: &[u8],
    ) -> Result<(), WitnessError> {
        require_bounded("foundation", foundation, MAX_WITNESS_OPENING_BYTES)?;
        require_bounded(
            "initial_register",
            initial_register,
            MAX_WITNESS_REGISTER_BYTES,
        )?;
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)?;
        let manifest = read_manifest(&transaction)?;
        if manifest.foundation_hash != [0_u8; 32] || manifest.current_period != OPENING_PERIOD {
            return Err(WitnessError::OpeningAlreadyCaptured);
        }
        let foundation_hash = content_digest::sha256_of(foundation);
        let register_hash = content_digest::sha256_of(initial_register);
        let candidate_hash = opening_candidate_hash(foundation_hash, register_hash);
        transaction.execute(
            "INSERT INTO content_entry (kind, entry_key, ordinal, raw_len, raw_hash, payload)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
            params![
                0_i64,
                FOUNDATION_KEY,
                0_i64,
                checked_i64(
                    u64::try_from(foundation.len()).map_err(|_| WitnessError::Arithmetic)?
                )?,
                &foundation_hash[..],
                foundation
            ],
        )?;
        transaction.execute(
            "INSERT INTO snapshot (
                period, world_hash, state_hash, candidate_hash, register,
                register_hash, receipts, receipts_hash, journal_tail_seq,
                journal_tail_hash, knowledge_tail_seq, knowledge_tail_hash
             ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)",
            params![
                checked_i64(OPENING_PERIOD)?,
                &[0_u8; 32][..],
                &register_hash[..],
                &candidate_hash[..],
                initial_register,
                &register_hash[..],
                &[] as &[u8],
                &content_digest::sha256_of(&[])[..],
                0_i64,
                &[0_u8; 32][..],
                0_i64,
                &[0_u8; 32][..]
            ],
        )?;
        transaction.execute(
            "UPDATE save_manifest SET foundation_hash = ?1, opening_register_hash = ?2
             WHERE id = 1",
            params![&foundation_hash[..], &register_hash[..]],
        )?;
        transaction.commit()?;
        Ok(())
    }

    /// Durably accept one organizer command for the next period.
    ///
    /// # Errors
    ///
    /// Refuses a wrong period, a conflicting nonce, or a second distinct
    /// commitment for the same period.
    #[allow(
        clippy::too_many_lines,
        reason = "one transaction keeps the acceptance, journal tail and ack atomic"
    )]
    pub fn accept_command(
        &mut self,
        period: u64,
        nonce: [u8; WITNESS_NONCE_BYTES],
        payload: &[u8],
    ) -> Result<WitnessAcceptance, WitnessError> {
        require_bounded("command", payload, MAX_WITNESS_JOURNAL_PAYLOAD_BYTES)?;
        let payload_hash = content_digest::sha256_of(payload);
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)?;
        let manifest = read_manifest(&transaction)?;
        if manifest.foundation_hash == [0_u8; 32] {
            return Err(WitnessError::OpeningRequired);
        }
        {
            use rusqlite::OptionalExtension;
            let existing = transaction
                .query_row(
                    "SELECT period, payload, accepted_seq FROM accepted_command
                     WHERE nonce = ?1",
                    params![&nonce[..]],
                    |row| {
                        Ok((
                            row.get::<_, i64>(0)?,
                            row.get::<_, Vec<u8>>(1)?,
                            row.get::<_, i64>(2)?,
                        ))
                    },
                )
                .optional()?;
            if let Some((existing_period, existing_payload, accepted_seq)) = existing {
                let existing_period = to_u64(existing_period, "accepted_command.period")?;
                if existing_period != period || existing_payload != payload {
                    return Err(WitnessError::ConflictingNonce);
                }
                drop(transaction);
                return Ok(WitnessAcceptance {
                    period,
                    nonce,
                    payload_hash,
                    acceptance_seq: to_u64(accepted_seq, "accepted_command.accepted_seq")?,
                    kind: WitnessAcceptanceKind::Existing,
                });
            }
        }
        let expected = manifest
            .current_period
            .checked_add(1)
            .ok_or(WitnessError::Arithmetic)?;
        if period != expected {
            return Err(WitnessError::WrongPeriod {
                expected,
                actual: period,
            });
        }
        let period_taken: i64 = transaction.query_row(
            "SELECT COUNT(*) FROM accepted_command WHERE period = ?1",
            params![checked_i64(period)?],
            |row| row.get(0),
        )?;
        if period_taken != 0 {
            return Err(WitnessError::PeriodCommitmentAlreadyAccepted { period });
        }
        let seq = manifest
            .journal_tail_seq
            .checked_add(1)
            .ok_or(WitnessError::Arithmetic)?;
        let entry_hash = journal_entry_hash(
            seq,
            WitnessJournalKind::OrganizerCommandAccepted,
            period,
            Some(nonce),
            None,
            None,
            payload_hash,
            manifest.journal_tail_hash,
        );
        transaction.execute(
            "INSERT INTO permanent_journal (
                seq, kind, period, nonce, subject_kind, subject_id, payload,
                raw_len, raw_hash, previous_hash, entry_hash
             ) VALUES (?1, ?2, ?3, ?4, NULL, NULL, ?5, ?6, ?7, ?8, ?9)",
            params![
                checked_i64(seq)?,
                WitnessJournalKind::OrganizerCommandAccepted.code(),
                checked_i64(period)?,
                &nonce[..],
                payload,
                checked_i64(u64::try_from(payload.len()).map_err(|_| WitnessError::Arithmetic)?)?,
                &payload_hash[..],
                &manifest.journal_tail_hash[..],
                &entry_hash[..]
            ],
        )?;
        transaction.execute(
            "INSERT INTO accepted_command (
                period, nonce, payload, raw_len, raw_hash, accepted_seq
             ) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
            params![
                checked_i64(period)?,
                &nonce[..],
                payload,
                checked_i64(u64::try_from(payload.len()).map_err(|_| WitnessError::Arithmetic)?)?,
                &payload_hash[..],
                checked_i64(seq)?
            ],
        )?;
        transaction.execute(
            "UPDATE save_manifest SET journal_tail_seq = ?1, journal_tail_hash = ?2
             WHERE id = 1",
            params![checked_i64(seq)?, &entry_hash[..]],
        )?;
        transaction.commit()?;
        self.journal_tail_seq = seq;
        self.journal_tail_hash = entry_hash;
        if self.fault.get() == Some(FaultPoint::AfterAcceptBeforeAck) {
            self.fault.set(None);
            return Err(WitnessError::InjectedFault);
        }
        Ok(WitnessAcceptance {
            period,
            nonce,
            payload_hash,
            acceptance_seq: seq,
            kind: WitnessAcceptanceKind::Inserted,
        })
    }

    /// Commit one complete canonical period candidate.
    ///
    /// # Errors
    ///
    /// Refuses a wrong or conflicting period, malformed payloads, a missing
    /// knowledge source, or a storage fault.
    #[allow(
        clippy::too_many_lines,
        reason = "one immediate transaction keeps every period section atomic"
    )]
    pub fn commit_period(
        &mut self,
        input: &WitnessPeriodCommit<'_>,
    ) -> Result<WitnessCommitReceipt, WitnessError> {
        validate_candidate(input)?;
        if input.period == OPENING_PERIOD {
            return Err(WitnessError::WrongPeriod {
                expected: 1,
                actual: 0,
            });
        }
        let register_hash = content_digest::sha256_of(input.register);
        let receipts_hash = content_digest::sha256_of(input.receipts);
        let candidate_hash = candidate_identity(input, register_hash, receipts_hash);
        if self.fault.get() == Some(FaultPoint::BeforeCommit) {
            self.fault.set(None);
            return Err(WitnessError::InjectedFault);
        }

        let started = Instant::now();
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)?;
        let manifest = read_manifest(&transaction)?;
        if manifest.foundation_hash == [0_u8; 32] {
            return Err(WitnessError::OpeningRequired);
        }
        if let Some(snapshot) = read_snapshot_header(&transaction, input.period)? {
            drop(transaction);
            if snapshot.candidate_hash != candidate_hash {
                return Err(WitnessError::ConflictingPeriodCommit {
                    period: input.period,
                });
            }
            self.commit_ns.set(elapsed_ns(started));
            return Ok(WitnessCommitReceipt {
                period: input.period,
                world_hash: snapshot.world_hash,
                state_hash: snapshot.state_hash,
                journal_tail_seq: snapshot.journal_tail_seq,
                journal_tail_hash: snapshot.journal_tail_hash,
                knowledge_tail_seq: snapshot.knowledge_tail_seq,
                knowledge_tail_hash: snapshot.knowledge_tail_hash,
                commit_ns: elapsed_ns(started),
                kind: WitnessCommitKind::Existing,
            });
        }
        let expected = manifest
            .current_period
            .checked_add(1)
            .ok_or(WitnessError::Arithmetic)?;
        if input.period != expected {
            return Err(WitnessError::WrongPeriod {
                expected,
                actual: input.period,
            });
        }

        let mut journal_seq = manifest.journal_tail_seq;
        let mut journal_hash = manifest.journal_tail_hash;
        let accepted = {
            use rusqlite::OptionalExtension;
            transaction
                .query_row(
                    "SELECT nonce, payload, raw_hash FROM accepted_command
                     WHERE period = ?1",
                    params![checked_i64(input.period)?],
                    |row| {
                        Ok((
                            row.get::<_, Vec<u8>>(0)?,
                            row.get::<_, Vec<u8>>(1)?,
                            row.get::<_, Vec<u8>>(2)?,
                        ))
                    },
                )
                .optional()?
        };
        if let Some((nonce, payload, raw_hash)) = accepted {
            let nonce: [u8; WITNESS_NONCE_BYTES] =
                nonce
                    .try_into()
                    .map_err(|_| WitnessError::IntegrityMismatch {
                        field: "accepted_command.nonce",
                    })?;
            let raw_hash = to_array32(raw_hash, "accepted_command.raw_hash")?;
            if content_digest::sha256_of(&payload) != raw_hash {
                return Err(WitnessError::IntegrityMismatch {
                    field: "accepted_command.payload",
                });
            }
            journal_seq = journal_seq.checked_add(1).ok_or(WitnessError::Arithmetic)?;
            let entry_hash = journal_entry_hash(
                journal_seq,
                WitnessJournalKind::OrganizerCommandConsumed,
                input.period,
                Some(nonce),
                None,
                None,
                raw_hash,
                journal_hash,
            );
            transaction.execute(
                "INSERT INTO permanent_journal (
                    seq, kind, period, nonce, subject_kind, subject_id, payload,
                    raw_len, raw_hash, previous_hash, entry_hash
                 ) VALUES (?1, ?2, ?3, ?4, NULL, NULL, ?5, ?6, ?7, ?8, ?9)",
                params![
                    checked_i64(journal_seq)?,
                    WitnessJournalKind::OrganizerCommandConsumed.code(),
                    checked_i64(input.period)?,
                    &nonce[..],
                    payload,
                    checked_i64(
                        u64::try_from(payload.len()).map_err(|_| WitnessError::Arithmetic)?
                    )?,
                    &raw_hash[..],
                    &journal_hash[..],
                    &entry_hash[..]
                ],
            )?;
            journal_hash = entry_hash;
        }

        let mut period_had_journal = journal_seq > manifest.journal_tail_seq;
        for entry in input.journal {
            journal_seq = journal_seq.checked_add(1).ok_or(WitnessError::Arithmetic)?;
            let payload_hash = content_digest::sha256_of(entry.payload);
            let entry_hash = journal_entry_hash(
                journal_seq,
                entry.kind,
                input.period,
                None,
                entry.subject_kind,
                entry.subject_id,
                payload_hash,
                journal_hash,
            );
            transaction.execute(
                "INSERT INTO permanent_journal (
                    seq, kind, period, nonce, subject_kind, subject_id, payload,
                    raw_len, raw_hash, previous_hash, entry_hash
                 ) VALUES (?1, ?2, ?3, NULL, ?4, ?5, ?6, ?7, ?8, ?9, ?10)",
                params![
                    checked_i64(journal_seq)?,
                    entry.kind.code(),
                    checked_i64(input.period)?,
                    entry.subject_kind,
                    entry.subject_id,
                    entry.payload,
                    checked_i64(
                        u64::try_from(entry.payload.len()).map_err(|_| WitnessError::Arithmetic)?
                    )?,
                    &payload_hash[..],
                    &journal_hash[..],
                    &entry_hash[..]
                ],
            )?;
            if entry.kind == WitnessJournalKind::FreightResolved {
                let (Some(subject_kind), Some(subject_id)) = (entry.subject_kind, entry.subject_id)
                else {
                    return Err(WitnessError::InvalidSubject { field: "journal" });
                };
                let unresolved = {
                    use rusqlite::OptionalExtension;
                    transaction
                        .query_row(
                            "SELECT seq FROM permanent_journal
                             WHERE kind = ?1 AND subject_kind = ?2 AND subject_id = ?3
                               AND resolved_period IS NULL AND seq < ?4
                             ORDER BY seq DESC LIMIT 1",
                            params![
                                WitnessJournalKind::FreightUnresolved.code(),
                                subject_kind,
                                subject_id,
                                checked_i64(journal_seq)?
                            ],
                            |row| row.get::<_, i64>(0),
                        )
                        .optional()?
                };
                let Some(unresolved) = unresolved else {
                    return Err(WitnessError::UnresolvedFreightMissing);
                };
                let updated = transaction.execute(
                    "UPDATE permanent_journal
                     SET resolved_period = ?1, resolution_seq = ?2
                     WHERE seq = ?3 AND resolved_period IS NULL",
                    params![
                        checked_i64(input.period)?,
                        checked_i64(journal_seq)?,
                        unresolved
                    ],
                )?;
                if updated != 1 {
                    return Err(WitnessError::UnresolvedFreightMissing);
                }
            }
            journal_hash = entry_hash;
        }
        period_had_journal |= journal_seq > manifest.journal_tail_seq;
        if !input.knowledge.is_empty() && !period_had_journal {
            return Err(WitnessError::KnowledgeSourceMissing);
        }

        let mut knowledge_seq = manifest.knowledge_tail_seq;
        let mut knowledge_hash = manifest.knowledge_tail_hash;
        for grant in input.knowledge {
            let player = grant.player_id.to_be_bytes();
            let duplicated: i64 = transaction.query_row(
                "SELECT COUNT(*) FROM knowledge_grant
                 WHERE player_id = ?1 AND subject_kind = ?2 AND subject_id = ?3
                   AND acquired_period = ?4",
                params![
                    &player[..],
                    grant.subject_kind,
                    grant.subject_id,
                    checked_i64(input.period)?
                ],
                |row| row.get(0),
            )?;
            if duplicated != 0 {
                return Err(WitnessError::DuplicateKnowledgeGrant);
            }
            knowledge_seq = knowledge_seq
                .checked_add(1)
                .ok_or(WitnessError::Arithmetic)?;
            let payload_hash = content_digest::sha256_of(grant.payload);
            let entry_hash = knowledge_entry_hash(
                knowledge_seq,
                player,
                grant.subject_kind,
                grant.subject_id,
                input.period,
                grant.observed_period,
                payload_hash,
                knowledge_hash,
            );
            transaction.execute(
                "INSERT INTO knowledge_grant (
                    seq, player_id, subject_kind, subject_id, acquired_period,
                    observed_period, payload, raw_len, raw_hash,
                    source_journal_seq, previous_hash, entry_hash
                 ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)",
                params![
                    checked_i64(knowledge_seq)?,
                    &player[..],
                    grant.subject_kind,
                    grant.subject_id,
                    checked_i64(input.period)?,
                    checked_i64(grant.observed_period)?,
                    grant.payload,
                    checked_i64(
                        u64::try_from(grant.payload.len()).map_err(|_| WitnessError::Arithmetic)?
                    )?,
                    &payload_hash[..],
                    checked_i64(journal_seq)?,
                    &knowledge_hash[..],
                    &entry_hash[..]
                ],
            )?;
            knowledge_hash = entry_hash;
        }

        transaction.execute(
            "INSERT INTO snapshot (
                period, world_hash, state_hash, candidate_hash, register,
                register_hash, receipts, receipts_hash, journal_tail_seq,
                journal_tail_hash, knowledge_tail_seq, knowledge_tail_hash
             ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)",
            params![
                checked_i64(input.period)?,
                &input.world_hash[..],
                &input.state_hash[..],
                &candidate_hash[..],
                input.register,
                &register_hash[..],
                input.receipts,
                &receipts_hash[..],
                checked_i64(journal_seq)?,
                &journal_hash[..],
                checked_i64(knowledge_seq)?,
                &knowledge_hash[..]
            ],
        )?;
        transaction.execute(
            "UPDATE save_manifest SET
                current_period = ?1, current_world_hash = ?2,
                journal_tail_seq = ?3, journal_tail_hash = ?4,
                knowledge_tail_seq = ?5, knowledge_tail_hash = ?6
             WHERE id = 1",
            params![
                checked_i64(input.period)?,
                &input.world_hash[..],
                checked_i64(journal_seq)?,
                &journal_hash[..],
                checked_i64(knowledge_seq)?,
                &knowledge_hash[..]
            ],
        )?;
        transaction.commit()?;
        let commit_ns = elapsed_ns(started);
        self.current_period = input.period;
        self.journal_tail_seq = journal_seq;
        self.journal_tail_hash = journal_hash;
        self.knowledge_tail_seq = knowledge_seq;
        self.knowledge_tail_hash = knowledge_hash;
        self.commit_ns.set(commit_ns);
        if self.fault.get() == Some(FaultPoint::AfterCommitBeforeAck) {
            self.fault.set(None);
            return Err(WitnessError::InjectedFault);
        }
        Ok(WitnessCommitReceipt {
            period: input.period,
            world_hash: input.world_hash,
            state_hash: input.state_hash,
            journal_tail_seq: journal_seq,
            journal_tail_hash: journal_hash,
            knowledge_tail_seq: knowledge_seq,
            knowledge_tail_hash: knowledge_hash,
            commit_ns,
            kind: WitnessCommitKind::Inserted,
        })
    }

    /// Read one player-authorized subject as of a committed period.
    ///
    /// # Errors
    ///
    /// Refuses a future period, an undisclosed subject, or stored bytes that
    /// no longer match their recorded length or hash.
    pub fn read_scoped_subject(
        &self,
        player_id: u64,
        subject_kind: &[u8],
        as_of_period: u64,
    ) -> Result<Vec<u8>, WitnessError> {
        if as_of_period > self.current_period {
            return Err(WitnessError::FuturePeriod {
                current: self.current_period,
                requested: as_of_period,
            });
        }
        validate_subject_bytes("subject_kind", subject_kind)?;
        let player = player_id.to_be_bytes();
        let stored = {
            use rusqlite::OptionalExtension;
            self.connection
                .query_row(
                    "SELECT payload, raw_len, raw_hash FROM knowledge_grant
                     WHERE player_id = ?1 AND subject_kind = ?2
                       AND acquired_period <= ?3
                     ORDER BY seq DESC LIMIT 1",
                    params![&player[..], subject_kind, checked_i64(as_of_period)?],
                    |row| {
                        Ok((
                            row.get::<_, Vec<u8>>(0)?,
                            row.get::<_, i64>(1)?,
                            row.get::<_, Vec<u8>>(2)?,
                        ))
                    },
                )
                .optional()?
        };
        let Some((payload, raw_len, raw_hash)) = stored else {
            return Err(WitnessError::UndisclosedSubject);
        };
        let raw_len = to_u64(raw_len, "knowledge_grant.raw_len")?;
        if u64::try_from(payload.len()).map_err(|_| WitnessError::Arithmetic)? != raw_len {
            return Err(WitnessError::IntegrityMismatch {
                field: "knowledge_grant.payload",
            });
        }
        if payload.len() > MAX_WITNESS_SCOPED_PAYLOAD_BYTES {
            return Err(WitnessError::IntegrityMismatch {
                field: "knowledge_grant.payload",
            });
        }
        let raw_hash = to_array32(raw_hash, "knowledge_grant.raw_hash")?;
        if content_digest::sha256_of(&payload) != raw_hash {
            return Err(WitnessError::IntegrityMismatch {
                field: "knowledge_grant.payload",
            });
        }
        Ok(payload)
    }

    /// Publish one verified online backup to a new destination.
    ///
    /// # Errors
    ///
    /// Refuses an existing destination, a backup or integrity failure, or a
    /// host I/O failure.
    pub fn export_online_backup(
        &self,
        destination: &Path,
    ) -> Result<WitnessExportReport, WitnessError> {
        let started = Instant::now();
        if destination.exists() {
            return Err(WitnessError::ExportDestinationExists);
        }
        let temp = temporary_export_path(destination)?;
        let mut target = Connection::open(&temp)?;
        {
            let backup = Backup::new(&self.connection, &mut target)?;
            backup.run_to_completion(64, Duration::ZERO, None)?;
        }
        drop(target);
        if self.fault.get() == Some(FaultPoint::DuringExport) {
            self.fault.set(None);
            remove_if_present(&temp)?;
            return Err(WitnessError::InjectedFault);
        }

        let verified = Connection::open_with_flags(&temp, OpenFlags::SQLITE_OPEN_READ_ONLY)?;
        let integrity: String =
            verified.query_row("PRAGMA integrity_check", [], |row| row.get(0))?;
        if integrity != "ok" {
            drop(verified);
            remove_if_present(&temp)?;
            return Err(WitnessError::ExportIdentityMismatch);
        }
        let page_count: i64 = verified.query_row("PRAGMA page_count", [], |row| row.get(0))?;
        let exported = read_manifest(&verified)?;
        let source = read_manifest(&self.connection)?;
        if exported.foundation_hash != source.foundation_hash
            || exported.current_period != source.current_period
            || exported.journal_tail_seq != source.journal_tail_seq
            || exported.journal_tail_hash != source.journal_tail_hash
            || exported.knowledge_tail_seq != source.knowledge_tail_seq
            || exported.knowledge_tail_hash != source.knowledge_tail_hash
        {
            drop(verified);
            remove_if_present(&temp)?;
            return Err(WitnessError::ExportIdentityMismatch);
        }
        drop(verified);
        if let Err(error) = fs::rename(&temp, destination) {
            remove_if_present(&temp)?;
            return Err(WitnessError::Io(error));
        }
        let destination_bytes = fs::metadata(destination)?.len();
        self.export_bytes.set(destination_bytes);
        Ok(WitnessExportReport {
            destination_bytes,
            page_count: to_u64(page_count, "export.page_count")?,
            integrity_verified: true,
            elapsed_ns: elapsed_ns(started),
        })
    }

    /// Measure separate storage, timing and memory metrics.
    ///
    /// # Errors
    ///
    /// Refuses a metadata or `SQLite` query failure.
    pub fn measure_footprint(&self) -> Result<WitnessStorageFootprint, WitnessError> {
        let main_db_bytes = fs::metadata(&self.path)?.len();
        let mut wal_path = self.path.clone().into_os_string();
        wal_path.push("-wal");
        let wal_bytes = fs::metadata(PathBuf::from(wal_path))
            .map(|metadata| metadata.len())
            .unwrap_or(0);
        let index_bytes: i64 = self.connection.query_row(
            "SELECT COALESCE(SUM(pgsize), 0) FROM dbstat
             WHERE name NOT IN (SELECT name FROM sqlite_master WHERE type = 'table')",
            [],
            |row| row.get(0),
        )?;
        Ok(WitnessStorageFootprint {
            main_db_bytes,
            wal_bytes,
            index_bytes: to_u64(index_bytes, "footprint.index_bytes")?,
            export_bytes: self.export_bytes.get(),
            cold_reopen_ns: self.cold_reopen_ns,
            commit_ns: self.commit_ns.get(),
            rss_bytes: resident_bytes(),
        })
    }

    #[cfg(test)]
    pub(super) fn inject_fault(&self, fault: FaultPoint) {
        self.fault.set(Some(fault));
    }
}

fn validate_candidate(input: &WitnessPeriodCommit<'_>) -> Result<(), WitnessError> {
    require_bounded("register", input.register, MAX_WITNESS_REGISTER_BYTES)?;
    require_bounded("receipts", input.receipts, MAX_WITNESS_RECEIPT_BYTES)?;
    for entry in input.journal {
        require_bounded("journal", entry.payload, MAX_WITNESS_JOURNAL_PAYLOAD_BYTES)?;
        if !matches!(
            entry.kind,
            WitnessJournalKind::FreightUnresolved
                | WitnessJournalKind::FreightResolved
                | WitnessJournalKind::ChoiceReceipt
        ) {
            return Err(WitnessError::ReservedJournalKind {
                code: entry.kind.code(),
            });
        }
        validate_subject_pair("journal", entry.subject_kind, entry.subject_id)?;
    }
    for grant in input.knowledge {
        require_bounded("knowledge", grant.payload, MAX_WITNESS_SCOPED_PAYLOAD_BYTES)?;
        validate_subject_bytes("knowledge_subject_kind", grant.subject_kind)?;
        validate_subject_bytes("knowledge_subject_id", grant.subject_id)?;
        if grant.observed_period > input.period {
            return Err(WitnessError::FuturePeriod {
                current: input.period,
                requested: grant.observed_period,
            });
        }
    }
    Ok(())
}

fn validate_subject_pair(
    field: &'static str,
    subject_kind: Option<&[u8]>,
    subject_id: Option<&[u8]>,
) -> Result<(), WitnessError> {
    match (subject_kind, subject_id) {
        (None, None) => Ok(()),
        (Some(kind), Some(id)) => {
            validate_subject_bytes(field, kind)?;
            validate_subject_bytes(field, id)
        }
        _ => Err(WitnessError::InvalidSubject { field }),
    }
}

fn validate_subject_bytes(field: &'static str, bytes: &[u8]) -> Result<(), WitnessError> {
    if bytes.is_empty() || bytes.len() > MAX_SUBJECT_BYTES {
        return Err(WitnessError::InvalidSubject { field });
    }
    Ok(())
}

fn require_bounded(field: &'static str, bytes: &[u8], limit: usize) -> Result<(), WitnessError> {
    if bytes.is_empty() {
        return Err(WitnessError::TruncatedPayload { field });
    }
    if bytes.len() > limit {
        return Err(WitnessError::PayloadTooLarge {
            field,
            limit,
            actual: bytes.len(),
        });
    }
    Ok(())
}

fn read_manifest(connection: &Connection) -> Result<Manifest, WitnessError> {
    use rusqlite::OptionalExtension;
    let row = connection
        .query_row(
            "SELECT schema_version, foundation_hash, current_period,
                    journal_tail_seq, journal_tail_hash, knowledge_tail_seq,
                    knowledge_tail_hash
             FROM save_manifest WHERE id = 1",
            [],
            |row| {
                Ok((
                    row.get::<_, i64>(0)?,
                    row.get::<_, Vec<u8>>(1)?,
                    row.get::<_, i64>(2)?,
                    row.get::<_, i64>(3)?,
                    row.get::<_, Vec<u8>>(4)?,
                    row.get::<_, i64>(5)?,
                    row.get::<_, Vec<u8>>(6)?,
                ))
            },
        )
        .optional()?;
    let Some((
        schema_version,
        foundation_hash,
        current_period,
        journal_tail_seq,
        journal_tail_hash,
        knowledge_tail_seq,
        knowledge_tail_hash,
    )) = row
    else {
        return Err(WitnessError::SchemaMismatch);
    };
    Ok(Manifest {
        schema_version: to_u64(schema_version, "save_manifest.schema_version")?,
        foundation_hash: to_array32(foundation_hash, "save_manifest.foundation_hash")?,
        current_period: to_u64(current_period, "save_manifest.current_period")?,
        journal_tail_seq: to_u64(journal_tail_seq, "save_manifest.journal_tail_seq")?,
        journal_tail_hash: to_array32(journal_tail_hash, "save_manifest.journal_tail_hash")?,
        knowledge_tail_seq: to_u64(knowledge_tail_seq, "save_manifest.knowledge_tail_seq")?,
        knowledge_tail_hash: to_array32(knowledge_tail_hash, "save_manifest.knowledge_tail_hash")?,
    })
}

fn read_snapshot_header(
    connection: &Connection,
    period: u64,
) -> Result<Option<SnapshotHeader>, WitnessError> {
    use rusqlite::OptionalExtension;
    let row = connection
        .query_row(
            "SELECT world_hash, state_hash, candidate_hash, journal_tail_seq,
                    journal_tail_hash, knowledge_tail_seq, knowledge_tail_hash
             FROM snapshot WHERE period = ?1",
            params![checked_i64(period)?],
            |row| {
                Ok((
                    row.get::<_, Vec<u8>>(0)?,
                    row.get::<_, Vec<u8>>(1)?,
                    row.get::<_, Vec<u8>>(2)?,
                    row.get::<_, i64>(3)?,
                    row.get::<_, Vec<u8>>(4)?,
                    row.get::<_, i64>(5)?,
                    row.get::<_, Vec<u8>>(6)?,
                ))
            },
        )
        .optional()?;
    let Some((
        world_hash,
        state_hash,
        candidate_hash,
        journal_tail_seq,
        journal_tail_hash,
        knowledge_tail_seq,
        knowledge_tail_hash,
    )) = row
    else {
        return Ok(None);
    };
    Ok(Some(SnapshotHeader {
        world_hash: to_array32(world_hash, "snapshot.world_hash")?,
        state_hash: to_array32(state_hash, "snapshot.state_hash")?,
        candidate_hash: to_array32(candidate_hash, "snapshot.candidate_hash")?,
        journal_tail_seq: to_u64(journal_tail_seq, "snapshot.journal_tail_seq")?,
        journal_tail_hash: to_array32(journal_tail_hash, "snapshot.journal_tail_hash")?,
        knowledge_tail_seq: to_u64(knowledge_tail_seq, "snapshot.knowledge_tail_seq")?,
        knowledge_tail_hash: to_array32(knowledge_tail_hash, "snapshot.knowledge_tail_hash")?,
    }))
}

fn opening_candidate_hash(foundation_hash: [u8; 32], register_hash: [u8; 32]) -> [u8; 32] {
    let mut bytes = Vec::new();
    bytes.extend_from_slice(LEDGER_DOMAIN);
    bytes.extend_from_slice(OPENING_PERIOD.to_be_bytes().as_slice());
    bytes.extend_from_slice(&foundation_hash);
    bytes.extend_from_slice(&register_hash);
    content_digest::sha256_of(&bytes)
}

fn candidate_identity(
    input: &WitnessPeriodCommit<'_>,
    register_hash: [u8; 32],
    receipts_hash: [u8; 32],
) -> [u8; 32] {
    let mut bytes = Vec::new();
    bytes.extend_from_slice(CANDIDATE_DOMAIN);
    bytes.extend_from_slice(&input.period.to_be_bytes());
    bytes.extend_from_slice(&input.world_hash);
    bytes.extend_from_slice(&input.state_hash);
    bytes.extend_from_slice(&register_hash);
    bytes.extend_from_slice(&receipts_hash);
    bytes.extend_from_slice(
        &u64::try_from(input.journal.len())
            .unwrap_or(u64::MAX)
            .to_be_bytes(),
    );
    for entry in input.journal {
        bytes.extend_from_slice(&entry.kind.code().to_be_bytes());
        push_subject(&mut bytes, entry.subject_kind, entry.subject_id);
        bytes.extend_from_slice(&content_digest::sha256_of(entry.payload));
    }
    bytes.extend_from_slice(
        &u64::try_from(input.knowledge.len())
            .unwrap_or(u64::MAX)
            .to_be_bytes(),
    );
    for grant in input.knowledge {
        bytes.extend_from_slice(&grant.player_id.to_be_bytes());
        bytes.extend_from_slice(&grant.observed_period.to_be_bytes());
        push_subject(&mut bytes, Some(grant.subject_kind), Some(grant.subject_id));
        bytes.extend_from_slice(&content_digest::sha256_of(grant.payload));
    }
    content_digest::sha256_of(&bytes)
}

fn push_subject(bytes: &mut Vec<u8>, subject_kind: Option<&[u8]>, subject_id: Option<&[u8]>) {
    match (subject_kind, subject_id) {
        (Some(kind), Some(id)) => {
            bytes.push(1);
            push_bytes(bytes, kind);
            push_bytes(bytes, id);
        }
        _ => bytes.push(0),
    }
}

fn push_bytes(bytes: &mut Vec<u8>, value: &[u8]) {
    bytes.extend_from_slice(&u64::try_from(value.len()).unwrap_or(u64::MAX).to_be_bytes());
    bytes.extend_from_slice(value);
}

#[allow(
    clippy::too_many_arguments,
    reason = "every immutable journal field enters the canonical hash chain"
)]
fn journal_entry_hash(
    seq: u64,
    kind: WitnessJournalKind,
    period: u64,
    nonce: Option<[u8; WITNESS_NONCE_BYTES]>,
    subject_kind: Option<&[u8]>,
    subject_id: Option<&[u8]>,
    payload_hash: [u8; 32],
    previous_hash: [u8; 32],
) -> [u8; 32] {
    let mut bytes = Vec::new();
    bytes.extend_from_slice(JOURNAL_DOMAIN);
    bytes.extend_from_slice(&seq.to_be_bytes());
    bytes.extend_from_slice(&kind.code().to_be_bytes());
    bytes.extend_from_slice(&period.to_be_bytes());
    match nonce {
        Some(nonce) => {
            bytes.push(1);
            bytes.extend_from_slice(&nonce);
        }
        None => bytes.push(0),
    }
    push_subject(&mut bytes, subject_kind, subject_id);
    bytes.extend_from_slice(&payload_hash);
    bytes.extend_from_slice(&previous_hash);
    content_digest::sha256_of(&bytes)
}

#[allow(
    clippy::too_many_arguments,
    reason = "every immutable knowledge field enters the canonical hash chain"
)]
fn knowledge_entry_hash(
    seq: u64,
    player: [u8; 8],
    subject_kind: &[u8],
    subject_id: &[u8],
    acquired_period: u64,
    observed_period: u64,
    payload_hash: [u8; 32],
    previous_hash: [u8; 32],
) -> [u8; 32] {
    let mut bytes = Vec::new();
    bytes.extend_from_slice(KNOWLEDGE_DOMAIN);
    bytes.extend_from_slice(&seq.to_be_bytes());
    bytes.extend_from_slice(&player);
    push_bytes(&mut bytes, subject_kind);
    push_bytes(&mut bytes, subject_id);
    bytes.extend_from_slice(&acquired_period.to_be_bytes());
    bytes.extend_from_slice(&observed_period.to_be_bytes());
    bytes.extend_from_slice(&payload_hash);
    bytes.extend_from_slice(&previous_hash);
    content_digest::sha256_of(&bytes)
}

fn to_array32(bytes: Vec<u8>, field: &'static str) -> Result<[u8; 32], WitnessError> {
    bytes
        .try_into()
        .map_err(|_| WitnessError::IntegrityMismatch { field })
}

fn to_u64(value: i64, field: &'static str) -> Result<u64, WitnessError> {
    u64::try_from(value).map_err(|_| WitnessError::IntegrityMismatch { field })
}

fn checked_i64(value: u64) -> Result<i64, WitnessError> {
    i64::try_from(value).map_err(|_| WitnessError::Arithmetic)
}

fn elapsed_ns(started: Instant) -> u64 {
    u64::try_from(started.elapsed().as_nanos()).unwrap_or(u64::MAX)
}

fn temporary_export_path(destination: &Path) -> Result<PathBuf, WitnessError> {
    let name = destination.file_name().ok_or_else(|| {
        WitnessError::Io(std::io::Error::new(
            ErrorKind::InvalidInput,
            "export destination has no file name",
        ))
    })?;
    let nanos = SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_err(|_| WitnessError::Arithmetic)?
        .as_nanos();
    let mut temp_name = OsString::from(".");
    temp_name.push(name);
    temp_name.push(format!(".{}.{nanos}.tmp", std::process::id()));
    Ok(destination.with_file_name(temp_name))
}

fn remove_if_present(path: &Path) -> Result<(), WitnessError> {
    match fs::remove_file(path) {
        Ok(()) => Ok(()),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Err(error) => Err(WitnessError::Io(error)),
    }
}

fn resident_bytes() -> Option<u64> {
    let statm = fs::read_to_string("/proc/self/statm").ok()?;
    let pages: u64 = statm.split_whitespace().nth(1)?.parse().ok()?;
    Some(pages.saturating_mul(4096))
}
