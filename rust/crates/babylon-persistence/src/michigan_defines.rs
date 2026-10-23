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

#[allow(unused_imports)]
use defines::{validate_process, MAX_EXACT_INTEGER};
#[allow(unused_imports)]
pub(crate) use defines::{
    CorridorDefines, MichiganDefines, OrganizerDefines, ProcessDefines, RegionalMassDefines,
    RouteDefines, SharedFreightDefines, StaffingDefines,
};
pub use defines::{MichiganDefinesError, MAX_MICHIGAN_DEFINES_BYTES};

#[allow(unused_imports)]
use babylon_kernel::clock::{DAYS_PER_TICK, WEEKS_PER_TICK};
#[allow(unused_imports)]
use serde::{Deserialize, Serialize};
#[allow(unused_imports)]
use std::collections::BTreeMap;
