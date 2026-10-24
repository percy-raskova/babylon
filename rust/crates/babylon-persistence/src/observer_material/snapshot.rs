//! Leaf implementation for the parent module; public paths stay on the parent.

use super::storage_witness;

use crate::production_projection::diagnostics::{self, Stage};

use babylon_tick::material_replay::IdentifiedMaterialTick;
use babylon_tick::material_world::{MaterialTickReceipts, MaterialWorldRegister};

use postgres::GenericClient;

use std::sync::{Arc, Weak};

use crate::economic_content;
use crate::economic_content::EconomicContentAdmission;
use crate::identity::CampaignId;
use crate::material_runtime;
use crate::material_runtime::StoredMaterialTick;
use crate::material_runtime::{FoundationReadSource, ObserverEndpointLookup};
use crate::material_storage::AdmittedReceiptWitness;
use crate::material_storage::LookupAnchor;
use crate::material_storage::OpeningRegister;
use crate::michigan_economy;
use crate::observer_reader::CommittedMaterialReceipts;
use crate::observer_reader::{
    ObserverEconomyError, ObserverVisibility, ProductionHistoryTarget, ProductionOutputPoint,
};
use crate::production_observation::ProductionSnapshot;
use crate::production_observation::ProductionStaffingAccount;
use crate::production_projection;
use crate::production_projection::history::OrderHistory;
use crate::production_projection::metadata::Metadata;
use crate::production_projection::sites;
use crate::production_projection::sites::Quantities;
use crate::production_projection::staffing;
use babylon_kernel::content_digest;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::HouseholdTimeAccounting;
use babylon_tick::material_world;
use diagnostics::Timing;
use postgres::Error;
use postgres::Row;
use uuid::Uuid;

pub(crate) struct MaterialObservation {
    pub(crate) foundation_digest: String,
    pub(crate) production: Option<ProductionSnapshot>,
    pub(crate) nominal_world_hash: Option<String>,
}

#[derive(Clone)]
pub(crate) struct MaterialObservationRow {
    pub(crate) row_campaign: Uuid,
    pub(crate) row_tick: i64,
    pub(crate) register_storage_bytes: Vec<u8>,
    pub(crate) lookup_delta: Option<Vec<u8>>,
    pub(crate) receipts: Option<Vec<u8>>,
    pub(crate) identity: Option<Vec<u8>>,
    pub(crate) content_hash: Option<Vec<u8>>,
}

pub(crate) fn decode_material_row(row: &Row) -> Result<MaterialObservationRow, Error> {
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
    let row_campaign: Uuid = header
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
    economic_content::validate_economic_header(
        &preset_id,
        duration,
        &content,
        &foundation_digest,
        tick,
    )
    .map_err(|_| ObserverEconomyError::ScenarioMismatch)?;
    if &row_campaign != campaign.as_uuid() {
        return Err(ObserverEconomyError::ScenarioMismatch);
    }
    let admission = if visibility == ObserverVisibility::FullObserver {
        let _foundation_timing = Timing::start(Stage::FoundationLoad, 0);
        let expected = foundation_digest
            .as_slice()
            .try_into()
            .map_err(|_| ObserverEconomyError::InvalidProjection)?;
        let captured = material_runtime::capture_material_foundation_components(
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
            let economic_timing = Timing::start(Stage::FoundationEconomicAdmission, 0);
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
    admission: Weak<EconomicContentAdmission>,
    admission_digest: [u8; 32],
    history: MaterialHistory,
}

/// Separate identities copied from the successfully authenticated opening.
/// The composite material foundation includes the graph foundation; its digest
/// is not the digest of that graph component or its projected graph state.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ObserverOpeningFoundations {
    pub material_foundation_sha256: [u8; 32],
    pub graph_foundation_sha256: [u8; 32],
}

impl ObserverMaterialCursor {
    pub(crate) fn admission(&self, campaign: CampaignId) -> Option<Arc<EconomicContentAdmission>> {
        (self.campaign == campaign)
            .then(|| self.admission.upgrade())
            .flatten()
    }
    #[must_use]
    pub fn completed_tick(&self) -> u64 {
        self.history.register.completed_tick()
    }

    /// Borrow the immutable register from the last successful complete observation.
    /// This is retained historical evidence; a later read still authenticates the
    /// database prefix before reuse. No state or canonical bytes are copied.
    #[must_use]
    pub fn current_register(&self) -> Option<&MaterialWorldRegister> {
        match &self.history.register {
            MaterialRegisterBoundary::Foundation => None,
            MaterialRegisterBoundary::Period(register) => Some(register),
        }
    }

    /// Borrow the exact authenticated opening while its admitted reader owner is
    /// alive. The callback cannot retain a register reference; neither the typed
    /// state nor canonical bytes are copied or added to the cursor's ownership.
    /// # Errors
    /// Refuses another campaign, a positive period, changed admission or an owner
    /// already released. A cursor is evidence of its successful read, not a fresh
    /// database authentication for later inputs.
    pub fn with_opening_register<T>(
        &self,
        campaign: CampaignId,
        observe: impl FnOnce(&MaterialWorldRegister) -> T,
    ) -> Result<T, ObserverEconomyError> {
        let owner = self.opening_admission(campaign)?;
        Ok(observe(owner.initial_register()))
    }

    /// Copy the distinct foundation digests from the original admitted read.
    /// No register, canonical export, or admission owner is retained or copied.
    /// This is evidence of that opening read, not a new database authentication.
    /// # Errors
    /// Refuses another campaign, a period cursor, changed admission, or an owner
    /// already released. Call before dropping the reader that owns admission.
    pub fn opening_foundations(
        &self,
        campaign: CampaignId,
    ) -> Result<ObserverOpeningFoundations, ObserverEconomyError> {
        let owner = self.opening_admission(campaign)?;
        Ok(ObserverOpeningFoundations {
            material_foundation_sha256: owner.digest(),
            graph_foundation_sha256: owner.graph_digest,
        })
    }

    fn opening_admission(
        &self,
        campaign: CampaignId,
    ) -> Result<Arc<EconomicContentAdmission>, ObserverEconomyError> {
        if self.history.register != MaterialRegisterBoundary::Foundation {
            return Err(ObserverEconomyError::TickAbsent);
        }
        let owner = self
            .admission(campaign)
            .ok_or(ObserverEconomyError::InvalidProjection)?;
        if owner.digest() != self.admission_digest {
            return Err(ObserverEconomyError::ScenarioMismatch);
        }
        Ok(owner)
    }
}

#[derive(Clone)]
pub(crate) struct MaterialHistory {
    pub(super) lookup: OpeningRegister,
    pub(super) lookup_chain: [u8; 32],
    pub(super) previous_lookup_chain: Option<[u8; 32]>,
    pub(super) register: MaterialRegisterBoundary,
    pub(super) opening: Option<MaterialRegisterBoundary>,
    pub(super) receipt: Option<(Arc<MaterialTickReceipts>, [u8; 32])>,
    receipt_witness: Option<AdmittedReceiptWitness>,
    pub(super) orders: OrderHistory,
    pub(super) prior_world: Option<[u8; 32]>,
    storage_prefix: [u8; 32],
}

/// Foundation state belongs to the immutable admission. A history owns only
/// committed period registers, including the previous period needed by proofs.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) enum MaterialRegisterBoundary {
    Foundation,
    Period(Arc<MaterialWorldRegister>),
}

impl MaterialRegisterBoundary {
    fn resolve<'a>(&'a self, expected: &'a EconomicContentAdmission) -> &'a MaterialWorldRegister {
        match self {
            Self::Foundation => expected.initial_register(),
            Self::Period(register) => register,
        }
    }

    pub(super) fn completed_tick(&self) -> u64 {
        match self {
            Self::Foundation => 0,
            Self::Period(register) => register.completed_tick(),
        }
    }
}

impl MaterialHistory {
    pub(super) fn receipt(&self) -> Option<(&MaterialTickReceipts, [u8; 32])> {
        self.receipt
            .as_ref()
            .map(|(rows, digest)| (rows.as_ref(), *digest))
    }

    pub(super) fn register<'a>(
        &'a self,
        expected: &'a EconomicContentAdmission,
    ) -> &'a MaterialWorldRegister {
        self.register.resolve(expected)
    }

    pub(super) fn opening<'a>(
        &'a self,
        expected: &'a EconomicContentAdmission,
    ) -> Option<&'a MaterialWorldRegister> {
        self.opening
            .as_ref()
            .map(|register| register.resolve(expected))
    }

    pub(super) fn new(expected: &EconomicContentAdmission) -> Result<Self, ObserverEconomyError> {
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
            receipt_witness: None,
            orders: OrderHistory::from_opening(expected.initial_register().state()).map_err(
                |error| {
                    let _ = diagnostics::projection::<()>(Stage::InitialHistory, 0, Err(error));
                    ObserverEconomyError::InvalidProjection
                },
            )?,
            prior_world: None,
            storage_prefix: storage_witness::seed(),
        })
    }

    fn append(
        &mut self,
        campaign: CampaignId,
        expected: &EconomicContentAdmission,
        index: u64,
        row: Row,
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

    pub(super) fn append_decoded(
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
        let fingerprint = storage_witness::fingerprint(&row)?;
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
            self.storage_prefix = storage_witness::append(self.storage_prefix, fingerprint);
            return Ok(());
        }
        // This history is a detached read candidate, never a published cursor.
        // The next append needs only the current register, order index and hashes;
        // obsolete prior state/receipts must not overlap the next full admission.
        self.opening = None;
        self.receipt = None;
        self.receipt_witness = None;
        let delta = lookup_delta
            .as_deref()
            .ok_or(ObserverEconomyError::InvalidProjection)?;
        let lookup = crate::material_storage::read_period_lookup(
            &self.lookup,
            index,
            delta,
            LookupAnchor::Previous(self.lookup_chain),
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
        // Complete codec admission already owns the typed register and receipts.
        // Bind the original canonical receipt bytes, then release serialization
        // and SQL package buffers before lifecycle/order validation allocates.
        let receipt_digest = content_digest::sha256_of(&admitted.receipt_bytes);
        drop(admitted.receipt_bytes);
        drop(register_storage_bytes);
        drop(lookup_delta);
        drop(receipts);
        self.append_receipt(
            expected,
            &next,
            identity
                .as_deref()
                .ok_or(ObserverEconomyError::InvalidProjection)?,
            receipt_digest,
            content_hash.as_deref(),
            admitted.receipts,
        )?;
        self.receipt_witness = Some(admitted.receipt_witness);
        let previous = std::mem::replace(
            &mut self.register,
            MaterialRegisterBoundary::Period(Arc::new(next)),
        );
        self.previous_lookup_chain = Some(self.lookup_chain);
        self.lookup_chain = lookup.chain;
        self.opening = Some(previous);
        self.storage_prefix = storage_witness::append(self.storage_prefix, fingerprint);
        Ok(())
    }

    fn append_receipt(
        &mut self,
        expected: &EconomicContentAdmission,
        next: &MaterialWorldRegister,
        identity: &[u8],
        receipt_digest: [u8; 32],
        content_hash: Option<&[u8]>,
        receipt: Arc<MaterialTickReceipts>,
    ) -> Result<(), ObserverEconomyError> {
        let index = next.completed_tick();
        let prior_register = self.register.resolve(expected);
        let identity = IdentifiedMaterialTick::decode(identity)
            .map_err(|_| diagnostics::invalid(Stage::ReceiptIdentity, index))?;
        if identity.resolve_tick() != index
            || identity.foundation_digest() != expected.digest()
            || content_hash != Some(identity.tick_content_hash().as_bytes().as_slice())
            || receipt_digest != identity.receipt_digest()
            || material_world::nominal_material_world_hash(identity.graph_world_after(), next)
                != identity.result_world_hash()
            || material_world::nominal_material_world_hash(
                identity.graph_world_before(),
                prior_register,
            ) != identity.prior_world_hash()
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
        let order_timing = Timing::start(Stage::OrderHistory, index);
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

pub(crate) const MATERIAL_PAGE_ROWS: u64 = 4;

pub(crate) fn material_rows(
    transaction: &mut impl GenericClient,
    campaign: CampaignId,
    start: u64,
    through: u64,
) -> Result<Vec<Row>, ObserverEconomyError> {
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

pub(crate) fn extend_history(
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

pub(crate) fn history_for_read(
    transaction: &mut impl GenericClient,
    campaign: CampaignId,
    tick: u64,
    expected: &Arc<EconomicContentAdmission>,
    cursor: &mut Option<ObserverMaterialCursor>,
) -> Result<MaterialHistory, ObserverEconomyError> {
    let reuse = cursor.as_ref().is_some_and(|c| {
        c.campaign == campaign
            && c.admission_digest == expected.digest()
            && c.completed_tick() <= tick
    });
    let (mut history, start) = if reuse {
        let cached = cursor
            .as_ref()
            .ok_or(ObserverEconomyError::InvalidProjection)?;
        storage_witness::verify_prefix(
            transaction,
            campaign,
            cached.completed_tick(),
            cached.history.storage_prefix,
        )?;
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
    Ok(history)
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
            foundation_digest: michigan_economy::digest_hex(&expected.digest()),
            production: None,
            nominal_world_hash: None,
        });
    }
    let history_timing = Timing::start(Stage::HistoryLoad, tick);
    let history = history_for_read(transaction, campaign, tick, expected, cursor)?;
    drop(history_timing);
    // Authenticate endpoint graph/events before allocating the full current projection.
    // Only the projected staffing accounts survive the endpoint ownership scope.
    let staffing_timing = Timing::start(Stage::Staffing, tick);
    let staffing_accounts = diagnostics::observer(
        Stage::Staffing,
        tick,
        authenticated_staffing(transaction, campaign, expected, &history),
    )?;
    drop(staffing_timing);
    let projection_timing = Timing::start(Stage::CurrentProjection, tick);
    let mut production = production_projection::project_economic_current(
        expected.view(),
        history.register(expected),
        history.opening(expected),
        history.receipt(),
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
            || cached.admission_digest != expected.digest()
            || cached.completed_tick() <= tick
    }) {
        *cursor = Some(ObserverMaterialCursor {
            campaign,
            admission: Arc::downgrade(expected),
            admission_digest: expected.digest(),
            history,
        });
    }
    Ok(MaterialObservation {
        foundation_digest: michigan_economy::digest_hex(&expected.digest()),
        production: Some(diagnostics::observer(
            Stage::Attribution,
            tick,
            attribute_production(production, expected, visibility, tick),
        )?),
        nominal_world_hash: prior_world.map(|hash| michigan_economy::digest_hex(&hash)),
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
            michigan_economy::digest_hex(&id.as_bytes()) == target.process_id
                && michigan_economy::digest_hex(&site.site_id.as_bytes()) == target.site_id
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
                let stored = material_runtime::read_observer_material_tick(
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
                let projected = sites::project_process(
                    &metadata,
                    &Quantities::new(
                        history.register(expected).state(),
                        history.receipt.as_ref().map(|(r, _)| r.as_ref()),
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

pub(crate) fn authenticated_history_endpoints<'w>(
    transaction: &mut impl GenericClient,
    campaign: CampaignId,
    expected: &'w EconomicContentAdmission,
    history: &'w MaterialHistory,
) -> Result<(StoredMaterialTick<'w>, Option<StoredMaterialTick<'w>>), ObserverEconomyError> {
    let tick = history.register.completed_tick();
    let register = history.register(expected);
    let result_world = history.prior_world;
    let period_receipt = history.receipt.as_ref();
    let (current, previous) = material_runtime::read_observer_material_endpoints(
        transaction,
        campaign,
        tick,
        expected.foundation_graph().scenario_scope(),
        expected.digest(),
        &expected.component_identity,
        ObserverEndpointLookup {
            opening: &history.lookup,
            current_chain: history.lookup_chain,
            previous_chain: history.previous_lookup_chain,
            registers: [Some(register), history.opening(expected)],
            receipt: history.receipt_witness.as_ref(),
        },
    )
    .map_err(|_| ObserverEconomyError::InvalidProjection)?;
    if current.register.as_ref() != register
        || Some(current.identity.result_world_hash()) != result_world
        || Some(current.identity.receipt_digest()) != period_receipt.map(|(_, digest)| *digest)
    {
        return Err(ObserverEconomyError::InvalidProjection);
    }
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
) -> Result<CommittedMaterialReceipts, ObserverEconomyError> {
    let mut history = MaterialHistory::new(expected)?;
    extend_history(transaction, campaign, expected, &mut history, 0, tick)?;
    let (current, _) = authenticated_history_endpoints(transaction, campaign, expected, &history)?;
    let identity = current.identity;
    drop(current);
    read_committed_receipts(campaign, tick, expected, &history, &identity)
}

pub(crate) fn read_committed_receipts(
    campaign: CampaignId,
    tick: u64,
    expected: &EconomicContentAdmission,
    history: &MaterialHistory,
    identity: &babylon_tick::material_replay::IdentifiedMaterialTick,
) -> Result<CommittedMaterialReceipts, ObserverEconomyError> {
    let (receipts, digest) = history
        .receipt
        .as_ref()
        .ok_or(ObserverEconomyError::TickAbsent)?;
    if receipts.resolve_tick != tick || *digest != identity.receipt_digest() {
        return Err(ObserverEconomyError::InvalidProjection);
    }
    let household_contributions = match &history.register(expected).state().accounting {
        CircuitAccounting::PhysicalControl => Vec::new(),
        CircuitAccounting::Monetary(economy) => match &economy.household_time {
            HouseholdTimeAccounting::NotModeled => Vec::new(),
            HouseholdTimeAccounting::Modeled(book) => {
                if book.contributions.iter().any(|row| row.period != tick) {
                    return Err(ObserverEconomyError::InvalidProjection);
                }
                book.contributions.clone()
            }
        },
    };
    Ok(CommittedMaterialReceipts {
        campaign_id: campaign,
        identity: *identity,
        material_register_bytes: history.register(expected).canonical_bytes().len(),
        receipts: Arc::clone(receipts),
        household_contributions,
    })
}

pub(crate) fn committed_observation(
    transaction: &mut impl GenericClient,
    campaign: CampaignId,
    tick: u64,
    expected: &Arc<EconomicContentAdmission>,
    cursor: &mut Option<ObserverMaterialCursor>,
) -> Result<(MaterialObservation, CommittedMaterialReceipts), ObserverEconomyError> {
    if tick == 0 {
        return Err(ObserverEconomyError::TickAbsent);
    }
    let history_timing = Timing::start(Stage::HistoryLoad, tick);
    let history = history_for_read(transaction, campaign, tick, expected, cursor)?;
    drop(history_timing);
    let staffing_timing = Timing::start(Stage::Staffing, tick);
    let (current, previous) =
        authenticated_history_endpoints(transaction, campaign, expected, &history)?;
    let identity = current.identity;
    let staffing = project_authenticated_staffing(expected, &history, &current, previous.as_ref())?;
    drop(previous);
    drop(current);
    drop(staffing_timing);
    let projection_timing = Timing::start(Stage::CurrentProjection, tick);
    let mut production = production_projection::project_economic_current(
        expected.view(),
        history.register(expected),
        history.opening(expected),
        history.receipt(),
        &history.orders,
    )
    .map_err(|_| ObserverEconomyError::InvalidProjection)?;
    drop(projection_timing);
    production.staffing_accounts = staffing;
    let production =
        attribute_production(production, expected, ObserverVisibility::FullObserver, tick)?;
    let observation = MaterialObservation {
        foundation_digest: michigan_economy::digest_hex(&expected.digest()),
        production: Some(production),
        nominal_world_hash: history
            .prior_world
            .map(|hash| michigan_economy::digest_hex(&hash)),
    };
    let accounting = read_committed_receipts(campaign, tick, expected, &history, &identity)?;
    *cursor = Some(ObserverMaterialCursor {
        campaign,
        admission: Arc::downgrade(expected),
        admission_digest: expected.digest(),
        history,
    });
    Ok((observation, accounting))
}

pub(crate) fn authenticated_staffing(
    transaction: &mut impl GenericClient,
    campaign: CampaignId,
    expected: &EconomicContentAdmission,
    history: &MaterialHistory,
) -> Result<Vec<ProductionStaffingAccount>, ObserverEconomyError> {
    let register = history.register(expected);
    let tick = register.completed_tick();
    if tick == 0 {
        return staffing::project_staffing_accounts(
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

pub(crate) fn project_authenticated_staffing(
    expected: &EconomicContentAdmission,
    history: &MaterialHistory,
    current: &StoredMaterialTick<'_>,
    previous: Option<&StoredMaterialTick<'_>>,
) -> Result<Vec<ProductionStaffingAccount>, ObserverEconomyError> {
    let register = history.register(expected);
    let period_receipt = history.receipt.as_ref();
    let tick = register.completed_tick();
    let prior_graph = previous.map_or(expected.foundation_graph(), |row| &row.graph);
    staffing::project_staffing_accounts(
        expected.staffing(),
        &current.graph,
        register,
        Some(prior_graph),
        &current.events,
        period_receipt.map(|(rows, _)| rows.as_ref()),
    )
    .map_err(|error| {
        let _ = diagnostics::projection::<()>(Stage::Staffing, tick, Err(error));
        ObserverEconomyError::InvalidProjection
    })
}

pub(crate) fn attribute_production(
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
mod opening_controls {
    use super::*;
    use crate::michigan_content::MichiganContentPreset;
    use uuid::Uuid;

    fn fixture() -> (
        CampaignId,
        Arc<EconomicContentAdmission>,
        ObserverMaterialCursor,
    ) {
        let foundation = MichiganContentPreset::FourWeekStandard
            .create_foundation(&crate::test_support::catalog())
            .unwrap();
        let owner = Arc::new(EconomicContentAdmission::from_foundation(foundation).unwrap());
        let campaign = CampaignId::from_uuid(Uuid::from_u128(0x342_000));
        let cursor = ObserverMaterialCursor {
            campaign,
            admission: Arc::downgrade(&owner),
            admission_digest: owner.digest(),
            history: MaterialHistory::new(&owner).unwrap(),
        };
        (campaign, owner, cursor)
    }

    #[test]
    fn opening_borrows_the_authenticated_owner_without_another_register() {
        let (campaign, owner, cursor) = fixture();
        assert!(cursor.current_register().is_none());
        let digest = cursor
            .with_opening_register(campaign, |register| {
                assert!(std::ptr::eq(register, owner.initial_register()));
                assert_eq!(register.completed_tick(), 0);
                register.digest()
            })
            .unwrap();
        assert_eq!(digest, owner.initial_register().digest());
        assert_eq!(Arc::strong_count(&owner), 1);
    }

    #[test]
    fn opening_borrow_refuses_another_campaign_digest_or_expired_owner() {
        let (campaign, owner, mut cursor) = fixture();
        let other = CampaignId::from_uuid(Uuid::from_u128(0x342_999));
        assert!(cursor.with_opening_register(other, |_| ()).is_err());
        cursor.admission_digest[0] ^= 1;
        assert!(cursor.with_opening_register(campaign, |_| ()).is_err());
        cursor.admission_digest = owner.digest();
        drop(owner);
        assert!(cursor.with_opening_register(campaign, |_| ()).is_err());
    }

    #[test]
    fn opening_foundations_preserve_distinct_admitted_component_identities() {
        let (campaign, owner, cursor) = fixture();
        let identity = cursor.opening_foundations(campaign).unwrap();
        assert_eq!(identity.material_foundation_sha256, owner.digest());
        assert_eq!(identity.graph_foundation_sha256, owner.graph_digest);
        assert_ne!(
            identity.material_foundation_sha256,
            identity.graph_foundation_sha256
        );
        assert_eq!(Arc::strong_count(&owner), 1);
    }

    #[test]
    fn opening_foundations_refuse_changed_or_released_admission_and_period_cursors() {
        let (campaign, owner, mut cursor) = fixture();
        let other = CampaignId::from_uuid(Uuid::from_u128(0x342_999));
        assert!(cursor.opening_foundations(other).is_err());
        cursor.admission_digest[0] ^= 1;
        assert!(cursor.opening_foundations(campaign).is_err());
        cursor.admission_digest = owner.digest();
        cursor.history.register =
            MaterialRegisterBoundary::Period(Arc::new(owner.initial_register().clone()));
        assert!(cursor.opening_foundations(campaign).is_err());
        cursor.history.register = MaterialRegisterBoundary::Foundation;
        drop(owner);
        assert!(cursor.opening_foundations(campaign).is_err());
    }
}
