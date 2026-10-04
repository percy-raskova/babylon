use super::{
    CountyHouseholdMargins, HouseholdReferenceError as Error, NationalHouseholdReference,
    COUNTY_COUNT, MAX_DECODED_BYTES,
};
use crate::national_counties::{acs_cell, AcsEstimate, NationalCountyReference, ObservationStatus};
use babylon_kernel::geography::CountyGeoid;

fn header() -> String {
    let mut names = vec!["county_geoid".to_owned()];
    for (table, count) in [("B11001", 9), ("B11002", 12), ("B19001", 17), ("B19051", 3)] {
        for line in 1..=count {
            for kind in ['E', 'M'] {
                for suffix in ["value", "raw", "status"] {
                    names.push(format!("{table}_{kind}{line:03}_{suffix}"));
                }
            }
        }
    }
    names.join(",")
}

pub(super) fn capture(
    text: &str,
    controls: &NationalCountyReference,
) -> Result<NationalHouseholdReference, Error> {
    if text.len() > MAX_DECODED_BYTES {
        return Err(Error::Bound);
    }
    if !text.ends_with('\n') || text.contains('\r') {
        return Err(Error::CsvShape);
    }
    let mut lines = text.lines();
    if lines.next() != Some(header().as_str()) {
        return Err(Error::Header);
    }
    let mut counties: Vec<CountyHouseholdMargins> = Vec::with_capacity(COUNTY_COUNT);
    for line in lines {
        if counties.len() == COUNTY_COUNT {
            return Err(Error::Bound);
        }
        let row = county(line, controls)?;
        if counties
            .last()
            .is_some_and(|prior| prior.geoid >= row.geoid)
        {
            return Err(Error::CountyOrder);
        }
        counties.push(row);
    }
    if counties.len() != COUNTY_COUNT
        || counties
            .iter()
            .zip(controls.counties())
            .any(|(left, right)| left.geoid != right.geoid())
    {
        return Err(Error::Coverage);
    }
    Ok(NationalHouseholdReference {
        counties: counties.into_boxed_slice(),
    })
}

fn observation(fields: &[&str]) -> Result<AcsEstimate, Error> {
    let estimate = acs_cell(&fields[..3]).map_err(Error::CountySource)?;
    let margin_of_error = acs_cell(&fields[3..]).map_err(Error::CountySource)?;
    if matches!(
        estimate.status(),
        ObservationStatus::MoeNotComputable
            | ObservationStatus::MoeOpenEndedMedian
            | ObservationStatus::ControlledEstimate
    ) || margin_of_error.status() == ObservationStatus::EstimateNotComputable
    {
        return Err(Error::SentinelRole);
    }
    Ok(AcsEstimate {
        estimate,
        margin_of_error,
    })
}

fn partition(rows: &[AcsEstimate], parent: usize, children: &[usize]) -> Result<(), Error> {
    let values: Option<Vec<_>> = children
        .iter()
        .map(|line| rows[line - 1].estimate.value())
        .collect();
    let Some(values) = values else {
        return Ok(());
    };
    let mut sum = 0_u64;
    for value in values {
        sum = sum.checked_add(value).ok_or(Error::Arithmetic)?;
        i64::try_from(sum).map_err(|_| Error::Arithmetic)?;
    }
    if rows[parent - 1]
        .estimate
        .value()
        .is_some_and(|target| sum != target)
    {
        return Err(Error::Partition);
    }
    Ok(())
}

fn observations<const N: usize>(fields: &[&str]) -> Result<Box<[AcsEstimate; N]>, Error> {
    fields
        .chunks_exact(6)
        .map(observation)
        .collect::<Result<Vec<_>, _>>()?
        .try_into()
        .map(Box::new)
        .map_err(|_| Error::CsvShape)
}

fn county(line: &str, controls: &NationalCountyReference) -> Result<CountyHouseholdMargins, Error> {
    let fields: Vec<_> = line.split(',').collect();
    if fields.len() != 247 {
        return Err(Error::CsvShape);
    }
    let geoid = CountyGeoid::try_from(fields[0]).map_err(|_| Error::CountyIdentity)?;
    let control = controls
        .county(geoid)
        .map_err(|_| Error::UnknownCounty(geoid))?
        .residents();
    let household_types: Box<[AcsEstimate; 9]> = observations(&fields[1..55])?;
    let household_persons: Box<[AcsEstimate; 12]> = observations(&fields[55..127])?;
    let income_households: Box<[AcsEstimate; 17]> = observations(&fields[127..229])?;
    let earnings_households: Box<[AcsEstimate; 3]> = observations(&fields[229..])?;
    partition(earnings_households.as_slice(), 1, &[2, 3])?;
    for (parent, children) in [(1, &[2, 7][..]), (2, &[3, 4]), (4, &[5, 6]), (7, &[8, 9])] {
        partition(household_types.as_slice(), parent, children)?;
    }
    for (parent, children) in [
        (1, &[2, 12][..]),
        (2, &[3, 6, 9]),
        (3, &[4, 5]),
        (6, &[7, 8]),
        (9, &[10, 11]),
    ] {
        partition(household_persons.as_slice(), parent, children)?;
    }
    partition(
        income_households.as_slice(),
        1,
        &[2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
    )?;
    if household_types[0] != control.households {
        return Err(Error::HouseholdControl);
    }
    if let (Some(households), Some(income_total)) = (
        household_types[0].estimate.value(),
        income_households[0].estimate.value(),
    ) {
        if households != income_total {
            return Err(Error::IncomeControl);
        }
    }
    if let (Some(households), Some(earnings_total)) = (
        household_types[0].estimate.value(),
        earnings_households[0].estimate.value(),
    ) {
        if households != earnings_total {
            return Err(Error::EarningsControl);
        }
    }
    let group_quarters = match (
        control.population_persons.estimate.value(),
        household_persons[0].estimate.value(),
    ) {
        (Some(population), Some(people)) => Some(
            population
                .checked_sub(people)
                .ok_or(Error::PopulationControl)?,
        ),
        _ => None,
    };
    Ok(CountyHouseholdMargins {
        geoid,
        household_types,
        household_persons,
        income_households,
        earnings_households,
        population: control.population_persons.clone(),
        group_quarters,
    })
}
