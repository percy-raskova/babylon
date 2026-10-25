//! Regenerate one national opening from supplied source captures and Designed policy.
//! This module owns no mutable runtime or filesystem fallback.

mod actors;

pub mod aid;

mod equipment;

mod external;

mod financial;

mod household_time;

mod markets;

mod routes;

mod templates;

#[path = "opening/build.rs"]
mod build;

mod detail;

pub(super) use build::FUNCTIONS;
use build::{amount, quantity, sum_amount, ActorContext, Builder, Result};
pub use build::{
    build_national_opening, NationalOpening, NationalOpeningError, NationalOpeningPolicy,
};
