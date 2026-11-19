//! Cash postings retain their legal classification. A release from group-owned escrow to a
//! member's spendable account increases group liquidity by the exact amount of the release.
use super::endpoint;
use super::income;
use super::{CompanyCashFlow, CompanyPeriod, CompanyStatementsError};
use crate::economic_flows::Principals;
use crate::site_financial_statements::{self, CashFlowCategory};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{AccountId, CompanyId, MoneyLocation, MoneyTransferPurpose, SiteId};
use babylon_tick::material_world::MaterialTickReceipts;
use std::collections::BTreeMap;

impl CompanyCashFlow {
    fn record(
        &mut self,
        category: CashFlowCategory,
        delta: Currency,
    ) -> Result<(), CompanyStatementsError> {
        let target = match category {
            CashFlowCategory::Operating => &mut self.operating,
            CashFlowCategory::Investing => &mut self.investing,
            CashFlowCategory::Financing => &mut self.financing,
            CashFlowCategory::ReserveReclassification => &mut self.reserve_reclassification,
        };
        income::add(target, delta)
    }
}
pub(super) fn project(
    reports: &mut BTreeMap<CompanyId, CompanyPeriod>,
    members: &BTreeMap<SiteId, CompanyId>,
    receipts: &MaterialTickReceipts,
    principals: &Principals,
) -> Result<(), CompanyStatementsError> {
    let investments = site_financial_statements::investment_reservations(None, receipts)
        .map_err(CompanyStatementsError::SiteBooks)?;
    for transfer in &receipts.money_transfers {
        let internal = match (transfer.debit.location, transfer.credit.location) {
            (MoneyLocation::Cash(a), MoneyLocation::Cash(b)) => {
                endpoint::group(a, members).filter(|g| endpoint::group(b, members) == Some(*g))
            }
            _ => None,
        };
        let escrow = match transfer.purpose {
            MoneyTransferPurpose::PurchaseReservation(id)
            | MoneyTransferPurpose::PurchaseRefund(id)
            | MoneyTransferPurpose::DeliverySettlement(id) => {
                let row = principals
                    .purchases
                    .get(&id)
                    .ok_or(CompanyStatementsError::ActivityMismatch)?;
                endpoint::group(row.payer, members)
                    .filter(|g| endpoint::group(row.recipient, members) == Some(*g))
            }
            _ => None,
        };
        for posting in [&transfer.debit, &transfer.credit] {
            let MoneyLocation::Cash(account) = posting.location else {
                continue;
            };
            let Some(company) = endpoint::group(account, members) else {
                continue;
            };
            let r = reports
                .get_mut(&company)
                .ok_or(CompanyStatementsError::TreasuryMismatch(company))?;
            let category =
                site_financial_statements::category(transfer, account, posting.delta, &investments)
                    .map_err(CompanyStatementsError::SiteBooks)?;
            let legal = if matches!(account, AccountId::Company(_)) {
                &mut r.parent
            } else {
                &mut r.subsidiaries
            };
            legal.cash_flow.record(category, posting.delta)?;
            if internal.is_none() {
                let category = if escrow == Some(company) {
                    CashFlowCategory::ReserveReclassification
                } else {
                    category
                };
                r.consolidated.cash_flow.record(category, posting.delta)?;
            }
        }
    }
    Ok(())
}
