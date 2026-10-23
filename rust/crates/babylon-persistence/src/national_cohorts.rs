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

#[cfg(test)]
use artifact::{decode_gzip, ARTIFACT};
pub use artifact::{
    national_cohort_reference, NationalCohortReference, NationalCohortReferenceError,
    LEAF_BASIS_SHA256,
};
use artifact::{ADMITTED_COUNT, GROUP_COUNT, MEMBER_COUNT};
