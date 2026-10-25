//! Isolated historical replay and explicit recovery into a new save.
//!
//! Replay selects the newest retained checkpoint at or before the target period,
//! authenticates every chunk it reaches, then validates the permanent journal
//! chain from that checkpoint through the target period's compact summary. The
//! reconstruction reports the exact committed world/state identity, the governed
//! choice receipts in the span, and the knowledge prefix that existed at the
//! target. It runs against a private copy taken with `SQLite`'s online backup, so
//! the live save is never mutated and no reconstruction can publish knowledge.
//!
//! Recovery is replay's sibling. `recover_to_new_save` verifies a damaged source
//! at a committed boundary, drops only unreachable cold layers (exhaustive detail
//! rows and historical checkpoints that no longer authenticate), publishes a
//! clean independent file and preserves the original as evidence. Damage to the
//! current root, the permanent journal or earned knowledge refuses rather than
//! fabricating a shorter campaign.
//!
//! The store verifies the durable replay *inputs and identities*: captured
//! content, checkpoint state bytes, the exact journal chain and the knowledge
//! prefix. Re-adjudicating periods under the exact build is the qualification
//! harness's job; this module never claims to have re-executed the economy.

use std::fmt::Formatter;
use std::fmt::Result as FmtResult;
use std::fs::OpenOptions;
use std::io::ErrorKind;
use std::path::Path;
use std::path::PathBuf;
use std::sync::atomic::AtomicBool;
use std::sync::atomic::Ordering;
use std::time::Instant;
use std::time::SystemTime;
use std::time::UNIX_EPOCH;

use rusqlite::Connection;
use rusqlite::OpenFlags;
use rusqlite::Row;

use babylon_kernel::content_digest;

use crate::sqlite_store::chunks::DetailFamily;
use crate::sqlite_store::chunks::JournalKind;
use crate::sqlite_store::chunks::SubjectKind;
use crate::sqlite_store::codec;
use crate::sqlite_store::codec::PayloadBudget;
use crate::sqlite_store::codec::PayloadCodec;
use crate::sqlite_store::codec::StoredPayload;
use crate::sqlite_store::export;
use crate::sqlite_store::export::ExportIdentity;
use crate::sqlite_store::owner;
use crate::sqlite_store::owner::BuildIdentity;
use crate::sqlite_store::owner::CurrentRoot;
use crate::sqlite_store::owner::JournalInput;
use crate::sqlite_store::owner::KnowledgeInput;
use crate::sqlite_store::owner::SnapshotHeader;
use crate::sqlite_store::owner::MAX_KNOWLEDGE_PAYLOAD_BYTES;
use crate::sqlite_store::retention;
use crate::sqlite_store::retention::PeriodSummary;
use crate::sqlite_store::schema;
use crate::sqlite_store::SaveError;
use crate::sqlite_store::SnapshotRole;

/// One authenticated exhaustive-detail row inside the retained window.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RecentDetailRow {
    /// Completed period the row belongs to.
    pub period: u64,
    /// Closed receipt or event family.
    pub family: DetailFamily,
    /// Ordered fragment inside the family.
    pub ordinal: u32,
    /// Exact canonical payload bytes.
    pub payload: Vec<u8>,
}

/// One governed choice receipt reconstructed from the permanent journal.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReplayedChoiceReceipt {
    /// Permanent journal sequence of the choice record.
    pub journal_seq: u64,
    /// Completed period the choice belongs to.
    pub period: u64,
    /// Typed subject the choice concerned.
    pub subject: Option<(SubjectKind, Vec<u8>)>,
    /// Exact canonical choice payload.
    pub payload: Vec<u8>,
    /// Entry hash binding the record into the journal chain.
    pub entry_hash: [u8; 32],
}

/// One knowledge grant visible in a reconstructing period's disclosure prefix.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReplayedGrant {
    /// Position in the knowledge chain.
    pub knowledge_seq: u64,
    /// Player who earned the fact.
    pub player_id: [u8; 8],
    /// Closed subject kind.
    pub subject_kind: SubjectKind,
    /// Exact subject identity bytes.
    pub subject_id: Vec<u8>,
    /// Caller-assigned grant key inside the subject.
    pub grant_key: i64,
    /// Period the fact was actually acquired.
    pub acquired_period: u64,
    /// Exact canonical fact payload.
    pub payload: Vec<u8>,
}

/// Verified reconstruction of one historical period's durable replay inputs.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedReplayReconstruction {
    /// Requested period.
    pub target_period: u64,
    /// Period of the checkpoint the reconstruction started from; zero is opening.
    pub source_checkpoint_period: u64,
    /// Whether the checkpoint was the retained opening.
    pub started_from_opening: bool,
    /// Committed canonical world identity of the target period.
    pub world_hash: [u8; 32],
    /// Committed canonical state identity of the target period.
    pub state_hash: [u8; 32],
    /// Permanent journal tail sequence at the target period.
    pub journal_tail_seq: u64,
    /// Permanent journal tail hash at the target period.
    pub journal_tail_hash: [u8; 32],
    /// Knowledge tail sequence at the target period.
    pub knowledge_tail_seq: u64,
    /// Knowledge tail hash at the target period.
    pub knowledge_tail_hash: [u8; 32],
    /// Completed periods the journal chain re-verified after the checkpoint.
    pub periods_verified: u64,
    /// Verified checkpoint chunk count.
    pub checkpoint_chunks: u64,
    /// Permanent journal records the chain walk authenticated.
    pub records_verified: u64,
    /// Governed choice receipts inside the reconstructed span.
    pub choice_receipts: Vec<ReplayedChoiceReceipt>,
    /// Facts disclosed at the target period only.
    pub knowledge_grants: Vec<ReplayedGrant>,
    /// Build identity the reconstruction authenticated.
    pub build_hash: [u8; 32],
    /// Captured content identity the reconstruction authenticated.
    pub content_hash: [u8; 32],
    /// Whether the isolated copy passed the save verifier.
    pub integrity_verified: bool,
    /// Wall time spent reconstructing and verifying.
    pub elapsed_ns: u64,
}

/// Verified result of one explicit recovery into a new save.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct VerifiedRecovery {
    /// Bytes in the published destination file.
    pub destination_bytes: u64,
    /// Committed period the recovered save preserves.
    pub recovered_period: u64,
    /// Committed world identity the recovered save preserves.
    pub world_hash: [u8; 32],
    /// Journal tail identity the recovered save preserves.
    pub journal_tail_hash: [u8; 32],
    /// Cold exhaustive-detail rows dropped as unauthenticated.
    pub cold_rows_dropped: u32,
    /// Cold historical checkpoints dropped as unauthenticated.
    pub checkpoints_dropped: u32,
    /// Whether the destination passed integrity, schema and hash checks.
    pub integrity_verified: bool,
    /// Wall time spent recovering and verifying.
    pub elapsed_ns: u64,
}

/// A checked replay, detail-read or recovery refusal.
#[derive(Debug)]
pub enum ReplayError {
    /// The store boundary refused.
    Save(SaveError),
    /// The target is later than the committed present.
    FuturePeriod {
        /// Committed period.
        current: u64,
        /// Requested period.
        requested: u64,
    },
    /// The caller cancelled the reconstruction.
    Cancelled,
    /// No retained checkpoint and no opening can start the request.
    NoCheckpoint {
        /// Requested period.
        target_period: u64,
    },
    /// A period in the span has no compact permanent summary.
    MissingPeriodSummary {
        /// Period whose summary is absent.
        period: u64,
    },
    /// A stored record disagrees with the chain it claims.
    DamagedRange {
        /// Retained layer that failed authentication.
        layer: &'static str,
        /// Exact diagnosis.
        reason: &'static str,
    },
}

impl std::fmt::Display for ReplayError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> FmtResult {
        match self {
            Self::Save(error) => write!(formatter, "the store refused the replay: {error}"),
            Self::FuturePeriod { current, requested } => write!(
                formatter,
                "period {requested} is after the committed period {current}"
            ),
            Self::Cancelled => formatter.write_str("the replay was cancelled"),
            Self::NoCheckpoint { target_period } => {
                write!(formatter, "no retained root starts period {target_period}")
            }
            Self::MissingPeriodSummary { period } => {
                write!(formatter, "period {period} has no compact summary")
            }
            Self::DamagedRange { layer, reason } => {
                write!(formatter, "the {layer} range is damaged: {reason}")
            }
        }
    }
}

impl std::error::Error for ReplayError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Save(error) => Some(error),
            _ => None,
        }
    }
}

impl From<SaveError> for ReplayError {
    fn from(error: SaveError) -> Self {
        Self::Save(error)
    }
}

/// Reconstruct one period from a private copy of the live campaign.
pub(super) fn reconstruct(
    connection: &Connection,
    path: &Path,
    build_hash: [u8; 32],
    content_hash: [u8; 32],
    current_period: u64,
    target_period: u64,
    cancel: &AtomicBool,
) -> Result<VerifiedReplayReconstruction, ReplayError> {
    let started = Instant::now();
    if target_period > current_period {
        return Err(ReplayError::FuturePeriod {
            current: current_period,
            requested: target_period,
        });
    }
    ensure_running(cancel)?;
    let isolated = isolated_copy(connection, path)?;
    let result = reconstruct_from_copy(&isolated, build_hash, content_hash, target_period, cancel);
    export::remove_if_present(&isolated);
    let mut reconstruction = result?;
    reconstruction.elapsed_ns = elapsed_ns(started);
    Ok(reconstruction)
}

fn reconstruct_from_copy(
    isolated: &Path,
    build_hash: [u8; 32],
    content_hash: [u8; 32],
    target_period: u64,
    cancel: &AtomicBool,
) -> Result<VerifiedReplayReconstruction, ReplayError> {
    let connection = Connection::open_with_flags(
        isolated,
        OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_NO_MUTEX,
    )
    .map_err(SaveError::from)?;
    schema::verify_installed_schema(&connection)?;
    let integrity: String = connection
        .query_row("PRAGMA integrity_check", [], |row| row.get(0))
        .map_err(SaveError::from)?;
    if integrity != "ok" {
        return Err(ReplayError::DamagedRange {
            layer: "save",
            reason: "the isolated copy failed its integrity check",
        });
    }
    let checkpoint = select_checkpoint(&connection, target_period)?;
    let (root, checkpoint_chunks) = owner::load_current_root(&connection, &checkpoint)?;
    let mut reconstruction = VerifiedReplayReconstruction {
        target_period,
        source_checkpoint_period: root.period,
        started_from_opening: checkpoint.role == SnapshotRole::Opening,
        world_hash: root.world_hash,
        state_hash: root.state_hash,
        journal_tail_seq: root.journal_tail_seq,
        journal_tail_hash: root.journal_tail_hash,
        knowledge_tail_seq: root.knowledge_tail_seq,
        knowledge_tail_hash: root.knowledge_tail_hash,
        periods_verified: 0,
        checkpoint_chunks,
        records_verified: 0,
        choice_receipts: Vec::new(),
        knowledge_grants: Vec::new(),
        build_hash,
        content_hash,
        integrity_verified: true,
        elapsed_ns: 0,
    };
    if root.period < target_period {
        replay_span(
            &connection,
            &root,
            target_period,
            cancel,
            &mut reconstruction,
        )?;
    }
    reconstruction.knowledge_grants = visible_grants(
        &connection,
        target_period,
        reconstruction.knowledge_tail_seq,
        reconstruction.journal_tail_seq,
        cancel,
    )?;
    Ok(reconstruction)
}

/// Walk the permanent journal from the checkpoint to the target summary.
fn replay_span(
    connection: &Connection,
    root: &CurrentRoot,
    target_period: u64,
    cancel: &AtomicBool,
    reconstruction: &mut VerifiedReplayReconstruction,
) -> Result<(), ReplayError> {
    let checkpoint_seq = integer(root.journal_tail_seq, "checkpoint journal sequence")?;
    let target = integer(target_period, "target period")?;
    let mut statement = connection
        .prepare(
            "SELECT journal_seq, kind, period, actor_id, subject_kind, subject_id, nonce,
                    record_key, codec, raw_len, raw_hash, payload, previous_hash, entry_hash
             FROM permanent_journal
             WHERE journal_seq > ?1 AND period <= ?2
             ORDER BY journal_seq",
        )
        .map_err(SaveError::from)?;
    let mut rows = statement
        .query(rusqlite::params![checkpoint_seq, target])
        .map_err(SaveError::from)?;
    let mut expected_hash = root.journal_tail_hash;
    let mut expected_period = root.period.checked_add(1).ok_or(SaveError::Arithmetic {
        field: "replay period",
    })?;
    let mut summaries: Vec<(u64, [u8; 32], PeriodSummary)> = Vec::new();
    while let Some(row) = rows.next().map_err(SaveError::from)? {
        ensure_running(cancel)?;
        let record = decode_journal_row(row)?;
        if record.previous_hash != expected_hash {
            return Err(ReplayError::DamagedRange {
                layer: "permanent journal",
                reason: "a record does not extend the previous entry hash",
            });
        }
        if record.period < expected_period {
            return Err(ReplayError::DamagedRange {
                layer: "permanent journal",
                reason: "a later record belongs to an earlier period",
            });
        }
        expected_hash = record.entry_hash;
        match record.kind {
            JournalKind::PeriodSummary => {
                let summary = retention::decode_period_summary(&record.payload)?;
                check_summary(&record, &summary)?;
                if summary.period != expected_period {
                    return Err(ReplayError::DamagedRange {
                        layer: "permanent journal",
                        reason: "a period summary skips a completed period",
                    });
                }
                expected_period = expected_period
                    .checked_add(1)
                    .ok_or(SaveError::Arithmetic {
                        field: "replay summary period",
                    })?;
                summaries.push((record.journal_seq, record.entry_hash, summary));
            }
            JournalKind::GovernedChoice => {
                reconstruction.choice_receipts.push(ReplayedChoiceReceipt {
                    journal_seq: record.journal_seq,
                    period: record.period,
                    subject: record.subject,
                    payload: record.payload,
                    entry_hash: record.entry_hash,
                });
            }
            _ => {}
        }
        reconstruction.records_verified = reconstruction.records_verified.saturating_add(1);
    }
    let Some((tail_seq, tail_hash, summary)) = summaries.last().copied() else {
        return Err(ReplayError::MissingPeriodSummary {
            period: root.period.saturating_add(1),
        });
    };
    if summary.period != target_period {
        return Err(ReplayError::MissingPeriodSummary {
            period: target_period,
        });
    }
    reconstruction.periods_verified =
        u64::try_from(summaries.len()).map_err(|_| SaveError::Arithmetic {
            field: "verified period count",
        })?;
    reconstruction.world_hash = summary.world_hash;
    reconstruction.state_hash = summary.state_hash;
    reconstruction.journal_tail_seq = tail_seq;
    reconstruction.journal_tail_hash = tail_hash;
    reconstruction.knowledge_tail_seq = summary.knowledge_tail_seq;
    reconstruction.knowledge_tail_hash = summary.knowledge_tail_hash;
    Ok(())
}

fn check_summary(record: &JournalRow, summary: &PeriodSummary) -> Result<(), ReplayError> {
    let prior_matches = summary
        .prior_journal_seq
        .checked_add(1)
        .is_some_and(|next| next == record.journal_seq)
        && summary.prior_journal_hash == record.previous_hash;
    if summary.period != record.period || !prior_matches {
        return Err(ReplayError::DamagedRange {
            layer: "permanent journal",
            reason: "a period summary disagrees with its own journal record",
        });
    }
    Ok(())
}

/// Return every knowledge grant visible in one reconstructing period.
fn visible_grants(
    connection: &Connection,
    target_period: u64,
    knowledge_tail_seq: u64,
    journal_tail_seq: u64,
    cancel: &AtomicBool,
) -> Result<Vec<ReplayedGrant>, ReplayError> {
    let limit = integer_sql(knowledge_tail_seq, "knowledge tail sequence")?;
    let mut statement = connection
        .prepare(
            "SELECT knowledge_seq, player_id, subject_kind, subject_id, grant_key,
                    acquired_period, source_journal_seq, payload, previous_hash, entry_hash
             FROM knowledge_grant WHERE knowledge_seq <= ?1 ORDER BY knowledge_seq",
        )
        .map_err(SaveError::from)?;
    let mut rows = statement.query([limit]).map_err(SaveError::from)?;
    let mut grants = Vec::new();
    let mut expected_hash = [0_u8; 32];
    let mut expected_seq = 1_u64;
    while let Some(row) = rows.next().map_err(SaveError::from)? {
        ensure_running(cancel)?;
        let grant = decode_grant_row(row)?;
        if grant.knowledge_seq != expected_seq || grant.previous_hash != expected_hash {
            return Err(ReplayError::DamagedRange {
                layer: "knowledge grant",
                reason: "the knowledge chain skips a position or link",
            });
        }
        if grant.acquired_period <= target_period && grant.source_journal_seq <= journal_tail_seq {
            grants.push(ReplayedGrant {
                knowledge_seq: grant.knowledge_seq,
                player_id: grant.player_id,
                subject_kind: grant.subject_kind,
                subject_id: grant.subject_id,
                grant_key: grant.grant_key,
                acquired_period: grant.acquired_period,
                payload: grant.payload,
            });
        }
        expected_hash = grant.entry_hash;
        expected_seq = expected_seq.checked_add(1).ok_or(SaveError::Arithmetic {
            field: "knowledge sequence",
        })?;
    }
    Ok(grants)
}

struct GrantRow {
    knowledge_seq: u64,
    player_id: [u8; 8],
    subject_kind: SubjectKind,
    subject_id: Vec<u8>,
    grant_key: i64,
    acquired_period: u64,
    source_journal_seq: u64,
    payload: Vec<u8>,
    previous_hash: [u8; 32],
    entry_hash: [u8; 32],
}

fn decode_grant_row(row: &Row<'_>) -> Result<GrantRow, SaveError> {
    let knowledge_seq = widen(row.get::<_, i64>(0)?, "knowledge sequence")?;
    let player_id: [u8; 8] = hash_width(row.get::<_, Vec<u8>>(1)?, "knowledge_grant")?;
    let subject_kind = SubjectKind::from_code(row.get(2)?).ok_or(SaveError::CorruptPayload {
        table: "knowledge_grant",
        reason: "the stored subject kind is outside the closed registry",
    })?;
    let subject_id: Vec<u8> = row.get(3)?;
    let grant_key: i64 = row.get(4)?;
    let acquired_period = widen(row.get::<_, i64>(5)?, "acquired period")?;
    let source_journal_seq = widen(row.get::<_, i64>(6)?, "source journal sequence")?;
    let payload: Vec<u8> = row.get(7)?;
    let previous_hash = hash32(row.get::<_, Vec<u8>>(8)?)?;
    let entry_hash = hash32(row.get::<_, Vec<u8>>(9)?)?;
    if payload.len() > MAX_KNOWLEDGE_PAYLOAD_BYTES {
        return Err(SaveError::PayloadTooLarge {
            table: "knowledge_grant",
            limit: MAX_KNOWLEDGE_PAYLOAD_BYTES,
            actual: payload.len(),
        });
    }
    let recomputed = owner::knowledge_entry_hash(&KnowledgeInput {
        knowledge_seq,
        player_id,
        subject_kind,
        subject_id: &subject_id,
        grant_key,
        acquired_period,
        source_journal_seq,
        raw_len: u32::try_from(payload.len()).map_err(|_| SaveError::CorruptPayload {
            table: "knowledge_grant",
            reason: "the stored payload is wider than its length prefix",
        })?,
        raw_hash: content_digest::sha256_of(&payload),
        previous_hash,
    })?;
    if recomputed != entry_hash {
        return Err(SaveError::CorruptPayload {
            table: "knowledge_grant",
            reason: "a stored grant does not match its entry hash",
        });
    }
    Ok(GrantRow {
        knowledge_seq,
        player_id,
        subject_kind,
        subject_id,
        grant_key,
        acquired_period,
        source_journal_seq,
        payload,
        previous_hash,
        entry_hash,
    })
}

/// Read every authenticated exhaustive-detail row of one family and period.
///
/// # Errors
///
/// Refuses a period outside the retained thirteen-period window, a payload
/// outside the recent-detail budget, a stored codec or length or digest
/// mismatch, or a `SQLite` failure.
pub(super) fn read_recent_detail(
    connection: &Connection,
    completed: u64,
    period: u64,
    family: DetailFamily,
) -> Result<Vec<RecentDetailRow>, SaveError> {
    retention::validate_detail_period(period, completed)?;
    let mut statement = connection.prepare(
        "SELECT ordinal, codec, raw_len, raw_hash, payload
         FROM recent_detail WHERE period = ?1 AND family = ?2 ORDER BY ordinal",
    )?;
    let mut rows = statement.query(rusqlite::params![
        integer_sql(period, "detail period")?,
        family.code()
    ])?;
    let mut detail = Vec::new();
    while let Some(row) = rows.next()? {
        let payload: Vec<u8> = row.get(4)?;
        let stored = StoredPayload {
            codec: PayloadCodec::from_code(row.get(1)?)?,
            raw_len: u32::try_from(row.get::<_, i64>(2)?).map_err(|_| {
                SaveError::CorruptPayload {
                    table: "recent_detail",
                    reason: "the stored decoded length is out of range",
                }
            })?,
            raw_hash: hash32(row.get(3)?)?,
            payload: &payload,
        };
        detail.push(RecentDetailRow {
            period,
            family,
            ordinal: u32::try_from(row.get::<_, i64>(0)?).map_err(|_| {
                SaveError::CorruptPayload {
                    table: "recent_detail",
                    reason: "the stored ordinal is out of range",
                }
            })?,
            payload: codec::decode_chunk_payload(PayloadBudget::RecentDetail, &stored)?,
        });
    }
    Ok(detail)
}

/// Recover one damaged campaign into a clean independent destination.
///
/// Only cold layers are dropped: exhaustive-detail rows and historical
/// checkpoints that no longer authenticate. The current root, the permanent
/// journal and earned knowledge must verify completely, because replacing them
/// would fabricate a campaign that never existed and could re-execute committed
/// periods. The source file is opened read-only and is never modified.
///
/// # Errors
///
/// Refuses a missing source, an existing destination, a mismatched build, any
/// damage to the current root or a permanent structure, an integrity failure, or
/// a host I/O failure. A failed recovery removes its temporary file.
pub(super) fn recover_to_new_save(
    source: &Path,
    destination: &Path,
    expected_build: BuildIdentity,
) -> Result<VerifiedRecovery, SaveError> {
    let started = Instant::now();
    if !source.exists() {
        return Err(SaveError::CampaignMissing {
            path: source.to_path_buf(),
        });
    }
    if destination.exists() {
        return Err(SaveError::ExportDestinationExists);
    }
    let identity = source_identity(source, expected_build)?;
    let unpublished = export::temporary_path(destination)?;
    let counts = match recover_into(source, &unpublished, &identity) {
        Ok(counts) => counts,
        Err(error) => {
            export::remove_if_present(&unpublished);
            return Err(error);
        }
    };
    let destination_bytes = match export::publish(&unpublished, destination) {
        Ok(bytes) => bytes,
        Err(error) => {
            export::remove_if_present(&unpublished);
            return Err(error);
        }
    };
    Ok(VerifiedRecovery {
        destination_bytes,
        recovered_period: identity.period,
        world_hash: identity.world_hash,
        journal_tail_hash: identity.journal_tail_hash,
        cold_rows_dropped: counts.0,
        checkpoints_dropped: counts.1,
        integrity_verified: true,
        elapsed_ns: elapsed_ns(started),
    })
}

fn recover_into(
    source: &Path,
    unpublished: &Path,
    identity: &ExportIdentity,
) -> Result<(u32, u32), SaveError> {
    let connection = Connection::open_with_flags(
        source,
        OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_NO_MUTEX,
    )?;
    connection.busy_timeout(schema::BUSY_TIMEOUT)?;
    schema::verify_installed_schema(&connection)?;
    export::backup_to(&connection, unpublished)?;
    drop(connection);

    let copy = Connection::open(unpublished)?;
    copy.busy_timeout(schema::BUSY_TIMEOUT)?;
    copy.pragma_update(None, "foreign_keys", "ON")?;
    let cold_rows_dropped = drop_damaged_detail(&copy)?;
    let checkpoints_dropped = drop_damaged_checkpoints(&copy)?;
    copy.execute_batch(&format!(
        "PRAGMA incremental_vacuum({})",
        retention::INCREMENTAL_VACUUM_PAGES
    ))?;
    drop(copy);

    export::verify_export(unpublished, identity)?;
    Ok((cold_rows_dropped, checkpoints_dropped))
}

fn drop_damaged_detail(connection: &Connection) -> Result<u32, SaveError> {
    let mut damaged = Vec::new();
    {
        let mut statement = connection.prepare(
            "SELECT period, family, ordinal, codec, raw_len, raw_hash, payload
             FROM recent_detail",
        )?;
        let mut rows = statement.query([])?;
        while let Some(row) = rows.next()? {
            let decoded = decode_detail_row(row);
            if decoded.is_err() {
                damaged.push((
                    row.get::<_, i64>(0)?,
                    row.get::<_, i64>(1)?,
                    row.get::<_, i64>(2)?,
                ));
            }
        }
    }
    for (period, family, ordinal) in &damaged {
        connection.execute(
            "DELETE FROM recent_detail WHERE period = ?1 AND family = ?2 AND ordinal = ?3",
            rusqlite::params![period, family, ordinal],
        )?;
    }
    u32::try_from(damaged.len()).map_err(|_| SaveError::Arithmetic {
        field: "dropped detail rows",
    })
}

fn decode_detail_row(row: &Row<'_>) -> Result<Vec<u8>, SaveError> {
    let payload: Vec<u8> = row.get(6)?;
    let stored = StoredPayload {
        codec: PayloadCodec::from_code(row.get(3)?)?,
        raw_len: u32::try_from(row.get::<_, i64>(4)?).map_err(|_| SaveError::CorruptPayload {
            table: "recent_detail",
            reason: "the stored decoded length is out of range",
        })?,
        raw_hash: hash32(row.get(5)?)?,
        payload: &payload,
    };
    codec::decode_chunk_payload(PayloadBudget::RecentDetail, &stored)
}

fn drop_damaged_checkpoints(connection: &Connection) -> Result<u32, SaveError> {
    let mut checkpoints = Vec::new();
    {
        let mut statement = connection.prepare(
            "SELECT snapshot_id, role, period, world_hash, state_hash, manifest_bytes,
                    committed_journal_seq, committed_journal_hash, knowledge_seq, knowledge_hash
             FROM snapshot WHERE role = 3",
        )?;
        let mut rows = statement.query([])?;
        while let Some(row) = rows.next()? {
            checkpoints.push(owner::decode_snapshot_row(row)?);
        }
    }
    let mut dropped = 0_u32;
    for checkpoint in &checkpoints {
        if owner::load_current_root(connection, checkpoint).is_err() {
            retention::delete_snapshot(connection, checkpoint.snapshot_id)?;
            dropped = dropped.saturating_add(1);
        }
    }
    connection.execute(
        "DELETE FROM state_chunk
         WHERE chunk_id NOT IN (SELECT chunk_id FROM snapshot_chunk)",
        [],
    )?;
    Ok(dropped)
}

fn source_identity(
    source: &Path,
    expected_build: BuildIdentity,
) -> Result<ExportIdentity, SaveError> {
    let connection = Connection::open_with_flags(
        source,
        OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_NO_MUTEX,
    )?;
    connection.busy_timeout(schema::BUSY_TIMEOUT)?;
    schema::verify_installed_schema(&connection)?;
    let manifest = owner::read_manifest(&connection)?;
    if manifest.build_hash != expected_build.hash() {
        return Err(SaveError::BuildMismatch {
            expected: expected_build.hash(),
            actual: manifest.build_hash,
        });
    }
    let snapshot = owner::read_snapshot(&connection, manifest.current_snapshot_id)?;
    if snapshot.role != SnapshotRole::Current && snapshot.role != SnapshotRole::Opening {
        return Err(SaveError::CorruptManifest {
            reason: "the manifest does not point at a restart root",
        });
    }
    Ok(ExportIdentity {
        campaign_id: manifest.campaign_id,
        build_hash: manifest.build_hash,
        content_hash: manifest.content_hash,
        current_snapshot_id: manifest.current_snapshot_id,
        period: snapshot.period,
        world_hash: snapshot.world_hash,
        state_hash: snapshot.state_hash,
        journal_tail_seq: manifest.journal_tail_seq,
        journal_tail_hash: manifest.journal_tail_hash,
        knowledge_tail_seq: manifest.knowledge_tail_seq,
        knowledge_tail_hash: manifest.knowledge_tail_hash,
    })
}

fn select_checkpoint(
    connection: &Connection,
    target_period: u64,
) -> Result<SnapshotHeader, ReplayError> {
    let target = integer_sql(target_period, "target period")?;
    let snapshot_id: Option<i64> = connection
        .query_row(
            "SELECT snapshot_id FROM snapshot WHERE period <= ?1
             ORDER BY period DESC, role ASC, snapshot_id DESC LIMIT 1",
            [target],
            |row| row.get(0),
        )
        .map(Some)
        .or_else(|error| match error {
            rusqlite::Error::QueryReturnedNoRows => Ok(None),
            other => Err(SaveError::from(other)),
        })?;
    let Some(snapshot_id) = snapshot_id else {
        return Err(ReplayError::NoCheckpoint { target_period });
    };
    Ok(owner::read_snapshot(connection, snapshot_id)?)
}

struct JournalRow {
    journal_seq: u64,
    kind: JournalKind,
    period: u64,
    subject: Option<(SubjectKind, Vec<u8>)>,
    payload: Vec<u8>,
    previous_hash: [u8; 32],
    entry_hash: [u8; 32],
}

fn decode_journal_row(row: &Row<'_>) -> Result<JournalRow, SaveError> {
    let journal_seq = widen(row.get::<_, i64>(0)?, "journal sequence")?;
    let kind = JournalKind::from_code(row.get(1)?).ok_or(SaveError::CorruptPayload {
        table: "permanent_journal",
        reason: "the stored journal kind is outside the closed registry",
    })?;
    let period = widen(row.get::<_, i64>(2)?, "journal period")?;
    let actor_bytes: Option<Vec<u8>> = row.get(3)?;
    let actor_id = actor_bytes
        .map(|bytes| hash_width::<8>(bytes, "permanent_journal"))
        .transpose()?;
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
            })
        }
    };
    let nonce_bytes: Option<Vec<u8>> = row.get(6)?;
    let nonce = nonce_bytes
        .map(|bytes| hash_width::<16>(bytes, "permanent_journal"))
        .transpose()?;
    let record_key: Option<Vec<u8>> = row.get(7)?;
    let payload: Vec<u8> = row.get(11)?;
    let stored = StoredPayload {
        codec: PayloadCodec::from_code(row.get(8)?)?,
        raw_len: u32::try_from(row.get::<_, i64>(9)?).map_err(|_| SaveError::CorruptPayload {
            table: "permanent_journal",
            reason: "the stored decoded length is out of range",
        })?,
        raw_hash: hash32(row.get(10)?)?,
        payload: &payload,
    };
    let decoded = codec::decode_chunk_payload(PayloadBudget::PermanentJournal, &stored)?;
    let previous_hash = hash32(row.get(12)?)?;
    let entry_hash = hash32(row.get(13)?)?;
    let recomputed = owner::journal_entry_hash(&JournalInput {
        journal_seq,
        kind,
        period,
        actor_id,
        subject: subject.as_ref().map(|(kind, id)| (*kind, id.as_slice())),
        nonce,
        record_key: record_key.as_deref(),
        raw_len: stored.raw_len,
        raw_hash: stored.raw_hash,
        previous_hash,
    })?;
    if recomputed != entry_hash {
        return Err(SaveError::CorruptPayload {
            table: "permanent_journal",
            reason: "a stored journal entry does not match its entry hash",
        });
    }
    Ok(JournalRow {
        journal_seq,
        kind,
        period,
        subject,
        payload: decoded,
        previous_hash,
        entry_hash,
    })
}

fn isolated_copy(connection: &Connection, source: &Path) -> Result<PathBuf, ReplayError> {
    let path = isolated_path(source)?;
    match export::backup_to(connection, &path) {
        Ok(()) => Ok(path),
        Err(error) => {
            export::remove_if_present(&path);
            Err(error.into())
        }
    }
}

fn isolated_path(source: &Path) -> Result<PathBuf, SaveError> {
    let directory = source.parent().unwrap_or_else(|| Path::new("."));
    let name = source
        .file_name()
        .and_then(|value| value.to_str())
        .unwrap_or("campaign");
    for attempt in 0..8_u32 {
        let stamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_or(0, |duration| duration.as_nanos());
        let candidate = directory.join(format!(
            ".{name}.replay-{}-{stamp}-{attempt}",
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
    Err(SaveError::Io(std::io::Error::new(
        ErrorKind::AlreadyExists,
        "could not reserve a unique replay path",
    )))
}

fn ensure_running(cancel: &AtomicBool) -> Result<(), ReplayError> {
    if cancel.load(Ordering::Relaxed) {
        return Err(ReplayError::Cancelled);
    }
    Ok(())
}

fn integer(value: u64, field: &'static str) -> Result<i64, ReplayError> {
    i64::try_from(value).map_err(|_| SaveError::Arithmetic { field }.into())
}

fn widen(value: i64, field: &'static str) -> Result<u64, SaveError> {
    u64::try_from(value).map_err(|_| SaveError::CorruptPayload {
        table: "permanent_journal",
        reason: match field {
            "acquired period" => "the stored acquisition period is negative",
            "source journal sequence" => "the stored source sequence is negative",
            "journal period" => "the stored journal period is negative",
            _ => "the stored sequence is negative",
        },
    })
}

fn integer_sql(value: u64, field: &'static str) -> Result<i64, SaveError> {
    i64::try_from(value).map_err(|_| SaveError::Arithmetic { field })
}

fn hash32(bytes: Vec<u8>) -> Result<[u8; 32], SaveError> {
    hash_width::<32>(bytes, "permanent_journal")
}

fn hash_width<const WIDTH: usize>(
    bytes: Vec<u8>,
    table: &'static str,
) -> Result<[u8; WIDTH], SaveError> {
    <[u8; WIDTH]>::try_from(bytes).map_err(|_| SaveError::CorruptPayload {
        table,
        reason: "a stored identity is not its published width",
    })
}

fn elapsed_ns(started: Instant) -> u64 {
    u64::try_from(started.elapsed().as_nanos()).map_or(u64::MAX, |value| value)
}
