//! Captured gift authority and detached next-period material commitments.
//!
//! Intent admission belongs to the authenticated organizer adapter. The circuit
//! independently joins every immutable mandate term and shares physical scarcity.

use crate::{
    FinalDemandPrincipalId, FreightLotId, GoodId, LogisticsNodeId, MaterialCircuitError, OrderId,
    RouteId, UnitId,
};
use babylon_kernel::{content_digest::sha256_of, currency::Currency};

type Result<T> = std::result::Result<T, MaterialCircuitError>;

/// At most three request/dispatch/refund rows per mandate and two due-lot
/// arrival/loss rows per pending lot, under their existing collection ceilings.
pub const MAX_AID_RECEIPTS_PER_PERIOD: usize = 5 * crate::MAX_MATERIAL_CIRCUIT_ROWS;

/// Designed authority captured with the campaign, never supplied by an action.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AidMandate {
    pub id: [u8; 32],
    pub source_hash: [u8; 32],
    pub donor_actor: u64,
    pub donor_contributor_id: u64,
    pub recipient_actor: u64,
    pub payer: crate::AccountId,
    pub donor: FinalDemandPrincipalId,
    pub recipient: FinalDemandPrincipalId,
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub labor_unit_id: UnitId,
    pub hours_per_unit: u64,
    pub maximum_quantity: u64,
    pub cash_per_unit: Currency,
    pub transport: AidTransport,
}

/// A household-to-household gift keeps principal ownership separate from sites.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AidTransport {
    Local,
    Routed {
        route_id: RouteId,
        from_node_id: LogisticsNodeId,
        to_node_id: LogisticsNodeId,
    },
}

/// Both practices were accepted independently during the preceding period.
/// This is a host boundary: engine admission must authenticate both actors.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AidResolveInput {
    pub mandate_id: [u8; 32],
    pub source_hash: [u8; 32],
    pub admitted_period: u64,
    pub donor_actor: u64,
    pub recipient_actor: u64,
    pub quantity: u64,
}

/// Current in-transit gift and exact outstanding cash principal.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AidFreightLot {
    pub lot_id: FreightLotId,
    pub commitment_id: OrderId,
    pub mandate_id: [u8; 32],
    pub route_id: RouteId,
    pub dispatch_period: u64,
    pub current_stage_index: u16,
    pub stage_arrival_period: u64,
    pub donor: FinalDemandPrincipalId,
    pub recipient: FinalDemandPrincipalId,
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub quantity: u64,
}

/// Only immutable mandates and unresolved freight survive publication.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct AidBook {
    pub mandates: Vec<AidMandate>,
    pub freight: Vec<AidFreightLot>,
}

/// Material evidence records actual scarcity, rather than promised outcomes.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AidReceipt {
    pub commitment_id: OrderId,
    pub mandate_id: [u8; 32],
    pub period: u64,
    pub dispatch_period: u64,
    pub transport: AidTransport,
    pub payer: crate::AccountId,
    pub donor: FinalDemandPrincipalId,
    pub recipient: FinalDemandPrincipalId,
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub outcome: AidOutcome,
    pub quantity: u64,
    pub carrying_amount: Currency,
    pub cash_amount: Currency,
    pub contribution_hours: u64,
}

/// Closed material outcomes; admission and dispatch never assert consumption.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum AidOutcome {
    Requested = 1,
    Dispatched = 2,
    Granted = 3,
    Lost = 4,
    Unshipped = 5,
}

/// Stable one-period principal; actor aliases cannot generate extra mandates.
#[must_use]
pub fn aid_commitment_id(mandate_id: [u8; 32], period: u64) -> OrderId {
    let mut bytes = b"babylon.household-aid-commitment.v1\0".to_vec();
    bytes.extend_from_slice(&mandate_id);
    bytes.extend_from_slice(&period.to_be_bytes());
    OrderId::from_bytes(sha256_of(&bytes))
}

impl AidMandate {
    pub(crate) fn validate(&self) -> Result<()> {
        if self.id == [0; 32]
            || self.source_hash == [0; 32]
            || self.donor_actor == 0
            || self.donor_contributor_id == 0
            || self.recipient_actor == 0
            || self.donor_actor == self.recipient_actor
            || self.donor == self.recipient
            || self.hours_per_unit == 0
            || self.maximum_quantity == 0
            || self.cash_per_unit.micro_units() <= 0
        {
            return Err(MaterialCircuitError::AidInvariant);
        }
        self.cash_per_unit
            .micro_units()
            .checked_mul(i128::from(self.maximum_quantity))
            .ok_or(MaterialCircuitError::Arithmetic)?;
        self.hours_per_unit
            .checked_mul(self.maximum_quantity)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        Ok(())
    }

    pub(crate) fn authenticate(&self, input: &AidResolveInput, period: u64) -> Result<OrderId> {
        self.validate()?;
        if input.mandate_id != self.id
            || input.source_hash != self.source_hash
            || input.donor_actor != self.donor_actor
            || input.recipient_actor != self.recipient_actor
            || input.quantity == 0
            || input.quantity > self.maximum_quantity
        {
            return Err(MaterialCircuitError::AidAuthority);
        }
        if input.admitted_period.checked_add(1) != Some(period) {
            return Err(MaterialCircuitError::PeriodInvariant);
        }
        Ok(aid_commitment_id(self.id, period))
    }
}

pub(crate) struct PreparedAid {
    pub orders: Vec<(AidMandate, OrderId, u64)>,
    pub surplus: std::collections::BTreeMap<(FinalDemandPrincipalId, GoodId, UnitId), u64>,
    pub hours: std::collections::BTreeMap<(FinalDemandPrincipalId, UnitId), u64>,
}
impl PreparedAid {
    pub(crate) fn empty() -> Self {
        Self {
            orders: Vec::new(),
            surplus: std::collections::BTreeMap::new(),
            hours: std::collections::BTreeMap::new(),
        }
    }
}

pub(crate) fn validate(state: &crate::MaterialCircuitState) -> Result<()> {
    use std::collections::BTreeSet;
    let crate::CircuitAccounting::Monetary(economy) = &state.accounting else {
        return Ok(());
    };
    let book = &economy.aid;
    if book.mandates.len() > crate::MAX_MATERIAL_CIRCUIT_ROWS
        || book
            .freight
            .len()
            .checked_add(state.freight.len())
            .ok_or(MaterialCircuitError::Arithmetic)?
            > crate::MAX_MATERIAL_CIRCUIT_ROWS
    {
        return Err(MaterialCircuitError::RowLimit);
    }
    if book.mandates.windows(2).any(|w| w[0].id >= w[1].id)
        || book.freight.windows(2).any(|w| w[0].lot_id >= w[1].lot_id)
    {
        return Err(MaterialCircuitError::AidInvariant);
    }
    let donors: BTreeSet<_> = book.mandates.iter().map(|m| m.donor).collect();
    let recipients: BTreeSet<_> = book.mandates.iter().map(|m| m.recipient).collect();
    if !donors.is_disjoint(&recipients) {
        return Err(MaterialCircuitError::AidInvariant);
    }
    for mandate in &book.mandates {
        validate_mandate(state, mandate)?;
    }
    let mut reserves = BTreeSet::new();
    let sale_lots: BTreeSet<_> = state.freight.iter().map(|l| l.lot_id).collect();
    for lot in &book.freight {
        let mandate = book
            .mandates
            .binary_search_by_key(&lot.mandate_id, |m| m.id)
            .ok()
            .map(|i| &book.mandates[i])
            .ok_or(MaterialCircuitError::AidAuthority)?;
        let AidTransport::Routed { route_id, .. } = mandate.transport else {
            return Err(MaterialCircuitError::AidInvariant);
        };
        if lot.route_id != route_id
            || lot.donor != mandate.donor
            || lot.recipient != mandate.recipient
            || lot.good_id != mandate.good_id
            || lot.unit_id != mandate.unit_id
            || lot.quantity == 0
            || lot.dispatch_period >= state.period
            || lot.stage_arrival_period < state.period
            || lot.commitment_id != aid_commitment_id(mandate.id, lot.dispatch_period)
            || lot.lot_id != aid_lot_id(lot.commitment_id)
            || sale_lots.contains(&lot.lot_id)
            || !reserves.insert(lot.commitment_id)
        {
            return Err(MaterialCircuitError::AidInvariant);
        }
        let legs: Vec<_> = state
            .route_stages
            .iter()
            .filter(|s| s.route_id == route_id)
            .collect();
        if legs.get(usize::from(lot.current_stage_index)).is_none() {
            return Err(MaterialCircuitError::AidInvariant);
        }
        let expected_arrival = legs
            .iter()
            .take(usize::from(lot.current_stage_index) + 1)
            .try_fold(lot.dispatch_period, |period, stage| {
                period
                    .checked_add(u64::from(stage.travel_periods))
                    .ok_or(MaterialCircuitError::Arithmetic)
            })?;
        if lot.stage_arrival_period != expected_arrival {
            return Err(MaterialCircuitError::AidInvariant);
        }
        let reserve = economy.book.aid_reserve(lot.commitment_id)?;
        let remaining = reserve
            .quantity
            .checked_sub(reserve.granted)
            .and_then(|q| q.checked_sub(reserve.refunded))
            .ok_or(MaterialCircuitError::Arithmetic)?;
        if reserve.quantity > mandate.maximum_quantity
            || reserve.granted != 0
            || reserve.payer != mandate.payer
            || reserve.donor != lot.donor
            || reserve.recipient != lot.recipient
            || remaining != lot.quantity
            || reserve.cash_per_unit != mandate.cash_per_unit
        {
            return Err(MaterialCircuitError::AidInvariant);
        }
    }
    if !reserves
        .into_iter()
        .eq(economy.book.snapshot().aid.into_iter().map(|r| r.id))
    {
        return Err(MaterialCircuitError::AidInvariant);
    }
    Ok(())
}

fn validate_mandate(state: &crate::MaterialCircuitState, mandate: &AidMandate) -> Result<()> {
    mandate.validate()?;
    let crate::CircuitAccounting::Monetary(economy) = &state.accounting else {
        return Err(MaterialCircuitError::AidInvariant);
    };
    let recurring = economy
        .recurring
        .as_ref()
        .ok_or(MaterialCircuitError::AidInvariant)?;
    let crate::HouseholdTimeAccounting::Modeled(time) = &economy.household_time else {
        return Err(MaterialCircuitError::AidInvariant);
    };
    economy.book.cash(mandate.payer)?;
    if mandate.payer == crate::AccountId::Household(mandate.recipient) {
        return Err(MaterialCircuitError::AidAuthority);
    }
    for principal in [mandate.donor, mandate.recipient] {
        if !recurring.household_stocks.iter().any(|r| {
            (r.principal_id, r.good_id, r.unit_id) == (principal, mandate.good_id, mandate.unit_id)
        }) || !recurring.household_needs.iter().any(|r| {
            (r.principal_id, r.good_id, r.unit_id) == (principal, mandate.good_id, mandate.unit_id)
        }) || !time
            .policies
            .iter()
            .any(|p| p.principal_id == principal && p.labor_unit_id == mandate.labor_unit_id)
        {
            return Err(MaterialCircuitError::AidAuthority);
        }
        economy.book.cash(crate::AccountId::Household(principal))?;
    }
    let donor = state
        .final_demand_principals
        .iter()
        .find(|p| p.id == mandate.donor)
        .ok_or(MaterialCircuitError::AidAuthority)?;
    let recipient = state
        .final_demand_principals
        .iter()
        .find(|p| p.id == mandate.recipient)
        .ok_or(MaterialCircuitError::AidAuthority)?;
    match mandate.transport {
        AidTransport::Local if donor.location != recipient.location => {
            return Err(MaterialCircuitError::AidAuthority)
        }
        AidTransport::Local => {}
        AidTransport::Routed {
            route_id,
            from_node_id,
            to_node_id,
        } => {
            let legs: Vec<_> = state
                .route_stages
                .iter()
                .filter(|s| s.route_id == route_id)
                .collect();
            if legs.first().map(|s| s.from_node_id) != Some(from_node_id)
                || legs.last().map(|s| s.to_node_id) != Some(to_node_id)
                || from_node_id == to_node_id
            {
                return Err(MaterialCircuitError::AidAuthority);
            }
        }
    }
    Ok(())
}

pub(crate) fn prepare(
    state: &mut crate::MaterialCircuitState,
    inputs: &[AidResolveInput],
    costs: &crate::valuation::CostClose,
    services: &[crate::HouseholdServiceReceipt],
    transfers: &mut Vec<crate::MoneyTransferReceipt>,
    receipts: &mut Vec<AidReceipt>,
) -> Result<PreparedAid> {
    use std::collections::{BTreeMap, BTreeSet};
    if inputs.is_empty() {
        return Ok(PreparedAid::empty());
    }
    if inputs.len() > crate::MAX_MATERIAL_CIRCUIT_ROWS {
        return Err(MaterialCircuitError::RowLimit);
    }
    let crate::CircuitAccounting::Monetary(economy) = &state.accounting else {
        return Err(MaterialCircuitError::AidAuthority);
    };
    let recurring = economy
        .recurring
        .as_ref()
        .ok_or(MaterialCircuitError::AidAuthority)?;
    let consumption =
        crate::recurring::households::preview_household_needs(recurring, state.period)?;
    let time =
        crate::household_time::preview(state, costs.attendance_members(), &consumption, services)?;
    let mut prepared = PreparedAid {
        orders: Vec::new(),
        surplus: consumption
            .iter()
            .map(|r| ((r.principal_id, r.good_id, r.unit_id), r.closing_quantity))
            .collect(),
        hours: time
            .iter()
            .map(|r| {
                (
                    (r.principal_id, r.labor_unit_id),
                    r.contribution_available_hours,
                )
            })
            .collect(),
    };
    let mandates: BTreeMap<_, _> = economy
        .aid
        .mandates
        .iter()
        .map(|m| (m.id, m.clone()))
        .collect();
    let mut staged = economy.book.clone();
    let mut seen = BTreeSet::new();
    let mut ordered: Vec<_> = inputs.iter().collect();
    ordered.sort_by_key(|i| i.mandate_id);
    for input in ordered {
        if !seen.insert(input.mandate_id) {
            return Err(MaterialCircuitError::AidAuthority);
        }
        let mandate = mandates
            .get(&input.mandate_id)
            .ok_or(MaterialCircuitError::AidAuthority)?;
        let id = mandate.authenticate(input, state.period)?;
        receipts.push(receipt(
            mandate,
            id,
            state.period,
            AidOutcome::Requested,
            crate::aid::AidFlow {
                quantity: input.quantity,
                carrying: zero(),
                cash: zero(),
                hours: 0,
            },
        ));
        let affordable =
            staged.cash(mandate.payer)?.micro_units() / mandate.cash_per_unit.micro_units();
        let quantity = u64::try_from(affordable.min(i128::from(input.quantity)))
            .map_err(|_| MaterialCircuitError::Arithmetic)?;
        if quantity == 0 {
            continue;
        }
        transfers.push(staged.reserve_aid(crate::AidCashReserve {
            id,
            payer: mandate.payer,
            donor: mandate.donor,
            recipient: mandate.recipient,
            quantity,
            cash_per_unit: mandate.cash_per_unit,
            granted: 0,
            refunded: 0,
        })?);
        prepared.orders.push((mandate.clone(), id, quantity));
    }
    let crate::CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Err(MaterialCircuitError::AidInvariant);
    };
    economy.book = staged;
    Ok(prepared)
}

#[derive(Clone, Copy)]
pub(crate) struct AidFlow {
    pub quantity: u64,
    pub carrying: Currency,
    pub cash: Currency,
    pub hours: u64,
}

pub(crate) fn receipt(
    m: &AidMandate,
    id: OrderId,
    period: u64,
    outcome: AidOutcome,
    flow: AidFlow,
) -> AidReceipt {
    AidReceipt {
        commitment_id: id,
        mandate_id: m.id,
        period,
        dispatch_period: period,
        transport: m.transport,
        payer: m.payer,
        donor: m.donor,
        recipient: m.recipient,
        good_id: m.good_id,
        unit_id: m.unit_id,
        outcome,
        quantity: flow.quantity,
        carrying_amount: flow.carrying,
        cash_amount: flow.cash,
        contribution_hours: flow.hours,
    }
}

fn zero() -> Currency {
    Currency::from_micro_units(0)
}
pub(crate) fn cash_amount(quantity: u64, mandate: &AidMandate) -> Result<Currency> {
    mandate
        .cash_per_unit
        .micro_units()
        .checked_mul(i128::from(quantity))
        .map(Currency::from_micro_units)
        .ok_or(MaterialCircuitError::Arithmetic)
}

pub(crate) fn take_household_stock(
    state: &mut crate::MaterialCircuitState,
    mandate: &AidMandate,
    quantity: u64,
) -> Result<u64> {
    let crate::CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Err(MaterialCircuitError::AidInvariant);
    };
    let recurring = economy
        .recurring
        .as_mut()
        .ok_or(MaterialCircuitError::AidInvariant)?;
    let row = recurring
        .household_stocks
        .iter_mut()
        .find(|r| {
            (r.principal_id, r.good_id, r.unit_id)
                == (mandate.donor, mandate.good_id, mandate.unit_id)
        })
        .ok_or(MaterialCircuitError::AidInvariant)?;
    let available = row.quantity;
    row.quantity = available
        .checked_sub(quantity)
        .ok_or(MaterialCircuitError::AidInvariant)?;
    Ok(available)
}

pub(crate) fn grant_household_stock(
    state: &mut crate::MaterialCircuitState,
    mandate: &AidMandate,
    quantity: u64,
) -> Result<()> {
    let crate::CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Err(MaterialCircuitError::AidInvariant);
    };
    let recurring = economy
        .recurring
        .as_mut()
        .ok_or(MaterialCircuitError::AidInvariant)?;
    let row = recurring
        .household_stocks
        .iter_mut()
        .find(|r| {
            (r.principal_id, r.good_id, r.unit_id)
                == (mandate.recipient, mandate.good_id, mandate.unit_id)
        })
        .ok_or(MaterialCircuitError::AidInvariant)?;
    row.quantity = row
        .quantity
        .checked_add(quantity)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    Ok(())
}

pub(crate) fn contribution_uses(
    state: &crate::MaterialCircuitState,
    receipts: &[AidReceipt],
) -> Result<Vec<crate::HouseholdContributionUse>> {
    let crate::CircuitAccounting::Monetary(economy) = &state.accounting else {
        return Ok(Vec::new());
    };
    receipts
        .iter()
        .filter(|r| r.contribution_hours > 0)
        .map(|r| {
            let mandate = economy
                .aid
                .mandates
                .binary_search_by_key(&r.mandate_id, |m| m.id)
                .ok()
                .map(|i| &economy.aid.mandates[i])
                .ok_or(MaterialCircuitError::AidAuthority)?;
            Ok(crate::HouseholdContributionUse {
                use_id: r.commitment_id.as_bytes(),
                principal_id: r.donor,
                actor_id: mandate.donor_actor,
                contributor_id: mandate.donor_contributor_id,
                hours: r.contribution_hours,
            })
        })
        .collect()
}

pub(crate) fn aid_lot_id(id: OrderId) -> FreightLotId {
    let mut bytes = b"babylon.household-aid-lot.v1\0".to_vec();
    bytes.extend_from_slice(&id.as_bytes());
    FreightLotId::from_bytes(sha256_of(&bytes))
}

impl AidReceipt {
    /// Reconcile actual gift evidence with its immutable captured authority.
    /// # Errors
    /// Refuses changed parties/units, invented principals or incompatible phases.
    pub fn validate_against(&self, mandate: &AidMandate) -> Result<()> {
        mandate.validate()?;
        if self.period == 0
            || self.dispatch_period == 0
            || self.dispatch_period > self.period
            || self.quantity == 0
            || self.quantity > mandate.maximum_quantity
            || self.mandate_id != mandate.id
            || self.commitment_id != aid_commitment_id(mandate.id, self.dispatch_period)
            || self.transport != mandate.transport
            || self.payer != mandate.payer
            || self.donor != mandate.donor
            || self.recipient != mandate.recipient
            || self.good_id != mandate.good_id
            || self.unit_id != mandate.unit_id
            || self.carrying_amount.micro_units() < 0
        {
            return Err(MaterialCircuitError::AidInvariant);
        }
        let cash = cash_amount(self.quantity, mandate)?;
        let hours = self
            .quantity
            .checked_mul(mandate.hours_per_unit)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        let (expected_cash, expected_hours) = match (self.outcome, self.transport) {
            (AidOutcome::Requested, _) => {
                if self.dispatch_period != self.period || self.carrying_amount != zero() {
                    return Err(MaterialCircuitError::AidInvariant);
                }
                (zero(), 0)
            }
            (AidOutcome::Unshipped, _) => {
                if self.dispatch_period != self.period || self.carrying_amount != zero() {
                    return Err(MaterialCircuitError::AidInvariant);
                }
                (cash, 0)
            }
            (AidOutcome::Dispatched, AidTransport::Routed { .. })
            | (AidOutcome::Granted, AidTransport::Local) => {
                if self.dispatch_period != self.period {
                    return Err(MaterialCircuitError::AidInvariant);
                }
                (cash, hours)
            }
            (AidOutcome::Granted | AidOutcome::Lost, AidTransport::Routed { .. }) => {
                if self.dispatch_period >= self.period {
                    return Err(MaterialCircuitError::AidInvariant);
                }
                (cash, 0)
            }
            _ => return Err(MaterialCircuitError::AidInvariant),
        };
        if self.cash_amount != expected_cash || self.contribution_hours != expected_hours {
            return Err(MaterialCircuitError::AidInvariant);
        }
        Ok(())
    }
}

pub(crate) fn validate_receipts(
    state: &crate::MaterialCircuitState,
    receipts: &[AidReceipt],
) -> Result<()> {
    use std::collections::BTreeSet;
    if receipts.len() > MAX_AID_RECEIPTS_PER_PERIOD {
        return Err(MaterialCircuitError::RowLimit);
    }
    let crate::CircuitAccounting::Monetary(economy) = &state.accounting else {
        return if receipts.is_empty() {
            Ok(())
        } else {
            Err(MaterialCircuitError::AidInvariant)
        };
    };
    let mut seen = BTreeSet::new();
    for receipt in receipts {
        if receipt.period != state.period {
            return Err(MaterialCircuitError::AidInvariant);
        }
        let mandate = economy
            .aid
            .mandates
            .binary_search_by_key(&receipt.mandate_id, |m| m.id)
            .ok()
            .map(|i| &economy.aid.mandates[i])
            .ok_or(MaterialCircuitError::AidAuthority)?;
        receipt.validate_against(mandate)?;
        if !seen.insert((receipt.commitment_id, receipt.outcome as u8)) {
            return Err(MaterialCircuitError::AidInvariant);
        }
    }
    Ok(())
}
