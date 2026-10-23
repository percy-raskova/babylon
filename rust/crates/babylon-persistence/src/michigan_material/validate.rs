//! Admission checks consume captured authority only, including on restart.
mod physical;

#[path = "validate/rules.rs"]
mod rules;

#[allow(unused_imports)]
pub(super) use rules::{apply, canonicalize, content, interventions};
#[allow(unused_imports)]
use rules::{
    county, digest, industry_authority, key, merchants, path, production_ceilings, route_ceilings,
    source_authority, unique, workforce,
};

#[allow(unused_imports)]
use super::{
    MichiganDeliveryPreset, MichiganIntervention, MichiganMaterialCorridor, MichiganMaterialError,
    MichiganMaterialGood, MichiganMaterialPath, MichiganMaterialSite, MichiganNormalizedContent,
    MichiganOwnerSource, MichiganSiteRole,
};
#[allow(unused_imports)]
use std::collections::{BTreeMap, BTreeSet};
