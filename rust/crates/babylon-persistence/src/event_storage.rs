//! Exact event dictionaries and native typed array chunks. Caller holds campaign
//! writer ownership and writes the durable marker last in the same transaction.
mod node_keys;

#[path = "event_storage/store.rs"]
mod store;

pub(crate) use store::insert;
pub use store::Error;
use store::{db, load_matching, refuse, KeyReference, KeyReferences, Lookup, CHUNK};
