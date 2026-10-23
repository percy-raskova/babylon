//! Bounded ordered receipt draining with coherent committed progress.

#[cfg(test)]
mod live_tests;

#[path = "worker/sweep.rs"]
mod sweep;

#[allow(unused_imports)]
pub(crate) use sweep::sweep;
#[allow(unused_imports)]
use sweep::{capture_receipt, read_progress, sweep_locked};

#[allow(unused_imports)]
use super::{publication, tick_knowledge, ArchiveReadScope};
#[allow(unused_imports)]
use crate::archive::{database, decode};
#[allow(unused_imports)]
use crate::production_projection::diagnostics::{Stage, Timing};
#[allow(unused_imports)]
use crate::{
    identity::CampaignId, ArchiveDossierProducer, ArchiveKnowledge, ArchiveMaterializeDisposition,
    ArchiveMaterializeMode, ArchiveReceiptDisposition, ArchiveWorkerCancellation,
    ArchiveWorkerSweepReport, PendingArchiveReceipt, SemanticArchiveError, SemanticArchiveStore,
};
#[allow(unused_imports)]
use postgres::{Client, IsolationLevel};
