//! Pinned, disjoint world reporting scopes and explicitly qualified source measures.
//!
//! Population projections and annual goods-trade dollars create no labor supply,
//! inventories, productive capacity, purchasing power or automatic demand.

mod model;

mod parse;

#[cfg(test)]
mod tests;

pub use model::*;

#[path = "world_reference/artifact.rs"]
mod artifact;

#[allow(unused_imports)]
use artifact::{
    decode, DIGESTS, MAX_COMPRESSED_BYTES, MAX_DECODED_BYTES, MEMBERSHIP, MEMBER_COUNT, POPULATION,
    REFERENCE, SCOPE_POLICY, TRADE,
};
pub use artifact::{world_reference, WorldReference, WorldReferenceError, WorldSourceDigests};

#[allow(unused_imports)]
use babylon_kernel::{
    content_digest::sha256_of,
    economic_location::{ForeignCounterpart, UsDependency},
};
#[allow(unused_imports)]
use std::{io::Read, sync::OnceLock};
