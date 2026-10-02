use super::{
    add, available, fraction, sub, zero, CapitalContributionReceipt, DistributionReceipt,
    PublicBudgetReceipt, Result, TaxReceipt,
};
use crate::{
    valuation::CostClose, AccountId, CashTransferPurpose, CircuitAccounting, MaterialCircuitState,
    MoneyTransferReceipt,
};
use babylon_kernel::currency::Currency;
use std::collections::BTreeMap;

pub(crate) struct FinancialClose {
    pub public_budgets: Vec<PublicBudgetReceipt>,
    pub taxes: Vec<TaxReceipt>,
    pub distributions: Vec<DistributionReceipt>,
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
                .ok_or(crate::MaterialCircuitError::FinancialInvariant)?;
            let paid = r.amount.min(*balance);
            *balance = sub(*balance, paid)?;
            if paid > zero() {
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
                unfunded: sub(r.amount, paid)?,
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
        let mut budgets = BTreeMap::new();
        for r in &e.financial.public_budgets {
            let cash = e.book.cash(AccountId::Public(r.public_account))?;
            budgets.insert(
                r.public_account,
                r.period_cap.min(available(cash, r.cash_floor)?),
            );
        }
        for r in &e.financial.public_allocations {
            let remaining = budgets
                .get_mut(&r.public_account)
                .ok_or(crate::MaterialCircuitError::FinancialInvariant)?;
            let paid = r.amount_per_period.min(*remaining);
            *remaining = sub(*remaining, paid)?;
            if paid > zero() {
                let sender = AccountId::Public(r.public_account);
                movements.push(e.book.transfer_cash(
                    sender,
                    r.recipient,
                    paid,
                    CashTransferPurpose::PublicTransfer,
                )?);
                costs.public_transfer(sender, r.recipient, paid)?;
            }
            self.public_budgets.push(PublicBudgetReceipt {
                period: state.period,
                public_account: r.public_account,
                recipient: r.recipient,
                treatment: r.treatment,
                priority: r.priority,
                requested: r.amount_per_period,
                paid,
                unfunded: sub(r.amount_per_period, paid)?,
            });
        }
        Ok(())
    }
    pub(crate) fn closing(
        &mut self,
        state: &mut MaterialCircuitState,
        costs: &mut CostClose,
        movements: &mut Vec<MoneyTransferReceipt>,
    ) -> Result<()> {
        self.collect_taxes(state, costs, movements)?;
        self.distribute(state, costs, movements)
    }
    fn collect_taxes(
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
                let assessed = fraction(taxable_amount, u64::from(r.rate_bps), 10_000)?;
                let collected = assessed.min(available(e.book.cash(r.payer)?, r.cash_floor)?);
                Ok(TaxReceipt {
                    period: state.period,
                    payer: r.payer,
                    public_recipient: r.public_recipient,
                    basis: r.basis,
                    rate_bps: r.rate_bps,
                    taxable_amount,
                    assessed,
                    collected,
                    uncollected: sub(assessed, collected)?,
                })
            })
            .collect::<Result<Vec<_>>>()?;
        for r in assessments {
            if r.collected > zero() {
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
    fn distribute(
        &mut self,
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
                let declared = fraction(earnings, u64::from(r.earnings_fraction_bps), 10_000)?
                    .min(r.period_cap)
                    .min(available(e.book.cash(issuer)?, r.cash_floor)?);
                Ok((r.issuer_site_id, earnings, declared))
            })
            .collect::<Result<Vec<_>>>()?;
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
                    .ok_or(crate::MaterialCircuitError::Arithmetic)
            })?;
            let floors = claims
                .iter()
                .try_fold(zero(), |n, r| add(n, fraction(declared, r.shares, total)?))?;
            let mut remainder = sub(declared, floors)?.micro_units();
            for r in claims {
                let extra = i128::from(remainder > 0);
                remainder -= extra;
                let paid = add(
                    fraction(declared, r.shares, total)?,
                    Currency::from_micro_units(extra),
                )?;
                if paid > zero() {
                    movements.push(e.book.transfer_cash(
                        AccountId::Site(issuer),
                        r.beneficiary,
                        paid,
                        CashTransferPurpose::OwnershipDistribution,
                    )?);
                    costs.distribution(issuer, r.beneficiary, paid)?;
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
