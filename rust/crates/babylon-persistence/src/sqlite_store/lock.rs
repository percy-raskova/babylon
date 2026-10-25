//! Task-scoped single-writer campaign lock and the store error surface.
//!
//! The owner writes a twenty-byte record beside the campaign database: the
//! owning process id in canonical big-endian order followed by the sixteen
//! canonical campaign identity bytes. A second writer refuses with that owner
//! identity instead of silently opening another runtime. The record is removed
//! when the owning handle drops. A record left by a crashed owner is reported,
//! never silently stolen.
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

use rusqlite::Error as SqliteError;
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
}

impl std::fmt::Display for SaveError {
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
            Self::InvalidField {
                table,
                field,
                reason,
            } => write!(formatter, "{table}.{field} is refused: {reason}"),
            Self::Arithmetic { field } => {
                write!(formatter, "{field} did not fit its checked integer range")
            }
        }
    }
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
    /// # Errors
    ///
    /// Refuses an existing owner record with
    /// [`SaveError::CampaignLocked`], a malformed existing record with
    /// [`SaveError::LockRecordInvalid`], or a host I/O failure.
    pub fn acquire(database: &Path, campaign_id: CampaignId) -> Result<Self, SaveError> {
        let path = lock_path(database);
        let owner_pid = std::process::id();
        match OpenOptions::new().write(true).create_new(true).open(&path) {
            Ok(mut file) => {
                if let Err(error) = write_owner(&mut file, owner_pid, campaign_id) {
                    let _ = fs::remove_file(&path);
                    return Err(SaveError::Io(error));
                }
                Ok(Self {
                    path,
                    owner_pid,
                    campaign_id,
                })
            }
            Err(error) if error.kind() == ErrorKind::AlreadyExists => match read_owner(&path)? {
                Some((owner_pid, campaign_id)) => Err(SaveError::CampaignLocked {
                    owner_pid,
                    campaign_id,
                }),
                None => Err(SaveError::LockRecordInvalid { path }),
            },
            Err(error) => Err(SaveError::Io(error)),
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
