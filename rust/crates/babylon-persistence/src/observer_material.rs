//! Separate full-observer material capability and exact historical projection.

use babylon_kernel::content_digest::sha256_of;
use babylon_tick::{
    material_replay::IdentifiedMaterialTick,
    material_world::{
        decode_material_receipts, nominal_material_world_hash, MaterialTickReceipts,
        MaterialWorldRegister,
    },
};
use postgres::GenericClient;
use std::sync::Arc;

use crate::{
    identity::CampaignId,
    material_runtime::read_observer_material_tick,
    michigan_content::{
        admit_michigan_content, validate_michigan_header, MichiganContentAdmission,
        MichiganPhysicalProjection,
    },
    michigan_economy::digest_hex,
    observer_reader::{
        ObserverEconomyError, ObserverVisibility, ProductionHistoryTarget, ProductionOutputPoint,
    },
    production_observation::ProductionSnapshot,
    production_projection::{history::OrderHistory, project_material_current, project_process},
};

pub(crate) struct MaterialObservation {
    pub(crate) foundation_digest: String,
    pub(crate) production: Option<ProductionSnapshot>,
    pub(crate) nominal_world_hash: Option<String>,
}

#[derive(Clone)]
struct MaterialObservationRow {
    row_campaign: uuid::Uuid,
    row_tick: i64,
    register_bytes: Vec<u8>,
    receipts: Option<Vec<u8>>,
    identity: Option<Vec<u8>>,
    content_hash: Option<Vec<u8>>,
    foundation_bytes: Option<Vec<u8>>,
}

fn decode_material_row(row: &postgres::Row) -> Result<MaterialObservationRow, postgres::Error> {
    Ok(MaterialObservationRow {
        row_campaign: row.try_get(0)?,
        row_tick: row.try_get(1)?,
        register_bytes: row.try_get(2)?,
        receipts: row.try_get(3)?,
        identity: row.try_get(4)?,
        content_hash: row.try_get(5)?,
        foundation_bytes: row.try_get(6)?,
    })
}

pub(crate) struct MaterialHeader {
    pub(crate) foundation_digest: Vec<u8>,
    pub(crate) admission: Option<Arc<MichiganContentAdmission>>,
}

pub(crate) fn read_material_header(
    transaction: &mut impl GenericClient,
    campaign: CampaignId,
    tick: u64,
    visibility: ObserverVisibility,
    cached: Option<&ObserverMaterialCursor>,
) -> Result<Option<MaterialHeader>, ObserverEconomyError> {
    let header = transaction.query_opt("SELECT campaign_id, preset_id, duration_kind, final_period, content_sha256, foundation_sha256 FROM public.v_material_campaign_identity_v2 WHERE campaign_id=$1", &[campaign.as_uuid()]).map_err(|_| ObserverEconomyError::Database)?;
    let Some(header) = header else {
        return Ok(None);
    };
    let row_campaign: uuid::Uuid = header
        .try_get(0)
        .map_err(|_| ObserverEconomyError::InvalidProjection)?;
    let preset_id: String = header
        .try_get(1)
        .map_err(|_| ObserverEconomyError::InvalidProjection)?;
    let duration = crate::material_runtime::read_duration(&header)
        .map_err(|_| ObserverEconomyError::InvalidProjection)?;
    let content: Vec<u8> = header
        .try_get("content_sha256")
        .map_err(|_| ObserverEconomyError::InvalidProjection)?;
    let foundation_digest: Vec<u8> = header
        .try_get("foundation_sha256")
        .map_err(|_| ObserverEconomyError::InvalidProjection)?;
    validate_michigan_header(&preset_id, duration, &content, &foundation_digest, tick)
        .map_err(|_| ObserverEconomyError::ScenarioMismatch)?;
    if &row_campaign != campaign.as_uuid() {
        return Err(ObserverEconomyError::ScenarioMismatch);
    }
    let admission = if visibility == ObserverVisibility::FullObserver {
        if let Some(cached) = cached.filter(|cursor| {
            cursor.campaign == campaign
                && cursor.admission.preset.id() == preset_id
                && cursor.admission.digest.as_slice() == foundation_digest.as_slice()
        }) {
            cached
                .admission
                .validate_header(duration, &content, &foundation_digest, tick)
                .map_err(|_| ObserverEconomyError::ScenarioMismatch)?;
            Some(Arc::clone(&cached.admission))
        } else {
            let row = transaction.query_opt("SELECT foundation_bytes FROM public.v_observer_material_state_v1 WHERE campaign_id=$1 AND resolve_tick=0", &[campaign.as_uuid()])
            .map_err(|_| ObserverEconomyError::Database)?.ok_or(ObserverEconomyError::ScenarioMismatch)?;
            let bytes: Vec<u8> = row
                .try_get(0)
                .map_err(|_| ObserverEconomyError::InvalidProjection)?;
            Some(Arc::new(
                admit_michigan_content(
                    &preset_id,
                    duration,
                    &content,
                    &foundation_digest,
                    tick,
                    &bytes,
                )
                .map_err(|_| ObserverEconomyError::ScenarioMismatch)?,
            ))
        }
    } else {
        // Public header shape is valid. Config, seed quantities and material
        // identities remain opaque to this capability; no independent admission
        // of those hidden values is claimed.
        None
    };
    Ok(Some(MaterialHeader {
        foundation_digest,
        admission,
    }))
}

/// Authenticated, bounded read cache. It cannot supply simulation inputs.
#[derive(Clone)]
pub struct ObserverMaterialCursor {
    campaign: CampaignId,
    admission: Arc<MichiganContentAdmission>,
    history: MaterialHistory,
}
impl ObserverMaterialCursor {
    #[must_use]
    pub fn completed_tick(&self) -> u64 {
        self.history.register.completed_tick()
    }
}

#[derive(Clone)]
struct MaterialHistory {
    register: MaterialWorldRegister,
    opening: Option<MaterialWorldRegister>,
    receipt: Option<(MaterialTickReceipts, [u8; 32])>,
    orders: OrderHistory,
    prior_world: Option<[u8; 32]>,
}

impl MaterialHistory {
    fn new(expected: &MichiganContentAdmission) -> Result<Self, ObserverEconomyError> {
        Ok(Self {
            register: expected.register.clone(),
            opening: None,
            receipt: None,
            orders: OrderHistory::from_catalog(&expected.catalog)
                .map_err(|_| ObserverEconomyError::InvalidProjection)?,
            prior_world: None,
        })
    }

    fn append(
        &mut self,
        campaign: CampaignId,
        expected: &MichiganContentAdmission,
        index: u64,
        row: &postgres::Row,
    ) -> Result<(), ObserverEconomyError> {
        let row = decode_material_row(row).map_err(|_| ObserverEconomyError::InvalidProjection)?;
        self.append_decoded(campaign, expected, index, row)
    }

    fn append_decoded(
        &mut self,
        campaign: CampaignId,
        expected: &MichiganContentAdmission,
        index: u64,
        row: MaterialObservationRow,
    ) -> Result<(), ObserverEconomyError> {
        if (index > 0 && self.register.completed_tick().checked_add(1) != Some(index))
            || (index == 0 && self.register.completed_tick() != 0)
        {
            return Err(ObserverEconomyError::InvalidProjection);
        }
        let MaterialObservationRow {
            row_campaign,
            row_tick,
            register_bytes,
            receipts,
            identity,
            content_hash,
            foundation_bytes,
        } = row;
        if &row_campaign != campaign.as_uuid() || u64::try_from(row_tick).ok() != Some(index) {
            return Err(ObserverEconomyError::InvalidProjection);
        }
        let next = MaterialWorldRegister::decode(&register_bytes)
            .map_err(|_| ObserverEconomyError::InvalidProjection)?;
        if next.completed_tick() != index {
            return Err(ObserverEconomyError::InvalidProjection);
        }
        if index == 0 {
            if foundation_bytes.as_deref() != Some(expected.canonical_bytes.as_slice())
                || next != expected.register
                || receipts.is_some()
                || identity.is_some()
                || content_hash.is_some()
            {
                return Err(ObserverEconomyError::ScenarioMismatch);
            }
        } else {
            if foundation_bytes.is_some() {
                return Err(ObserverEconomyError::InvalidProjection);
            }
            self.append_receipt(
                expected,
                &next,
                identity
                    .as_deref()
                    .ok_or(ObserverEconomyError::InvalidProjection)?,
                receipts
                    .as_deref()
                    .ok_or(ObserverEconomyError::InvalidProjection)?,
                content_hash.as_deref(),
            )?;
        }
        let previous = std::mem::replace(&mut self.register, next);
        if index > 0 {
            self.opening = Some(previous);
        }
        Ok(())
    }

    fn append_receipt(
        &mut self,
        expected: &MichiganContentAdmission,
        next: &MaterialWorldRegister,
        identity: &[u8],
        receipt_bytes: &[u8],
        content_hash: Option<&[u8]>,
    ) -> Result<(), ObserverEconomyError> {
        let index = next.completed_tick();
        let identity = IdentifiedMaterialTick::decode(identity)
            .map_err(|_| ObserverEconomyError::InvalidProjection)?;
        if identity.resolve_tick() != index
            || identity.foundation_digest() != expected.digest
            || content_hash != Some(identity.tick_content_hash().as_bytes().as_slice())
            || sha256_of(receipt_bytes) != identity.receipt_digest()
            || nominal_material_world_hash(identity.graph_world_after(), next)
                != identity.result_world_hash()
            || nominal_material_world_hash(identity.graph_world_before(), &self.register)
                != identity.prior_world_hash()
            || self
                .prior_world
                .is_some_and(|prior| prior != identity.prior_world_hash())
        {
            return Err(ObserverEconomyError::InvalidProjection);
        }
        let receipt = decode_material_receipts(receipt_bytes)
            .map_err(|_| ObserverEconomyError::InvalidProjection)?;
        if receipt.resolve_tick != identity.resolve_tick() {
            return Err(ObserverEconomyError::InvalidProjection);
        }
        let period_orders = crate::production_projection::lifecycle::validate_period(
            self.register.state(),
            next.state(),
            &receipt,
        )
        .map_err(|_| ObserverEconomyError::InvalidProjection)?;
        self.orders
            .record(self.register.state(), &period_orders)
            .map_err(|_| ObserverEconomyError::InvalidProjection)?;
        self.receipt = Some((receipt, identity.receipt_digest()));
        self.prior_world = Some(identity.result_world_hash());
        Ok(())
    }
}

const MATERIAL_PAGE_ROWS: u64 = 4;

fn material_rows(
    transaction: &mut impl GenericClient,
    campaign: CampaignId,
    start: u64,
    through: u64,
) -> Result<Vec<postgres::Row>, ObserverEconomyError> {
    let start_sql = i64::try_from(start).map_err(|_| ObserverEconomyError::TickAbsent)?;
    let through_sql = i64::try_from(through).map_err(|_| ObserverEconomyError::TickAbsent)?;
    let rows = transaction.query("SELECT campaign_id, resolve_tick, register_bytes, receipt_bytes, identity_bytes, tick_content_hash, foundation_bytes FROM public.v_observer_material_state_v1 WHERE campaign_id=$1 AND resolve_tick >= $2 AND resolve_tick <= $3 ORDER BY resolve_tick LIMIT 4", &[campaign.as_uuid(), &start_sql, &through_sql]).map_err(|_| ObserverEconomyError::Database)?;
    let expected = through
        .checked_sub(start)
        .and_then(|n| n.checked_add(1))
        .ok_or(ObserverEconomyError::TickAbsent)?
        .min(MATERIAL_PAGE_ROWS);
    if u64::try_from(rows.len()).ok() != Some(expected) {
        return Err(ObserverEconomyError::TickAbsent);
    }
    Ok(rows)
}

fn extend_history(
    transaction: &mut impl GenericClient,
    campaign: CampaignId,
    expected: &MichiganContentAdmission,
    history: &mut MaterialHistory,
    mut start: u64,
    through: u64,
) -> Result<(), ObserverEconomyError> {
    while start <= through {
        for row in material_rows(transaction, campaign, start, through)? {
            history.append(campaign, expected, start, &row)?;
            start = start
                .checked_add(1)
                .ok_or(ObserverEconomyError::TickAbsent)?;
        }
    }
    Ok(())
}

/// Header reads are safe for preview. Complete material reads are never issued for preview.
pub(crate) fn material_observation(
    transaction: &mut impl GenericClient,
    campaign: CampaignId,
    tick: u64,
    visibility: ObserverVisibility,
    expected: &Arc<MichiganContentAdmission>,
    cursor: &mut Option<ObserverMaterialCursor>,
) -> Result<MaterialObservation, ObserverEconomyError> {
    if visibility == ObserverVisibility::KnownPreview {
        return Ok(MaterialObservation {
            foundation_digest: digest_hex(&expected.digest),
            production: None,
            nominal_world_hash: None,
        });
    }
    let reuse = cursor.as_ref().is_some_and(|c| {
        c.campaign == campaign
            && c.admission.digest == expected.digest
            && c.completed_tick() <= tick
    });
    let (mut history, start) = if reuse {
        // The outer reader already owns a detached candidate until transaction commit.
        let cached = cursor
            .take()
            .ok_or(ObserverEconomyError::InvalidProjection)?;
        let start = cached
            .completed_tick()
            .checked_add(1)
            .ok_or(ObserverEconomyError::TickAbsent)?;
        (cached.history, start)
    } else {
        (MaterialHistory::new(expected)?, 0)
    };
    extend_history(transaction, campaign, expected, &mut history, start, tick)?;
    let MichiganPhysicalProjection::Normalized = expected.physical_projection;
    let mut production = project_material_current(
        &expected.catalog,
        expected.preset.delivery(),
        &history.register,
        history.opening.as_ref(),
        history.receipt.as_ref(),
        &history.orders,
    )
    .map_err(|_| ObserverEconomyError::InvalidProjection)?;
    production.staffing_accounts = authenticated_staffing(
        transaction,
        campaign,
        expected,
        &history.register,
        history.opening.as_ref(),
        history.prior_world,
        history.receipt.as_ref(),
    )?;
    let prior_world = history.prior_world;
    if cursor.as_ref().is_none_or(|cached| {
        cached.campaign != campaign
            || cached.admission.digest != expected.digest
            || cached.completed_tick() <= tick
    }) {
        *cursor = Some(ObserverMaterialCursor {
            campaign,
            admission: Arc::clone(expected),
            history,
        });
    }
    Ok(MaterialObservation {
        foundation_digest: digest_hex(&expected.digest),
        production: Some(attribute_production(production, expected, visibility)?),
        nominal_world_hash: prior_world.map(|hash| digest_hex(&hash)),
    })
}

pub(crate) fn production_history(
    transaction: &mut impl GenericClient,
    campaign: CampaignId,
    tick: u64,
    target: &ProductionHistoryTarget,
    expected: &MichiganContentAdmission,
) -> Result<Vec<ProductionOutputPoint>, ObserverEconomyError> {
    let process = expected
        .catalog
        .processes()
        .iter()
        .find(|process| {
            digest_hex(&process.id().as_bytes()) == target.process_id
                && digest_hex(&process.site_id().as_bytes()) == target.site_id
        })
        .ok_or(ObserverEconomyError::ProductionHistoryUnavailable)?;
    let start = tick.saturating_sub(babylon_kernel::clock::TICKS_PER_YEAR - 1);
    let mut history = MaterialHistory::new(expected)?;
    let mut points = Vec::new();
    let mut index = 0;
    while index <= tick {
        for row in material_rows(transaction, campaign, index, tick)? {
            history.append(campaign, expected, index, &row)?;
            index = index
                .checked_add(1)
                .ok_or(ObserverEconomyError::TickAbsent)?;
            let period = history.register.completed_tick();
            if period > 0 {
                // Authenticate the whole prefix once, even outside the display window.
                // The shared history append also proves nominal before/after identity
                // and continuity, which the envelope reader alone does not establish.
                let stored = read_observer_material_tick(
                    transaction,
                    campaign,
                    period,
                    expected.foundation_graph.scenario_scope(),
                    expected.digest,
                    &expected.component_identity,
                )
                .map_err(|_| ObserverEconomyError::InvalidProjection)?;
                if stored.register != history.register
                    || Some(stored.identity.result_world_hash()) != history.prior_world
                {
                    return Err(ObserverEconomyError::InvalidProjection);
                }
            }
            let projected = project_process(
                &expected.catalog,
                history.register.state(),
                process,
                history.receipt.as_ref().map(|(receipt, _)| receipt),
            )
            .map_err(|_| ObserverEconomyError::InvalidProjection)?;
            if projected.output_good_id != target.output_good_id
                || projected.output_unit_id != target.output_unit_id
            {
                return Err(ObserverEconomyError::ProductionHistoryUnavailable);
            }
            if period >= start {
                points.push(ProductionOutputPoint::from_process(period, &projected)?);
            }
        }
    }
    Ok(points)
}

fn authenticated_staffing(
    transaction: &mut impl GenericClient,
    campaign: CampaignId,
    expected: &MichiganContentAdmission,
    register: &MaterialWorldRegister,
    opening: Option<&MaterialWorldRegister>,
    result_world: Option<[u8; 32]>,
    period_receipt: Option<&(MaterialTickReceipts, [u8; 32])>,
) -> Result<Vec<crate::production_observation::ProductionStaffingAccount>, ObserverEconomyError> {
    use crate::production_projection::staffing::project_staffing_accounts;
    let tick = register.completed_tick();
    if tick == 0 {
        return project_staffing_accounts(
            &expected.staffing,
            &expected.foundation_graph,
            register,
            None,
            &[],
            None,
        )
        .map_err(|_| ObserverEconomyError::InvalidProjection);
    }
    let mut read = |tick| {
        read_observer_material_tick(
            transaction,
            campaign,
            tick,
            expected.foundation_graph.scenario_scope(),
            expected.digest,
            &expected.component_identity,
        )
        .map_err(|_| ObserverEconomyError::InvalidProjection)
    };
    let current = read(tick)?;
    if current.register != *register
        || Some(current.identity.result_world_hash()) != result_world
        || Some(current.identity.receipt_digest()) != period_receipt.map(|(_, digest)| *digest)
    {
        return Err(ObserverEconomyError::InvalidProjection);
    }
    let previous = if tick > 1 {
        Some(read(tick - 1)?)
    } else {
        None
    };
    let (prior_graph, prior_register) = if let Some(previous) = &previous {
        if previous.identity.result_world_hash() != current.identity.prior_world_hash() {
            return Err(ObserverEconomyError::InvalidProjection);
        }
        (&previous.graph, &previous.register)
    } else {
        (&expected.foundation_graph, &expected.register)
    };
    if Some(prior_register) != opening {
        return Err(ObserverEconomyError::InvalidProjection);
    }
    project_staffing_accounts(
        &expected.staffing,
        &current.graph,
        register,
        Some(prior_graph),
        &current.events,
        period_receipt.map(|(rows, _)| rows),
    )
    .map_err(|_| ObserverEconomyError::InvalidProjection)
}

fn attribute_production(
    mut production: ProductionSnapshot,
    expected: &MichiganContentAdmission,
    visibility: ObserverVisibility,
) -> Result<ProductionSnapshot, ObserverEconomyError> {
    expected
        .preset
        .label()
        .clone_into(&mut production.scenario_label);
    crate::production_projection::context::attach_observed_context(
        expected,
        visibility,
        &mut production,
    )
    .map_err(|_| ObserverEconomyError::InvalidProjection)?;
    Ok(production)
}

#[cfg(test)]
mod tests;
