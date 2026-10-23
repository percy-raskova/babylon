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

#[allow(unused_imports)]
use register::{
    append_block, array32, block, columns, compressed, digest, expand, normalize,
    normalize_existing_bounded, normalize_with, normalized_width, opening_xor_columns,
    restore_register, restore_section, restore_sections, rows, stored_section,
    validate_body_length, validate_descriptors, validate_opening_section, Block, Normalized,
    SectionDescriptors, StoredSection, DOMAIN, MAX_BYTES,
};
#[allow(unused_imports)]
pub(crate) use register::{decode_admitted, decode_against_admitted, MAX_STATE_PACKAGE_BYTES};
#[allow(unused_imports)]
pub use register::{
    encode_lookup, encode_register_with_opening, EncodedState, OpeningRegister, StorageError,
};

#[allow(unused_imports)]
use crate::storage_compression::{compress_exact, decompress_exact};
#[allow(unused_imports)]
use babylon_tick::material_world::{MaterialWorldRegister, MAX_MATERIAL_WORLD_REGISTER_BYTES};
#[allow(unused_imports)]
use layout::{kind, layout, Layout};
#[allow(unused_imports)]
use schema::{sections, Cursor, Section};
#[allow(unused_imports)]
use sha2::{Digest, Sha256};
#[allow(unused_imports)]
use std::{collections::BTreeMap, fmt};
