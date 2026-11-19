//! Group the exact asset and liability principals once for an authenticated endpoint.
use super::projection;
use super::{SiteBalanceSheet, SiteStatementsError};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, CapitalAccount, HistoricalCostSnapshot, MonetaryBookSnapshot, SiteId,
    StockCarryingValue,
};
use std::collections::BTreeMap;

type Balances = BTreeMap<SiteId, SiteBalanceSheet>;

impl SiteBalanceSheet {
    fn from_cash_and_capital(cash: Currency, capital: &CapitalAccount) -> Self {
        let zero = projection::zero();
        Self {
            cash,
            purchase_reserves: zero,
            payroll_reserves: zero,
            wage_receivables: zero,
            inventory: zero,
            freight: zero,
            equity_investments: zero,
            equipment: zero,
            total_assets: zero,
            wage_payables: zero,
            total_liabilities: zero,
            opening_capital: capital.opening_capital,
            contributed_capital: capital.contributed_capital,
            retained_earnings: capital.retained_earnings,
            total_equity: zero,
        }
    }

    fn reconcile(&mut self) -> Result<(), SiteStatementsError> {
        self.total_assets = projection::sum([
            self.cash,
            self.purchase_reserves,
            self.payroll_reserves,
            self.wage_receivables,
            self.inventory,
            self.freight,
            self.equity_investments,
            self.equipment,
        ])?;
        self.total_equity = projection::sum([
            self.opening_capital,
            self.contributed_capital,
            self.retained_earnings,
        ])?;
        self.total_liabilities = self.wage_payables;
        if projection::sub(self.total_assets, self.total_liabilities)? != self.total_equity {
            return Err(SiteStatementsError::BalanceSheetMismatch);
        }
        Ok(())
    }
}

pub(super) fn collect(
    money: &MonetaryBookSnapshot,
    costs: &HistoricalCostSnapshot,
    only: Option<SiteId>,
    stock_basis: impl FnMut(SiteId, &StockCarryingValue) -> Result<(), SiteStatementsError>,
) -> Result<Balances, SiteStatementsError> {
    let selected = |account: AccountId| match account {
        AccountId::Site(site) if only.is_none_or(|id| id == site) => Some(site),
        _ => None,
    };
    if only.is_some() && !money.accounts.iter().any(|row| selected(row.id).is_some()) {
        return Err(SiteStatementsError::SiteAbsent);
    }
    collect_selected(money, costs, selected, stock_basis)
}

/// Read the same legal balance-sheet lines for selected native account principals.
pub(crate) fn collect_selected<K: Copy + Ord>(
    money: &MonetaryBookSnapshot,
    costs: &HistoricalCostSnapshot,
    selected: impl Fn(AccountId) -> Option<K>,
    mut stock_basis: impl FnMut(K, &StockCarryingValue) -> Result<(), SiteStatementsError>,
) -> Result<BTreeMap<K, SiteBalanceSheet>, SiteStatementsError> {
    let mut cash: BTreeMap<_, _> = money
        .accounts
        .iter()
        .filter_map(|row| selected(row.id).map(|key| (key, row.cash)))
        .collect();
    let mut balances = BTreeMap::new();
    for capital in &costs.accounts {
        if let Some(site) = selected(capital.account) {
            let amount = cash
                .remove(&site)
                .ok_or(SiteStatementsError::BalanceSheetMismatch)?;
            balances.insert(
                site,
                SiteBalanceSheet::from_cash_and_capital(amount, capital),
            );
        }
    }
    if !cash.is_empty() {
        return Err(SiteStatementsError::BalanceSheetMismatch);
    }
    for purchase in &money.purchases {
        if let Some(site) = selected(purchase.buyer) {
            let balance = entry(&mut balances, &site)?;
            let amount = purchase
                .reserved_amount()
                .map_err(|_| SiteStatementsError::BalanceSheetMismatch)?;
            balance.purchase_reserves = projection::add(balance.purchase_reserves, amount)?;
        }
    }
    for shift in &money.shifts {
        if let Some(site) = selected(shift.employer) {
            let balance = entry(&mut balances, &site)?;
            let reserve = shift
                .reserved_amount()
                .map_err(|_| SiteStatementsError::BalanceSheetMismatch)?;
            let owed = shift
                .outstanding_wages()
                .map_err(|_| SiteStatementsError::BalanceSheetMismatch)?;
            balance.payroll_reserves = projection::add(balance.payroll_reserves, reserve)?;
            balance.wage_payables = projection::add(balance.wage_payables, owed)?;
        }
        if let Some(site) = selected(shift.payee) {
            let balance = entry(&mut balances, &site)?;
            let owed = shift
                .outstanding_wages()
                .map_err(|_| SiteStatementsError::BalanceSheetMismatch)?;
            balance.wage_receivables = projection::add(balance.wage_receivables, owed)?;
        }
    }
    for row in &costs.stocks {
        if let Some(site) = selected(row.owner) {
            stock_basis(site, row)?;
            let balance = entry(&mut balances, &site)?;
            balance.inventory = projection::add(balance.inventory, row.amount)?;
        }
    }
    for row in &costs.freight {
        if let Some(site) = selected(row.owner) {
            let balance = entry(&mut balances, &site)?;
            balance.freight = projection::add(balance.freight, row.amount)?;
        }
    }
    for row in &costs.equity {
        if let Some(site) = selected(row.owner) {
            let balance = entry(&mut balances, &site)?;
            balance.equity_investments = projection::add(balance.equity_investments, row.amount)?;
        }
    }
    for row in &costs.equipment {
        if let Some(site) = selected(AccountId::Site(row.owner)) {
            let balance = entry(&mut balances, &site)?;
            balance.equipment = projection::add(balance.equipment, row.amount)?;
        }
    }
    for balance in balances.values_mut() {
        balance.reconcile()?;
    }
    Ok(balances)
}

fn entry<'a, K: Ord>(
    balances: &'a mut BTreeMap<K, SiteBalanceSheet>,
    site: &K,
) -> Result<&'a mut SiteBalanceSheet, SiteStatementsError> {
    balances
        .get_mut(site)
        .ok_or(SiteStatementsError::BalanceSheetMismatch)
}
