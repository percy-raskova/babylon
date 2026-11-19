//! Whole-unit allocations use member cash once, then the conserved parent balance.
use super::model::{self, Result};
use super::{
    CompanyCondition, CompanyConditionOrder, CompanyPortfolioEvidence, CompanyPortfolioPolicy,
    CompanyProcessEvidence, CompanyProcessPlan,
};
use crate::{CompanyId, MaterialCircuitError, SiteId};
use babylon_kernel::currency::Currency;
use std::collections::BTreeMap;
impl CompanyPortfolioEvidence {
    /// Re-evaluate the original closing observations under the captured policy.
    /// # Errors
    /// Refuses inadmissible quantities, histories or currency arithmetic.
    pub fn recompute(&self, policy: &CompanyPortfolioPolicy) -> Result<Self> {
        Self::from_close(
            self.company,
            self.period,
            self.history.clone(),
            self.treasury_available,
            self.processes.clone(),
            policy,
        )
    }

    pub(super) fn from_close(
        company: CompanyId,
        period: u64,
        history: Vec<Currency>,
        treasury: Currency,
        mut processes: Vec<CompanyProcessEvidence>,
        policy: &CompanyPortfolioPolicy,
    ) -> Result<Self> {
        if period == 0
            || history.len()
                != usize::from(policy.history_periods)
                    .min(usize::try_from(period).unwrap_or(usize::MAX))
            || treasury.micro_units() < 0
        {
            return Err(MaterialCircuitError::FinancialInvariant);
        }
        processes.sort_unstable_by_key(|r| (r.site, r.process));
        if processes
            .windows(2)
            .any(|r| (r[0].site, r[0].process) == (r[1].site, r[1].process))
            || processes.iter().any(|r| {
                r.free_cash.micro_units() < 0
                    || r.earnings_budget.micro_units() < 0
                    || r.unit_price.micro_units() < 0
                    || ((r.replacement > 0 || r.expansion > 0) && r.unit_price.micro_units() == 0)
                    || r.produced_batches > r.capacity_batches
            })
        {
            return Err(MaterialCircuitError::EquipmentInvariant);
        }
        let income = history
            .iter()
            .copied()
            .try_fold(model::zero(), model::add)?
            .micro_units();
        let cap: u128 = processes
            .iter()
            .map(|r| u128::from(r.capacity_batches))
            .sum();
        let used: u128 = processes
            .iter()
            .map(|r| u128::from(r.produced_batches))
            .sum();
        let high = cap > 0 && used * 10_000 >= cap * u128::from(policy.high_utilization_bps);
        let unmet = processes.iter().any(|r| r.unmet_accepted_units > 0);
        let prefer_high_demand =
            policy.condition_order == CompanyConditionOrder::HighDemandBeforeSpare && high && unmet;
        let condition = if income < 0 {
            CompanyCondition::Loss
        } else if income == 0 {
            CompanyCondition::NoMatchingRow
        } else if processes.iter().any(|r| r.replacement > 0) {
            CompanyCondition::Replacement
        } else if used < cap && !prefer_high_demand {
            CompanyCondition::Spare
        } else if high && unmet {
            CompanyCondition::UnmetDemand
        } else {
            CompanyCondition::NoMatchingRow
        };
        let (large, spent) = allocate(&processes, treasury.micro_units(), i128::MAX)?;
        let modest = Currency::from_micro_units(spent)
            .floor_weighted_share(u128::from(policy.modest_expansion_bps), 10_000)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        let (small, _) = allocate(&processes, treasury.micro_units(), modest.micro_units())?;
        let (replacement, _) = allocate(&processes, treasury.micro_units(), 0)?;
        let plans = [vec![], replacement, small, large];
        let feasible = [
            true,
            !plans[1].is_empty(),
            plans[2].iter().any(|r| r.expansion > 0),
            plans[3].iter().any(|r| r.expansion > 0),
        ];
        let original_weights = policy
            .rows
            .get(condition as usize)
            .copied()
            .unwrap_or([1, 0, 0, 0]);
        let weights = std::array::from_fn(|i| if feasible[i] { original_weights[i] } else { 0 });
        Ok(Self {
            company,
            period,
            history,
            treasury_available: treasury,
            processes,
            condition,
            original_weights,
            weights,
            feasible,
            plans,
        })
    }
}
fn allocate(
    processes: &[CompanyProcessEvidence],
    mut central: i128,
    mut expansion_limit: i128,
) -> Result<(Vec<CompanyProcessPlan>, i128)> {
    let mut site_funds = BTreeMap::<SiteId, i128>::new();
    let mut profits = BTreeMap::<SiteId, i128>::new();
    let mut rows = Vec::with_capacity(processes.len());
    for r in processes {
        let cash = site_funds
            .entry(r.site)
            .or_insert(r.free_cash.micro_units());
        if *cash != r.free_cash.micro_units() {
            return Err(MaterialCircuitError::FinancialInvariant);
        }
        profits
            .entry(r.site)
            .and_modify(|v| *v = (*v).max(r.earnings_budget.micro_units()))
            .or_insert(r.earnings_budget.micro_units());
        rows.push(CompanyProcessPlan {
            site: r.site,
            process: r.process,
            replacement: 0,
            expansion: 0,
            funding: model::zero(),
        });
    }
    let mut spent = 0_i128;
    // Protect every affordable replacement before expansion competes for the same cash.
    for expansion in [false, true] {
        for (r, plan) in processes.iter().zip(&mut rows) {
            let price = r.unit_price.micro_units();
            let requested = if expansion {
                r.expansion
            } else {
                r.replacement
            };
            if requested == 0 {
                continue;
            }
            let cash = site_funds
                .get_mut(&r.site)
                .ok_or(MaterialCircuitError::FinancialInvariant)?;
            let profit = profits
                .get_mut(&r.site)
                .ok_or(MaterialCircuitError::FinancialInvariant)?;
            let funds = cash
                .checked_add(central)
                .ok_or(MaterialCircuitError::Arithmetic)?;
            let limit = if expansion {
                funds
                    .min(*profit)
                    .min(r.earnings_budget.micro_units())
                    .min(expansion_limit)
            } else {
                funds
            };
            let units = u64::try_from((limit / price).min(i128::from(requested)))
                .map_err(|_| MaterialCircuitError::Arithmetic)?;
            let cost = i128::from(units) * price;
            let own = (*cash).min(cost);
            *cash -= own;
            central -= cost - own;
            plan.funding = model::add(plan.funding, Currency::from_micro_units(cost - own))?;
            if expansion {
                spent = spent
                    .checked_add(cost)
                    .ok_or(MaterialCircuitError::Arithmetic)?;
                *profit -= cost;
                expansion_limit -= cost;
                plan.expansion = units;
            } else {
                plan.replacement = units;
            }
        }
    }
    rows.retain(|r| r.replacement > 0 || r.expansion > 0);
    Ok((rows, spent))
}
