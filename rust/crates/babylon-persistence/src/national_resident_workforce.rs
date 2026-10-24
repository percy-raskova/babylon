//! Pinned ACS resident worker classes, separate from workplace jobs and payroll.
//!
//! The eight disjoint B24080 classes reconcile to the existing B23025 employed
//! resident control. Original sex-specific estimates and margins remain intact;
//! summing two estimates does not invent a combined margin of error.

mod model;

mod parse;

#[cfg(test)]
mod tests;

pub use model::*;

#[path = "national_resident_workforce/artifact.rs"]
mod artifact;

pub use artifact::{
    national_resident_workforce_reference, NationalResidentWorkforceReference,
    ResidentWorkforceReferenceError,
};
use artifact::{COUNTY_COUNT, MAX_DECODED_BYTES};
