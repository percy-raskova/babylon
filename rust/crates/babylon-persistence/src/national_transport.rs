//! Bounded immutable source evidence and a Designed national transport graph.
//!
//! All counties remain actors. Mode compatibility and directed missing bulk
//! access are explicit. Capacity, timing and costs are Designed; costs are
//! unexecuted context until an authoritative monetary consumer pays a carrier.
//! This reference initializes no campaign and proves no adequate supply.

mod model;

mod raw;

#[cfg(test)]
mod tests;

mod validate;

pub use model::*;

#[path = "national_transport/artifact.rs"]
mod artifact;

#[allow(unused_imports)]
use artifact::{
    decode_gzip, parse_captured, qualify, ARTIFACT, ARTIFACT_SHA256, MAX_COMPRESSED_BYTES,
    MAX_DECODED_BYTES, POLICY, REFERENCE, SOURCES, SOURCES_SHA256,
};
pub use artifact::{
    national_transport_reference, NationalTransportError, NationalTransportReference,
};

#[allow(unused_imports)]
use crate::national_counties::{national_county_reference, NationalCountyReference};
#[allow(unused_imports)]
use babylon_kernel::{
    content_digest::sha256_of,
    economic_location::{EconomicLocation, ForeignCounterpart, UsDependency},
    geography::CountyGeoid,
};
#[allow(unused_imports)]
use std::{collections::BTreeMap, fmt::Write, io::Read, sync::OnceLock};

#[cfg(test)]
#[allow(unused_imports)]
pub(crate) use artifact::parse;
