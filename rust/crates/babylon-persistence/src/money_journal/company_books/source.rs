//! The nearest authenticated prior basis seeds ordinary sequential publication.
use crate::company_statements::{CompanyBooks, CompanyPeriod};
use crate::economic_content::EconomicContentAdmission;
use crate::identity::CampaignId;
use crate::money_journal::{storage, JournalError};
use crate::observer_reader::{
    CommittedMaterialReceipts, ObserverEconomyError, ObserverEconomyReader, ObserverMaterialCursor,
};
use babylon_tick::material_replay::IdentifiedMaterialTick;
use postgres::Row;

pub(in crate::money_journal) struct CompanyPublication {
    pub(super) companies: Vec<CompanyPeriod>,
    pub(super) checkpoint: Vec<u8>,
    pub(super) checkpoint_sha256: [u8; 32],
}
struct Seed {
    tick: u64,
    world: [u8; 32],
    bytes: Vec<u8>,
    sha256: [u8; 32],
}
pub(super) fn digest(row: &Row, name: &str) -> Result<[u8; 32], JournalError> {
    row.try_get::<_, &[u8]>(name)
        .map_err(|_| JournalError::Projection)?
        .try_into()
        .map_err(|_| JournalError::Projection)
}
pub(super) fn identity(row: &Row) -> Result<IdentifiedMaterialTick, JournalError> {
    let id = IdentifiedMaterialTick::decode(
        row.try_get("source_identity_bytes")
            .map_err(|_| JournalError::Projection)?,
    )
    .map_err(|_| JournalError::SourceChanged)?;
    let period: i64 = row
        .try_get("resolve_tick")
        .map_err(|_| JournalError::Projection)?;
    if id.foundation_digest() != digest(row, "foundation_sha256")?
        || *id.tick_content_hash().as_bytes() != digest(row, "tick_content_hash")?
        || id.receipt_digest() != digest(row, "receipt_sha256")?
        || u64::try_from(period).ok() != Some(id.resolve_tick())
    {
        return Err(JournalError::SourceChanged);
    }
    Ok(id)
}
const PRIOR_CHECKPOINT: &str = "
    SELECT * FROM public.v_observer_company_accounting_checkpoint_v1
    WHERE campaign_id = $1 AND resolve_tick < $2
    ORDER BY resolve_tick DESC LIMIT 1";

fn seed(
    observer: &ObserverEconomyReader,
    campaign: CampaignId,
    before: u64,
) -> Result<Option<Seed>, JournalError> {
    if before <= 1 {
        return Ok(None);
    }
    let mut client = storage::open_observer(observer)?;
    let mut upper = i64::try_from(before).map_err(|_| JournalError::Range)?;
    loop {
        let candidate = client
            .query_opt(PRIOR_CHECKPOINT, &[campaign.as_uuid(), &upper])
            .map_err(|_| JournalError::Database)?;
        let Some(row) = candidate else {
            return Ok(None);
        };
        let id = identity(&row)?;
        upper = i64::try_from(id.resolve_tick()).map_err(|_| JournalError::Range)?;
        if digest(&row, "result_world_hash")? != id.result_world_hash() {
            continue;
        }
        return Ok(Some(Seed {
            tick: id.resolve_tick(),
            world: id.result_world_hash(),
            sha256: digest(&row, "checkpoint_sha256")?,
            bytes: row
                .try_get("checkpoint_bytes")
                .map_err(|_| JournalError::Projection)?,
        }));
    }
}
impl CompanyPublication {
    pub(in crate::money_journal) fn derive(
        observer: &ObserverEconomyReader,
        at: &ObserverMaterialCursor,
        foundation: &EconomicContentAdmission,
        source: &CommittedMaterialReceipts,
    ) -> Result<Option<Self>, JournalError> {
        if foundation.material_catalog().company_payouts.is_empty() {
            return Ok(None);
        }
        let capture = foundation
            .foundation()
            .graph_foundation()
            .content_bundle()
            .economic_catalog()
            .ok_or(JournalError::Projection)?;
        if capture.national_companies().is_none() {
            return Err(JournalError::Projection);
        }
        let campaign = source.campaign_id;
        let target = source.identity.resolve_tick();
        let digest = foundation.digest();
        let mut upper = target;
        loop {
            let candidate = seed(observer, campaign, upper)?;
            let mut books = if candidate.is_some() {
                CompanyBooks::for_checkpoint(capture)
            } else {
                CompanyBooks::open(capture, foundation.initial_register().state())
            }
            .map_err(|_| JournalError::Projection)?;
            let mut start = 1;
            let mut prior = None;
            if let Some(seed) = candidate {
                if books
                    .restore(
                        campaign,
                        digest,
                        seed.world,
                        seed.tick + 1,
                        &seed.bytes,
                        seed.sha256,
                    )
                    .is_err()
                {
                    upper = seed.tick;
                    continue;
                }
                start = seed.tick + 1;
                prior = Some(seed.world);
            }
            let mut cursor = None;
            for tick in start..target {
                prior = Some(
                    observer
                        .with_committed_receipts(campaign, tick, &mut cursor, |c, f, r| {
                            if f.digest() != digest
                                || prior.is_some_and(|v| v != r.identity.prior_world_hash())
                            {
                                return Err(ObserverEconomyError::InvalidProjection);
                            }
                            let before = c.labor_opening(f)?.state();
                            let after = c
                                .current_register()
                                .ok_or(ObserverEconomyError::InvalidProjection)?
                                .state();
                            books
                                .replay_earlier(before, after, &r.receipts)
                                .map_err(|_| ObserverEconomyError::InvalidProjection)?;
                            Ok(r.identity.result_world_hash())
                        })
                        .map_err(JournalError::Observer)?,
                );
            }
            if prior.is_some_and(|v| v != source.identity.prior_world_hash()) {
                return Err(JournalError::SourceChanged);
            }
            let before = at
                .labor_opening(foundation)
                .map_err(JournalError::Observer)?
                .state();
            let after = at
                .current_register()
                .ok_or(JournalError::Projection)?
                .state();
            let companies = books
                .close(before, after, &source.receipts)
                .map_err(|_| JournalError::Projection)?;
            let (checkpoint, checkpoint_sha256) = books
                .checkpoint(campaign, digest, source.identity.result_world_hash())
                .map_err(|_| JournalError::Projection)?;
            return Ok(Some(Self {
                companies,
                checkpoint,
                checkpoint_sha256,
            }));
        }
    }
}
