//! Current lossless state17 storage. Canonical engine bytes remain the authority.
//! Storage sections have compiled schemas; no identity position maps are stored.
mod layout;

mod lookup;

mod offers;

mod schema;

#[cfg(test)]
mod tests;

pub use lookup::{IdentityEntry, IdentityKind, TypedLookup};

#[path = "state_storage/register.rs"]
mod register;

#[cfg(test)]
use register::{
    append_block, block, compressed, digest, expand, normalize, normalized_width, restore_section,
    stored_section, Block, StoredSection, DOMAIN,
};
use register::{columns, rows, MAX_BYTES};
pub(crate) use register::{decode_admitted, decode_against_admitted, MAX_STATE_PACKAGE_BYTES};
pub use register::{encode_lookup, encode_register_with_opening, OpeningRegister, StorageError};

#[cfg(test)]
use crate::storage_compression::{compress_exact, decompress_exact};
#[cfg(test)]
use babylon_tick::material_world::MaterialWorldRegister;
#[cfg(test)]
use layout::{kind, layout};
use schema::Cursor;
#[cfg(test)]
use schema::{sections, Section};
