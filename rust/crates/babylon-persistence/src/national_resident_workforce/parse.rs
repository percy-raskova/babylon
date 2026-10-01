use super::{
    NationalResidentWorkforceReference, ResidentWorkerClasses,
    ResidentWorkforceReferenceError as Error, COUNTY_COUNT, MAX_DECODED_BYTES,
};
use crate::national_counties::{acs_cell, AcsEstimate, NationalCountyReference, ObservationStatus};
use babylon_kernel::geography::CountyGeoid;

fn header() -> String {
    let mut names = vec!["county_geoid".to_owned()];
    for line in 1..=21 {
        for kind in ['E', 'M'] {
            for suffix in ["value", "raw", "status"] {
                names.push(format!("B24080_{kind}{line:03}_{suffix}"));
            }
        }
    }
    names.join(",")
}

pub(super) fn capture(
    text: &str,
    controls: &NationalCountyReference,
) -> Result<NationalResidentWorkforceReference, Error> {
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
    let mut counties: Vec<ResidentWorkerClasses> = Vec::with_capacity(COUNTY_COUNT);
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
    Ok(NationalResidentWorkforceReference {
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

fn known_sum(values: impl Iterator<Item = Option<u64>>) -> Result<Option<u64>, Error> {
    let values: Option<Vec<_>> = values.collect();
    let Some(values) = values else {
        return Ok(None);
    };
    let mut total = 0_u64;
    for value in values {
        total = total.checked_add(value).ok_or(Error::Arithmetic)?;
        i64::try_from(total).map_err(|_| Error::Arithmetic)?;
    }
    Ok(Some(total))
}

fn county(line: &str, controls: &NationalCountyReference) -> Result<ResidentWorkerClasses, Error> {
    let fields: Vec<_> = line.split(',').collect();
    if fields.len() != 127 {
        return Err(Error::CsvShape);
    }
    let geoid = CountyGeoid::try_from(fields[0]).map_err(|_| Error::CountyIdentity)?;
    let control = controls
        .county(geoid)
        .map_err(|_| Error::UnknownCounty(geoid))?;
    let observations: Vec<_> = fields[1..]
        .chunks_exact(6)
        .map(observation)
        .collect::<Result<_, _>>()?;
    let observations: [AcsEstimate; 21] = observations.try_into().map_err(|_| Error::CsvShape)?;
    let estimate = |line: usize| observations[line - 1].estimate.value();
    for (parent, members) in [
        (1, &[2, 12][..]),
        (2, &[3, 6, 7, 8, 9, 10, 11]),
        (3, &[4, 5]),
        (12, &[13, 16, 17, 18, 19, 20, 21]),
        (13, &[14, 15]),
    ] {
        if let (Some(parent), Some(sum)) = (
            estimate(parent),
            known_sum(members.iter().copied().map(estimate))?,
        ) {
            if parent != sum {
                return Err(Error::Partition);
            }
        }
    }
    if let (Some(total), Some(control)) = (
        estimate(1),
        control
            .residents()
            .civilian_employed_persons
            .estimate
            .value(),
    ) {
        if total != control {
            return Err(Error::ResidentControl);
        }
    }
    let mut persons = [None; 8];
    for (index, value) in persons.iter_mut().enumerate() {
        *value = known_sum([estimate(index + 4), estimate(index + 14)].into_iter())?;
    }
    Ok(ResidentWorkerClasses {
        geoid,
        observations: Box::new(observations),
        persons,
    })
}
