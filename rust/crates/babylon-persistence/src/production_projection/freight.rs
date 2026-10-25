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
use babylon_material_circuit::{MaterialCatalog, MaterialCircuitState};
