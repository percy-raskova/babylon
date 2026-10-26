//! Task-scoped single-writer campaign lock and the store error surface.
//!
//! The owner writes a twenty-byte record beside the campaign database: the
//! owning process id in canonical big-endian order followed by the sixteen
//! canonical campaign identity bytes. A second writer refuses with that owner
//! identity instead of silently opening another runtime. The record is removed
//! when the owning handle drops.
//!
//! A record left by a crashed owner is recovered only when both checks agree:
//! the recorded process id is not live, and the campaign database either has no
//! committed `save_manifest` row yet or records the same campaign identity. A
//! live owner always refuses. A dead owner whose database records a different
//! campaign refuses as [`SaveError::LockRecordMismatch`] rather than deleting
//! evidence. Takeover is serialized by a short-lived `.lock.recover` claim so
//! two recovering processes cannot delete each other's fresh record.
//!
//! [`SaveError`] is the store-level error surface. Task 5 (`P3a`) needs the lock
//! refusal and the schema, codec and chunk refusals; Task 6 (`P3b`) extends it
//! as the lifecycle operations land.

use std::fmt::Formatter;
use std::fmt::Result as FmtResult;
use std::fs;
use std::fs::File;
use std::fs::OpenOptions;
use std::io::Error as IoError;
use std::io::ErrorKind;
use std::io::Write;
use std::path::Path;
use std::path::PathBuf;

use rusqlite::Connection;
use rusqlite::Error as SqliteError;
use rusqlite::OpenFlags;
use rusqlite::OptionalExtension;
use uuid::Uuid;

use crate::identity::CampaignId;
use crate::sqlite_runtime_pin::SqlitePinError;
use crate::sqlite_store::codec::PayloadCodec;

/// Exact width of the owner record written beside the campaign database.
pub const LOCK_RECORD_BYTES: usize = 20;

/// Why the campaign store refused an operation.
#[derive(Debug)]
pub enum SaveError {
    /// Another live task owns this campaign path.
    CampaignLocked {
        /// Process id recorded by the owning writer.
        owner_pid: u32,
        /// Campaign identity recorded by the owning writer.
        campaign_id: CampaignId,
    },
    /// The lock record beside the campaign file is not an owner record.
    LockRecordInvalid {
        /// Path of the malformed lock record.
        path: PathBuf,
    },
    /// A dead owner's lock record names a campaign the database does not hold.
    LockRecordMismatch {
        /// Campaign identity recorded beside the database.
        recorded: CampaignId,
        /// Campaign identity the committed manifest records.
        manifest: CampaignId,
    },
    /// Another process is already recovering this campaign lock.
    LockRecoveryBusy {
        /// Path of the recovery claim that is held.
        path: PathBuf,
    },
    /// A campaign already exists at the requested creation path.
    CampaignExists {
        /// Path that already holds a campaign database.
        path: PathBuf,
    },
    /// No campaign database exists at the requested path.
    CampaignMissing {
        /// Path that holds no campaign database.
        path: PathBuf,
    },
    /// The linked `SQLite` runtime is not the pinned build.
    RuntimePin(SqlitePinError),
    /// `SQLite` refused a statement.
    Sqlite(SqliteError),
    /// Host file I/O failed.
    Io(IoError),
    /// The write-ahead log could not be enabled.
    WalUnavailable,
    /// The open database has an unsupported schema version.
    SchemaVersion {
        /// Version this build requires.
        expected: u32,
        /// Version found in the database.
        actual: u32,
    },
    /// The database does not carry the exact published table set.
    SchemaMismatch {
        /// What the verification found instead.
        reason: &'static str,
    },
    /// A durable pragma does not match the required mode.
    PragmaMismatch {
        /// Pragma name.
        pragma: &'static str,
        /// Required mode.
        expected: &'static str,
        /// Mode reported by `SQLite`.
        actual: String,
    },
    /// A decoded payload exceeded its table allowance.
    PayloadTooLarge {
        /// Table that owns the allowance.
        table: &'static str,
        /// Allowance in decoded bytes.
        limit: usize,
        /// Supplied or recorded decoded length.
        actual: usize,
    },
    /// A stored codec integer is outside the closed registry.
    UnsupportedCodec {
        /// Rejected integer code.
        codec: i64,
    },
    /// A stored payload does not use its table's fixed codec.
    CodecMismatch {
        /// Table that owns the fixed selection.
        table: &'static str,
        /// Codec the format version requires.
        expected: PayloadCodec,
        /// Codec recorded beside the payload.
        actual: PayloadCodec,
    },
    /// Stored bytes no longer match their recorded identity.
    CorruptPayload {
        /// Table that owns the payload.
        table: &'static str,
        /// What failed authentication.
        reason: &'static str,
    },
    /// A canonical zstd frame could not be produced.
    CompressionFailed {
        /// Table that owns the payload.
        table: &'static str,
    },
    /// A choice endpoint exceeded the governed `2^64` upper bound.
    ChoiceEndpointOutOfRange {
        /// Rejected endpoint.
        endpoint: u128,
    },
    /// An external content package was refused before campaign publication.
    ContentPackage {
        /// The exact package or host-profile refusal.
        reason: String,
    },
    /// A typed field was empty or otherwise outside its contract.
    InvalidField {
        /// Table that owns the field.
        table: &'static str,
        /// Field that failed admission.
        field: &'static str,
        /// Why the field was refused.
        reason: &'static str,
    },
    /// A period, sequence or length did not fit its checked integer range.
    Arithmetic {
        /// Field that failed conversion.
        field: &'static str,
    },
    /// The committed build identity differs from the expected build.
    BuildMismatch {
        /// Build identity the caller requires.
        expected: [u8; 32],
        /// Build identity the campaign manifest records.
        actual: [u8; 32],
    },
    /// The committed manifest or snapshot metadata is internally inconsistent.
    CorruptManifest {
        /// What failed verification.
        reason: &'static str,
    },
    /// The candidate was prepared against a different current root.
    StaleRoot {
        /// World identity the caller expected to replace.
        expected: [u8; 32],
        /// World identity the campaign currently commits.
        actual: [u8; 32],
    },
    /// The candidate period is not the next or an already committed period.
    WrongPeriod {
        /// Period the store requires.
        expected: u64,
        /// Period offered.
        actual: u64,
    },
    /// An already committed period was offered different canonical bytes.
    ConflictingPeriodCommit {
        /// Period that already holds a different commitment.
        period: u64,
    },
    /// A caller tried to author a journal kind the owner writes itself.
    ReservedJournalKind {
        /// Rejected integer code.
        code: i64,
    },
    /// A period candidate repeats one `(section, ordinal)` chunk position.
    DuplicateChunkPosition {
        /// Repeated section code.
        section: i64,
        /// Repeated ordinal.
        ordinal: u32,
    },
    /// A content admission repeats one `(kind, entry_key, ordinal)` position.
    DuplicateContentEntry,
    /// One identity tried to acquire knowledge twice in a period.
    DuplicateKnowledgeGrant,
    /// Earned knowledge cited no period journal record.
    KnowledgeSourceMissing,
    /// A resolution named no unresolved subject.
    UnresolvedSubjectMissing,
    /// A read requested a period beyond the committed present.
    FuturePeriod {
        /// Highest committed period.
        current: u64,
        /// Requested period.
        requested: u64,
    },
    /// No earned grant discloses the requested subject at that period.
    UndisclosedSubject,
    /// The export destination already exists and is never overwritten.
    ExportDestinationExists,
    /// The exported database failed integrity or identity verification.
    ExportIdentityMismatch,
    /// A deterministic test seam aborted the operation.
    #[cfg(test)]
    InjectedFault,
}

impl std::fmt::Display for SaveError {
    #[allow(
        clippy::too_many_lines,
        reason = "one flat match publishes every refusal without a nested helper"
    )]
    fn fmt(&self, formatter: &mut Formatter<'_>) -> FmtResult {
        match self {
            Self::CampaignLocked {
                owner_pid,
                campaign_id,
            } => write!(
                formatter,
                "campaign database is already owned by process {owner_pid} for campaign {}",
                campaign_id.as_uuid()
            ),
            Self::LockRecordInvalid { path } => write!(
                formatter,
                "campaign lock record {} is not a {LOCK_RECORD_BYTES}-byte owner record",
                path.display()
            ),
            Self::LockRecordMismatch { recorded, manifest } => write!(
                formatter,
                "campaign lock record names campaign {} but the database holds {}",
                recorded.as_uuid(),
                manifest.as_uuid()
            ),
            Self::LockRecoveryBusy { path } => write!(
                formatter,
                "campaign lock recovery is already claimed at {}",
                path.display()
            ),
            Self::CampaignExists { path } => {
                write!(formatter, "a campaign already exists at {}", path.display())
            }
            Self::CampaignMissing { path } => {
                write!(formatter, "no campaign exists at {}", path.display())
            }
            Self::RuntimePin(error) => write!(formatter, "SQLite runtime pin refused: {error}"),
            Self::Sqlite(error) => {
                write!(formatter, "SQLite refused the campaign statement: {error}")
            }
            Self::Io(error) => write!(formatter, "campaign store I/O refused: {error}"),
            Self::WalUnavailable => write!(formatter, "write-ahead logging is unavailable"),
            Self::SchemaVersion { expected, actual } => write!(
                formatter,
                "campaign schema version {actual} does not match required {expected}"
            ),
            Self::SchemaMismatch { reason } => {
                write!(formatter, "campaign schema is not exact: {reason}")
            }
            Self::PragmaMismatch {
                pragma,
                expected,
                actual,
            } => write!(
                formatter,
                "campaign pragma {pragma} is {actual} instead of {expected}"
            ),
            Self::PayloadTooLarge {
                table,
                limit,
                actual,
            } => write!(
                formatter,
                "{table} payload of {actual} decoded bytes exceeds the {limit}-byte allowance"
            ),
            Self::UnsupportedCodec { codec } => {
                write!(
                    formatter,
                    "payload codec {codec} is outside the closed registry"
                )
            }
            Self::CodecMismatch {
                table,
                expected,
                actual,
            } => write!(
                formatter,
                "{table} payload codec {} does not match the required {}",
                actual.code(),
                expected.code()
            ),
            Self::CorruptPayload { table, reason } => {
                write!(formatter, "{table} payload failed authentication: {reason}")
            }
            Self::CompressionFailed { table } => {
                write!(formatter, "{table} payload could not be compressed")
            }
            Self::ChoiceEndpointOutOfRange { endpoint } => write!(
                formatter,
                "choice endpoint {endpoint} exceeds the governed 2^64 upper bound"
            ),
            Self::ContentPackage { reason } => {
                write!(formatter, "content package refused: {reason}")
            }
            Self::InvalidField {
                table,
                field,
                reason,
            } => write!(formatter, "{table}.{field} is refused: {reason}"),
            Self::Arithmetic { field } => {
                write!(formatter, "{field} did not fit its checked integer range")
            }
            Self::BuildMismatch { expected, actual } => write!(
                formatter,
                "campaign build identity {} does not match required {}",
                hex_identity(actual),
                hex_identity(expected)
            ),
            Self::CorruptManifest { reason } => {
                write!(formatter, "campaign manifest is not consistent: {reason}")
            }
            Self::StaleRoot { expected, actual } => write!(
                formatter,
                "period candidate expects world {} but the campaign commits {}",
                hex_identity(expected),
                hex_identity(actual)
            ),
            Self::WrongPeriod { expected, actual } => write!(
                formatter,
                "campaign store expected period {expected}, received {actual}"
            ),
            Self::ConflictingPeriodCommit { period } => write!(
                formatter,
                "period {period} already holds a different canonical commitment"
            ),
            Self::ReservedJournalKind { code } => {
                write!(formatter, "journal kind {code} is written by the owner")
            }
            Self::DuplicateChunkPosition { section, ordinal } => write!(
                formatter,
                "state chunk section {section} ordinal {ordinal} is offered twice"
            ),
            Self::DuplicateContentEntry => {
                write!(formatter, "the admitted content repeats one entry position")
            }
            Self::DuplicateKnowledgeGrant => {
                write!(formatter, "a knowledge identity repeats in one period")
            }
            Self::KnowledgeSourceMissing => {
                write!(formatter, "earned knowledge cites no period journal record")
            }
            Self::UnresolvedSubjectMissing => {
                write!(
                    formatter,
                    "no unresolved journal subject matches the resolution"
                )
            }
            Self::FuturePeriod { current, requested } => write!(
                formatter,
                "period {requested} is beyond the committed period {current}"
            ),
            Self::UndisclosedSubject => {
                write!(
                    formatter,
                    "no earned grant discloses that subject at that period"
                )
            }
            Self::ExportDestinationExists => {
                write!(formatter, "the export destination already exists")
            }
            Self::ExportIdentityMismatch => {
                write!(
                    formatter,
                    "the export failed integrity or identity verification"
                )
            }
            #[cfg(test)]
            Self::InjectedFault => write!(formatter, "the test seam aborted the operation"),
        }
    }
}

fn hex_identity(bytes: &[u8; 32]) -> String {
    use std::fmt::Write as _;
    let mut out = String::with_capacity(64);
    for byte in *bytes {
        let _ = write!(out, "{byte:02x}");
    }
    out
}

impl std::error::Error for SaveError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::RuntimePin(error) => Some(error),
            Self::Sqlite(error) => Some(error),
            Self::Io(error) => Some(error),
            _ => None,
        }
    }
}

impl From<SqliteError> for SaveError {
    fn from(error: SqliteError) -> Self {
        Self::Sqlite(error)
    }
}

impl From<IoError> for SaveError {
    fn from(error: IoError) -> Self {
        Self::Io(error)
    }
}

impl From<SqlitePinError> for SaveError {
    fn from(error: SqlitePinError) -> Self {
        Self::RuntimePin(error)
    }
}

/// Compute the lock-record path published beside one campaign database.
#[must_use]
pub fn lock_path(database: &Path) -> PathBuf {
    let mut name = database.as_os_str().to_os_string();
    name.push(".lock");
    PathBuf::from(name)
}

/// Exclusive task-scoped owner of one campaign database path.
#[derive(Debug)]
pub struct CampaignLock {
    path: PathBuf,
    owner_pid: u32,
    campaign_id: CampaignId,
}

impl CampaignLock {
    /// Publish the owner record and hold the campaign path for this task.
    ///
    /// A record left by a dead process is recovered only after the campaign
    /// identity check in this module's documentation agrees. The takeover runs
    /// under a short-lived `.lock.recover` claim so two recovering processes
    /// cannot delete each other's fresh record.
    ///
    /// # Errors
    ///
    /// Refuses a live owner with [`SaveError::CampaignLocked`], a malformed
    /// existing record with [`SaveError::LockRecordInvalid`], a dead owner whose
    /// database records another campaign with
    /// [`SaveError::LockRecordMismatch`], a held recovery claim with
    /// [`SaveError::LockRecoveryBusy`], or a host I/O failure.
    pub fn acquire(database: &Path, campaign_id: CampaignId) -> Result<Self, SaveError> {
        let path = lock_path(database);
        let owner_pid = std::process::id();
        for _ in 0..RECOVERY_ATTEMPTS {
            match OpenOptions::new().write(true).create_new(true).open(&path) {
                Ok(mut file) => {
                    if let Err(error) = write_owner(&mut file, owner_pid, campaign_id) {
                        let _ = fs::remove_file(&path);
                        return Err(SaveError::Io(error));
                    }
                    return Ok(Self {
                        path,
                        owner_pid,
                        campaign_id,
                    });
                }
                Err(error) if error.kind() == ErrorKind::AlreadyExists => {
                    let Some((recorded_pid, recorded_campaign)) = read_owner(&path)? else {
                        return Err(SaveError::LockRecordInvalid { path });
                    };
                    if process_is_live(recorded_pid) {
                        return Err(SaveError::CampaignLocked {
                            owner_pid: recorded_pid,
                            campaign_id: recorded_campaign,
                        });
                    }
                    let _claim = RecoveryClaim::acquire(&path)?;
                    match read_owner(&path)? {
                        Some((pid, campaign))
                            if pid == recorded_pid && campaign == recorded_campaign =>
                        {
                            verify_stale_owner(database, recorded_campaign)?;
                            if let Err(error) = fs::remove_file(&path) {
                                if error.kind() != ErrorKind::NotFound {
                                    return Err(SaveError::Io(error));
                                }
                            }
                        }
                        Some(_) => {}
                        None => return Err(SaveError::LockRecordInvalid { path }),
                    }
                }
                Err(error) => return Err(SaveError::Io(error)),
            }
        }
        match read_owner(&path)? {
            Some((owner_pid, campaign_id)) => Err(SaveError::CampaignLocked {
                owner_pid,
                campaign_id,
            }),
            None => Err(SaveError::LockRecordInvalid { path }),
        }
    }

    /// Return the process id this handle published.
    #[must_use]
    pub const fn owner_pid(&self) -> u32 {
        self.owner_pid
    }

    /// Return the campaign identity this handle published.
    #[must_use]
    pub const fn campaign_id(&self) -> &CampaignId {
        &self.campaign_id
    }

    /// Return the lock-record path this handle owns.
    #[must_use]
    pub fn path(&self) -> &Path {
        &self.path
    }
}

impl Drop for CampaignLock {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.path);
    }
}

fn write_owner(file: &mut File, owner_pid: u32, campaign_id: CampaignId) -> Result<(), IoError> {
    let mut record = [0_u8; LOCK_RECORD_BYTES];
    record[..4].copy_from_slice(&owner_pid.to_be_bytes());
    record[4..].copy_from_slice(campaign_id.canonical_bytes());
    file.write_all(&record)?;
    file.sync_all()
}

fn read_owner(path: &Path) -> Result<Option<(u32, CampaignId)>, SaveError> {
    let bytes = fs::read(path)?;
    let Ok(record) = <[u8; LOCK_RECORD_BYTES]>::try_from(bytes.as_slice()) else {
        return Ok(None);
    };
    let pid_bytes: [u8; 4] = record[..4]
        .try_into()
        .map_err(|_| SaveError::LockRecordInvalid {
            path: path.to_path_buf(),
        })?;
    let campaign_bytes: [u8; 16] =
        record[4..]
            .try_into()
            .map_err(|_| SaveError::LockRecordInvalid {
                path: path.to_path_buf(),
            })?;
    Ok(Some((
        u32::from_be_bytes(pid_bytes),
        CampaignId::from_uuid(Uuid::from_bytes(campaign_bytes)),
    )))
}

/// Bounded takeover attempts before a competing owner wins the path.
const RECOVERY_ATTEMPTS: usize = 3;

/// Hold the short-lived recovery claim that serializes stale-lock takeover.
struct RecoveryClaim {
    path: PathBuf,
}

impl RecoveryClaim {
    fn acquire(lock: &Path) -> Result<Self, SaveError> {
        let path = recovery_path(lock);
        for _ in 0..RECOVERY_ATTEMPTS {
            match OpenOptions::new().write(true).create_new(true).open(&path) {
                Ok(mut file) => {
                    if let Err(error) = file
                        .write_all(&std::process::id().to_be_bytes())
                        .and_then(|()| file.sync_all())
                    {
                        let _ = fs::remove_file(&path);
                        return Err(SaveError::Io(error));
                    }
                    return Ok(Self { path });
                }
                Err(error) if error.kind() == ErrorKind::AlreadyExists => {
                    let holder = fs::read(&path)
                        .ok()
                        .and_then(|bytes| <[u8; 4]>::try_from(bytes.as_slice()).ok())
                        .map(u32::from_be_bytes);
                    match holder {
                        Some(pid) if !process_is_live(pid) => {
                            if let Err(error) = fs::remove_file(&path) {
                                if error.kind() != ErrorKind::NotFound {
                                    return Err(SaveError::Io(error));
                                }
                            }
                        }
                        _ => {
                            return Err(SaveError::LockRecoveryBusy { path });
                        }
                    }
                }
                Err(error) => return Err(SaveError::Io(error)),
            }
        }
        Err(SaveError::LockRecoveryBusy { path })
    }
}

impl Drop for RecoveryClaim {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.path);
    }
}

fn recovery_path(lock: &Path) -> PathBuf {
    let mut name = lock.as_os_str().to_os_string();
    name.push(".recover");
    PathBuf::from(name)
}

/// Report whether a recorded owner process is still live.
///
/// Linux answers from `/proc`; other targets conservatively report the owner as
/// live so a stale record is refused rather than stolen. A recorded pid of zero
/// is never a live owner.
fn process_is_live(pid: u32) -> bool {
    if pid == 0 {
        return false;
    }
    #[cfg(target_os = "linux")]
    {
        Path::new(&format!("/proc/{pid}")).exists()
    }
    #[cfg(not(target_os = "linux"))]
    {
        let _ = pid;
        true
    }
}

/// Refuse to reclaim a dead owner's record when the database names another
/// campaign. A database without a committed manifest cannot disagree yet.
fn verify_stale_owner(database: &Path, recorded: CampaignId) -> Result<(), SaveError> {
    match manifest_campaign_id(database)? {
        Some(manifest) if manifest != recorded => {
            Err(SaveError::LockRecordMismatch { recorded, manifest })
        }
        _ => Ok(()),
    }
}

/// Read the committed campaign identity beside a database, if it has one.
fn manifest_campaign_id(database: &Path) -> Result<Option<CampaignId>, SaveError> {
    if !database.exists() {
        return Ok(None);
    }
    let connection = Connection::open_with_flags(
        database,
        OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_NO_MUTEX,
    )?;
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
    let identity =
        <[u8; 16]>::try_from(bytes.as_slice()).map_err(|_| SaveError::CorruptManifest {
            reason: "the committed campaign identity is not sixteen bytes",
        })?;
    Ok(Some(CampaignId::from_uuid(Uuid::from_bytes(identity))))
}
