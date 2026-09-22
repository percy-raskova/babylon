//! Exact successor world-register ownership for the routed material circuit.
//!
//! An active register contains the complete current opening state, never an economic
//! summary or a second inventory ledger. The graph-only digest stays unchanged.

use babylon_kernel::content_digest::sha256_of;
use babylon_material_circuit::{
    advance_material_circuit, decode_material_circuit_state, encode_material_circuit_state,
    MaterialCircuitError, MaterialCircuitState, MaterialCircuitTransition,
};
use babylon_practice_contract::{
    decode_organizer_config, decode_organizer_state, encode_organizer_config,
    encode_organizer_state, OrganizerConfig, OrganizerError, OrganizerState,
    OrganizerWorkplaceFacts,
};

mod maintenance_receipt;
mod monetary_receipt;
mod recurring_receipt;

const REGISTER_DOMAIN: &[u8] = b"babylon.material-world-register.v4\0";
const NOMINAL_DOMAIN: &[u8] = b"babylon.nominal-material-world.v3\0";
const RECEIPT_DOMAIN: &[u8] = b"babylon.material-tick-receipts.v7\0";
/// Shared identity ceiling inherited by the aggregate replay envelope.
pub const MAX_MATERIAL_WORLD_REGISTER_BYTES: usize = 67_108_864;

/// One checked complete material register at a completed four-week boundary.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MaterialWorldRegister {
    completed_tick: u64,
    state: MaterialCircuitState,
    organizer: Option<(OrganizerConfig, OrganizerState)>,
    canonical_bytes: Vec<u8>,
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
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
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
        completed_tick: u64,
        state: MaterialCircuitState,
    ) -> Result<Self, MaterialWorldError> {
        Self::build(completed_tick, state, None)
    }

    fn build(
        completed_tick: u64,
        state: MaterialCircuitState,
        organizer: Option<(OrganizerConfig, OrganizerState)>,
    ) -> Result<Self, MaterialWorldError> {
        if completed_tick
            .checked_add(1)
            .ok_or(MaterialWorldError::Arithmetic)?
            != state.period
        {
            return Err(MaterialWorldError::PeriodMismatch);
        }
        let state_bytes = encode_material_circuit_state(&state)?;
        let state = decode_material_circuit_state(&state_bytes)?;
        let mut organizer_bytes = Vec::new();
        match &organizer {
            None => organizer_bytes.push(0),
            Some((config, state)) => {
                babylon_practice_contract::validate_organizer_pair(config, state)?;
                if state.period != completed_tick {
                    return Err(MaterialWorldError::PeriodMismatch);
                }
                organizer_bytes.push(1);
                for bytes in [
                    encode_organizer_config(config)?,
                    encode_organizer_state(state)?,
                ] {
                    organizer_bytes.extend_from_slice(
                        &u64::try_from(bytes.len())
                            .map_err(|_| MaterialWorldError::ByteLimit)?
                            .to_be_bytes(),
                    );
                    organizer_bytes.extend_from_slice(&bytes);
                }
            }
        }
        let length = REGISTER_DOMAIN
            .len()
            .checked_add(20)
            .and_then(|count| count.checked_add(state_bytes.len()))
            .and_then(|count| count.checked_add(organizer_bytes.len()))
            .ok_or(MaterialWorldError::Arithmetic)?;
        let mut bytes = bounded_bytes(length)?;
        bytes.extend_from_slice(REGISTER_DOMAIN);
        bytes.extend_from_slice(&4_u32.to_be_bytes());
        bytes.extend_from_slice(&completed_tick.to_be_bytes());
        bytes.extend_from_slice(
            &u64::try_from(state_bytes.len())
                .map_err(|_| MaterialWorldError::Arithmetic)?
                .to_be_bytes(),
        );
        bytes.extend_from_slice(&state_bytes);
        bytes.extend_from_slice(&organizer_bytes);
        let digest = sha256_of(&bytes);
        Ok(Self {
            completed_tick,
            state,
            organizer,
            canonical_bytes: bytes,
            digest,
        })
    }

    /// Bind captured organizer content and complete state into this world identity.
    /// # Errors
    /// Refuses invalid content/state, mismatched periods, or aggregate byte limits.
    pub fn with_organizer(
        self,
        config: OrganizerConfig,
        state: OrganizerState,
    ) -> Result<Self, MaterialWorldError> {
        Self::build(self.completed_tick, self.state, Some((config, state)))
    }

    #[must_use]
    pub fn organizer_config(&self) -> Option<&OrganizerConfig> {
        self.organizer.as_ref().map(|(config, _)| config)
    }

    #[must_use]
    pub fn organizer_state(&self) -> Option<&OrganizerState> {
        self.organizer.as_ref().map(|(_, state)| state)
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
        &self.canonical_bytes
    }
    #[must_use]
    pub const fn digest(&self) -> [u8; 32] {
        self.digest
    }

    /// Decode the exact complete register, including canonical state revalidation.
    /// # Errors
    /// Refuses unsupported/truncated/trailing/noncanonical bytes and invalid state.
    pub fn decode(bytes: &[u8]) -> Result<Self, MaterialWorldError> {
        let header = REGISTER_DOMAIN.len() + 20;
        if bytes.len() < header
            || bytes.len() > MAX_MATERIAL_WORLD_REGISTER_BYTES
            || !bytes.starts_with(REGISTER_DOMAIN)
        {
            return Err(MaterialWorldError::Wire);
        }
        let start = REGISTER_DOMAIN.len();
        if bytes[start..start + 4] != 4_u32.to_be_bytes() {
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
        let mut remaining = bytes.get(state_end..).ok_or(MaterialWorldError::Wire)?;
        let organizer = match remaining.split_first() {
            Some((0, [])) => None,
            Some((1, tail)) => {
                remaining = tail;
                let config = decode_organizer_config(take_organizer_section(&mut remaining)?)?;
                let state = decode_organizer_state(take_organizer_section(&mut remaining)?)?;
                if !remaining.is_empty() {
                    return Err(MaterialWorldError::Wire);
                }
                Some((config, state))
            }
            _ => return Err(MaterialWorldError::Wire),
        };
        let register = Self::build(tick, decode_material_circuit_state(state_bytes)?, organizer)?;
        if register.canonical_bytes != bytes {
            return Err(MaterialWorldError::Wire);
        }
        Ok(register)
    }

    /// Prepare one next-period successor without mutating this register.
    /// The existing material transition executes arrivals, prior commitments,
    /// dispatch and following-period commitments in its governed order.
    /// # Errors
    /// Refuses any circuit or receipt encoding failure without changing this owner.
    pub fn prepare_next(&self) -> Result<PreparedMaterialWorld, MaterialWorldError> {
        let transition = advance_material_circuit(&self.state)?;
        self.prepare_transition(transition)
    }

    /// Seal the result of the shared closed-period planner on this exact opening.
    pub(crate) fn prepare_transition(
        &self,
        transition: MaterialCircuitTransition,
    ) -> Result<PreparedMaterialWorld, MaterialWorldError> {
        if self.state.period.checked_add(1) != Some(transition.state.period) {
            return Err(MaterialWorldError::PeriodMismatch);
        }
        let receipts = encode_material_receipts(self.state.period, &transition)?;
        let organizer_facts = self
            .organizer_config()
            .map(|config| organizer_workplace_facts(config, &self.state, &transition))
            .transpose()?;
        let next = self
            .completed_tick
            .checked_add(1)
            .ok_or(MaterialWorldError::Arithmetic)?;
        let register = Self::try_new(next, transition.state)?;
        Ok(PreparedMaterialWorld {
            prior_digest: self.digest,
            register,
            receipt_bytes: receipts,
            organizer_facts,
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
}
impl PreparedMaterialWorld {
    #[must_use]
    pub fn organizer_workplace_facts(&self) -> Option<&OrganizerWorkplaceFacts> {
        self.organizer_facts.as_ref()
    }

    pub(crate) fn set_organizer(
        &mut self,
        config: OrganizerConfig,
        state: OrganizerState,
    ) -> Result<(), MaterialWorldError> {
        self.register = MaterialWorldRegister::build(
            self.register.completed_tick,
            self.register.state.clone(),
            Some((config, state)),
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

fn take_organizer_section<'a>(remaining: &mut &'a [u8]) -> Result<&'a [u8], MaterialWorldError> {
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

fn organizer_workplace_facts(
    config: &OrganizerConfig,
    opening: &MaterialCircuitState,
    transition: &MaterialCircuitTransition,
) -> Result<OrganizerWorkplaceFacts, MaterialWorldError> {
    let process_id = babylon_material_circuit::ProcessId::from_bytes(config.workplace_process_id);
    let output = opening
        .process_outputs
        .iter()
        .find(|row| row.process_id == process_id)
        .ok_or(MaterialWorldError::Wire)?;
    let produced_batches = transition
        .production
        .iter()
        .find(|row| row.process_id == process_id)
        .map_or(0, |receipt| receipt.produced_batches);
    let labor = opening
        .labor_coefficients
        .iter()
        .find(|row| row.process_id == process_id)
        .ok_or(MaterialWorldError::Wire)?;
    let maintenance = transition
        .maintenance
        .as_ref()
        .filter(|row| row.binding.consumer_process_id == process_id)
        .ok_or(MaterialWorldError::Wire)?;
    let mass = opening
        .freight_mass_coefficients
        .iter()
        .find(|row| row.good_id == output.good_id && row.unit_id == output.unit_id)
        .ok_or(MaterialWorldError::Wire)?;
    if mass.grams_per_unit != 1_000 {
        return Err(MaterialWorldError::Wire);
    }
    Ok(OrganizerWorkplaceFacts {
        period: opening.period,
        workplace_id: config.workplace_id,
        performed_labor_hours: produced_batches
            .checked_mul(labor.quantity_per_batch)
            .ok_or(MaterialWorldError::Arithmetic)?,
        output_kg: produced_batches
            .checked_mul(output.quantity_per_batch)
            .ok_or(MaterialWorldError::Arithmetic)?,
        maintenance_enabled_batches: maintenance.opening_service_batches,
        maintenance_consumed_batches: maintenance.consumed_service_batches,
        maintenance_expired_batches: maintenance.expired_service_batches,
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
    sha256_of(&bytes[..domain + 68])
}

fn bounded_bytes(length: usize) -> Result<Vec<u8>, MaterialWorldError> {
    if length > MAX_MATERIAL_WORLD_REGISTER_BYTES {
        return Err(MaterialWorldError::ByteLimit);
    }
    let mut bytes = Vec::new();
    bytes
        .try_reserve_exact(length)
        .map_err(|_| MaterialWorldError::Allocation)?;
    Ok(bytes)
}
fn receipt_row_limit(index: usize) -> usize {
    match index {
        6 => babylon_material_circuit::MAX_HANDLING_RECEIPTS_PER_PERIOD,
        10 => babylon_material_circuit::MAX_MONEY_TRANSFERS_PER_PERIOD,
        _ => babylon_material_circuit::MAX_MATERIAL_CIRCUIT_ROWS,
    }
}

fn encode_material_receipts(
    tick: u64,
    transition: &MaterialCircuitTransition,
) -> Result<Vec<u8>, MaterialWorldError> {
    if tick == 0 {
        return Err(MaterialWorldError::Wire);
    }
    let families = [
        (transition.production.len(), 80_usize),
        (transition.dispatches.len(), 112),
        (transition.losses.len(), 106),
        (transition.arrivals.len(), 40),
        (transition.deliveries.len(), 40),
        (transition.realizations.len(), 40),
        (transition.handling.len(), 97),
        (transition.local_fulfillments.len(), 168),
        (transition.local_transfers.len(), 168),
        (
            usize::from(transition.maintenance.is_some()),
            maintenance_receipt::ROW_BYTES,
        ),
        (
            transition.money_transfers.len(),
            monetary_receipt::TRANSFER_BYTES,
        ),
        (
            transition.wage_accruals.len(),
            monetary_receipt::ACCRUAL_BYTES,
        ),
        (transition.labor_use.len(), monetary_receipt::LABOR_BYTES),
        (
            transition.household_demand.len(),
            recurring_receipt::DEMAND_BYTES,
        ),
        (
            transition.household_consumption.len(),
            recurring_receipt::CONSUMPTION_BYTES,
        ),
        (
            transition.procurement.len(),
            recurring_receipt::PROCUREMENT_BYTES,
        ),
        (
            transition.production_plans.len(),
            recurring_receipt::PLAN_BYTES,
        ),
        (transition.prices.len(), recurring_receipt::PRICE_BYTES),
    ];
    if families
        .iter()
        .enumerate()
        .any(|(index, (count, _))| *count > receipt_row_limit(index))
    {
        return Err(MaterialWorldError::ByteLimit);
    }
    monetary_receipt::validate_order(&transition.wage_accruals, &transition.labor_use)?;
    recurring_receipt::validate_order(
        &transition.household_demand,
        &transition.household_consumption,
        &transition.procurement,
        &transition.production_plans,
        &transition.prices,
    )?;
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
    let mut bytes = bounded_bytes(length)?;
    bytes.extend_from_slice(RECEIPT_DOMAIN);
    bytes.extend_from_slice(&7_u32.to_be_bytes());
    bytes.extend_from_slice(&tick.to_be_bytes());
    for (tag, (count, _)) in families.iter().enumerate() {
        bytes.push(u8::try_from(tag + 1).map_err(|_| MaterialWorldError::Arithmetic)?);
        bytes.extend_from_slice(
            &u64::try_from(*count)
                .map_err(|_| MaterialWorldError::Arithmetic)?
                .to_be_bytes(),
        );
        match tag {
            0 => {
                for row in &transition.production {
                    bytes.extend_from_slice(&row.process_id.as_bytes());
                    bytes.extend_from_slice(&row.site_id.as_bytes());
                    bytes.extend_from_slice(&row.planned_batches.to_be_bytes());
                    bytes.extend_from_slice(&row.produced_batches.to_be_bytes());
                }
            }
            1 => {
                for row in &transition.dispatches {
                    bytes.extend_from_slice(&row.lot_id.as_bytes());
                    bytes.extend_from_slice(&row.order_id.as_bytes());
                    bytes.extend_from_slice(&row.route_id.as_bytes());
                    bytes.extend_from_slice(&row.quantity.to_be_bytes());
                    bytes.extend_from_slice(&row.final_arrival_period.to_be_bytes());
                }
            }
            2 => {
                for row in &transition.losses {
                    bytes.extend_from_slice(&row.lot_id.as_bytes());
                    bytes.extend_from_slice(&row.order_id.as_bytes());
                    bytes.extend_from_slice(&row.route_id.as_bytes());
                    bytes.extend_from_slice(&row.stage_index.to_be_bytes());
                    bytes.extend_from_slice(&row.quantity.to_be_bytes());
                }
            }
            3 => {
                for row in &transition.arrivals {
                    bytes.extend_from_slice(&row.order_id.as_bytes());
                    bytes.extend_from_slice(&row.quantity.to_be_bytes());
                }
            }
            4 => {
                for row in &transition.deliveries {
                    bytes.extend_from_slice(&row.order_id.as_bytes());
                    bytes.extend_from_slice(&row.quantity.to_be_bytes());
                }
            }
            5 => {
                for row in &transition.realizations {
                    bytes.extend_from_slice(&row.order_id.as_bytes());
                    bytes.extend_from_slice(&row.quantity.to_be_bytes());
                }
            }
            6 => {
                use babylon_material_circuit::OutboundOrderId;
                for row in &transition.handling {
                    bytes.extend_from_slice(&row.site_id.as_bytes());
                    let (tag, id) = match row.order {
                        OutboundOrderId::Delivery(id) => (1, id),
                        OutboundOrderId::LocalFinalDemand(id) => (2, id),
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
            }
            7 => {
                for row in &transition.local_fulfillments {
                    bytes.extend_from_slice(&row.order_id.as_bytes());
                    bytes.extend_from_slice(&row.retailer_site_id.as_bytes());
                    bytes.extend_from_slice(&row.demand_principal_id.as_bytes());
                    bytes.extend_from_slice(&row.good_id.as_bytes());
                    bytes.extend_from_slice(&row.unit_id.as_bytes());
                    bytes.extend_from_slice(&row.quantity.to_be_bytes());
                }
            }
            8 => {
                for row in &transition.local_transfers {
                    bytes.extend_from_slice(&row.order_id.as_bytes());
                    bytes.extend_from_slice(&row.supplier_site_id.as_bytes());
                    bytes.extend_from_slice(&row.buyer_site_id.as_bytes());
                    bytes.extend_from_slice(&row.good_id.as_bytes());
                    bytes.extend_from_slice(&row.unit_id.as_bytes());
                    bytes.extend_from_slice(&row.quantity.to_be_bytes());
                }
            }
            9 => {
                if let Some(row) = &transition.maintenance {
                    maintenance_receipt::encode(row, tick, &mut bytes)?;
                }
            }
            10 => {
                for row in &transition.money_transfers {
                    monetary_receipt::encode_transfer(row, &mut bytes)?;
                }
            }
            11 => {
                for row in &transition.wage_accruals {
                    monetary_receipt::encode_accrual(row, tick, &mut bytes)?;
                }
            }
            12 => {
                for row in &transition.labor_use {
                    monetary_receipt::encode_labor(row, tick, &mut bytes)?;
                }
            }
            13 => {
                for row in &transition.household_demand {
                    recurring_receipt::encode_demand(row, tick, &mut bytes)?;
                }
            }
            14 => {
                for row in &transition.household_consumption {
                    recurring_receipt::encode_consumption(row, tick, &mut bytes)?;
                }
            }
            15 => {
                for row in &transition.procurement {
                    recurring_receipt::encode_procurement(row, tick, &mut bytes)?;
                }
            }
            16 => {
                for row in &transition.production_plans {
                    recurring_receipt::encode_plan(row, tick, &mut bytes)?;
                }
            }
            17 => {
                for row in &transition.prices {
                    recurring_receipt::encode_price(row, tick, &mut bytes)?;
                }
            }
            _ => unreachable!("the eighteen material receipt families are closed"),
        }
    }
    debug_assert_eq!(bytes.len(), length);
    Ok(bytes)
}

/// Typed material evidence decoded only from an exact committed V7 receipt family.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MaterialTickReceipts {
    pub resolve_tick: u64,
    pub household_demand: Vec<babylon_material_circuit::HouseholdDemandReceipt>,
    pub household_consumption: Vec<babylon_material_circuit::HouseholdConsumptionReceipt>,
    pub procurement: Vec<babylon_material_circuit::ProcurementReceipt>,
    pub production_plans: Vec<babylon_material_circuit::ProductionPlanReceipt>,
    pub prices: Vec<babylon_material_circuit::PriceReceipt>,
    pub money_transfers: Vec<babylon_material_circuit::MoneyTransferReceipt>,
    pub wage_accruals: Vec<babylon_material_circuit::WageAccrualReceipt>,
    pub labor_use: Vec<babylon_material_circuit::LaborUseReceipt>,
    pub production: Vec<babylon_material_circuit::ProductionReceipt>,
    pub dispatches: Vec<babylon_material_circuit::RoutedDispatchReceipt>,
    pub losses: Vec<babylon_material_circuit::FreightLossReceipt>,
    pub arrivals: Vec<babylon_material_circuit::ArrivalReceipt>,
    pub deliveries: Vec<babylon_material_circuit::DeliveryReceipt>,
    pub realizations: Vec<babylon_material_circuit::RealizationReceipt>,
    pub handling: Vec<babylon_material_circuit::MerchantHandlingReceipt>,
    pub local_fulfillments: Vec<babylon_material_circuit::LocalRetailFulfillmentReceipt>,
    pub local_transfers: Vec<babylon_material_circuit::LocalTransferReceipt>,
    pub maintenance: Option<babylon_material_circuit::MaintenanceReceipt>,
}
/// Decode a bounded receipt family. Hash/campaign binding belongs to its V3 envelope.
/// # Errors
/// Refuses versions, tags, counts, truncation, trailing bytes and invalid quantity relations.
pub fn decode_material_receipts(bytes: &[u8]) -> Result<MaterialTickReceipts, MaterialWorldError> {
    use babylon_material_circuit::*;
    if bytes.len() > MAX_MATERIAL_WORLD_REGISTER_BYTES || !bytes.starts_with(RECEIPT_DOMAIN) {
        return Err(MaterialWorldError::Wire);
    }
    let mut cursor = ReceiptCursor {
        bytes,
        position: RECEIPT_DOMAIN.len(),
    };
    if cursor.take::<4>()? != 7_u32.to_be_bytes() {
        return Err(MaterialWorldError::Wire);
    }
    let resolve_tick = cursor.u64()?;
    if resolve_tick == 0 {
        return Err(MaterialWorldError::Wire);
    }
    let mut result = MaterialTickReceipts {
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
    for tag in 1..=18 {
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
            _ => return Err(MaterialWorldError::Wire),
        }
        .map_err(|_| MaterialWorldError::Allocation)?;
        for _ in 0..count {
            match tag {
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
                _ => return Err(MaterialWorldError::Wire),
            }
        }
    }
    if cursor.position != bytes.len() {
        return Err(MaterialWorldError::Wire);
    }
    monetary_receipt::validate_order(&result.wage_accruals, &result.labor_use)?;
    recurring_receipt::validate_order(
        &result.household_demand,
        &result.household_consumption,
        &result.procurement,
        &result.production_plans,
        &result.prices,
    )?;
    Ok(result)
}
struct ReceiptCursor<'a> {
    bytes: &'a [u8],
    position: usize,
}
impl ReceiptCursor<'_> {
    fn take<const N: usize>(&mut self) -> Result<[u8; N], MaterialWorldError> {
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
    fn u64(&mut self) -> Result<u64, MaterialWorldError> {
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

#[cfg(test)]
mod tests;
