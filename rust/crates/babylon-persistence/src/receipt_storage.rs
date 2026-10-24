//! Lossless storage of the one current complete V18 receipt format.
//! Canonical identities/hashes remain the authoritative evidence; this is a storage codec.
mod amount;

mod layout;

mod numeric;

#[path = "receipt_storage/storage.rs"]
mod storage;

#[cfg(test)]
pub(crate) use storage::typed_admission_count;
pub use storage::Error;
use storage::{buffer, Result};
pub(crate) use storage::{
    decode_admitted, encode, restore_canonical, AdmittedReceipts, MAX_RECEIPT_STORAGE_BYTES,
};
