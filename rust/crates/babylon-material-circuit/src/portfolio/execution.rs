//! The selected branch bounds real purchases. Only its certified treasury gap becomes contributed capital.
use super::evidence;
use super::model::{self, Result};
use super::{CompanyPortfolioRegister, CompanyPortfolioSelection};
use crate::{
    AccountId, CapitalContributionOrder, CircuitAccounting, ContributionId, MaterialCatalog,
    MaterialCircuitError, MaterialCircuitState, ProcessId, SiteId, MAX_MATERIAL_CIRCUIT_ROWS,
};
use babylon_kernel::content_digest;
use babylon_kernel::currency::Currency;
use std::collections::{BTreeMap, BTreeSet};
use MaterialCircuitError::CompanyPortfolioSelection as Invalid;
#[derive(Default)]
pub(crate) struct CompanyInvestment {
    members: BTreeSet<SiteId>,
    limits: BTreeMap<(SiteId, ProcessId), Limit>,
    orders: Vec<CapitalContributionOrder>,
}
struct Limit {
    replacement: u64,
    expansion: u64,
    expansion_budget: i128,
}
impl CompanyInvestment {
    pub(crate) fn prepare(
        catalog: &MaterialCatalog,
        opening: &MaterialCircuitState,
        prior: Option<&CompanyPortfolioRegister>,
        selections: &[CompanyPortfolioSelection],
    ) -> Result<Self> {
        if catalog.company_portfolios.is_none() {
            return if prior.is_none() && selections.is_empty() {
                Ok(Self::default())
            } else {
                Err(Invalid)
            };
        }
        let roster = evidence::members(catalog, opening)?;
        let mut plan = Self {
            members: roster.keys().copied().collect(),
            ..Self::default()
        };
        let Some(prior) = prior else {
            return if opening.period == 1 && selections.is_empty() {
                Ok(plan)
            } else {
                Err(Invalid)
            };
        };
        let period = opening.period.checked_sub(1).ok_or(Invalid)?;
        prior.validate(catalog, opening, period)?;
        let selected: BTreeMap<_, _> = selections.iter().map(|s| (s.company, s)).collect();
        if selections.len() != prior.companies.len() || selected.len() != selections.len() {
            return Err(Invalid);
        }
        for row in &prior.companies {
            let s = selected.get(&row.company).ok_or(Invalid)?;
            let ordinal = s.portfolio as usize;
            if s.evidence_period != row.period || row.weights[ordinal] == 0 {
                return Err(Invalid);
            }
            let mut gaps = BTreeMap::new();
            for r in &row.plans[ordinal] {
                let ix = row
                    .processes
                    .binary_search_by_key(&(r.site, r.process), |v| (v.site, v.process))
                    .map_err(|_| Invalid)?;
                let expansion_budget = row.processes[ix]
                    .unit_price
                    .micro_units()
                    .checked_mul(i128::from(r.expansion))
                    .ok_or(MaterialCircuitError::Arithmetic)?;
                if roster.get(&r.site) != Some(&row.company)
                    || plan
                        .limits
                        .insert(
                            (r.site, r.process),
                            Limit {
                                replacement: r.replacement,
                                expansion: r.expansion,
                                expansion_budget,
                            },
                        )
                        .is_some()
                {
                    return Err(Invalid);
                }
                if r.funding.micro_units() > 0 {
                    let v = gaps.entry(r.site).or_insert_with(model::zero);
                    *v = model::add(*v, r.funding)?;
                }
            }
            for (site, amount) in gaps {
                let mut bytes = b"babylon.company-portfolio-funding.v1\0".to_vec();
                bytes.extend_from_slice(&period.to_be_bytes());
                bytes.extend_from_slice(&row.company.as_bytes());
                bytes.extend_from_slice(&site.as_bytes());
                plan.orders.push(CapitalContributionOrder {
                    id: ContributionId::from_bytes(content_digest::sha256_of(&bytes)),
                    due_period: opening.period,
                    contributor: AccountId::Company(row.company),
                    issuer_site_id: site,
                    amount,
                });
            }
        }
        Ok(plan)
    }
    pub(crate) fn apply_funding(&mut self, state: &mut MaterialCircuitState) -> Result<()> {
        if self.orders.is_empty() {
            return Ok(());
        }
        let CircuitAccounting::Monetary(m) = &mut state.accounting else {
            return Err(Invalid);
        };
        if m.financial
            .contributions
            .len()
            .checked_add(self.orders.len())
            .is_none_or(|n| n > MAX_MATERIAL_CIRCUIT_ROWS)
        {
            return Err(MaterialCircuitError::RowLimit);
        }
        m.financial.contributions.append(&mut self.orders);
        m.financial.contributions.sort_unstable_by_key(|r| r.id);
        if m.financial
            .contributions
            .windows(2)
            .any(|r| r[0].id == r[1].id)
        {
            return Err(Invalid);
        }
        Ok(())
    }
    pub(crate) fn desired(
        &self,
        site: SiteId,
        process: ProcessId,
        replacement: u64,
        expansion: u64,
        price: Currency,
    ) -> Result<u64> {
        if !self.members.contains(&site) {
            return replacement
                .checked_add(expansion)
                .ok_or(MaterialCircuitError::Arithmetic);
        }
        let Some(l) = self.limits.get(&(site, process)) else {
            return Ok(0);
        };
        let approved = l.replacement.min(replacement);
        if approved < replacement {
            return Ok(approved);
        }
        if price.micro_units() <= 0 {
            return Err(Invalid);
        }
        let expansion_cost_limit = l.expansion_budget / price.micro_units();
        let units = u64::try_from(i128::from(expansion.min(l.expansion)).min(expansion_cost_limit))
            .map_err(|_| MaterialCircuitError::Arithmetic)?;
        approved
            .checked_add(units)
            .ok_or(MaterialCircuitError::Arithmetic)
    }
}
