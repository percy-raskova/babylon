use super::{
    allocate_county, CountyGeoid, CountyTimeControls, HouseholdTimeAllocationError as Error,
    HouseholdTimeMeasure as Measure, NationalHouseholdTimeAllocation,
};
use crate::{
    national_counties::{CountyReference, NationalCountyReference, SourceCell},
    national_household_allocation::{CountyHouseholdAllocation, NationalHouseholdAllocation},
    national_households::national_household_reference,
    national_resident_workforce::national_resident_workforce_reference,
};
/// Join pinned observed county controls to the existing counted household budgets.
/// Assignment across budgets is Designed; county age/workforce margins stay exact.
/// # Errors
/// Refuses incompatible source digests, roster, unavailable cells and impossible margins.
pub fn allocate_household_time(
    counties: &NationalCountyReference,
    households: &NationalHouseholdAllocation,
) -> Result<NationalHouseholdTimeAllocation, Error> {
    let household_source = national_household_reference().map_err(Error::HouseholdReference)?;
    let workforce_source =
        national_resident_workforce_reference().map_err(Error::WorkforceReference)?;
    if households.county_source_sha256 != counties.artifact_sha256()
        || households.household_source_sha256() != household_source.artifact_sha256()
        || households.classes_source_sha256 != workforce_source.artifact_sha256()
    {
        return Err(Error::SourceDigest);
    }
    validate_roster(
        counties,
        households
            .counties()
            .iter()
            .map(CountyHouseholdAllocation::county),
    )?;
    let mut rows = Vec::with_capacity(counties.counties().len());
    for county in counties.counties() {
        let id = county.geoid();
        let source = county.residents();
        let controls = CountyTimeControls {
            population: observation(id, Measure::Population, &source.population_persons.estimate)?,
            households: observation(id, Measure::Households, &source.households.estimate)?,
            eligible_16_plus: observation(
                id,
                Measure::Eligible16Plus,
                &source.age_16_plus_persons.estimate,
            )?,
            employed: observation(
                id,
                Measure::Employed,
                &source.civilian_employed_persons.estimate,
            )?,
            reserve: observation(
                id,
                Measure::Reserve,
                &source.civilian_unemployed_persons.estimate,
            )?,
            armed_forces: observation(
                id,
                Measure::ArmedForces,
                &source.armed_forces_persons.estimate,
            )?,
            inactive: observation(
                id,
                Measure::Inactive,
                &source.not_in_labor_force_persons.estimate,
            )?,
        };
        rows.push(allocate_county(
            id,
            controls,
            households
                .county(id)
                .map_err(|_| Error::CountyRoster)?
                .budgets(),
        )?);
    }
    Ok(NationalHouseholdTimeAllocation {
        county_source_sha256: counties.artifact_sha256(),
        household_source_sha256: household_source.artifact_sha256(),
        resident_workforce_source_sha256: workforce_source.artifact_sha256(),
        counties: rows,
    })
}
pub(super) fn validate_roster(
    source: &NationalCountyReference,
    keys: impl IntoIterator<Item = CountyGeoid>,
) -> Result<(), Error> {
    if keys
        .into_iter()
        .eq(source.counties().iter().map(CountyReference::geoid))
    {
        Ok(())
    } else {
        Err(Error::CountyRoster)
    }
}
pub(super) fn observation(
    county: CountyGeoid,
    measure: Measure,
    cell: &SourceCell,
) -> Result<u64, Error> {
    cell.value().ok_or_else(|| Error::UnavailableObservation {
        county,
        measure,
        status: cell.status(),
        raw: cell.raw().to_owned(),
    })
}
