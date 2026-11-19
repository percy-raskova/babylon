//! Canonical evidence stores physical and monetary inputs once. Captured policy reconstructs every branch.
use super::model::{self, Result};
use super::{CompanyPortfolioEvidence, CompanyPortfolioRegister, CompanyProcessEvidence};
use crate::{
    AccountId, CircuitAccounting, CompanyId, MaterialCatalog, MaterialCircuitError,
    MaterialCircuitState, ProcessId, SiteId, MAX_MATERIAL_CIRCUIT_ROWS,
};
use babylon_kernel::currency::Currency;
use std::collections::{BTreeMap, BTreeSet};
use MaterialCircuitError::CompanyPortfolioEvidence as Invalid;
/// Captured version of canonical, length-bounded portfolio observations.
pub const COMPANY_PORTFOLIO_DOMAIN: &[u8] = b"babylon.company-portfolio-evidence.v1\0";
impl CompanyPortfolioRegister {
    pub(super) fn validate(
        &self,
        catalog: &MaterialCatalog,
        state: &MaterialCircuitState,
        period: u64,
    ) -> Result<()> {
        let policy = catalog.company_portfolios.as_ref().ok_or(Invalid)?;
        if period == 0
            || period.checked_add(1) != Some(state.period)
            || self.companies.len() != catalog.company_payouts.len()
        {
            return Err(Invalid);
        }
        let roster = super::evidence::members(catalog, state)?;
        let CircuitAccounting::Monetary(m) = &state.accounting else {
            return Err(Invalid);
        };
        let floors: BTreeMap<_, _> = m
            .financial
            .distributions
            .iter()
            .map(|r| (r.issuer_site_id, r.cash_floor))
            .collect();
        let mut expected: BTreeSet<_> = catalog
            .process_outputs
            .iter()
            .filter_map(|r| {
                roster
                    .get(&r.site_id)
                    .map(|owner| (*owner, r.site_id, r.process_id))
            })
            .collect();
        let mut retained = BTreeMap::new();
        for v in &m.financial.contributions {
            if let AccountId::Company(c) = v.contributor {
                let amount = retained.entry(c).or_insert_with(model::zero);
                *amount = model::add(*amount, v.amount)?;
            }
        }
        for (row, parent) in self.companies.iter().zip(&catalog.company_payouts) {
            let cash = m
                .book
                .cash(AccountId::Company(parent.company))?
                .micro_units();
            let protected = retained
                .get(&parent.company)
                .copied()
                .unwrap_or_else(model::zero)
                .micro_units();
            if row.company != parent.company
                || row.period != period
                || row.treasury_available.micro_units() != cash.saturating_sub(protected).max(0)
            {
                return Err(Invalid);
            }
            for r in &row.processes {
                let free = m
                    .book
                    .cash(AccountId::Site(r.site))?
                    .micro_units()
                    .saturating_sub(floors.get(&r.site).ok_or(Invalid)?.micro_units())
                    .max(0);
                if !expected.remove(&(row.company, r.site, r.process))
                    || r.free_cash.micro_units() != free
                {
                    return Err(Invalid);
                }
            }
            let rebuilt = row.recompute(policy)?;
            if rebuilt != *row {
                return Err(Invalid);
            }
        }
        if !expected.is_empty() {
            return Err(Invalid);
        }
        Ok(())
    }
    /// Encode the source measurements needed for every alternative and its exact limits.
    /// # Errors
    /// Refuses oversized or inconsistent registers.
    pub fn canonical_bytes(
        &self,
        catalog: &MaterialCatalog,
        state: &MaterialCircuitState,
        period: u64,
    ) -> Result<Vec<u8>> {
        self.validate(catalog, state, period)?;
        let mut out = COMPANY_PORTFOLIO_DOMAIN.to_vec();
        out.extend_from_slice(&period.to_be_bytes());
        count(&mut out, self.companies.len())?;
        for row in &self.companies {
            out.extend_from_slice(&row.company.as_bytes());
            out.push(u8::try_from(row.history.len()).map_err(|_| Invalid)?);
            for v in &row.history {
                out.extend_from_slice(&v.micro_units().to_be_bytes());
            }
            out.extend_from_slice(&row.treasury_available.micro_units().to_be_bytes());
            count(&mut out, row.processes.len())?;
            for r in &row.processes {
                out.extend_from_slice(&r.site.as_bytes());
                out.extend_from_slice(&r.process.as_bytes());
                for v in [
                    r.produced_batches,
                    r.capacity_batches,
                    r.unmet_accepted_units,
                    r.used_service_batches,
                    r.replacement,
                    r.expansion,
                ] {
                    out.extend_from_slice(&v.to_be_bytes());
                }
                for v in [r.unit_price, r.free_cash, r.earnings_budget] {
                    out.extend_from_slice(&v.micro_units().to_be_bytes());
                }
            }
        }
        Ok(out)
    }
    /// Rebuild all alternatives under the admitted policy and check their material owners and available funding.
    /// # Errors
    /// Refuses stale periods, unexpected/unsorted owners, changed balances or noncanonical frames.
    pub fn decode(
        catalog: &MaterialCatalog,
        state: &MaterialCircuitState,
        period: u64,
        bytes: &[u8],
    ) -> Result<Self> {
        let policy = catalog.company_portfolios.as_ref().ok_or(Invalid)?;
        let mut read = Input(
            bytes
                .strip_prefix(COMPANY_PORTFOLIO_DOMAIN)
                .ok_or(Invalid)?,
        );
        if read.number()? != period {
            return Err(Invalid);
        }
        let n = read.count()?;
        if n != catalog.company_payouts.len() {
            return Err(Invalid);
        }
        let mut companies = Vec::new();
        let mut remaining = catalog.process_outputs.len();
        for parent in &catalog.company_payouts {
            let company = CompanyId::from_bytes(read.take()?);
            if company != parent.company {
                return Err(Invalid);
            }
            let [history_len] = read.take()?;
            if history_len == 0 || history_len > policy.history_periods {
                return Err(Invalid);
            }
            let mut history = Vec::new();
            for _ in 0..history_len {
                history.push(read.money()?);
            }
            let treasury = read.money()?;
            let num = read.count()?;
            remaining = remaining.checked_sub(num).ok_or(Invalid)?;
            let mut processes = Vec::new();
            for _ in 0..num {
                let site = SiteId::from_bytes(read.take()?);
                let process = ProcessId::from_bytes(read.take()?);
                processes.push(CompanyProcessEvidence {
                    site,
                    process,
                    produced_batches: read.number()?,
                    capacity_batches: read.number()?,
                    unmet_accepted_units: read.number()?,
                    used_service_batches: read.number()?,
                    replacement: read.number()?,
                    expansion: read.number()?,
                    unit_price: read.money()?,
                    free_cash: read.money()?,
                    earnings_budget: read.money()?,
                });
            }
            if processes
                .windows(2)
                .any(|r| (r[0].site, r[0].process) >= (r[1].site, r[1].process))
            {
                return Err(Invalid);
            }
            companies.push(CompanyPortfolioEvidence::from_close(
                company, period, history, treasury, processes, policy,
            )?);
        }
        if !read.0.is_empty() {
            return Err(Invalid);
        }
        let result = Self { companies };
        result.validate(catalog, state, period)?;
        Ok(result)
    }
}
fn count(out: &mut Vec<u8>, size: usize) -> Result<()> {
    if size > MAX_MATERIAL_CIRCUIT_ROWS {
        return Err(MaterialCircuitError::RowLimit);
    }
    out.extend_from_slice(&u32::try_from(size).map_err(|_| Invalid)?.to_be_bytes());
    Ok(())
}
struct Input<'a>(&'a [u8]);
impl Input<'_> {
    fn take<const N: usize>(&mut self) -> Result<[u8; N]> {
        let (value, more) = self.0.split_at_checked(N).ok_or(Invalid)?;
        self.0 = more;
        value.try_into().map_err(|_| Invalid)
    }
    fn number(&mut self) -> Result<u64> {
        Ok(u64::from_be_bytes(self.take()?))
    }
    fn money(&mut self) -> Result<Currency> {
        Ok(Currency::from_micro_units(i128::from_be_bytes(
            self.take()?,
        )))
    }
    fn count(&mut self) -> Result<usize> {
        let size = usize::try_from(u32::from_be_bytes(self.take()?)).map_err(|_| Invalid)?;
        if size > MAX_MATERIAL_CIRCUIT_ROWS {
            return Err(MaterialCircuitError::RowLimit);
        }
        Ok(size)
    }
}
