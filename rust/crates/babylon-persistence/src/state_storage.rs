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

use register::{columns, rows, MAX_BYTES};
pub(crate) use register::{decode_admitted, decode_against_admitted, MAX_STATE_PACKAGE_BYTES};
pub use register::{encode_lookup, encode_register_with_opening, OpeningRegister, StorageError};

use layout::layout;
use schema::Cursor;
