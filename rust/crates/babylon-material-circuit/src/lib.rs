//! Exact conserved production, inventory, order, and realization transitions.
#![forbid(unsafe_code)]
#![warn(clippy::pedantic)]

mod model;
mod transition;
mod wire;

pub use model::*;
pub use transition::advance_material_circuit_v1;
pub use wire::{
    decode_material_circuit_state_v1, encode_material_circuit_state_v1,
    material_circuit_state_v1_digest, MATERIAL_CIRCUIT_STATE_V1_DOMAIN_BYTES,
};
