//! Strict source records; all quantities remain observations in their named units.
use super::{
    AcsEstimate, CountyReference, InternalPoint, NationalCountyReference,
    NationalCountyReferenceError, ObservationStatus, ResidentEstimates, SourceCell,
    WorkplaceObservations, COUNTY_COUNT, MAX_CSV_BYTES,
};
use babylon_kernel::geography::{CountyGeoid, CountyJurisdiction, NationalCountyRoster};
type Error = NationalCountyReferenceError;
const COLUMN_COUNT: usize = 76;
const ACS_NAMES: [&str; 9] = [
    "population_persons",
    "households",
    "age_16_plus_persons",
    "labor_force_persons",
    "civilian_labor_force_persons",
    "civilian_employed_persons",
    "civilian_unemployed_persons",
    "armed_forces_persons",
    "not_in_labor_force_persons",
];

fn header() -> String {
    let mut names: Vec<String> = [
        "county_geoid",
        "state_fips",
        "county_fips",
        "county_name",
        "land_square_metres",
        "water_square_metres",
        "internal_point_latitude",
        "internal_point_longitude",
    ]
    .into_iter()
    .map(str::to_owned)
    .collect();
    for series in ACS_NAMES {
        for kind in ["estimate", "moe"] {
            for suffix in ["", "_raw", "_status"] {
                names.push(format!("acs_{series}_{kind}{suffix}"));
            }
        }
    }
    names.extend(["qcew_status".to_owned(), "qcew_disclosure_code".to_owned()]);
    for name in [
        "qcew_establishments",
        "qcew_jobs",
        "qcew_annual_payroll_usd",
        "qcew_mean_weekly_wage_usd",
    ] {
        for suffix in ["", "_raw", "_status"] {
            names.push(format!("{name}{suffix}"));
        }
    }
    names.join(",")
}

pub(super) fn parse_csv(text: &str) -> Result<NationalCountyReference, Error> {
    if text.len() > MAX_CSV_BYTES {
        return Err(Error::Bound);
    }
    if !text.ends_with('\n') || text.contains('\r') {
        return Err(Error::CsvShape);
    }
    let mut lines = text.lines();
    if lines.next() != Some(header().as_str()) {
        return Err(Error::Header);
    }
    let mut counties: Vec<CountyReference> = Vec::with_capacity(COUNTY_COUNT);
    for line in lines {
        if counties.len() == COUNTY_COUNT {
            return Err(Error::Bound);
        }
        let fields = csv_record(line)?;
        let fields: Vec<_> = fields.iter().map(String::as_str).collect();
        let row = county(&fields)?;
        if let Some(previous) = counties.last() {
            if previous.geoid == row.geoid {
                return Err(Error::DuplicateCounty(row.geoid));
            }
            if previous.geoid > row.geoid {
                return Err(Error::CountyOrder);
            }
        }
        counties.push(row);
    }
    let roster =
        NationalCountyRoster::try_new(counties.iter().map(CountyReference::geoid).collect())
            .map_err(|_| Error::RosterDigest)?;
    Ok(NationalCountyReference {
        roster,
        counties: counties.into_boxed_slice(),
    })
}

fn csv_record(line: &str) -> Result<Vec<String>, Error> {
    crate::reference_csv::record(line, COLUMN_COUNT).map_err(|_| Error::CsvShape)
}

fn integer(raw: &str) -> Result<u64, Error> {
    if raw.is_empty()
        || raw.len() > 19
        || !raw.bytes().all(|b| b.is_ascii_digit())
        || (raw.len() > 1 && raw.starts_with('0'))
    {
        return Err(Error::NumericValue);
    }
    let value = raw.parse::<u64>().map_err(|_| Error::NumericValue)?;
    i64::try_from(value).map_err(|_| Error::NumericValue)?;
    Ok(value)
}
fn cell(fields: &[&str], expected: &str, status: ObservationStatus) -> Result<SourceCell, Error> {
    if fields.len() != 3 || fields[2] != expected {
        return Err(Error::Observation);
    }
    let value = if status == ObservationStatus::Published {
        if fields[0] != fields[1] {
            return Err(Error::Observation);
        }
        Some(integer(fields[0])?)
    } else {
        if !fields[0].is_empty() {
            return Err(Error::Observation);
        }
        None
    };
    Ok(SourceCell {
        value,
        raw: fields[1].to_owned(),
        status,
    })
}
pub(crate) fn acs_cell(fields: &[&str]) -> Result<SourceCell, Error> {
    use ObservationStatus::{
        ControlledEstimate, EstimateNotComputable, InsufficientSampleCases, Missing,
        MoeNotComputable, MoeOpenEndedMedian, NotApplicableOrAvailable, Published,
    };
    let (name, status) = match fields.get(1).copied() {
        Some("" | "null") => ("missing", Missing),
        Some("-666666666") => ("estimate_not_computable", EstimateNotComputable),
        Some("-999999999") => ("insufficient_sample_cases", InsufficientSampleCases),
        Some("-888888888") => ("not_applicable_or_available", NotApplicableOrAvailable),
        Some("-222222222") => ("moe_not_computable", MoeNotComputable),
        Some("-333333333") => ("moe_open_ended_median", MoeOpenEndedMedian),
        Some("-555555555") => ("controlled_estimate", ControlledEstimate),
        _ => ("published", Published),
    };
    cell(fields, name, status)
}
pub(super) fn qcew(fields: &[&str]) -> Result<WorkplaceObservations, Error> {
    use ObservationStatus::{NotPublished, Published, Suppressed};
    if fields.len() != 14 {
        return Err(Error::CsvShape);
    }
    let status = match (fields[0], fields[1]) {
        ("published", "") => Published,
        ("suppressed", "N") => Suppressed,
        ("not_published", "") => NotPublished,
        _ => return Err(Error::Observation),
    };
    let measure = |index: usize| {
        let fields = &fields[2 + index * 3..5 + index * 3];
        let (name, expected) = match status {
            NotPublished => {
                if !fields[1].is_empty() {
                    return Err(Error::Observation);
                }
                ("not_published", NotPublished)
            }
            Suppressed if index > 0 => {
                if fields[1] != "0" {
                    return Err(Error::Observation);
                }
                ("suppressed", Suppressed)
            }
            _ => ("published", Published),
        };
        cell(fields, name, expected)
    };
    Ok(WorkplaceObservations {
        status,
        disclosure_code: fields[1].to_owned(),
        establishments: measure(0)?,
        jobs: measure(1)?,
        annual_payroll_usd: measure(2)?,
        mean_weekly_wage_usd: measure(3)?,
    })
}

fn coordinate(value: &str, whole_digits: usize, bound: u16) -> Result<String, Error> {
    if !value.is_ascii()
        || value.len() != whole_digits + 9
        || !matches!(value.as_bytes()[0], b'+' | b'-')
    {
        return Err(Error::Geography);
    }
    let (whole, fraction) = value[1..].split_once('.').ok_or(Error::Geography)?;
    if whole.len() != whole_digits
        || fraction.len() != 7
        || !whole
            .bytes()
            .chain(fraction.bytes())
            .all(|b| b.is_ascii_digit())
    {
        return Err(Error::Geography);
    }
    let degrees = whole.parse::<u16>().map_err(|_| Error::Geography)?;
    if degrees > bound || (degrees == bound && fraction != "0000000") {
        return Err(Error::Geography);
    }
    Ok(value.to_owned())
}
fn county(fields: &[&str]) -> Result<CountyReference, Error> {
    if fields.len() != COLUMN_COUNT {
        return Err(Error::CsvShape);
    }
    let geoid = CountyGeoid::try_from(fields[0]).map_err(Error::CountyIdentity)?;
    if !matches!(
        geoid.jurisdiction(),
        CountyJurisdiction::State | CountyJurisdiction::DistrictOfColumbia
    ) {
        return Err(Error::OutsideDomesticScope(geoid));
    }
    if geoid.state_fips() != fields[1].as_bytes()
        || geoid.county_fips() != fields[2].as_bytes()
        || fields[3].is_empty()
    {
        return Err(Error::Geography);
    }
    let estimate = |index: usize| -> Result<AcsEstimate, Error> {
        let offset = 8 + index * 6;
        Ok(AcsEstimate {
            estimate: acs_cell(&fields[offset..offset + 3])?,
            margin_of_error: acs_cell(&fields[offset + 3..offset + 6])?,
        })
    };
    let residents = ResidentEstimates {
        population_persons: estimate(0)?,
        households: estimate(1)?,
        age_16_plus_persons: estimate(2)?,
        labor_force_persons: estimate(3)?,
        civilian_labor_force_persons: estimate(4)?,
        civilian_employed_persons: estimate(5)?,
        civilian_unemployed_persons: estimate(6)?,
        armed_forces_persons: estimate(7)?,
        not_in_labor_force_persons: estimate(8)?,
    };
    resident_partitions(&residents)?;
    Ok(CountyReference {
        geoid,
        name: fields[3].to_owned(),
        land_square_metres: integer(fields[4])?,
        water_square_metres: integer(fields[5])?,
        internal_point: InternalPoint {
            latitude: coordinate(fields[6], 2, 90)?,
            longitude: coordinate(fields[7], 3, 180)?,
        },
        residents,
        workplaces: qcew(&fields[62..])?,
    })
}
fn resident_partitions(r: &ResidentEstimates) -> Result<(), Error> {
    for (total, left, right) in [
        (
            &r.age_16_plus_persons,
            &r.labor_force_persons,
            &r.not_in_labor_force_persons,
        ),
        (
            &r.labor_force_persons,
            &r.civilian_labor_force_persons,
            &r.armed_forces_persons,
        ),
        (
            &r.civilian_labor_force_persons,
            &r.civilian_employed_persons,
            &r.civilian_unemployed_persons,
        ),
    ] {
        if let (Some(total), Some(left), Some(right)) = (
            total.estimate.value,
            left.estimate.value,
            right.estimate.value,
        ) {
            if left.checked_add(right) != Some(total) {
                return Err(Error::ResidentPartition);
            }
        }
    }
    if let (Some(population), Some(adults)) = (
        r.population_persons.estimate.value,
        r.age_16_plus_persons.estimate.value,
    ) {
        if adults > population {
            return Err(Error::ResidentPartition);
        }
    }
    Ok(())
}
