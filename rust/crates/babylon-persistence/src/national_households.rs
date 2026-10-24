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

pub use artifact::{
    national_household_reference, HouseholdReferenceError, NationalHouseholdReference,
};
use artifact::{COUNTY_COUNT, MAX_DECODED_BYTES};
