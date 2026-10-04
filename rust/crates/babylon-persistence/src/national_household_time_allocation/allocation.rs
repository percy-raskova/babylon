use super::{
    CountyGeoid, CountyHouseholdTimeAllocation, CountyTimeControls, HouseholdTimeAllocation,
    HouseholdTimeAllocationError as Error,
};
use crate::national_household_allocation::{HouseholdBudgetAllocation, HouseholdBudgetKey};

pub(super) fn allocate_county(
    county: CountyGeoid,
    c: CountyTimeControls,
    budgets: &[HouseholdBudgetAllocation],
) -> Result<CountyHouseholdTimeAllocation, Error> {
    let add = |a: u64, b: u64| a.checked_add(b).ok_or(Error::Arithmetic { county });
    let force = add(c.employed, c.reserve)?;
    let extra_total = add(c.armed_forces, c.inactive)?;
    if add(force, extra_total)? != c.eligible_16_plus
        || c.eligible_16_plus > c.population
        || c.households > c.population
    {
        return Err(Error::CountyMargin { county });
    }
    let mut rows: Vec<_> = budgets.iter().collect();
    rows.sort_unstable_by_key(|row| row.key);
    let mut totals = [0_u64; 4];
    let mut capacities = Vec::with_capacity(rows.len());
    let mut previous = None;
    for row in &rows {
        if previous == Some(row.key) || row.key == HouseholdBudgetKey::PooledExternal {
            return Err(Error::BudgetIdentity { county });
        }
        previous = Some(row.key);
        let workforce = add(row.employed, row.reserve)?;
        if row.persons == 0
            || workforce > row.persons
            || row.households > row.persons
            || (row.key == HouseholdBudgetKey::CollectiveResidence && row.households != 0)
            || (row.key != HouseholdBudgetKey::CollectiveResidence && row.households == 0)
        {
            return Err(Error::BudgetMargin { county });
        }
        for (total, value) in
            totals
                .iter_mut()
                .zip([row.persons, row.households, row.employed, row.reserve])
        {
            *total = add(*total, value)?;
        }
        capacities.push(row.persons - workforce);
    }
    if totals != [c.population, c.households, c.employed, c.reserve] {
        return Err(Error::BudgetMargin { county });
    }
    let extras = apportion(county, extra_total, &capacities)?;
    let armed = apportion(county, c.armed_forces, &extras)?;
    let mut allocations = Vec::with_capacity(rows.len());
    for ((row, extra), armed_forces) in rows.into_iter().zip(extras).zip(armed) {
        let eligible_16_plus = add(add(row.employed, row.reserve)?, extra)?;
        let under_16 = row
            .persons
            .checked_sub(eligible_16_plus)
            .ok_or(Error::BudgetMargin { county })?;
        let inactive = extra
            .checked_sub(armed_forces)
            .ok_or(Error::BudgetMargin { county })?;
        allocations.push(HouseholdTimeAllocation {
            key: row.key,
            eligible_16_plus,
            armed_forces,
            inactive,
            under_16,
        });
    }
    Ok(CountyHouseholdTimeAllocation {
        county,
        budgets: allocations,
    })
}
fn apportion(county: CountyGeoid, total: u64, capacities: &[u64]) -> Result<Vec<u64>, Error> {
    let capacity = capacities.iter().try_fold(0_u64, |n, value| {
        n.checked_add(*value).ok_or(Error::Arithmetic { county })
    })?;
    if total > capacity {
        return Err(Error::BudgetMargin { county });
    }
    crate::national_resident_allocation::apportion(total, capacities)
        .map_err(|_| Error::Arithmetic { county })
}
