//! Captured, normalized Designed physical content with separate observed evidence.
//! Both regional and statewide authoring feed the same material compiler.

mod captured;

#[cfg(test)]
mod experiment_tests;

mod maintenance;

mod model;

#[cfg(test)]
mod normalized_tests;

mod regional;

mod source;

mod statewide;

mod validate;

pub use model::*;

#[path = "michigan_material/load.rs"]
mod load;

use load::{identity, SOURCE_URL};
pub use load::{
    MichiganControlReport, MichiganDeliveryPreset, MichiganMaterialCatalog, MichiganMaterialError,
    MAX_MICHIGAN_SOURCE_BYTES, MICHIGAN_INDUSTRY_BASELINE_SHA256,
};

use crate::michigan_defines::{MichiganDefines, MichiganDefinesError};
use babylon_kernel::content_digest::sha256_of;
