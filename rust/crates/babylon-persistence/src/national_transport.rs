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

#[cfg(test)]
use artifact::{decode_gzip, ARTIFACT};
pub use artifact::{
    national_transport_reference, NationalTransportError, NationalTransportReference,
};

#[cfg(test)]
pub(crate) use artifact::parse;
