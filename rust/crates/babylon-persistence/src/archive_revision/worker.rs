//! Bounded ordered receipt draining followed by exact adoption validation.

use super::{
    publication::{self, Work},
    tick_knowledge,
};
use crate::archive::{database, decode};
use crate::{
    ArchiveDossierProducerV1, ArchiveMaterializeDispositionV1, ArchiveMaterializeModeV1,
    ArchiveReceiptDispositionV1, ArchiveWorkerSweepReportV1, CampaignId, SemanticArchiveErrorV1,
    SemanticArchiveStoreV1,
};
use postgres::{Client, IsolationLevel};

pub(crate) fn sweep(
    store: &SemanticArchiveStoreV1,
    campaign: CampaignId,
    producer: &dyn ArchiveDossierProducerV1,
) -> Result<ArchiveWorkerSweepReportV1, SemanticArchiveErrorV1> {
    let mut client = store.connect("connect ordered Archive worker")?;
    publication::with_campaign_lock(&mut client, campaign, |client| {
        sweep_locked(client, campaign, producer)
    })
}

fn sweep_locked(
    client: &mut Client,
    campaign: CampaignId,
    producer: &dyn ArchiveDossierProducerV1,
) -> Result<ArchiveWorkerSweepReportV1, SemanticArchiveErrorV1> {
    let mut dispositions = Vec::new();
    for _ in 0..crate::ARCHIVE_SWEEP_MAX_RECEIPTS_V1 {
        let mut tx = client
            .build_transaction()
            .isolation_level(IsolationLevel::Serializable)
            .start()
            .map_err(|error| database("begin ordered Archive producer transaction", &error))?;
        let Some(work) = publication::next_work(&mut tx, campaign)? else {
            break;
        };
        let known = tick_knowledge::pin(&mut tx, &work.scope(campaign)?)?;
        let outcome = producer.produce(
            *campaign.as_uuid(),
            work.receipt(),
            &known,
            crate::ArchiveDirtyBatchV1::MAX_PAGES,
        )?;
        let coverage = if matches!(work, Work::Cutover(_)) {
            Some(producer.cutover_subjects(*campaign.as_uuid(), work.receipt(), &known)?)
        } else {
            None
        };
        let mode = if outcome.remaining() == 0 {
            ArchiveMaterializeModeV1::Consume
        } else {
            ArchiveMaterializeModeV1::Stage
        };
        let report = publication::publish(
            &mut tx,
            campaign,
            &work,
            outcome.batch(),
            mode,
            &known,
            coverage.as_deref(),
        )?;
        tx.commit()
            .map_err(|error| database("commit ordered Archive producer transaction", &error))?;
        if let Work::Receipt(receipt) = work {
            let disposition = match (mode, report.disposition()) {
                (_, ArchiveMaterializeDispositionV1::AlreadyConsumed) => {
                    ArchiveReceiptDispositionV1::AlreadyConsumed
                }
                (ArchiveMaterializeModeV1::Stage, _) => ArchiveReceiptDispositionV1::Paged,
                (ArchiveMaterializeModeV1::Consume, _) => ArchiveReceiptDispositionV1::Applied,
            };
            dispositions.push((receipt.resolve_tick(), disposition));
        }
        // Never evaluate a later quiet receipt against an incomplete earlier head.
        if mode == ArchiveMaterializeModeV1::Stage {
            break;
        }
    }
    let row=client.query_one("SELECT COALESCE((SELECT processed_tick FROM public.v_archive_verification_v1 WHERE campaign_id=$1),0), \
        sealed FROM public.v_archive_retention_v2 WHERE campaign_id=$1",&[campaign.as_uuid()])
        .map_err(|error|database("read ordered Archive maintenance progress",&error))?;
    Ok(ArchiveWorkerSweepReportV1::new(
        dispositions,
        super::storage::unsigned(decode(&row, 0)?)?,
        decode(&row, 1)?,
    ))
}
