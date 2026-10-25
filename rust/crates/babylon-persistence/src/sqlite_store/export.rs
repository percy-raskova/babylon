//! Online backup export, read-only verification and atomic publication.
//!
//! Export uses `SQLite`'s online backup mechanism into a reserved temporary file,
//! then reopens that file read-only and checks `integrity_check`, the exact
//! nine-table schema, the committed manifest identity, the current restart root
//! (manifest, chunk links and chunk bytes), and every stored payload hash. Only a
//! verified copy is linked onto a destination name that is still free, after the
//! file is synced and before the parent directory is synced, so a published
//! export is crash-durable and an existing destination is never overwritten. A
//! failed attempt removes its temporary file and leaves the source untouched.

use std::fs;
use std::fs::File;
use std::fs::OpenOptions;
use std::io::Error;
use std::io::ErrorKind;
use std::path::Path;
use std::path::PathBuf;
use std::time::Duration;
use std::time::SystemTime;
use std::time::UNIX_EPOCH;

use rusqlite::backup::Backup;
use rusqlite::params;
use rusqlite::Connection;
use rusqlite::OpenFlags;

use babylon_kernel::content_digest;

use crate::identity::CampaignId;
use crate::sqlite_store::chunks::JournalKind;
use crate::sqlite_store::chunks::SubjectKind;
use crate::sqlite_store::codec;
use crate::sqlite_store::codec::PayloadBudget;
use crate::sqlite_store::codec::PayloadCodec;
use crate::sqlite_store::codec::StoredPayload;
use crate::sqlite_store::lock::SaveError;
use crate::sqlite_store::owner;
use crate::sqlite_store::owner::JournalInput;
use crate::sqlite_store::owner::KnowledgeInput;
use crate::sqlite_store::owner::MAX_KNOWLEDGE_PAYLOAD_BYTES;
use crate::sqlite_store::schema;
use crate::sqlite_store::schema::SnapshotRole;

/// Verified result of one online export.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct VerifiedExport {
    /// Bytes in the published destination file.
    pub destination_bytes: u64,
    /// Pages in the published destination database.
    pub page_count: u64,
    /// Whether the destination passed integrity, schema and hash checks.
    pub integrity_verified: bool,
    /// Committed period the export preserves.
    pub current_period: u64,
    /// Committed world identity the export preserves.
    pub world_hash: [u8; 32],
    /// Journal tail identity the export preserves.
    pub journal_tail_hash: [u8; 32],
    /// Wall time spent exporting and verifying.
    pub elapsed_ns: u64,
}

/// Exact committed identity an export must preserve.
pub(super) struct ExportIdentity {
    pub(super) campaign_id: CampaignId,
    pub(super) build_hash: [u8; 32],
    pub(super) content_hash: [u8; 32],
    pub(super) current_snapshot_id: i64,
    pub(super) period: u64,
    pub(super) world_hash: [u8; 32],
    pub(super) state_hash: [u8; 32],
    pub(super) journal_tail_seq: u64,
    pub(super) journal_tail_hash: [u8; 32],
    pub(super) knowledge_tail_seq: u64,
    pub(super) knowledge_tail_hash: [u8; 32],
}

pub(super) struct ExportEvidence {
    pub(super) page_count: u64,
}

/// Reserve one unique temporary path beside the destination.
pub(super) fn temporary_path(destination: &Path) -> Result<PathBuf, SaveError> {
    if destination.exists() {
        return Err(SaveError::ExportDestinationExists);
    }
    let directory = destination.parent().unwrap_or_else(|| Path::new("."));
    let name = destination
        .file_name()
        .and_then(|value| value.to_str())
        .unwrap_or("campaign");
    for attempt in 0..8_u32 {
        let stamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_or(0, |duration| duration.as_nanos());
        let candidate = directory.join(format!(
            ".{name}.export-{}-{stamp}-{attempt}",
            std::process::id()
        ));
        match OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&candidate)
        {
            Ok(_) => return Ok(candidate),
            Err(error) if error.kind() == ErrorKind::AlreadyExists => {}
            Err(error) => return Err(SaveError::Io(error)),
        }
    }
    Err(SaveError::Io(Error::new(
        ErrorKind::AlreadyExists,
        "could not reserve a unique export path",
    )))
}

/// Copy the committed source database into the reserved target path.
pub(super) fn backup_to(source: &Connection, target: &Path) -> Result<(), SaveError> {
    let mut destination = Connection::open(target)?;
    {
        let backup = Backup::new(source, &mut destination)?;
        backup.run_to_completion(64, Duration::ZERO, None)?;
    }
    // The copy inherits the source's write-ahead header, so it would carry
    // `-wal`/`-shm` sidecars beside it. Switch it back to rollback mode: `SQLite`
    // then checkpoints and removes both sidecars, leaving one standalone file
    // that a single link can publish.
    let mode: String =
        destination.query_row("PRAGMA journal_mode = DELETE", [], |row| row.get(0))?;
    if !mode.eq_ignore_ascii_case("delete") {
        return Err(SaveError::PragmaMismatch {
            pragma: "journal_mode",
            expected: "delete",
            actual: mode,
        });
    }
    Ok(())
}

/// Verify one exported database read-only against the committed identity.
pub(super) fn verify_export(
    path: &Path,
    expected: &ExportIdentity,
) -> Result<ExportEvidence, SaveError> {
    let connection = Connection::open_with_flags(
        path,
        OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_NO_MUTEX,
    )?;
    let integrity: String = connection.query_row("PRAGMA integrity_check", [], |row| row.get(0))?;
    if integrity != "ok" {
        return Err(SaveError::ExportIdentityMismatch);
    }
    schema::verify_installed_schema(&connection)?;
    let manifest = owner::read_manifest(&connection)?;
    if manifest.campaign_id != expected.campaign_id
        || manifest.build_hash != expected.build_hash
        || manifest.content_hash != expected.content_hash
        || manifest.current_snapshot_id != expected.current_snapshot_id
        || manifest.journal_tail_seq != expected.journal_tail_seq
        || manifest.journal_tail_hash != expected.journal_tail_hash
        || manifest.knowledge_tail_seq != expected.knowledge_tail_seq
        || manifest.knowledge_tail_hash != expected.knowledge_tail_hash
    {
        return Err(SaveError::ExportIdentityMismatch);
    }
    let snapshot = owner::read_snapshot(&connection, expected.current_snapshot_id)?;
    if snapshot.role != SnapshotRole::Current && snapshot.role != SnapshotRole::Opening {
        return Err(SaveError::ExportIdentityMismatch);
    }
    if snapshot.period != expected.period
        || snapshot.world_hash != expected.world_hash
        || snapshot.state_hash != expected.state_hash
    {
        return Err(SaveError::ExportIdentityMismatch);
    }
    // Re-run the restart-root load the opener performs: the snapshot manifest,
    // its chunk links and every reached chunk byte must agree, so the verifier
    // proves the export opens a root rather than merely parses.
    let (root, _chunk_reads) = owner::load_current_root(&connection, &snapshot)?;
    if root.period != expected.period
        || root.world_hash != expected.world_hash
        || root.state_hash != expected.state_hash
    {
        return Err(SaveError::ExportIdentityMismatch);
    }
    verify_all_payloads(&connection)?;
    let page_count: i64 = connection.query_row("PRAGMA page_count", [], |row| row.get(0))?;
    Ok(ExportEvidence {
        page_count: u64::try_from(page_count).map_err(|_| SaveError::ExportIdentityMismatch)?,
    })
}

/// Publish the verified temporary database at its destination.
///
/// The verified file is synced to stable storage first. Publication is a hard
/// link, which creates the destination name only when it is still free, so a
/// destination that appears after [`temporary_path`]'s check is refused rather
/// than overwritten. The parent directory is synced afterwards so the new
/// entry survives a crash, and the temporary name is unlinked last.
pub(super) fn publish(temporary: &Path, destination: &Path) -> Result<u64, SaveError> {
    sync_file(temporary)?;
    match fs::hard_link(temporary, destination) {
        Ok(()) => {}
        Err(error) if error.kind() == ErrorKind::AlreadyExists => {
            return Err(SaveError::ExportDestinationExists);
        }
        Err(error) => return Err(SaveError::Io(error)),
    }
    remove_if_present(temporary);
    sync_directory(destination)?;
    Ok(fs::metadata(destination)?.len())
}

/// Flush one file's bytes and metadata to stable storage.
fn sync_file(path: &Path) -> Result<(), SaveError> {
    File::open(path)?.sync_all()?;
    Ok(())
}

/// Flush one published directory entry to stable storage.
fn sync_directory(path: &Path) -> Result<(), SaveError> {
    let directory = path.parent().unwrap_or_else(|| Path::new("."));
    File::open(directory)?.sync_all()?;
    Ok(())
}

/// Remove a temporary export database and its `-wal`/`-shm` sidecars.
pub(super) fn remove_if_present(path: &Path) {
    remove_one(path);
    for suffix in ["-wal", "-shm"] {
        let mut sidecar = path.as_os_str().to_os_string();
        sidecar.push(suffix);
        remove_one(&PathBuf::from(sidecar));
    }
}

fn remove_one(path: &Path) {
    if let Err(error) = fs::remove_file(path) {
        debug_assert_eq!(error.kind(), ErrorKind::NotFound);
    }
}

fn verify_all_payloads(connection: &Connection) -> Result<(), SaveError> {
    verify_bulk_table(connection, "content_entry", PayloadBudget::ContentEntry)?;
    verify_bulk_table(connection, "state_chunk", PayloadBudget::StateChunk)?;
    verify_bulk_table(connection, "recent_detail", PayloadBudget::RecentDetail)?;
    verify_journal(connection)?;
    verify_knowledge(connection)?;
    verify_service_state(connection)?;
    Ok(())
}

fn verify_bulk_table(
    connection: &Connection,
    table: &str,
    budget: PayloadBudget,
) -> Result<(), SaveError> {
    let mut statement = connection.prepare(&format!(
        "SELECT codec, raw_len, raw_hash, payload FROM {table}"
    ))?;
    let mut rows = statement.query([])?;
    while let Some(row) = rows.next()? {
        let codec_code: i64 = row.get(0)?;
        let raw_len: i64 = row.get(1)?;
        let raw_hash: Vec<u8> = row.get(2)?;
        let payload: Vec<u8> = row.get(3)?;
        decode_stored(budget, codec_code, raw_len, &raw_hash, &payload)?;
    }
    Ok(())
}

fn decode_stored(
    budget: PayloadBudget,
    codec_code: i64,
    raw_len: i64,
    raw_hash: &[u8],
    payload: &[u8],
) -> Result<Vec<u8>, SaveError> {
    let stored = StoredPayload {
        codec: PayloadCodec::from_code(codec_code)?,
        raw_len: u32::try_from(raw_len).map_err(|_| SaveError::CorruptPayload {
            table: budget.table(),
            reason: "the stored decoded length is out of range",
        })?,
        raw_hash: <[u8; 32]>::try_from(raw_hash).map_err(|_| SaveError::CorruptPayload {
            table: budget.table(),
            reason: "the stored hash is not 32 bytes",
        })?,
        payload,
    };
    codec::decode_chunk_payload(budget, &stored)
}

fn verify_journal(connection: &Connection) -> Result<(), SaveError> {
    let mut statement = connection.prepare(
        "SELECT journal_seq, kind, period, actor_id, subject_kind, subject_id, nonce,
                record_key, codec, raw_len, raw_hash, payload, previous_hash, entry_hash
         FROM permanent_journal ORDER BY journal_seq",
    )?;
    let mut rows = statement.query([])?;
    while let Some(row) = rows.next()? {
        let journal_seq = to_u64(row.get(0)?, "permanent_journal.journal_seq")?;
        let kind = JournalKind::from_code(row.get(1)?).ok_or(SaveError::CorruptPayload {
            table: "permanent_journal",
            reason: "the stored journal kind is outside the closed registry",
        })?;
        let period = to_u64(row.get(2)?, "permanent_journal.period")?;
        let actor_id = optional_width::<8>(row.get(3)?, "permanent_journal.actor_id")?;
        let subject_kind: Option<i64> = row.get(4)?;
        let subject_id: Option<Vec<u8>> = row.get(5)?;
        let subject = match (subject_kind, subject_id) {
            (Some(code), Some(id)) => {
                let kind = SubjectKind::from_code(code).ok_or(SaveError::CorruptPayload {
                    table: "permanent_journal",
                    reason: "the stored subject kind is outside the closed registry",
                })?;
                Some((kind, id))
            }
            (None, None) => None,
            _ => {
                return Err(SaveError::CorruptPayload {
                    table: "permanent_journal",
                    reason: "the stored subject pair is unpaired",
                });
            }
        };
        let nonce = optional_width::<16>(row.get(6)?, "permanent_journal.nonce")?;
        let record_key: Option<Vec<u8>> = row.get(7)?;
        let codec_code: i64 = row.get(8)?;
        let raw_len: i64 = row.get(9)?;
        let raw_hash: Vec<u8> = row.get(10)?;
        let payload: Vec<u8> = row.get(11)?;
        let decoded = decode_stored(
            PayloadBudget::PermanentJournal,
            codec_code,
            raw_len,
            &raw_hash,
            &payload,
        )?;
        let entry_hash = owner::journal_entry_hash(&JournalInput {
            journal_seq,
            kind,
            period,
            actor_id,
            subject: subject.as_ref().map(|(kind, id)| (*kind, id.as_slice())),
            nonce,
            record_key: record_key.as_deref(),
            raw_len: u32::try_from(raw_len).map_err(|_| SaveError::CorruptPayload {
                table: "permanent_journal",
                reason: "the stored decoded length is out of range",
            })?,
            raw_hash: content_digest::sha256_of(&decoded),
            previous_hash: hash32("permanent_journal", &row.get::<_, Vec<u8>>(12)?)?,
        })?;
        if entry_hash != hash32("permanent_journal", &row.get::<_, Vec<u8>>(13)?)? {
            return Err(SaveError::CorruptPayload {
                table: "permanent_journal",
                reason: "a stored journal entry does not match its entry hash",
            });
        }
    }
    Ok(())
}

fn verify_knowledge(connection: &Connection) -> Result<(), SaveError> {
    let mut statement = connection.prepare(
        "SELECT knowledge_seq, player_id, subject_kind, subject_id, grant_key,
                acquired_period, source_journal_seq, payload, previous_hash, entry_hash
         FROM knowledge_grant ORDER BY knowledge_seq",
    )?;
    let mut rows = statement.query([])?;
    while let Some(row) = rows.next()? {
        let knowledge_seq = to_u64(row.get(0)?, "knowledge_grant.knowledge_seq")?;
        let player_bytes: Vec<u8> = row.get(1)?;
        let player_id = required_width::<8>(&player_bytes, "knowledge_grant.player_id")?;
        let subject_kind =
            SubjectKind::from_code(row.get(2)?).ok_or(SaveError::CorruptPayload {
                table: "knowledge_grant",
                reason: "the stored subject kind is outside the closed registry",
            })?;
        let subject_id: Vec<u8> = row.get(3)?;
        let grant_key: i64 = row.get(4)?;
        let acquired_period = to_u64(row.get(5)?, "knowledge_grant.acquired_period")?;
        let source_journal_seq = to_u64(row.get(6)?, "knowledge_grant.source_journal_seq")?;
        let payload: Vec<u8> = row.get(7)?;
        if payload.len() > MAX_KNOWLEDGE_PAYLOAD_BYTES {
            return Err(SaveError::PayloadTooLarge {
                table: "knowledge_grant",
                limit: MAX_KNOWLEDGE_PAYLOAD_BYTES,
                actual: payload.len(),
            });
        }
        let entry_hash = owner::knowledge_entry_hash(&KnowledgeInput {
            knowledge_seq,
            player_id,
            subject_kind,
            subject_id: &subject_id,
            grant_key,
            acquired_period,
            source_journal_seq,
            raw_len: u32::try_from(payload.len()).map_err(|_| SaveError::CorruptPayload {
                table: "knowledge_grant",
                reason: "the stored payload length is out of range",
            })?,
            raw_hash: content_digest::sha256_of(&payload),
            previous_hash: hash32("knowledge_grant", &row.get::<_, Vec<u8>>(8)?)?,
        })?;
        if entry_hash != hash32("knowledge_grant", &row.get::<_, Vec<u8>>(9)?)? {
            return Err(SaveError::CorruptPayload {
                table: "knowledge_grant",
                reason: "a stored grant does not match its entry hash",
            });
        }
    }
    Ok(())
}

fn verify_service_state(connection: &Connection) -> Result<(), SaveError> {
    use rusqlite::OptionalExtension as _;
    let row = connection
        .query_row(
            "SELECT codec, raw_len, raw_hash, payload FROM service_state WHERE id = 1",
            params![],
            |row| {
                Ok((
                    row.get::<_, i64>(0)?,
                    row.get::<_, i64>(1)?,
                    row.get::<_, Vec<u8>>(2)?,
                    row.get::<_, Vec<u8>>(3)?,
                ))
            },
        )
        .optional()?;
    if let Some((codec_code, raw_len, raw_hash, payload)) = row {
        decode_stored(
            PayloadBudget::ServiceState,
            codec_code,
            raw_len,
            &raw_hash,
            &payload,
        )?;
    }
    Ok(())
}

fn optional_width<const WIDTH: usize>(
    value: Option<Vec<u8>>,
    field: &'static str,
) -> Result<Option<[u8; WIDTH]>, SaveError> {
    match value {
        Some(bytes) => required_width::<WIDTH>(&bytes, field).map(Some),
        None => Ok(None),
    }
}

fn required_width<const WIDTH: usize>(
    bytes: &[u8],
    field: &'static str,
) -> Result<[u8; WIDTH], SaveError> {
    <[u8; WIDTH]>::try_from(bytes).map_err(|_| SaveError::CorruptPayload {
        table: field,
        reason: "the stored identity is not its published width",
    })
}

fn hash32(table: &'static str, bytes: &[u8]) -> Result<[u8; 32], SaveError> {
    <[u8; 32]>::try_from(bytes).map_err(|_| SaveError::CorruptPayload {
        table,
        reason: "the stored hash is not 32 bytes",
    })
}

fn to_u64(value: i64, field: &'static str) -> Result<u64, SaveError> {
    u64::try_from(value).map_err(|_| SaveError::CorruptPayload {
        table: field,
        reason: "the stored integer is negative",
    })
}
