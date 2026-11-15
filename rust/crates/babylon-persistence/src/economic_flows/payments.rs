//! Project the signed custody tape into once-only economic settlements.
use super::accounts;
use super::model::FlowResult;
use super::principals::{Parties, Principals};
use super::{EconomicFlowError, EconomicPaymentPeriod, Settlement};
use crate::economic_content::EconomicContentAdmission;
use crate::observer_reader::CommittedMaterialReceipts;
use babylon_material_circuit::{
    AccountId, CircuitAccounting, MoneyLocation, MoneyTransferPurpose, MoneyTransferReceipt,
};
use babylon_tick::material_world::MaterialWorldRegister;

pub(crate) fn project(
    source: CommittedMaterialReceipts,
    foundation: &EconomicContentAdmission,
    previous: &MaterialWorldRegister,
    current: &MaterialWorldRegister,
) -> FlowResult<EconomicPaymentPeriod> {
    let (before, after, opening) = match (
        &previous.state().accounting,
        &current.state().accounting,
        &foundation.initial_register().state().accounting,
    ) {
        (
            CircuitAccounting::Monetary(before),
            CircuitAccounting::Monetary(after),
            CircuitAccounting::Monetary(opening),
        ) => (before, after, opening),
        (
            CircuitAccounting::PhysicalControl,
            CircuitAccounting::PhysicalControl,
            CircuitAccounting::PhysicalControl,
        ) if source.receipts.money_transfers.is_empty() => {
            return Ok(EconomicPaymentPeriod {
                source,
                accounts: Vec::new(),
                settlements: Vec::new(),
            })
        }
        _ => return Err(EconomicFlowError::MonetaryBookMismatch),
    };
    let catalog = foundation
        .foundation()
        .graph_foundation()
        .content_bundle()
        .economic_catalog()
        .ok_or(EconomicFlowError::MonetaryBookMismatch)?;
    let accounts = accounts::project(catalog, &opening.book)?;
    let agency = current
        .city_pd()
        .into_iter()
        .flat_map(|row| &row.attempts)
        .map(|attempt| &attempt.funding);
    let principals = Principals::for_period(&before.book, &after.book, &source.receipts, agency)?;
    let mut settlements = Vec::new();
    for (ordinal, transfer) in source.receipts.money_transfers.iter().enumerate() {
        if let Some((payer, recipient)) = parties(transfer, &principals)? {
            for account in [payer, recipient] {
                opening
                    .book
                    .cash(account)
                    .map_err(|_| EconomicFlowError::UnknownCashAccount)?;
            }
            settlements.push(Settlement {
                ordinal: u64::try_from(ordinal).map_err(|_| EconomicFlowError::ReceiptOrdinal)?,
                payer: payer.into(),
                recipient: recipient.into(),
            });
        }
    }
    Ok(EconomicPaymentPeriod {
        source,
        accounts,
        settlements,
    })
}

pub(super) fn parties(
    transfer: &MoneyTransferReceipt,
    principals: &Principals,
) -> FlowResult<Option<(AccountId, AccountId)>> {
    use MoneyTransferPurpose as Purpose;
    let amount = transfer.credit.delta.micro_units();
    if amount <= 0 || transfer.debit.delta.micro_units().checked_add(amount) != Some(0) {
        return Err(EconomicFlowError::InvalidPosting);
    }
    match transfer.purpose {
        Purpose::PurchaseReservation(id)
        | Purpose::PurchaseRefund(id)
        | Purpose::DeliverySettlement(id) => {
            let owner = principals
                .purchases
                .get(&id)
                .ok_or(EconomicFlowError::UnknownOrderPrincipal)?;
            if amount % owner.price.micro_units() != 0 {
                return Err(EconomicFlowError::InvalidPosting);
            }
            reserve_parties(transfer, *owner, MoneyLocation::PurchaseReserve(id))
        }
        Purpose::ShiftReservation(id)
        | Purpose::ShiftCancellation(id)
        | Purpose::WagePayment(id) => {
            let owner = principals
                .shifts
                .get(&id)
                .ok_or(EconomicFlowError::UnknownShiftPrincipal)?;
            if amount != owner.price.micro_units() {
                return Err(EconomicFlowError::InvalidPosting);
            }
            reserve_parties(transfer, *owner, MoneyLocation::PayrollReserve(id))
        }
        Purpose::Cash(_) => match (transfer.debit.location, transfer.credit.location) {
            (MoneyLocation::Cash(payer), MoneyLocation::Cash(recipient)) if payer != recipient => {
                Ok(Some((payer, recipient)))
            }
            _ => Err(EconomicFlowError::InvalidPosting),
        },
    }
}

fn reserve_parties(
    transfer: &MoneyTransferReceipt,
    owner: Parties,
    reserve: MoneyLocation,
) -> FlowResult<Option<(AccountId, AccountId)>> {
    use MoneyTransferPurpose as Purpose;
    let payer = MoneyLocation::Cash(owner.payer);
    let recipient = MoneyLocation::Cash(owner.recipient);
    let postings = (transfer.debit.location, transfer.credit.location);
    match transfer.purpose {
        Purpose::PurchaseReservation(_) | Purpose::ShiftReservation(_)
            if postings == (payer, reserve) =>
        {
            Ok(None)
        }
        Purpose::PurchaseRefund(_) | Purpose::ShiftCancellation(_)
            if postings == (reserve, payer) =>
        {
            Ok(None)
        }
        Purpose::DeliverySettlement(_) | Purpose::WagePayment(_)
            if postings == (reserve, recipient) =>
        {
            Ok(Some((owner.payer, owner.recipient)))
        }
        _ => Err(EconomicFlowError::InvalidPosting),
    }
}
