//! Shared gram capacity from authenticated opening budgets and committed movements.

mod aid;

mod rolling;

#[cfg(test)]
mod tests;

#[path = "freight/projection.rs"]
mod projection;

#[cfg(test)]
pub(super) use projection::project_freight_capacity_accounts;
pub(super) use projection::project_with_labels;
use projection::{
    budgets, reservation_receipts, Budgets, CompletedReservations, ReservationInput, Reservations,
    Result, RouteIndex,
};

use super::ProductionProjectionError;
#[cfg(test)]
use crate::michigan_economy::digest_hex;
#[cfg(test)]
use crate::production_observation::{
    ProductionFreightOrderDefinition, ProductionFreightReservation,
};
use babylon_material_circuit::MaterialCircuitState;
#[cfg(test)]
use babylon_tick::material_world::MaterialTickReceipts;
#[cfg(test)]
use std::collections::BTreeMap;
