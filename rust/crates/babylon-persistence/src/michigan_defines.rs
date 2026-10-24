//! Required, bounded numeric parameters for a newly created Michigan campaign.
//! Canonical values, not TOML whitespace or a mutable file path, enter identity.

mod maintenance;

mod statewide;

pub(crate) use maintenance::MaintenanceDefines;

pub(crate) use statewide::{
    CommodityDefines, CommodityDisposition, CommodityUnit, MerchantDefines, StatewideDefines,
    TemplateDefines, TransportDefines,
};

#[path = "michigan_defines/defines.rs"]
mod defines;

use defines::MAX_EXACT_INTEGER;
pub(crate) use defines::{MichiganDefines, OrganizerDefines};
pub use defines::{MichiganDefinesError, MAX_MICHIGAN_DEFINES_BYTES};
