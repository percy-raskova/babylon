//! Completed physical accounts from verified adjacent registers and receipts.
//!
//! This projection never allocates batches, routes freight, or advances a world.
//! It reports actual receipt quantities using the recipe that governed the period.

#[cfg(test)]
mod tests;

#[path = "material_balance/balance.rs"]
mod balance;

pub(super) use balance::project_with_labels;
pub use balance::{CompletedMaterialBalance, ProductionMaterialBalanceRow};
