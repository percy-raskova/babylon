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

use register::{admitted_count, Cursor, Result};
pub use register::{
    decode, encode, initial_lookup_chain, lookup_identity, read_period_lookup, seed,
    DecodedPeriodLookup, EncodedMaterial, Error, LookupAnchor,
};
pub(crate) use register::{decode_typed, decode_typed_with_witness, MAX_LOOKUP_BYTES};
#[cfg(test)]
use register::{encode_period_lookup, period_lookup_chain};
#[cfg(test)]
pub(crate) use register::{DecodedMaterial, LOOKUP_DOMAIN};

#[cfg(test)]
use crate::state_storage::{self, IdentityEntry, StorageError};
#[cfg(test)]
use crate::storage_compression::{compress_exact, decompress_exact};
#[cfg(test)]
use babylon_kernel::content_digest::sha256_of;
#[cfg(test)]
use babylon_tick::material_world::MaterialWorldRegister;

pub use register::{
    MAX_STORED_MATERIAL_LOOKUP_DELTA_BYTES, MAX_STORED_MATERIAL_RECEIPT_BYTES,
    MAX_STORED_MATERIAL_REGISTER_BYTES,
};
