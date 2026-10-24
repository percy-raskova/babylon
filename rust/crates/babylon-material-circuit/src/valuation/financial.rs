//! Financial flows bridge exact cash, equity carrying amounts and retained income.
use super::CostClose;
use super::Result;
use crate::{AccountId, MaterialCircuitError, SiteId, TaxBasis};
use babylon_kernel::currency::Currency;
impl CostClose {
    pub(crate) fn tax_base(&self, account: AccountId, basis: TaxBasis) -> Result<Currency> {
        let Some(a) = &self.active else {
            return Ok(super::zero());
        };
        let statement = a
            .income
            .get(&account)
            .ok_or(MaterialCircuitError::ValuationInvariant)?;
        Ok(match basis {
            TaxBasis::WageIncome => statement.wage_income,
            TaxBasis::PositiveOperatingIncome => statement.operating_income()?.max(super::zero()),
        })
    }
    pub(crate) fn eligible_earnings(&self, account: AccountId) -> Result<Currency> {
        let Some(a) = &self.active else {
            return Ok(super::zero());
        };
        let row = a
            .book
            .accounts
            .get(&account)
            .ok_or(MaterialCircuitError::ValuationInvariant)?;
        let statement = a
            .income
            .get(&account)
            .ok_or(MaterialCircuitError::ValuationInvariant)?;
        Ok(super::add(row.retained_earnings, statement.net_income()?)?.max(super::zero()))
    }
    pub(crate) fn contribution(
        &mut self,
        owner: AccountId,
        issuer: SiteId,
        amount: Currency,
    ) -> Result<()> {
        let Some(a) = &mut self.active else {
            return Ok(());
        };
        let carrying = a
            .book
            .equity
            .get_mut(&(owner, issuer))
            .ok_or(MaterialCircuitError::ValuationInvariant)?;
        *carrying = super::add(*carrying, amount)?;
        let total = a
            .contributions
            .entry(AccountId::Site(issuer))
            .or_insert_with(super::zero);
        *total = super::add(*total, amount)?;
        Ok(())
    }
    pub(crate) fn distribution(
        &mut self,
        issuer: SiteId,
        beneficiary: AccountId,
        amount: Currency,
    ) -> Result<()> {
        let Some(a) = &mut self.active else {
            return Ok(());
        };
        let total = a
            .distributions
            .entry(AccountId::Site(issuer))
            .or_insert_with(super::zero);
        *total = super::add(*total, amount)?;
        let statement = a.statement(beneficiary)?;
        statement.distribution_income = super::add(statement.distribution_income, amount)?;
        Ok(())
    }
    pub(crate) fn tax(
        &mut self,
        payer: AccountId,
        recipient: AccountId,
        amount: Currency,
    ) -> Result<()> {
        let Some(a) = &mut self.active else {
            return Ok(());
        };
        let statement = a.statement(payer)?;
        statement.tax_expense = super::add(statement.tax_expense, amount)?;
        let statement = a.statement(recipient)?;
        statement.tax_income = super::add(statement.tax_income, amount)?;
        Ok(())
    }
    pub(crate) fn public_transfer(
        &mut self,
        payer: AccountId,
        recipient: AccountId,
        amount: Currency,
    ) -> Result<()> {
        let Some(a) = &mut self.active else {
            return Ok(());
        };
        let statement = a.statement(payer)?;
        statement.public_transfer_expense = super::add(statement.public_transfer_expense, amount)?;
        let statement = a.statement(recipient)?;
        statement.public_transfer_income = super::add(statement.public_transfer_income, amount)?;
        Ok(())
    }
}
