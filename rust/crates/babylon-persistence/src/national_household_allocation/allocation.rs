use super::{
    HouseholdAllocationError as Error, HouseholdBudgetAllocation, HouseholdBudgetKey,
    HouseholdCountyControls,
};
type Result<T> = std::result::Result<T, Error>;
const KEYS: [HouseholdBudgetKey; 5] = [
    HouseholdBudgetKey::EarningNonowner,
    HouseholdBudgetKey::EarningOwner,
    HouseholdBudgetKey::NoEarnerNonowner,
    HouseholdBudgetKey::NoEarnerOwner,
    HouseholdBudgetKey::CollectiveResidence,
];

pub(super) fn allocate_county(
    c: HouseholdCountyControls,
    owner_bps: u16,
) -> Result<Vec<HouseholdBudgetAllocation>> {
    let households = c
        .with_historical_earnings_households
        .checked_add(c.without_historical_earnings_households)
        .ok_or(Error::Arithmetic)?;
    validate(c, households, owner_bps)?;
    if c.population == 0 {
        return Ok(vec![]);
    }
    let with_owners = owners(c.with_historical_earnings_households, owner_bps)?;
    let without_owners = owners(c.without_historical_earnings_households, owner_bps)?;
    let h = [
        c.with_historical_earnings_households - with_owners,
        with_owners,
        c.without_historical_earnings_households - without_owners,
        without_owners,
        0,
    ];
    let gq = c.population - c.household_persons;
    let maximum_ordinary_employed = if c.with_historical_earnings_households == 0 {
        0
    } else {
        c.household_persons - c.without_historical_earnings_households
    };
    let lower = c.employed.saturating_sub(gq);
    let upper = c.employed.min(maximum_ordinary_employed);
    if lower > upper {
        return Err(Error::DesignedAllocationInfeasible);
    }
    let weighted = u64::try_from(
        u128::from(c.employed) * u128::from(c.household_persons) / u128::from(c.population),
    )
    .map_err(|_| Error::Arithmetic)?;
    let ordinary_employed = weighted
        .clamp(lower, upper)
        .max(c.working_owners.min(upper));
    let persons = persons(c, h, households, ordinary_employed)?;
    let mut employed = [0; 5];
    let preferred_owners = c.working_owners.min(ordinary_employed).min(persons[1]);
    let residual = apportion(
        ordinary_employed - preferred_owners,
        &[persons[0], persons[1] - preferred_owners],
    )?;
    employed[0] = residual[0];
    employed[1] = residual[1]
        .checked_add(preferred_owners)
        .ok_or(Error::Arithmetic)?;
    employed[4] = c.employed - ordinary_employed;
    let capacities = persons
        .iter()
        .zip(employed)
        .map(|(p, e)| p.checked_sub(e).ok_or(Error::PopulationControl))
        .collect::<Result<Vec<_>>>()?;
    let reserves = apportion(c.reserve, &capacities)?;
    Ok((0..5)
        .filter(|i| persons[*i] > 0)
        .map(|i| HouseholdBudgetAllocation {
            key: KEYS[i],
            persons: persons[i],
            households: h[i],
            employed: employed[i],
            reserve: reserves[i],
        })
        .collect())
}

fn persons(
    c: HouseholdCountyControls,
    households: [u64; 5],
    ordinary_households: u64,
    employed: u64,
) -> Result<[u64; 5]> {
    let mut p = households;
    p[4] = c.population - c.household_persons;
    let mut remaining = c.household_persons - ordinary_households;
    let owner_extra = c
        .working_owners
        .min(employed)
        .saturating_sub(p[1])
        .min(remaining);
    p[1] = p[1].checked_add(owner_extra).ok_or(Error::Arithmetic)?;
    remaining -= owner_extra;
    let earning_capacity = p[0].checked_add(p[1]).ok_or(Error::Arithmetic)?;
    let required_extra = employed.saturating_sub(earning_capacity);
    remaining = remaining
        .checked_sub(required_extra)
        .ok_or(Error::DesignedAllocationInfeasible)?;
    for (slot, extra) in p[..2]
        .iter_mut()
        .zip(apportion(required_extra, &households[..2])?)
    {
        *slot = slot.checked_add(extra).ok_or(Error::Arithmetic)?;
    }
    for (slot, extra) in p[..4]
        .iter_mut()
        .zip(apportion(remaining, &households[..4])?)
    {
        *slot = slot.checked_add(extra).ok_or(Error::Arithmetic)?;
    }
    Ok(p)
}
fn validate(c: HouseholdCountyControls, households: u64, owner_bps: u16) -> Result<()> {
    if !(1..=10_000).contains(&owner_bps) {
        return Err(Error::Policy);
    }
    let workforce = c.employed.checked_add(c.reserve).ok_or(Error::Arithmetic)?;
    if c.household_persons > c.population
        || households > c.household_persons
        || (households == 0) != (c.household_persons == 0)
        || workforce > c.population
        || c.working_owners > c.employed
    {
        return Err(Error::PopulationControl);
    }
    Ok(())
}
fn owners(households: u64, bps: u16) -> Result<u64> {
    u64::try_from((u128::from(households) * u128::from(bps)).div_ceil(10_000))
        .map_err(|_| Error::Arithmetic)
}
fn apportion(total: u64, weights: &[u64]) -> Result<Vec<u64>> {
    crate::national_resident_allocation::apportion(total, weights).map_err(|error| match error {
        crate::national_resident_allocation::AllocationError::PopulationControl => {
            Error::DesignedAllocationInfeasible
        }
        _ => Error::Arithmetic,
    })
}
