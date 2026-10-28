//! Closed diagnostic inputs captured by the authoritative material foundation.
//!
//! Observations initialize named historical profiles; held-out observations never
//! enter this module. All trajectories use the ordinary material replay session.
mod freight;

pub(crate) mod regional;

pub mod report;

pub mod setup;

#[cfg(test)]
mod tests;

#[path = "simulation_experiment/experiment.rs"]
mod experiment;

pub(crate) use experiment::{admitted_freight_material, digest_valid, hex, product, sum, Result};
pub use experiment::{
    EmploymentStartingRow, ExperimentDelivery, ExperimentError, ExperimentIntervention,
    ExperimentProfile, SimulationExperimentV1, StartingSnapshot, MAX_EXPERIMENT_HORIZON,
    MAX_EXPERIMENT_INPUT_BYTES,
};
