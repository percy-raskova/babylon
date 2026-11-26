//! Regenerate one national opening from supplied source captures and Designed policy.
//! This module owns no mutable runtime or filesystem fallback.

mod actors;

mod dealing;

pub mod aid;
pub mod claimant;

mod equipment;

mod external;

pub(super) mod financial;

mod fund;

mod household_time;
mod lifecycle;

mod markets;

mod routes;

mod templates;

#[path = "opening/build.rs"]
mod build;

mod detail;

use build::{amount, quantity, sum_amount, ActorContext, Builder, Result};
pub use build::{
    build_national_opening, NationalOpening, NationalOpeningError, NationalOpeningPolicy,
};
pub use fund::fund_account;

#[cfg(test)]
mod grain_controls;
