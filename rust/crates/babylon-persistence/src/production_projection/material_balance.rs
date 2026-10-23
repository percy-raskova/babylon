//! Completed physical accounts from verified adjacent registers and receipts.
//!
//! This projection never allocates batches, routes freight, or advances a world.
//! It reports actual receipt quantities using the recipe that governed the period.

#[cfg(test)]
mod tests;

#[path = "material_balance/balance.rs"]
mod balance;

#[cfg(test)]
pub(super) use balance::project_material_balance;
pub(super) use balance::project_with_labels;
pub use balance::{CompletedMaterialBalance, ProductionMaterialBalanceRow};

#[cfg(test)]
use super::ProductionProjectionError;
#[cfg(test)]
use crate::michigan_economy::digest_hex;
#[cfg(test)]
use babylon_material_circuit::{
    GoodId, MaterialCircuitState, OrderId, OrderRow, ProcessId, SiteId, UnitId,
};
#[cfg(test)]
use babylon_tick::material_world::MaterialTickReceipts;
#[cfg(test)]
use std::collections::BTreeSet;
