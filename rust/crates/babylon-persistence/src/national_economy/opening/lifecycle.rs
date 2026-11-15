//! Allocate county ACS margins before folding the source leaves into game principals.
use super::{NationalOpening, NationalOpeningError as Error, Result};
use crate::national_ages::NationalAgeReference;
use crate::national_economy::grain::HouseholdIncidence;
use crate::national_economy::{GameHouseholdLifecyclePolicy, InitialAgeDistribution};
use crate::national_resident_allocation;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::{
    FinalDemandPrincipalId, HouseholdLifecycleBook, HouseholdTimeAccounting, ResidentAges,
};
use std::collections::BTreeMap;

#[derive(Clone, Copy)]
struct Exposure {
    principal: FinalDemandPrincipalId,
    eligible: u64,
    under_16: u64,
}

/// Assign teens, then seniors from remaining eligible people. The adult band receives
/// the residual. Integer ties follow the existing budget order or protected principal ID.
fn split(
    total: ResidentAges,
    exposures: &[Exposure],
) -> Result<Vec<(FinalDemandPrincipalId, ResidentAges)>> {
    let eligible: Vec<_> = exposures.iter().map(|e| e.eligible).collect();
    let count = |values: &[u64]| {
        values
            .iter()
            .try_fold(0_u64, |n, v| n.checked_add(*v).ok_or(Error::Arithmetic))
    };
    if count(&eligible)? != total.eligible().map_err(Error::TimeAccount)?
        || exposures.iter().try_fold(0_u64, |n, e| {
            n.checked_add(e.under_16).ok_or(Error::Arithmetic)
        })? != total.under_16
    {
        return Err(Error::SourceScope);
    }
    let teens = national_resident_allocation::apportion(total.age_16_17, &eligible)
        .map_err(Error::Workforce)?;
    let residual = eligible
        .iter()
        .zip(&teens)
        .map(|(e, t)| e.checked_sub(*t).ok_or(Error::SourceScope))
        .collect::<Result<Vec<_>>>()?;
    let seniors = national_resident_allocation::apportion(total.age_65_plus, &residual)
        .map_err(Error::Workforce)?;
    exposures
        .iter()
        .zip(teens)
        .zip(residual)
        .zip(seniors)
        .map(|(((e, age_16_17), remaining), age_65_plus)| {
            Ok((
                e.principal,
                ResidentAges {
                    under_16: e.under_16,
                    age_16_17,
                    age_18_64: remaining
                        .checked_sub(age_65_plus)
                        .ok_or(Error::SourceScope)?,
                    age_65_plus,
                },
            ))
        })
        .collect()
}

fn accumulate(target: &mut ResidentAges, source: ResidentAges) -> Result<()> {
    let add = |a: u64, b: u64| a.checked_add(b).ok_or(Error::Arithmetic);
    target.under_16 = add(target.under_16, source.under_16)?;
    target.age_16_17 = add(target.age_16_17, source.age_16_17)?;
    target.age_18_64 = add(target.age_18_64, source.age_18_64)?;
    target.age_65_plus = add(target.age_65_plus, source.age_65_plus)?;
    Ok(())
}

fn pushforward(
    result: &mut BTreeMap<FinalDemandPrincipalId, ResidentAges>,
    parent: &HouseholdIncidence,
    bands: ResidentAges,
    opening: &NationalOpening,
) -> Result<()> {
    let mut remainder = Exposure {
        principal: parent.destination,
        eligible: parent.time.eligible_16_plus,
        under_16: parent.time.under_16,
    };
    let mut leaves = Vec::new();
    for child in opening
        .aid
        .children
        .iter()
        .filter(|c| c.parent == parent.source)
    {
        remainder.under_16 = remainder
            .under_16
            .checked_sub(child.under16)
            .ok_or(Error::SourceScope)?;
        remainder.eligible = remainder
            .eligible
            .checked_sub(child.eligible)
            .ok_or(Error::SourceScope)?;
        leaves.push(Exposure {
            principal: child.principal,
            eligible: child.eligible,
            under_16: child.under16,
        });
    }
    if leaves.is_empty() {
        return accumulate(result.entry(parent.destination).or_default(), bands);
    }
    leaves.push(remainder);
    leaves.sort_unstable_by_key(|e| e.principal);
    for (principal, ages) in split(bands, &leaves)? {
        accumulate(result.entry(principal).or_default(), ages)?;
    }
    Ok(())
}

fn domestic(
    opening: &NationalOpening,
    reference: &NationalAgeReference,
) -> Result<BTreeMap<FinalDemandPrincipalId, ResidentAges>> {
    let mut sources = BTreeMap::<_, Vec<_>>::new();
    for parent in &opening.representation.household_incidence {
        sources.entry(parent.county).or_default().push(parent);
    }
    if sources.len() != reference.counties.len() {
        return Err(Error::SourceScope);
    }
    let mut result = BTreeMap::new();
    for (county, mut parents) in sources {
        parents.sort_unstable_by_key(|p| p.margins.key);
        let total = reference.county(county).ok_or(Error::SourceScope)?;
        let exposures: Vec<_> = parents
            .iter()
            .map(|p| Exposure {
                principal: p.source,
                eligible: p.time.eligible_16_plus,
                under_16: p.time.under_16,
            })
            .collect();
        for (parent, (_, bands)) in parents.into_iter().zip(split(*total, &exposures)?) {
            pushforward(&mut result, parent, bands, opening)?;
        }
    }
    Ok(result)
}

fn external(persons: u64, eligible: u64, shares: [u16; 3]) -> Result<ResidentAges> {
    let shares = shares.map(u64::from);
    let bands =
        national_resident_allocation::apportion(eligible, &shares).map_err(Error::Workforce)?;
    let [age_16_17, age_18_64, age_65_plus] = bands.as_slice() else {
        return Err(Error::SourceScope);
    };
    Ok(ResidentAges {
        under_16: persons.checked_sub(eligible).ok_or(Error::SourceScope)?,
        age_16_17: *age_16_17,
        age_18_64: *age_18_64,
        age_65_plus: *age_65_plus,
    })
}

pub(super) fn wire(
    opening: &mut NationalOpening,
    reference: &NationalAgeReference,
    terms: &GameHouseholdLifecyclePolicy,
    retailer_buffer_periods: u64,
) -> Result<()> {
    let mut domestic = domestic(opening, reference)?;
    let policies = &opening.opening.policies.household_time_policy;
    let eligible: BTreeMap<_, _> = policies
        .iter()
        .map(|p| (p.principal_id, p.eligible_persons))
        .collect();
    let mut positions = Vec::with_capacity(opening.opening.households.len());
    for h in &opening.opening.households {
        let expected = *eligible.get(&h.principal_id).ok_or(Error::Identity)?;
        let ages = match h.location {
            EconomicLocation::County(_) => {
                domestic.remove(&h.principal_id).ok_or(Error::Identity)?
            }
            EconomicLocation::Foreign(_) | EconomicLocation::Dependency(_) => {
                external(h.persons, expected, terms.external_eligible_age_bps)?
            }
        };
        if ages.persons().map_err(Error::TimeAccount)? != h.persons
            || ages.eligible().map_err(Error::TimeAccount)? != expected
        {
            return Err(Error::SourceScope);
        }
        positions.push((h.principal_id, ages));
    }
    if !domestic.is_empty() {
        return Err(Error::Identity);
    }
    let HouseholdTimeAccounting::Modeled(book) = &mut opening.opening.policies.household_time
    else {
        return Err(Error::Policy);
    };
    let mut lifecycle = match terms.initial_age_distribution {
        InitialAgeDistribution::UniformRemainingBirthdays => {
            HouseholdLifecycleBook::new(terms.rates, positions).map_err(Error::TimeAccount)?
        }
    };
    lifecycle.purchase_buffer_periods = Some(retailer_buffer_periods);
    book.lifecycle = Some(lifecycle);
    Ok(())
}
