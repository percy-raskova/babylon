//! Canonical cash, reserves and attendance terms inside the material state.

use babylon_kernel::currency::Currency;

use super::{append_rows, decode_rows, Cursor};
use crate::{
    AccountId, CashAccount, CircuitAccounting, EmploymentTerms, FinalDemandPrincipalId,
    FundedShift, MaterialCircuitError, MonetaryBook, MonetaryBookSnapshot, MonetaryCircuit,
    OrderId, OrganizationAccountId, OutboundOrderId, PublicAccountId, PurchaseEscrow, ShiftId,
    ShiftState, SiteId, UnitId,
};

fn append_account(output: &mut Vec<u8>, account: AccountId) {
    let (tag, identity) = match account {
        AccountId::Site(id) => (1, id.as_bytes()),
        AccountId::Household(id) => (2, id.as_bytes()),
        AccountId::Organization(id) => (3, id.as_bytes()),
        AccountId::Public(id) => (4, id.as_bytes()),
    };
    output.push(tag);
    output.extend_from_slice(&identity);
}

fn decode_account(cursor: &mut Cursor<'_>) -> Result<AccountId, MaterialCircuitError> {
    match cursor.u8()? {
        1 => Ok(AccountId::Site(SiteId::from_bytes(cursor.array()?))),
        2 => Ok(AccountId::Household(FinalDemandPrincipalId::from_bytes(
            cursor.array()?,
        ))),
        3 => Ok(AccountId::Organization(OrganizationAccountId::from_bytes(
            cursor.array()?,
        ))),
        4 => Ok(AccountId::Public(PublicAccountId::from_bytes(
            cursor.array()?,
        ))),
        _ => Err(MaterialCircuitError::WireEnum),
    }
}

fn append_order(output: &mut Vec<u8>, order: OutboundOrderId) {
    let (tag, id) = match order {
        OutboundOrderId::Delivery(id) => (1, id),
        OutboundOrderId::LocalFinalDemand(id) => (2, id),
    };
    output.push(tag);
    output.extend_from_slice(&id.as_bytes());
}

fn decode_order(cursor: &mut Cursor<'_>) -> Result<OutboundOrderId, MaterialCircuitError> {
    match cursor.u8()? {
        1 => Ok(OutboundOrderId::Delivery(OrderId::from_bytes(
            cursor.array()?,
        ))),
        2 => Ok(OutboundOrderId::LocalFinalDemand(OrderId::from_bytes(
            cursor.array()?,
        ))),
        _ => Err(MaterialCircuitError::WireEnum),
    }
}

fn decode_currency(cursor: &mut Cursor<'_>) -> Result<Currency, MaterialCircuitError> {
    Ok(Currency::from_micro_units(i128::from_be_bytes(
        cursor.array()?,
    )))
}

pub(super) fn append(
    output: &mut Vec<u8>,
    accounting: &CircuitAccounting,
) -> Result<(), MaterialCircuitError> {
    let CircuitAccounting::Monetary(economy) = accounting else {
        output.push(0);
        return Ok(());
    };
    output.push(1);
    let snapshot = economy.book.snapshot();
    append_rows(output, &snapshot.accounts, |bytes, row| {
        append_account(bytes, row.id);
        bytes.extend_from_slice(&row.cash.micro_units().to_be_bytes());
    })?;
    append_rows(output, &snapshot.purchases, |bytes, row| {
        append_order(bytes, row.order);
        append_account(bytes, row.buyer);
        append_account(bytes, row.seller);
        bytes.extend_from_slice(&row.quantity.to_be_bytes());
        bytes.extend_from_slice(&row.unit_price.micro_units().to_be_bytes());
        bytes.extend_from_slice(&row.delivered.to_be_bytes());
        bytes.extend_from_slice(&row.refunded.to_be_bytes());
    })?;
    append_rows(output, &snapshot.shifts, |bytes, row| {
        bytes.extend_from_slice(&row.id.as_bytes());
        append_account(bytes, row.employer);
        append_account(bytes, row.payee);
        bytes.extend_from_slice(&row.period.to_be_bytes());
        bytes.extend_from_slice(&row.committed_hours.to_be_bytes());
        bytes.extend_from_slice(&row.hourly_rate.micro_units().to_be_bytes());
        bytes.push(match row.state {
            ShiftState::Reserved => 1,
            ShiftState::Accrued => 2,
            ShiftState::Paid => 3,
            ShiftState::Cancelled => 4,
        });
    })?;
    append_rows(output, &economy.employment, |bytes, row| {
        bytes.extend_from_slice(&row.site_id.as_bytes());
        bytes.extend_from_slice(&row.unit_id.as_bytes());
        bytes.extend_from_slice(&row.payee.as_bytes());
        bytes.extend_from_slice(&row.hourly_rate.micro_units().to_be_bytes());
    })?;
    Ok(())
}

fn ordered_rows<T, K: Ord>(rows: &[T], key: impl Fn(&T) -> K) -> Result<(), MaterialCircuitError> {
    if rows.windows(2).any(|pair| key(&pair[0]) >= key(&pair[1])) {
        return Err(MaterialCircuitError::WireNoncanonical);
    }
    Ok(())
}

pub(super) fn decode(cursor: &mut Cursor<'_>) -> Result<CircuitAccounting, MaterialCircuitError> {
    match cursor.u8()? {
        0 => return Ok(CircuitAccounting::PhysicalControl),
        1 => {}
        _ => return Err(MaterialCircuitError::WireEnum),
    }
    let accounts = decode_rows(cursor, |bytes| {
        Ok(CashAccount {
            id: decode_account(bytes)?,
            cash: decode_currency(bytes)?,
        })
    })?;
    let purchases = decode_rows(cursor, |bytes| {
        Ok(PurchaseEscrow {
            order: decode_order(bytes)?,
            buyer: decode_account(bytes)?,
            seller: decode_account(bytes)?,
            quantity: bytes.u64()?,
            unit_price: decode_currency(bytes)?,
            delivered: bytes.u64()?,
            refunded: bytes.u64()?,
        })
    })?;
    let shifts = decode_rows(cursor, |bytes| {
        Ok(FundedShift {
            id: ShiftId::from_bytes(bytes.array()?),
            employer: decode_account(bytes)?,
            payee: decode_account(bytes)?,
            period: bytes.u64()?,
            committed_hours: bytes.u64()?,
            hourly_rate: decode_currency(bytes)?,
            state: match bytes.u8()? {
                1 => ShiftState::Reserved,
                2 => ShiftState::Accrued,
                3 => ShiftState::Paid,
                4 => ShiftState::Cancelled,
                _ => return Err(MaterialCircuitError::WireEnum),
            },
        })
    })?;
    let employment = decode_rows(cursor, |bytes| {
        Ok(EmploymentTerms {
            site_id: SiteId::from_bytes(bytes.array()?),
            unit_id: UnitId::from_bytes(bytes.array()?),
            payee: FinalDemandPrincipalId::from_bytes(bytes.array()?),
            hourly_rate: decode_currency(bytes)?,
        })
    })?;
    // The book constructor normalizes into ordered maps. Check the actual input
    // sequence first so malformed wire order cannot disappear during admission.
    ordered_rows(&accounts, |row| row.id)?;
    ordered_rows(&purchases, |row| row.order)?;
    ordered_rows(&shifts, |row| row.id)?;
    ordered_rows(&employment, |row| (row.site_id, row.unit_id))?;
    Ok(CircuitAccounting::Monetary(MonetaryCircuit {
        book: MonetaryBook::from_snapshot(MonetaryBookSnapshot {
            accounts,
            purchases,
            shifts,
        })?,
        employment,
    }))
}
