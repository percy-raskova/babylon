//! Exact monetary and attendance evidence; physical account joins belong to the host.
use std::collections::BTreeSet;

use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, CashTransferPurpose, FinalDemandPrincipalId, LaborUseReceipt, MoneyLocation,
    MoneyPosting, MoneyTransferPurpose, MoneyTransferReceipt, OrderId, OrganizationAccountId,
    OutboundOrderId, PublicAccountId, ShiftId, SiteId, UnitId, WageAccrualReceipt,
};

use super::{MaterialWorldError, ReceiptCursor};

pub(super) const TRANSFER_BYTES: usize = 134;
pub(super) const ACCRUAL_BYTES: usize = 130;
pub(super) const LABOR_BYTES: usize = 160;

pub(super) fn validate_order(
    wages: &[WageAccrualReceipt],
    labor: &[LaborUseReceipt],
) -> Result<(), MaterialWorldError> {
    let mut shifts = BTreeSet::new();
    if wages.iter().any(|row| !shifts.insert(row.shift))
        || labor
            .windows(2)
            .any(|pair| (pair[0].site_id, pair[0].unit_id) >= (pair[1].site_id, pair[1].unit_id))
    {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}

fn account_parts(account: AccountId) -> (u8, [u8; 32]) {
    match account {
        AccountId::Site(id) => (1, id.as_bytes()),
        AccountId::Household(id) => (2, id.as_bytes()),
        AccountId::Organization(id) => (3, id.as_bytes()),
        AccountId::Public(id) => (4, id.as_bytes()),
    }
}

fn account(tag: u8, id: [u8; 32]) -> Result<AccountId, MaterialWorldError> {
    match tag {
        1 => Ok(AccountId::Site(SiteId::from_bytes(id))),
        2 => Ok(AccountId::Household(FinalDemandPrincipalId::from_bytes(id))),
        3 => Ok(AccountId::Organization(OrganizationAccountId::from_bytes(
            id,
        ))),
        4 => Ok(AccountId::Public(PublicAccountId::from_bytes(id))),
        _ => Err(MaterialWorldError::Wire),
    }
}

fn order_parts(order: OutboundOrderId) -> (u8, [u8; 32]) {
    match order {
        OutboundOrderId::Delivery(id) => (1, id.as_bytes()),
        OutboundOrderId::LocalFinalDemand(id) => (2, id.as_bytes()),
    }
}

fn order(tag: u8, id: [u8; 32]) -> Result<OutboundOrderId, MaterialWorldError> {
    match tag {
        1 => Ok(OutboundOrderId::Delivery(OrderId::from_bytes(id))),
        2 => Ok(OutboundOrderId::LocalFinalDemand(OrderId::from_bytes(id))),
        _ => Err(MaterialWorldError::Wire),
    }
}

fn cash_purpose_tag(purpose: CashTransferPurpose) -> u8 {
    match purpose {
        CashTransferPurpose::Tax => 1,
        CashTransferPurpose::PublicTransfer => 2,
        CashTransferPurpose::HouseholdTransfer => 3,
        CashTransferPurpose::OwnershipDistribution => 4,
        CashTransferPurpose::CapitalContribution => 5,
        CashTransferPurpose::TransportService => 6,
        CashTransferPurpose::MutualAid => 7,
    }
}

fn cash_purpose(tag: u8) -> Result<CashTransferPurpose, MaterialWorldError> {
    match tag {
        1 => Ok(CashTransferPurpose::Tax),
        2 => Ok(CashTransferPurpose::PublicTransfer),
        3 => Ok(CashTransferPurpose::HouseholdTransfer),
        4 => Ok(CashTransferPurpose::OwnershipDistribution),
        5 => Ok(CashTransferPurpose::CapitalContribution),
        6 => Ok(CashTransferPurpose::TransportService),
        7 => Ok(CashTransferPurpose::MutualAid),
        _ => Err(MaterialWorldError::Wire),
    }
}

fn write_tagged(tag: u8, subtype: u8, id: [u8; 32], bytes: &mut Vec<u8>) {
    bytes.extend_from_slice(&[tag, subtype]);
    bytes.extend_from_slice(&id);
}

fn write_purpose(purpose: MoneyTransferPurpose, bytes: &mut Vec<u8>) {
    use MoneyTransferPurpose as P;
    let (tag, subtype, id) = match purpose {
        P::PurchaseReservation(order) | P::DeliverySettlement(order) | P::PurchaseRefund(order) => {
            let (subtype, id) = order_parts(order);
            let tag = match purpose {
                P::PurchaseReservation(_) => 1,
                P::DeliverySettlement(_) => 2,
                _ => 3,
            };
            (tag, subtype, id)
        }
        P::ShiftReservation(id) => (4, 0, id.as_bytes()),
        P::WagePayment(id) => (5, 0, id.as_bytes()),
        P::ShiftCancellation(id) => (6, 0, id.as_bytes()),
        P::Cash(purpose) => (7, cash_purpose_tag(purpose), [0; 32]),
    };
    write_tagged(tag, subtype, id, bytes);
}

fn read_purpose(
    cursor: &mut ReceiptCursor<'_>,
) -> Result<MoneyTransferPurpose, MaterialWorldError> {
    use MoneyTransferPurpose as P;
    let [tag, subtype] = cursor.take()?;
    let id = cursor.take()?;
    match tag {
        1 => Ok(P::PurchaseReservation(order(subtype, id)?)),
        2 => Ok(P::DeliverySettlement(order(subtype, id)?)),
        3 => Ok(P::PurchaseRefund(order(subtype, id)?)),
        4 if subtype == 0 => Ok(P::ShiftReservation(ShiftId::from_bytes(id))),
        5 if subtype == 0 => Ok(P::WagePayment(ShiftId::from_bytes(id))),
        6 if subtype == 0 => Ok(P::ShiftCancellation(ShiftId::from_bytes(id))),
        7 if id == [0; 32] => Ok(P::Cash(cash_purpose(subtype)?)),
        _ => Err(MaterialWorldError::Wire),
    }
}

fn write_location(location: MoneyLocation, bytes: &mut Vec<u8>) {
    let (tag, subtype, id) = match location {
        MoneyLocation::Cash(owner) => {
            let (subtype, id) = account_parts(owner);
            (1, subtype, id)
        }
        MoneyLocation::PurchaseReserve(order) => {
            let (subtype, id) = order_parts(order);
            (2, subtype, id)
        }
        MoneyLocation::PayrollReserve(id) => (3, 0, id.as_bytes()),
    };
    write_tagged(tag, subtype, id, bytes);
}

fn read_location(cursor: &mut ReceiptCursor<'_>) -> Result<MoneyLocation, MaterialWorldError> {
    let [tag, subtype] = cursor.take()?;
    let id = cursor.take()?;
    match tag {
        1 => Ok(MoneyLocation::Cash(account(subtype, id)?)),
        2 => Ok(MoneyLocation::PurchaseReserve(order(subtype, id)?)),
        3 if subtype == 0 => Ok(MoneyLocation::PayrollReserve(ShiftId::from_bytes(id))),
        _ => Err(MaterialWorldError::Wire),
    }
}

fn validate_transfer(row: &MoneyTransferReceipt) -> Result<(), MaterialWorldError> {
    use MoneyLocation::{Cash, PayrollReserve, PurchaseReserve};
    use MoneyTransferPurpose as P;
    let debit = row.debit.delta.micro_units();
    let credit = row.credit.delta.micro_units();
    if debit >= 0 || credit <= 0 || debit.checked_add(credit) != Some(0) {
        return Err(MaterialWorldError::Wire);
    }
    let valid = match (row.purpose, row.debit.location, row.credit.location) {
        (P::PurchaseReservation(id), Cash(_), PurchaseReserve(reserve))
        | (P::DeliverySettlement(id) | P::PurchaseRefund(id), PurchaseReserve(reserve), Cash(_)) => {
            id == reserve
        }
        (P::ShiftReservation(id), Cash(_), PayrollReserve(reserve))
        | (P::WagePayment(id) | P::ShiftCancellation(id), PayrollReserve(reserve), Cash(_)) => {
            id == reserve
        }
        (P::Cash(_), Cash(sender), Cash(recipient)) => sender != recipient,
        _ => false,
    };
    if valid {
        Ok(())
    } else {
        Err(MaterialWorldError::Wire)
    }
}

pub(super) fn encode_transfer(
    row: &MoneyTransferReceipt,
    bytes: &mut Vec<u8>,
) -> Result<(), MaterialWorldError> {
    validate_transfer(row)?;
    write_purpose(row.purpose, bytes);
    for posting in [&row.debit, &row.credit] {
        write_location(posting.location, bytes);
        bytes.extend_from_slice(&posting.delta.micro_units().to_be_bytes());
    }
    Ok(())
}

pub(super) fn decode_transfer(
    cursor: &mut ReceiptCursor<'_>,
) -> Result<MoneyTransferReceipt, MaterialWorldError> {
    let row = MoneyTransferReceipt {
        purpose: read_purpose(cursor)?,
        debit: MoneyPosting {
            location: read_location(cursor)?,
            delta: Currency::from_micro_units(i128::from_be_bytes(cursor.take()?)),
        },
        credit: MoneyPosting {
            location: read_location(cursor)?,
            delta: Currency::from_micro_units(i128::from_be_bytes(cursor.take()?)),
        },
    };
    validate_transfer(&row)?;
    Ok(row)
}

fn validate_accrual(row: &WageAccrualReceipt, period: u64) -> Result<(), MaterialWorldError> {
    if row.employer == row.payee
        || row.period != period
        || row.obligated_hours == 0
        || row.amount.micro_units() <= 0
    {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}

pub(super) fn encode_accrual(
    row: &WageAccrualReceipt,
    period: u64,
    bytes: &mut Vec<u8>,
) -> Result<(), MaterialWorldError> {
    validate_accrual(row, period)?;
    bytes.extend_from_slice(&row.shift.as_bytes());
    for owner in [row.employer, row.payee] {
        let (tag, id) = account_parts(owner);
        bytes.push(tag);
        bytes.extend_from_slice(&id);
    }
    bytes.extend_from_slice(&row.period.to_be_bytes());
    bytes.extend_from_slice(&row.obligated_hours.to_be_bytes());
    bytes.extend_from_slice(&row.amount.micro_units().to_be_bytes());
    Ok(())
}

pub(super) fn decode_accrual(
    cursor: &mut ReceiptCursor<'_>,
    period: u64,
) -> Result<WageAccrualReceipt, MaterialWorldError> {
    let row = WageAccrualReceipt {
        shift: ShiftId::from_bytes(cursor.take()?),
        employer: account(cursor.take::<1>()?[0], cursor.take()?)?,
        payee: account(cursor.take::<1>()?[0], cursor.take()?)?,
        period: cursor.u64()?,
        obligated_hours: cursor.u64()?,
        amount: Currency::from_micro_units(i128::from_be_bytes(cursor.take()?)),
    };
    validate_accrual(&row, period)?;
    Ok(row)
}

fn validate_labor(row: &LaborUseReceipt, period: u64) -> Result<(), MaterialWorldError> {
    if row.period != period
        || row.planned_hours.checked_add(row.unplanned_hours) != Some(row.available_hours)
        || row.funded_hours.checked_add(row.unfunded_hours) != Some(row.planned_hours)
        || row.used_hours.checked_add(row.paid_idle_hours) != Some(row.funded_hours)
    {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}

pub(super) fn encode_labor(
    row: &LaborUseReceipt,
    period: u64,
    bytes: &mut Vec<u8>,
) -> Result<(), MaterialWorldError> {
    validate_labor(row, period)?;
    for id in [
        row.site_id.as_bytes(),
        row.unit_id.as_bytes(),
        row.payee.as_bytes(),
    ] {
        bytes.extend_from_slice(&id);
    }
    for value in [
        row.period,
        row.available_hours,
        row.planned_hours,
        row.unplanned_hours,
        row.funded_hours,
        row.unfunded_hours,
        row.used_hours,
        row.paid_idle_hours,
    ] {
        bytes.extend_from_slice(&value.to_be_bytes());
    }
    Ok(())
}

pub(super) fn decode_labor(
    cursor: &mut ReceiptCursor<'_>,
    period: u64,
) -> Result<LaborUseReceipt, MaterialWorldError> {
    let row = LaborUseReceipt {
        site_id: SiteId::from_bytes(cursor.take()?),
        unit_id: UnitId::from_bytes(cursor.take()?),
        payee: FinalDemandPrincipalId::from_bytes(cursor.take()?),
        period: cursor.u64()?,
        available_hours: cursor.u64()?,
        planned_hours: cursor.u64()?,
        unplanned_hours: cursor.u64()?,
        funded_hours: cursor.u64()?,
        unfunded_hours: cursor.u64()?,
        used_hours: cursor.u64()?,
        paid_idle_hours: cursor.u64()?,
    };
    validate_labor(&row, period)?;
    Ok(row)
}
