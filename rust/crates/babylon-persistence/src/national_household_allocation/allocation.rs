use super::{
    HouseholdAllocationError as Error, HouseholdBudgetAllocation, HouseholdBudgetKey,
    HouseholdCountyControls,
};
use crate::national_resident_allocation::AllocationError;
use std::result::Result as StdResult;
type Result<T> = StdResult<T, Error>;
/// Slots: the five keys of schema 7 and earlier in key order, then the two bands of schema 8.
const KEYS: [HouseholdBudgetKey; SLOTS] = [
    HouseholdBudgetKey::EarningNonowner,
    HouseholdBudgetKey::EarningOwner,
    HouseholdBudgetKey::NoEarnerNonowner,
    HouseholdBudgetKey::NoEarnerOwner,
    HouseholdBudgetKey::CollectiveResidence,
    HouseholdBudgetKey::EarningLowerPaidHalf,
    HouseholdBudgetKey::EarningBetterPaidForty,
];
const SLOTS: usize = 7;
const COLLECTIVE: usize = 4;
/// The slots that hold earning households, in the order a remainder is dealt in.
const EARNING: [usize; 4] = [0, 1, 5, 6];
/// The slots of ordinary households.
const ORDINARY: [usize; 6] = [0, 1, 2, 3, 5, 6];

pub(super) fn allocate_county(
    c: HouseholdCountyControls,
    owner_bps: u16,
    next_forty_bps: Option<u16>,
) -> Result<Vec<HouseholdBudgetAllocation>> {
    let households = c
        .with_historical_earnings_households
        .checked_add(c.without_historical_earnings_households)
        .ok_or(Error::Arithmetic)?;
    validate(c, households, owner_bps, next_forty_bps)?;
    if c.population == 0 {
        return Ok(vec![]);
    }
    let with_owners = owners(c.with_historical_earnings_households, owner_bps)?;
    let without_owners = owners(c.without_historical_earnings_households, owner_bps)?;
    let mut h = [0; SLOTS];
    h[1] = with_owners;
    h[2] = c.without_historical_earnings_households - without_owners;
    h[3] = without_owners;
    let rest = c.with_historical_earnings_households - with_owners;
    if let Some(next) = next_forty_bps {
        // The owners and the better-paid forty are the top `owner + next` of the earning households.
        let upper = owners(
            c.with_historical_earnings_households,
            owner_bps.checked_add(next).ok_or(Error::Arithmetic)?,
        )?
        .max(with_owners);
        h[6] = upper - with_owners;
        h[5] = c.with_historical_earnings_households - upper;
    } else {
        h[0] = rest;
    }
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
    let mut employed = [0; SLOTS];
    let preferred_owners = c.working_owners.min(ordinary_employed).min(persons[1]);
    let weights: Vec<u64> = EARNING
        .iter()
        .map(|i| persons[*i] - if *i == 1 { preferred_owners } else { 0 })
        .collect();
    for (slot, share) in EARNING
        .iter()
        .zip(apportion(ordinary_employed - preferred_owners, &weights)?)
    {
        employed[*slot] = share;
    }
    employed[1] = employed[1]
        .checked_add(preferred_owners)
        .ok_or(Error::Arithmetic)?;
    employed[COLLECTIVE] = c.employed - ordinary_employed;
    let capacities = persons
        .iter()
        .zip(employed)
        .map(|(p, e)| p.checked_sub(e).ok_or(Error::PopulationControl))
        .collect::<Result<Vec<_>>>()?;
    let reserves = apportion(c.reserve, &capacities)?;
    Ok((0..SLOTS)
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
    households: [u64; SLOTS],
    ordinary_households: u64,
    employed: u64,
) -> Result<[u64; SLOTS]> {
    let mut p = households;
    p[COLLECTIVE] = c.population - c.household_persons;
    let mut remaining = c.household_persons - ordinary_households;
    let owner_extra = c
        .working_owners
        .min(employed)
        .saturating_sub(p[1])
        .min(remaining);
    p[1] = p[1].checked_add(owner_extra).ok_or(Error::Arithmetic)?;
    remaining -= owner_extra;
    let earning_capacity = EARNING.iter().try_fold(0_u64, |sum, i| {
        sum.checked_add(p[*i]).ok_or(Error::Arithmetic)
    })?;
    let required_extra = employed.saturating_sub(earning_capacity);
    remaining = remaining
        .checked_sub(required_extra)
        .ok_or(Error::DesignedAllocationInfeasible)?;
    spread(&mut p, &EARNING, required_extra, &households)?;
    spread(&mut p, &ORDINARY, remaining, &households)?;
    Ok(p)
}
/// Add `total` to the named slots in proportion to their households.
fn spread(
    p: &mut [u64; SLOTS],
    slots: &[usize],
    total: u64,
    households: &[u64; SLOTS],
) -> Result<()> {
    let weights: Vec<u64> = slots.iter().map(|i| households[*i]).collect();
    for (slot, extra) in slots.iter().zip(apportion(total, &weights)?) {
        p[*slot] = p[*slot].checked_add(extra).ok_or(Error::Arithmetic)?;
    }
    Ok(())
}
fn validate(
    c: HouseholdCountyControls,
    households: u64,
    owner_bps: u16,
    next_forty_bps: Option<u16>,
) -> Result<()> {
    if !(1..=10_000).contains(&owner_bps)
        || next_forty_bps
            .is_some_and(|next| next == 0 || u32::from(owner_bps) + u32::from(next) >= 10_000)
    {
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
        AllocationError::PopulationControl => Error::DesignedAllocationInfeasible,
        _ => Error::Arithmetic,
    })
}
