//! Pinned ACS household, household-person, income and earnings margins for 3,144 counties.
//!
//! These are separate 2020–2024 five-year marginal estimates, with original
//! 90-percent margins of error. They establish no joint household profiles,
//! workplace allocation, class, wages, wealth, domestic labor or game time.
//! Raw annotations are unavailable in the source bulk files, not empty strings.

mod model;

mod parse;

#[cfg(test)]
mod tests;

pub use model::*;

#[path = "national_households/artifact.rs"]
mod artifact;

#[allow(unused_imports)]
use artifact::{
    decode, ARTIFACT, ARTIFACT_SHA256, COUNTY_COUNT, COUNTY_REFERENCE_SHA256, MAX_COMPRESSED_BYTES,
    MAX_DECODED_BYTES, REFERENCE,
};
pub use artifact::{
    national_household_reference, HouseholdReferenceError, NationalHouseholdReference,
};

#[allow(unused_imports)]
use crate::national_counties::{
    national_county_reference, NationalCountyReference, NationalCountyReferenceError,
};
#[allow(unused_imports)]
use babylon_kernel::{
    content_digest::sha256_of,
    geography::{CountyGeoid, NATIONAL_COUNTY_COUNT},
};
#[allow(unused_imports)]
use std::{io::Read, sync::OnceLock};
