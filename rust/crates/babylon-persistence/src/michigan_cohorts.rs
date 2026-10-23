//! Observed county-sector BUSINESS aggregates in a separate immutable foundation.
//!
//! A node represents one source cell, not a named enterprise or allocated workers.
//! Sector hyperedges classify those aggregates; they imply no trade, employment,
//! organization membership, physical production, or ownership relation.

#[cfg(test)]
mod tests;

#[path = "michigan_cohorts/build.rs"]
mod build;

#[cfg(test)]
pub(crate) use build::michigan_staffed_scenario;
pub(crate) use build::{append_workforce_seed, build_cohorts_from_sources};
#[cfg(test)]
use build::{build_cohorts, BUSINESS_FIELDS};
pub use build::{
    michigan_business_local_name, michigan_business_subject, michigan_business_subject_for_owner,
    michigan_cohort_foundation, michigan_cohorts, michigan_sector_subject, MichiganCohorts,
    MichiganCohortsError, MICHIGAN_COHORT_SCENARIO, MICHIGAN_COHORT_SESSION,
};

#[cfg(test)]
use crate::michigan_economy::michigan_economy;
#[cfg(test)]
use crate::michigan_sectors::{michigan_county_sectors, MichiganSectorDisposition};
#[cfg(test)]
use babylon_graph::hypergraph_store::HypergraphStore;
#[cfg(test)]
use babylon_graph::stable_element::StableElementKey;
#[cfg(test)]
use babylon_tick::replay_session::ReplayTickSession;
