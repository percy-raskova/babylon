//! Selected-account joins over admitted books and complete committed receipts.
use super::balances;
use super::{
    CashFlowCategory, CashFlowStatement, CashFlowTransfer, PlanningControl, SiteBalanceSheet,
    SiteBookStatements, SiteCashFlowTotals, SitePeriodActivity, SiteStatementsError,
};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, CashTransferPurpose, CircuitAccounting, HistoricalCostSnapshot, IncomeReceipt,
    MonetaryBookSnapshot, MoneyLocation, MoneyTransferPurpose, MoneyTransferReceipt,
    OutboundOrderId, SiteId,
};
use babylon_tick::material_world::MaterialTickReceipts;

use std::collections::BTreeMap;

use std::result::Result as StdResult;

type Result<T> = StdResult<T, SiteStatementsError>;
pub(super) fn zero() -> Currency {
    Currency::from_micro_units(0)
}
pub(super) fn add(a: Currency, b: Currency) -> Result<Currency> {
    a.checked_add(b)
        .map_err(|_| SiteStatementsError::Arithmetic)
}
pub(super) fn sub(a: Currency, b: Currency) -> Result<Currency> {
    a.checked_sub(b)
        .map_err(|_| SiteStatementsError::Arithmetic)
}
pub(super) fn sum(values: impl IntoIterator<Item = Currency>) -> Result<Currency> {
    values.into_iter().try_fold(zero(), add)
}

pub(super) fn balance(
    site: SiteId,
    money: &MonetaryBookSnapshot,
    costs: &HistoricalCostSnapshot,
) -> Result<SiteBalanceSheet> {
    balances::collect(money, costs, Some(site), |_, _| Ok(()))?
        .remove(&site)
        .ok_or(SiteStatementsError::SiteAbsent)
}

pub(crate) fn project(
    site: SiteId,
    opening: Option<&CircuitAccounting>,
    closing: &CircuitAccounting,
    receipts: Option<&MaterialTickReceipts>,
) -> Result<SiteBookStatements> {
    let CircuitAccounting::Monetary(close) = closing else {
        return Err(SiteStatementsError::MonetaryBooksUnavailable);
    };
    let closing = balance(site, &close.book.snapshot(), &close.costs.snapshot())?;
    let ownership_claims = close
        .financial
        .ownership
        .iter()
        .filter(|r| r.issuer_site_id == site)
        .cloned()
        .collect();
    let (opening, activity) = match (opening, receipts) {
        (None, None) => (None, None),
        (Some(CircuitAccounting::Monetary(open)), Some(receipts)) => {
            let opening = balance(site, &open.book.snapshot(), &open.costs.snapshot())?;
            let activity = activity(site, &opening, &closing, receipts)?;
            (Some(opening), Some(activity))
        }
        _ => return Err(SiteStatementsError::PeriodMismatch),
    };
    Ok(SiteBookStatements {
        opening,
        closing,
        activity,
        ownership_claims,
        planning_control: PlanningControl::NotCaptured,
    })
}

pub(super) fn activity(
    site: SiteId,
    opening: &SiteBalanceSheet,
    closing: &SiteBalanceSheet,
    receipts: &MaterialTickReceipts,
) -> Result<SitePeriodActivity> {
    let account = AccountId::Site(site);
    let mut incomes = receipts.income.iter().filter(|r| r.account == account);
    let income = incomes
        .next()
        .ok_or(SiteStatementsError::IncomeReceiptMismatch)?;
    if incomes.next().is_some() {
        return Err(SiteStatementsError::IncomeReceiptMismatch);
    }
    let change_in_equity = equity_change(opening, closing, income, receipts.resolve_tick)?;
    let cash_flow = cash_flow(site, opening, closing, receipts)?;
    Ok(SitePeriodActivity {
        income: income.clone(),
        change_in_equity,
        cash_flow,
    })
}

pub(super) fn equity_change(
    opening: &SiteBalanceSheet,
    closing: &SiteBalanceSheet,
    income: &IncomeReceipt,
    period: u64,
) -> Result<Currency> {
    if income.period != period
        || income.validate().is_err()
        || income.opening_capital != opening.opening_capital
        || income.opening_capital != closing.opening_capital
        || income.opening_contributed_capital != opening.contributed_capital
        || income.closing_contributed_capital != closing.contributed_capital
        || income.opening_retained_earnings != opening.retained_earnings
        || income.closing_retained_earnings != closing.retained_earnings
    {
        return Err(SiteStatementsError::IncomeReceiptMismatch);
    }
    let change_in_equity = sub(closing.total_equity, opening.total_equity)?;
    if change_in_equity
        != sub(
            add(income.net_income, income.contributions_received)?,
            income.distributions_paid,
        )?
    {
        return Err(SiteStatementsError::EquityBridgeMismatch);
    }
    Ok(change_in_equity)
}

pub(super) fn cash_flow(
    site: SiteId,
    opening: &SiteBalanceSheet,
    closing: &SiteBalanceSheet,
    receipts: &MaterialTickReceipts,
) -> Result<CashFlowStatement> {
    let account = AccountId::Site(site);
    let investments = investment_reservations(Some(site), receipts)?;
    let mut totals = SiteCashFlowTotals::empty();
    let mut transfers = Vec::new();
    let cash = MoneyLocation::Cash(account);
    for (receipt_index, transfer) in receipts.money_transfers.iter().enumerate() {
        if transfer.debit.location != cash && transfer.credit.location != cash {
            continue;
        }
        let category = totals.record(site, transfer, &investments)?;
        transfers.push(CashFlowTransfer {
            receipt_index,
            category,
            transfer: transfer.clone(),
        });
    }
    let net_change_in_cash = sub(closing.cash, opening.cash)?;
    totals.reconcile(net_change_in_cash)?;
    Ok(CashFlowStatement {
        operating: totals.operating,
        investing: totals.investing,
        financing: totals.financing,
        reserve_reclassification: totals.reserve_reclassification,
        net_change_in_cash,
        opening_cash: opening.cash,
        closing_cash: closing.cash,
        change_in_purchase_reserves: sub(closing.purchase_reserves, opening.purchase_reserves)?,
        change_in_payroll_reserves: sub(closing.payroll_reserves, opening.payroll_reserves)?,
        transfers,
    })
}

impl SiteCashFlowTotals {
    pub(super) fn empty() -> Self {
        Self {
            operating: zero(),
            investing: zero(),
            financing: zero(),
            reserve_reclassification: zero(),
        }
    }

    /// A cash-to-cash transfer can have a different category for each party.
    pub(super) fn record(
        &mut self,
        site: SiteId,
        transfer: &MoneyTransferReceipt,
        investments: &BTreeMap<(SiteId, OutboundOrderId), Currency>,
    ) -> Result<CashFlowCategory> {
        let cash = MoneyLocation::Cash(AccountId::Site(site));
        if transfer.debit.delta.micro_units() >= 0
            || transfer.credit.delta.micro_units() <= 0
            || add(transfer.debit.delta, transfer.credit.delta)? != zero()
            || transfer.debit.location == transfer.credit.location
        {
            return Err(SiteStatementsError::InvalidTransfer);
        }
        let delta = if transfer.debit.location == cash {
            transfer.debit.delta
        } else if transfer.credit.location == cash {
            transfer.credit.delta
        } else {
            return Err(SiteStatementsError::InvalidTransfer);
        };
        let category = category(transfer, site, delta, investments)?;
        let target = match category {
            CashFlowCategory::Operating => &mut self.operating,
            CashFlowCategory::Investing => &mut self.investing,
            CashFlowCategory::Financing => &mut self.financing,
            CashFlowCategory::ReserveReclassification => &mut self.reserve_reclassification,
        };
        *target = add(*target, delta)?;
        Ok(category)
    }

    pub(super) fn reconcile(&self, expected: Currency) -> Result<()> {
        if sum([
            self.operating,
            self.investing,
            self.financing,
            self.reserve_reclassification,
        ])? != expected
        {
            return Err(SiteStatementsError::CashReconciliationMismatch);
        }
        Ok(())
    }
}

fn category(
    transfer: &MoneyTransferReceipt,
    site: SiteId,
    delta: Currency,
    investments: &BTreeMap<(SiteId, OutboundOrderId), Currency>,
) -> Result<CashFlowCategory> {
    let cash = MoneyLocation::Cash(AccountId::Site(site));
    let result = match transfer.purpose {
        MoneyTransferPurpose::PurchaseReservation(id)
            if transfer.debit.location == cash
                && transfer.credit.location == MoneyLocation::PurchaseReserve(id) =>
        {
            if let Some(amount) = investments.get(&(site, id)) {
                if *amount != transfer.credit.delta {
                    return Err(SiteStatementsError::InvestmentReceiptMismatch);
                }
                CashFlowCategory::Investing
            } else {
                CashFlowCategory::ReserveReclassification
            }
        }
        MoneyTransferPurpose::PurchaseRefund(id)
            if transfer.debit.location == MoneyLocation::PurchaseReserve(id)
                && transfer.credit.location == cash =>
        {
            CashFlowCategory::ReserveReclassification
        }
        MoneyTransferPurpose::ShiftReservation(id)
            if transfer.debit.location == cash
                && transfer.credit.location == MoneyLocation::PayrollReserve(id) =>
        {
            CashFlowCategory::ReserveReclassification
        }
        MoneyTransferPurpose::ShiftCancellation(id)
            if transfer.debit.location == MoneyLocation::PayrollReserve(id)
                && transfer.credit.location == cash =>
        {
            CashFlowCategory::ReserveReclassification
        }
        MoneyTransferPurpose::DeliverySettlement(id)
            if transfer.debit.location == MoneyLocation::PurchaseReserve(id)
                && transfer.credit.location == cash =>
        {
            CashFlowCategory::Operating
        }
        MoneyTransferPurpose::WagePayment(id)
            if transfer.debit.location == MoneyLocation::PayrollReserve(id)
                && transfer.credit.location == cash =>
        {
            CashFlowCategory::Operating
        }
        MoneyTransferPurpose::Cash(purpose)
            if matches!(transfer.debit.location, MoneyLocation::Cash(_))
                && matches!(transfer.credit.location, MoneyLocation::Cash(_)) =>
        {
            match purpose {
                CashTransferPurpose::CapitalContribution if delta.micro_units() < 0 => {
                    CashFlowCategory::Investing
                }
                CashTransferPurpose::CapitalContribution => CashFlowCategory::Financing,
                CashTransferPurpose::OwnershipDistribution if delta.micro_units() < 0 => {
                    CashFlowCategory::Financing
                }
                CashTransferPurpose::OwnershipDistribution
                | CashTransferPurpose::Tax
                | CashTransferPurpose::PublicTransfer
                | CashTransferPurpose::HouseholdTransfer
                | CashTransferPurpose::TransportService
                | CashTransferPurpose::MutualAid => CashFlowCategory::Operating,
            }
        }
        _ => return Err(SiteStatementsError::InvalidTransfer),
    };
    Ok(result)
}

pub(super) fn investment_reservations(
    site: Option<SiteId>,
    receipts: &MaterialTickReceipts,
) -> Result<BTreeMap<(SiteId, OutboundOrderId), Currency>> {
    let mut result = BTreeMap::new();
    for row in receipts
        .investment
        .iter()
        .filter(|r| site.is_none_or(|selected| r.site_id == selected) && r.admitted_units > 0)
    {
        if row.period != receipts.resolve_tick || row.validate().is_err() {
            return Err(SiteStatementsError::InvestmentReceiptMismatch);
        }
        let amount = row
            .unit_price
            .micro_units()
            .checked_mul(i128::from(row.admitted_units))
            .map(Currency::from_micro_units)
            .ok_or(SiteStatementsError::Arithmetic)?;
        if result
            .insert(
                (row.site_id, OutboundOrderId::Delivery(row.order_id)),
                amount,
            )
            .is_some()
        {
            return Err(SiteStatementsError::InvestmentReceiptMismatch);
        }
    }
    Ok(result)
}
