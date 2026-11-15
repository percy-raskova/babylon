//! Selected-account joins over admitted books and complete committed receipts.
use super::{
    CashFlowCategory, CashFlowStatement, CashFlowTransfer, PlanningControl, SiteBalanceSheet,
    SiteBookStatements, SitePeriodActivity, SiteStatementsError,
};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, CashTransferPurpose, CircuitAccounting, HistoricalCostSnapshot,
    MonetaryBookSnapshot, MoneyLocation, MoneyTransferPurpose, MoneyTransferReceipt,
    OutboundOrderId, SiteId,
};
use babylon_tick::material_world::MaterialTickReceipts;

use std::collections::BTreeMap;

use std::result::Result as StdResult;

type Result<T> = StdResult<T, SiteStatementsError>;
fn zero() -> Currency {
    Currency::from_micro_units(0)
}
fn add(a: Currency, b: Currency) -> Result<Currency> {
    a.checked_add(b)
        .map_err(|_| SiteStatementsError::Arithmetic)
}
fn sub(a: Currency, b: Currency) -> Result<Currency> {
    a.checked_sub(b)
        .map_err(|_| SiteStatementsError::Arithmetic)
}
fn sum(values: impl IntoIterator<Item = Currency>) -> Result<Currency> {
    values.into_iter().try_fold(zero(), add)
}

fn purchase_reserves(account: AccountId, money: &MonetaryBookSnapshot) -> Result<Currency> {
    let mut total = zero();
    for row in &money.purchases {
        if row.buyer == account {
            total = add(
                total,
                row.reserved_amount()
                    .map_err(|_| SiteStatementsError::BalanceSheetMismatch)?,
            )?;
        }
    }
    Ok(total)
}

pub(super) fn balance(
    site: SiteId,
    money: &MonetaryBookSnapshot,
    costs: &HistoricalCostSnapshot,
) -> Result<SiteBalanceSheet> {
    let account = AccountId::Site(site);
    let cash = money
        .accounts
        .iter()
        .find(|r| r.id == account)
        .ok_or(SiteStatementsError::SiteAbsent)?
        .cash;
    let capital = costs
        .accounts
        .iter()
        .find(|r| r.account == account)
        .ok_or(SiteStatementsError::BalanceSheetMismatch)?;
    let purchase_reserves = purchase_reserves(account, money)?;
    let mut payroll_reserves = zero();
    let mut wage_receivables = zero();
    let mut wage_payables = zero();
    for row in &money.shifts {
        if row.employer == account {
            payroll_reserves = add(
                payroll_reserves,
                row.reserved_amount()
                    .map_err(|_| SiteStatementsError::BalanceSheetMismatch)?,
            )?;
            wage_payables = add(
                wage_payables,
                row.outstanding_wages()
                    .map_err(|_| SiteStatementsError::BalanceSheetMismatch)?,
            )?;
        }
        if row.payee == account {
            wage_receivables = add(
                wage_receivables,
                row.outstanding_wages()
                    .map_err(|_| SiteStatementsError::BalanceSheetMismatch)?,
            )?;
        }
    }
    let inventory = sum(costs
        .stocks
        .iter()
        .filter(|r| r.owner == account)
        .map(|r| r.amount))?;
    let freight = sum(costs
        .freight
        .iter()
        .filter(|r| r.owner == account)
        .map(|r| r.amount))?;
    let equity_investments = sum(costs
        .equity
        .iter()
        .filter(|r| r.owner == account)
        .map(|r| r.amount))?;
    let equipment = sum(costs
        .equipment
        .iter()
        .filter(|r| r.owner == site)
        .map(|r| r.amount))?;
    let total_assets = sum([
        cash,
        purchase_reserves,
        payroll_reserves,
        wage_receivables,
        inventory,
        freight,
        equity_investments,
        equipment,
    ])?;
    let total_equity = sum([
        capital.opening_capital,
        capital.contributed_capital,
        capital.retained_earnings,
    ])?;
    if sub(total_assets, wage_payables)? != total_equity {
        return Err(SiteStatementsError::BalanceSheetMismatch);
    }
    Ok(SiteBalanceSheet {
        cash,
        purchase_reserves,
        payroll_reserves,
        wage_receivables,
        inventory,
        freight,
        equity_investments,
        equipment,
        total_assets,
        wage_payables,
        total_liabilities: wage_payables,
        opening_capital: capital.opening_capital,
        contributed_capital: capital.contributed_capital,
        retained_earnings: capital.retained_earnings,
        total_equity,
    })
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
    if incomes.next().is_some()
        || income.period != receipts.resolve_tick
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
    let cash_flow = cash_flow(site, opening, closing, receipts)?;
    Ok(SitePeriodActivity {
        income: income.clone(),
        change_in_equity,
        cash_flow,
    })
}

pub(super) fn cash_flow(
    site: SiteId,
    opening: &SiteBalanceSheet,
    closing: &SiteBalanceSheet,
    receipts: &MaterialTickReceipts,
) -> Result<CashFlowStatement> {
    let account = AccountId::Site(site);
    let investments = investment_reservations(site, receipts)?;
    let mut result = CashFlowStatement {
        operating: zero(),
        investing: zero(),
        financing: zero(),
        reserve_reclassification: zero(),
        net_change_in_cash: sub(closing.cash, opening.cash)?,
        opening_cash: opening.cash,
        closing_cash: closing.cash,
        change_in_purchase_reserves: sub(closing.purchase_reserves, opening.purchase_reserves)?,
        change_in_payroll_reserves: sub(closing.payroll_reserves, opening.payroll_reserves)?,
        transfers: Vec::new(),
    };
    for (receipt_index, transfer) in receipts.money_transfers.iter().enumerate() {
        let cash = MoneyLocation::Cash(account);
        if transfer.debit.location != cash && transfer.credit.location != cash {
            continue;
        }
        if transfer.debit.delta.micro_units() >= 0
            || transfer.credit.delta.micro_units() <= 0
            || add(transfer.debit.delta, transfer.credit.delta)? != zero()
            || transfer.debit.location == transfer.credit.location
        {
            return Err(SiteStatementsError::InvalidTransfer);
        }
        let delta = if transfer.debit.location == cash {
            transfer.debit.delta
        } else {
            transfer.credit.delta
        };
        let category = category(transfer, cash, delta, &investments)?;
        let target = match category {
            CashFlowCategory::Operating => &mut result.operating,
            CashFlowCategory::Investing => &mut result.investing,
            CashFlowCategory::Financing => &mut result.financing,
            CashFlowCategory::ReserveReclassification => &mut result.reserve_reclassification,
        };
        *target = add(*target, delta)?;
        result.transfers.push(CashFlowTransfer {
            receipt_index,
            category,
            transfer: transfer.clone(),
        });
    }
    if sum([
        result.operating,
        result.investing,
        result.financing,
        result.reserve_reclassification,
    ])? != result.net_change_in_cash
    {
        return Err(SiteStatementsError::CashReconciliationMismatch);
    }
    Ok(result)
}

fn category(
    transfer: &MoneyTransferReceipt,
    cash: MoneyLocation,
    delta: Currency,
    investments: &BTreeMap<OutboundOrderId, Currency>,
) -> Result<CashFlowCategory> {
    let result = match transfer.purpose {
        MoneyTransferPurpose::PurchaseReservation(id)
            if transfer.debit.location == cash
                && transfer.credit.location == MoneyLocation::PurchaseReserve(id) =>
        {
            if let Some(amount) = investments.get(&id) {
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

fn investment_reservations(
    site: SiteId,
    receipts: &MaterialTickReceipts,
) -> Result<BTreeMap<OutboundOrderId, Currency>> {
    let mut result = BTreeMap::new();
    for row in receipts
        .investment
        .iter()
        .filter(|r| r.site_id == site && r.admitted_units > 0)
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
            .insert(OutboundOrderId::Delivery(row.order_id), amount)
            .is_some()
        {
            return Err(SiteStatementsError::InvestmentReceiptMismatch);
        }
    }
    Ok(result)
}
