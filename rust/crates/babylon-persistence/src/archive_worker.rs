//! Production dirty-receipt Archive worker composition.

use postgres::Config;
use uuid::Uuid;

use crate::{
    database, decode, decode_digest, ArchiveDirtyBatchV1, ArchiveMaterializeDispositionV1,
    CampaignId, SemanticArchiveErrorV1, SemanticArchiveStoreV1,
};

/// Exact pending-receipt query used by the production Archive worker.
///
/// Claiming happens inside `SemanticArchiveStoreV1::materialize_receipt` under
/// `SERIALIZABLE`; this query deliberately avoids row locking because a
/// single-worker assumption holds and a double-run reconciles as
/// `AlreadyConsumed`.
pub const ARCHIVE_PENDING_RECEIPTS_SQL_V1: &str = "SELECT \
    d.resolve_tick, d.tick_content_hash \
    FROM babylon_state.archive_dirty_receipt_v1 d \
    LEFT JOIN babylon_meta.archive_receipt_consumption_v1 c \
      ON c.campaign_id = d.campaign_id \
     AND c.resolve_tick = d.resolve_tick \
    WHERE d.campaign_id = $1::uuid \
      AND c.campaign_id IS NULL \
    ORDER BY d.resolve_tick ASC";

/// One committed dirty receipt waiting for a content producer.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PendingArchiveReceiptV1 {
    resolve_tick: u64,
    tick_content_hash: [u8; 32],
}

impl PendingArchiveReceiptV1 {
    /// Validate a committed dirty receipt boundary.
    ///
    /// # Errors
    /// Refuses tick zero or a value outside `PostgreSQL` `BIGINT`.
    pub fn try_new(
        resolve_tick: u64,
        tick_content_hash: [u8; 32],
    ) -> Result<Self, SemanticArchiveErrorV1> {
        if resolve_tick == 0 || resolve_tick > i64::MAX as u64 {
            return Err(SemanticArchiveErrorV1::InvalidVerifiedTick);
        }
        Ok(Self {
            resolve_tick,
            tick_content_hash,
        })
    }

    /// Return the honest committed source tick.
    #[must_use]
    pub const fn resolve_tick(&self) -> u64 {
        self.resolve_tick
    }

    /// Return the exact tick content hash bound to the receipt.
    #[must_use]
    pub const fn tick_content_hash(&self) -> &[u8; 32] {
        &self.tick_content_hash
    }
}

/// Pure decision made for one pending receipt before any database work.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ArchiveReceiptPlanV1 {
    /// The producer returned an empty batch; leave the receipt pending.
    Defer,
    /// The producer returned a non-empty batch; invoke `materialize_receipt`.
    Materialize,
}

/// Observed outcome for one processed receipt.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ArchiveReceiptDispositionV1 {
    /// The producer returned an empty batch and the receipt stays pending.
    Deferred,
    /// `materialize_receipt` consumed the receipt now.
    Applied,
    /// `materialize_receipt` observed an exact prior consumption.
    AlreadyConsumed,
}

/// Content producer that turns one pending receipt into a bounded dirty batch.
pub trait ArchiveDossierProducerV1 {
    /// Produce the exact page batch for one committed dirty receipt.
    ///
    /// # Errors
    /// Returns any producer-side refusal as a `SemanticArchiveErrorV1`.
    fn produce(
        &self,
        campaign_id: Uuid,
        receipt: &PendingArchiveReceiptV1,
    ) -> Result<ArchiveDirtyBatchV1, SemanticArchiveErrorV1>;
}

/// Honest no-op producer: every pending receipt defers.
pub struct NullArchiveDossierProducerV1;

impl NullArchiveDossierProducerV1 {
    /// Construct the null producer.
    #[must_use]
    pub const fn new() -> Self {
        Self
    }
}

impl Default for NullArchiveDossierProducerV1 {
    fn default() -> Self {
        Self::new()
    }
}

impl ArchiveDossierProducerV1 for NullArchiveDossierProducerV1 {
    fn produce(
        &self,
        _campaign_id: Uuid,
        receipt: &PendingArchiveReceiptV1,
    ) -> Result<ArchiveDirtyBatchV1, SemanticArchiveErrorV1> {
        ArchiveDirtyBatchV1::try_new(receipt.resolve_tick, receipt.tick_content_hash, Vec::new())
    }
}

/// Per-sweep worker report with ordered dispositions and derived aggregates.
#[derive(Clone, Debug, PartialEq, Eq, Default)]
pub struct ArchiveWorkerSweepReportV1 {
    dispositions: Vec<(u64, ArchiveReceiptDispositionV1)>,
}

impl ArchiveWorkerSweepReportV1 {
    /// Construct one report from ordered per-receipt dispositions.
    #[must_use]
    pub fn new(dispositions: Vec<(u64, ArchiveReceiptDispositionV1)>) -> Self {
        Self { dispositions }
    }

    /// Borrow the ordered per-receipt outcomes.
    #[must_use]
    pub fn dispositions(&self) -> &[(u64, ArchiveReceiptDispositionV1)] {
        &self.dispositions
    }

    /// Count receipts left pending because the producer returned an empty batch.
    #[must_use]
    pub fn deferred_count(&self) -> usize {
        self.dispositions
            .iter()
            .filter(|(_, disposition)| *disposition == ArchiveReceiptDispositionV1::Deferred)
            .count()
    }

    /// Count receipts consumed by this sweep.
    #[must_use]
    pub fn applied_count(&self) -> usize {
        self.dispositions
            .iter()
            .filter(|(_, disposition)| *disposition == ArchiveReceiptDispositionV1::Applied)
            .count()
    }

    /// Count receipts observed as exactly consumed by a prior run.
    #[must_use]
    pub fn already_consumed_count(&self) -> usize {
        self.dispositions
            .iter()
            .filter(|(_, disposition)| *disposition == ArchiveReceiptDispositionV1::AlreadyConsumed)
            .count()
    }

    /// Highest `resolve_tick` that was applied or already-consumed this sweep.
    #[must_use]
    pub fn verified_tick(&self) -> u64 {
        self.dispositions
            .iter()
            .filter_map(|(tick, disposition)| {
                matches!(
                    disposition,
                    ArchiveReceiptDispositionV1::Applied
                        | ArchiveReceiptDispositionV1::AlreadyConsumed
                )
                .then_some(*tick)
            })
            .max()
            .unwrap_or(0)
    }
}

/// Pure per-receipt decision helper.
#[must_use]
pub fn classify_archive_receipt_v1(batch: &ArchiveDirtyBatchV1) -> ArchiveReceiptPlanV1 {
    if batch.pages().is_empty() {
        ArchiveReceiptPlanV1::Defer
    } else {
        ArchiveReceiptPlanV1::Materialize
    }
}

/// Pure sweep planner over a scripted producer-result sequence.
///
/// Returns `Err` at the first producer failure and never skips past it.
///
/// # Errors
/// Propagates the first producer error unchanged.
pub fn classify_archive_sweep_v1(
    batches: Vec<Result<ArchiveDirtyBatchV1, SemanticArchiveErrorV1>>,
) -> Result<Vec<ArchiveReceiptPlanV1>, SemanticArchiveErrorV1> {
    batches
        .into_iter()
        .map(|batch| Ok(classify_archive_receipt_v1(&batch?)))
        .collect()
}

/// Production Archive worker that composes a content producer with the
/// semantic Archive store.
pub struct ArchiveWorkerV1 {
    store: SemanticArchiveStoreV1,
}

impl ArchiveWorkerV1 {
    /// Bind the worker to one Rust-authoritative `PostgreSQL` target.
    #[must_use]
    pub fn new(config: &Config) -> Self {
        Self {
            store: SemanticArchiveStoreV1::new(config),
        }
    }

    /// Run one ordered sweep over all pending dirty receipts.
    ///
    /// Receipt claiming is delegated to [`SemanticArchiveStoreV1::materialize_receipt`],
    /// which binds the worker identity via [`crate::archive_worker_contract_sha256_v1`].
    ///
    /// # Errors
    /// Returns any producer refusal or database failure immediately, leaving
    /// the sweep incomplete.
    pub fn sweep_once(
        &mut self,
        campaign_id: CampaignId,
        producer: &dyn ArchiveDossierProducerV1,
    ) -> Result<ArchiveWorkerSweepReportV1, SemanticArchiveErrorV1> {
        let mut client = self.store.connect("connect Archive worker sweep")?;
        let rows = client
            .query(ARCHIVE_PENDING_RECEIPTS_SQL_V1, &[campaign_id.as_uuid()])
            .map_err(|error| database("query pending Archive receipts", &error))?;
        let mut dispositions = Vec::with_capacity(rows.len());
        for row in rows {
            let resolve_tick = decode::<i64>(&row, 0)?;
            let resolve_tick = u64::try_from(resolve_tick)
                .map_err(|_| SemanticArchiveErrorV1::StoredPageMismatch)?;
            let tick_content_hash = decode_digest(&row, 1)?;
            let receipt = PendingArchiveReceiptV1::try_new(resolve_tick, tick_content_hash)?;
            let batch = producer.produce(*campaign_id.as_uuid(), &receipt)?;
            if classify_archive_receipt_v1(&batch) == ArchiveReceiptPlanV1::Defer {
                dispositions.push((resolve_tick, ArchiveReceiptDispositionV1::Deferred));
                continue;
            }
            let report = self.store.materialize_receipt(campaign_id, &batch)?;
            let disposition = match report.disposition() {
                ArchiveMaterializeDispositionV1::Applied => ArchiveReceiptDispositionV1::Applied,
                ArchiveMaterializeDispositionV1::AlreadyConsumed => {
                    ArchiveReceiptDispositionV1::AlreadyConsumed
                }
            };
            dispositions.push((resolve_tick, disposition));
        }
        Ok(ArchiveWorkerSweepReportV1::new(dispositions))
    }
}
