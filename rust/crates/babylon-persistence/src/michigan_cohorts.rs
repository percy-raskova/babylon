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
#[allow(unused_imports)]
pub(crate) use build::michigan_staffed_scenario;
#[allow(unused_imports)]
use build::{
    append_business, append_sectors, build_cohorts, build_cohorts_with_workforce, BUSINESS_FIELDS,
};
#[allow(unused_imports)]
pub(crate) use build::{append_workforce_seed, build_cohorts_from_sources};
pub use build::{
    michigan_business_local_name, michigan_business_subject, michigan_business_subject_for_owner,
    michigan_cohort_foundation, michigan_cohorts, michigan_sector_subject, MichiganCohorts,
    MichiganCohortsError, MICHIGAN_COHORT_SCENARIO, MICHIGAN_COHORT_SESSION,
};

#[allow(unused_imports)]
use crate::{
    michigan_economy::{
        append_county_observations, foundation_from_sources, michigan_economy,
        MichiganEconomyError, QCEW_ECONOMICS_ARTIFACT_SHA256,
    },
    michigan_sectors::{
        michigan_county_sectors, MichiganCountySector, MichiganCountySectors, MichiganSectorCode,
        MichiganSectorDisposition, MichiganSectorsError, QCEW_SECTORS_ARTIFACT_SHA256,
        QCEW_SECTORS_SEMANTIC_SHA256,
    },
    FoundationContentBundle,
};
#[allow(unused_imports)]
use babylon_graph::{hypergraph_store::HypergraphStore, stable_element::StableElementKey};
#[allow(unused_imports)]
use babylon_tick::replay_session::ReplayTickSession;
#[allow(unused_imports)]
use std::{collections::BTreeMap, fmt::Write as _, sync::OnceLock};
