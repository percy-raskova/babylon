//! Leaf implementation for the parent module; public paths stay on the parent.

use super::super::{publication, tick_knowledge, ArchiveReadScope};

use crate::production_projection::diagnostics::{Stage, Timing};

use crate::identity::CampaignId;
use crate::{
    ArchiveDossierProducer, ArchiveKnowledge, ArchiveMaterializeDisposition,
    ArchiveMaterializeMode, ArchiveReceiptDisposition, ArchiveWorkerCancellation,
    ArchiveWorkerSweepReport, PendingArchiveReceipt, SemanticArchiveError, SemanticArchiveStore,
};

use crate::archive;
use crate::ArchiveDirtyBatch;
use postgres::{Client, IsolationLevel};

pub(crate) fn sweep(
    store: &SemanticArchiveStore,
    campaign: CampaignId,
    producer: &dyn ArchiveDossierProducer,
    cancellation: &ArchiveWorkerCancellation,
) -> Result<ArchiveWorkerSweepReport, SemanticArchiveError> {
    cancellation.check()?;
    let mut client = store.connect("connect ordered Archive worker")?;
    publication::with_campaign_lock(&mut client, campaign, |client| {
        sweep_locked(
            client,
            campaign,
            producer,
            cancellation,
            crate::ARCHIVE_SWEEP_MAX_RECEIPTS,
        )
    })
}

pub(in crate::archive_revision) fn sweep_locked(
    client: &mut Client,
    campaign: CampaignId,
    producer: &dyn ArchiveDossierProducer,
    cancellation: &ArchiveWorkerCancellation,
    receipt_budget: i64,
) -> Result<ArchiveWorkerSweepReport, SemanticArchiveError> {
    let mut dispositions = Vec::new();
    for _ in 0..receipt_budget {
        cancellation.check()?;
        let Some((receipt, known)) = capture_receipt(client, campaign)? else {
            break;
        };
        cancellation.check()?;
        // The campaign advisory lock remains held, but no worker publication
        // transaction or database snapshot spans producer authentication/rendering.
        let outcome = {
            let _timing = Timing::start(Stage::ArchiveProduction, receipt.resolve_tick());
            producer.produce(
                *campaign.as_uuid(),
                &receipt,
                &known,
                ArchiveDirtyBatch::MAX_PAGES,
            )?
        };
        let mode = if outcome.remaining() == 0 {
            ArchiveMaterializeMode::Consume
        } else {
            ArchiveMaterializeMode::Stage
        };
        cancellation.check()?;
        let mut prepared = publication::prepare(campaign, &receipt, outcome.batch(), &known)?;
        publication::authenticate_existing(client, &mut prepared)?;
        cancellation.check()?;
        let publication_timing = Timing::start(Stage::ArchivePublication, receipt.resolve_tick());
        let mut tx = client
            .build_transaction()
            .isolation_level(IsolationLevel::Serializable)
            .read_only(false)
            .start()
            .map_err(|error| {
                archive::database("begin ordered Archive publication transaction", &error)
            })?;
        {
            let _timing = Timing::start(Stage::ArchivePublicationSchema, receipt.resolve_tick());
            crate::current_schema::require_current_schema(&mut tx)
                .map_err(SemanticArchiveError::CurrentSchema)?;
        }
        let scope = ArchiveReadScope::committed(
            campaign,
            receipt.resolve_tick(),
            *receipt.tick_content_hash(),
        )?;
        // A new pin is durable only with its atomic page publication. Refuse a
        // changed unpinned grant cohort; existing pins remain the exact authority.
        publication::revalidate_prepared(&mut tx, campaign, &receipt)?;
        crate::archive_batch_matches_receipt(outcome.batch(), &receipt)?;
        {
            let _timing = Timing::start(Stage::ArchiveKnowledgePin, receipt.resolve_tick());
            tick_knowledge::pin_prepared(&mut tx, &scope, &known)?;
        }
        cancellation.check()?;
        let report = publication::publish(&mut tx, prepared, mode)?;
        cancellation.check()?;
        {
            let _timing = Timing::start(Stage::ArchivePublicationCommit, receipt.resolve_tick());
            tx.commit().map_err(|error| {
                archive::database("commit ordered Archive publication transaction", &error)
            })?;
        }
        drop(publication_timing);
        let disposition = match (mode, report.disposition()) {
            (_, ArchiveMaterializeDisposition::AlreadyConsumed) => {
                ArchiveReceiptDisposition::AlreadyConsumed
            }
            (ArchiveMaterializeMode::Stage, _) => ArchiveReceiptDisposition::Paged,
            (ArchiveMaterializeMode::Consume, _) => ArchiveReceiptDisposition::Applied,
        };
        dispositions.push((receipt.resolve_tick(), disposition));
        // Never evaluate a later quiet receipt against an incomplete earlier head.
        if mode == ArchiveMaterializeMode::Stage {
            break;
        }
    }
    read_progress(client, campaign, dispositions)
}

pub(in crate::archive_revision) fn capture_receipt(
    client: &mut Client,
    campaign: CampaignId,
) -> Result<Option<(PendingArchiveReceipt, ArchiveKnowledge)>, SemanticArchiveError> {
    let _timing = Timing::start(Stage::ArchiveReceiptCapture, 0);
    let mut tx = client
        .build_transaction()
        .isolation_level(IsolationLevel::Serializable)
        .read_only(true)
        .start()
        .map_err(|error| archive::database("begin ordered Archive input capture", &error))?;
    crate::current_schema::require_current_schema(&mut tx)
        .map_err(SemanticArchiveError::CurrentSchema)?;
    let captured = publication::next_receipt(&mut tx, campaign)?
        .map(|receipt| -> Result<_, SemanticArchiveError> {
            let scope = ArchiveReadScope::committed(
                campaign,
                receipt.resolve_tick(),
                *receipt.tick_content_hash(),
            )?;
            let known = tick_knowledge::capture(&mut tx, &scope)?;
            Ok((receipt, known))
        })
        .transpose()?;
    tx.commit()
        .map_err(|error| archive::database("finish ordered Archive input capture", &error))?;
    Ok(captured)
}

pub(in crate::archive_revision) fn read_progress(
    client: &mut Client,
    campaign: CampaignId,
    dispositions: Vec<(u64, ArchiveReceiptDisposition)>,
) -> Result<ArchiveWorkerSweepReport, SemanticArchiveError> {
    let mut tx = client
        .build_transaction()
        .isolation_level(IsolationLevel::RepeatableRead)
        .start()
        .map_err(|error| archive::database("begin coherent Archive progress", &error))?;
    // Admit pending receipt identities in this same committed snapshot.
    let pending = publication::next_receipt(&mut tx, campaign)?.is_some();
    let row = tx
        .query_one(
            "SELECT durable_tick,processed_tick \
        FROM public.v_archive_verification_v1 WHERE campaign_id=$1",
            &[campaign.as_uuid()],
        )
        .map_err(|error| archive::database("read ordered Archive maintenance progress", &error))?;
    let durable = super::super::storage::unsigned(archive::decode(&row, 0)?)?;
    let processed = super::super::storage::unsigned(archive::decode(&row, 1)?)?;
    if processed > durable {
        return Err(SemanticArchiveError::StoredPageMismatch);
    }
    let report = ArchiveWorkerSweepReport::new(dispositions, durable, processed, pending);
    tx.commit()
        .map_err(|error| archive::database("finish coherent Archive progress", &error))?;
    Ok(report)
}
