//! Fixed canonical gift evidence. Source authority remains in captured mandates.
use super::monetary_receipt::{account, account_parts};
use super::{MaterialWorldError, ReceiptCursor};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    aid_commitment_id, AidOutcome, AidReceipt, AidTransport, CircuitAccounting,
    FinalDemandPrincipalId, GoodId, LogisticsNodeId, MaterialCircuitState, OrderId, RouteId,
    UnitId,
};

pub(super) const ROW_BYTES: usize = 387;

pub(super) fn validate(rows: &[AidReceipt], tick: u64) -> Result<(), MaterialWorldError> {
    if rows.windows(2).any(|pair| {
        (pair[0].commitment_id, pair[0].outcome as u8)
            >= (pair[1].commitment_id, pair[1].outcome as u8)
    }) {
        return Err(MaterialWorldError::Wire);
    }
    for row in rows {
        validate_row(row, tick)?;
    }
    Ok(())
}

fn validate_row(row: &AidReceipt, tick: u64) -> Result<(), MaterialWorldError> {
    let valid = row.period == tick
        && tick > 0
        && row.dispatch_period > 0
        && row.dispatch_period <= tick
        && row.mandate_id != [0; 32]
        && row.commitment_id == aid_commitment_id(row.mandate_id, row.dispatch_period)
        && row.donor != row.recipient
        && row.quantity > 0
        && row.carrying_amount.micro_units() >= 0
        && row.cash_amount.micro_units() >= 0;
    if !valid {
        return Err(MaterialWorldError::Wire);
    }
    let zero_basis = row.carrying_amount.micro_units() == 0;
    let zero_cash = row.cash_amount.micro_units() == 0;
    let current = row.dispatch_period == tick;
    let outcome_valid = match (row.outcome, row.transport) {
        (AidOutcome::Requested, _) => {
            current && zero_basis && zero_cash && row.contribution_hours == 0
        }
        (AidOutcome::Unshipped, _) => {
            current && zero_basis && !zero_cash && row.contribution_hours == 0
        }
        (AidOutcome::Granted, AidTransport::Local)
        | (AidOutcome::Dispatched, AidTransport::Routed { .. }) => {
            current && !zero_cash && row.contribution_hours > 0
        }
        (AidOutcome::Granted | AidOutcome::Lost, AidTransport::Routed { .. }) => {
            !current && !zero_cash && row.contribution_hours == 0
        }
        _ => false,
    };
    if outcome_valid {
        Ok(())
    } else {
        Err(MaterialWorldError::Wire)
    }
}

pub(super) fn validate_state(
    rows: &[AidReceipt],
    state: &MaterialCircuitState,
) -> Result<(), MaterialWorldError> {
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        return if rows.is_empty() {
            Ok(())
        } else {
            Err(MaterialWorldError::Wire)
        };
    };
    for row in rows {
        let index = economy
            .aid
            .mandates
            .binary_search_by_key(&row.mandate_id, |mandate| mandate.id)
            .map_err(|_| MaterialWorldError::Wire)?;
        row.validate_against(&economy.aid.mandates[index])?;
    }
    Ok(())
}

pub(super) fn encode(
    rows: &[AidReceipt],
    tick: u64,
    bytes: &mut Vec<u8>,
) -> Result<(), MaterialWorldError> {
    validate(rows, tick)?;
    for row in rows {
        bytes.extend_from_slice(&row.commitment_id.as_bytes());
        bytes.extend_from_slice(&row.mandate_id);
        bytes.extend_from_slice(&row.period.to_be_bytes());
        bytes.extend_from_slice(&row.dispatch_period.to_be_bytes());
        let (tag, route, from, to) = match row.transport {
            AidTransport::Local => (1, [0; 32], [0; 32], [0; 32]),
            AidTransport::Routed {
                route_id,
                from_node_id,
                to_node_id,
            } => (
                2,
                route_id.as_bytes(),
                from_node_id.as_bytes(),
                to_node_id.as_bytes(),
            ),
        };
        bytes.push(tag);
        for id in [route, from, to] {
            bytes.extend_from_slice(&id);
        }
        let (payer, id) = account_parts(row.payer);
        bytes.push(payer);
        bytes.extend_from_slice(&id);
        for id in [
            row.donor.as_bytes(),
            row.recipient.as_bytes(),
            row.good_id.as_bytes(),
            row.unit_id.as_bytes(),
        ] {
            bytes.extend_from_slice(&id);
        }
        bytes.push(row.outcome as u8);
        bytes.extend_from_slice(&row.quantity.to_be_bytes());
        bytes.extend_from_slice(&row.carrying_amount.micro_units().to_be_bytes());
        bytes.extend_from_slice(&row.cash_amount.micro_units().to_be_bytes());
        bytes.extend_from_slice(&row.contribution_hours.to_be_bytes());
    }
    Ok(())
}

pub(super) fn decode(
    cursor: &mut ReceiptCursor<'_>,
    tick: u64,
) -> Result<AidReceipt, MaterialWorldError> {
    let commitment_id = OrderId::from_bytes(cursor.take()?);
    let mandate_id = cursor.take()?;
    let period = cursor.u64()?;
    let dispatch_period = cursor.u64()?;
    let [tag] = cursor.take()?;
    let route = cursor.take()?;
    let from = cursor.take()?;
    let to = cursor.take()?;
    let transport = match tag {
        1 if route == [0; 32] && from == [0; 32] && to == [0; 32] => AidTransport::Local,
        2 => AidTransport::Routed {
            route_id: RouteId::from_bytes(route),
            from_node_id: LogisticsNodeId::from_bytes(from),
            to_node_id: LogisticsNodeId::from_bytes(to),
        },
        _ => return Err(MaterialWorldError::Wire),
    };
    let [payer_tag] = cursor.take()?;
    let payer = account(payer_tag, cursor.take()?)?;
    let donor = FinalDemandPrincipalId::from_bytes(cursor.take()?);
    let recipient = FinalDemandPrincipalId::from_bytes(cursor.take()?);
    let good_id = GoodId::from_bytes(cursor.take()?);
    let unit_id = UnitId::from_bytes(cursor.take()?);
    let [outcome] = cursor.take()?;
    let outcome = match outcome {
        1 => AidOutcome::Requested,
        2 => AidOutcome::Dispatched,
        3 => AidOutcome::Granted,
        4 => AidOutcome::Lost,
        5 => AidOutcome::Unshipped,
        _ => return Err(MaterialWorldError::Wire),
    };
    let row = AidReceipt {
        commitment_id,
        mandate_id,
        period,
        dispatch_period,
        transport,
        payer,
        donor,
        recipient,
        good_id,
        unit_id,
        outcome,
        quantity: cursor.u64()?,
        carrying_amount: Currency::from_micro_units(i128::from_be_bytes(cursor.take()?)),
        cash_amount: Currency::from_micro_units(i128::from_be_bytes(cursor.take()?)),
        contribution_hours: cursor.u64()?,
    };
    validate_row(&row, tick)?;
    Ok(row)
}
