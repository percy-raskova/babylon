//! Accounting from validated adjacent registers and the completed receipt family.

mod attendance;

#[cfg(test)]
mod tests;

#[path = "labor/projection.rs"]
mod projection;

pub(super) use projection::project_labor_accounts;
use projection::{add_time, Budgets, Principal, Totals};

use super::ProductionProjectionError;
use babylon_material_circuit::MaterialCircuitState;
use babylon_tick::material_world::MaterialTickReceipts;
