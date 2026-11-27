//! Bounded, immutable capture of disjoint 2024 QCEW county observation groups.
//!
//! Known subtotals are not complete totals when a member is suppressed. QCEW
//! workplace jobs are not distinct resident persons. Eligibility here allocates
//! no game firms, labor, recipes, stocks, capacities or monetary balances.

mod composition;
pub use composition::{IndustrySourceComposition, IndustrySourceRow};

mod mapping;

mod model;

mod parse;

#[cfg(test)]
mod tests;

pub use model::{
    CohortKey, CohortReference, KnownSubtotal, QcewDisclosure, SourceMember, WorkplaceCohortKey,
};

#[path = "national_cohorts/artifact.rs"]
mod artifact;

#[cfg(test)]
use artifact::{decode_gzip, ARTIFACT};
pub use artifact::{
    national_cohort_reference, national_cohort_reference_v2, NationalCohortReference,
    NationalCohortReferenceError, JOBS_BASIS_V2_SHA256, LEAF_BASIS_SHA256,
};
pub(crate) use artifact::{ARTIFACT_V2, MAPPING_V2};
