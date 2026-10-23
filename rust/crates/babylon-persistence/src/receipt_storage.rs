//! Lossless storage of the one current complete V18 receipt format.
//! Canonical identities/hashes remain the authoritative evidence; this is a storage codec.
mod amount;

mod layout;

mod numeric;

#[path = "receipt_storage/storage.rs"]
mod storage;

#[cfg(test)]
#[allow(unused_imports)]
pub(crate) use storage::typed_admission_count;
pub use storage::Error;
#[allow(unused_imports)]
use storage::{
    buffer, decode_header, encode_columns, family_length, pack_row, prefer_family, stored_family,
    transpose, unpack_row, Cursor, FamilyPayload, Header, Result, CANONICAL_DOMAIN, DOMAIN,
};
#[allow(unused_imports)]
pub(crate) use storage::{
    decode_admitted, encode, restore_canonical, AdmittedReceipts, MAX_RECEIPT_STORAGE_BYTES,
};

#[allow(unused_imports)]
use crate::state_storage::{StorageError, TypedLookup};
#[allow(unused_imports)]
use crate::storage_compression::{compress_exact, decompress_exact, StorageCompressionError};
#[allow(unused_imports)]
use babylon_kernel::content_digest::sha256_of;
#[allow(unused_imports)]
use babylon_tick::material_world::{
    decode_material_receipts, receipt_row_limit, MaterialTickReceipts,
    MAX_MATERIAL_TICK_RECEIPT_BYTES, RECEIPT_FAMILY_COUNT, RECEIPT_ROW_BYTES,
};
