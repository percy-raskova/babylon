use super::cut;
use super::CapitalContributionReceipt;
use super::DistributionReceipt;
use super::PublicAllocation;
use super::PublicBudgetReceipt;
use super::PublicSpendingRule;
use super::Result;
use super::TaxReceipt;
use crate::valuation::CostClose;
use crate::{
    AccountId, CashTransferPurpose, CircuitAccounting, MaterialCircuitState, MonetaryBook,
    MoneyTransferReceipt,
};

use crate::{CompanyDistributionReceipt, MaterialCatalog, MaterialCircuitError};
use babylon_kernel::currency::Currency;
use std::collections::BTreeMap;

pub(crate) struct FinancialClose {
    pub public_budgets: Vec<PublicBudgetReceipt>,
    pub taxes: Vec<TaxReceipt>,
    pub distributions: Vec<DistributionReceipt>,
    pub company_distributions: Vec<CompanyDistributionReceipt>,
    pub contributions: Vec<CapitalContributionReceipt>,
}
impl FinancialClose {
    pub(crate) fn opening(
        state: &mut MaterialCircuitState,
        costs: &mut CostClose,
        movements: &mut Vec<MoneyTransferReceipt>,
    ) -> Result<Self> {
        let mut result = Self {
            public_budgets: vec![],
            taxes: vec![],
            distributions: vec![],
            company_distributions: vec![],
            contributions: vec![],
        };
        result.contribute(state, costs, movements)?;
        result.public_funding(state, costs, movements)?;
        Ok(result)
    }
    fn contribute(
        &mut self,
        state: &mut MaterialCircuitState,
        costs: &mut CostClose,
        movements: &mut Vec<MoneyTransferReceipt>,
    ) -> Result<()> {
        let CircuitAccounting::Monetary(e) = &mut state.accounting else {
            return Ok(());
        };
        // A receipt funded in this pass cannot finance another due contribution.
        let mut remaining: BTreeMap<_, _> = e
            .book
            .snapshot()
            .accounts
            .into_iter()
            .map(|r| (r.id, r.cash))
            .collect();
        let mut future = vec![];
        for r in std::mem::take(&mut e.financial.contributions) {
            if r.due_period != state.period {
                future.push(r);
                continue;
            }
            let balance = remaining
                .get_mut(&r.contributor)
                .ok_or(MaterialCircuitError::FinancialInvariant)?;
            let paid = r.amount.min(*balance);
            *balance = super::sub(*balance, paid)?;
            if paid > super::zero() {
                movements.push(e.book.transfer_cash(
                    r.contributor,
                    AccountId::Site(r.issuer_site_id),
                    paid,
                    CashTransferPurpose::CapitalContribution,
                )?);
                costs.contribution(r.contributor, r.issuer_site_id, paid)?;
            }
            self.contributions.push(CapitalContributionReceipt {
                period: state.period,
                id: r.id,
                contributor: r.contributor,
                issuer_site_id: r.issuer_site_id,
                requested: r.amount,
                paid,
                unfunded: super::sub(r.amount, paid)?,
            });
        }
        e.financial.contributions = future;
        Ok(())
    }
    fn public_funding(
        &mut self,
        state: &mut MaterialCircuitState,
        costs: &mut CostClose,
        movements: &mut Vec<MoneyTransferReceipt>,
    ) -> Result<()> {
        let CircuitAccounting::Monetary(e) = &mut state.accounting else {
            return Ok(());
        };
        let mut capped = BTreeMap::new();
        let mut proportional = BTreeMap::new();
        for r in &e.financial.public_budgets {
            let cash = e.book.cash(AccountId::Public(r.public_account))?;
            let free = super::available(cash, r.cash_floor)?;
            match r.rule {
                PublicSpendingRule::CappedInOrder => {
                    capped.insert(r.public_account, r.period_cap.min(free));
                }
                PublicSpendingRule::CashInProportion => {
                    proportional.insert(r.public_account, free);
                }
            }
        }
        // Allocations are sorted by account, so each account's rows are contiguous and keep that order.
        let allocations = &e.financial.public_allocations;
        let mut start = 0;
        while start < allocations.len() {
            let account = allocations[start].public_account;
            let len = allocations[start..]
                .iter()
                .take_while(|r| r.public_account == account)
                .count();
            let rows = &allocations[start..start + len];
            start += len;
            let paid = if let Some(free) = proportional.get(&account) {
                let claims: Vec<_> = rows
                    .iter()
                    .map(|r| (r.priority, r.amount_per_period))
                    .collect();
                cut::cut_in_proportion(*free, &claims)?
            } else {
                let remaining = capped
                    .get_mut(&account)
                    .ok_or(MaterialCircuitError::FinancialInvariant)?;
                let mut paid = Vec::with_capacity(rows.len());
                for r in rows {
                    let amount = r.amount_per_period.min(*remaining);
                    *remaining = super::sub(*remaining, amount)?;
                    paid.push(amount);
                }
                paid
            };
            for (r, amount) in rows.iter().zip(paid) {
                self.pay_public(state.period, &mut e.book, costs, movements, r, amount)?;
            }
        }
        Ok(())
    }
    fn pay_public(
        &mut self,
        period: u64,
        book: &mut MonetaryBook,
        costs: &mut CostClose,
        movements: &mut Vec<MoneyTransferReceipt>,
        r: &PublicAllocation,
        paid: Currency,
    ) -> Result<()> {
        if paid > super::zero() {
            let sender = AccountId::Public(r.public_account);
            movements.push(book.transfer_cash(
                sender,
                r.recipient,
                paid,
                CashTransferPurpose::PublicTransfer,
            )?);
            costs.public_transfer(sender, r.recipient, paid)?;
        }
        self.public_budgets.push(PublicBudgetReceipt {
            period,
            public_account: r.public_account,
            recipient: r.recipient,
            treatment: r.treatment,
            priority: r.priority,
            requested: r.amount_per_period,
            paid,
            unfunded: super::sub(r.amount_per_period, paid)?,
        });
        Ok(())
    }
    pub(crate) fn collect_taxes(
        &mut self,
        state: &mut MaterialCircuitState,
        costs: &mut CostClose,
        movements: &mut Vec<MoneyTransferReceipt>,
    ) -> Result<()> {
        let CircuitAccounting::Monetary(e) = &mut state.accounting else {
            return Ok(());
        };
        // All bases and free cash are observed before any current tax credits.
        let assessments = e
            .financial
            .taxes
            .iter()
            .map(|r| {
                let taxable_amount = costs.tax_base(r.payer, r.basis)?;
                let assessed = super::fraction(taxable_amount, u64::from(r.rate_bps), 10_000)?;
                let collected =
                    assessed.min(super::available(e.book.cash(r.payer)?, r.cash_floor)?);
                Ok(TaxReceipt {
                    period: state.period,
                    payer: r.payer,
                    public_recipient: r.public_recipient,
                    basis: r.basis,
                    rate_bps: r.rate_bps,
                    taxable_amount,
                    assessed,
                    collected,
                    uncollected: super::sub(assessed, collected)?,
                })
            })
            .collect::<Result<Vec<_>>>()?;
        for r in assessments {
            if r.collected > super::zero() {
                let recipient = AccountId::Public(r.public_recipient);
                movements.push(e.book.transfer_cash(
                    r.payer,
                    recipient,
                    r.collected,
                    CashTransferPurpose::Tax,
                )?);
                costs.tax(r.payer, recipient, r.collected)?;
            }
            self.taxes.push(r);
        }
        Ok(())
    }
    pub(crate) fn distribute(
        &mut self,
        catalog: &MaterialCatalog,
        state: &mut MaterialCircuitState,
        costs: &mut CostClose,
        movements: &mut Vec<MoneyTransferReceipt>,
    ) -> Result<()> {
        let CircuitAccounting::Monetary(e) = &mut state.accounting else {
            return Ok(());
        };
        // Capture every issuer before payouts. Cross-ownership never feeds back
        // into this period's eligible income or funding for another issuer.
        let budgets = e
            .financial
            .distributions
            .iter()
            .map(|r| {
                let issuer = AccountId::Site(r.issuer_site_id);
                let earnings = costs.eligible_earnings(issuer)?;
                let declared =
                    super::fraction(earnings, u64::from(r.earnings_fraction_bps), 10_000)?
                        .min(r.period_cap)
                        .min(super::available(e.book.cash(issuer)?, r.cash_floor)?);
                Ok((r.issuer_site_id, earnings, declared))
            })
            .collect::<Result<Vec<_>>>()?;
        self.company_distributions =
            super::company::pay(catalog, state.period, e, costs, movements)?;
        for (issuer, earnings, declared) in budgets {
            let start = e
                .financial
                .ownership
                .partition_point(|r| r.issuer_site_id < issuer);
            let end = e
                .financial
                .ownership
                .partition_point(|r| r.issuer_site_id <= issuer);
            let claims = &e.financial.ownership[start..end];
            let total = claims.iter().try_fold(0_u64, |n, r| {
                n.checked_add(r.shares)
                    .ok_or(MaterialCircuitError::Arithmetic)
            })?;
            let floors = claims.iter().try_fold(super::zero(), |n, r| {
                super::add(n, super::fraction(declared, r.shares, total)?)
            })?;
            let mut remainder = super::sub(declared, floors)?.micro_units();
            for r in claims {
                let extra = i128::from(remainder > 0);
                remainder -= extra;
                let paid = super::add(
                    super::fraction(declared, r.shares, total)?,
                    Currency::from_micro_units(extra),
                )?;
                if paid > super::zero() {
                    movements.push(e.book.transfer_cash(
                        AccountId::Site(issuer),
                        r.beneficiary,
                        paid,
                        CashTransferPurpose::OwnershipDistribution,
                    )?);
                    costs.distribution(AccountId::Site(issuer), r.beneficiary, paid)?;
                }
                self.distributions.push(DistributionReceipt {
                    period: state.period,
                    issuer_site_id: issuer,
                    beneficiary: r.beneficiary,
                    shares: r.shares,
                    total_shares: total,
                    eligible_earnings: earnings,
                    declared_total: declared,
                    paid,
                });
            }
        }
        Ok(())
    }
}
