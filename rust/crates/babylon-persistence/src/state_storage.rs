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
// Task 5 condition (b): `EncodedState` stays reachable at its old state_storage
// path even though this module is private and no in-tree caller names it yet.
#[allow(
    unused_imports,
    reason = "Task 5 condition (b): preserve EncodedState's old module path"
)]
pub use register::{
    encode_lookup, encode_register_with_opening, EncodedState, OpeningRegister, StorageError,
};

use layout::layout;
use schema::Cursor;
