//! Explicit Michigan control choices imported into the common captured catalog.

#[cfg(test)]
mod tests;

#[path = "michigan_content/preset.rs"]
mod preset;

pub use preset::{MichiganContentError, MichiganContentPreset, MICHIGAN_CONTENT_PRESETS};

#[allow(unused_imports)]
use crate::{
    economic_content::EconomicContentAdmission,
    material_runtime::MaterialRuntimeFoundation,
    michigan_cohorts::MICHIGAN_COHORT_SCENARIO,
    michigan_material::{MichiganDeliveryPreset, MichiganMaterialCatalog},
};
