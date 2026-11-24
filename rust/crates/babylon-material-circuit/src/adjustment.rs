//! The rules of ADR314 measured in rounds eight to ten, each asked for by a market policy.

mod bound;
mod policy;
mod receipts;
mod rest;
mod restart;
mod standing;

pub(crate) use bound::{bound_hiring, HiringBound};

#[cfg(test)]
pub(crate) use policy::refuse_combinations;
pub use policy::AdjustmentRule;
pub(crate) use policy::{admit, asks};
pub use receipts::{
    AdjustmentReceipt, GoodsOfferReceipt, HiringBoundReceipt, HiringLimit, OwnerSpareReceipt,
    PlaceMoveReceipt, RestartReceipt, RestartTest, RestingPriceReceipt, RestingPriceToCostReceipt,
    StopReceipt,
};
pub(crate) use rest::resting_among;
#[cfg(test)]
pub(crate) use rest::rests;
pub(crate) use restart::restart_stopped;
pub use restart::RESTART_QUIET_PERIODS;
#[cfg(test)]
pub(crate) use standing::{judge, SiteTest};
pub(crate) use standing::{test_workplaces, StopRound};
pub use standing::{StopHold, WorkplaceStanding, WorkplaceStandingRow};
