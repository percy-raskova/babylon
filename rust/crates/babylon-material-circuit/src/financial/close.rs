use super::cut;
use super::programs;
use super::CapitalContributionReceipt;
use super::DistributionReceipt;
use super::PublicAllocation;
use super::PublicBudgetReceipt;
use super::PublicProgramReceipt;
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

/// The period's book, costs and movements while one public account pays.
struct FundingRun<'a> {
    period: u64,
    book: &'a mut MonetaryBook,
    costs: &'a mut CostClose,
    movements: &'a mut Vec<MoneyTransferReceipt>,
}
/// A claim on a public account: a standing row or a program's due.
enum Source<'a> {
    Standing(&'a PublicAllocation),
    Program(&'a PublicProgramReceipt),
}
struct Claim<'a> {
    rank: u32,
    recipient: AccountId,
    /// Standing rows by treatment, then programs by key.
    order: (u8, u8, &'a str),
    amount: Currency,
    source: Source<'a>,
}

pub(crate) struct FinancialClose {
    pub public_budgets: Vec<PublicBudgetReceipt>,
    pub programs: Vec<PublicProgramReceipt>,
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
            programs: vec![],
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
        // What the programs owe is read from the state as the period opens, before any payment.
        let dues = match &state.accounting {
            CircuitAccounting::Monetary(e) => programs::program_dues(state, &e.financial.programs)?,
            CircuitAccounting::PhysicalControl => return Ok(()),
        };
        let period = state.period;
        let CircuitAccounting::Monetary(e) = &mut state.accounting else {
            return Ok(());
        };
        // Allocations are sorted by account, so each account's rows are contiguous and keep that order.
        let allocations = &e.financial.public_allocations;
        for budget in &e.financial.public_budgets {
            let account = budget.public_account;
            let cash = e.book.cash(AccountId::Public(account))?;
            let free = super::available(cash, budget.cash_floor)?;
            let start = allocations.partition_point(|r| r.public_account < account);
            let end = allocations.partition_point(|r| r.public_account <= account);
            let rows = &allocations[start..end];
            let mut run = FundingRun {
                period,
                book: &mut e.book,
                costs: &mut *costs,
                movements: &mut *movements,
            };
            match budget.rule {
                PublicSpendingRule::CappedInOrder => {
                    self.fund_capped(&mut run, rows, budget.period_cap.min(free))?;
                }
                PublicSpendingRule::CashInProportion => {
                    let owed: Vec<_> = dues
                        .iter()
                        .filter(|(r, _)| r.public_account == account)
                        .cloned()
                        .collect();
                    self.fund_in_proportion(&mut run, rows, &owed, free)?;
                }
            }
        }
        self.programs
            .sort_by(|a, b| (&a.program, a.recipient).cmp(&(&b.program, b.recipient)));
        Ok(())
    }
    /// Today's loop: the rows in their order, each paid what is left of the cap and the free cash.
    fn fund_capped(
        &mut self,
        run: &mut FundingRun<'_>,
        rows: &[PublicAllocation],
        mut remaining: Currency,
    ) -> Result<()> {
        for r in rows {
            let amount = r.amount_per_period.min(remaining);
            remaining = super::sub(remaining, amount)?;
            self.pay_public(run, r, amount)?;
        }
        Ok(())
    }
    /// Standing rows and programs of one account, ranked together and cut in proportion.
    fn fund_in_proportion(
        &mut self,
        run: &mut FundingRun<'_>,
        rows: &[PublicAllocation],
        owed: &[(PublicProgramReceipt, Currency)],
        free: Currency,
    ) -> Result<()> {
        let mut claims: Vec<Claim<'_>> = rows
            .iter()
            .map(|r| Claim {
                rank: r.priority,
                recipient: r.recipient,
                order: (0, r.treatment as u8, ""),
                amount: r.amount_per_period,
                source: Source::Standing(r),
            })
            .collect();
        claims.extend(owed.iter().map(|(receipt, amount)| Claim {
            rank: receipt.rank,
            recipient: AccountId::Household(receipt.recipient),
            order: (1, 0, receipt.program.as_str()),
            amount: *amount,
            source: Source::Program(receipt),
        }));
        claims.sort_by(|a, b| (a.rank, a.recipient, a.order).cmp(&(b.rank, b.recipient, b.order)));
        let ranked: Vec<_> = claims.iter().map(|c| (c.rank, c.amount)).collect();
        let paid = cut::cut_in_proportion(free, &ranked)?;
        for (claim, amount) in claims.iter().zip(paid) {
            match claim.source {
                Source::Standing(r) => self.pay_public(run, r, amount)?,
                Source::Program(receipt) => self.pay_program(run, receipt, amount)?,
            }
        }
        Ok(())
    }
    fn pay_program(
        &mut self,
        run: &mut FundingRun<'_>,
        due: &PublicProgramReceipt,
        paid: Currency,
    ) -> Result<()> {
        if paid > super::zero() {
            let sender = AccountId::Public(due.public_account);
            // A program's recipient is a household principal, so the account is always a household's.
            let recipient = AccountId::Household(due.recipient);
            run.movements.push(run.book.transfer_cash(
                sender,
                recipient,
                paid,
                CashTransferPurpose::PublicTransfer,
            )?);
            run.costs.public_transfer(sender, recipient, paid)?;
        }
        let receipt = PublicProgramReceipt {
            paid,
            unfunded: super::sub(due.due, paid)?,
            ..due.clone()
        };
        receipt.validate()?;
        self.programs.push(receipt);
        Ok(())
    }
    fn pay_public(
        &mut self,
        run: &mut FundingRun<'_>,
        r: &PublicAllocation,
        paid: Currency,
    ) -> Result<()> {
        if paid > super::zero() {
            let sender = AccountId::Public(r.public_account);
            run.movements.push(run.book.transfer_cash(
                sender,
                r.recipient,
                paid,
                CashTransferPurpose::PublicTransfer,
            )?);
            run.costs.public_transfer(sender, r.recipient, paid)?;
        }
        self.public_budgets.push(PublicBudgetReceipt {
            period: run.period,
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
        // All bases and free cash are observed before any current tax credits. A payer's rows
        // collect in key order from one running balance, so nothing is overdrawn.
        let mut balances = BTreeMap::new();
        let mut assessments = Vec::with_capacity(e.financial.taxes.len());
        for r in &e.financial.taxes {
            let taxable_amount = costs.tax_base(r.payer, r.basis)?;
            let assessed = super::fraction(taxable_amount, u64::from(r.rate_bps), 10_000)?;
            let balance = match balances.get(&r.payer) {
                Some(balance) => *balance,
                None => e.book.cash(r.payer)?,
            };
            let collected = assessed.min(super::available(balance, r.cash_floor)?);
            balances.insert(r.payer, super::sub(balance, collected)?);
            assessments.push(TaxReceipt {
                period: state.period,
                payer: r.payer,
                public_recipient: r.public_recipient,
                basis: r.basis,
                rate_bps: r.rate_bps,
                taxable_amount,
                assessed,
                collected,
                uncollected: super::sub(assessed, collected)?,
            });
        }
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
