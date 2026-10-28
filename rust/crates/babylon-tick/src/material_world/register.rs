//! Leaf implementation for the parent module; public paths stay on the parent.

use super::aid_receipt;
use super::collection_receipt;
use super::equipment_receipt;
use super::financial_receipt;
use super::household_time_receipt;
use super::income_receipt;
use super::installation_decision;
use super::maintenance_receipt;
use super::monetary_receipt;
use super::organizer_collection;
use super::organizer_support;
use super::organizer_time;
use super::recurring_receipt;
use super::service_receipt;
use super::workforce_receipt;

use babylon_material_circuit::ArrivalReceipt;

use babylon_material_circuit::DeliveryReceipt;

use babylon_material_circuit::FinalDemandPrincipalId;

use babylon_material_circuit::FreightLossReceipt;

use babylon_material_circuit::FreightLotId;

use babylon_material_circuit::GoodId;

use babylon_material_circuit::LocalRetailFulfillmentReceipt;

use babylon_material_circuit::LocalTransferReceipt;

use babylon_material_circuit::MerchantHandlingReceipt;

use babylon_material_circuit::OrderId;

use babylon_material_circuit::OutboundOrderId;

use babylon_material_circuit::ProcessId;

use babylon_material_circuit::ProductionReceipt;

use babylon_material_circuit::RealizationReceipt;

use babylon_material_circuit::RouteId;

use babylon_material_circuit::RoutedDispatchReceipt;

use babylon_material_circuit::SiteId;

use babylon_material_circuit::UnitId;

use babylon_material_circuit::MAX_ROUTE_STAGES_PER_ROUTE;

use babylon_material_circuit::{
    MaterialCatalog, MaterialCircuitError, MaterialCircuitState, MaterialCircuitTransition,
};

use babylon_kernel::content_digest;
use babylon_material_circuit::AidReceipt;
use babylon_material_circuit::CapitalContributionReceipt;
use babylon_material_circuit::CollectionReceipt;
use babylon_material_circuit::DistributionReceipt;
use babylon_material_circuit::EquipmentWearReceipt;
use babylon_material_circuit::HouseholdConsumptionReceipt;
use babylon_material_circuit::HouseholdDemandReceipt;
use babylon_material_circuit::HouseholdServiceReceipt;
use babylon_material_circuit::HouseholdTimeReceipt;
use babylon_material_circuit::IncomeReceipt;
use babylon_material_circuit::InstallationDecisionReceipt;
use babylon_material_circuit::InstallationReceipt;
use babylon_material_circuit::InvestmentReceipt;
use babylon_material_circuit::LaborUseReceipt;
use babylon_material_circuit::MaintenanceReceipt;
use babylon_material_circuit::MemberLaborUseReceipt;
use babylon_material_circuit::MoneyTransferReceipt;
use babylon_material_circuit::PriceReceipt;
use babylon_material_circuit::ProcurementReceipt;
use babylon_material_circuit::ProductionPlanReceipt;
use babylon_material_circuit::PublicBudgetReceipt;
use babylon_material_circuit::ServiceMarketReceipt;
use babylon_material_circuit::ServiceOutputReceipt;
use babylon_material_circuit::ServicePerformanceReceipt;
use babylon_material_circuit::StaffingMemberReceipt;
use babylon_material_circuit::TaxReceipt;
use babylon_material_circuit::WageAccrualReceipt;
use babylon_practice_contract::OrganizerAidSupport;
use babylon_practice_contract::OrganizerCollectionFact;
use babylon_practice_contract::OrganizerCommitment;
use babylon_practice_contract::OrganizerPeriodJournal;
use babylon_practice_contract::OrganizerPeriodTimeResources;
use babylon_practice_contract::{
    OrganizerConfig, OrganizerError, OrganizerState, OrganizerWorkplaceFacts,
};
use std::borrow::Cow;
use std::fmt::Formatter;
use std::fmt::Result as FmtResult;
use std::ops::Deref;
use std::sync::Arc;

pub(crate) const REGISTER_DOMAIN: &[u8] = b"babylon.material-world-register.v5\0";

pub(crate) const NOMINAL_DOMAIN: &[u8] = b"babylon.nominal-material-world.v3\0";

pub(crate) const RECEIPT_DOMAIN: &[u8] = b"babylon.material-tick-receipts.v18\0";

/// Designed 1 GB operational headroom explicitly authorized by the Director.
/// This standalone ceiling does not enlarge surrounding foundation or receipt bounds.
pub const MAX_MATERIAL_WORLD_REGISTER_BYTES: usize = 1_000_000_000;

/// Derived complete receipt bound from the closed family row limits and codecs.
/// Independent collection limits still reject excessive rows before allocation.
pub const MAX_MATERIAL_TICK_RECEIPT_BYTES: usize = maximum_material_receipt_bytes();

/// Number of ordered families in the current canonical receipt schema.
pub const RECEIPT_FAMILY_COUNT: usize = 36;

/// Exact canonical row widths, indexed by the zero-based receipt family.
pub const RECEIPT_ROW_BYTES: [usize; RECEIPT_FAMILY_COUNT] = [
    80_usize,
    112,
    106,
    40,
    40,
    40,
    97,
    168,
    168,
    maintenance_receipt::ROW_BYTES,
    monetary_receipt::TRANSFER_BYTES,
    monetary_receipt::ACCRUAL_BYTES,
    monetary_receipt::LABOR_BYTES,
    recurring_receipt::DEMAND_BYTES,
    recurring_receipt::CONSUMPTION_BYTES,
    recurring_receipt::PROCUREMENT_BYTES,
    recurring_receipt::PLAN_BYTES,
    recurring_receipt::PRICE_BYTES,
    income_receipt::ROW_BYTES,
    service_receipt::PERFORMANCE_BYTES,
    service_receipt::HOUSEHOLD_BYTES,
    service_receipt::MARKET_BYTES,
    service_receipt::OUTPUT_BYTES,
    financial_receipt::PUBLIC_BUDGETS_BYTES,
    financial_receipt::TAXES_BYTES,
    financial_receipt::DISTRIBUTIONS_BYTES,
    financial_receipt::CONTRIBUTIONS_BYTES,
    workforce_receipt::STAFFING_BYTES,
    workforce_receipt::ATTENDANCE_BYTES,
    equipment_receipt::INSTALLATION_BYTES,
    equipment_receipt::WEAR_BYTES,
    equipment_receipt::INVESTMENT_BYTES,
    installation_decision::ROW_BYTES,
    household_time_receipt::ROW_BYTES,
    aid_receipt::ROW_BYTES,
    collection_receipt::ROW_BYTES,
];

pub(crate) const fn maximum_material_receipt_bytes() -> usize {
    let mut total = RECEIPT_DOMAIN.len() + 12 + RECEIPT_FAMILY_COUNT * 9;
    let mut index = 0;
    while index < RECEIPT_FAMILY_COUNT {
        total += receipt_row_limit(index) * RECEIPT_ROW_BYTES[index];
        index += 1;
    }
    total
}

/// Immutable canonical register bytes that can be shared without copying.
///
/// The owned admission path adopts the caller's authenticated `Vec<u8>`
/// allocation, which `organizer_aid_replay` pins with a pointer comparison.
/// `Arc<[u8]>` cannot adopt an existing vector: it allocates a new inline
/// header and copies the bytes. The handle therefore keeps the `Arc<Vec<u8>>`
/// and hides the mutable vector behind [`Self::as_slice`], so no caller can
/// change canonical bytes through a retained clone.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SharedCanonicalBytes(
    #[allow(
        clippy::rc_buffer,
        reason = "owned register admission adopts the caller's exact canonical byte allocation"
    )]
    // STYLE-EXCEPTION(EXC-04): the handle adopts the caller's authenticated canonical allocation.
    Arc<Vec<u8>>,
);

impl SharedCanonicalBytes {
    fn from_vec(bytes: Vec<u8>) -> Self {
        // STYLE-EXCEPTION(EXC-04): adopts the caller's canonical byte allocation.
        Self(Arc::new(bytes))
    }

    fn from_slice(bytes: &[u8]) -> Result<Self, MaterialWorldError> {
        let mut owned = bounded_bytes(bytes.len(), MAX_MATERIAL_WORLD_REGISTER_BYTES)?;
        owned.extend_from_slice(bytes);
        Ok(Self::from_vec(owned))
    }

    /// Borrow the exact admitted canonical bytes.
    #[must_use]
    pub fn as_slice(&self) -> &[u8] {
        self.0.as_slice()
    }

    /// Whether both handles share one admitted allocation.
    #[must_use]
    pub fn shares_allocation(&self, other: &Self) -> bool {
        // STYLE-EXCEPTION(EXC-04): the no-copy sharing contract is asserted here.
        Arc::ptr_eq(&self.0, &other.0)
    }
}

/// One checked complete material register at a completed four-week boundary.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MaterialWorldRegister {
    completed_tick: u64,
    state: MaterialCircuitState,
    organizer: Option<(OrganizerConfig, OrganizerState, OrganizerPeriodJournal)>,
    canonical_bytes: SharedCanonicalBytes,
    /// Digest of the immutable catalog that admitted this register's state frame.
    catalog_digest: [u8; 32],
    digest: [u8; 32],
}

/// Failure never publishes any part of a proposed material transition.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum MaterialWorldError {
    Circuit(MaterialCircuitError),
    PeriodMismatch,
    Arithmetic,
    ByteLimit,
    Allocation,
    Wire,
    Organizer(OrganizerError),
}

impl std::fmt::Display for MaterialWorldError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FmtResult {
        write!(f, "material world refused: {self:?}")
    }
}

impl std::error::Error for MaterialWorldError {}

impl From<MaterialCircuitError> for MaterialWorldError {
    fn from(error: MaterialCircuitError) -> Self {
        Self::Circuit(error)
    }
}

impl From<OrganizerError> for MaterialWorldError {
    fn from(error: OrganizerError) -> Self {
        Self::Organizer(error)
    }
}

impl MaterialWorldRegister {
    /// Own and validate the full opening state for the next four-week interval.
    /// # Errors
    /// Refuses invalid circuit state, period mismatch, overflow or aggregate byte bound.
    pub fn try_new(
        catalog: &MaterialCatalog,
        completed_tick: u64,
        state: MaterialCircuitState,
    ) -> Result<Self, MaterialWorldError> {
        Self::build(catalog, completed_tick, state, None)
    }

    /// Admit one engine-produced canonical successor without a second decode pass.
    ///
    /// The caller supplies the immutable catalog and a state that already passed
    /// the engine's own canonical admission. This path encodes the state exactly
    /// once to mint the register bytes; it never drops the candidate and decodes
    /// it again merely to recover the value it already owns.
    /// # Errors
    /// Refuses a zero period, an invalid circuit state under the catalog, or the
    /// aggregate register byte bound.
    pub(super) fn from_validated_candidate(
        catalog: &MaterialCatalog,
        state: MaterialCircuitState,
    ) -> Result<Self, MaterialWorldError> {
        let completed_tick = state
            .period
            .checked_sub(1)
            .ok_or(MaterialWorldError::PeriodMismatch)?;
        let state_bytes = babylon_material_circuit::encode_material_circuit_state(catalog, &state)?;
        Self::assemble(catalog, completed_tick, state, None, &state_bytes)
    }

    fn build(
        catalog: &MaterialCatalog,
        completed_tick: u64,
        state: MaterialCircuitState,
        organizer: Option<(OrganizerConfig, OrganizerState, OrganizerPeriodJournal)>,
    ) -> Result<Self, MaterialWorldError> {
        if completed_tick
            .checked_add(1)
            .ok_or(MaterialWorldError::Arithmetic)?
            != state.period
        {
            return Err(MaterialWorldError::PeriodMismatch);
        }
        let state_bytes = babylon_material_circuit::encode_material_circuit_state(catalog, &state)?;
        drop(state);
        let state = babylon_material_circuit::decode_material_circuit_state(catalog, &state_bytes)?;
        Self::assemble(catalog, completed_tick, state, organizer, &state_bytes)
    }

    fn assemble(
        catalog: &MaterialCatalog,
        completed_tick: u64,
        state: MaterialCircuitState,
        organizer: Option<(OrganizerConfig, OrganizerState, OrganizerPeriodJournal)>,
        state_bytes: &[u8],
    ) -> Result<Self, MaterialWorldError> {
        let organizer_bytes = encode_bound_organizer(completed_tick, &state, organizer.as_ref())?;
        let length = REGISTER_DOMAIN
            .len()
            .checked_add(20)
            .and_then(|count| count.checked_add(state_bytes.len()))
            .and_then(|count| count.checked_add(organizer_bytes.len()))
            .ok_or(MaterialWorldError::Arithmetic)?;
        let mut bytes = bounded_bytes(length, MAX_MATERIAL_WORLD_REGISTER_BYTES)?;
        bytes.extend_from_slice(REGISTER_DOMAIN);
        bytes.extend_from_slice(&5_u32.to_be_bytes());
        bytes.extend_from_slice(&completed_tick.to_be_bytes());
        bytes.extend_from_slice(
            &u64::try_from(state_bytes.len())
                .map_err(|_| MaterialWorldError::Arithmetic)?
                .to_be_bytes(),
        );
        bytes.extend_from_slice(state_bytes);
        bytes.extend_from_slice(&organizer_bytes);
        let digest = content_digest::sha256_of(&bytes);
        Ok(Self {
            completed_tick,
            state,
            organizer,
            canonical_bytes: SharedCanonicalBytes::from_vec(bytes),
            catalog_digest: catalog.catalog_digest(),
            digest,
        })
    }

    /// Bind captured organizer content and complete state into this world identity.
    /// # Errors
    /// Refuses invalid content/state, mismatched periods, or aggregate byte limits.
    pub fn with_organizer(
        self,
        catalog: &MaterialCatalog,
        config: OrganizerConfig,
        state: OrganizerState,
        journal: OrganizerPeriodJournal,
    ) -> Result<Self, MaterialWorldError> {
        Self::build(
            catalog,
            self.completed_tick,
            self.state,
            Some((config, state, journal)),
        )
    }

    #[must_use]
    pub fn organizer_config(&self) -> Option<&OrganizerConfig> {
        self.organizer.as_ref().map(|(config, _, _)| config)
    }

    #[must_use]
    pub fn organizer_state(&self) -> Option<&OrganizerState> {
        self.organizer.as_ref().map(|(_, state, _)| state)
    }

    /// Retained exact organizer evidence for the encode-time journal window.
    #[must_use]
    pub fn organizer_journal(&self) -> Option<&OrganizerPeriodJournal> {
        self.organizer.as_ref().map(|(_, _, journal)| journal)
    }
    #[must_use]
    pub const fn completed_tick(&self) -> u64 {
        self.completed_tick
    }
    #[must_use]
    pub fn state(&self) -> &MaterialCircuitState {
        &self.state
    }
    #[must_use]
    pub fn canonical_bytes(&self) -> &[u8] {
        self.canonical_bytes.as_slice()
    }
    /// Share the immutable canonical allocation without cloning the state or bytes.
    #[must_use]
    pub fn shared_canonical_bytes(&self) -> SharedCanonicalBytes {
        self.canonical_bytes.clone()
    }
    #[must_use]
    pub const fn digest(&self) -> [u8; 32] {
        self.digest
    }
    /// Digest of the immutable catalog this register was admitted under.
    #[must_use]
    pub const fn catalog_digest(&self) -> [u8; 32] {
        self.catalog_digest
    }

    /// Decode stored or external register bytes against their admitting catalog.
    ///
    /// External bytes carry no definitions; the campaign's captured catalog is
    /// the only provenance that can authenticate them, so the caller supplies it.
    /// # Errors
    /// Refuses unsupported/truncated/trailing/noncanonical bytes, a foreign
    /// catalog digest and invalid state.
    pub fn decode_external(
        catalog: &MaterialCatalog,
        bytes: Vec<u8>,
    ) -> Result<Self, MaterialWorldError> {
        Self::decode_canonical(catalog, Cow::Owned(bytes))
    }

    fn decode_canonical(
        catalog: &MaterialCatalog,
        bytes: Cow<'_, [u8]>,
    ) -> Result<Self, MaterialWorldError> {
        let header = REGISTER_DOMAIN.len() + 20;
        if bytes.len() < header
            || bytes.len() > MAX_MATERIAL_WORLD_REGISTER_BYTES
            || !bytes.starts_with(REGISTER_DOMAIN)
        {
            return Err(MaterialWorldError::Wire);
        }
        let start = REGISTER_DOMAIN.len();
        if bytes[start..start + 4] != 5_u32.to_be_bytes() {
            return Err(MaterialWorldError::Wire);
        }
        let tick = u64::from_be_bytes(
            bytes[start + 4..start + 12]
                .try_into()
                .map_err(|_| MaterialWorldError::Wire)?,
        );
        let length = usize::try_from(u64::from_be_bytes(
            bytes[start + 12..header]
                .try_into()
                .map_err(|_| MaterialWorldError::Wire)?,
        ))
        .map_err(|_| MaterialWorldError::ByteLimit)?;
        let state_end = header
            .checked_add(length)
            .ok_or(MaterialWorldError::ByteLimit)?;
        let state_bytes = bytes
            .get(header..state_end)
            .ok_or(MaterialWorldError::Wire)?;
        let organizer_wire = bytes.get(state_end..).ok_or(MaterialWorldError::Wire)?;
        let mut remaining = organizer_wire;
        let organizer = match remaining.split_first() {
            Some((0, [])) => None,
            Some((1, tail)) => {
                remaining = tail;
                let config = babylon_practice_contract::decode_organizer_config(
                    take_organizer_section(&mut remaining)?,
                )?;
                let state = babylon_practice_contract::decode_organizer_state(
                    take_organizer_section(&mut remaining)?,
                )?;
                let journal = babylon_practice_contract::decode_organizer_journal(
                    &config,
                    take_organizer_section(&mut remaining)?,
                )?;
                if !remaining.is_empty() {
                    return Err(MaterialWorldError::Wire);
                }
                Some((config, state, journal))
            }
            _ => return Err(MaterialWorldError::Wire),
        };
        let state = babylon_material_circuit::decode_material_circuit_state(catalog, state_bytes)?;
        if tick.checked_add(1).ok_or(MaterialWorldError::Arithmetic)? != state.period {
            return Err(MaterialWorldError::PeriodMismatch);
        }
        // Validate the same canonical circuit and bound organizer as construction,
        // without assembling a second full outer register during admission.
        let canonical_state =
            babylon_material_circuit::encode_material_circuit_state(catalog, &state)?;
        let canonical_organizer = encode_bound_organizer(tick, &state, organizer.as_ref())?;
        let canonical_length = header
            .checked_add(canonical_state.len())
            .and_then(|count| count.checked_add(canonical_organizer.len()))
            .ok_or(MaterialWorldError::Arithmetic)?;
        if canonical_length > MAX_MATERIAL_WORLD_REGISTER_BYTES {
            return Err(MaterialWorldError::ByteLimit);
        }
        if canonical_state != state_bytes || canonical_organizer != organizer_wire {
            return Err(MaterialWorldError::Wire);
        }
        drop(canonical_state);
        drop(canonical_organizer);
        let digest = content_digest::sha256_of(&bytes);
        let canonical_bytes = match bytes {
            Cow::Owned(bytes) => SharedCanonicalBytes::from_vec(bytes),
            Cow::Borrowed(bytes) => SharedCanonicalBytes::from_slice(bytes)?,
        };
        Ok(Self {
            completed_tick: tick,
            state,
            organizer,
            canonical_bytes,
            catalog_digest: catalog.catalog_digest(),
            digest,
        })
    }

    /// Prepare one next-period successor without mutating this register.
    /// The existing material transition executes arrivals, prior commitments,
    /// dispatch and following-period commitments in its governed order.
    /// # Errors
    /// Refuses any circuit or receipt encoding failure without changing this owner.
    pub fn prepare_next(
        &self,
        catalog: &MaterialCatalog,
    ) -> Result<PreparedMaterialWorld, MaterialWorldError> {
        let transition = babylon_material_circuit::advance_material_circuit(catalog, &self.state)?;
        self.prepare_transition(catalog, transition, None)
    }

    /// Seal the result of the shared closed-period planner on this exact opening.
    pub(crate) fn prepare_transition(
        &self,
        catalog: &MaterialCatalog,
        transition: MaterialCircuitTransition,
        commitment: Option<&OrganizerCommitment>,
    ) -> Result<PreparedMaterialWorld, MaterialWorldError> {
        if self.state.period.checked_add(1) != Some(transition.state.period) {
            return Err(MaterialWorldError::PeriodMismatch);
        }
        let receipts = encode_material_receipts(self.state.period, &transition)?;
        let organizer_facts = self
            .organizer_config()
            .map(|config| organizer_workplace_facts(config, catalog, &self.state, &transition))
            .transpose()?;
        let organizer_aid_support = match (self.organizer_config(), self.organizer_state()) {
            (Some(config), Some(organizer)) => {
                organizer_support::facts(config, organizer, commitment, &self.state, &transition)?
            }
            (None, None) if commitment.is_none() => Vec::new(),
            _ => return Err(MaterialWorldError::Wire),
        };
        let organizer_collection_fact = match self.organizer_config() {
            Some(config) => organizer_collection::support(
                config,
                commitment,
                &transition.collections,
                &transition.state,
            )?,
            None if transition.collections.is_empty() => None,
            None => return Err(MaterialWorldError::Wire),
        };
        let register = Self::from_validated_candidate(catalog, transition.state)?;
        Ok(PreparedMaterialWorld {
            prior_digest: self.digest,
            register,
            receipt_bytes: receipts,
            organizer_facts,
            organizer_aid_support,
            organizer_collection_fact,
        })
    }
}

/// Detached exact successor and its immutable material event evidence.
#[derive(Debug, PartialEq, Eq)]
pub struct PreparedMaterialWorld {
    prior_digest: [u8; 32],
    register: MaterialWorldRegister,
    receipt_bytes: Vec<u8>,
    organizer_facts: Option<OrganizerWorkplaceFacts>,
    organizer_aid_support: Vec<OrganizerAidSupport>,
    organizer_collection_fact: Option<OrganizerCollectionFact>,
}

impl PreparedMaterialWorld {
    pub(crate) fn organizer_collection_fact(&self) -> Option<&OrganizerCollectionFact> {
        self.organizer_collection_fact.as_ref()
    }
    pub(crate) fn organizer_aid_support(&self) -> &[OrganizerAidSupport] {
        &self.organizer_aid_support
    }
    pub(crate) fn organizer_period_time_resources(
        &self,
        config: &OrganizerConfig,
    ) -> Result<OrganizerPeriodTimeResources, MaterialWorldError> {
        organizer_time::resources(&self.register.state, config, self.register.completed_tick)
    }

    pub(crate) fn set_organizer_with_household_time(
        &mut self,
        catalog: &MaterialCatalog,
        config: OrganizerConfig,
        organizer: OrganizerState,
        journal: OrganizerPeriodJournal,
    ) -> Result<(), MaterialWorldError> {
        let entries = journal.latest().ok_or(MaterialWorldError::Wire)?;
        let uses = organizer_time::uses(
            &config,
            &organizer,
            entries,
            self.register.completed_tick,
            &self.register.state,
        )?;
        let mut state = self.register.state.clone();
        babylon_material_circuit::consume_household_contributions(
            catalog,
            &mut state,
            self.register.completed_tick,
            &uses,
        )?;
        // Contributions debit a separate ledger; the material time partition is
        // still the gross supply actually closed before later political work.
        self.register = MaterialWorldRegister::build(
            catalog,
            self.register.completed_tick,
            state,
            Some((config, organizer, journal)),
        )?;
        Ok(())
    }
    #[must_use]
    pub fn organizer_workplace_facts(&self) -> Option<&OrganizerWorkplaceFacts> {
        self.organizer_facts.as_ref()
    }

    pub(crate) fn set_organizer(
        &mut self,
        catalog: &MaterialCatalog,
        config: OrganizerConfig,
        state: OrganizerState,
        journal: OrganizerPeriodJournal,
    ) -> Result<(), MaterialWorldError> {
        self.register = MaterialWorldRegister::build(
            catalog,
            self.register.completed_tick,
            self.register.state.clone(),
            Some((config, state, journal)),
        )?;
        Ok(())
    }
    #[must_use]
    pub const fn prior_digest(&self) -> [u8; 32] {
        self.prior_digest
    }
    #[must_use]
    pub const fn register(&self) -> &MaterialWorldRegister {
        &self.register
    }
    #[must_use]
    pub fn receipt_bytes(&self) -> &[u8] {
        &self.receipt_bytes
    }
    #[must_use]
    pub fn into_register(self) -> MaterialWorldRegister {
        self.register
    }
}

pub(crate) fn encode_bound_organizer(
    completed_tick: u64,
    circuit: &MaterialCircuitState,
    organizer: Option<&(OrganizerConfig, OrganizerState, OrganizerPeriodJournal)>,
) -> Result<Vec<u8>, MaterialWorldError> {
    let Some((config, state, journal)) = organizer else {
        return Ok(vec![0]);
    };
    organizer_collection::validate_binding(config, circuit)?;
    organizer_collection::current(config, state, journal, circuit, completed_tick)?;
    babylon_practice_contract::validate_organizer_journal(config, state, journal)?;
    if state.period != completed_tick {
        return Err(MaterialWorldError::PeriodMismatch);
    }
    let mut result = vec![1];
    for bytes in [
        babylon_practice_contract::encode_organizer_config(config)?,
        babylon_practice_contract::encode_organizer_state(state)?,
        babylon_practice_contract::encode_organizer_journal(config, journal)?,
    ] {
        result.extend_from_slice(
            &u64::try_from(bytes.len())
                .map_err(|_| MaterialWorldError::ByteLimit)?
                .to_be_bytes(),
        );
        result.extend_from_slice(&bytes);
    }
    Ok(result)
}

pub(crate) fn take_organizer_section<'a>(
    remaining: &mut &'a [u8],
) -> Result<&'a [u8], MaterialWorldError> {
    let prefix = remaining.get(..8).ok_or(MaterialWorldError::Wire)?;
    let length = usize::try_from(u64::from_be_bytes(
        prefix.try_into().map_err(|_| MaterialWorldError::Wire)?,
    ))
    .map_err(|_| MaterialWorldError::ByteLimit)?;
    let end = 8_usize
        .checked_add(length)
        .ok_or(MaterialWorldError::ByteLimit)?;
    let section = remaining.get(8..end).ok_or(MaterialWorldError::Wire)?;
    *remaining = remaining.get(end..).ok_or(MaterialWorldError::Wire)?;
    Ok(section)
}

pub(crate) fn organizer_workplace_facts(
    config: &OrganizerConfig,
    catalog: &MaterialCatalog,
    opening: &MaterialCircuitState,
    transition: &MaterialCircuitTransition,
) -> Result<OrganizerWorkplaceFacts, MaterialWorldError> {
    let process_id = babylon_material_circuit::ProcessId::from_bytes(config.workplace_process_id);
    let output = catalog
        .process_outputs
        .iter()
        .find(|row| row.process_id == process_id)
        .ok_or(MaterialWorldError::Wire)?;
    let produced_batches = transition
        .production
        .iter()
        .find(|row| row.process_id == process_id)
        .map_or(0, |receipt| receipt.produced_batches);
    let labor = catalog
        .labor_coefficients
        .iter()
        .find(|row| row.process_id == process_id)
        .ok_or(MaterialWorldError::Wire)?;
    let (maintenance_enabled_batches, maintenance_consumed_batches, maintenance_expired_batches) =
        match (
            &catalog.maintenance_binding,
            &opening.maintenance_service,
            &transition.maintenance,
        ) {
            (None, None, None) => (0, 0, 0),
            (Some(binding), Some(service), Some(receipt))
                if receipt.binding == *binding
                    && service.period == opening.period
                    && receipt.period == opening.period
                    && receipt.opening_service_batches == service.available_batches =>
            {
                if binding.consumer_process_id == process_id {
                    (
                        receipt.opening_service_batches,
                        receipt.consumed_service_batches,
                        receipt.expired_service_batches,
                    )
                } else {
                    (0, 0, 0)
                }
            }
            _ => return Err(MaterialWorldError::Wire),
        };
    let mass = catalog
        .commodities
        .iter()
        .find(|row| row.good_id == output.good_id && row.unit_id == output.unit_id)
        .ok_or(MaterialWorldError::Wire)?;
    let produced_units = produced_batches
        .checked_mul(output.quantity_per_batch)
        .ok_or(MaterialWorldError::Arithmetic)?;
    let output_grams = u128::from(produced_units)
        .checked_mul(u128::from(
            catalog
                .grams_per_unit(mass.good_id, mass.unit_id)
                .map_err(|_| MaterialWorldError::Wire)?,
        ))
        .ok_or(MaterialWorldError::Arithmetic)?;
    if output_grams % 1_000 != 0 {
        // The current report promises exact whole kilograms; never round away goods.
        return Err(MaterialWorldError::Wire);
    }
    let output_kg =
        u64::try_from(output_grams / 1_000).map_err(|_| MaterialWorldError::Arithmetic)?;
    Ok(OrganizerWorkplaceFacts {
        period: opening.period,
        workplace_id: config.workplace_id,
        performed_labor_hours: produced_batches
            .checked_mul(labor.quantity_per_batch)
            .ok_or(MaterialWorldError::Arithmetic)?,
        output_kg,
        maintenance_enabled_batches,
        maintenance_consumed_batches,
        maintenance_expired_batches,
    })
}

/// Successor nominal identity, binding both the graph world's identity and material state.
#[must_use]
pub fn nominal_material_world_hash(
    graph_world_hash: [u8; 32],
    register: &MaterialWorldRegister,
) -> [u8; 32] {
    let mut bytes = [0_u8; NOMINAL_DOMAIN.len() + 68];
    let domain = NOMINAL_DOMAIN.len();
    bytes[..domain].copy_from_slice(NOMINAL_DOMAIN);
    bytes[domain..domain + 4].copy_from_slice(&3_u32.to_be_bytes());
    bytes[domain + 4..domain + 36].copy_from_slice(&graph_world_hash);
    bytes[domain + 36..domain + 68].copy_from_slice(&register.digest);
    content_digest::sha256_of(&bytes[..domain + 68])
}

pub(crate) fn bounded_bytes(length: usize, maximum: usize) -> Result<Vec<u8>, MaterialWorldError> {
    if length > maximum {
        return Err(MaterialWorldError::ByteLimit);
    }
    let mut bytes = Vec::new();
    bytes
        .try_reserve_exact(length)
        .map_err(|_| MaterialWorldError::Allocation)?;
    Ok(bytes)
}

/// Canonical collection limit for an admitted zero-based receipt family.
/// Callers must first require `index < RECEIPT_FAMILY_COUNT`.
#[must_use]
pub const fn receipt_row_limit(index: usize) -> usize {
    match index {
        6 => babylon_material_circuit::MAX_HANDLING_RECEIPTS_PER_PERIOD,
        10 => babylon_material_circuit::MAX_MONEY_TRANSFERS_PER_PERIOD,
        19 => babylon_material_circuit::MAX_SERVICE_RECEIPTS_PER_PERIOD,
        11 | 27 | 28 => babylon_material_circuit::MAX_STAFFING_MEMBERS,
        15 => babylon_material_circuit::MAX_REPLENISHMENT_POLICIES,
        18 | 24 => babylon_material_circuit::MAX_MONETARY_ACCOUNTS,
        25 => babylon_material_circuit::MAX_OWNERSHIP_CLAIMS,
        34 => babylon_material_circuit::MAX_AID_RECEIPTS_PER_PERIOD,
        35 => 1,
        _ => babylon_material_circuit::MAX_MATERIAL_CIRCUIT_ROWS,
    }
}

pub(crate) fn encode_handling_receipts(
    rows: &[babylon_material_circuit::MerchantHandlingReceipt],
    bytes: &mut Vec<u8>,
) -> Result<(), MaterialWorldError> {
    use babylon_material_circuit::OutboundOrderId;
    for row in rows {
        bytes.extend_from_slice(&row.site_id.as_bytes());
        let (tag, id) = match row.order {
            OutboundOrderId::Delivery(id) => (1, id),
            OutboundOrderId::LocalFinalDemand(id) => (2, id),
            OutboundOrderId::Service(_) => return Err(MaterialWorldError::Wire),
        };
        bytes.push(tag);
        bytes.extend_from_slice(&id.as_bytes());
        for quantity in [
            row.feasible_quantity,
            row.handled_quantity,
            row.needed_hours,
            row.used_hours,
        ] {
            bytes.extend_from_slice(&quantity.to_be_bytes());
        }
    }
    Ok(())
}

macro_rules! encode_receipt_family_rows {
    ($tag:expr, $source:expr, $tick:expr, $bytes:expr) => {
        match $tag {
            0 => {
                for row in &$source.production {
                    $bytes.extend_from_slice(&row.process_id.as_bytes());
                    $bytes.extend_from_slice(&row.site_id.as_bytes());
                    $bytes.extend_from_slice(&row.planned_batches.to_be_bytes());
                    $bytes.extend_from_slice(&row.produced_batches.to_be_bytes());
                }
            }
            1 => {
                for row in &$source.dispatches {
                    $bytes.extend_from_slice(&row.lot_id.as_bytes());
                    $bytes.extend_from_slice(&row.order_id.as_bytes());
                    $bytes.extend_from_slice(&row.route_id.as_bytes());
                    $bytes.extend_from_slice(&row.quantity.to_be_bytes());
                    $bytes.extend_from_slice(&row.final_arrival_period.to_be_bytes());
                }
            }
            2 => {
                for row in &$source.losses {
                    $bytes.extend_from_slice(&row.lot_id.as_bytes());
                    $bytes.extend_from_slice(&row.order_id.as_bytes());
                    $bytes.extend_from_slice(&row.route_id.as_bytes());
                    $bytes.extend_from_slice(&row.stage_index.to_be_bytes());
                    $bytes.extend_from_slice(&row.quantity.to_be_bytes());
                }
            }
            3 => {
                for row in &$source.arrivals {
                    $bytes.extend_from_slice(&row.order_id.as_bytes());
                    $bytes.extend_from_slice(&row.quantity.to_be_bytes());
                }
            }
            4 => {
                for row in &$source.deliveries {
                    $bytes.extend_from_slice(&row.order_id.as_bytes());
                    $bytes.extend_from_slice(&row.quantity.to_be_bytes());
                }
            }
            5 => {
                for row in &$source.realizations {
                    $bytes.extend_from_slice(&row.order_id.as_bytes());
                    $bytes.extend_from_slice(&row.quantity.to_be_bytes());
                }
            }
            6 => encode_handling_receipts(&$source.handling, &mut $bytes)?,
            7 => {
                for row in &$source.local_fulfillments {
                    $bytes.extend_from_slice(&row.order_id.as_bytes());
                    $bytes.extend_from_slice(&row.retailer_site_id.as_bytes());
                    $bytes.extend_from_slice(&row.demand_principal_id.as_bytes());
                    $bytes.extend_from_slice(&row.good_id.as_bytes());
                    $bytes.extend_from_slice(&row.unit_id.as_bytes());
                    $bytes.extend_from_slice(&row.quantity.to_be_bytes());
                }
            }
            8 => {
                for row in &$source.local_transfers {
                    $bytes.extend_from_slice(&row.order_id.as_bytes());
                    $bytes.extend_from_slice(&row.supplier_site_id.as_bytes());
                    $bytes.extend_from_slice(&row.buyer_site_id.as_bytes());
                    $bytes.extend_from_slice(&row.good_id.as_bytes());
                    $bytes.extend_from_slice(&row.unit_id.as_bytes());
                    $bytes.extend_from_slice(&row.quantity.to_be_bytes());
                }
            }
            9 => {
                if let Some(row) = &$source.maintenance {
                    maintenance_receipt::encode(row, $tick, &mut $bytes)?;
                }
            }
            10 => {
                for row in &$source.money_transfers {
                    monetary_receipt::encode_transfer(row, &mut $bytes)?;
                }
            }
            11 => {
                for row in &$source.wage_accruals {
                    monetary_receipt::encode_accrual(row, $tick, &mut $bytes)?;
                }
            }
            12 => {
                for row in &$source.labor_use {
                    monetary_receipt::encode_labor(row, $tick, &mut $bytes)?;
                }
            }
            13 => {
                for row in &$source.household_demand {
                    recurring_receipt::encode_demand(row, $tick, &mut $bytes)?;
                }
            }
            14 => {
                for row in &$source.household_consumption {
                    recurring_receipt::encode_consumption(row, $tick, &mut $bytes)?;
                }
            }
            15 => {
                for row in &$source.procurement {
                    recurring_receipt::encode_procurement(row, $tick, &mut $bytes)?;
                }
            }
            16 => {
                for row in &$source.production_plans {
                    recurring_receipt::encode_plan(row, $tick, &mut $bytes)?;
                }
            }
            17 => {
                for row in &$source.prices {
                    recurring_receipt::encode_price(row, $tick, &mut $bytes)?;
                }
            }
            18 => income_receipt::encode(&$source.income, $tick, &mut $bytes)?,
            19 => service_receipt::encode_performance(
                &$source.service_performance,
                $tick,
                &mut $bytes,
            )?,
            20 => {
                service_receipt::encode_households(&$source.household_services, $tick, &mut $bytes)?
            }
            21 => service_receipt::encode_markets(&$source.service_markets, $tick, &mut $bytes)?,
            22 => service_receipt::encode_outputs(&$source.service_outputs, $tick, &mut $bytes)?,
            23 => financial_receipt::encode_public_budgets(
                &$source.public_budgets,
                $tick,
                &mut $bytes,
            )?,
            24 => financial_receipt::encode_taxes(&$source.taxes, $tick, &mut $bytes)?,
            25 => {
                financial_receipt::encode_distributions(&$source.distributions, $tick, &mut $bytes)?
            }
            26 => {
                financial_receipt::encode_contributions(&$source.contributions, $tick, &mut $bytes)?
            }
            27 => {
                for row in &$source.staffing_members {
                    workforce_receipt::encode_staffing(row, $tick, &mut $bytes)?;
                }
            }
            28 => {
                for row in &$source.member_labor_use {
                    workforce_receipt::encode_attendance(row, $tick, &mut $bytes)?;
                }
            }
            29 => {
                equipment_receipt::encode_installation(&$source.installation, $tick, &mut $bytes)?;
            }
            30 => equipment_receipt::encode_wear(&$source.equipment_wear, $tick, &mut $bytes)?,
            31 => equipment_receipt::encode_investment(&$source.investment, $tick, &mut $bytes)?,
            32 => {
                installation_decision::encode(&$source.installation_decisions, $tick, &mut $bytes)?;
            }
            33 => household_time_receipt::encode(&$source.household_time, $tick, &mut $bytes)?,
            34 => aid_receipt::encode(&$source.aid, $tick, &mut $bytes)?,
            35 => collection_receipt::encode(&$source.collections, $tick, &mut $bytes)?,
            _ => unreachable!("the thirty-five material receipt families are closed"),
        }
    };
}

#[allow(
    clippy::too_many_lines,
    reason = "one match arm per closed receipt family keeps each family's encoder beside the shared cursor"
)]
pub(crate) fn encode_material_receipts(
    tick: u64,
    transition: &MaterialCircuitTransition,
) -> Result<Vec<u8>, MaterialWorldError> {
    if tick == 0 {
        return Err(MaterialWorldError::Wire);
    }
    let counts: [usize; RECEIPT_FAMILY_COUNT] = [
        transition.production.len(),
        transition.dispatches.len(),
        transition.losses.len(),
        transition.arrivals.len(),
        transition.deliveries.len(),
        transition.realizations.len(),
        transition.handling.len(),
        transition.local_fulfillments.len(),
        transition.local_transfers.len(),
        usize::from(transition.maintenance.is_some()),
        transition.money_transfers.len(),
        transition.wage_accruals.len(),
        transition.labor_use.len(),
        transition.household_demand.len(),
        transition.household_consumption.len(),
        transition.procurement.len(),
        transition.production_plans.len(),
        transition.prices.len(),
        transition.income.len(),
        transition.service_performance.len(),
        transition.household_services.len(),
        transition.service_markets.len(),
        transition.service_outputs.len(),
        transition.public_budgets.len(),
        transition.taxes.len(),
        transition.distributions.len(),
        transition.contributions.len(),
        transition.staffing_members.len(),
        transition.member_labor_use.len(),
        transition.installation.len(),
        transition.equipment_wear.len(),
        transition.investment.len(),
        transition.installation_decisions.len(),
        transition.household_time.len(),
        transition.aid.len(),
        transition.collections.len(),
    ];
    let families: [(usize, usize); RECEIPT_FAMILY_COUNT] =
        std::array::from_fn(|index| (counts[index], RECEIPT_ROW_BYTES[index]));
    if families
        .iter()
        .enumerate()
        .any(|(index, (count, _))| *count > receipt_row_limit(index))
    {
        return Err(MaterialWorldError::ByteLimit);
    }
    monetary_receipt::validate_order(&transition.wage_accruals, &transition.labor_use)?;
    workforce_receipt::validate_join(
        &transition.staffing_members,
        &transition.member_labor_use,
        &transition.labor_use,
        &transition.wage_accruals,
    )?;
    equipment_receipt::validate_order(
        &transition.installation,
        &transition.equipment_wear,
        &transition.investment,
    )?;
    equipment_receipt::validate_installation(
        &transition.installation,
        &transition.member_labor_use,
        &transition.income,
    )?;
    equipment_receipt::validate_wear(
        &transition.equipment_wear,
        &transition.production,
        &transition.income,
    )?;
    equipment_receipt::validate_investment(&transition.investment, &transition.money_transfers)?;
    installation_decision::validate(&transition.installation_decisions, &transition.installation)?;
    income_receipt::validate_order(&transition.income)?;
    aid_receipt::validate(&transition.aid, tick)?;
    aid_receipt::validate_state(&transition.aid, &transition.state)?;
    collection_receipt::validate(
        &transition.collections,
        &transition.money_transfers,
        &transition.household_time,
        &transition.income,
        &transition.aid,
        tick,
    )?;
    collection_receipt::validate_state(&transition.collections, &transition.state)?;
    financial_receipt::validate(
        &transition.public_budgets,
        &transition.taxes,
        &transition.distributions,
        &transition.contributions,
        &transition.money_transfers,
    )?;
    service_receipt::validate_order(
        &transition.service_performance,
        &transition.household_services,
        &transition.service_markets,
        &transition.service_outputs,
    )?;
    recurring_receipt::validate_order(
        &transition.household_demand,
        &transition.household_consumption,
        &transition.procurement,
        &transition.production_plans,
        &transition.prices,
    )?;
    household_time_receipt::validate(
        &transition.household_time,
        &transition.member_labor_use,
        tick,
    )?;
    household_time_receipt::validate_state(&transition.state, &transition.household_time)?;
    let length = families.iter().try_fold(
        RECEIPT_DOMAIN.len() + 12 + families.len() * 9,
        |total, (count, width)| {
            total
                .checked_add(
                    count
                        .checked_mul(*width)
                        .ok_or(MaterialWorldError::Arithmetic)?,
                )
                .ok_or(MaterialWorldError::Arithmetic)
        },
    )?;
    let mut bytes = bounded_bytes(length, MAX_MATERIAL_TICK_RECEIPT_BYTES)?;
    bytes.extend_from_slice(RECEIPT_DOMAIN);
    bytes.extend_from_slice(&18_u32.to_be_bytes());
    bytes.extend_from_slice(&tick.to_be_bytes());
    for (tag, (count, _)) in families.iter().enumerate() {
        bytes.push(u8::try_from(tag + 1).map_err(|_| MaterialWorldError::Arithmetic)?);
        bytes.extend_from_slice(
            &u64::try_from(*count)
                .map_err(|_| MaterialWorldError::Arithmetic)?
                .to_be_bytes(),
        );
        encode_receipt_family_rows!(tag, transition, tick, &mut bytes);
    }
    debug_assert_eq!(bytes.len(), length);
    Ok(bytes)
}

/// Encode one closed receipt family exactly as the committed V18 frame does.
///
/// The permanent-journal extractor hashes this deterministic row encoding for
/// rows it summarizes rather than retains.
///
/// # Errors
///
/// Refuses a zero tick, a family tag outside the closed 1..=36 registry, or any
/// family encoder fault.
pub fn receipt_family_bytes(
    tick: u64,
    receipts: &MaterialTickReceipts,
    family: u8,
) -> Result<Vec<u8>, MaterialWorldError> {
    if tick == 0 || !(1..=36).contains(&family) {
        return Err(MaterialWorldError::Wire);
    }
    let mut bytes = Vec::new();
    encode_receipt_family_rows!(usize::from(family - 1), receipts, tick, &mut bytes);
    Ok(bytes)
}

/// Exact committed row count of one closed receipt family.
#[must_use]
pub fn receipt_family_rows(receipts: &MaterialTickReceipts, family: u8) -> usize {
    match family {
        1 => receipts.production.len(),
        2 => receipts.dispatches.len(),
        3 => receipts.losses.len(),
        4 => receipts.arrivals.len(),
        5 => receipts.deliveries.len(),
        6 => receipts.realizations.len(),
        7 => receipts.handling.len(),
        8 => receipts.local_fulfillments.len(),
        9 => receipts.local_transfers.len(),
        10 => usize::from(receipts.maintenance.is_some()),
        11 => receipts.money_transfers.len(),
        12 => receipts.wage_accruals.len(),
        13 => receipts.labor_use.len(),
        14 => receipts.household_demand.len(),
        15 => receipts.household_consumption.len(),
        16 => receipts.procurement.len(),
        17 => receipts.production_plans.len(),
        18 => receipts.prices.len(),
        19 => receipts.income.len(),
        20 => receipts.service_performance.len(),
        21 => receipts.household_services.len(),
        22 => receipts.service_markets.len(),
        23 => receipts.service_outputs.len(),
        24 => receipts.public_budgets.len(),
        25 => receipts.taxes.len(),
        26 => receipts.distributions.len(),
        27 => receipts.contributions.len(),
        28 => receipts.staffing_members.len(),
        29 => receipts.member_labor_use.len(),
        30 => receipts.installation.len(),
        31 => receipts.equipment_wear.len(),
        32 => receipts.investment.len(),
        33 => receipts.installation_decisions.len(),
        34 => receipts.household_time.len(),
        35 => receipts.aid.len(),
        36 => receipts.collections.len(),
        _ => 0,
    }
}

/// Typed material evidence decoded only from an exact committed V18 receipt family.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MaterialTickReceipts {
    pub household_time: Vec<HouseholdTimeReceipt>,
    pub aid: Vec<AidReceipt>,
    pub collections: Vec<CollectionReceipt>,
    pub installation: Vec<InstallationReceipt>,
    pub installation_decisions: Vec<InstallationDecisionReceipt>,
    pub equipment_wear: Vec<EquipmentWearReceipt>,
    pub investment: Vec<InvestmentReceipt>,
    pub staffing_members: Vec<StaffingMemberReceipt>,
    pub member_labor_use: Vec<MemberLaborUseReceipt>,
    pub public_budgets: Vec<PublicBudgetReceipt>,
    pub taxes: Vec<TaxReceipt>,
    pub distributions: Vec<DistributionReceipt>,
    pub contributions: Vec<CapitalContributionReceipt>,

    pub service_performance: Vec<ServicePerformanceReceipt>,
    pub household_services: Vec<HouseholdServiceReceipt>,
    pub service_markets: Vec<ServiceMarketReceipt>,
    pub service_outputs: Vec<ServiceOutputReceipt>,
    pub income: Vec<IncomeReceipt>,
    pub resolve_tick: u64,
    pub household_demand: Vec<HouseholdDemandReceipt>,
    pub household_consumption: Vec<HouseholdConsumptionReceipt>,
    pub procurement: Vec<ProcurementReceipt>,
    pub production_plans: Vec<ProductionPlanReceipt>,
    pub prices: Vec<PriceReceipt>,
    pub money_transfers: Vec<MoneyTransferReceipt>,
    pub wage_accruals: Vec<WageAccrualReceipt>,
    pub labor_use: Vec<LaborUseReceipt>,
    pub production: Vec<babylon_material_circuit::ProductionReceipt>,
    pub dispatches: Vec<babylon_material_circuit::RoutedDispatchReceipt>,
    pub losses: Vec<babylon_material_circuit::FreightLossReceipt>,
    pub arrivals: Vec<babylon_material_circuit::ArrivalReceipt>,
    pub deliveries: Vec<babylon_material_circuit::DeliveryReceipt>,
    pub realizations: Vec<babylon_material_circuit::RealizationReceipt>,
    pub handling: Vec<babylon_material_circuit::MerchantHandlingReceipt>,
    pub local_fulfillments: Vec<babylon_material_circuit::LocalRetailFulfillmentReceipt>,
    pub local_transfers: Vec<babylon_material_circuit::LocalTransferReceipt>,
    pub maintenance: Option<MaintenanceReceipt>,
}

/// Shared handle to one immutable committed receipt family.
///
/// Storage admission and every observer hold this handle instead of naming the
/// backing shared pointer, so the ownership decision stays in one place.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MaterialReceiptHandle(
    // STYLE-EXCEPTION(EXC-04): one immutable receipt family shared by storage and observers.
    Arc<MaterialTickReceipts>,
);

impl MaterialReceiptHandle {
    /// Bind a decoded receipt family into its one shared owner.
    #[must_use]
    pub fn new(receipts: MaterialTickReceipts) -> Self {
        // STYLE-EXCEPTION(EXC-04): one immutable receipt family shared by storage and observers.
        Self(Arc::new(receipts))
    }

    /// Whether both handles share one admitted receipt family.
    #[must_use]
    pub fn shares_allocation(&self, other: &Self) -> bool {
        // STYLE-EXCEPTION(EXC-04): witness reuse is asserted through this allocation check.
        Arc::ptr_eq(&self.0, &other.0)
    }
}

impl Deref for MaterialReceiptHandle {
    type Target = MaterialTickReceipts;

    fn deref(&self) -> &Self::Target {
        &self.0
    }
}

impl AsRef<MaterialTickReceipts> for MaterialReceiptHandle {
    fn as_ref(&self) -> &MaterialTickReceipts {
        &self.0
    }
}

/// Decode a bounded receipt family. Hash/campaign binding belongs to its V3 envelope.
/// # Errors
/// Refuses versions, tags, counts, truncation, trailing bytes and invalid quantity relations.
#[allow(
    clippy::too_many_lines,
    reason = "one match arm per closed receipt family keeps each family's decoder beside the shared cursor"
)]
pub fn decode_material_receipts(bytes: &[u8]) -> Result<MaterialTickReceipts, MaterialWorldError> {
    if bytes.len() > MAX_MATERIAL_TICK_RECEIPT_BYTES || !bytes.starts_with(RECEIPT_DOMAIN) {
        return Err(MaterialWorldError::Wire);
    }
    let mut cursor = ReceiptCursor {
        bytes,
        position: RECEIPT_DOMAIN.len(),
    };
    if cursor.take::<4>()? != 18_u32.to_be_bytes() {
        return Err(MaterialWorldError::Wire);
    }
    let resolve_tick = cursor.u64()?;
    if resolve_tick == 0 {
        return Err(MaterialWorldError::Wire);
    }
    let mut result = MaterialTickReceipts {
        household_time: Vec::new(),
        aid: Vec::new(),
        collections: Vec::new(),
        installation: Vec::new(),
        installation_decisions: Vec::new(),
        equipment_wear: Vec::new(),
        investment: Vec::new(),
        staffing_members: vec![],
        member_labor_use: vec![],
        public_budgets: vec![],
        taxes: vec![],
        distributions: vec![],
        contributions: vec![],

        service_performance: vec![],
        household_services: vec![],
        service_markets: vec![],
        service_outputs: vec![],
        income: Vec::new(),
        resolve_tick,
        household_demand: Vec::new(),
        household_consumption: Vec::new(),
        procurement: Vec::new(),
        production_plans: Vec::new(),
        prices: Vec::new(),
        money_transfers: Vec::new(),
        wage_accruals: Vec::new(),
        labor_use: Vec::new(),
        production: Vec::new(),
        dispatches: Vec::new(),
        losses: Vec::new(),
        arrivals: Vec::new(),
        deliveries: Vec::new(),
        realizations: Vec::new(),
        handling: Vec::new(),
        local_fulfillments: Vec::new(),
        local_transfers: Vec::new(),
        maintenance: None,
    };
    for tag in 1..=36 {
        if cursor.take::<1>()? != [tag] {
            return Err(MaterialWorldError::Wire);
        }
        let count = usize::try_from(cursor.u64()?).map_err(|_| MaterialWorldError::ByteLimit)?;
        if count > receipt_row_limit(usize::from(tag - 1)) {
            return Err(MaterialWorldError::ByteLimit);
        }
        if tag == 10 && count > 1 {
            return Err(MaterialWorldError::Wire);
        }
        let width = [
            80_usize,
            112,
            106,
            40,
            40,
            40,
            97,
            168,
            168,
            maintenance_receipt::ROW_BYTES,
            monetary_receipt::TRANSFER_BYTES,
            monetary_receipt::ACCRUAL_BYTES,
            monetary_receipt::LABOR_BYTES,
            recurring_receipt::DEMAND_BYTES,
            recurring_receipt::CONSUMPTION_BYTES,
            recurring_receipt::PROCUREMENT_BYTES,
            recurring_receipt::PLAN_BYTES,
            recurring_receipt::PRICE_BYTES,
            income_receipt::ROW_BYTES,
            service_receipt::PERFORMANCE_BYTES,
            service_receipt::HOUSEHOLD_BYTES,
            service_receipt::MARKET_BYTES,
            service_receipt::OUTPUT_BYTES,
            financial_receipt::PUBLIC_BUDGETS_BYTES,
            financial_receipt::TAXES_BYTES,
            financial_receipt::DISTRIBUTIONS_BYTES,
            financial_receipt::CONTRIBUTIONS_BYTES,
            workforce_receipt::STAFFING_BYTES,
            workforce_receipt::ATTENDANCE_BYTES,
            equipment_receipt::INSTALLATION_BYTES,
            equipment_receipt::WEAR_BYTES,
            equipment_receipt::INVESTMENT_BYTES,
            installation_decision::ROW_BYTES,
            household_time_receipt::ROW_BYTES,
            aid_receipt::ROW_BYTES,
            collection_receipt::ROW_BYTES,
        ][usize::from(tag - 1)];
        if count
            .checked_mul(width)
            .is_none_or(|length| length > bytes.len() - cursor.position)
        {
            return Err(MaterialWorldError::Wire);
        }
        match tag {
            1 => result.production.try_reserve_exact(count),
            2 => result.dispatches.try_reserve_exact(count),
            3 => result.losses.try_reserve_exact(count),
            4 => result.arrivals.try_reserve_exact(count),
            5 => result.deliveries.try_reserve_exact(count),
            6 => result.realizations.try_reserve_exact(count),
            7 => result.handling.try_reserve_exact(count),
            8 => result.local_fulfillments.try_reserve_exact(count),
            9 => result.local_transfers.try_reserve_exact(count),
            10 => Ok(()),
            11 => result.money_transfers.try_reserve_exact(count),
            12 => result.wage_accruals.try_reserve_exact(count),
            13 => result.labor_use.try_reserve_exact(count),
            14 => result.household_demand.try_reserve_exact(count),
            15 => result.household_consumption.try_reserve_exact(count),
            16 => result.procurement.try_reserve_exact(count),
            17 => result.production_plans.try_reserve_exact(count),
            18 => result.prices.try_reserve_exact(count),
            19 => result.income.try_reserve_exact(count),
            20 => result.service_performance.try_reserve_exact(count),
            21 => result.household_services.try_reserve_exact(count),
            22 => result.service_markets.try_reserve_exact(count),
            23 => result.service_outputs.try_reserve_exact(count),
            24 => result.public_budgets.try_reserve_exact(count),
            25 => result.taxes.try_reserve_exact(count),
            26 => result.distributions.try_reserve_exact(count),
            27 => result.contributions.try_reserve_exact(count),
            28 => result.staffing_members.try_reserve_exact(count),
            29 => result.member_labor_use.try_reserve_exact(count),
            30 => result.installation.try_reserve_exact(count),
            31 => result.equipment_wear.try_reserve_exact(count),
            32 => result.investment.try_reserve_exact(count),
            33 => result.installation_decisions.try_reserve_exact(count),
            34 => result.household_time.try_reserve_exact(count),
            35 => result.aid.try_reserve_exact(count),
            36 => result.collections.try_reserve_exact(count),

            _ => return Err(MaterialWorldError::Wire),
        }
        .map_err(|_| MaterialWorldError::Allocation)?;
        for _ in 0..count {
            match tag {
                36 => result
                    .collections
                    .push(collection_receipt::decode(&mut cursor, resolve_tick)?),
                35 => result
                    .aid
                    .push(aid_receipt::decode(&mut cursor, resolve_tick)?),
                34 => result
                    .household_time
                    .push(household_time_receipt::decode(&mut cursor, resolve_tick)?),
                30 => result
                    .installation
                    .push(equipment_receipt::decode_installation(
                        &mut cursor,
                        resolve_tick,
                    )?),
                31 => result
                    .equipment_wear
                    .push(equipment_receipt::decode_wear(&mut cursor, resolve_tick)?),
                32 => result.investment.push(equipment_receipt::decode_investment(
                    &mut cursor,
                    resolve_tick,
                )?),
                33 => result
                    .installation_decisions
                    .push(installation_decision::decode(&mut cursor, resolve_tick)?),
                1 => {
                    let process_id = ProcessId::from_bytes(cursor.take()?);
                    let site_id = SiteId::from_bytes(cursor.take()?);
                    let planned_batches = cursor.u64()?;
                    let produced_batches = cursor.u64()?;
                    if produced_batches > planned_batches {
                        return Err(MaterialWorldError::Wire);
                    }
                    result.production.push(ProductionReceipt {
                        process_id,
                        site_id,
                        planned_batches,
                        produced_batches,
                    });
                }
                2 => {
                    let lot_id = FreightLotId::from_bytes(cursor.take()?);
                    let order_id = OrderId::from_bytes(cursor.take()?);
                    let route_id = RouteId::from_bytes(cursor.take()?);
                    let quantity = cursor.positive()?;
                    let final_arrival_period = cursor.u64()?;
                    if final_arrival_period <= resolve_tick {
                        return Err(MaterialWorldError::Wire);
                    }
                    result.dispatches.push(RoutedDispatchReceipt {
                        lot_id,
                        order_id,
                        route_id,
                        quantity,
                        final_arrival_period,
                    });
                }
                3 => {
                    let lot_id = FreightLotId::from_bytes(cursor.take()?);
                    let order_id = OrderId::from_bytes(cursor.take()?);
                    let route_id = RouteId::from_bytes(cursor.take()?);
                    let stage_index = u16::from_be_bytes(cursor.take()?);
                    if usize::from(stage_index) >= MAX_ROUTE_STAGES_PER_ROUTE {
                        return Err(MaterialWorldError::Wire);
                    }
                    let quantity = cursor.positive()?;
                    result.losses.push(FreightLossReceipt {
                        lot_id,
                        order_id,
                        route_id,
                        stage_index,
                        quantity,
                    });
                }
                4 => result.arrivals.push(ArrivalReceipt {
                    order_id: OrderId::from_bytes(cursor.take()?),
                    quantity: cursor.positive()?,
                }),
                5 => result.deliveries.push(DeliveryReceipt {
                    order_id: OrderId::from_bytes(cursor.take()?),
                    quantity: cursor.positive()?,
                }),
                6 => result.realizations.push(RealizationReceipt {
                    order_id: OrderId::from_bytes(cursor.take()?),
                    quantity: cursor.positive()?,
                }),
                7 => {
                    let site_id = SiteId::from_bytes(cursor.take()?);
                    let [order_tag] = cursor.take()?;
                    let id = OrderId::from_bytes(cursor.take()?);
                    let order = match order_tag {
                        1 => OutboundOrderId::Delivery(id),
                        2 => OutboundOrderId::LocalFinalDemand(id),
                        _ => return Err(MaterialWorldError::Wire),
                    };
                    let feasible_quantity = cursor.u64()?;
                    let handled_quantity = cursor.u64()?;
                    let needed_hours = cursor.u64()?;
                    let used_hours = cursor.u64()?;
                    if handled_quantity > feasible_quantity
                        || used_hours > needed_hours
                        || (feasible_quantity == 0) != (needed_hours == 0)
                        || (handled_quantity == 0) != (used_hours == 0)
                        || u128::from(feasible_quantity) * u128::from(used_hours)
                            != u128::from(handled_quantity) * u128::from(needed_hours)
                        || result
                            .handling
                            .last()
                            .is_some_and(|row| (row.site_id, row.order) >= (site_id, order))
                    {
                        return Err(MaterialWorldError::Wire);
                    }
                    result.handling.push(MerchantHandlingReceipt {
                        site_id,
                        order,
                        feasible_quantity,
                        handled_quantity,
                        needed_hours,
                        used_hours,
                    });
                }
                8 => {
                    let row = LocalRetailFulfillmentReceipt {
                        order_id: OrderId::from_bytes(cursor.take()?),
                        retailer_site_id: SiteId::from_bytes(cursor.take()?),
                        demand_principal_id: FinalDemandPrincipalId::from_bytes(cursor.take()?),
                        good_id: GoodId::from_bytes(cursor.take()?),
                        unit_id: UnitId::from_bytes(cursor.take()?),
                        quantity: cursor.positive()?,
                    };
                    if result
                        .local_fulfillments
                        .last()
                        .is_some_and(|prior| prior.order_id >= row.order_id)
                    {
                        return Err(MaterialWorldError::Wire);
                    }
                    result.local_fulfillments.push(row);
                }
                9 => {
                    let row = LocalTransferReceipt {
                        order_id: OrderId::from_bytes(cursor.take()?),
                        supplier_site_id: SiteId::from_bytes(cursor.take()?),
                        buyer_site_id: SiteId::from_bytes(cursor.take()?),
                        good_id: GoodId::from_bytes(cursor.take()?),
                        unit_id: UnitId::from_bytes(cursor.take()?),
                        quantity: cursor.positive()?,
                    };
                    if row.supplier_site_id == row.buyer_site_id
                        || result
                            .local_transfers
                            .last()
                            .is_some_and(|prior| prior.order_id >= row.order_id)
                    {
                        return Err(MaterialWorldError::Wire);
                    }
                    result.local_transfers.push(row);
                }
                10 => {
                    result.maintenance =
                        Some(maintenance_receipt::decode(&mut cursor, resolve_tick)?);
                }
                11 => result
                    .money_transfers
                    .push(monetary_receipt::decode_transfer(&mut cursor)?),
                12 => result
                    .wage_accruals
                    .push(monetary_receipt::decode_accrual(&mut cursor, resolve_tick)?),
                13 => result
                    .labor_use
                    .push(monetary_receipt::decode_labor(&mut cursor, resolve_tick)?),
                14 => result
                    .household_demand
                    .push(recurring_receipt::decode_demand(&mut cursor, resolve_tick)?),
                15 => result
                    .household_consumption
                    .push(recurring_receipt::decode_consumption(
                        &mut cursor,
                        resolve_tick,
                    )?),
                16 => result
                    .procurement
                    .push(recurring_receipt::decode_procurement(
                        &mut cursor,
                        resolve_tick,
                    )?),
                17 => result
                    .production_plans
                    .push(recurring_receipt::decode_plan(&mut cursor, resolve_tick)?),
                18 => result
                    .prices
                    .push(recurring_receipt::decode_price(&mut cursor, resolve_tick)?),
                20 => result
                    .service_performance
                    .push(service_receipt::decode_performance(
                        &mut cursor,
                        resolve_tick,
                    )?),
                21 => result
                    .household_services
                    .push(service_receipt::decode_household(
                        &mut cursor,
                        resolve_tick,
                    )?),
                22 => result
                    .service_markets
                    .push(service_receipt::decode_market(&mut cursor, resolve_tick)?),
                23 => result
                    .service_outputs
                    .push(service_receipt::decode_output(&mut cursor, resolve_tick)?),
                24 => result
                    .public_budgets
                    .push(financial_receipt::decode_public_budgets(
                        &mut cursor,
                        resolve_tick,
                    )?),
                25 => result
                    .taxes
                    .push(financial_receipt::decode_taxes(&mut cursor, resolve_tick)?),
                26 => result
                    .distributions
                    .push(financial_receipt::decode_distributions(
                        &mut cursor,
                        resolve_tick,
                    )?),
                27 => result
                    .contributions
                    .push(financial_receipt::decode_contributions(
                        &mut cursor,
                        resolve_tick,
                    )?),
                28 => result
                    .staffing_members
                    .push(workforce_receipt::decode_staffing(
                        &mut cursor,
                        resolve_tick,
                    )?),
                29 => result
                    .member_labor_use
                    .push(workforce_receipt::decode_attendance(
                        &mut cursor,
                        resolve_tick,
                    )?),
                19 => result
                    .income
                    .push(income_receipt::decode(&mut cursor, resolve_tick)?),
                _ => return Err(MaterialWorldError::Wire),
            }
        }
    }
    if cursor.position != bytes.len() {
        return Err(MaterialWorldError::Wire);
    }
    monetary_receipt::validate_order(&result.wage_accruals, &result.labor_use)?;
    workforce_receipt::validate_join(
        &result.staffing_members,
        &result.member_labor_use,
        &result.labor_use,
        &result.wage_accruals,
    )?;
    equipment_receipt::validate_order(
        &result.installation,
        &result.equipment_wear,
        &result.investment,
    )?;
    equipment_receipt::validate_installation(
        &result.installation,
        &result.member_labor_use,
        &result.income,
    )?;
    equipment_receipt::validate_wear(&result.equipment_wear, &result.production, &result.income)?;
    equipment_receipt::validate_investment(&result.investment, &result.money_transfers)?;
    installation_decision::validate(&result.installation_decisions, &result.installation)?;
    income_receipt::validate_order(&result.income)?;
    aid_receipt::validate(&result.aid, resolve_tick)?;
    collection_receipt::validate(
        &result.collections,
        &result.money_transfers,
        &result.household_time,
        &result.income,
        &result.aid,
        resolve_tick,
    )?;
    financial_receipt::validate(
        &result.public_budgets,
        &result.taxes,
        &result.distributions,
        &result.contributions,
        &result.money_transfers,
    )?;
    service_receipt::validate_order(
        &result.service_performance,
        &result.household_services,
        &result.service_markets,
        &result.service_outputs,
    )?;
    recurring_receipt::validate_order(
        &result.household_demand,
        &result.household_consumption,
        &result.procurement,
        &result.production_plans,
        &result.prices,
    )?;
    household_time_receipt::validate(
        &result.household_time,
        &result.member_labor_use,
        resolve_tick,
    )?;
    Ok(result)
}

pub(crate) struct ReceiptCursor<'a> {
    pub(crate) bytes: &'a [u8],
    pub(crate) position: usize,
}

impl ReceiptCursor<'_> {
    pub(crate) fn take<const N: usize>(&mut self) -> Result<[u8; N], MaterialWorldError> {
        let end = self
            .position
            .checked_add(N)
            .ok_or(MaterialWorldError::Wire)?;
        let bytes = self
            .bytes
            .get(self.position..end)
            .ok_or(MaterialWorldError::Wire)?;
        self.position = end;
        bytes.try_into().map_err(|_| MaterialWorldError::Wire)
    }
    pub(crate) fn u64(&mut self) -> Result<u64, MaterialWorldError> {
        Ok(u64::from_be_bytes(self.take()?))
    }
    fn positive(&mut self) -> Result<u64, MaterialWorldError> {
        let value = self.u64()?;
        if value == 0 {
            Err(MaterialWorldError::Wire)
        } else {
            Ok(value)
        }
    }
}

/// Verify collection against the exact retained original command and shared time ledger.
/// # Errors
/// Refuses changed or missing receipt, mandate, actor, original action or consumed use.
pub fn validate_retained_collection(
    register: &MaterialWorldRegister,
    receipts: &MaterialTickReceipts,
) -> Result<(), MaterialWorldError> {
    if register.completed_tick() != receipts.resolve_tick {
        return Err(MaterialWorldError::PeriodMismatch);
    }
    match (
        register.organizer_config(),
        register.organizer_state(),
        register.organizer_journal(),
    ) {
        (Some(config), Some(organizer), Some(journal)) => organizer_collection::retained(
            config,
            organizer,
            journal,
            &receipts.collections,
            register.state(),
            receipts.resolve_tick,
        ),
        (None, None, None) if receipts.collections.is_empty() => Ok(()),
        _ => Err(MaterialWorldError::Wire),
    }
}
