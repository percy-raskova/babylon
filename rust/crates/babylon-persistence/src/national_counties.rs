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

#[allow(unused_imports)]
pub(crate) use artifact::ARTIFACT_SHA256;
#[allow(unused_imports)]
use artifact::{
    decode_gzip, ARTIFACT, COUNTY_COUNT, MAX_COMPRESSED_BYTES, MAX_CSV_BYTES, REFERENCE,
};
pub use artifact::{
    national_county_reference, AcsEstimate, CountyReference, InternalPoint,
    NationalCountyReference, NationalCountyReferenceError, ObservationStatus, ResidentEstimates,
    SourceCell, WorkplaceObservations,
};

#[allow(unused_imports)]
use babylon_kernel::{
    content_digest::sha256_of,
    geography::{CountyGeoid, CountyGeoidError, NationalCountyRoster, NATIONAL_COUNTY_COUNT},
};
#[allow(unused_imports)]
use parse::parse_csv;
#[allow(unused_imports)]
#[cfg(test)]
use parse::qcew;
#[allow(unused_imports)]
use std::{io::Read, sync::OnceLock};
