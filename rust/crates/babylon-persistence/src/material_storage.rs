//! Atomic staging of the current state and complete receipt storage codecs.
//! Lookup bytes are storage dependencies; canonical engine bytes remain unchanged.
mod descriptors;

mod receipt_witness;

pub use descriptors::Error as DescriptorError;

pub(crate) use receipt_witness::{AdmittedReceiptWitness, MaterialStorageWitnesses};

pub use crate::state_storage::{OpeningRegister, TypedLookup};

#[cfg(test)]
mod tests;

#[cfg(test)]
mod descriptor_controls;

#[cfg(test)]
mod descriptor_guard_controls;

#[path = "material_storage/register.rs"]
mod register;

#[cfg(test)]
pub(crate) use register::LOOKUP_DOMAIN;
use register::{admitted_count, Cursor, Result};
pub use register::{
    decode, encode, initial_lookup_chain, lookup_identity, read_period_lookup, seed,
    DecodedPeriodLookup, EncodedMaterial, Error, LookupAnchor,
};
pub(crate) use register::{
    decode_typed, decode_typed_with_witness, MaterialProvenance, MAX_LOOKUP_BYTES,
};

pub use register::{
    MAX_STORED_MATERIAL_LOOKUP_DELTA_BYTES, MAX_STORED_MATERIAL_RECEIPT_BYTES,
    MAX_STORED_MATERIAL_REGISTER_BYTES,
};
