//! Recover prior carry from a marker-bound checkpoint, or replay canonical periods on a cache miss.
use super::labor_facts::LaborFacts;
use super::{labor_replay, storage, JournalError, JournalPeriodSource};
use crate::identity::CampaignId;
use crate::observer_reader::{
    ObserverEconomyError, ObserverEconomyReader, ObserverMaterialCursor, ObserverVisibility,
};
use crate::recorded_labor::RecordedLaborCheckpoint;
use babylon_tick::material_replay::IdentifiedMaterialTick;
use postgres::Row;

pub(super) struct LaborPublication {
    pub facts: LaborFacts,
    pub checkpoint: RecordedLaborCheckpoint,
}

pub(super) struct LaborSeed {
    pub period: u64,
    pub foundation: [u8; 32],
    pub world: [u8; 32],
    pub bytes: Vec<u8>,
    pub sha256: [u8; 32],
}

fn digest(row: &Row, key: &str) -> Result<[u8; 32], JournalError> {
    row.try_get::<_, Vec<u8>>(key)
        .map_err(|_| JournalError::Projection)?
        .try_into()
        .map_err(|_| JournalError::Projection)
}

/// Only the latest retained cache strictly before the requested period can seed its opening.
pub(super) fn previous_checkpoint(
    observer: &ObserverEconomyReader,
    campaign: CampaignId,
    before: u64,
) -> Result<Option<LaborSeed>, JournalError> {
    if observer.visibility() != ObserverVisibility::FullObserver {
        return Err(JournalError::Authority);
    }
    if before <= 1 {
        return Ok(None);
    }
    let mut client = storage::open_observer(observer)?;
    let mut upper = i64::try_from(before).map_err(|_| JournalError::Range)?;
    loop {
        let row = client.query_opt("SELECT c.resolve_tick,c.checkpoint_bytes,c.sha256,c.foundation_sha256,c.tick_content_hash,c.receipt_sha256,c.result_world_hash,p.source_identity_bytes FROM public.v_observer_labor_checkpoint_v1 c JOIN public.v_observer_money_journal_period_v1 p USING(campaign_id,resolve_tick) WHERE c.campaign_id=$1 AND c.resolve_tick<$2 ORDER BY c.resolve_tick DESC LIMIT 1", &[campaign.as_uuid(),&upper]).map_err(|_|JournalError::Database)?;
        let Some(row) = row else { return Ok(None) };
        let identity = IdentifiedMaterialTick::decode(
            &row.try_get::<_, Vec<u8>>("source_identity_bytes")
                .map_err(|_| JournalError::Projection)?,
        )
        .map_err(|_| JournalError::Projection)?;
        upper = row
            .try_get("resolve_tick")
            .map_err(|_| JournalError::Projection)?;
        let period = u64::try_from(upper).map_err(|_| JournalError::Range)?;
        // Both the canonical identity bytes and these coordinates are pinned by the journal view.
        if identity.resolve_tick() != period
            || identity.foundation_digest() != digest(&row, "foundation_sha256")?
            || *identity.tick_content_hash().as_bytes() != digest(&row, "tick_content_hash")?
        {
            return Err(JournalError::SourceChanged);
        }
        // These two fields are derived marker data. A damaged marker disqualifies this seed.
        if identity.receipt_digest() != digest(&row, "receipt_sha256")?
            || identity.result_world_hash() != digest(&row, "result_world_hash")?
        {
            continue;
        }
        return Ok(Some(LaborSeed {
            period,
            foundation: identity.foundation_digest(),
            world: identity.result_world_hash(),
            bytes: row
                .try_get("checkpoint_bytes")
                .map_err(|_| JournalError::Projection)?,
            sha256: digest(&row, "sha256")?,
        }));
    }
}

pub(super) fn period(
    observer: &ObserverEconomyReader,
    campaign: CampaignId,
    target: u64,
    cursor: &mut Option<ObserverMaterialCursor>,
) -> Result<(JournalPeriodSource, LaborPublication), JournalError> {
    labor_replay::through(
        observer,
        campaign,
        target,
        cursor,
        None,
        |at, foundation, source, report, ledger| {
            let facts = LaborFacts::from_report(foundation, &report)
                .map_err(|_| ObserverEconomyError::InvalidProjection)?;
            let checkpoint = ledger
                .checkpoint()
                .map_err(ObserverEconomyError::RecordedLabor)?;
            Ok((
                at.journal_period(foundation, source)?,
                LaborPublication { facts, checkpoint },
            ))
        },
    )
    .map(|(_, publication)| publication)
    .map_err(JournalError::Observer)
}
