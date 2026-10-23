//! Resident stocks and explicit consumption, separate from merchant stock exits.
pub(crate) mod services;

pub use services::{CompletedHouseholdService, ProductionHouseholdServiceAccount};

#[path = "households/projection.rs"]
mod projection;

#[allow(unused_imports)]
pub(super) use projection::{completed_balances, project_with_labels};
#[allow(unused_imports)]
use projection::{received_stock, required_quantity, validate_consumption_balance, Key, Result};
pub use projection::{
    CompletedHouseholdBalance, ProductionHouseholdAccount, ProductionHouseholdKind,
};

#[allow(unused_imports)]
use super::{lifecycle, ProductionProjectionError};
#[allow(unused_imports)]
use crate::michigan_economy::digest_hex;
#[allow(unused_imports)]
use babylon_kernel::economic_location::EconomicLocation;
#[allow(unused_imports)]
use babylon_material_circuit::{
    FinalDemandPrincipalId, GoodId, HouseholdCohort, HouseholdConsumptionReceipt,
    HouseholdDemandReceipt, HouseholdNeed, MaterialCircuitState, UnitId,
};
#[allow(unused_imports)]
use babylon_tick::material_world::MaterialTickReceipts;
#[allow(unused_imports)]
use serde::{Deserialize, Serialize};
#[allow(unused_imports)]
use std::collections::BTreeMap;
