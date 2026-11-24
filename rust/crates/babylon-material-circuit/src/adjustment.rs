//! The rules of ADR314 measured in rounds eight to ten, each asked for by a market policy.

mod bound;
mod policy;
mod receipts;
mod rest;
mod standing;

pub(crate) use bound::{bound_hiring, HiringBound};
pub use policy::AdjustmentRule;
pub(crate) use policy::{admit, asks};
#[cfg(test)]
pub(crate) use policy::{refuse_combinations, NOT_YET_BUILT};
pub use receipts::{
    AdjustmentReceipt, HiringBoundReceipt, HiringLimit, PlaceMoveReceipt, RestingPriceReceipt,
    StopReceipt,
};
pub(crate) use rest::resting_among;
#[cfg(test)]
pub(crate) use rest::rests;
#[cfg(test)]
pub(crate) use standing::{judge, SiteTest};
pub(crate) use standing::{test_workplaces, StopRound};
pub use standing::{StopHold, WorkplaceStanding, WorkplaceStandingRow};
