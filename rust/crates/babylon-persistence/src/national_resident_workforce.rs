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

#[allow(unused_imports)]
use artifact::{
    decode, ARTIFACT, ARTIFACT_SHA256, COUNTY_COUNT, COUNTY_REFERENCE_SHA256, MAX_COMPRESSED_BYTES,
    MAX_DECODED_BYTES, REFERENCE,
};
pub use artifact::{
    national_resident_workforce_reference, NationalResidentWorkforceReference,
    ResidentWorkforceReferenceError,
};

#[allow(unused_imports)]
use crate::national_counties::{
    national_county_reference, NationalCountyReference, NationalCountyReferenceError,
};
#[allow(unused_imports)]
use babylon_kernel::{content_digest::sha256_of, geography::CountyGeoid};
#[allow(unused_imports)]
use std::{io::Read, sync::OnceLock};
