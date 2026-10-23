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

#[allow(unused_imports)]
pub(crate) use experiment::{digest_valid, hex, product, sum, validate_freight_authority, Result};
pub use experiment::{
    EmploymentStartingRow, ExperimentDelivery, ExperimentError, ExperimentIntervention,
    ExperimentProfile, SimulationExperimentV1, StartingSnapshot, MAX_EXPERIMENT_HORIZON,
    MAX_EXPERIMENT_INPUT_BYTES,
};

#[allow(unused_imports)]
use crate::material_runtime::MaterialRuntimeFoundation;
#[allow(unused_imports)]
use babylon_kernel::content_digest::sha256_of;
#[allow(unused_imports)]
use serde::{Deserialize, Serialize};
