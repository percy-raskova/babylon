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

#[allow(unused_imports)]
use register::{
    admitted_count, appended, encode_period_lookup, period_lookup_chain, Cursor, Result,
    INITIAL_CHAIN_DOMAIN, LOOKUP_VERSION, PERIOD_CHAIN_DOMAIN,
};
pub use register::{
    decode, encode, initial_lookup_chain, lookup_identity, read_period_lookup, seed,
    DecodedPeriodLookup, EncodedMaterial, Error, LookupAnchor,
};
#[allow(unused_imports)]
pub(crate) use register::{
    decode_typed, decode_typed_with_witness, DecodedMaterial, LOOKUP_DOMAIN, MAX_LOOKUP_BYTES,
    MAX_LOOKUP_PACKAGE_BYTES,
};

#[allow(unused_imports)]
use crate::receipt_storage;
#[allow(unused_imports)]
use crate::state_storage::{self, IdentityEntry, StorageError};
#[allow(unused_imports)]
use crate::storage_compression::{compress_exact, decompress_exact, StorageCompressionError};
#[allow(unused_imports)]
use babylon_kernel::content_digest::sha256_of;
#[allow(unused_imports)]
use babylon_tick::material_world::{MaterialTickReceipts, MaterialWorldRegister};

pub use register::{
    MAX_STORED_MATERIAL_LOOKUP_DELTA_BYTES, MAX_STORED_MATERIAL_RECEIPT_BYTES,
    MAX_STORED_MATERIAL_REGISTER_BYTES,
};
