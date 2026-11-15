//! Settled payments into and out of the selected geographic account group.

#[cfg(test)]
#[path = "money_map/tests.rs"]
mod tests;

#[path = "money_map/geometry.rs"]
mod geometry;
#[path = "money_map/rail.rs"]
mod rail;

#[path = "money_map/state.rs"]
mod state;

pub(super) use state::install;
pub(crate) use state::MoneyRail;
