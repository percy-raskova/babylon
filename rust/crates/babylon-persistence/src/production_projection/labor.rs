//! Accounting from validated adjacent registers and the completed receipt family.

mod attendance;

#[cfg(test)]
mod tests;

#[path = "labor/projection.rs"]
mod projection;

pub(super) use projection::project_labor_accounts;
use projection::{add_time, Budgets, Principal, Totals};
#[cfg(test)]
use projection::{budgets, completed_totals};

use super::ProductionProjectionError;
#[cfg(test)]
use crate::michigan_economy::digest_hex;
#[cfg(test)]
use crate::production_observation::CompletedProductionLabor;
use babylon_material_circuit::MaterialCircuitState;
#[cfg(test)]
use babylon_material_circuit::{ProcessId, SiteId, UnitId};
use babylon_tick::material_world::MaterialTickReceipts;
