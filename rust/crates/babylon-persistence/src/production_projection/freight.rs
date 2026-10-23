//! Shared gram capacity from authenticated opening budgets and committed movements.

mod aid;

mod rolling;

#[cfg(test)]
mod tests;

#[path = "freight/projection.rs"]
mod projection;

#[cfg(test)]
#[allow(unused_imports)]
pub(super) use projection::project_freight_capacity_accounts;
#[allow(unused_imports)]
pub(super) use projection::project_with_labels;
#[allow(unused_imports)]
use projection::{
    budgets, capacity_order, completed_reservations, participants, reconcile_reservation_budgets,
    reservation_receipts, Budgets, CapacityKey, CompletedReservations, OrderDefinitions,
    Participants, RawReservation, ReservationInput, ReservationOrders, Reservations, Result,
    RouteIndex,
};

#[allow(unused_imports)]
use super::{
    outbound::{completed_facts, identity, same_rows, OutboundFact},
    ProductionProjectionError,
};
#[allow(unused_imports)]
use crate::{
    michigan_economy::digest_hex,
    production_observation::CompletedProductionFreightCapacity,
    production_observation::ProductionCapacityKind,
    production_observation::ProductionFreightCapacityAccount,
    production_observation::ProductionFreightCapacityOrder,
    production_observation::{
        FreightOrderRegistry, ProductionFreightOrderDefinition, ProductionFreightReservation,
    },
};
#[allow(unused_imports)]
use babylon_material_circuit::{
    CorridorId, MaterialCircuitState, RouteId, RouteStage, SiteId, SupplierTransport,
};
#[allow(unused_imports)]
use babylon_tick::material_world::MaterialTickReceipts;
#[allow(unused_imports)]
use std::collections::{BTreeMap, BTreeSet};
