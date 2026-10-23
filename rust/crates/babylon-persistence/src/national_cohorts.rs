//! Bounded, immutable capture of disjoint 2024 QCEW county observation groups.
//!
//! Known subtotals are not complete totals when a member is suppressed. QCEW
//! workplace jobs are not distinct resident persons. Eligibility here allocates
//! no game firms, labor, recipes, stocks, capacities or monetary balances.

mod mapping;

mod model;

mod parse;

#[cfg(test)]
mod tests;

pub use model::{CohortKey, CohortReference, KnownSubtotal, QcewDisclosure, SourceMember};

#[path = "national_cohorts/artifact.rs"]
mod artifact;

#[allow(unused_imports)]
use artifact::{
    decode_gzip, ADMITTED_COUNT, ARTIFACT, ARTIFACT_SHA256, GROUP_COUNT, MAX_COMPRESSED_BYTES,
    MAX_CSV_BYTES, MEMBER_COUNT, REFERENCE,
};
pub use artifact::{
    national_cohort_reference, NationalCohortReference, NationalCohortReferenceError,
    LEAF_BASIS_SHA256,
};

#[allow(unused_imports)]
use crate::national_counties::{
    national_county_reference, NationalCountyReference, NationalCountyReferenceError,
};
#[allow(unused_imports)]
use babylon_kernel::{
    content_digest::sha256_of,
    geography::{CountyGeoid, CountyGeoidError, NationalCountyRoster},
};
#[allow(unused_imports)]
use std::{io::Read, sync::OnceLock};
