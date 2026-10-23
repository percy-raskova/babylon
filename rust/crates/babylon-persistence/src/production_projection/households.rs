//! Resident stocks and explicit consumption, separate from merchant stock exits.
pub(crate) mod services;

pub use services::{CompletedHouseholdService, ProductionHouseholdServiceAccount};

#[path = "households/projection.rs"]
mod projection;

use projection::Result;
pub(super) use projection::{completed_balances, project_with_labels};
pub use projection::{
    CompletedHouseholdBalance, ProductionHouseholdAccount, ProductionHouseholdKind,
};

use super::{lifecycle, ProductionProjectionError};
use crate::michigan_economy::digest_hex;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::{GoodId, MaterialCircuitState, UnitId};
use babylon_tick::material_world::MaterialTickReceipts;
