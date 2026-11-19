//! Opening-to-close legal books, external cash flows and group historical cost.
use super::carrying::{CompanyCarryingLedger, MarginActivity};
use super::endpoint::{self, Boundary, Endpoint};
use super::{
    cash, income, opening, CompanyBalance, CompanyBookPeriod, CompanyCashFlow, CompanyEliminations,
    CompanyIncome, CompanyPeriod, CompanyStatementsError,
};
use super::{CompanyEntry, CompanyEntryKind};
use crate::economic_catalog::CapturedEconomicCatalog;
use crate::economic_flows::Principals;
use crate::{michigan_economy, site_financial_statements};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, CircuitAccounting, CompanyId, MaterialCircuitState, SiteId,
};
use babylon_tick::material_world::MaterialTickReceipts;
use std::collections::BTreeMap;

/// Sequential reconstruction from a captured founding register and completed authenticated closes.
pub struct CompanyBooks {
    pub(super) members: BTreeMap<SiteId, CompanyId>,
    pub(super) carry: CompanyCarryingLedger,
    pub(super) next: u64,
}
impl CompanyBooks {
    pub(crate) fn for_checkpoint(
        capture: &CapturedEconomicCatalog,
    ) -> Result<Self, CompanyStatementsError> {
        let roster = capture
            .national_companies()
            .ok_or(CompanyStatementsError::MembershipNotCaptured)?;
        let members: BTreeMap<_, _> = roster
            .members
            .iter()
            .map(|m| (m.site, m.company.id()))
            .collect();
        if members.len() != roster.members.len() {
            return Err(CompanyStatementsError::BasisMismatch);
        }
        Ok(Self {
            members,
            carry: CompanyCarryingLedger::default(),
            next: 1,
        })
    }
    /// # Errors
    /// Refuses missing or inconsistent founding legal and ownership books.
    pub fn open(
        capture: &CapturedEconomicCatalog,
        initial: &MaterialCircuitState,
    ) -> Result<Self, CompanyStatementsError> {
        if initial.period != 1 {
            return Err(CompanyStatementsError::PeriodMismatch);
        }
        let groups = opening::project_opening(capture, initial)?;
        let members = groups
            .into_iter()
            .flat_map(|g| g.members.into_iter().map(move |m| (m.site, g.company)))
            .collect();
        Ok(Self {
            members,
            carry: CompanyCarryingLedger::default(),
            next: 1,
        })
    }
    /// # Errors
    /// Refuses a skipped/repeated close or any unbalanced two-sided entry. A failed
    /// projection leaves the prior ledger available for a retry with authentic evidence.
    pub fn close(
        &mut self,
        opening: &MaterialCircuitState,
        closing: &MaterialCircuitState,
        receipts: &MaterialTickReceipts,
    ) -> Result<Vec<CompanyPeriod>, CompanyStatementsError> {
        self.check_period(opening, closing, receipts)?;
        let mut carry = self.carry.clone();
        let before = Boundary::collect(opening, &self.members, &carry)?;
        let mut activity = carry.close(&self.members, &receipts.company_basis)?;
        let after = Boundary::collect(closing, &self.members, &carry)?;
        let mut reports = BTreeMap::new();
        for (&company, end) in &after.groups {
            let start = before
                .groups
                .get(&company)
                .ok_or(CompanyStatementsError::TreasuryMismatch(company))?;
            reports.insert(company, period(company, start, end));
        }
        if before.groups.len() != after.groups.len() {
            return Err(CompanyStatementsError::ActivityMismatch);
        }
        self.period_income(&mut reports, &before, &after, receipts)?;
        self.eliminations(&mut reports, receipts)?;
        let principals = admitted_orders(opening, closing, receipts)?;
        cash::project(&mut reports, &self.members, receipts, &principals)?;
        for (company, r) in &mut reports {
            consolidate(r, activity.remove(company).unwrap_or_default())?;
            r.parent.reconcile()?;
            r.subsidiaries.reconcile()?;
            r.consolidated.reconcile()?;
        }
        self.carry = carry;
        self.next = closing.period;
        Ok(reports.into_values().collect())
    }
    pub(crate) fn replay_earlier(
        &mut self,
        opening: &MaterialCircuitState,
        closing: &MaterialCircuitState,
        receipts: &MaterialTickReceipts,
    ) -> Result<(), CompanyStatementsError> {
        self.check_period(opening, closing, receipts)?;
        admitted_orders(opening, closing, receipts)?;
        let mut carry = self.carry.clone();
        carry.close(&self.members, &receipts.company_basis)?;
        self.carry = carry;
        self.next = closing.period;
        Ok(())
    }
    fn check_period(
        &self,
        b: &MaterialCircuitState,
        a: &MaterialCircuitState,
        r: &MaterialTickReceipts,
    ) -> Result<(), CompanyStatementsError> {
        if self.next != b.period
            || self.next != r.resolve_tick
            || self.next.checked_add(1) != Some(a.period)
        {
            return Err(CompanyStatementsError::PeriodMismatch);
        }
        Ok(())
    }
    fn period_income(
        &self,
        reports: &mut BTreeMap<CompanyId, CompanyPeriod>,
        b: &Boundary,
        a: &Boundary,
        r: &MaterialTickReceipts,
    ) -> Result<(), CompanyStatementsError> {
        let mut found = 0;
        for row in &r.income {
            let id = row.account;
            if let Some(c) = endpoint::group(id, &self.members) {
                let start = b
                    .legal
                    .get(&id)
                    .ok_or(CompanyStatementsError::ActivityMismatch)?;
                let end = a
                    .legal
                    .get(&id)
                    .ok_or(CompanyStatementsError::ActivityMismatch)?;
                site_financial_statements::equity_change(start, end, row, r.resolve_tick)
                    .map_err(CompanyStatementsError::SiteBooks)?;
                let report = reports
                    .get_mut(&c)
                    .ok_or(CompanyStatementsError::TreasuryMismatch(c))?;
                let legal = if matches!(id, AccountId::Company(_)) {
                    &mut report.parent
                } else {
                    &mut report.subsidiaries
                };
                legal.income.record(row)?;
                report.consolidated.income.record(row)?;
                found += 1;
            }
        }
        if found != b.legal.len() || found != a.legal.len() {
            return Err(CompanyStatementsError::ActivityMismatch);
        }
        Ok(())
    }
    fn eliminations(
        &self,
        reports: &mut BTreeMap<CompanyId, CompanyPeriod>,
        r: &MaterialTickReceipts,
    ) -> Result<(), CompanyStatementsError> {
        for (family, ordinal, issuer, owner, amount) in
            r.distributions
                .iter()
                .enumerate()
                .map(|(i, d)| {
                    (
                        26,
                        i,
                        AccountId::Site(d.issuer_site_id),
                        d.beneficiary,
                        d.paid,
                    )
                })
                .chain(
                    r.company_distributions.iter().enumerate().map(|(i, d)| {
                        (38, i, AccountId::Company(d.company), d.beneficiary, d.paid)
                    }),
                )
        {
            if let Some(c) = endpoint::group(issuer, &self.members)
                .filter(|c| endpoint::group(owner, &self.members) == Some(*c))
            {
                let report = reports
                    .get_mut(&c)
                    .ok_or(CompanyStatementsError::TreasuryMismatch(c))?;
                income::add(&mut report.eliminations.distributions, amount)?;
                if amount.micro_units() > 0 {
                    report.entries.push(CompanyEntry::new(
                        family,
                        ordinal,
                        CompanyEntryKind::Dividend,
                        issuer,
                        Some(owner),
                        amount,
                    ));
                }
            }
        }
        for (ordinal, row) in r.contributions.iter().enumerate() {
            if let Some(&c) = self
                .members
                .get(&row.issuer_site_id)
                .filter(|c| endpoint::group(row.contributor, &self.members) == Some(**c))
            {
                let report = reports
                    .get_mut(&c)
                    .ok_or(CompanyStatementsError::TreasuryMismatch(c))?;
                income::add(&mut report.eliminations.contributions, row.paid)?;
                if row.paid.micro_units() > 0 {
                    report.entries.push(CompanyEntry::new(
                        27,
                        ordinal,
                        CompanyEntryKind::Contribution,
                        row.contributor,
                        Some(AccountId::Site(row.issuer_site_id)),
                        row.paid,
                    ));
                }
            }
        }
        Ok(())
    }
}
fn admitted_orders(
    opening: &MaterialCircuitState,
    closing: &MaterialCircuitState,
    receipts: &MaterialTickReceipts,
) -> Result<Principals, CompanyStatementsError> {
    let (CircuitAccounting::Monetary(b), CircuitAccounting::Monetary(a)) =
        (&opening.accounting, &closing.accounting)
    else {
        return Err(CompanyStatementsError::MonetaryBooksUnavailable);
    };
    let principals = Principals::purchases_for_period(&b.book, &a.book, receipts)
        .map_err(|_| CompanyStatementsError::ActivityMismatch)?;
    for row in &receipts.company_basis {
        if let Some(s) = row.sale {
            let terms = principals
                .purchases
                .get(&s.order)
                .ok_or(CompanyStatementsError::BasisMismatch)?;
            let amount = terms
                .price
                .micro_units()
                .checked_mul(i128::from(row.quantity))
                .ok_or(CompanyStatementsError::Arithmetic)?;
            if s.buyer != terms.payer
                || terms.recipient != AccountId::Site(row.source.site())
                || s.proceeds.micro_units() != amount
            {
                return Err(CompanyStatementsError::BasisMismatch);
            }
        }
    }
    Ok(principals)
}
fn books(b: &CompanyBalance, a: &CompanyBalance) -> CompanyBookPeriod {
    CompanyBookPeriod {
        opening: b.clone(),
        closing: a.clone(),
        income: CompanyIncome::default(),
        cash_flow: CompanyCashFlow::default(),
    }
}
fn period(company: CompanyId, b: &Endpoint, a: &Endpoint) -> CompanyPeriod {
    let micros = Currency::from_micro_units;
    CompanyPeriod {
        company: michigan_economy::digest_hex(&company.as_bytes()),
        parent: books(&b.parent, &a.parent),
        subsidiaries: books(&b.subsidiaries, &a.subsidiaries),
        consolidated: books(&b.consolidated, &a.consolidated),
        entries: vec![],
        eliminations: CompanyEliminations {
            opening_investments: micros(b.holdings),
            closing_investments: micros(a.holdings),
            opening_intercompany_claims: micros(b.claims),
            closing_intercompany_claims: micros(a.claims),
            opening_unrealized_margin: micros(b.unrealized),
            closing_unrealized_margin: micros(a.unrealized),
            ..Default::default()
        },
    }
}
fn consolidate(r: &mut CompanyPeriod, m: MarginActivity) -> Result<(), CompanyStatementsError> {
    r.entries.extend(m.entries);
    r.entries.sort_by_key(|e| (e.family, e.ordinal));
    let e = &mut r.eliminations;
    e.sales = m.internal_sales;
    e.seller_cost = m.internal_cogs;
    e.margin_created = m.new_internal_margin;
    e.margin_realized = m.realized_margin;
    if e.opening_unrealized_margin
        .checked_add(e.margin_created)?
        .checked_sub(e.margin_realized)?
        != e.closing_unrealized_margin
        || e.opening_investments.checked_add(e.contributions)? != e.closing_investments
    {
        return Err(CompanyStatementsError::BasisMismatch);
    }
    let i = &mut r.consolidated.income;
    i.sales = i.sales.checked_sub(e.sales)?;
    i.cost_of_goods_sold = i
        .cost_of_goods_sold
        .checked_sub(e.seller_cost)?
        .checked_sub(m.realized_on_sales)?;
    i.operating_expenses = i
        .operating_expenses
        .checked_sub(m.realized_margin.checked_sub(m.realized_on_sales)?)?;
    i.other_income = i.other_income.checked_sub(e.distributions)?;
    i.distributions = i.distributions.checked_sub(e.distributions)?;
    i.contributions = i.contributions.checked_sub(e.contributions)?;
    i.profit = i
        .profit
        .checked_sub(e.distributions)?
        .checked_sub(e.margin_created)?
        .checked_add(e.margin_realized)?;
    Ok(())
}

#[cfg(test)]
#[path = "period_tests.rs"]
mod tests;
