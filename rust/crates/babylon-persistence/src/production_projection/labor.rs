//! Accounting from validated adjacent registers and the completed receipt family.

mod attendance;

#[cfg(test)]
mod tests;

#[path = "labor/projection.rs"]
mod projection;

#[allow(unused_imports)]
pub(super) use projection::project_labor_accounts;
#[allow(unused_imports)]
use projection::{
    add_handling_time, add_time, budgets, completed_totals, process_labor, Budgets, LaborTotals,
    Principal, Totals,
};

#[allow(unused_imports)]
use super::ProductionProjectionError;
#[allow(unused_imports)]
use crate::{
    michigan_economy::digest_hex, production_observation::CompletedProductionLabor,
    production_observation::ProductionLaborAccount,
};
#[allow(unused_imports)]
use babylon_material_circuit::{MaterialCircuitState, ProcessId, SiteId, UnitId};
#[allow(unused_imports)]
use babylon_tick::material_world::MaterialTickReceipts;
#[allow(unused_imports)]
use std::collections::{BTreeMap, BTreeSet};
