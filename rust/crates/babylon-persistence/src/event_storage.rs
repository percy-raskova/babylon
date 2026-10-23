//! Exact event dictionaries and native typed array chunks. Caller holds campaign
//! writer ownership and writes the durable marker last in the same transaction.
mod node_keys;

#[path = "event_storage/store.rs"]
mod store;

#[allow(unused_imports)]
pub(crate) use store::insert;
pub use store::Error;
#[allow(unused_imports)]
use store::{
    array, bits, collect_wanted, db, field_csv, id, lane, load_matching, project, reference,
    refuse, write_fields, write_lookups, write_parents, Field, KeyReference, KeyReferences, Lookup,
    LookupValue, Wanted, CHUNK,
};

#[allow(unused_imports)]
use crate::{identity::CampaignId, runtime::RustPersistenceRuntimeError};
#[allow(unused_imports)]
use babylon_bsl::identity_codec::StableBslValue;
#[allow(unused_imports)]
use babylon_tick::replay_session::SuccessfulEvent;
#[allow(unused_imports)]
use postgres::{
    binary_copy::BinaryCopyInWriter,
    fallible_iterator::FallibleIterator as _,
    types::{FromSqlOwned, ToSql, Type},
    GenericClient,
};
#[allow(unused_imports)]
use std::collections::{BTreeMap, BTreeSet};
#[allow(unused_imports)]
use std::io::Write;
