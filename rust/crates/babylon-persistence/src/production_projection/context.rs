//! Captured source context with native geographic scope and explicit missingness.

#[cfg(test)]
mod tests;

#[path = "context/rows.rs"]
mod rows;

#[allow(unused_imports)]
pub(crate) use rows::attach_observed_context;
#[allow(unused_imports)]
use rows::{
    checked_context, context_rows, national_rows, subtotal, visible_sites, ContextRows, Result,
};

#[allow(unused_imports)]
use super::{metadata::Metadata, ProductionProjectionError};
#[allow(unused_imports)]
use crate::{
    economic_catalog::{EconomicProjectionView, EconomicSiteSource, EconomicSourceView},
    economic_content::EconomicContentAdmission,
    michigan_cohorts::michigan_business_subject_for_owner,
    michigan_economy::digest_hex,
    michigan_material::MichiganOwnerSource,
    observer_reader::ObserverVisibility,
    production_observation::{
        DesignedProcessAttribution, ObservedKnownSubtotal, ObservedNationalCohortContext,
        ObservedSectorContext, ProductionBusinessSubject, ProductionSnapshot,
    },
    ArchiveEvidenceClass,
};
#[allow(unused_imports)]
use babylon_graph::stable_element::StableElementKey;
#[allow(unused_imports)]
use std::collections::{BTreeMap, BTreeSet};
