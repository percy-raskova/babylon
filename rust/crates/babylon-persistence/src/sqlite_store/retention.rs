//! Commit-time five-layer retention rotation and reachability reclamation.
//!
//! One period commit installs the successor current root and rotates retention
//! inside the same immediate transaction. `recent_detail` keeps the latest
//! thirteen completed periods; `snapshot` keeps the opening, the current root and
//! at most the two newest thirteen-period checkpoints; `state_chunk` rows no
//! retained snapshot reaches are deleted, and a bounded incremental vacuum
//! returns the freed pages afterwards. Captured content, the permanent journal
//! and earned knowledge are never candidates for rotation.
//!
//! The store also owns the terminal journal sequence of every period. The
//! deterministic rule is: one accepted-command record at acknowledgement, then
//! the command resolution record, the caller's evidence records in supplied
//! order, and finally the compact period summary written here. Because that
//! summary is the last record, the committed snapshot, the manifest tail and the
//! period summary all name the same sequence and hash.

use std::path::Path;

use rusqlite::Connection;
use rusqlite::Error;

use crate::sqlite_store::chunks::JournalKind;
use crate::sqlite_store::SaveError;

/// Number of completed periods retained as exhaustive technical detail.
pub const RECENT_DETAIL_PERIODS: u64 = 13;

/// Interval, in completed periods, between retained historical checkpoints.
pub const CHECKPOINT_INTERVAL: u64 = 13;

/// How many completed historical checkpoints stay retained.
pub const RETAINED_CHECKPOINTS: usize = 2;

/// Upper bound on pages returned to the file system by one rotation.
pub const INCREMENTAL_VACUUM_PAGES: i64 = 128;

/// Domain separator for the compact period summary payload.
const SUMMARY_DOMAIN: &[u8] = b"babylon.period-summary.v1\0";

/// Exact byte width of one encoded period summary body.
const SUMMARY_BODY_BYTES: usize = 8 + 32 + 32 + 32 + 8 + 32 + 8 + 32 + 4 + 4;

/// Whether one completed period installs a retained historical checkpoint.
#[must_use]
pub const fn is_checkpoint_period(period: u64) -> bool {
    period > 0 && period.is_multiple_of(CHECKPOINT_INTERVAL)
}

/// First completed period inside the retained exhaustive-detail window.
#[must_use]
pub const fn first_retained_detail_period(period: u64) -> u64 {
    let lookback = RECENT_DETAIL_PERIODS - 1;
    if period > lookback {
        period - lookback
    } else {
        1
    }
}

/// Honest, separately reported storage accounting for one rotated commit.
///
/// `gross_bytes_added` counts the canonical decoded bytes this commit wrote into
/// state chunks, journal records and knowledge grants. Deletions are reported
/// apart and never subtracted from it: `bytes_made_unreachable` is the exact
/// stored payload size of the rows rotation removed, and `reclaimed_bytes` is the
/// main-file shrinkage the bounded vacuum actually produced. `main_file_bytes`,
/// `free_page_bytes` and `wal_bytes` are separate physical quantities measured
/// after the commit.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct RetentionAccountingReport {
    /// Completed period the rotation produced.
    pub period: u64,
    /// Canonical decoded bytes this commit added.
    pub gross_bytes_added: u64,
    /// Stored payload bytes of the rows rotation removed.
    pub bytes_made_unreachable: u64,
    /// Main-file bytes the bounded incremental vacuum actually returned.
    pub reclaimed_bytes: u64,
    /// Main database file size after the commit.
    pub main_file_bytes: u64,
    /// Free pages still owned by the main file after the commit.
    pub free_page_bytes: u64,
    /// Write-ahead log bytes after the commit.
    pub wal_bytes: u64,
    /// Snapshots retained by the whole five-layer rule.
    pub snapshots_retained: u32,
    /// State chunks deleted because no retained snapshot reached them.
    pub chunks_reclaimed: u32,
    /// Exhaustive-detail rows deleted outside the thirteen-period window.
    pub detail_rows_reclaimed: u32,
}

/// The compact permanent summary one completed period appends last.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct PeriodSummary {
    /// Completed period.
    pub period: u64,
    /// Canonical identity of the exact period candidate that committed.
    pub candidate_hash: [u8; 32],
    /// Canonical world identity recorded by the period.
    pub world_hash: [u8; 32],
    /// Canonical state identity recorded by the period.
    pub state_hash: [u8; 32],
    /// Journal tail sequence immediately before this summary.
    pub prior_journal_seq: u64,
    /// Journal tail hash immediately before this summary.
    pub prior_journal_hash: [u8; 32],
    /// Knowledge tail sequence the period committed.
    pub knowledge_tail_seq: u64,
    /// Knowledge tail hash the period committed.
    pub knowledge_tail_hash: [u8; 32],
    /// Exhaustive-detail rows written for the period.
    pub detail_rows: u32,
    /// Caller evidence records written before the summary.
    pub evidence_records: u32,
}

impl PeriodSummary {
    /// Encode the summary as its exact canonical payload.
    #[must_use]
    pub fn encode(&self) -> Vec<u8> {
        let mut bytes = Vec::with_capacity(SUMMARY_DOMAIN.len() + SUMMARY_BODY_BYTES);
        bytes.extend_from_slice(SUMMARY_DOMAIN);
        bytes.extend_from_slice(&self.period.to_be_bytes());
        bytes.extend_from_slice(&self.candidate_hash);
        bytes.extend_from_slice(&self.world_hash);
        bytes.extend_from_slice(&self.state_hash);
        bytes.extend_from_slice(&self.prior_journal_seq.to_be_bytes());
        bytes.extend_from_slice(&self.prior_journal_hash);
        bytes.extend_from_slice(&self.knowledge_tail_seq.to_be_bytes());
        bytes.extend_from_slice(&self.knowledge_tail_hash);
        bytes.extend_from_slice(&self.detail_rows.to_be_bytes());
        bytes.extend_from_slice(&self.evidence_records.to_be_bytes());
        bytes
    }
}

/// Decode one stored period summary payload.
///
/// # Errors
///
/// Refuses a payload without the exact summary domain and width.
pub fn decode_period_summary(payload: &[u8]) -> Result<PeriodSummary, SaveError> {
    if payload.len() != SUMMARY_DOMAIN.len() + SUMMARY_BODY_BYTES
        || !payload.starts_with(SUMMARY_DOMAIN)
    {
        return Err(SaveError::CorruptPayload {
            table: "permanent_journal",
            reason: "the period summary payload is not its exact canonical width",
        });
    }
    let mut reader = SummaryReader {
        bytes: &payload[SUMMARY_DOMAIN.len()..],
        offset: 0,
    };
    Ok(PeriodSummary {
        period: reader.u64()?,
        candidate_hash: reader.hash()?,
        world_hash: reader.hash()?,
        state_hash: reader.hash()?,
        prior_journal_seq: reader.u64()?,
        prior_journal_hash: reader.hash()?,
        knowledge_tail_seq: reader.u64()?,
        knowledge_tail_hash: reader.hash()?,
        detail_rows: reader.u32()?,
        evidence_records: reader.u32()?,
    })
}

struct SummaryReader<'a> {
    bytes: &'a [u8],
    offset: usize,
}

impl SummaryReader<'_> {
    fn take(&mut self, width: usize) -> Result<&[u8], SaveError> {
        let end = self
            .offset
            .checked_add(width)
            .ok_or(SaveError::Arithmetic {
                field: "period summary offset",
            })?;
        let slice = self
            .bytes
            .get(self.offset..end)
            .ok_or(SaveError::CorruptPayload {
                table: "permanent_journal",
                reason: "the period summary payload is truncated",
            })?;
        self.offset = end;
        Ok(slice)
    }

    fn u64(&mut self) -> Result<u64, SaveError> {
        let mut value = [0_u8; 8];
        value.copy_from_slice(self.take(8)?);
        Ok(u64::from_be_bytes(value))
    }

    fn u32(&mut self) -> Result<u32, SaveError> {
        let mut value = [0_u8; 4];
        value.copy_from_slice(self.take(4)?);
        Ok(u32::from_be_bytes(value))
    }

    fn hash(&mut self) -> Result<[u8; 32], SaveError> {
        let mut value = [0_u8; 32];
        value.copy_from_slice(self.take(32)?);
        Ok(value)
    }
}

/// Delete one superseded snapshot and every chunk link it owned.
///
/// The chunks themselves stay until reachability reclamation runs, so a
/// checkpoint twin or the successor root keeps sharing their integer identity.
///
/// # Errors
///
/// Refuses a `SQLite` failure.
pub(super) fn delete_snapshot(connection: &Connection, snapshot_id: i64) -> Result<u64, SaveError> {
    let manifest_bytes: i64 = connection.query_row(
        "SELECT length(manifest_bytes) FROM snapshot WHERE snapshot_id = ?1",
        [snapshot_id],
        |row| row.get(0),
    )?;
    connection.execute(
        "DELETE FROM snapshot_chunk WHERE snapshot_id = ?1",
        [snapshot_id],
    )?;
    connection.execute("DELETE FROM snapshot WHERE snapshot_id = ?1", [snapshot_id])?;
    u64::try_from(manifest_bytes).map_err(|_| SaveError::CorruptPayload {
        table: "snapshot",
        reason: "the stored manifest length is negative",
    })
}

/// Rotate every layer and reclaim unreachable chunks inside the commit.
///
/// `gross_bytes_added` is supplied by the commit path, which knows exactly which
/// canonical bytes it inserted.
///
/// # Errors
///
/// Refuses a missing opening or current root, a `SQLite` failure, or a pragma
/// that cannot be read.
pub(super) fn rotate(
    connection: &Connection,
    period: u64,
    gross_bytes_added: u64,
    superseded_bytes: u64,
) -> Result<RetentionAccountingReport, SaveError> {
    let page_bytes = u64::try_from(reader_pragma(connection, "page_size")?)
        .map_err(|_| SaveError::Arithmetic { field: "page size" })?;
    let pages_before = reader_pragma(connection, "page_count")?;
    let retained = retained_snapshot_ids(connection)?;
    let bytes_made_unreachable = superseded_bytes
        .checked_add(unreachable_payload_bytes(connection, &retained)?)
        .ok_or(SaveError::Arithmetic {
            field: "unreachable bytes",
        })?;
    delete_snapshots_outside(connection, &retained)?;
    let chunks_reclaimed = delete_unreachable_chunks(connection)?;
    let detail_rows_reclaimed = prune_recent_detail(connection, period)?;

    connection.execute_batch(&format!(
        "PRAGMA incremental_vacuum({INCREMENTAL_VACUUM_PAGES})"
    ))?;

    let pages_after = reader_pragma(connection, "page_count")?;
    let free_pages = reader_pragma(connection, "freelist_count")?;
    let snapshots_retained = u32::try_from(retained.len()).map_err(|_| SaveError::Arithmetic {
        field: "retained snapshot count",
    })?;
    Ok(RetentionAccountingReport {
        period,
        gross_bytes_added,
        bytes_made_unreachable,
        reclaimed_bytes: page_bytes_of(page_bytes, pages_before.saturating_sub(pages_after))?,
        main_file_bytes: page_bytes_of(page_bytes, pages_after)?,
        free_page_bytes: page_bytes_of(page_bytes, free_pages)?,
        wal_bytes: 0,
        snapshots_retained,
        chunks_reclaimed,
        detail_rows_reclaimed,
    })
}

/// Return the physical write-ahead-log bytes beside one campaign path.
#[must_use]
pub fn wal_bytes(path: &Path) -> u64 {
    let mut sidecar = path.as_os_str().to_os_string();
    sidecar.push("-wal");
    std::fs::metadata(sidecar).map_or(0, |metadata| metadata.len())
}

/// Resolve one permanent evidence record by its closed kind and record key.
///
/// Rotation never deletes `permanent_journal` rows, so a compact state row that
/// names a receipt, observation or governed choice keeps its evidence resolvable
/// after every checkpoint and detail row that period owned has rotated out.
///
/// # Errors
///
/// Refuses an empty record key, a negative stored sequence, or a `SQLite`
/// failure.
pub(super) fn journal_sequence_for_record(
    connection: &Connection,
    kind: JournalKind,
    record_key: &[u8],
) -> Result<Option<u64>, SaveError> {
    if record_key.is_empty() {
        return Err(SaveError::InvalidField {
            table: "permanent_journal",
            field: "record_key",
            reason: "the record key is empty",
        });
    }
    let sequence: Option<i64> = connection
        .query_row(
            "SELECT journal_seq FROM permanent_journal WHERE kind = ?1 AND record_key = ?2",
            rusqlite::params![kind.code(), record_key],
            |row| row.get(0),
        )
        .map(Some)
        .or_else(|error| match error {
            Error::QueryReturnedNoRows => Ok(None),
            other => Err(other),
        })?;
    match sequence {
        Some(value) => Ok(Some(u64::try_from(value).map_err(|_| {
            SaveError::CorruptPayload {
                table: "permanent_journal",
                reason: "the stored journal sequence is negative",
            }
        })?)),
        None => Ok(None),
    }
}

/// Refuse a detail period that already fell out of the retained window.
///
/// # Errors
///
/// Refuses a zero period, a period after `completed`, or a period older than the
/// thirteen-period window.
pub(super) fn validate_detail_period(period: u64, completed: u64) -> Result<(), SaveError> {
    if period == 0 || period > completed || period < first_retained_detail_period(completed) {
        return Err(SaveError::InvalidField {
            table: "recent_detail",
            field: "period",
            reason: "the detail period is outside the retained thirteen-period window",
        });
    }
    Ok(())
}

fn retained_snapshot_ids(connection: &Connection) -> Result<Vec<i64>, SaveError> {
    let mut ids = Vec::with_capacity(RETAINED_CHECKPOINTS + 2);
    let opening: i64 = connection.query_row(
        "SELECT snapshot_id FROM snapshot WHERE role = 1",
        [],
        |row| row.get(0),
    )?;
    ids.push(opening);
    let current: i64 = connection.query_row(
        "SELECT snapshot_id FROM snapshot WHERE role = 2",
        [],
        |row| row.get(0),
    )?;
    ids.push(current);
    let limit = i64::try_from(RETAINED_CHECKPOINTS).map_err(|_| SaveError::Arithmetic {
        field: "retained checkpoint count",
    })?;
    let mut statement = connection.prepare(
        "SELECT snapshot_id FROM snapshot WHERE role = 3
         ORDER BY period DESC, snapshot_id DESC LIMIT ?1",
    )?;
    let rows = statement.query_map([limit], |row| row.get::<_, i64>(0))?;
    for row in rows {
        ids.push(row?);
    }
    Ok(ids)
}

fn delete_snapshots_outside(connection: &Connection, retained: &[i64]) -> Result<(), SaveError> {
    let mut doomed = Vec::new();
    {
        let sql = format!(
            "SELECT snapshot_id FROM snapshot WHERE snapshot_id NOT IN ({})",
            placeholders(retained.len())
        );
        let mut statement = connection.prepare(&sql)?;
        let rows = statement.query_map(rusqlite::params_from_iter(retained), |row| {
            row.get::<_, i64>(0)
        })?;
        for row in rows {
            doomed.push(row?);
        }
    }
    for snapshot_id in &doomed {
        delete_snapshot(connection, *snapshot_id)?;
    }
    Ok(())
}

fn delete_unreachable_chunks(connection: &Connection) -> Result<u32, SaveError> {
    let deleted = connection.execute(
        "DELETE FROM state_chunk
         WHERE chunk_id NOT IN (SELECT chunk_id FROM snapshot_chunk)",
        [],
    )?;
    u32::try_from(deleted).map_err(|_| SaveError::Arithmetic {
        field: "reclaimed chunk count",
    })
}

fn prune_recent_detail(connection: &Connection, period: u64) -> Result<u32, SaveError> {
    let first =
        i64::try_from(first_retained_detail_period(period)).map_err(|_| SaveError::Arithmetic {
            field: "retained detail period",
        })?;
    let deleted = connection.execute("DELETE FROM recent_detail WHERE period < ?1", [first])?;
    u32::try_from(deleted).map_err(|_| SaveError::Arithmetic {
        field: "reclaimed detail row count",
    })
}

fn unreachable_payload_bytes(connection: &Connection, retained: &[i64]) -> Result<u64, SaveError> {
    let snapshot_sql = format!(
        "SELECT COALESCE(SUM(length(manifest_bytes)), 0) FROM snapshot
         WHERE snapshot_id NOT IN ({})",
        placeholders(retained.len())
    );
    let snapshot_bytes: i64 =
        connection.query_row(&snapshot_sql, rusqlite::params_from_iter(retained), |row| {
            row.get(0)
        })?;
    let chunk_bytes: i64 = connection.query_row(
        "SELECT COALESCE(SUM(length(payload)), 0) FROM state_chunk
         WHERE chunk_id NOT IN (SELECT chunk_id FROM snapshot_chunk)",
        [],
        |row| row.get(0),
    )?;
    let bytes = |value: i64| -> Result<u64, SaveError> {
        u64::try_from(value).map_err(|_| SaveError::CorruptPayload {
            table: "snapshot",
            reason: "a stored byte count is negative",
        })
    };
    bytes(snapshot_bytes)?
        .checked_add(bytes(chunk_bytes)?)
        .ok_or(SaveError::Arithmetic {
            field: "unreachable bytes",
        })
}

fn placeholders(count: usize) -> String {
    let mut text = String::with_capacity(count * 2);
    for index in 0..count {
        if index != 0 {
            text.push(',');
        }
        text.push('?');
    }
    text
}

fn page_bytes_of(page_bytes: u64, pages: i64) -> Result<u64, SaveError> {
    u64::try_from(pages)
        .map_err(|_| SaveError::Arithmetic {
            field: "page count",
        })?
        .checked_mul(page_bytes)
        .ok_or(SaveError::Arithmetic {
            field: "page bytes",
        })
}

fn reader_pragma(connection: &Connection, name: &str) -> Result<i64, SaveError> {
    connection
        .query_row(&format!("PRAGMA {name}"), [], |row| row.get(0))
        .map_err(SaveError::from)
}
