//! Exact committed material presentation using one captured economic opening.
pub(crate) mod context;

pub(crate) mod diagnostics;

mod equipment;

#[cfg(test)]
mod equipment_fixture;

mod events;

#[cfg(test)]
mod events_tests;

mod freight;

#[cfg(test)]
mod generic_tests;

pub(crate) mod history;

pub(crate) mod households;

mod labor;

pub(crate) mod lifecycle;

mod maintenance;

pub(crate) mod material_balance;

mod merchants;

pub(crate) mod metadata;

mod outbound;

pub(crate) mod prices;

#[cfg(test)]
mod prices_tests;

#[cfg(test)]
pub(crate) mod recurring_fixture;

mod routes;

mod services;

#[cfg(test)]
mod services_fixture;

pub(crate) mod sites;

pub(crate) mod staffing;

#[cfg(test)]
mod tests;

mod aid;

#[cfg(test)]
#[path = "production_projection/aid_projection_tests.rs"]
mod aid_projection_tests;

#[path = "production_projection/projection.rs"]
mod projection;

#[cfg(test)]
pub(crate) use projection::project_material_observation;
pub(crate) use projection::{project_economic_current, ProductionProjectionError};
