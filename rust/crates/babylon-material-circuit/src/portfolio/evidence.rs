//! Material close facts for the next company's finite-kernel row.
use super::model::{self, Result};
use super::{CompanyPortfolioEvidence, CompanyPortfolioRegister, CompanyProcessEvidence};
use crate::{
    AccountId, CircuitAccounting, CompanyId, MaterialCatalog, MaterialCircuitError,
    MaterialCircuitState, MaterialCircuitTransition, SiteId,
};
use babylon_kernel::currency::Currency;
use std::collections::BTreeMap;
use MaterialCircuitError::CompanyPortfolioEvidence as Invalid;

/// Only direct, exclusively parent-owned workplaces take a portfolio.
pub(super) fn members(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
) -> Result<BTreeMap<SiteId, CompanyId>> {
    let CircuitAccounting::Monetary(m) = &state.accounting else {
        return Err(Invalid);
    };
    let mut roster = BTreeMap::new();
    for row in &m.financial.ownership {
        if let AccountId::Company(parent) = row.beneficiary {
            if catalog
                .company_payouts
                .binary_search_by_key(&parent, |p| p.company)
                .is_err()
                || roster.insert(row.issuer_site_id, parent).is_some()
            {
                return Err(Invalid);
            }
        }
    }
    if m.financial.ownership.iter().any(|r| {
        roster.contains_key(&r.issuer_site_id) && !matches!(r.beneficiary, AccountId::Company(_))
    }) {
        return Err(Invalid);
    }
    Ok(roster)
}
impl CompanyPortfolioRegister {
    /// Observe the completed period's realized operating income and productive evidence.
    /// # Errors
    /// Refuses nonconsecutive histories, missing company membership or inconsistent receipt evidence.
    pub fn observe(
        catalog: &MaterialCatalog,
        opening: &MaterialCircuitState,
        close: &MaterialCircuitTransition,
        previous: Option<&Self>,
    ) -> Result<Self> {
        let policy = catalog.company_portfolios.as_ref().ok_or(Invalid)?;
        let period = opening.period;
        if close.state.period
            != period
                .checked_add(1)
                .ok_or(MaterialCircuitError::Arithmetic)?
            || (period > 1) != previous.is_some()
        {
            return Err(Invalid);
        }
        let roster = members(catalog, &close.state)?;
        let CircuitAccounting::Monetary(m) = &close.state.accounting else {
            return Err(Invalid);
        };
        let statements: BTreeMap<_, _> = close.income.iter().map(|r| (r.account, r)).collect();
        let floors: BTreeMap<_, _> = m
            .financial
            .distributions
            .iter()
            .map(|r| (r.issuer_site_id, r.cash_floor))
            .collect();
        let mut income = BTreeMap::new();
        let mut spendable = BTreeMap::new();
        for (&site, &company) in &roster {
            let row = statements.get(&AccountId::Site(site)).ok_or(Invalid)?;
            if row.period != period {
                return Err(Invalid);
            }
            let current = income.entry(company).or_insert_with(model::zero);
            *current = model::add(*current, row.statement.operating_income()?)?;
            let cash = m.book.cash(AccountId::Site(site))?;
            let floor = floors.get(&site).ok_or(Invalid)?;
            spendable.insert(
                site,
                Currency::from_micro_units(
                    cash.micro_units()
                        .saturating_sub(floor.micro_units())
                        .max(0),
                ),
            );
        }
        let mut processes = observe_processes(catalog, opening, close, &roster, &spendable)?;
        let mut protected = BTreeMap::new();
        for r in &m.financial.contributions {
            if let AccountId::Company(parent) = r.contributor {
                let n = protected.entry(parent).or_insert_with(model::zero);
                *n = model::add(*n, r.amount)?;
            }
        }
        let mut companies = Vec::with_capacity(catalog.company_payouts.len());
        if previous.is_some_and(|v| v.companies.len() != catalog.company_payouts.len()) {
            return Err(Invalid);
        }
        for (i, terms) in catalog.company_payouts.iter().enumerate() {
            let parent = terms.company;
            let mut history = Vec::new();
            if let Some(prior) = previous {
                let r = prior.companies.get(i).ok_or(Invalid)?;
                if r.company != parent || r.period.checked_add(1) != Some(period) {
                    return Err(Invalid);
                }
                history.extend(
                    r.history.iter().copied().skip(
                        r.history
                            .len()
                            .saturating_add(1)
                            .saturating_sub(usize::from(policy.history_periods)),
                    ),
                );
            }
            history.push(income.remove(&parent).ok_or(Invalid)?);
            let funds = m.book.cash(AccountId::Company(parent))?.micro_units();
            let protected = protected
                .get(&parent)
                .copied()
                .unwrap_or_else(model::zero)
                .micro_units();
            let free = Currency::from_micro_units(funds.saturating_sub(protected).max(0));
            companies.push(CompanyPortfolioEvidence::from_close(
                parent,
                period,
                history,
                free,
                processes.remove(&parent).unwrap_or_default(),
                policy,
            )?);
        }
        Ok(Self { companies })
    }
}

fn observe_processes(
    catalog: &MaterialCatalog,
    opening: &MaterialCircuitState,
    close: &MaterialCircuitTransition,
    roster: &BTreeMap<SiteId, CompanyId>,
    spendable: &BTreeMap<SiteId, Currency>,
) -> Result<BTreeMap<CompanyId, Vec<CompanyProcessEvidence>>> {
    let investments: BTreeMap<_, _> = close
        .investment
        .iter()
        .map(|r| ((r.site_id, r.process_id), r))
        .collect();
    let production: BTreeMap<_, _> = close
        .production
        .iter()
        .map(|r| ((r.site_id, r.process_id), r.produced_batches))
        .collect();
    let mut plans: BTreeMap<_, _> = close
        .production_plans
        .iter()
        .map(|r| ((r.site_id, r.process_id), r.unshipped_quantity))
        .collect();
    for r in &close.service_markets {
        let unmet = r
            .admitted_quantity
            .checked_sub(r.performed_quantity)
            .ok_or(Invalid)?;
        if plans.insert((r.site_id, r.process_id), unmet).is_some() {
            return Err(Invalid);
        }
    }
    let capacities: BTreeMap<_, _> = opening
        .capacities
        .iter()
        .filter(|r| r.period == opening.period)
        .map(|r| ((r.site_id, r.process_id), r.available_batches))
        .collect();
    let mut wear = BTreeMap::new();
    for r in &close.equipment_wear {
        let n = wear.entry((r.site_id, r.process_id)).or_insert(0_u64);
        *n = n
            .checked_add(r.used_batches)
            .ok_or(MaterialCircuitError::Arithmetic)?;
    }
    let mut processes = BTreeMap::<_, Vec<_>>::new();
    for output in &catalog.process_outputs {
        let site = output.site_id;
        let Some(company) = roster.get(&site) else {
            continue;
        };
        let key = (site, output.process_id);
        let mut process = CompanyProcessEvidence {
            site,
            process: output.process_id,
            produced_batches: production.get(&key).copied().unwrap_or(0),
            capacity_batches: capacities.get(&key).copied().unwrap_or(0),
            unmet_accepted_units: plans.get(&key).copied().unwrap_or(0),
            used_service_batches: wear.get(&key).copied().unwrap_or(0),
            replacement: 0,
            expansion: 0,
            unit_price: model::zero(),
            free_cash: *spendable.get(&site).ok_or(Invalid)?,
            earnings_budget: model::zero(),
        };
        if let Some(r) = investments.get(&key) {
            let purchased_expansion = r
                .admitted_units
                .saturating_sub(r.replacement_requested_units);
            process.replacement = r
                .replacement_requested_units
                .saturating_sub(r.admitted_units);
            process.expansion = r
                .expansion_requested_units
                .checked_sub(purchased_expansion)
                .ok_or(Invalid)?;
            process.unit_price = r.unit_price;
            let spent = i128::from(purchased_expansion)
                .checked_mul(r.unit_price.micro_units())
                .ok_or(MaterialCircuitError::Arithmetic)?;
            process.earnings_budget = Currency::from_micro_units(
                r.earnings_budget
                    .micro_units()
                    .checked_sub(spent)
                    .ok_or(Invalid)?,
            );
        }
        processes.entry(*company).or_default().push(process);
    }
    Ok(processes)
}
