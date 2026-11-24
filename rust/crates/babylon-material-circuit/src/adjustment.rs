//! The rules of ADR314 measured in rounds eight to ten, each asked for by a market policy.

mod policy;

pub(crate) use policy::admit;
pub use policy::AdjustmentRule;
#[cfg(test)]
pub(crate) use policy::{asks, refuse_combinations, NOT_YET_BUILT};
