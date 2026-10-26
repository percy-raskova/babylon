//! Campaign lifecycle owner: create, open, accept, commit and export.
//!
//! One [`CampaignHandle`] owns the campaign database for its lifetime. Creation
//! writes the admitted content, the opening state and the opening snapshot
//! before the single `save_manifest` row. Opening re-reads only the committed
//! manifest, the current snapshot and the state chunks that snapshot reaches, so
//! the restart root costs `O(current_chunks)` and never scans historical
//! receipts. A commit prepares its chunks, journal records and knowledge grants
//! outside the write transaction, then inserts them in one `BEGIN IMMEDIATE`
//! transaction that updates `save_manifest` last.
//!
//! A committed period keeps a `Historical` snapshot row so a caller can replay
//! its exact canonical identity after a later period is committed. Retention
//! rotation, which turns that row into the thirteen-period roster, belongs to
//! Task 8 and is not implemented here.

use rusqlite::params;
use rusqlite::types::Type;
use rusqlite::Connection;
use rusqlite::OpenFlags;
use rusqlite::OptionalExtension;
use rusqlite::Result as SqliteResult;
use rusqlite::Row;
use rusqlite::TransactionBehavior;
use sha2::Digest;
use sha2::Sha256;
#[cfg(test)]
use std::cell::Cell;
use std::fmt::Formatter;
use std::fmt::Result as FmtResult;
use std::fs;
use std::io::Error;
use std::io::ErrorKind;
use std::path::Path;
use std::path::PathBuf;
use std::sync::atomic::AtomicBool;
use std::time::Instant;

use babylon_kernel::content_digest;
use uuid::Uuid;

use crate::identity::CampaignId;
use crate::sqlite_runtime_pin;
use crate::sqlite_store::archive_service;
use crate::sqlite_store::archive_service::DossierCompletion;
use crate::sqlite_store::archive_service::DossierRequest;
use crate::sqlite_store::archive_service::PublishedDossierReceipt;
use crate::sqlite_store::archive_service::ServiceError;
use crate::sqlite_store::archive_service::ServiceReceipt;
use crate::sqlite_store::chunks;
use crate::sqlite_store::chunks::ChunkSection;
use crate::sqlite_store::chunks::ContentEntryKind;
use crate::sqlite_store::chunks::DetailFamily;
use crate::sqlite_store::chunks::JournalKind;
use crate::sqlite_store::chunks::JournalRecordInput;
use crate::sqlite_store::chunks::JournalSubject;
use crate::sqlite_store::chunks::SubjectKind;
use crate::sqlite_store::codec;
use crate::sqlite_store::codec::PayloadBudget;
use crate::sqlite_store::codec::PayloadCodec;
use crate::sqlite_store::export;
use crate::sqlite_store::export::ExportIdentity;
use crate::sqlite_store::export::VerifiedExport;
use crate::sqlite_store::lock::CampaignLock;
use crate::sqlite_store::lock::SaveError;
use crate::sqlite_store::query;
use crate::sqlite_store::query::HistoryCursor;
use crate::sqlite_store::query::HistoryPage;
use crate::sqlite_store::query::PlayerQuery;
use crate::sqlite_store::query::PlayerResult;
use crate::sqlite_store::query::PlayerScope;
use crate::sqlite_store::query::ReadBoundary;
use crate::sqlite_store::query::ReadError;
use crate::sqlite_store::replay;
use crate::sqlite_store::replay::RecentDetailRow;
use crate::sqlite_store::replay::ReplayError;
use crate::sqlite_store::replay::VerifiedRecovery;
use crate::sqlite_store::replay::VerifiedReplayReconstruction;
use crate::sqlite_store::retention;
use crate::sqlite_store::retention::PeriodSummary;
use crate::sqlite_store::retention::RetentionAccountingReport;
use crate::sqlite_store::schema;
use crate::sqlite_store::schema::SnapshotRole;
use crate::sqlite_store::schema::SCHEMA_VERSION;

/// Ceiling for one earned knowledge payload.
pub const MAX_KNOWLEDGE_PAYLOAD_BYTES: usize = 1024 * 1024;

/// Ceiling for one typed subject identity or journal record key.
pub const MAX_SUBJECT_ID_BYTES: usize = 1024;

/// Ceiling for one content entry key.
pub const MAX_CONTENT_KEY_BYTES: usize = 1024;

/// Ceiling for the number of state chunks one snapshot manifest may declare.
pub const MAX_SNAPSHOT_CHUNKS: u32 = 4096;

/// Domain separator for the permanent journal hash chain.
const JOURNAL_DOMAIN: &[u8] = b"babylon.sqlite-store.journal.v1\0";
/// Domain separator for the earned-knowledge hash chain.
const KNOWLEDGE_DOMAIN: &[u8] = b"babylon.sqlite-store.knowledge.v1\0";
/// Domain separator for the canonical period-candidate identity.
const CANDIDATE_DOMAIN: &[u8] = b"babylon.sqlite-store.candidate.v1\0";
/// Domain separator for the admitted-content identity.
const CONTENT_DOMAIN: &[u8] = b"babylon.sqlite-store.content.v1\0";
/// Version tag of the canonical snapshot manifest bytes.
const MANIFEST_VERSION: u8 = 1;

/// Build identity a caller requires a campaign to have been written by.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct BuildIdentity {
    hash: [u8; 32],
}

impl BuildIdentity {
    /// Wrap an already-computed build hash.
    #[must_use]
    pub const fn from_hash(hash: [u8; 32]) -> Self {
        Self { hash }
    }

    /// Return the exact build hash bytes.
    #[must_use]
    pub const fn hash(self) -> [u8; 32] {
        self.hash
    }
}

/// One immutable content entry offered at campaign creation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AdmittedContentEntry {
    /// Closed content kind.
    pub kind: ContentEntryKind,
    /// Exact entry key bytes.
    pub key: Vec<u8>,
    /// Ordered fragment ordinal inside the entry.
    pub ordinal: u32,
    /// Exact decoded bytes.
    pub bytes: Vec<u8>,
}

/// Captured content and build identity admitted with a new campaign.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AdmittedContent {
    /// Durable campaign identity written beside every row that names it.
    pub campaign_id: CampaignId,
    /// Build identity required to reopen the campaign.
    pub build: BuildIdentity,
    /// Ordered captured source, compiled definitions, provenance and opening
    /// metadata entries.
    pub entries: Vec<AdmittedContentEntry>,
}

/// One immutable state chunk at a manifest position.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct StateChunk {
    /// Closed restart-root section.
    pub section: ChunkSection,
    /// Ordered fragment ordinal inside the section.
    pub ordinal: u32,
    /// Exact decoded bytes.
    pub bytes: Vec<u8>,
}

/// Opening state captured with a new campaign at period zero.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AdmittedOpening {
    /// Canonical world identity of the opening.
    pub world_hash: [u8; 32],
    /// Canonical state identity of the opening.
    pub state_hash: [u8; 32],
    /// Complete opening restart root.
    pub chunks: Vec<StateChunk>,
}

/// One organizer command offered for durable acceptance.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PlayerCommand {
    /// Period the command applies to, always the committed period plus one.
    pub period: u64,
    /// Durable actor identity.
    pub actor_id: [u8; 8],
    /// Canonical command payload bytes.
    pub payload: Vec<u8>,
}

/// One typed journal subject offered with a period candidate.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PreparedSubject {
    /// Closed subject kind.
    pub kind: SubjectKind,
    /// Exact typed identity bytes.
    pub id: Vec<u8>,
}

/// One immutable journal record offered with a period candidate.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PreparedJournalRecord {
    /// Closed record kind; the owner-written kinds are refused.
    pub kind: JournalKind,
    /// Optional typed subject.
    pub subject: Option<PreparedSubject>,
    /// Optional canonical idempotency key for projections such as dossiers.
    pub record_key: Option<Vec<u8>>,
    /// Exact canonical payload bytes.
    pub payload: Vec<u8>,
    /// Mark the newest unresolved record with the same subject as resolved.
    pub resolves_prior_subject: bool,
}

/// One fact or authority earned by a period candidate.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PreparedKnowledgeGrant {
    /// Player who earned the authority.
    pub player_id: [u8; 8],
    /// Typed subject the grant discloses.
    pub subject: PreparedSubject,
    /// Caller-assigned grant key inside the subject.
    pub grant_key: i64,
    /// Exact canonical payload bytes.
    pub payload: Vec<u8>,
}

/// One exhaustive technical-detail row offered with a period candidate.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PreparedDetailRow {
    /// Closed receipt or event family.
    pub family: DetailFamily,
    /// Ordered fragment inside the family.
    pub ordinal: u32,
    /// Exact canonical payload bytes.
    pub payload: Vec<u8>,
}

/// One complete period candidate prepared outside the write transaction.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PreparedPeriod {
    /// Period this candidate completes.
    pub period: u64,
    /// World identity the caller expects the committed root to hold.
    pub expected_world_hash: [u8; 32],
    /// Canonical world identity of the completed period.
    pub world_hash: [u8; 32],
    /// Canonical state identity of the completed period.
    pub state_hash: [u8; 32],
    /// Complete restart root of the completed period.
    pub chunks: Vec<StateChunk>,
    /// Ordered permanent journal records.
    pub journal: Vec<PreparedJournalRecord>,
    /// Facts or authorities earned in the period.
    pub knowledge: Vec<PreparedKnowledgeGrant>,
    /// Exhaustive technical detail retained for the thirteen-period window.
    pub detail: Vec<PreparedDetailRow>,
}

/// Whether an acceptance inserted a new commitment or replayed an existing one.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum AcceptanceKind {
    /// The nonce and period were free, so the commitment was inserted.
    Inserted,
    /// The exact nonce and bytes were already durable.
    Existing,
}

/// Durable acknowledgement of one accepted organizer command.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct AcceptanceReceipt {
    /// Period the command applies to.
    pub period: u64,
    /// Command nonce.
    pub nonce: [u8; 16],
    /// Digest of the accepted canonical payload.
    pub payload_hash: [u8; 32],
    /// Journal sequence of the immutable acceptance record.
    pub acceptance_seq: u64,
    /// Whether the acknowledgement inserted or replayed.
    pub kind: AcceptanceKind,
}

/// Whether a commit inserted a new period or replayed an identical one.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CommitKind {
    /// The period was inserted.
    Inserted,
    /// The same canonical candidate was already committed.
    Existing,
}

/// Durable acknowledgement of one committed period.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct CommittedPeriod {
    /// Committed period.
    pub period: u64,
    /// Canonical world identity recorded for the period.
    pub world_hash: [u8; 32],
    /// Canonical state identity recorded for the period.
    pub state_hash: [u8; 32],
    /// Journal tail after this commit.
    pub journal_tail_seq: u64,
    /// Hash of the journal tail entry.
    pub journal_tail_hash: [u8; 32],
    /// Knowledge tail after this commit.
    pub knowledge_tail_seq: u64,
    /// Hash of the knowledge tail entry.
    pub knowledge_tail_hash: [u8; 32],
    /// State chunks inserted by this commit.
    pub chunks_inserted: u32,
    /// State chunks shared with the preceding current snapshot.
    pub chunks_reused: u32,
    /// Time spent inside the commit transaction.
    pub commit_ns: u64,
    /// Whether the commit inserted or replayed.
    pub kind: CommitKind,
    /// Rotation and reclamation accounting for this commit.
    pub retention: RetentionAccountingReport,
}

/// One state chunk reached by the current snapshot.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct CurrentChunk {
    /// Closed restart-root section.
    pub section: ChunkSection,
    /// Ordered fragment ordinal inside the section.
    pub ordinal: u32,
    /// Integer identity of the stored chunk.
    pub chunk_id: i64,
    /// Exact decoded length.
    pub raw_len: u32,
    /// SHA-256 of the decoded bytes.
    pub raw_hash: [u8; 32],
}

/// Exact committed restart root of a campaign.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CurrentRoot {
    /// Snapshot row that owns this root.
    pub snapshot_id: i64,
    /// Committed period.
    pub period: u64,
    /// Canonical world identity.
    pub world_hash: [u8; 32],
    /// Canonical state identity.
    pub state_hash: [u8; 32],
    /// Journal tail at the commit.
    pub journal_tail_seq: u64,
    /// Journal tail hash at the commit.
    pub journal_tail_hash: [u8; 32],
    /// Knowledge tail at the commit.
    pub knowledge_tail_seq: u64,
    /// Knowledge tail hash at the commit.
    pub knowledge_tail_hash: [u8; 32],
    /// Complete ordered restart root.
    pub chunks: Vec<CurrentChunk>,
}

/// Exact durable journal and knowledge tails of one campaign.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct DurableTails {
    journal_seq: u64,
    journal_hash: [u8; 32],
    knowledge_seq: u64,
    knowledge_hash: [u8; 32],
}

impl DurableTails {
    /// Return the durable journal tail sequence.
    #[must_use]
    pub const fn journal_seq(self) -> u64 {
        self.journal_seq
    }

    /// Return the hash of the durable journal tail entry.
    #[must_use]
    pub const fn journal_hash(self) -> [u8; 32] {
        self.journal_hash
    }

    /// Return the durable knowledge tail sequence.
    #[must_use]
    pub const fn knowledge_seq(self) -> u64 {
        self.knowledge_seq
    }

    /// Return the hash of the durable knowledge tail entry.
    #[must_use]
    pub const fn knowledge_hash(self) -> [u8; 32] {
        self.knowledge_hash
    }
}

/// Why the store refused a command acceptance.
#[derive(Debug)]
pub enum CommandError {
    /// The nonce was reused with different bytes, actor or period.
    ConflictingNonce,
    /// One period already has an immutable accepted commitment.
    PeriodCommitmentAlreadyAccepted {
        /// Period that already has an accepted commitment.
        period: u64,
    },
    /// The command targets a period other than the next one.
    WrongPeriod {
        /// Period the store requires.
        expected: u64,
        /// Period offered.
        actual: u64,
    },
    /// The command payload is empty or otherwise outside its contract.
    InvalidCommand {
        /// Why the command was refused.
        reason: &'static str,
    },
    /// The selected host profile publishes no player-command surface.
    UnsupportedProfile,
    /// The underlying store refused the write.
    Store(SaveError),
}

impl std::fmt::Display for CommandError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> FmtResult {
        match self {
            Self::ConflictingNonce => {
                write!(
                    formatter,
                    "the command nonce was reused with different bytes"
                )
            }
            Self::PeriodCommitmentAlreadyAccepted { period } => write!(
                formatter,
                "period {period} already has an accepted commitment"
            ),
            Self::WrongPeriod { expected, actual } => write!(
                formatter,
                "the campaign store expected period {expected}, received {actual}"
            ),
            Self::InvalidCommand { reason } => {
                write!(formatter, "the organizer command is refused: {reason}")
            }
            Self::UnsupportedProfile => write!(
                formatter,
                "the selected host profile publishes no player-command surface"
            ),
            Self::Store(error) => write!(formatter, "the command acceptance was refused: {error}"),
        }
    }
}

impl std::error::Error for CommandError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Store(error) => Some(error),
            _ => None,
        }
    }
}

impl From<SaveError> for CommandError {
    fn from(error: SaveError) -> Self {
        Self::Store(error)
    }
}

impl From<rusqlite::Error> for CommandError {
    fn from(error: rusqlite::Error) -> Self {
        Self::Store(SaveError::from(error))
    }
}

/// Deterministic test seam for crash-point contract tests.
#[cfg(test)]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FaultPoint {
    /// Abort before the commit transaction opens.
    BeforeCommit,
    /// Abort inside the commit transaction before the manifest update.
    DuringCommit,
    /// Abort after the durable acceptance and before its acknowledgement.
    AfterAcceptBeforeAck,
    /// Abort after the durable commit and before its acknowledgement.
    AfterCommitBeforeAck,
    /// Abort during the online export before publication.
    DuringExport,
    /// Abort after the durable dossier publication and before its acknowledgement.
    AfterDossierBeforeAck,
}

/// Namespace for opening and creating campaigns in the embedded store.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct SqliteCampaignStore;

impl SqliteCampaignStore {
    /// Create one campaign database at a path that holds no committed campaign.
    ///
    /// The path is refused only when it already holds a committed
    /// `save_manifest` row. A creation that crashed before `create_inner`
    /// commits its single transaction (the one that ends with `save_manifest`)
    /// leaves partial database files and a stale lock record, and no reader could
    /// open them. That path is reclaimed instead of dead-ended: the campaign lock
    /// is taken first, so a live writer still refuses with
    /// [`SaveError::CampaignLocked`] and only a dead owner's record is recovered;
    /// then the path is re-checked for a committed manifest and, when absent, the
    /// partial database files are removed before creation starts from empty.
    ///
    /// # Errors
    ///
    /// Refuses a path holding a committed campaign, a lock record another live
    /// owner holds, a payload outside its table allowance, or a `SQLite`
    /// failure. A failed creation removes the partial database it just made so
    /// the path stays usable.
    #[allow(
        clippy::needless_pass_by_value,
        reason = "the published boundary admits the captured content and opening by value"
    )]
    pub fn create(
        path: &Path,
        captured: AdmittedContent,
        opening: AdmittedOpening,
    ) -> Result<CampaignHandle, SaveError> {
        sqlite_runtime_pin::verify_sqlite_runtime()?;
        validate_content(&captured)?;
        validate_chunks("state_chunk", &opening.chunks)?;
        if opening.chunks.is_empty() {
            return Err(SaveError::InvalidField {
                table: "snapshot",
                field: "chunks",
                reason: "the opening needs at least one state chunk",
            });
        }
        if recorded_campaign_id_at(path)?.is_some() {
            return Err(SaveError::CampaignExists {
                path: path.to_path_buf(),
            });
        }

        let lock = CampaignLock::acquire(path, captured.campaign_id)?;
        // Re-check under the lock: only an owner that held this lock can commit a
        // manifest, so a campaign that appeared between the check and the lock is
        // still refused rather than replaced.
        if recorded_campaign_id_at(path)?.is_some() {
            return Err(SaveError::CampaignExists {
                path: path.to_path_buf(),
            });
        }
        // No committed manifest root exists and no live owner holds the path, so
        // whatever is here is the remains of an interrupted creation.
        remove_database_files(path);
        match create_inner(path, &captured, &opening) {
            Ok(parts) => Ok(CampaignHandle {
                connection: parts.connection,
                _lock: lock,
                path: path.to_path_buf(),
                campaign_id: captured.campaign_id,
                build: captured.build,
                content_hash: parts.content_hash,
                current: parts.current,
                #[cfg(test)]
                fault: Cell::new(None),
                #[cfg(test)]
                opened_chunk_reads: parts.opened_chunk_reads,
                #[cfg(test)]
                export_bytes: Cell::new(0),
            }),
            Err(error) => {
                remove_database_files(path);
                Err(error)
            }
        }
    }

    /// Open the campaign committed at one path.
    ///
    /// The restart root costs `O(current_chunks)`: the manifest, the current
    /// snapshot, its chunk links and those chunks only.
    ///
    /// # Errors
    ///
    /// Refuses a missing campaign, an occupied live lock, a mismatched build,
    /// an inconsistent committed manifest, a tampered current chunk, or a
    /// `SQLite` failure.
    pub fn open(path: &Path, expected_build: BuildIdentity) -> Result<CampaignHandle, SaveError> {
        sqlite_runtime_pin::verify_sqlite_runtime()?;
        if !path.exists() {
            return Err(SaveError::CampaignMissing {
                path: path.to_path_buf(),
            });
        }
        let campaign_id = committed_campaign_id(path)?;
        let lock = CampaignLock::acquire(path, campaign_id)?;
        let connection = Connection::open_with_flags(
            path,
            OpenFlags::SQLITE_OPEN_READ_WRITE | OpenFlags::SQLITE_OPEN_NO_MUTEX,
        )?;
        schema::configure_connection(&connection)?;
        schema::verify_installed_schema(&connection)?;
        reconcile(connection, lock, path, campaign_id, expected_build)
    }

    /// Recover one damaged campaign into a clean independent destination.
    ///
    /// Cold layers that no longer authenticate are dropped; the current root,
    /// permanent journal and earned knowledge must verify completely. The source
    /// file is opened read-only and preserved as evidence.
    ///
    /// # Errors
    ///
    /// Refuses a missing source, an existing destination, a mismatched build, any
    /// damage to the current root or a permanent structure, an integrity failure,
    /// or a host I/O failure. A failed recovery publishes nothing.
    pub fn recover_to_new_save(
        damaged_path: &Path,
        destination: &Path,
        expected_build: BuildIdentity,
    ) -> Result<VerifiedRecovery, SaveError> {
        sqlite_runtime_pin::verify_sqlite_runtime()?;
        replay::recover_to_new_save(damaged_path, destination, expected_build)
    }
}

struct CreatedParts {
    connection: Connection,
    content_hash: [u8; 32],
    current: CurrentRoot,
    #[cfg(test)]
    opened_chunk_reads: u64,
}

/// One open campaign owned by this process.
pub struct CampaignHandle {
    // `connection` is declared before `lock` so it closes first during drop and
    // the lock record outlives every statement the handle can issue.
    connection: Connection,
    _lock: CampaignLock,
    path: PathBuf,
    campaign_id: CampaignId,
    build: BuildIdentity,
    content_hash: [u8; 32],
    current: CurrentRoot,
    #[cfg(test)]
    fault: Cell<Option<FaultPoint>>,
    #[cfg(test)]
    opened_chunk_reads: u64,
    #[cfg(test)]
    export_bytes: Cell<u64>,
}

impl std::fmt::Debug for CampaignHandle {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> FmtResult {
        formatter
            .debug_struct("CampaignHandle")
            .field("path", &self.path)
            .field("campaign_id", &self.campaign_id)
            .field("period", &self.current.period)
            .field("journal_tail_seq", &self.current.journal_tail_seq)
            .field("knowledge_tail_seq", &self.current.knowledge_tail_seq)
            .finish_non_exhaustive()
    }
}

impl CampaignHandle {
    /// Return the durable campaign identity.
    #[must_use]
    pub const fn campaign_id(&self) -> &CampaignId {
        &self.campaign_id
    }

    /// Return the build identity recorded at creation.
    #[must_use]
    pub const fn build(&self) -> BuildIdentity {
        self.build
    }

    /// Return the campaign database path.
    #[must_use]
    pub fn path(&self) -> &Path {
        &self.path
    }

    /// Return the exact committed restart root.
    #[must_use]
    pub const fn current(&self) -> &CurrentRoot {
        &self.current
    }

    /// Read and authenticate every fragment of one captured content entry.
    ///
    /// # Errors
    ///
    /// Refuses an absent entry, a payload outside the content budget, a codec or
    /// length or digest mismatch, or a `SQLite` failure.
    pub fn read_content_entry(
        &self,
        kind: ContentEntryKind,
        entry_key: &[u8],
    ) -> Result<Vec<Vec<u8>>, SaveError> {
        chunks::read_content_entry(&self.connection, kind, entry_key)
    }

    /// Durably accept one organizer command for the next period.
    ///
    /// A replay with the same nonce and equal bytes returns the original
    /// receipt. A different payload, actor or period for that nonce refuses.
    ///
    /// # Errors
    ///
    /// Refuses a conflicting nonce, a second distinct commitment for the same
    /// period, a period that is not the next one, an empty or oversized
    /// payload, or a `SQLite` failure.
    #[allow(
        clippy::too_many_lines,
        clippy::needless_pass_by_value,
        reason = "the published command boundary takes ownership and keeps one acceptance atomic"
    )]
    pub fn accept_command(
        &mut self,
        command: PlayerCommand,
        nonce: [u8; 16],
    ) -> Result<AcceptanceReceipt, CommandError> {
        if chunks::has_content_entry(
            &self.connection,
            ContentEntryKind::OpeningMetadata,
            chunks::AUTHORED_GRAPH_ADMISSION_KEY,
        )? {
            return Err(CommandError::UnsupportedProfile);
        }
        if command.payload.is_empty() {
            return Err(CommandError::InvalidCommand {
                reason: "the command payload is empty",
            });
        }
        if command.payload.len() > codec::MAX_PERMANENT_JOURNAL_BYTES {
            return Err(CommandError::Store(SaveError::PayloadTooLarge {
                table: "permanent_journal",
                limit: codec::MAX_PERMANENT_JOURNAL_BYTES,
                actual: command.payload.len(),
            }));
        }
        let payload_hash = content_digest::sha256_of(&command.payload);
        let payload_len =
            u32::try_from(command.payload.len()).map_err(|_| CommandError::InvalidCommand {
                reason: "the command payload does not fit its bounded length",
            })?;

        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)?;
        let existing = transaction
            .query_row(
                "SELECT period, actor_id, raw_len, raw_hash, journal_seq
                 FROM permanent_journal WHERE nonce = ?1 AND kind = ?2",
                params![&nonce[..], JournalKind::AcceptedCommand.code()],
                |row| {
                    Ok((
                        row.get::<_, i64>(0)?,
                        row.get::<_, Option<Vec<u8>>>(1)?,
                        row.get::<_, i64>(2)?,
                        row.get::<_, Vec<u8>>(3)?,
                        row.get::<_, i64>(4)?,
                    ))
                },
            )
            .optional()?;
        if let Some((period, actor, raw_len, raw_hash, seq)) = existing {
            if to_u64(period, "permanent_journal.period")? != command.period
                || actor.as_deref() != Some(&command.actor_id[..])
                || raw_len != i64::from(payload_len)
                || raw_hash.as_slice() != payload_hash
            {
                return Err(CommandError::ConflictingNonce);
            }
            return Ok(AcceptanceReceipt {
                period: command.period,
                nonce,
                payload_hash,
                acceptance_seq: to_u64(seq, "permanent_journal.journal_seq")?,
                kind: AcceptanceKind::Existing,
            });
        }

        let expected = self
            .current
            .period
            .checked_add(1)
            .ok_or(SaveError::Arithmetic {
                field: "next period",
            })?;
        if command.period != expected {
            return Err(CommandError::WrongPeriod {
                expected,
                actual: command.period,
            });
        }
        let period_taken: i64 = transaction.query_row(
            "SELECT COUNT(*) FROM permanent_journal WHERE kind = ?1 AND period = ?2",
            params![
                JournalKind::AcceptedCommand.code(),
                checked_i64(command.period, "command period")?
            ],
            |row| row.get(0),
        )?;
        if period_taken != 0 {
            return Err(CommandError::PeriodCommitmentAlreadyAccepted {
                period: command.period,
            });
        }

        let committed = read_manifest(&transaction)?;
        let journal_seq =
            committed
                .journal_tail_seq
                .checked_add(1)
                .ok_or(SaveError::Arithmetic {
                    field: "journal sequence",
                })?;
        let previous_hash = committed.journal_tail_hash;
        let entry_hash = journal_entry_hash(&JournalInput {
            journal_seq,
            kind: JournalKind::AcceptedCommand,
            period: command.period,
            actor_id: Some(command.actor_id),
            subject: None,
            nonce: Some(nonce),
            record_key: None,
            raw_len: payload_len,
            raw_hash: payload_hash,
            previous_hash,
        })?;
        chunks::write_journal_record(
            &transaction,
            &JournalRecordInput {
                journal_seq,
                kind: JournalKind::AcceptedCommand,
                period: command.period,
                actor_id: Some(command.actor_id),
                subject: None,
                nonce: Some(nonce),
                record_key: None,
                payload: &command.payload,
                previous_hash,
                entry_hash,
            },
        )?;
        transaction.execute(
            "UPDATE save_manifest SET journal_tail_seq = ?1, journal_tail_hash = ?2 WHERE id = 1",
            params![
                checked_i64(journal_seq, "journal sequence")?,
                &entry_hash[..]
            ],
        )?;
        transaction.commit()?;
        #[cfg(test)]
        if self.fault.get() == Some(FaultPoint::AfterAcceptBeforeAck) {
            self.fault.set(None);
            return Err(CommandError::Store(SaveError::InjectedFault));
        }
        Ok(AcceptanceReceipt {
            period: command.period,
            nonce,
            payload_hash,
            acceptance_seq: journal_seq,
            kind: AcceptanceKind::Inserted,
        })
    }

    /// Commit one complete canonical period candidate.
    ///
    /// # Errors
    ///
    /// Refuses a period that is neither the next one nor already committed with
    /// equal bytes, a stale expected root, a reserved journal kind, a repeated
    /// chunk position, knowledge without a journal source, an unresolved
    /// resolution, a payload outside its allowance, or a `SQLite` failure.
    #[allow(
        clippy::too_many_lines,
        reason = "one immediate transaction keeps every period section atomic"
    )]
    #[allow(
        clippy::needless_pass_by_value,
        reason = "the published commit boundary admits one prepared period by value"
    )]
    pub fn commit(&mut self, candidate: PreparedPeriod) -> Result<CommittedPeriod, SaveError> {
        let prepared = prepare_candidate(&candidate)?;
        if candidate.period == 0 {
            return Err(SaveError::WrongPeriod {
                expected: 1,
                actual: 0,
            });
        }
        #[cfg(test)]
        if self.fault.get() == Some(FaultPoint::BeforeCommit) {
            self.fault.set(None);
            return Err(SaveError::InjectedFault);
        }

        let started = Instant::now();
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)?;
        transaction.pragma_update(None, "defer_foreign_keys", "ON")?;
        let committed = read_manifest(&transaction)?;
        let current = read_snapshot(&transaction, committed.current_snapshot_id)?;

        if candidate.period <= current.period {
            let Some(existing) = period_summary_for(&transaction, candidate.period)? else {
                return Err(SaveError::WrongPeriod {
                    expected: current.period.checked_add(1).ok_or(SaveError::Arithmetic {
                        field: "next period",
                    })?,
                    actual: candidate.period,
                });
            };
            if existing.0.candidate_hash != prepared.candidate_hash {
                return Err(SaveError::ConflictingPeriodCommit {
                    period: candidate.period,
                });
            }
            transaction.commit()?;
            let summary = existing.0;
            return Ok(CommittedPeriod {
                period: summary.period,
                world_hash: summary.world_hash,
                state_hash: summary.state_hash,
                journal_tail_seq: existing.1,
                journal_tail_hash: existing.2,
                knowledge_tail_seq: summary.knowledge_tail_seq,
                knowledge_tail_hash: summary.knowledge_tail_hash,
                chunks_inserted: 0,
                chunks_reused: 0,
                commit_ns: elapsed_ns(started),
                kind: CommitKind::Existing,
                retention: RetentionAccountingReport {
                    period: summary.period,
                    ..RetentionAccountingReport::default()
                },
            });
        }

        let expected = current.period.checked_add(1).ok_or(SaveError::Arithmetic {
            field: "next period",
        })?;
        if candidate.period != expected {
            return Err(SaveError::WrongPeriod {
                expected,
                actual: candidate.period,
            });
        }
        if candidate.expected_world_hash != current.world_hash {
            return Err(SaveError::StaleRoot {
                expected: candidate.expected_world_hash,
                actual: current.world_hash,
            });
        }

        let mut journal_seq = committed.journal_tail_seq;
        let mut journal_hash = committed.journal_tail_hash;
        let mut gross_bytes_added = 0_u64;
        if let Some(accepted) = unresolved_command(&transaction, candidate.period)? {
            journal_seq = journal_seq.checked_add(1).ok_or(SaveError::Arithmetic {
                field: "journal sequence",
            })?;
            gross_bytes_added = gross_bytes_added.saturating_add(u64::from(accepted.raw_len));
            let entry_hash = journal_entry_hash(&JournalInput {
                journal_seq,
                kind: JournalKind::ResolvedBatch,
                period: candidate.period,
                actor_id: accepted.actor_id,
                subject: None,
                nonce: None,
                record_key: None,
                raw_len: accepted.raw_len,
                raw_hash: accepted.raw_hash,
                previous_hash: journal_hash,
            })?;
            chunks::write_journal_record(
                &transaction,
                &JournalRecordInput {
                    journal_seq,
                    kind: JournalKind::ResolvedBatch,
                    period: candidate.period,
                    actor_id: accepted.actor_id,
                    subject: None,
                    nonce: None,
                    record_key: None,
                    payload: &accepted.payload,
                    previous_hash: journal_hash,
                    entry_hash,
                },
            )?;
            transaction.execute(
                "UPDATE permanent_journal
                 SET resolved_period = ?1, resolution_seq = ?2
                 WHERE journal_seq = ?3 AND resolved_period IS NULL",
                params![
                    checked_i64(candidate.period, "journal period")?,
                    checked_i64(journal_seq, "journal sequence")?,
                    accepted.journal_seq
                ],
            )?;
            journal_hash = entry_hash;
        }

        for (record, descriptor) in candidate.journal.iter().zip(&prepared.journal) {
            journal_seq = journal_seq.checked_add(1).ok_or(SaveError::Arithmetic {
                field: "journal sequence",
            })?;
            gross_bytes_added = gross_bytes_added.saturating_add(u64::from(descriptor.raw_len));
            let subject = record
                .subject
                .as_ref()
                .map(|subject| (subject.kind, subject.id.as_slice()));
            let entry_hash = journal_entry_hash(&JournalInput {
                journal_seq,
                kind: record.kind,
                period: candidate.period,
                actor_id: None,
                subject,
                nonce: None,
                record_key: record.record_key.as_deref(),
                raw_len: descriptor.raw_len,
                raw_hash: descriptor.raw_hash,
                previous_hash: journal_hash,
            })?;
            chunks::write_journal_record(
                &transaction,
                &JournalRecordInput {
                    journal_seq,
                    kind: record.kind,
                    period: candidate.period,
                    actor_id: None,
                    subject: subject.map(|(kind, id)| JournalSubject { kind, id }),
                    nonce: None,
                    record_key: record.record_key.as_deref(),
                    payload: &record.payload,
                    previous_hash: journal_hash,
                    entry_hash,
                },
            )?;
            if record.resolves_prior_subject {
                let Some((kind, id)) = subject else {
                    return Err(SaveError::UnresolvedSubjectMissing);
                };
                resolve_prior_subject(&transaction, kind, id, candidate.period, journal_seq)?;
            }
            journal_hash = entry_hash;
        }

        if !candidate.knowledge.is_empty() && journal_seq == committed.journal_tail_seq {
            return Err(SaveError::KnowledgeSourceMissing);
        }

        let mut knowledge_seq = committed.knowledge_tail_seq;
        let mut knowledge_hash = committed.knowledge_tail_hash;
        for (grant, descriptor) in candidate.knowledge.iter().zip(&prepared.knowledge) {
            knowledge_seq = knowledge_seq.checked_add(1).ok_or(SaveError::Arithmetic {
                field: "knowledge sequence",
            })?;
            let entry_hash = knowledge_entry_hash(&KnowledgeInput {
                knowledge_seq,
                player_id: grant.player_id,
                subject_kind: grant.subject.kind,
                subject_id: &grant.subject.id,
                grant_key: grant.grant_key,
                acquired_period: candidate.period,
                source_journal_seq: journal_seq,
                raw_len: descriptor.raw_len,
                raw_hash: descriptor.raw_hash,
                previous_hash: knowledge_hash,
            })?;
            transaction.execute(
                "INSERT INTO knowledge_grant (
                    knowledge_seq, player_id, subject_kind, subject_id, grant_key,
                    acquired_period, source_journal_seq, payload, previous_hash, entry_hash
                 ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)",
                params![
                    checked_i64(knowledge_seq, "knowledge sequence")?,
                    &grant.player_id[..],
                    grant.subject.kind.code(),
                    &grant.subject.id,
                    grant.grant_key,
                    checked_i64(candidate.period, "knowledge period")?,
                    checked_i64(journal_seq, "knowledge source")?,
                    &grant.payload,
                    &knowledge_hash[..],
                    &entry_hash[..],
                ],
            )?;
            knowledge_hash = entry_hash;
            gross_bytes_added = gross_bytes_added.saturating_add(u64::from(descriptor.raw_len));
        }

        let detail_rows =
            u32::try_from(candidate.detail.len()).map_err(|_| SaveError::Arithmetic {
                field: "detail row count",
            })?;
        for row in &candidate.detail {
            chunks::write_recent_detail(
                &transaction,
                candidate.period,
                row.family,
                row.ordinal,
                &row.payload,
            )?;
            gross_bytes_added = gross_bytes_added.saturating_add(
                u64::try_from(row.payload.len()).map_err(|_| SaveError::Arithmetic {
                    field: "detail payload length",
                })?,
            );
        }

        // The owner writes the period's terminal compact summary. It binds the
        // identity the caller committed, the tails before it, and the knowledge
        // the period earned, so replay can verify every intervening commit
        // without retaining a snapshot for it.
        let summary = PeriodSummary {
            period: candidate.period,
            candidate_hash: prepared.candidate_hash,
            world_hash: candidate.world_hash,
            state_hash: candidate.state_hash,
            prior_journal_seq: journal_seq,
            prior_journal_hash: journal_hash,
            knowledge_tail_seq: knowledge_seq,
            knowledge_tail_hash: knowledge_hash,
            detail_rows,
            evidence_records: count(candidate.journal.len(), "evidence record count")?,
        };
        let summary_payload = summary.encode();
        journal_seq = journal_seq.checked_add(1).ok_or(SaveError::Arithmetic {
            field: "journal sequence",
        })?;
        let summary_hash = journal_entry_hash(&JournalInput {
            journal_seq,
            kind: JournalKind::PeriodSummary,
            period: candidate.period,
            actor_id: None,
            subject: None,
            nonce: None,
            record_key: None,
            raw_len: u32::try_from(summary_payload.len()).map_err(|_| SaveError::Arithmetic {
                field: "period summary length",
            })?,
            raw_hash: content_digest::sha256_of(&summary_payload),
            previous_hash: journal_hash,
        })?;
        chunks::write_journal_record(
            &transaction,
            &JournalRecordInput {
                journal_seq,
                kind: JournalKind::PeriodSummary,
                period: candidate.period,
                actor_id: None,
                subject: None,
                nonce: None,
                record_key: None,
                payload: &summary_payload,
                previous_hash: journal_hash,
                entry_hash: summary_hash,
            },
        )?;
        journal_hash = summary_hash;
        gross_bytes_added = gross_bytes_added.saturating_add(
            u64::try_from(summary_payload.len()).map_err(|_| SaveError::Arithmetic {
                field: "period summary length",
            })?,
        );

        let previous = previous_chunks(&transaction, current.snapshot_id)?;
        let ordered = ordered_chunks(&candidate.chunks);
        let mut links: Vec<(i64, ChunkDescriptor)> = Vec::with_capacity(prepared.chunks.len());
        let mut inserted = 0_u32;
        let mut reused = 0_u32;
        for (chunk, descriptor) in ordered.iter().zip(&prepared.chunks) {
            let chunk_id = match previous
                .iter()
                .find(|entry| entry.section == chunk.section && entry.ordinal == chunk.ordinal)
            {
                Some(entry)
                    if entry.raw_len == descriptor.raw_len
                        && entry.raw_hash == descriptor.raw_hash
                        && chunks::read_state_chunk(&transaction, entry.chunk_id)?
                            == chunk.bytes =>
                {
                    reused = reused.saturating_add(1);
                    entry.chunk_id
                }
                _ => {
                    inserted = inserted.saturating_add(1);
                    gross_bytes_added =
                        gross_bytes_added.saturating_add(u64::from(descriptor.raw_len));
                    chunks::write_state_chunk(
                        &transaction,
                        chunk.section,
                        chunk.ordinal,
                        &chunk.bytes,
                    )?
                }
            };
            links.push((chunk_id, *descriptor));
        }

        // Install the successor restart root. The superseded current row is
        // removed rather than demoted: a checkpoint period keeps its own twin,
        // and every other period's root is not part of the retained roster.
        // Foreign keys are deferred to `COMMIT` so the single current row, its
        // manifest reference and reachability reclamation can move in one
        // transaction while `save_manifest` still publishes last.
        let mut superseded_bytes = 0_u64;
        if current.role == SnapshotRole::Current {
            superseded_bytes = retention::delete_snapshot(&transaction, current.snapshot_id)?;
        }
        let manifest_bytes = encode_manifest(&prepared.chunks, prepared.candidate_hash)?;
        let snapshot_id = insert_snapshot(
            &transaction,
            SnapshotRole::Current,
            candidate.period,
            candidate.world_hash,
            candidate.state_hash,
            &manifest_bytes,
            journal_seq,
            journal_hash,
            knowledge_seq,
            knowledge_hash,
        )?;
        insert_chunk_links(&transaction, snapshot_id, &links)?;
        if retention::is_checkpoint_period(candidate.period) {
            let checkpoint_id = insert_snapshot(
                &transaction,
                SnapshotRole::Historical,
                candidate.period,
                candidate.world_hash,
                candidate.state_hash,
                &manifest_bytes,
                journal_seq,
                journal_hash,
                knowledge_seq,
                knowledge_hash,
            )?;
            insert_chunk_links(&transaction, checkpoint_id, &links)?;
        }
        let rotation = retention::rotate(
            &transaction,
            candidate.period,
            gross_bytes_added,
            superseded_bytes,
        )?;

        #[cfg(test)]
        if self.fault.get() == Some(FaultPoint::DuringCommit) {
            self.fault.set(None);
            return Err(SaveError::InjectedFault);
        }

        transaction.execute(
            "UPDATE save_manifest SET
                current_snapshot_id = ?1, journal_tail_seq = ?2, journal_tail_hash = ?3,
                knowledge_tail_seq = ?4, knowledge_tail_hash = ?5
             WHERE id = 1",
            params![
                snapshot_id,
                checked_i64(journal_seq, "journal sequence")?,
                &journal_hash[..],
                checked_i64(knowledge_seq, "knowledge sequence")?,
                &knowledge_hash[..],
            ],
        )?;
        transaction.commit()?;
        let commit_ns = elapsed_ns(started);
        let rotation = RetentionAccountingReport {
            wal_bytes: retention::wal_bytes(&self.path),
            ..rotation
        };
        self.current = CurrentRoot {
            snapshot_id,
            period: candidate.period,
            world_hash: candidate.world_hash,
            state_hash: candidate.state_hash,
            journal_tail_seq: journal_seq,
            journal_tail_hash: journal_hash,
            knowledge_tail_seq: knowledge_seq,
            knowledge_tail_hash: knowledge_hash,
            chunks: links
                .into_iter()
                .map(|(chunk_id, descriptor)| CurrentChunk {
                    section: descriptor.section,
                    ordinal: descriptor.ordinal,
                    chunk_id,
                    raw_len: descriptor.raw_len,
                    raw_hash: descriptor.raw_hash,
                })
                .collect(),
        };
        #[cfg(test)]
        if self.fault.get() == Some(FaultPoint::AfterCommitBeforeAck) {
            self.fault.set(None);
            return Err(SaveError::InjectedFault);
        }
        Ok(CommittedPeriod {
            period: candidate.period,
            world_hash: candidate.world_hash,
            state_hash: candidate.state_hash,
            journal_tail_seq: journal_seq,
            journal_tail_hash: journal_hash,
            knowledge_tail_seq: knowledge_seq,
            knowledge_tail_hash: knowledge_hash,
            chunks_inserted: inserted,
            chunks_reused: reused,
            commit_ns,
            kind: CommitKind::Inserted,
            retention: rotation,
        })
    }

    /// Read one player-authorized subject as of a committed period.
    ///
    /// Disclosure uses the acquisition period, never an observation period
    /// carried inside the payload. The stored entry hash authenticates the
    /// payload without a separate hash column.
    ///
    /// # Errors
    ///
    /// Refuses a future period, an undisclosed or another player's subject, a
    /// payload above one MiB, a mismatched stored entry hash, or a `SQLite`
    /// failure.
    pub fn read_granted_subject(
        &self,
        player_id: [u8; 8],
        subject_kind: SubjectKind,
        subject_id: &[u8],
        as_of_period: u64,
    ) -> Result<Vec<u8>, SaveError> {
        if as_of_period > self.current.period {
            return Err(SaveError::FuturePeriod {
                current: self.current.period,
                requested: as_of_period,
            });
        }
        if subject_id.is_empty() {
            return Err(SaveError::InvalidField {
                table: "knowledge_grant",
                field: "subject_id",
                reason: "the subject identity is empty",
            });
        }
        if subject_id.len() > MAX_SUBJECT_ID_BYTES {
            return Err(SaveError::InvalidField {
                table: "knowledge_grant",
                field: "subject_id",
                reason: "the subject identity exceeds one KiB",
            });
        }
        let stored = self
            .connection
            .query_row(
                "SELECT knowledge_seq, grant_key, acquired_period, source_journal_seq,
                        payload, previous_hash, entry_hash
                 FROM knowledge_grant
                 WHERE player_id = ?1 AND subject_kind = ?2 AND subject_id = ?3
                   AND acquired_period <= ?4
                 ORDER BY knowledge_seq DESC LIMIT 1",
                params![
                    &player_id[..],
                    subject_kind.code(),
                    subject_id,
                    checked_i64(as_of_period, "read period")?
                ],
                |row| {
                    Ok(StoredGrant {
                        knowledge_seq: row.get(0)?,
                        grant_key: row.get(1)?,
                        acquired_period: row.get(2)?,
                        source_journal_seq: row.get(3)?,
                        payload: row.get(4)?,
                        previous_hash: row.get(5)?,
                        entry_hash: row.get(6)?,
                    })
                },
            )
            .optional()?;
        let Some(stored) = stored else {
            return Err(SaveError::UndisclosedSubject);
        };
        if stored.payload.len() > MAX_KNOWLEDGE_PAYLOAD_BYTES {
            return Err(SaveError::PayloadTooLarge {
                table: "knowledge_grant",
                limit: MAX_KNOWLEDGE_PAYLOAD_BYTES,
                actual: stored.payload.len(),
            });
        }
        let entry_hash = knowledge_entry_hash(&KnowledgeInput {
            knowledge_seq: to_u64(stored.knowledge_seq, "knowledge_grant.knowledge_seq")?,
            player_id,
            subject_kind,
            subject_id,
            grant_key: stored.grant_key,
            acquired_period: to_u64(stored.acquired_period, "knowledge_grant.acquired_period")?,
            source_journal_seq: to_u64(
                stored.source_journal_seq,
                "knowledge_grant.source_journal_seq",
            )?,
            raw_len: u32::try_from(stored.payload.len()).map_err(|_| SaveError::Arithmetic {
                field: "knowledge payload length",
            })?,
            raw_hash: content_digest::sha256_of(&stored.payload),
            previous_hash: hash_from_row("knowledge_grant", &stored.previous_hash)?,
        })?;
        if entry_hash != hash_from_row("knowledge_grant", &stored.entry_hash)? {
            return Err(SaveError::CorruptPayload {
                table: "knowledge_grant",
                reason: "the stored payload does not match its entry hash",
            });
        }
        Ok(stored.payload)
    }

    /// Reconstruct one historical period from an isolated copy of the save.
    ///
    /// The newest retained checkpoint at or before `target_period` supplies the
    /// verified chunk bytes; the permanent journal chain supplies every
    /// intervening period identity and governed choice receipt, and the knowledge
    /// prefix exposes only facts acquired by the target. The live save is never
    /// mutated and no reconstruction grants live knowledge.
    ///
    /// # Errors
    ///
    /// Refuses a future period, a cancelled request, a missing compact period
    /// summary, damage to a retained layer, or a `SQLite` failure.
    pub fn replay_to_period(
        &self,
        target_period: u64,
        cancel: &AtomicBool,
    ) -> Result<VerifiedReplayReconstruction, ReplayError> {
        replay::reconstruct(
            &self.connection,
            &self.path,
            self.build.hash(),
            self.content_hash,
            self.current.period,
            target_period,
            cancel,
        )
    }

    /// Read the authenticated exhaustive detail of one retained period.
    ///
    /// # Errors
    ///
    /// Refuses a period outside the retained thirteen-period window, a stored
    /// payload that does not match its codec, length or digest, or a `SQLite`
    /// failure. Damage inside the window is diagnosed here rather than blocking
    /// the open of an otherwise valid campaign.
    pub fn read_recent_detail(
        &self,
        period: u64,
        family: DetailFamily,
    ) -> Result<Vec<RecentDetailRow>, SaveError> {
        replay::read_recent_detail(&self.connection, self.current.period, period, family)
    }

    /// Resolve one permanent evidence record by its closed kind and record key.
    ///
    /// A compact current row names its evidence by record key rather than by a
    /// sequence the tick could not know before commit. Rotation never deletes a
    /// permanent journal record, so this resolution survives every checkpoint and
    /// detail-row eviction.
    ///
    /// # Errors
    ///
    /// Refuses an empty record key or a `SQLite` failure.
    pub fn journal_sequence_for_record(
        &self,
        kind: JournalKind,
        record_key: &[u8],
    ) -> Result<Option<u64>, SaveError> {
        retention::journal_sequence_for_record(&self.connection, kind, record_key)
    }

    /// Return the durable journal and knowledge tails.
    ///
    /// # Errors
    ///
    /// Refuses a missing or inconsistent committed manifest.
    pub fn durable_tails(&self) -> Result<DurableTails, SaveError> {
        let manifest = read_manifest(&self.connection)?;
        Ok(DurableTails {
            journal_seq: manifest.journal_tail_seq,
            journal_hash: manifest.journal_tail_hash,
            knowledge_seq: manifest.knowledge_tail_seq,
            knowledge_hash: manifest.knowledge_tail_hash,
        })
    }

    /// Answer one closed query inside one player scope.
    ///
    /// # Errors
    ///
    /// Refuses a scope beyond the committed present, an unearned subject, a
    /// malformed identity, a damaged stored payload, or a `SQLite` failure.
    pub fn query(&self, scope: PlayerScope, query: PlayerQuery) -> Result<PlayerResult, ReadError> {
        let manifest = read_manifest(&self.connection)?;
        let boundary = ReadBoundary {
            committed_period: self.current.period,
            world_hash: self.current.world_hash,
            manifest: &manifest,
        };
        query::execute(&self.connection, &boundary, scope, query)
    }

    /// Read one bounded page of the player's visible journal.
    ///
    /// Pages default to fifty records, cap at two hundred, and order by
    /// `(period, journal_seq)`. A cursor continues strictly after the last
    /// delivered record.
    ///
    /// # Errors
    ///
    /// Refuses a scope beyond the committed present, a damaged stored payload, or
    /// a `SQLite` failure.
    pub fn history(
        &self,
        scope: PlayerScope,
        cursor: Option<HistoryCursor>,
        limit: u16,
    ) -> Result<HistoryPage, ReadError> {
        let manifest = read_manifest(&self.connection)?;
        let boundary = ReadBoundary {
            committed_period: self.current.period,
            world_hash: self.current.world_hash,
            manifest: &manifest,
        };
        query::history(&self.connection, &boundary, scope, cursor, limit)
    }

    /// Queue one demand-driven Archive dossier request.
    ///
    /// # Errors
    ///
    /// Refuses the 257th pending request, a stale request identity, a conflicting
    /// identity, a knowledge prefix that is not on the stored chain, an unearned
    /// subject, or a `SQLite` failure.
    #[allow(
        clippy::needless_pass_by_value,
        reason = "the published Archive boundary admits one typed request by value"
    )]
    pub fn enqueue_archive_dossier(
        &mut self,
        request: DossierRequest,
    ) -> Result<ServiceReceipt, ServiceError> {
        archive_service::enqueue(&mut self.connection, self.current.period, &request)
    }

    /// Publish one completed Archive dossier and retire its pending request.
    ///
    /// # Errors
    ///
    /// Refuses a stale expected service sequence, an unknown or conflicting
    /// request, a knowledge prefix that is not on the stored chain, an unearned
    /// subject, or a `SQLite` failure.
    #[allow(
        clippy::needless_pass_by_value,
        reason = "the published Archive boundary admits one typed completion by value"
    )]
    pub fn complete_archive_dossier(
        &mut self,
        completion: DossierCompletion,
    ) -> Result<PublishedDossierReceipt, ServiceError> {
        let receipt =
            archive_service::complete(&mut self.connection, self.current.period, &completion)?;
        #[cfg(test)]
        if self.fault.get() == Some(FaultPoint::AfterDossierBeforeAck) {
            self.fault.set(None);
            return Err(ServiceError::Store(SaveError::InjectedFault));
        }
        Ok(receipt)
    }

    /// Read every pending dossier request of this campaign.
    ///
    /// # Errors
    ///
    /// Refuses a damaged service record or a `SQLite` failure.
    pub fn pending_archive_dossiers(&self) -> Result<Vec<DossierRequest>, ServiceError> {
        archive_service::pending(&self.connection)
    }

    /// Publish one verified online backup to a new destination.
    ///
    /// # Errors
    ///
    /// Refuses an existing destination, a backup or integrity failure, a
    /// mismatched exported identity, or a host I/O failure. A failed export
    /// removes its temporary destination and leaves the source untouched.
    pub fn export_save(&self, destination: &Path) -> Result<VerifiedExport, SaveError> {
        let started = Instant::now();
        let manifest = read_manifest(&self.connection)?;
        let identity = ExportIdentity {
            campaign_id: self.campaign_id,
            build_hash: self.build.hash(),
            content_hash: self.content_hash,
            current_snapshot_id: self.current.snapshot_id,
            period: self.current.period,
            world_hash: self.current.world_hash,
            state_hash: self.current.state_hash,
            journal_tail_seq: manifest.journal_tail_seq,
            journal_tail_hash: manifest.journal_tail_hash,
            knowledge_tail_seq: manifest.knowledge_tail_seq,
            knowledge_tail_hash: manifest.knowledge_tail_hash,
        };
        let unpublished = export::temporary_path(destination)?;
        let result = export::backup_to(&self.connection, &unpublished).and_then(|()| {
            #[cfg(test)]
            if self.fault.get() == Some(FaultPoint::DuringExport) {
                self.fault.set(None);
                return Err(SaveError::InjectedFault);
            }
            let evidence = export::verify_export(&unpublished, &identity)?;
            let destination_bytes = export::publish(&unpublished, destination)?;
            Ok(VerifiedExport {
                destination_bytes,
                page_count: evidence.page_count,
                integrity_verified: true,
                current_period: identity.period,
                world_hash: identity.world_hash,
                journal_tail_hash: identity.journal_tail_hash,
                elapsed_ns: elapsed_ns(started),
            })
        });
        if result.is_err() {
            export::remove_if_present(&unpublished);
        }
        #[cfg(test)]
        if let Ok(export) = &result {
            self.export_bytes.set(export.destination_bytes);
        }
        result
    }

    /// Return how many current chunks opening authenticated.
    #[cfg(test)]
    #[must_use]
    pub const fn opened_chunk_reads(&self) -> u64 {
        self.opened_chunk_reads
    }

    /// Install one deterministic fault for the next matching operation.
    #[cfg(test)]
    pub fn inject_fault(&self, fault: FaultPoint) {
        self.fault.set(Some(fault));
    }

    /// Return the most recent verified export size.
    #[cfg(test)]
    #[must_use]
    pub fn last_export_bytes(&self) -> u64 {
        self.export_bytes.get()
    }
}

struct StoredGrant {
    knowledge_seq: i64,
    grant_key: i64,
    acquired_period: i64,
    source_journal_seq: i64,
    payload: Vec<u8>,
    previous_hash: Vec<u8>,
    entry_hash: Vec<u8>,
}

fn create_inner(
    path: &Path,
    captured: &AdmittedContent,
    opening: &AdmittedOpening,
) -> Result<CreatedParts, SaveError> {
    let mut connection = Connection::open(path)?;
    schema::configure_connection(&connection)?;
    schema::install_schema(&connection)?;
    let content_hash = admitted_content_hash(&captured.entries)?;
    let prepared = prepare_opening(opening)?;
    let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
    for entry in &captured.entries {
        chunks::write_content_entry(
            &transaction,
            entry.kind,
            &entry.key,
            entry.ordinal,
            &entry.bytes,
        )?;
    }
    let mut links = Vec::with_capacity(prepared.chunks.len());
    for (chunk, descriptor) in ordered_chunks(&opening.chunks).iter().zip(&prepared.chunks) {
        let chunk_id =
            chunks::write_state_chunk(&transaction, chunk.section, chunk.ordinal, &chunk.bytes)?;
        links.push((chunk_id, *descriptor));
    }
    let manifest_bytes = encode_manifest(&prepared.chunks, prepared.candidate_hash)?;
    let snapshot_id = insert_snapshot(
        &transaction,
        SnapshotRole::Opening,
        0,
        opening.world_hash,
        opening.state_hash,
        &manifest_bytes,
        0,
        [0_u8; 32],
        0,
        [0_u8; 32],
    )?;
    for (chunk_id, descriptor) in &links {
        transaction.execute(
            "INSERT INTO snapshot_chunk (snapshot_id, section, ordinal, chunk_id)
             VALUES (?1, ?2, ?3, ?4)",
            params![
                snapshot_id,
                descriptor.section.code(),
                i64::from(descriptor.ordinal),
                chunk_id
            ],
        )?;
    }
    transaction.execute(
        "INSERT INTO save_manifest (
            id, schema_version, campaign_id, build_hash, content_hash, current_snapshot_id,
            journal_tail_seq, journal_tail_hash, knowledge_tail_seq, knowledge_tail_hash
         ) VALUES (1, ?1, ?2, ?3, ?4, ?5, 0, ?6, 0, ?7)",
        params![
            i64::from(SCHEMA_VERSION),
            captured.campaign_id.canonical_bytes(),
            &captured.build.hash()[..],
            &content_hash[..],
            snapshot_id,
            &[0_u8; 32][..],
            &[0_u8; 32][..]
        ],
    )?;
    transaction.commit()?;

    let current = CurrentRoot {
        snapshot_id,
        period: 0,
        world_hash: opening.world_hash,
        state_hash: opening.state_hash,
        journal_tail_seq: 0,
        journal_tail_hash: [0_u8; 32],
        knowledge_tail_seq: 0,
        knowledge_tail_hash: [0_u8; 32],
        chunks: links
            .into_iter()
            .map(|(chunk_id, descriptor)| CurrentChunk {
                section: descriptor.section,
                ordinal: descriptor.ordinal,
                chunk_id,
                raw_len: descriptor.raw_len,
                raw_hash: descriptor.raw_hash,
            })
            .collect(),
    };
    #[cfg(test)]
    let opened_chunk_reads =
        u64::try_from(current.chunks.len()).map_err(|_| SaveError::Arithmetic {
            field: "current chunk count",
        })?;
    Ok(CreatedParts {
        connection,
        content_hash,
        current,
        #[cfg(test)]
        opened_chunk_reads,
    })
}

fn reconcile(
    connection: Connection,
    lock: CampaignLock,
    path: &Path,
    campaign_id: CampaignId,
    expected_build: BuildIdentity,
) -> Result<CampaignHandle, SaveError> {
    let manifest = read_manifest(&connection)?;
    if manifest.campaign_id != campaign_id {
        return Err(SaveError::CorruptManifest {
            reason: "the campaign identity changed between the lock and the manifest",
        });
    }
    if manifest.build_hash != expected_build.hash() {
        return Err(SaveError::BuildMismatch {
            expected: expected_build.hash(),
            actual: manifest.build_hash,
        });
    }
    let snapshot = read_snapshot(&connection, manifest.current_snapshot_id)?;
    if snapshot.role != SnapshotRole::Opening && snapshot.role != SnapshotRole::Current {
        return Err(SaveError::CorruptManifest {
            reason: "the manifest does not point at a restart root",
        });
    }
    if snapshot.committed_journal_seq > manifest.journal_tail_seq
        || snapshot.knowledge_seq != manifest.knowledge_tail_seq
        || snapshot.knowledge_hash != manifest.knowledge_tail_hash
    {
        return Err(SaveError::CorruptManifest {
            reason: "the manifest tails disagree with the current snapshot",
        });
    }
    if snapshot.committed_journal_seq == manifest.journal_tail_seq
        && snapshot.committed_journal_hash != manifest.journal_tail_hash
    {
        return Err(SaveError::CorruptManifest {
            reason: "the manifest journal tail disagrees with the current snapshot",
        });
    }
    let (current, opened_chunk_reads) = load_current_root(&connection, &snapshot)?;
    #[cfg(not(test))]
    let _ = opened_chunk_reads;
    verify_command_metadata(
        &connection,
        current.period,
        current.journal_tail_seq,
        current.journal_tail_hash,
    )?;
    Ok(CampaignHandle {
        connection,
        _lock: lock,
        path: path.to_path_buf(),
        campaign_id,
        build: expected_build,
        content_hash: manifest.content_hash,
        current,
        #[cfg(test)]
        fault: Cell::new(None),
        #[cfg(test)]
        opened_chunk_reads,
        #[cfg(test)]
        export_bytes: Cell::new(0),
    })
}

fn committed_campaign_id(path: &Path) -> Result<CampaignId, SaveError> {
    let connection = Connection::open_with_flags(
        path,
        OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_NO_MUTEX,
    )?;
    connection.busy_timeout(schema::BUSY_TIMEOUT)?;
    recorded_campaign_id(&connection)?.ok_or(SaveError::CorruptManifest {
        reason: "the campaign manifest is missing",
    })
}

/// Read the committed campaign identity of a path, if any, with write access.
///
/// Creation uses this probe because a crashed creation may still have a
/// write-ahead log to recover, which a read-only open cannot do. An absent path,
/// a path without `save_manifest`, or a `save_manifest` without its single row
/// all report `None` and are therefore reclaimable.
fn recorded_campaign_id_at(path: &Path) -> Result<Option<CampaignId>, SaveError> {
    if !path.exists() {
        return Ok(None);
    }
    let connection = Connection::open(path)?;
    connection.busy_timeout(schema::BUSY_TIMEOUT)?;
    recorded_campaign_id(&connection)
}

fn recorded_campaign_id(connection: &Connection) -> Result<Option<CampaignId>, SaveError> {
    let tables: i64 = connection.query_row(
        "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = 'save_manifest'",
        [],
        |row| row.get(0),
    )?;
    if tables == 0 {
        return Ok(None);
    }
    let recorded: Option<Vec<u8>> = connection
        .query_row(
            "SELECT campaign_id FROM save_manifest WHERE id = 1",
            [],
            |row| row.get(0),
        )
        .optional()?;
    let Some(bytes) = recorded else {
        return Ok(None);
    };
    let identity = hash16(&bytes)?;
    Ok(Some(CampaignId::from_uuid(Uuid::from_bytes(identity))))
}

/// Load the restart root one snapshot manifest declares and authenticate every
/// chunk it reaches.
///
/// # Errors
///
/// Refuses a manifest that disagrees with its links, a missing or foreign chunk,
/// or a chunk whose decoded bytes do not match its declared length and hash.
pub(super) fn load_current_root(
    connection: &Connection,
    snapshot: &SnapshotHeader,
) -> Result<(CurrentRoot, u64), SaveError> {
    let declared = decode_manifest(&snapshot.manifest_bytes)?;
    let mut statement = connection.prepare(
        "SELECT section, ordinal, chunk_id FROM snapshot_chunk
         WHERE snapshot_id = ?1 ORDER BY section, ordinal",
    )?;
    let mut rows = statement.query(params![snapshot.snapshot_id])?;
    let mut chunks = Vec::with_capacity(declared.chunks.len());
    let mut reads = 0_u64;
    while let Some(row) = rows.next()? {
        let section_code: i64 = row.get(0)?;
        let ordinal: i64 = row.get(1)?;
        let chunk_id: i64 = row.get(2)?;
        let descriptor = declared
            .chunks
            .get(chunks.len())
            .ok_or(SaveError::CorruptManifest {
                reason: "the snapshot reaches more chunks than its manifest declares",
            })?;
        let section = section_from_code(section_code)?;
        let ordinal = u32::try_from(ordinal).map_err(|_| SaveError::CorruptManifest {
            reason: "a stored chunk ordinal is out of range",
        })?;
        if descriptor.section != section || descriptor.ordinal != ordinal {
            return Err(SaveError::CorruptManifest {
                reason: "the snapshot manifest order disagrees with its chunk links",
            });
        }
        let bytes = chunks::read_state_chunk(connection, chunk_id)?;
        let declared_len =
            usize::try_from(descriptor.raw_len).map_err(|_| SaveError::CorruptManifest {
                reason: "a declared chunk length is out of range",
            })?;
        if bytes.len() != declared_len || content_digest::sha256_of(&bytes) != descriptor.raw_hash {
            return Err(SaveError::CorruptPayload {
                table: "snapshot",
                reason: "a current chunk does not match its manifest descriptor",
            });
        }
        reads = reads.saturating_add(1);
        chunks.push(CurrentChunk {
            section,
            ordinal,
            chunk_id,
            raw_len: descriptor.raw_len,
            raw_hash: descriptor.raw_hash,
        });
    }
    if chunks.len() != declared.chunks.len() {
        return Err(SaveError::CorruptManifest {
            reason: "the snapshot manifest declares chunks it does not reach",
        });
    }
    Ok((
        CurrentRoot {
            snapshot_id: snapshot.snapshot_id,
            period: snapshot.period,
            world_hash: snapshot.world_hash,
            state_hash: snapshot.state_hash,
            journal_tail_seq: snapshot.committed_journal_seq,
            journal_tail_hash: snapshot.committed_journal_hash,
            knowledge_tail_seq: snapshot.knowledge_seq,
            knowledge_tail_hash: snapshot.knowledge_hash,
            chunks,
        },
        reads,
    ))
}

fn verify_command_metadata(
    connection: &Connection,
    current_period: u64,
    committed_seq: u64,
    committed_hash: [u8; 32],
) -> Result<(), SaveError> {
    let expected_next = current_period.checked_add(1).ok_or(SaveError::Arithmetic {
        field: "next period",
    })?;
    let mut statement = connection.prepare(
        "SELECT journal_seq, period, previous_hash FROM permanent_journal
         WHERE kind = ?1 AND resolved_period IS NULL",
    )?;
    let mut rows = statement.query(params![JournalKind::AcceptedCommand.code()])?;
    while let Some(row) = rows.next()? {
        let journal_seq = to_u64(row.get(0)?, "permanent_journal.journal_seq")?;
        let period = to_u64(row.get(1)?, "permanent_journal.period")?;
        if period != expected_next {
            return Err(SaveError::CorruptManifest {
                reason: "an unresolved accepted command targets a non-future period",
            });
        }
        if journal_seq == committed_seq.saturating_add(1)
            && hash_from_row("permanent_journal", &row.get::<_, Vec<u8>>(2)?)? != committed_hash
        {
            return Err(SaveError::CorruptManifest {
                reason: "the pending command does not extend the committed journal chain",
            });
        }
    }
    let accepted: Option<AcceptedCommandRow> = connection
        .query_row(
            "SELECT journal_seq, resolved_period, resolution_seq, entry_hash
             FROM permanent_journal WHERE kind = ?1 AND period = ?2",
            params![
                JournalKind::AcceptedCommand.code(),
                checked_i64(current_period, "command period")?
            ],
            |row| {
                Ok(AcceptedCommandRow {
                    journal_seq: row.get(0)?,
                    resolved_period: row.get(1)?,
                    resolution_seq: row.get(2)?,
                    entry_hash: row.get(3)?,
                })
            },
        )
        .optional()?;
    if let Some(accepted) = accepted {
        let accepted_seq = accepted.journal_seq;
        let resolved_period = accepted.resolved_period;
        let resolution_seq = accepted.resolution_seq;
        let accepted_hash = accepted.entry_hash;
        let (Some(resolved_period), Some(resolution_seq)) = (resolved_period, resolution_seq)
        else {
            return Err(SaveError::CorruptManifest {
                reason: "the accepted command for the committed period is unresolved",
            });
        };
        if to_u64(resolved_period, "permanent_journal.resolved_period")? != current_period {
            return Err(SaveError::CorruptManifest {
                reason: "the accepted command resolved in another period",
            });
        }
        if resolution_seq != accepted_seq.saturating_add(1) {
            return Err(SaveError::CorruptManifest {
                reason: "the command resolution is not the next journal record",
            });
        }
        let resolution: Option<(i64, i64, Vec<u8>)> = connection
            .query_row(
                "SELECT kind, period, previous_hash FROM permanent_journal WHERE journal_seq = ?1",
                params![resolution_seq],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
            )
            .optional()?;
        match resolution {
            Some((kind, period, previous_hash))
                if kind == JournalKind::ResolvedBatch.code()
                    && to_u64(period, "permanent_journal.period")? == current_period
                    && hash_from_row("permanent_journal", &previous_hash)?
                        == hash_from_row("permanent_journal", &accepted_hash)? => {}
            _ => {
                return Err(SaveError::CorruptManifest {
                    reason: "the command resolution record is missing or foreign",
                });
            }
        }
    }
    Ok(())
}

struct AcceptedCommandRow {
    journal_seq: i64,
    resolved_period: Option<i64>,
    resolution_seq: Option<i64>,
    entry_hash: Vec<u8>,
}

fn resolve_prior_subject(
    connection: &Connection,
    subject_kind: SubjectKind,
    subject_id: &[u8],
    period: u64,
    resolution_seq: u64,
) -> Result<(), SaveError> {
    let unresolved: Option<i64> = connection
        .query_row(
            "SELECT journal_seq FROM permanent_journal
             WHERE kind <> ?1 AND subject_kind = ?2 AND subject_id = ?3
               AND resolved_period IS NULL AND journal_seq < ?4
             ORDER BY journal_seq DESC LIMIT 1",
            params![
                JournalKind::AcceptedCommand.code(),
                subject_kind.code(),
                subject_id,
                checked_i64(resolution_seq, "journal sequence")?
            ],
            |row| row.get(0),
        )
        .optional()?;
    let Some(unresolved) = unresolved else {
        return Err(SaveError::UnresolvedSubjectMissing);
    };
    let updated = connection.execute(
        "UPDATE permanent_journal SET resolved_period = ?1, resolution_seq = ?2
         WHERE journal_seq = ?3 AND resolved_period IS NULL",
        params![
            checked_i64(period, "journal period")?,
            checked_i64(resolution_seq, "journal sequence")?,
            unresolved
        ],
    )?;
    if updated != 1 {
        return Err(SaveError::UnresolvedSubjectMissing);
    }
    Ok(())
}

fn unresolved_command(
    connection: &Connection,
    period: u64,
) -> Result<Option<UnresolvedCommand>, SaveError> {
    let row = connection
        .query_row(
            "SELECT journal_seq, actor_id, codec, raw_len, raw_hash, payload
             FROM permanent_journal
             WHERE kind = ?1 AND period = ?2 AND resolved_period IS NULL",
            params![
                JournalKind::AcceptedCommand.code(),
                checked_i64(period, "command period")?
            ],
            |row| {
                Ok((
                    row.get::<_, i64>(0)?,
                    row.get::<_, Option<Vec<u8>>>(1)?,
                    row.get::<_, i64>(2)?,
                    row.get::<_, i64>(3)?,
                    row.get::<_, Vec<u8>>(4)?,
                    row.get::<_, Vec<u8>>(5)?,
                ))
            },
        )
        .optional()?;
    let Some((journal_seq, actor, codec_code, raw_len, raw_hash, payload)) = row else {
        return Ok(None);
    };
    let actor_id =
        match actor {
            Some(bytes) => Some(<[u8; 8]>::try_from(bytes.as_slice()).map_err(|_| {
                SaveError::CorruptPayload {
                    table: "permanent_journal",
                    reason: "the accepted actor identity is not eight bytes",
                }
            })?),
            None => None,
        };
    let stored = codec::StoredPayload {
        codec: PayloadCodec::from_code(codec_code)?,
        raw_len: u32::try_from(raw_len).map_err(|_| SaveError::CorruptPayload {
            table: "permanent_journal",
            reason: "the accepted payload length is out of range",
        })?,
        raw_hash: hash_from_row("permanent_journal", &raw_hash)?,
        payload: &payload,
    };
    let decoded = codec::decode_chunk_payload(PayloadBudget::PermanentJournal, &stored)?;
    Ok(Some(UnresolvedCommand {
        journal_seq,
        actor_id,
        payload: decoded,
        raw_len: stored.raw_len,
        raw_hash: stored.raw_hash,
    }))
}

struct UnresolvedCommand {
    journal_seq: i64,
    actor_id: Option<[u8; 8]>,
    payload: Vec<u8>,
    raw_len: u32,
    raw_hash: [u8; 32],
}

fn previous_chunks(
    connection: &Connection,
    snapshot_id: i64,
) -> Result<Vec<CurrentChunk>, SaveError> {
    let mut statement = connection.prepare(
        "SELECT snapshot_chunk.section, snapshot_chunk.ordinal, snapshot_chunk.chunk_id,
                state_chunk.raw_len, state_chunk.raw_hash
         FROM snapshot_chunk
         JOIN state_chunk ON state_chunk.chunk_id = snapshot_chunk.chunk_id
         WHERE snapshot_chunk.snapshot_id = ?1
         ORDER BY snapshot_chunk.section, snapshot_chunk.ordinal",
    )?;
    let rows = statement.query_map(params![snapshot_id], |row| {
        Ok((
            row.get::<_, i64>(0)?,
            row.get::<_, i64>(1)?,
            row.get::<_, i64>(2)?,
            row.get::<_, i64>(3)?,
            row.get::<_, Vec<u8>>(4)?,
        ))
    })?;
    let mut chunks = Vec::new();
    for row in rows {
        let (section_code, ordinal, chunk_id, raw_len, raw_hash) = row?;
        chunks.push(CurrentChunk {
            section: section_from_code(section_code)?,
            ordinal: u32::try_from(ordinal).map_err(|_| SaveError::CorruptManifest {
                reason: "a stored chunk ordinal is out of range",
            })?,
            chunk_id,
            raw_len: u32::try_from(raw_len).map_err(|_| SaveError::CorruptManifest {
                reason: "a stored chunk length is out of range",
            })?,
            raw_hash: hash_from_row("state_chunk", &raw_hash)?,
        });
    }
    Ok(chunks)
}

pub(super) struct SnapshotHeader {
    pub(super) snapshot_id: i64,
    pub(super) role: SnapshotRole,
    pub(super) period: u64,
    pub(super) world_hash: [u8; 32],
    pub(super) state_hash: [u8; 32],
    pub(super) manifest_bytes: Vec<u8>,
    pub(super) committed_journal_seq: u64,
    pub(super) committed_journal_hash: [u8; 32],
    pub(super) knowledge_seq: u64,
    pub(super) knowledge_hash: [u8; 32],
}

pub(super) struct Manifest {
    pub(super) campaign_id: CampaignId,
    pub(super) build_hash: [u8; 32],
    pub(super) content_hash: [u8; 32],
    pub(super) current_snapshot_id: i64,
    pub(super) journal_tail_seq: u64,
    pub(super) journal_tail_hash: [u8; 32],
    pub(super) knowledge_tail_seq: u64,
    pub(super) knowledge_tail_hash: [u8; 32],
}

pub(super) fn read_manifest(connection: &Connection) -> Result<Manifest, SaveError> {
    connection
        .query_row(
            "SELECT schema_version, campaign_id, build_hash, content_hash, current_snapshot_id,
                    journal_tail_seq, journal_tail_hash, knowledge_tail_seq, knowledge_tail_hash
             FROM save_manifest WHERE id = 1",
            [],
            |row| {
                let schema_version = row.get::<_, i64>(0)?;
                if schema_version != i64::from(SCHEMA_VERSION) {
                    return Err(corruption(
                        "the manifest schema version disagrees with the file",
                    ));
                }
                Ok(Manifest {
                    campaign_id: CampaignId::from_uuid(uuid::Uuid::from_bytes(
                        hash16(&row.get::<_, Vec<u8>>(1)?).map_err(to_sqlite)?,
                    )),
                    build_hash: hash_from_row("save_manifest", &row.get::<_, Vec<u8>>(2)?)
                        .map_err(to_sqlite)?,
                    content_hash: hash_from_row("save_manifest", &row.get::<_, Vec<u8>>(3)?)
                        .map_err(to_sqlite)?,
                    current_snapshot_id: row.get(4)?,
                    journal_tail_seq: to_u64(row.get(5)?, "save_manifest.journal_tail_seq")
                        .map_err(to_sqlite)?,
                    journal_tail_hash: hash_from_row("save_manifest", &row.get::<_, Vec<u8>>(6)?)
                        .map_err(to_sqlite)?,
                    knowledge_tail_seq: to_u64(row.get(7)?, "save_manifest.knowledge_tail_seq")
                        .map_err(to_sqlite)?,
                    knowledge_tail_hash: hash_from_row("save_manifest", &row.get::<_, Vec<u8>>(8)?)
                        .map_err(to_sqlite)?,
                })
            },
        )
        .map_err(SaveError::from)
}

pub(super) fn read_snapshot(
    connection: &Connection,
    snapshot_id: i64,
) -> Result<SnapshotHeader, SaveError> {
    connection
        .query_row(
            "SELECT snapshot_id, role, period, world_hash, state_hash, manifest_bytes,
                    committed_journal_seq, committed_journal_hash, knowledge_seq, knowledge_hash
             FROM snapshot WHERE snapshot_id = ?1",
            params![snapshot_id],
            decode_snapshot_row,
        )
        .optional()?
        .ok_or(SaveError::CorruptManifest {
            reason: "the manifest names a missing snapshot",
        })
}

/// Read one committed period's compact permanent summary.
///
/// The summary is the durable reconciliation identity of a committed period, so
/// a lost-ack retry is answered without a retained snapshot and without
/// re-executing the period.
fn period_summary_for(
    connection: &Connection,
    period: u64,
) -> Result<Option<(PeriodSummary, u64, [u8; 32])>, SaveError> {
    let row = connection
        .query_row(
            "SELECT journal_seq, codec, raw_len, raw_hash, payload, entry_hash
             FROM permanent_journal
             WHERE kind = ?1 AND period = ?2 ORDER BY journal_seq",
            params![
                JournalKind::PeriodSummary.code(),
                checked_i64(period, "summary period")?
            ],
            decode_stored_summary,
        )
        .optional()?;
    let Some(stored_summary) = row else {
        return Ok(None);
    };
    let stored = codec::StoredPayload {
        codec: codec::PayloadCodec::from_code(stored_summary.codec)?,
        raw_len: stored_summary.raw_len,
        raw_hash: hash_from_row("permanent_journal", &stored_summary.raw_hash)?,
        payload: &stored_summary.payload,
    };
    let decoded = codec::decode_chunk_payload(PayloadBudget::PermanentJournal, &stored)?;
    let summary = retention::decode_period_summary(&decoded)?;
    if summary.period != period {
        return Err(SaveError::CorruptManifest {
            reason: "the period summary names another period",
        });
    }
    let retained_manifest: Option<Vec<u8>> = connection
        .query_row(
            "SELECT manifest_bytes FROM snapshot WHERE period = ?1
             ORDER BY snapshot_id DESC LIMIT 1",
            [checked_i64(period, "summary period")?],
            |row| row.get(0),
        )
        .optional()?;
    if let Some(manifest_bytes) = retained_manifest {
        if decode_manifest(&manifest_bytes)?.candidate_hash != summary.candidate_hash {
            return Err(SaveError::CorruptManifest {
                reason: "the retained snapshot and the period summary disagree",
            });
        }
    }
    Ok(Some((
        summary,
        to_u64(stored_summary.journal_seq, "permanent_journal.journal_seq")?,
        hash_from_row("permanent_journal", &stored_summary.entry_hash)?,
    )))
}

struct StoredSummaryRow {
    journal_seq: i64,
    codec: i64,
    raw_len: u32,
    raw_hash: Vec<u8>,
    payload: Vec<u8>,
    entry_hash: Vec<u8>,
}

fn decode_stored_summary(row: &Row<'_>) -> SqliteResult<StoredSummaryRow> {
    Ok(StoredSummaryRow {
        journal_seq: row.get(0)?,
        codec: row.get(1)?,
        raw_len: u32::try_from(row.get::<_, i64>(2)?)
            .map_err(|_| corruption("the period summary length is out of range"))?,
        raw_hash: row.get(3)?,
        payload: row.get(4)?,
        entry_hash: row.get(5)?,
    })
}

pub(super) fn decode_snapshot_row(row: &Row<'_>) -> SqliteResult<SnapshotHeader> {
    Ok(SnapshotHeader {
        snapshot_id: row.get(0)?,
        role: snapshot_role_from_code(row.get(1)?)?,
        period: to_u64(row.get(2)?, "snapshot.period").map_err(to_sqlite)?,
        world_hash: hash_from_row("snapshot", &row.get::<_, Vec<u8>>(3)?).map_err(to_sqlite)?,
        state_hash: hash_from_row("snapshot", &row.get::<_, Vec<u8>>(4)?).map_err(to_sqlite)?,
        manifest_bytes: row.get(5)?,
        committed_journal_seq: to_u64(row.get(6)?, "snapshot.committed_journal_seq")
            .map_err(to_sqlite)?,
        committed_journal_hash: hash_from_row("snapshot", &row.get::<_, Vec<u8>>(7)?)
            .map_err(to_sqlite)?,
        knowledge_seq: to_u64(row.get(8)?, "snapshot.knowledge_seq").map_err(to_sqlite)?,
        knowledge_hash: hash_from_row("snapshot", &row.get::<_, Vec<u8>>(9)?).map_err(to_sqlite)?,
    })
}

/// Insert one snapshot row and return its integer identity.
#[allow(
    clippy::too_many_arguments,
    reason = "the snapshot row is the physical commit boundary and mirrors it exactly"
)]
fn insert_snapshot(
    connection: &Connection,
    role: SnapshotRole,
    period: u64,
    world_hash: [u8; 32],
    state_hash: [u8; 32],
    manifest_bytes: &[u8],
    journal_seq: u64,
    journal_hash: [u8; 32],
    knowledge_seq: u64,
    knowledge_hash: [u8; 32],
) -> Result<i64, SaveError> {
    connection.execute(
        "INSERT INTO snapshot (
            role, period, world_hash, state_hash, manifest_bytes,
            committed_journal_seq, committed_journal_hash, knowledge_seq, knowledge_hash
         ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)",
        params![
            role.code(),
            checked_i64(period, "snapshot period")?,
            &world_hash[..],
            &state_hash[..],
            manifest_bytes,
            checked_i64(journal_seq, "journal sequence")?,
            &journal_hash[..],
            checked_i64(knowledge_seq, "knowledge sequence")?,
            &knowledge_hash[..],
        ],
    )?;
    Ok(connection.last_insert_rowid())
}

fn insert_chunk_links(
    connection: &Connection,
    snapshot_id: i64,
    links: &[(i64, ChunkDescriptor)],
) -> Result<(), SaveError> {
    for (chunk_id, descriptor) in links {
        connection.execute(
            "INSERT INTO snapshot_chunk (snapshot_id, section, ordinal, chunk_id)
             VALUES (?1, ?2, ?3, ?4)",
            params![
                snapshot_id,
                descriptor.section.code(),
                i64::from(descriptor.ordinal),
                chunk_id
            ],
        )?;
    }
    Ok(())
}

fn validate_content(captured: &AdmittedContent) -> Result<(), SaveError> {
    let mut seen: Vec<(i64, Vec<u8>, u32)> = Vec::with_capacity(captured.entries.len());
    for entry in &captured.entries {
        if entry.key.is_empty() {
            return Err(SaveError::InvalidField {
                table: "content_entry",
                field: "entry_key",
                reason: "the entry key is empty",
            });
        }
        if entry.key.len() > MAX_CONTENT_KEY_BYTES {
            return Err(SaveError::InvalidField {
                table: "content_entry",
                field: "entry_key",
                reason: "the entry key exceeds one KiB",
            });
        }
        if entry.bytes.len() > codec::MAX_CONTENT_CHUNK_BYTES {
            return Err(SaveError::PayloadTooLarge {
                table: "content_entry",
                limit: codec::MAX_CONTENT_CHUNK_BYTES,
                actual: entry.bytes.len(),
            });
        }
        let position = (entry.kind.code(), entry.key.clone(), entry.ordinal);
        if seen.contains(&position) {
            return Err(SaveError::DuplicateContentEntry);
        }
        seen.push(position);
    }
    Ok(())
}

fn validate_chunks(table: &'static str, chunks: &[StateChunk]) -> Result<(), SaveError> {
    if u32::try_from(chunks.len()).map_or(true, |count| count > MAX_SNAPSHOT_CHUNKS) {
        return Err(SaveError::InvalidField {
            table,
            field: "chunks",
            reason: "the restart root exceeds the snapshot chunk ceiling",
        });
    }
    let mut seen: Vec<(ChunkSection, u32)> = Vec::with_capacity(chunks.len());
    for chunk in chunks {
        if chunk.bytes.len() > codec::MAX_STATE_CHUNK_BYTES {
            return Err(SaveError::PayloadTooLarge {
                table,
                limit: codec::MAX_STATE_CHUNK_BYTES,
                actual: chunk.bytes.len(),
            });
        }
        if seen.contains(&(chunk.section, chunk.ordinal)) {
            return Err(SaveError::DuplicateChunkPosition {
                section: chunk.section.code(),
                ordinal: chunk.ordinal,
            });
        }
        seen.push((chunk.section, chunk.ordinal));
    }
    Ok(())
}

struct PreparedCandidate {
    chunks: Vec<ChunkDescriptor>,
    journal: Vec<JournalDescriptor>,
    knowledge: Vec<KnowledgeDescriptor>,
    candidate_hash: [u8; 32],
}

#[derive(Clone, Copy)]
struct ChunkDescriptor {
    section: ChunkSection,
    ordinal: u32,
    raw_len: u32,
    raw_hash: [u8; 32],
}

struct JournalDescriptor {
    raw_len: u32,
    raw_hash: [u8; 32],
}

struct KnowledgeDescriptor {
    raw_len: u32,
    raw_hash: [u8; 32],
}

fn ordered_chunks(chunks: &[StateChunk]) -> Vec<&StateChunk> {
    let mut ordered: Vec<&StateChunk> = chunks.iter().collect();
    ordered.sort_by_key(|chunk| (chunk.section.code(), chunk.ordinal));
    ordered
}

fn prepare_opening(opening: &AdmittedOpening) -> Result<PreparedCandidate, SaveError> {
    let chunks: Vec<ChunkDescriptor> = ordered_chunks(&opening.chunks)
        .iter()
        .map(|chunk| {
            Ok(ChunkDescriptor {
                section: chunk.section,
                ordinal: chunk.ordinal,
                raw_len: u32::try_from(chunk.bytes.len()).map_err(|_| SaveError::Arithmetic {
                    field: "state chunk length",
                })?,
                raw_hash: content_digest::sha256_of(&chunk.bytes),
            })
        })
        .collect::<Result<_, SaveError>>()?;
    let candidate_hash =
        period_candidate_hash(0, opening.world_hash, opening.state_hash, &chunks, &[], &[])?;
    Ok(PreparedCandidate {
        chunks,
        journal: Vec::new(),
        knowledge: Vec::new(),
        candidate_hash,
    })
}

#[allow(
    clippy::too_many_lines,
    reason = "one admission pass validates every section of the prepared period before publication"
)]
fn prepare_candidate(candidate: &PreparedPeriod) -> Result<PreparedCandidate, SaveError> {
    if candidate.chunks.is_empty() {
        return Err(SaveError::InvalidField {
            table: "snapshot",
            field: "chunks",
            reason: "a period commit needs at least one state chunk",
        });
    }
    validate_chunks("state_chunk", &candidate.chunks)?;
    let chunks: Vec<ChunkDescriptor> = ordered_chunks(&candidate.chunks)
        .iter()
        .map(|chunk| {
            Ok(ChunkDescriptor {
                section: chunk.section,
                ordinal: chunk.ordinal,
                raw_len: u32::try_from(chunk.bytes.len()).map_err(|_| SaveError::Arithmetic {
                    field: "state chunk length",
                })?,
                raw_hash: content_digest::sha256_of(&chunk.bytes),
            })
        })
        .collect::<Result<_, SaveError>>()?;

    let mut journal = Vec::with_capacity(candidate.journal.len());
    for record in &candidate.journal {
        if matches!(
            record.kind,
            JournalKind::AcceptedCommand | JournalKind::ResolvedBatch | JournalKind::PeriodSummary
        ) {
            return Err(SaveError::ReservedJournalKind {
                code: record.kind.code(),
            });
        }
        if record.payload.len() > codec::MAX_PERMANENT_JOURNAL_BYTES {
            return Err(SaveError::PayloadTooLarge {
                table: "permanent_journal",
                limit: codec::MAX_PERMANENT_JOURNAL_BYTES,
                actual: record.payload.len(),
            });
        }
        match &record.subject {
            Some(subject) if subject.id.is_empty() => {
                return Err(SaveError::InvalidField {
                    table: "permanent_journal",
                    field: "subject_id",
                    reason: "the subject identity is empty",
                });
            }
            Some(subject) if subject.id.len() > MAX_SUBJECT_ID_BYTES => {
                return Err(SaveError::InvalidField {
                    table: "permanent_journal",
                    field: "subject_id",
                    reason: "the subject identity exceeds one KiB",
                });
            }
            None if record.resolves_prior_subject => {
                return Err(SaveError::UnresolvedSubjectMissing);
            }
            _ => {}
        }
        if record.record_key.as_ref().is_some_and(Vec::is_empty) {
            return Err(SaveError::InvalidField {
                table: "permanent_journal",
                field: "record_key",
                reason: "the record key is empty",
            });
        }
        if record
            .record_key
            .as_ref()
            .is_some_and(|key| key.len() > MAX_SUBJECT_ID_BYTES)
        {
            return Err(SaveError::InvalidField {
                table: "permanent_journal",
                field: "record_key",
                reason: "the record key exceeds one KiB",
            });
        }
        journal.push(JournalDescriptor {
            raw_len: u32::try_from(record.payload.len()).map_err(|_| SaveError::Arithmetic {
                field: "journal payload length",
            })?,
            raw_hash: content_digest::sha256_of(&record.payload),
        });
    }

    let mut knowledge = Vec::with_capacity(candidate.knowledge.len());
    let mut seen: Vec<([u8; 8], SubjectKind, Vec<u8>, i64)> =
        Vec::with_capacity(candidate.knowledge.len());
    for grant in &candidate.knowledge {
        if grant.payload.is_empty() || grant.payload.len() > MAX_KNOWLEDGE_PAYLOAD_BYTES {
            return Err(SaveError::PayloadTooLarge {
                table: "knowledge_grant",
                limit: MAX_KNOWLEDGE_PAYLOAD_BYTES,
                actual: grant.payload.len(),
            });
        }
        if grant.subject.id.is_empty() {
            return Err(SaveError::InvalidField {
                table: "knowledge_grant",
                field: "subject_id",
                reason: "the subject identity is empty",
            });
        }
        if grant.subject.id.len() > MAX_SUBJECT_ID_BYTES {
            return Err(SaveError::InvalidField {
                table: "knowledge_grant",
                field: "subject_id",
                reason: "the subject identity exceeds one KiB",
            });
        }
        let identity = (
            grant.player_id,
            grant.subject.kind,
            grant.subject.id.clone(),
            grant.grant_key,
        );
        if seen.contains(&identity) {
            return Err(SaveError::DuplicateKnowledgeGrant);
        }
        seen.push(identity);
        knowledge.push(KnowledgeDescriptor {
            raw_len: u32::try_from(grant.payload.len()).map_err(|_| SaveError::Arithmetic {
                field: "knowledge payload length",
            })?,
            raw_hash: content_digest::sha256_of(&grant.payload),
        });
    }

    let candidate_hash = period_candidate_hash(
        candidate.period,
        candidate.world_hash,
        candidate.state_hash,
        &chunks,
        &journal,
        &knowledge,
    )?;
    Ok(PreparedCandidate {
        chunks,
        journal,
        knowledge,
        candidate_hash,
    })
}

fn period_candidate_hash(
    period: u64,
    world_hash: [u8; 32],
    state_hash: [u8; 32],
    chunks: &[ChunkDescriptor],
    journal: &[JournalDescriptor],
    knowledge: &[KnowledgeDescriptor],
) -> Result<[u8; 32], SaveError> {
    let mut bytes = CanonicalBytes::new(CANDIDATE_DOMAIN);
    bytes.u64(period);
    bytes.hash(world_hash);
    bytes.hash(state_hash);
    bytes.u32(count(chunks.len(), "candidate chunk count")?);
    for chunk in chunks {
        bytes.i64(chunk.section.code());
        bytes.u32(chunk.ordinal);
        bytes.u32(chunk.raw_len);
        bytes.hash(chunk.raw_hash);
    }
    bytes.u32(count(journal.len(), "candidate journal count")?);
    for record in journal {
        bytes.u32(record.raw_len);
        bytes.hash(record.raw_hash);
    }
    bytes.u32(count(knowledge.len(), "candidate knowledge count")?);
    for grant in knowledge {
        bytes.u32(grant.raw_len);
        bytes.hash(grant.raw_hash);
    }
    Ok(bytes.finish())
}

fn admitted_content_hash(entries: &[AdmittedContentEntry]) -> Result<[u8; 32], SaveError> {
    let mut bytes = CanonicalBytes::new(CONTENT_DOMAIN);
    bytes.u32(count(entries.len(), "content entry count")?);
    for entry in entries {
        bytes.i64(entry.kind.code());
        bytes.blob(&entry.key)?;
        bytes.u32(entry.ordinal);
        bytes.u32(count(entry.bytes.len(), "content entry length")?);
        bytes.hash(content_digest::sha256_of(&entry.bytes));
    }
    Ok(bytes.finish())
}

pub(super) struct JournalInput<'a> {
    pub(super) journal_seq: u64,
    pub(super) kind: JournalKind,
    pub(super) period: u64,
    pub(super) actor_id: Option<[u8; 8]>,
    pub(super) subject: Option<(SubjectKind, &'a [u8])>,
    pub(super) nonce: Option<[u8; 16]>,
    pub(super) record_key: Option<&'a [u8]>,
    pub(super) raw_len: u32,
    pub(super) raw_hash: [u8; 32],
    pub(super) previous_hash: [u8; 32],
}

/// Hash one journal record's canonical identity.
///
/// # Errors
///
/// Refuses a subject identity or record key wider than its `u32` length prefix.
pub(super) fn journal_entry_hash(input: &JournalInput<'_>) -> Result<[u8; 32], SaveError> {
    let mut bytes = CanonicalBytes::new(JOURNAL_DOMAIN);
    bytes.u64(input.journal_seq);
    bytes.i64(input.kind.code());
    bytes.u64(input.period);
    match input.actor_id {
        Some(actor) => {
            bytes.u8(1);
            bytes.raw(&actor);
        }
        None => bytes.u8(0),
    }
    match input.subject {
        Some((kind, id)) => {
            bytes.u8(1);
            bytes.i64(kind.code());
            bytes.blob(id)?;
        }
        None => bytes.u8(0),
    }
    match input.nonce {
        Some(nonce) => {
            bytes.u8(1);
            bytes.raw(&nonce);
        }
        None => bytes.u8(0),
    }
    match input.record_key {
        Some(key) => {
            bytes.u8(1);
            bytes.blob(key)?;
        }
        None => bytes.u8(0),
    }
    bytes.u32(input.raw_len);
    bytes.hash(input.raw_hash);
    bytes.hash(input.previous_hash);
    Ok(bytes.finish())
}

pub(super) struct KnowledgeInput<'a> {
    pub(super) knowledge_seq: u64,
    pub(super) player_id: [u8; 8],
    pub(super) subject_kind: SubjectKind,
    pub(super) subject_id: &'a [u8],
    pub(super) grant_key: i64,
    pub(super) acquired_period: u64,
    pub(super) source_journal_seq: u64,
    pub(super) raw_len: u32,
    pub(super) raw_hash: [u8; 32],
    pub(super) previous_hash: [u8; 32],
}

/// Hash one earned grant's canonical identity.
///
/// # Errors
///
/// Refuses a subject identity wider than its `u32` length prefix.
pub(super) fn knowledge_entry_hash(input: &KnowledgeInput<'_>) -> Result<[u8; 32], SaveError> {
    let mut bytes = CanonicalBytes::new(KNOWLEDGE_DOMAIN);
    bytes.u64(input.knowledge_seq);
    bytes.raw(&input.player_id);
    bytes.i64(input.subject_kind.code());
    bytes.blob(input.subject_id)?;
    bytes.i64(input.grant_key);
    bytes.u64(input.acquired_period);
    bytes.u64(input.source_journal_seq);
    bytes.u32(input.raw_len);
    bytes.hash(input.raw_hash);
    bytes.hash(input.previous_hash);
    Ok(bytes.finish())
}

fn encode_manifest(
    chunks: &[ChunkDescriptor],
    candidate_hash: [u8; 32],
) -> Result<Vec<u8>, SaveError> {
    let mut bytes = CanonicalBytes::new(&[]);
    bytes.u8(MANIFEST_VERSION);
    bytes.u32(count(chunks.len(), "snapshot chunk count")?);
    for chunk in chunks {
        bytes.i64(chunk.section.code());
        bytes.u32(chunk.ordinal);
        bytes.u32(chunk.raw_len);
        bytes.hash(chunk.raw_hash);
    }
    bytes.hash(candidate_hash);
    Ok(bytes.into_bytes())
}

struct DecodedManifest {
    chunks: Vec<ChunkDescriptor>,
    candidate_hash: [u8; 32],
}

fn decode_manifest(bytes: &[u8]) -> Result<DecodedManifest, SaveError> {
    let mut reader = ManifestReader::new(bytes);
    if reader.u8()? != MANIFEST_VERSION {
        return Err(SaveError::CorruptManifest {
            reason: "the snapshot manifest version is unsupported",
        });
    }
    let count = reader.u32()?;
    if count > MAX_SNAPSHOT_CHUNKS {
        return Err(SaveError::CorruptManifest {
            reason: "the snapshot manifest declares too many chunks",
        });
    }
    let capacity = usize::try_from(count).map_err(|_| SaveError::CorruptManifest {
        reason: "the snapshot manifest chunk count is out of range",
    })?;
    let mut chunks = Vec::with_capacity(capacity);
    for _ in 0..count {
        chunks.push(ChunkDescriptor {
            section: section_from_code(reader.i64()?)?,
            ordinal: reader.u32()?,
            raw_len: reader.u32()?,
            raw_hash: reader.hash()?,
        });
    }
    let candidate_hash = reader.hash()?;
    if !reader.is_empty() {
        return Err(SaveError::CorruptManifest {
            reason: "the snapshot manifest has trailing bytes",
        });
    }
    Ok(DecodedManifest {
        chunks,
        candidate_hash,
    })
}

struct ManifestReader<'a> {
    bytes: &'a [u8],
    offset: usize,
}

impl<'a> ManifestReader<'a> {
    const fn new(bytes: &'a [u8]) -> Self {
        Self { bytes, offset: 0 }
    }

    const fn is_empty(&self) -> bool {
        self.offset == self.bytes.len()
    }

    fn take(&mut self, width: usize) -> Result<&'a [u8], SaveError> {
        let end = self
            .offset
            .checked_add(width)
            .ok_or(SaveError::CorruptManifest {
                reason: "the snapshot manifest offset overflowed",
            })?;
        let slice = self
            .bytes
            .get(self.offset..end)
            .ok_or(SaveError::CorruptManifest {
                reason: "the snapshot manifest is truncated",
            })?;
        self.offset = end;
        Ok(slice)
    }

    fn u8(&mut self) -> Result<u8, SaveError> {
        let slice = self.take(1)?;
        slice.first().copied().ok_or(SaveError::CorruptManifest {
            reason: "the snapshot manifest is truncated",
        })
    }

    fn u32(&mut self) -> Result<u32, SaveError> {
        let slice = self.take(4)?;
        let array: [u8; 4] = slice.try_into().map_err(|_| SaveError::CorruptManifest {
            reason: "the snapshot manifest integer is truncated",
        })?;
        Ok(u32::from_be_bytes(array))
    }

    fn i64(&mut self) -> Result<i64, SaveError> {
        let slice = self.take(8)?;
        let array: [u8; 8] = slice.try_into().map_err(|_| SaveError::CorruptManifest {
            reason: "the snapshot manifest integer is truncated",
        })?;
        Ok(i64::from_be_bytes(array))
    }

    fn hash(&mut self) -> Result<[u8; 32], SaveError> {
        let slice = self.take(32)?;
        <[u8; 32]>::try_from(slice).map_err(|_| SaveError::CorruptManifest {
            reason: "the snapshot manifest hash is truncated",
        })
    }
}

struct CanonicalBytes(Vec<u8>);

impl CanonicalBytes {
    fn new(domain: &[u8]) -> Self {
        Self(domain.to_vec())
    }

    fn raw(&mut self, bytes: &[u8]) {
        self.0.extend_from_slice(bytes);
    }

    fn u8(&mut self, value: u8) {
        self.0.push(value);
    }

    fn u32(&mut self, value: u32) {
        self.0.extend_from_slice(&value.to_be_bytes());
    }

    fn u64(&mut self, value: u64) {
        self.0.extend_from_slice(&value.to_be_bytes());
    }

    fn i64(&mut self, value: i64) {
        self.0.extend_from_slice(&value.to_be_bytes());
    }

    fn blob(&mut self, bytes: &[u8]) -> Result<(), SaveError> {
        let length = u32::try_from(bytes.len()).map_err(|_| SaveError::Arithmetic {
            field: "canonical blob length",
        })?;
        self.u32(length);
        self.0.extend_from_slice(bytes);
        Ok(())
    }

    fn hash(&mut self, hash: [u8; 32]) {
        self.0.extend_from_slice(&hash);
    }

    fn finish(self) -> [u8; 32] {
        Sha256::digest(&self.0).into()
    }

    fn into_bytes(self) -> Vec<u8> {
        self.0
    }
}

fn section_from_code(code: i64) -> Result<ChunkSection, SaveError> {
    ChunkSection::from_code(code).ok_or(SaveError::CorruptManifest {
        reason: "a stored chunk section is outside the closed registry",
    })
}

fn snapshot_role_from_code(code: i64) -> SqliteResult<SnapshotRole> {
    match code {
        1 => Ok(SnapshotRole::Opening),
        2 => Ok(SnapshotRole::Current),
        3 => Ok(SnapshotRole::Historical),
        other => Err(corruption(format!(
            "snapshot role {other} is outside the closed registry"
        ))),
    }
}

fn hash_from_row(table: &'static str, bytes: &[u8]) -> Result<[u8; 32], SaveError> {
    <[u8; 32]>::try_from(bytes).map_err(|_| SaveError::CorruptPayload {
        table,
        reason: "the stored hash is not 32 bytes",
    })
}

fn hash16(bytes: &[u8]) -> Result<[u8; 16], SaveError> {
    <[u8; 16]>::try_from(bytes).map_err(|_| SaveError::CorruptManifest {
        reason: "the stored campaign identity is not sixteen bytes",
    })
}

#[allow(
    clippy::needless_pass_by_value,
    reason = "map_err supplies the owned SaveError and the adapter only formats it"
)]
fn to_sqlite(error: SaveError) -> rusqlite::Error {
    rusqlite::Error::FromSqlConversionFailure(
        0,
        Type::Blob,
        Box::new(Error::new(ErrorKind::InvalidData, error.to_string())),
    )
}

fn corruption(reason: impl Into<String>) -> rusqlite::Error {
    rusqlite::Error::FromSqlConversionFailure(
        0,
        Type::Blob,
        Box::new(Error::new(ErrorKind::InvalidData, reason.into())),
    )
}

fn to_u64(value: i64, field: &'static str) -> Result<u64, SaveError> {
    u64::try_from(value).map_err(|_| SaveError::Arithmetic { field })
}

fn checked_i64(value: u64, field: &'static str) -> Result<i64, SaveError> {
    i64::try_from(value).map_err(|_| SaveError::Arithmetic { field })
}

fn count(value: usize, field: &'static str) -> Result<u32, SaveError> {
    u32::try_from(value).map_err(|_| SaveError::Arithmetic { field })
}

fn elapsed_ns(started: Instant) -> u64 {
    u64::try_from(started.elapsed().as_nanos()).unwrap_or(u64::MAX)
}

fn remove_database_files(path: &Path) {
    let _ = fs::remove_file(path);
    for suffix in ["-wal", "-shm"] {
        let mut sidecar = path.as_os_str().to_os_string();
        sidecar.push(suffix);
        let _ = fs::remove_file(PathBuf::from(sidecar));
    }
}
