//! Adjacent authenticated aid evidence. No allocation, pricing or economic replay.
use super::ProductionProjectionError;
use babylon_material_circuit::{
    AccountId, AidCashReserve, AidMandate, AidOutcome, AidReceipt, AidTransport, CircuitAccounting,
    FinalDemandPrincipalId, GoodId, MaterialCircuitState, MonetaryCircuit, MoneyLocation,
    MoneyTransferPurpose, MoneyTransferReceipt, OrderId, UnitId,
};
use babylon_tick::material_world::MaterialTickReceipts;
use std::collections::{BTreeMap, BTreeSet};
type Result<T> = std::result::Result<T, ProductionProjectionError>;
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
type Posting = (MoneyLocation, MoneyLocation, i128);
type Cash = BTreeMap<(OrderId, u8), Posting>;
type Reserves = BTreeMap<OrderId, AidCashReserve>;
type Reservations = BTreeMap<OrderId, u64>;
pub(super) fn join(
    prior: &MaterialCircuitState,
    current: &MaterialCircuitState,
    receipt: &MaterialTickReceipts,
) -> Result<Gifts> {
    let (CircuitAccounting::Monetary(before), CircuitAccounting::Monetary(after)) =
        (&prior.accounting, &current.accounting)
    else {
        return if receipt.aid.is_empty() {
            Ok(Gifts::default())
        } else {
            Err(ProductionProjectionError::State)
        };
    };
    if before.aid.mandates != after.aid.mandates
        || receipt.resolve_tick != prior.period
        || prior.period.checked_add(1) != Some(current.period)
    {
        return Err(ProductionProjectionError::History);
    }
    let mandates: Mandates<'_> = before.aid.mandates.iter().map(|m| (m.id, m)).collect();
    if mandates.len() != before.aid.mandates.len() {
        return Err(ProductionProjectionError::State);
    }
    let (gifts, mut flows, cash) = collect(receipt, &mandates)?;
    reconcile_freight(prior, current, &mut flows)?;
    let reservations = check_cash(before, after, receipt, &mandates, cash)?;
    check_fresh(flows, reservations)?;
    Ok(gifts)
}
fn collect(
    receipt: &MaterialTickReceipts,
    mandates: &Mandates<'_>,
) -> Result<(Gifts, Flows, Cash)> {
    let mut gifts = Gifts::default();
    let mut seen = BTreeSet::new();
    let mut flows = BTreeMap::<OrderId, Flow>::new();
    let mut cash = BTreeMap::<(OrderId, u8), (MoneyLocation, MoneyLocation, i128)>::new();
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
        record_payment(row, &mut cash)?;
    }
    Ok((gifts, flows, cash))
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
        AidOutcome::Unshipped => add(&mut flow.unshipped, row.quantity)?,
    }
    Ok(())
}
fn record_payment(row: &AidReceipt, cash: &mut Cash) -> Result<()> {
    let payment = match row.outcome {
        AidOutcome::Granted => Some((1, MoneyLocation::Cash(AccountId::Household(row.recipient)))),
        AidOutcome::Lost | AidOutcome::Unshipped => Some((2, MoneyLocation::Cash(row.payer))),
        _ => None,
    };
    if let Some((tag, target)) = payment {
        let entry = cash.entry((row.commitment_id, tag)).or_insert((
            MoneyLocation::AidReserve(row.commitment_id),
            target,
            0,
        ));
        if entry.1 != target {
            return Err(ProductionProjectionError::State);
        }
        entry.2 = entry
            .2
            .checked_add(row.cash_amount.micro_units())
            .ok_or(ProductionProjectionError::Arithmetic)?;
    }
    Ok(())
}
fn check_cash(
    before: &MonetaryCircuit,
    after: &MonetaryCircuit,
    receipt: &MaterialTickReceipts,
    mandates: &Mandates<'_>,
    mut cash: Cash,
) -> Result<Reservations> {
    let mut reservations = BTreeMap::<OrderId, u64>::new();
    let mut reserves: BTreeMap<_, _> = before
        .book
        .snapshot()
        .aid
        .into_iter()
        .map(|r| (r.id, r))
        .collect();
    for transfer in &receipt.money_transfers {
        let (id, tag) = match transfer.purpose {
            MoneyTransferPurpose::AidReservation(id) => (id, 0),
            MoneyTransferPurpose::AidGrant(id) => (id, 1),
            MoneyTransferPurpose::AidRefund(id) => (id, 2),
            _ => continue,
        };
        let expected = if tag == 0 {
            reserve_transfer(
                id,
                transfer,
                receipt,
                mandates,
                &mut reservations,
                &mut reserves,
            )?
        } else {
            settle_transfer(id, tag, &mut cash, &mut reserves)?
        };
        if (
            transfer.debit.location,
            transfer.credit.location,
            transfer.credit.delta.micro_units(),
        ) != expected
            || transfer.debit.delta.micro_units().checked_neg() != Some(expected.2)
        {
            return Err(ProductionProjectionError::State);
        }
    }
    if !cash.is_empty() {
        return Err(ProductionProjectionError::State);
    }
    reserves.retain(|_, r| r.granted.checked_add(r.refunded) != Some(r.quantity));
    let actual: BTreeMap<_, _> = after
        .book
        .snapshot()
        .aid
        .into_iter()
        .map(|r| (r.id, r))
        .collect();
    if reserves != actual {
        return Err(ProductionProjectionError::State);
    }
    Ok(reservations)
}
fn reserve_transfer(
    id: OrderId,
    transfer: &MoneyTransferReceipt,
    receipt: &MaterialTickReceipts,
    mandates: &Mandates<'_>,
    reservations: &mut Reservations,
    reserves: &mut Reserves,
) -> Result<Posting> {
    let row = receipt
        .aid
        .iter()
        .find(|r| r.commitment_id == id && r.outcome == AidOutcome::Requested)
        .ok_or(ProductionProjectionError::State)?;
    let mandate = mandates
        .get(&row.mandate_id)
        .ok_or(ProductionProjectionError::State)?;
    let amount = transfer.credit.delta.micro_units();
    let price = mandate.cash_per_unit.micro_units();
    if amount <= 0 || price <= 0 || amount % price != 0 {
        return Err(ProductionProjectionError::State);
    }
    let quantity =
        u64::try_from(amount / price).map_err(|_| ProductionProjectionError::Arithmetic)?;
    if quantity > row.quantity || reservations.insert(id, quantity).is_some() {
        return Err(ProductionProjectionError::State);
    }
    if reserves
        .insert(
            id,
            AidCashReserve {
                id,
                payer: row.payer,
                donor: row.donor,
                recipient: row.recipient,
                quantity,
                cash_per_unit: mandate.cash_per_unit,
                granted: 0,
                refunded: 0,
            },
        )
        .is_some()
    {
        return Err(ProductionProjectionError::State);
    }
    Ok((
        MoneyLocation::Cash(row.payer),
        MoneyLocation::AidReserve(id),
        amount,
    ))
}
fn settle_transfer(
    id: OrderId,
    tag: u8,
    cash: &mut Cash,
    reserves: &mut Reserves,
) -> Result<Posting> {
    let expected = cash
        .remove(&(id, tag))
        .ok_or(ProductionProjectionError::State)?;
    let reserve = reserves
        .get_mut(&id)
        .ok_or(ProductionProjectionError::State)?;
    let price = reserve.cash_per_unit.micro_units();
    if price <= 0 || expected.2 <= 0 || expected.2 % price != 0 {
        return Err(ProductionProjectionError::State);
    }
    let quantity =
        u64::try_from(expected.2 / price).map_err(|_| ProductionProjectionError::Arithmetic)?;
    if tag == 1 {
        add(&mut reserve.granted, quantity)?;
    } else {
        add(&mut reserve.refunded, quantity)?;
    }
    reserve
        .reserved_amount()
        .map_err(|_| ProductionProjectionError::State)?;
    Ok(expected)
}
fn check_fresh(flows: Flows, mut reservations: Reservations) -> Result<()> {
    for (id, flow) in flows {
        let fresh = reservations.remove(&id).unwrap_or(0);
        if flow.requested > 0 {
            let dispatched = flow
                .dispatched
                .checked_add(flow.granted)
                .and_then(|q| q.checked_add(flow.unshipped))
                .ok_or(ProductionProjectionError::Arithmetic)?;
            if dispatched != fresh || fresh > flow.requested || flow.lost > 0 {
                return Err(ProductionProjectionError::State);
            }
        } else if fresh > 0 {
            return Err(ProductionProjectionError::State);
        }
    }
    if !reservations.is_empty() {
        return Err(ProductionProjectionError::State);
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
