//! Canonical current routed-material state bytes for restart and replay.

mod accounting;

mod aid;

mod capacity;

mod equipment;

mod financial;

mod household_time;

mod recurring;

#[cfg(test)]
mod row_limits_tests;

mod services;

mod valuation;

#[path = "wire/state.rs"]
mod state;

pub(crate) use state::Cursor;
use state::{append_bounded_rows, append_rows, decode_bounded_rows, decode_rows};
#[cfg(test)]
use state::{
    append_inventory, decode_input_coefficients, decode_inventory, decode_stage_capacities,
    decode_supplier_routes,
};
pub use state::{
    decode_material_circuit_state, encode_material_circuit_state, material_circuit_state_digest,
    MATERIAL_CIRCUIT_SOURCE_SHA256, MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES,
};

#[cfg(test)]
use crate::{
    GoodId, InventoryRow, MaterialCircuitError, SiteId, UnitId, MAX_MATERIAL_CIRCUIT_ROWS,
};
