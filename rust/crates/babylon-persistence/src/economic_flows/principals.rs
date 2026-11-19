//! Counterparties captured before reservation, including orders retired within the period.
use super::model::FlowResult;
use super::EconomicFlowError;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, AgencyObservationFundingReceipt, MonetaryBook, MonetaryError, MoneyTransferPurpose,
    OutboundOrderId, ShiftId,
};
use babylon_tick::material_world::MaterialTickReceipts;
use std::collections::BTreeMap;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct Parties {
    pub(crate) payer: AccountId,
    pub(crate) recipient: AccountId,
    /// Per unit for a purchase, entire funded obligation for a shift.
    pub(crate) price: Currency,
}

#[derive(Default)]
pub(crate) struct Principals {
    pub(crate) purchases: BTreeMap<OutboundOrderId, Parties>,
    pub(crate) shifts: BTreeMap<ShiftId, Parties>,
}

fn bind<K: Ord>(
    table: &mut BTreeMap<K, Parties>,
    key: K,
    payer: AccountId,
    recipient: AccountId,
    price: Currency,
) -> FlowResult<()> {
    let parties = Parties {
        payer,
        recipient,
        price,
    };
    if payer == recipient
        || price.micro_units() <= 0
        || table.insert(key, parties).is_some_and(|old| old != parties)
    {
        return Err(EconomicFlowError::ConflictingPrincipal);
    }
    Ok(())
}

impl Principals {
    pub(super) fn for_period<'a>(
        before: &MonetaryBook,
        after: &MonetaryBook,
        receipts: &MaterialTickReceipts,
        agency: impl IntoIterator<Item = &'a AgencyObservationFundingReceipt>,
    ) -> FlowResult<Self> {
        let mut result = Self::purchases_for_period(before, after, receipts)?;
        result.payroll(before, after, receipts, agency)?;
        Ok(result)
    }
    pub(crate) fn purchases_for_period(
        before: &MonetaryBook,
        after: &MonetaryBook,
        receipts: &MaterialTickReceipts,
    ) -> FlowResult<Self> {
        let mut result = Self::default();
        for row in before.purchases().chain(after.purchases()) {
            bind(
                &mut result.purchases,
                row.order,
                row.buyer,
                row.seller,
                row.unit_price,
            )?;
        }
        result.retired_purchases(receipts)?;
        Ok(result)
    }

    fn retired_purchases(&mut self, receipts: &MaterialTickReceipts) -> FlowResult<()> {
        for row in &receipts.household_demand {
            if row.admitted_quantity > 0 {
                bind(
                    &mut self.purchases,
                    OutboundOrderId::LocalFinalDemand(row.order_id),
                    AccountId::Household(row.principal_id),
                    AccountId::Site(row.retailer_site_id),
                    row.unit_price,
                )?;
            }
        }
        for row in &receipts.procurement {
            if row.admitted_quantity > 0 {
                bind(
                    &mut self.purchases,
                    OutboundOrderId::Delivery(row.order_id),
                    AccountId::Site(row.buyer_site_id),
                    AccountId::Site(row.supplier_site_id),
                    row.unit_price,
                )?;
            }
        }
        for row in &receipts.investment {
            if row.admitted_units > 0 {
                bind(
                    &mut self.purchases,
                    OutboundOrderId::Delivery(row.order_id),
                    AccountId::Site(row.site_id),
                    AccountId::Site(row.supplier_site_id),
                    row.unit_price,
                )?;
            }
        }
        for row in &receipts.service_performance {
            if row.admitted_quantity > 0 {
                bind(
                    &mut self.purchases,
                    OutboundOrderId::Service(row.order_id),
                    row.buyer,
                    AccountId::Site(row.provider_site_id),
                    row.unit_price,
                )?;
            }
        }
        Ok(())
    }

    fn payroll<'a>(
        &mut self,
        before: &MonetaryBook,
        after: &MonetaryBook,
        receipts: &MaterialTickReceipts,
        agency: impl IntoIterator<Item = &'a AgencyObservationFundingReceipt>,
    ) -> FlowResult<()> {
        for row in &receipts.wage_accruals {
            bind(
                &mut self.shifts,
                row.shift,
                row.employer,
                row.payee,
                row.amount,
            )?;
        }
        for funding in agency {
            let input = &funding.input;
            if input.due_period == receipts.resolve_tick && funding.reserved.micro_units() > 0 {
                bind(
                    &mut self.shifts,
                    input.shift_id,
                    AccountId::Organization(input.agency),
                    AccountId::Household(input.principal_id),
                    funding.reserved,
                )?;
            }
        }
        for transfer in &receipts.money_transfers {
            let (MoneyTransferPurpose::ShiftReservation(id)
            | MoneyTransferPurpose::WagePayment(id)
            | MoneyTransferPurpose::ShiftCancellation(id)) = transfer.purpose
            else {
                continue;
            };
            for book in [before, after] {
                match book.shift(id) {
                    Ok(shift) => {
                        let amount = shift
                            .hourly_rate
                            .micro_units()
                            .checked_mul(i128::from(shift.committed_hours))
                            .ok_or(EconomicFlowError::InvalidPosting)?;
                        bind(
                            &mut self.shifts,
                            id,
                            shift.employer,
                            shift.payee,
                            Currency::from_micro_units(amount),
                        )?;
                    }
                    Err(MonetaryError::UnknownShift) => {}
                    Err(_) => return Err(EconomicFlowError::UnknownShiftPrincipal),
                }
            }
        }
        Ok(())
    }
}
