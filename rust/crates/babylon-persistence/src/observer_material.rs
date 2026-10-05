//! Separate full-observer material capability and exact historical projection.

use crate::production_projection::diagnostics::{self, Stage};
use babylon_kernel::content_digest::sha256_of;
use babylon_tick::{
    material_replay::IdentifiedMaterialTick,
    material_world::{nominal_material_world_hash, MaterialTickReceipts, MaterialWorldRegister},
};
use postgres::GenericClient;
use std::sync::Arc;

use crate::{
    economic_content::{validate_economic_header, EconomicContentAdmission},
    identity::CampaignId,
    material_runtime::{
        capture_material_foundation_components, read_observer_material_tick, FoundationReadSource,
    },
    michigan_economy::digest_hex,
    observer_reader::{
        ObserverEconomyError, ObserverVisibility, ProductionHistoryTarget, ProductionOutputPoint,
    },
    production_observation::ProductionSnapshot,
    production_projection::{
        history::OrderHistory,
        metadata::Metadata,
        project_economic_current,
        sites::{project_process, Quantities},
    },
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
    register_storage_bytes: Vec<u8>,
    lookup_delta: Option<Vec<u8>>,
    receipts: Option<Vec<u8>>,
    identity: Option<Vec<u8>>,
    content_hash: Option<Vec<u8>>,
}

fn decode_material_row(row: &postgres::Row) -> Result<MaterialObservationRow, postgres::Error> {
    Ok(MaterialObservationRow {
        row_campaign: row.try_get(0)?,
        row_tick: row.try_get(1)?,
        register_storage_bytes: row.try_get(2)?,
        lookup_delta: row.try_get(6)?,
        receipts: row.try_get(3)?,
        identity: row.try_get(4)?,
        content_hash: row.try_get(5)?,
    })
}

pub(crate) struct MaterialHeader {
    pub(crate) foundation_digest: Vec<u8>,
    pub(crate) admission: Option<Arc<EconomicContentAdmission>>,
}

pub(crate) fn read_material_header(
    transaction: &mut impl GenericClient,
    campaign: CampaignId,
    tick: u64,
    visibility: ObserverVisibility,
    cached: Option<&Arc<EconomicContentAdmission>>,
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
    validate_economic_header(&preset_id, duration, &content, &foundation_digest, tick)
        .map_err(|_| ObserverEconomyError::ScenarioMismatch)?;
    if &row_campaign != campaign.as_uuid() {
        return Err(ObserverEconomyError::ScenarioMismatch);
    }
    let admission = if visibility == ObserverVisibility::FullObserver {
        let _foundation_timing = diagnostics::Timing::start(Stage::FoundationLoad, 0);
        let expected = foundation_digest
            .as_slice()
            .try_into()
            .map_err(|_| ObserverEconomyError::InvalidProjection)?;
        let captured = capture_material_foundation_components(
            transaction,
            campaign,
            expected,
            FoundationReadSource::FullObserver,
        )
        .map_err(|_| ObserverEconomyError::ScenarioMismatch)?;
        if let Some(cached) = cached {
            cached
                .validate_header(duration, &content, &foundation_digest, tick)
                .map_err(|_| ObserverEconomyError::ScenarioMismatch)?;
            if cached.preset_id() != preset_id {
                return Err(ObserverEconomyError::ScenarioMismatch);
            }
            captured
                .validate_against(cached)
                .map_err(|_| ObserverEconomyError::ScenarioMismatch)?;
            Some(Arc::clone(cached))
        } else {
            let rebuilt = captured
                .admit()
                .map_err(|_| ObserverEconomyError::ScenarioMismatch)?;
            let economic_timing = diagnostics::Timing::start(Stage::FoundationEconomicAdmission, 0);
            let admitted = EconomicContentAdmission::from_foundation(rebuilt)
                .map_err(|_| ObserverEconomyError::ScenarioMismatch)?;
            drop(economic_timing);
            if admitted.preset_id() != preset_id {
                return Err(ObserverEconomyError::ScenarioMismatch);
            }
            admitted
                .validate_header(duration, &content, &foundation_digest, tick)
                .map_err(|_| ObserverEconomyError::ScenarioMismatch)?;
            Some(Arc::new(admitted))
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
    admission: Arc<EconomicContentAdmission>,
    history: MaterialHistory,
}
impl ObserverMaterialCursor {
    pub(crate) fn admission(&self, campaign: CampaignId) -> Option<Arc<EconomicContentAdmission>> {
        (self.campaign == campaign).then(|| Arc::clone(&self.admission))
    }
    #[must_use]
    pub fn completed_tick(&self) -> u64 {
        self.history.register.completed_tick()
    }
}

#[derive(Clone)]
struct MaterialHistory {
    lookup: crate::material_storage::OpeningRegister,
    lookup_chain: [u8; 32],
    previous_lookup_chain: Option<[u8; 32]>,
    register: MaterialRegisterBoundary,
    opening: Option<MaterialRegisterBoundary>,
    receipt: Option<(MaterialTickReceipts, [u8; 32])>,
    orders: OrderHistory,
    prior_world: Option<[u8; 32]>,
}

/// Foundation state belongs to the immutable admission. A history owns only
/// committed period registers, including the previous period needed by proofs.
#[derive(Clone, Debug, PartialEq, Eq)]
enum MaterialRegisterBoundary {
    Foundation,
    Period(Box<MaterialWorldRegister>),
}

impl MaterialRegisterBoundary {
    fn resolve<'a>(&'a self, expected: &'a EconomicContentAdmission) -> &'a MaterialWorldRegister {
        match self {
            Self::Foundation => expected.initial_register(),
            Self::Period(register) => register,
        }
    }

    fn completed_tick(&self) -> u64 {
        match self {
            Self::Foundation => 0,
            Self::Period(register) => register.completed_tick(),
        }
    }
}

impl MaterialHistory {
    fn register<'a>(&'a self, expected: &'a EconomicContentAdmission) -> &'a MaterialWorldRegister {
        self.register.resolve(expected)
    }

    fn opening<'a>(
        &'a self,
        expected: &'a EconomicContentAdmission,
    ) -> Option<&'a MaterialWorldRegister> {
        self.opening
            .as_ref()
            .map(|register| register.resolve(expected))
    }

    fn new(expected: &EconomicContentAdmission) -> Result<Self, ObserverEconomyError> {
        let lookup = expected
            .opening()
            .map_err(|_| ObserverEconomyError::InvalidProjection)?
            .clone();
        let lookup_chain = crate::material_storage::initial_lookup_chain(&lookup)
            .map_err(|_| ObserverEconomyError::InvalidProjection)?;
        Ok(Self {
            lookup,
            lookup_chain,
            previous_lookup_chain: None,
            register: MaterialRegisterBoundary::Foundation,
            opening: None,
            receipt: None,
            orders: OrderHistory::from_opening(expected.initial_register().state()).map_err(
                |error| {
                    let _ = diagnostics::projection::<()>(Stage::InitialHistory, 0, Err(error));
                    ObserverEconomyError::InvalidProjection
                },
            )?,
            prior_world: None,
        })
    }

    fn append(
        &mut self,
        campaign: CampaignId,
        expected: &EconomicContentAdmission,
        index: u64,
        row: postgres::Row,
    ) -> Result<(), ObserverEconomyError> {
        let decoded = diagnostics::observer(
            Stage::MaterialRow,
            index,
            decode_material_row(&row).map_err(|_| ObserverEconomyError::InvalidProjection),
        )?;
        // Release the driver's backing buffers before canonical admission starts.
        drop(row);
        self.append_decoded(campaign, expected, index, decoded)
    }

    fn append_decoded(
        &mut self,
        campaign: CampaignId,
        expected: &EconomicContentAdmission,
        index: u64,
        row: MaterialObservationRow,
    ) -> Result<(), ObserverEconomyError> {
        if (index > 0 && self.register.completed_tick().checked_add(1) != Some(index))
            || (index == 0 && self.register.completed_tick() != 0)
        {
            return Err(diagnostics::invalid(Stage::MaterialRow, index));
        }
        let MaterialObservationRow {
            row_campaign,
            row_tick,
            register_storage_bytes,
            lookup_delta,
            receipts,
            identity,
            content_hash,
        } = row;
        if &row_campaign != campaign.as_uuid() || u64::try_from(row_tick).ok() != Some(index) {
            return Err(diagnostics::invalid(Stage::MaterialRow, index));
        }
        if index == 0 {
            if lookup_delta.is_some()
                || receipts.is_some()
                || identity.is_some()
                || content_hash.is_some()
                || self.register(expected) != expected.initial_register()
            {
                return Err(ObserverEconomyError::ScenarioMismatch);
            }
            // The foundation reader already admitted these exact canonical bytes.
            // The view aliases the same opening column. Keep the admitted owner
            // rather than allocating and decoding a second full national register.
            if register_storage_bytes != expected.initial_register().canonical_bytes() {
                // Preserve malformed-register diagnostics on the refusal path.
                drop(
                    MaterialWorldRegister::decode(&register_storage_bytes)
                        .map_err(|_| diagnostics::invalid(Stage::RegisterDecode, index))?,
                );
                return Err(ObserverEconomyError::ScenarioMismatch);
            }
            return Ok(());
        }
        // This history is a detached read candidate, never a published cursor.
        // The next append needs only the current register, order index and hashes;
        // obsolete prior state/receipts must not overlap the next full admission.
        self.opening = None;
        self.receipt = None;
        let delta = lookup_delta
            .as_deref()
            .ok_or(ObserverEconomyError::InvalidProjection)?;
        let lookup = crate::material_storage::read_period_lookup(
            &self.lookup,
            index,
            delta,
            crate::material_storage::LookupAnchor::Previous(self.lookup_chain),
        )
        .map_err(|_| diagnostics::invalid(Stage::LookupDecode, index))?;
        let admitted = crate::material_storage::decode_typed(
            &self.lookup,
            index,
            &register_storage_bytes,
            receipts
                .as_deref()
                .ok_or(ObserverEconomyError::InvalidProjection)?,
            &lookup.lookup,
            lookup.chain,
        )
        .map_err(|_| diagnostics::invalid(Stage::StorageDecode, index))?;
        let next = admitted.register;
        if next.completed_tick() != index {
            return Err(diagnostics::invalid(Stage::RegisterDecode, index));
        }
        self.append_receipt(
            expected,
            &next,
            identity
                .as_deref()
                .ok_or(ObserverEconomyError::InvalidProjection)?,
            &admitted.receipt_bytes,
            content_hash.as_deref(),
            admitted.receipts,
        )?;
        let previous = std::mem::replace(
            &mut self.register,
            MaterialRegisterBoundary::Period(Box::new(next)),
        );
        self.previous_lookup_chain = Some(self.lookup_chain);
        self.lookup_chain = lookup.chain;
        self.opening = Some(previous);
        Ok(())
    }

    fn append_receipt(
        &mut self,
        expected: &EconomicContentAdmission,
        next: &MaterialWorldRegister,
        identity: &[u8],
        receipt_bytes: &[u8],
        content_hash: Option<&[u8]>,
        receipt: MaterialTickReceipts,
    ) -> Result<(), ObserverEconomyError> {
        let index = next.completed_tick();
        let prior_register = self.register.resolve(expected);
        let identity = IdentifiedMaterialTick::decode(identity)
            .map_err(|_| diagnostics::invalid(Stage::ReceiptIdentity, index))?;
        if identity.resolve_tick() != index
            || identity.foundation_digest() != expected.digest()
            || content_hash != Some(identity.tick_content_hash().as_bytes().as_slice())
            || sha256_of(receipt_bytes) != identity.receipt_digest()
            || nominal_material_world_hash(identity.graph_world_after(), next)
                != identity.result_world_hash()
            || nominal_material_world_hash(identity.graph_world_before(), prior_register)
                != identity.prior_world_hash()
            || self
                .prior_world
                .is_some_and(|prior| prior != identity.prior_world_hash())
        {
            return diagnostics::observer(
                Stage::ReceiptBinding,
                index,
                Err(ObserverEconomyError::InvalidProjection),
            );
        }
        if receipt.resolve_tick != identity.resolve_tick() {
            return diagnostics::observer(
                Stage::ReceiptTick,
                index,
                Err(ObserverEconomyError::InvalidProjection),
            );
        }
        let period_orders = crate::production_projection::lifecycle::validate_period(
            prior_register.state(),
            next.state(),
            &receipt,
        )
        .map_err(|error| {
            let _ = diagnostics::projection::<()>(Stage::PeriodLifecycle, index, Err(error));
            ObserverEconomyError::InvalidProjection
        })?;
        // This history belongs to the detached read candidate. The outer
        // reader publishes it only after every admission and commit succeeds.
        // A refusal discards the candidate, so a second index copy is redundant.
        let order_timing = diagnostics::Timing::start(Stage::OrderHistory, index);
        self.orders
            .record(prior_register.state(), &period_orders)
            .map_err(|error| {
                let _ = diagnostics::projection::<()>(Stage::OrderHistory, index, Err(error));
                ObserverEconomyError::InvalidProjection
            })?;
        drop(order_timing);
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
    let rows = transaction.query("SELECT campaign_id, resolve_tick, register_storage_bytes, receipt_storage_bytes, identity_bytes, tick_content_hash, lookup_delta_bytes FROM public.v_observer_material_state_v1 WHERE campaign_id=$1 AND resolve_tick >= $2 AND resolve_tick <= $3 ORDER BY resolve_tick LIMIT 4", &[campaign.as_uuid(), &start_sql, &through_sql]).map_err(|_| ObserverEconomyError::Database)?;
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
    expected: &EconomicContentAdmission,
    history: &mut MaterialHistory,
    mut start: u64,
    through: u64,
) -> Result<(), ObserverEconomyError> {
    while start <= through {
        for row in material_rows(transaction, campaign, start, through)? {
            history.append(campaign, expected, start, row)?;
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
    expected: &Arc<EconomicContentAdmission>,
    cursor: &mut Option<ObserverMaterialCursor>,
) -> Result<MaterialObservation, ObserverEconomyError> {
    if visibility == ObserverVisibility::KnownPreview {
        return Ok(MaterialObservation {
            foundation_digest: digest_hex(&expected.digest()),
            production: None,
            nominal_world_hash: None,
        });
    }
    let history_timing = diagnostics::Timing::start(Stage::HistoryLoad, tick);
    let reuse = cursor.as_ref().is_some_and(|c| {
        c.campaign == campaign
            && c.admission.digest() == expected.digest()
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
        (
            diagnostics::observer(Stage::InitialHistory, tick, MaterialHistory::new(expected))?,
            0,
        )
    };
    diagnostics::observer(
        Stage::ExtendHistory,
        tick,
        extend_history(transaction, campaign, expected, &mut history, start, tick),
    )?;
    drop(history_timing);
    // Authenticate endpoint graph/events before allocating the full current projection.
    // Only the projected staffing accounts survive the endpoint ownership scope.
    let staffing_timing = diagnostics::Timing::start(Stage::Staffing, tick);
    let staffing_accounts = diagnostics::observer(
        Stage::Staffing,
        tick,
        authenticated_staffing(transaction, campaign, expected, &history),
    )?;
    drop(staffing_timing);
    let projection_timing = diagnostics::Timing::start(Stage::CurrentProjection, tick);
    let mut production = project_economic_current(
        expected.view(),
        history.register(expected),
        history.opening(expected),
        history.receipt.as_ref(),
        &history.orders,
    )
    .map_err(|error| {
        let _ = diagnostics::projection::<()>(Stage::CurrentProjection, tick, Err(error));
        ObserverEconomyError::InvalidProjection
    })?;
    drop(projection_timing);
    production.staffing_accounts = staffing_accounts;
    let prior_world = history.prior_world;
    if cursor.as_ref().is_none_or(|cached| {
        cached.campaign != campaign
            || cached.admission.digest() != expected.digest()
            || cached.completed_tick() <= tick
    }) {
        *cursor = Some(ObserverMaterialCursor {
            campaign,
            admission: Arc::clone(expected),
            history,
        });
    }
    Ok(MaterialObservation {
        foundation_digest: digest_hex(&expected.digest()),
        production: Some(diagnostics::observer(
            Stage::Attribution,
            tick,
            attribute_production(production, expected, visibility, tick),
        )?),
        nominal_world_hash: prior_world.map(|hash| digest_hex(&hash)),
    })
}

pub(crate) fn production_history(
    transaction: &mut impl GenericClient,
    campaign: CampaignId,
    tick: u64,
    target: &ProductionHistoryTarget,
    expected: &EconomicContentAdmission,
) -> Result<Vec<ProductionOutputPoint>, ObserverEconomyError> {
    let metadata =
        Metadata::new(expected.view()).map_err(|_| ObserverEconomyError::InvalidProjection)?;
    let process = *metadata
        .processes
        .iter()
        .find(|(id, (site, _, _))| {
            digest_hex(&id.as_bytes()) == target.process_id
                && digest_hex(&site.site_id.as_bytes()) == target.site_id
        })
        .map(|(id, _)| id)
        .ok_or(ObserverEconomyError::ProductionHistoryUnavailable)?;
    let start = tick.saturating_sub(babylon_kernel::clock::TICKS_PER_YEAR - 1);
    let mut history = MaterialHistory::new(expected)?;
    let mut points = Vec::new();
    let mut index = 0;
    while index <= tick {
        for row in material_rows(transaction, campaign, index, tick)? {
            history.append(campaign, expected, index, row)?;
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
                    expected.foundation_graph().scenario_scope(),
                    expected.digest(),
                    &expected.component_identity,
                    (
                        &history.lookup,
                        history.lookup_chain,
                        [Some(history.register(expected)), history.opening(expected)],
                    ),
                )
                .map_err(|_| ObserverEconomyError::InvalidProjection)?;
                if stored.register.as_ref() != history.register(expected)
                    || Some(stored.identity.result_world_hash()) != history.prior_world
                {
                    return Err(ObserverEconomyError::InvalidProjection);
                }
            }
            if period >= start {
                let projected = project_process(
                    &metadata,
                    &Quantities::new(
                        history.register(expected).state(),
                        history.receipt.as_ref().map(|(r, _)| r),
                    ),
                    process,
                )
                .map_err(|_| ObserverEconomyError::InvalidProjection)?;
                if projected.output_good_id != target.output_good_id
                    || projected.output_unit_id != target.output_unit_id
                {
                    return Err(ObserverEconomyError::ProductionHistoryUnavailable);
                }
                points.push(ProductionOutputPoint::from_process(period, &projected)?);
            }
        }
    }
    Ok(points)
}

fn authenticated_history_endpoints<'w>(
    transaction: &mut impl GenericClient,
    campaign: CampaignId,
    expected: &'w EconomicContentAdmission,
    history: &'w MaterialHistory,
) -> Result<
    (
        crate::material_runtime::StoredMaterialTick<'w>,
        Option<crate::material_runtime::StoredMaterialTick<'w>>,
    ),
    ObserverEconomyError,
> {
    let tick = history.register.completed_tick();
    let register = history.register(expected);
    let result_world = history.prior_world;
    let period_receipt = history.receipt.as_ref();
    let mut read = |requested: u64| {
        let _envelope_timing = diagnostics::Timing::start(Stage::AuthenticatedEnvelope, requested);
        let chain = if requested == tick {
            history.lookup_chain
        } else if requested.checked_add(1) == Some(tick) {
            history
                .previous_lookup_chain
                .ok_or(ObserverEconomyError::InvalidProjection)?
        } else {
            return Err(ObserverEconomyError::InvalidProjection);
        };
        read_observer_material_tick(
            transaction,
            campaign,
            requested,
            expected.foundation_graph().scenario_scope(),
            expected.digest(),
            &expected.component_identity,
            (
                &history.lookup,
                chain,
                [Some(register), history.opening(expected)],
            ),
        )
        .map_err(|_| ObserverEconomyError::InvalidProjection)
    };
    let current = read(tick)?;
    if current.register.as_ref() != register
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
    let prior_register = if let Some(previous) = &previous {
        if previous.identity.result_world_hash() != current.identity.prior_world_hash() {
            return Err(ObserverEconomyError::InvalidProjection);
        }
        previous.register.as_ref()
    } else {
        expected.initial_register()
    };
    if Some(prior_register) != history.opening(expected) {
        return Err(ObserverEconomyError::InvalidProjection);
    }
    Ok((current, previous))
}

pub(crate) fn committed_receipts(
    transaction: &mut impl GenericClient,
    campaign: CampaignId,
    tick: u64,
    expected: &EconomicContentAdmission,
) -> Result<crate::observer_reader::CommittedMaterialReceipts, ObserverEconomyError> {
    let mut history = MaterialHistory::new(expected)?;
    extend_history(transaction, campaign, expected, &mut history, 0, tick)?;
    let (current, _) = authenticated_history_endpoints(transaction, campaign, expected, &history)?;
    let identity = current.identity;
    drop(current);
    take_committed_receipts(campaign, tick, expected, &mut history, &identity)
}

fn take_committed_receipts(
    campaign: CampaignId,
    tick: u64,
    expected: &EconomicContentAdmission,
    history: &mut MaterialHistory,
    identity: &babylon_tick::material_replay::IdentifiedMaterialTick,
) -> Result<crate::observer_reader::CommittedMaterialReceipts, ObserverEconomyError> {
    let (receipts, digest) = history
        .receipt
        .take()
        .ok_or(ObserverEconomyError::TickAbsent)?;
    if receipts.resolve_tick != tick || digest != identity.receipt_digest() {
        return Err(ObserverEconomyError::InvalidProjection);
    }
    let household_contributions = match &history.register(expected).state().accounting {
        babylon_material_circuit::CircuitAccounting::PhysicalControl => Vec::new(),
        babylon_material_circuit::CircuitAccounting::Monetary(economy) => {
            match &economy.household_time {
                babylon_material_circuit::HouseholdTimeAccounting::NotModeled => Vec::new(),
                babylon_material_circuit::HouseholdTimeAccounting::Modeled(book) => {
                    if book.contributions.iter().any(|row| row.period != tick) {
                        return Err(ObserverEconomyError::InvalidProjection);
                    }
                    book.contributions.clone()
                }
            }
        }
    };
    Ok(crate::observer_reader::CommittedMaterialReceipts {
        campaign_id: campaign,
        identity: *identity,
        receipts,
        household_contributions,
    })
}

pub(crate) fn committed_observation(
    transaction: &mut impl GenericClient,
    campaign: CampaignId,
    tick: u64,
    expected: &EconomicContentAdmission,
) -> Result<
    (
        MaterialObservation,
        crate::observer_reader::CommittedMaterialReceipts,
    ),
    ObserverEconomyError,
> {
    if tick == 0 {
        return Err(ObserverEconomyError::TickAbsent);
    }
    let history_timing = diagnostics::Timing::start(Stage::HistoryLoad, tick);
    let mut history = MaterialHistory::new(expected)?;
    extend_history(transaction, campaign, expected, &mut history, 0, tick)?;
    drop(history_timing);
    let staffing_timing = diagnostics::Timing::start(Stage::Staffing, tick);
    let (current, previous) =
        authenticated_history_endpoints(transaction, campaign, expected, &history)?;
    let identity = current.identity;
    let staffing = project_authenticated_staffing(expected, &history, &current, previous.as_ref())?;
    drop(previous);
    drop(current);
    drop(staffing_timing);
    let projection_timing = diagnostics::Timing::start(Stage::CurrentProjection, tick);
    let mut production = project_economic_current(
        expected.view(),
        history.register(expected),
        history.opening(expected),
        history.receipt.as_ref(),
        &history.orders,
    )
    .map_err(|_| ObserverEconomyError::InvalidProjection)?;
    drop(projection_timing);
    production.staffing_accounts = staffing;
    let production =
        attribute_production(production, expected, ObserverVisibility::FullObserver, tick)?;
    let observation = MaterialObservation {
        foundation_digest: digest_hex(&expected.digest()),
        production: Some(production),
        nominal_world_hash: history.prior_world.map(|hash| digest_hex(&hash)),
    };
    let accounting = take_committed_receipts(campaign, tick, expected, &mut history, &identity)?;
    Ok((observation, accounting))
}

fn authenticated_staffing(
    transaction: &mut impl GenericClient,
    campaign: CampaignId,
    expected: &EconomicContentAdmission,
    history: &MaterialHistory,
) -> Result<Vec<crate::production_observation::ProductionStaffingAccount>, ObserverEconomyError> {
    use crate::production_projection::staffing::project_staffing_accounts;
    let register = history.register(expected);
    let tick = register.completed_tick();
    if tick == 0 {
        return project_staffing_accounts(
            expected.staffing(),
            expected.foundation_graph(),
            register,
            None,
            &[],
            None,
        )
        .map_err(|error| {
            let _ = diagnostics::projection::<()>(Stage::Staffing, tick, Err(error));
            ObserverEconomyError::InvalidProjection
        });
    }
    let (current, previous) =
        authenticated_history_endpoints(transaction, campaign, expected, history)?;
    project_authenticated_staffing(expected, history, &current, previous.as_ref())
}

fn project_authenticated_staffing(
    expected: &EconomicContentAdmission,
    history: &MaterialHistory,
    current: &crate::material_runtime::StoredMaterialTick<'_>,
    previous: Option<&crate::material_runtime::StoredMaterialTick<'_>>,
) -> Result<Vec<crate::production_observation::ProductionStaffingAccount>, ObserverEconomyError> {
    use crate::production_projection::staffing::project_staffing_accounts;
    let register = history.register(expected);
    let period_receipt = history.receipt.as_ref();
    let tick = register.completed_tick();
    let prior_graph = previous.map_or(expected.foundation_graph(), |row| &row.graph);
    project_staffing_accounts(
        expected.staffing(),
        &current.graph,
        register,
        Some(prior_graph),
        &current.events,
        period_receipt.map(|(rows, _)| rows),
    )
    .map_err(|error| {
        let _ = diagnostics::projection::<()>(Stage::Staffing, tick, Err(error));
        ObserverEconomyError::InvalidProjection
    })
}

fn attribute_production(
    mut production: ProductionSnapshot,
    expected: &EconomicContentAdmission,
    visibility: ObserverVisibility,
    tick: u64,
) -> Result<ProductionSnapshot, ObserverEconomyError> {
    crate::production_projection::context::attach_observed_context(
        expected,
        visibility,
        &mut production,
    )
    .map_err(|error| {
        let _ = diagnostics::projection::<()>(Stage::Attribution, tick, Err(error));
        ObserverEconomyError::InvalidProjection
    })?;
    Ok(production)
}

#[cfg(test)]
mod tests;
