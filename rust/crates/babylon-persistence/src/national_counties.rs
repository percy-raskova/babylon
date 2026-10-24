//! Immutable capture of the pinned 2024 national county reference artifact.
//!
//! TIGER supplies the 3,144-county fifty-state/DC roster. ACS supplies 2020–2024
//! five-year resident estimates and 90-percent margins of error. QCEW supplies
//! 2024 covered workplace jobs and payroll. These observations allocate no game
//! persons, households, labor pools, firms, money or production capacity.

mod parse;

#[cfg(test)]
mod tests;

pub(crate) use parse::acs_cell;

#[path = "national_counties/artifact.rs"]
mod artifact;

pub(crate) use artifact::ARTIFACT_SHA256;
pub use artifact::{
    national_county_reference, AcsEstimate, CountyReference, InternalPoint,
    NationalCountyReference, NationalCountyReferenceError, ObservationStatus, ResidentEstimates,
    SourceCell, WorkplaceObservations,
};
use artifact::{COUNTY_COUNT, MAX_CSV_BYTES};
