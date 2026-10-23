//! Explicit Michigan control choices imported into the common captured catalog.

#[cfg(test)]
mod tests;

#[path = "michigan_content/preset.rs"]
mod preset;

pub use preset::{MichiganContentError, MichiganContentPreset, MICHIGAN_CONTENT_PRESETS};

#[cfg(test)]
use crate::economic_content::EconomicContentAdmission;
#[cfg(test)]
use crate::michigan_material::MichiganMaterialCatalog;
