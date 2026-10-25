//! Exact successor world-register ownership for the routed material circuit.
//!
//! An active register contains the complete current opening state, never an economic
//! summary or a second inventory ledger. The graph-only digest stays unchanged.

mod aid_receipt;

mod collection_receipt;

mod equipment_receipt;

mod financial_receipt;

mod household_time_receipt;

#[cfg(test)]
mod household_time_tests;

mod income_receipt;

mod installation_decision;

mod maintenance_receipt;

mod monetary_receipt;

pub(crate) mod organizer_collection;

mod organizer_support;

mod organizer_time;

mod recurring_receipt;

mod service_receipt;

mod workforce_receipt;

#[cfg(test)]
mod tests;

#[path = "material_world/register.rs"]
mod register;

use register::ReceiptCursor;
#[cfg(test)]
use register::{bounded_bytes, encode_material_receipts, RECEIPT_DOMAIN};
pub use register::{
    decode_material_receipts, nominal_material_world_hash, receipt_family_bytes,
    receipt_family_rows, receipt_row_limit, validate_retained_collection, MaterialReceiptHandle,
    MaterialTickReceipts, MaterialWorldError, MaterialWorldRegister, PreparedMaterialWorld,
    SharedCanonicalBytes, MAX_MATERIAL_TICK_RECEIPT_BYTES, MAX_MATERIAL_WORLD_REGISTER_BYTES,
    RECEIPT_FAMILY_COUNT, RECEIPT_ROW_BYTES,
};
