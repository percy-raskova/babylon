//! Reconcile income and the change in equity before and after elimination.
use super::{CompanyBookPeriod, CompanyIncome, CompanyStatementsError};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::IncomeReceipt;

impl CompanyIncome {
    pub(super) fn record(&mut self, r: &IncomeReceipt) -> Result<(), CompanyStatementsError> {
        let s = &r.statement;
        let other = s
            .wage_income
            .checked_add(s.tax_income)?
            .checked_add(s.public_transfer_income)?
            .checked_add(s.distribution_income)?
            .checked_add(s.gift_income)?;
        let expenses = s.sales.checked_sub(s.cost_of_goods_sold)?.checked_sub(
            s.operating_income()
                .map_err(|_| CompanyStatementsError::ActivityMismatch)?,
        )?;
        self.sales = self.sales.checked_add(s.sales)?;
        self.cost_of_goods_sold = self.cost_of_goods_sold.checked_add(s.cost_of_goods_sold)?;
        self.operating_expenses = self.operating_expenses.checked_add(expenses)?;
        self.taxes = self.taxes.checked_add(s.tax_expense)?;
        self.other_income = self.other_income.checked_add(other)?;
        self.other_expenses = self
            .other_expenses
            .checked_add(s.public_transfer_expense)?
            .checked_add(s.gift_expense)?;
        self.profit = self.profit.checked_add(r.net_income)?;
        self.distributions = self.distributions.checked_add(r.distributions_paid)?;
        self.contributions = self.contributions.checked_add(r.contributions_received)?;
        Ok(())
    }
}
impl CompanyBookPeriod {
    pub(super) fn reconcile(&self) -> Result<(), CompanyStatementsError> {
        let i = &self.income;
        let c = &self.cash_flow;
        if i.sales
            .checked_sub(i.cost_of_goods_sold)?
            .checked_sub(i.operating_expenses)?
            .checked_sub(i.taxes)?
            .checked_add(i.other_income)?
            .checked_sub(i.other_expenses)?
            != i.profit
            || self
                .opening
                .equity
                .checked_add(i.profit)?
                .checked_add(i.contributions)?
                .checked_sub(i.distributions)?
                != self.closing.equity
            || self
                .opening
                .retained_earnings
                .checked_add(i.profit)?
                .checked_sub(i.distributions)?
                != self.closing.retained_earnings
            || self
                .opening
                .cash
                .checked_add(c.operating)?
                .checked_add(c.investing)?
                .checked_add(c.financing)?
                .checked_add(c.reserve_reclassification)?
                != self.closing.cash
        {
            return Err(CompanyStatementsError::ActivityMismatch);
        }
        Ok(())
    }
}
pub(super) fn add(target: &mut Currency, amount: Currency) -> Result<(), CompanyStatementsError> {
    *target = target.checked_add(amount)?;
    Ok(())
}
