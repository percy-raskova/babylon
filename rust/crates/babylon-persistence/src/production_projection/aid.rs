//! Adjacent authenticated aid evidence. No allocation, pricing or economic replay.
use super::ProductionProjectionError;
use babylon_material_circuit::MaterialCatalog;
use babylon_material_circuit::{
    AccountId, AidMandate, AidOutcome, AidReceipt, AidTransport, CashTransferPurpose,
    CircuitAccounting, FinalDemandPrincipalId, GoodId, MaterialCircuitState, MoneyLocation,
    MoneyTransferPurpose, OrderId, UnitId,
};
use babylon_tick::material_world::MaterialTickReceipts;
use std::collections::{BTreeMap, BTreeSet};
use std::result::Result as StdResult;
type Result<T> = StdResult<T, ProductionProjectionError>;
pub(super) type Key = (FinalDemandPrincipalId, GoodId, UnitId);
#[derive(Default)]
pub(super) struct Gifts {
    pub before_demand: BTreeMap<Key, u64>,
    pub received: BTreeMap<Key, u64>,
    pub sent: BTreeMap<Key, u64>,
}
#[derive(Default)]
struct Flow {
    requested: u64,
    dispatched: u64,
    granted: u64,
    lost: u64,
    unshipped: u64,
}
fn add(value: &mut u64, quantity: u64) -> Result<()> {
    *value = value
        .checked_add(quantity)
        .ok_or(ProductionProjectionError::Arithmetic)?;
    Ok(())
}
fn sum(rows: &mut BTreeMap<Key, u64>, key: Key, quantity: u64) -> Result<()> {
    add(rows.entry(key).or_default(), quantity)
}
type Mandates<'a> = BTreeMap<[u8; 32], &'a AidMandate>;
type Flows = BTreeMap<OrderId, Flow>;
pub(super) fn join(
    catalog: &MaterialCatalog,
    prior: &MaterialCircuitState,
    current: &MaterialCircuitState,
    receipt: &MaterialTickReceipts,
) -> Result<Gifts> {
    let (CircuitAccounting::Monetary(_), CircuitAccounting::Monetary(_)) =
        (&prior.accounting, &current.accounting)
    else {
        return if receipt.aid.is_empty() {
            Ok(Gifts::default())
        } else {
            Err(ProductionProjectionError::State)
        };
    };
    if receipt.resolve_tick != prior.period || prior.period.checked_add(1) != Some(current.period) {
        return Err(ProductionProjectionError::History);
    }
    let mandates: Mandates<'_> = catalog.aid_mandates.iter().map(|m| (m.id, m)).collect();
    if mandates.len() != catalog.aid_mandates.len() {
        return Err(ProductionProjectionError::State);
    }
    let (gifts, mut flows) = collect(receipt, &mandates)?;
    reconcile_freight(prior, current, &mut flows)?;
    validate_cash_custody(receipt)?;
    check_fresh(&flows)?;
    Ok(gifts)
}
fn collect(receipt: &MaterialTickReceipts, mandates: &Mandates<'_>) -> Result<(Gifts, Flows)> {
    let mut gifts = Gifts::default();
    let mut seen = BTreeSet::new();
    let mut flows = BTreeMap::<OrderId, Flow>::new();
    for row in &receipt.aid {
        let mandate = mandates
            .get(&row.mandate_id)
            .ok_or(ProductionProjectionError::State)?;
        row.validate_against(mandate)
            .map_err(|_| ProductionProjectionError::State)?;
        if row.period != receipt.resolve_tick
            || !seen.insert((row.commitment_id, row.outcome as u8))
        {
            return Err(ProductionProjectionError::State);
        }
        record_movement(row, &mut gifts, &mut flows)?;
    }
    Ok((gifts, flows))
}
fn record_movement(row: &AidReceipt, gifts: &mut Gifts, flows: &mut Flows) -> Result<()> {
    let flow = flows.entry(row.commitment_id).or_default();
    let donor = (row.donor, row.good_id, row.unit_id);
    let recipient = (row.recipient, row.good_id, row.unit_id);
    match row.outcome {
        AidOutcome::Requested => add(&mut flow.requested, row.quantity)?,
        AidOutcome::Dispatched => {
            add(&mut flow.dispatched, row.quantity)?;
            sum(&mut gifts.sent, donor, row.quantity)?;
        }
        AidOutcome::Granted => {
            add(&mut flow.granted, row.quantity)?;
            sum(&mut gifts.received, recipient, row.quantity)?;
            if row.transport == AidTransport::Local {
                sum(&mut gifts.sent, donor, row.quantity)?;
            } else {
                sum(&mut gifts.before_demand, recipient, row.quantity)?;
            }
        }
        AidOutcome::Lost => add(&mut flow.lost, row.quantity)?,
        AidOutcome::Unshipped | AidOutcome::FoodReceivingRefused => {
            add(&mut flow.unshipped, row.quantity)?;
        }
        AidOutcome::CashRequested
        | AidOutcome::CashGranted
        | AidOutcome::CashUnfunded
        | AidOutcome::CashReceivingRefused => {}
    }
    Ok(())
}
/// Reconcile each current-close mutual-aid transfer to exactly one typed cash leg.
pub(crate) fn validate_cash_custody(receipt: &MaterialTickReceipts) -> Result<()> {
    check_cash_requests(receipt)?;
    let mut joined = BTreeSet::new();
    join_cash_grants(receipt, &mut joined)?;
    join_collections(receipt, &mut joined)?;
    if receipt
        .money_transfers
        .iter()
        .enumerate()
        .any(|(index, row)| {
            row.purpose == MoneyTransferPurpose::Cash(CashTransferPurpose::MutualAid)
                && !joined.contains(&index)
        })
    {
        return Err(ProductionProjectionError::State);
    }
    Ok(())
}
fn check_cash_requests(receipt: &MaterialTickReceipts) -> Result<()> {
    let terminal = |row: &&AidReceipt| {
        matches!(
            row.outcome,
            AidOutcome::CashGranted | AidOutcome::CashUnfunded | AidOutcome::CashReceivingRefused
        )
    };
    for request in receipt
        .aid
        .iter()
        .filter(|row| row.outcome == AidOutcome::CashRequested)
    {
        let results: Vec<_> = receipt
            .aid
            .iter()
            .filter(terminal)
            .filter(|row| row.commitment_id == request.commitment_id)
            .collect();
        if results.len() != 1 || results[0].cash_amount > request.cash_amount {
            return Err(ProductionProjectionError::State);
        }
    }
    for result in receipt.aid.iter().filter(terminal) {
        if !receipt.aid.iter().any(|row| {
            row.outcome == AidOutcome::CashRequested && row.commitment_id == result.commitment_id
        }) {
            return Err(ProductionProjectionError::State);
        }
    }
    Ok(())
}
fn join_cash_grants(receipt: &MaterialTickReceipts, joined: &mut BTreeSet<usize>) -> Result<()> {
    for row in receipt
        .aid
        .iter()
        .filter(|row| row.outcome == AidOutcome::CashGranted)
    {
        let matches: Vec<_> = receipt
            .money_transfers
            .iter()
            .enumerate()
            .filter(|(_, transfer)| {
                transfer.purpose == MoneyTransferPurpose::Cash(CashTransferPurpose::MutualAid)
                    && transfer.debit.location == MoneyLocation::Cash(row.payer)
                    && transfer.credit.location
                        == MoneyLocation::Cash(AccountId::Household(row.recipient))
            })
            .collect();
        if matches.len() != 1
            || row.period != receipt.resolve_tick
            || row.dispatch_period != receipt.resolve_tick
            || !joined.insert(matches[0].0)
            || matches[0].1.credit.delta != row.cash_amount
            || matches[0].1.debit.delta.micro_units().checked_neg()
                != Some(row.cash_amount.micro_units())
        {
            return Err(ProductionProjectionError::State);
        }
        let request = receipt
            .aid
            .iter()
            .find(|request| {
                request.commitment_id == row.commitment_id
                    && request.outcome == AidOutcome::CashRequested
            })
            .ok_or(ProductionProjectionError::State)?;
        if row.cash_amount > request.cash_amount {
            return Err(ProductionProjectionError::State);
        }
    }
    Ok(())
}
fn join_collections(receipt: &MaterialTickReceipts, joined: &mut BTreeSet<usize>) -> Result<()> {
    for row in &receipt.collections {
        row.validate()
            .map_err(|_| ProductionProjectionError::State)?;
        if row.period != receipt.resolve_tick {
            return Err(ProductionProjectionError::State);
        }
        if let Some(ordinal) = row.transfer_ordinal {
            let index = usize::try_from(ordinal).map_err(|_| ProductionProjectionError::State)?;
            let transfer = receipt
                .money_transfers
                .get(index)
                .ok_or(ProductionProjectionError::State)?;
            if !joined.insert(index)
                || transfer.purpose != MoneyTransferPurpose::Cash(CashTransferPurpose::MutualAid)
                || transfer.debit.location != MoneyLocation::Cash(AccountId::Household(row.donor))
                || transfer.credit.location
                    != MoneyLocation::Cash(AccountId::Organization(row.recipient))
                || transfer.debit.delta.micro_units().checked_neg()
                    != Some(row.collected.micro_units())
                || transfer.credit.delta != row.collected
            {
                return Err(ProductionProjectionError::State);
            }
        }
    }
    Ok(())
}

fn check_fresh(flows: &Flows) -> Result<()> {
    for flow in flows.values().filter(|flow| flow.requested > 0) {
        let ended = flow
            .dispatched
            .checked_add(flow.granted)
            .and_then(|q| q.checked_add(flow.unshipped))
            .ok_or(ProductionProjectionError::Arithmetic)?;
        if ended != flow.requested || flow.lost > 0 {
            return Err(ProductionProjectionError::State);
        }
    }
    Ok(())
}
fn reconcile_freight(
    prior: &MaterialCircuitState,
    current: &MaterialCircuitState,
    flows: &mut BTreeMap<OrderId, Flow>,
) -> Result<()> {
    let (CircuitAccounting::Monetary(before), CircuitAccounting::Monetary(after)) =
        (&prior.accounting, &current.accounting)
    else {
        return Err(ProductionProjectionError::State);
    };
    let mut actual: BTreeMap<_, _> = after
        .aid
        .freight
        .iter()
        .map(|l| (l.commitment_id, l))
        .collect();
    if actual.len() != after.aid.freight.len() {
        return Err(ProductionProjectionError::State);
    }
    for lot in &before.aid.freight {
        let flow = flows.entry(lot.commitment_id).or_default();
        if flow.requested > 0 || flow.dispatched > 0 || flow.unshipped > 0 {
            return Err(ProductionProjectionError::State);
        }
        let remaining = lot
            .quantity
            .checked_sub(flow.granted)
            .and_then(|q| q.checked_sub(flow.lost))
            .ok_or(ProductionProjectionError::State)?;
        match actual.remove(&lot.commitment_id) {
            Some(next)
                if next.quantity == remaining
                    && next.mandate_id == lot.mandate_id
                    && next.dispatch_period == lot.dispatch_period
                    && next.lot_id == lot.lot_id => {}
            None if remaining == 0 => {}
            _ => return Err(ProductionProjectionError::State),
        }
    }
    for (id, lot) in actual {
        let flow = flows.get(&id).ok_or(ProductionProjectionError::State)?;
        if flow.requested == 0
            || flow.dispatched != lot.quantity
            || lot.dispatch_period != prior.period
        {
            return Err(ProductionProjectionError::State);
        }
    }
    Ok(())
}
