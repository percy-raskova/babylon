//! The rules of ADR314 measured in rounds eight to ten, each asked for by a market policy.

mod bound;
mod policy;
mod receipts;

pub(crate) use bound::{bound_hiring, HiringBound};
pub use policy::AdjustmentRule;
pub(crate) use policy::{admit, asks};
#[cfg(test)]
pub(crate) use policy::{refuse_combinations, NOT_YET_BUILT};
pub use receipts::{AdjustmentReceipt, HiringBoundReceipt, HiringLimit, PlaceMoveReceipt};
