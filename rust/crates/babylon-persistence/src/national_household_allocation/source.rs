use super::{
    allocate_county, CountyHouseholdAllocation, HouseholdAllocationError as Error,
    HouseholdCountyControls, NationalHouseholdAllocation,
};
use crate::{
    national_counties::{CountyReference, NationalCountyReference},
    national_households::{HistoricalEarnings, NationalHouseholdReference},
    national_resident_workforce::{NationalResidentWorkforceReference, WorkerClass},
};
type Result<T> = std::result::Result<T, Error>;

/// Combine independent source margins only through the explicit Designed policy.
/// # Errors
/// Refuses incompatible rosters, absent controls or an infeasible counted allocation.
pub fn allocate_households(
    counties: &NationalCountyReference,
    households: &NationalHouseholdReference,
    workforce: &NationalResidentWorkforceReference,
    owner_bps: u16,
) -> Result<NationalHouseholdAllocation> {
    if households.counties().len() != counties.counties().len()
        || workforce.counties().len() != counties.counties().len()
    {
        return Err(Error::SourceScope);
    }
    let mut rows = Vec::with_capacity(counties.counties().len());
    for county in counties.counties() {
        rows.push(CountyHouseholdAllocation {
            county: county.geoid(),
            budgets: allocate_county(controls(county, households, workforce)?, owner_bps)?,
        });
    }
    Ok(NationalHouseholdAllocation {
        private_owner_households_bps: owner_bps,
        county_source_sha256: counties.artifact_sha256(),
        classes_source_sha256: workforce.artifact_sha256(),
        household_source_sha256: households.artifact_sha256(),
        counties: rows,
    })
}
fn controls(
    county: &CountyReference,
    households: &NationalHouseholdReference,
    workforce: &NationalResidentWorkforceReference,
) -> Result<HouseholdCountyControls> {
    let margins = households
        .county(county.geoid())
        .map_err(|_| Error::SourceScope)?;
    let classes = workforce
        .county(county.geoid())
        .map_err(|_| Error::SourceScope)?;
    let value = |cell: &crate::national_counties::AcsEstimate| {
        cell.estimate.value().ok_or(Error::MissingObservation)
    };
    let resident = county.residents();
    let population = value(&resident.population_persons)?;
    let employed = value(&resident.civilian_employed_persons)?;
    let working_owners = classes
        .persons(WorkerClass::IncorporatedSelfEmployed)
        .ok_or(Error::MissingObservation)?
        .checked_add(
            classes
                .persons(WorkerClass::UnincorporatedSelfEmployed)
                .ok_or(Error::MissingObservation)?,
        )
        .ok_or(Error::Arithmetic)?;
    if value(margins.total_households())? != value(&resident.households)?
        || value(margins.population_persons())? != population
        || value(classes.total())? != employed
    {
        return Err(Error::PopulationControl);
    }
    Ok(HouseholdCountyControls {
        population,
        household_persons: value(margins.persons_in_households())?,
        with_historical_earnings_households: value(
            margins.historical_earnings_households(HistoricalEarnings::WithEarnings),
        )?,
        without_historical_earnings_households: value(
            margins.historical_earnings_households(HistoricalEarnings::NoEarnings),
        )?,
        employed,
        reserve: value(&resident.civilian_unemployed_persons)?,
        working_owners,
    })
}
