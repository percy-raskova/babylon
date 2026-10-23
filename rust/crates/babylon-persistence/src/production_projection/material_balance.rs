//! Completed physical accounts from verified adjacent registers and receipts.
//!
//! This projection never allocates batches, routes freight, or advances a world.
//! It reports actual receipt quantities using the recipe that governed the period.

#[cfg(test)]
mod tests;

#[path = "material_balance/balance.rs"]
mod balance;

#[cfg(test)]
#[allow(unused_imports)]
pub(super) use balance::project_material_balance;
#[allow(unused_imports)]
pub(super) use balance::project_with_labels;
#[allow(unused_imports)]
use balance::{
    add, add_dispatches, add_final_demand, add_local_transfers, add_losses, add_production,
    add_transport, check_movement, finish_row, inventory_ledger, multiply, order_map, process_map,
    Amounts, Ledger, Movement, Movements, OrderPrincipal, Orders, Principal, Process, Processes,
};
pub use balance::{CompletedMaterialBalance, ProductionMaterialBalanceRow};

#[allow(unused_imports)]
use super::ProductionProjectionError;
#[allow(unused_imports)]
use crate::michigan_economy::digest_hex;
#[allow(unused_imports)]
#[cfg(test)]
use crate::michigan_material::MichiganMaterialCatalog;
#[allow(unused_imports)]
use babylon_material_circuit::{
    GoodId, MaterialCircuitState, OrderId, OrderRow, ProcessId, SiteId, UnitId,
};
#[allow(unused_imports)]
use babylon_tick::material_world::MaterialTickReceipts;
#[allow(unused_imports)]
use serde::{Deserialize, Serialize};
#[allow(unused_imports)]
use std::collections::{BTreeMap, BTreeSet};
